import data_service
import json

def test_chart_timeframes():
    print("Testing fetch_stock_data with different periods...")
    
    # Test 1D
    print("\n--- 1D (5m interval) ---")
    data_1d = data_service.fetch_stock_data("NVDA", period="1d", interval="5m")
    if data_1d and data_1d['history']:
        print(f"Fetched {len(data_1d['history'])} points.")
        print(f"First date: {data_1d.get('history_dates', [])[0]}")
    else:
        print("Failed to fetch 1D data.")

    # Test ALL (Max)
    print("\n--- ALL (Max, 1mo interval) ---")
    data_max = data_service.fetch_stock_data("NVDA", period="max", interval="1mo")
    if data_max and data_max['history']:
        print(f"Fetched {len(data_max['history'])} points.")
        print(f"First date: {data_max.get('history_dates', [])[0]}")
        print(f"Last date: {data_max.get('history_dates', [])[-1]}")
    else:
        print("Failed to fetch Max data.")

def test_morning_espresso():
    print("\nTesting get_morning_espresso_narrative...")
    tokens = data_service.get_morning_espresso_narrative()
    print(f"Generated {len(tokens)} tokens.")
    for t in tokens:
        print(f"[{t['type']}] {t['content']} ({t['sentiment']})")

def test_opportunities():
    print("\nTesting get_opportunities (Real Analysis)...")
    opps = data_service.get_opportunities("BALANCED")
    print(f"Found {len(opps)} opportunities.")
    
    for opp in opps:
        print(f"\nSymbol: {opp['symbol']} ({opp['name']})")
        print(f"Confidence: {opp['confidence']}%")
        print(f"Opp Score: {opp['opp_score']}")
        print(f"Trade Setup: {opp['trade_setup']}")
        print("Narrative:")
        for t in opp['narrative']:
            print(f"  - {t['content']}")

if __name__ == "__main__":
    test_chart_timeframes()
    test_morning_espresso()
    test_opportunities()
