import yfinance as yf
import json

def check_news():
    try:
        ticker = yf.Ticker("NVDA")
        news = ticker.news
        print(json.dumps(news, indent=2))
        
        # Also check history dates
        hist = ticker.history(period="1mo")
        print("\nHistory Index:")
        print(hist.index)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_news()
