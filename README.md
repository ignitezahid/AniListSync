# 🎌 AniListSync

> **Synchronize your AniList and MyAnimeList libraries directly from your Telegram Saved Messages.**

AniListSync is a command-line anime library manager that scans your Telegram Saved Messages, intelligently matches anime titles, and keeps your **AniList** and **MyAnimeList** libraries synchronized.

---

## ✨ Features

- 🤖 Automation & Scheduled Sync (interval config, sync-on-startup, auto backup/health)
- 🔄 Telegram → AniList → MyAnimeList synchronization
- ⚡ Live Telegram monitoring with ESC exit
- 🔎 Manual Search with interactive franchise support
- 📚 Library Search with status filters, search history & fuzzy fallback
- 📁 Collection Manager with stats, sorting, export & custom icons
- 🚀 Bulk Operations (refresh caches, health check, repair, optimize)
- 🧠 Smart search with fuzzy matching & alias learning
- 📺 Recommended watch order in franchise view
- 🔁 Retry Queue Manager
- 🗂 Alias Manager with duplicate detection
- 💾 Search Cache
- 🛠 Compare, Auto Repair (70%+ confidence), Library Health scanner
- 📊 Enhanced Statistics (Completion Analytics, Genre Analytics, exportable reports)
- 💾 Backup, Restore, Import & Export (JSON, CSV, TXT, Markdown, HTML, XLSX)
- ⚙️ Built-in Settings Manager
- 📋 Startup Dashboard with card panels, relative time, countdown, health score
- 🧩 Plugin system with Discord RPC, Notifications, Cloud Backup, custom themes
- 🎮 Discord Rich Presence (sync, automation, statistics, collections, health states)
- 🔔 Desktop notifications (sync, backup, health scan)
- ☁️ Cloud Backup (GitHub Releases with auto-cleanup)
- 🎨 7 built-in themes (Dracula, Catppuccin, Nord, Tokyo Night, Solarized Light, Matrix, Gruvbox)
- 🎨 Rich terminal interface with live theme switching
- 📋 About page with version, Python, platform, plugins/themes, diagnostics

---

## 📸 Preview

| Main Menu | Sync |
|----------|------|
| ![](docs/menu.png)|
| ![](docs/sync.png)|
| ![](docs/export.png)|
| ![](docs/library.png)|
| ![](docs/repair.png)|
| ![](docs/statistics.png)|
| ![](docs/retry_queue.png)|
| ![](docs/live_tracking.png)|
---

# 🚀 Installation

```bash
git clone https://github.com/ignitezahid/AniListSync.git
cd AniListSync
pip install -r requirements.txt
```

Create your configuration file.

**Windows**

```bash
copy config.example.py config.py
```

**Linux / macOS**

```bash
cp config.example.py config.py
```

Edit **config.py** with your API credentials and run:

```bash
python main.py
```

---

# 🔑 Required API Keys

| Service | Credentials |
|---------|-------------|
| Telegram | API ID & API Hash |
| AniList | Access Token |
| MyAnimeList | Client ID & Client Secret |

- Telegram: https://my.telegram.org/apps
- AniList: https://docs.anilist.co/guide/auth/
- MyAnimeList: https://myanimelist.net/apiconfig

---

# 📋 Dashboard & Main Menu

On startup, a dashboard shows connection status, library stats, storage, and sync info in card-style panels:

```text
╭────────────────────────────────────────────╮
│               🎌 AniListSync               │
│        Anime Library Manager v2.7.0        │
│               by ignitezahid               │
╰────────────────────────────────────────────╯

  Connected as ignitezahid

╭─── Connections ────────────────────────────╮
│  Telegram          🟢 Connected              │
│  AniList           🟢 Connected              │
│  MyAnimeList       🟢 Connected              │
│  Automation        🟢 Active (30 min)        │
╰─────────────────────────────────────────────╯

╭─── Library ────────────────────────────────╮
│  AniList Entries   1064                      │
│  MAL Entries       938                       │
│  Aliases           55                        │
│  Collections       3                         │
╰─────────────────────────────────────────────╯

╭─── Storage ────────────────────────────────╮
│  Search Cache      29                        │
│  Retry Queue        0                        │
│  Exports            4                        │
│  Backups            50                       │
│  Plugins            8                         │
╰─────────────────────────────────────────────╯

╭─── Sync ───────────────────────────────────╮
│  Last Sync         3 min ago                 │
│  Next Sync         18h 30m                   │
│  Health            100%                      │
╰─────────────────────────────────────────────╯
```

```text
  1. 🔄  Sync
  2. 🤖  Automation

  3. 🔎  Search
  4. 📚  Library Search
  5. 🗂   Collections

  6. 📊  Statistics

  7. 🔍  Compare
  8. 🛠   Repair
  9. 🚀  Bulk Operations

 10. 🧩  Plugins

 11. 📋  About

 12. 🧰  Tools
 13. 🚪  Exit
```

During sync, a live progress bar tracks import progress:

```text
[████████████░░░░░░░░] 153 / 874
Checking:
Attack on Titan
```

---

# 🧰 Built-in Tools

- 🧩 Plugin Manager (enable/disable, configure, view logs, run commands)
- 📋 About page (version, Python, platform, plugins, themes, diagnostics)
- 🤖 Automation (scheduled sync, sync-on-startup, auto backup, auto health)
- Export / Import (JSON, CSV, TXT, Markdown, HTML, XLSX)
- Backup / Restore
- Alias Manager (view, search, edit, merge, delete, detect duplicates)
- Search Cache
- Retry Queue Manager
- Settings (Basic & Advanced)
- Library Health Scanner (12 grouped checks)
- Library Search with status filters, search history & fuzzy fallback
- Collection Manager (stats, sorting, export, icons)
- Bulk Operations (refresh, repair, optimize)

