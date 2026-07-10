from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QProgressBar, QTextEdit, QFrame,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from gui.theme import get_log_stylesheet
from core.plugin_loader import plugin_manager


class SignalRelay(QWidget):
    log_line = pyqtSignal(str)
    progress = pyqtSignal(int, str)
    finished = pyqtSignal(bool, str)

    def __init__(self):
        super().__init__()


class SyncLogHandler:
    def __init__(self, relay: SignalRelay, widget: QTextEdit):
        self.relay = relay
        self.widget = widget

    def write(self, text: str):
        if text.strip():
            self.relay.log_line.emit(text)

    def flush(self):
        pass


class SyncWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._relay = SignalRelay()
        self._running = False
        self._sync_task = None
        self._relay.log_line.connect(self._append_log)
        self._relay.finished.connect(self._on_finished)
        self._log_handler = SyncLogHandler(self._relay, None)
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(16)

        heading = QLabel("Sync")
        heading.setObjectName("heading")
        sub = QLabel("Import anime titles from Telegram and sync to AniList and MyAnimeList.")
        sub.setObjectName("subheading")
        layout.addWidget(heading)
        layout.addWidget(sub)

        controls = QHBoxLayout()
        controls.setSpacing(12)

        self._sync_btn = QPushButton("Start Sync")
        self._sync_btn.setObjectName("primary")
        self._sync_btn.setMinimumWidth(140)
        self._sync_btn.clicked.connect(self._start_sync)
        controls.addWidget(self._sync_btn)

        controls.addStretch()

        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet("color: #565f89; font-size: 13px;")
        controls.addWidget(self._status_label)

        layout.addLayout(controls)

        self._progress = QProgressBar()
        self._progress.setVisible(False)
        self._progress.setMinimum(0)
        self._progress.setMaximum(100)
        self._progress.setTextVisible(True)
        layout.addWidget(self._progress)

        log_label = QLabel("Output")
        log_label.setObjectName("section")
        layout.addWidget(log_label)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setStyleSheet(get_log_stylesheet())
        self._log.setMinimumHeight(250)
        layout.addWidget(self._log)

        layout.addStretch()
        self.setLayout(layout)

    def _append_log(self, text: str):
        self._log.append(text)

    def _start_sync(self):
        if self._running:
            return
        self._running = True
        self._sync_btn.setEnabled(False)
        self._sync_btn.setText("Syncing...")
        self._log.clear()
        self._progress.setVisible(True)
        self._progress.setValue(0)
        self._status_label.setText("Starting sync...")
        self._status_label.setStyleSheet("color: #e0af68; font-size: 13px;")

        plugin_manager.call_hook("on_sync_start")

        import sys
        import io
        old_stdout = sys.stdout
        sys.stdout = self._log_handler

        from telegram_client import client, ensure_connected, disconnect_client
        from settings import get_setting
        from modes.automation import run_auto_backup, run_auto_health

        self._relay.progress.connect(self._update_progress)

        async def _run():
            try:
                self._relay.progress.emit(5, "Starting backup...")
                run_auto_backup()
                self._relay.progress.emit(15, "Connecting to Telegram...")
                ok = await ensure_connected()
                if not ok:
                    self._relay.log_line.emit("Telegram not connected. Cannot sync.")
                    self._relay.finished.emit(False, "Telegram disconnected")
                    return

                self._relay.progress.emit(30, "Importing from Telegram...")
                from sync import main as sync_main
                await sync_main(gui_mode=True)
                self._relay.progress.emit(85, "Running health check...")
                run_auto_health()
                self._relay.progress.emit(100, "Sync completed")
                self._relay.finished.emit(True, "Sync completed")
            except Exception as e:
                import traceback
                tb = traceback.format_exc()
                self._relay.log_line.emit(f"Sync error: {e}")
                for line in tb.split("\n"):
                    self._relay.log_line.emit(line)
                self._relay.finished.emit(False, str(e))

        import asyncio
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        self._sync_task = asyncio.ensure_future(_run(), loop=loop)

    def _update_progress(self, value: int, status: str):
        self._progress.setValue(value)
        self._status_label.setText(status)

    def _on_finished(self, success: bool, message: str):
        self._running = False
        self._sync_btn.setEnabled(True)
        self._sync_btn.setText("Start Sync")
        self._progress.setValue(100)

        import sys
        sys.stdout = sys.__stdout__

        if success:
            self._status_label.setText("Sync completed")
            self._status_label.setStyleSheet("color: #9ece6a; font-size: 13px; font-weight: 600;")
            self._relay.log_line.emit("Sync completed successfully.")
        else:
            self._status_label.setText(f"Sync failed: {message}")
            self._status_label.setStyleSheet("color: #f7768e; font-size: 13px; font-weight: 600;")

        QTimer.singleShot(2000, self._progress.hide)
        plugin_manager.call_hook("on_sync_finish")

    def reapply_theme(self):
        self._log.setStyleSheet(get_log_stylesheet())
