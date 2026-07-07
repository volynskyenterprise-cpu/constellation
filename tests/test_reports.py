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
from constellation.io import write_json
from constellation.reports import InstitutionalResearchReportBuilder, InstitutionalResearchReportStore
from constellation.workflow import WorkflowStore


class InstitutionalResearchReportTests(unittest.TestCase):
    def test_empty_state_report_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)

            report = InstitutionalResearchReportStore(root).generate()

            self.assertEqual(len(report.sections), 13)
            self.assertTrue(report.missing_artifacts)
            self.assertTrue((root / "outputs" / "reports" / "latest-report.json").exists())

    def test_report_generation_from_existing_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            _write_artifacts(root)

            report = InstitutionalResearchReportStore(root).generate()

            self.assertEqual(report.risks_gaps, ["Review evidence quality."])
            self.assertEqual(report.thesis_references, ["thesis_1"])
            self.assertEqual(len(report.evidence_references), 1)

    def test_missing_artifact_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)

            status = InstitutionalResearchReportBuilder(root).status()
            report = InstitutionalResearchReportStore(root).generate()

            self.assertGreater(len([item for item in status.values() if not item["exists"]]), 0)
            self.assertIn("dashboard", report.missing_artifacts)

    def test_markdown_export(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            store = InstitutionalResearchReportStore(root)
            store.generate()

            output = store.export()

            self.assertTrue(output.exists())
            self.assertIn("# Institutional Research Report", output.read_text(encoding="utf-8"))

    def test_report_status(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            _write_artifacts(root)

            status = InstitutionalResearchReportStore(root).status()

            self.assertEqual(status["total_inputs"], 13)
            self.assertGreater(status["available_inputs"], 0)

    def test_report_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            store = InstitutionalResearchReportStore(root)

            store.generate()
            store.generate()

            self.assertEqual(len(store.history()), 2)

    def test_report_show(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            store = InstitutionalResearchReportStore(root)
            report = store.generate()

            shown = store.show(report.report_id)

            self.assertEqual(shown.report_id, report.report_id)

    def test_cli_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            _write_artifacts(root)

            latest_output = io.StringIO()
            with redirect_stdout(latest_output):
                latest_exit = main(["report", "--root", str(root), "latest", "--export"])
            report_id = json.loads((root / "outputs" / "reports" / "latest-report.json").read_text(encoding="utf-8"))["report_id"]
            status_output = io.StringIO()
            with redirect_stdout(status_output):
                status_exit = main(["report", "--root", str(root), "status"])
            history_output = io.StringIO()
            with redirect_stdout(history_output):
                history_exit = main(["report", "--root", str(root), "history"])
            show_output = io.StringIO()
            with redirect_stdout(show_output):
                show_exit = main(["report", "--root", str(root), "show", report_id])

            self.assertEqual(latest_exit, 0)
            self.assertEqual(status_exit, 0)
            self.assertEqual(history_exit, 0)
            self.assertEqual(show_exit, 0)
            self.assertIn("report_id:", latest_output.getvalue())
            self.assertIn("available_inputs:", status_output.getvalue())
            self.assertIn(report_id, show_output.getvalue())

    def test_dashboard_integration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            InstitutionalResearchReportStore(root).generate()

            dashboard = ExecutiveDashboardStore(root).generate(overwrite=True)

            self.assertTrue(dashboard.institutional_research_report_summary["available"])
            self.assertIn("latest_report_id", dashboard.institutional_research_report_summary)

    def test_workflow_integration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)

            run = WorkflowStore(root).run("Morning")

            self.assertIn("report latest", [step["command"] for step in run.executed_steps])
            self.assertTrue((root / "outputs" / "reports" / "latest-report.json").exists())

    def test_deterministic_report_id(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            _write_artifacts(root)
            store = InstitutionalResearchReportStore(root)

            first = store.generate()
            second = store.generate()

            self.assertEqual(first.report_id, second.report_id)

    def test_no_provider_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)

            with patch("constellation.providers.EchoProvider.generate") as generate:
                InstitutionalResearchReportStore(root).generate()

            generate.assert_not_called()


def _create_minimal_tree(root: Path) -> None:
    for relative in [
        "config",
        "outputs/dashboard",
        "outputs/daily",
        "outputs/morning",
        "outputs/evolution",
        "outputs/thesis",
        "outputs/evidence-graph",
        "outputs/memory",
        "outputs/source-monitor",
        "outputs/workflows",
        "outputs/intake",
        "outputs/google-drive",
        "inbox/google-drive/incoming",
        "inbox/gmail/incoming",
        "inbox/manual/incoming",
        "memory/evidence",
        "memory/graph",
        "logs/runs",
    ]:
        (root / relative).mkdir(parents=True, exist_ok=True)
    (root / "config" / "sources.yaml").write_text("sources: []\n", encoding="utf-8")
    (root / "config" / "google-drive.example.yaml").write_text(
        "credentials_path: config/secrets/google-drive-client.json\n"
        "token_path: config/secrets/google-drive-token.json\n"
        "scopes:\n"
        "  - drive.readonly\n",
        encoding="utf-8",
    )


def _write_artifacts(root: Path) -> None:
    write_json(
        root / "outputs" / "dashboard" / "dashboard.json",
        {
            "dashboard_id": "dashboard_1",
            "executive_summary": {"status": "completed"},
            "current_risks_gaps": ["Review evidence quality."],
            "recommended_next_actions": ["Review source documents."],
        },
    )
    write_json(root / "outputs" / "daily" / "daily-run.json", {"run_id": "daily_1", "status": "completed"})
    write_json(root / "outputs" / "morning" / "morning-brief.json", {"brief_id": "morning_1", "risks_or_gaps": [], "recommended_next_actions": []})
    write_json(
        root / "outputs" / "evolution" / "evolution.json",
        {"delta": {"delta_id": "delta_1", "summary": "Evidence increased.", "evidence_gained": ["ev_1"], "evidence_removed": [], "graph_node_growth": 1, "graph_edge_growth": 1, "trend_records": [], "longitudinal_health_score": 80}},
    )
    write_json(
        root / "outputs" / "thesis" / "theses.json",
        {"theses": [{"thesis_id": "thesis_1", "title": "Robotics thesis", "status": "active", "confidence": {"label": "medium"}, "supporting_evidence_ids": ["ev_1"], "conflicting_evidence_ids": [], "source_ids": ["source-a"]}]},
    )
    write_json(
        root / "outputs" / "evidence-graph" / "evidence-graph.json",
        {
            "nodes": [{"node_id": "ev_1", "node_type": "evidence", "label": "Evidence one", "source_ids": ["source-a"], "artifact_ids": []}],
            "edges": [],
        },
    )
    write_json(root / "outputs" / "memory" / "latest-snapshot.json", {"snapshot_id": "snapshot_1", "source_document_references": ["source-a"]})
    write_json(root / "outputs" / "source-monitor" / "latest-monitor.json", {"monitor_id": "monitor_1", "summary": {"sources_checked": 1, "sources_changed": 1}})
    write_json(root / "outputs" / "workflows" / "latest-workflow.json", {"run_id": "workflow_1", "executed_steps": []})
    write_json(root / "outputs" / "intake" / "intake-manifest.json", {"manifest_id": "manifest_1", "counts": {"imported": 1}, "items": [{"destination_path": "research_inputs/doc.md"}]})
    write_json(root / "outputs" / "google-drive" / "google-drive-sync-manifest.json", {"sync_id": "drive_1", "downloaded_files": []})


if __name__ == "__main__":
    unittest.main()
