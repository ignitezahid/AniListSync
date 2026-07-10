import io
import json
from contextlib import redirect_stdout
from pathlib import Path

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QGridLayout, QFrame, QAbstractItemView,
)
from PyQt6.QtCore import Qt, QTimer

from gui.widgets import scroll_area_widget, apply_outer_layout, make_log_text, LogOpsMixin


class RepairWidget(QWidget, LogOpsMixin):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        scroll, layout = scroll_area_widget()

        heading = QLabel("Repair")
        heading.setObjectName("heading")
        sub = QLabel("Manually repair missing or unmatched entries from the compare report.")
        sub.setObjectName("subheading")
        layout.addWidget(heading)
        layout.addWidget(sub)

        counts_group = QGroupBox("Report Summary")
        self._counts_grid = QGridLayout()
        self._counts_grid.setSpacing(8)
        counts_group.setLayout(self._counts_grid)

        self._missing_count_label = QLabel("?")
        self._missing_count_label.setStyleSheet("color: #f7768e; font-size: 18px; font-weight: 700;")
        self._notfound_count_label = QLabel("?")
        self._notfound_count_label.setStyleSheet("color: #e0af68; font-size: 18px; font-weight: 700;")

        self._counts_grid.addWidget(QLabel("Missing from AniList:"), 0, 0)
        self._counts_grid.addWidget(self._missing_count_label, 0, 1)
        self._counts_grid.addWidget(QLabel("Not Found:"), 1, 0)
        self._counts_grid.addWidget(self._notfound_count_label, 1, 1)
        layout.addWidget(counts_group)

        actions = QHBoxLayout()
        actions.setSpacing(12)
        self._repair_missing_btn = QPushButton("Repair Missing")
        self._repair_missing_btn.clicked.connect(lambda: self._run_repair("missing"))
        actions.addWidget(self._repair_missing_btn)

        self._repair_notfound_btn = QPushButton("Repair Not Found")
        self._repair_notfound_btn.clicked.connect(lambda: self._run_repair("not_found"))
        actions.addWidget(self._repair_notfound_btn)

        self._auto_repair_btn = QPushButton("Auto Repair (70%+)")
        self._auto_repair_btn.setObjectName("primary")
        self._auto_repair_btn.clicked.connect(self._auto_repair)
        actions.addWidget(self._auto_repair_btn)

        actions.addStretch()
        layout.addLayout(actions)

        self._log = make_log_text()
        self._log.setMinimumHeight(200)
        layout.addWidget(self._log)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #565f89; font-size: 12px;")
        layout.addWidget(self._status_label)

        layout.addStretch()
        apply_outer_layout(self, scroll)

    def showEvent(self, event):
        super().showEvent(event)
        self._load_counts()

    def _load_counts(self):
        report = {}
        try:
            report = json.loads(Path("missing_anilist.json").read_text(encoding="utf-8"))
        except Exception:
            report = {}
        summary = report.get("summary", {}) if isinstance(report, dict) else {}
        missing = summary.get("missing_from_anilist", 0)
        nf = summary.get("not_found", 0)
        self._missing_count_label.setText(str(missing))
        self._notfound_count_label.setText(str(nf))

    def _run_repair(self, which):
        self._log.clear()
        self._status_label.setText(f"Repairing {which}...")
        try:
            from modes.repair import repair
            buf = io.StringIO()
            with redirect_stdout(buf):
                repair()
            self._log.setText(buf.getvalue())
            self._load_counts()
            self._status_label.setText("Repair complete")
        except Exception as e:
            self._log.setText(str(e))
            self._status_label.setText(f"Repair failed: {e}")

    def _auto_repair(self):
        self._log.clear()
        self._status_label.setText("Running auto repair...")
        try:
            from modes.repair import auto_repair
            report = {}
            try:
                report = json.loads(Path("missing_anilist.json").read_text(encoding="utf-8"))
            except Exception:
                report = {}
            buf = io.StringIO()
            with redirect_stdout(buf):
                auto_repair(report)
            self._log.setText(buf.getvalue())
            self._load_counts()
            self._status_label.setText("Auto repair complete")
        except Exception as e:
            self._log.setText(str(e))
            self._status_label.setText(f"Auto repair failed: {e}")
