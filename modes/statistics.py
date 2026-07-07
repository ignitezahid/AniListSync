from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
import json

from rich.table import Table

from anilist import (
    ALIASES,
    SEARCH_CACHE,
    get_completed_anime,
)

from mal import get_completed_mal_ids

from modes.tools import _export_dataset, _health_input
from utils.constants import BACKUP_DIR, EXPORT_DIR, RETRY_FILE
from utils.file_utils import load_json
from utils.ui import console, show_header, warning
from core.plugin_loader import plugin_manager
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
    console.print(f"[title]{title}[/]")


def _kv_table(rows):
    t = Table(show_header=False, box=None, pad_edge=False)
    t.add_column("", style="white", width=18)
    t.add_column("", style="green")
    for k, v in rows:
        t.add_row(k, str(v))
    console.print(t)


def _export_stats_report(anime_list, status_counter, total_count, avg_eps, avg_score,
                         genre_counter, season_counter, last_sync, avg_sync_time,
                         telegram_found, most_studio, most_genre, most_year,
                         backup_count, export_count, cache_hits, cache_misses,
                         search_accuracy, retry_queue):
    name = f"statistics_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    rows = []
    rows.append({"Section": "Library / AniList", "Value": str(len(anime_list))})
    rows.append({"Section": "Library / MAL", "Value": str(len(get_completed_mal_ids()))})
    rows.append({"Section": "Library / Telegram", "Value": str(telegram_found)})
    status_labels = {
        "COMPLETED": "Completed", "CURRENT": "Watching", "DROPPED": "Dropped",
        "PAUSED": "Paused", "PLANNING": "Planning", "REPEATING": "Rewatching",
    }
    for key, label in status_labels.items():
        count = status_counter.get(key, 0)
        if count:
            pct = count / total_count * 100
            rows.append({"Section": f"Completion / {label}", "Value": f"{count} ({pct:.1f}%)"})
    rows.append({"Section": "Completion / Average Episodes", "Value": str(avg_eps)})
    rows.append({"Section": "Completion / Average Score", "Value": str(avg_score)})
    for genre, count in genre_counter.most_common():
        rows.append({"Section": f"Genre / {genre}", "Value": str(count)})
    season_labels = {"WINTER": "Winter", "SPRING": "Spring", "SUMMER": "Summer", "FALL": "Fall"}
    for season in ["WINTER", "SPRING", "SUMMER", "FALL"]:
        c = season_counter.get(season, 0)
        if c:
            rows.append({"Section": f"Season / {season_labels.get(season, season)}", "Value": str(c)})
    rows.append({"Section": "Search / Aliases Learned", "Value": str(len(ALIASES))})
    rows.append({"Section": "Search / Cache Hits", "Value": str(cache_hits)})
    rows.append({"Section": "Search / Cache Misses", "Value": str(cache_misses)})
    rows.append({"Section": "Search / Retry Queue", "Value": str(len(retry_queue))})
    rows.append({"Section": "Search / Accuracy", "Value": f"{search_accuracy}%"})
    rows.append({"Section": "Sync / Last Sync", "Value": last_sync})
    rows.append({"Section": "Sync / Avg Sync Time", "Value": f"{avg_sync_time}s" if avg_sync_time else "N/A"})
    if most_studio:
        rows.append({"Section": "Library Analysis / Most Added Studio", "Value": f"{most_studio[0][0]} ({most_studio[0][1]})"})
    if most_genre:
        rows.append({"Section": "Library Analysis / Most Added Genre", "Value": f"{most_genre[0][0]} ({most_genre[0][1]})"})
    if most_year:
        rows.append({"Section": "Library Analysis / Most Added Year", "Value": f"{most_year[0][0]} ({most_year[0][1]})"})
    rows.append({"Section": "System / Backups", "Value": str(backup_count)})
    rows.append({"Section": "System / Exports", "Value": str(export_count)})
    rows.append({"Section": "System / Version", "Value": str(VERSION)})
    json_data = {
        "library": {
            "anilist": len(anime_list),
            "mal": len(get_completed_mal_ids()),
            "telegram": telegram_found,
        },
        "completion": {
            k: {"count": status_counter.get(k, 0), "pct": round(status_counter.get(k, 0) / total_count * 100, 1)}
            for k, label in status_labels.items() if status_counter.get(k, 0)
        },
        "averages": {"episodes": avg_eps, "score": avg_score},
        "genres": dict(genre_counter.most_common()),
        "seasons": {season_labels.get(s, s): c for s, c in season_counter.items()},
        "search": {
            "aliases": len(ALIASES),
            "cache_hits": cache_hits,
            "cache_misses": cache_misses,
            "retry_queue": len(retry_queue),
            "accuracy": search_accuracy,
        },
        "sync": {"last_sync": last_sync, "avg_sync_time": avg_sync_time},
        "library_analysis": {
            "most_studio": f"{most_studio[0][0]} ({most_studio[0][1]})" if most_studio else None,
            "most_genre": f"{most_genre[0][0]} ({most_genre[0][1]})" if most_genre else None,
            "most_year": f"{most_year[0][0]} ({most_year[0][1]})" if most_year else None,
        },
        "system": {"backups": backup_count, "exports": export_count, "version": VERSION},
        "timestamp": datetime.now().isoformat(),
    }
    _export_dataset(name, json_data, rows, ["Section", "Value"])


