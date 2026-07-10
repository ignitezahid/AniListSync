import threading

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QGroupBox, QGridLayout, QFrame, QMessageBox,
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal

from gui.widgets import scroll_area_widget, apply_outer_layout, make_log_text, LogOpsMixin, threaded_op, _main_thread


class ToolsWidget(QWidget, LogOpsMixin):
    _health_result = pyqtSignal(object)

    def __init__(self):
        super().__init__()
        self._build_ui()
        self._health_result.connect(self._finish_health)

    def _build_ui(self):
        scroll, layout = scroll_area_widget()

        heading = QLabel("Tools")
        heading.setObjectName("heading")
        sub = QLabel("Export, import, backup, restore, and manage your data.")
        sub.setObjectName("subheading")
        layout.addWidget(heading)
        layout.addWidget(sub)

        export_group = QGroupBox("Export")
        export_grid = QGridLayout()
        export_grid.setSpacing(6)
        export_grid.addWidget(self._btn("Export AniList", lambda: self._run_export("anilist")), 0, 0)
        export_grid.addWidget(self._btn("Export MAL", lambda: self._run_export("mal")), 0, 1)
        export_grid.addWidget(self._btn("Export Telegram", lambda: self._run_export("telegram")), 0, 2)
        export_grid.addWidget(self._btn("Export Missing", lambda: self._run_export("missing")), 1, 0)
        export_grid.addWidget(self._btn("Export Aliases", lambda: self._run_export("aliases")), 1, 1)
        export_grid.addWidget(self._btn("Export Search Cache", lambda: self._run_export("cache")), 1, 2)
        export_grid.addWidget(self._btn("Export Retry Queue", lambda: self._run_export("retry")), 2, 0)
        export_group.setLayout(export_grid)
        layout.addWidget(export_group)

        import_group = QGroupBox("Import")
        import_grid = QGridLayout()
        import_grid.setSpacing(6)
        import_grid.addWidget(self._btn("Import Aliases", lambda: self._run_import("aliases")), 0, 0)
        import_grid.addWidget(self._btn("Import Retry Queue", lambda: self._run_import("retry_queue")), 0, 1)
        import_grid.addWidget(self._btn("Import Search Cache", lambda: self._run_import("search_cache")), 0, 2)
        import_grid.addWidget(self._btn("Import Settings", lambda: self._run_import("settings")), 1, 0)
        import_grid.addWidget(self._btn("Import Telegram TXT", lambda: self._run_import("telegram_txt")), 1, 1)
        import_grid.addWidget(self._btn("Import Custom File", lambda: self._run_import("custom")), 1, 2)
        import_group.setLayout(import_grid)
        layout.addWidget(import_group)

        mgmt_group = QGroupBox("Maintenance")
        mgmt_grid = QGridLayout()
        mgmt_grid.setSpacing(6)
        mgmt_grid.addWidget(self._btn("Backup All Data", self._run_backup), 0, 0)
        mgmt_grid.addWidget(self._btn("Restore from Backup", self._run_restore), 0, 1)
        mgmt_grid.addWidget(self._btn("Library Health", self._run_health), 1, 0)
        mgmt_grid.addWidget(self._btn("Alias Manager", self._run_alias), 1, 1)
        mgmt_grid.addWidget(self._btn("Search Cache Manager", self._run_cache_mgr), 2, 0)
        mgmt_grid.addWidget(self._btn("Retry Queue Manager", self._run_retry_mgr), 2, 1)
        mgmt_group.setLayout(mgmt_grid)
        layout.addWidget(mgmt_group)

        log_label = QLabel("Output")
        log_label.setObjectName("section")
        layout.addWidget(log_label)

        self._log = make_log_text()
        self._log.setMinimumHeight(150)
        layout.addWidget(self._log)

        self._fix_container = QHBoxLayout()
        layout.addLayout(self._fix_container)

        self._status_label = QLabel("")
        self._status_label.setStyleSheet("color: #565f89; font-size: 12px;")
        layout.addWidget(self._status_label)

        layout.addStretch()
        apply_outer_layout(self, scroll)

    def _btn(self, text, callback):
        btn = QPushButton(text)
        btn.clicked.connect(callback)
        btn.setMinimumHeight(34)
        return btn

    # _log_op inherited from LogOpsMixin

    def _run_export(self, which):
        from modes.tools.export_tools import (
            export_anilist_library, export_mal_library,
            export_missing_anime, export_retry_queue,
            export_aliases, export_search_cache,
        )
        import asyncio
        async def _tg():
            from modes.tools.export_tools import export_telegram_titles
            await export_telegram_titles()
        mapping = {
            "anilist": export_anilist_library,
            "mal": export_mal_library,
            "telegram": _tg,
            "missing": export_missing_anime,
            "retry": export_retry_queue,
            "aliases": export_aliases,
            "cache": export_search_cache,
        }
        fn = mapping.get(which)
        if not fn:
            return
        # API-calling exports run in a background thread
        if which in ("anilist", "mal", "telegram"):
            threaded_op(self._log, self._status_label, f"Export {which}", fn)
        else:
            self._log_op(f"Export {which}", fn)

    def _run_import(self, which):
        from modes.tools.import_tools import (
            import_anilist, import_mal, import_telegram,
        )
        mapping = {
            "anilist": import_anilist,
            "mal": import_mal,
            "telegram": import_telegram,
        }
        fn = mapping.get(which)
        if fn:
            self._log_op(f"Import {which}", fn)

    def _run_backup(self):
        from modes.tools.backup import backup_center
        threaded_op(self._log, self._status_label, "Backup", backup_center)

    def _run_restore(self):
        from gui.dialogs import RestoreDialog
        dlg = RestoreDialog(self)
        dlg.exec()

    def _run_health(self):
        self._log.clear()
        self._status_label.setText("Running Library Health...")
        self._clear_fix_buttons()
        def run():
            from modes.tools.health import _compute_health_score
            pct, groups, issues = _compute_health_score()
            skipped_keywords = ["token", "cred", "api_id", "api_hash", "session", "telegram"]
            filtered_issues = [i for i in issues if not any(k in i.lower() for k in skipped_keywords)]
            skipped = len(issues) - len(filtered_issues)
            if skipped:
                passed_approx = round(pct * 12 / 100)
                new_total = 12 - skipped
                pct = int(passed_approx * 100 / new_total)
                pct = min(pct, 100)
                issues = filtered_issues
                for group in groups:
                    if group[0] == "Accounts":
                        new_items = []
                        for name, status in group[1]:
                            if name in ("API Credentials", "Telegram"):
                                new_items.append((name, "—  Skipped (GUI)"))
                            else:
                                new_items.append((name, status))
                        group[1].clear()
                        group[1].extend(new_items)
                        break
            lines = []
            color = "🟢" if pct >= 80 else ("🟡" if pct >= 50 else "🔴")
            lines.append(f"Library Health — {pct}% {color}\n")
            for group_name, items in groups:
                lines.append(f"  {group_name}\n  " + "─" * 40)
                for name, status in items:
                    lines.append(f"\n    {status}  {name}")
                lines.append("\n")
            if issues:
                lines.append("\n  Suggestions\n  " + "─" * 40)
                for issue in issues:
                    lines.append(f"\n    {issue}")
                lines.append("\n")
            text = "".join(lines)
            self._health_result.emit((text, issues))
        threading.Thread(target=run, daemon=True).start()

    def _clear_fix_buttons(self):
        while self._fix_container.count():
            item = self._fix_container.takeAt(0)
            w = item.widget()
            if w:
                w.hide()
                w.setParent(None)
                w.deleteLater()

    def _finish_health(self, data):
        text, issues = data
        self._log.setText(text)
        self._status_label.setText("Library Health complete")
        self._clear_fix_buttons()
        if issues:
            for issue in issues:
                action = self._issue_action(issue)
                if action:
                    btn = QPushButton(action["label"])
                    btn.setMinimumHeight(30)
                    if action.get("tab"):
                        btn.clicked.connect(lambda checked, a=action: self._switch_tab(a["tab"]))
                    elif action.get("fn"):
                        btn.clicked.connect(lambda checked, a=action: self._run_fix(a))
                    elif action.get("info"):
                        btn.clicked.connect(lambda checked, a=action: QMessageBox.information(self, "Manual Fix", a["info"]))
                    self._fix_container.addWidget(btn)

    def _issue_action(self, issue):
        issue_lower = issue.lower()
        if "duplicate" in issue_lower or "broken" in issue_lower:
            return {"label": "Fix Duplicates", "fn": "_open_alias_manager"}
        if "mal id" in issue_lower:
            return {"label": "Repair MAL IDs", "tab": "repair"}
        if "retry" in issue_lower:
            return {"label": "Process Retry Queue", "fn": "_open_retry_queue"}
        if "cache" in issue_lower:
            return {"label": "Manage Cache", "fn": "_open_search_cache"}
        if "backup" in issue_lower:
            return {"label": "Clean Backups", "fn": "_clean_backups"}
        if "resume" in issue_lower:
            return {"label": "Reset Resume", "fn": "_reset_resume"}
        if "missing setting" in issue_lower or "wrong type" in issue_lower or "unknown setting" in issue_lower:
            return {"label": "Fix Settings", "fn": "_fix_settings"}
        if "export" in issue_lower or "corrupted" in issue_lower:
            return {"label": "Open Export Folder", "fn": "_open_exports"}
        if "token" in issue_lower or "cred" in issue_lower:
            if "anilist" in issue_lower:
                if "missing" in issue_lower or "placeholder" in issue_lower:
                    return {"label": "Set AniList Token", "info": "Open config.py and set ANILIST_TOKEN to your AniList access token"}
                return {"label": "Refresh AniList Token", "info": "Your AniList token has expired. Generate a new one and update config.py"}
            if "mal" in issue_lower:
                if "missing" in issue_lower:
                    return {"label": "Set MAL Tokens", "info": "MAL tokens are missing. Run the app without --gui and authenticate with MyAnimeList"}
                return {"label": "Refresh MAL Token", "info": "Your MAL token has expired. Re-authenticate by running the app without --gui"}
            return {"label": "Fix Credentials", "info": "Check config.py and mal_tokens.json for valid API credentials"}
        if "telegram" in issue_lower:
            if "api_id" in issue_lower:
                return {"label": "Set API_ID", "info": "Open config.py and set API_ID to your Telegram API ID from https://my.telegram.org/apps"}
            if "api_hash" in issue_lower:
                return {"label": "Set API_HASH", "info": "Open config.py and set API_HASH to your Telegram API hash from https://my.telegram.org/apps"}
            if "session" in issue_lower:
                return {"label": "Connect Telegram", "tab": "dashboard"}
            return {"label": "Fix Telegram", "info": "Check config.py for API_ID/API_HASH, then connect on Dashboard"} 
        if "syn" in issue_lower and "library" in issue_lower:
            return {"label": "Sync Library", "info": "Go to the Sync tab and run a full sync"}
        return None

    def _switch_tab(self, tab_name):
        parent = self.parent()
        while parent and not hasattr(parent, 'switch_tab'):
            parent = parent.parent()
        if parent and hasattr(parent, 'switch_tab'):
            parent.switch_tab(tab_name)

    def _run_fix(self, action):
        fn_name = action["fn"]
        if fn_name == "_clean_backups":
            from modes.tools.backup import _clean_old_backups
            self._run_fix_threaded("Clean Backups", _clean_old_backups)
        elif fn_name == "_reset_resume":
            from utils.file_utils import save_json
            from utils.constants import RESUME_FILE
            save_json(RESUME_FILE, {"last_message_id": 0})
            self._log.append("\n[Reset] Resume file reset to last_message_id: 0.")
        elif fn_name == "_fix_settings":
            from utils.file_utils import load_json, save_json
            from utils.constants import SETTINGS_FILE
            from settings import DEFAULT_SETTINGS
            fixed = dict(load_json(SETTINGS_FILE, {}))
            for k, v in DEFAULT_SETTINGS.items():
                fixed.setdefault(k, v)
            fixed = {k: v for k, v in fixed.items() if k in DEFAULT_SETTINGS}
            for k, v in DEFAULT_SETTINGS.items():
                if k in fixed and fixed[k] is not None and not isinstance(fixed[k], type(v)):
                    fixed[k] = v
            save_json(SETTINGS_FILE, fixed)
            self._log.append("\n[Fix] Configuration repaired.")
        elif fn_name == "_open_exports":
            import os
            from utils.constants import EXPORT_DIR
            os.startfile(EXPORT_DIR)
        elif fn_name == "_open_alias_manager":
            self._run_alias()
        elif fn_name == "_open_retry_queue":
            self._run_retry_mgr()
        elif fn_name == "_open_search_cache":
            self._run_cache_mgr()

    def _run_fix_threaded(self, label, fn):
        self._log.append(f"\nRunning {label}...")
        def run():
            import io
            from contextlib import redirect_stdout, redirect_stderr
            buf = io.StringIO()
            try:
                with redirect_stdout(buf), redirect_stderr(buf):
                    fn()
                text = buf.getvalue()
                _main_thread.call.emit(lambda: self._log.append(text if text else f"\n{label} complete."))
            except Exception as e:
                _main_thread.call.emit(lambda: self._log.append(f"\n{label} failed: {e}"))
        threading.Thread(target=run, daemon=True).start()

    def _run_alias(self):
        from gui.dialogs import AliasManagerDialog
        dlg = AliasManagerDialog(self)
        dlg.exec()

    def _run_cache_mgr(self):
        from gui.dialogs import SearchCacheDialog
        dlg = SearchCacheDialog(self)
        dlg.exec()

    def _run_retry_mgr(self):
        from gui.dialogs import RetryQueueDialog
        dlg = RetryQueueDialog(self)
        dlg.exec()
