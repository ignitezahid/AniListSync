import asyncio
from asyncio import Queue
from concurrent.futures import ThreadPoolExecutor, as_completed
import json
import msvcrt
import os
from pathlib import Path
import threading
import time as time_module
from datetime import datetime, timezone
from telethon import events

from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Column

from core.plugin_loader import plugin_manager

from telegram_client import client, get_chat_sources, iter_all_sources
from utils import logger
from utils.backup import backup_file
from utils.menu_keys import *  # noqa: F405
from utils.constants import ALIASES_FILE, CACHE_FILE, RESUME_FILE, RETRY_FILE
from utils.file_utils import load_json, save_json
from utils.ui import (
    ask,
    console,
    warning,
    watcher_ready,
    show_key_value_table,
    show_menu,
)
from anilist import (
    search_anime,
    add_to_list,
    search_candidates,
    save_alias,
    get_media_with_relations,
)
from mal import (
    add_to_list as add_to_mal,
)

def load_resume(chat: str = "me") -> int:
    if os.environ.get("RESET_RESUME", "0") == "1":
        return 0
    data = load_json(RESUME_FILE, {})
    ids = data.get("last_message_ids") or {}
    return ids.get(chat, data.get("last_message_id", 0))


def save_resume(message_id: int, chat: str = "me") -> None:
    data = load_json(RESUME_FILE, {})
    ids = data.get("last_message_ids") or {}
    ids[chat] = message_id
    data["last_message_ids"] = ids
    save_json(RESUME_FILE, data)


def load_retry_queue() -> set[str]:
    return set(load_json(RETRY_FILE, []))


def save_retry_queue(queue: set[str]) -> None:
    with _id_lock:
        save_json(RETRY_FILE, list(queue))


completed_ids: set[int] = set()
mal_completed_ids: set[int] = set()
_id_lock = threading.Lock()

processed_titles: set[str] = set()
TITLE_QUEUE: Queue = Queue()
_importing: bool = False


def anime_title(anime: dict) -> str:
    title = anime.get("title") or {}
    return (
        title.get("english")
        or title.get("romaji")
        or title.get("native")
        or "Unknown title"
    )


def _start_date_key(anime: dict) -> tuple:
    sd = anime.get("startDate") or {}
    return (sd.get("year") or 9999, sd.get("month") or 0, sd.get("day") or 0)


def generate_watch_order(selected: dict, related: list[dict]):
    exclude_types = {"ADAPTATION", "CHARACTER", "ALTERNATIVE"}
    exclude_formats = {"MUSIC"}
    all_anime = [selected]
    for r in related:
        if r.get("relationType") in exclude_types:
            continue
        if r.get("format") in exclude_formats:
            continue
        all_anime.append(r)

    all_anime.sort(key=_start_date_key)

    console.print()
    console.print("Recommended Order")
    console.print("-" * 40)
    for i, anime in enumerate(all_anime, 1):
        sd = anime.get("startDate") or {}
        y = sd.get("year") or "?"
        m = str(sd.get("month") or "").zfill(2) if sd.get("month") else "??"
        d = str(sd.get("day") or "").zfill(2) if sd.get("day") else "??"
        console.print(f"  {i:>2}. {anime_title(anime)}")
        console.print(f"       ({y}-{m}-{d})")
    console.print()


