# Changelog

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
