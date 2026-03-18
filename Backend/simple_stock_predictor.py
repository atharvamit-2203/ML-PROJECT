"""
Simple Stock Predictor with Classification and Multinomial Regression
========================================================================
Uses all available datasets with simplified models for price prediction and direction classification.
Includes: Gradient Boosting, Logistic Regression, and Multinomial Regression.

Install dependencies:
    pip install pandas numpy scikit-learn flask flask-cors

Run:
    python simple_stock_predictor.py
"""

import os
import json
import warnings
import numpy as np
import pandas as pd
from pathlib import Path
from flask import Flask, request, jsonify
from flask_cors import CORS
from sklearn.ensemble import GradientBoostingRegressor, RandomForestClassifier
from sklearn.linear_model import LogisticRegression, LinearRegression
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.metrics import accuracy_score, classification_report, mean_absolute_percentage_error, r2_score
from sklearn.model_selection import train_test_split

warnings.filterwarnings("ignore")

# ─────────────────────────────────────────────
# 1. CONFIGURATION
# ─────────────────────────────────────────────

DATA_DIR = Path(".")
PORT = 5001

# All available datasets including the new daily ones
DATASET_MAP = {
    "HDFC": (DATA_DIR / "HDFC.csv", "hdfc"),
    "SPARC.NS": (DATA_DIR / "SPARC.NS_stock_data.csv", "indexed"),
    "TATAMOTORS": (DATA_DIR / "TATAMOTORS_NSE.csv", "standard"),
    "TATACHEM.NS": (DATA_DIR / "TATACHEM.NS_stock_data.csv", "indexed"),
    "TLKM": (DATA_DIR / "Stock_TLKM_2005-2024.csv", "standard"),
    "BSE_FMCG": (DATA_DIR / "SNP BSE FMCG.csv", "fmcg"),
    "ADANIGREEN.NS": (DATA_DIR / "ADANIGREEN.NS_stock_data.csv", "indexed"),
    "HINDUSTAN_ZINC": (DATA_DIR / "Dataset Hindustan Zinc Limited.csv", "indexed_special"),
    "NMDC_STEEL": (DATA_DIR / "NMDC_Steel_Ltd.csv", "indexed_special"),
    # New daily datasets
    "LT": (DATA_DIR / "LT_daily.csv", "daily"),
    "TITAN": (DATA_DIR / "TITAN_daily.csv", "daily"),
    "ULTRACEMCO": (DATA_DIR / "ULTRACEMCO_daily.csv", "daily"),
}

# Simplified feature set
FEATURE_COLS = [
    "open", "high", "low", "close", "volume",
    "returns", "MA5", "MA20", "RSI", "Volatility"
]

# ─────────────────────────────────────────────
# 2. DATA LOADERS
# ─────────────────────────────────────────────

def load_hdfc_csv(path: Path, ticker: str) -> pd.DataFrame:
    """Load HDFC specific format"""
    df = pd.read_csv(path)
    df = df.rename(columns={
        'TIMESTAMP': 'date', 'OPEN': 'open', 'HIGH': 'high',
        'LOW': 'low', 'CLOSE': 'close', 'TOTTRDQTY': 'volume'
    })
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    df['ticker'] = ticker
    return df[['date', 'open', 'high', 'low', 'close', 'volume', 'ticker']].dropna()

def load_standard_csv(path: Path, ticker: str) -> pd.DataFrame:
    """Load standard CSV format with Date/Open/High/Low/Close/Volume columns"""
    df = pd.read_csv(path)
    
    # Handle different date column names
    date_col = 'Date' if 'Date' in df.columns else 'date'
    df['date'] = pd.to_datetime(df[date_col], errors='coerce')
    
    # Standardize column names
    df = df.rename(columns={
        'Open': 'open', 'High': 'high', 'Low': 'low', 
        'Close': 'close', 'Volume': 'volume'
    })
    
    df['ticker'] = ticker
    return df[['date', 'open', 'high', 'low', 'close', 'volume', 'ticker']].dropna()

