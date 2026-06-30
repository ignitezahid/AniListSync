from anilist import ALIASES, save_alias, search_candidates
from utils.file_utils import save_json
from utils.ui import ask, pause, success, warning, show_header, show_key_value_table, show_menu


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
                "Statistics",
                "Back",
            ],
        )

        if choice == "1":

            view_aliases()

        elif choice == "2":

            search_alias()

        elif choice == "3":

            edit_alias()

        elif choice == "4":

            merge_aliases()

        elif choice == "5":

            delete_alias()

        elif choice == "6":

            alias_statistics()

        elif choice == "7":

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

        if choice == "n":

            if end < len(aliases):

                page += 1

        elif choice == "p":

            if page > 0:

                page -= 1

        elif choice == "q":

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

    pick = int(
        ask()
    )

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
