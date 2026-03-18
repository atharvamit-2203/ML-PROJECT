"""
Stock Market Price Predictor — Python Backend
==============================================
Uses: pandas, numpy, scikit-learn, Flask
Preprocesses 6 datasets, trains Gradient Boosting models,
and exposes a REST API for interactive predictions.

Install dependencies:
    pip install pandas numpy scikit-learn flask flask-cors

Run:
    python stock_predictor_backend.py

API Endpoints:
    GET  /tickers                          → list all available tickers
    GET  /ticker/<ticker>                  → ticker metadata + last features
    POST /predict                          → predict next-day close with custom features
    GET  /history/<ticker>?days=90         → historical OHLCV data
    GET  /signals/<ticker>                 → technical indicator signals
    GET  /train_report                     → model training summary for all tickers
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import RobustScaler
from sklearn.metrics import mean_absolute_percentage_error, mean_squared_error, r2_score

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# 1.  CONFIGURATION
# ─────────────────────────────────────────────

DATA_DIR = Path(".")          # folder where CSV files live — change if needed
PORT     = 5000

# Map: ticker_name -> (csv_path, loader_format)
# Formats: "hdfc" | "sparc" | "tatamotors" | "tatachem" | "tlkm" | "fmcg"
DATASET_MAP = {
    "HDFC":        (DATA_DIR / "HDFC.csv",                     "hdfc"),
    "SPARC.NS":    (DATA_DIR / "SPARC_NS_stock_data.csv",      "indexed"),
    "TATAMOTORS":  (DATA_DIR / "TATAMOTORS_NSE.csv",           "standard"),
    "TATACHEM.NS": (DATA_DIR / "TATACHEM_NS_stock_data.csv",   "indexed"),
    "TLKM":        (DATA_DIR / "Stock_TLKM_2005-2024.csv",     "standard"),
    "BSE_FMCG":    (DATA_DIR / "SNP BSE FMCG.csv",            "fmcg"),
}

FEATURE_COLS = [
    "Open", "High", "Low", "Close", "returns",
    "MA5", "MA20", "MA50",
    "Volatility", "Upper_Band", "Lower_Band",
    "EMA12", "EMA26", "MACD", "MACD_signal",
    "RSI", "HL_pct", "OC_pct",
]

# ─────────────────────────────────────────────
# 2.  DATA LOADERS
# ─────────────────────────────────────────────

def load_hdfc(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df.columns = [c.strip().lower() for c in df.columns]
    df = df.rename(columns={
        "timestamp": "date", "open": "Open", "high": "High",
        "low": "Low", "close": "Close", "tottrdqty": "Volume",
    })
    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    df["ticker"] = "HDFC"
    return df[["date","Open","High","Low","Close","Volume","ticker"]].dropna(subset=["date","Close"])


def load_indexed(path: Path, ticker: str) -> pd.DataFrame:
    """Handles SPARC and TATACHEM — index column is the date."""
    df = pd.read_csv(path, index_col=0)
    df.index = pd.to_datetime(df.index, errors="coerce")
    df = df.reset_index().rename(columns={
        "index": "date", "open": "Open", "high": "High",
        "low": "Low", "close": "Close", "volume": "Volume",
    })
    df["ticker"] = ticker
    return df[["date","Open","High","Low","Close","Volume","ticker"]].dropna(subset=["date","Close"])


def load_standard(path: Path, ticker: str) -> pd.DataFrame:
    """Handles TATAMOTORS and TLKM — standard Date/Open/High/Low/Close/Volume."""
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["Date"], errors="coerce")
    df["ticker"] = ticker
    return df.rename(columns={
        "Open":"Open","High":"High","Low":"Low","Close":"Close","Volume":"Volume"
    })[["date","Open","High","Low","Close","Volume","ticker"]].dropna(subset=["date","Close"])


def load_fmcg(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path)
    df["date"] = pd.to_datetime(df["Date"], dayfirst=True, errors="coerce")
    df["ticker"] = "BSE_FMCG"
    df["Volume"] = np.nan
    return df.rename(columns={
        "Open":"Open","High":"High","Low":"Low","Close":"Close"
    })[["date","Open","High","Low","Close","Volume","ticker"]].dropna(subset=["date","Close"])


def load_all_data() -> dict[str, pd.DataFrame]:
    """Load every dataset and return a dict of raw DataFrames keyed by ticker."""
    raw = {}
    for ticker, (path, fmt) in DATASET_MAP.items():
        if not path.exists():
            print(f"  [WARN] {path} not found — skipping {ticker}")
            continue
        if fmt == "hdfc":
            df = load_hdfc(path)
        elif fmt == "indexed":
            df = load_indexed(path, ticker)
        elif fmt == "standard":
            df = load_standard(path, ticker)
        elif fmt == "fmcg":
            df = load_fmcg(path)
        else:
            raise ValueError(f"Unknown format: {fmt}")
        df = df.sort_values("date").reset_index(drop=True)
        raw[ticker] = df
        print(f"  Loaded {ticker:20s}  rows={len(df)}  "
              f"{df['date'].min().date()} → {df['date'].max().date()}")
    return raw


# ─────────────────────────────────────────────
# 3.  FEATURE ENGINEERING
# ─────────────────────────────────────────────

def engineer_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Add 14 technical indicators + returns + target.
    Target = next day's closing price (shift -1).
    Rows with NaN in critical features are dropped.
    """
    df = df.copy().sort_values("date").reset_index(drop=True)

    # Returns
    df["returns"] = df["Close"].pct_change()

    # Moving averages
    df["MA5"]  = df["Close"].rolling(5).mean()
    df["MA20"] = df["Close"].rolling(20).mean()
    df["MA50"] = df["Close"].rolling(50).mean()

    # Volatility (20-day rolling std of returns)
    df["Volatility"] = df["returns"].rolling(20).std()

    # Bollinger Bands
    std20              = df["Close"].rolling(20).std()
    df["Upper_Band"]   = df["MA20"] + 2 * std20
    df["Lower_Band"]   = df["MA20"] - 2 * std20

    # EMA & MACD
    df["EMA12"]       = df["Close"].ewm(span=12).mean()
    df["EMA26"]       = df["Close"].ewm(span=26).mean()
    df["MACD"]        = df["EMA12"] - df["EMA26"]
    df["MACD_signal"] = df["MACD"].ewm(span=9).mean()

    # RSI (14-period)
    delta = df["Close"].diff()
    gain  = delta.clip(lower=0).rolling(14).mean()
    loss  = (-delta.clip(upper=0)).rolling(14).mean()
    rs    = gain / loss.replace(0, np.nan)
    df["RSI"] = 100 - (100 / (1 + rs))

    # Intraday range ratios
    df["HL_pct"] = (df["High"] - df["Low"])   / df["Close"]
    df["OC_pct"] = (df["Open"] - df["Close"]) / df["Close"]

    # Volume moving average (optional — may be NaN for FMCG)
    df["Volume_MA10"] = df["Volume"].rolling(10).mean()

    # Target: next-day close
    df["Target"] = df["Close"].shift(-1)

    # Drop rows where core features are NaN
    df = df.dropna(subset=["Target", "MA50", "RSI", "MACD"]).reset_index(drop=True)
    return df


