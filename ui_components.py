import random
from PySide6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QLabel, QFrame, 
                               QPushButton, QGridLayout, QSizePolicy, QStackedWidget, QScrollArea,
                               QCheckBox, QSlider, QLineEdit, QButtonGroup, QGraphicsDropShadowEffect)
from PySide6.QtCore import Qt, Signal, QSize, QUrl, QByteArray, QTimer, QDateTime
from PySide6.QtGui import QPainter, QColor, QPen, QBrush, QLinearGradient, QFont, QPixmap, QPainterPath
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

import styles
import data_service

# --- Ticker to Domain Mapping ---
TICKER_TO_DOMAIN = {
    'AAPL': 'apple.com', 'MSFT': 'microsoft.com', 'GOOGL': 'abc.xyz', 'AMZN': 'amazon.com',
    'NVDA': 'nvidia.com', 'TSLA': 'tesla.com', 'META': 'meta.com', 'BRK-B': 'berkshirehathaway.com',
    'V': 'visa.com', 'JNJ': 'jnj.com', 'WMT': 'walmart.com', 'JPM': 'jpmorganchase.com',
    'MA': 'mastercard.com', 'PG': 'pg.com', 'UNH': 'unitedhealthgroup.com', 'DIS': 'disney.com',
    'HD': 'homedepot.com', 'BAC': 'bankofamerica.com', 'NFLX': 'netflix.com', 'ADBE': 'adobe.com',
    'CRM': 'salesforce.com', 'INTC': 'intel.com', 'AMD': 'amd.com', 'PYPL': 'paypal.com',
    'CSCO': 'cisco.com', 'PFE': 'pfizer.com', '^GSPC': 'spglobal.com', '^IXIC': 'nasdaq.com',
    '^DJI': 'dowjones.com'
}

