from core.plugin_loader import plugin_manager, PLUGIN_LOGS_DIR
from utils.ui import ask, console, show_header, success, warning

PERMISSION_ICONS = {
    "network": "\U0001f310 Network",
    "filesystem": "\U0001f4c1 Filesystem",
    "notifications": "\U0001f514 Notifications",
    "discord_ipc": "\U0001f3ae Discord IPC",
}


def _perm_label(p: str) -> str:
    return PERMISSION_ICONS.get(p, p)


def _toggle_label(pid: str) -> str:
    return "\U0001f7e2 Enabled" if plugin_manager.is_enabled(pid) else "\U0001f534 Disabled"


def _view_log(pid: str):
    log_path = PLUGIN_LOGS_DIR / f"{pid}.log"
    if not log_path.exists():
        warning("No log file found.")
        return
    console.print()
    with open(log_path, encoding="utf-8") as f:
        lines = f.readlines()
    if not lines:
        warning("Log is empty.")
        return
    for line in lines[-20:]:
        console.print(f"  {line.strip()}")
    console.print()
    ask("Press Enter to continue.")


def _clear_log(pid: str):
    log_path = PLUGIN_LOGS_DIR / f"{pid}.log"
    try:
        log_path.write_text("")
        success("Log cleared.")
    except Exception as e:
        warning(f"Failed to clear log: {e}")


def _configure_plugin(pid: str):
    instance = plugin_manager._plugins.get(pid)
    if not instance or not hasattr(instance, "settings"):
        warning("This plugin has no settings.")
        return
    manifest = plugin_manager._manifests.get(pid, {})
    show_header(f"Configure {manifest.get('name', pid)}")
    settings = instance.settings
    if not settings:
        console.print("  [dim]No settings configured.[/]")
    else:
        for key, value in settings.items():
            console.print(f"  {key}: {value}")
    console.print()
    warning("Settings editing not yet implemented.")


