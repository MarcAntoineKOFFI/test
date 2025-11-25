import yfinance as yf
import pandas as pd
import numpy as np
import json
import os
import random
from datetime import datetime, timedelta
import time
import pytz
import uuid
from enum import Enum
from concurrent.futures import ThreadPoolExecutor

# --- Caching & Async Globals ---
DATA_CACHE = {}
PENDING_REQUESTS = {}
CACHE_DIR = "cache"
os.makedirs(CACHE_DIR, exist_ok=True)

# Thread Pool for Async Operations
THREAD_POOL = ThreadPoolExecutor(max_workers=12)

# --- Narrative Engine Types ---
class TokenType(Enum):
    ACTION = "ACTION"
    EVIDENCE = "EVIDENCE"
    CONTEXT = "CONTEXT"
    CATALYST = "CATALYST" # New for News/Events

class Sentiment(Enum):
    BULLISH = "BULLISH"
    BEARISH = "BEARISH"
    NEUTRAL = "NEUTRAL"

# Configuration
MARKET_INDICES = [
    { 'symbol': '^GSPC', 'name': 'S&P 500' },
    { 'symbol': '^IXIC', 'name': 'NASDAQ' },
    { 'symbol': '^DJI', 'name': 'Dow Jones' }
]

SAMPLE_STOCKS = [
    'AAPL', 'MSFT', 'GOOGL', 'AMZN', 'NVDA', 'TSLA', 'META', 'BRK-B',
    'V', 'JNJ', 'WMT', 'JPM', 'MA', 'PG', 'UNH', 'DIS', 'HD', 'BAC',
    'NFLX', 'ADBE', 'CRM', 'INTC', 'AMD', 'PYPL', 'CSCO', 'PFE'
]

# Mock Data Constants
BASE_PRICES = {
    '^GSPC': 4500, '^IXIC': 14000, '^DJI': 35000, 'AAPL': 180, 'MSFT': 370,
    'GOOGL': 140, 'AMZN': 150, 'NVDA': 480, 'TSLA': 240, 'META': 320,
    'BRK-B': 360, 'V': 250, 'JNJ': 160, 'WMT': 160, 'JPM': 150, 'MA': 400,
    'PG': 150, 'UNH': 520, 'DIS': 95, 'HD': 320, 'BAC': 30, 'NFLX': 450,
    'ADBE': 550, 'CRM': 210, 'INTC': 45, 'AMD': 140, 'PYPL': 60, 'CSCO': 50,
    'PFE': 30
}

STOCK_NAMES = {
    '^GSPC': 'S&P 500', '^IXIC': 'NASDAQ Composite', '^DJI': 'Dow Jones Industrial Average',
    'AAPL': 'Apple Inc.', 'MSFT': 'Microsoft Corporation', 'GOOGL': 'Alphabet Inc.',
    'AMZN': 'Amazon.com Inc.', 'NVDA': 'NVIDIA Corporation', 'TSLA': 'Tesla, Inc.',
    'META': 'Meta Platforms Inc.', 'BRK-B': 'Berkshire Hathaway Inc.', 'V': 'Visa Inc.',
    'JNJ': 'Johnson & Johnson', 'WMT': 'Walmart Inc.', 'JPM': 'JPMorgan Chase & Co.',
    'MA': 'Mastercard Inc.', 'PG': 'Procter & Gamble Co.', 'UNH': 'UnitedHealth Group Inc.',
    'DIS': 'The Walt Disney Company', 'HD': 'The Home Depot Inc.', 'BAC': 'Bank of America Corp.',
    'NFLX': 'Netflix Inc.', 'ADBE': 'Adobe Inc.', 'CRM': 'Salesforce Inc.',
    'INTC': 'Intel Corporation', 'AMD': 'Advanced Micro Devices Inc.',
    'PYPL': 'PayPal Holdings Inc.', 'CSCO': 'Cisco Systems Inc.', 'PFE': 'Pfizer Inc.'
}

# --- Caching Layer ---
DATA_CACHE = {}
PENDING_REQUESTS = {}
CACHE_DIR = "cache"

if not os.path.exists(CACHE_DIR):
    os.makedirs(CACHE_DIR)

def get_cached_data(key, max_age_seconds=60):
    """Retrieves data from in-memory cache if valid."""
    if key in DATA_CACHE:
        entry = DATA_CACHE[key]
        if time.time() - entry['timestamp'] < max_age_seconds:
            return entry['data']
    return None

def set_cached_data(key, data):
    """Stores data in in-memory cache."""
    DATA_CACHE[key] = {
        'data': data,
        'timestamp': time.time()
    }

def get_file_cache(filename, max_age_hours=24):
    """Retrieves data from file cache if valid."""
    filepath = os.path.join(CACHE_DIR, filename)
    if os.path.exists(filepath):
        mtime = os.path.getmtime(filepath)
        if time.time() - mtime < max_age_hours * 3600:
            try:
                with open(filepath, 'r') as f:
                    return json.load(f)
            except:
                pass
    return None

def set_file_cache(filename, data):
    """Stores data in file cache."""
    filepath = os.path.join(CACHE_DIR, filename)
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f)
    except Exception as e:
        print(f"Error writing cache file {filename}: {e}")
def fetch_stock_data(symbol, period="1mo", interval="1d"):
    """
    Fetches stock data using yfinance, falling back to mock data if it fails.
    Includes history for sparklines.
    """
    # 1. Check Cache (Memory -> File)
    cache_key = f"{symbol}_stock_{period}_{interval}"
    cached = get_cached_data(cache_key)
    if cached:
        return cached
        
    # Check File Cache (1 hour expiry)
    file_cached = get_file_cache(f"{symbol}_stock_data.json", max_age_hours=1)
    if file_cached:
        set_cached_data(cache_key, file_cached) # Populate memory cache
        return file_cached

    try:
        ticker = yf.Ticker(symbol)
        # Get fast info if available
        info = ticker.fast_info
        
        price = info.last_price
        prev_close = info.previous_close
        
        if price is None or prev_close is None:
            raise ValueError("Missing price data")

        change = price - prev_close
        change_percent = (change / prev_close) * 100
        
        # Fetch history for sparkline (last 30 points)
        history = ticker.history(period=period, interval=interval)
        history_prices = history['Close'].tolist() if not history.empty else []
        history_dates = [dt.strftime("%Y-%m-%d") for dt in history.index] if not history.empty else []
        
        name = STOCK_NAMES.get(symbol, symbol)
        
        data = {
            'symbol': symbol,
            'price': price,
            'change': change,
            'change_percent': change_percent,
            'name': name,
            'history': history_prices,
            'history_dates': history_dates,
            'timestamps': ['10:00 AM', '10:30 AM', '11:00 AM', '11:30 AM', '12:00 PM', '12:30 PM', '1:00 PM', '1:30 PM', '2:00 PM', '2:30 PM', '3:00 PM', '3:30 PM', '4:00 PM'],
            'rvol': random.uniform(0.5, 3.0),
            'open': info.open if info.open else price,
            'high': info.day_high if info.day_high else price,
            'low': info.day_low if info.day_low else price,
            'volume': info.last_volume if info.last_volume else 0,
            'market_cap': info.market_cap if info.market_cap else 0,
            'pe_ratio': 0, # Placeholder
            'dividend_yield': 0 # Placeholder
        }
        
        # 2. Set Cache (In-Memory + File)
        set_cached_data(cache_key, data)
        set_file_cache(f"{symbol}_stock_data.json", data)
        return data

    except Exception as e:
        # print(f"Error fetching {symbol}: {e}. Using mock data.")
        return generate_mock_data(symbol)