def choose_franchise(result: dict) -> list[dict]:
    selected, related = get_media_with_relations(result["id"])

    if not selected:
        return [result]

    console.print()
    console.print("Found:")
    console.print(anime_title(selected))

    if not related:
        return [selected]

    # Load library IDs to skip completed
    library_ids = set()
    try:
        with open("state.json", encoding="utf-8") as f:
            state = json.load(f)
        library_ids = set(state.get("anilist_ids", []))
    except Exception:
        pass

    in_library = [a for a in related if a["id"] in library_ids]
    available = [a for a in related if a["id"] not in library_ids]

    console.print()

    if in_library:
        console.print("Already in library")
        console.print("─" * 40)
        for anime in in_library:
            console.print(f"  ✓ {anime_title(anime)}")
        console.print()

    if not available:
        console.print("All related anime already in library.")
        return [selected]

    # Group available by format
    format_order = ["TV", "TV_SHORT", "MOVIE", "OVA", "ONA", "SPECIAL", "MUSIC"]
    format_labels = {"TV_SHORT": "TV Short", "MOVIE": "Movie", "ONA": "ONA", "SPECIAL": "Special", "MUSIC": "Music"}
    groups = {}
    for anime in available:
        fmt = anime.get("format") or "OTHER"
        groups.setdefault(fmt, []).append(anime)

    console.print("Franchise")
    console.print("─" * 40)
    for fmt in format_order:
        items = groups.get(fmt)
        if items is None:
            continue
        label = format_labels.get(fmt, fmt.title())
        console.print(f"  {label:<12} {len(items)}")
        for i, anime in enumerate(items, 1):
            console.print(f"    {i}. {anime_title(anime)}")
        console.print()
    for fmt, items in groups.items():
        if fmt in format_order:
            continue
        console.print(f"  {fmt:<12} {len(items)}")
        for i, anime in enumerate(items, 1):
            console.print(f"    {i}. {anime_title(anime)}")
        console.print()

    choice = show_menu(
        "Related Anime",
        [
            "🔹 Add selected anime only",
            "📚 Add all available",
            "🔍 Search another title",
            "📺 Show recommended watch order",
            "✋ Choose manually",
            "❌ Cancel"
        ],
    )

    if choice == RELATED_ADD_ALL:
        return [selected] + available

    elif choice == RELATED_SEARCH:
        return "search_again"

    elif choice == RELATED_ORDER:
        generate_watch_order(selected, related)
        return "search_again"

    if choice == RELATED_CHOOSE:
        flat = []
        for fmt in format_order:
            flat.extend(groups.get(fmt, []))
        for fmt, items in groups.items():
            if fmt not in format_order:
                flat.extend(items)

        console.print(f"  1. {anime_title(selected)}")
        for i, anime in enumerate(flat, 2):
            console.print(f"  {i}. {anime_title(anime)}")
        picks = ask("Choose numbers (comma separated):")

        chosen = []
        for item in picks.split(","):
            item = item.strip()
            if not item.isdigit():
                continue
            index = int(item)
            if index == 1:
                chosen.append(selected)
            elif 2 <= index <= len(flat) + 1:
                chosen.append(flat[index - 2])

        unique = []
        seen_ids = set()
        for anime in chosen:
            if anime["id"] in seen_ids:
                continue
            seen_ids.add(anime["id"])
            unique.append(anime)
        return unique

    if choice == RELATED_CANCEL:
        return []

    return [selected]


def interactive_search(title: str):
    """Search AniList and let the user choose the result."""

    attempts = 0
    while True:
        attempts += 1
        if attempts > 20:
            warning("Too many attempts. Cancelling.")
            return None

        result = search_anime(title)

        if not result:
            warning("No anime found.")
            title = ask("Search (leave blank to cancel):")

            if not title:
                return None

            continue

        if result.get("status") == "NOT_YET_RELEASED":
            warning("This anime has not been released yet.")
            title = ask("Search (leave blank to cancel):")

            if not title:
                return None

            continue

        selected = choose_franchise(result)

        if selected == "search_again":
            title = ask("Search:")
            continue

        if not selected:
            return None

        return selected


def add_selected_anime(
    anime: dict | None,
    stats: dict | None = None,
    retry_queue: set[str] | None = None,
    retry_title: str | None = None,
) -> bool:
    media_id = anime["id"]
    title = anime_title(anime)

    console.print()
    console.print(f"Adding: {title}")

    if media_id in completed_ids:
        if stats is not None:
            stats["exists"] += 1
        console.print("[AniList] Already Exists")
    else:
        if add_to_list(media_id):
            if stats is not None:
                stats["added"] += 1
            completed_ids.add(media_id)
            logger.success(
                "[AniList] Added"
            )
        else:
            if stats is not None:
                stats["failed"] += 1
            if (
                retry_queue is not None
                and retry_title is not None
                and retry_title not in retry_queue
            ):
                retry_queue.add(retry_title)
                save_retry_queue(retry_queue)
            console.print(f"[AniList] Failed: {title}\n")
            return False

    mal_id = anime.get("idMal")
    if not mal_id:
        console.print("[MAL] No MAL ID — skipped\n")
    elif mal_id in mal_completed_ids:
        console.print("[MAL] Already Exists\n")
    else:
        mal_added = add_to_mal(
            mal_id,
            episodes=anime.get("episodes"),
        )
        if mal_added == "added":
            mal_completed_ids.add(mal_id)
            console.print("[MAL] Added\n")
        elif mal_added == "updated":
            mal_completed_ids.add(mal_id)
            console.print("[MAL] Updated\n")
        else:
            if stats is not None:
                stats["failed"] += 1
            if (
                retry_queue is not None
                and retry_title is not None
                and retry_title not in retry_queue
            ):
                retry_queue.add(retry_title)
                save_retry_queue(retry_queue)

            console.print(f"[MAL] Failed: {title}\n")
            return False

    plugin_manager.call_hook("on_anime_added", anime)
    return True


