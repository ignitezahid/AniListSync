from anilist import get_completed_anime
from utils.file_utils import data_file, save_json, load_json
from utils.ui import ask, console, pause, show_header, warning
from difflib import get_close_matches as _fuzzy_match
from datetime import date

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
            titles = [a.get("title", "") for a in anime_list]
            fuzzy = _fuzzy_match(query_lower, [t.lower() for t in titles], n=3, cutoff=0.5)
            if fuzzy:
                console.print("\n[yellow]No exact results. Did you mean:[/]")
                console.print()
                for i, f in enumerate(fuzzy, 1):
                    orig = next(t for t in titles if t.lower() == f)
                    console.print(f"  {i}. {orig}")
                console.print()
                retry = ask("Try a number, or press Enter to search again:")
                if retry in ("1", "2", "3"):
                    idx = int(retry) - 1
                    query_lower = fuzzy[idx]
                    matches = [a for a in anime_list if a.get("title", "").lower() == query_lower]
                    if matches:
                        _add_to_history(matches[0].get("title", ""))
                if not matches:
                    continue
            else:
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

        console.print()
        console.print("  [c]  Save to collection")
        console.print("  [Enter]  Back")
        console.print()
        action = ask("Action:")
        if action.lower() == "c":
            collections = load_json("collections.json", {})
            if not collections:
                warning("No collections exist. Create one from the Collection Manager first.")
            else:
                names = sorted(collections.keys())
                console.print()
                for i, name in enumerate(names, 1):
                    col = collections[name]
                    icon = col.get("icon", "📁") if isinstance(col, dict) else "📁"
                    entries = col.get("entries", col) if isinstance(col, dict) else col
                    console.print(f"  {i}. {icon} {name} [dim]({len(entries)})[/]")
                console.print()
                pick = ask("Collection number:")
                if pick.isdigit():
                    idx = int(pick) - 1
                    if 0 <= idx < len(names):
                        col_name = names[idx]
                        col = collections[col_name]
                        if isinstance(col, list):
                            col = {"icon": "📁", "entries": col}
                            collections[col_name] = col
                        existing_ids = {e["id"] for e in col["entries"]}
                        added = 0
                        skipped = 0
                        for anime in filtered[:30]:
                            if anime["id"] in existing_ids:
                                skipped += 1
                            else:
                                col["entries"].append({
                                    "id": anime["id"],
                                    "idMal": anime.get("idMal"),
                                    "title": anime.get("title") or anime.get("romaji") or "Unknown",
                                    "added_at": str(date.today()),
                                })
                                existing_ids.add(anime["id"])
                                added += 1
                        if added or skipped:
                            from utils.file_utils import save_json
                            save_json("collections.json", collections)
                            console.print(f"  [green]Added: {added}[/]  [yellow]Already existed: {skipped}[/]")
                        else:
                            warning("Nothing to add.")
                        continue

        pause()
