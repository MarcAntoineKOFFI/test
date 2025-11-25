from PySide6.QtWidgets import (QWidget, QLabel, QVBoxLayout, QHBoxLayout, QFrame, 
                               QGraphicsDropShadowEffect, QSizePolicy, QScrollArea, QPushButton, QGridLayout, 
                               QButtonGroup, QComboBox, QTabWidget, QTableWidget, QHeaderView, QAbstractItemView, 
                               QProgressBar, QCheckBox, QRadioButton, QLineEdit, QTableWidgetItem, QSlider, QSpinBox, QApplication)
from PySide6.QtCore import Qt, QTimer, QSize, QPoint, QRect, Signal, QUrl, QThreadPool
from PySide6.QtGui import QColor, QPainter, QBrush, QPen, QFont, QLinearGradient, QPainterPath, QPixmap
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from datetime import datetime
import styles
import data_service
from async_utils import Worker

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
        
        # Cache
        self.cached_path = None
        self.cached_fill_path = None

    def update_data(self, data, rvol=None):
        self.data = data
        if rvol is not None:
            self.rvol = rvol
        self.cached_path = None
        self.cached_fill_path = None
        self._progress = 0.0
        self.timer.start(16)
        self.update()

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

    def calculate_points(self, width, height):
        if not self.data or len(self.data) < 2:
            return []
            
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
        return points

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        points = self.calculate_points(self.width(), self.height())
        if not points:
            return
            
        # Progressive Draw Limit
        num_points_to_draw = int(len(points) * self._progress)
        if num_points_to_draw < 2:
            return
            
        current_points = points[:num_points_to_draw]
        
        # 1. Create Path with Smooth Curves (Cubic Bezier)
        path = QPainterPath()
        fill_path = QPainterPath()
        
        # Check cache if animation complete
        if self._progress >= 1.0 and self.cached_path:
            path = self.cached_path
            fill_path = self.cached_fill_path
        else:
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
                
            # 2. Draw Gradient Fill (Luma Fade: 40% -> 0%)
            # Close the path for filling
            fill_path = QPainterPath(path)
            fill_path.lineTo(current_points[-1][0], self.height())
            fill_path.lineTo(current_points[0][0], self.height())
            fill_path.closeSubpath()
            
            # Update cache if complete
            if self._progress >= 1.0:
                self.cached_path = path
                self.cached_fill_path = fill_path
        
        # Determine Color
        is_positive = self.data[-1] >= self.data[0]
        color_hex = styles.COLORS["success"] if is_positive else styles.COLORS["danger"]
        base_color = QColor(color_hex)
        
        gradient = QLinearGradient(0, 0, 0, self.height())
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
        width = self.width()
        height = self.height()
        
        rvol_rect = [width - 8, height/2 - 10, 4, 20]
        painter.setPen(Qt.NoPen)
        
        pill_color = QColor(styles.COLORS["surface_light"])
        if self.rvol > 1.5:
             pill_color = QColor(styles.COLORS["neon_purple"])
             painter.setBrush(QColor(styles.COLORS["neon_purple"] + "40"))
             painter.drawRoundedRect(int(width - 10), int(height/2 - 12), 8, 24, 4, 4)
             
        painter.setBrush(pill_color)
        painter.drawRoundedRect(int(width - 8), int(height/2 - 10), 4, 20, 2, 2)

class DetailedChartWidget(QWidget):
    def __init__(self, data=None, dates=None, parent=None):
        super().__init__(parent)
        self.data = data if data else [] # Can be list of floats (line) or list of dicts (ohlc)
        self.dates = dates if dates else []
        self.chart_type = "CANDLE" # LINE or CANDLE
        self.setMinimumHeight(300)
        self.setMouseTracking(True)
        self.cursor_pos = None
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.cached_pixmap = None

    def set_data(self, data, dates=None):
        self.data = data
        if dates:
            self.dates = dates
        self.cached_pixmap = None
        self.update()

    def decimate_data(self, data, threshold=200):
        if len(data) <= threshold:
            return data
            
        # Simple aggregation/resampling
        new_data = []
        bucket_size = len(data) / threshold
        
        for i in range(threshold):
            start_idx = int(i * bucket_size)
            end_idx = int((i + 1) * bucket_size)
            chunk = data[start_idx:end_idx]
            
            if not chunk: continue
            
            if isinstance(chunk[0], dict): # OHLC
                agg = {
                    'date': chunk[0]['date'], # Use first date
                    'open': chunk[0]['open'],
                    'high': max(d['high'] for d in chunk),
                    'low': min(d['low'] for d in chunk),
                    'close': chunk[-1]['close'],
                    'volume': sum(d.get('volume', 0) for d in chunk)
                }
                new_data.append(agg)
            else: # Line
                # Average or just take first? Average is smoother.
                avg_val = sum(chunk) / len(chunk)
                new_data.append(avg_val)
                
        return new_data
        
    def set_chart_type(self, type_str):
        self.chart_type = type_str
        self.cached_pixmap = None
        self.update()
        
    def resizeEvent(self, event):
        self.cached_pixmap = None
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
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        width = self.width()
        height = self.height()
        data_len = len(self.data)
        
        # 1. Background & Grid
        # painter.fillRect(0, 0, width, height, QColor(styles.COLORS['surface'])) # Transparent background
        
        # Calculate value range for mapping (needed for both caching and tooltip)
        all_vals = []
        for d in self.data:
            if isinstance(d, dict):
                all_vals.extend([d['open'], d['high'], d['low'], d['close']])
            else:
                all_vals.append(d)
        
        min_val = min(all_vals) if all_vals else 0
        max_val = max(all_vals) if all_vals else 1
        val_range = max_val - min_val if max_val != min_val else 1.0
        
        # Define map_y helper (used in both cache creation and tooltip)
        def map_y(val):
            padding = height * 0.05
            available_height = height - (2 * padding)
            return height - padding - ((val - min_val) / val_range) * available_height
        
        # 2. Draw Chart (Cached)
        if self.cached_pixmap is None:
            self.cached_pixmap = QPixmap(width, height)
            self.cached_pixmap.fill(Qt.transparent)
            
            cache_painter = QPainter(self.cached_pixmap)
            cache_painter.setRenderHint(QPainter.Antialiasing)
            
            # Draw Grid on Cache
            grid_pen = QPen(QColor(styles.COLORS['grid_line']))
            grid_pen.setStyle(Qt.DashLine)
            grid_pen.setWidth(1)
            cache_painter.setPen(grid_pen)
            for i in range(1, 5):
                y = i * (height / 5)
                cache_painter.drawLine(0, int(y), width, int(y))
            
            # Decimate Data for Rendering
            render_data = self.decimate_data(self.data, threshold=300) # Limit to 300 candles/points
            render_len = len(render_data)
            
            # Helper to map index to X (Local scope for cache_painter)
            # Helper to map index to X (Local scope for cache_painter)
            def map_x_render(idx):
                return (idx / (render_len - 1)) * width if render_len > 1 else width / 2
            
            # Helper to map Value to Y
            all_vals = []
            for d in render_data:
                if isinstance(d, dict):
                    all_vals.extend([d['open'], d['high'], d['low'], d['close']])
                else:
                    all_vals.append(d)
            
            min_val = min(all_vals) if all_vals else 0
            max_val = max(all_vals) if all_vals else 1
            val_range = max_val - min_val if max_val != min_val else 1.0
            
            def map_y(val):
                # Add some padding (5%)
                padding = height * 0.05
                available_height = height - (2 * padding)
                return height - padding - ((val - min_val) / val_range) * available_height

            if self.chart_type == "CANDLE" and isinstance(render_data[0], dict):
                # Draw Candlesticks
                candle_width = max(1, (width / render_len) * 0.6)
                
                for i, candle in enumerate(render_data):
                    x = map_x_render(i)
                    y_open = map_y(candle['open'])
                    y_close = map_y(candle['close'])
                    y_high = map_y(candle['high'])
                    y_low = map_y(candle['low'])
                    
                    is_up = candle['close'] >= candle['open']
                    color = QColor(styles.COLORS['success']) if is_up else QColor(styles.COLORS['danger'])
                    
                    cache_painter.setPen(QPen(color, 1))
                    cache_painter.drawLine(int(x), int(y_high), int(x), int(y_low)) # Wick
                    
                    rect_top = min(y_open, y_close)
                    rect_height = abs(y_close - y_open)
                    if rect_height < 1: rect_height = 1
                    
                    cache_painter.setBrush(color)
                    cache_painter.setPen(Qt.NoPen)
                    cache_painter.drawRect(int(x - candle_width/2), int(rect_top), int(candle_width), int(rect_height))
                    
            else:
                # Draw Line Chart
                path = QPainterPath()
                fill_path = QPainterPath()
                
                # Prepare points
                points = []
                for i in range(render_len):
                    val = render_data[i] if not isinstance(render_data[i], dict) else render_data[i]['close']
                    x = map_x_render(i)
                    y = map_y(val)
                    points.append((x, y))
                    
                if points:
                    path.moveTo(points[0][0], points[0][1])
                    fill_path.moveTo(points[0][0], height)
                    fill_path.lineTo(points[0][0], points[0][1])
                    
                    for x, y in points[1:]:
                        path.lineTo(x, y)
                        fill_path.lineTo(x, y)
                        
                    fill_path.lineTo(points[-1][0], height)
                    fill_path.closeSubpath()
                    
                    # Gradient Fill
                    color = QColor(styles.COLORS['accent'])
                    gradient = QLinearGradient(0, 0, 0, height)
                    gradient.setColorAt(0, QColor(color.red(), color.green(), color.blue(), 100))
                    gradient.setColorAt(1, QColor(color.red(), color.green(), color.blue(), 0))
                    
                    cache_painter.setBrush(gradient)
                    cache_painter.setPen(Qt.NoPen)
                    cache_painter.drawPath(fill_path)
                    
                    # Line Stroke
                    cache_painter.setBrush(Qt.NoBrush)
                    cache_painter.setPen(QPen(color, 2))
                    cache_painter.drawPath(path)
    
            # 3. Axes (on Cache)
            cache_painter.setPen(QColor(styles.COLORS['text_secondary']))
            cache_painter.setFont(QFont("Consolas", 8))
            
            # Y-Axis
            y_steps = 5
            for i in range(y_steps + 1):
                val = min_val + (i * (val_range / y_steps))
                y = map_y(val)
                cache_painter.drawText(int(width - 50), int(y) + 4, f"${val:.2f}")
                
            # X-Axis
            x_steps = 5
            data_len = len(self.data)
            for i in range(x_steps + 1):
                idx = int(i * (data_len - 1) / x_steps) # Use original data len for dates
                x = (i / x_steps) * width
                
                date_str = ""
                if isinstance(self.data[0], dict):
                    date_str = self.data[idx]['date'][5:10] # MM-DD
                elif self.dates and idx < len(self.dates):
                    date_str = self.dates[idx][5:]
                    
                cache_painter.drawText(int(x) - 15, height - 5, date_str)
                
            cache_painter.end()

        # Draw Cached Pixmap
        painter.drawPixmap(0, 0, self.cached_pixmap)
            painter.setPen(QPen(QColor("white"), 1, Qt.DashLine))
            painter.drawLine(int(x), 0, int(x), height)
            
            # Draw Tooltip
            if isinstance(self.data[0], dict):
                candle = self.data[idx]
                lines = [
                    f"Date: {candle['date']}",
                    f"Open: {candle['open']:.2f}",
                    f"High: {candle['high']:.2f}",
                    f"Low:  {candle['low']:.2f}",
                    f"Close:{candle['close']:.2f}"
                ]
                val = candle['close']
            else:
                val = self.data[idx]
                date_str = self.dates[idx] if self.dates and idx < len(self.dates) else "N/A"
                lines = [
                    f"Date: {date_str}",
                    f"Price: {val:.2f}"
                ]
                
            y = map_y(val)
            painter.drawLine(0, int(y), width, int(y))
            
            # Tooltip Box
            tw, th = 140, 20 * len(lines) + 10
            tx = x + 10 if x + 10 + tw < width else x - 10 - tw
            ty = y - th - 10 if y - th - 10 > 0 else y + 10
            
            painter.setBrush(QColor(30, 30, 30, 230))
            painter.setPen(QPen(QColor(styles.COLORS['surface_light']), 1))
            painter.drawRoundedRect(int(tx), int(ty), int(tw), int(th), 5, 5)
            
            painter.setPen(QColor("white"))
            for i, line in enumerate(lines):
                painter.drawText(int(tx) + 10, int(ty) + 20 + (i*18), line)
                
        painter.end()

class ComparisonWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {styles.COLORS['surface']};
                border: 1px solid {styles.COLORS['surface_light']};
                border-radius: 8px;
            }}
            QLabel {{ border: none; }}
        """)
        
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("COMPARATIVE ANALYSIS")
        header.setStyleSheet(f"font-family: {styles.FONTS['primary']}; font-size: 14px; font-weight: bold; color: {styles.COLORS['accent']};")
        layout.addWidget(header)
        
        # Tabs for Table vs Heatmap
        self.tabs = QTabWidget()
        self.tabs.setStyleSheet(f"""
            QTabWidget::pane {{ border: none; }}
            QTabBar::tab {{
                background: {styles.COLORS['surface_light']};
                color: {styles.COLORS['text_secondary']};
                padding: 8px 16px;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
            }}
            QTabBar::tab:selected {{
                background: {styles.COLORS['accent']};
                color: white;
            }}
        """)
        
        # 1. Performance Table
        self.perf_table = QTableWidget()
        self.perf_table.setColumnCount(6)
        self.perf_table.setHorizontalHeaderLabels(["Symbol", "1D", "1W", "1M", "YTD", "1Y"])
        self.perf_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.perf_table.verticalHeader().setVisible(False)
        self.perf_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: transparent;
                gridline-color: {styles.COLORS['surface_light']};
                color: white;
            }}
            QHeaderView::section {{
                background-color: {styles.COLORS['surface_light']};
                color: {styles.COLORS['text_secondary']};
                border: none;
                padding: 4px;
            }}
        """)
        self.tabs.addTab(self.perf_table, "Performance")
        
        # 2. Correlation Heatmap (Simplified as Table for now)
        self.corr_table = QTableWidget()
        self.corr_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.corr_table.verticalHeader().setVisible(True)
        self.corr_table.setStyleSheet(self.perf_table.styleSheet())
        self.tabs.addTab(self.corr_table, "Correlation")
        
        layout.addWidget(self.tabs)
        
    def set_data(self, data):
        if not data: return
        
        # 1. Performance
        perf_data = data.get('performance', [])
        self.perf_table.setRowCount(len(perf_data))
        
        for i, row in enumerate(perf_data):
            self.perf_table.setItem(i, 0, QTableWidgetItem(row['symbol']))
            
            keys = ['1d', '1w', '1m', 'ytd', '1y']
            for j, key in enumerate(keys):
                val = row.get(key, 0.0)
                item = QTableWidgetItem(f"{val:+.2f}%")
                
                color = styles.COLORS['success'] if val > 0 else styles.COLORS['danger']
                item.setForeground(QColor(color))
                item.setTextAlignment(Qt.AlignCenter)
                self.perf_table.setItem(i, j+1, item)
                
        # 2. Correlation
        corr_matrix = data.get('correlation', {})
        symbols = list(corr_matrix.keys())
        
        self.corr_table.setRowCount(len(symbols))
        self.corr_table.setColumnCount(len(symbols))
        self.corr_table.setHorizontalHeaderLabels(symbols)
        self.corr_table.setVerticalHeaderLabels(symbols)
        
        for i, sym1 in enumerate(symbols):
            for j, sym2 in enumerate(symbols):
                val = corr_matrix[sym1].get(sym2, 0.0)
                item = QTableWidgetItem(f"{val:.2f}")
                item.setTextAlignment(Qt.AlignCenter)
                
                # Colorize
                if val > 0.8:
                    bg = QColor(styles.COLORS['success'])
                    bg.setAlpha(100)
                    item.setBackground(bg)
                elif val < 0:
                    bg = QColor(styles.COLORS['danger'])
                    bg.setAlpha(50)
                    item.setBackground(bg)
                    
                self.corr_table.setItem(i, j, item)