class LogoWidget(QWidget):
    def __init__(self, symbol, size=50, parent=None):
        super().__init__(parent)
        self.symbol = symbol
        self.setFixedSize(size, size)
        self.pixmap = None
        self.manager = QNetworkAccessManager(self)
        self.manager.finished.connect(self.on_reply)
        
        # Initial fetch
        self.fetch_logo()

    def fetch_logo(self):
        domain = TICKER_TO_DOMAIN.get(self.symbol)
        if domain:
            url = f"https://unavatar.io/{domain}?fallback=false"
            request = QNetworkRequest(QUrl(url))
            self.manager.get(request)
        else:
            # No domain mapping, stay with fallback
            pass

    def on_reply(self, reply):
        if reply.error() == QNetworkReply.NetworkError.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            if pixmap.loadFromData(data):
                self.pixmap = pixmap
                self.update()
        reply.deleteLater()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Background Container (White for transparency safety or fallback gradient)
        rect = self.rect()
        
        if self.pixmap:
            # Draw White Container for Logo Safety
            painter.setBrush(QColor("white"))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect, 12, 12)
            
            # Draw Logo (Scaled)
            # Margins to keep it looking nice
            margin = 4
            target_rect = rect.adjusted(margin, margin, -margin, -margin)
            scaled = self.pixmap.scaled(target_rect.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            
            # Center it
            x = target_rect.x() + (target_rect.width() - scaled.width()) / 2
            y = target_rect.y() + (target_rect.height() - scaled.height()) / 2
            
            painter.drawPixmap(int(x), int(y), scaled)
            
        else:
            # Fallback: Graphical Icon Tile
            hash_val = sum(ord(c) for c in self.symbol)
            hue = (hash_val * 137.508) % 360
            bg_color = QColor.fromHsl(int(hue), 200, 100)
            
            gradient = QLinearGradient(0, 0, rect.width(), rect.height())
            gradient.setColorAt(0, bg_color.lighter(130))
            gradient.setColorAt(1, bg_color)
            
            painter.setBrush(QBrush(gradient))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(rect, 12, 12)
            
            # Text (Initials)
            painter.setPen(QColor("white"))
            font_size = int(rect.height() * 0.4)
            font = QFont("Arial", font_size, QFont.Bold)
            painter.setFont(font)
            painter.drawText(rect, Qt.AlignCenter, self.symbol[:1])

class SparklineWidget(QWidget):
    def __init__(self, data, rvol=1.0, parent=None):
        super().__init__(parent)
        self.data = data
        self.rvol = rvol
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumHeight(40)
        
        # Animation State
        self._progress = 0.0
        self._pulse_radius = 4.0
        self._pulse_growing = True
        
        # Progressive Draw Animation
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.animate_progress)
        self.timer.start(16) # ~60 FPS
        
        # Pulse Animation
        self.pulse_timer = QTimer(self)
        self.pulse_timer.timeout.connect(self.animate_pulse)
        self.pulse_timer.start(50)

    def animate_progress(self):
        if self._progress < 1.0:
            self._progress += 0.02 # 800ms duration approx (50 frames)
            self.update()
        else:
            self.timer.stop()

    def animate_pulse(self):
        if self._pulse_growing:
            self._pulse_radius += 0.2
            if self._pulse_radius >= 8.0:
                self._pulse_growing = False
        else:
            self._pulse_radius -= 0.2
            if self._pulse_radius <= 4.0:
                self._pulse_growing = True
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        if not self.data or len(self.data) < 2:
            return

        width = self.width()
        height = self.height()
        
        # Determine Color
        is_positive = self.data[-1] >= self.data[0]
        color_hex = styles.COLORS["success"] if is_positive else styles.COLORS["danger"]
        base_color = QColor(color_hex)
        
        # Scales
        min_val = min(self.data)
        max_val = max(self.data)
        val_range = max_val - min_val if max_val != min_val else 1
        
        # Calculate Points
        chart_width = width - 15
        step_x = chart_width / (len(self.data) - 1)
        
        points = []
        for i, val in enumerate(self.data):
            x = i * step_x
            y = height - ((val - min_val) / val_range * (height - 10)) - 5
            points.append((x, y))
            
        # Progressive Draw Limit
        num_points_to_draw = int(len(points) * self._progress)
        if num_points_to_draw < 2:
            return
            
        current_points = points[:num_points_to_draw]
        
        # 1. Create Path with Smooth Curves (Cubic Bezier)
        path = QPainterPath()
        path.moveTo(current_points[0][0], current_points[0][1])
        
        for i in range(len(current_points) - 1):
            p1 = current_points[i]
            p2 = current_points[i+1]
            
            # Control points for smooth curve
            c1_x = p1[0] + (p2[0] - p1[0]) * 0.5
            c1_y = p1[1]
            c2_x = p1[0] + (p2[0] - p1[0]) * 0.5
            c2_y = p2[1]
            
            path.cubicTo(c1_x, c1_y, c2_x, c2_y, p2[0], p2[1])
            
        # 2. Draw Gradient Fill (Luma Fade)
        # Close the path for filling
        fill_path = QPainterPath(path)
        fill_path.lineTo(current_points[-1][0], height)
        fill_path.lineTo(current_points[0][0], height)
        fill_path.closeSubpath()
        
        # 2. Draw Gradient Fill (Luma Fade: 40% -> 0%)
        # Close the path for filling
        fill_path = QPainterPath(path)
        fill_path.lineTo(current_points[-1][0], height)
        fill_path.lineTo(current_points[0][0], height)
        fill_path.closeSubpath()
        
        gradient = QLinearGradient(0, 0, 0, height)
        gradient.setColorAt(0, QColor(base_color.red(), base_color.green(), base_color.blue(), 102)) # 40% opacity
        gradient.setColorAt(1.0, QColor(base_color.red(), base_color.green(), base_color.blue(), 0)) # 0% opacity
        
        painter.setBrush(QBrush(gradient))
        painter.setPen(Qt.NoPen)
        painter.drawPath(fill_path)
        
        # 3. Draw Line (Neon Stroke)
        pen = QPen(base_color, 2)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        painter.setPen(pen)
        painter.setBrush(Qt.NoBrush)
        painter.drawPath(path)
            
        # 3. Pulse Effect (Last Point)
        if self._progress >= 1.0:
            last_x, last_y = points[-1]
            
            # Glow
            painter.setBrush(Qt.NoBrush)
            glow_pen = QPen(base_color, 2)
            glow_color = QColor(base_color)
            glow_color.setAlpha(100)
            glow_pen.setColor(glow_color)
            painter.setPen(glow_pen)
            painter.drawEllipse(int(last_x - self._pulse_radius), int(last_y - self._pulse_radius), 
                                int(self._pulse_radius * 2), int(self._pulse_radius * 2))
            
            # Dot
            painter.setBrush(base_color)
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(last_x - 3), int(last_y - 3), 6, 6)

        # RVOL Indicator
        rvol_rect = [width - 8, height/2 - 10, 4, 20]
        painter.setPen(Qt.NoPen)
        
        pill_color = QColor(styles.COLORS["surface_light"])
        if self.rvol > 1.5:
             pill_color = QColor(styles.COLORS["neon_purple"])
             painter.setBrush(QColor(styles.COLORS["neon_purple"] + "40"))
             painter.drawRoundedRect(width - 10, height/2 - 12, 8, 24, 4, 4)
             
        painter.setBrush(pill_color)
        painter.drawRoundedRect(width - 8, height/2 - 10, 4, 20, 2, 2)

