import zipfile
import io
import os
import requests
from datetime import datetime
from pathlib import Path

BACKUP_DIR = Path("backups")
DATA_DIR = Path("data")
STATE_FILE = Path("state.json")
DATA_FILES = [
    "settings.json", "aliases.json", "retry_queue.json",
    "search_cache.json", "resume.json", "collections.json",
]


def _create_zip() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        if BACKUP_DIR.is_dir():
            for fp in sorted(BACKUP_DIR.iterdir()):
                if fp.is_file():
                    zf.write(fp, f"backups/{fp.name}")
        for name in DATA_FILES + (["state.json"] if STATE_FILE.exists() else []):
            for base in (Path("."), DATA_DIR):
                p = base / name
                if p.exists():
                    zf.write(p, name)
                    break
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


class S3Provider(BackupProvider):
    @property
    def name(self):
        return "s3"

    def label(self):
        return "Amazon S3 / Compatible"

    def fields(self):
        return [
            {"key": "s3_access_key", "label": "Access Key ID", "secret": True},
            {"key": "s3_secret_key", "label": "Secret Access Key", "secret": True},
            {"key": "s3_bucket", "label": "Bucket name", "secret": False},
            {"key": "s3_region", "label": "Region (e.g. us-east-1)", "secret": False},
            {"key": "s3_endpoint", "label": "Endpoint URL (optional, for MinIO etc.)", "secret": False},
            {"key": "s3_prefix", "label": "Key prefix (optional, default: anilistsync_backup/)", "secret": False},
            {"key": "keep_last", "label": "Backups to keep", "secret": False},
        ]

    def configure(self, settings: dict, log):
        super().configure(settings, log)
        current = settings.get("keep_last", 10)
        try:
            val = input(f"  Backups to keep [{current}]: ").strip()
            if val:
                settings["keep_last"] = int(val)
        except (EOFError, KeyboardInterrupt):
            pass
        except ValueError:
            log("Invalid number for keep_last", "WARN")

    def _get_s3_prefix(self, settings: dict) -> str:
        return settings.get("s3_prefix", "anilistsync_backup/")

    def upload(self, data: bytes, settings: dict, log) -> str | None:
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError:
            return "boto3 not installed. Run: pip install boto3"

        access_key = settings.get("s3_access_key", "")
        secret_key = settings.get("s3_secret_key", "")
        bucket = settings.get("s3_bucket", "")
        region = settings.get("s3_region", "us-east-1")
        endpoint = settings.get("s3_endpoint", "") or None

        kwargs = {
            "aws_access_key_id": access_key,
            "aws_secret_access_key": secret_key,
            "region_name": region,
        }
        if endpoint:
            kwargs["endpoint_url"] = endpoint

        try:
            client = boto3.client("s3", **kwargs)
        except Exception as e:
            return f"Failed to create S3 client: {e}"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        prefix = self._get_s3_prefix(settings)
        key = f"{prefix}backup_{timestamp}.zip"

        try:
            client.put_object(Bucket=bucket, Key=key, Body=data, ContentType="application/zip")
        except ClientError as e:
            return f"S3 upload failed: {e}"
        except Exception as e:
            return f"S3 upload error: {e}"

        log(f"Backup uploaded to s3://{bucket}/{key} ({len(data)} bytes)")
        self._cleanup_old_s3(client, bucket, prefix, settings, log)
        return None

    def _cleanup_old_s3(self, client, bucket: str, prefix: str, settings: dict, log):
        try:
            keep = int(settings.get("keep_last", 10))
        except (ValueError, TypeError):
            keep = 10
        if keep < 1:
            return

        try:
            resp = client.list_objects_v2(Bucket=bucket, Prefix=prefix)
            objects = resp.get("Contents", [])
            if len(objects) <= keep:
                return
            objects.sort(key=lambda o: o["LastModified"])
            to_delete = objects[:-keep]
            for obj in to_delete:
                client.delete_object(Bucket=bucket, Key=obj["Key"])
                log(f"Deleted old S3 backup {obj['Key']}")
        except Exception as e:
            log(f"S3 cleanup error: {e}", "WARN")


