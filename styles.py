
# styles.py

COLORS = {
    "background": "#060607",       # Deep Obsidian
    "surface": "#141415",          # Surface Layer
    "surface_light": "#27272A",    # Borders / Inputs
    "text_primary": "#FFFFFF",     # Bright White
    "text_secondary": "#71717A",   # Muted Metallic Gray
    "accent": "#00FFC2",           # Teal
    "danger": "#FF6B6B",           # Crimson
    "success": "#00FFC2",          # Teal (Same as accent for consistency)
    "neon_purple": "#BC13FE",      # RVOL
    "defensive": "#3B82F6",        # Blue
    "balanced": "#F59E0B",         # Amber
    "speculative": "#EC4899",      # Pink
    "news_accent": "#8B5CF6",      # Violet
    "input_bg": "#27272A",
    "input_focus": "rgba(0, 255, 194, 0.2)",
    "sidebar_active_bg": "#161b22",
    "sidebar_active_accent": "#2F80ED",
    "master_surface": "#141415",
    "sub_surface": "#1C1C1E",
    "sub_surface_border": "#2C2C2E",
    "grid_line": "#27272A" # Added missing key
}

FONTS = {
    "primary": "Inter", # Or Geist if available, falling back to system sans
    "monospace": "Consolas"
}

TRADER_THEME = f"""
    QMainWindow {{
        background-color: {COLORS["background"]};
    }}
    QWidget {{
        background-color: {COLORS["background"]};
        color: {COLORS["text_primary"]};
        font-family: '{FONTS["primary"]}', sans-serif;
    }}
    QFrame#Card, QFrame#Sidebar {{
        background-color: {COLORS["surface"]};
        border: 1px solid {COLORS["surface_light"]};
        border-radius: 12px;
    }}
    QLabel {{
        color: {COLORS["text_primary"]};
        background-color: transparent;
    }}
    QLabel#SectionTitle {{
        color: {COLORS["text_secondary"]};
        font-weight: bold;
        font-size: 12px;
        letter-spacing: 1px;
        text-transform: uppercase;
        border: none;
    }}
    QPushButton#SidebarBtn {{
        background-color: transparent;
        color: {COLORS["text_secondary"]};
        text-align: left;
        padding: 12px 20px;
        border: none;
        border-radius: 8px;
        font-weight: 600;
        font-size: 14px;
    }}
    QPushButton#SidebarBtn:hover {{
        background-color: {COLORS["surface_light"]};
        color: {COLORS["text_primary"]};
    }}
    QPushButton#SidebarBtn:checked {{
        background-color: {COLORS["surface_light"]}80; /* Transparent surface */
        color: {COLORS["accent"]};
        border-left: 3px solid {COLORS["accent"]};
    }}
    QLineEdit {{
        background-color: {COLORS["input_bg"]};
        color: {COLORS["text_primary"]};
        border: 1px solid {COLORS["surface_light"]};
        border-radius: 6px;
        padding: 8px;
        font-size: 13px;
    }}
    QLineEdit:focus {{
        border: 1px solid {COLORS["accent"]};
        background-color: {COLORS["surface_light"]};
    }}
    QScrollBar:vertical {{
        border: none;
        background: {COLORS["background"]};
        width: 8px;
        margin: 0px;
    }}
    QScrollBar::handle:vertical {{
        background: {COLORS["surface_light"]};
        min-height: 20px;
        border-radius: 4px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
        height: 0px;
    }}
"""
