from pathlib import Path
import json
from datetime import datetime, timezone, timedelta

import time

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QGridLayout, QFrame, QProgressBar,
    QDialog, QRadioButton, QDialogButtonBox,
)
from PyQt6.QtCore import Qt, QTimer

from gui.widgets import scroll_area_widget, apply_outer_layout
from version import VERSION
from anilist import SEARCH_CACHE
from utils.constants import RETRY_FILE, BACKUP_DIR, EXPORT_DIR, STATE_FILE
from utils.file_utils import load_json
from settings import get_setting
from core.plugin_loader import plugin_manager

# Cache for dashboard/statistics data with 30s TTL
_cache = {"data": None, "ts": 0.0, "ttl": 30}


def _get_cached_library():
    """Return cached library data, refreshing from API if cache is stale (30s TTL).
    Shared across statistics and dashboard widgets to reduce API calls."""
    from anilist import get_completed_anime
    now = time.time()
    if _cache["data"] is None or (now - _cache["ts"]) > _cache["ttl"]:
        _cache["data"] = get_completed_anime()
        _cache["ts"] = now
    return _cache["data"]


def invalidate_library_cache():
    """Force the library cache to refresh on next access."""
    _cache["data"] = None
    _cache["ts"] = 0.0


class StatRow(QFrame):
    def __init__(self, label: str, value: str):
        super().__init__()
        self.setStyleSheet("QFrame { background: transparent; }")
        layout = QHBoxLayout()
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(12)
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #565f89; font-size: 13px;")
        val = QLabel(str(value))
        val.setStyleSheet("color: #c0caf5; font-size: 13px; font-weight: 600;")
        val.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        layout.addWidget(lbl)
        layout.addStretch()
        layout.addWidget(val)
        self.setLayout(layout)


class StatisticsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        scroll, layout = scroll_area_widget()

        heading = QLabel("Statistics")
        heading.setObjectName("heading")
        sub = QLabel("Library analytics, genre breakdowns, and system stats.")
        sub.setObjectName("subheading")
        layout.addWidget(heading)
        layout.addWidget(sub)

        self._grid = QGridLayout()
        self._grid.setSpacing(12)
        layout.addLayout(self._grid)

        self._export_btn = QPushButton("Export Statistics Report")
        self._export_btn.clicked.connect(self._export_report)
        layout.addWidget(self._export_btn)

        self._status_label = QLabel("Loading...")
        self._status_label.setStyleSheet("color: #565f89; font-size: 12px;")
        layout.addWidget(self._status_label)

        layout.addStretch()
        apply_outer_layout(self, scroll)

    def showEvent(self, event):
        super().showEvent(event)
        QTimer.singleShot(100, self._refresh)

    def _clear_grid(self):
        while self._grid.count():
            item = self._grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

    def _make_group(self, title: str, rows: list) -> QGroupBox:
        group = QGroupBox(title)
        vl = QVBoxLayout()
        vl.setSpacing(2)
        for label, value in rows:
            vl.addWidget(StatRow(label, value))
        group.setLayout(vl)
        return group

    def _refresh(self):
        self._status_label.setText("Computing statistics...")
        QTimer.singleShot(100, self._run_refresh)

    def _run_refresh(self):
        try:
            state = load_json(STATE_FILE, {})
            library = _get_cached_library()
            from mal import get_completed_mal_anime
            mal_anime = get_completed_mal_anime()
            mal_ids = {a["idMal"] for a in mal_anime if a.get("idMal")}
            from anilist import ALIASES

            anilist_count = len(library)
            mal_count = len(mal_ids)

            status_counts = {"CURRENT": 0, "COMPLETED": 0, "PLANNING": 0, "DROPPED": 0, "PAUSED": 0, "REPEATING": 0}
            genres = {}
            seasons = {"WINTER": 0, "SPRING": 0, "SUMMER": 0, "FALL": 0}
            total_eps = 0
            total_score = 0
            scored = 0
            studio_count = {}
            year_count = {}
            for a in library:
                s = a.get("status", "")
                if s in status_counts:
                    status_counts[s] += 1
                for g in a.get("genres") or []:
                    genres[g] = genres.get(g, 0) + 1
                season = a.get("season", "")
                if season in seasons:
                    seasons[season] += 1
                eps = a.get("episodes") or 0
                total_eps += eps
                score = a.get("score")
                if score:
                    total_score += score
                    scored += 1
                for studio in (a.get("studios") or []):
                    name = studio.get("name") if isinstance(studio, dict) else studio
                    if name:
                        studio_count[name] = studio_count.get(name, 0) + 1
                yr = a.get("season_year")
                if yr:
                    year_count[yr] = year_count.get(yr, 0) + 1

            avg_score = round(total_score / scored, 1) if scored else 0
            avg_eps = round(total_eps / len(library), 1) if library else 0

            top_genre = max(genres, key=genres.get) if genres else "-"
            top_studio = max(studio_count, key=studio_count.get) if studio_count else "-"
            top_year = max(year_count, key=year_count.get) if year_count else "-"
            active_season = max(seasons, key=seasons.get) if any(seasons.values()) else "-"

            retry = load_json(RETRY_FILE, [])
            export_count = len(list(Path(EXPORT_DIR).glob("*")))
            backup_count = len(list(Path(BACKUP_DIR).glob("*")))

            last_sync = state.get("last_sync", "")
            last_sync_str = self._relative_time(last_sync) if last_sync else "Never"

            usage = load_json("data/usage_stats.json", {})

            self._clear_grid()

            self._grid.addWidget(self._make_group("Library", [
                ("AniList Entries", str(anilist_count)),
                ("MAL Entries", str(mal_count)),
                ("Telegram Found", str(usage.get("telegram_found", 0))),
            ]), 0, 0)

            self._grid.addWidget(self._make_group("Completion", [
                ("Watching", str(status_counts["CURRENT"])),
                ("Completed", str(status_counts["COMPLETED"])),
                ("Planning", str(status_counts["PLANNING"])),
                ("Dropped", str(status_counts["DROPPED"])),
                ("Avg Episodes", str(avg_eps)),
                ("Avg Score", str(avg_score)),
            ]), 0, 1)

            self._grid.addWidget(self._make_group("Top Items", [
                ("Top Genre", top_genre),
                ("Top Studio", top_studio),
                ("Top Year", str(top_year)),
                ("Active Season", active_season),
            ]), 0, 2)

            self._grid.addWidget(self._make_group("Search & Sync", [
                ("Aliases", str(len(ALIASES))),
                ("Cache Entries", str(len(SEARCH_CACHE))),
                ("Retry Queue", str(len(retry))),
                ("Last Sync", last_sync_str),
            ]), 1, 0)

            self._grid.addWidget(self._make_group("System", [
                ("Exports", str(export_count)),
                ("Backups", str(backup_count)),
                ("Plugins", str(len(plugin_manager.get_plugins()))),
                ("Version", VERSION),
            ]), 1, 1)

            self._status_label.setText("Updated")
        except Exception as e:
            self._status_label.setText(f"Error: {e}")

    def _relative_time(self, iso_str):
        try:
            dt = datetime.fromisoformat(iso_str)
            now = datetime.now(timezone.utc) if dt.tzinfo else datetime.now()
            diff = now - dt
            secs = int(diff.total_seconds())
            if secs < 60: return "Just now"
            if secs < 3600: return f"{secs // 60} min ago"
            if secs < 86400: return f"{secs // 3600}h ago"
            return f"{secs // 86400}d ago"
        except Exception:
            return iso_str

    def _choose_format(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Export Format")
        dlg.setFixedWidth(300)
        layout = QVBoxLayout()
        layout.setSpacing(8)
        formats = ["JSON", "CSV", "TXT", "Markdown", "HTML"]
        try:
            import openpyxl  # noqa: F401
            formats.append("Excel")
        except ImportError:
            pass
        buttons = []
        group = None
        from PyQt6.QtWidgets import QButtonGroup
        group = QButtonGroup(dlg)
        for i, fmt in enumerate(formats):
            rb = QRadioButton(fmt)
            if i == 0:
                rb.setChecked(True)
            group.addButton(rb, i)
            layout.addWidget(rb)
        btn_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel)
        btn_box.accepted.connect(dlg.accept)
        btn_box.rejected.connect(dlg.reject)
        layout.addWidget(btn_box)
        dlg.setLayout(layout)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            idx = group.checkedId()
            return formats[idx].lower()
        return None

    def _export_report(self):
        try:
            fmt = self._choose_format()
            if not fmt:
                self._status_label.setText("Export cancelled")
                return
        except Exception:
            return
        self._status_label.setText("Exporting...")
        try:
            from modes.tools.common import export_json, export_csv, export_markdown, export_html, export_xlsx, export_path
            from anilist import get_completed_anime, ALIASES, SEARCH_CACHE
            from mal import get_completed_mal_anime, get_completed_mal_ids
            from collections import Counter
            from pathlib import Path

            state = load_json("state.json", {})
            library = get_completed_anime()
            mal_lib = get_completed_mal_anime()

            status_counter = Counter()
            genre_counter = Counter()
            season_counter = Counter()
            total_eps = 0
            total_score = 0
            scored = 0
            for a in library:
                s = a.get("status", "")
                if s:
                    status_counter[s] += 1
                for g in a.get("genres") or []:
                    genre_counter[g] += 1
                season = a.get("season", "")
                if season:
                    season_counter[season] += 1
                total_eps += a.get("episodes") or 0
                score = a.get("score")
                if score:
                    total_score += score
                    scored += 1

            total_count = len(library)
            avg_eps = round(total_eps / total_count, 1) if total_count else 0
            avg_score = round(total_score / scored, 1) if scored else 0
            telegram_found = load_json("data/usage_stats.json", {}).get("telegram_found", 0)
            retry_queue = load_json(RETRY_FILE, [])
            export_count = len(list(Path(EXPORT_DIR).glob("*")))
            backup_count = len(list(Path(BACKUP_DIR).glob("*")))

            json_data = {
                "library": {
                    "anilist": total_count,
                    "mal": len(get_completed_mal_ids()),
                    "telegram": telegram_found,
                },
                "completion": {
                    k: {"count": v, "pct": round(v / total_count * 100, 1) if total_count else 0}
                    for k, v in status_counter.items()
                },
                "averages": {"episodes": avg_eps, "score": avg_score},
                "genres": dict(genre_counter.most_common()),
                "seasons": dict(season_counter.most_common()),
                "search": {
                    "aliases": len(ALIASES),
                    "cache_entries": len(SEARCH_CACHE),
                    "retry_queue": len(retry_queue),
                },
                "sync": {"last_sync": state.get("last_sync", "")},
                "system": {"backups": backup_count, "exports": export_count, "version": VERSION},
                "timestamp": datetime.now().isoformat(),
            }
            headers = ["Section", "Value"]
            rows = []
            rows.append({"Section": "Library / AniList", "Value": str(total_count)})
            rows.append({"Section": "Library / MAL", "Value": str(len(get_completed_mal_ids()))})
            rows.append({"Section": "Library / Telegram", "Value": str(telegram_found)})
            status_labels = {
                "COMPLETED": "Completed", "CURRENT": "Watching", "DROPPED": "Dropped",
                "PAUSED": "Paused", "PLANNING": "Planning", "REPEATING": "Rewatching",
            }
            for key, label in status_labels.items():
                count = status_counter.get(key, 0)
                if count:
                    pct = count / total_count * 100 if total_count else 0
                    rows.append({"Section": f"Completion / {label}", "Value": f"{count} ({pct:.1f}%)"})
            rows.append({"Section": "Completion / Average Episodes", "Value": str(avg_eps)})
            rows.append({"Section": "Completion / Average Score", "Value": str(avg_score)})
            for genre, count in genre_counter.most_common():
                rows.append({"Section": f"Genre / {genre}", "Value": str(count)})
            season_labels = {"WINTER": "Winter", "SPRING": "Spring", "SUMMER": "Summer", "FALL": "Fall"}
            for season in ["WINTER", "SPRING", "SUMMER", "FALL"]:
                c = season_counter.get(season, 0)
                if c:
                    rows.append({"Section": f"Season / {season_labels.get(season, season)}", "Value": str(c)})
            rows.append({"Section": "Search / Aliases Learned", "Value": str(len(ALIASES))})
            rows.append({"Section": "Search / Cache Entries", "Value": str(len(SEARCH_CACHE))})
            rows.append({"Section": "Search / Retry Queue", "Value": str(len(retry_queue))})
            rows.append({"Section": "Sync / Last Sync", "Value": state.get("last_sync", "")})
            rows.append({"Section": "System / Backups", "Value": str(backup_count)})
            rows.append({"Section": "System / Exports", "Value": str(export_count)})
            rows.append({"Section": "System / Version", "Value": VERSION})

            name = f"statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            def _export_txt():
                path = export_path(f"{name}.txt")
                with open(path, "w", encoding="utf-8") as f:
                    f.write("AniListSync Statistics Report\n")
                    f.write(f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                    f.write("=" * 40 + "\n\n")
                    for row in rows:
                        f.write(f"{row['Section']}\n")
                        f.write(f"  {row['Value']}\n\n")
                return path

            export_map = {
                "json": lambda: export_json(name, json_data),
                "csv": lambda: export_csv(name, rows, headers),
                "txt": _export_txt,
                "markdown": lambda: export_markdown(name, rows, headers),
                "html": lambda: export_html(name, rows, headers),
                "excel": lambda: export_xlsx(name, rows, headers),
            }
            fn = export_map.get(fmt)
            if fn:
                path = fn()
                if path:
                    self._status_label.setText(f"Exported to {path}")
                else:
                    self._status_label.setText("Export failed")
        except Exception as e:
            self._status_label.setText(f"Export failed: {e}")
