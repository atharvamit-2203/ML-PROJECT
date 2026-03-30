import os
import pandas as pd
import yfinance as yf
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional, Dict
import datetime
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import json
import numpy as np
from sklearn.ensemble import RandomForestClassifier, GradientBoostingRegressor
from sklearn.linear_model import LinearRegression, LogisticRegression
from sklearn.metrics import accuracy_score

app = FastAPI()

# Enable CORS for frontend communication
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Resilient session for Yahoo Finance
session = requests.Session()
retry = Retry(total=3, backoff_factor=1, status_forcelist=[502, 503, 504])
session.mount('https://', HTTPAdapter(max_retries=retry))

# Common frontend IDs / aliases -> exchange symbols.
SYMBOL_ALIASES = {
    "TATAMOTORS": "TATAMOTORS.NS",
    "TATACHEM": "TATACHEM.NS",
    "SPARC": "SPARC.NS",
    "LT": "LT.NS",
    "TITAN": "TITAN.NS",
    "ULTRACEMCO": "ULTRACEMCO.NS",
    "ADANIGREEN": "ADANIGREEN.NS",
    "HDFC": "HDFCBANK.NS",
    "HINDUSTAN_ZINC": "HINDZINC.NS",
    "HINDZINC": "HINDZINC.NS",
    "BSE_FMCG": "^BSEFMC",
    "TLKM": "TLKM.JK",
}


def _extract_close_series(data: List[Dict]) -> List[float]:
    """Extract close prices from mixed-case OHLC payloads."""
    closes: List[float] = []
    for row in data:
        value = row.get("Close", row.get("close"))
        if value is None:
            continue
        try:
            closes.append(float(value))
        except (TypeError, ValueError):
            continue
    return closes


def _build_lagged_features(series: List[float], lags: int = 5):
    """Create autoregressive lag features: X[t] = series[t-lags:t], y[t] = series[t]."""
    arr = np.array(series, dtype=float)
    if len(arr) <= lags:
        return np.empty((0, lags)), np.array([])

    X, y = [], []
    for i in range(lags, len(arr)):
        X.append(arr[i - lags:i])
        y.append(arr[i])
    return np.array(X), np.array(y)


def _build_direction_dataset(series: List[float], lags: int = 5):
    """Build classification dataset for next-day direction using lagged returns."""
    arr = np.array(series, dtype=float)
    if len(arr) <= lags + 1:
        return np.empty((0, lags)), np.array([])

    returns = np.diff(arr) / arr[:-1]
    X, y = [], []
    for i in range(lags, len(returns)):
        X.append(returns[i - lags:i])
        y.append(1 if returns[i] > 0 else 0)
    return np.array(X), np.array(y)


def _build_multiclass_dataset(series: List[float], lags: int = 5):
    """Build 3-class dataset from next-day returns: SELL/NEUTRAL/BUY."""
    arr = np.array(series, dtype=float)
    if len(arr) <= lags + 1:
        return np.empty((0, lags)), np.array([])

    returns = np.diff(arr) / arr[:-1]
    X, y = [], []
    for i in range(lags, len(returns)):
        next_ret = returns[i]
        if next_ret < -0.005:
            label = 0  # SELL
        elif next_ret > 0.005:
            label = 2  # BUY
        else:
            label = 1  # NEUTRAL
        X.append(returns[i - lags:i])
        y.append(label)
    return np.array(X), np.array(y)


def _infer_dayfirst_from_values(values) -> bool:
    """Infer whether day-first parsing should be used for date strings."""
    sample_raw = ""
    for v in list(values)[:20]:
        if pd.notna(v):
            sample_raw = str(v).strip()
            if sample_raw:
                break
    # ISO-like format: YYYY-MM-DD -> month/day ambiguity does not apply.
    if len(sample_raw) >= 10 and sample_raw[4] == "-" and sample_raw[7] == "-":
        return False
    return True

