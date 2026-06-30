import asyncio
import os
from telethon import events

from telegram_client import client
from utils import logger
from utils.backup import backup_file
from utils.constants import ALIASES_FILE, CACHE_FILE, RESUME_FILE, RETRY_FILE
from utils.file_utils import load_json, save_json
from utils.ui import (
    ask,
    success,
    warning,
    watcher_ready,
    show_key_value_table,
    show_menu,
)
from anilist import (
    search_anime,
    add_to_list,
    get_completed_ids,
    search_candidates,
    save_alias,
    get_media_with_relations,
)
from mal import (
    add_to_list as add_to_mal,
    get_completed_mal_ids,
)

def load_resume() -> int:
    if os.environ.get("RESET_RESUME", "0") == "1":
        return 0
    data = load_json(RESUME_FILE, {})
    return data.get("last_message_id", 0)


def save_resume(message_id: int) -> None:
    save_json(RESUME_FILE, {"last_message_id": message_id})


def load_retry_queue() -> list[str]:
    return load_json(RETRY_FILE, [])


def save_retry_queue(queue: list[str]) -> None:
    save_json(RETRY_FILE, queue)


completed_ids: set[int] = set()
mal_completed_ids: set[int] = set()

processed_titles: set[str] = set()


def anime_title(anime: dict) -> str:
    title = anime.get("title") or {}
    return (
        title.get("english")
        or title.get("romaji")
        or title.get("native")
        or "Unknown title"
    )


def choose_franchise(result: dict) -> list[dict]:
    selected, related = get_media_with_relations(result["id"])

    if not selected:
        return [result]

    print()
    print("Found:")
    print(anime_title(selected))

    if not related:
        return [selected]

    print()
    print(f"Related anime detected ({len(related)})")
    print()

    for i, anime in enumerate(related, 1):
        print(f"{i}. {anime_title(anime)}")

    choice = show_menu(
        "Related Anime",
        [
            "Add only selected anime",
            "Add entire franchise",
            "Choose manually",
            "Cancel",
        ],
    )

    if choice == "2":
        return [selected] + related

    if choice == "3":
        print()
        print(f"1. {anime_title(selected)}")

        for i, anime in enumerate(related, 2):
            print(f"{i}. {anime_title(anime)}")

        picks = ask("Choose numbers (comma separated):")

        chosen = []

        for item in picks.split(","):
            item = item.strip()

            if not item.isdigit():
                continue

            index = int(item)

            if index == 1:
                chosen.append(selected)
            elif 2 <= index <= len(related) + 1:
                chosen.append(related[index - 2])

        unique = []
        seen_ids = set()

        for anime in chosen:
            if anime["id"] in seen_ids:
                continue

            seen_ids.add(anime["id"])
            unique.append(anime)

        return unique

    if choice == "4":
        return []

    return [selected]


def add_selected_anime(
    anime: dict,
    stats: dict | None = None,
    retry_queue: list[str] | None = None,
    retry_title: str | None = None,
) -> bool:
    media_id = anime["id"]
    title = anime_title(anime)

    print()
    print(f"Adding: {title}")

    if media_id in completed_ids:
        if stats is not None:
            stats["exists"] += 1
        print("[AniList] Already Exists")
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
                retry_queue.append(retry_title)
                save_retry_queue(retry_queue)
                retry_queue.append(retry_title)
                save_retry_queue(retry_queue)
            print(f"[AniList] Failed: {title}\n")
            return False

    if anime.get("idMal") in mal_completed_ids:
        print("[MAL] Already Exists\n")
    else:
        mal_added = add_to_mal(
            anime.get("idMal"),
            episodes=anime.get("episodes"),
        )
        if mal_added == "added":
            mal_completed_ids.add(anime.get("idMal"))
            print("[MAL] Added\n")
        elif mal_added == "updated":
            mal_completed_ids.add(anime.get("idMal"))
            print("[MAL] Updated\n")
        else:
            if stats is not None:
                stats["failed"] += 1
            if (
                retry_queue is not None
                and retry_title is not None
                and retry_title not in retry_queue
            ):
                retry_queue.append(retry_title)
                save_retry_queue(retry_queue)

            print(f"[MAL] Failed: {title}\n")
            return False

    return True


async def import_old_messages(stats: dict, last_message_id: int) -> None:
    global processed_titles

    print("Importing previous Saved Messages...\n")

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
        logger.info(
            f"Checking: {title}"
        )

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
                        retry_queue.append(title)
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

        selected_anime = choose_franchise(result)

        if not selected_anime:
            stats["cancelled"] += 1
            warning("Cancelled.")
            return

        for anime in selected_anime:
            if not add_selected_anime(
                anime,
                stats,
                retry_queue,
                title,
            ):
                stats["failed_titles"] += 1
                return

        stats["completed"] += 1

        # If it previously failed but now succeeded, remove from retry queue.
        if title in retry_queue:
            retry_queue.remove(title)
            save_retry_queue(retry_queue)

    # First retry known failures
    for title in list(retry_queue):
        await process_title(title)

    # Then process chronological history with resume.
    async for message in client.iter_messages("me", reverse=True):
        if not getattr(message, "text", None):
            continue

        # Telegram IDs increase over time.
        if message.id <= last_message_id:
            continue

        title = message.text.strip()
        await process_title(title)

        # Update resume progress after we've attempted this message.
        save_resume(message.id)


@client.on(events.NewMessage(chats="me"))
async def new_saved_message(event):
    if not event.raw_text:
        return

    title = event.raw_text.strip()
    if not title:
        return

    print(f"\nNew anime detected: {title}")
    await asyncio.sleep(1)

    result = search_anime(title)
    if not result:
        logger.warning(
            "[NOT FOUND]"
        )
        return

    selected_anime = choose_franchise(result)

    if not selected_anime:
        warning("Cancelled.")
        return

    for anime in selected_anime:
        add_selected_anime(anime)
    print()
    watcher_ready()


async def main() -> None:
    global completed_ids, mal_completed_ids, processed_titles

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

    me = await client.get_me()
    print(f"Connected to Telegram as {me.first_name}\n")

    backup_file(ALIASES_FILE)
    backup_file(CACHE_FILE)
    backup_file(RESUME_FILE)
    backup_file(RETRY_FILE)

    print("Loading AniList...")
    completed_ids = get_completed_ids()

    print("Loading MyAnimeList...")
    mal_completed_ids = get_completed_mal_ids()
    print(f"Loaded {len(mal_completed_ids)} anime from MyAnimeList.")

    processed_titles = set()
    last_message_id = load_resume()

    await import_old_messages(stats, last_message_id)

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

    watcher_ready()
    await client.run_until_disconnected()