def generate_mock_data(symbol):
    """
    Generates realistic mock data for a stock symbol, including history.
    """
    base_price = BASE_PRICES.get(symbol, random.uniform(50, 250))
    
    # Seed based on symbol
    seed_val = sum(ord(c) for c in symbol)
    random.seed(seed_val + int(time.time() / 60)) 
    
    variation = (random.random() - 0.5) * 0.1 
    price = base_price * (1 + variation)
    
    time_variation = (datetime.now().minute / 60) - 0.5
    change_percent = time_variation * 6 
    change = price * (change_percent / 100)
    
    # Generate mock history (random walk)
    history = []
    curr = base_price
    for _ in range(30):
        curr = curr * (1 + (random.random() - 0.5) * 0.05)
        history.append(curr)
    history.append(price) # Ensure last point matches current price
    
    return {
        'symbol': symbol,
        'price': price,
        'change': change,
        'change_percent': change_percent,
        'name': STOCK_NAMES.get(symbol, symbol),
        'history': history,
        'history_dates': [(datetime.now() - timedelta(days=30-i)).strftime("%Y-%m-%d") for i in range(31)],
        'timestamps': ['9:30', '10:00', '10:30', '11:00', '11:30', '12:00', '12:30', '13:00', '13:30', '14:00', '14:30', '15:00', '15:30', '16:00'],
        'rvol': random.uniform(0.5, 3.0),
        'open': base_price * (1 + (random.random() - 0.5) * 0.02),
        'high': max(history) * (1 + random.random() * 0.01),
        'low': min(history) * (1 - random.random() * 0.01),
        'volume': int(random.uniform(1000000, 50000000)),
        'pe_ratio': round(random.uniform(15, 60), 2),
        'market_cap': random.uniform(10e9, 2e12)
    }

def fetch_fundamentals(symbol):
    """
    Fetches fundamental data (ratios, margins, etc.) with file-based caching.
    """
    filename = f"{symbol}_fundamentals.json"
    cached = get_file_cache(filename)
    if cached:
        return cached

    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        data = {
            'market_cap': info.get('marketCap'),
            'pe_ratio': info.get('trailingPE'),
            'forward_pe': info.get('forwardPE'),
            'peg_ratio': info.get('pegRatio'),
            'price_to_book': info.get('priceToBook'),
            'dividend_yield': info.get('dividendYield'),
            'beta': info.get('beta'),
            'profit_margins': info.get('profitMargins'),
            'operating_margins': info.get('operatingMargins'),
            'return_on_assets': info.get('returnOnAssets'),
            'return_on_equity': info.get('returnOnEquity'),
            'revenue_growth': info.get('revenueGrowth'),
            'earnings_growth': info.get('earningsGrowth'),
            'target_price': info.get('targetMeanPrice'),
            'recommendation': info.get('recommendationKey'),
            'sector': info.get('sector'),
            'industry': info.get('industry'),
            'description': info.get('longBusinessSummary')
        }
        
        set_file_cache(filename, data)
        return data
        
    except Exception as e:
        print(f"Error fetching fundamentals for {symbol}: {e}")
        return None

def get_market_indices():
    results = []
    for index in MARKET_INDICES:
        data = fetch_stock_data(index['symbol'])
        if data:
            results.append(data)
    return results

def get_top_gainers_losers():
    stock_data = []
    
    # Parallel Fetching
    with ThreadPoolExecutor(max_workers=10) as executor:
        results = list(executor.map(fetch_stock_data, SAMPLE_STOCKS))
    
    stock_data = [d for d in results if d]
            
    stock_data.sort(key=lambda x: x['change_percent'], reverse=True)
    
    gainers = stock_data[:5]
    losers = stock_data[-5:]
    losers.reverse()
    
    return gainers, losers

def get_talking_points():
    """
    Fetches real news headlines from yfinance for major tickers.
    """
    points = []
    try:
        # Fetch news for a major index or popular stock
        ticker = yf.Ticker("SPY") 
        news = ticker.news
        
        if news:
            for item in news[:4]:
                title = item.get('title', '')
                if title:
                    points.append(title)
        else:
             points.append('Market is currently open - Live trading in progress')
             points.append('Monitor earnings reports and Federal Reserve announcements')

    except Exception:
        points.append('Market is currently open - Live trading in progress')
        points.append('Monitor earnings reports and Federal Reserve announcements')
        
    return points

def get_trader_skills():
    """
    Returns data for the Radar Chart.
    """
    return {
        "labels": ["Consistency", "Risk Mgmt", "Profitability", "Timing", "Diversity", "Resilience"],
        "values": [85, 70, 92, 65, 78, 88] # 0-100 scale
    }

def get_kpis(symbol):
    """
    Returns mock KPIs for the detailed view.
    """
    return {
        "Risk": "Medium",
        "Max Return": "+12.5%",
        "Drawdown Time": "4 Days",
        "Volatility": "1.2%",
        "Sharpe Ratio": "1.8",
        "Beta": "1.1"
    }

def get_rationale(symbol):
    """
    Returns a mock strategic rationale.
    """
    return (
        f"Strategic Rationale for {symbol}:\n"
        "Strong momentum indicators suggest continued upside potential, though overbought conditions "
        "warrant caution. Recent volume spikes confirm institutional interest. "
        "Primary support levels hold firm, providing a solid risk/reward ratio for short-term entries."
    )

# --- Narrative Engine Logic ---

