from pathlib import Path
import sys

from utils.file_utils import json_exists, load_json, save_json


def startup_checks():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    folders = [
        "data",
        "logs",
        "exports",
        "backups",
    ]

    for folder in folders:
        Path(folder).mkdir(
            exist_ok=True
        )

        print(
            f"✓ {folder}"
        )

    required_files = [
        "settings.json",
        "aliases.json",
        "search_cache.json",
        "retry_queue.json",
        "resume.json",
    ]

    for filename in required_files:
        data = load_json(
            filename,
            {}
        )

        if not json_exists(filename):
            save_json(
                filename,
                data
            )
