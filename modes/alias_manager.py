import re

from anilist import ALIASES, save_alias, search_candidates
from utils.file_utils import save_json
from utils.ui import ask, console, pause, success, warning, show_header, show_key_value_table, show_menu
from utils.menu_keys import *  # noqa: F405


def alias_manager():

    while True:

        choice = show_menu(
            "Alias Manager",
            [
                "View aliases",
                "Search alias",
                "Edit alias",
                "Merge aliases",
                "Delete alias",
                "Detect duplicates",
                "Statistics",
                "Back",
            ],
        )

        if choice == ALIAS_VIEW:
            view_aliases()

        elif choice == ALIAS_SEARCH:
            search_alias()

        elif choice == ALIAS_EDIT:
            edit_alias()

        elif choice == ALIAS_MERGE:
            merge_aliases()

        elif choice == ALIAS_DELETE:
            delete_alias()

        elif choice == ALIAS_DEDUP:
            detect_duplicates()

        elif choice == ALIAS_STATS:
            alias_statistics()

        elif choice == ALIAS_BACK:
            break

        else:

            warning("Invalid choice.")


def view_aliases():

    aliases = sorted(ALIASES.items())

    PAGE_SIZE = 50

    page = 0

    while True:

        start = page * PAGE_SIZE
        end = start + PAGE_SIZE

        current = aliases[start:end]

        show_header(
            f"Aliases {start+1}-{min(end, len(aliases))} "
            f"of {len(aliases)}"
        )

        for alias, data in current:

            print(
                f"{alias} -> {data['title']}"
            )

        print()

        print("[N] Next")
        print("[P] Previous")
        print("[Q] Back")

        choice = ask(">").lower()

        if choice == PAGE_NEXT:

            if end < len(aliases):

                page += 1

        elif choice == PAGE_PREV:

            if page > 0:

                page -= 1

        elif choice == PAGE_BACK:

            break


def search_alias():

    query = ask("Search:").lower()

    print()

    found = False

    for alias, data in sorted(ALIASES.items()):

        if query in alias:

            found = True

            print(

                alias,

                "->",

                data["title"]

            )

    if not found:

        warning("No aliases found.")

    pause()


def edit_alias():

    alias = ask("Alias:").lower()

    if alias not in ALIASES:

        warning("Alias not found.")

        pause()

        return

    print()

    print("Current mapping")

    print()

    print(alias)

    print("↓")

    print(ALIASES[alias]["title"])

    query = ask("New search (Enter = reuse title):")

    if not query:

        query = alias

    candidates = search_candidates(query)

    if not candidates:

        warning("No candidates found.")

        pause()

        return

    print()

    for i, (score, candidate) in enumerate(candidates, 1):

        title = (
            candidate["title"].get("english")
            or
            candidate["title"].get("romaji")
            or
            candidate["title"].get("native")
        )

        print(f"{i}. {title} ({score:.1f}%)")

    try:
        pick = int(ask())
    except ValueError:
        warning("Invalid selection.")
        return

    if pick < 1 or pick > len(candidates):
        warning("Invalid selection.")
        return

    result = candidates[pick-1][1]

    save_alias(
        alias,
        result
    )

    success("Alias updated.")


def merge_aliases():

    keep = ask("Alias to keep:").lower()

    if keep not in ALIASES:
        warning("Alias not found.")
        pause()
        return

    remove = ask("Alias to remove:").lower()

    if remove not in ALIASES:
        warning("Alias not found.")
        pause()
        return

    if keep == remove:

        warning("Both aliases are the same.")

        pause()

        return

    print()

    print("Keep")

    print(
        keep,
        "->",
        ALIASES[keep]["title"]
    )

    print()

    print("Delete")

    print(
        remove,
        "->",
        ALIASES[remove]["title"]
    )

    confirm = ask("Merge? (y/n):").lower()

    if confirm == "y":

        del ALIASES[remove]

        save_json(
            "aliases.json",
            ALIASES
        )

        success("Merged.")


def delete_alias():

    alias = ask("Alias to delete:").lower()

    if alias not in ALIASES:
        warning("Alias not found.")
        pause()
        return

    print()
    print(alias)
    print("↓")
    print(ALIASES[alias]["title"])

    confirm = ask("Delete this alias? (y/n):").lower()

    if confirm not in ("y", "yes"):
        warning("Cancelled.")
        pause()
        return

    del ALIASES[alias]

    save_json("aliases.json", ALIASES)

    success("Alias deleted.")
    pause()


def detect_duplicates():

    def normalize(key):
        return re.sub(r"[^a-z0-9]", "", key.lower())

    groups = {}
    for key in ALIASES:
        normal = normalize(key)
        groups.setdefault(normal, []).append(key)

    duplicates = {k: v for k, v in groups.items() if len(v) > 1}

    if not duplicates:
        show_header("Detect Duplicates")
        success("No duplicate aliases found.")
        pause()
        return

    show_header("Detect Duplicates")
    print(f"Found [green]{sum(len(v) for v in duplicates.values())}[/] duplicate aliases\n")

    any_merged = False

    for normal, keys in duplicates.items():
        console.print(f"[dim]{'─' * 40}[/]")

        for i, key in enumerate(keys, 1):
            data = ALIASES[key]
            title = data.get("title", "?")
            console.print(f"  {i}. [cyan]{key}[/] -> {title}")

        print()
        pick = ask("Keep which one? (number, 0 = skip)").strip()
        if not pick.isdigit():
            warning("Skipped.")
            print()
            continue
        pick = int(pick)
        if pick < 1 or pick > len(keys):
            print()
            continue
        keep_key = keys[pick - 1]
        for key in keys:
            if key != keep_key:
                del ALIASES[key]
        save_json("aliases.json", ALIASES)
        success(f"Merged into '{keep_key}'.")
        any_merged = True
        print()

    if not any_merged:
        warning("No aliases were merged.")

    pause()


def alias_statistics():

    aliases = list(ALIASES.keys())
    values = {"Total aliases": len(aliases)}

    if aliases:

        longest = max(aliases, key=len)
        shortest = min(aliases, key=len)

        avg = sum(
            len(a)
            for a in aliases
        ) / len(aliases)

        values.update(
            {
                "Longest": longest,
                "Shortest": shortest,
                "Average": f"{avg:.1f}",
            }
        )

    show_key_value_table("Alias Statistics", values)
    pause()