def statistics():
    plugin_manager.call_hook("on_statistics")
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

    status_labels = {
        "COMPLETED": "Completed",
        "CURRENT": "Watching",
        "DROPPED": "Dropped",
        "PAUSED": "Paused",
        "PLANNING": "Planning",
        "REPEATING": "Rewatching",
    }

    status_counter: Counter = Counter()
    total_episodes = 0
    total_scores = 0
    score_count = 0
    for a in anime_list:
        s = a.get("status") or "UNKNOWN"
        status_counter[s] += 1
        eps = a.get("episodes") or 0
        total_episodes += eps
        sc = a.get("score")
        if sc is not None:
            total_scores += sc
            score_count += 1

    total_count = len(anime_list) or 1
    avg_eps = round(total_episodes / total_count, 1)
    avg_score = round(total_scores / score_count, 2) if score_count else 0

    _section("Library")
    _kv_table([
        ("AniList", len(anime_list)),
        ("MAL", len(get_completed_mal_ids())),
        ("Telegram", telegram_found),
    ])

    console.print()
    _section("Completion Analytics")
    rows = []
    for key, label in status_labels.items():
        count = status_counter.get(key, 0)
        if count:
            pct = count / total_count * 100
            rows.append((label, f"{count} ({pct:.1f}%)"))
    _kv_table(rows)
    _kv_table([
        ("Average Episodes", str(avg_eps)),
        ("Average Score", str(avg_score)),
    ])

    console.print()
    _section("Genre Analytics")
    _kv_table(genre_counter.most_common())

    season_counter: Counter = Counter()
    for a in anime_list:
        s = a.get("season")
        if s:
            season_counter[s] += 1

    console.print()
    _section("Most Active Season")
    season_labels = {"WINTER": "Winter", "SPRING": "Spring", "SUMMER": "Summer", "FALL": "Fall"}
    season_items = []
    for season in ["WINTER", "SPRING", "SUMMER", "FALL"]:
        c = season_counter.get(season, 0)
        if c:
            season_items.append((season_labels.get(season, season), c))
    season_items.sort(key=lambda x: -x[1])
    _kv_table(season_items)

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

    print()
    print("  0. Export statistics")
    warning("Press ESC to return.")
    print("Choice: ", end="", flush=True)
    choice = _health_input()
    if choice == "0":

        _export_stats_report(
            anime_list, status_counter, total_count, avg_eps, avg_score,
            genre_counter, season_counter, last_sync, avg_sync_time,
            telegram_found, most_studio, most_genre, most_year,
            backup_count, export_count, cache_hits, cache_misses,
            search_accuracy, retry_queue,
        )
