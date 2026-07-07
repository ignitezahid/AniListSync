import importlib.util
import json
from datetime import datetime
from pathlib import Path
from typing import Callable

from version import VERSION

PLUGINS_DIR = Path("plugins")
PLUGINS_STATE = Path("data/plugins.json")
PLUGIN_LOGS_DIR = Path("logs/plugins")
PLUGIN_DATA_DIR = Path("data/plugins")


def _parse_version(v: str) -> tuple[int, ...]:
    try:
        return tuple(int(x) for x in v.split("."))
    except Exception:
        return (0,)


def _topological_sort(manifests: dict[str, dict]) -> list[str]:
    sorted_ids: list[str] = []
    visited: set[str] = set()
    temp: set[str] = set()

    def visit(pid: str):
        if pid in temp:
            return
        if pid in visited:
            return
        manifest = manifests.get(pid)
        if not manifest:
            visited.add(pid)
            return
        temp.add(pid)
        for dep in manifest.get("depends", []):
            visit(dep)
        temp.discard(pid)
        visited.add(pid)
        sorted_ids.append(pid)

    for pid in manifests:
        visit(pid)
    return sorted_ids


class PluginError:
    def __init__(self, pid: str, message: str, manifest: dict | None = None):
        self.pid = pid
        self.message = message
        self.manifest = manifest or {}


