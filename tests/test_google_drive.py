from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from constellation.cli import main
from constellation.google_drive import (
    DEPENDENCY_MESSAGE,
    GOOGLE_DOC_MIME_TYPE,
    GoogleDriveConnector,
    GoogleDriveDependencyError,
    GoogleDriveFile,
    GoogleDriveSyncManifest,
)


class GoogleDriveConnectorTests(unittest.TestCase):
    def test_missing_dependency_message(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _root(Path(temp_dir), enabled=True)
            connector = GoogleDriveConnector(root)

            with patch("constellation.google_drive._google_dependencies", side_effect=GoogleDriveDependencyError(DEPENDENCY_MESSAGE)):
                with self.assertRaisesRegex(GoogleDriveDependencyError, "pip install -e"):
                    connector.list_files()

    def test_config_loading(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _root(Path(temp_dir), enabled=False)

            config = GoogleDriveConnector(root).load_config()

            self.assertEqual(config["download_folder"], "inbox/google-drive/incoming")
            self.assertEqual(config["allowed_extensions"], [".md", ".txt", ".pdf"])

    def test_source_filtering(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _root(Path(temp_dir), enabled=True, second_source=True)
            service = FakeDriveService({"folder_a": [_api_file("file_a", "a.md")], "folder_b": [_api_file("file_b", "b.md")]})

            files = GoogleDriveConnector(root, service=service).list_files("source_a")

            self.assertEqual([file.file_id for file in files], ["file_a"])

    def test_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _root(Path(temp_dir), enabled=True)
            service = FakeDriveService({"folder_a": [_api_file("file_a", "a.md", content=b"a")]})

            manifest = GoogleDriveConnector(root, service=service).sync(dry_run=True)

            self.assertEqual(len(manifest.downloaded_files), 1)
            self.assertFalse((root / "inbox" / "google-drive" / "incoming" / "a.md").exists())

    def test_supported_extension_filtering(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _root(Path(temp_dir), enabled=True)
            service = FakeDriveService({"folder_a": [_api_file("file_a", "a.exe")]})

            manifest = GoogleDriveConnector(root, service=service).sync(dry_run=True)

            self.assertEqual(len(manifest.skipped_files), 1)
            self.assertEqual(manifest.skipped_files[0].metadata["skip_reason"], "unsupported_file_type")

    def test_google_doc_export_as_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _root(Path(temp_dir), enabled=True)
            service = FakeDriveService({"folder_a": [_api_file("doc_a", "Doc A", mime_type=GOOGLE_DOC_MIME_TYPE, content=b"# Doc A")]})

            with patch("constellation.google_drive._google_dependencies", return_value={"MediaIoBaseDownload": FakeDownloader}):
                manifest = GoogleDriveConnector(root, service=service).sync()

            self.assertEqual(manifest.downloaded_files[0].destination_path, str(root / "inbox" / "google-drive" / "incoming" / "Doc A.md"))

    def test_duplicate_detection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _root(Path(temp_dir), enabled=True)
            incoming = root / "inbox" / "google-drive" / "incoming"
            incoming.mkdir(parents=True, exist_ok=True)
            (incoming / "existing.md").write_bytes(b"same")
            service = FakeDriveService({"folder_a": [_api_file("file_a", "a.md", content=b"same")]})

            with patch("constellation.google_drive._google_dependencies", return_value={"MediaIoBaseDownload": FakeDownloader}):
                manifest = GoogleDriveConnector(root, service=service).sync()

            self.assertEqual(len(manifest.duplicate_files), 1)
            self.assertFalse((incoming / "a.md").exists())

    def test_manifest_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _root(Path(temp_dir), enabled=True)
            service = FakeDriveService({"folder_a": [_api_file("file_a", "a.md", content=b"a")]})

            with patch("constellation.google_drive._google_dependencies", return_value={"MediaIoBaseDownload": FakeDownloader}):
                GoogleDriveConnector(root, service=service).sync()

            self.assertTrue((root / "outputs" / "google-drive" / "google-drive-sync-manifest.json").exists())
            self.assertTrue((root / "outputs" / "google-drive" / "google-drive-sync-manifest.md").exists())

    def test_cli_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _root(Path(temp_dir), enabled=False)

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["drive", "--root", str(root), "status"])

            self.assertEqual(exit_code, 0)
            self.assertIn("config_present: True", output.getvalue())

    def test_cli_dry_run(self) -> None:
        fake_manifest = GoogleDriveSyncManifest(
            sync_id="sync_test",
            source_folder_id=None,
            downloaded_files=[_drive_file("file_a", "a.md", status="available")],
            skipped_files=[],
            duplicate_files=[],
            errors=[],
            created_at="2026-07-05T09:00:00-07:00",
        )

        with patch("constellation.cli.GoogleDriveConnector") as connector_cls:
            connector = connector_cls.return_value
            connector.sync.return_value = fake_manifest
            connector.json_path = Path("outputs/google-drive/google-drive-sync-manifest.json")
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["drive", "sync", "--dry-run"])

        self.assertEqual(exit_code, 0)
        self.assertIn("downloaded: 1", output.getvalue())
        connector.sync.assert_called_once_with(source_id=None, dry_run=True)

    def test_cli_sync_with_mocked_files(self) -> None:
        fake_manifest = GoogleDriveSyncManifest(
            sync_id="sync_test",
            source_folder_id="source_a",
            downloaded_files=[_drive_file("file_a", "a.md", status="downloaded")],
            skipped_files=[],
            duplicate_files=[],
            errors=[],
            created_at="2026-07-05T09:00:00-07:00",
        )

        with patch("constellation.cli.GoogleDriveConnector") as connector_cls:
            connector = connector_cls.return_value
            connector.sync.return_value = fake_manifest
            connector.json_path = Path("outputs/google-drive/google-drive-sync-manifest.json")
            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["drive", "sync", "--source", "source_a"])

        self.assertEqual(exit_code, 0)
        self.assertIn("downloaded: 1", output.getvalue())
        connector.sync.assert_called_once_with(source_id="source_a", dry_run=False)

    def test_no_secrets_written_to_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _root(Path(temp_dir), enabled=True)
            service = FakeDriveService({"folder_a": [_api_file("file_a", "a.md", content=b"a")]})

            with patch("constellation.google_drive._google_dependencies", return_value={"MediaIoBaseDownload": FakeDownloader}):
                GoogleDriveConnector(root, service=service).sync()

            manifest_text = (root / "outputs" / "google-drive" / "google-drive-sync-manifest.json").read_text(encoding="utf-8")
            self.assertNotIn("credentials", manifest_text)
            self.assertNotIn("token", manifest_text)
            self.assertNotIn("secret", manifest_text.lower())

    def test_no_google_drive_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _root(Path(temp_dir), enabled=True)
            service = FakeDriveService({"folder_a": [_api_file("file_a", "a.md", content=b"a")]})

            with patch("constellation.google_drive._google_dependencies", return_value={"MediaIoBaseDownload": FakeDownloader}):
                GoogleDriveConnector(root, service=service).sync()

            self.assertEqual(service.mutation_calls, [])

    def test_intake_pipeline_remains_separate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _root(Path(temp_dir), enabled=True)
            service = FakeDriveService({"folder_a": [_api_file("file_a", "a.md", content=b"a")]})

            with patch("constellation.google_drive._google_dependencies", return_value={"MediaIoBaseDownload": FakeDownloader}):
                GoogleDriveConnector(root, service=service).sync()

            self.assertFalse((root / "outputs" / "intake" / "intake-manifest.json").exists())
            self.assertFalse((root / "research_inputs").exists())


class FakeRequest:
    def __init__(self, data: bytes) -> None:
        self.data = data


class FakeDownloader:
    def __init__(self, buffer, request) -> None:
        self.buffer = buffer
        self.request = request
        self.done = False

    def next_chunk(self):
        if not self.done:
            self.buffer.write(self.request.data)
            self.done = True
        return None, True


class FakeExecute:
    def __init__(self, payload) -> None:
        self.payload = payload

    def execute(self):
        return self.payload


class FakeFilesResource:
    def __init__(self, folders: dict[str, list[dict[str, object]]], mutation_calls: list[str]) -> None:
        self.folders = folders
        self.mutation_calls = mutation_calls

    def list(self, **kwargs):
        q = kwargs.get("q", "")
        folder_id = str(q).split("'")[1]
        return FakeExecute({"files": self.folders.get(folder_id, [])})

    def get_media(self, fileId: str):
        return FakeRequest(_content_for(self.folders, fileId))

    def export_media(self, fileId: str, mimeType: str):
        return FakeRequest(_content_for(self.folders, fileId))

    def update(self, **kwargs):
        self.mutation_calls.append("update")
        return FakeExecute({})

    def delete(self, **kwargs):
        self.mutation_calls.append("delete")
        return FakeExecute({})


class FakeDriveService:
    def __init__(self, folders: dict[str, list[dict[str, object]]]) -> None:
        self.folders = folders
        self.mutation_calls: list[str] = []

    def files(self):
        return FakeFilesResource(self.folders, self.mutation_calls)


def _root(path: Path, *, enabled: bool, second_source: bool = False) -> Path:
    (path / "config").mkdir(parents=True)
    (path / "config" / "google-drive.example.yaml").write_text(
        """credentials_path: config/secrets/google-drive-credentials.json
token_path: config/secrets/google-drive-token.json
scopes:
  - https://www.googleapis.com/auth/drive.readonly
download_folder: inbox/google-drive/incoming
allowed_extensions:
  - .md
  - .txt
  - .pdf
""",
        encoding="utf-8",
    )
    sources = [
        f"""  - id: source_a
    display_name: Source A
    source_type: google_drive
    enabled: {str(enabled).lower()}
    folder_id: folder_a
    destination_channel: google-drive
    expected_format:
      - md
      - txt
      - pdf
"""
    ]
    if second_source:
        sources.append(
            """  - id: source_b
    display_name: Source B
    source_type: google_drive
    enabled: true
    folder_id: folder_b
    destination_channel: google-drive
    expected_format:
      - md
      - txt
      - pdf
"""
        )
    (path / "config" / "sources.yaml").write_text("sources:\n" + "".join(sources), encoding="utf-8")
    return path


def _api_file(file_id: str, name: str, *, mime_type: str = "text/markdown", content: bytes = b"content") -> dict[str, object]:
    return {
        "id": file_id,
        "name": name,
        "mimeType": mime_type,
        "modifiedTime": "2026-07-05T09:00:00Z",
        "size": str(len(content)),
        "content": content,
    }


def _content_for(folders: dict[str, list[dict[str, object]]], file_id: str) -> bytes:
    for files in folders.values():
        for file in files:
            if file["id"] == file_id:
                return file.get("content", b"content")
    return b""


def _drive_file(file_id: str, name: str, *, status: str) -> GoogleDriveFile:
    return GoogleDriveFile(
        file_id=file_id,
        name=name,
        mime_type="text/markdown",
        modified_time=None,
        size=None,
        sha256=None,
        source_folder_id="folder_a",
        destination_path=None,
        status=status,
        metadata={},
    )


if __name__ == "__main__":
    unittest.main()
