import threading

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QGridLayout, QFrame,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from gui.widgets import scroll_area_widget, apply_outer_layout, make_log_text, LogOpsMixin, threaded_op


class BulkOpsWidget(QWidget, LogOpsMixin):
    _health_result = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._build_ui()
        self._health_result.connect(self._finish_health)

    def _build_ui(self):
        scroll, layout = scroll_area_widget()

        heading = QLabel("Bulk Operations")
        heading.setObjectName("heading")
        sub = QLabel("Batch maintenance tasks for your library.")
        sub.setObjectName("subheading")
        layout.addWidget(heading)
        layout.addWidget(sub)

        cache_group = QGroupBox("Cache Management")
        cache_grid = QGridLayout()
        cache_grid.setSpacing(8)
        cache_grid.addWidget(self._btn("Refresh AniList Cache", self._run_refresh_al), 0, 0)
        cache_grid.addWidget(self._btn("Refresh MAL Cache", self._run_refresh_mal), 0, 1)
        cache_grid.addWidget(self._btn("Refresh All IDs", self._run_refresh_all), 1, 0)
        cache_grid.addWidget(self._btn("Rebuild Statistics", self._run_rebuild_stats), 1, 1)
        cache_group.setLayout(cache_grid)
        layout.addWidget(cache_group)

        repair_group = QGroupBox("Repair & Cleanup")
        repair_grid = QGridLayout()
        repair_grid.setSpacing(8)
        repair_grid.addWidget(self._btn("Library Health Check", self._run_health), 0, 0)
        repair_grid.addWidget(self._btn("Repair Missing MAL IDs", self._run_repair_mal), 0, 1)
        repair_grid.addWidget(self._btn("Remove Duplicate Aliases", self._run_dedup), 1, 0)
        repair_grid.addWidget(self._btn("Clean Old Backups", self._run_clean), 1, 1)
        repair_grid.addWidget(self._btn("Optimize Database", self._run_optimize), 2, 0, 1, 2)
        repair_group.setLayout(repair_grid)
        layout.addWidget(repair_group)

        log_label = QLabel("Output")
        log_label.setObjectName("section")
        layout.addWidget(log_label)

        self._log = make_log_text()
        self._log.setMinimumHeight(150)
        layout.addWidget(self._log)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #565f89; font-size: 12px;")
        layout.addWidget(self._status_label)

        layout.addStretch()
        apply_outer_layout(self, scroll)

    def _btn(self, text, callback):
        btn = QPushButton(text)
        btn.clicked.connect(callback)
        btn.setMinimumHeight(36)
        return btn

    # _log_op inherited from LogOpsMixin

    def _run_refresh_al(self):
        from modes.bulk_operations import _refresh_anilist_cache
        threaded_op(self._log, self._status_label, "Refresh AniList Cache", _refresh_anilist_cache)

    def _run_refresh_mal(self):
        from modes.bulk_operations import _refresh_mal_cache
        threaded_op(self._log, self._status_label, "Refresh MAL Cache", _refresh_mal_cache)

    def _run_refresh_all(self):
        from modes.bulk_operations import _refresh_all_ids
        threaded_op(self._log, self._status_label, "Refresh All IDs", _refresh_all_ids)

    def _run_rebuild_stats(self):
        from modes.bulk_operations import _rebuild_statistics
        threaded_op(self._log, self._status_label, "Rebuild Statistics", _rebuild_statistics)

    def _run_health(self):
        self._log.clear()
        self._status_label.setText("Running Library Health...")
        def run():
            from modes.tools.health import library_health_text
            result = library_health_text()
            self._health_result.emit(result)
        threading.Thread(target=run, daemon=True).start()

    def _finish_health(self, text):
        self._log.setText(text)
        self._status_label.setText("Library Health complete")

    def _run_repair_mal(self):
        from modes.bulk_operations import _repair_missing_mal_ids
        threaded_op(self._log, self._status_label, "Repair Missing MAL IDs", _repair_missing_mal_ids)

    def _run_dedup(self):
        from modes.alias_manager import detect_duplicates
        self._log_op("Remove Duplicate Aliases", detect_duplicates)

    def _run_clean(self):
        from modes.bulk_operations import _clean_old_backups
        threaded_op(self._log, self._status_label, "Clean Old Backups", _clean_old_backups)

    def _run_optimize(self):
        from modes.bulk_operations import _optimize_database
        threaded_op(self._log, self._status_label, "Optimize Database", _optimize_database)
