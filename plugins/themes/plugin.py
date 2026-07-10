THEMES = {
    "Dracula": {
        "title": "bold magenta",
        "success": "bold bright_green",
        "warning": "bold bright_yellow",
        "error": "bold bright_red",
        "info": "bold bright_cyan",
        "menu": "bold white",
        "border": "bright_magenta",
        "bg": "#282A36",
    },
    "Catppuccin": {
        "title": "bold bright_blue",
        "success": "bold green",
        "warning": "bright_yellow",
        "error": "bright_red",
        "info": "bold bright_cyan",
        "menu": "bold white",
        "border": "bright_blue",
        "bg": "#1E1E2E",
    },
    "Nord": {
        "title": "underline bright_cyan",
        "success": "bold bright_green",
        "warning": "bold yellow",
        "error": "bold red",
        "info": "bold bright_blue",
        "menu": "bold white",
        "border": "cyan",
        "bg": "#2E3440",
    },
    "Tokyo Night": {
        "title": "bold blue",
        "success": "green",
        "warning": "bright_yellow",
        "error": "red",
        "info": "cyan",
        "menu": "bold white",
        "border": "bright_blue",
        "bg": "#1A1B26",
    },
    "Solarized Light": {
        "title": "bold bright_black",
        "success": "bold green",
        "warning": "bold yellow",
        "error": "bold red",
        "info": "bold blue",
        "menu": "dim bright_black",
        "border": "bright_black",
        "bg": "#E8DCC4",
    },
    "Matrix": {
        "title": "bold #00FF41",
        "success": "#00FF41",
        "warning": "bold #80FF80",
        "error": "bold #FF0044",
        "info": "#00FF41",
        "menu": "bold #00CC33",
        "border": "#00FF41",
        "bg": "#001100",
    },
    "Gruvbox": {
        "title": "bold #FABD2F",
        "success": "bold #B8BB26",
        "warning": "bold #FE8019",
        "error": "bold #FB4934",
        "info": "bold #83A598",
        "menu": "bold #EBDBB2",
        "border": "#FABD2F",
        "bg": "#282828",
    },
}

ACTIVE_KEY = "active"


class Plugin:
    @property
    def theme(self):
        name = self.settings.get(ACTIVE_KEY, "Default")
        raw = THEMES.get(name, {})
        return {k: v for k, v in raw.items() if k != "bg"}

    @property
    def bg_color(self) -> str | None:
        name = self.settings.get(ACTIVE_KEY, "Default")
        return THEMES.get(name, {}).get("bg")

    @property
    def active_theme_name(self) -> str:
        return self.settings.get(ACTIVE_KEY, "Default")

    @property
    def total_themes(self) -> int:
        return len(THEMES)

    def on_load(self):
        if ACTIVE_KEY not in self.settings:
            self.settings[ACTIVE_KEY] = "Default"
            self.save_settings()
        self.log(f"Themes plugin loaded. Active: {self.settings[ACTIVE_KEY]}")

    def _apply(self, name: str):
        self.settings[ACTIVE_KEY] = name
        self.settings["bg"] = THEMES.get(name, {}).get("bg", "#1a1b26")
        self.save_settings()
        from utils.ui import reload_theme
        reload_theme()

    def get_commands(self):
        return [
            ("Switch Theme", self._switch_theme),
            ("Show Current", self._show_current),
        ]

    def _switch_theme(self):
        names = list(THEMES.keys()) + ["Default"]
        current = self.settings.get(ACTIVE_KEY, "Default")
        print()
        for i, name in enumerate(names, 1):
            marker = ">" if name == current else " "
            print(f"  {marker} {i}. {name}")
        print()
        try:
            pick = input("  Pick a theme: ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        if pick.isdigit():
            idx = int(pick) - 1
            if 0 <= idx < len(names):
                self._apply(names[idx])
                print(f"  Theme switched to '{names[idx]}'.")
        elif pick and pick in names:
            self._apply(pick)
            print(f"  Theme switched to '{pick}'.")

    def _show_current(self):
        print(f"  Active theme: {self.settings.get(ACTIVE_KEY, 'Default')}")
