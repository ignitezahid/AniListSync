import io
import asyncio
import threading
from contextlib import redirect_stdout, redirect_stderr

from PyQt6.QtWidgets import (
    QScrollArea, QWidget, QFrame, QTextEdit, QVBoxLayout,
)
from PyQt6.QtCore import Qt, QTimer, QObject, pyqtSignal

class _MainThread(QObject):
    call = pyqtSignal(object)

_main_thread = _MainThread()
_main_thread.call.connect(lambda fn: fn())
from PyQt6.QtWidgets import QPushButton, QWidget
from PyQt6.QtGui import QPainter, QColor, QPen

from gui.theme import get_log_stylesheet


def make_log_text() -> QTextEdit:
    """Create a read-only monospace log QTextEdit with consistent styling."""
    te = QTextEdit()
    te.setReadOnly(True)
    te.setStyleSheet(get_log_stylesheet())
    return te


def scroll_area_widget(margins=(28, 20, 28, 20), spacing=16):
    """Create a QScrollArea with a prepared content layout.

    Returns (scroll_area, content_layout). Caller should add widgets
    to ``content_layout`` then wrap with ``apply_outer_layout(self, scroll_area)``.

    Saves ~10 lines of boilerplate per widget (12 widgets = ~120 lines saved).
    """
    layout = QVBoxLayout()
    layout.setContentsMargins(*margins)
    layout.setSpacing(spacing)
    container = QWidget()
    container.setLayout(layout)

    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setFrameShape(QFrame.Shape.NoFrame)
    scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    scroll.setWidget(container)
    return scroll, layout


def apply_outer_layout(widget, scroll):
    """Apply the zero-margin outer layout containing *scroll* to *widget*."""
    outer = QVBoxLayout()
    outer.setContentsMargins(0, 0, 0, 0)
    outer.addWidget(scroll)
    widget.setLayout(outer)


# ── Operation runner helpers ──────────────────────────────────────────────

def run_op(log_widget: QTextEdit, status_label, label: str, fn):
    """Run a sync or async function, capturing stdout/stderr into a log widget."""
    log_widget.clear()
    status_label.setText(f"Running {label}...")
    QTimer.singleShot(100, lambda: _do_op(log_widget, status_label, label, fn))


def _do_op(log_widget: QTextEdit, status_label, label: str, fn):
    buf = io.StringIO()
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            result = fn()
            if asyncio.iscoroutine(result):
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                loop.run_until_complete(result)
        log_widget.setText(buf.getvalue())
        status_label.setText(f"{label} complete")
    except Exception as e:
        log_widget.setText(buf.getvalue() + f"\nError: {e}")
        import traceback
        log_widget.setText(log_widget.toPlainText() + "\n" + traceback.format_exc())
        status_label.setText(f"{label} failed: {e}")


def threaded_op(log_widget: QTextEdit, status_label, label: str, fn):
    """Run a function in a background thread and log its stdout.
    Handles both sync and async (coroutine) functions."""
    log_widget.clear()
    status_label.setText(f"Running {label}...")
    threading.Thread(target=_threaded_do_op, args=(log_widget, status_label, label, fn), daemon=True).start()


def _threaded_do_op(log_widget, status_label, label, fn):
    buf = io.StringIO()
    try:
        with redirect_stdout(buf), redirect_stderr(buf):
            result = fn()
            if asyncio.iscoroutine(result):
                try:
                    loop = asyncio.get_running_loop()
                except RuntimeError:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                loop.run_until_complete(result)
        text = buf.getvalue()
        _main_thread.call.emit(lambda: _finish_op(log_widget, status_label, label, text, None))
    except Exception as e:
        text = buf.getvalue()
        import traceback
        _main_thread.call.emit(lambda: _finish_op(log_widget, status_label, label, text, (e, traceback.format_exc())))


def _finish_op(log_widget, status_label, label, text, error_info):
    if error_info:
        e, tb = error_info
        log_widget.setText(text + f"\nError: {e}\n{tb}")
        status_label.setText(f"{label} failed: {e}")
    else:
        log_widget.setText(text)
        status_label.setText(f"{label} complete")


# ── Shared styles ──────────────────────────────────────────────────────────

CONNECT_BTN_STYLESHEET = """
    QPushButton {
        color: #7aa2f7;
        font-size: 12px;
        font-weight: 600;
        border: 1px solid #7aa2f7;
        border-radius: 4px;
        padding: 2px 10px;
        background: transparent;
    }
    QPushButton:hover {
        background: #7aa2f7;
        color: #1a1b26;
    }
"""


def make_connect_btn(callback) -> QPushButton:
    """Create a styled outline 'Connect' button."""
    btn = QPushButton("Connect")
    btn.setStyleSheet(CONNECT_BTN_STYLESHEET)
    btn.clicked.connect(callback)
    return btn


# ── Loading Spinner ────────────────────────────────────────────────────────

class LoadingSpinner(QWidget):
    """An animated spinning indicator for async operations."""

    def __init__(self, parent=None, size=24, color="#7aa2f7", width=3):
        super().__init__(parent)
        self._size = size
        self._color = QColor(color)
        self._width = width
        self._angle = 0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._rotate)
        self.setFixedSize(size + 4, size + 4)

    def start(self):
        self._timer.start(50)
        self.show()

    def stop(self):
        self._timer.stop()
        self.hide()

    def _rotate(self):
        self._angle = (self._angle + 30) % 360
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.translate(self.width() / 2, self.height() / 2)
        painter.rotate(self._angle)

        pen = QPen(self._color, self._width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        rect = self.rect().adjusted(4, 4, -4, -4)
        painter.drawArc(rect, 0, 270 * 16)
        painter.end()


class LogOpsMixin:
    """Mixin providing ``_log_op(self, label, fn)`` for widgets with ``self._log`` and ``self._status_label``."""

    def _log_op(self, label: str, fn):
        run_op(self._log, self._status_label, label, fn)
