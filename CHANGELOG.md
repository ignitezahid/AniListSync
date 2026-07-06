# Changelog

## v2.7.0 (2026-07-06)

### Added
- 🧩 **Plugin System** — full plugin framework with `PluginManager`, discovery, dependency sorting, compatibility checks, per-plugin logs/settings, permissions, commands, and hooks
- 🎛 **Plugin Manager** — menu (option 10) with enable/disable, reload, configure, view/clear log, run commands, detail view with status/metadata/deps/permissions
- 🎨 **Themes as Plugins** — 7 built-in themes: Dracula, Catppuccin, Nord, Tokyo Night, Solarized Light, Matrix, Gruvbox, with live switching via Rich 15 theme stack API + OSC terminal background
- 🎮 **Discord RPC Plugin** — Rich Presence with states for sync, automation, statistics, collections, health, idle; keepalive thread, fire-and-forget updates, configurable client ID
- 🔔 **Notifications Plugin** — Windows toast notifications (plyer/BurntToast/console fallback) on sync finish, backup, health scan with per-type toggles
- ☁️ **Cloud Backup Plugin** — zip compression + upload to GitHub Releases with configurable provider system and auto-cleanup (keeps last N)
- 📋 **About Page** — quick diagnostic view showing version, Python, platform, plugin/themes counts, current theme, author, repository
- 🔌 **Hooks** — `on_automation()`, `on_statistics()`, `on_collections()` added; `on_startup`/`on_shutdown`/`on_sync_start`/`on_sync_finish`/`on_anime_added`/`on_health_scan`/`on_backup`/`on_restore` wired into all mode entry points
- 📊 **Genre Analytics** — sorted genre breakdown in Statistics
- 📄 **Exportable Statistics** — export full stats report (JSON/CSV/TXT/HTML/XLSX/MD)
- 📚 **Plugin API documentation** — `docs/plugins.md` covering manifest, hooks, commands, permissions, settings, logging, dependencies, theme plugins
- 🚪 **Safe exit** — `os._exit(0)` with no hanging or Telethon GC warnings

### Improved
- 📊 **Completion Analytics** — aligned via `_kv_table()` instead of f-string padding
- 📚 **Library Search** — Recent Searches shown once per session (not every loop), 2 blank lines before search prompt, ESC exits directly (no more `pause()` loop), removed save-to-collection/`[c]`/`Action:` prompt
- 🔄 **Sync** — resume saves after every title (not every 10th), titles processed in Telegram message order, no "Adding:" progress bar in `add_anime_batch()`, deduplicated retry queue (list→set)
- 📋 **Dashboard** — uses cached `state.json` counts instead of live AniList API call (matches sync numbers, faster)
- 🔔 **Library Health Notification** — saves `health_pct` to `state.json` before hook fires so plugins read real value instead of 0%
- 🎨 **Main menu reorganized** — blank-line separators by purpose group, option numbers: Sync(1), Automation(2), Search(3), Library Search(4), Collections(5), Statistics(6), Compare(7), Repair(8), Bulk Operations(9), Plugins(10), About(11), Tools(12), Exit(13)
- 📋 **Plugin Manager header** — summary bar showing Plugins (app-only), Themes (actual count), Enabled (app-only), Errors
- 🔢 **Blank separators in menus** — no longer consume a number in auto-numbering
- 🎛 **Plugin detail view** — shows commands list inline (from `get_commands()` callback)

### Changed
- 🎨 **Theme system** — now plugin-based instead of hardcoded in `ui.py`, loaded via `reload_theme()` after discovery, uses Rich 15 `push_theme`/`pop_theme` stack API
- 🎨 **Background color** — set via OSC escape sequences (`ESC ] 11 ; #RRGGBB ST`), only when `console.color_system` is available (skips legacy cmd.exe)
- 🎨 **Theme styles** — use named standard colors (bold magenta, bright_blue, etc.) for legacy terminal compatibility
- 🎨 **Border style** — added to all themes, wired into all Panel uses via `console.get_style("border")`
- 🎨 **Section headers** — hardcoded `[bold cyan]` replaced with `[title]` tag across all modes
- 🧩 **Plugins moved** from `core/plugins/` to `plugins/{id}/` (one folder per plugin)
- 📦 **`sample_plugin`** removed, reference dropped from `docs/plugins.md`
- 🔄 **Telegram client** — kept alive across session instead of per-operation `with client:` blocks, connected lazily on first sync
- 🐛 **Timing instrumentation removed** from sync after Discord RPC timeout diagnosis

### Fixed
- 🐛 **Exit hanging** — `os._exit(0)` instead of `break` avoids hanging on `client.disconnect()` and ugly Telethon "Exception ignored" GC warnings
- 🐛 **Dashboard count mismatch** — reads `state.json` instead of querying live AniList API
- 🐛 **Library Health notification** — shows 0% because `health_pct` was never saved to `state.json`
- 🐛 **Discord RPC blocking sync** — `response_timeout`/`connection_timeout` reduced to 2s, `_update()` made fire-and-forget via `run_coroutine_threadsafe` to prevent 10s delays
- 🐛 **Discord RPC asset name** — corrected from `anilistsync` to `AniListSync` (case-sensitive)
- 🐛 **Resume message gap** — saved after every title instead of every 10th, preventing re-processing of already-synced titles