def normalize_symbol(symbol: str) -> str:
    """Normalize symbols for Indian markets by appending .NS if needed"""
    if not symbol:
        return ""
    symbol = symbol.strip().upper().rstrip(",.;:")

    # Convert known aliases first.
    if symbol in SYMBOL_ALIASES:
        return SYMBOL_ALIASES[symbol]

    # If it's a popular Indian stock without .NS, append it
    indian_stocks = ["RELIANCE", "TCS", "HDFCBANK", "ICICIBANK", "INFY", "TATAMOTORS", "SBIN", "BHARTIARTL", "ITC", "KOTAKBANK", "LT", "HINDUNILVR", "BAJFINANCE", "ADANIENT", "SUNPHARMA", "TITAN", "AXISBANK", "ASIANPAINT", "MARUTI", "ULTRACEMCO"]
    if symbol in indian_stocks:
        return f"{symbol}.NS"
    return symbol


def build_symbol_candidates(symbol: str) -> List[str]:
    """Return prioritized candidate symbols to improve hit rate across providers."""
    raw = (symbol or "").strip().upper().rstrip(",.;:")
    if not raw:
        return []

    candidates: List[str] = []

    # Alias candidate first when known.
    if raw in SYMBOL_ALIASES:
        candidates.append(SYMBOL_ALIASES[raw])

    normalized = normalize_symbol(raw)
    candidates.append(normalized)
    candidates.append(raw)

    # If user already sent exchange suffix, try plain symbol too.
    if raw.endswith(".NS") or raw.endswith(".BO"):
        candidates.append(raw.rsplit(".", 1)[0])
    else:
        candidates.append(f"{raw}.NS")
        candidates.append(f"{raw}.BO")

    # Deduplicate while preserving order.
    seen = set()
    ordered: List[str] = []
    for c in candidates:
        if c and c not in seen:
            seen.add(c)
            ordered.append(c)
    return ordered


def _load_local_history_from_csv(symbol: str):
    """Load stock history from local CSV files as a fallback when remote APIs fail."""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    backend_dir = os.path.dirname(os.path.abspath(__file__))

    token = symbol.upper().replace(".NS", "").replace(".BO", "").replace("^", "")
    alias_token = SYMBOL_ALIASES.get(token, token).upper().replace(".NS", "").replace(".BO", "").replace("^", "")
    lookup_tokens = {token, alias_token}

    candidates = []
    for search_dir in [backend_dir, project_root]:
        try:
            for f in os.listdir(search_dir):
                if f.lower().endswith(".csv"):
                    candidates.append(os.path.join(search_dir, f))
        except Exception:
            continue

    # Prefer files that include any lookup token.
    ranked = []
    for p in candidates:
        name = os.path.basename(p).upper()
        score = 0
        for t in lookup_tokens:
            if t and t in name:
                score += len(t)
        if score > 0:
            ranked.append((score, p))
    ranked.sort(key=lambda x: x[0], reverse=True)

    for _, path in ranked:
        try:
            df = pd.read_csv(path)
            if df.empty:
                continue

            cols = list(df.columns)
            clean_cols = [str(c).lower().strip() for c in cols]

            date_idx = next((i for i, c in enumerate(clean_cols) if "date" in c or "time" in c), 0)
            date_col = cols[date_idx]

            # Auto-detect date format style to avoid dayfirst warnings on ISO dates.
            use_dayfirst = _infer_dayfirst_from_values(df[date_col].tolist())
            df[date_col] = pd.to_datetime(df[date_col], dayfirst=use_dayfirst, errors="coerce")
            df.dropna(subset=[date_col], inplace=True)
            if df.empty:
                continue

            open_col = next((cols[i] for i, c in enumerate(clean_cols) if c == "open"), None)
            high_col = next((cols[i] for i, c in enumerate(clean_cols) if c == "high"), None)
            low_col = next((cols[i] for i, c in enumerate(clean_cols) if c == "low"), None)
            close_col = next((cols[i] for i, c in enumerate(clean_cols) if c in ["close", "adjclose"]), None)
            volume_col = next((cols[i] for i, c in enumerate(clean_cols) if "volume" in c), None)

            if not close_col:
                # Try generic price-like columns.
                close_col = next((cols[i] for i, c in enumerate(clean_cols) if "price" in c), None)
            if not close_col:
                continue

            if not open_col:
                open_col = close_col
            if not high_col:
                high_col = close_col
            if not low_col:
                low_col = close_col

            # Coerce numeric columns once, then skip invalid rows safely.
            for c in [open_col, high_col, low_col, close_col]:
                df[c] = pd.to_numeric(df[c], errors="coerce")
            if volume_col:
                df[volume_col] = pd.to_numeric(df[volume_col], errors="coerce").fillna(0)

            df.dropna(subset=[open_col, high_col, low_col, close_col], inplace=True)
            if df.empty:
                continue

            df = df.sort_values(by=date_col)
            out = []
            for _, row in df.iterrows():
                out.append({
                    "date": row[date_col].strftime("%Y-%m-%d %H:%M:%S"),
                    "Open": float(row[open_col]),
                    "High": float(row[high_col]),
                    "Low": float(row[low_col]),
                    "Close": float(row[close_col]),
                    "Volume": float(row[volume_col]) if volume_col else 0,
                })

            if out:
                return out, os.path.basename(path)
        except Exception:
            continue

    return None, None

