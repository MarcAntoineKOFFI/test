import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
import ui_components
import data_service

def verify_deep_linking():
    app = QApplication(sys.argv)
    
    # 1. Create MorningEspressoWidget
    widget = ui_components.MorningEspressoWidget()
    widget.show()
    
    # 2. Set Data with Tickers and Common Words
    narrative = [
        {"type": "CONTEXT", "content": "Market is OPEN."},
        {"type": "CATALYST", "content": "NVDA is up more THAN expected."},
        {"type": "ACTION", "content": "Buy TSLA."}
    ]
    widget.set_data(narrative)
    
    # 3. Verify HTML Content
    html_content = widget.content_label.text()
    print(f"Content HTML: {html_content}")
    
    if "href='ticker:NVDA'" in html_content:
        print("PASS: NVDA link found.")
    else:
        print("FAIL: NVDA link NOT found.")
        
    if "href='ticker:TSLA'" in html_content:
        print("PASS: TSLA link found.")
    else:
        print("FAIL: TSLA link NOT found.")
        
    if "href='ticker:OPEN'" not in html_content:
        print("PASS: OPEN link correctly ignored.")
    else:
        print("FAIL: OPEN link incorrectly found.")
        
    if "href='ticker:THAN'" not in html_content:
        print("PASS: THAN link correctly ignored.")
    else:
        print("FAIL: THAN link incorrectly found.")
        
    # 4. Verify Signal
    def on_ticker_clicked(ticker):
        print(f"SIGNAL RECEIVED: Ticker {ticker} clicked.")
        app.quit()
        
    widget.ticker_clicked.connect(on_ticker_clicked)
    
    # 5. Simulate Click (Hard to simulate QLinkActivated event programmatically without mouse, 
    # but we can emit the signal manually to test the chain if we wanted, 
    # or just trust the linkActivated connection if HTML is correct).
    # We will manually trigger the handler to ensure logic works.
    print("Simulating click on 'ticker:NVDA'...")
    widget.handle_link("ticker:NVDA")
    
    # Timeout
    QTimer.singleShot(2000, app.quit)
    
    app.exec()

if __name__ == "__main__":
    verify_deep_linking()
