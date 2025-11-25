import sys
import os
import json
import random
import time
from datetime import datetime
import pytz
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, 
                               QLabel, QFrame, QPushButton, QGridLayout, QScrollArea, QStackedWidget, QLineEdit)
from PySide6.QtCore import Qt, QTimer, QSize, QPropertyAnimation, QEasingCurve, QPoint, QRect, QThreadPool
from PySide6.QtGui import QColor, QPalette, QFont, QIcon, QPainter, QLinearGradient, QBrush, QPen

# Matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

import styles
import data_service
import ui_components
from async_utils import Worker, WorkerSignals

class SplashScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(600, 400)
        
        # Center on screen
        screen = QApplication.primaryScreen().availableGeometry()
        x = (screen.width() - self.width()) // 2
        y = (screen.height() - self.height()) // 2
        self.move(x, y)
        
        # Fake progress for animation
        self.progress = 0
        self.status_text = "Initializing Market Data..."
        self.start_time = time.time()
        
        # Force Arrow Cursor
        self.setCursor(Qt.ArrowCursor)
        
        # Animation Timer
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate_progress)
        self.timer.start(30) # 30ms update interval
        
    def animate_progress(self):
        # Increment progress slowly up to 90%
        if self.progress < 90:
            self.progress += 0.5
            self.update()
        
    def set_status(self, message):
        self.status_text = message
        # Jump progress slightly on status update
        self.progress = min(self.progress + 10, 95)
        self.update()
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background Gradient
        gradient = QLinearGradient(0, 0, 0, self.height())
        gradient.setColorAt(0, QColor("#202022"))
        gradient.setColorAt(1, QColor("#0a0a0a"))
        painter.setBrush(QBrush(gradient))
        
        # Border with Glow effect (simulated)
        painter.setPen(QPen(QColor(styles.COLORS['accent']), 2))
        painter.drawRoundedRect(1, 1, self.width()-2, self.height()-2, 15, 15)
        
        # Logo Text
        painter.setPen(QColor("white"))
        painter.setFont(QFont("Segoe UI", 36, QFont.Bold))
        painter.drawText(0, 80, self.width(), 60, Qt.AlignCenter, "TRADER")
        
        painter.setPen(QColor(styles.COLORS['accent']))
        painter.drawText(0, 130, self.width(), 60, Qt.AlignCenter, "TALE")
        
        # Loading Text
        painter.setPen(QColor(styles.COLORS['text_secondary']))
        painter.setFont(QFont("Segoe UI", 10))
        painter.drawText(0, 220, self.width(), 30, Qt.AlignCenter, self.status_text)
        
        # Progress Bar Background
        bar_w = 300
        bar_h = 4
        bar_x = (self.width() - bar_w) // 2
        bar_y = 260
        
        painter.setBrush(QColor(styles.COLORS['surface_light']))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(bar_x, bar_y, bar_w, bar_h, 2, 2)
        
        # Progress Bar Fill
        fill_w = int(bar_w * (self.progress / 100))
        painter.setBrush(QColor(styles.COLORS['accent']))
        painter.drawRoundedRect(bar_x, bar_y, fill_w, bar_h, 2, 2)

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TraderTale Equity Dashboard")
        self.setMinimumSize(1400, 900)
        self.setStyleSheet(styles.TRADER_THEME)
        
        # State
        self.watchlist_symbols = self.load_watchlist()
        self.current_risk_profile = "BALANCED"
        
        # Thread Pool for async operations
        self.threadpool = QThreadPool()
        
        # Main Layout (HBox: Sidebar + Content)
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QHBoxLayout(self.central_widget)
        self.main_layout.setSpacing(0)
        self.main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Sidebar (Floating Navigation Dock)
        self.setup_sidebar()
        
        # Master Surface Card (Content Wrapper)
        self.master_surface = QFrame()
        self.master_surface.setObjectName("MasterSurface")
        self.master_surface.setStyleSheet(f"""
            QFrame#MasterSurface {{
                background-color: {styles.COLORS['master_surface']};
                border-radius: 24px;
                border: 1px solid {styles.COLORS['surface_light']};
            }}
        """)
        
        # Apply Shadow Effect to Master Surface
        from PySide6.QtWidgets import QGraphicsDropShadowEffect
        shadow = QGraphicsDropShadowEffect(self.master_surface)
        shadow.setBlurRadius(40)
        shadow.setXOffset(0)
        shadow.setYOffset(0)
        shadow.setColor(QColor(0, 0, 0, 128))
        self.master_surface.setGraphicsEffect(shadow)
        
        # Layout for Master Surface
        surface_layout = QVBoxLayout(self.master_surface)
        surface_layout.setContentsMargins(0, 0, 0, 0) # Content fills the card
        surface_layout.setSpacing(0)

        # Content Area (Scrollable Right Pane)
        self.content_scroll = QScrollArea()
        self.content_scroll.setWidgetResizable(True)
        self.content_scroll.setStyleSheet("background: transparent; border: none;")
        self.content_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        
        # Stacked Widget inside Scroll Area
        self.stack = QStackedWidget()
        self.content_scroll.setWidget(self.stack)
        
        surface_layout.addWidget(self.content_scroll)
        
        # Add master surface to main layout (CRITICAL!)
        self.main_layout.addWidget(self.master_surface)
        
    def update_sidebar_state(self, active_text):
        for text, btn in self.sidebar_btns.items():
            btn.setChecked(text == active_text)

    def setup_dashboard_ui(self):
        # Create Dashboard Page
        self.dashboard_page = QWidget()
        self.dashboard_layout = QVBoxLayout(self.dashboard_page)
        self.dashboard_layout.setContentsMargins(20, 20, 20, 20)
        self.dashboard_layout.setSpacing(10)
        
        # Add to Stack
        self.stack.addWidget(self.dashboard_page)

        # Header
        header_layout = QHBoxLayout()
        title = QLabel("Command Center")
        title.setObjectName("HeaderTitle")
        self.last_update_label = QLabel("Last updated: --")
        self.last_update_label.setObjectName("LastUpdate")
        self.last_update_label.setStyleSheet(f"color: {styles.COLORS['text_secondary']};")
        header_layout.addWidget(title)
        header_layout.addStretch()
        header_layout.addWidget(self.last_update_label)
        self.dashboard_layout.addLayout(header_layout)
        
        # Grid
        self.grid_layout = QGridLayout()
        self.grid_layout.setSpacing(10)
        self.dashboard_layout.addLayout(self.grid_layout)
        
        # Column 1: Market Overview & Watchlist
        col1 = QVBoxLayout()
        col1.setSpacing(10)
        
        self.indices_card = self.create_card("Market Indices", "marketIndices")
        col1.addWidget(self.indices_card)
        
        self.watchlist_card = self.create_watchlist_card()
        col1.addWidget(self.watchlist_card)
        
        # Fix Layout: Indices compact, Watchlist expands
        col1.setStretch(0, 0)
        col1.setStretch(1, 1)
        
        self.grid_layout.addLayout(col1, 0, 0)
        
        # Column 2: Top Performers (Moved to Col 2 since Talking Points is gone)
        col2 = QVBoxLayout()
        col2.setSpacing(10)
        
        self.best_performers_card = self.create_card("Top Gainers", "bestPerformers")
        col2.addWidget(self.best_performers_card)
        
        self.worst_performers_card = self.create_card("Top Losers", "worstPerformers")
        col2.addWidget(self.worst_performers_card)
        
        self.grid_layout.addLayout(col2, 0, 1)
        
        # Column Stretches
        self.grid_layout.setColumnStretch(0, 1)
        self.grid_layout.setColumnStretch(1, 2) # Give more space to performers
        
    def create_card(self, title, object_name):
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        header = QLabel(title)
        header.setObjectName("SectionTitle")
        layout.addWidget(header)
        
        content_layout = QVBoxLayout()
        content_layout.setObjectName(f"{object_name}_content")
        layout.addLayout(content_layout)
        layout.addStretch()
        
        return card

    def create_watchlist_card(self):
        card = QFrame()
        card.setObjectName("Card")
        layout = QVBoxLayout(card)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        header_layout = QHBoxLayout()
        title = QLabel("WATCHLIST")
        title.setObjectName("SectionTitle")
        header_layout.addWidget(title)
        header_layout.addStretch()
        
        self.stock_input = QLineEdit()
        self.stock_input.setPlaceholderText("+ Add Symbol")
        self.stock_input.setFixedWidth(100)
        self.stock_input.returnPressed.connect(self.add_to_watchlist)
        header_layout.addWidget(self.stock_input)
        
        layout.addLayout(header_layout)
        
        # No internal scroll needed if main page scrolls, but keeping it for list management
        # Actually, if main page scrolls, internal scrolls can be annoying. 
        # Let's make it a simple layout for now, or keep scroll if list is long.
        # Keeping scroll for watchlist specifically as it can get very long.
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        
        self.watchlist_container = QWidget()
        self.watchlist_layout = QVBoxLayout(self.watchlist_container)
        self.watchlist_layout.setSpacing(10)
        self.watchlist_layout.setContentsMargins(0, 0, 0, 0)
        scroll.setWidget(self.watchlist_container)
        
        layout.addWidget(scroll)
        
        return card

    def refresh_all_data(self):
        self.refresh_indices()
        self.refresh_watchlist()
        self.refresh_performers()
        self.update_last_update_time()

    def refresh_indices(self):
        worker = Worker(data_service.get_market_indices)
        worker.signals.result.connect(self.update_indices_ui)
        self.threadpool.start(worker)

    def update_indices_ui(self, indices):
        self.clear_layout(self.indices_card.findChild(QVBoxLayout, "marketIndices_content"))
        layout = self.indices_card.findChild(QVBoxLayout, "marketIndices_content")
        for data in indices:
            card = ui_components.TickerCard(data)
            card.clicked.connect(lambda s=data['symbol']: self.show_detail(s))
            layout.addWidget(card)

    def refresh_watchlist(self):
        self.clear_layout(self.watchlist_layout)
        if not self.watchlist_symbols:
            empty_label = QLabel("No stocks tracked.")
            empty_label.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-style: italic;")
            empty_label.setAlignment(Qt.AlignCenter)
            self.watchlist_layout.addWidget(empty_label)
            return

        self.watchlist_queue = list(self.watchlist_symbols)
        self.process_watchlist_batch()

    def process_watchlist_batch(self):
        if not self.watchlist_queue:
            return
            
        batch_size = 3
        batch = self.watchlist_queue[:batch_size]
        self.watchlist_queue = self.watchlist_queue[batch_size:]
        
        worker = Worker(self.fetch_watchlist_batch_data, batch)
        worker.signals.result.connect(self.update_watchlist_batch_ui)
        self.threadpool.start(worker)

    def fetch_watchlist_batch_data(self, symbols):
        results = []
        for symbol in symbols:
            data = data_service.fetch_stock_data(symbol)
            if data:
                results.append(data)
        return results

    def update_watchlist_batch_ui(self, data_list):
        for data in data_list:
            card = ui_components.TickerCard(data)
            card.clicked.connect(lambda s=data['symbol']: self.show_detail(s))
            self.watchlist_layout.addWidget(card)
        
        # Continue with next batch
        if self.watchlist_queue:
            QTimer.singleShot(100, self.process_watchlist_batch)

    def refresh_performers(self):
        worker = Worker(data_service.get_top_gainers_losers)
        worker.signals.result.connect(self.update_performers_ui)
        self.threadpool.start(worker)

    def update_performers_ui(self, data_tuple):
        gainers, losers = data_tuple
        
        self.clear_layout(self.best_performers_card.findChild(QVBoxLayout, "bestPerformers_content"))
        best_layout = self.best_performers_card.findChild(QVBoxLayout, "bestPerformers_content")
        for data in gainers[:3]:
            card = ui_components.TickerCard(data)
            card.clicked.connect(lambda s=data['symbol']: self.show_detail(s))
            best_layout.addWidget(card)
            
        self.clear_layout(self.worst_performers_card.findChild(QVBoxLayout, "worstPerformers_content"))
        worst_layout = self.worst_performers_card.findChild(QVBoxLayout, "worstPerformers_content")
        for data in losers[:3]:
            card = ui_components.TickerCard(data)
            card.clicked.connect(lambda s=data['symbol']: self.show_detail(s))
            worst_layout.addWidget(card)

    def update_last_update_time(self):
        from datetime import datetime
        now = datetime.now().strftime("%H:%M:%S")
        self.last_update_label.setText(f"UPDATED: {now}")

    def add_to_watchlist(self):
        symbol = self.stock_input.text().strip().upper()
        if symbol and symbol not in self.watchlist_symbols:
            self.watchlist_symbols.append(symbol)
            self.save_watchlist()
            self.stock_input.clear()
            self.refresh_watchlist()

    def load_watchlist(self):
        try:
            if os.path.exists("watchlist.json"):
                with open("watchlist.json", "r") as f:
                    return json.load(f)
        except:
            pass
        return ["AAPL", "TSLA", "NVDA", "AMD"]

    def save_watchlist(self):
        with open("watchlist.json", "w") as f:
            json.dump(self.watchlist_symbols, f)

    def clear_layout(self, layout):
        if layout is not None:
            while layout.count():
                item = layout.takeAt(0)
                widget = item.widget()
                if widget is not None:
                    widget.deleteLater()

    def show_dashboard(self):
        self.stack.setCurrentIndex(0)
        self.update_sidebar_state("Dashboard")

    def show_detail(self, symbol):
        self.stack.setCurrentWidget(self.detail_view)
        self.update_sidebar_state("Watchlist") # Or keep current
        # Fetch data for detail view
        worker = Worker(data_service.fetch_stock_data, symbol)
        worker.signals.result.connect(self.detail_view.set_data)
        self.threadpool.start(worker)

    def show_sector(self, sector_name):
        self.stack.setCurrentWidget(self.sector_view)
        # Fetch sector data
        worker = Worker(self._fetch_sector_data, sector_name)
        worker.signals.result.connect(lambda data: self.sector_view.set_data(data[0], data[1]))
        self.threadpool.start(worker)
        
    def _fetch_sector_data(self, sector_name, progress_callback=None):
        sector_data = data_service.get_sector_data(sector_name)
        top_performers = data_service.get_sector_top_performers(sector_name)
        return sector_data, top_performers

    def show_talking_points(self):
        self.stack.setCurrentWidget(self.talking_points_view)
        self.update_sidebar_state("Talking Points")
        self.refresh_talking_points()

    def show_settings(self):
        self.stack.setCurrentWidget(self.settings_view)
        self.update_sidebar_state("Settings")

    def on_risk_profile_changed(self, profile):
        self.current_risk_profile = profile
        # Update Talking Points with new profile
        if hasattr(self.talking_points_view, 'refresh_opportunities'):
            self.talking_points_view.refresh_opportunities(profile)

    def refresh_talking_points(self):
        # Fetch narrative and opportunities
        # 1. Update Morning Espresso
        narrative_tokens = data_service.get_morning_espresso_narrative()
        if hasattr(self.talking_points_view, 'espresso'):
            self.talking_points_view.espresso.set_data(narrative_tokens)
        
        # 2. Update Opportunities based on Risk Profile
        if hasattr(self.talking_points_view, 'refresh_opportunities'):
            self.talking_points_view.refresh_opportunities(self.current_risk_profile)

    def setup_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        sidebar.setStyleSheet(f"""
            QFrame#Sidebar {{
                background-color: {styles.COLORS['surface']};
                border-right: 1px solid {styles.COLORS['surface_light']};
            }}
        """)
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(20, 30, 20, 30)
        layout.setSpacing(15)
        
        # Clock and Market Status
        est = pytz.timezone('US/Eastern')
        now_est = datetime.now(est)
        
        # NY Time (Primary)
        clock_label = QLabel(now_est.strftime("%H:%M"))
        clock_label.setAlignment(Qt.AlignCenter)
        clock_label.setStyleSheet(f"color: {styles.COLORS['text_primary']}; font-size: 24px; font-weight: bold; font-family: 'Consolas';")
        layout.addWidget(clock_label)
        
        # Label
        est_label = QLabel("NEW YORK")
        est_label.setAlignment(Qt.AlignCenter)
        est_label.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        layout.addWidget(est_label)
        
        # Market Status
        hour = now_est.hour
        minute = now_est.minute
        # Market hours: 9:30 - 16:00 EST
        market_minutes = hour * 60 + minute
        open_minutes = 9 * 60 + 30
        close_minutes = 16 * 60
        
        is_open = open_minutes <= market_minutes < close_minutes and now_est.weekday() < 5
        
        if is_open:
            status_text = "OPEN UNTIL 16:00"
            status_color = styles.COLORS['success']
        else:
            status_text = "OPEN AT 09:30"
            status_color = styles.COLORS['danger']
        
        status_label = QLabel(status_text)
        status_label.setAlignment(Qt.AlignCenter)
        status_label.setStyleSheet(f"color: {status_color}; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
        layout.addWidget(status_label)
        
        layout.addSpacing(20)
        
        # Navigation Buttons
        self.sidebar_btns = {}
        # Removed Watchlist as per user request
        nav_items = [("Dashboard", "Dashboard"), ("Talking Points", "Talking Points"), ("Settings", "Settings")]
        
        for text, key in nav_items:
            btn = QPushButton(text)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(40)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: transparent;
                    color: {styles.COLORS['text_secondary']};
                    border: none;
                    border-radius: 8px;
                    text-align: left;
                    padding-left: 15px;
                    font-weight: bold;
                    font-size: 14px;
                }}
                QPushButton:checked {{
                    background-color: {styles.COLORS['surface_light']};
                    color: {styles.COLORS['text_primary']};
                    border-left: 3px solid {styles.COLORS['accent']};
                }}
                QPushButton:hover {{
                    background-color: {styles.COLORS['surface_light']}80;
                    color: {styles.COLORS['text_primary']};
                }}
            """)
            
            if key == "Dashboard":
                btn.clicked.connect(self.show_dashboard)
            elif key == "Talking Points":
                btn.clicked.connect(self.show_talking_points)
            elif key == "Watchlist":
                btn.clicked.connect(self.show_dashboard) 
            elif key == "Settings":
                btn.clicked.connect(self.show_settings)
                
            layout.addWidget(btn)
            self.sidebar_btns[key] = btn
            
        layout.addStretch()
        
        # User Profile / Logo
        profile_btn = QPushButton("TR") # Initials
        profile_btn.setFixedSize(40, 40)
        profile_btn.setStyleSheet(f"""
            background-color: {styles.COLORS['surface_light']};
            color: white;
            border-radius: 20px;
            font-weight: bold;
        """)
        layout.addWidget(profile_btn, alignment=Qt.AlignCenter)
        
        self.main_layout.addWidget(sidebar)

    def setup_ui_deferred(self, splash):
        self.setup_dashboard_ui()
        
        self.detail_view = ui_components.DetailedAnalysisView()
        self.stack.addWidget(self.detail_view)
        
        self.talking_points_view = ui_components.TalkingPointsView()
        if hasattr(self.talking_points_view, 'ticker_selected'):
            self.talking_points_view.ticker_selected.connect(self.show_detail)
        if hasattr(self.talking_points_view, 'sectorClicked'):
            self.talking_points_view.sectorClicked.connect(self.show_sector)
        self.stack.addWidget(self.talking_points_view)
        
        self.sector_view = ui_components.SectorView()
        self.sector_view.back_clicked.connect(self.show_talking_points)
        self.stack.addWidget(self.sector_view)
        
        self.settings_view = ui_components.SettingsView()
        if hasattr(self.settings_view, 'profile_changed'):
            self.settings_view.profile_changed.connect(self.on_risk_profile_changed)
        self.stack.addWidget(self.settings_view)
        
        # Start Pre-fetching Data (Warm up cache)
        worker = Worker(self.pre_fetch_data)
        if splash:
            worker.signals.progress.connect(splash.set_status)
        worker.signals.result.connect(lambda: self.finalize_startup(splash))
        self.threadpool.start(worker)

    def pre_fetch_data(self, progress_callback):
        """Fetches heavy data in background to warm up cache."""
        progress_callback.emit("Analyzing Market Data (Top Gainers)...")
        try:
            data_service.get_top_gainers_losers()
        except Exception:
            pass
        
        progress_callback.emit("Scanning Opportunities (Talking Points)...")
        try:
            data_service.get_opportunities()
        except Exception:
            pass
        
        progress_callback.emit("Finalizing...")
        return True

    def finalize_startup(self, splash):
        """Called when pre-fetching is done."""
        # Don't call refresh_all_data here - it may crash or hang
        # We'll do it after the main window is visible
        
        # Ensure splash screen shows for at least 2 seconds
        elapsed = time.time() - splash.start_time
        delay = 0
        if elapsed < 2.0:
            delay = int((2.0 - elapsed) * 1000)
            
        QTimer.singleShot(delay, lambda: self._show_main_window(splash))
        
    def _show_main_window(self, splash):
        self.show()
        self.update_sidebar_state("Dashboard")
        
        if splash:
            splash.close()
            
        # Now refresh data after window is visible
        QTimer.singleShot(100, self.refresh_all_data)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Splash Screen
    splash = SplashScreen()
    splash.show()
    app.processEvents()
    
    # Create Window (Hidden initially)
    window = MainWindow()
    
    # Start Deferred Loading
    QTimer.singleShot(0, lambda: window.setup_ui_deferred(splash))
    
    sys.exit(app.exec())
