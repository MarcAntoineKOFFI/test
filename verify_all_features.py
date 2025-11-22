import data_service
import sys
from datetime import datetime

def verify_all():
    print("=== VERIFYING ADVANCED ANALYTICS & FUNDAMENTALS ===")
    
    symbol = "NVDA"
    
    # 1. Fundamentals
    print(f"\n[1] Testing Fundamentals for {symbol}...")
    fund = data_service.fetch_fundamentals(symbol)
    if fund:
        print(f"    SUCCESS: Market Cap: {fund.get('mkt_cap')}, PE: {fund.get('pe')}")
    else:
        print("    FAILURE: No fundamentals returned.")
        
    # 2. Risk Metrics
    print(f"\n[2] Testing Risk Metrics for {symbol}...")
    risk = data_service.calculate_risk_metrics(symbol)
    if risk:
        print(f"    SUCCESS: Beta: {risk.get('beta')}, Sharpe: {risk.get('sharpe')}")
    else:
        print("    FAILURE: No risk metrics returned.")
        
    # 3. Morning Espresso
    print("\n[3] Testing Morning Espresso Narrative...")
    narrative = data_service.get_morning_espresso_narrative()
    if narrative:
        print(f"    SUCCESS: Generated {len(narrative)} tokens.")
    else:
        print("    FAILURE: No narrative generated.")
        
    # 4. Opportunities
    print("\n[4] Testing Opportunities Generation...")
    opps = data_service.get_opportunities("BALANCED")
    if opps:
        print(f"    SUCCESS: Generated {len(opps)} opportunities.")
        for opp in opps:
            print(f"    - {opp['symbol']}: Score {opp['opp_score']}, Confidence {opp['confidence']}%")
    else:
        print("    FAILURE: No opportunities generated.")
        
    print("\n=== VERIFICATION COMPLETE ===")

if __name__ == "__main__":
    verify_all()
