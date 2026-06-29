from utils.file_utils import load_json, save_json
from utils.constants import SETTINGS_FILE


DEFAULT_SETTINGS = {
    "debug": False,
    "stop_after": 30,
    "stop_after_existing": 30,
    "anilist_per_page": 50,
    "search_results": 50,
    "max_retries": 6,
    "search_threshold": 70,
    "interactive_sync": True,
    "auto_backup": True,
    "default_status": "COMPLETED",
    "mal_default_status": "completed",

    # New defaults (added from data/settings.json)
    "enable_anilist": True,
    "enable_mal": True,
    "resume_import": True,
    "retry_failed": True,
    "auto_learn_aliases": True,
    "franchise_sync": True,
    "use_search_cache": True,
    "fuzzy_matching": True,
    "interactive_search": True,
    "confirm_before_sync": False,
}



def load_settings():
    settings = load_json(
        SETTINGS_FILE,
        DEFAULT_SETTINGS
    )

    # Ensure new keys exist even for older settings.json files
    if isinstance(settings, dict):
        for key, value in DEFAULT_SETTINGS.items():
            settings.setdefault(key, value)

    return settings



def save_settings(settings):
    save_json(
        SETTINGS_FILE,
        settings
    )


def save():
    save_settings(SETTINGS)



SETTINGS = load_settings()


def get_setting(key, default=None):
    return SETTINGS.get(key, default)


def set_setting(key, value):
    SETTINGS[key] = value
    save_settings(SETTINGS)