# ─────────────────────────────────────────────
# 4.  MODEL TRAINING
# ─────────────────────────────────────────────

def train_model(df: pd.DataFrame, ticker: str) -> dict:
    """
    Train a GradientBoostingRegressor on the processed DataFrame.
    Returns a dict with model, scaler, metrics, and metadata.
    """
    feat_cols = [f for f in FEATURE_COLS if f in df.columns and df[f].notna().sum() > 50]

    X = df[feat_cols].ffill().fillna(0)
    y = df["Target"]

    n     = len(X)
    split = int(n * 0.80)          # 80/20 train-test split
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]

    # Robust scaling handles outliers better than StandardScaler
    scaler   = RobustScaler()
    X_train_s = scaler.fit_transform(X_train)
    X_test_s  = scaler.transform(X_test)

    model = GradientBoostingRegressor(
        n_estimators=200,
        max_depth=4,
        learning_rate=0.05,
        subsample=0.8,
        min_samples_split=5,
        min_samples_leaf=3,
        random_state=42,
    )
    model.fit(X_train_s, y_train)

    # Evaluation
    preds = model.predict(X_test_s)
    mape  = mean_absolute_percentage_error(y_test, preds) * 100
    rmse  = np.sqrt(mean_squared_error(y_test, preds))
    r2    = r2_score(y_test, preds)

    # Feature importances
    fi = dict(zip(feat_cols, model.feature_importances_.round(4)))
    fi_sorted = dict(sorted(fi.items(), key=lambda x: x[1], reverse=True))

    last_row = df.iloc[-1]

    return {
        "ticker":        ticker,
        "model":         model,
        "scaler":        scaler,
        "feat_cols":     feat_cols,
        "metrics": {
            "mape":      round(mape, 4),
            "rmse":      round(rmse, 4),
            "r2":        round(r2, 4),
            "train_rows": split,
            "test_rows":  n - split,
        },
        "feature_importance": fi_sorted,
        "last_close":    float(last_row["Close"]),
        "last_date":     str(last_row["date"].date()),
        "last_features": {fc: float(last_row[fc]) for fc in feat_cols},
        "history":       df[["date","Open","High","Low","Close","Volume","returns","RSI","MACD","MA20"]].copy(),
    }


