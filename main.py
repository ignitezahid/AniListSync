from utils.startup import startup_checks

startup_checks()

# noqa: E402
import os  # noqa: E402
import sys  # noqa: E402
import traceback  # noqa: E402
import warnings  # noqa: E402

# Suppress harmless Windows asyncio proactor cleanup warnings from Telethon
warnings.filterwarnings("ignore", category=ResourceWarning, message=".*ProactorBasePipeTransport.*")
warnings.filterwarnings("ignore", category=ResourceWarning, message=".*unclosed transport.*")

from telegram_client import client, init_accounts, ensure_connected, disconnect_client  # noqa: E402
from sync import main as sync_main  # noqa: E402
from menu import show_dashboard, show_main_menu  # noqa: E402
from utils.ui import success, warning, console  # noqa: E402
from utils.ui import reload_theme  # noqa: E402
from settings import get_setting  # noqa: E402
from modes.automation import run_auto_backup, run_auto_health, automation_menu  # noqa: E402
from modes.about import about  # noqa: E402
from modes.manual_search import manual_search  # noqa: E402
from modes.library_search import library_search  # noqa: E402
from modes.compare import compare  # noqa: E402
from modes.repair import repair  # noqa: E402
from core.plugin_manager import plugin_menu  # noqa: E402
from core.plugin_loader import plugin_manager  # noqa: E402
from utils.menu_keys import *  # noqa: E402,F405

plugin_manager.discover()
reload_theme()
init_accounts()
plugin_manager.call_hook("on_startup")

_client_started = False


def _ensure_client() -> bool:
    """Start or reconnect the primary Telegram client."""
    try:
        if client.is_connected():
            return True
        client.start()
        return True
    except Exception as e:
        warning(f"Telegram connection failed: {e}")
        return False


def run_sync():
    global _client_started
    try:
        run_auto_backup()
        if not _client_started:
            _client_started = _ensure_client()
        if not _client_started:
            warning("Cannot sync — Telegram not connected.")
            return
        client.loop.run_until_complete(sync_main())
        run_auto_health()
    except Exception:
        with open("logs/error.log", "a", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        traceback.print_exc()


show_dashboard()

# Auto-sync on startup
if get_setting("sync_on_startup"):
    console.print("  [title]Auto Sync on Startup[/]")
    run_sync()

while True:

    plugin_manager.call_hook("on_idle")

    try:
        choice = show_main_menu()
    except (EOFError, KeyboardInterrupt):
        choice = EXIT

    if choice == SYNC:
        run_sync()

    elif choice == AUTOMATION:
        plugin_manager.call_hook("on_automation")
        automation_menu()

    elif choice == MANUAL_SEARCH:
        plugin_manager.call_hook("on_manual_search")
        manual_search()

    elif choice == LIBRARY_SEARCH:
        plugin_manager.call_hook("on_library_search")
        library_search()

    elif choice == COLLECTIONS:
        plugin_manager.call_hook("on_collections")

        from modes.collection_manager import collection_manager

        collection_manager()

    elif choice == STATISTICS:
        plugin_manager.call_hook("on_statistics")

        from modes.statistics import statistics

        statistics()

    elif choice == COMPARE:
        plugin_manager.call_hook("on_compare")
        if not _client_started:
            _client_started = _ensure_client()
        if _client_started:
            client.loop.run_until_complete(compare())

    elif choice == REPAIR:
        plugin_manager.call_hook("on_repair")
        repair()

    elif choice == BULK_OPS:
        plugin_manager.call_hook("on_bulk_operations")

        from modes.bulk_operations import bulk_operations

        bulk_operations()

    elif choice == PLUGINS:
        plugin_manager.call_hook("on_plugin_menu")
        plugin_menu()

    elif choice == ABOUT:
        about()

    elif choice == TOOLS:
        plugin_manager.call_hook("on_tools")

        from modes.tools import data_center

        if not _client_started:
            _client_started = _ensure_client()
        if _client_started:
            client.loop.run_until_complete(data_center())

    elif choice == EXIT:

        success("Goodbye!")
        plugin_manager.call_hook("on_shutdown")
        try:
            if _client_started:
                client.loop.run_until_complete(disconnect_client())
        except Exception:
            pass
        sys.stdout.flush()
        os._exit(0)

    else:

        warning("Invalid choice.")
