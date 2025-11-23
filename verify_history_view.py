
import sys
import os
from PySide6.QtWidgets import QApplication

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

import ui_components

def test_history_view_instantiation():
    app = QApplication.instance() or QApplication(sys.argv)
    
    try:
        print("Attempting to instantiate IdeaHistoryView...")
        view = ui_components.IdeaHistoryView()
        print("PASS: IdeaHistoryView instantiated successfully.")
        
        # Test setting data
        history = [
            {
                "created_at": "2023-10-27T10:00:00",
                "symbol": "AAPL",
                "status": "OPEN",
                "trade_setup": {"entry": 150.0}
            }
        ]
        view.set_data(history)
        print("PASS: set_data called successfully.")
        
    except Exception as e:
        print(f"FAIL: Error instantiating IdeaHistoryView: {e}")
        sys.exit(1)

if __name__ == "__main__":
    test_history_view_instantiation()
