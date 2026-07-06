from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from constellation.cli import main
from constellation.daily import DailyPipelineStore


class DailyPipelineTests(unittest.TestCase):
    def test_successful_pipeline_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)

            run = DailyPipelineStore(root).run()

            self.assertEqual(run.status, "completed")
            self.assertTrue((root / "outputs" / "daily" / "daily-run.json").exists())
            self.assertTrue((root / "outputs" / "daily" / "daily-manifest.json").exists())
            self.assertTrue((root / "outputs" / "daily" / "daily-report.md").exists())
            self.assertEqual([stage["name"] for stage in run.stages], _STAGES)

    def test_overwrite_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            store = DailyPipelineStore(root)
            store.run()

            with self.assertRaises(Exception):
                store.run()
            second = store.run(overwrite=True)

            self.assertEqual(second.status, "completed")
            self.assertEqual(len(store.history()), 2)

    def test_history_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            store = DailyPipelineStore(root)

            store.run()

            history = json.loads((root / "outputs" / "daily" / "daily-history.json").read_text(encoding="utf-8"))
            self.assertEqual(len(history["runs"]), 1)

    def test_export_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            store = DailyPipelineStore(root)
            store.run()

            output_path = store.export()

            self.assertTrue(output_path.exists())
            self.assertIn("# Daily Intelligence Pipeline", output_path.read_text(encoding="utf-8"))

    def test_deterministic_manifest_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            store = DailyPipelineStore(root)

            first = store.run()
            second = store.run(overwrite=True)

            self.assertEqual(first.manifest["thesis_count"], second.manifest["thesis_count"])
            self.assertEqual(first.manifest["graph_nodes"], second.manifest["graph_nodes"])
            self.assertEqual([stage["name"] for stage in first.stages], [stage["name"] for stage in second.stages])
            self.assertEqual([stage["status"] for stage in first.stages], [stage["status"] for stage in second.stages])

    def test_missing_google_drive_configuration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root, include_google_config=False)

            run = DailyPipelineStore(root).run()
            drive_stage = next(stage for stage in run.stages if stage["name"] == "google_drive_sync")

            self.assertEqual(drive_stage["status"], "skipped")
            self.assertIn("configuration missing", drive_stage["details"]["reason"])

    def test_empty_intake(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)

            run = DailyPipelineStore(root).run()

            self.assertEqual(run.manifest["intake_files_processed"], 0)

    def test_repeated_execution_cli_with_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)

            first_output = io.StringIO()
            with redirect_stdout(first_output):
                first_exit = main(["daily", "--root", str(root)])
            second_output = io.StringIO()
            with redirect_stdout(second_output):
                second_exit = main(["daily", "--root", str(root), "--overwrite"])
            history_output = io.StringIO()
            with redirect_stdout(history_output):
                history_exit = main(["daily", "--root", str(root), "history"])

            self.assertEqual(first_exit, 0)
            self.assertEqual(second_exit, 0)
            self.assertEqual(history_exit, 0)
            self.assertIn("daily_run_id:", first_output.getvalue())
            self.assertEqual(history_output.getvalue().count("daily_"), 2)

    def test_cli_status_and_export(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            DailyPipelineStore(root).run()

            status_output = io.StringIO()
            with redirect_stdout(status_output):
                status_exit = main(["daily", "--root", str(root), "status"])
            export_output = io.StringIO()
            with redirect_stdout(export_output):
                export_exit = main(["daily", "--root", str(root), "export"])

            self.assertEqual(status_exit, 0)
            self.assertIn("status: completed", status_output.getvalue())
            self.assertEqual(export_exit, 0)
            self.assertIn("daily_report:", export_output.getvalue())

    def test_no_provider_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            with patch("constellation.providers.EchoProvider.generate") as generate:
                DailyPipelineStore(root).run()

            generate.assert_not_called()


_STAGES = [
    "source_monitoring",
    "intake_scan",
    "google_drive_sync",
    "morning_brief",
    "memory_snapshot",
    "evidence_graph",
    "thesis_intelligence",
]


def _create_minimal_tree(root: Path, *, include_google_config: bool = True) -> None:
    for relative in [
        "inbox/google-drive/incoming",
        "inbox/gmail/incoming",
        "inbox/manual/incoming",
        "config",
        "memory/evidence",
        "memory/graph",
        "logs/runs",
    ]:
        (root / relative).mkdir(parents=True, exist_ok=True)
    if include_google_config:
        (root / "config" / "google-drive.example.yaml").write_text(
            "credentials_path: config/secrets/google-drive-client.json\n"
            "token_path: config/secrets/google-drive-token.json\n"
            "scopes:\n"
            "  - drive.readonly\n",
            encoding="utf-8",
        )
    (root / "config" / "sources.yaml").write_text("sources: []\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
