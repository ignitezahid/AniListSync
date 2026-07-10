import json
import msvcrt
import re
import time
from datetime import datetime
from pathlib import Path

import requests

from utils.constants import (
    ALIASES_FILE, BACKUP_DIR, CACHE_FILE, EXPORT_DIR,
    RESUME_FILE, RETRY_FILE, SETTINGS_FILE,
)
from utils.file_utils import load_json, save_json
from utils.ui import success, warning, show_header
from core.plugin_loader import plugin_manager
from settings import DEFAULT_SETTINGS
from config import ANILIST_TOKEN, API_ID, API_HASH
from modes.alias_manager import detect_duplicates
from modes.repair import repair as run_repair
from modes.retry_queue import retry_queue_menu
from .backup import _clean_old_backups
from .common import _export_dataset


def _health_input():
    """Read input with ESC support. Returns the string or None if ESC pressed.
    Safe to call from GUI (no console) — returns None immediately."""
    buf = ""
    try:
        msvcrt.kbhit()
    except RuntimeError:
        return None
    while True:
        try:
            if msvcrt.kbhit():
                key = msvcrt.getch()
                if key == b"\x1b":
                    return None
                if key == b"\r":
                    return buf
                if key == b"\x7f" or key == b"\x08":
                    buf = buf[:-1]
                    print("\b \b", end="", flush=True)
                elif key in (b"\xe0", b"\x00"):
                    msvcrt.getch()
                else:
                    try:
                        ch = key.decode("utf-8")
                        buf += ch
                        print(ch, end="", flush=True)
                    except UnicodeDecodeError:
                        pass
        except RuntimeError:
            return None


def _export_health_report(pct, groups, issues):
    name = f"health_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
    rows = []
    for group_name, items in groups:
        for item_name, status in items:
            rows.append({"Section": f"{group_name} / {item_name}", "Status": status})
    if issues:
        for issue in issues:
            rows.append({"Section": "Suggestion", "Status": issue})
    rows.append({"Section": "Overall", "Status": f"{pct}%"})
    json_data = {
        "health_pct": pct,
        "timestamp": datetime.now().isoformat(),
        "groups": [
            {"group": group_name, "checks": [{"name": n, "status": s} for n, s in items]}
            for group_name, items in groups
        ],
        "issues": issues,
    }
    _export_dataset(name, json_data, rows, ["Section", "Status"])


