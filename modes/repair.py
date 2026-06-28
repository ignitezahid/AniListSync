from anilist import (
    search_candidates,
    save_alias,
    add_to_list,
    find_similar_aliases
)

from mal import add_to_list as add_to_mal
from utils.file_utils import load_json, save_json


REPAIR_FILE = "missing_anilist.json"


def save_repair_report(report):
    save_json(REPAIR_FILE, report)


def repair():
    report = load_json(REPAIR_FILE)

    if not report:
        print(f"\n{REPAIR_FILE} not found.")
        print("Run Compare mode first (menu option 2) to generate it.\n")
        return

    while True:
        print()
        print("=" * 40)
        print("Repair Mode")
        print("=" * 40)
        print()

        missing_count = len(report.get("missing", []))
        not_found_count = len(report.get("not_found", []))

        print(f"1. Missing from AniList ({missing_count})")
        print(f"2. Not Found ({not_found_count})")
        print("3. Back")
        print()

        choice = input("Choice: ").strip()

        if choice == "3" or not choice:
            return

        if choice == "1":
            repair_list = report.get("missing", [])
        elif choice == "2":
            repair_list = report.get("not_found", [])
        else:
            continue

        index = 0

        while index < len(repair_list):
            anime = repair_list[index]

            matched = anime.get("matched_title")

            print()
            print("=" * 50)
            print(f"{index+1} / {len(repair_list)}")
            print()
            print(anime["telegram_title"])

            if matched:
                print(f"Current Match: {matched}")
            else:
                print("Current Match: None")

            # Step 1-6: fuzzy learned alias auto-repair
            aliases = find_similar_aliases(
                anime["telegram_title"]
            )

            if aliases:
                print("\nSimilar aliases found:\n")

                for i, item in enumerate(aliases, 1):
                    print(
                        f"{i}. "
                        f'{item["alias"]} '
                        f'→ {item["data"]["title"]} '
                        f'({item["score"]:.1f}%)'
                    )

                use_one = input(
                    "\nUse one? (1-5, Enter = No): "
                ).strip()

                if use_one:
                    alias = aliases[int(use_one) - 1]["data"]

                    add_to_list(alias["id"])
                    add_to_mal(
                        alias["idMal"],
                        episodes=alias["episodes"]
                    )

                    repair_list.pop(index)

                    save_repair_report(report)

                    print("✓ Auto repaired")
                    continue

            choice = input("[Y]es [N]ext [Q]uit : ").lower()

            if choice == "q":
                return

            if choice == "n":
                index += 1
                continue

            if choice != "y":
                save_repair_report(report)
                continue

            # Search Again flow
            query = input(
                "\nSearch (press Enter to reuse current title): "
            ).strip()

            if not query:
                query = anime["telegram_title"]

            candidates = search_candidates(query)

            if not candidates:
                print("No candidates found.")
                continue

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
                pick = int(
                    input("\nSelect number (0 = Cancel): ")
                )
            except ValueError:
                print("Invalid number.")
                continue

            if pick < 0 or pick > len(candidates):
                print("Invalid choice.")
                continue

            if pick == 0:
                continue

            result = candidates[pick - 1][1]

            print("\n" + "=" * 50)
            print("Selected:")
            print(
                result["title"].get("english")
                or
                result["title"].get("romaji")
                or
                result["title"].get("native")
            )
            print(f"Romaji  : {result['title'].get('romaji')}")
            print(f"English : {result['title'].get('english')}")
            print(f"Episodes: {result['episodes']}")
            print(f"MAL ID  : {result['idMal']}")
            print("=" * 50)

            confirm = input(
                "\nAccept this match? (y/n): "
            ).lower().strip()

            if confirm != "y":
                continue

            save_alias(
                anime["telegram_title"],
                result
            )

            add_to_list(result["id"])
            add_to_mal(
                result["idMal"],
                episodes=result["episodes"]
            )

            repair_list.pop(index)

            save_repair_report(report)

            print()
            print("✓ Alias saved")
            print("✓ Added to AniList")
            print("✓ Added to MyAnimeList")
            print("✓ Removed from repair list")
            print(f"\nRemaining: {len(repair_list)}")

            continue

