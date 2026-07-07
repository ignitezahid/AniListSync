import json
from pathlib import Path

from utils.constants import ALIASES_FILE, CACHE_FILE, RETRY_FILE
from utils.file_utils import load_json
from utils.ui import warning, show_menu
from utils.menu_keys import *  # noqa: F405
from anilist import get_completed_anime
from mal import get_completed_mal_anime
from telegram_client import client

from .common import (
    _alias_rows,
    _alias_txt_lines,
    _anime_fields,
    _export_dataset,
    _library_rows,
)


def export_menu():
    return show_menu(
        "Export Center",
        [
            "AniList",
            "MAL",
            "Telegram",
            "Missing",
            "Retry Queue",
            "Aliases",
            "Search Cache",
            "Back",
        ],
    )


async def export_center():
    while True:
        choice = export_menu()
        if choice == EXPORT_ANILIST:
            export_anilist_library()
        elif choice == EXPORT_MAL:
            export_mal_library()
        elif choice == EXPORT_TELEGRAM:
            await export_telegram_titles()
        elif choice == EXPORT_MISSING:
            export_missing_anime()
        elif choice == EXPORT_RETRY:
            export_retry_queue()
        elif choice == EXPORT_ALIASES:
            export_aliases()
        elif choice == EXPORT_CACHE:
            export_search_cache()
        elif choice == EXPORT_BACK:
            break
        else:
            warning("Invalid choice.")


def export_anilist_library():
    anime = sorted(get_completed_anime(), key=lambda item: item.get("title", "").lower())
    rows = _library_rows(anime)
    headers = ["Title", "AniList ID", "MAL ID", "Episodes", "Status", "Progress"]
    txt_lines = [item.get("title", "") for item in anime]
    _export_dataset("anilist_library", anime, rows, headers, txt_lines=txt_lines)


def export_mal_library():
    anime = sorted(get_completed_mal_anime(), key=lambda item: item.get("title", "").lower())
    rows = _library_rows(anime)
    headers = ["Title", "AniList ID", "MAL ID", "Episodes", "Status", "Progress"]
    txt_lines = [item.get("title", "") for item in anime]
    _export_dataset("mal_library", anime, rows, headers, txt_lines=txt_lines)


async def export_telegram_titles():
    started_here = False
    seen = set()
    titles = []
    if not client.is_connected():
        await client.start()
        started_here = True
    try:
        async for message in client.iter_messages("me", reverse=True):
            if not getattr(message, "text", None):
                continue
            title = message.text.strip()
            if not title or title in seen:
                continue
            seen.add(title)
            titles.append(title)
    finally:
        if started_here:
            await client.disconnect()
    rows = [{"Title": title} for title in titles]
    _export_dataset("telegram_titles", titles, rows, ["Title"])


def export_missing_anime():
    report = load_json("missing_anilist.json", None)
    if report is None:
        root_report = Path("missing_anilist.json")
        if root_report.exists():
            with open(root_report, encoding="utf-8") as f:
                report = json.load(f)
    if not report:
        warning("No missing anime report found. Run Compare first.")
        return
    missing = report.get("missing", [])
    rows = [
        {
            "Title": item.get("matched_title") or item.get("telegram_title", ""),
            "Telegram Title": item.get("telegram_title", ""),
            "AniList ID": item.get("id", ""),
            "MAL ID": item.get("idMal", ""),
            "Episodes": item.get("episodes", ""),
            "Reason": item.get("reason", ""),
        }
        for item in missing
    ]
    headers = ["Title", "Telegram Title", "AniList ID", "MAL ID", "Episodes", "Reason"]
    _export_dataset("missing", missing, rows, headers)


def export_retry_queue():
    queue = load_json(RETRY_FILE, [])
    rows = [{"Title": title} for title in queue]
    _export_dataset("retry_queue", queue, rows, ["Title"])


def export_aliases():
    aliases = load_json(ALIASES_FILE, {})
    rows = _alias_rows(aliases)
    headers = ["Alias", "Title", "AniList ID", "MAL ID", "Episodes"]
    _export_dataset("aliases", aliases, rows, headers, txt_lines=_alias_txt_lines(aliases))


def export_search_cache():
    cache = load_json(CACHE_FILE, {})
    rows = []
    for query, item in sorted(cache.items()):
        title, anilist_id, mal_id, episodes = _anime_fields(item)
        rows.append({
            "Query": query,
            "Title": title,
            "AniList ID": anilist_id,
            "MAL ID": mal_id,
            "Episodes": episodes,
        })
    headers = ["Query", "Title", "AniList ID", "MAL ID", "Episodes"]
    _export_dataset("search_cache", cache, rows, headers)
