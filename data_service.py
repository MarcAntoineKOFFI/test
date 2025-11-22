import yfinance as yf
import random
import datetime
import time
from enum import Enum

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

def fetch_stock_data(symbol):
    """
    Fetches stock data using yfinance, falling back to mock data if it fails.
    Includes history for sparklines.
    """
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
        # Optimization: For a real app, we might cache this or fetch less frequently
        history = ticker.history(period="1mo", interval="1d")
        history_prices = history['Close'].tolist() if not history.empty else []
        
        name = STOCK_NAMES.get(symbol, symbol)
        
        return {
            'symbol': symbol,
            'price': price,
            'change': change,
            'change_percent': change_percent,
            'name': name,
            'history': history_prices,
            'timestamps': ['10:00 AM', '10:30 AM', '11:00 AM', '11:30 AM', '12:00 PM', '12:30 PM', '1:00 PM', '1:30 PM', '2:00 PM', '2:30 PM', '3:00 PM', '3:30 PM', '4:00 PM'],
            'rvol': random.uniform(0.5, 3.0),
            'open': info.open if info.open else price,
            'high': info.day_high if info.day_high else price,
            'low': info.day_low if info.day_low else price,
            'volume': info.last_volume if info.last_volume else 0,
            'pe_ratio': random.uniform(15, 60), # Mock PE for speed
            'market_cap': info.market_cap if info.market_cap else 0
        }
        
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
    
    time_variation = (datetime.datetime.now().minute / 60) - 0.5
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
        'timestamps': ['9:30', '10:00', '10:30', '11:00', '11:30', '12:00', '12:30', '13:00', '13:30', '14:00', '14:30', '15:00', '15:30', '16:00'],
        'rvol': random.uniform(0.5, 3.0),
        'open': base_price * (1 + (random.random() - 0.5) * 0.02),
        'high': max(history) * (1 + random.random() * 0.01),
        'low': min(history) * (1 - random.random() * 0.01),
        'volume': int(random.uniform(1000000, 50000000)),
        'pe_ratio': round(random.uniform(15, 60), 2),
        'market_cap': random.uniform(10e9, 2e12)
    }

def get_market_indices():
    results = []
    for index in MARKET_INDICES:
        data = fetch_stock_data(index['symbol'])
        if data:
            results.append(data)
    return results

def get_top_gainers_losers():
    stock_data = []
    for symbol in SAMPLE_STOCKS:
        data = fetch_stock_data(symbol)
        if data:
            stock_data.append(data)
            
    stock_data.sort(key=lambda x: x['change_percent'], reverse=True)
    
    gainers = stock_data[:5]
    losers = stock_data[-5:]
    losers.reverse()
    
    return gainers, losers

def get_talking_points():
    """Legacy function, kept for compatibility if needed, but new UI uses specific providers."""
    points = []
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

def generate_narrative(symbol):
    """
    Generates a structured narrative based on mock technical/fundamental data.
    Returns a list of NarrativeToken dicts.
    """
    # Mock Data Derivation
    rvol = random.uniform(0.8, 3.5)
    rsi = random.uniform(20, 80)
    sma_50_diff = random.uniform(-5, 10) # Percent above/below SMA 50
    
    tokens = []
    
    # 1. Catalyst Check (Mock Calendar)
    # Randomly assign a catalyst to some stocks
    if random.random() < 0.2:
        catalyst_type = random.choice(["EARNINGS BEAT", "FDA APPROVAL", "M&A RUMOR", "GUIDANCE RAISE"])
        tokens.append({'content': "SURGE", 'type': TokenType.ACTION.value, 'sentiment': Sentiment.BULLISH.value})
        tokens.append({'content': "driven by", 'type': TokenType.CONTEXT.value, 'sentiment': Sentiment.NEUTRAL.value})
        tokens.append({'content': catalyst_type, 'type': TokenType.CATALYST.value, 'sentiment': Sentiment.BULLISH.value, 'meta': {'headline': f"{symbol} Reports Strong Q3 Results", 'source': "Reuters", 'time': "08:30 AM"}})
        return tokens

    # 2. Momentum Logic
    if rvol > 2.0 and sma_50_diff > 0:
        tokens.append({'content': "INSTITUTIONAL ACCUMULATION", 'type': TokenType.ACTION.value, 'sentiment': Sentiment.BULLISH.value})
        tokens.append({'content': "detected;", 'type': TokenType.CONTEXT.value, 'sentiment': Sentiment.NEUTRAL.value})
        tokens.append({'content': f"volume is {rvol:.1f}x average", 'type': TokenType.EVIDENCE.value, 'sentiment': Sentiment.BULLISH.value})
        tokens.append({'content': ", confirming breakout.", 'type': TokenType.CONTEXT.value, 'sentiment': Sentiment.NEUTRAL.value})
        return tokens
        
    # 3. Mean Reversion (Oversold)
    if rsi < 30:
        tokens.append({'content': "TECHNICAL CAPITULATION", 'type': TokenType.ACTION.value, 'sentiment': Sentiment.BULLISH.value})
        tokens.append({'content': "offers entry;", 'type': TokenType.CONTEXT.value, 'sentiment': Sentiment.NEUTRAL.value})
        tokens.append({'content': f"Oversold RSI ({int(rsi)})", 'type': TokenType.EVIDENCE.value, 'sentiment': Sentiment.BULLISH.value})
        tokens.append({'content': "at support.", 'type': TokenType.CONTEXT.value, 'sentiment': Sentiment.NEUTRAL.value})
        return tokens

    # 4. Mean Reversion (Overbought)
    if rsi > 70:
        tokens.append({'content': "PROFIT TAKING", 'type': TokenType.ACTION.value, 'sentiment': Sentiment.BEARISH.value})
        tokens.append({'content': "suggested;", 'type': TokenType.CONTEXT.value, 'sentiment': Sentiment.NEUTRAL.value})
        tokens.append({'content': f"Overextended RSI ({int(rsi)})", 'type': TokenType.EVIDENCE.value, 'sentiment': Sentiment.BEARISH.value})
        tokens.append({'content': "signals pullback.", 'type': TokenType.CONTEXT.value, 'sentiment': Sentiment.NEUTRAL.value})
        return tokens
        
    # Default / Neutral
    tokens.append({'content': "CONSOLIDATING", 'type': TokenType.ACTION.value, 'sentiment': Sentiment.NEUTRAL.value})
    tokens.append({'content': "near 50-day MA;", 'type': TokenType.CONTEXT.value, 'sentiment': Sentiment.NEUTRAL.value})
    tokens.append({'content': "awaiting catalyst.", 'type': TokenType.CONTEXT.value, 'sentiment': Sentiment.NEUTRAL.value})
    return tokens

