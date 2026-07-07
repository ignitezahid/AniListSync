import json
from pathlib import Path

from utils.backup import backup_file
from utils.constants import ALIASES_FILE, CACHE_FILE, RETRY_FILE, SETTINGS_FILE
from utils.file_utils import load_json, save_json
from utils.ui import ask, error, success, warning, show_menu
from utils.menu_keys import *  # noqa: F405

from .common import EXPORT_PATH, _merge_data, ensure_exports


def _ask_import_path(default_name):
    raw = ask(f"Import file [{default_name}]:").strip('"')
    path = Path(raw or default_name)
    if not path.exists():
        path = EXPORT_PATH / path
    if not path.exists():
        error("File not found.")
        return None
    return path


def import_json_file(filename, merge=False, path=None):
    if path is None:
        path = _ask_import_path(filename)
    if not path:
        return
    try:
        with open(path, encoding="utf-8") as f:
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
    with open(path, encoding="utf-8") as f:
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
    raw = ask('File path:').strip('"')
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
        if choice == IMPORT_ALIASES:
            import_json_file(ALIASES_FILE, merge=True)
        elif choice == IMPORT_RETRY:
            import_json_file(RETRY_FILE, merge=True)
        elif choice == IMPORT_CACHE:
            import_json_file(CACHE_FILE, merge=True)
        elif choice == IMPORT_SETTINGS:
            import_json_file(SETTINGS_FILE, merge=False)
        elif choice == IMPORT_TELEGRAM:
            import_telegram_txt("telegram.txt")
        elif choice == IMPORT_CUSTOM:
            import_custom_file()
        elif choice == IMPORT_BACK:
            break
        else:
            warning("Invalid choice.")