class DetailedChartWidget(SparklineWidget):
    def __init__(self, data, parent=None):
        super().__init__(data, rvol=0, parent=parent)
        self.setMinimumHeight(300)
        self.setMouseTracking(True)
        self.cursor_pos = None
        
    def resizeEvent(self, event):
        super().resizeEvent(event)
        
    def mouseMoveEvent(self, event):
        self.cursor_pos = event.pos()
        self.update()
        super().mouseMoveEvent(event)
        
    def leaveEvent(self, event):
        self.cursor_pos = None
        self.update()
        super().leaveEvent(event)
        
    def paintEvent(self, event):
        super().paintEvent(event)
        
        if not self.data or len(self.data) < 2:
            return
            
        # Re-calculate points (duplicated logic, ideally refactor to shared method, but keeping simple for now)
        width = self.width()
        height = self.height()
        min_val = min(self.data)
        max_val = max(self.data)
        val_range = max_val - min_val if max_val != min_val else 1
        chart_width = width - 15
        step_x = chart_width / (len(self.data) - 1)
        
        points = []
        for i, val in enumerate(self.data):
            x = i * step_x
            y = height - ((val - min_val) / val_range * (height - 10)) - 5
            points.append((x, y))
            
        if self.cursor_pos:
            # Find nearest point
            mouse_x = self.cursor_pos.x()
            nearest_idx = min(range(len(points)), key=lambda i: abs(points[i][0] - mouse_x))
            nx, ny = points[nearest_idx]
            
            painter = QPainter(self)
            painter.setRenderHint(QPainter.Antialiasing)
            
            # Phantom Grid (Dashed, 0.1 opacity)
            grid_pen = QPen(QColor(255, 255, 255, 25), 1, Qt.DashLine) # ~10% opacity
            painter.setPen(grid_pen)
            # Draw some horizontal grid lines
            for i in range(1, 5):
                y = i * (height / 5)
                painter.drawLine(0, int(y), width, int(y))
            
            # Floating Axis Labels (Monospace, Muted)
            painter.setPen(QColor(styles.COLORS['text_secondary']))
            painter.setFont(QFont("Consolas", 8))
            
            # Y-Axis (Price) - Draw labels on the right side
            # Calculate nice steps
            y_steps = 5
            y_step_val = val_range / y_steps
            for i in range(y_steps + 1):
                val = min_val + (i * y_step_val)
                y_pos = height - ((val - min_val) / val_range * (height - 40)) - 20
                painter.drawText(width - 50, int(y_pos) + 4, f"${val:.2f}")
            
            # X-Axis (Date) - Draw labels at the bottom
            # Mock dates for now, assuming last 30 days
            end_date = QDateTime.currentDateTime()
            x_steps = 5
            x_step_px = chart_width / x_steps
            for i in range(x_steps + 1):
                x_pos = i * x_step_px
                # Calculate date: end_date - (total_width - x_pos) mapped to days
                # Simplified: just map index to date
                days_ago = int((1 - (i / x_steps)) * 30) # Mock 30 day window
                date_str = end_date.addDays(-days_ago).toString("MMM dd")
                painter.drawText(int(x_pos), height - 5, date_str)

            # 1. Crosshairs (Dashed, Glow)
            pen = QPen(QColor("white"), 1, Qt.DashLine)
            painter.setPen(pen)
            painter.drawLine(int(nx), 0, int(nx), height - 20) # Vertical, stop at x-axis
            painter.drawLine(0, int(ny), width - 50, int(ny))  # Horizontal, stop at y-axis
            
            # 2. Halo Marker
            painter.setBrush(Qt.NoBrush)
            halo_pen = QPen(QColor("white"), 2)
            painter.setPen(halo_pen)
            painter.drawEllipse(int(nx - 6), int(ny - 6), 12, 12)
            
            painter.setBrush(QColor("white"))
            painter.setPen(Qt.NoPen)
            painter.drawEllipse(int(nx - 3), int(ny - 3), 6, 6)
            
            # 3. Tooltip (OHLC Style)
            # Determine color based on price change from open (first point)
            price = self.data[nearest_idx]
            start_price = self.data[0]
            is_up = price >= start_price
            border_color = styles.COLORS["accent"] if is_up else styles.COLORS["danger"]
            
            # Mock OHLC Data (since we only have close prices in self.data)
            # In a real app, we'd look up the full OHLC record.
            # For now, we simulate a small range around the close price.
            open_p = price * 0.998
            high_p = price * 1.005
            low_p = price * 0.995
            close_p = price
            
            # Dynamic Date Calculation
            # Map nearest_idx to a date. Assuming data is daily and ends today.
            days_from_end = len(self.data) - 1 - nearest_idx
            current_date = QDateTime.currentDateTime().addDays(-days_from_end)
            
            tooltip_lines = [
                f"DATE:  {current_date.toString('MMM dd, yyyy')}", 
                f"OPEN:  ${open_p:.2f}",
                f"HIGH:  ${high_p:.2f}",
                f"LOW:   ${low_p:.2f}",
                f"CLOSE: ${close_p:.2f}"
            ]
            
            # Draw Tooltip Box
            rect_w, rect_h = 160, 100
            rect_x = nx + 15 if nx + 15 + rect_w < width else nx - 15 - rect_w
            rect_y = ny - 50 if ny - 50 > 0 else ny + 20
            # Ensure y stays within bounds
            if rect_y + rect_h > height: rect_y = height - rect_h - 10
            if rect_y < 0: rect_y = 10
            
            painter.setBrush(QColor("#1E1E20"))
            painter.setPen(QPen(QColor(border_color), 1))
            painter.drawRoundedRect(int(rect_x), int(rect_y), rect_w, rect_h, 6, 6)
            
            # Text
            painter.setPen(QColor("white"))
            painter.setFont(QFont("Consolas", 9, QFont.Bold))
            
            y_offset = rect_y + 20
            for line in tooltip_lines:
                painter.drawText(int(rect_x) + 10, int(y_offset), line)
                y_offset += 16

class TickerCard(QFrame):
    clicked = Signal(str)

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self.symbol = data['symbol']
        self.setObjectName("Card")
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedHeight(80)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(15, 10, 15, 10)
        layout.setSpacing(15)
        
        self.logo = LogoWidget(self.symbol, size=50)
        layout.addWidget(self.logo)
        
        text_layout = QVBoxLayout()
        text_layout.setSpacing(2)
        
        ticker_label = QLabel(self.symbol)
        ticker_label.setStyleSheet("color: white; font-weight: bold; font-size: 14px; border: none; background: transparent;")
        text_layout.addWidget(ticker_label)
        
        name_label = QLabel(data['name'])
        name_label.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-size: 11px; border: none; background: transparent;")
        name_label.setWordWrap(False)
        font_metrics = name_label.fontMetrics()
        elided_name = font_metrics.elidedText(data['name'], Qt.ElideRight, 150)
        name_label.setText(elided_name)
        
        text_layout.addWidget(name_label)
        layout.addLayout(text_layout)
        
        layout.addStretch(1)
        
        self.sparkline = SparklineWidget(data.get('history', []), rvol=data.get('rvol', 1.0))
        layout.addWidget(self.sparkline, 2)

    def mousePressEvent(self, event):
        self.clicked.emit(self.symbol)
        super().mousePressEvent(event)

