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

from utils.ui import ask, error, success, warning, show_header, show_menu



SETTING_LABELS = {
    "enable_anilist": "Enable AniList Sync",
    "enable_mal": "Enable MyAnimeList Sync",
    "resume_import": "Resume Imports",
    "retry_failed": "Retry Failed Anime",
    "auto_learn_aliases": "Auto Learn Aliases",
    "franchise_sync": "Franchise Sync",
    "use_search_cache": "Use Search Cache",
    "fuzzy_matching": "Fuzzy Matching",
    "interactive_search": "Interactive Search",
    "auto_backup": "Automatic Backup",
    "confirm_before_sync": "Confirm Before Sync",

    # Non-menu/common settings (kept for backwards compatibility)
    "interactive_sync": "Interactive Search",
    "debug": "Debug Mode",
    "search_threshold": "Search Similarity Threshold",
    "search_results": "Maximum Search Results",
    "max_retries": "Maximum Retries",
    "stop_after": "Stop After",
    "stop_after_existing": "Stop After Existing",
    "anilist_per_page": "AniList Page Size",
    "default_status": "AniList Default Status",
    "mal_default_status": "MAL Default Status",
}


# Settings menu definition (grouped) to avoid dumping every key with enumerate/print.
# Format: [(group_title, [(setting_key, setting_label), ...]), ...]
SETTINGS_MENU = [

    (
        "Synchronization",
        [
            ("enable_anilist", "Enable AniList Sync"),
            ("enable_mal", "Enable MyAnimeList Sync"),
            ("resume_import", "Resume Imports"),
            ("retry_failed", "Retry Failed Anime"),
            ("auto_learn_aliases", "Auto Learn Aliases"),
            ("franchise_sync", "Franchise Sync"),
        ],
    ),

    (
        "Search",
        [
            ("use_cache", "Use Search Cache"),
            ("fuzzy_matching", "Fuzzy Matching"),
            ("interactive_search", "Interactive Search"),
        ],
    ),

    (
        "Backup",
        [
            ("auto_backup", "Automatic Backup"),
        ],
    ),

    (
        "User Interface",
        [
            ("confirm_before_sync", "Confirm Before Sync"),
        ],
    ),

    (
        "Advanced",
        [
            ("debug", "Debug Mode"),
            ("search_threshold", "Search Threshold"),
            ("search_results", "Maximum Search Results"),
            ("max_retries", "Maximum Retries"),
            ("anilist_per_page", "AniList Page Size"),
            ("stop_after", "Stop After"),
            ("stop_after_existing", "Stop After Existing"),
            ("default_status", "AniList Default Status"),
            ("mal_default_status", "MAL Default Status"),
        ],
    ),
]



# BASIC_SETTINGS must be right below SETTINGS_MENU.
BASIC_SETTINGS = {
    "enable_anilist",
    "enable_mal",
    "resume_import",
    "retry_failed",
    "auto_learn_aliases",
    "franchise_sync",
    "use_cache",
    "fuzzy_matching",
    "interactive_search",
    "auto_backup",
    "confirm_before_sync",
}

ADVANCED_SETTINGS = {
    "debug",
    "search_threshold",
    "search_results",
    "max_retries",
    "anilist_per_page",
    "stop_after",
    "stop_after_existing",
    "default_status",
    "mal_default_status",
}



# Map flat setting keys to their top-level section in data/settings.json
SETTINGS_KEY_TO_SECTION = {
    # sync
    "enable_anilist": "sync",
    "enable_mal": "sync",
    "resume_import": "sync",
    "retry_failed": "sync",
    "auto_learn_aliases": "sync",
    "franchise_sync": "sync",

    # search
    "use_search_cache": "search",
    "fuzzy_matching": "search",
    "interactive_search": "search",

    # backup
    "auto_backup": "backup",

    # ui
    "confirm_before_sync": "ui",
}


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
        choice = show_menu(
            "Export Format",
            [
                "JSON",
                "CSV",
                "TXT",
                "Markdown",
                "Cancel",
            ],
        )

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

        warning("Invalid choice.")


