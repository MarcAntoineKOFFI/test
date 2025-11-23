import sys
from PySide6.QtWidgets import QApplication, QMainWindow
from ui_components import DetailedAnalysisView
import data_service

# Mock data for initial set_data call
mock_data = {
    'symbol': 'AAPL',
    'name': 'Apple Inc.',
    'price': 150.00,
    'change': 1.50,
    'change_percent': 1.00,
    'history': [], # Will be fetched by set_data
    'history_dates': []
}

def verify_charting():
    app = QApplication(sys.argv)
    
    window = QMainWindow()
    view = DetailedAnalysisView()
    window.setCentralWidget(view)
    window.resize(1200, 800)
    window.show()
    
    # Simulate data loading
    print("Setting data...")
    view.set_data(mock_data)
    print("Data set.")
    
    sys.exit(app.exec())

if __name__ == "__main__":
    verify_charting()