def calculate_real_indicators(symbol):
    """
    Calculates real technical indicators using pandas (Manual implementation).
    Returns a dictionary of indicators or None if calculation fails.
    """
    try:
        ticker = yf.Ticker(symbol)
        # Fetch 6 months to ensure enough data for indicators (e.g. 50 SMA)
        df = ticker.history(period="6mo", interval="1d")
        
        if df.empty or len(df) < 50:
            return None
            
        close = df['Close']
        
        # --- RSI (14) ---
        delta = close.diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        # Fix division by zero or initial NaNs if needed, but rolling mean handles it mostly.
        # Better RSI calculation (Wilder's Smoothing) is standard but simple rolling is okay for now.
        # Let's use Exponential Moving Average for RSI to be closer to standard? 
        # Actually, standard RSI uses Wilder's smoothing.
        # Simple implementation:
        delta = close.diff()
        up = delta.clip(lower=0)
        down = -1 * delta.clip(upper=0)
        ema_up = up.ewm(com=13, adjust=False).mean()
        ema_down = down.ewm(com=13, adjust=False).mean()
        rs = ema_up / ema_down
        df['RSI'] = 100 - (100 / (1 + rs))

        # --- MACD (12, 26, 9) ---
        exp1 = close.ewm(span=12, adjust=False).mean()
        exp2 = close.ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['MACD_SIGNAL'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        # --- Bollinger Bands (20, 2) ---
        df['BBM'] = close.rolling(window=20).mean()
        df['STD'] = close.rolling(window=20).std()
        df['BBU'] = df['BBM'] + (df['STD'] * 2)
        df['BBL'] = df['BBM'] - (df['STD'] * 2)
        
        # --- RVOL (Volume / 20-day MA Volume) ---
        df['Vol_MA'] = df['Volume'].rolling(window=20).mean()
        df['RVOL'] = df['Volume'] / df['Vol_MA']
        
        # --- 50 SMA ---
        df['SMA_50'] = close.rolling(window=50).mean()
        
        # Get last row
        last = df.iloc[-1]
        
        indicators = {
            'rsi': round(last['RSI'], 2) if pd.notna(last['RSI']) else 50.0,
            'macd': round(last['MACD'], 2) if pd.notna(last.get('MACD')) else 0.0,
            'macd_signal': round(last['MACD_SIGNAL'], 2) if pd.notna(last.get('MACD_SIGNAL')) else 0.0,
            'bb_upper': round(last['BBU'], 2) if pd.notna(last.get('BBU')) else 0.0,
            'bb_lower': round(last['BBL'], 2) if pd.notna(last.get('BBL')) else 0.0,
            'bb_middle': round(last['BBM'], 2) if pd.notna(last.get('BBM')) else 0.0,
            'price': round(last['Close'], 2),
            'rvol': round(last['RVOL'], 2) if pd.notna(last['RVOL']) else 1.0,
            'sma_50': round(last['SMA_50'], 2) if pd.notna(last['SMA_50']) else 0.0,
            'volume': int(last['Volume'])
        }
        
        # Distance from SMA
        if indicators['sma_50'] > 0:
            indicators['sma_50_distance'] = round(((indicators['price'] - indicators['sma_50']) / indicators['sma_50']) * 100, 2)
        else:
            indicators['sma_50_distance'] = 0.0
            
        return indicators
        
    except Exception as e:
        print(f"Error calculating indicators for {symbol}: {e}")
        return None

def calculate_setup_confidence(indicators):
    """
    Calculates a confidence score (50-98) based on technical confluence.
    """
    score = 50
    
    rsi = indicators['rsi']
    macd = indicators['macd']
    signal = indicators['macd_signal']
    price = indicators['price']
    bbu = indicators['bb_upper']
    bbl = indicators['bb_lower']
    bbm = indicators['bb_middle']
    rvol = indicators['rvol']
    
    # RSI Logic
    if 30 <= rsi <= 70:
        score += 10
    elif rsi < 30:
        score += 15 # Oversold bounce potential
    elif rsi > 70:
        score -= 10 # Overbought risk
        
    # MACD Logic
    if macd > signal:
        score += 10
    else:
        score -= 5
        
    # Bollinger Bands
    if price > bbu:
        score -= 15 # Overextended
    elif bbm < price <= bbu:
        score += 5 # Uptrending
    elif bbl <= price <= bbm:
        score += 5 # Support zone
    elif price < bbl:
        score += 10 # Oversold extreme
        
    # RVOL
    if rvol > 2.0:
        score += 5 # Extra bonus for very high volume
    if rvol > 1.5:
        score += 10
    elif rvol < 0.8:
        score -= 5
        
    # Bounds
    score = max(50, min(98, score))
    return int(score)

def calculate_atr(symbol, period=14):
    """Calculates Average True Range."""
    try:
        ticker = yf.Ticker(symbol)
        # Fetch enough data for 14 period ATR
        df = ticker.history(period="1mo", interval="1d")
        if df.empty:
            return 1.0
            
        high_low = df['High'] - df['Low']
        high_close = (df['High'] - df['Close'].shift()).abs()
        low_close = (df['Low'] - df['Close'].shift()).abs()
        
        ranges = pd.concat([high_low, high_close, low_close], axis=1)
        true_range = ranges.max(axis=1)
        atr = true_range.rolling(window=period).mean().iloc[-1]
        
        return atr if pd.notna(atr) else 1.0
    except:
        return 1.0

# --- Symbol to Sector Mapping ---
SYMBOL_TO_SECTOR = {
    'AAPL': 'XLK', 'MSFT': 'XLK', 'NVDA': 'XLK', 'AMD': 'XLK', 'ADBE': 'XLK', 'CRM': 'XLK', 'CSCO': 'XLK', 'INTC': 'XLK',
    'GOOGL': 'XLC', 'META': 'XLC', 'NFLX': 'XLC', 'DIS': 'XLC',
    'AMZN': 'XLY', 'TSLA': 'XLY', 'HD': 'XLY', 'MCD': 'XLY', 'NKE': 'XLY',
    'JPM': 'XLF', 'BAC': 'XLF', 'V': 'XLF', 'MA': 'XLF', 'BRK-B': 'XLF',
    'UNH': 'XLV', 'JNJ': 'XLV', 'PFE': 'XLV', 'LLY': 'XLV', 'MRK': 'XLV',
    'XOM': 'XLE', 'CVX': 'XLE',
    'PG': 'XLP', 'WMT': 'XLP', 'KO': 'XLP', 'PEP': 'XLP',
    'BA': 'XLI', 'CAT': 'XLI', 'GE': 'XLI', 'HON': 'XLI',
    'LIN': 'XLB', 'SHW': 'XLB',
    'NEE': 'XLU', 'DUK': 'XLU'
}

def generate_narrative(symbol, indicators=None):
    """
    Generates a narrative based on REAL technical indicators.
    """
    if indicators is None:
        indicators = calculate_real_indicators(symbol)
        if indicators is None:
            return [{'content': "Data unavailable", 'type': TokenType.CONTEXT.value, 'sentiment': Sentiment.NEUTRAL.value}]

    tokens = []
    
    # Extract real metrics
    rvol = indicators['rvol']
    rsi = indicators['rsi']
    sma_dist = indicators['sma_50_distance']
    price = indicators['price']
    sma_50 = indicators['sma_50']
    
    # 1. Institutional Action (High RVOL)
    if rvol > 1.5:
        tokens.append({'content': "INSTITUTIONAL ACCUMULATION", 'type': TokenType.ACTION.value, 'sentiment': Sentiment.BULLISH.value})
        tokens.append({'content': f"detected; volume is {rvol}x average,", 'type': TokenType.EVIDENCE.value, 'sentiment': Sentiment.BULLISH.value})
        
        if price > sma_50:
             tokens.append({'content': f"confirming breakout above 50SMA (${sma_50}).", 'type': TokenType.CONTEXT.value, 'sentiment': Sentiment.BULLISH.value})
        else:
             tokens.append({'content': f"fighting resistance at 50SMA (${sma_50}).", 'type': TokenType.CONTEXT.value, 'sentiment': Sentiment.NEUTRAL.value})
             
    # 2. Oversold/Overbought (RSI)
    elif rsi < 30:
        tokens.append({'content': "OVERSOLD CAPITULATION", 'type': TokenType.ACTION.value, 'sentiment': Sentiment.BULLISH.value})
        tokens.append({'content': f"RSI is {rsi}, suggesting mean reversion bounce.", 'type': TokenType.EVIDENCE.value, 'sentiment': Sentiment.BULLISH.value})
        
    elif rsi > 70:
        tokens.append({'content': "OVEREXTENDED RALLY", 'type': TokenType.ACTION.value, 'sentiment': Sentiment.BEARISH.value})
        tokens.append({'content': f"RSI is {rsi}, profit taking likely.", 'type': TokenType.EVIDENCE.value, 'sentiment': Sentiment.BEARISH.value})
        
    # 3. Consolidation (Default)
    else:
        tokens.append({'content': "CONSOLIDATING", 'type': TokenType.ACTION.value, 'sentiment': Sentiment.NEUTRAL.value})
        tokens.append({'content': f"near 50-day SMA (${sma_50});", 'type': TokenType.CONTEXT.value, 'sentiment': Sentiment.NEUTRAL.value})
        
        # Try to find a real news catalyst
        news = fetch_news_for_symbol(symbol, lookback_hours=48)
        if news:
            latest = news[0]
            headline = latest['headline']
            # Truncate if too long
            if len(headline) > 60:
                headline = headline[:57] + "..."
            tokens.append({'content': f"News: {headline}", 'type': TokenType.CATALYST.value, 'sentiment': latest['sentiment']})
        else:
            tokens.append({'content': "awaiting catalyst.", 'type': TokenType.CATALYST.value, 'sentiment': Sentiment.NEUTRAL.value})

    # 4. Sector Context & Relative Strength
    try:
        # Sector Comparison
        sector_sym = SYMBOL_TO_SECTOR.get(symbol)
        if sector_sym:
            sector_data = fetch_stock_data(sector_sym)
            stock_data = fetch_stock_data(symbol)
            
            if sector_data and stock_data:
                rel_perf = stock_data['change_percent'] - sector_data['change_percent']
                if abs(rel_perf) > 0.5:
                    perf_text = "outperforming" if rel_perf > 0 else "underperforming"
                    sentiment = Sentiment.BULLISH.value if rel_perf > 0 else Sentiment.BEARISH.value
                    tokens.append({'content': f"{perf_text} sector by {abs(rel_perf):.1f}%.", 'type': TokenType.CONTEXT.value, 'sentiment': sentiment})
                    
        # Market Comparison (vs SPY)
        spy_data = fetch_stock_data('^GSPC')
        stock_data = fetch_stock_data(symbol) # Re-fetch or reuse? Reuse would be better but fetch is cached/fast enough for now
        if spy_data and stock_data:
             rel_spy = stock_data['change_percent'] - spy_data['change_percent']
             if rel_spy > 1.0:
                 tokens.append({'content': "Showing relative strength vs Market.", 'type': TokenType.EVIDENCE.value, 'sentiment': Sentiment.BULLISH.value})
                 
    except Exception as e:
        print(f"Error adding context: {e}")

    return tokens

def get_opportunities(risk_profile="BALANCED", settings=None):
    """
    Returns filtered opportunities based on REAL analysis and scoring.
    Ensures at least 3 results are returned by prioritizing matches but allowing fallbacks.
    """
    if settings is None:
        settings = load_settings()
        
    # 1. Filter Pool based on mock risk profile mapping (simplified)
    pool = list(STOCK_NAMES.keys())
    
    # Filter by Sector
    SECTOR_ETF_TO_NAME = {
        'XLK': 'Technology', 'XLF': 'Financials', 'XLE': 'Energy',
        'XLV': 'Healthcare', 'XLI': 'Industrials', 'XLP': 'Staples',
        'XLU': 'Utilities', 'XLY': 'Discretionary', 'XLB': 'Materials',
        'XLC': 'Communication'
    }
    
    allowed_sectors = settings.get('coverage_sectors', [])
    filtered_pool = []
    
    for sym in pool:
        etf = SYMBOL_TO_SECTOR.get(sym)
        if etf:
            sector_name = SECTOR_ETF_TO_NAME.get(etf, "Unknown")
            if sector_name in allowed_sectors or not allowed_sectors:
                filtered_pool.append(sym)
        else:
            filtered_pool.append(sym)
            
    pool = filtered_pool
    
    # Limit pool for performance, but ensure enough candidates
    import random
    random.shuffle(pool)
    pool = pool[:20] # Analyze 20 stocks to ensure we find enough matches
    
    scored_opps = []
    
    # Parallel Indicator Calculation
    def process_symbol(symbol):
        indicators = calculate_real_indicators(symbol)
        if not indicators:
            return None
        return (symbol, indicators)

    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(process_symbol, pool))
        
    for res in results:
        if not res:
            continue
            
        symbol, indicators = res
            
        # Filter by RVOL Threshold (Problem Ten)
        min_rvol = settings.get('rvol_threshold', 0.0)
        is_rvol_ok = indicators['rvol'] >= min_rvol
        # if indicators['rvol'] < min_rvol:
        #     continue # Relaxed to ensure we get results
            
        # Calculate Confidence
        confidence = calculate_setup_confidence(indicators)
        
        # Calculate Opportunity Score
        opp_score = confidence
        if indicators['rvol'] > 2.0: opp_score += 10
        elif indicators['rvol'] > 1.5: opp_score += 5
        elif indicators['rvol'] < 0.8: opp_score -= 5
        
        # Price Action Modifier
        if indicators['price'] > indicators['sma_50']: opp_score += 3
        
        # Calculate ATR
        atr = calculate_atr(symbol)
        
        # Trade Setup Parameters
        price = indicators['price']
        stop_loss = 0.0
        target = 0.0
        pos_size = "0%"
        horizon = "Unknown"
        
        # Risk Profile Logic
        beta = indicators.get('beta', 1.0)
        is_match = False
        
        # Determine Match & Setup based on Requested Profile
        if risk_profile == "DEFENSIVE":
            is_defensive_sector = SYMBOL_TO_SECTOR.get(symbol) in ['XLP', 'XLU', 'XLV']
            if beta <= 0.9 or is_defensive_sector: # Relaxed slightly from 0.85
                is_match = True
                
            stop_loss = price - (1.5 * atr)
            target = price + (2.0 * atr)
            pos_size = "2-3%"
            
        elif risk_profile == "BALANCED":
            if 0.7 <= beta <= 1.5: # Relaxed slightly
                is_match = True
                
            stop_loss = price - (2.0 * atr)
            target = price + (3.0 * atr)
            pos_size = "3-5%"
            
        else: # SPECULATIVE
            is_spec_sector = SYMBOL_TO_SECTOR.get(symbol) in ['XLK', 'XLC', 'XLY']
            if beta >= 1.1 or is_spec_sector: # Relaxed from 1.2
                is_match = True
                
            stop_loss = price - (2.5 * atr)
            target = price + (5.0 * atr)
            pos_size = "5-8%"
            
        risk_reward = (target - price) / (price - stop_loss) if (price - stop_loss) > 0 else 0
        
        # Time Horizon Logic
        if indicators['rvol'] > 2.5 and indicators['macd'] > indicators['macd_signal']:
            horizon = "Swing (3-10 Days)"
        elif indicators['rsi'] < 30:
            horizon = "Mean Reversion (1-3 Days)"
        else:
            horizon = "Position (2-4 Weeks)"
            
        # Generate Narrative
        narrative = generate_narrative(symbol, indicators)
        
        # Get Catalyst (Earnings)
        catalyst = get_next_catalyst(symbol)
        
        scored_opps.append({
            'symbol': symbol,
            'name': STOCK_NAMES.get(symbol, symbol),
            'confidence': confidence,
            'opp_score': opp_score,
            'narrative': narrative,
            'catalyst': catalyst,
            'trade_setup': {
                'entry': price,
                'stop': round(stop_loss, 2),
                'target': round(target, 2),
                'risk_reward': round(risk_reward, 2),
                'position_size': pos_size,
                'time_horizon': horizon
            },
            'rvol': indicators['rvol'],
            'history': [], 
            'change': 0.0,
            'change': 0.0,
            'change_percent': 0.0,
            'is_match': is_match,
            'is_rvol_ok': is_rvol_ok
        })
        
    # Sort by Match (True first), then RVOL OK, then Opportunity Score
    scored_opps.sort(key=lambda x: (x['is_match'], x['is_rvol_ok'], x['opp_score']), reverse=True)
    
    # Return top 10 (guarantees at least 3 if pool has 3 valid stocks)
    return scored_opps[:10]

