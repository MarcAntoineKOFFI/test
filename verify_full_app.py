import sys
import time
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
import main
import ui_components

def verify_app():
    print("Initializing Application...")
    app = QApplication(sys.argv)
    window = main.MainWindow()
    window.show()
    
    print("Testing Dashboard Load...")
    # Allow some time for initial data fetch
    app.processEvents()
    time.sleep(1)
    
    print("Testing Tab Switching...")
    # Switch to Detailed Analysis (Simulate clicking a ticker)
    print(" - Switching to Detailed Analysis...")
    window.show_detail("AAPL")
    app.processEvents()
    time.sleep(1)
    
    # Switch back to Dashboard
    print(" - Switching back to Dashboard...")
    window.show_dashboard()
    app.processEvents()
    time.sleep(1)
    
    # Switch to Talking Points
    print(" - Switching to Talking Points...")
    window.show_talking_points()
    app.processEvents()
    time.sleep(1)
    
    # Switch to Settings
    print(" - Switching to Settings...")
    window.show_settings()
    app.processEvents()
    time.sleep(1)
    
    print("Testing Data Refresh...")
    window.refresh_all_data()
    app.processEvents()
    
    print("Verification Complete: App ran without crashing.")
    sys.exit(0)

if __name__ == "__main__":
    verify_app()
