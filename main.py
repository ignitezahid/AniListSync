from utils.startup import startup_checks

startup_checks()

# noqa: E402
import traceback  # noqa: E402

from telegram_client import client  # noqa: E402
from sync import main as sync_main  # noqa: E402
from menu import show_dashboard, show_main_menu  # noqa: E402
from utils.ui import success, warning, console  # noqa: E402
from settings import get_setting  # noqa: E402
from modes.automation import run_auto_backup, run_auto_health  # noqa: E402


def run_sync():
    try:
        run_auto_backup()
        with client:
            client.loop.run_until_complete(sync_main())
        run_auto_health()
    except Exception:
        with open("logs/error.log", "a", encoding="utf-8") as f:
            traceback.print_exc(file=f)
        traceback.print_exc()


show_dashboard()

# Auto-sync on startup
if get_setting("sync_on_startup"):
    console.print("  [bold cyan]Auto Sync on Startup[/]")
    run_sync()

while True:

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

        from modes.compare import compare

        with client:
            client.loop.run_until_complete(compare())

    elif choice == "7":

        from modes.repair import repair

        repair()

    elif choice == "8":

        from modes.tools import data_center

        client.loop.run_until_complete(data_center())

    elif choice == "9":

        from modes.statistics import statistics

        statistics()

    elif choice == "10":

        from modes.bulk_operations import bulk_operations

        bulk_operations()

    elif choice == "11":

        success("Goodbye!")
        break

    else:

        warning("Invalid choice.")
