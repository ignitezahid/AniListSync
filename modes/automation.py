from utils.ui import show_header, console, ask, warning, success
from utils.backup import backup_file
from settings import set_setting, get_setting


def _status(key: str) -> str:
    return "[green]ON[/]" if get_setting(key) else "[red]OFF[/]"


def _interval_label() -> str:
    mins = get_setting("automation_interval_minutes", 30)
    if mins < 60:
        return f"Every {mins} min"
    if mins == 60:
        return "Every hour"
    if mins < 1440:
        return f"Every {mins // 60}h"
    return f"Every {mins // 1440}d"


def automation_menu():
    while True:
        show_header("Automation")
        enabled = get_setting("automation_enabled")
        console.print(f"  Scheduled Sync   {_status('automation_enabled')}")
        if enabled:
            console.print(f"  Interval         {_interval_label()}")
        console.print()
        console.print(f"  1. Toggle Scheduled Sync  {_status('automation_enabled')}")
        console.print(f"  2. Interval               {_interval_label()}")
        console.print()
        console.print(f"  3. Sync on Startup        {_status('sync_on_startup')}")
        console.print(f"  4. Live Tracking on Startup  {_status('live_tracking_on_startup')}")
        console.print(f"  5. Auto Backup before Sync  {_status('auto_backup_before_sync')}")
        console.print(f"  6. Auto Health after Sync    {_status('auto_health_after_sync')}")
        console.print()
        console.print("  7. Back")
        console.print()
        choice = ask("Choice:")

        if choice == "1":
            set_setting("automation_enabled", not get_setting("automation_enabled"))
            if get_setting("automation_enabled"):
                success("Scheduled sync enabled.")
            else:
                warning("Scheduled sync disabled.")

        elif choice == "2":
            console.print()
            console.print("  Interval options:")
            console.print("  1. 15 minutes")
            console.print("  2. 30 minutes")
            console.print("  3. 1 hour")
            console.print("  4. 6 hours")
            console.print("  5. Daily (24 hours)")
            console.print()
            pick = ask("Pick:")
            mapping = {"1": 15, "2": 30, "3": 60, "4": 360, "5": 1440}
            if pick in mapping:
                set_setting("automation_interval_minutes", mapping[pick])
                success(f"Interval set to {mapping[pick]} minutes.")

        elif choice == "3":
            set_setting("sync_on_startup", not get_setting("sync_on_startup"))

        elif choice == "4":
            set_setting("live_tracking_on_startup", not get_setting("live_tracking_on_startup"))

        elif choice == "5":
            set_setting("auto_backup_before_sync", not get_setting("auto_backup_before_sync"))

        elif choice == "6":
            set_setting("auto_health_after_sync", not get_setting("auto_health_after_sync"))

        elif choice == "7":
            break


def run_auto_backup():
    if get_setting("auto_backup_before_sync"):
        from utils.constants import ALIASES_FILE, CACHE_FILE, RESUME_FILE, RETRY_FILE
        console.print()
        console.print("  [bold cyan]Auto Backup[/]")
        for f in [ALIASES_FILE, CACHE_FILE, RESUME_FILE, RETRY_FILE]:
            backup_file(f)
        success("Backup complete.")


def run_auto_health():
    if get_setting("auto_health_after_sync"):
        from modes.tools import _compute_health_score
        pct, _, _ = _compute_health_score()
        if pct <= 60:
            from modes.tools import library_health
            console.print()
            console.print("  [bold cyan]Auto Health Scan[/]")
            library_health()
