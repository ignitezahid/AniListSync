from datetime import date, datetime
from utils.file_utils import load_json, save_json
from utils.ui import show_header, console, ask, warning, pause, success, error, show_menu
from anilist import get_completed_anime
from core.plugin_loader import plugin_manager
from modes.tools import export_json, export_csv, export_markdown, export_html
from utils.menu_keys import *  # noqa: F405

COLLECTIONS_FILE = "collections.json"
SORT_OPTIONS = ["Alphabetical", "Recently Added", "Score", "Year"]


def _anime_title(anime: dict) -> str:
    title = anime.get("title") or {}
    return title.get("english") or title.get("romaji") or title.get("native") or "Unknown"


def _now():
    return datetime.now().isoformat(timespec="minutes")


def _load():
    data = load_json(COLLECTIONS_FILE, {})
    migrated = False
    for name, val in list(data.items()):
        if isinstance(val, list):
            data[name] = {
                "icon": "📁",
                "created_at": _now(),
                "updated_at": _now(),
                "entries": val,
            }
            migrated = True
    if migrated:
        _save(data)
    return data


def _save(data):
    save_json(COLLECTIONS_FILE, data)


_lib_cache: dict | None = None


def _lib_lookup() -> dict:
    global _lib_cache
    if _lib_cache is None:
        _lib_cache = {a["id"]: a for a in get_completed_anime()}
    return _lib_cache


def _collection_stats(entries: list, lib: dict) -> dict:
    total = len(entries)
    completed = 0
    scores = []
    for e in entries:
        anime = lib.get(e["id"])
        if anime:
            if anime.get("status") == "COMPLETED":
                completed += 1
            s = anime.get("score")
            if s is not None:
                scores.append(s)
    avg_score = round(sum(scores) / len(scores), 1) if scores else None
    return {"total": total, "completed": completed, "avg_score": avg_score}


def _format_collection(name: str, col: dict, stats: dict) -> str:
    icon = col.get("icon", "📁")
    total = stats["total"]
    completed = stats["completed"]
    avg = stats.get("avg_score")
    parts = [f"{icon} {name}"]
    parts.append(f"[dim]{total} entries")
    if completed:
        parts.append(f"· {completed} completed")
    if avg is not None:
        parts.append(f"· avg {avg}/100[/]")
    else:
        parts.append("[/]")
    return " ".join(parts)


def _pick_collection(collections: dict, action: str) -> tuple[str, dict] | None:
    names = sorted(collections.keys())
    if not names:
        warning(f"No collections to {action}.")
        return None
    lib = _lib_lookup()
    console.print()
    for i, name in enumerate(names, 1):
        col = collections[name]
        stats = _collection_stats(col["entries"], lib)
        console.print(f"  {i}. {_format_collection(name, col, stats)}")
    console.print()
    choice = ask(f"Pick a collection to {action}:")
    if not choice:
        return None
    if choice.isdigit():
        idx = int(choice) - 1
        if 0 <= idx < len(names):
            return names[idx], collections[names[idx]]
    warning("Invalid choice.")
    return None


def _search_collections(collections: dict) -> dict:
    """Filter collections by name."""
    query = ask("Search collection:").strip().lower()
    if not query:
        return collections
    filtered = {k: v for k, v in collections.items() if query in k.lower()}
    if not filtered:
        warning("No matching collections.")
        return collections
    return filtered


def _create_collection(collections: dict):
    name = ask("Collection name:").strip()
    if not name:
        return
    if name in collections:
        warning(f"Collection '{name}' already exists.")
        return
    icon = ask("Icon (emoji, Enter for 📁):").strip()
    if not icon:
        icon = "📁"
    collections[name] = {
        "icon": icon,
        "created_at": _now(),
        "updated_at": _now(),
        "entries": [],
    }
    _save(collections)
    success("Collection created.")


def _set_icon(collections: dict):
    result = _pick_collection(collections, "re-icon")
    if not result:
        return
    name, col = result
    icon = ask("New icon (emoji):").strip()
    if not icon:
        return
    col["icon"] = icon
    col["updated_at"] = _now()
    _save(collections)
    success("Icon updated.")


def _rename_collection(collections: dict):
    result = _pick_collection(collections, "rename")
    if not result:
        return
    name, col = result
    new = ask("New name:").strip()
    if not new:
        return
    if new in collections:
        warning(f"Collection '{new}' already exists.")
        return
    collections[new] = collections.pop(name)
    collections[new]["updated_at"] = _now()
    _save(collections)
    success(f"Renamed to '{new}'.")


def _delete_collection(collections: dict):
    result = _pick_collection(collections, "delete")
    if not result:
        return
    name, col = result
    confirm = ask(f"Delete '{name}' with {len(col['entries'])} entries? (y/N):")
    if confirm.lower() != "y":
        return
    del collections[name]
    _save(collections)
    success(f"Deleted '{name}'.")


