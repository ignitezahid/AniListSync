import sys
import os
import asyncio
import ctypes
import warnings

warnings.filterwarnings("ignore", category=ResourceWarning, message=".*ProactorBasePipeTransport.*")
warnings.filterwarnings("ignore", category=ResourceWarning, message=".*unclosed transport.*")

from utils.startup import startup_checks

from PyQt6.QtWidgets import QApplication, QWidget, QLabel, QVBoxLayout, QSplashScreen, QMessageBox
from PyQt6.QtGui import QFont, QIcon, QPainter, QColor, QPixmap
from PyQt6.QtCore import Qt, QTimer
import qasync

from gui.theme import apply_dark_theme, THEME_PALETTES
from gui.main_window import MainWindow
from core.plugin_loader import plugin_manager
from utils.ui import reload_theme


def launch_gui():
    startup_checks()

    app = QApplication(sys.argv)
    app.setApplicationName("AniListSync")
    app.setOrganizationName("ignitezahid")
    app.setStyle("Fusion")

    font = QFont("Segoe UI", 13)
    app.setFont(font)
    apply_dark_theme(app)

    ico_path = os.path.join(os.getcwd(), "app_icon.ico")
    if os.path.exists(ico_path):
        app.setWindowIcon(QIcon(ico_path))

    # ── Splash screen ──────────────────────────────────────
    p = THEME_PALETTES.get("Default", THEME_PALETTES["Default"])
    splash_pm = QPixmap(1280, 800)
    splash_pm.fill(QColor(p["bg"]))
    painter = QPainter(splash_pm)
    painter.setPen(QColor("#7aa2f7"))
    fnt = QFont("Segoe UI", 58, QFont.Weight.Bold)
    painter.setFont(fnt)
    painter.drawText(splash_pm.rect(), Qt.AlignmentFlag.AlignCenter, "AniListSync")
    painter.end()
    splash = QSplashScreen(splash_pm)
    splash.show()
    app.processEvents()

    # ── Fast initialisation with splash status messages ────
    splash.showMessage("Discovering plugins...",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, QColor("#565f89"))
    app.processEvents()
    plugin_manager.discover()

    splash.showMessage("Applying theme...",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, QColor("#565f89"))
    app.processEvents()
    reload_theme()

    splash.showMessage("Initialising Telegram...",
        Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignHCenter, QColor("#565f89"))
    app.processEvents()
    from telegram_client import init_accounts
    init_accounts()

    loop = qasync.QEventLoop(app)
    asyncio.set_event_loop(loop)

    window = MainWindow()
    if os.path.exists(ico_path):
        window.setWindowIcon(QIcon(ico_path))

    def _force_taskbar_icon():
        try:
            hwnd = int(window.winId())
            hicon = ctypes.windll.user32.LoadImageW(
                0, ico_path, 1, 0, 0, 0x00000010
            )
            if hicon:
                ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 0, hicon)
                ctypes.windll.user32.SendMessageW(hwnd, 0x0080, 1, hicon)
        except Exception:
            pass

    QTimer.singleShot(100, _force_taskbar_icon)

    app.aboutToQuit.connect(loop.stop)
    app.lastWindowClosed.connect(loop.stop)

    # ── Centre and show window immediately ─────────────────
    screen = app.primaryScreen()
    if screen:
        center = screen.availableGeometry().center()
        window.move(center.x() - window.width() // 2, center.y() - window.height() // 2)

    window.show()
    splash.finish(window)
    window.raise_()
    window.activateWindow()
    app.processEvents()

    # ── Deferred: non-blocking background initialisation ────
    dashboard = window._pages.get("dashboard")

    # Load deferred plugins (Discord RPC, Cloud Backup, Notifications)
    # These are non-essential — safe to load after the window appears.
    QTimer.singleShot(0, lambda: plugin_manager.load_lazy_plugins())

    # Connection checks are already handled by dashboard._bg_refresh()
    # in a background thread, so we just schedule it.
    if dashboard:
        QTimer.singleShot(50, dashboard._bg_refresh)

    # ── First-run welcome dialog ──────────────────────────
    def _show_welcome():
        import config as cfg
        from gui.dashboard_widget import _is_placeholder
        if (_is_placeholder(getattr(cfg, "API_ID", 0)) and
            _is_placeholder(getattr(cfg, "ANILIST_TOKEN", ""))):
            from settings import get_setting, set_setting
            if not get_setting("welcome_shown", False):
                set_setting("welcome_shown", True)
                QMessageBox.information(window, "Welcome to AniListSync v3.0",
                    "Your services are not yet connected.\n\n"
                    'Click the "Connect" buttons on each Dashboard card to set up:\n'
                    "\u2022 AniList \u2014 paste your access token\n"
                    "\u2022 Telegram \u2014 in-app phone authentication\n"
                    "\u2022 MyAnimeList \u2014 browser OAuth flow\n\n"
                    "All credentials are saved automatically \u2014 no file editing needed!")

    QTimer.singleShot(500, _show_welcome)

    loop.run_forever()
    os._exit(0)


if __name__ == "__main__":
    launch_gui()