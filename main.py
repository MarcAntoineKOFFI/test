import sys
import json
import os
import numpy as np
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                               QHBoxLayout, QLabel, QFrame, QLineEdit, QPushButton, 
                               QGridLayout, QScrollArea, QMessageBox, QStackedWidget, QSizePolicy)
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QIcon, QColor

# Matplotlib
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.pyplot as plt

import styles
import data_service
import ui_components

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TraderTale Equity Dashboard")
        self.setMinimumSize(1400, 900)
        self.setStyleSheet(styles.TRADER_THEME)
        
        # State
        self.watchlist_symbols = self.load_watchlist()
        
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
        
        # Add Master Surface to Main Layout with Margins
        self.main_layout.addWidget(self.master_surface)
        self.main_layout.setContentsMargins(0, 24, 24, 24) # Top, Left (0 because sidebar is there), Right, Bottom
        
        # Page 1: Dashboard
        self.dashboard_widget = QWidget()
        self.dashboard_layout = QVBoxLayout(self.dashboard_widget)
        self.dashboard_layout.setSpacing(32) # Increased spacing
        self.dashboard_layout.setContentsMargins(32, 32, 32, 32)
        self.setup_dashboard_ui()
        self.stack.addWidget(self.dashboard_widget)
        
        # Page 2: Detailed Analysis
        self.detail_view = ui_components.DetailedAnalysisView()
        self.detail_view.back_clicked.connect(self.show_dashboard)
        self.stack.addWidget(self.detail_view)

        # Page 3: Talking Points
        self.talking_points_view = ui_components.TalkingPointsView()
        self.talking_points_view.back_clicked.connect(self.show_dashboard)
        self.talking_points_view.ticker_selected.connect(self.show_detail)
        self.stack.addWidget(self.talking_points_view)
        
        # Page 4: Settings
        self.settings_view = ui_components.SettingsView()
        self.settings_view.risk_profile_changed.connect(self.on_risk_profile_changed)
        self.stack.addWidget(self.settings_view)
        
        self.current_risk_profile = "BALANCED"
        
        # Timer
        self.timer = QTimer()
        self.timer.timeout.connect(self.refresh_all_data)
        self.timer.start(60000) 
        
        # Initial Load
        QTimer.singleShot(100, self.refresh_all_data)

    def setup_sidebar(self):
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(280) # Slightly wider for floating look
        sidebar.setStyleSheet("background-color: transparent; border: none;") # Transparent Container
        
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(20, 40, 20, 40) # Ample padding
        layout.setSpacing(15)
        
        # Logo / Title Area
        title = QLabel("TRADER\nTALE")
        title.setStyleSheet(f"font-size: 24px; font-weight: 900; color: white; letter-spacing: 2px; padding-left: 15px;")
        layout.addWidget(title)
        
        layout.addSpacing(40) # Significant vertical padding
        
        # Menu Items (Pill Metaphor)
        buttons = ["Dashboard", "Talking Points", "Settings"]
        self.sidebar_btns = {}
        
        # Style for Sidebar Buttons
        btn_style = f"""
            QPushButton {{
                background-color: transparent;
                color: #6B7280;
                border: none;
                border-radius: 24px; /* 99px equivalent for height */
                text-align: left;
                padding: 12px 24px;
                font-weight: 600;
                font-size: 14px;
            }}
            QPushButton:hover {{
                color: white;
                background-color: rgba(255, 255, 255, 0.05);
            }}
            QPushButton:checked {{
                background-color: {styles.COLORS['sidebar_active_bg']};
                color: white;
                border: 1px solid {styles.COLORS['sidebar_active_accent']};
                /* Inner glow simulation via border or background */
            }}
        """
        
        for btn_text in buttons:
            btn = QPushButton(btn_text)
            btn.setObjectName("SidebarBtn")
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(48)
            btn.setStyleSheet(btn_style)
            
            if btn_text == "Talking Points":
                btn.clicked.connect(self.show_talking_points)
            elif btn_text == "Dashboard":
                btn.clicked.connect(self.show_dashboard)
            elif btn_text == "Settings":
                btn.clicked.connect(self.show_settings)
                
            layout.addWidget(btn)
            self.sidebar_btns[btn_text] = btn
            
        # Set default active
        self.sidebar_btns["Dashboard"].setChecked(True)
            
        layout.addStretch()
        
        # User Profile Stub
        user_label = QLabel("Marc Antoine")
        user_label.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; padding: 20px; font-weight: bold;")
        layout.addWidget(user_label)
        
        self.main_layout.addWidget(sidebar)

    def update_sidebar_state(self, active_text):
        for text, btn in self.sidebar_btns.items():
            btn.setChecked(text == active_text)

    def setup_dashboard_ui(self):
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
        self.grid_layout.setSpacing(20)
        self.dashboard_layout.addLayout(self.grid_layout)
        
        # Column 1: Market Overview & Watchlist
        col1 = QVBoxLayout()
        col1.setSpacing(20)
        
        self.indices_card = self.create_card("Market Indices", "marketIndices")
        col1.addWidget(self.indices_card)
        
        # Market News (New)
        self.market_news_card = ui_components.MarketNewsWidget()
        col1.addWidget(self.market_news_card)
        
        self.watchlist_card = self.create_watchlist_card()
        col1.addWidget(self.watchlist_card)
        
        self.grid_layout.addLayout(col1, 0, 0)
        
        # Column 2: Top Performers (Moved to Col 2 since Talking Points is gone)
        col2 = QVBoxLayout()
        col2.setSpacing(20)
        
        self.best_performers_card = self.create_card("Top Gainers", "bestPerformers")
        col2.addWidget(self.best_performers_card)
        
        self.worst_performers_card = self.create_card("Top Losers", "worstPerformers")
        col2.addWidget(self.worst_performers_card)
        
        self.grid_layout.addLayout(col2, 0, 1)
        
        # Column Stretches
        self.grid_layout.setColumnStretch(0, 1)
        self.grid_layout.setColumnStretch(1, 2) # Give more space to performers
        
        # Column Stretches


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
        self.clear_layout(self.indices_card.findChild(QVBoxLayout, "marketIndices_content"))
        layout = self.indices_card.findChild(QVBoxLayout, "marketIndices_content")
        
        indices = data_service.get_market_indices()
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

        for symbol in self.watchlist_symbols:
            data = data_service.fetch_stock_data(symbol)
            if data:
                card = ui_components.TickerCard(data)
                card.clicked.connect(lambda s=symbol: self.show_detail(s))
                self.watchlist_layout.addWidget(card)

    def refresh_performers(self):
        self.clear_layout(self.best_performers_card.findChild(QVBoxLayout, "bestPerformers_content"))
        self.clear_layout(self.worst_performers_card.findChild(QVBoxLayout, "worstPerformers_content"))
        
        gainers, losers = data_service.get_top_gainers_losers()
        
        best_layout = self.best_performers_card.findChild(QVBoxLayout, "bestPerformers_content")
        for data in gainers[:3]:
            card = ui_components.TickerCard(data)
            card.clicked.connect(lambda s=data['symbol']: self.show_detail(s))
            best_layout.addWidget(card)

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
        data = data_service.fetch_stock_data(symbol)
        if data:
            self.detail_view.set_data(data)
            self.stack.setCurrentIndex(1)
            # No sidebar update needed, or keep previous active

        
        self.grid_layout.addLayout(col1, 0, 0)
        
        # Column 2: Talking Points (Expanded)
        col2 = QVBoxLayout()
        col2.setSpacing(20)
        
        self.talking_points_card = self.create_card("Talking Points", "talkingPoints")
        col2.addWidget(self.talking_points_card)
        
        self.grid_layout.addLayout(col2, 0, 1)
        
        # Column 3: Top Performers
        col3 = QVBoxLayout()
        col3.setSpacing(20)
        
        self.best_performers_card = self.create_card("Top Gainers", "bestPerformers")
        col3.addWidget(self.best_performers_card)
        
        self.worst_performers_card = self.create_card("Top Losers", "worstPerformers")
        col3.addWidget(self.worst_performers_card)
        
        self.grid_layout.addLayout(col3, 0, 2)
        
        # Column Stretches
        self.grid_layout.setColumnStretch(0, 1)
        self.grid_layout.setColumnStretch(1, 1)
        self.grid_layout.setColumnStretch(2, 1)

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
        self.clear_layout(self.indices_card.findChild(QVBoxLayout, "marketIndices_content"))
        layout = self.indices_card.findChild(QVBoxLayout, "marketIndices_content")
        
        indices = data_service.get_market_indices()
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

        for symbol in self.watchlist_symbols:
            data = data_service.fetch_stock_data(symbol)
            if data:
                card = ui_components.TickerCard(data)
                card.clicked.connect(lambda s=symbol: self.show_detail(s))
                self.watchlist_layout.addWidget(card)

    def refresh_performers(self):
        self.clear_layout(self.best_performers_card.findChild(QVBoxLayout, "bestPerformers_content"))
        self.clear_layout(self.worst_performers_card.findChild(QVBoxLayout, "worstPerformers_content"))
        
        gainers, losers = data_service.get_top_gainers_losers()
        
        best_layout = self.best_performers_card.findChild(QVBoxLayout, "bestPerformers_content")
        for data in gainers[:3]:
            card = ui_components.TickerCard(data)
            card.clicked.connect(lambda s=data['symbol']: self.show_detail(s))
            best_layout.addWidget(card)

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
        data = data_service.fetch_stock_data(symbol)
        if data:
            self.detail_view.set_data(data)
            self.stack.setCurrentIndex(1)
            # No sidebar update needed, or keep previous active

    def show_talking_points(self):
        self.stack.setCurrentIndex(2)
        self.update_sidebar_state("Talking Points")
        
    def show_settings(self):
        self.stack.setCurrentWidget(self.settings_view)
        self.update_sidebar_state("Settings")

    def on_risk_profile_changed(self, profile):
        self.current_risk_profile = profile
        self.refresh_talking_points()
        
    def refresh_talking_points(self):
        # 1. Update Morning Espresso
        narrative_tokens = data_service.get_morning_espresso_narrative()
        self.talking_points_view.espresso.set_data(narrative_tokens)
        
        # 2. Update Opportunities based on Risk Profile
        # 2. Update Opportunities based on Risk Profile
        # The view handles fetching based on profile
        self.talking_points_view.refresh_opportunities(self.current_risk_profile)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
