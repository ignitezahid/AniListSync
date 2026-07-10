from PyQt6.QtGui import QPalette, QColor
from PyQt6.QtCore import Qt

DARK_STYLESHEET = """
/* ── Base ────────────────────────────────────────────── */
QMainWindow {
    background-color: #1a1b26;
    color: #c0caf5;
    font-family: 'Segoe UI', 'SF Pro Display', sans-serif;
    font-size: 13px;
}

/* Layout containers should be transparent — content inherits from window */
QFrame {
    background: transparent;
}

/* ── Menu ────────────────────────────────────────────── */
QMenuBar {
    background-color: #16161e;
    color: #c0caf5;
    border-bottom: 1px solid #2f3340;
}
QMenuBar::item:selected {
    background-color: #2f3340;
}
QMenu {
    background-color: #1a1b26;
    color: #c0caf5;
    border: 1px solid #2f3340;
}
QMenu::item:selected {
    background-color: #2f3340;
}

/* ── Labels ──────────────────────────────────────────── */
QLabel {
    background: transparent;
}
QLabel#heading {
    font-size: 26px;
    font-weight: 700;
    color: #7aa2f7;
    padding: 12px 0 4px 0;
}
QLabel#subheading {
    font-size: 13px;
    color: #565f89;
    padding: 0 0 12px 0;
}
QLabel#section {
    font-size: 11px;
    font-weight: 600;
    color: #a9b1d6;
    padding: 2px 0 2px 0;
    letter-spacing: 0.5px;
}
QLabel#value {
    font-size: 13px;
    color: #c0caf5;
}
QLabel#label {
    font-size: 13px;
    color: #565f89;
}

/* ── Buttons ─────────────────────────────────────────── */
QPushButton {
    background-color: #2f3340;
    color: #c0caf5;
    border: 1px solid #3b3f52;
    border-radius: 6px;
    padding: 7px 18px;
    font-size: 13px;
    min-height: 18px;
}
QPushButton:hover {
    background-color: #3b3f52;
    border-color: #565f89;
}
QPushButton:pressed {
    background-color: #1f2335;
    padding-top: 8px;
    padding-bottom: 6px;
}
QPushButton:disabled {
    background-color: #1a1b26;
    color: #565f89;
    border-color: #2f3340;
}
QPushButton#primary {
    background-color: #7aa2f7;
    color: #1a1b26;
    font-weight: 600;
    border: none;
    min-height: 20px;
}
QPushButton#primary:hover {
    background-color: #89b4fa;
}
QPushButton#primary:pressed {
    background-color: #6c8ed9;
    padding-top: 8px;
    padding-bottom: 6px;
}
QPushButton#primary:disabled {
    background-color: #2f3340;
    color: #565f89;
}
QPushButton#danger {
    background-color: #f7768e;
    color: #1a1b26;
    font-weight: 600;
    border: none;
}
QPushButton#danger:hover {
    background-color: #ff9eaf;
}
QPushButton#success {
    background-color: #9ece6a;
    color: #1a1b26;
    font-weight: 600;
    border: none;
}

/* ── Navigation Sidebar ──────────────────────────────── */
QListWidget {
    background-color: #16161e;
    border: none;
    border-right: 1px solid #2f3340;
    color: #565f89;
    font-size: 13px;
    outline: none;
    padding: 4px 0;
}
QListWidget::item {
    padding: 10px 18px;
    border-radius: 0;
    border-left: 3px solid transparent;
}
QListWidget::item:selected {
    background-color: #1f2335;
    color: #7aa2f7;
    border-left: 3px solid #7aa2f7;
}
QListWidget::item:hover:!selected {
    background-color: #1a1b26;
    color: #a9b1d6;
}

/* ── Tabs ────────────────────────────────────────────── */
QTabWidget::pane {
    border: 1px solid #2f3340;
    border-radius: 6px;
    background-color: #1a1b26;
}
QTabBar::tab {
    background-color: #16161e;
    color: #565f89;
    border: 1px solid #2f3340;
    border-bottom: none;
    border-top-left-radius: 6px;
    border-top-right-radius: 6px;
    padding: 8px 18px;
    margin-right: 2px;
}
QTabBar::tab:selected {
    background-color: #1a1b26;
    color: #7aa2f7;
    border-bottom: 1px solid #1a1b26;
}
QTabBar::tab:hover:!selected {
    color: #a9b1d6;
}

/* ── Group Box ───────────────────────────────────────── */
QGroupBox {
    border: 1px solid rgba(47, 51, 64, 0.4);
    border-radius: 8px;
    margin-top: 16px;
    padding: 18px 14px 12px 14px;
    font-weight: 700;
    font-size: 14px;
    color: #a9b1d6;
    background-color: rgba(31, 35, 53, 0.3);
}
QGroupBox::title {
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 2px 8px;
    background: transparent;
}

/* ── Inputs ──────────────────────────────────────────── */
QLineEdit, QSpinBox, QDoubleSpinBox, QComboBox, QTextEdit, QPlainTextEdit {
    background-color: #1f2335;
    color: #c0caf5;
    border: 1px solid #2f3340;
    border-radius: 6px;
    padding: 7px 10px;
    font-size: 13px;
}
QLineEdit:focus, QSpinBox:focus, QDoubleSpinBox:focus, QComboBox:focus, QTextEdit:focus, QPlainTextEdit:focus {
    border-color: #7aa2f7;
}
QComboBox::drop-down {
    border: none;
    padding-right: 8px;
}
QComboBox QAbstractItemView {
    background-color: #1a1b26;
    color: #c0caf5;
    selection-background-color: #2f3340;
    border: 1px solid #2f3340;
    border-radius: 4px;
}

/* ── Checkbox ────────────────────────────────────────── */
QCheckBox {
    spacing: 8px;
    color: #c0caf5;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 4px;
    border: 1px solid #3b3f52;
    background-color: #1f2335;
}
QCheckBox::indicator:checked {
    background-color: #7aa2f7;
    border-color: #7aa2f7;
}
QCheckBox::indicator:hover {
    border-color: #565f89;
}

/* ── Scrollbars ──────────────────────────────────────── */
QScrollBar:vertical {
    background-color: transparent;
    width: 8px;
    border: none;
    margin: 0;
}
QScrollBar::handle:vertical {
    background-color: #2f3340;
    min-height: 30px;
    border-radius: 4px;
}
QScrollBar::handle:vertical:hover {
    background-color: #3b3f52;
}
QScrollBar::handle:vertical:pressed {
    background-color: #565f89;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0;
}
QScrollBar:horizontal {
    background-color: transparent;
    height: 8px;
    border: none;
    margin: 0;
}
QScrollBar::handle:horizontal {
    background-color: #2f3340;
    min-width: 30px;
    border-radius: 4px;
}
QScrollBar::handle:horizontal:hover {
    background-color: #3b3f52;
}
QScrollBar::handle:horizontal:pressed {
    background-color: #565f89;
}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
    width: 0;
}

/* ── Progress Bar ────────────────────────────────────── */
QProgressBar {
    border: 1px solid #2f3340;
    border-radius: 5px;
    text-align: center;
    color: #c0caf5;
    background-color: #1f2335;
    height: 22px;
    font-size: 12px;
}
QProgressBar::chunk {
    background-color: #7aa2f7;
    border-radius: 4px;
}

/* ── Status Bar ──────────────────────────────────────── */
QStatusBar {
    background-color: #16161e;
    color: #565f89;
    border-top: 1px solid #2f3340;
    font-size: 12px;
    min-height: 24px;
}
QStatusBar::item {
    border: none;
}

/* ── Splitter ────────────────────────────────────────── */
QSplitter::handle {
    background-color: #2f3340;
}

/* ── Tool Tip ────────────────────────────────────────── */
QToolTip {
    background-color: #1a1b26;
    color: #c0caf5;
    border: 1px solid #3b3f52;
    border-radius: 4px;
    padding: 6px 10px;
    font-size: 12px;
}

/* ── Table ───────────────────────────────────────────── */
QTableWidget {
    background-color: #1a1b26;
    alternate-background-color: #13141E;
    color: #c0caf5;
    border: 1px solid #2f3340;
    border-radius: 6px;
    gridline-color: #24283b;
}
QTableWidget::item {
    padding: 6px 10px;
}
QTableWidget::item:selected {
    background-color: #2f3340;
    color: #7aa2f7;
}
QTableWidget::item:hover:!selected {
    background-color: #1f2335;
}
QHeaderView::section {
    background-color: #16161e;
    color: #565f89;
    border: none;
    border-bottom: 1px solid #2f3340;
    padding: 7px 10px;
    font-weight: 600;
}

/* ── StatCard ────────────────────────────────────────── */
StatCard {
    background-color: rgba(31, 35, 53, 0.55);
    border: 1px solid rgba(47, 51, 64, 0.4);
    border-radius: 10px;
    padding: 14px 16px;
}
StatCard:hover {
    border-color: rgba(59, 63, 82, 0.6);
    background-color: rgba(34, 39, 57, 0.65);
}
"""

