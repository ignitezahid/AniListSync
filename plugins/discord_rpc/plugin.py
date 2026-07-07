import asyncio
import json
import os
import platform
import subprocess
import threading
import time
import warnings
from pathlib import Path

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
        self._current_anime = ""
        self._keepalive: threading.Timer | None = None
        self._retry_timer: threading.Timer | None = None
        self._last_state = ""
        self._last_details = ""
        self._last_large_text = "AniListSync"
        self._start_time: int | None = None
        self._retry_ts: float = 0

    # --- helpers ---

    def _custom(self, key: str, default: str = "") -> str:
        val = self.settings.get(f"discord_{key}", "")
        return val if val else default

    def _resolve(self, auto_state: str, auto_details: str) -> tuple[str, str]:
        return (
            self._custom("state", auto_state),
            self._custom("details", auto_details),
        )

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
            state, details = self._resolve("Idle", "AniListSync")
            self._update(state, details, "AniListSync")
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
            sys = platform.system()
            if sys == "Windows":
                result = subprocess.run(
                    ["tasklist", "/FI", "IMAGENAME eq Discord.exe", "/NH"],
                    capture_output=True, text=True, timeout=3,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
                return "Discord.exe" in result.stdout
            elif sys == "Darwin":
                result = subprocess.run(
                    ["pgrep", "-x", "Discord"],
                    capture_output=True, timeout=3,
                )
                return result.returncode == 0
            else:
                result = subprocess.run(
                    ["pgrep", "-x", "discord"],
                    capture_output=True, timeout=3,
                )
                return result.returncode == 0
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

    # --- hooks ---

    def on_load(self):
        self.log("Discord RPC loaded")

    def on_startup(self):
        self._connect()
        if self._connected:
            state, details = self._resolve("Idle", "AniListSync")
            self._update(state, details, "AniListSync")

    def on_shutdown(self):
        self._disconnect()

    def on_idle(self):
        if self._connected:
            state, details = self._resolve("Idle", "AniListSync")
            self._update(state, details, "AniListSync")

    def on_sync_start(self):
        self._sync_count = 0
        self._current_anime = ""
        count = self._library_count()
        state, details = self._resolve("Synchronizing Library", count)
        self._update(state, details, "AniListSync")

    def on_anime_added(self, anime):
        self._sync_count += 1
        title = (
            (anime.get("title") or {}).get("english")
            or (anime.get("title") or {}).get("romaji")
            or ""
        )
        self._current_anime = title
        state, details = self._resolve(
            "Synchronizing Library",
            title if title else f"{self._sync_count} titles synced",
        )
        self._update(state, details, "AniListSync")

    def on_sync_finish(self):
        state, details = self._resolve("Sync Complete", f"{self._sync_count} titles")
        self._update(state, details, "AniListSync")

    def on_automation(self):
        state, details = self._resolve("Running Automation", "Scheduled tasks")
        self._update(state, details, "AniListSync")

    def on_manual_search(self):
        state, details = self._resolve("Manual Search", "Searching titles")
        self._update(state, details, "AniListSync")

    def on_library_search(self):
        state, details = self._resolve("Library Search", "Browsing library")
        self._update(state, details, "AniListSync")

    def on_statistics(self):
        state, details = self._resolve("Viewing Statistics", "Library analytics")
        self._update(state, details, "AniListSync")

    def on_collections(self):
        state, details = self._resolve("Managing Collections", "Organizing library")
        self._update(state, details, "AniListSync")

    def on_compare(self):
        state, details = self._resolve("Comparing", "Library vs Telegram")
        self._update(state, details, "AniListSync")

    def on_repair(self):
        state, details = self._resolve("Running Repair", "Fixing library issues")
        self._update(state, details, "AniListSync")

    def on_bulk_operations(self):
        state, details = self._resolve("Bulk Operations", "Batch library actions")
        self._update(state, details, "AniListSync")

    def on_plugin_menu(self):
        state, details = self._resolve("Plugin Manager", "Managing plugins")
        self._update(state, details, "AniListSync")

    def on_tools(self):
        state, details = self._resolve("Tools", "Utility functions")
        self._update(state, details, "AniListSync")

    def on_health_scan(self):
        count = self._library_count()
        state, details = self._resolve("Library Health", count)
        self._update(state, details, "AniListSync")

    def on_backup(self, path):
        if self._state == "Synchronizing Library":
            return
        state, details = self._resolve("Creating Backup", path)
        self._update(state, details, "AniListSync")

    # --- commands ---

    def get_commands(self):
        return [
            ("Reconnect RPC", self._reconnect_rpc),
            ("Set Client ID", self._set_client_id),
            ("Set Custom State", self._set_custom_state),
            ("Set Custom Details", self._set_custom_details),
            ("Clear Custom Text", self._clear_custom_text),
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

    def _set_custom_state(self):
        current = self.settings.get("discord_state", "")
        try:
            val = input(f"  Custom state text [{current}]: ").strip()
            self.settings["discord_state"] = val
            self.save_settings()
            if self._connected:
                self._update(
                    val or self._last_state,
                    self._last_details,
                    "AniListSync",
                )
            print("  Custom state updated.")
        except (EOFError, KeyboardInterrupt):
            pass

    def _set_custom_details(self):
        current = self.settings.get("discord_details", "")
        try:
            val = input(f"  Custom details text [{current}]: ").strip()
            self.settings["discord_details"] = val
            self.save_settings()
            if self._connected:
                self._update(
                    self._last_state,
                    val or self._last_details,
                    "AniListSync",
                )
            print("  Custom details updated.")
        except (EOFError, KeyboardInterrupt):
            pass

    def _clear_custom_text(self):
        self.settings["discord_state"] = ""
        self.settings["discord_details"] = ""
        self.save_settings()
        print("  Custom text cleared — auto-generated text will show.")