def get_morning_espresso():
    """Returns top 3 market stories."""
    return [
        {
            "headline": "Tech Rotates to Value",
            "bullets": ["Yield curve steepening favors financials", "Nasdaq 100 hits resistance at 15k", "Buy JPM, Sell QQQ"],
            "sentiment": "CAUTION"
        },
        {
            "headline": "CPI Print Beats Estimates",
            "bullets": ["Core inflation cools to 3.2%", "Fed pause probability rises to 80%", "Long duration assets bid"],
            "sentiment": "OPPORTUNITY"
        },
        {
            "headline": "Geopolitical Risk Spikes",
            "bullets": ["Energy sector acting as hedge", "Defense stocks breaking out", "Monitor XLE and ITA"],
            "sentiment": "CAUTION"
        }
    ]

def get_whisper_numbers():
    """Returns consensus vs whisper data."""
    return [
        {"symbol": "TSLA", "event": "Earnings", "consensus": 3.20, "whisper": 3.55, "date": "Today AMC"},
        {"symbol": "NVDA", "event": "Earnings", "consensus": 1.10, "whisper": 1.05, "date": "Tomorrow AMC"},
        {"symbol": "NFP", "event": "Econ Print", "consensus": 180, "whisper": 220, "date": "Friday 8:30"},
        {"symbol": "AAPL", "event": "Earnings", "consensus": 1.40, "whisper": 1.42, "date": "Next Week"},
    ]

def get_opportunities(risk_profile="BALANCED"):
    """Returns filtered opportunities based on risk profile."""
    # Mock filtering logic
    all_symbols = list(STOCK_NAMES.keys())
    random.shuffle(all_symbols)
    
    # Filter based on profile (Mock)
    # Defensive: Low Beta, Div Payers (JNJ, PG, KO, etc.)
    # Balanced: Mega Cap Tech (AAPL, MSFT, GOOGL)
    # Speculative: High Beta (TSLA, NVDA, AMD, NFLX)
    
    defensive_pool = ['JNJ', 'PG', 'KO', 'PEP', 'WMT', 'UNH', 'VZ', 'T', 'MRK', 'PFE']
    speculative_pool = ['TSLA', 'NVDA', 'AMD', 'NFLX', 'PYPL', 'META', 'BABA', 'COIN', 'PLTR']
    balanced_pool = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'V', 'MA', 'JPM', 'DIS', 'CSCO']
    
    target_pool = []
    if risk_profile == "DEFENSIVE":
        target_pool = defensive_pool
    elif risk_profile == "SPECULATIVE":
        target_pool = speculative_pool
    else:
        target_pool = balanced_pool
        
    # Select 3 random from pool that exist in STOCK_NAMES/DATA
    # Note: SAMPLE_STOCKS contains the keys we use in fetch_stock_data
    available_pool = [s for s in target_pool if s in SAMPLE_STOCKS]
    
    # If pool is empty (due to mock data limits), fallback to sample stocks
    if not available_pool:
        available_pool = SAMPLE_STOCKS[:5]
        
    selected = available_pool[:3] if len(available_pool) >= 3 else available_pool
    
    results = []
    for symbol in selected:
        narrative = generate_narrative(symbol)
        confidence = random.randint(75, 98)
        results.append({
            "symbol": symbol,
            "name": STOCK_NAMES.get(symbol, symbol),
            "confidence": confidence,
            "narrative": narrative
        })
        
    return results

def get_morning_espresso_narrative():
    """Returns a tokenized narrative for the morning market update."""
    tokens = []
    tokens.append({'content': "MARKET OPEN:", 'type': TokenType.ACTION.value, 'sentiment': Sentiment.NEUTRAL.value})
    tokens.append({'content': "Futures are pointing", 'type': TokenType.CONTEXT.value, 'sentiment': Sentiment.NEUTRAL.value})
    tokens.append({'content': "HIGHER", 'type': TokenType.ACTION.value, 'sentiment': Sentiment.BULLISH.value})
    tokens.append({'content': "as inflation data comes in", 'type': TokenType.CONTEXT.value, 'sentiment': Sentiment.NEUTRAL.value})
    tokens.append({'content': "COOLER THAN EXPECTED.", 'type': TokenType.EVIDENCE.value, 'sentiment': Sentiment.BULLISH.value})
    tokens.append({'content': "Tech sector leading the charge with", 'type': TokenType.CONTEXT.value, 'sentiment': Sentiment.NEUTRAL.value})
    tokens.append({'content': "NVDA +2.5%", 'type': TokenType.CATALYST.value, 'sentiment': Sentiment.BULLISH.value})
    tokens.append({'content': "premarket.", 'type': TokenType.CONTEXT.value, 'sentiment': Sentiment.NEUTRAL.value})
    return tokens
