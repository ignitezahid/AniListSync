# Changelog

## v2.6.0 (2026-07-05)

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
