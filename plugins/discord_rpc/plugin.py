import asyncio
import json
import os
import subprocess
import threading
import time
import warnings
from pathlib import Path

# pypresence creates internal async tasks that can trigger
# "coroutine was never awaited" when used from background threads.
warnings.filterwarnings("ignore", message="coroutine.*was never awaited")

STATE_FILE = Path("state.json")

try:
    from pypresence import Presence
    from pypresence.exceptions import DiscordNotFound
    from pypresence.payloads import Payload
    HAS_PYPRESENCE = True
except ImportError:
    HAS_PYPRESENCE = False
    Presence = None
    DiscordNotFound = Exception
    Payload = None

CLIENT_ID_DEFAULT = "1523636189037334630"


class Plugin:
    def __init__(self):
        self._rpc = None
        self._connected = False
        self._state = "idle"
        self._sync_count = 0
        self._health_pct = 0
        self._keepalive: threading.Timer | None = None
        self._retry_timer: threading.Timer | None = None
        self._last_state = ""
        self._last_details = ""
        self._last_large_text = "AniListSync"
        self._start_time: int | None = None
        self._retry_ts: float = 0

    def _connect(self):
        if not HAS_PYPRESENCE:
            self.log("pypresence not installed — run: pip install pypresence", "WARN")
            return
        if self._connected:
            return
        self._disconnect()
        cid = self.settings.get("client_id", CLIENT_ID_DEFAULT)
        try:
            self._rpc = Presence(cid, response_timeout=2, connection_timeout=2)
            self._rpc.connect()
            self._connected = True
            self._start_keepalive()
            self._stop_retry_timer()
            self._update("Idle", "AniListSync", "AniListSync")
            self.log("Connected to Discord RPC")
        except DiscordNotFound:
            self.log("Discord not running — launch Discord first", "WARN")
            self._rpc = None
            self._start_retry_timer()
        except Exception as e:
            self.log(f"Failed to connect: {e}", "ERROR")
            self._rpc = None
            self._start_retry_timer()

    def _disconnect(self):
        self._stop_keepalive()
        self._stop_retry_timer()
        if self._rpc and self._connected:
            try:
                self._rpc.close()
            except Exception:
                pass
            self._connected = False
            self.log("Disconnected from Discord RPC")


    def _update(self, state: str, details: str = None, large_text: str = "AniListSync"):
        if not self._connected or not self._rpc:
            if HAS_PYPRESENCE and time.time() - self._retry_ts > 10:
                self._retry_ts = time.time()
                self._connect()
            if not self._connected or not self._rpc:
                return
        if self._start_time is None:
            self._start_time = int(time.time())
        self._state = state
        self._last_state = state
        self._last_details = details or ""
        self._last_large_text = large_text
        kwargs = dict(
            state=state,
            details=details,
            large_text=large_text,
            start=self._start_time,
        )
        try:
            self._rpc.update(**kwargs)
        except RuntimeError:
            self._send_async(**kwargs)
        except Exception as e:
            self.log(f"Update error: {e}", "WARN")

    def _send_async(self, **kwargs):
        payload_data = Payload.set_activity(pid=os.getpid(), activity=True, **kwargs)
        async def _do():
            try:
                self._rpc.send_data(1, payload_data)
                await asyncio.wait_for(self._rpc.read_output(), timeout=2)
            except Exception:
                pass
        try:
            fut = asyncio.run_coroutine_threadsafe(_do(), self._rpc.loop)
            fut.add_done_callback(lambda _: None)
        except Exception:
            pass

    def _start_keepalive(self):
        self._stop_keepalive()
        def _keep():
            if not self._connected or not self._rpc:
                return
            kwargs = dict(
                state=self._last_state,
                details=self._last_details or None,
                large_text=self._last_large_text,
                start=self._start_time,
            )
            try:
                self._rpc.update(**kwargs)
            except RuntimeError:
                self._send_async(**kwargs)
            except Exception:
                self._disconnect()
                return
            self._keepalive = threading.Timer(20, _keep)
            self._keepalive.daemon = True
            self._keepalive.start()
        self._keepalive = threading.Timer(20, _keep)
        self._keepalive.daemon = True
        self._keepalive.start()

    def _stop_keepalive(self):
        if self._keepalive:
            self._keepalive.cancel()
            self._keepalive = None

    def _start_retry_timer(self):
        self._stop_retry_timer()
        self._retry_timer = threading.Timer(5, self._retry_connect)
        self._retry_timer.daemon = True
        self._retry_timer.start()

    def _stop_retry_timer(self):
        if self._retry_timer:
            self._retry_timer.cancel()
            self._retry_timer = None

    def _discord_running(self) -> bool:
        try:
            result = subprocess.run(
                ["tasklist", "/FI", "IMAGENAME eq Discord.exe", "/NH"],
                capture_output=True, text=True, timeout=3,
                creationflags=subprocess.CREATE_NO_WINDOW,
            )
            return "Discord.exe" in result.stdout
        except Exception:
            return False

    def _retry_connect(self):
        if self._connected or not HAS_PYPRESENCE:
            return
        if self._discord_running():
            self._connect()
        if not self._connected:
            self._start_retry_timer()

    def _library_count(self) -> str:
        try:
            with open(STATE_FILE, encoding="utf-8") as f:
                data = json.load(f)
            processed = data.get("processed", 0)
            return f"{processed} Anime" if processed else "Unknown"
        except Exception:
            return "Unknown"

    def on_load(self):
        self.log("Discord RPC loaded")

    def on_startup(self):
        self._connect()
        if self._connected:
            self._update("Idle", "AniListSync", "AniListSync")

    def on_shutdown(self):
        self._disconnect()

    def on_idle(self):
        if self._connected:
            self._update("Idle", "AniListSync", "AniListSync")

    def on_sync_start(self):
        self._sync_count = 0
        count = self._library_count()
        self._update("Synchronizing Library", count, "AniListSync")

    def on_anime_added(self, anime):
        self._sync_count += 1
        self._update(
            "Synchronizing Library",
            f"{self._sync_count} titles synced",
            "AniListSync",
        )

    def on_sync_finish(self):
        self._update("Sync Complete", f"{self._sync_count} titles", "AniListSync")

    def on_automation(self):
        self._update("Running Automation", "Scheduled tasks", "AniListSync")

    def on_manual_search(self):
        self._update("Manual Search", "Searching titles", "AniListSync")

    def on_library_search(self):
        self._update("Library Search", "Browsing library", "AniListSync")

    def on_statistics(self):
        self._update("Viewing Statistics", "Library analytics", "AniListSync")

    def on_collections(self):
        self._update("Managing Collections", "Organizing library", "AniListSync")

    def on_compare(self):
        self._update("Comparing", "Library vs Telegram", "AniListSync")

    def on_repair(self):
        self._update("Running Repair", "Fixing library issues", "AniListSync")

    def on_bulk_operations(self):
        self._update("Bulk Operations", "Batch library actions", "AniListSync")

    def on_plugin_menu(self):
        self._update("Plugin Manager", "Managing plugins", "AniListSync")

    def on_tools(self):
        self._update("Tools", "Utility functions", "AniListSync")

    def on_health_scan(self):
        count = self._library_count()
        self._update("Library Health", count, "AniListSync")

    def on_backup(self, path):
        if self._state == "Synchronizing Library":
            return
        self._update("Creating Backup", path, "AniListSync")

    def get_commands(self):
        return [
            ("Reconnect RPC", self._reconnect_rpc),
            ("Set Client ID", self._set_client_id),
        ]

    def _reconnect_rpc(self):
        self._disconnect()
        self._connect()
        print("  Reconnected to Discord RPC.")

    def _set_client_id(self):
        current = self.settings.get("client_id", CLIENT_ID_DEFAULT)
        try:
            val = input(f"  Enter Discord Application ID [{current}]: ").strip()
            if val:
                self.settings["client_id"] = val
                self.save_settings()
                self._disconnect()
                self._connect()
                print("  Client ID updated.")
        except (EOFError, KeyboardInterrupt):
            pass