class GDriveProvider(BackupProvider):
    @property
    def name(self):
        return "gdrive"

    def label(self):
        return "Google Drive"

    def fields(self):
        return [
            {"key": "gdrive_token_path", "label": "Token file path (optional, default: gdrive_token.json)", "secret": False},
            {"key": "gdrive_creds_path", "label": "OAuth credentials JSON path", "secret": False},
            {"key": "gdrive_folder_id", "label": "Folder ID (optional, root if empty)", "secret": False},
            {"key": "keep_last", "label": "Backups to keep", "secret": False},
        ]

    def configure(self, settings: dict, log):
        for f in self.fields():
            if f["key"] == "keep_last":
                continue
            current = settings.get(f["key"], "")
            if f["key"] == "gdrive_token_path":
                current = current or "gdrive_token.json"
            prompt = f"  {f['label']} [{current}]: "
            try:
                val = input(prompt).strip()
                if val:
                    settings[f["key"]] = val
            except (EOFError, KeyboardInterrupt):
                return
        current = settings.get("keep_last", 10)
        try:
            val = input(f"  Backups to keep [{current}]: ").strip()
            if val:
                settings["keep_last"] = int(val)
        except (EOFError, KeyboardInterrupt):
            pass
        except ValueError:
            log("Invalid number for keep_last", "WARN")

    def _get_service(self, settings: dict, log):
        try:
            from google.auth.transport.requests import Request
            from google.oauth2.credentials import Credentials
            from google_auth_oauthlib.flow import InstalledAppFlow
            from googleapiclient.discovery import build
        except ImportError:
            return None, "google-api-python-client not installed. Run: pip install google-api-python-client google-auth-oauthlib"

        token_path = settings.get("gdrive_token_path", "gdrive_token.json")
        creds_path = settings.get("gdrive_creds_path", "")
        SCOPES = ["https://www.googleapis.com/auth/drive.file"]

        creds = None
        if Path(token_path).exists():
            try:
                import json
                creds = Credentials.from_authorized_user_file(token_path, SCOPES)
            except Exception as e:
                log(f"Failed to load token: {e}", "WARN")

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                try:
                    creds.refresh(Request())
                except Exception as e:
                    log(f"Token refresh failed: {e}, re-authenticating...", "WARN")
                    creds = None
            if not creds:
                if not creds_path:
                    return None, "OAuth credentials JSON path is required for first-time auth"
                try:
                    flow = InstalledAppFlow.from_client_secrets_file(creds_path, SCOPES)
                    creds = flow.run_local_server(port=0)
                except Exception as e:
                    return None, f"OAuth flow failed: {e}"
                try:
                    import json
                    with open(token_path, "w") as f:
                        f.write(creds.to_json())
                    log(f"Token saved to {token_path}")
                except Exception as e:
                    log(f"Failed to save token: {e}", "WARN")

        try:
            service = build("drive", "v3", credentials=creds)
            return service, None
        except Exception as e:
            return None, f"Failed to build Drive service: {e}"

    def upload(self, data: bytes, settings: dict, log) -> str | None:
        service, err = self._get_service(settings, log)
        if err:
            return err

        try:
            from googleapiclient.http import MediaIoBaseUpload
        except ImportError:
            return "google-api-python-client not installed"

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"anilistsync_backup_{timestamp}.zip"
        folder_id = settings.get("gdrive_folder_id", "") or None

        media = MediaIoBaseUpload(io.BytesIO(data), mimetype="application/zip", resumable=True)
        file_metadata = {"name": filename}
        if folder_id:
            file_metadata["parents"] = [folder_id]

        try:
            service.files().create(body=file_metadata, media_body=media, fields="id,name").execute()
        except Exception as e:
            return f"Google Drive upload failed: {e}"

        log(f"Backup uploaded to Google Drive as {filename} ({len(data)} bytes)")
        self._cleanup_old_gdrive(service, folder_id, settings, log)
        return None

    def _cleanup_old_gdrive(self, service, folder_id: str | None, settings: dict, log):
        try:
            keep = int(settings.get("keep_last", 10))
        except (ValueError, TypeError):
            keep = 10
        if keep < 1:
            return

        query = "name contains 'anilistsync_backup_' and mimeType='application/zip'"
        if folder_id:
            query += f" and '{folder_id}' in parents"

        try:
            page_token = None
            files = []
            while True:
                resp = service.files().list(
                    q=query, spaces="drive",
                    fields="nextPageToken, files(id, name, createdTime)",
                    orderBy="createdTime", pageToken=page_token,
                ).execute()
                files.extend(resp.get("files", []))
                page_token = resp.get("nextPageToken")
                if not page_token:
                    break

            files.sort(key=lambda f: f.get("createdTime", ""))
            to_delete = files[:-keep] if len(files) > keep else []
            for f in to_delete:
                service.files().delete(fileId=f["id"]).execute()
                log(f"Deleted old Drive backup {f['name']}")
        except Exception as e:
            log(f"Google Drive cleanup error: {e}", "WARN")


PROVIDERS: dict[str, BackupProvider] = {
    "github": GitHubProvider(),
    "s3": S3Provider(),
    "gdrive": GDriveProvider(),
}


def _get_provider(name: str) -> BackupProvider | None:
    return PROVIDERS.get(name)


class Plugin:
    def __init__(self):
        pass

    def on_load(self):
        self.log("Cloud Backup plugin loaded")

    def on_sync_finish(self):
        if not self.settings.get("auto_upload", True):
            return
        self._do_backup()

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
            print(f"  [yellow]Backup skipped — {err}[/]")
            return

        self.log("Creating backup archive…")
        try:
            data = _create_zip()
        except Exception as e:
            self.log(f"Zip creation failed: {e}", "ERROR")
            print(f"  [red]Backup failed — zip creation error: {e}[/]")
            return

        self.log(f"Uploading via {p.label()} ({len(data)} bytes)…")
        print(f"  Uploading backup to {p.label()}…")
        err = p.upload(data, self.settings, self.log)
        if err:
            self.log(f"Upload failed: {err}", "ERROR")
            print(f"  [red]Backup upload failed: {err}[/]")
        else:
            print(f"  [green]Backup uploaded successfully via {p.label()}[/]")

    def get_commands(self):
        return [
            ("Upload Backup Now", self._cmd_upload),
            ("Configure Provider", self._cmd_configure),
        ]

    def _cmd_upload(self):
        self._do_backup()

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
