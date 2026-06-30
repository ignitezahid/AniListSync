from utils.startup import startup_checks

startup_checks()

import traceback

from telegram_client import client
from sync import main as sync_main
from menu import show_main_menu
from utils.ui import success, warning

while True:

    choice = show_main_menu()

    if choice == "1":

        try:

            with client:
                client.loop.run_until_complete(sync_main())

        except Exception:

            with open(
                "logs/error.log",
                "a",
                encoding="utf-8"
            ) as f:

                traceback.print_exc(file=f)

            traceback.print_exc()

    elif choice == "2":

        from modes.compare import compare

        with client:
            client.loop.run_until_complete(compare())

    elif choice == "3":

        from modes.repair import repair

        repair()

    elif choice == "4":

        from modes.tools import data_center

        client.loop.run_until_complete(data_center())

    elif choice == "5":

        from modes.statistics import statistics

        statistics()

    elif choice == "6":

        success("Goodbye!")
        break

    else:

        warning("Invalid choice.")