def _collection_details(collections: dict):
    result = _pick_collection(collections, "view")
    if not result:
        return
    name, col = result
    entries = col["entries"]
    lib = _lib_lookup()
    stats = _collection_stats(entries, lib)

    show_header(name)
    icon = col.get("icon", "📁")
    console.print(f"  {icon} [bold]{name}[/]")
    console.print()
    console.print(f"  Entries      [green]{stats['total']}[/]")
    console.print(f"  Completed    [green]{stats['completed']}[/]")
    if stats["avg_score"] is not None:
        console.print(f"  Avg Score    [green]{stats['avg_score']}/100[/]")
    console.print(f"  Created      [dim]{col.get('created_at', '?')[:10]}[/]")
    console.print(f"  Updated      [dim]{col.get('updated_at', '?')[:10]}[/]")

    console.print()
    if entries:
        show_num = ask("Show entries? (number to list, Enter to skip):")
        if show_num and show_num.isdigit():
            count = min(int(show_num), len(entries))
            sort_key = _choose_sort()
            sorted_entries = _sort_entries(entries, sort_key, lib)
            console.print()
            for i, e in enumerate(sorted_entries[:count], 1):
                console.print(f"  {i:>3}. {e['title']}  [dim]added: {e.get('added_at', '?')}[/]")
    pause()


def _view_collection(collections: dict):
    result = _pick_collection(collections, "view")
    if not result:
        return
    name, col = result
    entries = col["entries"]
    if not entries:
        warning(f"'{name}' is empty.")
        return
    sort_key = _choose_sort()
    lib = _lib_lookup()
    sorted_entries = _sort_entries(entries, sort_key, lib)
    show_header(f"{col.get('icon', '📁')} {name}")
    for i, e in enumerate(sorted_entries, 1):
        console.print(f"  {i:>3}. {e['title']}  [dim]added: {e.get('added_at', '?')}[/]")
    pause()


def _choose_sort() -> str:
    choice = show_menu("Sort By", SORT_OPTIONS + ["Cancel"])
    mapping = {"1": "alpha", "2": "added", "3": "score", "4": "year"}
    return mapping.get(choice, "alpha")


def _sort_entries(entries: list, key: str, lib: dict) -> list:
    if key == "added":
        return sorted(entries, key=lambda e: e.get("added_at", ""), reverse=True)
    if key == "score":
        def sort_key(e):
            anime = lib.get(e["id"])
            return -(anime.get("score") or 0) if anime else 0
        return sorted(entries, key=sort_key)
    if key == "year":
        def sort_key(e):
            anime = lib.get(e["id"])
            return -(anime.get("season_year") or 0) if anime else 0
        return sorted(entries, key=sort_key)
    return sorted(entries, key=lambda e: e.get("title", "").lower())


def _add_to_collection(collections: dict):
    result = _pick_collection(collections, "add to")
    if not result:
        return
    name, col = result

    anime_list = get_completed_anime()
    existing_ids = {e["id"] for e in col["entries"]}

    query = ask("Search title to add:").strip().lower()
    if not query:
        return

    matches = []
    for a in anime_list:
        t = (a.get("title") or "").lower()
        if query in t:
            matches.append(a)

    if not matches:
        warning("No matches found in library.")
        return

    console.print()
    for i, a in enumerate(matches[:20], 1):
        status = " [green]✓[/]" if a["id"] in existing_ids else ""
        console.print(f"  {i}. {_anime_title(a)}{status}")
    console.print()

    picks = ask("Numbers to add (comma separated, Enter to cancel):")
    if not picks:
        return

    added = 0
    skipped = 0
    for p in picks.split(","):
        p = p.strip()
        if not p.isdigit():
            continue
        idx = int(p) - 1
        if 0 <= idx < len(matches):
            anime = matches[idx]
            if anime["id"] in existing_ids:
                skipped += 1
            else:
                col["entries"].append({
                    "id": anime["id"],
                    "idMal": anime.get("idMal"),
                    "title": _anime_title(anime),
                    "added_at": str(date.today()),
                })
                existing_ids.add(anime["id"])
                added += 1
    if added or skipped:
        col["updated_at"] = _now()
        _save(collections)
        console.print(f"  [green]Added: {added}[/]  [yellow]Already existed: {skipped}[/]")
    else:
        warning("Nothing to add.")


def _remove_from_collection(collections: dict):
    result = _pick_collection(collections, "remove from")
    if not result:
        return
    name, col = result
    entries = col["entries"]
    if not entries:
        warning(f"'{name}' is empty.")
        return

    show_header(f"Remove from {name}")
    for i, entry in enumerate(entries, 1):
        console.print(f"  {i}. {entry.get('title', 'Unknown')}")
    console.print()
    picks = ask("Numbers to remove (comma separated, Enter to cancel):")
    if not picks:
        return

    indices = set()
    for p in picks.split(","):
        p = p.strip()
        if p.isdigit():
            idx = int(p) - 1
            if 0 <= idx < len(entries):
                indices.add(idx)

    if not indices:
        return

    col["entries"] = [e for i, e in enumerate(entries) if i not in indices]
    col["updated_at"] = _now()
    _save(collections)
    success(f"Removed {len(indices)} from '{name}'.")


