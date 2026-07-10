"""Dialog classes for interactive operations previously restricted to CLI.

Provides GUI replacements for: Restore from Backup, Retry Queue Manager,
Search Cache Manager, and Alias Manager — all originally flagged "CLI Only".
"""

import re
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QHeaderView, QLineEdit, QMessageBox, QWidget, QAbstractItemView,
    QGroupBox, QGridLayout, QTabWidget,
)
from PyQt6.QtCore import Qt

from anilist import ALIASES
from utils.constants import BACKUP_DIR, RETRY_FILE, CACHE_FILE, DATA_DIR
from utils.file_utils import load_json, save_json
from utils.backup import backup_file
from shutil import copy2


# ── Utility ────────────────────────────────────────────────────────────────

def _original_backup_name(filename: str) -> str | None:
    """Extract original data filename from a timestamped backup name."""
    match = re.match(r"(.+)_\d{8}_\d{6}(\.json)$", filename)
    if not match:
        return None
    return match.group(1) + match.group(2)


# ── Restore from Backup ────────────────────────────────────────────────────

class RestoreDialog(QDialog):
    """Show a list of backups and let the user restore one."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Restore from Backup")
        self.setMinimumSize(520, 400)
        self._backups: list[Path] = []
        self._build_ui()
        self._load_backups()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(12)

        heading = QLabel("Restore a data file from a previous backup.")
        heading.setWordWrap(True)
        heading.setStyleSheet("font-size: 13px; color: #a9b1d6; padding-bottom: 4px;")
        layout.addWidget(heading)

        self._status_label = QLabel("Loading backups...")
        self._status_label.setStyleSheet("color: #565f89; font-size: 12px;")
        layout.addWidget(self._status_label)

        self._list = QListWidget()
        self._list.currentItemChanged.connect(self._on_selection)
        layout.addWidget(self._list)

        info_group = QGroupBox("Details")
        info_layout = QGridLayout()
        info_layout.setSpacing(6)
        self._info_orig = QLabel("-")
        self._info_orig.setStyleSheet("color: #c0caf5; font-weight: 600;")
        self._info_date = QLabel("-")
        self._info_date.setStyleSheet("color: #565f89;")
        info_layout.addWidget(QLabel("Original file:"), 0, 0)
        info_layout.addWidget(self._info_orig, 0, 1)
        info_layout.addWidget(QLabel("Backup date:"), 1, 0)
        info_layout.addWidget(self._info_date, 1, 1)
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)

        btn_row = QHBoxLayout()
        btn_row.addStretch()
        self._restore_btn = QPushButton("Restore Selected")
        self._restore_btn.setObjectName("primary")
        self._restore_btn.setEnabled(False)
        self._restore_btn.clicked.connect(self._do_restore)
        btn_row.addWidget(self._restore_btn)

        self._close_btn = QPushButton("Close")
        self._close_btn.clicked.connect(self.reject)
        btn_row.addWidget(self._close_btn)
        layout.addLayout(btn_row)
        self.setLayout(layout)

    def _load_backups(self):
        path = Path(BACKUP_DIR)
        if not path.is_dir():
            self._status_label.setText("No backup directory found.")
            return
        self._backups = sorted(path.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
        if not self._backups:
            self._status_label.setText("No backups found.")
            return
        self._list.blockSignals(True)
        self._list.clear()
        for bp in self._backups:
            item = QListWidgetItem(bp.name)
            item.setData(Qt.ItemDataRole.UserRole, str(bp))
            self._list.addItem(item)
        self._list.blockSignals(False)
        self._status_label.setText(f"{len(self._backups)} backup(s) found.")

    def _on_selection(self, curr, prev):
        if not curr:
            self._restore_btn.setEnabled(False)
            self._info_orig.setText("-")
            self._info_date.setText("-")
            return
        bp = Path(curr.data(Qt.ItemDataRole.UserRole))
        orig = _original_backup_name(bp.name)
        self._info_orig.setText(orig or "Unknown")
        try:
            dt = datetime.fromtimestamp(bp.stat().st_mtime)
            self._info_date.setText(dt.strftime("%Y-%m-%d %H:%M:%S"))
        except Exception:
            self._info_date.setText(str(bp.stat().st_mtime))
        self._restore_btn.setEnabled(orig is not None)

    def _do_restore(self):
        curr = self._list.currentItem()
        if not curr:
            return
        bp = Path(curr.data(Qt.ItemDataRole.UserRole))
        orig = _original_backup_name(bp.name)
        if not orig:
            QMessageBox.warning(self, "Error", "Could not detect original filename.")
            return
        reply = QMessageBox.question(
            self, "Confirm Restore",
            f"Restore {bp.name}\n→ data/{orig}?\n\n"
            "A backup of the current file will be created first.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        dest = Path(DATA_DIR) / orig
        if dest.exists():
            backup_file(orig)
        try:
            copy2(bp, dest)
        except Exception as e:
            QMessageBox.critical(self, "Restore Failed", str(e))
            return
        from core.plugin_loader import plugin_manager
        plugin_manager.call_hook("on_restore", str(bp))
        QMessageBox.information(self, "Success", f"Restored data/{orig} from backup.")
        self.accept()


# ── Retry Queue Manager ────────────────────────────────────────────────────

class RetryQueueDialog(QDialog):
    """View, remove items from, or clear the retry queue."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Retry Queue Manager")
        self.setMinimumSize(500, 380)
        self._queue: list = []
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)

        self._stats_label = QLabel("")
        self._stats_label.setStyleSheet("color: #565f89; font-size: 12px;")
        layout.addWidget(self._stats_label)

        self._list = QListWidget()
        self._list.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        layout.addWidget(self._list)

        btn_row = QHBoxLayout()
        btn_row.setSpacing(8)
        self._remove_btn = QPushButton("Remove Selected")
        self._remove_btn.clicked.connect(self._remove_selected)
        btn_row.addWidget(self._remove_btn)

        self._clear_btn = QPushButton("Clear All")
        self._clear_btn.setObjectName("danger")
        self._clear_btn.clicked.connect(self._clear_all)
        btn_row.addWidget(self._clear_btn)

        self._refresh_btn = QPushButton("Refresh")
        self._refresh_btn.clicked.connect(self._refresh)
        btn_row.addWidget(self._refresh_btn)

        btn_row.addStretch()
        self._close_btn = QPushButton("Close")
        self._close_btn.clicked.connect(self.accept)
        btn_row.addWidget(self._close_btn)
        layout.addLayout(btn_row)
        self.setLayout(layout)

    def _refresh(self):
        self._queue = load_json(RETRY_FILE, [])
        self._list.blockSignals(True)
        self._list.clear()
        for title in self._queue:
            QListWidgetItem(title, self._list)
        self._list.blockSignals(False)
        total = len(self._queue)
        self._stats_label.setText(f"Total: {total} title(s)" + (" ✓ Empty" if not total else ""))

    def _remove_selected(self):
        selected = {item.text() for item in self._list.selectedItems()}
        if not selected:
            QMessageBox.information(self, "Notice", "Select items to remove.")
            return
        if not self._queue:
            return
        self._queue = [t for t in self._queue if t not in selected]
        save_json(RETRY_FILE, self._queue)
        self._refresh()

    def _clear_all(self):
        if not self._queue:
            QMessageBox.information(self, "Notice", "Retry queue is already empty.")
            return
        reply = QMessageBox.question(
            self, "Clear Queue",
            f"Clear all {len(self._queue)} title(s) from the retry queue?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self._queue = []
        save_json(RETRY_FILE, [])
        self._refresh()


# ── Search Cache Manager ───────────────────────────────────────────────────

class SearchCacheDialog(QDialog):
    """View, search, delete, and clear the search cache."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search Cache Manager")
        self.setMinimumSize(600, 450)
        self._cache: dict = {}
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)

        tabs = QTabWidget()
        tabs.setTabPosition(QTabWidget.TabPosition.North)

        # ── View Tab ──
        view_tab = QWidget()
        view_layout = QVBoxLayout(view_tab)
        view_layout.setSpacing(8)

        search_row = QHBoxLayout()
        self._view_filter = QLineEdit()
        self._view_filter.setPlaceholderText("Filter entries...")
        self._view_filter.textChanged.connect(self._populate_view)
        search_row.addWidget(self._view_filter)
        self._view_stats = QLabel("")
        self._view_stats.setStyleSheet("color: #565f89; font-size: 12px;")
        search_row.addWidget(self._view_stats)
        view_layout.addLayout(search_row)

        self._view_table = QTableWidget()
        self._view_table.setColumnCount(3)
        self._view_table.setHorizontalHeaderLabels(["Search Query", "Matched Title", "Status"])
        self._view_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._view_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._view_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._view_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._view_table.setAlternatingRowColors(True)
        self._view_table.verticalHeader().setVisible(False)
        view_layout.addWidget(self._view_table)

        view_btn_row = QHBoxLayout()
        self._view_delete_btn = QPushButton("Delete Selected")
        self._view_delete_btn.clicked.connect(self._delete_selected)
        view_btn_row.addWidget(self._view_delete_btn)

        self._view_clear_btn = QPushButton("Clear All")
        self._view_clear_btn.setObjectName("danger")
        self._view_clear_btn.clicked.connect(self._clear_cache)
        view_btn_row.addWidget(self._view_clear_btn)

        self._view_export_btn = QPushButton("Export")
        self._view_export_btn.clicked.connect(self._export_cache)
        view_btn_row.addWidget(self._view_export_btn)

        view_btn_row.addStretch()
        view_layout.addLayout(view_btn_row)
        tabs.addTab(view_tab, "View")

        # ── Statistics Tab ──
        stats_tab = QWidget()
        stats_layout = QVBoxLayout(stats_tab)
        stats_layout.setSpacing(10)
        self._stats_grid = QGridLayout()
        self._stats_grid.setSpacing(8)
        stats_layout.addLayout(self._stats_grid)
        stats_layout.addStretch()
        tabs.addTab(stats_tab, "Statistics")

        layout.addWidget(tabs)
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)
        self.setLayout(layout)

    def _cache_title(self, anime) -> str:
        if anime is None:
            return "[NOT FOUND]"
        return (
            anime.get("title", {}).get("english")
            or anime.get("title", {}).get("romaji")
            or anime.get("title", {}).get("native")
            or "Unknown"
        )

    def _refresh(self):
        self._cache = load_json(CACHE_FILE, {})
        self._populate_view()
        self._update_stats()

    def _populate_view(self):
        query = self._view_filter.text().strip().lower()
        entries = sorted(
            [(k, v) for k, v in self._cache.items() if query in k.lower()],
            key=lambda x: x[0],
        )
        self._view_table.setRowCount(len(entries))
        for i, (key, anime) in enumerate(entries):
            self._view_table.setItem(i, 0, QTableWidgetItem(key))
            self._view_table.setItem(i, 1, QTableWidgetItem(self._cache_title(anime)))
            if anime is None:
                item = QTableWidgetItem("Not Found")
                item.setForeground(Qt.GlobalColor.red)
            else:
                item = QTableWidgetItem("Found")
                item.setForeground(Qt.GlobalColor.green)
            self._view_table.setItem(i, 2, item)
        self._view_stats.setText(f"{len(entries)} / {len(self._cache)} entries")

    def _update_stats(self):
        total = len(self._cache)
        successful = sum(1 for v in self._cache.values() if v)
        failed = total - successful
        # Clear grid
        while self._stats_grid.count():
            item = self._stats_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._stats_grid.addWidget(QLabel("Total Entries:"), 0, 0)
        lbl = QLabel(str(total))
        lbl.setStyleSheet("color: #c0caf5; font-weight: 600; font-size: 15px;")
        self._stats_grid.addWidget(lbl, 0, 1)
        self._stats_grid.addWidget(QLabel("Successful:"), 1, 0)
        lbl2 = QLabel(str(successful))
        lbl2.setStyleSheet("color: #9ece6a; font-weight: 600; font-size: 15px;")
        self._stats_grid.addWidget(lbl2, 1, 1)
        self._stats_grid.addWidget(QLabel("Not Found:"), 2, 0)
        lbl3 = QLabel(str(failed))
        lbl3.setStyleSheet("color: #f7768e; font-weight: 600; font-size: 15px;")
        self._stats_grid.addWidget(lbl3, 2, 1)

    def _delete_selected(self):
        row = self._view_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Notice", "Select an entry to delete.")
            return
        key = self._view_table.item(row, 0).text()
        if key not in self._cache:
            return
        reply = QMessageBox.question(
            self, "Delete Entry",
            f"Delete cache entry '{key}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        del self._cache[key]
        save_json(CACHE_FILE, self._cache)
        self._refresh()

    def _clear_cache(self):
        if not self._cache:
            QMessageBox.information(self, "Notice", "Cache is already empty.")
            return
        reply = QMessageBox.question(
            self, "Clear Cache",
            f"Clear all {len(self._cache)} entries from the search cache?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        save_json(CACHE_FILE, {})
        self._cache = {}
        self._refresh()

    def _export_cache(self):
        from modes.tools.export_tools import export_search_cache
        try:
            export_search_cache()
            QMessageBox.information(self, "Export", "Search cache exported successfully.")
        except Exception as e:
            QMessageBox.warning(self, "Export Failed", str(e))


# ── Alias Manager ──────────────────────────────────────────────────────────

class AliasManagerDialog(QDialog):
    """View, search, delete, detect duplicates, and view stats for aliases."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Alias Manager")
        self.setMinimumSize(650, 480)
        self._build_ui()
        self._refresh()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setSpacing(10)

        tabs = QTabWidget()

        # ── View Tab ──
        view_tab = QWidget()
        view_layout = QVBoxLayout(view_tab)
        view_layout.setSpacing(8)

        search_row = QHBoxLayout()
        self._view_filter = QLineEdit()
        self._view_filter.setPlaceholderText("Filter aliases...")
        self._view_filter.textChanged.connect(self._populate_view)
        search_row.addWidget(self._view_filter)
        self._view_stats = QLabel("")
        self._view_stats.setStyleSheet("color: #565f89; font-size: 12px;")
        search_row.addWidget(self._view_stats)
        view_layout.addLayout(search_row)

        self._view_table = QTableWidget()
        self._view_table.setColumnCount(3)
        self._view_table.setHorizontalHeaderLabels(["Alias", "Matched Title", "AniList ID"])
        self._view_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._view_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._view_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._view_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._view_table.setAlternatingRowColors(True)
        self._view_table.verticalHeader().setVisible(False)
        view_layout.addWidget(self._view_table)

        view_btn_row = QHBoxLayout()
        self._view_delete_btn = QPushButton("Delete Selected")
        self._view_delete_btn.clicked.connect(self._delete_selected)
        view_btn_row.addWidget(self._view_delete_btn)
        view_btn_row.addStretch()
        view_layout.addLayout(view_btn_row)
        tabs.addTab(view_tab, "View")

        # ── Duplicates Tab ──
        dup_tab = QWidget()
        dup_layout = QVBoxLayout(dup_tab)
        dup_layout.setSpacing(8)

        dup_info = QLabel("Detect aliases that point to the same normalized key and merge them.")
        dup_info.setWordWrap(True)
        dup_info.setStyleSheet("color: #565f89; font-size: 12px;")
        dup_layout.addWidget(dup_info)

        self._dup_table = QTableWidget()
        self._dup_table.setColumnCount(3)
        self._dup_table.setHorizontalHeaderLabels(["Normalized Key", "Duplicate Aliases", "Action"])
        self._dup_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._dup_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self._dup_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.ResizeToContents)
        self._dup_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._dup_table.setAlternatingRowColors(True)
        self._dup_table.verticalHeader().setVisible(False)
        dup_layout.addWidget(self._dup_table)

        dup_btn_row = QHBoxLayout()
        self._dup_merge_btn = QPushButton("Merge Selected Group")
        self._dup_merge_btn.setObjectName("primary")
        self._dup_merge_btn.clicked.connect(self._merge_selected_duplicates)
        dup_btn_row.addWidget(self._dup_merge_btn)
        self._dup_refresh_btn = QPushButton("Refresh")
        self._dup_refresh_btn.clicked.connect(self._populate_duplicates)
        dup_btn_row.addWidget(self._dup_refresh_btn)
        dup_btn_row.addStretch()
        dup_layout.addLayout(dup_btn_row)
        tabs.addTab(dup_tab, "Duplicates")

        # ── Statistics Tab ──
        stats_tab = QWidget()
        stats_layout = QVBoxLayout(stats_tab)
        stats_layout.setSpacing(10)
        self._stats_grid = QGridLayout()
        self._stats_grid.setSpacing(8)
        stats_layout.addLayout(self._stats_grid)
        stats_layout.addStretch()
        tabs.addTab(stats_tab, "Statistics")

        layout.addWidget(tabs)
        close_row = QHBoxLayout()
        close_row.addStretch()
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        close_row.addWidget(close_btn)
        layout.addLayout(close_row)
        self.setLayout(layout)

    def _refresh(self):
        self._populate_view()
        self._populate_duplicates()
        self._update_stats()

    def _populate_view(self):
        query = self._view_filter.text().strip().lower()
        items = sorted(
            [(k, v) for k, v in ALIASES.items() if query in k.lower()],
            key=lambda x: x[0],
        )
        self._view_table.setRowCount(len(items))
        for i, (alias, data) in enumerate(items):
            self._view_table.setItem(i, 0, QTableWidgetItem(alias))
            self._view_table.setItem(i, 1, QTableWidgetItem(data.get("title", "?")))
            self._view_table.setItem(i, 2, QTableWidgetItem(str(data.get("anilist_id", ""))))
        self._view_stats.setText(f"{len(items)} / {len(ALIASES)} aliases")

    def _populate_duplicates(self):
        def normalize(key):
            return re.sub(r"[^a-z0-9]", "", key.lower())
        groups = {}
        for key in ALIASES:
            normal = normalize(key)
            groups.setdefault(normal, []).append(key)
        duplicates = {k: v for k, v in groups.items() if len(v) > 1}
        self._dup_table.setRowCount(len(duplicates))
        for i, (normal, keys) in enumerate(sorted(duplicates.items())):
            self._dup_table.setItem(i, 0, QTableWidgetItem(normal))
            self._dup_table.setItem(i, 1, QTableWidgetItem(", ".join(keys)))
            merge_btn = QPushButton("Merge → Keep First")
            merge_btn.setMaximumWidth(140)
            merge_btn.clicked.connect(lambda _, n=normal, ks=keys: self._merge_single(n, ks))
            self._dup_table.setCellWidget(i, 2, merge_btn)

    def _merge_single(self, normal: str, keys: list[str]):
        if not keys:
            return
        keep = keys[0]
        for key in keys[1:]:
            if key in ALIASES:
                del ALIASES[key]
        save_json("aliases.json", ALIASES)
        QMessageBox.information(self, "Merged", f"Merged {len(keys) - 1} duplicate(s) into '{keep}'.")
        self._populate_duplicates()
        self._populate_view()
        self._update_stats()

    def _merge_selected_duplicates(self):
        row = self._dup_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Notice", "Select a duplicate group to merge.")
            return
        normal = self._dup_table.item(row, 0).text()
        def normalize(k):
            return re.sub(r"[^a-z0-9]", "", k.lower())
        keys = [k for k in ALIASES if normalize(k) == normal]
        if len(keys) < 2:
            return
        self._merge_single(normal, keys)

    def _delete_selected(self):
        row = self._view_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Notice", "Select an alias to delete.")
            return
        alias = self._view_table.item(row, 0).text()
        if alias not in ALIASES:
            return
        title = ALIASES[alias].get("title", "?")
        reply = QMessageBox.question(
            self, "Delete Alias",
            f"Delete alias '{alias}' → {title}?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        del ALIASES[alias]
        save_json("aliases.json", ALIASES)
        self._refresh()

    def _update_stats(self):
        total = len(ALIASES)
        while self._stats_grid.count():
            item = self._stats_grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()

        aliases = list(ALIASES.keys())
        longest = max(aliases, key=len) if aliases else "-"
        shortest = min(aliases, key=len) if aliases else "-"
        avg_len = round(sum(len(a) for a in aliases) / total, 1) if total else 0

        self._stats_grid.addWidget(QLabel("Total Aliases:"), 0, 0)
        lbl = QLabel(str(total))
        lbl.setStyleSheet("color: #c0caf5; font-weight: 600; font-size: 15px;")
        self._stats_grid.addWidget(lbl, 0, 1)

        self._stats_grid.addWidget(QLabel("Longest:"), 1, 0)
        lbl2 = QLabel(longest)
        lbl2.setStyleSheet("color: #c0caf5; font-weight: 600;")
        self._stats_grid.addWidget(lbl2, 1, 1)

        self._stats_grid.addWidget(QLabel("Shortest:"), 2, 0)
        lbl3 = QLabel(shortest)
        lbl3.setStyleSheet("color: #c0caf5; font-weight: 600;")
        self._stats_grid.addWidget(lbl3, 2, 1)

        self._stats_grid.addWidget(QLabel("Average Length:"), 3, 0)
        lbl4 = QLabel(str(avg_len))
        lbl4.setStyleSheet("color: #c0caf5; font-weight: 600;")
        self._stats_grid.addWidget(lbl4, 3, 1)