class DetailedAnalysisView(QWidget):
    back_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(20)
        
        # Header
        header = QHBoxLayout()
        self.back_btn = QPushButton("← BACK")
        self.back_btn.setObjectName("IconBtn")
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.clicked.connect(self.back_clicked.emit)
        self.back_btn.setFixedWidth(80)
        header.addWidget(self.back_btn)
        header.addStretch()
        self.layout.addLayout(header)
        
        # Main Card
        self.card = QFrame()
        self.card.setObjectName("Card")
        self.card.setStyleSheet(f"background-color: {styles.COLORS['surface']}; border-radius: 16px; border: 1px solid {styles.COLORS['surface_light']};")
        card_layout = QVBoxLayout(self.card)
        card_layout.setContentsMargins(40, 40, 40, 40)
        card_layout.setSpacing(30)
        
        # 1. Stock Identity Header
        info_header = QHBoxLayout()
        info_header.setSpacing(20)
        
        self.logo = LogoWidget("XX", size=64)
        info_header.addWidget(self.logo)
        
        info_text = QVBoxLayout()
        info_text.setSpacing(0)
        self.ticker_label = QLabel("TICKER")
        self.ticker_label.setStyleSheet("color: white; font-weight: 900; font-size: 32px; letter-spacing: 1px;")
        self.name_label = QLabel("Company Name")
        self.name_label.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-size: 14px; font-weight: 500;")
        info_text.addWidget(self.ticker_label)
        info_text.addWidget(self.name_label)
        info_header.addLayout(info_text)
        
        info_header.addStretch()
        
        # Price & Change
        price_text = QVBoxLayout()
        price_text.setAlignment(Qt.AlignRight)
        price_text.setSpacing(5)
        
        self.price_label = QLabel("$0.00")
        self.price_label.setStyleSheet("color: white; font-weight: 900; font-size: 56px;")
        
        change_layout = QHBoxLayout()
        change_layout.setAlignment(Qt.AlignRight)
        
        self.change_label = QLabel("+0.00%")
        self.change_label.setAlignment(Qt.AlignCenter)
        
        self.timestamp_label = QLabel("LIVE") 
        self.timestamp_label.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-size: 11px; font-weight: bold; margin-left: 10px;")
        
        change_layout.addWidget(self.change_label)
        change_layout.addWidget(self.timestamp_label)
        
        price_text.addWidget(self.price_label)
        price_text.addLayout(change_layout)
        info_header.addLayout(price_text)
        
        card_layout.addLayout(info_header)
        
        # 2. Control Header (Timeframe Selector)
        control_header = QHBoxLayout()
        control_header.setContentsMargins(0, 0, 0, 10)
        control_header.addStretch()
        
        self.timeframe_group = QButtonGroup(self)
        self.timeframe_group.setExclusive(True)
        self.timeframe_group.buttonClicked.connect(self.on_timeframe_changed)
        
        timeframes = ["1D", "1W", "1M", "3M", "YTD", "1Y", "ALL"]
        for tf in timeframes:
            btn = QPushButton(tf)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedSize(40, 30)
            btn.setCheckable(True)
            # Glass Pill Style with Active State Logic
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgba(255, 255, 255, 0.05);
                    color: {styles.COLORS['text_secondary']};
                    border: none;
                    border-radius: 15px;
                    font-weight: bold;
                    font-size: 11px;
                }}
                QPushButton:hover {{
                    color: white;
                    background-color: rgba(255, 255, 255, 0.1);
                }}
                QPushButton:checked {{
                    color: {styles.COLORS['accent']};
                    background-color: rgba(0, 255, 194, 0.1);
                    border-bottom: 2px solid {styles.COLORS['accent']};
                }}
            """)
            self.timeframe_group.addButton(btn)
            control_header.addWidget(btn)
            
            if tf == "1M":
                btn.setChecked(True)
                
        card_layout.addLayout(control_header)

        # 3. Chart Visualization
        self.chart = DetailedChartWidget([100, 105, 102, 108, 107, 110, 115]) 
        card_layout.addWidget(self.chart)
        
        # 3. Key Metrics Grid (HUD Style)
        self.kpi_container = QWidget()
        self.kpi_layout = QHBoxLayout(self.kpi_container) # Horizontal layout for HUD
        self.kpi_layout.setSpacing(0)
        self.kpi_layout.setContentsMargins(0, 20, 0, 20)
        card_layout.addWidget(self.kpi_container)
        
        # Removed Strategic Rationale as requested
        
        self.layout.addWidget(self.card)

    def on_timeframe_changed(self, btn):
        # Simulate Data Morph / Slicing
        # In a real app, this would fetch new data based on the timeframe.
        # For now, we just randomize the chart data to show the transition.
        import random
        new_data = [100 + random.uniform(-10, 10) for _ in range(20)]
        self.chart.data = new_data
        # Restart Animation
        self.chart._progress = 0.0
        self.chart.timer.start(16)
        self.chart.update()

    def set_data(self, data):
        # Update Header
        self.logo.symbol = data['symbol']
        self.logo.fetch_logo()
        self.logo.update()
        
        self.ticker_label.setText(data['symbol'])
        self.name_label.setText(data['name'])
        self.price_label.setText(f"${data['price']:.2f}")
        
        change = data['change']
        change_pct = data['change_percent']
        sign = "+" if change >= 0 else ""
        self.change_label.setText(f"{sign}{change:.2f} ({sign}{change_pct:.2f}%)")
        
        # Color Logic
        if change >= 0:
            self.change_label.setStyleSheet(f"background-color: {styles.COLORS['accent']}20; color: {styles.COLORS['accent']}; border-radius: 12px; padding: 4px 12px; font-weight: bold;")
        else:
            self.change_label.setStyleSheet(f"background-color: {styles.COLORS['danger']}20; color: {styles.COLORS['danger']}; border-radius: 12px; padding: 4px 12px; font-weight: bold;")

        # Update Chart
        self.chart.data = data.get('history', [])
        self.chart._progress = 0.0 # Reset animation
        self.chart.timer.start(16) # Restart animation
        self.chart.update()

        # Update KPIs (HUD Style)
        # Clear existing
        while self.kpi_layout.count():
            item = self.kpi_layout.takeAt(0)
            if i < len(metrics) - 1:
                divider = QFrame()
                divider.setFixedWidth(1)
                divider.setStyleSheet(f"background-color: {styles.COLORS['surface_light']};") # Simple divider for now
                self.kpi_layout.addWidget(divider)
                
        self.kpi_layout.addStretch()
        
        # Risk Metrics HUD (Bottom Grid)
        # Add a new container for Risk Metrics if not already present? 
        # The user asked to "dismantle these containers and implement a Head-Up Display (HUD) Grid"
        # The previous code added `self.kpi_container` to `card_layout`.
        # We should add another row or reuse this one. The user listed specific fields:
        # RISK, MAX RETURN, VOLATILITY, DRAWDOWN TIME, SHARPE RATIO, BETA
        
        # Let's create a secondary HUD row below the main metrics if needed, or replace them.
        # The user said "The most critical error is the disappearance of the Risk/Performance metrics... You must dismantle these containers and implement a Head-Up Display (HUD) Grid."
        # And "populate this grid with the following key-value pairs: RISK... MAX RETURN... etc."
        # So I will ADD this new grid below the existing one (or replace if implied, but "disappearance" suggests they were missing).
        # I'll add a separator and then the Risk HUD.
        
        if not hasattr(self, 'risk_hud_container'):
             self.risk_hud_container = QWidget()
             self.risk_hud_layout = QGridLayout(self.risk_hud_container)
             self.risk_hud_layout.setContentsMargins(0, 20, 0, 0)
             self.risk_hud_layout.setSpacing(20)
             # Find where to add it. It should be in card_layout.
             # We can't easily access card_layout here without storing it.
             # But wait, `self.kpi_container` is in `card_layout`.
             # I can add it to `self.kpi_container`'s parent layout? No, I don't have reference.
             # I will assume I need to add it during `__init__` or find a way to insert it.
             # Actually, I can just add it to the layout of `self.kpi_container`? No, that's an HBox.
             
             # Better approach: In `__init__`, I created `self.kpi_container`. I should create `self.risk_hud_container` there too.
             # But I'm in `set_data`.
             # I'll fix `__init__` in a separate edit or just append to `self.card.layout()`?
             # `self.card.layout()` is `card_layout`.
             self.card.layout().addWidget(self.risk_hud_container)

        # Clear Risk HUD
        while self.risk_hud_layout.count():
            item = self.risk_hud_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        risk_metrics = [
            ("RISK", "DEGEN"),
            ("MAX RETURN", "+12.5%"),
            ("VOLATILITY", "HIGH"),
            ("DRAWDOWN", "4 Days"),
            ("SHARPE", "1.8"),
            ("BETA", "1.1")
        ]
        
        for i, (label, value) in enumerate(risk_metrics):
            # No container, just text
            lbl = QLabel(label)
            lbl.setStyleSheet("color: #7D7882; font-size: 10px; text-transform: uppercase; letter-spacing: 1px;")
            lbl.setAlignment(Qt.AlignLeft)
            
            val = QLabel(value)
            val.setStyleSheet("color: white; font-size: 18px; font-weight: 700; font-family: 'Consolas';")
            val.setAlignment(Qt.AlignLeft)
            
            # Add to grid (2 rows: Label, Value)
            # Actually, user said "Grid (grid-template-columns: repeat(4, 1fr))"
            # So 4 columns. We have 6 items. 4 on top, 2 on bottom? Or 6 columns?
            # "repeat(4, 1fr)" implies 4 columns.
            # Let's do 4 columns.
            
            row = (i // 4) * 2 # 0, 2
            col = i % 4
            
            self.risk_hud_layout.addWidget(lbl, row, col)
            self.risk_hud_layout.addWidget(val, row + 1, col)
            
            # Vertical Divider? "Use subtle vertical dividers... between columns"
            if col < 3 and i < 4: # Only for first row, between columns
                 line = QFrame()
                 line.setFixedWidth(1)
                 line.setStyleSheet("background-color: rgba(255,255,255,0.1);")
                 self.risk_hud_layout.addWidget(line, row, col, 2, 1, Qt.AlignRight)

# --- Talking Points Components ---

class MorningEspressoWidget(QFrame):
    ticker_clicked = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {styles.COLORS['surface']}; border-radius: 10px; border: 1px solid {styles.COLORS['surface_light']};")
        # Removed fixed height constraint to allow auto-expansion
        layout = QVBoxLayout(self)
        layout.setSpacing(15)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Header
        header = QLabel("MORNING ESPRESSO")
        header.setStyleSheet(f"color: {styles.COLORS['accent']}; font-weight: 900; letter-spacing: 2px; font-size: 14px; border: none; background: transparent;")
        layout.addWidget(header)
        
        # Content
        self.content_label = QLabel("Loading narrative...")
        self.content_label.setWordWrap(True)
        self.content_label.setAlignment(Qt.AlignTop | Qt.AlignLeft)
        # Typography: No borders, legible font, line-height
        # Added CSS for links: white glow and underline on hover
        self.content_label.setStyleSheet(f"""
            QLabel {{
                color: {styles.COLORS['text_primary']}; 
                font-size: 16px; 
                line-height: 1.6; 
                border: none; 
                background: transparent;
            }}
            a {{
                color: white;
                text-decoration: none;
                font-weight: bold;
            }}
            a:hover {{
                color: #00FFC2; /* Neon Teal */
                text-decoration: underline;
            }}
        """)
        self.content_label.setTextFormat(Qt.RichText)
        self.content_label.setTextInteractionFlags(Qt.TextBrowserInteraction)
        self.content_label.linkActivated.connect(self.handle_link)
        layout.addWidget(self.content_label)
        
        layout.addStretch()

    def handle_link(self, link):
        if link.startswith("ticker:"):
            symbol = link.split(":")[1]
            self.ticker_clicked.emit(symbol)

    def set_data(self, narrative_tokens):
        html = ""
        # Simulate "Block Layout" by treating tokens as potential blocks if needed, 
        # but for now we construct a rich paragraph with interactive tickers.
        
        import re
        
        for token in narrative_tokens:
            content = token['content']
            t_type = token['type']
            
            # Interactive Ticker Logic: Wrap tickers (e.g., NVDA, TSLA) in links
            # Refined Regex: Exclude common uppercase words.
            # Look for 2-5 uppercase letters, but filter out common words.
            
            def replace_ticker(match):
                ticker = match.group(0)
                # Blacklist of common uppercase words that might appear in narrative
                blacklist = {"OPEN", "HIGH", "LOW", "CLOSE", "VOL", "RISK", "BETA", "THAN", "THE", "FOR", "AND", "WITH", "FROM", "THAT", "THIS", "HAVE", "WILL", "ARE", "WAS", "BUT", "NOT"}
                if ticker in blacklist:
                    return ticker
                return f"<a href='ticker:{ticker}' style='color: white; text-decoration: underline; font-weight: bold;'>{ticker}</a>"
            
            content = re.sub(r'\b[A-Z]{2,5}\b', replace_ticker, content)
            
            style = ""
            if t_type == "ACTION":
                style = "color: white; font-weight: 900;"
            elif t_type == "CATALYST":
                 style = f"color: {styles.COLORS['news_accent']}; font-weight: bold;"
            elif t_type == "CONTEXT":
                 style = f"color: {styles.COLORS['text_secondary']};"
                 
            html += f"<span style='{style}'>{content}</span> "
            
        self.content_label.setText(html)

class RiskProfileSelector(QWidget):
    profileChanged = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        self.buttons = {}
        profiles = [("DEFENSIVE", styles.COLORS["defensive"]), 
                    ("BALANCED", styles.COLORS["balanced"]), 
                    ("SPECULATIVE", styles.COLORS["speculative"])]
        
        for name, color in profiles:
            btn = QPushButton(name)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(30)
            # Store color for styling
            btn.setProperty("activeColor", color)
            btn.clicked.connect(lambda checked, n=name: self.on_click(n))
            layout.addWidget(btn)
            self.buttons[name] = btn
            
        self.current_profile = "BALANCED"
        self.update_styles()
        
    def on_click(self, name):
        self.current_profile = name
        self.update_styles()
        self.profileChanged.emit(name)
        
    def update_styles(self):
        for name, btn in self.buttons.items():
            active_color = btn.property("activeColor")
            if name == self.current_profile:
                btn.setChecked(True)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {active_color};
                        color: white;
                        border: none;
                        border-radius: 15px;
                        font-weight: bold;
                        font-size: 11px;
                    }}
                """)
            else:
                btn.setChecked(False)
                btn.setStyleSheet(f"""
                    QPushButton {{
                        background-color: {styles.COLORS['surface_light']};
                        color: {styles.COLORS['text_secondary']};
                        border: none;
                        border-radius: 15px;
                        font-weight: bold;
                        font-size: 11px;
                    }}
                    QPushButton:hover {{
                        background-color: {styles.COLORS['surface_light']}88;
                    }}
                """)