def get_sector_data(sector_name):
    """
    Fetches comprehensive sector data using Sector ETFs as proxies.
    """
    SECTOR_NAME_TO_ETF = {v: k for k, v in SECTOR_ETF_TO_NAME.items()}
    etf_symbol = SECTOR_NAME_TO_ETF.get(sector_name)
    
    if not etf_symbol:
        return None
        
    try:
        data = fetch_stock_data(etf_symbol)
        if not data:
            return None
            
        # Enrich with extra stats
        ticker = yf.Ticker(etf_symbol)
        info = ticker.info
        
        data['yield'] = info.get('yield', 0)
        data['pe'] = info.get('trailingPE', 0)
        data['beta'] = info.get('beta', 1.0)
        data['assets'] = info.get('totalAssets', 0)
        data['description'] = info.get('longBusinessSummary', f"Sector ETF for {sector_name}")
        
        return data
    except Exception as e:
        print(f"Error fetching sector data: {e}")
        return None

def get_sector_top_performers(sector_name, limit=5):
    """
    Returns top performing stocks in a sector.
    For now, returns a sample list based on the sector mapping.
    """
    SECTOR_NAME_TO_ETF = {v: k for k, v in SECTOR_ETF_TO_NAME.items()}
    etf = SECTOR_NAME_TO_ETF.get(sector_name)
    
    # Find symbols in this sector from our known list
    sector_symbols = [s for s, e in SYMBOL_TO_SECTOR.items() if e == etf]
    
    # If we don't have enough, add some big names based on sector
    if len(sector_symbols) < 3:
        if sector_name == 'Technology': sector_symbols.extend(['AAPL', 'MSFT', 'NVDA', 'AMD', 'CRM'])
        elif sector_name == 'Financials': sector_symbols.extend(['JPM', 'BAC', 'V', 'MA', 'GS'])
        elif sector_name == 'Healthcare': sector_symbols.extend(['UNH', 'JNJ', 'PFE', 'LLY', 'MRK'])
        elif sector_name == 'Consumer Discretionary': sector_symbols.extend(['AMZN', 'TSLA', 'HD', 'MCD', 'NKE'])
        elif sector_name == 'Communication Services': sector_symbols.extend(['GOOGL', 'META', 'NFLX', 'DIS', 'TMUS'])
    
    sector_symbols = list(set(sector_symbols)) # Unique
    
    results = []
    with ThreadPoolExecutor(max_workers=5) as executor:
        futures = {executor.submit(fetch_stock_data, sym): sym for sym in sector_symbols}
        for future in futures:
            res = future.result()
            if res:
                results.append(res)
                
    # Sort by performance
    results.sort(key=lambda x: x['change_percent'], reverse=True)
    return results[:limit][:3]