def export_menu():
    return show_menu(
        "Export Center",
        [
            "AniList",
            "MAL",
            "Telegram",
            "Missing",
            "Retry Queue",
            "Aliases",
            "Search Cache",
            "Back",
        ],
    )


def settings_home():
    while True:
        choice = show_menu(
            "Settings",
            [
                "Basic Settings",
                "Advanced Settings",
                "Back",
            ],
        )

        if choice == "1":
            settings_editor("basic")
            continue

        if choice == "2":
            settings_editor("advanced")
            continue

        if choice == "3":
            return



def settings_editor(mode):
    from settings import load_settings

    settings = load_settings()

    while True:

        title = "Basic Settings" if mode == "basic" else "Advanced Settings"
        show_header(title)
        option_map = {}
        option = 1

        for section, items in SETTINGS_MENU:

            visible_items = []

            for key, label in items:

                if mode == "basic" and key not in BASIC_SETTINGS:
                    continue

                if mode == "advanced" and key not in ADVANCED_SETTINGS:
                    continue

                visible_items.append((key, label))

            if not visible_items:
                continue

            print(f"[ {section} ]")

            for key, label in visible_items:

                option_map[option] = key

                value = None

                if section == "Synchronization":
                    value = settings["sync"][key]
                elif section == "Search":
                    value = settings["search"][key]
                elif section == "Backup":
                    value = settings["backup"][key]
                elif section == "User Interface":
                    value = settings["ui"][key]
                elif section == "Advanced":
                    value = settings.get(key)

                if isinstance(value, bool):
                    value = "ON" if value else "OFF"

                print(f"{option}. {label:<30} {value}")

                option += 1

            print()

        back_option = option
        print("-" * 40)
        print(f"{back_option}. Back")
        print()

        pick = ask()
        if not pick.isdigit():
            warning("Invalid choice.")
            continue

        idx = int(pick)
        if idx == back_option:
            break

        key = option_map.get(idx)
        if not key:
            warning("Invalid choice.")
            continue

        # Determine which nested section the key belongs to and preserve type.
        if key in settings.get("sync", {}):
            section_key = "sync"
        elif key in settings.get("search", {}):
            section_key = "search"
        elif key in settings.get("backup", {}):
            section_key = "backup"
        elif key in settings.get("ui", {}):
            section_key = "ui"
        elif key in settings:
            section_key = None
        else:
            error("Unknown setting key.")
            continue

        if section_key is None:
            old_val = settings[key]
        else:
            old_val = settings[section_key][key]

        # Boolean settings toggle automatically
        if isinstance(old_val, bool):
            if section_key is None:
                settings[key] = not old_val
            else:
                settings[section_key][key] = not old_val

            # Display friendly label
            label = key
            for _, items in SETTINGS_MENU:
                for setting_key, setting_label in items:
                    if setting_key == key:
                        label = setting_label
                        break
                if label != key:
                    break

            save_json(SETTINGS_FILE, settings)

            success(f"{label} -> {'ON' if settings[section_key][key] else 'OFF'}")
            continue

        # Numeric/Text settings still ask for input
        new_val = ask(f"New value for {key}:")

        if isinstance(old_val, int):
            value = int(new_val)

        elif isinstance(old_val, float):
            value = float(new_val)

        else:
            value = new_val

        if section_key is None:
            settings[key] = value
        else:
            settings[section_key][key] = value

        save_json(SETTINGS_FILE, settings)
        success("Saved.")