def load_indexed_special_csv(path: Path, ticker: str) -> pd.DataFrame:
    """Load CSV with date as index and special column format"""
    df = pd.read_csv(path, index_col=0)
    df.index = pd.to_datetime(df.index, errors='coerce')
    df = df.reset_index()
    
    # Handle case where index is named differently
    if df.columns[0] != 'date':
        df = df.rename(columns={df.columns[0]: 'date'})
    
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    
    # Standardize column names
    df = df.rename(columns={
        'Open': 'open', 'High': 'high', 'Low': 'low',
        'Close': 'close', 'Volume': 'volume'
    })
    
    df['ticker'] = ticker
    return df[['date', 'open', 'high', 'low', 'close', 'volume', 'ticker']].dropna()

def load_indexed_csv(path: Path, ticker: str) -> pd.DataFrame:
    """Load CSV with date as index"""
    df = pd.read_csv(path, index_col=0)
    df.index = pd.to_datetime(df.index, errors='coerce')
    df = df.reset_index().rename(columns={'index': 'date'})
    
    # Standardize column names
    df = df.rename(columns={
        'Open': 'open', 'High': 'high', 'Low': 'low',
        'Close': 'close', 'Volume': 'volume'
    })
    
    df['ticker'] = ticker
    return df[['date', 'open', 'high', 'low', 'close', 'volume', 'ticker']].dropna()

def load_daily_csv(path: Path, ticker: str) -> pd.DataFrame:
    """Load daily CSV format (already processed)"""
    df = pd.read_csv(path)
    df['date'] = pd.to_datetime(df['date'], errors='coerce')
    
    # Standardize column names
    df = df.rename(columns={
        'Open': 'open', 'High': 'high', 'Low': 'low',
        'Close': 'close', 'Volume': 'volume'
    })
    
    df['ticker'] = ticker
    return df[['date', 'open', 'high', 'low', 'close', 'volume', 'ticker']].dropna()

def load_fmcg_csv(path: Path, ticker: str) -> pd.DataFrame:
    """Load FMCG dataset format"""
    df = pd.read_csv(path)
    df['date'] = pd.to_datetime(df['Date'], errors='coerce')
    
    df = df.rename(columns={
        'Open': 'open', 'High': 'high', 'Low': 'low',
        'Close': 'close'
    })
    
    df['volume'] = 0  # FMCG dataset doesn't have volume
    df['ticker'] = ticker
    return df[['date', 'open', 'high', 'low', 'close', 'volume', 'ticker']].dropna()

def load_all_datasets() -> dict:
    """Load all available datasets"""
    datasets = {}
    
    for ticker, (path, format_type) in DATASET_MAP.items():
        if not path.exists():
            print(f"  [WARN] {path} not found — skipping {ticker}")
            continue
            
        try:
            if format_type == "daily":
                df = load_daily_csv(path, ticker)
            elif format_type == "hdfc":
                df = load_hdfc_csv(path, ticker)
            elif format_type == "indexed_special":
                df = load_indexed_special_csv(path, ticker)
            elif format_type == "indexed":
                df = load_indexed_csv(path, ticker)
            elif format_type == "fmcg":
                df = load_fmcg_csv(path, ticker)
            else:  # standard
                df = load_standard_csv(path, ticker)
                
            df = df.sort_values('date').reset_index(drop=True)
            datasets[ticker] = df
            print(f"  Loaded {ticker:15s} rows={len(df):6d}  {df['date'].min().date()} → {df['date'].max().date()}")
            
        except Exception as e:
            print(f"  [ERROR] Failed to load {ticker}: {e}")
    
    return datasets

# ─────────────────────────────────────────────
# 3. FEATURE ENGINEERING
# ─────────────────────────────────────────────