def add_anime_batch(
    selected_anime: list[dict],
    stats: dict | None = None,
    retry_queue: set[str] | None = None,
    title: str | None = None,
) -> bool:
    max_workers = min(4, len(selected_anime))
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(add_selected_anime, anime, stats, retry_queue, title): anime
            for anime in selected_anime
        }
        with Progress(
            TextColumn("[progress.description]{task.description:<52}", table_column=Column(width=52)),
            BarColumn(),
            TextColumn(" {task.completed:>4.0f}/{task.total}"),
            console=console,
        ) as progress:
            task = progress.add_task("Adding:", total=len(selected_anime))
            for future in as_completed(futures):
                if not future.result():
                    return False
                progress.advance(task)
    return True


async def import_old_messages(stats: dict, last_message_id: int) -> None:
    global processed_titles

    print("Importing from Saved Messages...\n")

    if last_message_id:
        print(f"Resuming from message ID: {last_message_id}")
    else:
        print("Starting a new import.")

    retry_queue = load_retry_queue()
    if retry_queue:
        print(f"Retrying {len(retry_queue)} previously failed anime...")

    async def process_title(title: str) -> None:
        if not title:
            return
        if title in processed_titles:
            return

        processed_titles.add(title)
        stats["checked"] += 1

        await asyncio.sleep(1)

        result = search_anime(title)
        if not result:
            while True:
                option = show_menu(
                    f"Anime not found: {title}",
                    [
                        "Search Again",
                        "Skip",
                    ],
                )

                if option == "2":
                    stats["not_found"] += 1
                    if title not in retry_queue:
                        retry_queue.add(title)
                        save_retry_queue(retry_queue)
                    logger.warning(
                        f"[NOT FOUND] {title}"
                    )
                    return

                if option != "1":
                    warning("Invalid choice.")
                    continue

                query = ask("Search (Enter = reuse title):")
                if not query:
                    query = title

                candidates = search_candidates(query)
                if not candidates:
                    warning("No results.")
                    continue

                print()
                for i, (score, anime) in enumerate(candidates, 1):
                    print(
                        f"{i}. "
                        f"{anime['title']['english'] or anime['title']['romaji']} "
                        f"({score:.1f}%)"
                    )

                try:
                    pick = int(ask())
                except ValueError:
                    warning("Invalid choice.")
                    continue

                if pick < 1 or pick > len(candidates):
                    warning("Invalid choice.")
                    continue

                result = candidates[pick - 1][1]

                # Always save using Telegram title (NOT query)
                save_alias(title, result)
                break

        selected_anime = interactive_search(title)

        if not selected_anime:
            stats["cancelled"] += 1
            warning("Cancelled.")
            return

        if not add_anime_batch(selected_anime, stats, retry_queue, title):
            stats["failed_titles"] += 1
            return

        stats["completed"] += 1

        # If it previously failed but now succeeded, remove from retry queue.
        if title in retry_queue:
            retry_queue.remove(title)
            save_retry_queue(retry_queue)

    # Collect all titles upfront for progress tracking
    all_titles = list(retry_queue)
    seen = set(all_titles)
    title_to_msg_id = {}

    for c, chat in iter_all_sources():
        chat_last_id = load_resume(chat)
        try:
            async for message in c.iter_messages(chat, min_id=chat_last_id, reverse=True):
                if not getattr(message, "text", None):
                    continue
                title = message.text.strip()
                if title and title not in seen:
                    all_titles.append(title)
                    seen.add(title)
                    title_to_msg_id[title] = (chat, message.id)
        except Exception as e:
            print(f"  [yellow]Skipping chat '{chat}': {e}[/]")

    if not all_titles:
        print("No new titles to process.")
        return

    with Progress(
        TextColumn("[progress.description]{task.description:<50}", table_column=Column(width=52)),
        BarColumn(),
        TextColumn(" {task.completed:>4.0f}/{task.total}"),
        console=console,
    ) as progress:
        task = progress.add_task("Checking:", total=len(all_titles))

        for title in all_titles:
            progress.update(task, description=f"Checking:\n{title}")

            if title not in processed_titles:
                progress.stop()
                await process_title(title)
                progress.start()

            info = title_to_msg_id.get(title)
            if info:
                chat, msg_id = info
                save_resume(msg_id, chat)

            progress.advance(task)


_watchers_registered = False


def _register_watchers():
    global _watchers_registered
    if _watchers_registered:
        return
    _watchers_registered = True
    from telegram_client import get_all_clients

    for c, sources in get_all_clients():
        for src in sources:
            _register_single_watcher(c, src)