def _compute_health_score():
    issues = []
    total_checks = 12
    passed = 0

    aliases = load_json(ALIASES_FILE, {})
    broken = [k for k, v in aliases.items() if not v or not v.get("id")]
    dup_count = 0
    seen = set()
    for k in aliases:
        key = re.sub(r"[^a-zA-Z0-9]", "", k).lower()
        if key in seen:
            dup_count += 1
        seen.add(key)
    if not broken and not dup_count:
        passed += 1
    if not dup_count:
        passed += 1

    cache = load_json(CACHE_FILE, {})
    cache_age_days = None
    try:
        mtime = Path(CACHE_FILE).stat().st_mtime
        cache_age_days = int((time.time() - mtime) / 86400)
    except Exception:
        pass
    if cache and (cache_age_days is None or cache_age_days <= 30):
        passed += 1

    retry = load_json(RETRY_FILE, [])
    if not retry:
        passed += 1

    resume = load_json(RESUME_FILE, {})
    resume_ok = True
    if not resume:
        resume_ok = False
    else:
        msg_id = resume.get("last_message_id")
        if msg_id is None or not isinstance(msg_id, int) or msg_id < 0:
            resume_ok = False
    if resume_ok:
        passed += 1

    backup_count = 0
    try:
        backup_path = Path(BACKUP_DIR)
        if backup_path.is_dir():
            backup_count = len(list(backup_path.iterdir()))
    except Exception:
        pass
    if backup_count <= 100:
        passed += 1

    export_issues = 0
    export_dir = Path(EXPORT_DIR)
    if not export_dir.is_dir():
        export_issues += 1
    else:
        export_files = list(export_dir.iterdir())
        if not export_files:
            export_issues += 1
        else:
            corrupted = 0
            for f in export_files:
                if f.suffix == ".json":
                    try:
                        json.loads(f.read_text(encoding="utf-8"))
                    except Exception:
                        corrupted += 1
            if corrupted:
                export_issues += 1
    if not export_issues:
        passed += 1

    settings = load_json(SETTINGS_FILE, {})
    config_issues = 0
    if not isinstance(settings, dict):
        config_issues += 1
    else:
        missing = [k for k in DEFAULT_SETTINGS if k not in settings]
        if missing:
            config_issues += 1
        unknown = [k for k in settings if k not in DEFAULT_SETTINGS]
        if unknown:
            config_issues += 1
        invalid = []
        for k, v in DEFAULT_SETTINGS.items():
            if k in settings and settings[k] is not None and not isinstance(settings[k], type(v)):
                invalid.append(k)
        if invalid:
            config_issues += 1
    if not config_issues:
        passed += 1

    missing_mal = 0
    try:
        with open("state.json", encoding="utf-8") as f:
            state = json.load(f)
        mal_ids = state.get("mal_ids", [])
        missing_mal = sum(1 for mid in mal_ids if not mid)
        if not missing_mal:
            passed += 1
    except Exception:
        pass

    cred_issues = 0
    if not ANILIST_TOKEN or ANILIST_TOKEN == "your_anilist_access_token":
        cred_issues += 1
    else:
        try:
            r = requests.post(
                "https://graphql.anilist.co",
                json={"query": "{ Viewer { id } }"},
                headers={"Authorization": f"Bearer {ANILIST_TOKEN}"},
                timeout=10,
            )
            if r.status_code != 200:
                cred_issues += 1
        except Exception:
            cred_issues += 1
    mal_tokens = load_json("mal_tokens.json", {})
    if not mal_tokens or not mal_tokens.get("access_token"):
        cred_issues += 1
    else:
        expires = mal_tokens.get("expires_at", 0)
        if time.time() >= expires:
            cred_issues += 1
    if not cred_issues:
        passed += 1

    telegram_ok = True
    if not API_ID or API_ID == 0:
        telegram_ok = False
    if not API_HASH or API_HASH == "your_telegram_api_hash":
        telegram_ok = False
    if not Path("telegram_session.session").exists():
        telegram_ok = False
    if telegram_ok:
        passed += 1

    anilist_ok = True
    try:
        with open("state.json", encoding="utf-8") as f:
            state = json.load(f)
        if not state.get("anilist_ids", []):
            anilist_ok = False
    except Exception:
        anilist_ok = False
    if anilist_ok:
        passed += 1

    pct = int(passed / total_checks * 100) if total_checks else 100

    groups = [
        ("Library", [
            ("Aliases",
             "✓ OK" if not broken and not dup_count
             else f"⚠ {len(broken)} broken, {dup_count} dup" if broken and dup_count
             else f"⚠ {len(broken)} broken" if broken
             else f"⚠ {dup_count} dup"),
            ("Retry Queue", "✓ Empty" if not retry else f"⚠ {len(retry)} pending"),
        ]),
        ("Storage", [
            ("Search Cache",
             f"✓ {len(cache)} entries" if cache and (cache_age_days is None or cache_age_days <= 30)
             else f"⚠ {len(cache)} entries, {cache_age_days}d" if cache
             else "⚠ Empty"),
            ("Exports", "✓ OK" if not export_issues else "⚠ Issues"),
            ("Backups", f"✓ {backup_count}" if backup_count <= 100 else f"⚠ {backup_count}"),
        ]),
        ("Accounts", [
            ("API Credentials", "✓ OK" if not cred_issues else "⚠ Issues"),
            ("Telegram", "✓ OK" if telegram_ok else "⚠ Issues"),
            ("AniList", "✓ OK" if anilist_ok else "⚠ Missing"),
            ("MyAnimeList", "✓ OK" if not missing_mal else f"⚠ {missing_mal} missing"),
        ]),
        ("Configuration", [
            ("Settings", "✓ OK" if not config_issues else "⚠ Issues"),
            ("Resume File", "✓ OK" if resume_ok else "⚠ Issues"),
        ]),
    ]

    issues = []
    if broken:
        issues.append(f"⚠ {len(broken)} broken aliases")
    if dup_count:
        issues.append(f"⚠ {dup_count} duplicate aliases")
    if cache and cache_age_days is not None and cache_age_days > 30:
        issues.append(f"⚠ Cache hasn't been refreshed in {cache_age_days} days ({len(cache)} entries)")
    elif not cache:
        issues.append("⚠ Search cache is empty")
    if retry:
        issues.append(f"⚠ {len(retry)} entries in retry queue")
    if not resume:
        issues.append("⚠ Resume file is missing or empty")
    elif not resume_ok:
        issues.append("⚠ Resume file has invalid last_message_id")
    if backup_count > 100:
        issues.append(f"⚠ Large backup folder ({backup_count} backups)")
    if export_issues:
        if not export_dir.is_dir():
            issues.append("⚠ Export folder is missing")
        elif not list(export_dir.iterdir()):
            issues.append("⚠ Export folder is empty")
        else:
            issues.append(f"⚠ {corrupted} corrupted export files")
    if not isinstance(settings, dict):
        issues.append("⚠ Settings file is corrupted")
    else:
        if missing:
            issues.append(f"⚠ {len(missing)} missing settings")
        if unknown:
            issues.append(f"⚠ {len(unknown)} unknown settings keys")
        if invalid:
            issues.append(f"⚠ {len(invalid)} settings with wrong type")
    if missing_mal:
        issues.append(f"⚠ {missing_mal} entries missing MAL IDs")
    if cred_issues:
        if not ANILIST_TOKEN or ANILIST_TOKEN == "your_anilist_access_token":
            issues.append("⚠ AniList token missing or placeholder")
        else:
            issues.append("⚠ AniList token is invalid or expired")
        if not mal_tokens or not mal_tokens.get("access_token"):
            issues.append("⚠ MAL tokens missing")
        elif time.time() >= mal_tokens.get("expires_at", 0):
            issues.append("⚠ MAL token is expired")
    if not telegram_ok:
        if not API_ID or API_ID == 0:
            issues.append("⚠ Telegram API_ID not configured")
        if not API_HASH or API_HASH == "your_telegram_api_hash":
            issues.append("⚠ Telegram API_HASH not configured")
        if not Path("telegram_session.session").exists():
            issues.append("⚠ Telegram session file missing")
    if not anilist_ok:
        issues.append("⚠ AniList library not loaded")

    return pct, groups, issues