def create_features(df: pd.DataFrame) -> pd.DataFrame:
    """Create simplified features for all models"""
    df = df.copy().sort_values('date').reset_index(drop=True)
    
    # Basic returns
    df['returns'] = df['close'].pct_change()
    
    # Moving averages
    df['MA5'] = df['close'].rolling(5).mean()
    df['MA20'] = df['close'].rolling(20).mean()
    
    # RSI (simplified)
    delta = df['close'].diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    rs = gain / loss.replace(0, np.nan)
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Volatility
    df['Volatility'] = df['returns'].rolling(20).std()
    
    # Target variables
    df['next_close'] = df['close'].shift(-1)  # For regression
    df['direction'] = np.where(df['next_close'] > df['close'], 'UP', 'DOWN')  # For classification
    df['price_change_pct'] = (df['next_close'] - df['close']) / df['close'] * 100  # For multinomial
    
    # Create categories for multinomial regression
    conditions = [
        df['price_change_pct'] > 2,      # Strong UP
        (df['price_change_pct'] > 0.5) & (df['price_change_pct'] <= 2),  # Moderate UP
        (df['price_change_pct'] >= -0.5) & (df['price_change_pct'] <= 0.5),  # FLAT
        (df['price_change_pct'] >= -2) & (df['price_change_pct'] < -0.5),  # Moderate DOWN
        df['price_change_pct'] <= -2     # Strong DOWN
    ]
    choices = ['STRONG_UP', 'MODERATE_UP', 'FLAT', 'MODERATE_DOWN', 'STRONG_DOWN']
    df['movement_category'] = np.select(conditions, choices, default='FLAT')
    
    return df.dropna()

# ─────────────────────────────────────────────
# 4. MODEL TRAINING
# ─────────────────────────────────────────────

def train_models(df: pd.DataFrame, ticker: str) -> dict:
    """Train regression, classification, and multinomial models"""
    
    # Prepare features
    feature_cols = [col for col in FEATURE_COLS if col in df.columns]
    X = df[feature_cols].fillna(0)
    
    # Split data
    split = int(len(X) * 0.8)
    X_train, X_test = X.iloc[:split], X.iloc[split:]
    
    # Regression targets
    y_reg_train = df['next_close'].iloc[:split]
    y_reg_test = df['next_close'].iloc[split:]
    
    # Classification targets
    y_cls_train = df['direction'].iloc[:split]
    y_cls_test = df['direction'].iloc[split:]
    
    # Multinomial targets
    y_multi_train = df['movement_category'].iloc[:split]
    y_multi_test = df['movement_category'].iloc[split:]
    
    # Scale features
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)
    
    models = {}
    
    # 1. Regression Models
    print(f"  Training regression models for {ticker}...")
    
    # Gradient Boosting Regressor
    gb_reg = GradientBoostingRegressor(n_estimators=100, max_depth=3, random_state=42)
    gb_reg.fit(X_train_scaled, y_reg_train)
    gb_pred = gb_reg.predict(X_test_scaled)
    gb_mape = mean_absolute_percentage_error(y_reg_test, gb_pred) * 100
    gb_r2 = r2_score(y_reg_test, gb_pred)
    
    # Linear Regression
    lin_reg = LinearRegression()
    lin_reg.fit(X_train_scaled, y_reg_train)
    lin_pred = lin_reg.predict(X_test_scaled)
    lin_mape = mean_absolute_percentage_error(y_reg_test, lin_pred) * 100
    lin_r2 = r2_score(y_reg_test, lin_pred)
    
    models['regression'] = {
        'gradient_boosting': {
            'model': gb_reg,
            'mape': gb_mape,
            'r2': gb_r2,
            'type': 'regression'
        },
        'linear': {
            'model': lin_reg,
            'mape': lin_mape,
            'r2': lin_r2,
            'type': 'regression'
        }
    }
    
    # 2. Classification Models
    print(f"  Training classification models for {ticker}...")
    
    # Random Forest Classifier
    rf_cls = RandomForestClassifier(n_estimators=100, max_depth=5, random_state=42)
    rf_cls.fit(X_train_scaled, y_cls_train)
    rf_pred = rf_cls.predict(X_test_scaled)
    rf_acc = accuracy_score(y_cls_test, rf_pred)
    
    # Logistic Regression
    log_reg = LogisticRegression(random_state=42, max_iter=1000)
    log_reg.fit(X_train_scaled, y_cls_train)
    log_pred = log_reg.predict(X_test_scaled)
    log_acc = accuracy_score(y_cls_test, log_pred)
    
    models['classification'] = {
        'random_forest': {
            'model': rf_cls,
            'accuracy': rf_acc,
            'type': 'classification'
        },
        'logistic': {
            'model': log_reg,
            'accuracy': log_acc,
            'type': 'classification'
        }
    }
    
    # 3. Multinomial Regression
    print(f"  Training multinomial model for {ticker}...")
    
    try:
        multi_reg = LogisticRegression(multi_class='multinomial', random_state=42, max_iter=1000)
    except TypeError:
        # Fallback for older scikit-learn versions
        multi_reg = LogisticRegression(random_state=42, max_iter=1000)
    
    multi_reg.fit(X_train_scaled, y_multi_train)
    multi_pred = multi_reg.predict(X_test_scaled)
    multi_acc = accuracy_score(y_multi_test, multi_pred)
    
    models['multinomial'] = {
        'model': multi_reg,
        'accuracy': multi_acc,
        'type': 'multinomial'
    }
    
    # Store metadata
    last_row = df.iloc[-1]
    
    return {
        'ticker': ticker,
        'models': models,
        'scaler': scaler,
        'feature_cols': feature_cols,
        'last_features': {col: float(last_row[col]) for col in feature_cols},
        'last_close': float(last_row['close']),
        'last_date': str(last_row['date'].date()),
        'categories': ['STRONG_UP', 'MODERATE_UP', 'FLAT', 'MODERATE_DOWN', 'STRONG_DOWN']
    }

