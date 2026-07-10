from pathlib import Path
import sys

from utils.file_utils import json_exists, load_json, save_json


def _is_placeholder(val, placeholder=None):
    if val is None:
        return True
    if isinstance(val, int) and val == 0:
        return True
    if isinstance(val, str):
        if not val or val.startswith("your_"):
            return True
        if placeholder and val == placeholder:
            return True
    return False


def _config_wizard():
    print()
    print("  [First Run Setup]")
    print("  It looks like your config.py still has placeholder values.")
    print("  Let's set them up now.")
    print()

    config_path = Path("config.py")
    lines = config_path.read_text(encoding="utf-8").splitlines()
    new_lines = list(lines)
    changed = False

    current = {}
    try:
        from config import API_ID, API_HASH, MAL_CLIENT_ID, MAL_CLIENT_SECRET, ANILIST_TOKEN
        current = dict(API_ID=API_ID, API_HASH=API_HASH,
                       MAL_CLIENT_ID=MAL_CLIENT_ID,
                       MAL_CLIENT_SECRET=MAL_CLIENT_SECRET,
                       ANILIST_TOKEN=ANILIST_TOKEN)
    except Exception:
        pass

    prompts = [
        ("API_ID", "Telegram API ID (integer)", None),
        ("API_HASH", "Telegram API Hash", None),
        ("MAL_CLIENT_ID", "MyAnimeList Client ID", None),
        ("MAL_CLIENT_SECRET", "MyAnimeList Client Secret", None),
        ("ANILIST_TOKEN", "AniList Access Token", None),
    ]

    for key, label, placeholder in prompts:
        val = current.get(key)
        if not _is_placeholder(val, placeholder):
            continue
        try:
            inp = input(f"  {label}: ").strip()
            if not inp:
                continue
            changed = True
            for i, line in enumerate(new_lines):
                stripped = line.strip()
                if stripped.startswith(key) and "=" in stripped:
                    old_val = stripped.split("=", 1)[1].strip().strip(",")
                    if isinstance(val, int):
                        new_lines[i] = line.replace(old_val, inp)
                    else:
                        new_lines[i] = line.replace(old_val, f'"{inp}"')
                    break
        except (EOFError, KeyboardInterrupt):
            print()
            return changed

    if changed:
        config_path.write_text("\n".join(new_lines), encoding="utf-8")
        print("  Config saved to config.py")
    return changed


def startup_checks():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    folders = ["data", "logs", "exports", "backups"]

    for folder in folders:
        Path(folder).mkdir(exist_ok=True)

    required_files = [
        "settings.json",
        "aliases.json",
        "search_cache.json",
        "retry_queue.json",
        "resume.json",
    ]

    for filename in required_files:
        data = load_json(filename, {})
        if not json_exists(filename):
            save_json(filename, data)

    config_path = Path("config.py")
    if not config_path.exists():
        example_path = Path("config.example.py")
        if example_path.exists():
            import shutil
            shutil.copy(str(example_path), str(config_path))
            print("  [OK] config.py created from config.example.py")

    if config_path.exists():
        try:
            from config import API_ID, API_HASH, MAL_CLIENT_ID, MAL_CLIENT_SECRET, ANILIST_TOKEN
            placeholders = (
                _is_placeholder(API_ID) or
                _is_placeholder(API_HASH) or
                _is_placeholder(ANILIST_TOKEN) or
                _is_placeholder(MAL_CLIENT_ID) or
                _is_placeholder(MAL_CLIENT_SECRET)
            )
            if placeholders:
                try:
                    val = input("  Config has placeholder values. Run setup now? (Y/n): ").strip().lower()
                    if val != "n":
                        _config_wizard()
                except (EOFError, KeyboardInterrupt):
                    pass
        except Exception:
            pass