# ─────────────────────────────────────────────
# 5.  PREDICTION ENGINE
# ─────────────────────────────────────────────

def predict(model_info: dict, custom_features: dict | None = None) -> dict:
    """
    Predict next-day close price.

    Parameters
    ----------
    model_info     : dict returned by train_model()
    custom_features: dict of {feature_name: value} to override last-known values
                     e.g. {"Close": 2700, "RSI": 45}
                     Any features not provided use the last known values.

    Returns
    -------
    dict with predicted price, change %, and confidence interval
    """
    feat_cols = model_info["feat_cols"]
    last_f    = model_info["last_features"]

    # Build feature vector: start with last known, then override with user input
    feature_vector = np.array([last_f[fc] for fc in feat_cols], dtype=float)

    if custom_features:
        for fc_name, value in custom_features.items():
            if fc_name in feat_cols:
                idx = feat_cols.index(fc_name)
                feature_vector[idx] = float(value)

    # Scale and predict
    scaler = model_info["scaler"]
    model  = model_info["model"]
    X_scaled = scaler.transform(feature_vector.reshape(1, -1))
    pred_price = float(model.predict(X_scaled)[0])

    last_close  = model_info["last_close"]
    change_pct  = (pred_price - last_close) / last_close * 100
    mape        = model_info["metrics"]["mape"]

    # Approximate confidence interval using model MAPE
    ci_lower = pred_price * (1 - mape / 100)
    ci_upper = pred_price * (1 + mape / 100)

    return {
        "ticker":         model_info["ticker"],
        "last_close":     round(last_close,  2),
        "last_date":      model_info["last_date"],
        "predicted_close": round(pred_price, 2),
        "change_pct":     round(change_pct,  4),
        "direction":      "UP" if change_pct > 0 else "DOWN",
        "confidence_interval": {
            "lower": round(ci_lower, 2),
            "upper": round(ci_upper, 2),
        },
        "model_mape_pct": mape,
        "features_used":  dict(zip(feat_cols, feature_vector.tolist())),
    }


# ─────────────────────────────────────────────
# 6.  TECHNICAL SIGNALS
# ─────────────────────────────────────────────