# ─────────────────────────────────────────────
# 5. PREDICTION FUNCTIONS
# ─────────────────────────────────────────────

def predict_future_prices(model_info: dict, days_ahead: int = 5, custom_features: dict = None) -> dict:
    """Predict future prices for multiple days ahead"""
    
    feature_cols = model_info['feature_cols']
    last_features = model_info['last_features'].copy()
    
    # Update with custom features if provided
    if custom_features:
        for key, value in custom_features.items():
            if key in feature_cols:
                last_features[key] = float(value)
    
    # Get the regression models
    gb_model = model_info['models']['regression']['gradient_boosting']['model']
    lin_model = model_info['models']['regression']['linear']['model']
    scaler = model_info['scaler']
    
    # Create recursive predictions
    gb_predictions = []
    lin_predictions = []
    
    # Start with current features
    current_features = last_features.copy()
    current_close = current_features['close']
    
    for day in range(1, days_ahead + 1):
        # Create feature vector
        X = np.array([current_features[col] for col in feature_cols]).reshape(1, -1)
        X_scaled = scaler.transform(X)
        
        # Predict next day's close
        gb_next = float(gb_model.predict(X_scaled)[0])
        lin_next = float(lin_model.predict(X_scaled)[0])
        
        gb_predictions.append(gb_next)
        lin_predictions.append(lin_next)
        
        # Update features for next iteration (simplified approach)
        # In a real scenario, you'd recalculate all technical indicators
        current_features['close'] = gb_next  # Use GB prediction as base
        current_features['open'] = gb_next
        current_features['high'] = gb_next * 1.02  # Simple estimation
        current_features['low'] = gb_next * 0.98   # Simple estimation
        
        # Update moving averages (simplified)
        if 'MA5' in current_features:
            current_features['MA5'] = (current_features['MA5'] * 4 + gb_next) / 5
        if 'MA20' in current_features:
            current_features['MA20'] = (current_features['MA20'] * 19 + gb_next) / 20
    
    return {
        'ticker': model_info['ticker'],
        'last_close': model_info['last_close'],
        'last_date': model_info['last_date'],
        'days_ahead': days_ahead,
        'gradient_boosting': {
            'predictions': [round(pred, 2) for pred in gb_predictions],
            'total_change_pct': round((gb_predictions[-1] - model_info['last_close']) / model_info['last_close'] * 100, 2),
            'daily_changes': [round(((gb_predictions[i] - (model_info['last_close'] if i == 0 else gb_predictions[i-1])) / 
                                  (model_info['last_close'] if i == 0 else gb_predictions[i-1])) * 100, 3) 
                            for i in range(len(gb_predictions))]
        },
        'linear_regression': {
            'predictions': [round(pred, 2) for pred in lin_predictions],
            'total_change_pct': round((lin_predictions[-1] - model_info['last_close']) / model_info['last_close'] * 100, 2),
            'daily_changes': [round(((lin_predictions[i] - (model_info['last_close'] if i == 0 else lin_predictions[i-1])) / 
                                  (model_info['last_close'] if i == 0 else lin_predictions[i-1])) * 100, 3) 
                            for i in range(len(lin_predictions))]
        }
    }

