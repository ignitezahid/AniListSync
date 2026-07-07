import msvcrt
import sys as _sys
from rich.align import Align
from rich.console import Console
from rich.panel import Panel
from rich.text import Text
from rich.theme import Theme
from rich import box
from rich.table import Table

theme = Theme(
    {
        "title": "bold cyan",
        "success": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "info": "bold blue",
        "menu": "bold white",
        "border": "bright_blue",
    }
)

console = Console(theme=theme)

_theme_pushed = False


def show_header(title: str):
    """Display a consistent screen header."""

    console.print()

    panel = Panel(
        Align.center(f"[title]{title}[/]"),
        border_style=console.get_style("border"),
        box=box.ROUNDED,
        padding=(0, 3),
        expand=False,
    )

    console.print(Align.center(panel))
    console.print()




def show_app_header(version: str, creator: str):
    """Display the AniListSync startup banner."""

    title = Text(justify="center")

    title.append("🎌 AniListSync\n", style="bold bright_cyan")
    title.append(f"Anime Library Manager v{version}\n", style=console.get_style("info"))
    title.append(f"by {creator}", style="dim")

    panel = Panel(
        title,
        border_style=console.get_style("border"),
        box=box.ROUNDED,
        padding=(1, 8),
        expand=False,
    )

    console.print()
    console.print(Align.center(panel))
    console.print()


def success(message: str):
    console.print(f"[success]✓ {message}[/]")


def warning(message: str):
    console.print(f"[warning]⚠ {message}[/]")


def error(message: str):
    console.print(f"[error]✗ {message}[/]")


def info(message: str):
    console.print(f"[info]{message}[/]")


def watcher_ready() -> None:
    """Display that the live watcher is ready for new messages."""

    console.print()
    console.print("[success]🟢 Watching Saved Messages...[/]")
    warning("Press ESC to return.")



def pause():
    """Pause until the user presses ESC."""

    warning("Press ESC to return.")
    while True:
        try:
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b"\x1b":
                    break
        except (EOFError, KeyboardInterrupt):
            break


def ask(prompt: str = "Choice:"):
    """Prompt the user for input."""

    try:
        return console.input(f"[menu]{prompt}[/] ").strip()
    except (EOFError, KeyboardInterrupt):
        return ""



def show_menu(title: str, options: list[str]):
    """Display a menu with numbered options. Empty strings render as blank separators."""

    show_header(title)

    table = Table(
        show_header=False,
        box=None,
        pad_edge=False,
    )

    title_style = console.get_style("title")
    menu_style = console.get_style("menu")
    table.add_column("No", style=title_style, width=3)
    table.add_column("Option", style=menu_style)

    counter = 0
    for option in options:
        if not option:
            table.add_row("", "")
        else:
            counter += 1
            table.add_row(f"{counter}.", option)

    console.print(table)
    console.print()

    return ask()


def show_key_value_table(title: str, data: dict):
    """Display a two-column key/value table."""

    show_header(title)

    table = Table(
        show_header=True,
        header_style=console.get_style("title"),
    )

    table.add_column("Metric", style=console.get_style("menu"))
    table.add_column("Value", justify="right", style=console.get_style("success"))

    for key, value in data.items():
        table.add_row(key, str(value))

    console.print(table)



def show_list_table(title: str, items: list[str], column_name: str = "Item"):
    """Display a numbered list in a table."""

    show_header(title)

    table = Table(
        show_header=True,
        header_style=console.get_style("title"),
    )

    table.add_column("No", justify="right", style=console.get_style("title"), width=4)
    table.add_column(column_name, style=console.get_style("menu"))

    for i, item in enumerate(items, start=1):
        table.add_row(str(i), item)

    console.print(table)


def reload_theme():
    """Apply theme from loaded theme plugins and set terminal background."""
    global _theme_pushed
    from core.plugin_loader import plugin_manager
    if _theme_pushed:
        console.pop_theme()
        _theme_pushed = False
    plugin_themes = plugin_manager.get_theme()
    if plugin_themes:
        base = dict(theme.styles)
        base.update(plugin_themes)
        console.push_theme(Theme(base), inherit=False)
        _theme_pushed = True

    _set_terminal_bg(plugin_manager)


def _set_terminal_bg(pm):
    """Set terminal background via OSC escape if a theme plugin defines bg_color."""
    bg = None
    for pid in list(pm._plugins.keys()):
        if not pm.is_enabled(pid):
            continue
        manifest = pm._manifests.get(pid)
        if manifest and manifest.get("type") == "theme":
            inst = pm._plugins.get(pid)
            if inst and hasattr(inst, "bg_color"):
                bg = inst.bg_color
                break
    try:
        if bg and console.color_system:
            _sys.stdout.write(f"\x1b]11;{bg}\x1b\\")
        elif console.color_system:
            _sys.stdout.write("\x1b]111\x1b\\")
        if bg or console.color_system:
            _sys.stdout.flush()
    except Exception:
        pass
