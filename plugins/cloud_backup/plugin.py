import zipfile
import io
import requests
from datetime import datetime
from pathlib import Path

BACKUP_DIR = Path("backups")
STATE_FILE = Path("state.json")


def _create_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if BACKUP_DIR.is_dir():
            for fp in sorted(BACKUP_DIR.iterdir()):
                if fp.is_file():
                    zf.write(fp, f"backups/{fp.name}")
        for name in ["state.json", "settings.json", "aliases.json", "retry_queue.json", "search_cache.json", "resume.json", "collections.json"]:
            p = Path(name)
            if p.exists():
                zf.write(p, name)
    buf.seek(0)
    return buf.read()


class BackupProvider:
    """Base class for cloud backup providers."""

    @property
    def name(self) -> str:
        return "base"

    def label(self) -> str:
        return self.name

    def fields(self) -> list[dict]:
        """Return field definitions for configure UI.
        Each entry: {"key": str, "label": str, "secret": bool}
        """
        return []

    def configure(self, settings: dict, log):
        """Prompt user for provider settings. Mutates settings in place."""
        for f in self.fields():
            current = settings.get(f["key"], "")
            prompt = f"  {f['label']} [{current}]: "
            try:
                val = input(prompt).strip()
                if val:
                    settings[f["key"]] = val
            except (EOFError, KeyboardInterrupt):
                return

    def validate(self, settings: dict) -> str | None:
        """Return error string if settings are incomplete, else None."""
        for f in self.fields():
            if f["key"] == "keep_last":
                continue
            if not settings.get(f["key"]):
                return f"Missing {f['label']}"
        return None

    def upload(self, data: bytes, settings: dict, log) -> str | None:
        """Upload data. Return None on success, error string on failure."""
        raise NotImplementedError


class GitHubProvider(BackupProvider):
    @property
    def name(self):
        return "github"

    def label(self):
        return "GitHub Releases"

    def fields(self):
        return [
            {"key": "github_token", "label": "GitHub Token", "secret": True},
            {"key": "github_owner", "label": "GitHub Owner (user/org)", "secret": False},
            {"key": "github_repo", "label": "GitHub Repo name", "secret": False},
            {"key": "keep_last", "label": "Backups to keep", "secret": False},
        ]

    def configure(self, settings: dict, log):
        super().configure(settings, log)
        current = settings.get("keep_last", 5)
        try:
            val = input(f"  Backups to keep [{current}]: ").strip()
            if val:
                settings["keep_last"] = int(val)
        except (EOFError, KeyboardInterrupt):
            pass
        except ValueError:
            log("Invalid number for keep_last", "WARN")

    def upload(self, data: bytes, settings: dict, log) -> str | None:
        token = settings.get("github_token", "")
        owner = settings.get("github_owner", "")
        repo = settings.get("github_repo", "")
        tag = datetime.now().strftime("%Y%m%d_%H%M%S")

        release_url = f"https://api.github.com/repos/{owner}/{repo}/releases"
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }

        payload = {
            "tag_name": tag,
            "name": f"Backup {tag}",
            "body": "Auto backup from AniListSync",
            "draft": False,
            "prerelease": False,
        }

        resp = requests.post(release_url, json=payload, headers=headers, timeout=30)
        if resp.status_code not in (201, 422):
            return f"Release create failed: {resp.status_code}"

        if resp.status_code == 422:
            release_id = None
            for r in requests.get(release_url, headers=headers, timeout=30).json():
                if r.get("tag_name") == tag:
                    release_id = r["id"]
                    break
            if not release_id:
                return f"Tag {tag} exists but no release found"
            upload_url = f"https://uploads.github.com/repos/{owner}/{repo}/releases/{release_id}/assets"
        else:
            release = resp.json()
            upload_url = release["upload_url"].replace("{?name,label}", "")

        asset_name = f"anilistsync_backup_{tag}.zip"
        asset_headers = {**headers, "Content-Type": "application/zip"}
        asset_resp = requests.post(
            f"{upload_url}?name={asset_name}",
            data=data,
            headers=asset_headers,
            timeout=60,
        )
        if asset_resp.status_code not in (201, 200):
            return f"Upload failed: {asset_resp.status_code}"
        log(f"Backup uploaded as {tag} ({len(data)} bytes)")
        self._cleanup_old_releases(settings, log)
        return None

    def _cleanup_old_releases(self, settings: dict, log):
        try:
            keep = int(settings.get("keep_last", 5))
        except (ValueError, TypeError):
            keep = 5
        if keep < 1:
            return

        token = settings.get("github_token", "")
        owner = settings.get("github_owner", "")
        repo = settings.get("github_repo", "")
        headers = {
            "Authorization": f"token {token}",
            "Accept": "application/vnd.github.v3+json",
        }
        url = f"https://api.github.com/repos/{owner}/{repo}/releases"

        try:
            resp = requests.get(url, headers=headers, timeout=30)
            if resp.status_code != 200:
                return
            releases = resp.json()
            backup_releases = [
                r for r in releases
                if r.get("tag_name", "").replace("_", "").replace("-", "").isdigit()
            ]
            backup_releases.sort(key=lambda r: r.get("created_at", ""))
            to_delete = backup_releases[:-keep] if len(backup_releases) > keep else []
            for r in to_delete:
                rid = r["id"]
                tag_name = r.get("tag_name", "?")
                del_resp = requests.delete(f"{url}/{rid}", headers=headers, timeout=30)
                if del_resp.status_code == 204:
                    log(f"Deleted old release {tag_name}")
                else:
                    log(f"Failed to delete {tag_name}: {del_resp.status_code}", "WARN")
        except Exception as e:
            log(f"Cleanup error: {e}", "WARN")


