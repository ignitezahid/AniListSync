from utils.constants import SETTINGS_FILE
from utils.file_utils import save_json
from utils.ui import ask, success, warning, show_header, show_menu
from utils.menu_keys import *  # noqa: F405
from settings import load_settings


SETTING_LABELS = {
    "enable_anilist": "Enable AniList Sync",
    "enable_mal": "Enable MyAnimeList Sync",
    "resume_import": "Resume Imports",
    "retry_failed": "Retry Failed Anime",
    "auto_learn_aliases": "Auto Learn Aliases",
    "franchise_sync": "Franchise Sync",
    "use_search_cache": "Use Search Cache",
    "fuzzy_matching": "Fuzzy Matching",
    "interactive_search": "Interactive Search",
    "auto_backup": "Automatic Backup",
    "confirm_before_sync": "Confirm Before Sync",
    "interactive_sync": "Interactive Search",
    "debug": "Debug Mode",
    "search_threshold": "Search Similarity Threshold",
    "search_results": "Maximum Search Results",
    "max_retries": "Maximum Retries",
    "stop_after": "Stop After",
    "stop_after_existing": "Stop After Existing",
    "anilist_per_page": "AniList Page Size",
    "default_status": "AniList Default Status",
    "mal_default_status": "MAL Default Status",
}

SETTINGS_MENU = [
    (
        "Synchronization",
        [
            ("enable_anilist", "Enable AniList Sync"),
            ("enable_mal", "Enable MyAnimeList Sync"),
            ("resume_import", "Resume Imports"),
            ("retry_failed", "Retry Failed Anime"),
            ("auto_learn_aliases", "Auto Learn Aliases"),
            ("franchise_sync", "Franchise Sync"),
        ],
    ),
    (
        "Search",
        [
            ("use_cache", "Use Search Cache"),
            ("fuzzy_matching", "Fuzzy Matching"),
            ("interactive_search", "Interactive Search"),
        ],
    ),
    (
        "Backup",
        [
            ("auto_backup", "Automatic Backup"),
        ],
    ),
    (
        "User Interface",
        [
            ("confirm_before_sync", "Confirm Before Sync"),
        ],
    ),
    (
        "Advanced",
        [
            ("debug", "Debug Mode"),
            ("search_threshold", "Search Threshold"),
            ("search_results", "Maximum Search Results"),
            ("max_retries", "Maximum Retries"),
            ("anilist_per_page", "AniList Page Size"),
            ("stop_after", "Stop After"),
            ("stop_after_existing", "Stop After Existing"),
            ("default_status", "AniList Default Status"),
            ("mal_default_status", "MAL Default Status"),
        ],
    ),
]

BASIC_SETTINGS = {
    "enable_anilist", "enable_mal", "resume_import", "retry_failed",
    "auto_learn_aliases", "franchise_sync", "use_cache", "fuzzy_matching",
    "interactive_search", "auto_backup", "confirm_before_sync",
}

ADVANCED_SETTINGS = {
    "debug", "search_threshold", "search_results", "max_retries",
    "anilist_per_page", "stop_after", "stop_after_existing",
    "default_status", "mal_default_status",
}

SETTINGS_KEY_TO_SECTION = {
    "enable_anilist": "sync", "enable_mal": "sync", "resume_import": "sync",
    "retry_failed": "sync", "auto_learn_aliases": "sync", "franchise_sync": "sync",
    "use_search_cache": "search", "fuzzy_matching": "search", "interactive_search": "search",
    "auto_backup": "backup", "confirm_before_sync": "ui",
}


def settings_home():
    while True:
        choice = show_menu("Settings", ["Basic Settings", "Advanced Settings", "Back"])
        if choice == SETTINGS_BASIC:
            settings_editor("basic")
        elif choice == SETTINGS_ADVANCED:
            settings_editor("advanced")
        elif choice == SETTINGS_BACK:
            return


def settings_editor(mode):
    settings = load_settings()
    items = SETTINGS_MENU
    while True:
        title = "Basic Settings" if mode == "basic" else "Advanced Settings"
        show_header(title)
        option_map = {}
        option = 1
        for section, section_items in items:
            visible = [(k, lbl) for k, lbl in section_items
                       if (mode == "basic" and k in BASIC_SETTINGS)
                       or (mode == "advanced" and k in ADVANCED_SETTINGS)]
            if not visible:
                continue
            print(f"[ {section} ]")
            for key, label in visible:
                option_map[option] = key
                value = _get_value(settings, key)
                if isinstance(value, bool):
                    value = "ON" if value else "OFF"
                print(f"{option}. {label:<30} {value}")
                option += 1
            print()
        back_option = option
        print("-" * 40)
        print(f"{back_option}. Back")
        print()
        pick = ask()
        if not pick.isdigit():
            warning("Invalid choice.")
            continue
        idx = int(pick)
        if idx == back_option:
            break
        key = option_map.get(idx)
        if not key:
            warning("Invalid choice.")
            continue
        section_key = None
        for s, s_items in items:
            for k, _ in s_items:
                if k == key:
                    section_key = SETTINGS_KEY_TO_SECTION.get(k)
                    break
            if section_key:
                break
        if section_key and section_key in settings:
            old_val = settings[section_key].get(key)
        else:
            old_val = settings.get(key)
        if isinstance(old_val, bool):
            if section_key:
                settings[section_key][key] = not old_val
            else:
                settings[key] = not old_val
            save_json(SETTINGS_FILE, settings)
            label = SETTING_LABELS.get(key, key)
            new_state = "ON" if (section_key and settings[section_key][key]) or (not section_key and settings[key]) else "OFF"
            success(f"{label} -> {new_state}")
            continue
        new_val = ask(f"New value for {key}:")
        try:
            if isinstance(old_val, int):
                value = int(new_val)
            elif isinstance(old_val, float):
                value = float(new_val)
            else:
                value = new_val
        except ValueError:
            warning("Invalid value.")
            continue
        if section_key:
            settings[section_key][key] = value
        else:
            settings[key] = value
        save_json(SETTINGS_FILE, settings)
        success("Saved.")


def _get_value(settings, key):
    section_key = SETTINGS_KEY_TO_SECTION.get(key)
    if section_key and section_key in settings:
        return settings[section_key].get(key, "?")
    return settings.get(key, "?")