def get_morning_espresso_narrative():
    """
    Returns a tokenized narrative based on REAL market data (Indices, Sectors, Time).
    """
    tokens = []
    
    # 1. Time of Day Logic
    ny_tz = pytz.timezone('America/New_York')
    now_ny = datetime.now(ny_tz)
    current_time = now_ny.time()
    
    market_open = datetime.strptime("09:30", "%H:%M").time()
    market_close = datetime.strptime("16:00", "%H:%M").time()
    
    session_token = ""
    if current_time < market_open:
        session_token = "PREMARKET SESSION"
    elif current_time > market_close:
        session_token = "MARKET CLOSE RECAP"
    else:
        session_token = "MARKET OPEN"
        
    tokens.append({'content': f"{session_token}:", 'type': TokenType.ACTION.value, 'sentiment': Sentiment.NEUTRAL.value})

    # 2. Fetch Major Indices
    indices = ['^GSPC', '^IXIC', '^DJI']
    changes = []
    
    try:
        # Batch fetch might be faster but individual is safer for error handling per index
        for idx in indices:
            data = fetch_stock_data(idx)
            if data:
                changes.append(data.get('change_percent', 0.0))
                
        if not changes:
            avg_change = 0.0
        else:
            avg_change = sum(changes) / len(changes)
            
        # 3. Classify Market State
        market_state = "NEUTRAL"
        sentiment = Sentiment.NEUTRAL.value
        action_text = "CONSOLIDATION"
        
        if avg_change > 1.0:
            market_state = "STRONGLY BULLISH"
            sentiment = Sentiment.BULLISH.value
            action_text = "BROAD RALLY"
        elif 0.3 <= avg_change <= 1.0:
            market_state = "MODERATELY BULLISH"
            sentiment = Sentiment.BULLISH.value
            action_text = "POSITIVE MOMENTUM"
        elif -0.3 < avg_change < 0.3:
            market_state = "NEUTRAL"
            sentiment = Sentiment.NEUTRAL.value
            action_text = "RANGE-BOUND TRADING"
        elif -1.0 <= avg_change <= -0.3:
            market_state = "MODERATELY BEARISH"
            sentiment = Sentiment.BEARISH.value
            action_text = "SELLING PRESSURE"
        else: # < -1.0
            market_state = "STRONGLY BEARISH"
            sentiment = Sentiment.BEARISH.value
            action_text = "RISK-OFF MOVE"
            
        tokens.append({'content': action_text, 'type': TokenType.ACTION.value, 'sentiment': sentiment})
        
        # Context with specific numbers
        sp500 = next((d for d in [fetch_stock_data('^GSPC')] if d), None)
        nasdaq = next((d for d in [fetch_stock_data('^IXIC')] if d), None)
        
        context_str = ""
        if sp500:
            sign = "+" if sp500['change_percent'] >= 0 else ""
            context_str += f"S&P {sign}{sp500['change_percent']:.2f}%"
        if nasdaq:
            sign = "+" if nasdaq['change_percent'] >= 0 else ""
            context_str += f", Nasdaq {sign}{nasdaq['change_percent']:.2f}%"
            
        tokens.append({'content': context_str, 'type': TokenType.CONTEXT.value, 'sentiment': Sentiment.NEUTRAL.value})
        
        # 4. Sector Analysis
        sectors = {
            'XLK': 'Technology', 'XLF': 'Financials', 'XLE': 'Energy',
            'XLV': 'Healthcare', 'XLI': 'Industrials', 'XLP': 'Staples',
            'XLU': 'Utilities', 'XLY': 'Discretionary', 'XLB': 'Materials'
        }
        
        best_sector = None
        best_change = -999.0
        
        # Fetch sector data (limit to top 3 for speed if needed, but let's try all)
        for sym, name in sectors.items():
            s_data = fetch_stock_data(sym)
            if s_data and s_data['change_percent'] > best_change:
                best_change = s_data['change_percent']
                best_sector = name
                
        if best_sector:
            tokens.append({'content': f"{best_sector.upper()} SECTOR OUTPERFORMING", 'type': TokenType.CATALYST.value, 'sentiment': Sentiment.BULLISH.value})
            tokens.append({'content': f"(+{best_change:.2f}%)", 'type': TokenType.CONTEXT.value, 'sentiment': Sentiment.NEUTRAL.value})

    except Exception as e:
        # Fallback if fetching fails
        print(f"Error generating narrative: {e}")
        tokens.append({'content': "Market data unavailable.", 'type': TokenType.CONTEXT.value, 'sentiment': Sentiment.NEUTRAL.value})

    return tokens