class PluginManager:
    def __init__(self):
        self._plugins: dict[str, object] = {}
        self._manifests: dict[str, dict] = {}
        self._enabled: dict[str, bool] = {}
        self._errors: dict[str, PluginError] = {}
        self._settings: dict[str, dict] = {}
        self._permissions_consent: dict[str, list[str]] = {}
        self._loaded_at: dict[str, str] = {}

    def discover(self):
        self._plugins.clear()
        self._manifests.clear()
        self._errors.clear()
        self._load_state()
        PLUGIN_LOGS_DIR.mkdir(parents=True, exist_ok=True)
        PLUGIN_DATA_DIR.mkdir(parents=True, exist_ok=True)

        if not PLUGINS_DIR.is_dir():
            return

        for folder in sorted(PLUGINS_DIR.iterdir()):
            if not folder.is_dir():
                continue
            manifest_path = folder / "manifest.json"
            if not manifest_path.exists():
                continue
            manifest = self._validate_manifest(manifest_path)
            if manifest:
                pid = manifest["id"]
                self._manifests[pid] = manifest
                if not self._check_compatibility(pid, manifest):
                    continue

        ordered = _topological_sort(self._manifests)
        for pid in ordered:
            if self._enabled.get(pid, True) and pid not in self._plugins and pid not in self._errors:
                folder = PLUGINS_DIR / pid
                self._load_plugin(folder, self._manifests[pid])

    def _validate_manifest(self, path: Path) -> dict | None:
        try:
            with open(path, encoding="utf-8") as f:
                m = json.load(f)
            required = {"name", "id", "version", "entry"}
            if not required.issubset(m.keys()):
                return None
            return m
        except Exception:
            return None

    def _check_compatibility(self, pid: str, manifest: dict) -> bool:
        app_ver = _parse_version(VERSION)
        min_ver = manifest.get("min_app_version")
        max_ver = manifest.get("max_app_version")
        if min_ver and app_ver < _parse_version(min_ver):
            self._errors[pid] = PluginError(
                pid, f"Requires AniListSync {min_ver}+ (current: {VERSION})", manifest
            )
            return False
        if max_ver and app_ver > _parse_version(max_ver):
            self._errors[pid] = PluginError(
                pid, f"Requires AniListSync <= {max_ver} (current: {VERSION})", manifest
            )
            return False
        return True

    def _load_plugin(self, folder: Path, manifest: dict):
        pid = manifest["id"]
        entry_path = folder / manifest["entry"]
        if not entry_path.exists():
            self._errors[pid] = PluginError(
                pid, f"Entry file '{manifest['entry']}' not found", manifest
            )
            return
        try:
            spec = importlib.util.spec_from_file_location(pid, entry_path)
            if not spec or not spec.loader:
                self._errors[pid] = PluginError(pid, "Failed to create module spec", manifest)
                return
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
        except Exception as e:
            self._errors[pid] = PluginError(pid, f"Import error: {e}", manifest)
            return

        if not hasattr(mod, "Plugin"):
            self._errors[pid] = PluginError(pid, "No 'Plugin' class found", manifest)
            return

        try:
            instance = mod.Plugin()
        except Exception as e:
            self._errors[pid] = PluginError(pid, f"Instantiation error: {e}", manifest)
            return

        instance._plugin_id = pid
        self._inject_settings(instance, pid)
        self._inject_logger(instance, pid)

        if not self._check_permissions(pid, manifest):
            self.grant_permissions(pid, interactive=False)

        self._plugins[pid] = instance
        self._loaded_at[pid] = datetime.now().strftime("%I:%M %p")

    def _inject_settings(self, instance: object, pid: str):
        settings_path = PLUGIN_DATA_DIR / f"{pid}.json"
        if settings_path.exists():
            try:
                with open(settings_path, encoding="utf-8") as f:
                    settings = json.load(f)
            except Exception:
                settings = {}
        else:
            settings = {}
            settings_path.parent.mkdir(parents=True, exist_ok=True)
            with open(settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, indent=2)
        self._settings[pid] = settings
        instance.settings = settings

        def _save_settings():
            try:
                with open(settings_path, "w", encoding="utf-8") as f:
                    json.dump(self._settings.get(pid, {}), f, indent=2)
            except Exception:
                pass

        instance.save_settings = _save_settings

    def _inject_logger(self, instance: object, pid: str):
        log_path = PLUGIN_LOGS_DIR / f"{pid}.log"
        instance.log_path = log_path

        def _log(msg: str, level: str = "INFO"):
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            line = f"[{timestamp}] [{level}] {msg}\n"
            try:
                with open(log_path, "a", encoding="utf-8") as f:
                    f.write(line)
            except Exception:
                pass

        instance.log = _log

    def _check_permissions(self, pid: str, manifest: dict) -> bool:
        required = manifest.get("permissions", [])
        if not required:
            return True
        granted = self._permissions_consent.get(pid, [])
        return all(p in granted for p in required)

    def grant_permissions(self, pid: str, interactive: bool = True) -> bool:
        manifest = self._manifests.get(pid)
        if not manifest:
            return False
        required = manifest.get("permissions", [])
        if not required:
            return True
        if not interactive:
            self._permissions_consent[pid] = required
            return True
        print(f"\n  Plugin [{manifest.get('name', pid)}] requests:")
        for p in required:
            print(f"    - {p}")
        print()
        try:
            resp = input("  Grant permissions? (y/N): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            resp = "n"
        if resp == "y":
            self._permissions_consent[pid] = required
            return True
        return False

    def _load_state(self):
        try:
            with open(PLUGINS_STATE, encoding="utf-8") as f:
                data = json.load(f)
            self._enabled = data.get("enabled", {})
            self._permissions_consent = data.get("permissions", {})
        except Exception:
            self._enabled = {}
            self._permissions_consent = {}

    def _save_state(self):
        PLUGINS_STATE.parent.mkdir(parents=True, exist_ok=True)
        with open(PLUGINS_STATE, "w", encoding="utf-8") as f:
            json.dump({
                "enabled": self._enabled,
                "permissions": self._permissions_consent,
            }, f, indent=2)

    def is_enabled(self, pid: str) -> bool:
        return self._enabled.get(pid, True)

    def enable(self, pid: str):
        if not self._check_permissions(pid, self._manifests.get(pid, {})):
            if not self.grant_permissions(pid):
                return
        self._enabled[pid] = True
        self._save_state()
        if pid in self._manifests and pid not in self._plugins:
            folder = PLUGINS_DIR / pid
            self._errors.pop(pid, None)
            self._load_plugin(folder, self._manifests[pid])

    def disable(self, pid: str):
        self._enabled[pid] = False
        self._save_state()
        instance = self._plugins.pop(pid, None)
        if instance:
            self._call_method(instance, pid, "on_unload")

    def reload(self, pid: str):
        self._plugins.pop(pid, None)
        self._errors.pop(pid, None)
        if pid in self._manifests and self.is_enabled(pid):
            folder = PLUGINS_DIR / pid
            self._load_plugin(folder, self._manifests[pid])

    def has_error(self, pid: str) -> bool:
        return pid in self._errors

    def get_error(self, pid: str) -> PluginError | None:
        return self._errors.get(pid)

    def call_hook(self, hook_name: str, *args, **kwargs):
        for pid in list(self._plugins.keys()):
            if not self.is_enabled(pid):
                continue
            instance = self._plugins.get(pid)
            if not instance:
                continue
            self._call_method(instance, pid, hook_name, *args, **kwargs)

    def _call_method(self, instance: object, pid: str, method_name: str, *args, **kwargs):
        method = getattr(instance, method_name, None)
        if not method:
            return
        try:
            method(*args, **kwargs)
        except Exception as e:
            msg = f"{method_name} error: {e}"
            self._log_error(pid, msg)

    def _log_error(self, pid: str, msg: str):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        log_path = PLUGIN_LOGS_DIR / f"{pid}.log"
        try:
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"[{timestamp}] [ERROR] {msg}\n")
        except Exception:
            pass

    def get_theme_plugins(self) -> list[tuple[str, dict]]:
        result: list[tuple[str, dict]] = []
        for pid in list(self._plugins.keys()):
            if not self.is_enabled(pid):
                continue
            manifest = self._manifests.get(pid)
            if manifest and manifest.get("type") == "theme":
                instance = self._plugins.get(pid)
                if instance and hasattr(instance, "theme"):
                    result.append((pid, instance.theme))
        return result

    def get_theme(self) -> dict | None:
        merged: dict = {}
        for pid in list(self._plugins.keys()):
            if not self.is_enabled(pid):
                continue
            manifest = self._manifests.get(pid)
            if manifest and manifest.get("type") == "theme":
                instance = self._plugins.get(pid)
                if instance and hasattr(instance, "theme"):
                    merged.update(instance.theme)
        return merged or None

    def get_total_themes(self) -> int:
        total = 0
        for pid in list(self._plugins.keys()):
            if not self.is_enabled(pid):
                continue
            manifest = self._manifests.get(pid)
            if manifest and manifest.get("type") == "theme":
                instance = self._plugins.get(pid)
                if instance and hasattr(instance, "total_themes"):
                    total += instance.total_themes
        return total or len([p for p in self._manifests if self._manifests[p].get("type") == "theme"])

    def get_commands(self, pid: str) -> list[tuple[str, Callable]]:
        instance = self._plugins.get(pid)
        if not instance:
            return []
        method = getattr(instance, "get_commands", None)
        if not method:
            return []
        try:
            return method()
        except Exception:
            return []

    def get_plugins(self) -> list[tuple[str, dict, bool]]:
        result = []
        for pid, manifest in self._manifests.items():
            result.append((pid, manifest, pid in self._plugins))
        return sorted(result, key=lambda x: x[1].get("name", ""))

    def get_loaded_at(self, pid: str) -> str:
        return self._loaded_at.get(pid, "-")

    def count_hooks(self, pid: str) -> int:
        instance = self._plugins.get(pid)
        if not instance:
            return 0
        count = 0
        for attr in dir(instance):
            if attr.startswith("on_") and callable(getattr(instance, attr)):
                count += 1
        if hasattr(instance, "get_commands") and callable(instance.get_commands):
            count += 1
        return count

    def get_plugin(self, pid: str) -> object | None:
        """Return the plugin instance by ID, or None if not loaded."""
        return self._plugins.get(pid)

    def get_manifest(self, pid: str) -> dict | None:
        """Return the manifest dict for a plugin by ID, or None."""
        return self._manifests.get(pid)

    def get_errors(self) -> dict[str, PluginError]:
        """Return all plugin errors keyed by plugin ID."""
        return dict(self._errors)

    def plugin_count(self) -> int:
        """Return the total number of loaded plugins."""
        return len(self._plugins)


plugin_manager = PluginManager()