class OpportunityCard(QFrame):
    clicked = Signal(str)

    def __init__(self, data, parent=None):
        super().__init__(parent)
        self.data = data
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"background-color: {styles.COLORS['surface']}; border-radius: 10px; border: 1px solid {styles.COLORS['surface_light']};")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Left: Logo + Ticker
        left_layout = QVBoxLayout()
        left_layout.setSpacing(5)
        left_layout.setAlignment(Qt.AlignTop)
        
        # Logo & Ticker Row
        header_row = QHBoxLayout()
        logo = LogoWidget(data['symbol'], size=40)
        header_row.addWidget(logo)
        
        ticker = QLabel(data['symbol'])
        ticker.setStyleSheet("color: white; font-weight: 900; font-size: 20px;")
        header_row.addWidget(ticker)
        left_layout.addLayout(header_row)
        
        layout.addLayout(left_layout)
        
        # Center: Narrative Hook
        narrative_text = self.render_narrative(data['narrative'])
        narrative_lbl = QLabel(narrative_text)
        narrative_lbl.setWordWrap(True)
        narrative_lbl.setTextFormat(Qt.RichText)
        narrative_lbl.setStyleSheet("font-size: 14px; line-height: 1.5;")
        layout.addWidget(narrative_lbl, 1) # Stretch
        
        # Right: Confidence + Copy
        right_layout = QVBoxLayout()
        right_layout.setAlignment(Qt.AlignTop)
        right_layout.setSpacing(10)
        
        # Confidence Badge (Top Right)
        conf_label = QLabel(f"{data['confidence']}% CONFIDENCE")
        conf_label.setAlignment(Qt.AlignCenter)
        conf_label.setStyleSheet(f"""
            color: {styles.COLORS['accent']}; 
            font-size: 10px; 
            font-weight: bold; 
            border: 1px solid {styles.COLORS['accent']}; 
            border-radius: 12px; 
            padding: 4px 8px;
        """)
        right_layout.addWidget(conf_label)
        
        copy_btn = QPushButton("COPY")
        copy_btn.setCursor(Qt.PointingHandCursor)
        copy_btn.setFixedSize(60, 30)
        copy_btn.setStyleSheet(f"background-color: {styles.COLORS['surface_light']}; color: white; border-radius: 4px; font-size: 10px; font-weight: bold;")
        right_layout.addWidget(copy_btn, 0, Qt.AlignRight)
        
        layout.addLayout(right_layout)
        
    def render_narrative(self, tokens):
        html = ""
        for token in tokens:
            content = token['content']
            t_type = token['type']
            sentiment = token['sentiment']
            
            style = ""
            if t_type == "ACTION":
                style = "color: white; font-weight: 900;"
            elif t_type == "EVIDENCE":
                color = styles.COLORS['success'] if sentiment == "BULLISH" else styles.COLORS['danger']
                style = f"color: {color}; font-weight: bold;"
            elif t_type == "CATALYST":
                style = f"color: {styles.COLORS['news_accent']}; font-weight: bold; text-decoration: underline;"
            else: # CONTEXT
                style = f"color: {styles.COLORS['text_secondary']};"
                
            html += f"<span style='{style}'>{content}</span> "
        return html

    def mousePressEvent(self, event):
        self.clicked.emit(self.data['symbol'])
        super().mousePressEvent(event)

class WhisperNumberWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {styles.COLORS['surface']}; border-radius: 10px; border: 1px solid {styles.COLORS['surface_light']};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        title = QLabel("VS CONSENSUS")
        title.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-weight: bold; letter-spacing: 1px; font-size: 12px;")
        layout.addWidget(title)
        
        self.content_layout = QVBoxLayout()
        layout.addLayout(self.content_layout)
        
    def set_data(self, data):
        # Clear existing
        while self.content_layout.count():
            item = self.content_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        for item in data:
            row = QHBoxLayout()
            
            lbl = QLabel(item['metric'])
            lbl.setStyleSheet("color: white; font-size: 14px;")
            row.addWidget(lbl)
            
            row.addStretch()
            
            val = QLabel(item['value'])
            val.setStyleSheet(f"color: {styles.COLORS['accent']}; font-weight: bold; font-size: 14px;")
            row.addWidget(val)
            
            self.content_layout.addLayout(row)
            
            # Bar
            bar_bg = QFrame()
            bar_bg.setFixedHeight(4)
            bar_bg.setStyleSheet(f"background-color: {styles.COLORS['surface_light']}; border-radius: 2px;")
            
            # Calculate width based on some metric (mocked here)
            # In a real app, we'd calculate width relative to max
            
            self.content_layout.addWidget(bar_bg)

