from telethon import TelegramClient

_chat_sources: list[str] | None = None
_account_clients: list[dict] = []


def _load_config():
    import config as cfg
    return cfg


def get_chat_sources() -> list[str]:
    global _chat_sources
    if _chat_sources is None:
        from settings import get_setting
        _chat_sources = get_setting("telegram_sources", ["me"])
    return _chat_sources


def reload_chat_sources() -> None:
    global _chat_sources
    _chat_sources = None


cfg = _load_config()
_accounts_data = getattr(cfg, "TELEGRAM_ACCOUNTS", [])

if _accounts_data:
    _first = _accounts_data[0]
else:
    _first = {"api_id": cfg.API_ID, "api_hash": cfg.API_HASH, "session_name": getattr(cfg, "SESSION_NAME", "telegram_session")}
client = TelegramClient(_first["session_name"], _first["api_id"], _first["api_hash"])


def init_accounts():
    global _account_clients
    _account_clients = []
    # Skip index 0 (primary) — module-level `client` already handles it
    for acct in _accounts_data[1:]:
        c = TelegramClient(
            acct.get("session_name", f"telegram_{acct['api_id']}"),
            acct["api_id"],
            acct["api_hash"],
        )
        _account_clients.append({
            "client": c,
            "sources": acct.get("sources", ["me"]),
        })


def get_all_clients() -> list[tuple[TelegramClient, list[str]]]:
    if not _account_clients and getattr(cfg, "TELEGRAM_ACCOUNTS", None):
        init_accounts()
    result = [(client, get_chat_sources())]
    for entry in _account_clients:
        result.append((entry["client"], entry["sources"]))
    return result


def iter_all_sources():
    for c, sources in get_all_clients():
        for src in sources:
            yield c, src


async def _ensure_client_auth(c: TelegramClient) -> bool:
    try:
        if not c.is_connected():
            await c.connect()
        if not await c.is_user_authorized():
            return False
        return True
    except Exception:
        return False


async def ensure_connected() -> bool:
    primary_ok = await _ensure_client_auth(client)
    for entry in _account_clients:
        await _ensure_client_auth(entry["client"])
    return primary_ok


async def disconnect_client() -> None:
    for c in [client] + [e["client"] for e in _account_clients]:
        try:
            if getattr(c, "is_connected", lambda: False)():
                await c.disconnect()
        except Exception:
            pass
