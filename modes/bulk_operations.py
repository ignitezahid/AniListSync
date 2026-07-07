import json

from utils.ui import warning, success, show_menu
from utils.menu_keys import *  # noqa: F405
from utils.file_utils import load_json, save_json
from anilist import get_completed_anime, get_completed_ids
from mal import get_completed_mal_ids
from modes.tools import _clean_old_backups, library_health
from modes.alias_manager import detect_duplicates
from modes.statistics import statistics


def _refresh_anilist_cache():
    success("Refreshing AniList cache from API...")
    ids = list(get_completed_anime(force_refresh=True))
    success(f"Refreshed {len(ids)} AniList entries.")


def _refresh_mal_cache():
    success("Refreshing MAL cache from API...")
    ids = list(get_completed_mal_ids(force_refresh=True))
    success(f"Refreshed {len(ids)} MAL entries.")


def _refresh_all_ids():
    success("Refreshing all caches from API...")
    anilist_ids = list(get_completed_ids(force_refresh=True))
    mal_ids = list(get_completed_mal_ids(force_refresh=True))
    try:
        with open("state.json", encoding="utf-8") as f:
            state = json.load(f)
    except Exception:
        state = {}
    state["anilist_ids"] = anilist_ids
    state["mal_ids"] = mal_ids
    try:
        with open("state.json", "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2)
    except Exception:
        pass
    success(f"Refreshed {len(anilist_ids)} AniList + {len(mal_ids)} MAL IDs.")


def _run_library_health():
    library_health()


def _repair_missing_mal_ids():
    lib = {a["id"]: a for a in get_completed_anime()}
    collections = load_json("collections.json", {})
    fixed = 0
    for name, col in collections.items():
        entries = col.get("entries", col) if isinstance(col, dict) else col
        for entry in entries:
            if entry.get("idMal") is None:
                anime = lib.get(entry["id"])
                if anime and anime.get("idMal") is not None:
                    entry["idMal"] = anime["idMal"]
                    fixed += 1
    if fixed:
        save_json("collections.json", collections)
        success(f"Repaired {fixed} missing MAL IDs.")
    else:
        warning("No missing MAL IDs found.")


def _remove_duplicate_aliases():
    detect_duplicates()


def _clean_old_backups_wrapper():
    _clean_old_backups()


def _rebuild_statistics():
    statistics()


def _optimize_database():
    lib_ids = {a["id"] for a in get_completed_anime()}
    collections = load_json("collections.json", {})

    total_removed = 0
    empty_collections = []

    for name, col in list(collections.items()):
        if isinstance(col, list):
            col = {"icon": "📁", "entries": col}
            collections[name] = col
        entries = col.get("entries", [])
        before = len(entries)

        seen = set()
        deduped = []
        stale = 0
        for e in entries:
            eid = e.get("id")
            if eid in seen:
                stale += 1
                continue
            seen.add(eid)
            if eid not in lib_ids:
                stale += 1
                continue
            deduped.append(e)

        col["entries"] = deduped
        total_removed += before - len(deduped)

        if not deduped:
            empty_collections.append(name)

    for name in empty_collections:
        del collections[name]

    if total_removed or empty_collections:
        save_json("collections.json", collections)
        if total_removed:
            success(f"Removed {total_removed} stale/duplicate entries.")
        if empty_collections:
            success(f"Removed {len(empty_collections)} empty collections.")
    else:
        warning("Nothing to optimize.")


def bulk_operations():
    while True:
        choice = show_menu(
            "Bulk Operations",
            [
                "\U0001f9f9 Refresh AniList Cache",
                "\U0001f9f9 Refresh MAL Cache",
                "\U0001f504 Refresh All IDs",
                "\U0001fa7a Run Library Health",
                "\U0001f527 Repair Missing MAL IDs",
                "\u267b  Remove Duplicate Aliases",
                "\U0001f4c2 Clean Old Backups",
                "\U0001f4c8 Rebuild Statistics",
                "\U0001f680 Optimize Database",
                "Back",
            ],
        )

        if choice == BULK_REFRESH_AL:
            _refresh_anilist_cache()
        elif choice == BULK_REFRESH_MAL:
            _refresh_mal_cache()
        elif choice == BULK_REFRESH_ALL:
            _refresh_all_ids()
        elif choice == BULK_HEALTH:
            _run_library_health()
        elif choice == BULK_REPAIR_MAL:
            _repair_missing_mal_ids()
        elif choice == BULK_DEDUP:
            _remove_duplicate_aliases()
        elif choice == BULK_CLEAN:
            _clean_old_backups_wrapper()
        elif choice == BULK_REBUILD:
            _rebuild_statistics()
        elif choice == BULK_OPTIMIZE:
            _optimize_database()
        elif choice == BACK:
            break
        else:
            warning("Invalid choice.")
