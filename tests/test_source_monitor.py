from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from constellation.dashboard import ExecutiveDashboardStore
from constellation.daily import DailyPipelineStore
from constellation.source_monitor import SourceMonitorStore


class SourceMonitorTests(unittest.TestCase):
    def test_initial_monitoring(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _minimal_tree(root)

            run = SourceMonitorStore(root).run()

            self.assertGreaterEqual(run.summary["sources_checked"], 6)
            self.assertGreaterEqual(run.summary["new_items"], 1)

    def test_unchanged_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _minimal_tree(root)
            store = SourceMonitorStore(root)
            store.run()

            second = store.run(overwrite=True)

            self.assertGreater(second.summary["sources_unchanged"], 0)

    def test_changed_source_updated_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _minimal_tree(root)
            store = SourceMonitorStore(root)
            store.run()

            (root / "memory" / "evidence" / "ev_test.json").write_text('{"evidence_id":"ev_test","claim":"updated"}', encoding="utf-8")
            second = store.run(overwrite=True)

            evidence_change = _change(second, "local_evidence_files")
            self.assertEqual(evidence_change.status, "UPDATED ITEMS")
            self.assertIn("memory\\evidence\\ev_test.json", evidence_change.updated_items)

    def test_new_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _minimal_tree(root)
            store = SourceMonitorStore(root)
            store.run()

            (root / "inbox" / "manual" / "incoming" / "new.md").write_text("new", encoding="utf-8")
            second = store.run(overwrite=True)

            manual_change = _change(second, "local_intake_manual")
            self.assertEqual(manual_change.status, "NEW ITEMS")
            self.assertTrue(manual_change.new_items)

    def test_removed_files(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _minimal_tree(root)
            (root / "inbox" / "manual" / "incoming" / "old.md").write_text("old", encoding="utf-8")
            store = SourceMonitorStore(root)
            store.run()

            (root / "inbox" / "manual" / "incoming" / "old.md").unlink()
            second = store.run(overwrite=True)

            manual_change = _change(second, "local_intake_manual")
            self.assertEqual(manual_change.status, "REMOVED ITEMS")
            self.assertTrue(manual_change.removed_items)

    def test_failed_source(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _minimal_tree(root)
            _remove_tree(root / "inbox" / "manual")

            run = SourceMonitorStore(root).run()

            self.assertGreaterEqual(run.summary["sources_failed"], 1)
            self.assertEqual(_change(run, "local_intake_manual").status, "FAILED")

    def test_history_and_export(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _minimal_tree(root)
            store = SourceMonitorStore(root)

            store.run()
            store.run(overwrite=True)
            output_path = store.export()

            self.assertEqual(len(store.history()), 2)
            self.assertTrue(output_path.exists())
            self.assertIn("# Source Monitor", output_path.read_text(encoding="utf-8"))

    def test_dashboard_integration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _minimal_tree(root)
            SourceMonitorStore(root).run()

            dashboard = ExecutiveDashboardStore(root).generate()

            self.assertTrue(dashboard.source_monitoring_summary["available"])
            self.assertGreaterEqual(dashboard.source_monitoring_summary["sources_checked"], 6)

    def test_daily_pipeline_integration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _minimal_tree(root)

            run = DailyPipelineStore(root).run()

            self.assertEqual(run.stages[0]["name"], "source_monitoring")
            self.assertIn("source_monitor_summary", run.manifest)

    def test_deterministic_fingerprints(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _minimal_tree(root)
            store = SourceMonitorStore(root)
            first = store.run()
            second = store.run(overwrite=True)

            first_fp = _snapshot(first, "local_evidence_files").fingerprint
            second_fp = _snapshot(second, "local_evidence_files").fingerprint

            self.assertEqual(first_fp, second_fp)


def _change(run, source_id):
    for change in run.changes:
        if change.source_id == source_id:
            return change
    raise AssertionError(f"missing change {source_id}")


def _snapshot(run, source_id):
    for snapshot in run.snapshots:
        if snapshot.source_id == source_id:
            return snapshot
    raise AssertionError(f"missing snapshot {source_id}")


def _minimal_tree(root: Path) -> None:
    for relative in [
        "inbox/google-drive/incoming",
        "inbox/gmail/incoming",
        "inbox/manual/incoming",
        "memory/evidence",
        "outputs/thesis",
        "outputs/theses",
        "config",
        "logs/runs",
    ]:
        (root / relative).mkdir(parents=True, exist_ok=True)
    (root / "memory" / "evidence" / "ev_test.json").write_text('{"evidence_id":"ev_test","claim":"initial"}', encoding="utf-8")
    (root / "outputs" / "thesis" / "theses.json").write_text('{"theses":[]}', encoding="utf-8")
    (root / "config" / "sources.yaml").write_text(
        "sources:\n"
        "  - id: drive_alpha\n"
        "    display_name: Drive Alpha\n"
        "    source_type: google_drive\n"
        "    intake_channel: google-drive\n"
        "    folder_id: folder_alpha\n"
        "    enabled: true\n",
        encoding="utf-8",
    )


def _remove_tree(path: Path) -> None:
    for child in sorted(path.rglob("*"), reverse=True):
        if child.is_file():
            child.unlink()
        elif child.is_dir():
            child.rmdir()
    path.rmdir()


if __name__ == "__main__":
    unittest.main()
