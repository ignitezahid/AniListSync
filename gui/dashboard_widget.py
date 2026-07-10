from datetime import datetime, timedelta, timezone
from pathlib import Path
import json
import os

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QGroupBox,
    QGridLayout, QFrame, QSizePolicy, QPushButton,
    QInputDialog, QMessageBox, QScrollArea, QApplication,
    QGraphicsOpacityEffect, QMenu,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPropertyAnimation, QPoint
import threading

from gui.theme import get_glass_rgb, THEME_PALETTES, apply_dark_theme, refresh_inline_styles
from gui.widgets import scroll_area_widget, apply_outer_layout, make_connect_btn
from version import VERSION, CREATOR
from anilist import ALIASES, SEARCH_CACHE, test_connection as test_anilist
from mal import test_connection as test_mal
from utils.constants import BACKUP_DIR, EXPORT_DIR, RETRY_FILE, STATE_FILE, COLLECTIONS_FILE, DATA_DIR, TG_STATUS_FILE
from utils.file_utils import load_json
from settings import get_setting
from core.plugin_loader import plugin_manager


_placeholder_strs = {"your_anilist_access_token", "your_mal_client_id", "your_mal_client_secret", "your_telegram_api_hash"}


def _is_placeholder(val):
    if val is None:
        return True
    if isinstance(val, int) and val == 0:
        return True
    if isinstance(val, str) and (not val or val in _placeholder_strs):
        return True
    return False


def _write_config_value(key, value, quote=True):
    """Write a single key=value to config.py, then reload the config module."""
    cfg_path = os.path.join(os.getcwd(), "config.py")
    import re
    with open(cfg_path, "r", encoding="utf-8") as f:
        content = f.read()
    if quote:
        new_val = f'{key} = "{value}"'
    else:
        new_val = f"{key} = {value}"
    content = re.sub(
        rf'^{key}\s*=.*?(?=\n|$)',
        new_val,
        content,
        count=1, flags=re.MULTILINE
    )
    with open(cfg_path, "w", encoding="utf-8") as f:
        f.write(content)
    import importlib
    import config as cfg
    importlib.reload(cfg)
    return cfg


class StatusDot(QLabel):
    def __init__(self, connected: bool | None):
        super().__init__()
        if connected is None:
            color = "#565f89"
        else:
            color = "#9ece6a" if connected else "#f7768e"
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                border-radius: 5px;
                min-width: 10px;
                max-width: 10px;
                min-height: 10px;
                max-height: 10px;
            }}
        """)


class StatCard(QFrame):
    def __init__(self, label: str, value: str, color: str = "#c0caf5"):
        super().__init__()
        self._accent = color
        self.setMinimumWidth(160)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Expanding,
        )
        self._apply_glass_style()
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 6, 8, 6)
        layout.setSpacing(2)

        lbl = QLabel(label)
        lbl.setWordWrap(True)
        lbl.setStyleSheet("color: #565f89; font-size: 12px; font-weight: 700; letter-spacing: 1px;")

        self._val = QLabel(value)
        self._val.setStyleSheet(f"color: {color}; font-size: 30px; font-weight: 800;")

        layout.addWidget(lbl)
        layout.addWidget(self._val)
        self.setLayout(layout)

    def _apply_glass_style(self):
        light = get_glass_rgb("light")
        medium = get_glass_rgb("medium")
        medium_light = get_glass_rgb("medium_light")
        hover = get_glass_rgb("hover")
        self.setStyleSheet(f"""