async def data_center():
    ensure_exports()

    while True:
        choice = show_menu(
            "Tools",
            [
                "Export",
                "Import",
                "Backup",
                "Restore",
                "Alias Manager",
                "Search Cache",
                "Retry Queue",
                "Settings",
                "Back",
            ],
        )

        if choice == "1":
            await export_center()
        elif choice == "2":
            import_center()
        elif choice == "3":
            backup_center()
        elif choice == "4":
            restore_center()
        elif choice == "5":
            from modes.alias_manager import alias_manager
            alias_manager()
        elif choice == "6":
            export_search_cache()
        elif choice == "7":
            from modes.retry_queue import retry_queue_menu
            retry_queue_menu()

        elif choice == "8":
            settings_home()

        elif choice == "9":
            break
        else:
            warning("Invalid choice.")


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
            warning("Invalid choice.")


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
        warning("No missing anime report found. Run Compare first.")
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
        choice = show_menu(
            "Import Center",
            [
                "aliases.json",
                "retry_queue.json",
                "search_cache.json",
                "settings.json",
                "telegram.txt",
                "Custom file",
                "Back",
            ],
        )

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
            warning("Invalid choice.")


def backup_center():
    created = 0

    for filename in DATA_FILES:
        if data_file(filename).exists():
            backup_file(filename)
            created += 1

    success(f"Backed up {created} data file(s).")


def restore_center():
    backups = sorted(Path(BACKUP_DIR).glob("*.json"), reverse=True)

    if not backups:
        warning("No backups found.")
        return

    choice = show_menu(
        "Restore Backup",
        [path.name for path in backups] + ["Back"],
    )

    if not choice.isdigit():
        warning("Invalid choice.")
        return

    index = int(choice)
    if index == len(backups) + 1:
        return
    if index < 1 or index > len(backups):
        warning("Invalid choice.")
        return

    backup = backups[index - 1]
    original = _original_backup_name(backup.name)

    if not original:
        error("Could not detect original filename.")
        return

    confirm = ask(f"Restore {backup.name} to data/{original}? (y/n):").lower()
    if confirm != "y":
        warning("Restore cancelled.")
        return

    if data_file(original).exists():
        backup_file(original)

    copy2(backup, data_file(original))
    success(f"Restored data/{original}.")


def import_json_file(filename, merge=False, path=None):
    if path is None:
        path = _ask_import_path(filename)

    if not path:
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            incoming = json.load(f)
    except Exception as exc:
        error(f"Could not read JSON: {exc}")
        return

    current = load_json(filename, [] if isinstance(incoming, list) else {})

    if merge:
        mode = ask("Merge with current data? (Y=merge, N=replace, C=cancel):").lower()
        if mode == "c":
            warning("Import cancelled.")
            return
        replace = mode == "n"
    else:
        confirm = ask(f"Replace data/{filename}? (y/n):").lower()
        if confirm != "y":
            warning("Import cancelled.")
            return
        replace = True

    backup_file(filename)

    if replace:
        save_json(filename, incoming)
        success(f"Imported {filename}.")
        return

    merged = _merge_data(current, incoming)
    save_json(filename, merged)
    success(f"Merged import into {filename}.")


def import_telegram_txt(filename, path=None):
    if path is None:
        path = _ask_import_path(filename)

    if not path:
        return

    with open(path, "r", encoding="utf-8") as f:
        titles = [line.strip() for line in f if line.strip()]

    if not titles:
        warning("No titles found.")
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
    success(f"Imported {added} title(s) into retry_queue.json.")


def import_custom_file():
    raw = ask("File path:").strip('"')
    if not raw:
        return

    path = Path(raw)
    if not path.exists():
        path = EXPORT_PATH / raw

    if not path.exists():
        error("File not found.")
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
        warning("Supported custom imports: aliases, retry queue, cache, settings, or TXT titles.")


def _export_dataset(name, json_data, rows, headers, txt_lines=None):
    fmt = choose_format()

    if not fmt:
        warning("Export cancelled.")
        return

    if fmt == "json":
        path = export_json(name, json_data)
    elif fmt == "csv":
        path = export_csv(name, rows, headers)
    elif fmt == "txt":
        path = export_txt(name, txt_lines if txt_lines is not None else rows)
    else:
        path = export_markdown(name, rows, headers)

    success(f"Exported to {path}")


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
    raw = ask(f"Import file [{default_name}]:").strip('"')
    path = Path(raw or default_name)

    if not path.exists():
        path = EXPORT_PATH / path

    if not path.exists():
        error("File not found.")
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