def predict_all(model_info: dict, custom_features: dict = None) -> dict:
    """Make predictions using all model types"""
    
    feature_cols = model_info['feature_cols']
    last_features = model_info['last_features'].copy()
    
    # Update with custom features if provided
    if custom_features:
        for key, value in custom_features.items():
            if key in feature_cols:
                last_features[key] = float(value)
    
    # Create feature vector
    X = np.array([last_features[col] for col in feature_cols]).reshape(1, -1)
    X_scaled = model_info['scaler'].transform(X)
    
    results = {
        'ticker': model_info['ticker'],
        'last_close': model_info['last_close'],
        'last_date': model_info['last_date']
    }
    
    # Regression predictions
    gb_model = model_info['models']['regression']['gradient_boosting']['model']
    lin_model = model_info['models']['regression']['linear']['model']
    
    gb_pred = float(gb_model.predict(X_scaled)[0])
    lin_pred = float(lin_model.predict(X_scaled)[0])
    
    results['regression'] = {
        'gradient_boosting': {
            'predicted_price': round(gb_pred, 2),
            'change_pct': round((gb_pred - model_info['last_close']) / model_info['last_close'] * 100, 3),
            'mape': model_info['models']['regression']['gradient_boosting']['mape'],
            'r2': model_info['models']['regression']['gradient_boosting']['r2']
        },
        'linear': {
            'predicted_price': round(lin_pred, 2),
            'change_pct': round((lin_pred - model_info['last_close']) / model_info['last_close'] * 100, 3),
            'mape': model_info['models']['regression']['linear']['mape'],
            'r2': model_info['models']['regression']['linear']['r2']
        }
    }
    
    # Classification predictions
    rf_model = model_info['models']['classification']['random_forest']['model']
    log_model = model_info['models']['classification']['logistic']['model']
    
    rf_pred = rf_model.predict(X_scaled)[0]
    log_pred = log_model.predict(X_scaled)[0]
    
    rf_proba = rf_model.predict_proba(X_scaled)[0]
    log_proba = log_model.predict_proba(X_scaled)[0]
    
    results['classification'] = {
        'random_forest': {
            'direction': rf_pred,
            'accuracy': model_info['models']['classification']['random_forest']['accuracy'],
            'probabilities': {
                'UP': float(rf_proba[1]) if len(rf_proba) == 2 else 0.0,
                'DOWN': float(rf_proba[0]) if len(rf_proba) == 2 else 0.0
            }
        },
        'logistic': {
            'direction': log_pred,
            'accuracy': model_info['models']['classification']['logistic']['accuracy'],
            'probabilities': {
                'UP': float(log_proba[1]) if len(log_proba) == 2 else 0.0,
                'DOWN': float(log_proba[0]) if len(log_proba) == 2 else 0.0
            }
        }
    }
    
    # Multinomial prediction
    multi_model = model_info['models']['multinomial']['model']
    multi_pred = multi_model.predict(X_scaled)[0]
    multi_proba = multi_model.predict_proba(X_scaled)[0]
    
    results['multinomial'] = {
        'category': multi_pred,
        'accuracy': model_info['models']['multinomial']['accuracy'],
        'probabilities': {
            cat: float(prob) for cat, prob in zip(model_info['categories'], multi_proba)
        }
    }
    
    return results

# ─────────────────────────────────────────────
# 6. BOOTSTRAP - LOAD AND TRAIN
# ─────────────────────────────────────────────

print("\n🔄 Loading all datasets...")
RAW_DATA = load_all_datasets()

print("\n⚙️ Processing features and training models...")
TRAINED_MODELS = {}

