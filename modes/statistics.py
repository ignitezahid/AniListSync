from pathlib import Path

from utils.ui import pause, show_key_value_table

from anilist import (
    get_completed_ids,
    ALIASES,
    SEARCH_CACHE
)

from mal import get_completed_mal_ids

from utils.constants import BACKUP_DIR, RESUME_FILE, RETRY_FILE, SETTINGS_FILE
from utils.file_utils import load_json


def statistics():

    retry_queue = load_json(
        RETRY_FILE,
        []
    )

    resume = load_json(
        RESUME_FILE,
        {}

    )

    settings = load_json(
        SETTINGS_FILE,
        {}
    )

    backup_count = len(
        list(Path(BACKUP_DIR).glob("*"))
    )

    show_key_value_table(
        "Anime Library Statistics",
        {
            "AniList Entries": len(get_completed_ids()),
            "MyAnimeList Entries": len(get_completed_mal_ids()),
            "Aliases": len(ALIASES),
            "Search Cache": len(SEARCH_CACHE),
            "Retry Queue": len(retry_queue),
            "Backups": backup_count,
            "Resume ID": resume.get("last_message_id", 0),
        },
    )

    pause()
