from anilist import ALIASES, save_alias, search_candidates
from utils.file_utils import save_json


def alias_manager():

    while True:

        print()

        print("=" * 50)
        print("Alias Manager")
        print("=" * 50)

        print()

        print("1. View aliases")
        print("2. Search alias")
        print("3. Edit alias")
        print("4. Merge aliases")
        print("5. Delete alias")
        print("6. Statistics")
        print("7. Back")

        print()

        choice = input("Choice: ").strip()

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

            print("Invalid choice.")


def view_aliases():

    aliases = sorted(ALIASES.items())

    PAGE_SIZE = 50

    page = 0

    while True:

        start = page * PAGE_SIZE
        end = start + PAGE_SIZE

        current = aliases[start:end]

        print()

        print("=" * 60)

        print(
            f"Aliases {start+1}-{min(end, len(aliases))} "
            f"of {len(aliases)}"
        )

        print("=" * 60)

        for alias, data in current:

            print(
                f"{alias} -> {data['title']}"
            )

        print()

        print("[N] Next")
        print("[P] Previous")
        print("[Q] Back")

        choice = input("> ").lower().strip()

        if choice == "n":

            if end < len(aliases):

                page += 1

        elif choice == "p":

            if page > 0:

                page -= 1

        elif choice == "q":

            break


def search_alias():

    query = input(

        "\nSearch: "

    ).lower().strip()

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

        print("No aliases found.")

    input("\nPress Enter...")


def edit_alias():

    alias = input(
        "\nAlias: "
    ).lower().strip()

    if alias not in ALIASES:

        print("Alias not found.")

        input("\nPress Enter...")

        return

    print()

    print("Current mapping")

    print()

    print(alias)

    print("↓")

    print(ALIASES[alias]["title"])

    query = input(

        "\nNew search (Enter = reuse title): "

    ).strip()

    if not query:

        query = alias

    candidates = search_candidates(query)

    if not candidates:

        print("No candidates found.")

        input("\nPress Enter...")

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
        input("\nChoice: ")
    )

    result = candidates[pick-1][1]

    save_alias(
        alias,
        result
    )

    print("Alias updated.")


def merge_aliases():

    keep = input(
        "\nAlias to keep: "
    ).lower().strip()

    if keep not in ALIASES:
        print("Alias not found.")
        input("\nPress Enter...")
        return

    remove = input(
        "Alias to remove: "
    ).lower().strip()

    if remove not in ALIASES:
        print("Alias not found.")
        input("\nPress Enter...")
        return

    if keep == remove:

        print("Both aliases are the same.")

        input("\nPress Enter...")

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

    confirm = input(

        "\nMerge? (y/n): "

    ).lower()

    if confirm == "y":

        del ALIASES[remove]

        save_json(
            "aliases.json",
            ALIASES
        )

        print("Merged.")


def alias_statistics():

    aliases = list(ALIASES.keys())

    print(f"Total aliases : {len(aliases)}")

    if aliases:

        longest = max(aliases, key=len)
        shortest = min(aliases, key=len)

        avg = sum(
            len(a)
            for a in aliases
        ) / len(aliases)

        print(f"Longest : {longest}")
        print(f"Shortest: {shortest}")
        print(f"Average : {avg:.1f}")

    input("\nPress Enter...")
