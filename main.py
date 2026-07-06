from utils.startup import startup_checks

startup_checks()

# noqa: E402
import traceback  # noqa: E402

from telegram_client import client  # noqa: E402
from sync import main as sync_main  # noqa: E402
from menu import show_dashboard, show_main_menu  # noqa: E402
from utils.ui import success, warning, console  # noqa: E402
from utils.ui import reload_theme  # noqa: E402
from settings import get_setting  # noqa: E402
from modes.automation import run_auto_backup, run_auto_health  # noqa: E402
from core.plugin_loader import plugin_manager  # noqa: E402

plugin_manager.discover()
reload_theme()
plugin_manager.call_hook("on_startup")

_client_started = False


def run_sync():
    global _client_started
    try:
        run_auto_backup()
        if not _client_started:
            client.start()
            _client_started = True
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

    choice = show_main_menu()

    if choice == "1":
        run_sync()

    elif choice == "2":

        from modes.automation import automation_menu

        automation_menu()

    elif choice == "3":
        from modes.manual_search import manual_search
        manual_search()

    elif choice == "4":

        from modes.library_search import library_search

        library_search()

    elif choice == "5":

        from modes.collection_manager import collection_manager

        collection_manager()

    elif choice == "6":

        from modes.statistics import statistics

        statistics()

    elif choice == "7":

        from modes.compare import compare

        if not _client_started:
            client.start()
            _client_started = True
        client.loop.run_until_complete(compare())

    elif choice == "8":

        from modes.repair import repair

        repair()

    elif choice == "9":

        from modes.bulk_operations import bulk_operations

        bulk_operations()

    elif choice == "10":

        from core.plugin_manager import plugin_menu

        plugin_menu()

    elif choice == "11":

        from modes.about import about

        about()

    elif choice == "12":

        from modes.tools import data_center

        if not _client_started:
            client.start()
            _client_started = True
        client.loop.run_until_complete(data_center())

    elif choice == "13":

        success("Goodbye!")
        plugin_manager.call_hook("on_shutdown")
        import sys
        import os
        sys.stdout.flush()
        os._exit(0)

    else:

        warning("Invalid choice.")
