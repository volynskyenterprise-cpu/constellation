from __future__ import annotations

import io
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from .io import read_json, write_json
from .models import JsonMap
from .simple_yaml import load_yaml


class GoogleDriveError(RuntimeError):
    pass


class GoogleDriveDependencyError(GoogleDriveError):
    pass


DEPENDENCY_MESSAGE = "Google Drive dependencies are not installed. Run: pip install -e .[google-drive]"
GOOGLE_DOC_MIME_TYPE = "application/vnd.google-apps.document"
MARKDOWN_EXPORT_MIME_TYPE = "text/markdown"
TEXT_EXPORT_MIME_TYPE = "text/plain"
DRIVE_READONLY_SCOPE = "https://www.googleapis.com/auth/drive.readonly"
SCOPE_ALIASES = {"drive.readonly": DRIVE_READONLY_SCOPE, DRIVE_READONLY_SCOPE: DRIVE_READONLY_SCOPE}


@dataclass(frozen=True)
class GoogleDriveFile:
    file_id: str
    name: str
    mime_type: str
    modified_time: str | None
    size: str | None
    sha256: str | None
    source_folder_id: str
    destination_path: str | None
    status: str
    metadata: JsonMap

    def to_dict(self) -> JsonMap:
        return {
            "file_id": self.file_id,
            "name": self.name,
            "mime_type": self.mime_type,
            "modified_time": self.modified_time,
            "size": self.size,
            "sha256": self.sha256,
            "source_folder_id": self.source_folder_id,
            "destination_path": self.destination_path,
            "status": self.status,
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class GoogleDriveSyncManifest:
    sync_id: str
    source_folder_id: str | None
    downloaded_files: list[GoogleDriveFile]
    skipped_files: list[GoogleDriveFile]
    duplicate_files: list[GoogleDriveFile]
    errors: list[JsonMap]
    created_at: str

    def to_dict(self) -> JsonMap:
        return {
            "sync_id": self.sync_id,
            "source_folder_id": self.source_folder_id,
            "downloaded_files": [item.to_dict() for item in self.downloaded_files],
            "skipped_files": [item.to_dict() for item in self.skipped_files],
            "duplicate_files": [item.to_dict() for item in self.duplicate_files],
            "errors": self.errors,
            "created_at": self.created_at,
        }


class GoogleDriveConnector:
    def __init__(self, root: Path, service: Any | None = None) -> None:
        self.root = root
        self.service = service
        self.output_dir = root / "outputs" / "google-drive"
        self.json_path = self.output_dir / "google-drive-sync-manifest.json"
        self.markdown_path = self.output_dir / "google-drive-sync-manifest.md"

    def load_config(self) -> JsonMap:
        drive_path = self.root / "config" / "google-drive.yaml"
        example_path = self.root / "config" / "google-drive.example.yaml"
        config_path = drive_path if drive_path.exists() else example_path
        if not config_path.exists():
            raise GoogleDriveError("Google Drive config is missing. Create config/google-drive.yaml or review config/google-drive.example.yaml.")
        config = load_yaml(config_path)
        config["config_path"] = str(config_path)
        config["sources"] = self._drive_sources()
        return config

    def status(self) -> JsonMap:
        try:
            config = self.load_config()
            config_present = True
            config_error = None
        except GoogleDriveError as exc:
            config = {}
            config_present = False
            config_error = str(exc)
        credentials_path = config.get("credentials_path")
        token_path = config.get("token_path")
        return {
            "config_present": config_present,
            "config_path": config.get("config_path"),
            "config_error": config_error,
            "dependencies_installed": google_drive_dependencies_installed(),
            "credentials_path_configured": isinstance(credentials_path, str) and bool(credentials_path),
            "token_path_configured": isinstance(token_path, str) and bool(token_path),
            "enabled_sources": [source["id"] for source in config.get("sources", []) if isinstance(source, dict) and source.get("enabled") is True],
        }

    def authenticate(self):
        if self.service is not None:
            return self.service
        config = self.load_config()
        scopes = normalize_scopes(config.get("scopes", []))
        deps = _google_dependencies()
        credentials_path = self.root / str(config.get("credentials_path", ""))
        token_path = self.root / str(config.get("token_path", ""))
        credentials = None
        if token_path.exists():
            credentials = deps["Credentials"].from_authorized_user_file(str(token_path), scopes)
        if credentials and credentials.expired and credentials.refresh_token:
            credentials.refresh(deps["Request"]())
        if not credentials or not credentials.valid:
            if not credentials_path.exists():
                raise GoogleDriveError(f"Google Drive credentials file is missing: {credentials_path}")
            flow = deps["InstalledAppFlow"].from_client_secrets_file(str(credentials_path), scopes)
            credentials = flow.run_local_server(port=0)
            token_path.parent.mkdir(parents=True, exist_ok=True)
            token_path.write_text(credentials.to_json(), encoding="utf-8")
        self.service = deps["build"]("drive", "v3", credentials=credentials)
        return self.service

    def list_files(self, source_id: str | None = None) -> list[GoogleDriveFile]:
        service = self.authenticate()
        sources = _filter_sources(self._drive_sources(), source_id)
        files: list[GoogleDriveFile] = []
        for source in sources:
            folder_id = source.get("folder_id")
            if not isinstance(folder_id, str) or not folder_id:
                continue
            response = service.files().list(
                q=f"'{folder_id}' in parents and trashed = false",
                fields="files(id,name,mimeType,modifiedTime,size,md5Checksum)",
                pageSize=1000,
            ).execute()
            for item in response.get("files", []):
                if isinstance(item, dict):
                    files.append(_drive_file_from_api(item, folder_id, "available"))
        return sorted(files, key=lambda item: (item.source_folder_id, item.name.lower(), item.file_id))

    def download_file(self, file: GoogleDriveFile, *, dry_run: bool = False) -> GoogleDriveFile:
        config = self.load_config()
        allowed_extensions = set(_string_list(config.get("allowed_extensions", [".md", ".txt", ".pdf"])))
        destination_dir = self.root / str(config.get("download_folder", "inbox/google-drive/incoming"))
        destination_name, request = self._download_request(file, allowed_extensions)
        if destination_name is None or request is None:
            return _replace_file(file, status="skipped", metadata={**file.metadata, "skip_reason": "unsupported_file_type"})
        destination_path = destination_dir / destination_name
        if dry_run:
            return _replace_file(file, destination_path=str(destination_path), status="available")
        destination_dir.mkdir(parents=True, exist_ok=True)
        existing_hashes = _existing_hashes(destination_dir)
        if destination_path.exists():
            return _replace_file(file, destination_path=str(destination_path), status="skipped", metadata={**file.metadata, "skip_reason": "destination_exists"})
        buffer = io.BytesIO()
        downloader = _google_dependencies()["MediaIoBaseDownload"](buffer, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        data = buffer.getvalue()
        digest = sha256(data).hexdigest()
        if digest in existing_hashes:
            return _replace_file(file, sha256=digest, destination_path=str(destination_path), status="duplicate")
        destination_path.write_bytes(data)
        return _replace_file(file, sha256=digest, destination_path=str(destination_path), status="downloaded")

    def sync(self, *, source_id: str | None = None, dry_run: bool = False) -> GoogleDriveSyncManifest:
        downloaded: list[GoogleDriveFile] = []
        skipped: list[GoogleDriveFile] = []
        duplicates: list[GoogleDriveFile] = []
        errors: list[JsonMap] = []
        for file in self.list_files(source_id):
            try:
                result = self.download_file(file, dry_run=dry_run)
            except Exception as exc:
                errors.append({"file_id": file.file_id, "name": file.name, "error": str(exc)})
                continue
            if result.status in {"downloaded", "available"}:
                downloaded.append(result)
            elif result.status == "duplicate":
                duplicates.append(result)
            else:
                skipped.append(result)
        manifest = GoogleDriveSyncManifest(
            sync_id=f"gdrive_sync_{_digest('|'.join(item.file_id + ':' + item.status for item in downloaded + skipped + duplicates))}",
            source_folder_id=source_id,
            downloaded_files=downloaded,
            skipped_files=skipped,
            duplicate_files=duplicates,
            errors=errors,
            created_at=_now_iso(),
        )
        self.write_manifest(manifest)
        return manifest

    def write_manifest(self, manifest: GoogleDriveSyncManifest) -> None:
        write_json(self.json_path, manifest.to_dict())
        self.markdown_path.parent.mkdir(parents=True, exist_ok=True)
        self.markdown_path.write_text(render_sync_manifest_markdown(manifest), encoding="utf-8")

    def _drive_sources(self) -> list[JsonMap]:
        path = self.root / "config" / "sources.yaml"
        if not path.exists():
            return []
        data = load_yaml(path)
        sources = data.get("sources", [])
        if not isinstance(sources, list):
            return []
        return [source for source in sources if isinstance(source, dict) and source.get("source_type") == "google_drive"]

    def _download_request(self, file: GoogleDriveFile, allowed_extensions: set[str]) -> tuple[str | None, Any | None]:
        service = self.authenticate()
        name = file.name
        suffix = Path(name).suffix.lower()
        if file.mime_type == GOOGLE_DOC_MIME_TYPE:
            try:
                return (f"{Path(name).stem}.md", service.files().export_media(fileId=file.file_id, mimeType=MARKDOWN_EXPORT_MIME_TYPE))
            except Exception:
                return (f"{Path(name).stem}.txt", service.files().export_media(fileId=file.file_id, mimeType=TEXT_EXPORT_MIME_TYPE))
        if suffix not in allowed_extensions:
            return None, None
        return name, service.files().get_media(fileId=file.file_id)


def google_drive_dependencies_installed() -> bool:
    try:
        _google_dependencies()
    except GoogleDriveDependencyError:
        return False
    return True


def normalize_scopes(raw_scopes: Any) -> list[str]:
    scopes: list[str] = []
    if not isinstance(raw_scopes, list):
        raise GoogleDriveError("Google Drive config scopes must be a non-empty list.")
    for raw_scope in raw_scopes:
        scope = _scope_string(raw_scope)
        if scope is None:
            raise GoogleDriveError(f"Unsupported Google Drive scope entry: {raw_scope}")
        normalized = SCOPE_ALIASES.get(scope)
        if normalized is None:
            raise GoogleDriveError(f"Unsupported Google Drive scope: {scope}")
        if normalized not in scopes:
            scopes.append(normalized)
    if not scopes:
        raise GoogleDriveError("Google Drive config scopes must include drive.readonly.")
    return scopes


def render_sync_manifest_markdown(manifest: GoogleDriveSyncManifest) -> str:
    lines = [
        "# Google Drive Sync Manifest",
        "",
        f"Sync ID: `{manifest.sync_id}`",
        f"Source folder: `{manifest.source_folder_id or 'all enabled sources'}`",
        f"Created: `{manifest.created_at}`",
        "",
        "## Counts",
        "",
        f"- Downloaded: {len(manifest.downloaded_files)}",
        f"- Skipped: {len(manifest.skipped_files)}",
        f"- Duplicates: {len(manifest.duplicate_files)}",
        f"- Errors: {len(manifest.errors)}",
        "",
    ]
    for title, items in [("Downloaded Files", manifest.downloaded_files), ("Skipped Files", manifest.skipped_files), ("Duplicate Files", manifest.duplicate_files)]:
        lines.extend([f"## {title}", ""])
        if not items:
            lines.extend(["- None", ""])
            continue
        for item in items:
            lines.extend(
                [
                    f"- `{item.file_id}` {item.name}",
                    f"  Status: `{item.status}`",
                    f"  Destination: `{item.destination_path or ''}`",
                    f"  SHA-256: `{item.sha256 or ''}`",
                ]
            )
        lines.append("")
    lines.extend(["## Errors", ""])
    if not manifest.errors:
        lines.extend(["- None", ""])
    else:
        for error in manifest.errors:
            lines.append(f"- `{error.get('file_id', 'unknown')}` {error.get('error', '')}")
        lines.append("")
    return "\n".join(lines)


def _google_dependencies() -> JsonMap:
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from google_auth_oauthlib.flow import InstalledAppFlow
        from googleapiclient.discovery import build
        from googleapiclient.http import MediaIoBaseDownload
    except ImportError as exc:
        raise GoogleDriveDependencyError(DEPENDENCY_MESSAGE) from exc
    return {
        "Request": Request,
        "Credentials": Credentials,
        "InstalledAppFlow": InstalledAppFlow,
        "build": build,
        "MediaIoBaseDownload": MediaIoBaseDownload,
    }


def _filter_sources(sources: list[JsonMap], source_id: str | None) -> list[JsonMap]:
    enabled = [source for source in sources if source.get("enabled") is True]
    if source_id is None:
        return enabled
    return [source for source in enabled if source.get("id") == source_id]


def _drive_file_from_api(data: JsonMap, folder_id: str, status: str) -> GoogleDriveFile:
    return GoogleDriveFile(
        file_id=str(data.get("id", "")),
        name=str(data.get("name", "")),
        mime_type=str(data.get("mimeType", "")),
        modified_time=data.get("modifiedTime") if isinstance(data.get("modifiedTime"), str) else None,
        size=data.get("size") if isinstance(data.get("size"), str) else None,
        sha256=None,
        source_folder_id=folder_id,
        destination_path=None,
        status=status,
        metadata={key: value for key, value in data.items() if key not in {"id", "name", "content"}},
    )


def _replace_file(
    file: GoogleDriveFile,
    *,
    sha256: str | None = None,
    destination_path: str | None = None,
    status: str | None = None,
    metadata: JsonMap | None = None,
) -> GoogleDriveFile:
    return GoogleDriveFile(
        file_id=file.file_id,
        name=file.name,
        mime_type=file.mime_type,
        modified_time=file.modified_time,
        size=file.size,
        sha256=file.sha256 if sha256 is None else sha256,
        source_folder_id=file.source_folder_id,
        destination_path=file.destination_path if destination_path is None else destination_path,
        status=file.status if status is None else status,
        metadata=file.metadata if metadata is None else metadata,
    )


def _existing_hashes(directory: Path) -> set[str]:
    if not directory.exists():
        return set()
    return {_file_hash(path) for path in directory.iterdir() if path.is_file() and path.name != "README.md"}


def _file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _scope_string(value: Any) -> str | None:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict) and len(value) == 1:
        key, raw = next(iter(value.items()))
        if isinstance(key, str) and isinstance(raw, str):
            return f"{key}:{raw}".strip()
    return None


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:16]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
