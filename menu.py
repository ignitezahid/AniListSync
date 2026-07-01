from pathlib import Path

from rich.table import Table
from rich.panel import Panel
from rich.align import Align
from rich import box

from version import VERSION, CREATOR
from utils.ui import console, show_app_header, show_menu
from anilist import ALIASES, SEARCH_CACHE, test_connection as test_anilist
from mal import test_connection as test_mal
from utils.constants import RETRY_FILE
from utils.file_utils import load_json


def _connection_status(test_fn):
    try:
        if test_fn():
            return "Connected ✅"
        return "Disconnected ❌"
    except Exception:
        return "Disconnected ❌"


def _telegram_status():
    session_file = Path("telegram_session.session")
    return "Connected ✅" if session_file.exists() else "Disconnected ❌"


def show_dashboard():
    show_app_header(VERSION, CREATOR)

    conn_table = Table(show_header=False, box=None, pad_edge=False)
    conn_table.add_column("Service", style="bold white", width=12)
    conn_table.add_column("Status", style="bold")

    anilist_status = _connection_status(test_anilist)
    mal_status = _connection_status(test_mal)
    telegram_status = _telegram_status()

    conn_table.add_row("AniList", anilist_status)
    conn_table.add_row("MAL", mal_status)
    conn_table.add_row("Telegram", telegram_status)

    console.print(conn_table)
    console.print()

    retry_queue = load_json(RETRY_FILE, [])

    stats_table = Table(show_header=False, box=None, pad_edge=False)
    stats_table.add_column("Metric", style="white")
    stats_table.add_column("Value", justify="right", style="green")

    stats_table.add_row("Aliases", str(len(ALIASES)))
    stats_table.add_row("Search Cache", str(len(SEARCH_CACHE)))
    stats_table.add_row("Retry Queue", str(len(retry_queue)))

    console.print(stats_table)
    console.print()

    separator = Panel(
        Align.center(""),
        border_style="bright_blue",
        box=box.MINIMAL,
        padding=(0, 0),
        expand=False,
        width=42,
    )
    console.print(Align.center(separator))
    console.print()


def show_main_menu():
    return show_menu(
        "Main Menu",
        [
            "🔄  Sync",
            "🔎  Search",
            "🔍  Compare",
            "🛠  Repair",
            "🧰  Tools",
            "📊  Statistics",
            "🚪  Exit",
        ],
    )