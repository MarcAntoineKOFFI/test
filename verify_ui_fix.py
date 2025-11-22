import sys
from PySide6.QtWidgets import QApplication
from ui_components import NewsItemWidget
from datetime import datetime

def test_news_item_widget():
    app = QApplication(sys.argv)
    
    data = {
        'source': 'Test Source',
        'timestamp': datetime.now().isoformat(),
        'headline': 'Test Headline',
        'sentiment': 'BULLISH',
        'url': 'http://example.com'
    }
    
    try:
        widget = NewsItemWidget(data)
        print("SUCCESS: NewsItemWidget instantiated correctly.")
    except Exception as e:
        print(f"FAILURE: {e}")

if __name__ == "__main__":
    test_news_item_widget()
