from anilist import get_completed_anime
from utils.file_utils import data_file, save_json
from utils.ui import ask, console, pause, show_header

HISTORY_FILE = "search_history.json"
MAX_HISTORY = 5
STATUS_MAP = {
    "1": "CURRENT",
    "2": "COMPLETED",
    "3": "PLANNING",
    "4": "DROPPED",
}
STATUS_LABELS = {
    "CURRENT": "Watching",
    "COMPLETED": "Completed",
    "PLANNING": "Planning",
    "DROPPED": "Dropped",
}


def _load_history():
    try:
        import json
        path = data_file(HISTORY_FILE)
        if path.exists():
            with open(path) as f:
                return json.load(f)
    except Exception:
        pass
    return []


def _save_history(history):
    try:
        save_json(HISTORY_FILE, history)
    except Exception:
        pass


def _add_to_history(query):
    history = _load_history()
    if query in history:
        history.remove(query)
    history.insert(0, query)
    _save_history(history[:MAX_HISTORY])


def library_search():
    while True:
        show_header("Library Search")

        history = _load_history()
        if history:
            console.print("[bold cyan]Recent Searches[/]")
            for i, h in enumerate(history, 1):
                console.print(f"  {i}. {h}")
            console.print()

        query = ask("Search (Enter to go back):")
        if not query:
            return

        query_lower = query.lower()

        anime_list = get_completed_anime()

        matches = []
        for anime in anime_list:
            title = anime.get("title") or ""
            if query_lower in title.lower():
                matches.append(anime)

        if not matches:
            console.print("\n[yellow]No results found.[/]\n")
            continue

        _add_to_history(query)

        console.print()
        console.print("[bold cyan]Filter[/]")
        console.print("  1. Watching")
        console.print("  2. Completed")
        console.print("  3. Planning")
        console.print("  4. Dropped")
        console.print("  5. All")
        console.print()

        filter_choice = ask("Filter:")

        selected_status = STATUS_MAP.get(filter_choice)

        if selected_status:
            filtered = [a for a in matches if a.get("status") == selected_status]
        else:
            filtered = matches

        if not filtered:
            label = STATUS_LABELS.get(selected_status, "").lower()
            msg = f"No {label} results found." if label else "No results found."
            console.print(f"\n[yellow]{msg}[/]\n")
            continue

        filtered.sort(key=lambda a: (
            a.get("season_year") or 0,
            a.get("season_order") or 0,
            a.get("title") or "",
        ))

        console.print(f"\nFound [green]({len(filtered)})[/]\n")

        for i, anime in enumerate(filtered[:30], 1):
            title = anime.get("title", "")
            season_year = anime.get("season_year")
            progress = anime.get("progress", "")
            parts = []
            if season_year:
                parts.append(f"[dim]{season_year}[/]")
            if progress:
                parts.append(f"[dim]({progress} ep)[/]")
            details = "  ".join(parts)
            console.print(f"  {i}. {title}  {details}")

        pause()