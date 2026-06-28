<div align="center">

# AniListSync

Sync anime titles from Telegram Saved Messages to AniList and MyAnimeList.

`Python` `AniList` `MyAnimeList` `Telegram`

```text
Anime Library Manager v2.0.0
by ignitezahid
```

</div>

---

## ✨ Features

| Feature | What It Does |
| --- | --- |
| Sync | Reads anime titles from Telegram Saved Messages |
| AniList + MAL | Adds matched anime to both services |
| Alias Manager | Learns and edits title aliases |
| Repair Mode | Fixes missing or not-found anime |
| Franchise Manager | Lets you add related anime together |

## 🚀 Quick Start

- [ ] Install Python
- [ ] Clone/download this repo
- [ ] Install dependencies
- [ ] Create `config.py`
- [ ] Add your API keys
- [ ] Run `main.py`

```bash
git clone YOUR_REPO_URL
cd AniListSync
pip install -r requirements.txt
copy config.example.py config.py
python main.py
```

Use this on macOS/Linux instead of `copy`:

```bash
cp config.example.py config.py
```

## 🔑 Add Your Keys

Open `config.py` and replace the example values:

```python
API_ID = 123456
API_HASH = "your_telegram_api_hash"
MAL_CLIENT_ID = "your_mal_client_id"
MAL_CLIENT_SECRET = "your_mal_client_secret"
ANILIST_TOKEN = "your_anilist_access_token"
```

Do not edit your keys into `config.example.py`. Keep real keys only in `config.py`.

## 🔗 Get API Keys

| Service | What You Need | Link |
| --- | --- | --- |
| Telegram | `API_ID`, `API_HASH` | https://my.telegram.org/apps |
| AniList | `ANILIST_TOKEN` | https://docs.anilist.co/guide/auth/ |
| MyAnimeList | `MAL_CLIENT_ID`, `MAL_CLIENT_SECRET` | https://myanimelist.net/apiconfig |
| MyAnimeList Docs | API reference | https://myanimelist.net/apiconfig/references/api/v2 |

Notes:

- Telegram sends the login code inside Telegram.
- `API_ID` is a number, so do not put it in quotes.
- The other keys are text, so keep them in quotes.

## 🧭 Menu

When you run the app, you will see:

```text
1. Sync       Add Telegram Saved Messages to AniList/MAL
2. Compare    Find missing or not-found anime
3. Repair     Fix missing or not-found matches
4. Export     Coming soon
5. Statistics View stats
6. Exit
```

## 🔒 Security

Keep these private:

```text
API_HASH
MAL_CLIENT_SECRET
ANILIST_TOKEN
telegram_session.session
data/mal_tokens.json
```

If you accidentally upload a secret, delete it from GitHub and regenerate it.

## 🛠️ Troubleshooting

| Problem | Fix |
| --- | --- |
| `python` not found | Try `py main.py` or reinstall Python with PATH enabled |
| Missing packages | Run `pip install -r requirements.txt` |
| `config.py` missing | Copy `config.example.py` to `config.py` |
| Telegram login stuck | Delete `telegram_session.session` and log in again |
| Old missing anime still appears | Rerun Compare Mode; `missing_anilist.json` is only a saved report |
