import sys
from PySide6.QtWidgets import QApplication
import ui_components
import main

def test_ui():
    app = QApplication(sys.argv)
    
    # Test DetailedAnalysisView
    print("Testing DetailedAnalysisView...")
    view = ui_components.DetailedAnalysisView()
    data = {
        'symbol': 'NVDA',
        'name': 'NVIDIA Corp',
        'price': 145.20,
        'change': 2.50,
        'change_percent': 1.75,
        'open': 143.00,
        'high': 146.00,
        'low': 142.50,
        'volume': 50000000,
        'history': [140, 142, 141, 144, 143, 145, 145.2]
    }
    view.set_data(data)
    print("DetailedAnalysisView initialized and data set.")
    
    # Test MainWindow (Dashboard)
    print("Testing MainWindow...")
    window = main.MainWindow()
    window.show()
    print("MainWindow initialized.")
    
    print("All tests passed!")
    # app.exec() # Don't block

if __name__ == "__main__":
    test_ui()