def plugin_menu():
    while True:
        show_header("Plugin Manager")
        plugins = plugin_manager.get_plugins()
        if not plugins:
            console.print("  [dim]No plugins found.[/]")
            console.print()
            console.print("  1. Back")
            console.print()
            if ask("Choice:") == "1":
                break
            continue

        loaded = sum(1 for _, _, is_loaded in plugins if is_loaded)
        enabled = sum(1 for pid, m, _ in plugins if m.get("type") != "theme" and plugin_manager.is_enabled(pid))
        errors = len(plugin_manager._errors)

        app_plugins = [(pid, m, loaded) for pid, m, loaded in plugins if m.get("type") != "theme"]
        theme_plugins = [(pid, m, loaded) for pid, m, loaded in plugins if m.get("type") == "theme"]
        all_plugins = app_plugins + theme_plugins

        console.print(f"  Plugins: {len(app_plugins)}   Themes: {plugin_manager.get_total_themes()}   Enabled: {enabled}   Errors: {errors}")
        console.print()

        idx = 1
        if app_plugins:
            for pid, manifest, loaded in app_plugins:
                name = manifest.get("name", pid)
                ver = manifest.get("version", "?")
                status = "\U0001f7e2" if plugin_manager.is_enabled(pid) else "\U0001f534"
                if plugin_manager.has_error(pid):
                    console.print(f"  {idx}. [red]\u274c[/] {name}")
                elif loaded:
                    console.print(f"  {idx}. [green]\u2713[/] {status} {name}  [dim]v{ver}[/]")
                else:
                    console.print(f"  {idx}. [yellow]\u26a0[/] {status} {name}  [dim]v{ver}[/]")
                idx += 1

        if app_plugins and theme_plugins:
            console.print()

        if theme_plugins:
            console.print("  [bold]── Themes ──[/]")
            for pid, manifest, loaded in theme_plugins:
                name = manifest.get("name", pid)
                ver = manifest.get("version", "?")
                status = "\U0001f7e2" if plugin_manager.is_enabled(pid) else "\U0001f534"
                if plugin_manager.has_error(pid):
                    console.print(f"  {idx}. [red]\u274c[/] {name}")
                elif loaded:
                    console.print(f"  {idx}. [green]\u2713[/] {status} {name}  [dim]v{ver}[/]")
                else:
                    console.print(f"  {idx}. [yellow]\u26a0[/] {status} {name}  [dim]v{ver}[/]")
                idx += 1

        console.print()
        console.print("  0. Back")
        console.print()
        pick = ask("Pick a plugin number for details, or 0 to go back:")
        if pick == "0" or not pick:
            break
        if not pick.isdigit():
            continue
        idx_num = int(pick) - 1
        if idx_num < 0 or idx_num >= len(all_plugins):
            continue
        pid, manifest, loaded = all_plugins[idx_num]

        while True:
            show_header(manifest.get("name", pid))
            console.print(f"  ID:           {pid}")
            console.print(f"  Version:      {manifest.get('version', '?')}")
            console.print(f"  Author:       {manifest.get('author', '?')}")
            if manifest.get("website"):
                console.print(f"  Website:      {manifest['website']}")
            if manifest.get("repository"):
                console.print(f"  Repository:   {manifest['repository']}")
            if manifest.get("license"):
                console.print(f"  License:      {manifest['license']}")
            console.print(f"  Description:  {manifest.get('description', 'N/A')}")

            if loaded:
                console.print("  Status:       [green]Loaded[/]")
                console.print(f"  Last Loaded:  {plugin_manager.get_loaded_at(pid)}")
                console.print(f"  Hooks:        {plugin_manager.count_hooks(pid)} registered")
            elif plugin_manager.has_error(pid):
                err = plugin_manager.get_error(pid)
                console.print("  Status:       [red]Error[/]")
                console.print(f"  Reason:       {err.message}")
            else:
                console.print("  Status:       [yellow]Not loaded[/]")

            deps = manifest.get("depends", [])
            if deps:
                dep_labels = []
                for d in deps:
                    dm = plugin_manager._manifests.get(d)
                    if dm and d in plugin_manager._plugins:
                        dep_labels.append(f"[green]\u2713[/] {dm.get('name', d)}")
                    else:
                        name = dm.get('name', d) if dm else d
                        dep_labels.append(f"[red]\u2717[/] {name} [dim](missing)[/]")
                console.print(f"  Dependencies: {', '.join(dep_labels)}")

            perms = manifest.get("permissions", [])
            if perms:
                console.print(f"  Permissions:  {', '.join(_perm_label(p) for p in perms)}")

            ver_r = []
            if manifest.get("min_app_version"):
                ver_r.append(f"\u2265 {manifest['min_app_version']}")
            if manifest.get("max_app_version"):
                ver_r.append(f"\u2264 {manifest['max_app_version']}")
            if ver_r:
                console.print(f"  App version:  {' '.join(ver_r)}")

            console.print()

            has_settings = loaded and hasattr(plugin_manager._plugins.get(pid), "settings")
            log_exists = loaded

            # Build commands list
            opts = []
            opts.append(("1", f"Toggle  {_toggle_label(pid)}"))
            opts.append(("2", "Reload"))

            if has_settings:
                opts.append(("3", "Configure"))

            next_cmd = len(opts) + 1
            commands = plugin_manager.get_commands(pid)
            for clabel, _cfunc in commands:
                opts.append((str(next_cmd), clabel))
                next_cmd += 1

            if log_exists:
                opts.append((str(next_cmd), "View Log"))
                next_cmd += 1
                opts.append((str(next_cmd), "Clear Log"))
                next_cmd += 1

            opts.append(("0", "Back"))

            for key, label in opts:
                console.print(f"  {key}. {label}")
            console.print()
            action = ask("Choice:")

            if action == "1":
                if plugin_manager.is_enabled(pid):
                    plugin_manager.disable(pid)
                    warning(f"{manifest.get('name', pid)} disabled.")
                else:
                    plugin_manager.enable(pid)
                    success(f"{manifest.get('name', pid)} enabled.")
            elif action == "2":
                plugin_manager.reload(pid)
                success(f"{manifest.get('name', pid)} reloaded.")
            elif action == "3" and has_settings:
                _configure_plugin(pid)
            elif action == "0":
                break
            else:
                cmd_start = 3
                if has_settings:
                    cmd_start += 1
                log_view_key = cmd_start + len(commands)
                log_clear_key = log_view_key + 1

                if log_exists and action == str(log_view_key):
                    _view_log(pid)
                elif log_exists and action == str(log_clear_key):
                    _clear_log(pid)
                else:
                    for ci, (clabel, cfunc) in enumerate(commands, cmd_start):
                        if action == str(ci):
                            try:
                                cfunc()
                            except Exception as e:
                                warning(f"Command error: {e}")
                            break
