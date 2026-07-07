# 🎌 AniListSync

> Synchronize your AniList and MyAnimeList libraries from your Telegram Saved Messages.

Command-line anime library manager — scans Telegram, matches titles, syncs **AniList** and **MyAnimeList**.

---

## ✨ Features

- 🔄 Telegram → AniList → MyAnimeList sync with live progress
- 🤖 Automation & scheduled sync (interval, sync-on-startup, auto backup/health)
- 🔎 Manual Search with interactive franchise support & watch order
- 📚 Library Search with status filters, search history & fuzzy fallback
- 📁 Collection Manager (stats, sorting, export, icons)
- 📊 Statistics with Completion & Genre Analytics, exportable reports
- 🛠 Compare, Auto Repair, Library Health scanner
- 🧩 Plugin system — Discord RPC v1.5.0, Notifications, Cloud Backup, 7 themes
- 💾 Backup/Restore, Import/Export (JSON, CSV, TXT, MD, HTML, XLSX)
- 📋 Startup dashboard with card panels, relative time, health score

---

## 🚀 Installation

```bash
git clone https://github.com/ignitezahid/AniListSync.git
cd AniListSync
pip install -r requirements.txt
copy config.example.py config.py   # Windows
cp config.example.py config.py     # Linux/macOS
```

Edit **config.py** with your API credentials and run `python main.py`.

## 🔑 API Keys

| Service | Credentials |
|---------|-------------|
| Telegram | [API ID & Hash](https://my.telegram.org/apps) |
| AniList | [Access Token](https://docs.anilist.co/guide/auth/) |
| MyAnimeList | [Client ID & Secret](https://myanimelist.net/apiconfig) |

---

## 📋 Main Menu

```text
 1. 🔄  Sync          7.  🔍  Compare
 2. 🤖  Automation    8.  🛠   Repair
 3. 🔎  Search        9.  🚀  Bulk Operations
 4. 📚  Library Search
 5. 🗂   Collections  10. 🧩  Plugins
                      11. 📋  About
 6. 📊  Statistics    12. 🧰  Tools
                      13. 🚪  Exit
```

---

## 🧩 Plugin System

Each plugin lives in `plugins/<name>/` with a `manifest.json` and entry script.

- 🎮 **Discord RPC v1.5.0** — Rich Presence with auto-reconnect via process detection
- 🔔 **Notifications** — Windows toasts on sync/backup/health (per-type toggles)
- ☁️ **Cloud Backup** — zip + upload to GitHub Releases (extensible providers)
- 🎨 **Themes** — 7 themes (Dracula, Catppuccin, Nord, Tokyo Night, Solarized Light, Matrix, Gruvbox)

See [`docs/plugins.md`](docs/plugins.md) for the plugin API.

---

## 🗺️ Roadmap

### ✅ v2.8 — Robustness & Stability
- Discord RPC v1.5.0 auto-reconnect (process detection, 5s polling, background timer)
- tools.py split into package, menu constants, first-run config wizard
- Crash fixes: guarded int()/input(), subprocess timeout, json.load guards
- Windows ResourceWarning suppression, BACK_10 constant fix

### 🔜 v2.9+
- Cloud Backup providers (S3, Google Drive)
- Discord & Telegram integrations, Web Dashboard
- Multi-Profile support, Desktop GUI

---

## 🔒 Security

Never commit: `config.py`, `*.session`, `data/mal_tokens.json`

---

## 📜 License

MIT License — Made by **ignitezahid**

⭐ If you find AniListSync useful, consider starring the repository.