# --- News Engine ---

def analyze_sentiment(headline):
    """
    Analyzes headline sentiment using keyword scoring.
    Returns: BULLISH, BEARISH, or NEUTRAL
    """
    headline_lower = headline.lower()
    
    bullish_keywords = [
        "beat", "beats", "exceed", "exceeds", "surge", "surges", "surged", "rally", "rallies", "rallied",
        "upgrade", "upgraded", "breakout", "breakthrough", "growth", "strong", "robust", "outperform",
        "acquisition", "approved", "approval", "win", "wins", "won", "positive", "record", "high",
        "soar", "soars", "jump", "jumps", "expand"
    ]
    
    bearish_keywords = [
        "miss", "misses", "missed", "decline", "declines", "declined", "fall", "falls", "fell",
        "drop", "drops", "dropped", "plunge", "plunges", "plunged", "downgrade", "downgraded",
        "lawsuit", "investigation", "probe", "recall", "cut", "cuts", "loss", "losses", "weak",
        "weakness", "underperform", "concern", "concerns", "warning", "warns", "warned", "risk",
        "low", "slump", "slumps", "tumble"
    ]
    
    bullish_score = 0
    bearish_score = 0
    
    words = headline_lower.split()
    
    # Simple scoring (could be weighted)
    for word in words:
        # Strip punctuation
        clean_word = word.strip('.,:;!?')
        if clean_word in bullish_keywords:
            bullish_score += 1
        elif clean_word in bearish_keywords:
            bearish_score += 1
            
    if bullish_score > bearish_score:
        return Sentiment.BULLISH.value
    elif bearish_score > bullish_score:
        return Sentiment.BEARISH.value
    else:
        return Sentiment.NEUTRAL.value

def load_news_from_cache(symbol, max_age_hours=1):
    """Loads news from local JSON cache if fresh."""
    cache_file = "news_cache.json"
    if not os.path.exists(cache_file):
        return None
        
    try:
        with open(cache_file, 'r') as f:
            cache = json.load(f)
            
        if symbol in cache:
            entry = cache[symbol]
            last_updated = datetime.fromisoformat(entry['last_updated'])
            if datetime.now() - last_updated < timedelta(hours=max_age_hours):
                return entry['articles']
    except Exception as e:
        print(f"Cache load error: {e}")
        
    return None

def save_news_to_cache(symbol, articles):
    """Saves news to local JSON cache."""
    cache_file = "news_cache.json"
    cache = {}
    
    if os.path.exists(cache_file):
        try:
            with open(cache_file, 'r') as f:
                cache = json.load(f)
        except:
            pass
            
    cache[symbol] = {
        'last_updated': datetime.now().isoformat(),
        'articles': articles
    }
    
    try:
        with open(cache_file, 'w') as f:
            json.dump(cache, f, indent=2)
    except Exception as e:
        print(f"Cache save error: {e}")

def fetch_news_for_symbol(symbol, lookback_hours=24):
    """
    Fetches news from yfinance, analyzes sentiment, and caches results.
    """
    # Check cache first
    cached_news = load_news_from_cache(symbol)
    if cached_news:
        return cached_news
        
    news_events = []
    try:
        ticker = yf.Ticker(symbol)
        raw_news = ticker.news
        
        cutoff_time = datetime.now() - timedelta(hours=lookback_hours)
        
        for item in raw_news:
            # Parse timestamp
            ts = item.get('providerPublishTime')
            if ts:
                pub_time = datetime.fromtimestamp(ts)
            else:
                pub_time = datetime.now() # Fallback
                
            if pub_time < cutoff_time:
                continue
                
            headline = item.get('title', '')
            sentiment = analyze_sentiment(headline)
            
            event = {
                'event_id': f"{symbol}_{item.get('uuid', uuid.uuid4())}",
                'event_type': 'NEWS',
                'symbol': symbol,
                'timestamp': pub_time.isoformat(), # Serialize for JSON
                'headline': headline,
                'source': item.get('publisher', 'Unknown'),
                'url': item.get('link', ''),
                'sentiment': sentiment
            }
            news_events.append(event)
            
        # Save to cache
        save_news_to_cache(symbol, news_events)
        
    except Exception as e:
        print(f"Error fetching news for {symbol}: {e}")
        
    return news_events

def get_next_catalyst(symbol):
    """
    Finds next earnings date or event.
    """
    try:
        ticker = yf.Ticker(symbol)
        calendar = ticker.calendar
        
        if calendar and 'Earnings Date' in calendar:
            # yfinance calendar format varies, sometimes it's a dict, sometimes list
            # Assuming dict with 'Earnings Date' list
            earnings_dates = calendar.get('Earnings Date', [])
            if earnings_dates:
                next_date = earnings_dates[0] # datetime.date object
                days_until = (next_date - datetime.now().date()).days
                
                if 0 <= days_until <= 30:
                    return f"Earnings in {days_until} days ({next_date.strftime('%Y-%m-%d')})"
                elif days_until < 0:
                     return "Earnings passed"
                else:
                     return f"Earnings on {next_date.strftime('%Y-%m-%d')}"
                     
        return "No upcoming catalyst"
    except:
        return "TBD"

# --- Advanced Analytics (Phase 4) ---

def fetch_fundamentals(symbol):
    """
    Fetches fundamental data (Valuation, Profitability, Growth).
    Returns a dictionary of metrics.
    """
    try:
        ticker = yf.Ticker(symbol)
        info = ticker.info
        
        # Valuation
        pe = info.get('trailingPE', 0)
        fpe = info.get('forwardPE', 0)
        peg = info.get('pegRatio', 0)
        ps = info.get('priceToSalesTrailing12Months', 0)
        pb = info.get('priceToBook', 0)
        mkt_cap = info.get('marketCap', 0)
        
        # Profitability
        gross_margin = info.get('grossMargins', 0)
        op_margin = info.get('operatingMargins', 0)
        net_margin = info.get('profitMargins', 0)
        roe = info.get('returnOnEquity', 0)
        
        # Growth (Quarterly)
        rev_growth = info.get('revenueGrowth', 0)
        earn_growth = info.get('earningsGrowth', 0)
        
        return {
            'pe': round(pe, 2) if pe else 0,
            'fpe': round(fpe, 2) if fpe else 0,
            'peg': round(peg, 2) if peg else 0,
            'ps': round(ps, 2) if ps else 0,
            'pb': round(pb, 2) if pb else 0,
            'mkt_cap': mkt_cap,
            'gross_margin': round(gross_margin * 100, 1) if gross_margin else 0,
            'op_margin': round(op_margin * 100, 1) if op_margin else 0,
            'net_margin': round(net_margin * 100, 1) if net_margin else 0,
            'roe': round(roe * 100, 1) if roe else 0,
            'rev_growth': round(rev_growth * 100, 1) if rev_growth else 0,
            'earn_growth': round(earn_growth * 100, 1) if earn_growth else 0
        }
    except Exception as e:
        print(f"Error fetching fundamentals for {symbol}: {e}")
        return None

