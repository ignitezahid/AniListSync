import re
from pathlib import Path
from shutil import copy2

from utils.backup import backup_file
from utils.constants import BACKUP_DIR
from utils.file_utils import data_file
from utils.ui import ask, error, success, warning, show_menu

from core.plugin_loader import plugin_manager
from .common import DATA_FILES


def _original_backup_name(filename):
    match = re.match(r"(.+)_\d{8}_\d{6}(\.json)$", filename)
    if not match:
        return None
    return match.group(1) + match.group(2)


def backup_center():
    created = 0
    for filename in DATA_FILES:
        if data_file(filename).exists():
            backup_file(filename)
            created += 1
    success(f"Backed up {created} data file(s).")


def _clean_old_backups(keep: int = 50):
    path = Path(BACKUP_DIR)
    if not path.is_dir():
        warning("No backup directory found.")
        return
    backups = sorted(path.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    if len(backups) <= keep:
        success(f"Only {len(backups)} backups, nothing to clean.")
        return
    to_remove = backups[keep:]
    for b in to_remove:
        try:
            b.unlink()
        except Exception:
            pass
    success(f"Removed {len(to_remove)} old backups, kept {keep}.")


def restore_center():
    backups = sorted(Path(BACKUP_DIR).glob("*"), reverse=True)
    if not backups:
        warning("No backups found.")
        return
    choice = show_menu("Restore Backup", [path.name for path in backups] + ["Back"])
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
    plugin_manager.call_hook("on_restore", str(backup))
