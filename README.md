# 🎌 AniListSync

> **Synchronize your AniList and MyAnimeList libraries directly from your Telegram Saved Messages.**

AniListSync is a command-line anime library manager that scans your Telegram Saved Messages, intelligently matches anime titles, and keeps your **AniList** and **MyAnimeList** libraries synchronized.

---

## ✨ Features

- 🔄 Telegram → AniList → MyAnimeList synchronization
- ⚡ Live Telegram monitoring
- 🔎 Manual Search
- 🧠 Smart search with fuzzy matching & alias learning
- 📚 Franchise Sync
- 🔁 Retry Queue Manager
- 🗂 Alias Manager
- 💾 Search Cache
- 🛠 Compare & Repair libraries
- 📊 Statistics (Exports, Last Sync, Version)
- 💾 Backup, Restore, Import & Export
- ⚙️ Built-in Settings Manager
- 📋 Startup Dashboard
- 🎨 Rich terminal interface, progress bars

---

## 📸 Preview

| Main Menu | Sync |
|----------|------|
| ![](docs/menu.png) | ![](docs/sync.png) |
| ![](docs/retry_queue.png) | ![](docs/live_tracking.png) |

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

On startup, a dashboard shows connection status and quick stats before the menu:

```text
╭──────────────────────────────╮
│         AniListSync          │
│ Anime Library Manager 2.3.0  │
╰──────────────────────────────╯

AniList : Connected ✅
MAL      : Connected ✅
Telegram : Connected ✅

Aliases       143
Search Cache   89
Retry Queue     2

──────────────────────────────
```

```text
1. 🔄 Sync
2. 🔎 Search
3. 🔍 Compare
4. 🛠 Repair
5. 🧰 Tools
6. 📊 Statistics
7. 🚪 Exit
```

During sync, a live progress bar tracks import progress:

```text
[████████████░░░░░░░░] 153 / 874
Checking:
Attack on Titan
```

---

# 🧰 Built-in Tools

- Export / Import
- Backup / Restore
- Alias Manager
- Search Cache
- Retry Queue Manager
- Settings (Basic & Advanced)

---

# 🗺️ Roadmap

### v2.3

- [x] Rich terminal interface
- [x] Retry Queue Manager
- [x] Manual Search
- [x] Live MyAnimeList synchronization
- [x] Interactive Search
- [x] Better export formats
- [x] Startup dashboard with connection status
- [x] Enhanced statistics (Exports, Last Sync, Version)
- [x] Live progress bar during sync
- [x] Search feedback ("Searching AniList...")

### v2.4

- [ ] Duplicate alias detection
- [ ] Library Search

### v3.0

- [ ] Desktop GUI
- [ ] Plugin system

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