class TalkingPointsView(QWidget):
    back_clicked = Signal()
    ticker_selected = Signal(str) # New signal for navigation

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        # Remove excessive margins to align flush top
        self.layout.setContentsMargins(20, 0, 20, 20) 
        self.layout.setSpacing(10)
        self.layout.setAlignment(Qt.AlignTop) 
        
        # Header
        header = QHBoxLayout()
        header.setContentsMargins(0, 10, 0, 10) # Small vertical padding for header
        self.back_btn = QPushButton("← BACK")
        self.back_btn.setObjectName("IconBtn")
        self.back_btn.setCursor(Qt.PointingHandCursor)
        self.back_btn.clicked.connect(self.back_clicked.emit)
        self.back_btn.setFixedWidth(80)
        header.addWidget(self.back_btn)
        
        header.addStretch()
        
        self.risk_selector = RiskProfileSelector()
        self.risk_selector.profileChanged.connect(self.refresh_opportunities)
        header.addWidget(self.risk_selector)
        
        self.layout.addLayout(header)
        
        # Bento Grid Layout
        self.grid = QGridLayout()
        self.grid.setSpacing(20)
        self.layout.addLayout(self.grid)
        
        # 1. Morning Espresso (Large Left Block)
        self.espresso = MorningEspressoWidget()
        self.espresso.ticker_clicked.connect(self.ticker_selected.emit) # Connect signal
        self.grid.addWidget(self.espresso, 0, 0, 2, 1) # Row 0, Col 0, RowSpan 2, ColSpan 1
        
        # 2. Opportunities List (Right Column)
        self.opp_container = QWidget()
        self.opp_layout = QVBoxLayout(self.opp_container)
        self.opp_layout.setContentsMargins(0, 0, 0, 0)
        self.opp_layout.setSpacing(15)
        
        # Scroll Area for Opportunities
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setWidget(self.opp_container)
        
        self.grid.addWidget(scroll, 0, 1, 2, 1)
        
        # Column Stretch
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 2)
        
        # Initial Load
        self.refresh_data()

    def refresh_data(self):
        # 1. Morning Espresso
        espresso_data = data_service.get_morning_espresso_narrative()
        self.espresso.set_data(espresso_data)
        
        # 2. Opportunities
        self.refresh_opportunities(self.risk_selector.current_profile)

    def refresh_opportunities(self, profile):
        # Clear existing
        while self.opp_layout.count():
            item = self.opp_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        opps = data_service.get_opportunities(profile)
        for opp in opps:
            card = OpportunityCard(opp)
            # Connect click signal
            card.clicked.connect(self.ticker_selected.emit)
            self.opp_layout.addWidget(card)
            
        self.opp_layout.addStretch()

