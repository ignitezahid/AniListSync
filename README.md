# 🎌 AniListSync

> **Synchronize your AniList and MyAnimeList libraries directly from your Telegram Saved Messages.**

AniListSync is a command-line anime library manager that scans your Telegram Saved Messages, intelligently matches anime titles, and keeps your **AniList** and **MyAnimeList** libraries synchronized.

---

## ✨ Features

- 🔄 Telegram → AniList → MyAnimeList synchronization
- ⚡ Live Telegram monitoring
- 🧠 Smart search with fuzzy matching & alias learning
- 📚 Franchise Sync
- 🔁 Retry Queue Manager
- 🛠 Compare & repair libraries
- 📊 Statistics dashboard
- 💾 Backup, Restore, Import & Export
- 🎨 Modern Rich-powered terminal interface

---

## 📸 Preview

| Main Menu | Sync |
|----------|------|
| ![](docs/menu.png) | ![](docs/sync.png) |

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

# ⚙️ Built-in Tools

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
- [ ] Better export formats

### v2.4

- [ ] Duplicate alias detection
- [ ] Improved statistics

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