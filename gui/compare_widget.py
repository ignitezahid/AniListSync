import json
import threading
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit,
    QGroupBox, QGridLayout, QScrollArea, QFrame, QAbstractItemView,
    QMessageBox, QDialog, QCheckBox, QDialogButtonBox,
    QApplication,
)
from PyQt6.QtGui import QTextCursor
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from gui.theme import get_log_stylesheet


class CandidateDialog(QDialog):
    def __init__(self, candidates: list, title: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Multiple Matches: {title}")
        self.setMinimumWidth(520)
        self.setMinimumHeight(420)
        self._result = None
        self._candidates = candidates
        layout = QVBoxLayout()
        layout.setSpacing(12)
        layout.addWidget(QLabel(f"Choose match for:  {title}"))

        self._table = QTableWidget()
        self._table.setColumnCount(2)
        self._table.setHorizontalHeaderLabels(["Title", "Match"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeMode.ResizeToContents)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)

        self._checkboxes = []
        for score, anime in candidates:
            row = self._table.rowCount()
            self._table.insertRow(row)
            cb = QCheckBox()
            self._checkboxes.append((cb, anime))
            self._table.setCellWidget(row, 0, cb)
            display_title = (
                anime["title"]["english"]
                or anime["title"]["romaji"]
                or anime["title"]["native"]
            )
            self._table.setItem(row, 0, QTableWidgetItem(display_title))
            self._table.setItem(row, 1, QTableWidgetItem(f"{score:.1f}%"))

        self._table.setRowCount(len(candidates))
        layout.addWidget(self._table)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(8)
        add_selected = QPushButton("Add Selected")
        add_all = QPushButton("Add All")
        add_checked = QPushButton("Add Checked")
        skip = QPushButton("Skip")

        add_selected.clicked.connect(self._on_add_selected)
        add_all.clicked.connect(self._on_add_all)
        add_checked.clicked.connect(self._on_add_checked)
        skip.clicked.connect(self._on_skip)

        btn_layout.addWidget(add_selected)
        btn_layout.addWidget(add_all)
        btn_layout.addWidget(add_checked)
        btn_layout.addWidget(skip)
        layout.addLayout(btn_layout)
        self.setLayout(layout)

    def _on_add_selected(self):
        checked = [(cb, a) for cb, a in self._checkboxes if cb.isChecked()]
        if not checked:
            return
        self._result = ("selected", [a for _, a in checked])
        self.accept()

    def _on_add_all(self):
        self._result = ("all", [a for _, a in self._candidates])
        self.accept()

    def _on_add_checked(self):
        checked = [a for cb, a in self._checkboxes if cb.isChecked()]
        if not checked:
            return
        self._result = ("checked", checked)
        self.accept()

    def _on_skip(self):
        self._result = ("skip", [])
        self.accept()

    def result_data(self):
        return self._result


class CompareWidget(QWidget):
    log_signal = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._extra_matches: list[dict] = []
        self._build_ui()
        self.log_signal.connect(self._append_log)

    def _build_ui(self):
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)

        container = QWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(16)

        heading = QLabel("Compare")
        heading.setObjectName("heading")
        sub = QLabel("Compare Telegram Saved Messages against your AniList library.")
        sub.setObjectName("subheading")
        layout.addWidget(heading)
        layout.addWidget(sub)

        self._run_btn = QPushButton("Run Compare")
        self._run_btn.setObjectName("primary")
        self._run_btn.setMinimumWidth(140)
        self._run_btn.clicked.connect(self._run_compare)
        layout.addWidget(self._run_btn)

        summary_group = QGroupBox("Summary")
        self._summary_grid = QGridLayout()
        self._summary_grid.setSpacing(8)
        summary_group.setLayout(self._summary_grid)
        layout.addWidget(summary_group)

        self._summary_keys = ["Telegram Total", "Already in AniList", "Missing from AniList", "Not Found"]
        self._summary_labels = {}
        for i, key in enumerate(self._summary_keys):
            lbl = QLabel("?")
            lbl.setStyleSheet("color: #c0caf5; font-size: 18px; font-weight: 700;")
            self._summary_labels[key] = lbl
            self._summary_grid.addWidget(QLabel(key), i, 0)
            self._summary_grid.addWidget(lbl, i, 1)

        missing_label = QLabel("Missing Entries")
        missing_label.setObjectName("section")
        layout.addWidget(missing_label)

        self._missing_table = QTableWidget()
        self._missing_table.setColumnCount(3)
        self._missing_table.setHorizontalHeaderLabels(["Title", "Status", "Media ID"])
        self._missing_table.horizontalHeader().setStretchLastSection(False)
        self._missing_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        for i in range(1, 3):
            self._missing_table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeMode.ResizeToContents)
        self._missing_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._missing_table.setAlternatingRowColors(True)
        self._missing_table.verticalHeader().setVisible(False)
        self._missing_table.setMinimumHeight(150)
        layout.addWidget(self._missing_table)

        self._log = QTextEdit()
        self._log.setReadOnly(True)
        self._log.setStyleSheet(get_log_stylesheet())
        self._log.setMinimumHeight(100)
        layout.addWidget(self._log)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #565f89; font-size: 12px;")
        layout.addWidget(self._status_label)

        layout.addStretch()
        container.setLayout(layout)
        scroll.setWidget(container)

        outer = QVBoxLayout()
        outer.setContentsMargins(0, 0, 0, 0)
        outer.addWidget(scroll)
        self.setLayout(outer)

    def _append_log(self, text):
        self._log.moveCursor(QTextCursor.MoveOperation.End)
        self._log.insertPlainText(text)

    def showEvent(self, event):
        super().showEvent(event)
        self._load_report()

    def _load_report(self):
        try:
            report = json.loads(Path("missing_anilist.json").read_text(encoding="utf-8"))
            summary = report.get("summary", {})
            self._summary_labels["Telegram Total"].setText(str(summary.get("telegram_total", "?")))
            self._summary_labels["Already in AniList"].setText(str(summary.get("already_in_anilist", "?")))
            self._summary_labels["Missing from AniList"].setText(str(summary.get("missing_from_anilist", "?")))
            self._summary_labels["Not Found"].setText(str(summary.get("not_found", "?")))
            missing = report.get("missing", [])
            self._missing_table.setRowCount(len(missing))
            for i, entry in enumerate(missing):
                self._missing_table.setItem(i, 0, QTableWidgetItem(entry.get("title", "?")))
                self._missing_table.setItem(i, 1, QTableWidgetItem("Missing"))
                self._missing_table.setItem(i, 2, QTableWidgetItem(str(entry.get("id", ""))))
        except Exception:
            for key in self._summary_keys:
                self._summary_labels[key].setText("-")
            self._missing_table.setRowCount(0)

    def reapply_theme(self):
        self._log.setStyleSheet(get_log_stylesheet())

    def _run_compare(self):
        self._run_btn.setEnabled(False)
        self._status_label.setText("Running compare...")
        QTimer.singleShot(100, self._do_compare)

    def _candidate_handler(self, all_candidates, title):
        from anilist import rank_candidates
        ranked = rank_candidates(all_candidates, title, limit=None)
        if not ranked:
            return None
        dlg = CandidateDialog(ranked, title, self)
        if dlg.exec() != QDialog.DialogCode.Accepted:
            return None
        action, items = dlg.result_data()
        if action == "skip" or not items:
            return None
        if action == "all":
            self._extra_matches.extend(items[1:])
            return items[0]
        if action in ("selected", "checked"):
            self._extra_matches.extend(items[1:])
            return items[0]
        return None

    async def _run_compare_async(self):
        import sys, asyncio, time
        import anilist
        from modes.compare import compare as original_compare
        import modes.compare

        class LiveStream:
            def __init__(self, widget):
                self._widget = widget
            def write(self, text):
                self._widget.log_signal.emit(text)
            def flush(self):
                pass

        self._extra_matches = []

        import concurrent.futures
        from PyQt6.QtWidgets import QApplication
        original_graphql = anilist.graphql_request
        _real_sleep = time.sleep
        _main_thread = threading.current_thread()
        def responsive_sleep(secs):
            if threading.current_thread() is _main_thread:
                for _ in range(int(secs * 10)):
                    QApplication.processEvents()
                    _real_sleep(0.09)
            else:
                _real_sleep(secs)
        def responsive_graphql(query, variables=None):
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                fut = pool.submit(original_graphql, query, variables)
                while True:
                    try:
                        return fut.result(timeout=0.1)
                    except concurrent.futures.TimeoutError:
                        QApplication.processEvents()

        anilist.graphql_request = responsive_graphql
        time.sleep = responsive_sleep

        def gui_search(title):
            from anilist import search_anime
            return search_anime(title, candidate_handler=self._candidate_handler)

        old_compare_search = modes.compare.search_anime
        modes.compare.search_anime = gui_search
        old_stdout = sys.stdout
        sys.stdout = LiveStream(self)

        try:
            await original_compare()

            if self._extra_matches:
                try:
                    report = json.loads(Path("missing_anilist.json").read_text(encoding="utf-8"))
                    for anime in self._extra_matches:
                        report["summary"]["missing_from_anilist"] += 1
                        report["missing"].append({
                            "telegram_title": "",
                            "matched_title": (
                                anime["title"]["english"]
                                or anime["title"]["romaji"]
                                or anime["title"]["native"]
                            ),
                            "id": anime["id"],
                            "idMal": anime["idMal"],
                            "episodes": anime["episodes"],
                            "reason": "Missing from AniList (batch)",
                        })
                    Path("missing_anilist.json").write_text(
                        json.dumps(report, indent=4, ensure_ascii=False), encoding="utf-8"
                    )
                except Exception:
                    pass

            self._load_report()
            self._status_label.setText("Compare complete")
        except Exception as e:
            self.log_signal.emit(f"\nError: {e}")
            self._status_label.setText(f"Compare failed: {e}")
        finally:
            self._run_btn.setEnabled(True)
            sys.stdout = old_stdout
            modes.compare.search_anime = old_compare_search
            anilist.graphql_request = original_graphql
            time.sleep = old_time_sleep

    def _do_compare(self):
        self._run_btn.setEnabled(False)
        self._log.clear()
        self._status_label.setText("Running compare...")
        import asyncio
        asyncio.get_event_loop().create_task(self._run_compare_async())
