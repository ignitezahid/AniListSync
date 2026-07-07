# 🎌 AniListSync

> Synchronize your AniList and MyAnimeList libraries from your Telegram Saved Messages.

[![Stars](https://img.shields.io/github/stars/ignitezahid/AniListSync?style=flat-square&logo=github)](https://github.com/ignitezahid/AniListSync/stargazers)
[![License](https://img.shields.io/github/license/ignitezahid/AniListSync?style=flat-square)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue?style=flat-square&logo=python)](https://www.python.org/)
[![Release](https://img.shields.io/github/v/release/ignitezahid/AniListSync?style=flat-square&logo=git)](https://github.com/ignitezahid/AniListSync/releases)

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

Edit **config.py** with your API credentials, or just run `python main.py` — the first-run wizard will detect placeholders and guide you through setup interactively.

## 🔑 API Keys

| Service | Credentials |
|---------|-------------|
| Telegram | [API ID & Hash](https://my.telegram.org/apps) |
| AniList | [Access Token](https://docs.anilist.co/guide/auth/) |
| MyAnimeList | [Client ID & Secret](https://myanimelist.net/apiconfig) |

---

## 📋 Main Menu

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
