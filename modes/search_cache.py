from utils.constants import CACHE_FILE
from utils.file_utils import load_json, save_json
from utils.ui import ask, pause, success, warning, show_header, show_menu
from utils.ui import show_key_value_table
from modes.tools import export_search_cache
def export_cache():

    export_search_cache()


def search_cache_menu():

    while True:

        choice = show_menu(
            "Search Cache",
            [
                "View Cache",
                "Search Entry",
                "Delete Entry",
                "Clear Cache",
                "Export Cache",
                "Statistics",
                "Back",
            ],
        )

        if choice == "1":
            view_cache()

        elif choice == "2":
            search_cache()

        elif choice == "3":
            delete_cache_entry()

        elif choice == "4":
            clear_cache()

        elif choice == "5":
            export_cache()

        elif choice == "6":
            cache_statistics()

        elif choice == "7":
            break

        else:
            warning("Invalid choice.")


def view_cache():

    cache = load_json(CACHE_FILE, {})

    entries = sorted(cache.items())

    PAGE_SIZE = 50

    page = 0

    while True:

        start = page * PAGE_SIZE
        end = start + PAGE_SIZE

        current = entries[start:end]

        show_header(
            f"Search Cache {start + 1}-{min(end, len(entries))} of {len(entries)}"
        )

        if not current:

            print("Cache is empty.\n")

        else:

            for query, anime in current:

                if anime:

                    title = (
                        anime.get("title", {}).get("english")
                        or anime.get("title", {}).get("romaji")
                        or anime.get("title", {}).get("native")
                        or "Unknown"
                    )

                else:

                    title = "[NOT FOUND]"

                print(f"{query} -> {title}")

        print()
        print("[N] Next")
        print("[P] Previous")
        print("[Q] Back")

        choice = ask(">").lower()

        if choice == "n":

            if end < len(entries):
                page += 1

        elif choice == "p":

            if page > 0:
                page -= 1

        elif choice == "q":

            break


def search_cache():

    cache = load_json(CACHE_FILE, {})

    query = ask("Search:").lower().strip()

    print()

    found = False

    for key, anime in sorted(cache.items()):

        if query not in key.lower():
            continue

        found = True

        if anime:

            title = (
                anime.get("title", {}).get("english")
                or anime.get("title", {}).get("romaji")
                or anime.get("title", {}).get("native")
                or "Unknown"
            )

        else:

            title = "[NOT FOUND]"

        print(f"{key} -> {title}")

    if not found:
        warning("No matching entries found.")

    pause()


def delete_cache_entry():

    while True:

        cache = load_json(CACHE_FILE, {})

        query = ask("Entry to delete (Enter = Back):").lower().strip()

        if not query:
            return

        if query not in cache:

            warning("Entry not found.")
            print()
            continue

        print()

        anime = cache[query]

        if anime:

            title = (
                anime.get("title", {}).get("english")
                or anime.get("title", {}).get("romaji")
                or anime.get("title", {}).get("native")
                or "Unknown"
            )

            print(f"{query} -> {title}")

        else:

            print(f"{query} -> [NOT FOUND]")

        confirm = ask("Delete this entry? (y/n):").lower()

        if confirm != "y":

            warning("Cancelled.")
            print()
            continue

        del cache[query]

        save_json(CACHE_FILE, cache)

        success("Entry deleted.")
        print()


def clear_cache():

    cache = load_json(CACHE_FILE, {})

    if not cache:

        warning("Search cache is already empty.")

        pause()

        return

    confirm = ask("Clear the entire search cache? (y/n):").lower()

    if confirm != "y":

        warning("Cancelled.")

        pause()

        return

    save_json(CACHE_FILE, {})

    success("Search cache cleared.")

    pause()


def cache_statistics():

    cache = load_json(CACHE_FILE, {})

    total = len(cache)

    successful = sum(
        1
        for value in cache.values()
        if value
    )

    failed = total - successful

    values = {
        "Total Entries": total,
        "Successful": successful,
        "Not Found": failed,
    }

    show_key_value_table(
        "Search Cache Statistics",
        values,
    )

    pause()