import subprocess
import json
from pathlib import Path

STATE_FILE = Path("state.json")


def _notify(title: str, body: str):
    try:
        import plyer
        plyer.notification.notify(title=title, message=body, app_name="AniListSync", timeout=5)
        return
    except ImportError:
        pass
    try:
        subprocess.run(
            [
                "powershell", "-Command",
                f"""New-BurntToastNotification -AppLogo "" -Text '{title}', '{body}'""",
            ],
            capture_output=True,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return
    except Exception:
        pass
    print(f"\n  [Notifications] {title}: {body}")


class Plugin:
    def __init__(self):
        self._added = 0
        self._failed = 0

    def on_load(self):
        self.log("Notifications plugin loaded")
        defaults = {"notify_sync": True, "notify_backup": True, "notify_health": True}
        changed = False
        for k, v in defaults.items():
            if k not in self.settings:
                self.settings[k] = v
                changed = True
        if changed:
            self.save_settings()

    def on_sync_start(self):
        self._added = 0
        self._failed = 0

    def on_sync_finish(self):
        if not self.settings.get("notify_sync", True):
            return
        added = self._added
        failed = self._failed
        body_parts = []
        if added:
            body_parts.append(f"Added: {added}")
        if failed:
            body_parts.append(f"Failed: {failed}")
        body = "  ".join(body_parts) if body_parts else "Sync complete"
        _notify("Sync Complete", body)
        self.log(f"Sync finished: {body}")

    def on_anime_added(self, anime):
        self._added += 1

    def on_backup(self, path):
        if not self.settings.get("notify_backup", True):
            return
        name = Path(path).name
        _notify("Backup Created", name)
        self.log(f"Backup: {name}")

    def on_health_scan(self):
        if not self.settings.get("notify_health", True):
            return
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                state = json.load(f)
            pct = state.get("health_pct", 0)
            _notify("Library Health", f"Health: {pct}%")
        except Exception:
            pass

    def get_commands(self):
        return [
            ("Toggle Notifications", self._toggle_settings),
        ]

    def _toggle_settings(self):
        labels = {
            "notify_sync": "Sync complete",
            "notify_backup": "Backup created",
            "notify_health": "Health scan",
        }
        keys = list(labels.keys())
        print()
        for i, key in enumerate(keys, 1):
            val = self.settings.get(key, True)
            status = "ON" if val else "OFF"
            print(f"  {i}. {labels[key]:20s} [{status}]")
        print()
        try:
            pick = input("  Toggle which? (number, or 0 to exit): ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        if pick.isdigit():
            idx = int(pick) - 1
            if 0 <= idx < len(keys):
                key = keys[idx]
                self.settings[key] = not self.settings.get(key, True)
                self.save_settings()
                print(f"  {labels[key]}: {'ON' if self.settings[key] else 'OFF'}")
