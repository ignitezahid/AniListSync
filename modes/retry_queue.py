from utils.constants import RETRY_FILE
from utils.file_utils import load_json, save_json
from utils.ui import (
    show_menu,
    show_header,
    show_list_table,
    ask,
    pause,
    success,
    warning,
)


def retry_queue_menu():
    while True:
        choice = show_menu(
            "Retry Queue",
            [
                "View Queue",
                "Remove Titles",
                "Clear Queue",
                "Back",
            ],
        )

        if choice == "1":
            view_retry_queue()

        elif choice == "2":
            remove_retry_titles()

        elif choice == "3":
            clear_retry_queue()

        elif choice == "4":
            return

        else:
            warning("Invalid choice.")


def view_retry_queue():
    retry_queue = load_json(RETRY_FILE, [])

    if not retry_queue:
        show_header("Retry Queue")
        success("Retry queue is empty.")
        pause()
        return

    show_list_table(
        "Retry Queue",
        retry_queue,
        "Retry Title",
    )

    pause()

def remove_retry_titles():
    retry_queue = load_json(RETRY_FILE, [])

    if not retry_queue:
        show_header("Remove Retry Titles")
        success("Retry queue is empty.")
        pause()
        return

    show_list_table(
        "Remove Retry Titles",
        retry_queue,
        "Retry Title",
    )

    selection = ask("Numbers to remove (comma separated):")

    try:
        indexes = {
            int(x.strip()) - 1
            for x in selection.split(",")
        }
    except ValueError:
        warning("Invalid input.")
        pause()
        return

    new_queue = [
        title
        for i, title in enumerate(retry_queue)
        if i not in indexes
    ]

    removed = len(retry_queue) - len(new_queue)

    save_json(RETRY_FILE, new_queue)

    remaining = len(new_queue)
    success(f"Removed {removed} title(s).")

    if remaining:
        warning(f"{remaining} title(s) remaining in the retry queue.")
    else:
        success("Retry queue is now empty.")
    pause()


def clear_retry_queue():
    retry_queue = load_json(RETRY_FILE, [])

    if not retry_queue:
        show_header("Clear Retry Queue")
        success("Retry queue is already empty.")
        pause()
        return

    confirm = ask("Clear the retry queue? (y/n):").lower()

    if confirm not in ("y", "yes"):
        warning("Cancelled.")
        pause()
        return

    save_json(RETRY_FILE, [])

    success("Retry queue cleared.")
    pause()