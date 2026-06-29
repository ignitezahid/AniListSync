import csv
import json
import re
from pathlib import Path
from shutil import copy2

from utils.backup import backup_file
from utils.constants import (
    ALIASES_FILE,
    BACKUP_DIR,
    CACHE_FILE,
    EXPORT_DIR,
    RESUME_FILE,
    RETRY_FILE,
    SETTINGS_FILE,
)
from utils.file_utils import data_file, load_json, save_json


EXPORT_PATH = Path(EXPORT_DIR)
DATA_FILES = [
    ALIASES_FILE,
    CACHE_FILE,
    RETRY_FILE,
    RESUME_FILE,
    SETTINGS_FILE,
    "missing_anilist.json",
]


def ensure_exports():
    EXPORT_PATH.mkdir(parents=True, exist_ok=True)


def export_path(filename):
    ensure_exports()
    return EXPORT_PATH / filename


def export_json(filename, data):
    path = export_path(_with_suffix(filename, "json"))

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

    return path


def export_txt(filename, data):
    path = export_path(_with_suffix(filename, "txt"))

    with open(path, "w", encoding="utf-8") as f:
        f.write("\n\n".join(_txt_lines(data)))
        f.write("\n")

    return path


def export_csv(filename, rows, headers):
    path = export_path(_with_suffix(filename, "csv"))

    with open(path, "w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        writer.writerows(rows)

    return path


def export_markdown(filename, rows, headers):
    path = export_path(_with_suffix(filename, "md"))

    with open(path, "w", encoding="utf-8") as f:
        f.write("| " + " | ".join(headers) + " |\n")
        f.write("| " + " | ".join(["---"] * len(headers)) + " |\n")

        for row in rows:
            values = [
                str(row.get(header, "")).replace("\n", " ")
                for header in headers
            ]
            f.write("| " + " | ".join(values) + " |\n")

    return path


def choose_format():
    while True:
        print()
        print("Export format")
        print()
        print("1. JSON")
        print("2. CSV")
        print("3. TXT")
        print("4. Markdown")
        print("5. Cancel")
        print()

        choice = input("Choice: ").strip()

        if choice == "1":
            return "json"
        if choice == "2":
            return "csv"
        if choice == "3":
            return "txt"
        if choice == "4":
            return "md"
        if choice == "5":
            return None

        print("Invalid choice.")


def export_menu():
    print()
    print("=" * 30)
    print("Export Center")
    print("=" * 30)
    print()
    print("1 AniList")
    print("2 MAL")
    print("3 Telegram")
    print("4 Missing")
    print("5 Retry Queue")
    print("6 Aliases")
    print("7 Search Cache")
    print("8 Back")
    print()

    return input("Choice: ").strip()


async def data_center():
    ensure_exports()

    while True:
        print()
        print("=" * 45)
        print("Data Center")
        print("=" * 45)
        print()
        print("1. Export")
        print("2. Import")
        print("3. Backup")
        print("4. Restore")
        print("5. Back")
        print()

        choice = input("Choice: ").strip()

        if choice == "1":
            await export_center()
        elif choice == "2":
            import_center()
        elif choice == "3":
            backup_center()
        elif choice == "4":
            restore_center()
        elif choice == "5":
            break
        else:
            print("Invalid choice.")


async def export_center():
    while True:
        choice = export_menu()

        if choice == "1":
            export_anilist_library()
        elif choice == "2":
            export_mal_library()
        elif choice == "3":
            await export_telegram_titles()
        elif choice == "4":
            export_missing_anime()
        elif choice == "5":
            export_retry_queue()
        elif choice == "6":
            export_aliases()
        elif choice == "7":
            export_search_cache()
        elif choice == "8":
            break
        else:
            print("Invalid choice.")


def export_anilist_library():
    from anilist import get_completed_anime

    anime = sorted(
        get_completed_anime(),
        key=lambda item: item.get("title", "").lower()
    )
    rows = _library_rows(anime)
    headers = ["Title", "AniList ID", "MAL ID", "Episodes", "Status", "Progress"]
    txt_lines = [item.get("title", "") for item in anime]

    _export_dataset("anilist_library", anime, rows, headers, txt_lines=txt_lines)


def export_mal_library():
    from mal import get_completed_mal_anime

    anime = sorted(
        get_completed_mal_anime(),
        key=lambda item: item.get("title", "").lower()
    )
    rows = _library_rows(anime)
    headers = ["Title", "AniList ID", "MAL ID", "Episodes", "Status", "Progress"]
    txt_lines = [item.get("title", "") for item in anime]

    _export_dataset("mal_library", anime, rows, headers, txt_lines=txt_lines)


async def export_telegram_titles():
    from telegram_client import client

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
            with open(root_report, "r", encoding="utf-8") as f:
                report = json.load(f)

    if not report:
        print("No missing anime report found. Run Compare first.")
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


def import_center():
    ensure_exports()

    while True:
        print()
        print("=" * 30)
        print("Import Center")
        print("=" * 30)
        print()
        print("1. aliases.json")
        print("2. retry_queue.json")
        print("3. search_cache.json")
        print("4. settings.json")
        print("5. telegram.txt")
        print("6. Custom file")
        print("7. Back")
        print()

        choice = input("Choice: ").strip()

        if choice == "1":
            import_json_file(ALIASES_FILE, merge=True)
        elif choice == "2":
            import_json_file(RETRY_FILE, merge=True)
        elif choice == "3":
            import_json_file(CACHE_FILE, merge=True)
        elif choice == "4":
            import_json_file(SETTINGS_FILE, merge=False)
        elif choice == "5":
            import_telegram_txt("telegram.txt")
        elif choice == "6":
            import_custom_file()
        elif choice == "7":
            break
        else:
            print("Invalid choice.")


def backup_center():
    created = 0

    for filename in DATA_FILES:
        if data_file(filename).exists():
            backup_file(filename)
            created += 1

    print(f"Backed up {created} data file(s).")


def restore_center():
    backups = sorted(Path(BACKUP_DIR).glob("*.json"), reverse=True)

    if not backups:
        print("No backups found.")
        return

    print()
    print("=" * 30)
    print("Restore Backup")
    print("=" * 30)
    print()

    for index, path in enumerate(backups, 1):
        print(f"{index}. {path.name}")

    print(f"{len(backups) + 1}. Back")
    print()

    choice = input("Choice: ").strip()

    if not choice.isdigit():
        print("Invalid choice.")
        return

    index = int(choice)
    if index == len(backups) + 1:
        return
    if index < 1 or index > len(backups):
        print("Invalid choice.")
        return

    backup = backups[index - 1]
    original = _original_backup_name(backup.name)

    if not original:
        print("Could not detect original filename.")
        return

    confirm = input(f"Restore {backup.name} to data/{original}? (y/n): ").strip().lower()
    if confirm != "y":
        print("Restore cancelled.")
        return

    if data_file(original).exists():
        backup_file(original)

    copy2(backup, data_file(original))
    print(f"Restored data/{original}.")


def import_json_file(filename, merge=False, path=None):
    if path is None:
        path = _ask_import_path(filename)

    if not path:
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            incoming = json.load(f)
    except Exception as exc:
        print(f"Could not read JSON: {exc}")
        return

    current = load_json(filename, [] if isinstance(incoming, list) else {})

    if merge:
        mode = input("Merge with current data? (Y=merge, N=replace, C=cancel): ").strip().lower()
        if mode == "c":
            print("Import cancelled.")
            return
        replace = mode == "n"
    else:
        confirm = input(f"Replace data/{filename}? (y/n): ").strip().lower()
        if confirm != "y":
            print("Import cancelled.")
            return
        replace = True

    backup_file(filename)

    if replace:
        save_json(filename, incoming)
        print(f"Imported {filename}.")
        return

    merged = _merge_data(current, incoming)
    save_json(filename, merged)
    print(f"Merged import into {filename}.")


def import_telegram_txt(filename, path=None):
    if path is None:
        path = _ask_import_path(filename)

    if not path:
        return

    with open(path, "r", encoding="utf-8") as f:
        titles = [line.strip() for line in f if line.strip()]

    if not titles:
        print("No titles found.")
        return

    queue = load_json(RETRY_FILE, [])
    added = 0

    for title in titles:
        if title in queue:
            continue
        queue.append(title)
        added += 1

    backup_file(RETRY_FILE)
    save_json(RETRY_FILE, queue)
    print(f"Imported {added} title(s) into retry_queue.json.")


def import_custom_file():
    raw = input("File path: ").strip().strip('"')
    if not raw:
        return

    path = Path(raw)
    if not path.exists():
        path = EXPORT_PATH / raw

    if not path.exists():
        print("File not found.")
        return

    name = path.name.lower()

    if name == ALIASES_FILE:
        import_json_file(ALIASES_FILE, merge=True, path=path)
    elif name == RETRY_FILE:
        import_json_file(RETRY_FILE, merge=True, path=path)
    elif name == CACHE_FILE:
        import_json_file(CACHE_FILE, merge=True, path=path)
    elif name == SETTINGS_FILE:
        import_json_file(SETTINGS_FILE, merge=False, path=path)
    elif name.endswith(".txt"):
        import_telegram_txt(path.name, path=path)
    else:
        print("Supported custom imports: aliases, retry queue, cache, settings, or TXT titles.")


def _export_dataset(name, json_data, rows, headers, txt_lines=None):
    fmt = choose_format()

    if not fmt:
        print("Export cancelled.")
        return

    if fmt == "json":
        path = export_json(name, json_data)
    elif fmt == "csv":
        path = export_csv(name, rows, headers)
    elif fmt == "txt":
        path = export_txt(name, txt_lines if txt_lines is not None else rows)
    else:
        path = export_markdown(name, rows, headers)

    print(f"Exported to {path}")


def _alias_rows(aliases):
    rows = []

    for alias, data in sorted(aliases.items()):
        rows.append({
            "Alias": alias,
            "Title": data.get("title", ""),
            "AniList ID": data.get("id", ""),
            "MAL ID": data.get("idMal", ""),
            "Episodes": data.get("episodes", ""),
        })

    return rows


def _library_rows(anime_list):
    rows = []

    for anime in anime_list:
        rows.append({
            "Title": anime.get("title", ""),
            "AniList ID": anime.get("id", ""),
            "MAL ID": anime.get("idMal", ""),
            "Episodes": anime.get("episodes", ""),
            "Status": anime.get("status", ""),
            "Progress": anime.get("progress", ""),
        })

    return rows


def _alias_txt_lines(aliases):
    lines = []

    for alias, data in sorted(aliases.items()):
        lines.append(
            f"{alias}\n->\n{data.get('title', '')}\n----------------"
        )

    return lines


def _anime_fields(item):
    if not item:
        return "", "", "", ""

    if isinstance(item, list):
        item = item[0][1] if item and isinstance(item[0], list) and len(item[0]) > 1 else item[0]

    title = ""
    if isinstance(item, dict):
        raw_title = item.get("title", "")
        if isinstance(raw_title, dict):
            title = (
                raw_title.get("english")
                or raw_title.get("romaji")
                or raw_title.get("native")
                or ""
            )
        else:
            title = raw_title

        return (
            title,
            item.get("id", ""),
            item.get("idMal", ""),
            item.get("episodes", ""),
        )

    return str(item), "", "", ""


def _txt_lines(data):
    if isinstance(data, list):
        lines = []
        for item in data:
            if isinstance(item, dict):
                lines.append(item.get("Title") or item.get("Alias") or str(item))
            else:
                lines.append(str(item))
        return lines

    if isinstance(data, dict):
        return [f"{key}: {value}" for key, value in data.items()]

    return [str(data)]


def _merge_data(current, incoming):
    if isinstance(current, dict) and isinstance(incoming, dict):
        merged = dict(current)
        merged.update(incoming)
        return merged

    if isinstance(current, list) and isinstance(incoming, list):
        merged = list(current)
        for item in incoming:
            if item not in merged:
                merged.append(item)
        return merged

    return incoming


def _ask_import_path(default_name):
    raw = input(f"Import file [{default_name}]: ").strip().strip('"')
    path = Path(raw or default_name)

    if not path.exists():
        path = EXPORT_PATH / path

    if not path.exists():
        print("File not found.")
        return None

    return path


def _original_backup_name(filename):
    match = re.match(r"(.+)_\d{8}_\d{6}(\.json)$", filename)
    if not match:
        return None

    return match.group(1) + match.group(2)


def _with_suffix(filename, suffix):
    path = Path(filename)

    if path.suffix:
        return path.name

    return f"{filename}.{suffix}"