PROVIDERS: dict[str, BackupProvider] = {
    "github": GitHubProvider(),
}


def _get_provider(name: str) -> BackupProvider | None:
    return PROVIDERS.get(name)


class Plugin:
    def __init__(self):
        self._pending = False

    def on_load(self):
        self.log("Cloud Backup plugin loaded")

    def on_sync_finish(self):
        if not self.settings.get("auto_upload", True):
            return
        self._do_backup()

    def on_backup(self, path):
        self._pending = True

    def _provider(self) -> BackupProvider | None:
        name = self.settings.get("provider", "github")
        p = _get_provider(name)
        if not p:
            self.log(f"Unknown provider '{name}'", "ERROR")
        return p

    def _do_backup(self):
        p = self._provider()
        if not p:
            return

        err = p.validate(self.settings)
        if err:
            self.log(f"Provider config incomplete: {err}", "WARN")
            return

        self.log("Creating backup archive…")
        try:
            data = _create_zip()
        except Exception as e:
            self.log(f"Zip creation failed: {e}", "ERROR")
            return

        self.log(f"Uploading via {p.label()} ({len(data)} bytes)…")
        err = p.upload(data, self.settings, self.log)
        if err:
            self.log(f"Upload failed: {err}", "ERROR")
        self._pending = False

    def get_commands(self):
        return [
            ("Upload Backup Now", self._cmd_upload),
            ("Configure Provider", self._cmd_configure),
        ]

    def _cmd_upload(self):
        self._do_backup()
        print("  Backup upload triggered.")

    def _cmd_configure(self):
        try:
            current_provider = self.settings.get("provider", "github")
            print(f"  Current provider: {current_provider}")
            print(f"  Available: {', '.join(PROVIDERS.keys())}")
            val = input(f"  Provider [{current_provider}]: ").strip()
            if val:
                if val not in PROVIDERS:
                    print(f"  Unknown provider '{val}'")
                    return
                self.settings["provider"] = val
                self.save_settings()
                print(f"  Provider set to '{val}'")

            p = self._provider()
            if p:
                p.configure(self.settings, self.log)
                auto = input("  Auto-upload after sync? (Y/n): ").strip().lower()
                self.settings["auto_upload"] = auto != "n"
                self.save_settings()
                print(f"  Cloud Backup settings saved (provider: {p.label()}).")
        except (EOFError, KeyboardInterrupt):
            pass
