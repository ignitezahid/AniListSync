from pathlib import Path

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

    print()

    print("=" * 50)
    print("Anime Library Statistics")
    print("=" * 50)

    print()

    print(
        f"AniList Entries : {len(get_completed_ids())}"
    )

    print(
        f"MAL Entries     : {len(get_completed_mal_ids())}"
    )

    print(
        f"Aliases         : {len(ALIASES)}"
    )

    print(
        f"Search Cache    : {len(SEARCH_CACHE)}"
    )

    print(
        f"Retry Queue     : {len(retry_queue)}"
    )

    print(
        f"Backups         : {backup_count}"
    )

    print(
        f"Resume ID       : {resume.get('last_message_id',0)}"
    )

    print()

    print("=" * 50)

    input("\nPress Enter to continue...")
