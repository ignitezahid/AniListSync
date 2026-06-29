from version import CREATOR, VERSION


def show_menu():

    print()
    print("=" * 45)
    print(
        f"Anime Library Manager v{VERSION}"
    )
    print(
        f"by {CREATOR}"
    )
    print("=" * 45)
    print()

    print("1. Sync")
    print("2. Compare")
    print("3. Repair")
    print("4. Tools")
    print("5. Statistics")
    print("6. Exit")
    print()

    return input("Choice: ").strip()