THEME_ACCENTS = {
    "Light": "#4A90D9",
    "Dark": "#58A6FF",
    "Dracula": "#BD93F9",
    "Catppuccin": "#89B4FA",
    "Nord": "#88C0D0",
    "Tokyo Night": "#7AA2F7",
    "Solarized Light": "#268BD2",
    "Matrix": "#00FF41",
    "Gruvbox": "#FABD2F",
    "Default": "#7AA2F7",
}

THEME_PALETTES = {
    "Light": {
        "bg": "#F5F5F5", "darker": "#E8E8E8", "light": "#FFFFFF",
        "medium": "#D0D0D0", "medium_light": "#B8B8B8", "hover": "#F0F0F0",
        "text": "#1A1A1A", "text_secondary": "#444444", "text_muted": "#5A5A5A",
    },
    "Dark": {
        "bg": "#0D1117", "darker": "#0A0C10", "light": "#161B22",
        "medium": "#21262D", "medium_light": "#30363D", "hover": "#1C2128",
        "text": "#E6EDF3", "text_secondary": "#8B949E", "text_muted": "#484F58",
    },
    "Dracula": {
        "bg": "#282A36", "darker": "#21222C", "light": "#313244",
        "medium": "#3B3D4E", "medium_light": "#45475A", "hover": "#2C2E3D",
    },
    "Catppuccin": {
        "bg": "#1E1E2E", "darker": "#181825", "light": "#252536",
        "medium": "#313244", "medium_light": "#45475A", "hover": "#212132",
    },
    "Nord": {
        "bg": "#2E3440", "darker": "#242933", "light": "#373E4D",
        "medium": "#434C5E", "medium_light": "#4C566A", "hover": "#323946",
    },
    "Tokyo Night": {
        "bg": "#1A1B26", "darker": "#13141E", "light": "#24283B",
        "medium": "#2F3340", "medium_light": "#3B3F52", "hover": "#222739",
    },
    "Solarized Light": {
        "bg": "#E8DCC4", "darker": "#D5C8A8", "light": "#FDF6E3",
        "medium": "#EEE8D5", "medium_light": "#E0D8C8", "hover": "#F2E9D3",
    },
    "Matrix": {
        "bg": "#001100", "darker": "#000800", "light": "#002200",
        "medium": "#003300", "medium_light": "#004400", "hover": "#001900",
    },
    "Gruvbox": {
        "bg": "#282828", "darker": "#1D2021", "light": "#32302F",
        "medium": "#3C3836", "medium_light": "#504945", "hover": "#2D2C2B",
    },
    "Default": {
        "bg": "#1A1B26", "darker": "#13141E", "light": "#24283B",
        "medium": "#2F3340", "medium_light": "#3B3F52", "hover": "#222739",
    },
}


