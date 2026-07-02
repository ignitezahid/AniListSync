from datetime import datetime, timezone
from pathlib import Path

from rich.table import Table
from rich.panel import Panel
from rich.align import Align
from rich.text import Text
from rich import box

from version import VERSION, CREATOR
from utils.ui import console, show_menu
from anilist import (
    ALIASES,
    SEARCH_CACHE,
    test_connection as test_anilist,
)
from mal import test_connection as test_mal
from utils.constants import BACKUP_DIR, EXPORT_DIR, RETRY_FILE
from utils.file_utils import load_json


def _connection_status(test_fn):
    try:
        result = test_fn()
        if result:
            return "🟢 Connected", result if isinstance(result, str) else None
        return "🔴 Disconnected", None
    except Exception:
        return "🔴 Disconnected", None


def _telegram_status():
    session_file = Path("telegram_session.session")
    if session_file.exists():
        return "🟢 Connected"
    return "🔴 Disconnected"


def _load_state():
    try:
        import json
        with open("state.json", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def _format_last_sync(state):
    iso_str = state.get("last_sync", "")
    if not iso_str:
        return None
    try:
        dt = datetime.fromisoformat(iso_str)
        day = dt.strftime("%d").lstrip("0")
        return dt.strftime(f"{day} %b %Y %I:%M %p")
    except Exception:
        return None


def show_dashboard():
    header_panel = Panel(
        Text(justify="center")
        .append("\n🎌 AniListSync\n", style="bold bright_cyan")
        .append(f"Anime Library Manager v{VERSION}\n", style="bold white")
        .append(f"by {CREATOR}", style="dim"),
        border_style="bright_blue",
        box=box.ROUNDED,
        padding=(1, 8),
        expand=False,
    )
    console.print()
    console.print(Align.center(header_panel))
    console.print()

    anilist_status, anilist_user = _connection_status(test_anilist)
    if anilist_user:
        console.print(f"  Connected as [bold cyan]{anilist_user}[/]")
    console.print()

    separator = f"  [dim]{'─' * 50}[/]"
    console.print(separator)
    console.print()

    mal_status, _ = _connection_status(test_mal)
    telegram_status = _telegram_status()

    conn_table = Table(show_header=False, box=None, pad_edge=False)
    conn_table.add_column("", style="bold white", width=16)
    conn_table.add_column("", style="bold")
    conn_table.add_row("Telegram", telegram_status)
    conn_table.add_row("AniList", anilist_status)
    conn_table.add_row("MyAnimeList", mal_status)
    console.print(conn_table)

    console.print()
    console.print(separator)
    console.print()

    retry_queue = load_json(RETRY_FILE, [])
    backup_count = len(list(Path(BACKUP_DIR).glob("*")))
    export_count = len(list(Path(EXPORT_DIR).glob("*")))

    stats_table = Table(show_header=False, box=None, pad_edge=False)
    stats_table.add_column("", style="white", width=18)
    stats_table.add_column("", justify="right", style="green")
    stats_table.add_row("Aliases", str(len(ALIASES)))
    stats_table.add_row("Search Cache", str(len(SEARCH_CACHE)))
    stats_table.add_row("Retry Queue", str(len(retry_queue)))
    stats_table.add_row("Exports", str(export_count))
    stats_table.add_row("Backups", str(backup_count))
    console.print(stats_table)

    console.print()
    console.print(separator)
    console.print()

    state = _load_state()
    anilist_count = state.get("anilist_entries", "?")
    mal_count = state.get("mal_entries", "?")

    entry_table = Table(show_header=False, box=None, pad_edge=False)
    entry_table.add_column("", style="white", width=18)
    entry_table.add_column("", justify="right", style="green")
    entry_table.add_row("AniList Entries", str(anilist_count))
    entry_table.add_row("MAL Entries", str(mal_count))
    console.print(entry_table)

    console.print()
    console.print(separator)
    console.print()

    last_sync = _format_last_sync(state)
    if last_sync:
        sync_table = Table(show_header=False, box=None, pad_edge=False)
        sync_table.add_column("", style="white", width=18)
        sync_table.add_column("", style="green")
        sync_table.add_row("Last Sync", last_sync)
        console.print(sync_table)
        console.print()


def show_main_menu():
    return show_menu(
        "Main Menu",
        [
            "🔄  Sync",
            "🔎  Search",
            "📚  Library Search",
            "🔍  Compare",
            "🛠  Repair",
            "🧰  Tools",
            "📊  Statistics",
            "🚪  Exit",
        ],
    )