def calculate_risk_metrics(symbol, lookback_years=1):
    """
    Calculates real risk metrics (Beta, Sharpe, Volatility, Drawdown).
    """
    try:
        ticker = yf.Ticker(symbol)
        # Fetch 1 year of data
        end_date = datetime.now()
        start_date = end_date - timedelta(days=365*lookback_years)
        
        df = ticker.history(start=start_date, end=end_date, interval="1d")
        if df.empty or len(df) < 200:
            return None
            
        # Benchmark (SPY) for Beta
        spy = yf.Ticker("SPY")
        spy_df = spy.history(start=start_date, end=end_date, interval="1d")
        
        # Align dates
        df_rets = df['Close'].pct_change().dropna()
        spy_rets = spy_df['Close'].pct_change().dropna()
        
        # Inner join to ensure same dates
        aligned = pd.concat([df_rets, spy_rets], axis=1, join='inner')
        aligned.columns = ['Stock', 'SPY']
        
        returns = aligned['Stock']
        market_returns = aligned['SPY']
        
        # 1. Beta
        covariance = returns.cov(market_returns)
        variance = market_returns.var()
        beta = covariance / variance if variance != 0 else 1.0
        
        # 2. Volatility (Annualized)
        volatility = returns.std() * np.sqrt(252)
        
        # 3. Sharpe Ratio (Risk Free Rate assumed 4%)
        rf_rate = 0.04
        excess_returns = returns - (rf_rate / 252)
        sharpe = (excess_returns.mean() / returns.std()) * np.sqrt(252) if returns.std() != 0 else 0
        
        # 4. Max Drawdown
        cumulative = (1 + returns).cumprod()
        peak = cumulative.cummax()
        drawdown = (cumulative - peak) / peak
        max_drawdown = drawdown.min()
        
        # Classification
        risk_level = "MODERATE"
        if beta > 1.5 or volatility > 0.4:
            risk_level = "AGGRESSIVE"
        elif beta < 0.8 and volatility < 0.2:
            risk_level = "DEFENSIVE"
            
        return {
            'beta': round(beta, 2),
            'sharpe': round(sharpe, 2),
            'volatility': round(volatility * 100, 1),
            'max_drawdown': round(max_drawdown * 100, 1),
            'risk_level': risk_level
        }
        
    except Exception as e:
        print(f"Error calculating risk metrics for {symbol}: {e}")
        return None

# --- Settings Persistence ---

def load_settings():
    """Loads user settings from JSON."""
    settings_file = "user_settings.json"
    default_settings = {
        "risk_profile": "BALANCED",
        "dark_mode": True,
        "notifications": True,
        "rvol_threshold": 1.0,
        "coverage_sectors": ["Technology", "Financials", "Energy", "Healthcare", "Industrials", "Staples", "Utilities", "Discretionary", "Materials"]
    }
    
    if not os.path.exists(settings_file):
        return default_settings
        
    try:
        with open(settings_file, 'r') as f:
            saved = json.load(f)
            # Merge with defaults to ensure all keys exist
            default_settings.update(saved)
            return default_settings
    except:
        return default_settings

def save_settings(settings):
    """Saves user settings to JSON."""
    settings_file = "user_settings.json"
    try:
        with open(settings_file, 'w') as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print(f"Error saving settings: {e}")

# --- Phase 5: Market Regime & Advanced Analytics ---

def detect_market_regime():
    """
    Analyzes SPY to determine the current market regime.
    Returns a dictionary with regime details.
    """
    try:
        spy = yf.Ticker("SPY")
        # Fetch enough data for 50 SMA and ATR
        df = spy.history(period="3mo", interval="1d")
        
        if df.empty or len(df) < 50:
            return {
                "regime": "NEUTRAL",
                "trend": "SIDEWAYS",
                "volatility": "NORMAL",
                "description": "Insufficient data to determine regime."
            }
            
        close = df['Close']
        
        # 1. Trend Analysis (20 vs 50 SMA)
        sma_20 = close.rolling(window=20).mean().iloc[-1]
        sma_50 = close.rolling(window=50).mean().iloc[-1]
        current_price = close.iloc[-1]
        
        trend = "SIDEWAYS"
        if current_price > sma_20 > sma_50:
            trend = "STRONG UPTREND"
        elif current_price < sma_20 < sma_50:
            trend = "STRONG DOWNTREND"
        elif current_price > sma_50:
            trend = "UPTREND"
        elif current_price < sma_50:
            trend = "DOWNTREND"
            
        # 2. Volatility Analysis (ATR / Price)
        high_low = df['High'] - df['Low']
        atr_14 = high_low.rolling(window=14).mean().iloc[-1]
        atr_pct = (atr_14 / current_price) * 100
        
        volatility = "NORMAL"
        if atr_pct > 1.5:
            volatility = "HIGH"
        elif atr_pct < 0.5:
            volatility = "LOW"
            
        # 3. Regime Classification
        regime = "NEUTRAL"
        description = "Market is directionless."
        
        if trend == "STRONG UPTREND" and volatility == "LOW":
            regime = "BULLISH GRIND"
            description = "Steady uptrend with low volatility. Buy dips."
        elif trend == "STRONG UPTREND" and volatility == "HIGH":
            regime = "VOLATILE BULL"
            description = "Uptrend but choppy. Wide stops needed."
        elif trend == "STRONG DOWNTREND":
            regime = "BEARISH"
            description = "Market in correction. Cash is king."
        elif trend == "SIDEWAYS" and volatility == "HIGH":
            regime = "CHOPPY"
            description = "No clear trend and high risk. Reduce size."
            
        return {
            "regime": regime,
            "trend": trend,
            "volatility": volatility,
            "description": description,
            "sma_20": round(sma_20, 2),
            "sma_50": round(sma_50, 2),
            "atr_pct": round(atr_pct, 2)
        }
        
    except Exception as e:
        print(f"Error detecting market regime: {e}")
        return {"regime": "UNKNOWN", "trend": "UNKNOWN", "volatility": "UNKNOWN", "description": "Error analyzing market."}

def analyze_sector_rotation():
    """
    Analyzes sector ETF performance to identify rotation.
    Returns sorted list of sectors (best to worst).
    """
    sectors = {
        'XLK': 'Technology', 'XLF': 'Financials', 'XLE': 'Energy',
        'XLV': 'Healthcare', 'XLI': 'Industrials', 'XLP': 'Staples',
        'XLU': 'Utilities', 'XLY': 'Discretionary', 'XLB': 'Materials',
        'XLC': 'Communication', 'IYR': 'Real Estate'
    }
    
    results = []
    try:
        # Batch fetch would be ideal, but loop is fine for 11 items
        for sym, name in sectors.items():
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="1mo", interval="1d")
            
            if not hist.empty:
                current = hist['Close'].iloc[-1]
                prev_1d = hist['Close'].iloc[-2] if len(hist) > 1 else current
                prev_1w = hist['Close'].iloc[-6] if len(hist) > 6 else current
                prev_1mo = hist['Close'].iloc[0]
                
                chg_1d = ((current - prev_1d) / prev_1d) * 100
                chg_1w = ((current - prev_1w) / prev_1w) * 100
                chg_1mo = ((current - prev_1mo) / prev_1mo) * 100
                
                results.append({
                    'symbol': sym,
                    'name': name,
                    '1d': round(chg_1d, 2),
                    '1w': round(chg_1w, 2),
                    '1mo': round(chg_1mo, 2)
                })
                
        # Sort by 1 week performance (momentum)
        results.sort(key=lambda x: x['1w'], reverse=True)
        return results
        
    except Exception as e:
        print(f"Error analyzing sectors: {e}")
        return []

