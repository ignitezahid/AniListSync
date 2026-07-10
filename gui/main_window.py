from pathlib import Path
import json
import sys

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout,
    QListWidget, QListWidgetItem, QStackedWidget,
    QSystemTrayIcon, QMenu,
)
from PyQt6.QtCore import Qt, QSize, QTimer
from PyQt6.QtGui import QFont, QIcon, QPainter, QColor, QPixmap


DATA_DIR = "data"
TG_STATUS_FILE = "tg_status.json"


NAV_ITEMS = [
    ("\U0001f4ca  Dashboard",   "dashboard"),
    ("\U0001f504  Sync",        "sync"),
    ("\U0001f916  Automation",  "automation"),
    ("\U0001f50d  Search",      "search"),
    ("\U0001f4da  Library",     "library"),
    ("\U0001f4c1  Collections", "collections"),
    ("\U0001f4ca  Statistics",  "statistics"),
    ("\U0001f50d  Compare",     "compare"),
    ("\U0001f527  Repair",      "repair"),
    ("\U0001f680  Bulk Ops",    "bulk"),
    ("\u2699\ufe0f  Settings",  "settings"),
    ("\U0001f9e9  Plugins",     "plugins"),
    ("\U0001f4cb  About",       "about"),
    ("\U0001f6f8  Tools",       "tools"),
]

_WIDGET_MAP = {
    "dashboard": lambda: __import__("gui.dashboard_widget", fromlist=["DashboardWidget"]).DashboardWidget(),
    "sync": lambda: __import__("gui.sync_widget", fromlist=["SyncWidget"]).SyncWidget(),
    "automation": lambda: __import__("gui.automation_widget", fromlist=["AutomationWidget"]).AutomationWidget(),
    "search": lambda: __import__("gui.search_widget", fromlist=["SearchWidget"]).SearchWidget(),
    "library": lambda: __import__("gui.library_widget", fromlist=["LibraryWidget"]).LibraryWidget(),
    "collections": lambda: __import__("gui.collections_widget", fromlist=["CollectionsWidget"]).CollectionsWidget(),
    "statistics": lambda: __import__("gui.statistics_widget", fromlist=["StatisticsWidget"]).StatisticsWidget(),
    "compare": lambda: __import__("gui.compare_widget", fromlist=["CompareWidget"]).CompareWidget(),
    "repair": lambda: __import__("gui.repair_widget", fromlist=["RepairWidget"]).RepairWidget(),
    "bulk": lambda: __import__("gui.bulkops_widget", fromlist=["BulkOpsWidget"]).BulkOpsWidget(),
    "settings": lambda: __import__("gui.settings_widget", fromlist=["SettingsWidget"]).SettingsWidget(),
    "plugins": lambda: __import__("gui.plugin_widget", fromlist=["PluginWidget"]).PluginWidget(),
    "about": lambda: __import__("gui.about_widget", fromlist=["AboutWidget"]).AboutWidget(),
    "tools": lambda: __import__("gui.tools_widget", fromlist=["ToolsWidget"]).ToolsWidget(),
}


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self._started = False
        self.setWindowTitle("AniListSync")
        self.setMinimumSize(1024, 680)
        self.resize(1280, 800)

        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout()
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)

        self._nav = QListWidget()
        self._nav.setFixedWidth(200)
        self._nav.setIconSize(QSize(20, 20))

        font = QFont("Segoe UI", 13)
        self._nav.setFont(font)

        for label, _ in NAV_ITEMS:
            item = QListWidgetItem(label)
            self._nav.addItem(item)

        self._nav.currentRowChanged.connect(self._nav_changed)

        main_layout.addWidget(self._nav)

        self._stack = QStackedWidget()
        self._pages: dict[str, QWidget] = {}

        self._stack.addWidget(QWidget())
        self._nav.blockSignals(True)
        self._nav.setCurrentRow(0)
        self._nav.blockSignals(False)

        main_layout.addWidget(self._stack)
        central.setLayout(main_layout)

        self._get_or_create("dashboard")
        self._stack.setCurrentWidget(self._pages["dashboard"])

        QTimer.singleShot(200, self._pages["dashboard"]._check_tg_async)
        QTimer.singleShot(300, self._create_tray)

    def _get_or_create(self, key: str) -> QWidget:
        if key not in self._pages:
            self._pages[key] = _WIDGET_MAP[key]()
            self._stack.addWidget(self._pages[key])
        return self._pages[key]

    def _nav_changed(self, index: int):
        if 0 <= index < len(NAV_ITEMS):
            _, key = NAV_ITEMS[index]
            w = self._get_or_create(key)
            self._stack.setCurrentWidget(w)

    def switch_tab(self, key: str):
        for i, (_, k) in enumerate(NAV_ITEMS):
            if k == key:
                self._get_or_create(key)
                self._nav.blockSignals(True)
                self._nav.setCurrentRow(i)
                self._nav.blockSignals(False)
                self._stack.setCurrentWidget(self._pages[key])
                return

    # ── System Tray ──────────────────────────────────────

    def _create_tray(self):
        """Create a system tray icon with a theme-aware colored icon."""
        self._tray = QSystemTrayIcon(self)
        self._update_tray_icon()

        tray_menu = QMenu()
        show_action = tray_menu.addAction("\U0001f4ca  Show AniListSync")
        show_action.triggered.connect(self._show_from_tray)
        tray_menu.addSeparator()
        quit_action = tray_menu.addAction("\u274c  Quit")
        quit_action.triggered.connect(self.close)

        self._tray.setContextMenu(tray_menu)
        self._tray.activated.connect(self._tray_activated)
        self._tray.setToolTip("AniListSync")
        self._tray.show()

    def _update_tray_icon(self):
        """Set the window and tray icon from app_icon.ico.
        Searches the working directory and MEIPASS for the icon file."""
        icon = QIcon()
        candidates = [Path("app_icon.ico")]
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            candidates.append(Path(sys._MEIPASS) / "app_icon.ico")
        for path in candidates:
            if path.exists():
                icon = QIcon(str(path))
                break
        else:
            # Fallback: draw a simple colored circle
            size = 64
            pm = QPixmap(size, size)
            pm.fill(Qt.GlobalColor.transparent)
            painter = QPainter(pm)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QColor("#7aa2f7"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(2, 2, size - 4, size - 4)
            painter.end()
            icon = QIcon(pm)
        if hasattr(self, '_tray'):
            self._tray.setIcon(icon)
        self.setWindowIcon(icon)

    def _show_from_tray(self):
        self.showNormal()
        self.raise_()
        self.activateWindow()

    def _tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self._show_from_tray()

    def closeEvent(self, event):
        from core.plugin_loader import plugin_manager
        plugin_manager.call_hook("on_shutdown")
        try:
            import asyncio
            try:
                asyncio.get_running_loop().stop()
            except RuntimeError:
                pass
        except Exception:
            pass
        event.accept()