# --- Settings View ---

class SettingsView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.layout.setSpacing(30)
        self.layout.setAlignment(Qt.AlignTop)
        
        title = QLabel("SETTINGS")
        title.setStyleSheet(f"color: white; font-size: 24px; font-weight: 900; letter-spacing: 1px;")
        self.layout.addWidget(title)
        
        # 1. Coverage & Universe (Multi-Select)
        self.add_section_header("COVERAGE & UNIVERSE")
        
        universe_layout = QHBoxLayout()
        universe_layout.setSpacing(10)
        
        sectors = ["Technology", "Healthcare", "Finance", "Energy", "Consumer", "Industrial"]
        for sector in sectors:
            btn = QPushButton(sector)
            btn.setCheckable(True)
            btn.setChecked(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {styles.COLORS['surface_light']};
                    color: {styles.COLORS['text_secondary']};
                    border: 1px solid {styles.COLORS['surface_light']};
                    border-radius: 15px;
                    padding: 8px 16px;
                    font-weight: bold;
                }}
                QPushButton:checked {{
                    background-color: {styles.COLORS['accent']}20;
                    color: {styles.COLORS['accent']};
                    border: 1px solid {styles.COLORS['accent']};
                }}
            """)
            universe_layout.addWidget(btn)
            
        universe_layout.addStretch()
        self.layout.addLayout(universe_layout)
        
        # 2. Client Tiering (Toggle Matrix)
        self.add_section_header("CLIENT TIERING")
        
        tiering_grid = QGridLayout()
        tiering_grid.setSpacing(15)
        
        tiers = ["Platinum", "Gold", "Silver"]
        regions = ["North America", "EMEA", "APAC"]
        
        # Headers
        for i, region in enumerate(regions):
            lbl = QLabel(region)
            lbl.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-weight: bold;")
            tiering_grid.addWidget(lbl, 0, i+1, Qt.AlignCenter)
            
        for i, tier in enumerate(tiers):
            lbl = QLabel(tier)
            lbl.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-weight: bold;")
            tiering_grid.addWidget(lbl, i+1, 0)
            
            for j, region in enumerate(regions):
                chk = QCheckBox()
                chk.setChecked(True)
                chk.setStyleSheet(f"""
                    QCheckBox::indicator {{
                        width: 20px;
                        height: 20px;
                        border-radius: 4px;
                        border: 1px solid {styles.COLORS['text_secondary']};
                        background-color: {styles.COLORS['surface']};
                    }}
                    QCheckBox::indicator:checked {{
                        background-color: {styles.COLORS['accent']};
                        border: 1px solid {styles.COLORS['accent']};
                    }}
                """)
                tiering_grid.addWidget(chk, i+1, j+1, Qt.AlignCenter)
                
        self.layout.addLayout(tiering_grid)
        
        # 3. RVOL Sensitivity (Slider)
        self.add_section_header("RVOL SENSITIVITY")
        
        rvol_layout = QHBoxLayout()
        
        self.rvol_slider = QSlider(Qt.Horizontal)
        self.rvol_slider.setRange(15, 50) # 1.5 to 5.0
        self.rvol_slider.setValue(25)
        self.rvol_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                border: 1px solid {styles.COLORS['surface_light']};
                height: 8px;
                background: {styles.COLORS['surface']};
                margin: 2px 0;
                border-radius: 4px;
            }}
            QSlider::handle:horizontal {{
                background: {styles.COLORS['accent']};
                border: 1px solid {styles.COLORS['accent']};
                width: 18px;
                height: 18px;
                margin: -7px 0;
                border-radius: 9px;
            }}
        """)
        
        self.rvol_label = QLabel("2.5x")
        self.rvol_label.setStyleSheet("color: white; font-weight: bold; font-size: 16px; margin-left: 10px;")
        self.rvol_slider.valueChanged.connect(lambda v: self.rvol_label.setText(f"{v/10:.1f}x"))
        
        rvol_layout.addWidget(self.rvol_slider)
        rvol_layout.addWidget(self.rvol_label)
        
        self.layout.addLayout(rvol_layout)
        
        self.layout.addStretch()

    def add_section_header(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-size: 12px; font-weight: bold; letter-spacing: 1px; margin-top: 20px;")
        self.layout.addWidget(lbl)