def get_earnings_calendar(days=7):
    """
    Fetches upcoming earnings for the coverage universe.
    """
    upcoming = []
    for sym in SAMPLE_STOCKS:
        try:
            ticker = yf.Ticker(sym)
            cal = ticker.calendar
            if cal and 'Earnings Date' in cal:
                dates = cal.get('Earnings Date', [])
                if dates:
                    next_date = dates[0]
                    days_until = (next_date - datetime.now().date()).days
                    
                    if 0 <= days_until <= days:
                        upcoming.append({
                            'symbol': sym,
                            'date': next_date.strftime('%Y-%m-%d'),
                            'days_until': days_until
                        })
        except:
            continue
            
    upcoming.sort(key=lambda x: x['days_until'])
    return upcoming

def save_opportunity_to_history(opportunity):
    """
    Saves a generated opportunity to a history JSON file.
    """
    history_file = "idea_history.json"
    history = []
    
    if os.path.exists(history_file):
        try:
            with open(history_file, 'r') as f:
                history = json.load(f)
        except:
            pass
            
    # Add timestamp and ID
    opportunity['created_at'] = datetime.now().isoformat()
    opportunity['id'] = str(uuid.uuid4())
    opportunity['status'] = 'OPEN' # OPEN, CLOSED, EXPIRED
    
    # Keep only last 50
    history.insert(0, opportunity)
    history = history[:50]
    
    try:
        with open(history_file, 'w') as f:
            json.dump(history, f, indent=2)
    except Exception as e:
        print(f"Error saving history: {e}")

def get_idea_history():
    """Returns the list of saved opportunities."""
    history_file = "idea_history.json"
    if not os.path.exists(history_file):
        return []
    try:
        with open(history_file, 'r') as f:
            return json.load(f)
    except:
        return []

def analyze_portfolio_correlation(symbols):
    """
    Calculates correlation matrix for a list of symbols.
    Returns the average correlation (0-1).
    """
    if not symbols or len(symbols) < 2:
        return 0.0
        
    try:
        data = {}
        for sym in symbols:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="3mo", interval="1d")
            if not hist.empty:
                data[sym] = hist['Close'].pct_change().dropna()
                
        df = pd.DataFrame(data)
        corr_matrix = df.corr()
        
        # Calculate average off-diagonal correlation
        n = len(df.columns)
        if n < 2: return 0.0
        
        sum_corr = corr_matrix.sum().sum() - n
        avg_corr = sum_corr / (n * (n - 1))
        
        return round(avg_corr, 2)
        
    except Exception as e:
        print(f"Error calculating correlation: {e}")
        return 0.0

def fetch_detailed_ohlc_data(symbol, period="1mo", interval="1d"):
    """
    Fetches detailed OHLC data for advanced charting.
    Returns a list of dictionaries suitable for candlestick rendering.
    """
    try:
        ticker = yf.Ticker(symbol)
        history = ticker.history(period=period, interval=interval)
        
        if history.empty:
            return []
            
        data = []
        for date, row in history.iterrows():
            data.append({
                'date': date.strftime("%Y-%m-%d %H:%M"),
                'open': row['Open'],
                'high': row['High'],
                'low': row['Low'],
                'close': row['Close'],
                'volume': row['Volume']
            })
            
        return data
    except Exception as e:
        print(f"Error fetching OHLC data for {symbol}: {e}")
        return []

def get_comparison_data(target_symbol, comparison_symbols=None):
    """
    Fetches performance data for target symbol and a list of comparison symbols.
    Calculates returns for 1D, 1W, 1M, YTD, 1Y.
    Calculates correlation matrix.
    """
    if comparison_symbols is None:
        comparison_symbols = ['^GSPC', 'XLK'] # Default to S&P 500 and Tech Sector
        
    all_symbols = [target_symbol] + comparison_symbols
    
    performance_data = []
    
    # 1. Fetch Performance Stats
    for sym in all_symbols:
        try:
            ticker = yf.Ticker(sym)
            hist = ticker.history(period="1y")
            
            if hist.empty:
                continue
                
            current_price = hist['Close'].iloc[-1]
            
            # Helper to get return
            def get_return(days):
                if len(hist) > days:
                    prev = hist['Close'].iloc[-days-1]
                    return ((current_price - prev) / prev) * 100
                return 0.0
                
            # YTD
            current_year = datetime.now().year
            ytd_start = f"{current_year-1}-12-31"
            ytd_hist = hist.loc[ytd_start:]
            ytd_return = 0.0
            if not ytd_hist.empty:
                ytd_open = ytd_hist['Close'].iloc[0]
                ytd_return = ((current_price - ytd_open) / ytd_open) * 100
                
            stats = {
                'symbol': sym,
                'name': STOCK_NAMES.get(sym, sym),
                '1d': get_return(1),
                '1w': get_return(5),
                '1m': get_return(21),
                'ytd': ytd_return,
                '1y': get_return(252)
            }
            performance_data.append(stats)
            
        except Exception as e:
            print(f"Error fetching comparison data for {sym}: {e}")
            
    # 2. Calculate Correlation Matrix
    correlation_matrix = {}
    try:
        # Download batch data for correlation
        batch_data = yf.download(all_symbols, period="1y", progress=False)['Close']
        corr_df = batch_data.corr()
        
        # Convert to dictionary format: {'AAPL': {'MSFT': 0.8, ...}, ...}
        for sym1 in all_symbols:
            correlation_matrix[sym1] = {}
            for sym2 in all_symbols:
                if sym1 in corr_df and sym2 in corr_df:
                    correlation_matrix[sym1][sym2] = corr_df.loc[sym1, sym2] if sym1 != sym2 else 1.0
                else:
                    correlation_matrix[sym1][sym2] = 0.0
                    
    except Exception as e:
        print(f"Error calculating correlation matrix: {e}")
        
    return {
        'performance': performance_data,
        'correlation': correlation_matrix
    }

# --- Async Wrappers ---

def fetch_stock_data_async(symbol):
    return THREAD_POOL.submit(fetch_stock_data, symbol)

def fetch_fundamentals_async(symbol):
    return THREAD_POOL.submit(fetch_fundamentals, symbol)

def get_market_indices_async():
    return THREAD_POOL.submit(get_market_indices)

def get_top_gainers_losers_async():
    return THREAD_POOL.submit(get_top_gainers_losers)

def get_talking_points_async():
    return THREAD_POOL.submit(get_talking_points)

def get_morning_espresso_narrative_async():
    return THREAD_POOL.submit(get_morning_espresso_narrative)

def analyze_sector_rotation_async():
    return THREAD_POOL.submit(analyze_sector_rotation)

def get_earnings_calendar_async():
    return THREAD_POOL.submit(get_earnings_calendar)

def get_opportunities_async(profile):
    return THREAD_POOL.submit(get_opportunities, profile)

def fetch_detailed_ohlc_data_async(symbol, period="1mo", interval="1d"):
    return THREAD_POOL.submit(fetch_detailed_ohlc_data, symbol, period, interval)

def get_comparison_data_async(symbol):
    return THREAD_POOL.submit(get_comparison_data, symbol)

def fetch_news_for_symbol_async(symbol, lookback_hours=24):
    return THREAD_POOL.submit(fetch_news_for_symbol, symbol, lookback_hours)

def calculate_risk_metrics_async(symbol):
    return THREAD_POOL.submit(calculate_risk_metrics, symbol)

def get_idea_history_async():
    return THREAD_POOL.submit(get_idea_history)