# Mutable log stylesheet updated on each theme change so inline log widgets stay in sync.
_LOG_STYLESHEET = """
    QTextEdit {
        background-color: #0f0f1a;
        color: #a9b1d6;
        border: 1px solid #2f3340;
        border-radius: 6px;
        padding: 10px;
        font-family: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', monospace;
        font-size: 12px;
    }
"""

# Current theme glass colors for inline stylesheets (StatCard, QGroupBox).
_GLASS_LIGHT_RGB = "31, 35, 53"
_GLASS_MEDIUM_RGB = "47, 51, 64"
_GLASS_MEDIUM_LIGHT_RGB = "59, 63, 82"
_GLASS_HOVER_RGB = "34, 39, 57"


def get_log_stylesheet() -> str:
    """Return the current log stylesheet matching the active theme."""
    return _LOG_STYLESHEET


def get_glass_rgb(key: str) -> str:
    """Return a current theme glass RGB string ('r, g, b').
    Keys: light, medium, medium_light, hover."""
    return {
        "light": _GLASS_LIGHT_RGB,
        "medium": _GLASS_MEDIUM_RGB,
        "medium_light": _GLASS_MEDIUM_LIGHT_RGB,
        "hover": _GLASS_HOVER_RGB,
    }.get(key, _GLASS_LIGHT_RGB)


def _hex_to_rgb_str(hex_color: str) -> str:
    """Convert '#1f2335' to '31, 35, 53'."""
    h = hex_color.lstrip("#")
    return f"{int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}"


