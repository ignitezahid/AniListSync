from pathlib import Path
from shutil import copy2
from datetime import datetime
from utils.constants import BACKUP_DIR, DATA_DIR
from core.plugin_loader import plugin_manager

DATA_PATH = Path(DATA_DIR)
BACKUP_PATH = Path(BACKUP_DIR)


def backup_file(filename):

    BACKUP_PATH.mkdir(exist_ok=True)

    source = DATA_PATH / filename

    if not source.exists():
        return

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    destination = BACKUP_PATH / (
        f"{source.stem}_{timestamp}{source.suffix}"
    )

    copy2(source, destination)
    plugin_manager.call_hook("on_backup", str(destination))
