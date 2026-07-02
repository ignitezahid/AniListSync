from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from rich.table import Table

from anilist import (
    ALIASES,
    SEARCH_CACHE,
    get_completed_anime,
    get_completed_ids,
)

from mal import get_completed_mal_ids

from utils.constants import BACKUP_DIR, EXPORT_DIR, RETRY_FILE
from utils.file_utils import load_json
from utils.ui import console, pause, show_header
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
        if minutes := seconds // 60:
            if minutes < 60:
                return f"{minutes} min ago"
            if hours := minutes // 60:
                if hours < 24:
                    return f"{hours}h ago"
                return f"{hours // 24}d ago"
    except Exception:
        return "Unknown"
    return "Unknown"


def _section(title):
    console.print(f"[bold cyan]{title}[/]")


def _kv_table(rows):
    t = Table(show_header=False, box=None, pad_edge=False)
    t.add_column("", style="white", width=18)
    t.add_column("", style="green")
    for k, v in rows:
        t.add_row(k, str(v))
    console.print(t)


def statistics():
    retry_queue = load_json(RETRY_FILE, [])
    backup_count = len(list(Path(BACKUP_DIR).glob("*")))
    export_count = len(list(Path(EXPORT_DIR).glob("*")))

    cache_values = list(SEARCH_CACHE.values())
    cache_hits = sum(1 for v in cache_values if v)
    cache_misses = sum(1 for v in cache_values if not v)
    total_searches = cache_hits + cache_misses
    search_accuracy = round(cache_hits / total_searches * 100) if total_searches else 0

    last_sync = "Never"
    state_path = Path("state.json")
    if state_path.exists():
        try:
            import json
            with open(state_path, encoding="utf-8") as f:
                state = json.load(f)
            ls = state.get("last_sync", "")
            if ls:
                dt = datetime.fromisoformat(ls)
                last_sync = dt.strftime("%d %b %Y %I:%M %p").lstrip("0")
        except Exception:
            pass

    avg_sync_time = None
    telegram_found = 0
    usage_path = Path("data/usage_stats.json")
    if usage_path.exists():
        try:
            import json
            with open(usage_path, encoding="utf-8") as f:
                usage = json.load(f)
            durations = usage.get("sync_durations", [])
            if durations:
                avg_sync_time = round(sum(durations) / len(durations))
            telegram_found = usage.get("telegram_found", 0)
        except Exception:
            pass

    anime_list = get_completed_anime()
    studio_counter: Counter = Counter()
    genre_counter: Counter = Counter()
    year_counter: Counter = Counter()

    for anime in anime_list:
        for studio in anime.get("studios") or []:
            studio_counter[studio] += 1
        for genre in anime.get("genres") or []:
            genre_counter[genre] += 1
        year = anime.get("season_year")
        if year:
            year_counter[year] += 1

    most_studio = studio_counter.most_common(1)
    most_genre = genre_counter.most_common(1)
    most_year = year_counter.most_common(1)

    show_header("Statistics")
    console.print()

    _section("Library")
    _kv_table([
        ("AniList", len(get_completed_ids())),
        ("MAL", len(get_completed_mal_ids())),
        ("Telegram", telegram_found),
    ])

    console.print()
    _section("Search")
    _kv_table([
        ("Aliases Learned", len(ALIASES)),
        ("Cache Hits", cache_hits),
        ("Cache Misses", cache_misses),
        ("Retry Queue", len(retry_queue)),
        ("Search Accuracy", f"{search_accuracy}%"),
    ])

    console.print()
    _section("Sync")
    _kv_table([
        ("Last Sync", last_sync),
        ("Avg Sync Time", f"{avg_sync_time}s" if avg_sync_time else "N/A"),
    ])

    console.print()
    _section("Library Analysis")
    _kv_table([
        (
            "Most Added Studio",
            f"{most_studio[0][0]} ({most_studio[0][1]})" if most_studio else "N/A",
        ),
        (
            "Most Added Genre",
            f"{most_genre[0][0]} ({most_genre[0][1]})" if most_genre else "N/A",
        ),
        (
            "Most Added Year",
            f"{most_year[0][0]} ({most_year[0][1]})" if most_year else "N/A",
        ),
    ])

    console.print()
    _section("System")
    _kv_table([
        ("Backups", backup_count),
        ("Exports", export_count),
        ("Version", VERSION),
    ])

    pause()