for ticker, df in RAW_DATA.items():
    print(f"\nProcessing {ticker}...")
    try:
        processed_df = create_features(df)
        if len(processed_df) < 100:  # Skip if too little data
            print(f"  Skipping {ticker} - insufficient data ({len(processed_df)} rows)")
            continue
            
        model_info = train_models(processed_df, ticker)
        TRAINED_MODELS[ticker] = model_info
        
        # Print summary
        reg_info = model_info['models']['regression']['gradient_boosting']
        cls_info = model_info['models']['classification']['random_forest']
        multi_info = model_info['models']['multinomial']
        
        print(f"  ✓ {ticker}: GB MAPE={reg_info['mape']:.2f}%, RF Acc={cls_info['accuracy']:.3f}, Multi Acc={multi_info['accuracy']:.3f}")
        
    except Exception as e:
        print(f"  ✗ Error training {ticker}: {e}")

print(f"\n✅ Successfully trained models for {len(TRAINED_MODELS)} tickers")

# ─────────────────────────────────────────────
# 7. FLASK API
# ─────────────────────────────────────────────

app = Flask(__name__)
CORS(app)

@app.route('/')
def index():
    return jsonify({
        'app': 'Simple Stock Predictor API',
        'version': '2.0',
        'models': 'Regression, Classification, Multinomial, Future Predictions',
        'tickers': list(TRAINED_MODELS.keys()),
        'endpoints': [
            'GET /tickers',
            'GET /predict/<ticker>',
            'GET /predict_future/<ticker>?days=5',
            'POST /predict',
            'GET /models/<ticker>'
        ],
        'features': [
            'Next-day price prediction',
            'Multi-day future forecasting (1-30 days)',
            'Direction classification (UP/DOWN)',
            'Movement categorization (5 categories)',
            'Multiple regression models',
            'Technical indicator integration'
        ]
    })

@app.route('/tickers')
def get_tickers():
    result = {}
    for ticker, info in TRAINED_MODELS.items():
        result[ticker] = {
            'last_close': info['last_close'],
            'last_date': info['last_date'],
            'regression_mape': info['models']['regression']['gradient_boosting']['mape'],
            'classification_accuracy': info['models']['classification']['random_forest']['accuracy'],
            'multinomial_accuracy': info['models']['multinomial']['accuracy']
        }
    return jsonify(result)

@app.route('/predict/<ticker>')
def predict_ticker(ticker):
    ticker = ticker.upper()
    if ticker not in TRAINED_MODELS:
        return jsonify({'error': f'Ticker {ticker} not found'}), 404
    
    result = predict_all(TRAINED_MODELS[ticker])
    return jsonify(result)

@app.route('/predict_future/<ticker>')
def predict_future_ticker(ticker):
    ticker = ticker.upper()
    if ticker not in TRAINED_MODELS:
        return jsonify({'error': f'Ticker {ticker} not found'}), 404
    
    days = int(request.args.get('days', 5))
    if days < 1 or days > 30:
        return jsonify({'error': 'Days must be between 1 and 30'}), 400
    
    result = predict_future_prices(TRAINED_MODELS[ticker], days_ahead=days)
    return jsonify(result)

@app.route('/predict', methods=['POST'])
def predict_with_features():
    body = request.get_json(force=True, silent=True) or {}
    ticker = str(body.get('ticker', '')).upper()
    custom_features = body.get('features', {})
    days_ahead = body.get('days_ahead', 1)
    
    if not ticker:
        return jsonify({'error': 'Ticker is required'}), 400
    if ticker not in TRAINED_MODELS:
        return jsonify({'error': f'Ticker {ticker} not found'}), 404
    
    result = predict_all(TRAINED_MODELS[ticker], custom_features)
    
    # Add future predictions if requested
    if days_ahead > 1:
        future_result = predict_future_prices(TRAINED_MODELS[ticker], days_ahead=days_ahead, custom_features=custom_features)
        result['future_predictions'] = future_result
    
    return jsonify(result)

@app.route('/models/<ticker>')
def get_model_info(ticker):
    ticker = ticker.upper()
    if ticker not in TRAINED_MODELS:
        return jsonify({'error': f'Ticker {ticker} not found'}), 404
    
    info = TRAINED_MODELS[ticker]
    return jsonify({
        'ticker': ticker,
        'feature_cols': info['feature_cols'],
        'last_features': info['last_features'],
        'last_close': info['last_close'],
        'last_date': info['last_date'],
        'categories': info['categories'],
        'model_performance': {
            'gradient_boosting_mape': info['models']['regression']['gradient_boosting']['mape'],
            'linear_mape': info['models']['regression']['linear']['mape'],
            'random_forest_accuracy': info['models']['classification']['random_forest']['accuracy'],
            'logistic_accuracy': info['models']['classification']['logistic']['accuracy'],
            'multinomial_accuracy': info['models']['multinomial']['accuracy']
        }
    })

