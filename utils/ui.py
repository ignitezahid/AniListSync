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
    }
)

console = Console(theme=theme)


def show_header(title: str):
    """Display a consistent screen header."""

    console.print()

    panel = Panel(
        Align.center(f"[bold cyan]{title}[/bold cyan]"),
        border_style="bright_blue",
        box=box.ROUNDED,
        padding=(0, 3),
        expand=False,
    )

    console.print(Align.center(panel))
    console.print()


from rich.text import Text


def show_app_header(version: str, creator: str):
    """Display the AniListSync startup banner."""

    title = Text(justify="center")

    title.append("🎌 AniListSync\n", style="bold bright_cyan")
    title.append(f"Anime Library Manager v{version}\n", style="bold white")
    title.append(f"by {creator}", style="dim")

    panel = Panel(
        title,
        border_style="bright_blue",
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
    console.print("[bold green]🟢 Watching Saved Messages...[/]")



def pause():
    """Pause until the user presses Enter."""

    console.input("\n[bold green]Press Enter to continue...[/]")


def ask(prompt: str = "Choice:"):
    """Prompt the user for input."""

    return console.input(f"[bold green]{prompt}[/] ").strip()



def show_menu(title: str, options: list[str]):
    """Display a menu with numbered options."""

    show_header(title)

    table = Table(
        show_header=False,
        box=None,
        pad_edge=False,
    )

    table.add_column("No", style="bold cyan", width=3)
    table.add_column("Option", style="white")

    for index, option in enumerate(options, start=1):
        table.add_row(f"{index}.", option)

    console.print(table)
    console.print()

    return ask()


def show_key_value_table(title: str, data: dict):
    """Display a two-column key/value table."""

    show_header(title)

    table = Table(
        show_header=True,
        header_style="bold cyan",
    )

    table.add_column("Metric", style="white")
    table.add_column("Value", justify="right", style="green")

    for key, value in data.items():
        table.add_row(key, str(value))

    console.print(table)



def show_list_table(title: str, items: list[str], column_name: str = "Item"):
    """Display a numbered list in a table."""

    show_header(title)

    table = Table(
        show_header=True,
        header_style="bold cyan",
    )

    table.add_column("No", justify="right", style="cyan", width=4)
    table.add_column(column_name, style="white")

    for i, item in enumerate(items, start=1):
        table.add_row(str(i), item)

    console.print(table)