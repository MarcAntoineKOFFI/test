import sys
import os
sys.path.append(os.getcwd())
import data_service

def test():
    print("Testing get_opportunities...")
    try:
        opps = data_service.get_opportunities("BALANCED")
        print(f"Got {len(opps)} opportunities.")
        for o in opps:
            print(f"- {o['symbol']}: Score={o['opp_score']}, Match={o.get('is_match')}, RVOL_OK={o.get('is_rvol_ok')}")
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test()
