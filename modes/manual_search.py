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
            pause()
            return

        for anime in selected_anime:
            if add_selected_anime(anime):
                success(f"Added: {anime['title']['romaji']}")

        console.print()
