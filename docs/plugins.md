# Plugin API

AniListSync 2.6.0+ supports a plugin system. Each plugin lives in its own folder under `plugins/` and consists of a `manifest.json` and an entry script.

---

## Folder Structure

```
plugins/
├── my_plugin/
│   ├── manifest.json
│   └── plugin.py
```

---

## manifest.json

```json
{
    "name": "My Plugin",
    "id": "my_plugin",
    "version": "1.0.0",
    "type": "app",
    "author": "you",
    "description": "What my plugin does.",
    "website": "https://github.com/you/AniListSync",
    "repository": "https://github.com/you/AniListSync",
    "license": "MIT",
    "entry": "plugin.py",
    "min_app_version": "2.6.0",
    "max_app_version": "3.0.0",
    "depends": ["other_plugin"],
    "permissions": ["network"]
}
```

| Field | Required | Description |
|---|---|---|
| `name` | yes | Human-readable name |
| `id` | yes | Unique identifier (folder name, no spaces) |
| `version` | yes | Semantic version |
| `entry` | yes | Entry script filename (e.g. `plugin.py`) |
| `type` | — | `"app"` (default), `"theme"` |
| `author` | — | Plugin author |
| `description` | — | Short description |
| `website` | — | Project website |
| `repository` | — | Source repo URL |
| `license` | — | SPDX license identifier |
| `min_app_version` | — | Minimum AniListSync version (e.g. `"2.6.0"`) |
| `max_app_version` | — | Maximum AniListSync version |
| `depends` | — | List of plugin IDs that must be loaded first |
| `permissions` | — | List of permission strings (see below) |

### `type`

- `"app"` — Standard plugin. Provides hooks and/or commands.
- `"theme"` — Theme plugin. Exports a `theme` dict on the Plugin class. Overrides console colors. Only the last-loaded theme plugin's colors take effect.

### Permissions

| Permission | Icon | Description |
|---|---|---|
| `"network"` | 🌐 | HTTP requests to external APIs |
| `"filesystem"` | 📁 | Read/write files outside plugin's own data |
| `"notifications"` | 🔔 | Show system notifications |
| `"discord_ipc"` | 🎮 | Discord Rich Presence / IPC |

Permissions are auto-granted during startup discovery. On manual enable, the user is prompted.

---

## Entry Script (`plugin.py`)

Your entry script must export a class named `Plugin`.

```python
class Plugin:
    def on_load(self):
        pass
```

The framework instantiates your class once and injects the following attributes:

### Injected Attributes

| Attribute | Type | Description |
|---|---|---|
| `self._plugin_id` | `str` | Plugin ID from manifest |
| `self.settings` | `dict` | Per-plugin settings (loaded from `data/plugins/{id}.json`) |
| `self.save_settings()` | `callable` | Persist `self.settings` to disk |
| `self.log(msg, level)` | `callable` | Write to `logs/plugins/{id}.log` |
| `self.log_path` | `Path` | Path to the plugin's log file |

---

## Hooks

Hooks are methods on your Plugin class that the framework calls at specific points. All hooks are optional — define only the ones you need.

### Lifecycle

| Hook | When | Args |
|---|---|---|
| `on_load()` | After plugin is instantiated | — |
| `on_unload()` | Plugin is disabled | — |
| `on_startup()` | App starts (after `discover()`) | — |
| `on_shutdown()` | App exits (menu option 12) | — |

### Sync

| Hook | When | Args |
|---|---|---|
| `on_sync_start()` | Sync begins | — |
| `on_anime_added(anime)` | Each title processed | `anime` — the anime dict |
| `on_sync_finish()` | Sync completes | — |

### Library Management

| Hook | When | Args |
|---|---|---|
| `on_automation()` | Automation menu opened | — |
| `on_statistics()` | Statistics screen opened | — |
| `on_collections()` | Collection manager opened | — |
| `on_health_scan()` | Library health scan run | — |
| `on_backup(path)` | Backup file created | `path` — path string of backup |
| `on_restore(path)` | Backup restored | `path` — path string of restored file |

---

## Commands

Plugins can expose user-invokable commands that appear in the Plugin Manager detail view.

Define a `get_commands()` method returning a list of `(label, callback)` tuples:

```python
class Plugin:
    def get_commands(self):
        return [
            ("Say Hello", self._hello),
            ("Reset Counter", self._reset),
        ]

    def _hello(self):
        print("  Hello from my plugin!")

    def _reset(self):
        self.settings["counter"] = 0
        self.save_settings()
        print("  Counter reset.")
```

The callback receives no arguments and runs synchronously in the main menu loop.

---

## Theme Plugins

A theme plugin provides a `theme` dict on the Plugin class. The dict maps Rich style names to style strings (color + attributes).

```python
class Plugin:
    theme = {
        "title": "bold #BD93F9",
        "success": "bold #50FA7B",
        "warning": "bold #FFB86C",
        "error": "bold #FF5555",
        "info": "bold #8BE9FD",
        "menu": "bold #F8F8F2",
    }

    def on_load(self):
        pass
```

Available style names:

| Style | Default | Description |
|---|---|---|
| `title` | `bold cyan` | Section headers |
| `success` | `bold green` | Success messages |
| `warning` | `bold yellow` | Warning messages |
| `error` | `bold red` | Error messages |
| `info` | `bold blue` | Info messages |
| `menu` | `bold white` | Menu text |

Only one theme plugin should be enabled at a time. If multiple are enabled, the last one (in dependency order) wins.

---

## Settings

Per-plugin settings are stored in `data/plugins/{id}.json`. The dict is injected as `self.settings`. Call `self.save_settings()` to persist.

```python
class Plugin:
    def on_load(self):
        if "counter" not in self.settings:
            self.settings["counter"] = 0
            self.save_settings()
```

Settings are editable via the Plugin Manager's "Configure" option, which shows a raw key-value view.

---

## Logging

Each plugin has its own log file at `logs/plugins/{id}.log`.

```python
self.log("Something happened")
self.log("Something bad", "WARN")
self.log("Something crashed", "ERROR")
```

Log files can be viewed and cleared from the Plugin Manager detail view.

---

## Dependencies

Plugins can declare dependencies via `"depends"` in manifest. Plugins are loaded in topological order using DFS. If a dependency is missing, the dependent plugin still loads — check at runtime if needed.

```json
{
    "depends": ["cloud_backup"]
}
```

---

## Plugin Manager

The Plugin Manager (menu item 10) provides:

- **Toggle** — Enable/disable a plugin
- **Reload** — Re-import the plugin from disk
- **View Log** — Show last 20 log lines
- **Clear Log** — Truncate log file
- **Configure** — View/edit raw settings
- **Commands** — Run plugin-defined commands
