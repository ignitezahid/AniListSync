from datetime import datetime, timezone
from pathlib import Path

from utils.ui import pause, show_key_value_table

from anilist import (
    ALIASES,
    SEARCH_CACHE
)

from utils.constants import BACKUP_DIR, EXPORT_DIR, RETRY_FILE
from utils.file_utils import load_json
from version import VERSION


def _relative_time(iso_str: str) -> str:
    if not iso_str:
        return "Never"
    try:
        then = datetime.fromisoformat(iso_str)
        now = datetime.now(timezone.utc) if then.tzinfo else datetime.now()
        diff = now - then
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return "Just now"
        if seconds < 3600:
            return f"{seconds // 60} minutes ago"
        if seconds < 86400:
            return f"{seconds // 3600} hours ago"
        return f"{seconds // 86400} days ago"
    except Exception:
        return "Unknown"


def statistics():

    retry_queue = load_json(RETRY_FILE, [])

    backup_count = len(list(Path(BACKUP_DIR).glob("*")))

    export_count = len(list(Path(EXPORT_DIR).glob("*")))

    last_sync = "Never"
    state_path = Path("state.json")
    if state_path.exists():
        try:
            import json
            with open(state_path, encoding="utf-8") as f:
                state = json.load(f)
            last_sync = _relative_time(state.get("last_sync", ""))
        except Exception:
            pass

    show_key_value_table(
        "AniListSync Statistics",
        {
            "Aliases": len(ALIASES),
            "Search Cache": len(SEARCH_CACHE),
            "Retry Queue": len(retry_queue),
            "Backups": backup_count,
            "Exports": export_count,
            "Last Sync": last_sync,
            "Version": VERSION,
        },
    )

    pause()