def compute_signals(model_info: dict, custom_features: dict | None = None) -> list[dict]:
    """Return a list of buy/sell/neutral signals from technical indicators."""
    feat_cols = model_info["feat_cols"]
    last_f    = model_info["last_features"].copy()

    if custom_features:
        last_f.update({k: v for k, v in custom_features.items() if k in feat_cols})

    def g(name):
        return last_f.get(name, 0)

    rsi      = g("RSI")
    macd     = g("MACD")
    macd_sig = g("MACD_signal")
    close    = g("Close")
    ma20     = g("MA20")
    ma50     = g("MA50")
    upper_bb = g("Upper_Band")
    lower_bb = g("Lower_Band")
    vol      = g("Volatility")

    signals = [
        {
            "indicator": "RSI",
            "value":     round(rsi, 2),
            "signal":    "BUY" if rsi < 35 else ("SELL" if rsi > 65 else "NEUTRAL"),
            "reason":    "Oversold" if rsi < 35 else ("Overbought" if rsi > 65 else "Neutral zone"),
        },
        {
            "indicator": "MACD",
            "value":     round(macd, 4),
            "signal":    "BUY" if macd > macd_sig else ("SELL" if macd < macd_sig else "NEUTRAL"),
            "reason":    "Bullish crossover" if macd > macd_sig else "Bearish crossover",
        },
        {
            "indicator": "MA Trend",
            "value":     round(close, 2),
            "signal":    "BUY" if close > ma20 and close > ma50 else (
                         "SELL" if close < ma20 and close < ma50 else "NEUTRAL"),
            "reason":    f"Price {'above' if close > ma20 else 'below'} MA20 & {'above' if close > ma50 else 'below'} MA50",
        },
        {
            "indicator": "Bollinger Bands",
            "value":     round(close, 2),
            "signal":    "SELL" if close > upper_bb else ("BUY" if close < lower_bb else "NEUTRAL"),
            "reason":    "Near upper band — overbought" if close > upper_bb else (
                         "Near lower band — oversold" if close < lower_bb else "Within normal range"),
        },
        {
            "indicator": "Volatility",
            "value":     round(vol * 100, 4),
            "signal":    "BUY" if vol < 0.012 else ("SELL" if vol > 0.025 else "NEUTRAL"),
            "reason":    "Low volatility — stable trend" if vol < 0.012 else (
                         "High volatility — risky entry" if vol > 0.025 else "Moderate volatility"),
        },
    ]

    bull = sum(1 for s in signals if s["signal"] == "BUY")
    bear = sum(1 for s in signals if s["signal"] == "SELL")
    overall = "BULLISH" if bull > bear else ("BEARISH" if bear > bull else "NEUTRAL")

    return {
        "signals":        signals,
        "summary":        overall,
        "bullish_count":  bull,
        "bearish_count":  bear,
        "neutral_count":  len(signals) - bull - bear,
    }


# ─────────────────────────────────────────────
# 7.  BOOTSTRAP — LOAD & TRAIN EVERYTHING
# ─────────────────────────────────────────────

print("\n🔄  Loading datasets...")
RAW_DATA      : dict[str, pd.DataFrame] = load_all_data()

print("\n⚙️   Engineering features...")
PROCESSED_DATA: dict[str, pd.DataFrame] = {}
for t, df in RAW_DATA.items():
    PROCESSED_DATA[t] = engineer_features(df)
    print(f"  {t:20s}  processed rows={len(PROCESSED_DATA[t])}")

print("\n🤖  Training models...")
MODELS: dict[str, dict] = {}
for t, df in PROCESSED_DATA.items():
    info = train_model(df, t)
    MODELS[t] = info
    m = info["metrics"]
    print(f"  {t:20s}  MAPE={m['mape']:.2f}%  RMSE={m['rmse']:.2f}  R²={m['r2']:.4f}")

print("\n✅  All models ready.\n")


# ─────────────────────────────────────────────
# 8.  FLASK REST API
# ─────────────────────────────────────────────

app = Flask(__name__)
CORS(app)   # allow frontend at any origin


