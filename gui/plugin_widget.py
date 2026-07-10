import builtins

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QTableWidget, QTableWidgetItem, QHeaderView, QAbstractItemView,
    QMessageBox, QDialog, QTextEdit, QLineEdit, QApplication, QFrame,
)
from PyQt6.QtCore import Qt, QTimer

from core.plugin_loader import plugin_manager


class PluginWidget(QWidget):
    def __init__(self):
        super().__init__()
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(28, 20, 28, 20)
        layout.setSpacing(16)

        heading = QLabel("Plugins")
        heading.setObjectName("heading")
        sub = QLabel("Manage AniListSync plugins. Enable, disable, and configure extensions.")
        sub.setObjectName("subheading")
        layout.addWidget(heading)
        layout.addWidget(sub)

        self._table = QTableWidget()
        self._table.setColumnCount(5)
        self._table.setHorizontalHeaderLabels(["Name", "Version", "Status", "Commands", "Error"])
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        self._table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self._table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self._table.verticalHeader().setVisible(False)
        self._table.setAlternatingRowColors(False)

        layout.addWidget(self._table)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(10)

        self._toggle_btn = QPushButton("Toggle Enable/Disable")
        self._toggle_btn.clicked.connect(self._toggle_plugin)
        btn_layout.addWidget(self._toggle_btn)

        self._reload_btn = QPushButton("Reload")
        self._reload_btn.clicked.connect(self._reload_plugin)
        btn_layout.addWidget(self._reload_btn)

        self._refresh_btn = QPushButton("Refresh List")
        self._refresh_btn.clicked.connect(self._populate)
        btn_layout.addWidget(self._refresh_btn)

        self._configure_btn = QPushButton("Configure")
        self._configure_btn.setObjectName("primary")
        self._configure_btn.clicked.connect(self._configure_plugin)
        btn_layout.addWidget(self._configure_btn)

        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        layout.addStretch()
        self.setLayout(layout)

    def showEvent(self, event):
        super().showEvent(event)
        self._populate()

    def _plugin_emoji(self, pid: str) -> str:
        icons = {
            "cloud_backup": "☁️",
            "discord_rpc": "🎮",
            "notifications": "🔔",
            "themes": "🎨",
        }
        return icons.get(pid, "🔌")

    def _populate(self):
        plugins = plugin_manager.get_plugins()
        errors = plugin_manager.get_errors()
        self._table.setRowCount(len(plugins))

        for row, (pid, manifest, loaded) in enumerate(plugins):
            enabled = plugin_manager.is_enabled(pid)

            display_name = f"{self._plugin_emoji(pid)}  {manifest.get('name', pid)}  ({pid})"
            self._table.setItem(row, 0, QTableWidgetItem(display_name))
            self._table.setItem(row, 1, QTableWidgetItem(manifest.get("version", "-")))

            if not enabled:
                status = "Disabled"
            elif loaded:
                status = "Active"
            elif pid in errors:
                status = "Error"
            else:
                status = "Inactive"
            status_item = QTableWidgetItem(status)
            if status == "Active":
                status_item.setForeground(Qt.GlobalColor.green)
            elif status == "Error":
                status_item.setForeground(Qt.GlobalColor.red)
            else:
                status_item.setForeground(Qt.GlobalColor.gray)
            self._table.setItem(row, 2, status_item)

            cmds = plugin_manager.get_commands(pid)
            self._table.setItem(row, 3, QTableWidgetItem(str(len(cmds)) if cmds else "-"))

            err = errors.get(pid)
            self._table.setItem(row, 4, QTableWidgetItem(err.message if err else ""))

            self._table.setRowHeight(row, 32)

    def _toggle_plugin(self):
        row = self._table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Plugins", "Select a plugin first.")
            return
        text = self._table.item(row, 0).text()
        pid = text.split("(")[-1].split(")")[0]

        if plugin_manager.is_enabled(pid):
            plugin_manager.disable(pid)
        else:
            plugin_manager.enable(pid)

        self._populate()

    def _reload_plugin(self):
        row = self._table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Plugins", "Select a plugin first.")
            return
        text = self._table.item(row, 0).text()
        pid = text.split("(")[-1].split(")")[0]
        plugin_manager.reload(pid)
        self._populate()

    def _configure_plugin(self):
        row = self._table.currentRow()
        if row < 0:
            QMessageBox.information(self, "Plugins", "Select a plugin first.")
            return
        text = self._table.item(row, 0).text()
        pid = text.split("(")[-1].split(")")[0]
        manifest = None
        for p, m, _ in plugin_manager.get_plugins():
            if p == pid:
                manifest = m
                break

        settings = plugin_manager._settings.get(pid, {})
        cmds = plugin_manager.get_commands(pid)

        dlg = QDialog(self)
        dlg.setWindowTitle(f"Configure: {manifest.get('name', pid)}")
        dlg.setMinimumWidth(500)
        dlg.setMinimumHeight(400)
        vl = QVBoxLayout(dlg)

        info = QLabel(f"{manifest.get('name', pid)} v{manifest.get('version', '?')}")
        info.setStyleSheet("font-size: 15px; font-weight: 700; color: #7aa2f7;")
        vl.addWidget(info)

        desc = QLabel(manifest.get("description", ""))
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #565f89; font-size: 12px;")
        vl.addWidget(desc)

        if settings:
            vl.addWidget(QLabel("Settings", objectName="section"))
            for k, v in settings.items():
                row_h = QHBoxLayout()
                row_h.addWidget(QLabel(f"  {k}:"))
                val_lbl = QLabel(str(v))
                val_lbl.setStyleSheet("color: #c0caf5; font-weight: 600;")
                row_h.addWidget(val_lbl)
                row_h.addStretch()
                vl.addLayout(row_h)

        if cmds:
            vl.addWidget(QLabel("Commands", objectName="section"))
            for cmd_name, cmd_fn in cmds:
                cmd_row = QHBoxLayout()
                cmd_row.addWidget(QLabel(f"  {cmd_name}"))
                cmd_row.addStretch()
                run_btn = QPushButton("Run")
                run_btn.setMaximumWidth(60)
                run_btn.clicked.connect(lambda checked, fn=cmd_fn, n=cmd_name: self._run_plugin_cmd(dlg, fn, n))
                cmd_row.addWidget(run_btn)
                vl.addLayout(cmd_row)

        if not settings and not cmds:
            vl.addWidget(QLabel("No settings or commands available."))

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)
        vl.addWidget(close_btn)
        dlg.exec()

    def _run_plugin_cmd(self, dlg, fn, name):
        import sys

        out_dlg = QDialog(dlg)
        out_dlg.setWindowTitle(f"Command: {name}")
        out_dlg.setMinimumWidth(550)
        out_dlg.setMinimumHeight(350)
        vl = QVBoxLayout(out_dlg)
        te = QTextEdit()
        te.setReadOnly(True)
        vl.addWidget(te)

        input_queue = []
        inp_layout = QHBoxLayout()
        inp_edit = QLineEdit()
        inp_edit.setPlaceholderText("Type response here and press Enter...")
        inp_edit.setMinimumHeight(32)

        def submit():
            t = inp_edit.text()
            if t:
                input_queue.append(t)
                te.append(f">>> {t}")
                inp_edit.clear()

        inp_edit.returnPressed.connect(submit)
        inp_layout.addWidget(inp_edit)
        send_btn = QPushButton("Send")
        send_btn.setObjectName("primary")
        send_btn.clicked.connect(submit)
        inp_layout.addWidget(send_btn)
        vl.addLayout(inp_layout)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(out_dlg.accept)
        vl.addWidget(close_btn)

        old_input = builtins.input
        old_stdout = sys.stdout
        out = [""]

        class Capture:
            def write(self, s):
                out[0] += s
                te.setPlainText(out[0])
                te.verticalScrollBar().setValue(te.verticalScrollBar().maximum())
                QApplication.processEvents()
            def flush(self):
                QApplication.processEvents()

        def gui_input(prompt=""):
            Capture().write(prompt + "\n")
            inp_edit.setFocus()
            while not input_queue:
                QApplication.processEvents()
            return input_queue.pop(0)

        builtins.input = gui_input
        sys.stdout = Capture()

        def run_fn():
            try:
                Capture().write("Running...\n")
                fn()
                Capture().write("\nDone.\n")
                try:
                    from gui.theme import apply_dark_theme, refresh_inline_styles
                    app = QApplication.instance()
                    if app:
                        settings = plugin_manager._settings.get("themes", {})
                        theme_name = settings.get("active", "Default")
                        bg = settings.get("bg")
                        Capture().write(f"\nTheme: {theme_name}  bg: {bg}\n")
                        apply_dark_theme(app, theme_name)
                        refresh_inline_styles(app)
                except Exception as e:
                    Capture().write(f"\nTheme apply warning: {e}\n")
            except Exception as e:
                Capture().write(f"\nError: {e}\n")
            finally:
                sys.stdout = old_stdout
                builtins.input = old_input
            QTimer.singleShot(1500, out_dlg.accept)

        out_dlg.show()
        QTimer.singleShot(0, run_fn)
        out_dlg.exec()