@app.get("/api/stock/history")
async def get_stock_history(symbol: str, period: str = "1mo", interval: str = "1d"):
    """Fetch historical data for a given symbol with multi-level fallbacks"""
    clean_symbol = normalize_symbol(symbol)
    symbol_candidates = build_symbol_candidates(symbol)

    # Strategy 0: Prefer local CSV datasets when available to improve reliability and reduce API noise.
    local_data, local_file = _load_local_history_from_csv(clean_symbol)
    if local_data:
        return {"symbol": clean_symbol, "data": local_data, "source": f"local_csv:{local_file}"}
    
    try:
        # Strategy 1: yfinance with multi-candidate symbol resolution.
        for candidate in symbol_candidates or [clean_symbol]:
            try:
                ticker = yf.Ticker(candidate)
                df = ticker.history(period=period, interval=interval)
            except Exception:
                continue

            if not df.empty:
                df = df.reset_index()
                # Standardize date column name
                if 'Date' in df.columns: df.rename(columns={'Date': 'date'}, inplace=True)
                elif 'Datetime' in df.columns: df.rename(columns={'Datetime': 'date'}, inplace=True)

                data = df.to_dict(orient="records")
                # Format dates to string
                for item in data:
                    if isinstance(item['date'], (pd.Timestamp, datetime.datetime)):
                        item['date'] = item['date'].strftime('%Y-%m-%d %H:%M:%S')

                return {"symbol": candidate, "data": data, "source": "yfinance"}

        # Strategy 2: Direct Yahoo API fallback with candidates.
        for candidate in symbol_candidates or [clean_symbol]:
            try:
                url = f"https://query1.finance.yahoo.com/v8/finance/chart/{candidate}?range={period}&interval={interval}"
                headers = {'User-Agent': 'Mozilla/5.0'}
                response = session.get(url, headers=headers, timeout=10)
            except Exception:
                continue

            if response.status_code == 200:
                try:
                    result = response.json().get('chart', {}).get('result', [None])[0]
                except Exception:
                    result = None
                if result:
                    timestamps = result.get('timestamp', [])
                    indicators = result.get('indicators', {}).get('quote', [{}])[0]

                    ohlc_data = []
                    for i in range(len(timestamps)):
                        ohlc_data.append({
                            "date": datetime.datetime.fromtimestamp(timestamps[i]).strftime('%Y-%m-%d %H:%M:%S'),
                            "Open": indicators.get('open', [0]*len(timestamps))[i],
                            "High": indicators.get('high', [0]*len(timestamps))[i],
                            "Low": indicators.get('low', [0]*len(timestamps))[i],
                            "Close": indicators.get('close', [0]*len(timestamps))[i],
                            "Volume": indicators.get('volume', [0]*len(timestamps))[i],
                        })
                    if ohlc_data:
                        return {"symbol": candidate, "data": ohlc_data, "source": "direct_api"}

        # Strategy 3: Local CSV fallback for workspace datasets.
        local_data, local_file = _load_local_history_from_csv(clean_symbol)
        if local_data:
            return {"symbol": clean_symbol, "data": local_data, "source": f"local_csv:{local_file}"}

        raise Exception("No data found from APIs")

    except Exception as e:
        print(f"Error fetching {clean_symbol}: {e}")

        # Try local CSV fallback again to avoid dropping to mock data on transient API exceptions.
        local_data, local_file = _load_local_history_from_csv(clean_symbol)
        if local_data:
            return {"symbol": clean_symbol, "data": local_data, "source": f"local_csv:{local_file}"}

        # Strategy 4: Realistic Mock Data as last resort
        mock_data = []
        base = 100.0 if ".NS" not in clean_symbol else 1500.0
        now = datetime.datetime.now()
        for i in range(30):
            date = (now - datetime.timedelta(days=30-i)).strftime('%Y-%m-%d %H:%M:%S')
            mock_data.append({
                "date": date,
                "Open": base * (1 + (i*0.01)),
                "High": base * (1 + (i*0.012)),
                "Low": base * (1 + (i*0.008)),
                "Close": base * (1 + (i*0.011)),
                "Volume": 1000000 + (i*50000)
            })
        return {"symbol": clean_symbol, "data": mock_data, "source": "mock_fallback"}

