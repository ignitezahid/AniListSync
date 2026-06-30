from version import VERSION, CREATOR
from utils.ui import show_app_header, show_menu


def show_main_menu():
    show_app_header(VERSION, CREATOR)

    return show_menu(
        "Main Menu",
        [
            "🔄  Sync",
            "🔎  Search",
            "🔍  Compare",
            "🛠  Repair",
            "🧰  Tools",
            "📊  Statistics",
            "🚪  Exit",
        ],
    )