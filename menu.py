from datetime import datetime, timedelta, timezone
from pathlib import Path

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
from mal import (
    test_connection as test_mal,
)
from utils.constants import BACKUP_DIR, EXPORT_DIR, RETRY_FILE
from utils.file_utils import load_json
from core.plugin_loader import plugin_manager


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
        now = datetime.now(timezone.utc) if dt.tzinfo else datetime.now()
        diff = now - dt
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return "Just now"
        if seconds < 3600:
            m = seconds // 60
            return f"{m} min ago"
        if seconds < 86400:
            h = seconds // 3600
            return f"{h}h ago"
        d = seconds // 86400
        return f"{d}d ago"
    except Exception:
        return None


def show_dashboard():
    header_panel = Panel(
        Text(justify="center")
        .append("\n🎌 AniListSync\n", style="bold bright_cyan")
        .append(f"Anime Library Manager v{VERSION}\n", style=console.get_style("info"))
        .append(f"by {CREATOR}", style="dim"),
        border_style=console.get_style("border"),
        box=box.ROUNDED,
        padding=(1, 8),
        expand=False,
    )
    console.print()
    console.print(Align.center(header_panel))
    console.print()

    anilist_status, anilist_user = _connection_status(test_anilist)
    if anilist_user:
        console.print(f"  Connected as [info]{anilist_user}[/]")
    console.print()

    mal_status, _ = _connection_status(test_mal)
    telegram_status = _telegram_status()
    state = _load_state()
    anilist_count = state.get("anilist_entries", "?")
    mal_count = state.get("mal_entries", "?")

    from settings import get_setting

    import re as _re

    def _visible_width(s: str) -> int:
        plain = _re.sub(r"\[/?\w+(?: \w+=[^\]]*)?\]", "", s)
        width = 0
        for ch in plain:
            if ord(ch) > 0xFFFF:
                width += 2
            elif ord(ch) > 0x7F:
                width += 2
            else:
                width += 1
        return width

    def _pad_line(line: str, target: int) -> str:
        needed = target - _visible_width(line)
        if needed > 0:
            return line + " " * needed
        return line

    conn_lines = [
        f"  Telegram      {telegram_status}",
        f"  AniList       {anilist_status}",
        f"  MyAnimeList   {mal_status}",
    ]
    if get_setting("automation_enabled"):
        mins = get_setting("automation_interval_minutes", 30)
        if mins < 60:
            interval = f"{mins} min"
        elif mins == 60:
            interval = "1 hour"
        else:
            interval = f"{mins // 60}h"
        conn_lines.append(f"  Automation    [green]🟢 Active ({interval})[/]")
    else:
        conn_lines.append("  Automation    [dim]🔴 Disabled[/]")

    retry_queue = load_json(RETRY_FILE, [])
    backup_count = len(list(Path(BACKUP_DIR).glob("*")))
    export_count = len(list(Path(EXPORT_DIR).glob("*")))

    collections = load_json("collections.json", {})
    collection_count = len(collections)

    lib_lines = [
        f"  AniList Entries   {anilist_count}",
        f"  MAL Entries       {mal_count}",
        f"  Aliases           {len(ALIASES)}",
        f"  Collections       {collection_count}",
    ]

    storage_lines = [
        f"  Search Cache      {len(SEARCH_CACHE)}",
        f"  Retry Queue        {len(retry_queue)}",
        f"  Exports            {export_count}",
        f"  Backups            {backup_count}",
        f"  Plugins            {len(plugin_manager.get_plugins())}",
    ]

    last_sync = _format_last_sync(state)
    sync_lines: list[str] = []
    if last_sync:
        sync_lines.append(f"  Last Sync         {last_sync}")
        if get_setting("automation_enabled"):
            mins = get_setting("automation_interval_minutes", 30)
            last_iso = state.get("last_sync", "")
            if last_iso:
                try:
                    last_dt = datetime.fromisoformat(last_iso)
                    next_dt = last_dt + timedelta(minutes=mins)
                    now = datetime.now(timezone.utc) if last_dt.tzinfo else datetime.now()
                    if next_dt > now:
                        remaining = next_dt - now
                        total_secs = int(remaining.total_seconds())
                        if total_secs < 60:
                            next_str = "Soon"
                        elif total_secs < 3600:
                            next_str = f"{total_secs // 60} min"
                        else:
                            hours = total_secs // 3600
                            mins_left = (total_secs % 3600) // 60
                            next_str = f"{hours}h {mins_left}m"
                    else:
                        next_str = "Now"
                    sync_lines.append(f"  Next Sync         {next_str}")
                except Exception:
                    pass
        from modes.tools import _compute_health_score
        try:
            hp, _, _ = _compute_health_score()
            color = "🟢" if hp >= 80 else ("🟡" if hp >= 50 else "🔴")
            sync_lines.append(f"  Health            {color} {hp}%")
        except Exception:
            pass

    all_lines = conn_lines + lib_lines + storage_lines + sync_lines
    max_width = max(_visible_width(line) for line in all_lines) if all_lines else 0

    conn_text = "\n".join(_pad_line(line, max_width) for line in conn_lines)
    console.print(Panel(conn_text, title="Connections", border_style=console.get_style("border"), box=box.ROUNDED, padding=(0, 1), expand=False))

    lib_text = "\n".join(_pad_line(line, max_width) for line in lib_lines)
    console.print(Panel(lib_text, title="Library", border_style=console.get_style("border"), box=box.ROUNDED, padding=(0, 1), expand=False))

    storage_text = "\n".join(_pad_line(line, max_width) for line in storage_lines)
    console.print(Panel(storage_text, title="Storage", border_style=console.get_style("border"), box=box.ROUNDED, padding=(0, 1), expand=False))

    if last_sync:
        sync_text = "\n".join(_pad_line(line, max_width) for line in sync_lines)
        console.print(Panel(sync_text, title="Sync", border_style=console.get_style("border"), box=box.ROUNDED, padding=(0, 1), expand=False))

    console.print()


def show_main_menu():
    return show_menu(
        "Main Menu",
        [
            "🔄  Sync",
            "🤖  Automation",
            "",
            "🔎  Search",
            "📚  Library Search",
            "🗂   Collections",
            "",
            "📊  Statistics",
            "",
            "🔍  Compare",
            "🛠   Repair",
            "🚀  Bulk Operations",
            "",
            "🧩  Plugins",
            "",
            "📋  About",
            "",
            "🧰  Tools",
            "🚪  Exit",
        ],
    )
