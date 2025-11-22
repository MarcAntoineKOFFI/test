import sys
from PySide6.QtWidgets import QApplication
from ui_components import DetailedAnalysisView

def test_detailed_view():
    app = QApplication(sys.argv)
    
    view = DetailedAnalysisView()
    
    # Mock Data
    data = {
        'symbol': 'AAPL',
        'name': 'Apple Inc.',
        'price': 150.00,
        'change': 1.50,
        'change_percent': 1.0,
        'open': 148.00,
        'high': 151.00,
        'low': 148.00,
        'volume': 50000000,
        'mkt_cap': 2500000000000,
        'history': [148, 149, 150, 151, 150],
        'history_dates': ['2023-01-01', '2023-01-02', '2023-01-03', '2023-01-04', '2023-01-05']
    }
    
    try:
        view.set_data(data)
        print("SUCCESS: DetailedAnalysisView.set_data executed correctly.")
    except Exception as e:
        print(f"FAILURE: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_detailed_view()