class FundamentalAnalysisView(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {styles.COLORS['surface']};
                border: 1px solid {styles.COLORS['surface_light']};
                border-radius: 8px;
            }}
            QLabel {{ border: none; }}
        """)
        
        layout = QVBoxLayout(self)
        
        # Header
        header = QLabel("FUNDAMENTAL ANALYSIS")
        header.setStyleSheet(f"font-family: {styles.FONTS['primary']}; font-size: 14px; font-weight: bold; color: {styles.COLORS['accent']};")
        layout.addWidget(header)
        
        # Content Grid
        self.grid = QGridLayout()
        self.grid.setSpacing(15)
        layout.addLayout(self.grid)
        
        # Metrics to display
        self.metrics = {
            "Valuation": [
                ("P/E Ratio", "pe"), ("Forward P/E", "fpe"), ("PEG Ratio", "peg"),
                ("P/S Ratio", "ps"), ("P/B Ratio", "pb"), ("Market Cap", "mkt_cap")
            ],
            "Profitability": [
                ("Gross Margin", "gross_margin"), ("Operating Margin", "op_margin"),
                ("Net Margin", "net_margin"), ("ROE", "roe")
            ],
            "Growth": [
                ("Revenue Growth", "rev_growth"), ("Earnings Growth", "earn_growth")
            ]
        }
        
        self.labels = {}
        
        row = 0
        for category, items in self.metrics.items():
            # Category Header
            cat_label = QLabel(category.upper())
            cat_label.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-size: 10px; font-weight: bold; margin-top: 10px;")
            self.grid.addWidget(cat_label, row, 0, 1, 2)
            row += 1
            
            for label, key in items:
                # Label
                lbl = QLabel(label)
                lbl.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-size: 12px;")
                self.grid.addWidget(lbl, row, 0)
                
                # Value
                val_lbl = QLabel("--")
                val_lbl.setStyleSheet("color: white; font-size: 12px; font-weight: bold;")
                val_lbl.setAlignment(Qt.AlignRight)
                self.grid.addWidget(val_lbl, row, 1)
                
                self.labels[key] = val_lbl
                row += 1
                
        layout.addStretch()
        
    def set_data(self, data):
        if not data: return
        
        for key, label_widget in self.labels.items():
            val = data.get(key, 0)
            
            # Format based on key
            if key == 'mkt_cap':
                if val > 1e12: text = f"${val/1e12:.2f}T"
                elif val > 1e9: text = f"${val/1e9:.2f}B"
                elif val > 1e6: text = f"${val/1e6:.2f}M"
                else: text = f"${val:,.0f}"
            elif 'margin' in key or 'growth' in key or 'roe' in key:
                text = f"{val}%"
                if val > 0: label_widget.setStyleSheet(f"color: {styles.COLORS['success']}; font-weight: bold;")
                elif val < 0: label_widget.setStyleSheet(f"color: {styles.COLORS['danger']}; font-weight: bold;")
                else: label_widget.setStyleSheet("color: white; font-weight: bold;")
            else:
                text = f"{val:.2f}"
                label_widget.setStyleSheet("color: white; font-weight: bold;")
                
            label_widget.setText(text)

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
        
        # Price & Change (Added as requested)
        price_layout = QVBoxLayout()
        price_layout.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        price_layout.setSpacing(2)
        
        price_val = data.get('price', 0.0)
        change_val = data.get('change', 0.0)
        change_pct = data.get('change_percent', 0.0)
        
        self.price_lbl = QLabel(f"${price_val:.2f}")
        self.price_lbl.setStyleSheet("color: white; font-weight: bold; font-size: 14px; border: none; background: transparent;")
        self.price_lbl.setAlignment(Qt.AlignRight)
        
        sign = "+" if change_val >= 0 else ""
        color = styles.COLORS['success'] if change_val >= 0 else styles.COLORS['danger']
        self.change_lbl = QLabel(f"{sign}{change_val:.2f} ({sign}{change_pct:.2f}%)")
        self.change_lbl.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 11px; border: none; background: transparent;")
        self.change_lbl.setAlignment(Qt.AlignRight)
        
        price_layout.addWidget(self.price_lbl)
        price_layout.addWidget(self.change_lbl)
        
        layout.addLayout(price_layout)
        
        layout.addStretch(1)
        
        self.sparkline = SparklineWidget(data.get('history', []), rvol=data.get('rvol', 1.0))
        layout.addWidget(self.sparkline, 2)

    def update_data(self, data):
        self.data = data
        
        price_val = data.get('price', 0.0)
        change_val = data.get('change', 0.0)
        change_pct = data.get('change_percent', 0.0)
        
        self.price_lbl.setText(f"${price_val:.2f}")
        
        sign = "+" if change_val >= 0 else ""
        color = styles.COLORS['success'] if change_val >= 0 else styles.COLORS['danger']
        self.change_lbl.setText(f"{sign}{change_val:.2f} ({sign}{change_pct:.2f}%)")
        self.change_lbl.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 11px; border: none; background: transparent;")
        
        self.sparkline.update_data(data.get('history', []), rvol=data.get('rvol', 1.0))

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.symbol)
        super().mousePressEvent(event)

class NewsItemWidget(QFrame):
    clicked = Signal(str) # url

    def __init__(self, news_data, parent=None):
        super().__init__(parent)
        self.news_data = news_data
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet(f"background-color: {styles.COLORS['surface_light']}; border-radius: 8px;")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(5)
        
        # Header: Source + Time + Sentiment
        header = QHBoxLayout()
        
        source_lbl = QLabel(news_data.get('source', 'Unknown'))
        source_lbl.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-size: 10px; font-weight: bold; text-transform: uppercase;")
        header.addWidget(source_lbl)
        
        header.addStretch()
        
        # Sentiment Badge
        sentiment = news_data.get('sentiment', 'NEUTRAL')
        if sentiment == "BULLISH":
            color = styles.COLORS['success']
            text = "BULLISH"
        elif sentiment == "BEARISH":
            color = styles.COLORS['danger']
            text = "BEARISH"
        else:
            color = styles.COLORS['text_secondary']
            text = "NEUTRAL"
            
        sent_lbl = QLabel(text)
        sent_lbl.setStyleSheet(f"color: {color}; font-size: 9px; font-weight: bold; border: 1px solid {color}; border-radius: 4px; padding: 2px 4px;")
        header.addWidget(sent_lbl)
        
        # Time
        ts = datetime.fromisoformat(news_data['timestamp'])
        time_str = ts.strftime("%b %d, %H:%M")
        time_lbl = QLabel(time_str)
        time_lbl.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-size: 10px;")
        header.addWidget(time_lbl)
        
        layout.addLayout(header)
        
        # Headline
        title_text = news_data.get('title', news_data.get('headline', 'No Title'))
        headline = QLabel(title_text)
        headline.setWordWrap(True)
        headline.setStyleSheet("color: white; font-size: 14px; font-weight: bold;")
        layout.addWidget(headline)
        
    def mousePressEvent(self, event):
        import webbrowser
        url = self.news_data.get('url')
        if url:
            webbrowser.open(url)
        super().mousePressEvent(event)

class NewsTimelineWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)
        
        header = QLabel("RECENT NEWS")
        header.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-size: 12px; font-weight: bold; letter-spacing: 1px; margin-bottom: 10px;")
        layout.addWidget(header)
        
        self.scroll = QScrollArea()
        self.scroll.setWidgetResizable(True)
        self.scroll.setStyleSheet("background: transparent; border: none;")
        
        self.container = QWidget()
        self.container_layout = QVBoxLayout(self.container)
        self.container_layout.setContentsMargins(0, 0, 0, 0)
        self.container_layout.setSpacing(10)
        self.container_layout.addStretch()
        
        self.scroll.setWidget(self.container)
        layout.addWidget(self.scroll)
        
    def set_news(self, news):
        # Clear existing
        while self.container_layout.count() > 1: # Keep stretch
            item = self.container_layout.takeAt(0)

    def load_news(self, symbol):
        # Deprecated: Use set_news with async fetcher
        pass

class MarketNewsWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        # To be implemented for Dashboard
        pass

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
        
        # Connect timeframe button group to handler
        self.timeframe_group.buttonClicked.connect(self.on_timeframe_changed)
                
        card_layout.addLayout(control_header)
        
        # Chart Controls
        chart_controls = QHBoxLayout()
        chart_controls.setContentsMargins(0, 0, 0, 0)
        
        self.chart_type_combo = QComboBox()
        self.chart_type_combo.addItems(["CANDLE", "LINE"])
        self.chart_type_combo.setCursor(Qt.PointingHandCursor)
        self.chart_type_combo.setStyleSheet(f"""
            QComboBox {{
                background-color: {styles.COLORS['surface_light']};
                color: white;
                border: none;
                border-radius: 4px;
                padding: 4px 8px;
                font-weight: bold;
            }}
            QComboBox::drop-down {{ border: none; }}
        """)
        self.chart_type_combo.currentTextChanged.connect(self.on_chart_type_changed)
        chart_controls.addWidget(self.chart_type_combo)
        chart_controls.addStretch()
        
        card_layout.addLayout(chart_controls)

        # 3. Chart Visualization
        self.chart = DetailedChartWidget([100, 105, 102, 108, 107, 110, 115]) 
        card_layout.addWidget(self.chart)
        
        # 3. Key Metrics Grid (HUD Style)
        self.kpi_container = QWidget()
        self.kpi_layout = QHBoxLayout(self.kpi_container) # Horizontal layout for HUD
        self.kpi_layout.setSpacing(0)
        self.kpi_layout.setContentsMargins(0, 20, 0, 20)
        self.kpi_layout.setContentsMargins(0, 20, 0, 20)
        card_layout.addWidget(self.kpi_container)
        
        # Risk HUD
        self.risk_hud_container = QWidget()
        self.risk_hud_layout = QGridLayout(self.risk_hud_container)
        self.risk_hud_layout.setContentsMargins(0, 0, 0, 0)
        card_layout.addWidget(self.risk_hud_container)
        
        # 4. News Timeline
        self.news_timeline = NewsTimelineWidget()
        # Add to a splitter or just below chart?
        # For now, add below chart
        card_layout.addWidget(self.news_timeline)
        
        self.layout.addWidget(self.card)
        
        # 5. Comparative Analysis
        self.comparison_widget = ComparisonWidget()
        self.comparison_widget.setMinimumHeight(400) # Ensure it's big enough
        self.layout.addWidget(self.comparison_widget)
        
        # 6. Fundamental Analysis
        self.fundamental_widget = FundamentalAnalysisView()
        self.layout.addWidget(self.fundamental_widget)

    def on_chart_type_changed(self, text):
        self.chart.set_chart_type(text)

    def on_timeframe_changed(self, btn):
        tf = btn.text()
        period = "1mo"
        interval = "1d"
        
        if tf == "1D":
            period = "1d"
            interval = "5m"
        elif tf == "1W":
            period = "5d"
            interval = "15m"
        elif tf == "1M":
            period = "1mo"
            interval = "1d"
        elif tf == "3M":
            period = "3mo"
            interval = "1d"
        elif tf == "YTD":
            period = "ytd"
            interval = "1d"
        elif tf == "1Y":
            period = "1y"
            interval = "1d" # or 1wk
        elif tf == "ALL":
            period = "max"
            interval = "1mo" # Monthly candles for max history
            
        # Fetch new data
        # Async Fetch
        worker = Worker(data_service.fetch_detailed_ohlc_data, self.ticker_label.text(), period=period, interval=interval)
        worker.signals.result.connect(self.chart.set_data)
        QThreadPool.globalInstance().start(worker)

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

        # Async Fetches
        symbol = data['symbol']
        
        # 1. Chart
        worker_chart = Worker(data_service.fetch_detailed_ohlc_data, symbol, period="1mo", interval="1d")
        worker_chart.signals.result.connect(self.chart.set_data)
        QThreadPool.globalInstance().start(worker_chart)
        
        # 2. Comparison
        worker_comp = Worker(data_service.get_comparison_data, symbol)
        worker_comp.signals.result.connect(self.comparison_widget.set_data)
        QThreadPool.globalInstance().start(worker_comp)
        
        # 3. Fundamentals
        worker_fund = Worker(data_service.fetch_fundamentals, symbol)
        worker_fund.signals.result.connect(self.fundamental_widget.set_data)
        QThreadPool.globalInstance().start(worker_fund)
        
        # 4. News
        worker_news = Worker(data_service.fetch_news_for_symbol, symbol)
        worker_news.signals.result.connect(self.news_timeline.set_news)
        QThreadPool.globalInstance().start(worker_news)

        # 5. Risk Metrics
        worker_risk = Worker(data_service.calculate_risk_metrics, symbol)
        worker_risk.signals.result.connect(self.update_risk_hud)
        QThreadPool.globalInstance().start(worker_risk)

        # Update KPIs (HUD Style) - Using available data immediately
        # Clear existing
        while self.kpi_layout.count():
            item = self.kpi_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        metrics = [
            ("OPEN", f"${data.get('open', 0):.2f}"),
            ("HIGH", f"${data.get('high', 0):.2f}"),
            ("LOW", f"${data.get('low', 0):.2f}"),
            ("VOL", f"{data.get('volume', 0)/1000000:.1f}M"),
            ("MKT CAP", f"{data.get('mkt_cap', 0)/1000000000:.1f}B")
        ]
        
        self.kpi_layout.addStretch()
        
        for i, (label, value) in enumerate(metrics):
            container = QWidget()
            vbox = QVBoxLayout(container)
            vbox.setContentsMargins(15, 0, 15, 0)
            vbox.setSpacing(4)
            
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-size: 10px; font-weight: bold; letter-spacing: 1px;")
            
            val = QLabel(value)
            val.setAlignment(Qt.AlignCenter)
            val.setStyleSheet("color: white; font-size: 14px; font-weight: bold; font-family: 'Consolas';")
            
            vbox.addWidget(lbl)
            vbox.addWidget(val)
            
            self.kpi_layout.addWidget(container)
            
            # Divider
            if i < len(metrics) - 1:
                divider = QFrame()
                divider.setFixedWidth(1)
                divider.setFixedHeight(24)
                divider.setStyleSheet(f"background-color: {styles.COLORS['surface_light']};")
                self.kpi_layout.addWidget(divider)
                
        self.kpi_layout.addStretch()
        
        # Initialize Risk HUD container if needed (it's created in init, but layout might be empty)
        # We clear it in update_risk_hud

    def update_risk_hud(self, risk_data):
        if not risk_data:
            risk_data = {
                'risk_level': 'UNKNOWN', 'max_return': 'N/A', 'volatility': 0, 
                'max_drawdown': 0, 'sharpe': 0, 'beta': 0
            }
            
        # Clear Risk HUD
        while self.risk_hud_layout.count():
            item = self.risk_hud_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        risk_metrics = [
            ("RISK", risk_data.get('risk_level', 'UNKNOWN')),
            ("MAX DD", f"{risk_data.get('max_drawdown', 0)}%"),
            ("VOLATILITY", f"{risk_data.get('volatility', 0)}%"),
            ("SHARPE", f"{risk_data.get('sharpe', 0)}"),
            ("BETA", f"{risk_data.get('beta', 0)}")
        ]
        
        # Populate Risk HUD
        for i, (label, value) in enumerate(risk_metrics):
            container = QWidget()
            vbox = QVBoxLayout(container)
            vbox.setContentsMargins(0, 0, 0, 0)
            vbox.setSpacing(5)
            
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-size: 10px; font-weight: bold;")
            
            val = QLabel(str(value))
            val.setAlignment(Qt.AlignCenter)
            val.setStyleSheet("color: white; font-size: 14px; font-weight: bold; font-family: 'Consolas';")
            
            vbox.addWidget(lbl)
            vbox.addWidget(val)
            
            row = 0
            col = i
            self.risk_hud_layout.addWidget(container, row, col)

        # Fundamentals Section
        if not hasattr(self, 'fund_container'):
            self.fund_container = QWidget()
            self.fund_layout = QGridLayout(self.fund_container)
            self.fund_layout.setContentsMargins(0, 20, 0, 0)
            self.fund_layout.setSpacing(15)
            self.card.layout().addWidget(self.fund_container)
            
        # Clear Fundamentals
        while self.fund_layout.count():
            item = self.fund_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        symbol = self.ticker_label.text()
        fund_data = data_service.fetch_fundamentals(symbol)
        if fund_data:
            # Format Market Cap
            mc = fund_data['mkt_cap']
            if mc > 1e12: mc_str = f"${mc/1e12:.2f}T"
            elif mc > 1e9: mc_str = f"${mc/1e9:.2f}B"
            else: mc_str = f"${mc/1e6:.2f}M"
            
            f_metrics = [
                ("MKT CAP", mc_str),
                ("P/E", f"{fund_data['pe']}"),
                ("FWD P/E", f"{fund_data['fpe']}"),
                ("PEG", f"{fund_data['peg']}"),
                ("P/S", f"{fund_data['ps']}"),
                ("REV GR", f"{fund_data['rev_growth']}%"),
                ("EPS GR", f"{fund_data['earn_growth']}%"),
                ("GROSS MGN", f"{fund_data['gross_margin']}%"),
                ("NET MGN", f"{fund_data['net_margin']}%"),
                ("ROE", f"{fund_data['roe']}%")
            ]
            
            for i, (label, value) in enumerate(f_metrics):
                container = QWidget()
                vbox = QVBoxLayout(container)
                vbox.setContentsMargins(0, 0, 0, 0)
                vbox.setSpacing(2)
                
                lbl = QLabel(label)
                lbl.setAlignment(Qt.AlignCenter)
                lbl.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-size: 9px; font-weight: bold;")
                
                val = QLabel(str(value))
                val.setAlignment(Qt.AlignCenter)
                val.setStyleSheet("color: white; font-size: 12px; font-weight: bold; font-family: 'Consolas';")
                
                vbox.addWidget(lbl)
                vbox.addWidget(val)
                
                row = i // 5
                col = i % 5
                self.fund_layout.addWidget(container, row, col)

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
        header_layout = QHBoxLayout()
        header = QLabel("MORNING ESPRESSO")
        header.setStyleSheet(f"color: {styles.COLORS['accent']}; font-weight: 900; letter-spacing: 2px; font-size: 14px; border: none; background: transparent;")
        header_layout.addWidget(header)
        
        header_layout.addStretch()
        
        # Regime Badge
        self.regime_badge = QLabel("NEUTRAL")
        self.regime_badge.hide() # Hidden by default until data loaded
        header_layout.addWidget(self.regime_badge)
        
        layout.addLayout(header_layout)
        
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

    def handle_link(self, link):
        if link.startswith("ticker:"):
            symbol = link.split(":")[1]
            self.ticker_clicked.emit(symbol)

    def set_data(self, narrative_tokens, regime_data=None):
        # 1. Update Regime Badge if provided
        if regime_data:
            regime = regime_data.get('regime', 'NEUTRAL')
            trend = regime_data.get('trend', 'SIDEWAYS')
            vol = regime_data.get('volatility', 'NORMAL')
            
            # Color logic
            color = styles.COLORS['text_secondary']
            if "BULL" in regime: color = styles.COLORS['success']
            elif "BEAR" in regime: color = styles.COLORS['danger']
            elif "CHOPPY" in regime: color = styles.COLORS['warning']
            
            self.regime_badge.setText(f"{regime} • {trend}")
            self.regime_badge.setStyleSheet(f"color: {color}; border: 1px solid {color}; border-radius: 4px; padding: 4px 8px; font-size: 10px; font-weight: bold;")
            self.regime_badge.show()
        else:
            self.regime_badge.hide()

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
                blacklist = {"OPEN", "HIGH", "LOW", "CLOSE", "VOL", "RISK", "BETA", "THAN", "THE", "FOR", "AND", "WITH", "FROM", "THAT", "THIS", "HAVE", "WILL", "ARE", "WAS", "BUT", "NOT", "RECAP", "MARKET", "SESSION"}
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

class SectorRotationWidget(QFrame):
    sectorClicked = Signal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {styles.COLORS['surface']}; border-radius: 10px; border: 1px solid {styles.COLORS['surface_light']};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        header = QLabel("SECTOR ROTATION (1W)")
        header.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        layout.addWidget(header)
        
        self.grid = QGridLayout()
        self.grid.setSpacing(5)
        layout.addLayout(self.grid)
        
    def set_data(self, sectors):
        # Clear
        while self.grid.count():
            item = self.grid.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Display as a heatmap grid
        # Top 3 Green, Bottom 3 Red, Middle Grey
        
        for i, sector in enumerate(sectors):
            name = sector['name']
            change = sector['1w']
            
            # Color
            bg_color = styles.COLORS['surface_light']
            text_color = "white"
            
            if change > 1.0:
                bg_color = styles.COLORS['success'] + "40" # Low opacity
                text_color = styles.COLORS['success']
            elif change < -1.0:
                bg_color = styles.COLORS['danger'] + "40"
                text_color = styles.COLORS['danger']
                
            btn = QPushButton(f"{name}\n{change:+.1f}%")
            btn.setCursor(Qt.PointingHandCursor)
            # Store name in property to retrieve on click
            btn.setProperty("sector_name", name)
            btn.clicked.connect(lambda checked=False, n=name: self.sectorClicked.emit(n))
            
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {bg_color}; 
                    color: {text_color}; 
                    border: none;
                    border-radius: 4px; 
                    font-size: 10px; 
                    font-weight: bold; 
                    padding: 5px;
                    text-align: center;
                }}
                QPushButton:hover {{
                    border: 1px solid {text_color};
                }}
            """)
            
            row = i // 3
            col = i % 3
            self.grid.addWidget(btn, row, col)

class EarningsWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {styles.COLORS['surface']}; border-radius: 10px; border: 1px solid {styles.COLORS['surface_light']};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        header = QLabel("UPCOMING EARNINGS")
        header.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        layout.addWidget(header)
        
        self.list_layout = QVBoxLayout()
        layout.addLayout(self.list_layout)
        layout.addStretch()
        
    def set_data(self, earnings):
        while self.list_layout.count():
            item = self.list_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        if not earnings:
            lbl = QLabel("No earnings in next 7 days.")
            lbl.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-style: italic; font-size: 11px;")
            self.list_layout.addWidget(lbl)
            return
            
        for item in earnings[:5]: # Show top 5
            row = QHBoxLayout()
            
            sym = QLabel(item['symbol'])
            sym.setStyleSheet("color: white; font-weight: bold;")
            
            date = QLabel(f"in {item['days_until']} days")
            date.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-size: 11px;")
            
            row.addWidget(sym)
            row.addStretch()
            row.addWidget(date)
            
            self.list_layout.addLayout(row)

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
        
        # Risk Warning Label
        self.warning_label = QLabel("")
        self.warning_label.setStyleSheet(f"color: {styles.COLORS['danger']}; font-size: 10px; font-weight: bold; margin-left: 10px;")
        self.warning_label.hide()
        layout.addWidget(self.warning_label)
        
    def set_risk_warning(self, visible, text=""):
        if visible:
            self.warning_label.setText(text)
            self.warning_label.show()
        else:
            self.warning_label.hide()
        
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
        copy_btn.clicked.connect(self.copy_to_clipboard)
        right_layout.addWidget(copy_btn, 0, Qt.AlignRight)
        self.copy_btn = copy_btn
        
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

    def copy_to_clipboard(self):
        """Formats opportunity data and copies to clipboard."""
        data = self.data
        setup = data.get('trade_setup', {})
        
        # Format Plain Text
        text = f"TRADE IDEA: {data['symbol']} - {data['name']}\n"
        text += f"Confidence: {data['confidence']}%\n\n"
        
        # Narrative (Strip HTML)
        narrative_text = ""
        for token in data['narrative']:
            narrative_text += token['content'] + " "
        text += f"NARRATIVE:\n{narrative_text.strip()}\n\n"
        
        text += "TRADE PARAMETERS:\n"
        text += f"- Entry: ${setup.get('entry', 0):.2f}\n"
        text += f"- Stop Loss: ${setup.get('stop', 0):.2f}\n"
        text += f"- Target: ${setup.get('target', 0):.2f}\n"
        text += f"- Risk/Reward: {setup.get('risk_reward', 0)}:1\n"
        text += f"- Position Size: {setup.get('position_size', '0%')}\n"
        text += f"- Horizon: {setup.get('time_horizon', 'Unknown')}\n"
        
        if data.get('catalyst'):
            text += f"- Catalyst: {data['catalyst']}\n"
            
        text += f"\nGenerated: {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        # Copy
        clipboard = QApplication.clipboard()
        clipboard.setText(text)
        
        # Feedback
        original_text = self.copy_btn.text()
        self.copy_btn.setText("COPIED!")
        self.copy_btn.setStyleSheet(f"background-color: {styles.COLORS['success']}; color: black; border-radius: 4px; font-size: 10px; font-weight: bold;")
        
        QTimer.singleShot(2000, lambda: self.restore_copy_btn(original_text))
        
        # Save to History
        try:
            data_service.save_opportunity_to_history(data)
        except Exception as e:
            print(f"Error saving history: {e}")

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
        
        # Refresh Controls
        self.last_updated_label = QLabel("Updated: Just now")
        self.last_updated_label.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-size: 11px; margin-right: 10px;")
        header.addWidget(self.last_updated_label)
        
        self.refresh_btn = QPushButton("REFRESH")
        self.refresh_btn.setCursor(Qt.PointingHandCursor)
        self.refresh_btn.setFixedSize(70, 30)
        self.refresh_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles.COLORS['surface_light']};
                color: {styles.COLORS['text_secondary']};
                border: 1px solid {styles.COLORS['surface_light']};
                border-radius: 15px;
                font-weight: bold;
                font-size: 10px;
            }}
            QPushButton:hover {{
                border: 1px solid {styles.COLORS['accent']};
                color: white;
            }}
        """)
        self.refresh_btn.clicked.connect(self.refresh_data)
        header.addWidget(self.refresh_btn)
        
        self.history_btn = QPushButton("HISTORY")
        self.history_btn.setCursor(Qt.PointingHandCursor)
        self.history_btn.setFixedSize(70, 30)
        self.history_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles.COLORS['surface_light']};
                color: {styles.COLORS['text_secondary']};
                border: 1px solid {styles.COLORS['surface_light']};
                border-radius: 15px;
                font-weight: bold;
                font-size: 10px;
            }}
            QPushButton:hover {{
                border: 1px solid {styles.COLORS['accent']};
                color: white;
            }}
        """)
        self.history_btn.clicked.connect(self.show_history)
        header.addWidget(self.history_btn)
        
        header.addSpacing(20)
        
        # self.risk_selector moved to grid body
        # header.addWidget(self.risk_selector)
        
        self.layout.addLayout(header)
        
        # Bento Grid Layout
        self.grid = QGridLayout()
        self.grid.setSpacing(20)
        self.layout.addLayout(self.grid)
        
        # 1. Morning Espresso (Large Left Block)
        self.espresso = MorningEspressoWidget()
        self.espresso.ticker_clicked.connect(self.ticker_selected.emit) # Connect signal
        self.grid.addWidget(self.espresso, 0, 0, 1, 2) # Full width top
        
        # 2. Middle Row: Sector Rotation & Earnings
        self.sector_widget = SectorRotationWidget()
        self.sector_widget.sectorClicked.connect(self.sectorClicked.emit)
        self.grid.addWidget(self.sector_widget, 1, 0, 1, 1)
        
        self.earnings_widget = EarningsWidget()
        self.grid.addWidget(self.earnings_widget, 1, 1, 1, 1)
        
        # 3. Risk Selector (New Row)
        risk_container = QWidget()
        risk_layout = QHBoxLayout(risk_container)
        risk_layout.setContentsMargins(0, 10, 0, 0)
        
        lbl = QLabel("OPPORTUNITIES")
        lbl.setStyleSheet(f"color: {styles.COLORS['accent']}; font-weight: 900; letter-spacing: 1px; font-size: 14px;")
        risk_layout.addWidget(lbl)
        risk_layout.addStretch()
        
        self.risk_selector = RiskProfileSelector()
        self.risk_selector.profileChanged.connect(self.refresh_opportunities)
        risk_layout.addWidget(self.risk_selector)
        
        self.grid.addWidget(risk_container, 2, 0, 1, 2)

        # 4. Opportunities List (Bottom Row)
        self.opp_container = QWidget()
        self.opp_layout = QVBoxLayout(self.opp_container)
        self.opp_layout.setContentsMargins(0, 0, 0, 0)
        self.opp_layout.setSpacing(15)
        
        # Scroll Area for Opportunities
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("background: transparent; border: none;")
        scroll.setWidget(self.opp_container)
        
        self.grid.addWidget(scroll, 3, 0, 1, 2) # Full width bottom
        
        # Column Stretch
        self.grid.setColumnStretch(0, 1)
        self.grid.setColumnStretch(1, 1)
        
        # Row Stretch (Make Opportunities list expand)
        self.grid.setRowStretch(3, 1)
        
        # Initial Load
        self.refresh_data()

    def refresh_data(self):
        # Show loading state
        QApplication.setOverrideCursor(Qt.WaitCursor)
        try:
            # 1. Morning Espresso & Regime
            espresso_data = data_service.get_morning_espresso_narrative()
            regime_data = data_service.detect_market_regime()
            self.espresso.set_data(espresso_data, regime_data)
            
            # 2. Sector Rotation
            sectors = data_service.analyze_sector_rotation()
            self.sector_widget.set_data(sectors)
            
            # 3. Earnings
            earnings = data_service.get_earnings_calendar()
            self.earnings_widget.set_data(earnings)
            
            # 2. Opportunities
            self.refresh_opportunities(self.risk_selector.current_profile)
            
            # 3. Update Timestamp
            now = datetime.now().strftime("%H:%M:%S")
            self.last_updated_label.setText(f"Updated: {now}")
        finally:
            QApplication.restoreOverrideCursor()

    def refresh_opportunities(self, profile):
        # Clear existing
        while self.opp_layout.count():
            item = self.opp_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        opps = data_service.get_opportunities(profile)
        
        # Check Correlation of Top Picks
        symbols = [o['symbol'] for o in opps]
        correlation = data_service.analyze_portfolio_correlation(symbols)
        
        # Update Risk Badge (reuse or create new)
        if correlation > 0.7:
             self.risk_selector.set_risk_warning(True, f"High Correlation: {correlation:.2f}")
        else:
             self.risk_selector.set_risk_warning(False)
             
        for opp in opps:
            card = OpportunityCard(opp)
            # Connect click signal
            card.clicked.connect(self.ticker_selected.emit)
            self.opp_layout.addWidget(card)
            
        self.opp_layout.addStretch()

    def show_history(self):
        self.history_window = IdeaHistoryView()
        history_data = data_service.get_idea_history()
        self.history_window.set_data(history_data)
        self.history_window.resize(600, 400)
        self.history_window.show()