StatCard {{
    background-color: rgba({light}, 0.55);
    border: 1px solid rgba({medium}, 0.4);
    border-left: 3px solid {self._accent};
    border-radius: 10px;
    padding: 14px 16px;
}}
StatCard:hover {{
    border-color: rgba({medium_light}, 0.6);
    background-color: rgba({hover}, 0.65);
    border-left-color: {self._accent};
}}
""")

    def reapply_theme(self):
        self._apply_glass_style()


class ConnectionRow(QFrame):
    def __init__(self, name: str, connected: bool | None, detail: str = ""):
        super().__init__()
        self.setStyleSheet("ConnectionRow { background: transparent; }")
        layout = QHBoxLayout()
        layout.setContentsMargins(4, 4, 4, 4)
        layout.setSpacing(10)

        dot = StatusDot(connected)
        layout.addWidget(dot)

        label = QLabel(name)
        label.setStyleSheet("color: #c0caf5; font-size: 13px; font-weight: 500;")

        if connected is None:
            status = QLabel("Checking...")
            style = "#565f89"
        else:
            status = QLabel("Connected" if connected else "Disconnected")
            style = "#9ece6a" if connected else "#f7768e"
        status.setStyleSheet(f"color: {style}; font-size: 13px;")

        layout.addWidget(label)
        layout.addStretch()
        layout.addWidget(status)

        if detail:
            det = QLabel(detail)
            det.setStyleSheet("color: #565f89; font-size: 12px;")
            layout.addWidget(det)

        self.setLayout(layout)


class DashboardWidget(QWidget):
    _telegram_ok = False
    _tg_connected = None
    _anilist_ok = None
    _anilist_user = ""
    _mal_ok = None
    _bg_done = pyqtSignal(object)
    _health_done = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self._first_show = True
        self._cached_health = None
        self._health_last_checked = None
        self._last_sync_timer = None
        self._hidden_cards_file = Path(DATA_DIR) / "card_layout.json"
        self._hidden_cards = self._load_hidden_cards()
        self._style_tooltips()
        self._build_ui()
        self._tg_checked = False
        self._tg_status_cache = Path(DATA_DIR) / TG_STATUS_FILE
        self._conn_cache = Path(DATA_DIR) / "conn_cache.json"
        self._tg_connected, self._telegram_ok = self._load_tg_cache()
        self._load_conn_cache()
        self._bg_done.connect(self._on_bg_done)
        self._health_done.connect(self._on_health_done)
        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._bg_refresh)
        self._refresh_timer.start(30000)

        # Populate dashboard immediately with locally-cached data
        # BEFORE the window is shown, then _bg_refresh() updates it.
        # Health score is computed in a background thread via _refresh_health().
        self._refresh_display()
        QTimer.singleShot(100, self._refresh_health)

    def _load_tg_cache(self):
        try:
            val = json.loads(self._tg_status_cache.read_text(encoding="utf-8"))
            ok = bool(val.get("connected", False))
            return ok, ok
        except Exception:
            return None, False

    def _save_tg_cache(self, ok: bool):
        try:
            self._tg_status_cache.write_text(
                json.dumps({"connected": ok}), encoding="utf-8"
            )
        except Exception:
            pass

    def _load_conn_cache(self):
        """Load cached AniList/MAL connection status so dashboard shows
        real status immediately instead of 'Checking...' on cold start."""
        try:
            val = json.loads(self._conn_cache.read_text(encoding="utf-8"))
            self._anilist_ok = bool(val.get("anilist_ok", False))
            self._anilist_user = val.get("anilist_user", "")
            self._mal_ok = bool(val.get("mal_ok", False))
        except Exception:
            pass

    def _save_conn_cache(self, anilist_ok: bool, anilist_user: str, mal_ok: bool):
        """Persist connection status so it's available on next cold start."""
        try:
            self._conn_cache.write_text(
                json.dumps({
                    "anilist_ok": anilist_ok,
                    "anilist_user": anilist_user,
                    "mal_ok": mal_ok,
                }), encoding="utf-8"
            )
        except Exception:
            pass

    def _build_ui(self):
        scroll, layout = scroll_area_widget(spacing=18)

        # Heading row with gear button aligned right
        heading_row = QHBoxLayout()
        heading_row.setContentsMargins(0, 0, 0, 0)
        heading = QLabel("AniListSync")
        heading.setObjectName("heading")
        heading_row.addWidget(heading)
        heading_row.addStretch()

        self._gear_btn = QPushButton("\u2699")
        self._gear_btn.setFixedSize(32, 32)
        self._gear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self._gear_btn.setToolTip("<div style='text-align:left'>Dashboard options</div>")
        self._gear_btn.setStyleSheet("""
            QPushButton {
                color: #565f89; background: transparent;
                border: 1px solid transparent; border-radius: 6px;
                font-size: 18px; padding: 0;
            }
            QPushButton:hover {
                color: #c0caf5; border-color: #565f89;
            }
        """)
        self._gear_btn.clicked.connect(self._show_gear_menu)
        heading_row.addWidget(self._gear_btn)
        layout.addLayout(heading_row)

        sub = QLabel(f"Anime Library Manager v{VERSION} by {CREATOR}")
        sub.setObjectName("subheading")
        layout.addWidget(sub)

        self._connections_group = QGroupBox("Connections")
        self._connections_layout = QVBoxLayout()
        self._connections_layout.setSpacing(4)
        self._connections_group.setLayout(self._connections_layout)
        layout.addWidget(self._connections_group)

        self._stats_group = QGroupBox("Library")
        self._stats_grid = QGridLayout()
        self._stats_grid.setSpacing(10)
        self._stats_grid.setColumnStretch(0, 1)
        self._stats_grid.setColumnStretch(1, 1)
        self._stats_group.setLayout(self._stats_grid)
        layout.addWidget(self._stats_group)

        self._storage_group = QGroupBox("Storage")
        self._storage_grid = QGridLayout()
        self._storage_grid.setSpacing(10)
        self._storage_grid.setColumnStretch(0, 1)
        self._storage_grid.setColumnStretch(1, 1)
        self._storage_grid.setColumnStretch(2, 1)
        self._storage_group.setLayout(self._storage_grid)
        layout.addWidget(self._storage_group)

        self._sync_group = QGroupBox("Sync")
        self._sync_grid = QGridLayout()
        self._sync_grid.setSpacing(10)
        self._sync_grid.setColumnStretch(0, 1)
        self._sync_grid.setColumnStretch(1, 1)
        self._sync_grid.setColumnStretch(2, 1)
        self._sync_group.setLayout(self._sync_grid)
        layout.addWidget(self._sync_group)

        layout.addStretch()
        apply_outer_layout(self, scroll)

    def showEvent(self, event):
        super().showEvent(event)
        # Guard against false showEvent on window state changes (maximize, etc.)
        if hasattr(self, '_window_shown') and self._window_shown:
            return
        self._window_shown = True
        if self._first_show:
            self._first_show = False
            if not self._tg_checked:
                self._tg_checked = True
                QTimer.singleShot(200, self._check_tg_async)

    def _check_tg_async(self):
        import asyncio
        asyncio.get_event_loop().create_task(self._update_tg_status())

    async def _update_tg_status(self):
        try:
            from telegram_client import ensure_connected
            ok = await ensure_connected()
            self._telegram_ok = ok
        except Exception:
            self._telegram_ok = False
        self._tg_connected = self._telegram_ok
        self._save_tg_cache(self._telegram_ok)
        self._refresh_display()

    def _bg_refresh(self):
        def run():
            try:
                anilist_ok, anilist_user = True, str(test_anilist()) if test_anilist() else ""
            except Exception:
                anilist_ok, anilist_user = False, ""
            try:
                mal_ok = bool(test_mal())
            except Exception:
                mal_ok = False
            self._bg_done.emit((anilist_ok, anilist_user, mal_ok))
        threading.Thread(target=run, daemon=True).start()

    def _on_bg_done(self, data):
        anilist_ok, anilist_user, mal_ok = data
        self._anilist_ok, self._anilist_user = anilist_ok, anilist_user
        self._mal_ok = mal_ok
        self._save_conn_cache(anilist_ok, anilist_user, mal_ok)
        self._refresh_display()
        # Recompute health after fresh connection data
        QTimer.singleShot(0, self._refresh_health)

    def _conn_row(self, name: str, ok: bool, auth_cb=None, detail: str = ""):
        container = QFrame()
        container.setStyleSheet("QFrame { background: transparent; }")
        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.addWidget(ConnectionRow(name, ok, detail))
        if auth_cb:
            row.addWidget(make_connect_btn(auth_cb))
        container.setLayout(row)
        return container

    def _refresh_display(self):
        anilist_ok = getattr(self, "_anilist_ok", None)
        anilist_user = getattr(self, "_anilist_user", "")
        mal_ok = getattr(self, "_mal_ok", None)
        telegram_ok = self._test_tg_connection()
        if telegram_ok is None:
            telegram_ok = getattr(self, "_telegram_ok", None)

        self._clear_layout(self._connections_layout)
        if anilist_user:
            user_lbl = QLabel(f"👤  {anilist_user}")
            user_lbl.setStyleSheet("font-size: 16px; font-weight: 700; color: #7aa2f7; padding: 2px 0 6px 0; background: transparent;")
            self._connections_layout.addWidget(user_lbl)
        tg_auth = self._auth_tg if self._tg_connected is False else None
        self._connections_layout.addWidget(self._conn_row("Telegram", telegram_ok, tg_auth))
        self._connections_layout.addWidget(self._conn_row("AniList", anilist_ok, self._auth_anilist if not anilist_ok else None))
        self._connections_layout.addWidget(self._conn_row("MyAnimeList", mal_ok, self._auth_mal if not mal_ok else None))

        auto_active = get_setting("automation_enabled")
        if auto_active:
            mins = get_setting("automation_interval_minutes", 30)
            interval = f"{mins} min" if mins < 60 else (f"{mins // 60}h" if mins == 60 else f"{mins // 60}h")
            auto_text = f"Automation     Active ({interval})"
            auto_color = "#9ece6a"
        else:
            auto_text = "Automation     Disabled"
            auto_color = "#565f89"
        auto_lbl = QLabel(auto_text)
        auto_lbl.setStyleSheet(f"color: {auto_color}; font-size: 12px; font-weight: 500; padding: 4px 0;")
        self._connections_layout.addWidget(auto_lbl)



        state = self._load_state()

        anilist_count = state.get("anilist_entries")
        if anilist_count is None:
            anilist_ids = state.get("anilist_ids")
            if anilist_ids:
                anilist_count = len(anilist_ids)
            else:
                try:
                    anilist_count = len(load_json("data/anilist_cache.json", []))
                except Exception:
                    anilist_count = "?"
        mal_count = state.get("mal_entries")
        if mal_count is None:
            mal_ids = state.get("mal_ids")
            if mal_ids:
                mal_count = len(mal_ids)
            else:
                try:
                    mal_count = len(load_json("data/mal_cache.json", []))
                except Exception:
                    mal_count = "?"
        try:
            from mal import get_completed_mal_anime
            mal_lib = get_completed_mal_anime()
            if mal_lib:
                mal_count = len(mal_lib)
        except Exception:
            pass

        aliases_count = len(ALIASES) if ALIASES else 0
        collections_count = len(load_json(COLLECTIONS_FILE, {}))
        cache_count = len(SEARCH_CACHE) if SEARCH_CACHE else 0
        retry = load_json(RETRY_FILE, [])
        try:
            export_count = len(list(Path(EXPORT_DIR).glob("*")))
        except Exception:
            export_count = 0
        try:
            backup_count = len(list(Path(BACKUP_DIR).glob("*")))
        except Exception:
            backup_count = 0
        plugin_count = len(plugin_manager.get_plugins())

        self._clear_layout(self._stats_grid)
        lib_cards = [
            ("AniList Entries", str(anilist_count)),
            ("MAL Entries", str(mal_count)),
            ("Aliases", str(aliases_count)),
            ("Collections", str(collections_count)),
        ]
        shown_idx = 0
        for i, (label, value) in enumerate(lib_cards):
            if label in self._hidden_cards:
                continue
            card = StatCard(label, value)
            self._add_card_context_menu(card, label)
            self._stats_grid.addWidget(card, shown_idx // 2, shown_idx % 2)
            shown_idx += 1

        self._clear_layout(self._storage_grid)
        storage_cards = [
            ("Search Cache", str(cache_count), "#bb9af7"),
            ("Retry Queue", str(len(retry)), "#f7768e"),
            ("Exports", str(export_count), "#e0af68"),
            ("Backups", str(backup_count), "#7dcfff"),
            ("Plugins", str(plugin_count), "#73daca"),
        ]
        shown_idx = 0
        for i, (label, value, color) in enumerate(storage_cards):
            if label in self._hidden_cards:
                continue
            card = StatCard(label, value, color)
            self._add_card_context_menu(card, label)
            self._storage_grid.addWidget(card, shown_idx // 3, shown_idx % 3)
            shown_idx += 1

        self._clear_layout(self._sync_grid)
        last_sync = self._format_last_sync(state)
        self._last_sync_iso = state.get("last_sync", "")
        # Health score is cached from the last background computation.
        hp = self._cached_health
        health_str = f"{hp}%" if hp is not None else "?"
        health_color = "#9ece6a" if (hp is not None and hp >= 80) else ("#e0af68" if (hp is not None and hp >= 50) else "#f7768e")
        next_str = self._compute_next_sync(state)

        sync_cards_col = 0
        if "Last Sync" not in self._hidden_cards:
            self._last_sync_card = StatCard("Last Sync", last_sync or "Never", "#7aa2f7")
            self._add_card_context_menu(self._last_sync_card, "Last Sync")
            # Apply age-based accent color immediately
            self._update_sync_card_color()
            if self._last_sync_iso:
                try:
                    dt = datetime.fromisoformat(self._last_sync_iso)
                    if dt.tzinfo:
                        dt = dt.astimezone()
                    date_part = dt.strftime("%Y-%m-%d")
                    time_part = dt.strftime("%H:%M:%S")
                    self._last_sync_card.setToolTip(f"<table style='border:none;border-collapse:collapse;color:#c0caf5;font-family:Segoe UI;font-size:13px'><tr><td style='padding:0 6px 0 0'>Synced→</td><td style='padding:0'>{date_part}</td></tr><tr><td style='padding:0 6px 0 0'></td><td style='padding:0'>{time_part}</td></tr></table>")
                except Exception:
                    self._last_sync_card.setToolTip(f"<div style='text-align:left'>Synced→ {self._last_sync_iso}</div>")
            self._last_sync_card.setCursor(Qt.CursorShape.PointingHandCursor)
            self._last_sync_card.installEventFilter(self)
            self._sync_grid.addWidget(self._last_sync_card, 0, sync_cards_col)
            sync_cards_col += 1

        if "Health" not in self._hidden_cards:
            self._health_card = StatCard("Health", health_str, health_color)
            self._add_card_context_menu(self._health_card, "Health")
            self._update_health_tooltip()
            self._sync_grid.addWidget(self._health_card, 0, sync_cards_col)
            sync_cards_col += 1

        if "Next Sync" not in self._hidden_cards:
            self._next_sync_card = StatCard("Next Sync", next_str, "#565f89")
            self._add_card_context_menu(self._next_sync_card, "Next Sync")
            if self._last_sync_iso and get_setting("automation_enabled"):
                try:
                    mins = get_setting("automation_interval_minutes", 30)
                    last_dt = datetime.fromisoformat(self._last_sync_iso)
                    if last_dt.tzinfo:
                        last_dt = last_dt.astimezone()
                    next_dt = last_dt + timedelta(minutes=mins)
                    if next_dt.tzinfo:
                        next_dt = next_dt.astimezone()
                    nd = next_dt.strftime("%Y-%m-%d")
                    nt = next_dt.strftime("%H:%M:%S")
                    self._next_sync_card.setToolTip(f"<table style='border:none;border-collapse:collapse;color:#c0caf5;font-family:Segoe UI;font-size:13px'><tr><td style='padding:0 6px 0 0'>Next→</td><td style='padding:0'>{nd}</td></tr><tr><td style='padding:0 6px 0 0'></td><td style='padding:0'>{nt}</td></tr></table>")
                except Exception:
                    pass
            self._sync_grid.addWidget(self._next_sync_card, 0, sync_cards_col)
            sync_cards_col += 1

        self._start_last_sync_timer()

    def _test_conn(self, fn):
        try:
            result = fn()
            if result:
                return True, str(result) if not isinstance(result, bool) else ""
            return False, ""
        except Exception:
            return False, ""

    def _test_tg_connection(self):
        if self._tg_connected is None:
            return None
        return self._telegram_ok

    def _load_state(self):
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def _format_relative_time(self, iso_str: str) -> str | None:
        """Convert an ISO datetime string to a human-readable relative time."""
        if not iso_str:
            return None
        try:
            dt = datetime.fromisoformat(iso_str)
            now = datetime.now(timezone.utc) if dt.tzinfo else datetime.now()
            diff = now - dt
            seconds = int(diff.total_seconds())
            if seconds < 60:
                return "Just now"
            if seconds < 3600:
                m = seconds // 60
                return "1 min ago" if m == 1 else f"{m} min ago"
            if seconds < 86400:
                h = seconds // 3600
                return "1 hour ago" if h == 1 else f"{h} hours ago"
            d = seconds // 86400
            return "1 day ago" if d == 1 else f"{d} days ago"
        except Exception:
            return None

    def _format_last_sync(self, state):
        return self._format_relative_time(state.get("last_sync", ""))

    def _compute_next_sync(self, state):
        if not get_setting("automation_enabled"):
            return "-"
        mins = get_setting("automation_interval_minutes", 30)
        last_iso = state.get("last_sync", "")
        if not last_iso:
            return "Now"
        try:
            last_dt = datetime.fromisoformat(last_iso)
            next_dt = last_dt + timedelta(minutes=mins)
            now = datetime.now(timezone.utc) if last_dt.tzinfo else datetime.now()
            if next_dt <= now:
                return "Now"
            remaining = next_dt - now
            total_secs = int(remaining.total_seconds())
            if total_secs < 60:
                return "Soon"
            if total_secs < 3600:
                return f"{total_secs // 60} min"
            hours = total_secs // 3600
            mins_left = (total_secs % 3600) // 60
            return f"{hours}h {mins_left}m"
        except Exception:
            return "-"

    def _refresh_health(self):
        """Compute health score in a background thread and emit signal.
        Never blocks the main thread."""
        from modes.tools import _compute_health_score

        def run():
            try:
                hp, groups, issues = _compute_health_score()
                skipped_keywords = ["token", "cred", "api_id", "api_hash", "session", "telegram"]
                filtered = [i for i in issues if not any(k in i.lower() for k in skipped_keywords)]
                skipped = len(issues) - len(filtered)
                if skipped:
                    total_checks = 12
                    passed = round(hp * total_checks / 100)
                    new_total = total_checks - skipped
                    hp = int(passed * 100 / new_total) if new_total else 100
                    hp = min(hp, 100)
                self._health_done.emit(hp)
            except Exception:
                self._health_done.emit(None)

        threading.Thread(target=run, daemon=True).start()

    def eventFilter(self, obj, event):
        if obj is getattr(self, '_last_sync_card', None) and event.type() == event.Type.MouseButtonPress:
            self._show_sync_info()
            return True
        return super().eventFilter(obj, event)

    def _show_sync_info(self):
        """Show a popup with sync details from the current state."""
        state = self._load_state()
        last_sync_iso = state.get("last_sync", "")
        if not last_sync_iso:
            QMessageBox.information(self, "Sync Info", "No sync has been performed yet.")
            return
        try:
            dt = datetime.fromisoformat(last_sync_iso)
            if dt.tzinfo:
                dt = dt.astimezone()
            formatted = dt.strftime("%B %d, %Y at %I:%M %p")
        except Exception:
            formatted = last_sync_iso
        anilist_count = state.get("anilist_entries", "?")
        mal_count = state.get("mal_entries", "?")
        msg = (
            f"Last Sync: {formatted}\n\n"
            f"AniList Entries: {anilist_count}\n"
            f"MAL Entries: {mal_count}\n"
        )
        auto_enabled = get_setting("automation_enabled")
        if auto_enabled:
            mins = get_setting("automation_interval_minutes", 30)
            msg += f"Automation: Active (every {mins} min)\n"
        else:
            msg += "Automation: Disabled\n"
        QMessageBox.information(self, "Sync Info", msg)

    def _start_last_sync_timer(self):
        """Start/restart a 60-second timer that updates the Last Sync
        relative time (e.g. '5 min ago' → '6 min ago') in-place."""
        if self._last_sync_timer is not None:
            self._last_sync_timer.stop()
        if not self._last_sync_iso:
            return
        self._last_sync_timer = QTimer(self)
        self._last_sync_timer.timeout.connect(self._tick_last_sync)
        self._last_sync_timer.start(60000)

    def _sync_age_seconds(self) -> int | None:
        """Return seconds since last sync, or None if unknown."""
        if not self._last_sync_iso:
            return None
        try:
            dt = datetime.fromisoformat(self._last_sync_iso)
            now = datetime.now(timezone.utc) if dt.tzinfo else datetime.now()
            return int((now - dt).total_seconds())
        except Exception:
            return None

    def _update_sync_card_color(self):
        """Update the Last Sync card's left-border accent color based on age.
        Green (recent) -> Yellow (hours) -> Orange (day) -> Red (old)."""
        card = getattr(self, '_last_sync_card', None)
        if card is None:
            return
        secs = self._sync_age_seconds()
        if secs is None:
            color = "#565f89"
        elif secs < 3600:       # < 1 hour
            color = "#9ece6a"
        elif secs < 21600:      # 1-6 hours
            color = "#e0af68"
        elif secs < 86400:      # 6-24 hours
            color = "#f7768e"
        else:                    # > 24 hours
            color = "#db4b4b"
        card._accent = color
        card._apply_glass_style()

    def _tick_last_sync(self):
        """Recompute the relative 'Last Sync' time and update the card in-place."""
        if not self._last_sync_iso:
            return
        card = getattr(self, '_last_sync_card', None)
        if card is None:
            return
        text = self._format_relative_time(self._last_sync_iso)
        if text:
            card._val.setText(text)
        self._update_sync_card_color()

    def _style_tooltips(self):
        """Apply a custom dark theme to all QToolTip popups in the dashboard."""
        self.setStyleSheet(self.styleSheet() + """
            QToolTip {
                background-color: #1a1b26;
                color: #c0caf5;
                border: 1px solid #565f89;
                border-radius: 6px;
                padding: 6px 10px;
                font-size: 13px;
                font-family: 'Segoe UI';
                text-align: left;
            }
        """)

    def _update_health_tooltip(self):
        """Update the Health card tooltip with the last-check timestamp."""
        card = getattr(self, '_health_card', None)
        if card is None:
            return
        hp = self._cached_health
        health_str = f"{hp}%" if hp is not None else "?"
        checked = self._health_last_checked
        if checked:
            date_part = checked.strftime("%Y-%m-%d")
            time_part = checked.strftime("%H:%M:%S")
            card.setToolTip(f"<table style='border:none;border-collapse:collapse;color:#c0caf5;font-family:Segoe UI;font-size:13px'><tr><td style='padding:0 6px 0 0'>Checked→</td><td style='padding:0'>{date_part}</td></tr><tr><td style='padding:0 6px 0 0'></td><td style='padding:0'>{time_part}</td></tr></table>")
        else:
            card.setToolTip(f"<div style='text-align:left'>Health→ {health_str}</div>")

    def _fade_in_widget(self, widget, duration=300):
        """Apply a quick fade-in animation on a widget."""
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)
        anim = QPropertyAnimation(effect, b"opacity", self)
        anim.setDuration(duration)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.start()

    def _on_health_done(self, hp: int | None):
        """Update cached health score and the StatCard value in-place."""
        self._cached_health = hp
        self._health_last_checked = datetime.now()
        health_str = f"{hp}%" if hp is not None else "?"
        if hp is not None and hp >= 80:
            color = "#9ece6a"
        elif hp is not None and hp >= 50:
            color = "#e0af68"
        else:
            color = "#f7768e"
        card = getattr(self, '_health_card', None)
        if card is not None:
            card._val.setText(health_str)
            card._val.setStyleSheet(f"color: {color}; font-size: 30px; font-weight: 800;")
            card._accent = color
            self._update_health_tooltip()
            self._fade_in_widget(card._val, 350)

    def _clear_layout(self, layout):
        while layout.count():
            item = layout.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()
            elif item.layout():
                self._clear_layout(item.layout())

    def reapply_theme(self):
        """Re-apply StatCard glass inline stylesheets after a theme switch."""
        for child in self.findChildren(StatCard):
            child.reapply_theme()
        # Force full style repolish on the entire widget tree.
        # This is the only reliable way to get palette changes to apply to
        # widgets in hidden pages of a QStackedWidget.
        app = QApplication.instance()
        self._repolish(self, app)

    def _repolish(self, w, app):
        """Recursively unpolish/repolish a widget and its children."""
        for child in w.findChildren(QWidget):
            app.style().unpolish(child)
            app.style().polish(child)
            child.update()
        app.style().unpolish(w)
        app.style().polish(w)
        w.update()

    def _apply_theme(self, name: str):
        """Apply a theme by name and persist the choice."""
        from core.plugin_loader import plugin_manager as _pm
        app = QApplication.instance()
        if not app:
            return
        p = THEME_PALETTES.get(name, THEME_PALETTES["Default"])
        apply_dark_theme(app, name)
        refresh_inline_styles(app)
        _pm._settings.setdefault("themes", {})
        _pm._settings["themes"]["active"] = name
        _pm._settings["themes"]["bg"] = p["bg"]
        for pid, manifest, loaded in _pm.get_plugins():
            if pid == "themes":
                inst = _pm._plugins.get(pid)
                if inst and hasattr(inst, "settings"):
                    inst.settings["active"] = name
                    inst.settings["bg"] = p["bg"]
                    inst.save_settings()
                break
        self.reapply_theme()
        # Update system tray icon to match new theme accent
        for w in app.allWidgets():
            if hasattr(w, '_update_tray_icon'):
                try:
                    w._update_tray_icon()
                except Exception:
                    pass

    # ── Hidden cards management ───────────────────────────

    def _load_hidden_cards(self) -> set:
        """Load the set of hidden card labels from disk."""
        try:
            data = json.loads(self._hidden_cards_file.read_text(encoding="utf-8"))
            return set(data) if isinstance(data, list) else set()
        except Exception:
            return set()

    def _save_hidden_cards(self):
        """Persist hidden card labels to disk."""
        try:
            self._hidden_cards_file.write_text(
                json.dumps(list(self._hidden_cards)), encoding="utf-8"
            )
        except Exception:
            pass

    def _add_card_context_menu(self, card: QFrame, label: str):
        """Attach a right-click context menu to hide a dashboard card."""
        card.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        card.customContextMenuRequested.connect(
            lambda pos, l=label, c=card: self._show_card_menu(pos, l, c)
        )

    def _show_card_menu(self, pos, label: str, card: QFrame):
        """Show a context menu for the given card at the correct screen position."""
        menu = QMenu()
        hide = menu.addAction(f"\u2716  Hide '{label}'")
        hide.triggered.connect(lambda: self._hide_card(label))
        menu.exec(card.mapToGlobal(pos))

    def _show_gear_menu(self):
        """Show the gear button's popup menu with dashboard options."""
        menu = QMenu()
        if self._hidden_cards:
            restore = menu.addAction("\u21ba  Restore hidden cards")
            restore.triggered.connect(self._restore_hidden_cards)
        reset = menu.addAction("\u21bb  Reset Cache")
        reset.triggered.connect(self._reset_cache)
        menu.exec(self._gear_btn.mapToGlobal(QPoint(0, self._gear_btn.height())))

    def _hide_card(self, label: str):
        """Add the card label to hidden cards and refresh the dashboard."""
        self._hidden_cards.add(label)
        self._save_hidden_cards()
        self._refresh_display()

    def _restore_hidden_cards(self):
        """Clear all hidden cards and refresh the dashboard."""
        self._hidden_cards.clear()
        self._save_hidden_cards()
        self._refresh_display()

    def _reset_cache(self):
        """Clear cached connection statuses and force a fresh check."""
        reply = QMessageBox.question(
            self, "Reset Cache",
            "Clear cached connection status and force a fresh connection check?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        try:
            self._conn_cache.unlink(missing_ok=True)
        except Exception:
            pass
        try:
            self._tg_status_cache.unlink(missing_ok=True)
        except Exception:
            pass
        self._anilist_ok = None
        self._anilist_user = ""
        self._mal_ok = None
        self._tg_connected = None
        self._telegram_ok = False
        self._refresh_display()
        QTimer.singleShot(100, self._bg_refresh)

    def refresh_now(self):
        self._bg_refresh()

    def _auth_anilist(self):
        import webbrowser
        webbrowser.open("https://anilist.co/settings/developer")
        token, ok = QInputDialog.getText(self, "AniList Token",
            "1. Browser opened to anilist.co/settings/developer.\n"
            "2. Click 'Create New Client', then copy the Access Token.\n"
            "3. Paste the token below:")
        if not ok or not token.strip():
            return
        token = token.strip()
        try:
            cfg = _write_config_value("ANILIST_TOKEN", token)
            cfg.ANILIST_TOKEN = token
            import anilist
            anilist.HEADERS["Authorization"] = f"Bearer {token}"
            QMessageBox.information(self, "Success",
                "AniList token saved! Checking connection...")
            self._bg_refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error",
                f"Failed to save token: {e}\n\nEdit config.py manually.")

    def _auth_tg(self):
        import config as cfg
        if _is_placeholder(getattr(cfg, "API_ID", 0)) or _is_placeholder(getattr(cfg, "API_HASH", None)):
            api_id, ok = QInputDialog.getInt(self, "Telegram API ID",
                "Enter your Telegram API ID (from https://my.telegram.org/apps):",
                value=0, min=1, max=99999999)
            if not ok:
                return
            api_hash, ok = QInputDialog.getText(self, "Telegram API Hash",
                "Enter your Telegram API Hash (from https://my.telegram.org/apps):")
            if not ok or not api_hash.strip():
                return
            cfg = _write_config_value("API_ID", str(api_id), quote=False)
            cfg = _write_config_value("API_HASH", api_hash.strip())
            try:
                import importlib
                import telegram_client
                importlib.reload(telegram_client)
            except Exception as e:
                QMessageBox.warning(self, "Notice",
                    f"Credentials saved to config.py, but reload failed: {e}\n\n"
                    "Please restart the app for Telegram credentials to take effect.")
                return
        phone, ok = QInputDialog.getText(self, "Telegram Authentication",
            "Enter your phone number (e.g., +1234567890):")
        if not ok or not phone.strip():
            return
        self._tg_auth_phone = phone.strip()
        self._tg_code = None
        import asyncio
        try:
            from telegram_client import client as tg_client
            asyncio.ensure_future(self._tg_connect(tg_client))
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Telegram auth failed: {e}")

    async def _tg_connect(self, tg_client):
        try:
            if not tg_client.is_connected():
                await tg_client.connect()
            if not await tg_client.is_user_authorized():
                await tg_client.send_code_request(self._tg_auth_phone)
                self._tg_code = None
                self._tg_awaiting_code = True
                code, ok = QInputDialog.getText(self, "Telegram Code",
                    f"Enter the code sent to {self._tg_auth_phone}:")
                self._tg_awaiting_code = False
                if ok and code.strip():
                    await tg_client.sign_in(self._tg_auth_phone, code.strip())
                else:
                    return
            QMessageBox.information(self, "Success", "Telegram authentication successful!")
            self._check_tg_async()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Telegram auth failed: {e}")

    def _auth_mal(self):
        import config as cfg
        import webbrowser
        if _is_placeholder(getattr(cfg, "MAL_CLIENT_ID", None)) or _is_placeholder(getattr(cfg, "MAL_CLIENT_SECRET", None)):
            client_id, ok = QInputDialog.getText(self, "MAL Client ID",
                "Enter your MyAnimeList Client ID (from https://myanimelist.net/apiconfig):")
            if not ok or not client_id.strip():
                return
            client_secret, ok = QInputDialog.getText(self, "MAL Client Secret",
                "Enter your MyAnimeList Client Secret:")
            if not ok or not client_secret.strip():
                return
            cfg = _write_config_value("MAL_CLIENT_ID", client_id.strip())
            cfg = _write_config_value("MAL_CLIENT_SECRET", client_secret.strip())
            import importlib
            import mal
            importlib.reload(mal)
        try:
            from mal import get_auth_url, get_tokens, save_tokens
            url, verifier = get_auth_url()
            webbrowser.open(url)
            code, ok = QInputDialog.getText(self, "MAL Authentication",
                "A browser has been opened for MAL authorization.\n"
                "Authorize the app, then paste the code from the URL here:")
            if not ok or not code.strip():
                return
            tokens = get_tokens(code.strip(), verifier)
            save_tokens(tokens)
            QMessageBox.information(self, "Success", "MAL authentication successful!")
            self._bg_refresh()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"MAL authentication failed: {e}")
