from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path

from constellation.cli import main
from constellation.dashboard import ExecutiveDashboardBuilder
from constellation.real_estate_daily import RealEstateDailyEngine, RealEstateDailyStore
from constellation.workflow import WorkflowRun, WorkflowStore, render_workflow_report


def write_intake_config(root: Path, intake_root: Path, *, enabled: bool = True) -> None:
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "config" / "real-estate-assignment.example.yaml").write_text(
        "real_estate_assignment:\n  default_root: real-estate/assignments\n",
        encoding="utf-8",
    )
    (root / "config" / "real-estate-intake.local.yaml").write_text(
        "real_estate_intake:\n"
        "  enabled: true\n"
        "  assignment_root: real-estate/assignments\n"
        "  source_mode: reference\n"
        "  sources:\n"
        "    - id: real_estate_daily_test\n"
        f"      enabled: {'true' if enabled else 'false'}\n"
        "      source_type: local_directory\n"
        f"      root_path: {intake_root.as_posix()}\n"
        "      include_patterns:\n"
        "        - incoming/*.json\n"
        "      archive_processed: false\n",
        encoding="utf-8",
    )


def write_assignment(path: Path, **overrides) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "order_id": "DAILY-100",
        "subject_address": "100 Daily Street",
        "city": "Los Angeles",
        "state": "CA",
        "postal_code": "90001",
        "client_name": "Daily Client",
        "lender": "Daily Lender",
        "amc": "Daily AMC",
        "due_date": "2026-07-20",
        "effective_date": "2026-07-15",
        "assignment_type": "appraisal",
        "property_type": "single_family_residential",
        "report_type": "appraisal_report",
        "intended_use": "mortgage_lending",
    }
    data.update(overrides)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return path


class RealEstateDailyAutomationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name) / "repo"
        self.intake_root = Path(self.tempdir.name) / "intake"
        self.root.mkdir()
        (self.intake_root / "incoming").mkdir(parents=True)
        write_intake_config(self.root, self.intake_root)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_daily_imports_builds_refreshes_outputs_and_review_warnings(self) -> None:
        write_assignment(self.intake_root / "incoming" / "daily.json")
        orphan = self.root / "real-estate" / "assignments" / "orphan-assignment"
        orphan.mkdir(parents=True)
        (orphan / "assignment.yaml").write_text(
            "assignment:\n  assignment_id: orphan-assignment\n  subject:\n    address: 999 Orphan Road\n",
            encoding="utf-8",
        )

        run = RealEstateDailyEngine(self.root).run(overwrite=True)
        store = RealEstateDailyStore(self.root)

        self.assertIn(run.status, {"completed", "completed_with_warnings"})
        self.assertEqual(run.artifacts_imported, 1)
        self.assertEqual(run.canonical_assignments_created, 1)
        self.assertEqual(run.canonical_assignments_updated, 1)
        self.assertEqual(run.assignments_built, 1)
        self.assertGreaterEqual(run.review_item_count, 1)
        self.assertEqual(run.provenance["migration_applied"], 0)
        self.assertTrue(store.latest_json.exists())
        self.assertTrue(store.report_md.exists())
        self.assertTrue(store.history_json.exists())
        self.assertTrue(store.delta_json.exists())
        self.assertIn("Real Estate Daily Automation", store.report_md.read_text(encoding="utf-8"))
        self.assertTrue((self.root / "outputs" / "dashboard" / "dashboard.json").exists())

    def test_no_change_rerun_is_idempotent_and_does_not_apply_migration(self) -> None:
        write_assignment(self.intake_root / "incoming" / "daily.json")
        first = RealEstateDailyEngine(self.root).run(overwrite=True)
        second = RealEstateDailyEngine(self.root).run(overwrite=True)
        delta = json.loads(RealEstateDailyStore(self.root).delta_json.read_text(encoding="utf-8"))

        self.assertEqual(first.artifacts_imported, 1)
        self.assertEqual(second.artifacts_imported, 0)
        self.assertEqual(second.artifacts_updated, 0)
        self.assertEqual(second.assignments_built, 0)
        self.assertTrue(delta["no_change"])
        self.assertEqual(second.provenance["migration_applied"], 0)

    def test_cli_daily_run_status_history_and_export(self) -> None:
        write_assignment(self.intake_root / "incoming" / "daily.json")
        commands = [
            ["real-estate", "--root", str(self.root), "daily"],
            ["real-estate", "--root", str(self.root), "daily", "status"],
            ["real-estate", "--root", str(self.root), "daily", "history"],
            ["real-estate", "--root", str(self.root), "daily", "export"],
        ]
        for command in commands:
            with self.subTest(command=command):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = main(command)
                self.assertEqual(code, 0, output.getvalue())
                self.assertIn("daily", output.getvalue().lower())

    def test_workflow_morning_includes_real_estate_daily_and_report_section(self) -> None:
        store = WorkflowStore(self.root)
        morning = store.get("Morning")
        commands = [step.command for step in morning.steps]
        self.assertIn("real-estate daily", commands)
        self.assertGreater(commands.index("real-estate daily"), commands.index("process research"))

        run = RealEstateDailyEngine(self.root).run(overwrite=True)
        workflow_run = WorkflowRun(
            run_id="workflow_test",
            workflow_id="morning",
            workflow_name="Morning",
            started_at="2026-07-15T00:00:00-07:00",
            completed_at="2026-07-15T00:00:01-07:00",
            duration=1.0,
            status="completed",
            executed_steps=[
                {
                    "name": "Real Estate Daily Automation",
                    "command": "real-estate daily",
                    "status": run.status,
                    "details": {
                        "real_estate_daily_run_id": run.run_id,
                        "daily_report_path": run.output_paths["daily_report"],
                        "review_queue_path": run.output_paths.get("review_queue", ""),
                    },
                }
            ],
            failed_steps=[],
            version="7.2.4",
        )
        report = render_workflow_report(workflow_run)
        self.assertIn("Real Estate Daily Automation", report)
        self.assertIn("Daily report", report)
        self.assertIn(run.output_paths["daily_report"], report)

    def test_dashboard_includes_real_estate_daily_summary(self) -> None:
        write_assignment(self.intake_root / "incoming" / "daily.json")
        RealEstateDailyEngine(self.root).run(overwrite=True)
        dashboard = ExecutiveDashboardBuilder(self.root).build()
        summary = dashboard.real_estate_assignment_summary

        self.assertTrue(summary["daily_run_available"])
        self.assertIn(summary["daily_run_status"], {"completed", "completed_with_warnings"})
        self.assertEqual(summary["daily_artifacts_imported"], 1)
        self.assertEqual(dashboard.executive_summary["real_estate_daily_status"], summary["daily_run_status"])

    def test_missing_intake_config_degrades_with_warning(self) -> None:
        tempdir = tempfile.TemporaryDirectory()
        try:
            root = Path(tempdir.name) / "repo"
            root.mkdir()
            run = RealEstateDailyEngine(root).run(overwrite=True)
            self.assertEqual(run.status, "completed")
            self.assertEqual(run.intake_candidates, 0)
            self.assertEqual(run.warning_count, 0)
            self.assertEqual(run.error_count, 0)
        finally:
            tempdir.cleanup()

    def test_batch_launcher_contains_real_estate_conditional_review_logic(self) -> None:
        text = (Path(__file__).resolve().parents[1] / "tools" / "run_constellation_morning.bat").read_text(encoding="utf-8")
        self.assertIn("latest-real-estate-daily-run.json", text)
        self.assertIn("real-estate-daily-report.md", text)
        self.assertIn("review-queue.md", text)
        self.assertIn("OPEN_REAL_ESTATE", text)


if __name__ == "__main__":
    unittest.main()