@app.route("/", methods=["GET"])
def index():
    return jsonify({
        "app":      "Stock Price Predictor API",
        "version":  "1.0",
        "tickers":  list(MODELS.keys()),
        "endpoints": [
            "GET  /tickers",
            "GET  /ticker/<ticker>",
            "POST /predict",
            "GET  /history/<ticker>?days=90",
            "GET  /signals/<ticker>",
            "GET  /train_report",
        ],
    })


@app.route("/tickers", methods=["GET"])
def get_tickers():
    """List all available tickers with quick summary."""
    result = {}
    for t, info in MODELS.items():
        result[t] = {
            "last_close": info["last_close"],
            "last_date":  info["last_date"],
            "mape_pct":   info["metrics"]["mape"],
            "r2":         info["metrics"]["r2"],
        }
    return jsonify(result)


@app.route("/ticker/<ticker>", methods=["GET"])
def get_ticker(ticker: str):
    """Full metadata for a single ticker including last known feature values."""
    ticker = ticker.upper()
    if ticker not in MODELS:
        return jsonify({"error": f"Ticker '{ticker}' not found. Available: {list(MODELS.keys())}"}), 404

    info = MODELS[ticker]
    return jsonify({
        "ticker":             ticker,
        "last_close":         info["last_close"],
        "last_date":          info["last_date"],
        "metrics":            info["metrics"],
        "feature_importance": info["feature_importance"],
        "last_features":      info["last_features"],
        "available_features": info["feat_cols"],
    })


@app.route("/predict", methods=["POST"])
def post_predict():
    """
    Predict next-day close price.

    Body (JSON):
    {
        "ticker": "HDFC",                 ← required
        "features": {                     ← optional overrides
            "Close":      2700.0,
            "RSI":        45.0,
            "MACD":       8.5,
            "Volatility": 0.015
        }
    }

    If 'features' is omitted, prediction uses last known values.
    """
    body = request.get_json(force=True, silent=True) or {}
    ticker = str(body.get("ticker", "")).upper()

    if not ticker:
        return jsonify({"error": "Field 'ticker' is required."}), 400
    if ticker not in MODELS:
        return jsonify({"error": f"Ticker '{ticker}' not found. Available: {list(MODELS.keys())}"}), 404

    custom = body.get("features", None)
    result = predict(MODELS[ticker], custom_features=custom)
    return jsonify(result)


@app.route("/history/<ticker>", methods=["GET"])
def get_history(ticker: str):
    """
    Return historical OHLCV + indicator data.

    Query params:
        days  (int, default 90)  — how many trailing rows to return
    """
    ticker = ticker.upper()
    if ticker not in MODELS:
        return jsonify({"error": f"Ticker '{ticker}' not found."}), 404

    days = int(request.args.get("days", 90))
    df   = MODELS[ticker]["history"].tail(days).copy()
    df["date"] = df["date"].astype(str)
    df = df.fillna("null")    # JSON-safe
    records = df.to_dict(orient="records")
    return jsonify({"ticker": ticker, "days": len(records), "data": records})


@app.route("/signals/<ticker>", methods=["GET"])
def get_signals(ticker: str):
    """
    Technical indicator signals for a ticker.

    Optionally pass feature overrides as query params:
        /signals/HDFC?Close=2700&RSI=45
    """
    ticker = ticker.upper()
    if ticker not in MODELS:
        return jsonify({"error": f"Ticker '{ticker}' not found."}), 404

    # Parse query param overrides
    allowed = set(MODELS[ticker]["feat_cols"])
    custom  = {}
    for k, v in request.args.items():
        if k in allowed:
            try:
                custom[k] = float(v)
            except ValueError:
                pass

    result = compute_signals(MODELS[ticker], custom_features=custom or None)
    result["ticker"] = ticker
    result["last_date"] = MODELS[ticker]["last_date"]
    return jsonify(result)


