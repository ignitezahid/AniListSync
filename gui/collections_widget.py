from pathlib import Path
import json
from datetime import datetime

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QListWidget, QListWidgetItem, QTableWidget, QTableWidgetItem,
    QHeaderView, QInputDialog, QMessageBox, QScrollArea, QFrame,
    QAbstractItemView, QTextEdit, QDialog, QCheckBox,
)
from PyQt6.QtCore import Qt, QTimer

from gui.widgets import scroll_area_widget, apply_outer_layout
from utils.file_utils import load_json, save_json
from utils.constants import COLLECTIONS_FILE


class CollectionsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._collections = {}
        self._lib_lookup = {}
        self._build_ui()

    def _build_ui(self):
        scroll, layout = scroll_area_widget()

        heading = QLabel("Collections")
        heading.setObjectName("heading")
        sub = QLabel("Create and manage custom anime collections.")
        sub.setObjectName("subheading")
        layout.addWidget(heading)
        layout.addWidget(sub)

        content = QHBoxLayout()
        content.setSpacing(16)

        left = QVBoxLayout()
        left.setSpacing(8)
        left_label = QLabel("Collections")
        left_label.setObjectName("section")
        left.addWidget(left_label)

        self._list = QListWidget()
        self._list.setMinimumWidth(200)
        self._list.currentItemChanged.connect(self._on_select)
        left.addWidget(self._list)

        btn_row1 = QHBoxLayout()
        self._create_btn = QPushButton("+ New")
        self._create_btn.clicked.connect(self._create)
        btn_row1.addWidget(self._create_btn)
        self._rename_btn = QPushButton("Rename")
        self._rename_btn.clicked.connect(self._rename)
        btn_row1.addWidget(self._rename_btn)
        self._delete_btn = QPushButton("Delete")
        self._delete_btn.clicked.connect(self._delete)
        btn_row1.addWidget(self._delete_btn)
        left.addLayout(btn_row1)

        btn_row2 = QHBoxLayout()
        self._export_btn = QPushButton("Export")
        self._export_btn.clicked.connect(self._export)
        btn_row2.addWidget(self._export_btn)
        left.addLayout(btn_row2)

        self._stats_label = QLabel("")
        self._stats_label.setStyleSheet("color: #565f89; font-size: 12px; padding: 4px 0;")
        left.addWidget(self._stats_label)

        content.addLayout(left)

        right = QVBoxLayout()
        right.setSpacing(8)
        right_label = QLabel("Entries")
        right_label.setObjectName("section")
        right.addWidget(right_label)

        self._entries_table = QTableWidget()
        self._entries_table.setColumnCount(4)
        self._entries_table.setHorizontalHeaderLabels(["Title", "Score", "Episodes", "Status"])
        self._entries_table.horizontalHeader().setStretchLastSection(False)
        self._entries_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 4):
            self._entries_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        self._entries_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._entries_table.setAlternatingRowColors(True)
        self._entries_table.verticalHeader().setVisible(False)
        self._entries_table.setMinimumHeight(150)
        right.addWidget(self._entries_table)

        entry_btn_row = QHBoxLayout()
        self._add_entry_btn = QPushButton("Add Anime")
        self._add_entry_btn.clicked.connect(self._add_entry)
        entry_btn_row.addWidget(self._add_entry_btn)
        self._remove_entry_btn = QPushButton("Remove Selected")
        self._remove_entry_btn.clicked.connect(self._remove_entry)
        entry_btn_row.addWidget(self._remove_entry_btn)
        entry_btn_row.addStretch()
        right.addLayout(entry_btn_row)

        content.addLayout(right, 1)
        layout.addLayout(content)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #565f89; font-size: 12px;")
        layout.addWidget(self._status_label)

        layout.addStretch()
        apply_outer_layout(self, scroll)

    def showEvent(self, event):
        super().showEvent(event)
        self._reload()

    def _reload(self):
        self._collections = load_json(COLLECTIONS_FILE, {})
        self._lib_lookup = self._build_lib_lookup()
        self._list.blockSignals(True)
        self._list.clear()
        for name in sorted(self._collections.keys()):
            col = self._collections[name]
            icon = col.get("icon", "")
            label = f"{icon}  {name}" if icon else name
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, name)
            self._list.addItem(item)
        self._list.blockSignals(False)
        self._entries_table.setRowCount(0)

    def _build_lib_lookup(self):
        lookup = {}
        try:
            from anilist import get_completed_anime
            for a in get_completed_anime():
                aid = a.get("id")
                if aid:
                    lookup[aid] = a
        except Exception:
            pass
        return lookup

    def _on_select(self, curr, prev):
        if not curr:
            self._entries_table.setRowCount(0)
            self._stats_label.setText("")
            return
        name = curr.data(Qt.ItemDataRole.UserRole)
        col = self._collections.get(name)
        if not col:
            return
        entries = col.get("entries", [])
        total = len(entries)
        completed = 0
        total_score = 0
        scored = 0
        for e in entries:
            anime = self._lib_lookup.get(e.get("id"), {})
            if anime.get("status") == "COMPLETED":
                completed += 1
            s = anime.get("score")
            if s:
                total_score += s
                scored += 1
        avg = round(total_score / scored, 1) if scored else 0
        self._stats_label.setText(f"Total: {total}  Completed: {completed}  Avg: {avg}")

        self._entries_table.setRowCount(len(entries))
        for i, entry in enumerate(entries):
            aid = entry.get("id")
            anime = self._lib_lookup.get(aid, {})
            title = entry.get("title", "") or \
                    (anime.get("title", {}) or {}).get("romaji", "") or \
                    (anime.get("title", {}) or {}).get("english", "") or str(aid)
            self._entries_table.setItem(i, 0, QTableWidgetItem(title))
            score = anime.get("score")
            self._entries_table.setItem(i, 1, QTableWidgetItem(str(score) if score else "-"))
            eps = anime.get("episodes")
            self._entries_table.setItem(i, 2, QTableWidgetItem(str(eps) if eps else "-"))
            status = (anime.get("status") or "?").replace("_", " ").title()
            self._entries_table.setItem(i, 3, QTableWidgetItem(status))

    def _create(self):
        name, ok = QInputDialog.getText(self, "Create Collection", "Collection name:")
        if not ok or not name.strip():
            return
        name = name.strip()
        if name in self._collections:
            QMessageBox.warning(self, "Error", f"Collection '{name}' already exists.")
            return
        icon, ok = QInputDialog.getText(self, "Collection Icon", "Emoji icon (optional):")
        icon = icon.strip() if ok else ""
        self._collections[name] = {
            "icon": icon,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "entries": [],
        }
        save_json(COLLECTIONS_FILE, self._collections)
        self._reload()
        self._status_label.setText(f"Created collection '{name}'")

    def _rename(self):
        curr = self._list.currentItem()
        if not curr:
            return
        old_name = curr.data(Qt.ItemDataRole.UserRole)
        new_name, ok = QInputDialog.getText(self, "Rename Collection", "New name:", text=old_name)
        if not ok or not new_name.strip() or new_name.strip() == old_name:
            return
        new_name = new_name.strip()
        self._collections[new_name] = self._collections.pop(old_name)
        self._collections[new_name]["updated_at"] = datetime.now().isoformat()
        save_json(COLLECTIONS_FILE, self._collections)
        self._reload()
        self._status_label.setText(f"Renamed to '{new_name}'")

    def _delete(self):
        curr = self._list.currentItem()
        if not curr:
            return
        name = curr.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(self, "Delete Collection",
                                     f"Delete '{name}'?", QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply != QMessageBox.StandardButton.Yes:
            return
        del self._collections[name]
        save_json(COLLECTIONS_FILE, self._collections)
        self._reload()
        self._status_label.setText(f"Deleted '{name}'")

    def _export(self):
        curr = self._list.currentItem()
        if not curr:
            return
        name = curr.data(Qt.ItemDataRole.UserRole)
        from modes.collection_manager import _export_collection
        try:
            _export_collection(self._collections)
            self._status_label.setText(f"Exported '{name}'")
        except Exception as e:
            self._status_label.setText(f"Export failed: {e}")

    def _show_stats(self):
        curr = self._list.currentItem()
        if not curr:
            return
        name = curr.data(Qt.ItemDataRole.UserRole)
        col = self._collections.get(name, {})
        entries = col.get("entries", [])
        total = len(entries)
        completed = 0
        total_score = 0
        scored = 0
        for e in entries:
            anime = self._lib_lookup.get(e.get("id"), {})
            if anime.get("status") == "COMPLETED":
                completed += 1
            s = anime.get("score")
            if s:
                total_score += s
                scored += 1
        QMessageBox.information(self, f"Stats: {name}",
                                f"Total: {total}\nCompleted: {completed}\nAvg Score: {avg}")

    def _add_entry(self):
        curr = self._list.currentItem()
        if not curr:
            QMessageBox.information(self, "Notice", "Select a collection first.")
            return
        name = curr.data(Qt.ItemDataRole.UserRole)
        col = self._collections.get(name)
        if col is None:
            return

        from anilist import get_completed_anime
        library = get_completed_anime()
        existing_ids = {e["id"] for e in col.get("entries", [])}

        mode, ok = QInputDialog.getItem(self, "Add Anime", "Select method:",
                                        ["Search by title", "Filter by tag"], 0, False)
        if not ok:
            return

        if mode == "Search by title":
            query, ok = QInputDialog.getText(self, "Search Title", "Search:")
            if not ok or not query:
                return
            query = query.strip().lower()
            matches = [a for a in library if query in (a.get("title") or "").lower()]
        else:
            all_genres = sorted(set(g for a in library for g in a.get("genres") or []))
            pick_dlg = QDialog(self)
            pick_dlg.setWindowTitle("Select Tags")
            pick_dlg.setMinimumWidth(350)
            pick_dlg.setMinimumHeight(400)
            pvl = QVBoxLayout(pick_dlg)
            scroll = QScrollArea()
            scroll.setWidgetResizable(True)
            scroll.setFrameShape(QFrame.Shape.NoFrame)
            cw = QWidget()
            cvl = QVBoxLayout(cw)
            genre_cbs = {}
            for g in all_genres:
                cb = QCheckBox(g)
                cb.setChecked(False)
                genre_cbs[g] = cb
                cvl.addWidget(cb)
            cvl.addStretch()
            scroll.setWidget(cw)
            pvl.addWidget(scroll, 1)
            ok_btn = QPushButton("OK")
            ok_btn.setObjectName("primary")
            def close_pick():
                pick_dlg.accept()
            ok_btn.clicked.connect(close_pick)
            pvl.addWidget(ok_btn)
            pick_dlg.exec()
            selected_genres = {g for g, cb in genre_cbs.items() if cb.isChecked()}
            if not selected_genres:
                return
            matches = [a for a in library if any(g in selected_genres for g in (a.get("genres") or []))]

        if not matches:
            QMessageBox.information(self, "No Matches", "No matches found.")
            return

        dlg = QDialog(self)
        dlg.setWindowTitle("Select Anime to Add")
        dlg.setMinimumWidth(450)
        dlg.setMinimumHeight(400)
        vl = QVBoxLayout(dlg)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        cw = QWidget()
        cvl = QVBoxLayout(cw)

        checkboxes = {}
        for a in matches:
            title = a.get("title") or "?"
            exists = "✓" if a["id"] in existing_ids else ""
            cb = QCheckBox(f"{title} {exists}" if exists else title)
            if a["id"] not in existing_ids:
                cb.setChecked(True)
            checkboxes[a["id"]] = (cb, a)
            cvl.addWidget(cb)
        cvl.addStretch()
        scroll.setWidget(cw)
        vl.addWidget(scroll, 1)

        btn_row = QHBoxLayout()
        add_btn = QPushButton("Add Checked")
        add_btn.setObjectName("primary")
        def do_add():
            added = 0
            skipped = 0
            entries = col.setdefault("entries", [])
            existing = {e["id"] for e in entries}
            for aid, (cb, a) in checkboxes.items():
                if cb.isChecked():
                    if aid in existing:
                        skipped += 1
                    else:
                        from datetime import date
                        entries.append({
                            "id": a["id"],
                            "idMal": a.get("idMal"),
                            "title": a.get("title"),
                            "added_at": str(date.today()),
                        })
                        added += 1
            if added or skipped:
                col["updated_at"] = datetime.now().isoformat()
                save_json(COLLECTIONS_FILE, self._collections)
                self._reload()
                self._on_select(self._list.currentItem(), None)
                self._status_label.setText(f"Added: {added}  Already existed: {skipped}")
            else:
                self._status_label.setText("Nothing to add")
            dlg.accept()
        add_btn.clicked.connect(do_add)
        btn_row.addWidget(add_btn)

        cancel = QPushButton("Cancel")
        cancel.clicked.connect(dlg.reject)
        btn_row.addWidget(cancel)
        vl.addLayout(btn_row)

        dlg.exec()

    def _remove_entry(self):
        curr = self._list.currentItem()
        if not curr:
            return
        name = curr.data(Qt.ItemDataRole.UserRole)
        row = self._entries_table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Notice", "Select an entry to remove.")
            return
        entries = self._collections[name].get("entries", [])
        if row < len(entries):
            del entries[row]
            self._collections[name]["entries"] = entries
            self._collections[name]["updated_at"] = datetime.now().isoformat()
            save_json(COLLECTIONS_FILE, self._collections)
            self._on_select(self._list.currentItem(), None)
            self._status_label.setText("Entry removed")
