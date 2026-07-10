import threading

from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QCheckBox, QGroupBox, QComboBox, QTextEdit,
)

from gui.widgets import scroll_area_widget, apply_outer_layout, make_log_text
from settings import get_setting, set_setting


class AutomationWidget(QWidget):
    _health_result = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self._build_ui()
        self._health_result.connect(self._finish_health)
        self._load_state()

    def _build_ui(self):
        scroll, layout = scroll_area_widget(spacing=18)

        heading = QLabel("Automation")
        heading.setObjectName("heading")
        sub = QLabel("Configure and manage scheduled sync automation.")
        sub.setObjectName("subheading")
        layout.addWidget(heading)
        layout.addWidget(sub)

        toggle_group = QGroupBox("Status")
        toggle_layout = QVBoxLayout()
        toggle_layout.setSpacing(8)
        self._enabled_cb = QCheckBox("Enable Scheduled Sync")
        self._enabled_cb.toggled.connect(self._on_toggle)
        toggle_layout.addWidget(self._enabled_cb)
        toggle_group.setLayout(toggle_layout)
        layout.addWidget(toggle_group)

        config_group = QGroupBox("Configuration")
        config_layout = QVBoxLayout()
        config_layout.setSpacing(10)

        interval_row = QHBoxLayout()
        interval_row.addWidget(QLabel("Sync Interval:"))
        self._interval_combo = QComboBox()
        self._interval_combo.addItem("15 minutes", 15)
        self._interval_combo.addItem("30 minutes", 30)
        self._interval_combo.addItem("1 hour", 60)
        self._interval_combo.addItem("6 hours", 360)
        self._interval_combo.addItem("Daily", 1440)
        self._interval_combo.currentIndexChanged.connect(self._on_interval)
        interval_row.addWidget(self._interval_combo)
        interval_row.addStretch()
        config_layout.addLayout(interval_row)

        self._startup_cb = QCheckBox("Sync on Startup")
        self._startup_cb.toggled.connect(lambda v: set_setting("sync_on_startup", v))
        config_layout.addWidget(self._startup_cb)

        self._live_cb = QCheckBox("Live Tracking on Startup")
        self._live_cb.toggled.connect(lambda v: set_setting("live_tracking_on_startup", v))
        config_layout.addWidget(self._live_cb)

        self._backup_cb = QCheckBox("Auto Backup before Sync")
        self._backup_cb.toggled.connect(lambda v: set_setting("auto_backup_before_sync", v))
        config_layout.addWidget(self._backup_cb)

        self._health_cb = QCheckBox("Auto Health after Sync")
        self._health_cb.toggled.connect(lambda v: set_setting("auto_health_after_sync", v))
        config_layout.addWidget(self._health_cb)

        config_group.setLayout(config_layout)
        layout.addWidget(config_group)

        actions_group = QGroupBox("Actions")
        actions_layout = QHBoxLayout()
        actions_layout.setSpacing(12)

        self._run_backup_btn = QPushButton("Run Backup Now")
        self._run_backup_btn.clicked.connect(self._run_backup)
        actions_layout.addWidget(self._run_backup_btn)

        self._run_health_btn = QPushButton("Run Health Check")
        self._run_health_btn.clicked.connect(self._run_health)
        actions_layout.addWidget(self._run_health_btn)

        actions_layout.addStretch()
        actions_group.setLayout(actions_layout)
        layout.addWidget(actions_group)

        log_label = QLabel("Output")
        log_label.setObjectName("section")
        layout.addWidget(log_label)

        self._log = make_log_text()
        self._log.setMinimumHeight(120)
        layout.addWidget(self._log)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #565f89; font-size: 12px;")
        layout.addWidget(self._status_label)

        layout.addStretch()
        apply_outer_layout(self, scroll)

    def _load_state(self):
        self._enabled_cb.setChecked(get_setting("automation_enabled", False))
        mins = get_setting("automation_interval_minutes", 30)
        idx = self._interval_combo.findData(mins)
        if idx >= 0:
            self._interval_combo.setCurrentIndex(idx)
        self._startup_cb.setChecked(get_setting("sync_on_startup", False))
        self._live_cb.setChecked(get_setting("live_tracking_on_startup", False))
        self._backup_cb.setChecked(get_setting("auto_backup_before_sync", False))
        self._health_cb.setChecked(get_setting("auto_health_after_sync", False))

    def _on_toggle(self, checked):
        set_setting("automation_enabled", checked)
        self._status_label.setText("Automation enabled" if checked else "Automation disabled")

    def _on_interval(self, idx):
        mins = self._interval_combo.currentData()
        set_setting("automation_interval_minutes", mins)
        self._status_label.setText(f"Interval set to {self._interval_combo.currentText()}")

    def _run_backup(self):
        self._status_label.setText("Running backup...")
        try:
            from modes.automation import run_auto_backup
            run_auto_backup()
            self._status_label.setText("Backup complete")
        except Exception as e:
            self._status_label.setText(f"Backup failed: {e}")

    def _run_health(self):
        self._status_label.setText("Running Library Health...")
        def run():
            from modes.tools.health import library_health_text
            result = library_health_text()
            self._health_result.emit(result)
        threading.Thread(target=run, daemon=True).start()

    def _finish_health(self, text):
        self._log.setText(text)
        self._status_label.setText("Library Health complete")
