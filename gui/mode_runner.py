import sys
import io
import asyncio
import threading
from contextlib import redirect_stdout, redirect_stderr

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTextEdit, QScrollArea, QFrame,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from gui.theme import get_log_stylesheet


class OutputRelay(QWidget):
    line_written = pyqtSignal(str)
    finished = pyqtSignal()


class ModeRunnerWidget(QWidget):
    def __init__(self, title: str, description: str, mode_fn, is_async: bool = False):
        super().__init__()
        self._mode_fn = mode_fn
        self._is_async = is_async
        self._running = False
        self._relay = OutputRelay()
        self._relay.line_written.connect(self._append_output)
        self._relay.finished.connect(self._on_finished)
        self._build_ui(title, description)

    def _build_ui(self, title: str, description: str):
        layout = QVBoxLayout()
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(16)

        heading = QLabel(title)
        heading.setObjectName("heading")
        sub = QLabel(description)
        sub.setObjectName("subheading")
        layout.addWidget(heading)
        layout.addWidget(sub)

        controls = QHBoxLayout()
        controls.setSpacing(12)

        self._run_btn = QPushButton("Run")
        self._run_btn.setObjectName("primary")
        self._run_btn.setMinimumWidth(120)
        self._run_btn.clicked.connect(self._run)
        controls.addWidget(self._run_btn)

        controls.addStretch()

        self._status_label = QLabel("Ready")
        self._status_label.setStyleSheet("color: #565f89; font-size: 13px;")
        controls.addWidget(self._status_label)

        layout.addLayout(controls)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)

        self._output = QTextEdit()
        self._output.setReadOnly(True)
        self._output.setStyleSheet(get_log_stylesheet())
        self._output.setMinimumHeight(300)

        scroll.setWidget(self._output)
        layout.addWidget(scroll)

        layout.addStretch()
        self.setLayout(layout)

    def _append_output(self, text: str):
        self._output.append(text)

    def _run(self):
        if self._running:
            return
        self._running = True
        self._run_btn.setEnabled(False)
        self._run_btn.setText("Running...")
        self._output.clear()
        self._status_label.setText("Running...")
        self._status_label.setStyleSheet("color: #e0af68; font-size: 13px;")

        if self._is_async:
            self._run_async()
        else:
            self._run_sync()

    def _run_sync(self):
        def target():
            buf = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(buf):
                try:
                    self._mode_fn()
                except Exception as e:
                    print(f"Error: {e}")
                    import traceback
                    traceback.print_exc()

            output = buf.getvalue()
            if output:
                self._relay.line_written.emit(output)
            self._relay.finished.emit()

        t = threading.Thread(target=target, daemon=True)
        t.start()

    def _run_async(self):
        async def _run():
            buf = io.StringIO()
            with redirect_stdout(buf), redirect_stderr(buf):
                try:
                    from telegram_client import client, ensure_connected
                    await ensure_connected()
                    await self._mode_fn()
                except Exception as e:
                    print(f"Error: {e}")
                    import traceback
                    traceback.print_exc()

            output = buf.getvalue()
            if output:
                self._relay.line_written.emit(output)
            self._relay.finished.emit()

        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        asyncio.ensure_future(_run(), loop=loop)

    def _on_finished(self):
        self._running = False
        self._run_btn.setEnabled(True)
        self._run_btn.setText("Run")
        self._status_label.setText("Done")
        self._status_label.setStyleSheet("color: #9ece6a; font-size: 13px; font-weight: 600;")

    def reapply_theme(self):
        self._output.setStyleSheet(get_log_stylesheet())
