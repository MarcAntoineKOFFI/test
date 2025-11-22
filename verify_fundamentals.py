import data_service
import sys

def test_fundamentals():
    symbol = "AAPL"
    print(f"Fetching fundamentals for {symbol}...")
    fund_data = data_service.fetch_fundamentals(symbol)
    
    if fund_data:
        print("SUCCESS: Fundamentals fetched.")
        print(fund_data)
    else:
        print("FAILURE: Fundamentals returned None.")

def test_risk_metrics():
    symbol = "AAPL"
    print(f"Calculating risk metrics for {symbol}...")
    risk_data = data_service.calculate_risk_metrics(symbol)
    
    if risk_data:
        print("SUCCESS: Risk metrics calculated.")
        print(risk_data)
    else:
        print("FAILURE: Risk metrics returned None.")

if __name__ == "__main__":
    test_fundamentals()
    print("-" * 20)
    test_risk_metrics()
