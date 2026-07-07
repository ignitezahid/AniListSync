# Telegram API credentials
API_ID = 0
API_HASH = "your_telegram_api_hash"

# MyAnimeList OAuth credentials
MAL_CLIENT_ID = "your_mal_client_id"
MAL_CLIENT_SECRET = "your_mal_client_secret"

# AniList OAuth access token
ANILIST_TOKEN = "your_anilist_access_token"

# Default AniList status for newly added anime
DEFAULT_STATUS = "COMPLETED"

# Session file name
SESSION_NAME = "telegram_session"

# Telegram chat sources to sync from (default: "me" = Saved Messages)
# Add usernames with @, channel links, or group IDs:
#   TELEGRAM_SOURCES = ["me", "@animechannel", "https://t.me/joinchat/..."]
# Configured via settings.json → "telegram_sources"

# Additional Telegram accounts for multi-account support
# Each account needs its own API credentials and session file.
# TELEGRAM_ACCOUNTS = [
#     {"api_id": 123456, "api_hash": "abc123", "session_name": "alt_session"},
# ]

# Files used by the project
STATE_FILE = "state.json"
FAILED_FILE = "failed_titles.txt"

