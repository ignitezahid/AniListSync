import asyncio

from telegram_client import client
from utils.file_utils import save_json
from anilist import (
    search_anime,
    get_completed_ids
)
async def compare():
    completed_ids = get_completed_ids()

    processed = set()

    report = {
        "summary": {
            "telegram_total": 0,
            "already_in_anilist": 0,
            "missing_from_anilist": 0,
            "not_found": 0
        },
        "missing": [],
        "not_found": []
    }

    async for message in client.iter_messages(
        "me",
        reverse=True
    ):
        if not message.text:
            continue

        title = message.text.strip()

        report["summary"]["telegram_total"] += 1

        if title in processed:
            continue

        processed.add(title)

        print(f"Checking: {title}")

        await asyncio.sleep(1)

        result = search_anime(title)

        if not result:
            report["summary"]["not_found"] += 1
            report["not_found"].append({
                "telegram_title": title
            })
            continue

        if result["id"] in completed_ids:
            report["summary"]["already_in_anilist"] += 1
        else:
            report["summary"]["missing_from_anilist"] += 1
            report["missing"].append({
                "telegram_title": title,
                "matched_title": (
                    result["title"]["english"]
                    or
                    result["title"]["romaji"]
                ),
                "id": result["id"],
                "idMal": result["idMal"],
                "episodes": result["episodes"],
                "reason": "Missing from AniList"
            })

    save_json("missing_anilist.json", report)

    print()
    print("=" * 40)
    print("Comparison Finished")
    print("=" * 40)
    print(f'Telegram : {report["summary"]["telegram_total"]}')
    print(f'AniList  : {report["summary"]["already_in_anilist"]}')
    print(f'Missing  : {report["summary"]["missing_from_anilist"]}')
    print(f'Not Found: {report["summary"]["not_found"]}')
    print()
    print("Saved as missing_anilist.json")