# ─────────────────────────────────────────────
# 8. CLI MODE
# ─────────────────────────────────────────────

def interactive_cli():
    print("\n" + "="*60)
    print("  SIMPLE STOCK PREDICTOR - INTERACTIVE MODE")
    print("="*60)
    
    tickers = list(TRAINED_MODELS.keys())
    if not tickers:
        print("No models available!")
        return
    
    while True:
        print(f"\nAvailable tickers: {', '.join(tickers)}")
        ticker = input("Enter ticker (or 'quit'): ").strip().upper()
        
        if ticker in ('QUIT', 'Q', 'EXIT'):
            break
        if ticker not in TRAINED_MODELS:
            print(f"❌ Unknown ticker. Choose from: {tickers}")
            continue
        
        print(f"\n{'─'*50}")
        print(f"Ticker: {ticker}")
        info = TRAINED_MODELS[ticker]
        print(f"Last Close: ₹{info['last_close']:,.2f} ({info['last_date']})")
        print(f"{'─'*50}")
        
        # Ask for future prediction days
        try:
            days = int(input("How many days ahead to predict? (1-30, default=5): ") or "5")
            days = max(1, min(30, days))
        except ValueError:
            days = 5
        
        # Get predictions
        result = predict_all(info)
        future_result = predict_future_prices(info, days_ahead=days)
        
        print(f"\n📈 REGRESSION PREDICTIONS:")
        reg = result['regression']
        print(f"  Gradient Boosting: ₹{reg['gradient_boosting']['predicted_price']:,.2f} ({reg['gradient_boosting']['change_pct']:+.2f}%)")
        print(f"  Linear Regression:  ₹{reg['linear']['predicted_price']:,.2f} ({reg['linear']['change_pct']:+.2f}%)")
        
        print(f"\n📊 CLASSIFICATION PREDICTIONS:")
        cls = result['classification']
        print(f"  Random Forest: {cls['random_forest']['direction']} (Acc: {cls['random_forest']['accuracy']:.3f})")
        print(f"  Logistic Reg:   {cls['logistic']['direction']} (Acc: {cls['logistic']['accuracy']:.3f})")
        
        print(f"\n🎯 MULTINOMIAL PREDICTION:")
        multi = result['multinomial']
        print(f"  Category: {multi['category']} (Acc: {multi['accuracy']:.3f})")
        print(f"  Probabilities:")
        for cat, prob in multi['probabilities'].items():
            print(f"    {cat}: {prob:.3f}")
        
        print(f"\n🔮 FUTURE PREDICTIONS ({days} days):")
        print(f"  Last Close: ₹{future_result['last_close']:,.2f}")
        print(f"\n  Gradient Boosting:")
        gb = future_result['gradient_boosting']
        for i, (pred, change) in enumerate(zip(gb['predictions'], gb['daily_changes']), 1):
            print(f"    Day {i}: ₹{pred:,.2f} ({change:+.2f}%)")
        print(f"    Total Change: {gb['total_change_pct']:+.2f}%")
        
        print(f"\n  Linear Regression:")
        lin = future_result['linear_regression']
        for i, (pred, change) in enumerate(zip(lin['predictions'], lin['daily_changes']), 1):
            print(f"    Day {i}: ₹{pred:,.2f} ({change:+.2f}%)")
        print(f"    Total Change: {lin['total_change_pct']:+.2f}%")
        
        print(f"{'─'*50}")

if __name__ == "__main__":
    import sys
    if "--cli" in sys.argv:
        interactive_cli()
    else:
        print(f"🚀 Starting Simple Stock Predictor API on http://0.0.0.0:{PORT}")
        print("   Add --cli flag for interactive mode")
        app.run(host="0.0.0.0", port=PORT, debug=False)
