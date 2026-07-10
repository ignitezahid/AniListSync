from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QCheckBox, QSpinBox, QLineEdit, QGroupBox, QGridLayout,
    QMessageBox, QFrame, QInputDialog, QComboBox, QApplication,
)
from PyQt6.QtCore import Qt

from gui.theme import THEME_ACCENTS, THEME_PALETTES, apply_dark_theme, refresh_inline_styles
from gui.widgets import scroll_area_widget, apply_outer_layout
from settings import SETTINGS, set_setting, get_setting
from core.plugin_loader import plugin_manager


class SettingsWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._checkboxes: dict[str, QCheckBox] = {}
        self._spinners: dict[str, QSpinBox] = {}
        self._texts: dict[str, QLineEdit] = {}
        self._build_ui()

    def _build_ui(self):
        scroll, layout = scroll_area_widget()

        heading = QLabel("Settings")
        heading.setObjectName("heading")
        sub = QLabel("Configure AniListSync behavior.")
        sub.setObjectName("subheading")
        layout.addWidget(heading)
        layout.addWidget(sub)

        conn_group = QGroupBox("Connections")
        conn_layout = QVBoxLayout()
        conn_layout.setSpacing(8)

        mal_status = QLabel("")
        try:
            from mal import load_tokens
            tk = load_tokens()
            mal_ok = bool(tk and tk.get("access_token"))
        except Exception:
            mal_ok = False

        mal_row = QHBoxLayout()
        mal_lbl = QLabel(f"MAL: {'Connected' if mal_ok else 'Disconnected'}")
        mal_lbl.setStyleSheet(f"color: {'#9ece6a' if mal_ok else '#f7768e'}; font-size: 13px; font-weight: 600;")
        mal_row.addWidget(mal_lbl)
        if not mal_ok:
            mal_btn = QPushButton("Connect MAL")
            mal_btn.clicked.connect(self._auth_mal)
            mal_row.addWidget(mal_btn)
        mal_row.addStretch()
        conn_layout.addLayout(mal_row)

        conn_group.setLayout(conn_layout)
        layout.addWidget(conn_group)

        theme_group = QGroupBox("Theme")
        theme_layout = QHBoxLayout()
        theme_layout.setSpacing(10)
        theme_lbl = QLabel("GUI Theme:")
        theme_lbl.setStyleSheet("color: #c0caf5; font-size: 13px;")
        theme_layout.addWidget(theme_lbl)

        self._theme_combo = QComboBox()
        theme_names = list(THEME_ACCENTS.keys())
        self._theme_combo.addItems(theme_names)
        self._theme_combo.blockSignals(True)
        from core.plugin_loader import plugin_manager
        current_theme = plugin_manager._settings.get("themes", {}).get("active", "Default")
        if current_theme in theme_names:
            self._theme_combo.setCurrentText(current_theme)
        elif "Default" in theme_names:
            self._theme_combo.setCurrentText("Default")
        self._theme_combo.blockSignals(False)
        self._theme_combo.setMinimumWidth(160)
        self._theme_combo.currentTextChanged.connect(self._on_theme_changed)
        theme_layout.addWidget(self._theme_combo)
        theme_layout.addStretch()
        theme_group.setLayout(theme_layout)
        layout.addWidget(theme_group)

        sync_group = QGroupBox("Sync")
        sync_grid = QGridLayout()
        sync_grid.setSpacing(8)
        row = 0

        self._checkboxes["enable_anilist"] = self._add_checkbox("Sync to AniList", "enable_anilist", sync_grid, row); row += 1
        self._checkboxes["enable_mal"] = self._add_checkbox("Sync to MyAnimeList", "enable_mal", sync_grid, row); row += 1
        self._checkboxes["interactive_sync"] = self._add_checkbox("Interactive sync", "interactive_sync", sync_grid, row); row += 1
        self._checkboxes["resume_import"] = self._add_checkbox("Resume import", "resume_import", sync_grid, row); row += 1
        self._checkboxes["retry_failed"] = self._add_checkbox("Retry failed entries", "retry_failed", sync_grid, row); row += 1
        self._checkboxes["auto_learn_aliases"] = self._add_checkbox("Auto-learn aliases", "auto_learn_aliases", sync_grid, row); row += 1
        self._checkboxes["franchise_sync"] = self._add_checkbox("Franchise sync", "franchise_sync", sync_grid, row); row += 1
        self._checkboxes["fuzzy_matching"] = self._add_checkbox("Fuzzy matching", "fuzzy_matching", sync_grid, row); row += 1
        self._checkboxes["use_search_cache"] = self._add_checkbox("Use search cache", "use_search_cache", sync_grid, row); row += 1
        self._checkboxes["confirm_before_sync"] = self._add_checkbox("Confirm before sync", "confirm_before_sync", sync_grid, row); row += 1

        self._spinners["search_threshold"] = self._add_spinner("Search threshold (%)", "search_threshold", 0, 100, sync_grid, row); row += 1
        self._spinners["search_results"] = self._add_spinner("Search results", "search_results", 1, 200, sync_grid, row); row += 1
        self._spinners["max_retries"] = self._add_spinner("Max retries", "max_retries", 0, 100, sync_grid, row); row += 1
        self._spinners["stop_after"] = self._add_spinner("Stop after (new)", "stop_after", 0, 999999, sync_grid, row); row += 1
        self._spinners["stop_after_existing"] = self._add_spinner("Stop after (existing)", "stop_after_existing", 0, 999999, sync_grid, row); row += 1

        sync_group.setLayout(sync_grid)
        layout.addWidget(sync_group)

        tg_group = QGroupBox("Telegram")
        tg_grid = QGridLayout()
        tg_grid.setSpacing(8)
        row = 0

        current_sources = get_setting("telegram_sources", ["me"])
        self._texts["telegram_sources"] = self._add_text("Chat sources (comma-separated)", current_sources, tg_grid, row); row += 1

        tg_group.setLayout(tg_grid)
        layout.addWidget(tg_group)

        auto_group = QGroupBox("Automation")
        auto_grid = QGridLayout()
        auto_grid.setSpacing(8)
        row = 0

        self._checkboxes["automation_enabled"] = self._add_checkbox("Enable automation", "automation_enabled", auto_grid, row); row += 1
        self._spinners["automation_interval_minutes"] = self._add_spinner("Interval (minutes)", "automation_interval_minutes", 1, 1440, auto_grid, row); row += 1
        self._checkboxes["sync_on_startup"] = self._add_checkbox("Sync on startup", "sync_on_startup", auto_grid, row); row += 1
        self._checkboxes["live_tracking_on_startup"] = self._add_checkbox("Live tracking on startup", "live_tracking_on_startup", auto_grid, row); row += 1
        self._checkboxes["auto_backup_before_sync"] = self._add_checkbox("Backup before sync", "auto_backup_before_sync", auto_grid, row); row += 1
        self._checkboxes["auto_health_after_sync"] = self._add_checkbox("Health check after sync", "auto_health_after_sync", auto_grid, row); row += 1

        auto_group.setLayout(auto_grid)
        layout.addWidget(auto_group)

        other_group = QGroupBox("Defaults")
        other_grid = QGridLayout()
        other_grid.setSpacing(8)
        row = 0

        self._texts["default_status"] = self._add_text("Default AniList status", get_setting("default_status", "COMPLETED"), other_grid, row); row += 1
        self._texts["mal_default_status"] = self._add_text("Default MAL status", get_setting("mal_default_status", "completed"), other_grid, row); row += 1
        self._checkboxes["auto_backup"] = self._add_checkbox("Auto backup", "auto_backup", other_grid, row); row += 1
        self._checkboxes["debug"] = self._add_checkbox("Debug mode", "debug", other_grid, row); row += 1

        other_group.setLayout(other_grid)
        layout.addWidget(other_group)

        notif_group = QGroupBox("Notifications")
        notif_layout = QVBoxLayout()
        notif_layout.setSpacing(6)

        self._notify_checkboxes: dict[str, QCheckBox] = {}
        notif_items = [
            ("notify_desktop", "Desktop notifications"),
            ("notify_sync", "Sync complete"),
            ("notify_backup", "Backup created"),
            ("notify_health", "Health scan"),
            ("notify_anime_added", "Anime added"),
        ]
        notify_plugin = self._get_notify_plugin()
        for key, label in notif_items:
            cb = QCheckBox(label)
            if notify_plugin:
                cb.setChecked(notify_plugin.settings.get(key, True))
            else:
                cb.setChecked(True)
                cb.setEnabled(False)
            notif_layout.addWidget(cb)
            self._notify_checkboxes[key] = cb

        notif_status = QLabel("" if notify_plugin else "Notifications plugin not loaded")
        notif_status.setStyleSheet("color: #565f89; font-size: 12px;")
        notif_layout.addWidget(notif_status)

        notif_group.setLayout(notif_layout)
        layout.addWidget(notif_group)

        btn_layout = QHBoxLayout()
        btn_layout.addStretch()
        save_btn = QPushButton("Save Settings")
        save_btn.setObjectName("primary")
        save_btn.clicked.connect(self._save)
        save_btn.setMinimumWidth(140)
        btn_layout.addWidget(save_btn)
        layout.addLayout(btn_layout)

        layout.addStretch()
        apply_outer_layout(self, scroll)

    def _add_checkbox(self, label: str, key: str, grid: QGridLayout, row: int) -> QCheckBox:
        cb = QCheckBox(label)
        cb.setChecked(get_setting(key, False))
        grid.addWidget(cb, row, 0, 1, 2)
        return cb

    def _add_spinner(self, label: str, key: str, min_v: int, max_v: int, grid: QGridLayout, row: int) -> QSpinBox:
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #565f89; font-size: 13px;")
        sp = QSpinBox()
        sp.setMinimum(min_v)
        sp.setMaximum(max_v)
        sp.setValue(get_setting(key, 0))
        sp.setMinimumWidth(100)
        grid.addWidget(lbl, row, 0)
        grid.addWidget(sp, row, 1, Qt.AlignmentFlag.AlignLeft)
        return sp

    def _add_text(self, label: str, value, grid: QGridLayout, row: int) -> QLineEdit:
        lbl = QLabel(label)
        lbl.setStyleSheet("color: #565f89; font-size: 13px;")
        te = QLineEdit()
        if isinstance(value, list):
            te.setText(", ".join(value))
        else:
            te.setText(str(value))
        grid.addWidget(lbl, row, 0)
        grid.addWidget(te, row, 1)
        return te

    def _on_theme_changed(self, theme_name: str):
        """Apply a GUI theme immediately when the user picks one from the combo."""
        app = QApplication.instance()
        if app:
            apply_dark_theme(app, theme_name)
            refresh_inline_styles(app)
            # Persist choice so it survives restart. The themes plugin reads this.
            from core.plugin_loader import plugin_manager
            p = THEME_PALETTES.get(theme_name, THEME_PALETTES["Default"])
            plugin_manager._settings.setdefault("themes", {})
            plugin_manager._settings["themes"]["active"] = theme_name
            plugin_manager._settings["themes"]["bg"] = p["bg"]
            # Find the themes plugin instance and save its settings to disk.
            for pid, manifest, loaded in plugin_manager.get_plugins():
                if pid == "themes":
                    inst = plugin_manager._plugins.get(pid)
                    if inst and hasattr(inst, "settings"):
                        inst.settings["active"] = theme_name
                        inst.settings["bg"] = p["bg"]
                        inst.save_settings()
                    break

    def _get_notify_plugin(self):
        """Return the notifications plugin instance, or None."""
        for pid, manifest, loaded in plugin_manager.get_plugins():
            if pid == "notifications":
                return plugin_manager._plugins.get(pid)
        return None

    def _save(self):
        for key, cb in self._checkboxes.items():
            set_setting(key, cb.isChecked())

        for key, sp in self._spinners.items():
            set_setting(key, sp.value())

        for key, te in self._texts.items():
            if key == "telegram_sources":
                sources = [s.strip() for s in te.text().split(",") if s.strip()]
                set_setting(key, sources)
            else:
                set_setting(key, te.text())

        # Save notification settings to the plugin instance
        notify_plugin = self._get_notify_plugin()
        if notify_plugin:
            for key, cb in self._notify_checkboxes.items():
                notify_plugin.settings[key] = cb.isChecked()
            notify_plugin.save_settings()

        QMessageBox.information(self, "Settings", "Settings saved successfully.")

    def _auth_mal(self):
        import webbrowser
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
        except Exception as e:
            QMessageBox.critical(self, "Error", f"MAL authentication failed: {e}")
