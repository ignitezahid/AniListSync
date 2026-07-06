import sys
import platform

from core.plugin_loader import plugin_manager
from utils.ui import show_header, console, pause
from version import VERSION, CREATOR


def about():
    show_header("About")

    loaded = len([p for p in plugin_manager.get_plugins() if p[2]])
    total = len(plugin_manager.get_plugins())
    enabled = sum(1 for pid, _, _ in plugin_manager.get_plugins() if plugin_manager.is_enabled(pid))
    errors = len(plugin_manager._errors)
    themes = plugin_manager.get_theme_plugins()

    current_theme = "Default"
    for pid, _, _ in plugin_manager.get_plugins():
        if pid == "themes":
            inst = plugin_manager._plugins.get(pid)
            if inst and hasattr(inst, "active_theme_name"):
                current_theme = inst.active_theme_name
            break

    console.print("  AniListSync")
    console.print(f"  Version:       {VERSION}")
    console.print()
    console.print(f"  Python:        {sys.version.split()[0]}")
    console.print(f"  Platform:      {platform.platform()}")
    console.print()
    console.print(f"  Loaded:        {loaded} / {total} plugins")
    console.print(f"  Enabled:       {enabled}")
    console.print(f"  Themes:        {len(themes)}")
    if errors:
        console.print(f"  Errors:        [red]{errors}[/]")
    console.print()
    console.print(f"  Theme:         {current_theme}")
    console.print()
    console.print(f"  Author:        {CREATOR}")
    console.print(f"  Repository:    github.com/{CREATOR}/AniListSync")
    console.print()

    pause()
