import json
import subprocess
import urllib.request
from pathlib import Path

STATE_FILE = Path("state.json")


def _desktop_notify(title: str, body: str):
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
            timeout=5,
        )
        return
    except Exception:
        pass
    print(f"\n  [Notifications] {title}: {body}")


def _send_webhook(url: str, title: str, body: str):
    if not url:
        return
    try:
        payload = json.dumps({"content": f"**{title}**\n{body}"}).encode()
        req = urllib.request.Request(
            url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        urllib.request.urlopen(req, timeout=5)
    except Exception as e:
        print(f"  [Notifications] Webhook failed: {e}")


def _send_telegram(chat: str, title: str, body: str):
    if not chat:
        return
    try:
        from telegram_client import client
        import asyncio
        msg = f"*{title}*\n{body}"
        if client.is_connected():
            loop = client.loop
            if loop and loop.is_running():
                asyncio.run_coroutine_threadsafe(
                    client.send_message(chat, msg), loop,
                )
    except Exception as e:
        print(f"  [Notifications] Telegram push failed: {e}")


class Plugin:
    def __init__(self):
        self._added = 0
        self._failed = 0

    # --- helpers ---

    def _notify(self, title: str, body: str, event_type: str = ""):
        if self.settings.get("notify_desktop", True):
            _desktop_notify(title, body)
        webhook = self.settings.get("notify_webhook_url", "")
        if webhook:
            _send_webhook(webhook, title, body)
        tg_chat = self.settings.get("notify_telegram_chat", "")
        if tg_chat:
            _send_telegram(tg_chat, title, body)
        self.log(f"[{event_type}] {title}: {body}")

    def _anime_title(self, anime: dict) -> str:
        t = anime.get("title") or {}
        return t.get("english") or t.get("romaji") or t.get("native") or "Unknown"

    # --- lifecycle ---

    def on_load(self):
        self.log("Notifications plugin loaded")
        defaults = {
            "notify_desktop": True,
            "notify_sync": True,
            "notify_backup": True,
            "notify_health": True,
            "notify_anime_added": False,
            "notify_webhook_url": "",
            "notify_telegram_chat": "",
        }
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
        parts = []
        if added:
            parts.append(f"Added: {added}")
        if failed:
            parts.append(f"Failed: {failed}")
        body = "  ".join(parts) if parts else "Sync complete"
        self._notify("Sync Complete", body, "sync_finish")

    def on_anime_added(self, anime):
        self._added += 1
        if not self.settings.get("notify_anime_added", False):
            return
        title = self._anime_title(anime)
        self._notify("Anime Added", title, "anime_added")

    def on_backup(self, path):
        if not self.settings.get("notify_backup", True):
            return
        name = Path(path).name
        self._notify("Backup Created", name, "backup")

    def on_health_scan(self):
        if not self.settings.get("notify_health", True):
            return
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                state = json.load(f)
            pct = state.get("health_pct", 0)
            self._notify("Library Health", f"Health: {pct}%", "health")
        except Exception:
            pass

    # --- commands ---

    def get_commands(self):
        return [
            ("Toggle Notifications", self._toggle_settings),
            ("Set Webhook URL", self._set_webhook),
            ("Set Telegram Chat", self._set_telegram_chat),
            ("Test Notification", self._test_notify),
        ]

    def _toggle_settings(self):
        labels = {
            "notify_desktop": "Desktop notification",
            "notify_sync": "Sync complete",
            "notify_backup": "Backup created",
            "notify_health": "Health scan",
            "notify_anime_added": "Anime added push",
        }
        keys = list(labels.keys())
        print()
        for i, key in enumerate(keys, 1):
            val = self.settings.get(key, False)
            status = "ON" if val else "OFF"
            print(f"  {i}. {labels[key]:24s} [{status}]")
        print()
        try:
            pick = input("  Toggle which? (number, or 0 to exit): ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        if pick.isdigit():
            idx = int(pick) - 1
            if 0 <= idx < len(keys):
                key = keys[idx]
                self.settings[key] = not self.settings.get(key, False)
                self.save_settings()
                print(f"  {labels[key]}: {'ON' if self.settings[key] else 'OFF'}")

    def _set_webhook(self):
        current = self.settings.get("notify_webhook_url", "")
        try:
            val = input(f"  Discord/Generic webhook URL [{current}]: ").strip()
            if val:
                self.settings["notify_webhook_url"] = val
                self.save_settings()
                print("  Webhook URL updated.")
        except (EOFError, KeyboardInterrupt):
            pass

    def _set_telegram_chat(self):
        current = self.settings.get("notify_telegram_chat", "")
        try:
            val = input(f"  Telegram chat (username/@/ID) [{current}]: ").strip()
            if val:
                self.settings["notify_telegram_chat"] = val
                self.save_settings()
                print("  Telegram chat updated.")
        except (EOFError, KeyboardInterrupt):
            pass

    def _test_notify(self):
        self._notify("Test Notification", "If you see this, it works!", "test")