def _register_single_watcher(c, src):
    source_key = src  # capture the configured source string (e.g. "me", "@channel")

    @c.on(events.NewMessage(chats=src))
    async def new_source_message(event):
        await _handle_new_message(event, source_key)

    return new_source_message


async def _handle_new_message(event, source_key: str):
    global _importing
    if _importing or not event.raw_text:
        return

    title = event.raw_text.strip()
    if not title:
        return

    if event.id <= load_resume(source_key):
        return

    print(f"\nNew anime detected: {title}")
    print(f"From: {source_key} (ID: {event.id})")
    await asyncio.sleep(1)

    await TITLE_QUEUE.put(title)
    save_resume(event.id, source_key)


async def main(gui_mode: bool = False) -> None:
    global completed_ids, mal_completed_ids, processed_titles, _importing

    sync_start = time_module.time()

    plugin_manager.call_hook("on_sync_start")

    stats = {
        "checked": 0,
        "completed": 0,
        "added": 0,
        "exists": 0,
        "not_found": 0,
        "failed": 0,
        "failed_titles": 0,
        "cancelled": 0,
        "aliases": 0,
    }

    backup_file(ALIASES_FILE)
    backup_file(CACHE_FILE)
    backup_file(RESUME_FILE)
    backup_file(RETRY_FILE)

    print("Loading AniList...")
    cached = {}
    try:
        with open("state.json", encoding="utf-8") as f:
            cached = json.load(f)
    except Exception:
        pass

    anilist_ids = cached.get("anilist_ids", [])
    mal_ids = cached.get("mal_ids", [])
    completed_ids = set(anilist_ids)
    mal_completed_ids = set(mal_ids)

    print(f"Loaded {len(anilist_ids)} anime from AniList.")
    print("Loading MyAnimeList...")
    print(f"Loaded {len(mal_ids)} anime from MyAnimeList.")

    global _importing

    processed_titles = set()
    last_message_id = load_resume()

    _importing = True
    await import_old_messages(stats, last_message_id)
    _importing = False

    show_key_value_table(
        "Import Finished",
        {
            "Checked": stats["checked"],
            "Completed": stats["completed"],
            "Not Found": stats["not_found"],
            "Failed Titles": stats["failed_titles"],
            "Cancelled": stats["cancelled"],
            "Title Total": (
                stats["completed"]
                + stats["not_found"]
                + stats["failed_titles"]
                + stats["cancelled"]
            ),
            "Anime Added": stats["added"],
            "Anime Existing": stats["exists"],
            "Anime Failed": stats["failed"],
            "Aliases Learned": stats["aliases"],
        },
    )

    try:
        with open("state.json", "w", encoding="utf-8") as f:
            json.dump({
                "last_sync": datetime.now(timezone.utc).isoformat(),
                "anilist_entries": len(completed_ids),
                "mal_entries": len(mal_completed_ids),
                "anilist_ids": list(completed_ids),
                "mal_ids": list(mal_completed_ids),
            }, f)
    except Exception:
        pass

    sync_duration = time_module.time() - sync_start
    try:
        usage_path = Path("data/usage_stats.json")
        usage = {}
        if usage_path.exists():
            with open(usage_path, encoding="utf-8") as f:
                usage = json.load(f)
        durations = usage.get("sync_durations", [])
        durations.append(round(sync_duration))
        usage["sync_durations"] = durations[-20:]
        usage["telegram_found"] = stats["checked"]
        with open(usage_path, "w", encoding="utf-8") as f:
            json.dump(usage, f)
    except Exception:
        pass

    plugin_manager.call_hook("on_sync_finish")

    if gui_mode:
        return

    _register_watchers()

    console.print()
    watcher_ready()

    state_counter = 0

    while True:

        if msvcrt.kbhit():
            key = msvcrt.getch()
            if key == b"\x1b":
                break

        if not TITLE_QUEUE.empty():

            title = await TITLE_QUEUE.get()

            selected_anime = interactive_search(title)

            if not selected_anime:
                logger.warning("[NOT FOUND]")
                continue

            if not add_anime_batch(selected_anime):
                logger.warning("[FAILED]")
                continue

            try:
                state_counter += 1
                if state_counter % 5 == 0:
                    with open("state.json", "w", encoding="utf-8") as f:
                        json.dump({
                            "last_sync": datetime.now(timezone.utc).isoformat(),
                            "anilist_entries": len(completed_ids),
                            "mal_entries": len(mal_completed_ids),
                            "anilist_ids": list(completed_ids),
                            "mal_ids": list(mal_completed_ids),
                        }, f)
            except Exception:
                pass

            console.print()
            watcher_ready()

        await asyncio.sleep(0.05)
