from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from constellation.cli import main
from constellation.intake import IntakeEngine


class IntakePipelineTests(unittest.TestCase):
    def test_empty_inbox_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _root(Path(temp_dir))

            items = IntakeEngine(root).scan()

            self.assertEqual(items, [])

    def test_multiple_inboxes_scan(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _root(Path(temp_dir))
            _write(root, "manual", "manual.md", "manual")
            _write(root, "gmail", "gmail.txt", "gmail")

            items = IntakeEngine(root).scan()

            self.assertEqual(len(items), 2)
            self.assertEqual([item.source_channel for item in items], ["gmail", "manual"])

    def test_manifest_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _root(Path(temp_dir))
            _write(root, "manual", "brief.md", "hello")

            manifest = IntakeEngine(root).import_items()

            self.assertEqual(manifest.counts["imported"], 1)
            self.assertTrue((root / "outputs" / "intake" / "intake-manifest.json").exists())
            self.assertTrue((root / "outputs" / "intake" / "intake-manifest.md").exists())

    def test_duplicate_detection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _root(Path(temp_dir))
            _write(root, "manual", "first.md", "same content")
            _write(root, "gmail", "second.md", "same content")

            manifest = IntakeEngine(root).import_items()

            self.assertEqual(manifest.counts["imported"], 1)
            self.assertEqual(manifest.counts["duplicates"], 1)

    def test_repeated_imports_skip_duplicates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _root(Path(temp_dir))
            _write(root, "manual", "brief.md", "hello")
            engine = IntakeEngine(root)

            first = engine.import_items()
            second = engine.import_items()

            self.assertEqual(first.counts["imported"], 1)
            self.assertEqual(second.counts["imported"], 1)
            self.assertEqual(second.counts["duplicates"], 1)

    def test_deterministic_scan_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _root(Path(temp_dir))
            _write(root, "manual", "b.md", "b")
            _write(root, "manual", "a.md", "a")
            engine = IntakeEngine(root)

            first = [item.item_id for item in engine.scan()]
            second = [item.item_id for item in engine.scan()]

            self.assertEqual(first, second)

    def test_overwrite_protection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _root(Path(temp_dir))
            _write(root, "manual", "brief.md", "incoming")
            destination_dir = root / "research_inputs" / _today()
            destination_dir.mkdir(parents=True)
            (destination_dir / "brief.md").write_text("different", encoding="utf-8")

            manifest = IntakeEngine(root).import_items()

            self.assertEqual(manifest.counts["errors"], 1)
            self.assertEqual((destination_dir / "brief.md").read_text(encoding="utf-8"), "different")

    def test_cli_scan_import_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _root(Path(temp_dir))
            _write(root, "manual", "brief.md", "hello")

            scan_output = io.StringIO()
            with redirect_stdout(scan_output):
                scan_exit = main(["intake", "--root", str(root), "scan"])
            import_output = io.StringIO()
            with redirect_stdout(import_output):
                import_exit = main(["intake", "--root", str(root), "import"])
            status_output = io.StringIO()
            with redirect_stdout(status_output):
                status_exit = main(["intake", "--root", str(root), "status"])

            self.assertEqual(scan_exit, 0)
            self.assertIn("channel=manual", scan_output.getvalue())
            self.assertEqual(import_exit, 0)
            self.assertIn("imported: 1", import_output.getvalue())
            self.assertEqual(status_exit, 0)
            self.assertIn("imported: 1", status_output.getvalue())

    def test_import_preserves_provenance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _root(Path(temp_dir))
            source = _write(root, "google-drive", "brief.md", "hello")

            manifest = IntakeEngine(root).import_items()
            item = manifest.items[0]

            self.assertEqual(item.source_channel, "google-drive")
            self.assertEqual(Path(item.original_path), source)
            self.assertEqual(Path(item.destination_path or "").name, "brief.md")
            self.assertEqual(len(item.file_hash), 64)

    def test_manifest_json_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = _root(Path(temp_dir))
            _write(root, "manual", "brief.md", "hello")

            IntakeEngine(root).import_items()
            data = json.loads((root / "outputs" / "intake" / "intake-manifest.json").read_text(encoding="utf-8"))

            self.assertEqual(data["counts"]["imported"], 1)
            self.assertEqual(data["items"][0]["status"], "imported")


def _root(path: Path) -> Path:
    for channel in ["google-drive", "gmail", "manual"]:
        incoming = path / "inbox" / channel / "incoming"
        incoming.mkdir(parents=True)
        (incoming / "README.md").write_text("placeholder", encoding="utf-8")
    return path


def _write(root: Path, channel: str, name: str, content: str) -> Path:
    path = root / "inbox" / channel / "incoming" / name
    path.write_text(content, encoding="utf-8")
    return path


def _today() -> str:
    from datetime import datetime

    return datetime.now().astimezone().date().isoformat()


if __name__ == "__main__":
    unittest.main()