### New Dependencies
- `pypresence>=4.0.0` — Discord Rich Presence plugin
- `plyer>=2.0.0` — Desktop notifications plugin

---

### Added
- 🤖 **Automation & Scheduled Sync** — new Automation menu (option 2) with interval config (15m/30m/1h/6h/24h), toggle on/off
- 🚀 **Sync on Startup** — optional auto-sync when app launches
- 💾 **Auto Backup before Sync** — backs up aliases, cache, resume, retry queue before each sync
- 🩺 **Auto Health after Sync** — runs health scan if score drops to 60% or below
- 📊 **Completion Analytics** — per-status counts with percentages in Statistics
- 🎭 **Genre Analytics** — sorted genre breakdown in Statistics
- 📄 **Exportable Statistics** — export full stats report (JSON/CSV/TXT/HTML/XLSX/MD)
- 📋 **Dashboard 3.0** — card-style panels (Connections, Library, Storage, Sync) instead of flat tables
- ⏱ **Relative Last Sync** — shows "3 min ago" instead of absolute timestamp
- ⏳ **Next Sync Countdown** — shows remaining time until next scheduled sync (when automation enabled)
- 🩺 **Health Score on Dashboard** — live health percentage in Sync panel
- 🏗 **`_compute_health_score()`** — reusable health computation for both dashboard and health menu

### Improved
- 💾 **State.json writes less frequently** — only written every 5th sync instead of every sync, preserving accurate timestamps
- 🔁 **Retry queue deduplication** — changed from `list` to `set` to prevent duplicate entries
- ⚡ **Collection Manager library cache** — library lookup cached to avoid repeated API calls
- 🩺 **Health menu Fix actions** — backup cleanup and other fix actions now refresh the health view immediately instead of requiring re-entry
- 🧰 **Backup threshold raised** — library health warning now triggers at 100 backups (was 50)
- ⌨️ **Statistics ESC exit** — press ESC to return, "0" to export (matches health report pattern)

### Changed
- 🔢 **Main menu renumbered** — Automation inserted as option 2, shifting Search→3, Library Search→4, Collections→5, Compare→6, Repair→7, Tools→8, Statistics→9, Bulk Operations→10, Exit→11
- 🗑 **Removed `pause()` from `tools.py`** — unused import and stale call in `_clean_old_backups()`

### New Settings
- `automation_enabled` — enable/disable scheduled sync
- `automation_interval_minutes` — interval between syncs (default: 30)
- `sync_on_startup` — auto-sync when app starts
- `live_tracking_on_startup` — auto-start live tracking on startup
- `auto_backup_before_sync` — backup before each sync
- `auto_health_after_sync` — health check after each sync

---

## v2.4.0

### Added
- Dashboard 2.0 with connection status, entry counts, and cached counts
- Library Search with status filters (Watching, Completed, Planning, Dropped) and search history
- Better Statistics with cache hits/misses, accuracy, studio/genre/year analysis
- Better Export (HTML, XLSX)
- Duplicate Alias Detection
- Auto Repair (70%+ confidence)

### Improved
- Franchise Sync with library-aware display
- Performance mode with AniList/MAL library caching
- Live watcher with ESC exit via msvcrt polling

### Fixed
- Live Tracking input conflicts (queue-based title processing)
- Cache refresh logic
- API optimizations

---

## v2.5.0 (2026-07-05)

### Added
- 📁 **Collection Manager** — create/manage custom collections with icons, stats, sorting, export
- 🚀 **Bulk Operations** — refresh caches, repair MAL IDs, health check, optimize database
- 📺 **Recommended Watch Order** — chronological franchise display in search results
- 🧹 **Fuzzy-matching fallback** — "Did you mean?" suggestions when library search returns no results
- 📊 **Average score** in library data (added `averageScore` to GraphQL query)
- 🔧 **Optimize Database** — deduplicates collection entries, removes stale/dead references
- 🔧 **Repair Missing MAL IDs** — fills in `idMal` for collection entries from library cache

### Improved
- 🎨 **Menu alignment** — normalized emoji widths for consistent spacing
- 📊 **Library Search** — save-to-collection integration with duplicate counts
- 📄 **Export** — openpyxl requirement shown upfront in menu
- 📋 **Dashboard** — reflects new menu items and v2.5.0 version

### Changed
- 🗂 "Collection Manager" renamed to "Collections" in main menu
- 🚀 "Bulk Operations" promoted from Tools submenu to top-level (option 9)
- 🔢 Menu renumbered: Exit moved from 9 to 10

### Fixed
- 🐛 Rich markup eating `[e]`, `[s]` etc. shortcut labels (escaped with `\[`)
- 🐛 Undefined `warning` reference in library_search.py
- 🐛 Undefined `Path` reference in sync.py
- 🐛 Unused imports & variables across the codebase (76 ruff issues resolved)
- 🐛 Removed test artifacts (`test_file_util.py`, `data/test.json`)

### Housekeeping
- 🧹 Added `pyproject.toml` with ruff configuration
- 🧹 Removed `__pycache__` directories
- 🧹 Converted bare `print()` to Rich `success()` in compare.py