@app.route("/train_report", methods=["GET"])
def train_report():
    """Full training metrics and feature importances for every model."""
    report = {}
    for t, info in MODELS.items():
        report[t] = {
            "metrics":            info["metrics"],
            "feature_importance": info["feature_importance"],
            "last_close":         info["last_close"],
            "last_date":          info["last_date"],
        }
    return jsonify(report)


# ─────────────────────────────────────────────
# 9.  COMMAND-LINE INTERACTIVE MODE
#     Run: python stock_predictor_backend.py --cli
# ─────────────────────────────────────────────

def interactive_cli():
    """Standalone CLI mode — no Flask required."""
    print("\n" + "="*60)
    print("  STOCK PREDICTOR — INTERACTIVE CLI")
    print("="*60)

    tickers = list(MODELS.keys())
    while True:
        print(f"\nAvailable tickers: {', '.join(tickers)}")
        ticker = input("Enter ticker (or 'quit'): ").strip().upper()

        if ticker in ("QUIT", "Q", "EXIT"):
            print("Goodbye.")
            break
        if ticker not in MODELS:
            print(f"  ❌ Unknown ticker. Choose from: {tickers}")
            continue

        info = MODELS[ticker]
        print(f"\n{'─'*50}")
        print(f"  Ticker    : {ticker}")
        print(f"  Last close: ₹{info['last_close']:,.2f}  ({info['last_date']})")
        print(f"  Model R²  : {info['metrics']['r2']:.4f}   MAPE: {info['metrics']['mape']:.2f}%")
        print(f"{'─'*50}")

        # Show current features
        print("\nCurrent feature values (press Enter to keep, or type a new value):")
        custom = {}
        editable = ["Close", "Open", "High", "Low", "RSI", "MACD", "Volatility", "MA5", "MA20"]
        for feat in editable:
            if feat not in info["last_features"]:
                continue
            cur_val = info["last_features"][feat]
            disp    = f"{cur_val:.4f}" if abs(cur_val) < 1 else f"{cur_val:,.2f}"
            user_in = input(f"  {feat:<14} [{disp}]: ").strip()
            if user_in:
                try:
                    custom[feat] = float(user_in)
                except ValueError:
                    print(f"    ⚠ Invalid value — using {disp}")

        # Predict
        result  = predict(info, custom_features=custom or None)
        signals = compute_signals(info, custom_features=custom or None)

        print(f"\n{'═'*50}")
        print(f"  PREDICTED NEXT-DAY CLOSE : ₹{result['predicted_close']:,.2f}")
        print(f"  Last close               : ₹{result['last_close']:,.2f}")
        chg = result["change_pct"]
        arrow = "▲" if chg >= 0 else "▼"
        print(f"  Change                   : {arrow} {chg:+.3f}%")
        ci = result["confidence_interval"]
        print(f"  Confidence interval      : ₹{ci['lower']:,.2f} — ₹{ci['upper']:,.2f}")
        print(f"{'─'*50}")
        print(f"  Direction : {result['direction']}")
        print(f"  Signals   : {signals['summary']}  "
              f"(↑{signals['bullish_count']} ↓{signals['bearish_count']} ={signals['neutral_count']})")
        print(f"\n  Technical Signals:")
        for s in signals["signals"]:
            mark = "✅" if s["signal"] == "BUY" else ("❌" if s["signal"] == "SELL" else "➖")
            print(f"    {mark} {s['indicator']:<18} {s['signal']:<8}  {s['reason']}")
        print(f"{'═'*50}")

        again = input("\n  Predict another scenario for this ticker? [y/N]: ").strip().lower()
        if again != "y":
            continue


# ─────────────────────────────────────────────
# 10.  ENTRY POINT
# ─────────────────────────────────────────────

if __name__ == "__main__":
    import sys

    if "--cli" in sys.argv:
        interactive_cli()
    else:
        print(f"🚀  Starting Flask API on http://0.0.0.0:{PORT}")
        print("    Add --cli flag to use the interactive command-line mode instead.\n")
        app.run(host="0.0.0.0", port=PORT, debug=False)