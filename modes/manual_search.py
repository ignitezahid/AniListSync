from rich.progress import BarColumn, Progress, TextColumn
from rich.table import Column

from utils.ui import show_header, ask, success, warning, pause, console
from sync import interactive_search, add_selected_anime


def manual_search():
    show_header("Search")

    while True:

        title = ask("Search (Enter to return):")

        if not title:
            warning("Cancelled.")
            return

        selected_anime = interactive_search(title)

        if not selected_anime:
            warning("Cancelled.")
            return

        with Progress(
            TextColumn("[progress.description]{task.description:<50}", table_column=Column(width=52)),
            BarColumn(),
            TextColumn(" {task.completed:>4.0f}/{task.total}"),
            console=console,
        ) as progress:
            task = progress.add_task("Adding:", total=len(selected_anime))

            for anime in selected_anime:
                progress.update(task, description=f"Adding:\n{anime['title']['romaji']}")
                if add_selected_anime(anime):
                    success(f"Added: {anime['title']['romaji']}")
                progress.advance(task)

        console.print()
