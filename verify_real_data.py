import sys
from PySide6.QtWidgets import QApplication
import ui_components
import data_service
import main

def test_real_data():
    app = QApplication(sys.argv)
    
    print("Fetching real data for NVDA...")
    data = data_service.fetch_stock_data("NVDA")
    
    if not data:
        print("Failed to fetch data.")
        return

    print(f"Data fetched: {data['symbol']} Price: {data['price']}")
    print(f"History points: {len(data['history'])}")
    print(f"History dates: {len(data.get('history_dates', []))}")
    
    if 'history_dates' in data and len(data['history_dates']) > 0:
        print(f"First date: {data['history_dates'][0]}")
        print(f"Last date: {data['history_dates'][-1]}")
    else:
        print("No history dates found!")

    # Test DetailedAnalysisView with real data
    print("Initializing DetailedAnalysisView...")
    view = ui_components.DetailedAnalysisView()
    view.set_data(data)
    print("DetailedAnalysisView set_data successful.")
    
    # Test TickerCard with real data
    print("Initializing TickerCard...")
    card = ui_components.TickerCard(data)
    print("TickerCard initialized.")
    
    print("All tests passed!")

if __name__ == "__main__":
    test_real_data()
