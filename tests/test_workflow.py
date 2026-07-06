from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from constellation.cli import main
from constellation.dashboard import ExecutiveDashboardStore
from constellation.workflow import WorkflowDefinition, WorkflowEngine, WorkflowStep, WorkflowStore


class WorkflowAutomationTests(unittest.TestCase):
    def test_builtin_workflow_definitions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)

            definitions = WorkflowStore(root).definitions()

            self.assertEqual([definition.name for definition in definitions], ["Morning", "Research Refresh", "Executive Snapshot"])
            self.assertTrue((root / "outputs" / "workflows" / "workflow-definitions.json").exists())

    def test_show_workflow_by_name(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)

            definition = WorkflowStore(root).get("Morning")

            self.assertEqual(definition.id, "morning")
            self.assertEqual([step.command for step in definition.steps], _MORNING_COMMANDS)

    def test_unknown_workflow_fails(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)

            with self.assertRaises(Exception):
                WorkflowStore(root).get("Unknown")

    def test_run_executive_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)

            run = WorkflowStore(root).run("Executive Snapshot")

            self.assertEqual(run.status, "completed")
            self.assertEqual(run.workflow_name, "Executive Snapshot")
            self.assertEqual(len(run.executed_steps), 3)
            self.assertTrue((root / "outputs" / "workflows" / "latest-workflow.json").exists())
            self.assertTrue((root / "outputs" / "workflows" / "workflow-report.md").exists())

    def test_run_morning_workflow_skips_unconfigured_drive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root, include_google_config=False)

            run = WorkflowStore(root).run("Morning")

            self.assertEqual(run.status, "completed")
            drive_step = next(step for step in run.executed_steps if step["command"] == "drive sync")
            self.assertEqual(drive_step["status"], "skipped")

    def test_history_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            store = WorkflowStore(root)

            store.run("Executive Snapshot")
            store.run("Executive Snapshot")

            history = store.history()
            self.assertEqual(len(history), 2)
            self.assertEqual(history[-1].workflow_name, "Executive Snapshot")

    def test_export_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            store = WorkflowStore(root)
            store.run("Executive Snapshot")

            output_path = store.export()

            self.assertTrue(output_path.exists())
            self.assertIn("# Workflow Automation Report", output_path.read_text(encoding="utf-8"))

    def test_continue_on_failure_allows_later_steps(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            definition = WorkflowDefinition(
                id="failure-test",
                name="Failure Test",
                description="Test continue-on-failure.",
                enabled=True,
                created_at="2026-07-06T00:00:00-07:00",
                updated_at="2026-07-06T00:00:00-07:00",
                steps=[
                    WorkflowStep("Bad Step", "missing command", {}, True, True),
                    WorkflowStep("Intake Scan", "intake scan", {}, True, False),
                ],
            )

            run = WorkflowEngine(root).run(definition)

            self.assertEqual(run.status, "completed_with_failures")
            self.assertEqual(len(run.executed_steps), 2)
            self.assertEqual(len(run.failed_steps), 1)

    def test_failure_without_continue_stops_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            definition = WorkflowDefinition(
                id="blocked-test",
                name="Blocked Test",
                description="Test blocking failure.",
                enabled=True,
                created_at="2026-07-06T00:00:00-07:00",
                updated_at="2026-07-06T00:00:00-07:00",
                steps=[
                    WorkflowStep("Bad Step", "missing command", {}, True, False),
                    WorkflowStep("Intake Scan", "intake scan", {}, True, False),
                ],
            )

            run = WorkflowEngine(root).run(definition)

            self.assertEqual(run.status, "failed")
            self.assertEqual(len(run.executed_steps), 1)

    def test_disabled_step_is_skipped(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            definition = WorkflowDefinition(
                id="disabled-step-test",
                name="Disabled Step Test",
                description="Test disabled steps.",
                enabled=True,
                created_at="2026-07-06T00:00:00-07:00",
                updated_at="2026-07-06T00:00:00-07:00",
                steps=[WorkflowStep("Disabled", "intake scan", {}, False, False)],
            )

            run = WorkflowEngine(root).run(definition)

            self.assertEqual(run.status, "completed")
            self.assertEqual(run.executed_steps[0]["status"], "skipped")

    def test_dashboard_reads_latest_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            WorkflowStore(root).run("Executive Snapshot")

            dashboard = ExecutiveDashboardStore(root).generate(overwrite=True)

            self.assertTrue(dashboard.workflow_automation_summary["available"])
            self.assertEqual(dashboard.workflow_automation_summary["workflow_name"], "Executive Snapshot")

    def test_cli_workflow_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)

            list_output = io.StringIO()
            with redirect_stdout(list_output):
                list_exit = main(["workflow", "--root", str(root), "list"])
            run_output = io.StringIO()
            with redirect_stdout(run_output):
                run_exit = main(["workflow", "--root", str(root), "run", "Executive Snapshot"])
            show_output = io.StringIO()
            with redirect_stdout(show_output):
                show_exit = main(["workflow", "--root", str(root), "show", "Morning"])
            history_output = io.StringIO()
            with redirect_stdout(history_output):
                history_exit = main(["workflow", "--root", str(root), "history"])
            export_output = io.StringIO()
            with redirect_stdout(export_output):
                export_exit = main(["workflow", "--root", str(root), "export"])

            self.assertEqual(list_exit, 0)
            self.assertEqual(run_exit, 0)
            self.assertEqual(show_exit, 0)
            self.assertEqual(history_exit, 0)
            self.assertEqual(export_exit, 0)
            self.assertIn("Morning", list_output.getvalue())
            self.assertIn("workflow_run_id:", run_output.getvalue())
            self.assertIn('"id": "morning"', show_output.getvalue())
            self.assertIn("Executive Snapshot", history_output.getvalue())
            self.assertIn("workflow_report:", export_output.getvalue())

    def test_no_provider_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)

            with patch("constellation.providers.EchoProvider.generate") as generate:
                WorkflowStore(root).run("Executive Snapshot")

            generate.assert_not_called()

    def test_latest_workflow_json_shape(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            WorkflowStore(root).run("Executive Snapshot")

            data = json.loads((root / "outputs" / "workflows" / "latest-workflow.json").read_text(encoding="utf-8"))

            self.assertEqual(data["workflow_id"], "executive-snapshot")
            self.assertIn("executed_steps", data)
            self.assertIn("failed_steps", data)


_MORNING_COMMANDS = [
    "monitor",
    "drive sync",
    "intake scan",
    "morning",
    "memory snapshot",
    "evidence-graph build",
    "thesis build",
    "daily",
    "dashboard",
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