def _theme_qss(accent: str, theme: str = "Default") -> str:
    p = THEME_PALETTES.get(theme, THEME_PALETTES["Default"])
    qss = DARK_STYLESHEET
    # Background + border replacements
    qss = qss.replace("#7aa2f7", accent.lower())
    qss = qss.replace("#1a1b26", p["bg"])
    qss = qss.replace("#16161e", p["darker"])
    qss = qss.replace("#1f2335", p["light"])
    qss = qss.replace("#2f3340", p["medium"])
    qss = qss.replace("#3b3f52", p["medium_light"])
    qss = qss.replace("#222739", p["hover"])
    qss = qss.replace("alternate-background-color: #13141E", f"alternate-background-color: {p['darker']}")
    # Glass color replacements
    light_rgb = _hex_to_rgb_str(p["light"])
    medium_rgb = _hex_to_rgb_str(p["medium"])
    medium_light_rgb = _hex_to_rgb_str(p["medium_light"])
    hover_rgb = _hex_to_rgb_str(p["hover"])
    qss = qss.replace("31, 35, 53, 0.55", f"{light_rgb}, 0.55")  # StatCard bg
    qss = qss.replace("31, 35, 53, 0.3", f"{light_rgb}, 0.3")   # QGroupBox bg
    qss = qss.replace("47, 51, 64, 0.4", f"{medium_rgb}, 0.4")  # border (StatCard + QGroupBox)
    qss = qss.replace("59, 63, 82, 0.6", f"{medium_light_rgb}, 0.6")  # StatCard hover border
    qss = qss.replace("34, 39, 57, 0.65", f"{hover_rgb}, 0.65")  # StatCard hover bg
    # Text color replacements (with backward-compatible defaults)
    text = p.get("text", "#c0caf5")
    text_secondary = p.get("text_secondary", "#a9b1d6")
    text_muted = p.get("text_muted", "#565f89")
    qss = qss.replace("#c0caf5", text)
    qss = qss.replace("#a9b1d6", text_secondary)
    qss = qss.replace("#565f89", text_muted)
    # Bold all text in Light theme for crisp readability
    if theme == "Light":
        qss += """
QLabel, QPushButton, QLineEdit, QSpinBox, QDoubleSpinBox,
QTextEdit, QPlainTextEdit, QCheckBox, QComboBox,
QTabBar::tab, QListWidget, QListWidget::item,
QTableWidget::item, QHeaderView::section, QGroupBox,
QGroupBox::title, QStatusBar, QMenuBar, QMenu, QMenu::item,
QProgressBar, QToolTip {
    font-weight: 600 !important;
}
"""
    return qss


def apply_dark_theme(app, theme: str = "Default", bg: str | None = None):
    accent = THEME_ACCENTS.get(theme, THEME_ACCENTS["Default"])
    p = THEME_PALETTES.get(theme, THEME_PALETTES["Default"])
    app.setStyleSheet(_theme_qss(accent, theme))
    # Read text colors from palette (backward-compatible defaults)
    text_color = p.get("text", "#c0caf5")
    text_muted = p.get("text_muted", "#565f89")
    palette = QPalette()
    palette.setColor(QPalette.ColorRole.Window, QColor(p["bg"]))
    palette.setColor(QPalette.ColorRole.WindowText, QColor(text_color))
    palette.setColor(QPalette.ColorRole.Base, QColor(p["light"]))
    palette.setColor(QPalette.ColorRole.AlternateBase, QColor(p["darker"]))
    palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(p["bg"]))
    palette.setColor(QPalette.ColorRole.ToolTipText, QColor(text_color))
    palette.setColor(QPalette.ColorRole.Text, QColor(text_color))
    palette.setColor(QPalette.ColorRole.Button, QColor(p["medium"]))
    palette.setColor(QPalette.ColorRole.ButtonText, QColor(text_color))
    palette.setColor(QPalette.ColorRole.Highlight, QColor(accent))
    # Use white highlighted text for light themes, matching bg for dark themes
    bg_qcolor = QColor(p["bg"])
    if bg_qcolor.lightness() > 128:
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#1A1A1A"))
    else:
        palette.setColor(QPalette.ColorRole.HighlightedText, QColor(p["bg"]))
    app.setPalette(palette)

    # Update mutable log stylesheet so inline QTextEdits match the new theme.
    global _LOG_STYLESHEET
    text_secondary = p.get("text_secondary", "#a9b1d6")
    _LOG_STYLESHEET = f"""
    QTextEdit {{
        background-color: {p['darker']};
        color: {text_secondary};
        border: 1px solid {p['medium']};
        border-radius: 6px;
        padding: 10px;
        font-family: 'Cascadia Code', 'Fira Code', 'JetBrains Mono', monospace;
        font-size: 12px;
    }}
"""

    # Update glass RGB values for inline StatCard / QGroupBox stylesheets.
    global _GLASS_LIGHT_RGB, _GLASS_MEDIUM_RGB, _GLASS_MEDIUM_LIGHT_RGB, _GLASS_HOVER_RGB
    _GLASS_LIGHT_RGB = _hex_to_rgb_str(p["light"])
    _GLASS_MEDIUM_RGB = _hex_to_rgb_str(p["medium"])
    _GLASS_MEDIUM_LIGHT_RGB = _hex_to_rgb_str(p["medium_light"])
    _GLASS_HOVER_RGB = _hex_to_rgb_str(p["hover"])


def refresh_inline_styles(app):
    """Call reapply_theme() on all page widgets after a theme switch."""
    for w in app.allWidgets():
        if hasattr(w, "reapply_theme"):
            try:
                w.reapply_theme()
            except Exception:
                pass
