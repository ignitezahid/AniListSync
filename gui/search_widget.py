from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QLineEdit, QTableWidget, QTableWidgetItem, QHeaderView,
    QScrollArea, QFrame, QMessageBox, QAbstractItemView,
    QDialog, QCheckBox, QGroupBox,
)
from PyQt6.QtCore import Qt, QTimer


class SearchWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._results = []
        self._build_ui()

    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(16)

        heading = QLabel("Search")
        heading.setObjectName("heading")
        sub = QLabel("Search for anime titles on AniList and add them to your library.")
        sub.setObjectName("subheading")
        layout.addWidget(heading)
        layout.addWidget(sub)

        search_row = QHBoxLayout()
        search_row.setSpacing(10)
        self._input = QLineEdit()
        self._input.setPlaceholderText("Search anime title...")
        self._input.returnPressed.connect(self._do_search)
        self._input.setMinimumHeight(36)
        search_row.addWidget(self._input)

        self._search_btn = QPushButton("Search")
        self._search_btn.setObjectName("primary")
        self._search_btn.setMinimumWidth(100)
        self._search_btn.clicked.connect(self._do_search)
        search_row.addWidget(self._search_btn)
        layout.addLayout(search_row)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #565f89; font-size: 12px;")
        layout.addWidget(self._status_label)

        results_label = QLabel("Results")
        results_label.setObjectName("section")
        layout.addWidget(results_label)

        self._table = QTableWidget()
        self._table.setColumnCount(6)
        self._table.setHorizontalHeaderLabels(["Title", "Type", "Score", "Episodes", "Status", "ID"])
        self._table.horizontalHeader().setStretchLastSection(False)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 6):
            self._table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setMinimumHeight(200)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        layout.addWidget(self._table)

        btn_row = QHBoxLayout()
        self._add_btn = QPushButton("Add Selected to Library")
        self._add_btn.setObjectName("primary")
        self._add_btn.clicked.connect(self._add_selected)
        self._add_btn.setEnabled(False)
        btn_row.addWidget(self._add_btn)
        btn_row.addStretch()
        layout.addLayout(btn_row)

        layout.addStretch()
        container.setLayout(layout)
        scroll.setWidget(container)

        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        self.setLayout(outer)

    def _do_search(self):
        query = self._input.text().strip()
        if not query:
            return
        self._status_label.setText("Searching...")
        self._search_btn.setEnabled(False)
        QTimer.singleShot(100, lambda: self._run_search(query))

    def _run_search(self, query):
        try:
            from anilist import search_all
            results = search_all(query)
            if results:
                self._results = results
                self._populate_table(results)
                self._status_label.setText(f"Found {len(results)} result(s)")
                self._add_btn.setEnabled(True)
            else:
                self._table.setRowCount(0)
                self._results = []
                self._status_label.setText("No results found")
                self._add_btn.setEnabled(False)
        except Exception as e:
            self._status_label.setText(f"Search failed: {e}")
        finally:
            self._search_btn.setEnabled(True)

    def _populate_table(self, results):
        self._table.setRowCount(len(results))
        for i, anime in enumerate(results):
            title = anime.get("title", {}).get("romaji", anime.get("title", {}).get("english", "?"))
            self._table.setItem(i, 0, QTableWidgetItem(title))
            self._table.setItem(i, 1, QTableWidgetItem(anime.get("type", "?")))
            score = anime.get("averageScore")
            self._table.setItem(i, 2, QTableWidgetItem(str(score) if score else "?"))
            eps = anime.get("episodes")
            self._table.setItem(i, 3, QTableWidgetItem(str(eps) if eps else "?"))
            status = anime.get("status", "?").replace("_", " ").title()
            self._table.setItem(i, 4, QTableWidgetItem(status))
            self._table.setItem(i, 5, QTableWidgetItem(str(anime.get("id", ""))))

    def _title_of(self, anime):
        return anime.get("title", {}).get("romaji") or anime.get("title", {}).get("english") or "?"

    def _add_selected(self):
        row = self._table.currentRow()
        if row < 0 or row >= len(self._results):
            QMessageBox.information(self, "Notice", "Select a result first.")
            return
        anime = self._results[row]
        from anilist import get_media_with_relations
        selected, related = get_media_with_relations(anime["id"])
        if not selected:
            selected = anime

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Add: {self._title_of(selected)}")
        dlg.setMinimumWidth(500)
        dlg.setMinimumHeight(400)
        vl = QVBoxLayout(dlg)

        info = QLabel(f"<b>{self._title_of(selected)}</b>")
        info.setStyleSheet("font-size: 16px; color: #7aa2f7;")
        vl.addWidget(info)

        if not related:
            vl.addWidget(QLabel("No related franchise entries found."))
            btn = QPushButton("Add Selected Only")
            btn.setObjectName("primary")
            def add_only():
                dlg.accept()
                QTimer.singleShot(100, lambda: self._run_add(selected))
            btn.clicked.connect(add_only)
            vl.addWidget(btn)
            cancel = QPushButton("Cancel")
            cancel.clicked.connect(dlg.reject)
            vl.addWidget(cancel)
            dlg.exec()
            return

        import json
        try:
            with open("state.json", encoding="utf-8") as f:
                state = json.load(f)
            library_ids = set(state.get("anilist_ids", []))
        except Exception:
            library_ids = set()

        available = [a for a in related if a["id"] not in library_ids]
        in_library = [a for a in related if a["id"] in library_ids]

        if in_library:
            group = QGroupBox("Already in Library")
            gvl = QVBoxLayout()
            for a in in_library:
                gvl.addWidget(QLabel(f"✓  {self._title_of(a)}"))
            group.setLayout(gvl)
            vl.addWidget(group)

        if not available:
            vl.addWidget(QLabel("All related anime already in library."))
            btn = QPushButton("Add Selected Only")
            btn.setObjectName("primary")
            def add_only_2():
                dlg.accept()
                QTimer.singleShot(100, lambda: self._run_add(selected))
            btn.clicked.connect(add_only_2)
            vl.addWidget(btn)
            cancel = QPushButton("Cancel")
            cancel.clicked.connect(dlg.reject)
            vl.addWidget(cancel)
            dlg.exec()
            return

        group = QGroupBox("Franchise")
        gvl = QVBoxLayout()
        format_order = ["TV", "TV_SHORT", "MOVIE", "OVA", "ONA", "SPECIAL", "MUSIC"]
        format_labels = {"TV_SHORT": "TV Short", "MOVIE": "Movie"}
        groups = {}
        for a in available:
            fmt = a.get("format") or "OTHER"
            groups.setdefault(fmt, []).append(a)

        checkboxes = {}
        for fmt in format_order:
            items = groups.get(fmt)
            if not items:
                continue
            label = format_labels.get(fmt, fmt.title())
            hdr = QLabel(f"<b>{label}</b>")
            hdr.setStyleSheet("color: #c0caf5; margin-top: 4px;")
            gvl.addWidget(hdr)
            for a in items:
                cb = QCheckBox(self._title_of(a))
                checkboxes[a["id"]] = cb
                gvl.addWidget(cb)
        for fmt, items in groups.items():
            if fmt in format_order:
                continue
            for a in items:
                cb = QCheckBox(self._title_of(a))
                checkboxes[a["id"]] = cb
                gvl.addWidget(cb)
        group.setLayout(gvl)
        vl.addWidget(group)

        btn_row = QHBoxLayout()
        add_sel = QPushButton("Add Selected Only")
        add_sel.clicked.connect(lambda: (dlg.accept(), QTimer.singleShot(100, lambda: self._run_add(selected))))
        btn_row.addWidget(add_sel)

        add_all = QPushButton("Add All Available")
        add_all.setObjectName("primary")
        def do_add_all():
            dlg.accept()
            to_add = [selected] + available
            QTimer.singleShot(100, lambda: self._run_batch(to_add))
        add_all.clicked.connect(do_add_all)
        btn_row.addWidget(add_all)
        vl.addLayout(btn_row)

        choose_row = QHBoxLayout()
        add_chosen = QPushButton("Add Checked")
        add_chosen.setObjectName("primary")
        def do_add_checked():
            dlg.accept()
            to_add = [selected]
            for a in available:
                cb = checkboxes.get(a["id"])
                if cb and cb.isChecked():
                    to_add.append(a)
            QTimer.singleShot(100, lambda: self._run_batch(to_add))
        add_chosen.clicked.connect(do_add_checked)
        choose_row.addWidget(add_chosen)

        cancel = QPushButton("Cancel")
        cancel.clicked.connect(dlg.reject)
        choose_row.addWidget(cancel)
        vl.addLayout(choose_row)

        dlg.exec()

    def _run_add(self, anime):
        try:
            from sync import add_selected_anime
            add_selected_anime(anime)
            self._status_label.setText("Added successfully")
        except Exception as e:
            self._status_label.setText(f"Failed: {e}")
        finally:
            self._add_btn.setEnabled(True)

    def _run_batch(self, to_add):
        try:
            from sync import add_anime_batch, add_selected_anime
            if len(to_add) == 1:
                add_selected_anime(to_add[0])
            else:
                add_anime_batch(to_add)
            self._status_label.setText(f"Added {len(to_add)} anime")
        except Exception as e:
            self._status_label.setText(f"Failed: {e}")
        finally:
            self._add_btn.setEnabled(True)
