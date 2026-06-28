from utils.file_utils import load_json
from utils.constants import SETTINGS_FILE

settings = load_json(
    SETTINGS_FILE,
    {}
)