def resolve_csv_path(filename: str):
    """Find a CSV file in the backend folder or project root"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    
    possible_paths = [
        os.path.join(backend_dir, filename),
        os.path.join(project_root, filename),
        filename
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    return None

@app.get("/api/simulator/stocks")
async def list_simulator_stocks():
    """List available CSV files for the trading simulator from both backend and root"""
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    backend_dir = os.path.dirname(os.path.abspath(__file__))
    
    stocks = []
    seen = set()
    
    for search_dir in [backend_dir, project_root]:
        try:
            for f in os.listdir(search_dir):
                if f.endswith(".csv") and f not in seen:
                    seen.add(f)
                    stocks.append({
                        "filename": f,
                        "name": f.split('.')[0].replace('_', ' ').replace('Dataset ', '').title(),
                        "symbol": f.split('_')[0].split('.')[0].upper()
                    })
        except:
            continue
            
    return {"stocks": stocks}

@app.get("/api/simulator/metadata/{filename}")
async def get_simulator_metadata(filename: str):
    """Analyze CSV to detect year ranges, interval, and headers"""
    try:
        actual_path = resolve_csv_path(filename)
        if not actual_path:
            raise HTTPException(status_code=404, detail=f"File {filename} not found in backend or root")
            
        df_full = pd.read_csv(actual_path, nrows=100)

        
        # Detect date column
        date_col = next((c for c in df_full.columns if "date" in c.lower() or "time" in c.lower()), None)
        if not date_col:
            # Fallback: check first column
            try:
                pd.to_datetime(df_full.iloc[0, 0], dayfirst=_infer_dayfirst_from_values([df_full.iloc[0, 0]]))
                date_col = df_full.columns[0]
            except:
                raise HTTPException(status_code=400, detail="Cannot find date column")
        
        # Load all dates to get range and unique years
        df_all_dates = pd.read_csv(actual_path, usecols=[df_full.columns.get_loc(date_col)])
        df_all_dates.columns = ['date']
        metadata_dayfirst = _infer_dayfirst_from_values(df_all_dates['date'].tolist())
        df_all_dates['date'] = pd.to_datetime(df_all_dates['date'], dayfirst=metadata_dayfirst, errors='coerce')
        df_all_dates.dropna(subset=['date'], inplace=True)
        
        years = sorted(df_all_dates['date'].dt.year.unique().tolist())
        first_date = df_all_dates['date'].min()
        last_date = df_all_dates['date'].max()
        
        # Detect interval
        interval = "Unknown"
        if len(df_all_dates) > 1:
            diff = df_all_dates['date'].iloc[1] - df_all_dates['date'].iloc[0]
            mins = int(abs(diff.total_seconds()) / 60)
            if mins == 1: interval = "1m"
            elif mins == 5: interval = "5m"
            elif mins >= 1440: interval = "1d"
            else: interval = f"{mins}m"
            
        return {
            "filename": filename,
            "years": [int(y) for y in years],
            "interval": interval,
            "start_date": first_date.strftime("%Y-%m-%d"),
            "end_date": last_date.strftime("%Y-%m-%d")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/simulator/data/{filename}")
async def get_simulator_data(filename: str, start_year: Optional[int] = None, end_year: Optional[int] = None):
    """Load simulator data with filtering and robust column mapping"""
    try:
        actual_path = resolve_csv_path(filename)
        if not actual_path:
            raise HTTPException(status_code=404, detail=f"File {filename} not found")

            
        df = pd.read_csv(actual_path)
        
        # Identify Columns
        cols = list(df.columns)
        clean_cols = [str(c).lower().strip() for c in cols]
        
        date_idx = next((i for i, c in enumerate(clean_cols) if "date" in c or "time" in c), 0)
        date_col = cols[date_idx]
        data_dayfirst = _infer_dayfirst_from_values(df[date_col].tolist())
        df[date_col] = pd.to_datetime(df[date_col], dayfirst=data_dayfirst, errors='coerce')
        df.dropna(subset=[date_col], inplace=True)
        
        # Filter by year
        if start_year: df = df[df[date_col].dt.year >= start_year]
        if end_year: df = df[df[date_col].dt.year <= end_year]
        
        # Map OHLCV
        mapping = {
            "date": date_col,
            "open": next((cols[i] for i, c in enumerate(clean_cols) if c == "open"), None),
            "high": next((cols[i] for i, c in enumerate(clean_cols) if c == "high"), None),
            "low": next((cols[i] for i, c in enumerate(clean_cols) if c == "low"), None),
            "close": next((cols[i] for i, c in enumerate(clean_cols) if c in ["close", "adjclose"]), None),
            "volume": next((cols[i] for i, c in enumerate(clean_cols) if "volume" in c), None),
        }
        
        # Fallback for missing OHLCV (some simple CSVs just have price)
        if not mapping["open"]: mapping["open"] = mapping["close"]
        if not mapping["high"]: mapping["high"] = mapping["close"]
        if not mapping["low"]: mapping["low"] = mapping["close"]
        
        # Construct standardized output
        result_data = []
        for _, row in df.iterrows():
            result_data.append({
                "date": row[mapping["date"]].strftime("%Y-%m-%d %H:%M:%S"),
                "open": float(row[mapping["open"]]),
                "high": float(row[mapping["high"]]),
                "low": float(row[mapping["low"]]),
                "close": float(row[mapping["close"]]),
                "volume": float(row[mapping["volume"]]) if mapping["volume"] else 0
            })
            
        return {"filename": filename, "data": result_data}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/predict/{symbol}")
async def predict_stock(symbol: str):
    """Predict point for Predictor page (matches original expected API)"""
    clean_symbol = normalize_symbol(symbol)
    history = await get_stock_history(clean_symbol, period="6mo", interval="1d")
    data = history.get("data", [])
    
    if not data:
        raise HTTPException(status_code=404, detail="No data for prediction")

    close_series = _extract_close_series(data)
    if len(close_series) < 12:
        raise HTTPException(status_code=400, detail="Not enough data for model inference")

    last_close = close_series[-1]

    # ---- Random Forest binary direction classifier ----
    X_dir, y_dir = _build_direction_dataset(close_series, lags=5)
    if len(y_dir) < 8:
        direction = "UP" if close_series[-1] > close_series[-2] else "DOWN"
        rf_accuracy = 0.5
    else:
        split = max(1, int(len(y_dir) * 0.8))
        X_train, X_test = X_dir[:split], X_dir[split:]
        y_train, y_test = y_dir[:split], y_dir[split:]

        rf = RandomForestClassifier(n_estimators=200, random_state=42)
        rf.fit(X_train, y_train)

        latest_returns = np.diff(np.array(close_series, dtype=float)) / np.array(close_series[:-1], dtype=float)
        latest_features = latest_returns[-5:].reshape(1, -1)
        direction = "UP" if int(rf.predict(latest_features)[0]) == 1 else "DOWN"

        if len(y_test) > 0:
            rf_accuracy = float(accuracy_score(y_test, rf.predict(X_test)))
        else:
            rf_accuracy = float(rf.score(X_train, y_train))

    # ---- Multinomial logistic classifier for BUY/NEUTRAL/SELL ----
    X_multi, y_multi = _build_multiclass_dataset(close_series, lags=5)
    class_map = {0: "SELL", 1: "NEUTRAL", 2: "STRONG_BUY"}

    if len(y_multi) < 12 or len(set(y_multi.tolist())) < 2:
        pct_change = (close_series[-1] - close_series[-6]) / close_series[-6] if len(close_series) > 6 else 0.0
        if pct_change > 0.02:
            category = "STRONG_BUY"
        elif pct_change < -0.02:
            category = "SELL"
        else:
            category = "NEUTRAL"
    else:
        try:
            # Keep constructor args minimal for broad sklearn-version compatibility.
            logreg = LogisticRegression(max_iter=1000)
            logreg.fit(X_multi, y_multi)
            latest_returns = np.diff(np.array(close_series, dtype=float)) / np.array(close_series[:-1], dtype=float)
            latest_features = latest_returns[-5:].reshape(1, -1)
            pred_class = int(logreg.predict(latest_features)[0])
            category = class_map.get(pred_class, "NEUTRAL")
        except Exception:
            # If classification model cannot run in the current environment, avoid hard failure.
            pct_change = (close_series[-1] - close_series[-6]) / close_series[-6] if len(close_series) > 6 else 0.0
            if pct_change > 0.02:
                category = "STRONG_BUY"
            elif pct_change < -0.02:
                category = "SELL"
            else:
                category = "NEUTRAL"

    return {
        "symbol": clean_symbol,
        "last_close": float(last_close),
        "classification": {
            "random_forest": {"direction": direction, "accuracy": float(round(rf_accuracy, 4))}
        },
        "multinomial": {
            "category": category
        }
    }

@app.get("/predict_future/{symbol}")
async def predict_future(symbol: str, days: int = 14):
    """Generate future price predictions for Predictor page"""
    clean_symbol = normalize_symbol(symbol)
    history = await get_stock_history(clean_symbol, period="1y", interval="1d")
    data = history.get("data", [])
    
    if not data:
        raise HTTPException(status_code=404, detail="No data for future prediction")

    close_series = _extract_close_series(data)
    if len(close_series) < 20:
        raise HTTPException(status_code=400, detail="Not enough data for regression forecast")

    last_close = float(close_series[-1])
    lags = 10
    X, y = _build_lagged_features(close_series, lags=lags)
    if len(y) < 10:
        raise HTTPException(status_code=400, detail="Not enough lagged samples for regression")

    # Train both Linear Regression and Gradient Boosting.
    # Keep gradient_boosting in response for frontend compatibility.
    linreg = LinearRegression()
    gbr = GradientBoostingRegressor(random_state=42)
    linreg.fit(X, y)
    gbr.fit(X, y)

    history_window_linear = close_series[-lags:]
    history_window_gbr = close_series[-lags:]
    predictions_linear: List[float] = []
    predictions_gbr: List[float] = []

    for _ in range(days):
        x_lin = np.array(history_window_linear[-lags:], dtype=float).reshape(1, -1)
        next_lin = float(linreg.predict(x_lin)[0])
        predictions_linear.append(next_lin)
        history_window_linear.append(next_lin)

        x_gbr = np.array(history_window_gbr[-lags:], dtype=float).reshape(1, -1)
        next_gbr = float(gbr.predict(x_gbr)[0])
        predictions_gbr.append(next_gbr)
        history_window_gbr.append(next_gbr)

    final_pred = predictions_gbr[-1] if predictions_gbr else last_close
        
    return {
        "symbol": clean_symbol,
        "linear_regression": {
            "predictions": [float(p) for p in predictions_linear],
            "total_change_pct": float(((predictions_linear[-1] - last_close) / last_close) * 100) if predictions_linear else 0.0,
        },
        "gradient_boosting": {
            "predictions": [float(p) for p in predictions_gbr],
            "total_change_pct": float(((final_pred - last_close) / last_close) * 100)
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
