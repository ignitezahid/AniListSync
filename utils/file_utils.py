from pathlib import Path
import json
from utils.constants import DATA_DIR


DATA_PATH = Path(DATA_DIR)


def data_file(name: str) -> Path:
    """
    Returns the full path of a file inside the data folder.
    """
    return DATA_PATH / name


def load_json(filename: str, default=None):
    """
    Load JSON safely.

    Returns default if the file doesn't exist.
    """

    path = data_file(filename)

    if not path.exists():
        return default

    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    except Exception:
        return default


def save_json(filename: str, data):

    path = data_file(filename)

    path.parent.mkdir(parents=True, exist_ok=True)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )


def json_exists(filename: str):

    return data_file(filename).exists()


def delete_json(filename: str):

    path = data_file(filename)

    if path.exists():
        path.unlink()