def library_health():
    show_header("Library Health")
    print()

    pct, groups, issues = _compute_health_score()
    color = "🟢" if pct >= 80 else ("🟡" if pct >= 50 else "🔴")

    show_header(f"Library Health — {pct}% {color}")
    print()

    for group_name, items in groups:
        print(group_name)
        print("─" * 40)
        for name, status in items:
            print(f"  {status}  {name}")
        print()

    try:
        with open("state.json", encoding="utf-8") as f:
            state = json.load(f)
        state["health_pct"] = pct
        with open("state.json", "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception:
        pass

    plugin_manager.call_hook("on_health_scan")

    _interactive_loop(pct, groups, issues)


def library_health_text() -> str:
    """Run health check and return formatted output as plain text (no interactive loop).
    Safe to call from a background thread."""
    pct, groups, issues = _compute_health_score()
    # Save health_pct to state and notify plugins (same as library_health() does)
    try:
        with open("state.json", encoding="utf-8") as f:
            state = json.load(f)
        state["health_pct"] = pct
        with open("state.json", "w", encoding="utf-8") as f:
            json.dump(state, f)
    except Exception:
        pass
    plugin_manager.call_hook("on_health_scan")
    lines = []
    color = "🟢" if pct >= 80 else ("🟡" if pct >= 50 else "🔴")
    lines.append(f"Library Health — {pct}% {color}")
    lines.append("")
    for group_name, items in groups:
        lines.append(f"  {group_name}")
        lines.append("  " + "─" * 40)
        for name, status in items:
            lines.append(f"    {status}  {name}")
        lines.append("")
    if issues:
        lines.append("  Suggestions")
        lines.append("  " + "─" * 40)
        for issue in issues:
            lines.append(f"    {issue}")
        lines.append("")
    return "\n".join(lines)


def _interactive_loop(pct, groups, issues):
    while True:
        if issues:
            print("Suggestions")
            print("─" * 40)
            for i, issue in enumerate(issues, 1):
                if "duplicate" in issue.lower():
                    label = "Merge duplicate aliases"
                elif "mal id" in issue.lower():
                    label = "Repair missing MAL IDs"
                elif "retry" in issue.lower():
                    label = "Retry failed titles"
                elif "broken" in issue.lower():
                    label = "Fix broken aliases"
                elif "cache" in issue.lower():
                    label = "Refresh stale cache"
                elif "backup" in issue.lower():
                    label = "Clean old backups"
                elif "resume" in issue.lower():
                    label = "Review resume file"
                elif "export" in issue.lower() or "corrupted" in issue.lower():
                    label = "Review exports"
                elif "missing setting" in issue.lower():
                    label = "Add missing settings"
                elif "unknown setting" in issue.lower():
                    label = "Review unknown settings"
                elif "wrong type" in issue.lower():
                    label = "Fix setting types"
                elif "token" in issue.lower():
                    label = "Fix API credentials"
                elif "telegram" in issue.lower():
                    label = "Fix Telegram connection"
                elif "anilist library" in issue.lower():
                    label = "Sync AniList library"
                else:
                    label = issue
                print(f"  {i}. {label}")
            print()

        print("  0. Export report")
        warning("Press ESC to return.")
        print()
        print("Fix: ", end="", flush=True)

        choice = _health_input()
        print()
        if choice is None:
            return
        if choice == "0":
            _export_health_report(pct, groups, issues)
            continue
        if choice.isdigit() and issues:
            idx = int(choice) - 1
            issue_types = []
            for issue in issues:
                if "duplicate" in issue.lower():
                    issue_types.append("aliases")
                elif "mal id" in issue.lower():
                    issue_types.append("repair")
                elif "retry" in issue.lower():
                    issue_types.append("retry")
                elif "broken" in issue.lower():
                    issue_types.append("aliases")
                elif "cache" in issue.lower():
                    issue_types.append("cache")
                elif "backup" in issue.lower():
                    issue_types.append("backup")
                elif "resume" in issue.lower():
                    issue_types.append("resume")
                elif "export" in issue.lower() or "corrupted" in issue.lower():
                    issue_types.append("export")
                elif "missing setting" in issue.lower() or "wrong type" in issue.lower():
                    issue_types.append("config")
                elif "token" in issue.lower():
                    issue_types.append("creds")
                elif "telegram" in issue.lower():
                    issue_types.append("telegram")
                elif "anilist library" in issue.lower():
                    issue_types.append("sync")
                else:
                    issue_types.append(None)
            if 0 <= idx < len(issue_types):
                action = issue_types[idx]
                if action == "aliases":
                    detect_duplicates()
                    continue
                elif action == "repair":
                    run_repair()
                    continue
                elif action == "retry":
                    retry_queue_menu()
                    continue
                elif action == "cache":
                    from modes.search_cache import search_cache_menu
                    search_cache_menu()
                    continue
                elif action == "backup":
                    _clean_old_backups()
                    continue
                elif action == "resume":
                    save_json(RESUME_FILE, {"last_message_id": 0})
                    success("Resume file reset to last_message_id: 0.")
                    continue
                elif action == "export":
                    warning("No automated fix — review exports/ folder manually.")
                elif action == "config":
                    fixed = dict(load_json(SETTINGS_FILE, {}))
                    for k, v in DEFAULT_SETTINGS.items():
                        fixed.setdefault(k, v)
                    fixed = {k: v for k, v in fixed.items() if k in DEFAULT_SETTINGS}
                    for k, v in DEFAULT_SETTINGS.items():
                        if k in fixed and fixed[k] is not None and not isinstance(fixed[k], type(v)):
                            fixed[k] = v
                    save_json(SETTINGS_FILE, fixed)
                    success("Configuration repaired.")
                    continue
                elif action == "creds":
                    warning("No automated fix — check config.py and mal_tokens.json manually.")
                elif action == "telegram":
                    warning("No automated fix — check config.py and telegram_session.session manually.")
                elif action == "sync":
                    warning("Run a full sync to populate library data.")