class IdeaHistoryView(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {styles.COLORS['surface']}; border-radius: 10px; border: 1px solid {styles.COLORS['surface_light']};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 15, 15, 15)
        layout.setSpacing(10)
        
        header = QLabel("IDEA HISTORY")
        header.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-size: 11px; font-weight: bold; letter-spacing: 1px;")
        layout.addWidget(header)
        
        self.table = QTableWidget()
        self.table.setColumnCount(5)
        self.table.setHorizontalHeaderLabels(["Date", "Symbol", "Status", "Entry", "Result"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.table.verticalHeader().setVisible(False)
        self.table.setStyleSheet(f"""
            QTableWidget {{
                background-color: transparent;
                border: none;
                gridline-color: {styles.COLORS['surface_light']};
            }}
            QHeaderView::section {{
                background-color: {styles.COLORS['surface_light']};
                color: {styles.COLORS['text_secondary']};
                border: none;
                padding: 5px;
                font-weight: bold;
            }}
            QTableWidget::item {{
                color: white;
                padding: 5px;
            }}
        """)
        layout.addWidget(self.table)
        
    def set_data(self, history):
        self.table.setRowCount(len(history))
        for i, item in enumerate(history):
            date_str = item.get('created_at', '')[:10]
            setup = item.get('trade_setup', {})
            
            self.table.setItem(i, 0, QTableWidgetItem(date_str))
            self.table.setItem(i, 1, QTableWidgetItem(item.get('symbol', '')))
            self.table.setItem(i, 2, QTableWidgetItem(item.get('status', 'OPEN')))
            self.table.setItem(i, 3, QTableWidgetItem(f"${setup.get('entry', 0):.2f}"))
            
            # Mock Result
            result = "---"
            if item.get('status') == 'CLOSED':
                result = "+5.2%" # Mock
            self.table.setItem(i, 4, QTableWidgetItem(result))

# --- Settings View ---

class SettingsView(QWidget):
    risk_profile_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(40, 40, 40, 40)
        self.layout.setSpacing(30)
        self.layout.setAlignment(Qt.AlignTop)
        
        title = QLabel("SETTINGS")
        title.setStyleSheet(f"color: white; font-size: 24px; font-weight: 900; letter-spacing: 1px;")
        self.layout.addWidget(title)
        
        # 1. Risk Profile
        self.add_section_header("RISK PROFILE")
        
        profile_layout = QHBoxLayout()
        profile_layout.setSpacing(15)
        
        self.profiles = ["DEFENSIVE", "BALANCED", "SPECULATIVE"]
        self.profile_btns = {}
        
        for profile in self.profiles:
            btn = QPushButton(profile)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(50)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {styles.COLORS['surface_light']};
                    color: {styles.COLORS['text_secondary']};
                    border: 1px solid {styles.COLORS['surface_light']};
                    border-radius: 10px;
                    font-weight: bold;
                    font-size: 14px;
                }}
                QPushButton:checked {{
                    background-color: {styles.COLORS['accent']}20;
                    color: {styles.COLORS['accent']};
                    border: 1px solid {styles.COLORS['accent']};
                }}
                QPushButton:hover {{
                    border: 1px solid {styles.COLORS['accent']};
                }}
            """)
            btn.clicked.connect(lambda checked, p=profile: self.on_profile_changed(p))
            profile_layout.addWidget(btn)
            self.profile_btns[profile] = btn
            
        # Default to Balanced
        self.profile_btns["BALANCED"].setChecked(True)
        
        self.layout.addLayout(profile_layout)
        
        # 2. Appearance
        self.add_section_header("APPEARANCE")
        
        dark_mode_layout = QHBoxLayout()
        dark_lbl = QLabel("Dark Mode")
        dark_lbl.setStyleSheet(f"color: {styles.COLORS['text_primary']}; font-size: 16px;")
        
        self.dark_toggle = QCheckBox()
        self.dark_toggle.setChecked(True)
        self.dark_toggle.setCursor(Qt.PointingHandCursor)
        self.dark_toggle.setStyleSheet(f"""
            QCheckBox::indicator {{
                width: 40px;
                height: 20px;
                border-radius: 10px;
                background-color: {styles.COLORS['surface_light']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {styles.COLORS['accent']};
            }}
        """)
        
        dark_mode_layout.addWidget(dark_lbl)
        dark_mode_layout.addStretch()
        dark_mode_layout.addWidget(self.dark_toggle)
        
        self.layout.addLayout(dark_mode_layout)
        
        # 3. Notifications
        self.add_section_header("NOTIFICATIONS")
        
        notif_layout = QHBoxLayout()
        notif_lbl = QLabel("Enable Desktop Notifications")
        notif_lbl.setStyleSheet(f"color: {styles.COLORS['text_primary']}; font-size: 16px;")
        
        self.notif_toggle = QCheckBox()
        self.notif_toggle.setChecked(True)
        self.notif_toggle.setCursor(Qt.PointingHandCursor)
        self.notif_toggle.setStyleSheet(f"""
            QCheckBox::indicator {{
                width: 40px;
                height: 20px;
                border-radius: 10px;
                background-color: {styles.COLORS['surface_light']};
            }}
            QCheckBox::indicator:checked {{
                background-color: {styles.COLORS['accent']};
            }}
        """)
        
        notif_layout.addWidget(notif_lbl)
        notif_layout.addStretch()
        notif_layout.addWidget(self.notif_toggle)
        
        self.layout.addLayout(notif_layout)
        
        self.layout.addLayout(notif_layout)
        
        # 4. Coverage Universe (Sectors)
        self.add_section_header("COVERAGE UNIVERSE")
        
        self.sectors = ["Technology", "Financials", "Energy", "Healthcare", "Industrials", "Staples", "Utilities", "Discretionary", "Materials", "Communication"]
        self.sector_btns = {}
        
        sector_grid = QGridLayout()
        sector_grid.setSpacing(10)
        
        for i, sector in enumerate(self.sectors):
            btn = QPushButton(sector)
            btn.setCheckable(True)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFixedHeight(30)
            btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: {styles.COLORS['surface_light']};
                    color: {styles.COLORS['text_secondary']};
                    border: 1px solid {styles.COLORS['surface_light']};
                    border-radius: 15px;
                    font-size: 11px;
                    font-weight: bold;
                }}
                QPushButton:checked {{
                    background-color: {styles.COLORS['accent']}20;
                    color: {styles.COLORS['accent']};
                    border: 1px solid {styles.COLORS['accent']};
                }}
            """)
            btn.clicked.connect(self.save_state)
            
            row = i // 3
            col = i % 3
            sector_grid.addWidget(btn, row, col)
            self.sector_btns[sector] = btn
            
        self.layout.addLayout(sector_grid)
        
        # 5. RVOL Sensitivity
        self.add_section_header("RVOL SENSITIVITY")
        
        rvol_layout = QHBoxLayout()
        self.rvol_slider = QSlider(Qt.Horizontal)
        self.rvol_slider.setRange(5, 30) # 0.5 to 3.0
        self.rvol_slider.setValue(10)
        self.rvol_slider.setCursor(Qt.PointingHandCursor)
        self.rvol_slider.valueChanged.connect(self.on_rvol_changed)
        
        self.rvol_label = QLabel("1.0x")
        self.rvol_label.setStyleSheet("color: white; font-weight: bold;")
        self.rvol_label.setFixedWidth(40)
        
        rvol_layout.addWidget(self.rvol_slider)
        rvol_layout.addWidget(self.rvol_label)
        self.layout.addLayout(rvol_layout)
        
        # 6. Client Tiers (Matrix)
        self.add_section_header("CLIENT TIERS")
        
        tiers_layout = QGridLayout()
        tiers_layout.setSpacing(10)
        
        regions = ["NA", "EMEA", "APAC"]
        tiers = ["Platinum", "Gold", "Silver"]
        
        # Headers
        for i, region in enumerate(regions):
            lbl = QLabel(region)
            lbl.setAlignment(Qt.AlignCenter)
            lbl.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-size: 10px; font-weight: bold;")
            tiers_layout.addWidget(lbl, 0, i + 1)
            
        self.tier_checks = {}
        
        for r, tier in enumerate(tiers):
            lbl = QLabel(tier)
            lbl.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-size: 11px; font-weight: bold;")
            tiers_layout.addWidget(lbl, r + 1, 0)
            
            for c, region in enumerate(regions):
                chk = QCheckBox()
                chk.setCursor(Qt.PointingHandCursor)
                chk.setStyleSheet(f"""
                    QCheckBox::indicator {{
                        width: 16px; height: 16px; border-radius: 4px;
                        border: 1px solid {styles.COLORS['surface_light']};
                        background-color: transparent;
                    }}
                    QCheckBox::indicator:checked {{
                        background-color: {styles.COLORS['accent']};
                        border: 1px solid {styles.COLORS['accent']};
                    }}
                """)
                chk.stateChanged.connect(self.save_state)
                tiers_layout.addWidget(chk, r + 1, c + 1, alignment=Qt.AlignCenter)
                self.tier_checks[f"{tier}_{region}"] = chk
                
        self.layout.addLayout(tiers_layout)
        
        self.layout.addStretch()
        
        # Load Settings
        self.load_state()

    def set_risk_warning(self, visible, text=""):
        # This method should be in RiskProfileSelector, not SettingsView
        # But since I called it on self.risk_selector in TalkingPointsView, 
        # I need to implement it in RiskProfileSelector class.
        pass

    def on_rvol_changed(self, value):
        float_val = value / 10.0
        self.rvol_label.setText(f"{float_val:.1f}x")
        self.save_state()

    def load_state(self):
        settings = data_service.load_settings()
        
        # Risk Profile
        profile = settings.get("risk_profile", "BALANCED")
        if profile in self.profile_btns:
            self.on_profile_changed(profile) # This emits signal too
            
        # Appearance
        self.dark_toggle.setChecked(settings.get("dark_mode", True))
        self.notif_toggle.setChecked(settings.get("notifications", True))
        
        # Sectors
        covered = settings.get("coverage_sectors", [])
        for sector, btn in self.sector_btns.items():
            btn.setChecked(sector in covered)
            
        # RVOL
        rvol = settings.get("rvol_threshold", 1.0)
        self.rvol_slider.setValue(int(rvol * 10))
        self.rvol_label.setText(f"{rvol:.1f}x")
        
        # Client Tiers
        tiers = settings.get("client_tiers", {})
        for key, chk in self.tier_checks.items():
            # key is "Platinum_NA"
            tier, region = key.split("_")
            if tier in tiers and region in tiers[tier]:
                chk.setChecked(True)
            else:
                chk.setChecked(False)
                
    def save_state(self):
        settings = {
            "risk_profile": next((p for p, b in self.profile_btns.items() if b.isChecked()), "BALANCED"),
            "dark_mode": self.dark_toggle.isChecked(),
            "notifications": self.notif_toggle.isChecked(),
            "rvol_threshold": self.rvol_slider.value() / 10.0,
            "coverage_sectors": [s for s, b in self.sector_btns.items() if b.isChecked()],
            "client_tiers": {}
        }
        
        # Reconstruct tiers dict
        tiers_dict = {}
        for key, chk in self.tier_checks.items():
            if chk.isChecked():
                tier, region = key.split("_")
                if tier not in tiers_dict:
                    tiers_dict[tier] = []
                tiers_dict[tier].append(region)
        settings["client_tiers"] = tiers_dict
        
        data_service.save_settings(settings)

    def add_section_header(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-size: 12px; font-weight: bold; letter-spacing: 1px; margin-top: 20px;")
        self.layout.addWidget(lbl)
        
    def on_profile_changed(self, profile):
        # Enforce single selection
        for p, btn in self.profile_btns.items():
            if p != profile:
                btn.setChecked(False)
        
        self.profile_btns[profile].setChecked(True)
        self.risk_profile_changed.emit(profile)
        self.save_state()

    def add_section_header(self, text):
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-size: 12px; font-weight: bold; letter-spacing: 1px; margin-top: 20px;")
        self.layout.addWidget(lbl)

class MarketNewsWidget(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {styles.COLORS['surface']}; border-radius: 16px; border: 1px solid {styles.COLORS['surface_light']};")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(15)
        
        header = QLabel("MARKET NEWS")
        header.setStyleSheet(f"color: {styles.COLORS['accent']}; font-weight: 900; letter-spacing: 1px; font-size: 14px; border: none; background: transparent;")
        layout.addWidget(header)
        
        self.news_list = QVBoxLayout()
        self.news_list.setSpacing(10)
        layout.addLayout(self.news_list)
        
        layout.addStretch()
        
        # Initial Load
        # self.load_news() # Deferred to prevent blocking startup
        
    def load_news(self):
        # Clear
        while self.news_list.count():
            item = self.news_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Fetch Market News (using ^GSPC as proxy for general market news)
        # In real app, might use a specific "general news" endpoint
        news = data_service.fetch_news_for_symbol('^GSPC', lookback_hours=24)
        
        for i, event in enumerate(news[:3]): # Top 3
            item = NewsItemWidget(event)
            # Make it slightly more compact for dashboard?
            # Reuse NewsItemWidget is fine
            self.news_list.addWidget(item)
            
        if not news:
            lbl = QLabel("No market news available.")
            lbl.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-style: italic; border: none; background: transparent;")
            self.news_list.addWidget(lbl)

class SectorView(QFrame):
    back_clicked = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet(f"background-color: {styles.COLORS['background']};")
        
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(20, 20, 20, 20)
        self.layout.setSpacing(20)
        
        # Header
        header_row = QHBoxLayout()
        
        back_btn = QPushButton("← BACK")
        back_btn.setCursor(Qt.PointingHandCursor)
        back_btn.setFixedSize(80, 30)
        back_btn.clicked.connect(self.back_clicked.emit)
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {styles.COLORS['surface']};
                color: {styles.COLORS['text_secondary']};
                border: 1px solid {styles.COLORS['surface_light']};
                border-radius: 4px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {styles.COLORS['surface_light']};
                color: white;
            }}
        """)
        header_row.addWidget(back_btn)
        
        self.title_lbl = QLabel("SECTOR VIEW")
        self.title_lbl.setStyleSheet("color: white; font-size: 24px; font-weight: 900; letter-spacing: 1px;")
        header_row.addWidget(self.title_lbl)
        
        header_row.addStretch()
        
        self.price_lbl = QLabel("--")
        self.price_lbl.setStyleSheet("color: white; font-size: 24px; font-weight: bold; font-family: 'Consolas';")
        header_row.addWidget(self.price_lbl)
        
        self.change_lbl = QLabel("--")
        self.change_lbl.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-size: 18px; font-weight: bold;")
        header_row.addWidget(self.change_lbl)
        
        self.layout.addLayout(header_row)
        
        # Stats Grid
        stats_container = QFrame()
        stats_container.setStyleSheet(f"background-color: {styles.COLORS['surface']}; border-radius: 10px; border: 1px solid {styles.COLORS['surface_light']};")
        stats_layout = QHBoxLayout(stats_container)
        stats_layout.setContentsMargins(20, 20, 20, 20)
        stats_layout.setSpacing(40)
        
        self.stats_labels = {}
        for key in ["YIELD", "AVG P/E", "BETA", "ASSETS"]:
            col = QVBoxLayout()
            lbl = QLabel(key)
            lbl.setStyleSheet(f"color: {styles.COLORS['text_secondary']}; font-size: 10px; font-weight: bold;")
            col.addWidget(lbl, alignment=Qt.AlignCenter)
            
            val = QLabel("--")
            val.setStyleSheet("color: white; font-size: 16px; font-weight: bold; font-family: 'Consolas';")
            col.addWidget(val, alignment=Qt.AlignCenter)
            self.stats_labels[key] = val
            stats_layout.addLayout(col)
            
        self.layout.addWidget(stats_container)
        
        # Top Performers
        perf_header = QLabel("TOP PERFORMERS")
        perf_header.setStyleSheet(f"color: {styles.COLORS['accent']}; font-weight: 900; letter-spacing: 1px; font-size: 14px;")
        self.layout.addWidget(perf_header)
        
        self.performers_scroll = QScrollArea()
        self.performers_scroll.setWidgetResizable(True)
        self.performers_scroll.setFixedHeight(220) # Height for cards
        self.performers_scroll.setStyleSheet("background: transparent; border: none;")
        self.performers_scroll.setVerticalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.performers_container = QWidget()
        self.performers_layout = QHBoxLayout(self.performers_container)
        self.performers_layout.setContentsMargins(0, 0, 0, 0)
        self.performers_layout.setSpacing(15)
        self.performers_layout.addStretch()
        
        self.performers_scroll.setWidget(self.performers_container)
        self.layout.addWidget(self.performers_scroll)
        
        # News
        news_header = QLabel("SECTOR NEWS")
        news_header.setStyleSheet(f"color: {styles.COLORS['accent']}; font-weight: 900; letter-spacing: 1px; font-size: 14px;")
        self.layout.addWidget(news_header)
        
        self.news_widget = NewsTimelineWidget()
        self.layout.addWidget(self.news_widget)
        
    def set_data(self, sector_data, top_performers):
        # Header
        self.title_lbl.setText(sector_data.get('name', 'SECTOR').upper())
        
        price = sector_data.get('price', 0)
        change = sector_data.get('change', 0)
        
        self.price_lbl.setText(f"${price:.2f}")
        
        color = styles.COLORS['success'] if change >= 0 else styles.COLORS['danger']
        sign = "+" if change >= 0 else ""
        self.change_lbl.setText(f"{sign}{change:.2f}%")
        self.change_lbl.setStyleSheet(f"color: {color}; font-size: 18px; font-weight: bold;")
        
        # Stats
        self.stats_labels["YIELD"].setText(f"{sector_data.get('yield', 0):.2f}%")
        self.stats_labels["AVG P/E"].setText(f"{sector_data.get('pe', 0):.1f}")
        self.stats_labels["BETA"].setText(f"{sector_data.get('beta', 1.0):.2f}")
        
        assets = sector_data.get('assets', 0)
        if assets > 1e9:
            assets_str = f"${assets/1e9:.1f}B"
        elif assets > 1e6:
            assets_str = f"${assets/1e6:.1f}M"
        else:
            assets_str = f"${assets:,.0f}"
        self.stats_labels["ASSETS"].setText(assets_str)
        
        # Top Performers
        # Clear existing
        while self.performers_layout.count() > 1: # Keep stretch at end
            item = self.performers_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
                
        # Add new cards
        # Insert before stretch (which is at index count-1)
        for stock in top_performers:
            card = TickerCard(stock)
            card.setFixedSize(160, 200) # Compact card
            self.performers_layout.insertWidget(self.performers_layout.count()-1, card)
            
        # News (Mock for now, or fetch if available)
        # self.news_widget.load_news(sector_data.get('symbol')) # If we had sector news