def _collection_statistics(collections: dict):
    result = _pick_collection(collections, "stats for")
    if not result:
        return
    name, col = result
    lib = _lib_lookup()
    stats = _collection_stats(col["entries"], lib)

    show_header(f"{col.get('icon', '📁')} {name}")
    console.print(f"  Entries      [green]{stats['total']}[/]")
    console.print(f"  Completed    [green]{stats['completed']}[/]")
    console.print(f"  Remaining    [yellow]{stats['total'] - stats['completed']}[/]")
    if stats["avg_score"] is not None:
        console.print(f"  Avg Score    [green]{stats['avg_score']}/100[/]")
    else:
        console.print("  Avg Score    [dim]N/A[/]")
    pause()


def _collection_menu(collections: dict) -> str | None:
    show_header("Collections")
    lib = _lib_lookup()

    if collections:
        search_query = ask("Search collections (Enter to skip):").strip().lower()
        console.print()

        if search_query:
            filtered = {k: v for k, v in collections.items() if search_query in k.lower()}
        else:
            filtered = collections

        if filtered:
            for i, (name, col) in enumerate(sorted(filtered.items()), 1):
                stats = _collection_stats(col["entries"], lib)
                console.print(f"  {i}. {_format_collection(name, col, stats)}")
        else:
            warning("No matching collections.")
            console.print()
    else:
        console.print("  [dim]No collections yet.[/]\n")

    console.print()
    console.print("  [title]Options[/]")
    console.print("  \\[+]      Create")
    console.print("  \\[e]      Edit (view / add / remove)")
    console.print("  \\[s]      Statistics")
    console.print("  \\[x]      Export")
    console.print("  \\[i]      Set icon")
    console.print("  \\[r]      Rename")
    console.print("  \\[d]      Delete")
    console.print("  \\[Enter]  Back")
    console.print()
    return ask()


def _export_collection(collections: dict):
    result = _pick_collection(collections, "export")
    if not result:
        return
    name, col = result
    entries = col["entries"]
    if not entries:
        warning("Nothing to export — collection is empty.")
        return

    lib = _lib_lookup()
    headers = ["Title", "ID", "MAL ID", "Score", "Year", "Status", "Progress", "Added"]

    rows = []
    for e in entries:
        anime = lib.get(e["id"])
        rows.append({
            "Title": e["title"],
            "ID": e["id"],
            "MAL ID": e.get("idMal") or "",
            "Score": f"{anime.get('score') or ''}/100" if anime and anime.get("score") else "",
            "Year": anime.get("season_year") or "" if anime else "",
            "Status": anime.get("status") or "" if anime else "",
            "Progress": f"{anime.get('progress') or 0} ep" if anime else "",
            "Added": e.get("added_at", ""),
        })

    fmt = show_menu(
        "Export Format",
        ["JSON", "CSV", "Markdown", "HTML", "Cancel"],
    )

    exporters = {
        "1": ("json", export_json, rows),
        "2": ("csv", export_csv, (rows, headers)),
        "3": ("md", export_markdown, (rows, headers)),
        "4": ("html", export_html, (rows, headers)),
    }

    if fmt not in exporters:
        return

    ext, func, args = exporters[fmt]
    safe_name = name.replace(" ", "_").replace("/", "_")
    filename = f"collection_{safe_name}"

    try:
        if ext == "json":
            path = func(filename, rows)
        else:
            path = func(filename, *args)
        if path:
            success(f"Exported to [cyan]{path}[/]")
    except Exception as e:
        error(f"Export failed: {e}")
    pause()


def collection_manager():
    plugin_manager.call_hook("on_collections")
    while True:
        collections = _load()
        choice = _collection_menu(collections)

        if not choice:
            break

        if choice == COL_CREATE:
            _create_collection(collections)

        elif choice == COL_EDIT:
            if not collections:
                warning("No collections yet.")
            else:
                sub = show_menu(
                    "Edit Collection",
                    [
                        "View contents (sorted)",
                        "Add anime",
                        "Remove anime",
                        "Cancel",
                    ],
                )
                if sub == COL_VIEW:
                    _view_collection(_load())
                elif sub == COL_ADD:
                    _add_to_collection(_load())
                elif sub == COL_REMOVE:
                    _remove_from_collection(_load())

        elif choice == COL_STATS:
            if collections:
                _collection_statistics(_load())
            else:
                warning("No collections yet.")

        elif choice == COL_EXPORT:
            if collections:
                _export_collection(_load())
            else:
                warning("No collections yet.")

        elif choice == COL_ICON:
            if collections:
                _set_icon(collections)
            else:
                warning("No collections yet.")

        elif choice == COL_RENAME:
            _rename_collection(collections)

        elif choice == COL_DELETE:
            _delete_collection(collections)
