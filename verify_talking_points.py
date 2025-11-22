import sys
from PySide6.QtWidgets import QApplication
import data_service
import ui_components

def test_narrative_engine():
    print("Testing Narrative Engine...")
    symbols = ['AAPL', 'TSLA', 'NVDA']
    for symbol in symbols:
        print(f"\nGenerating narrative for {symbol}:")
        tokens = data_service.generate_narrative(symbol)
        for token in tokens:
            print(f" - [{token['type']}] {token['content']} ({token['sentiment']})")
            
    print("\nTesting Opportunity Fetching:")
    profiles = ["DEFENSIVE", "BALANCED", "SPECULATIVE"]
    for profile in profiles:
        print(f"\nProfile: {profile}")
        opps = data_service.get_opportunities(profile)
        for opp in opps:
            print(f" - {opp['symbol']} ({opp['confidence']}%): {len(opp['narrative'])} tokens")

def test_ui_components():
    print("\nTesting UI Components...")
    app = QApplication.instance() or QApplication(sys.argv)
    
    try:
        print("Initializing MorningEspressoWidget...")
        espresso = ui_components.MorningEspressoWidget()
        print("Success.")
        
        print("Initializing RiskProfileSelector...")
        risk = ui_components.RiskProfileSelector()
        print("Success.")
        
        print("Initializing WhisperNumberWidget...")
        whisper = ui_components.WhisperNumberWidget()
        print("Success.")
        
        print("Initializing TalkingPointsView...")
        view = ui_components.TalkingPointsView()
        print("Success.")
        
        print("Simulating Risk Profile Change...")
        view.update_opportunities("SPECULATIVE")
        print("Success.")
        
    except Exception as e:
        print(f"UI Component Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_narrative_engine()
    test_ui_components()
    print("\nVerification Complete: All systems operational.")
