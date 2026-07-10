import json
import threading
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QComboBox, QTextEdit, QFrame, QAbstractItemView,
    QStyledItemDelegate, QStyle, QApplication,
)
from PyQt6.QtGui import QPixmap, QFont, QPainter
from PyQt6.QtCore import Qt, QTimer, QSize, pyqtSignal, QRectF

from gui.widgets import scroll_area_widget, apply_outer_layout
from utils.constants import COVER_CACHE_DIR, DATA_DIR


class CoverDelegate(QStyledItemDelegate):
    def __init__(self, pixmaps: dict):
        super().__init__()
        self._pixmaps = pixmaps

    def paint(self, painter, option, index):
        pixmap = self._pixmaps.get(index.data(Qt.ItemDataRole.UserRole))
        if pixmap:
            painter.save()
            painter.setClipRect(option.rect)
            painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
            scaled = pixmap.scaled(
                option.rect.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            x = option.rect.x() + (option.rect.width() - scaled.width()) // 2
            y = option.rect.y() + (option.rect.height() - scaled.height()) // 2
            painter.drawPixmap(x, y, scaled)
            painter.restore()
        else:
            super().paint(painter, option, index)


class LibraryWidget(QWidget):
    cover_loaded = pyqtSignal(str, object)
    library_ready = pyqtSignal()

    def __init__(self):
        super().__init__()
        self._library = []
        self._pixmaps: dict[str, QPixmap] = {}
        self._pending: dict[str, list[int]] = {}
        self._cover_cache_dir = Path(DATA_DIR) / COVER_CACHE_DIR
        self._cover_cache_dir.mkdir(parents=True, exist_ok=True)
        self.cover_loaded.connect(self._on_cover_loaded)
        self.library_ready.connect(self._on_library_ready)
        self._loaded = False
        self._build_ui()
        QTimer.singleShot(0, self._preload)

    def _build_ui(self):
        scroll, layout = scroll_area_widget()

        heading = QLabel("Library Search")
        heading.setObjectName("heading")
        sub = QLabel("Search and filter your existing AniList library.")
        sub.setObjectName("subheading")
        layout.addWidget(heading)
        layout.addWidget(sub)

        filter_row = QHBoxLayout()
        filter_row.setSpacing(10)
        self._input = QLineEdit()
        self._input.setPlaceholderText("Search your library...")
        self._input.returnPressed.connect(self._do_search)
        self._input.setMinimumHeight(36)
        filter_row.addWidget(self._input)

        self._filter_combo = QComboBox()
        self._filter_combo.addItems(["All", "Watching", "Completed", "Planning", "Dropped"])
        filter_row.addWidget(self._filter_combo)

        self._search_btn = QPushButton("Search")
        self._search_btn.setObjectName("primary")
        self._search_btn.setMinimumWidth(100)
        self._search_btn.clicked.connect(self._do_search)
        filter_row.addWidget(self._search_btn)

        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.clicked.connect(self._refresh_library)
        filter_row.addWidget(self._refresh_btn)
        layout.addLayout(filter_row)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #565f89; font-size: 12px;")
        layout.addWidget(self._status_label)

        recent_label = QLabel("Recent Searches")
        recent_label.setObjectName("section")
        layout.addWidget(recent_label)

        self._recent_label = QLabel("")
        self._recent_label.setStyleSheet("color: #565f89; font-size: 12px;")
        layout.addWidget(self._recent_label)

        results_label = QLabel("Results")
        results_label.setObjectName("section")
        layout.addWidget(results_label)

        self._table = QTableWidget()
        self._table.setColumnCount(7)
        self._table.setHorizontalHeaderLabels(["", "Title", "Status", "Score", "Episodes", "Season", "Year"])
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self._table.setColumnWidth(0, 52)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        for i in range(2, 7):
            self._table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setItemDelegateForColumn(0, CoverDelegate(self._pixmaps))
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setMinimumHeight(450)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.verticalHeader().setDefaultSectionSize(72)
        font = self._table.font()
        font.setPointSize(10)
        self._table.setFont(font)
        layout.addWidget(self._table, 1)
        apply_outer_layout(self, scroll)

    def showEvent(self, event):
        super().showEvent(event)
        self._load_recent()
        if not self._loaded:
            self._loaded = True
            if self._library:
                self._do_search()
                self._status_label.setText(f"{len(self._library)} entries")
            else:
                self._status_label.setText("Loading...")

    def _preload(self):
        def load():
            try:
                from anilist import get_completed_anime
                self._library = get_completed_anime()
            except Exception:
                pass
            self.library_ready.emit()
        threading.Thread(target=load, daemon=True).start()

    def _on_library_ready(self):
        if self._library and self._loaded:
            self._do_search()
            self._status_label.setText(f"{len(self._library)} entries")

    def _load_recent(self):
        try:
            hist = json.loads(Path("search_history.json").read_text(encoding="utf-8"))
            if hist:
                self._recent_label.setText("  " + ",  ".join(hist[:5]))
        except Exception:
            pass

    def _refresh_library(self):
        self._library = []
        self._table.setRowCount(0)
        self._status_label.setText("Refreshing library...")
        QTimer.singleShot(100, self._run_refresh)

    def _run_refresh(self):
        try:
            from anilist import get_completed_anime
            self._library = get_completed_anime(force_refresh=True)
            from gui.statistics_widget import invalidate_library_cache
            invalidate_library_cache()
            self._status_label.setText(f"Library refreshed: {len(self._library)} entries")
            self._do_search()
        except Exception as e:
            self._status_label.setText(f"Refresh failed: {e}")

    def _do_search(self):
        query = self._input.text().strip().lower()
        filter_text = self._filter_combo.currentText()

        filtered = []
        for anime in self._library:
            title = anime.get("title") or ""
            if query and query not in title.lower():
                continue
            if filter_text != "All" and anime.get("status") != filter_text.upper():
                continue
            filtered.append(anime)
        if query:
            filtered.sort(key=lambda a: (a.get("season_year") or 0, a.get("season_order") or 0, (a.get("title") or "").lower()))
        else:
            filtered.sort(key=lambda a: (a.get("title") or "").lower())

        self._populate_table(filtered)
        self._status_label.setText(f"{len(filtered)} result(s)")

    def _populate_table(self, results):
        self._table.setRowCount(len(results))
        new_pending: dict[str, list[int]] = {}
        for i, anime in enumerate(results):
            cover_url = anime.get("cover_image") or ""
            item = QTableWidgetItem()
            if cover_url in self._pixmaps:
                item.setData(Qt.ItemDataRole.UserRole, cover_url)
            elif cover_url:
                cache_path = self._cover_cache_dir / self._cover_filename(cover_url)
                if cache_path.exists():
                    pixmap = QPixmap(str(cache_path))
                    if not pixmap.isNull():
                        pixmap = pixmap.scaledToWidth(52, Qt.TransformationMode.SmoothTransformation)
                        self._pixmaps[cover_url] = pixmap
                        item.setData(Qt.ItemDataRole.UserRole, cover_url)
                    else:
                        item = None
                else:
                    if cover_url not in new_pending:
                        new_pending[cover_url] = []
                    new_pending[cover_url].append(i)
                    if cover_url not in self._pending:
                        threading.Thread(target=self._load_image, args=(cover_url,), daemon=True).start()
                    item = None
            else:
                item = None
            self._table.setItem(i, 0, item or QTableWidgetItem(""))

            title = anime.get("title") or "?"
            title_item = QTableWidgetItem(title)
            title_item.setFont(QFont("", 11))
            self._table.setItem(i, 1, title_item)

            status = (anime.get("status") or "?").replace("_", " ").title()
            self._table.setItem(i, 2, QTableWidgetItem(status))
            score = anime.get("score")
            self._table.setItem(i, 3, QTableWidgetItem(str(score) if score else "-"))
            eps = anime.get("episodes")
            self._table.setItem(i, 4, QTableWidgetItem(str(eps) if eps else "-"))
            season = anime.get("season", "")
            self._table.setItem(i, 5, QTableWidgetItem(season if season else "-"))
            year = anime.get("season_year")
            self._table.setItem(i, 6, QTableWidgetItem(str(year) if year else "-"))
        self._pending = new_pending

    @staticmethod
    def _cover_filename(url):
        return Path(url.rsplit("/", 1)[-1] or "cover.jpg")

    def _load_image(self, url):
        try:
            import requests
            resp = requests.get(url, timeout=10)
            if resp.status_code == 200:
                cache_path = self._cover_cache_dir / self._cover_filename(url)
                try:
                    cache_path.write_bytes(resp.content)
                except Exception:
                    pass
                self.cover_loaded.emit(url, resp.content)
        except Exception:
            pass

    def _on_cover_loaded(self, url, data):
        pixmap = QPixmap()
        if pixmap.loadFromData(data):
            pixmap = pixmap.scaledToWidth(52, Qt.TransformationMode.SmoothTransformation)
            self._pixmaps[url] = pixmap
            for row in self._pending.get(url, []):
                item = self._table.item(row, 0)
                if item:
                    item.setData(Qt.ItemDataRole.UserRole, url)
            self._table.viewport().update()

    def reapply_theme(self):
        app = QApplication.instance()
        self._repolish(app)

    def _repolish(self, app):
        for child in self.findChildren(QWidget):
            app.style().unpolish(child)
            app.style().polish(child)
            child.update()
        app.style().unpolish(self)
        app.style().polish(self)
        self.update()
