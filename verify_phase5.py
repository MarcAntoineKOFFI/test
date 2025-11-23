
import sys
import os
import json
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import data_service

def test_market_regime():
    print("\n--- Testing Market Regime ---")
    regime = data_service.detect_market_regime()
    print(json.dumps(regime, indent=2))
    if regime['regime'] == "UNKNOWN":
        print("FAIL: Regime detection failed")
    else:
        print("PASS: Regime detected")

def test_sector_rotation():
    print("\n--- Testing Sector Rotation ---")
    sectors = data_service.analyze_sector_rotation()
    print(f"Found {len(sectors)} sectors")
    if sectors:
        print(f"Top Sector: {sectors[0]['name']} ({sectors[0]['1w']}%)")
        print("PASS: Sectors analyzed")
    else:
        print("FAIL: No sectors found")

def test_earnings_calendar():
    print("\n--- Testing Earnings Calendar ---")
    earnings = data_service.get_earnings_calendar(days=30)
    print(f"Found {len(earnings)} upcoming earnings")
    if earnings:
        print(f"Next: {earnings[0]['symbol']} in {earnings[0]['days_until']} days")
    print("PASS: Earnings calendar scanned (might be empty if no earnings soon)")

def test_portfolio_risk():
    print("\n--- Testing Portfolio Risk ---")
    symbols = ['AAPL', 'MSFT', 'NVDA'] # Tech heavy
    corr = data_service.analyze_portfolio_correlation(symbols)
    print(f"Correlation for {symbols}: {corr}")
    
    symbols_div = ['AAPL', 'XOM', 'JNJ'] # Diverse
    corr_div = data_service.analyze_portfolio_correlation(symbols_div)
    print(f"Correlation for {symbols_div}: {corr_div}")
    
    if corr > corr_div:
        print("PASS: Tech portfolio has higher correlation than diverse portfolio")
    else:
        print("WARN: Correlation logic might need tuning")

def test_history():
    print("\n--- Testing Idea History ---")
    opp = {
        "symbol": "TEST",
        "name": "Test Corp",
        "confidence": 90,
        "narrative": [],
        "trade_setup": {"entry": 100}
    }
    data_service.save_opportunity_to_history(opp)
    
    history = data_service.get_idea_history()
    print(f"History items: {len(history)}")
    
    found = False
    for item in history:
        if item['symbol'] == "TEST":
            found = True
            break
            
    if found:
        print("PASS: History saved and retrieved")
    else:
        print("FAIL: Saved item not found in history")

if __name__ == "__main__":
    test_market_regime()
    test_sector_rotation()
    test_earnings_calendar()
    test_portfolio_risk()
    test_history()