---

# 🧩 Plugin System

AniListSync 2.7.0+ supports a plugin system. Each plugin lives in its own folder under `plugins/` and consists of a `manifest.json` and an entry script.

**Built-in plugins:**
- 🎮 **Discord RPC** — Rich Presence with states for sync, automation, statistics, etc.
- 🔔 **Notifications** — Windows toast notifications on sync/backup/health
- ☁️ **Cloud Backup** — zip compression + upload to GitHub Releases (extensible provider system)
- 🎨 **Themes** — 7 built-in themes (Dracula, Catppuccin, Nord, Tokyo Night, Solarized Light, Matrix, Gruvbox) with live switching

See [`docs/plugins.md`](docs/plugins.md) for the full plugin API documentation.

---

# 🗺️ Roadmap

### ✅ v2.3

- [x] 🎨 Rich terminal interface
- [x] 🔁 Retry Queue Manager
- [x] 🔎 Manual Search
- [x] 🔄 Live MyAnimeList synchronization
- [x] 🧠 Interactive Search
- [x] 📄 Better export formats
- [x] 📋 Startup dashboard with connection status
- [x] 📊 Enhanced statistics (Exports, Last Sync, Version)
- [x] 📈 Live progress bar during sync
- [x] 💬 Search feedback ("Searching AniList...")

### ✅ v2.4

- [x] 📊 Dashboard 2.0 (connection status, entry counts, cached counts)
- [x] 📚 Library Search with status filters & search history
- [x] 📈 Better Statistics (cache hits/misses, accuracy, studio/genre/year analysis)
- [x] 📄 Better Export (HTML, XLSX)
- [x] 🎨 Better Search (Rich table display)
- [x] 🧠 Duplicate Alias Detection
- [x] 🤖 Auto Repair (70%+ confidence)
- [x] 🕒 Search History (last 5)

### ✅ v2.5

- [x] 📁 Collection Manager (stats, sorting, export, icons, search)
- [x] 🚀 Bulk Operations (refresh, health, repair, optimize)
- [x] 📺 Recommended watch order in franchise view
- [x] 🧹 Fuzzy-matching fallback in library search
- [x] 📊 Average score in library data (GraphQL)
- [x] 🛠 Release hardening (ruff cleanup, unused code removal)

### ✅ v2.6

- [x] 🤖 Automation & Scheduled Sync (menu, interval config, sync-on-startup)
- [x] 📊 Statistics 3.0 (Completion Analytics, Genre Analytics, exportable reports)
- [x] 📋 Dashboard 3.0 (card-style panels, relative time, countdown, health score)
- [x] 🔧 Retry queue deduplication (list → set)
- [x] 🧰 Library Health refactored (`_compute_health_score()` reusable for dashboard)
- [x] 💾 State.json written less frequently (every 5th sync, preserves timestamps)
- [x] ⚡ Collection Manager library cache (avoids repeated API calls)
- [x] 🔄 Auto Backup before sync & Auto Health after sync

### ✅ v2.7 — Plugin System & Integrations

- [x] 🧩 Plugin System (discovery, dependency sorting, permissions, hooks, commands, per-plugin logs/settings)
- [x] 🎨 7 Themes as Plugins (Dracula, Catppuccin, Nord, Tokyo Night, Solarized Light, Matrix, Gruvbox)
- [x] 🎮 Discord Rich Presence Plugin (sync, automation, statistics, collections, health states)
- [x] 🔔 Notifications Plugin (sync finish, backup, health scan, per-type toggles)
- [x] ☁️ Cloud Backup Plugin (zip compression, GitHub Releases provider, keep-last cleanup)
- [x] 📋 About Page (version, Python, platform, plugins/themes, diagnostics)
- [x] 🎛 Plugin Manager (detail view, configure, logs, commands, plugin commands)
- [x] 📚 Plugin API documentation (`docs/plugins.md`)
- [x] 📊 Statistics: Genre Analytics, exportable reports, `_kv_table()` alignment
- [x] 📚 Library Search: ESC exits directly, recent searches once per session, 2 blank lines before prompt
- [x] 🔄 Sync: resume saves after every title, preserves Telegram message order, no "Adding:" progress bar
- [x] 📋 Dashboard: uses cached state.json counts (no live API call, matches sync numbers)
- [x] 🚪 Exit: safe shutdown via `os._exit(0)` — no hanging or GC warnings
- [x] 🔔 Library Health notification: saves `health_pct` to state.json (fixes 0% bug)

### v2.8 — Cloud & Quality-of-Life
- [ ] 📦 Plugin Marketplace
- [ ] ☁️ Cloud Backup providers (S3, Google Drive)
- [ ] 📊 Better Export & Reporting

### v2.9
- [ ] Cloud Backup providers (S3, Google Drive)
- [ ] Discord & Telegram Integrations
- [ ] Web Dashboard
- [ ] API Improvements

### v3.0
- [ ] Multi-Profile Support
- [ ] Advanced Customization
- [ ] Desktop GUI
- [ ] Cross-Platform Installer
---

# 🔒 Security

Never commit:

```text
config.py
telegram_session.session
telegram_session.session-journal
data/mal_tokens.json
```

---

# 🤝 Contributing

Contributions, bug reports, and feature requests are always welcome.

---

# 📜 License

MIT License

---

<div align="center">

Made with ❤️ by **ignitezahid**

⭐ If you find AniListSync useful, consider starring the repository.

</div>
