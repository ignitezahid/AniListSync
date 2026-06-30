from anilist import (
    search_candidates,
    save_alias,
    add_to_list,
    find_similar_aliases
)

from mal import add_to_list as add_to_mal
from utils.file_utils import load_json, save_json
from utils.ui import ask, error, success, warning, show_header, show_menu


REPAIR_FILE = "missing_anilist.json"


def save_repair_report(report):
    save_json(REPAIR_FILE, report)


def repair():
    report = load_json(REPAIR_FILE)

    if not report:
        error(f"{REPAIR_FILE} not found.")
        warning("Run Compare mode first (menu option 2) to generate it.")
        return

    while True:
        missing_count = len(report.get("missing", []))
        not_found_count = len(report.get("not_found", []))

        choice = show_menu(
            "Repair Mode",
            [
                f"Missing from AniList ({missing_count})",
                f"Not Found ({not_found_count})",
                "Back",
            ],
        )

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

            show_header(f"{index+1} / {len(repair_list)}")
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

                use_one = ask("Use one? (1-5, Enter = No):")

                if use_one:
                    alias = aliases[int(use_one) - 1]["data"]

                    add_to_list(alias["id"])
                    add_to_mal(
                        alias["idMal"],
                        episodes=alias["episodes"]
                    )

                    repair_list.pop(index)

                    save_repair_report(report)

                    success("Auto repaired")
                    continue

            choice = ask("[Y]es [N]ext [Q]uit:").lower()

            if choice == "q":
                return

            if choice == "n":
                index += 1
                continue

            if choice != "y":
                save_repair_report(report)
                continue

            # Search Again flow
            query = ask("Search (press Enter to reuse current title):")

            if not query:
                query = anime["telegram_title"]

            candidates = search_candidates(query)

            if not candidates:
                warning("No candidates found.")
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
                    ask("Select number (0 = Cancel):")
                )
            except ValueError:
                warning("Invalid number.")
                continue

            if pick < 0 or pick > len(candidates):
                warning("Invalid choice.")
                continue

            if pick == 0:
                continue

            result = candidates[pick - 1][1]

            show_header("Selected")
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

            confirm = ask("Accept this match? (y/n):").lower()

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

            success("Alias saved")
            success("Added to AniList")
            success("Added to MyAnimeList")
            success("Removed from repair list")
            print(f"\nRemaining: {len(repair_list)}")

            continue

