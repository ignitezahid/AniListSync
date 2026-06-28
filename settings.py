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
}


def load_settings():
    return load_json(
        SETTINGS_FILE,
        DEFAULT_SETTINGS
    )


def save_settings(settings):
    save_json(
        SETTINGS_FILE,
        settings
    )


SETTINGS = load_settings()

