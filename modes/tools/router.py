import json

from utils.ui import success, warning, show_menu
from utils.menu_keys import *  # noqa: F405
from mal import get_completed_mal_ids
from anilist import get_completed_ids
from modes.retry_queue import retry_queue_menu
from modes.alias_manager import detect_duplicates, alias_manager

from .common import ensure_exports
from .export_tools import export_center
from .health import _clean_old_backups, library_health
from .import_tools import import_center
from .backup import backup_center, restore_center
from .settings import settings_home


def bulk_operations():
    while True:
        choice = show_menu(
            "Bulk Operations",
            [
                "Refresh all MAL IDs",
                "Refresh all AniList IDs",
                "Refresh Library Caches",
                "Refresh Search Cache",
                "Retry Failed Titles",
                "Remove Duplicate Aliases",
                "Clean Old Backups",
                "Rebuild Statistics",
                "Verify Library",
                "Back",
            ],
        )

        if choice == BULK_TOOL_MAL:
            print("Refreshing MAL IDs from API...")
            mal_ids = list(get_completed_mal_ids(force_refresh=True))
            try:
                with open("state.json", encoding="utf-8") as f:
                    state = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                state = {}
            state["mal_ids"] = mal_ids
            with open("state.json", "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            success(f"Refreshed {len(mal_ids)} MAL IDs.")

        elif choice == BULK_TOOL_AL:
            print("Refreshing AniList IDs from API...")
            anilist_ids = list(get_completed_ids(force_refresh=True))
            try:
                with open("state.json", encoding="utf-8") as f:
                    state = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                state = {}
            state["anilist_ids"] = anilist_ids
            with open("state.json", "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            success(f"Refreshed {len(anilist_ids)} AniList IDs.")

        elif choice == BULK_TOOL_BOTH:
            print("Refreshing all library caches from API...")
            anilist_ids = list(get_completed_ids(force_refresh=True))
            mal_ids = list(get_completed_mal_ids(force_refresh=True))
            try:
                with open("state.json", encoding="utf-8") as f:
                    state = json.load(f)
            except (FileNotFoundError, json.JSONDecodeError):
                state = {}
            state["anilist_ids"] = anilist_ids
            state["mal_ids"] = mal_ids
            with open("state.json", "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            success(f"Refreshed {len(anilist_ids)} AniList + {len(mal_ids)} MAL IDs.")

        elif choice == BULK_TOOL_CACHE:
            from modes.search_cache import search_cache
            search_cache()

        elif choice == BULK_TOOL_RETRY:
            retry_queue_menu()

        elif choice == BULK_TOOL_DEDUP:
            detect_duplicates()

        elif choice == BULK_TOOL_CLEAN:
            _clean_old_backups()

        elif choice == BULK_TOOL_STATS:
            from modes.statistics import statistics
            statistics()

        elif choice == BULK_TOOL_VERIFY:
            library_health()

        elif choice == BACK:
            break
        else:
            warning("Invalid choice.")


async def data_center():
    ensure_exports()

    while True:
        choice = show_menu(
            "Tools",
            [
                "Export",
                "Import",
                "Backup",
                "Restore",
                "Alias Manager",
                "Search Cache",
                "Retry Queue",
                "Settings",
                "Library Health",
                "Back",
            ],
        )

        if choice == TOOLS_EXPORT:
            await export_center()
        elif choice == TOOLS_IMPORT:
            import_center()
        elif choice == TOOLS_BACKUP:
            backup_center()
        elif choice == TOOLS_RESTORE:
            restore_center()
        elif choice == TOOLS_ALIAS:
            alias_manager()
        elif choice == TOOLS_CACHE:
            from modes.search_cache import search_cache_menu
            search_cache_menu()
        elif choice == TOOLS_RETRY:
            retry_queue_menu()
        elif choice == TOOLS_SETTINGS:
            settings_home()
        elif choice == TOOLS_HEALTH:
            library_health()
        elif choice == BACK:
            break
        else:
            warning("Invalid choice.")
