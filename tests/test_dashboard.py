from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from constellation.cli import main
from constellation.dashboard import ExecutiveDashboardBuilder, ExecutiveDashboardStore
from constellation.io import write_json


NOW = "2026-07-06T09:00:00-07:00"


class ExecutiveDashboardTests(unittest.TestCase):
    def test_empty_state_dashboard(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            dashboard = ExecutiveDashboardStore(Path(temp_dir)).generate()

            self.assertEqual(dashboard.daily_pipeline_status["status"], "unavailable")
            self.assertIn("Unavailable artifacts", " ".join(dashboard.limitations))

    def test_dashboard_generation_from_existing_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_artifacts(root)

            dashboard = ExecutiveDashboardStore(root).generate()

            self.assertEqual(dashboard.daily_pipeline_status["status"], "completed")
            self.assertEqual(dashboard.evidence_summary["evidence_count"], 2)
            self.assertEqual(dashboard.thesis_intelligence_summary["thesis_count"], 2)
            self.assertEqual(dashboard.thesis_intelligence_summary["strengthening_count"], 1)
            self.assertEqual(dashboard.evidence_graph_summary["node_count"], 3)

    def test_missing_artifact_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_artifacts(root)
            (root / "outputs" / "daily" / "daily-run.json").unlink()

            dashboard = ExecutiveDashboardStore(root).generate()

            self.assertFalse(dashboard.artifact_status["daily_run"]["exists"])
            self.assertEqual(dashboard.daily_pipeline_status["status"], "unavailable")

    def test_status_command(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_artifacts(root)

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["dashboard", "--root", str(root), "status"])

            self.assertEqual(exit_code, 0)
            self.assertIn("dashboard_inputs:", output.getvalue())
            self.assertIn("available: daily_run", output.getvalue())

    def test_markdown_export(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_artifacts(root)
            store = ExecutiveDashboardStore(root)
            store.generate()

            output_path = store.export()

            self.assertTrue(output_path.exists())
            self.assertIn("# Executive Dashboard", output_path.read_text(encoding="utf-8"))

    def test_overwrite_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_artifacts(root)
            store = ExecutiveDashboardStore(root)
            store.generate()

            with self.assertRaises(Exception):
                store.generate()
            dashboard = store.generate(overwrite=True)

            self.assertEqual(dashboard.daily_pipeline_status["status"], "completed")

    def test_cli_generate_export_overwrite(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_artifacts(root)

            generate_output = io.StringIO()
            with redirect_stdout(generate_output):
                generate_exit = main(["dashboard", "--root", str(root)])
            export_output = io.StringIO()
            with redirect_stdout(export_output):
                export_exit = main(["dashboard", "--root", str(root), "--export"])
            overwrite_output = io.StringIO()
            with redirect_stdout(overwrite_output):
                overwrite_exit = main(["dashboard", "--root", str(root), "--overwrite"])

            self.assertEqual(generate_exit, 0)
            self.assertIn("dashboard_id:", generate_output.getvalue())
            self.assertEqual(export_exit, 0)
            self.assertIn("dashboard:", export_output.getvalue())
            self.assertEqual(overwrite_exit, 0)

    def test_deterministic_output_structure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_artifacts(root)

            first = ExecutiveDashboardBuilder(root).build().to_dict()
            second = ExecutiveDashboardBuilder(root).build().to_dict()
            first.pop("created_at")
            second.pop("created_at")

            self.assertEqual(first, second)

    def test_no_provider_execution_or_external_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_artifacts(root)
            with patch("constellation.providers.EchoProvider.generate") as generate:
                ExecutiveDashboardStore(root).generate()

            generate.assert_not_called()


def _write_artifacts(root: Path) -> None:
    write_json(
        root / "outputs" / "daily" / "daily-run.json",
        {
            "run_id": "daily_alpha",
            "status": "completed",
            "created_at": NOW,
            "completed_at": NOW,
            "runtime_seconds": 1.25,
            "version": "3.8.0",
            "stages": [],
            "manifest": {"thesis_count": 2, "evidence_graph_id": "evidence_graph_alpha"},
            "limitations": [],
        },
    )
    (root / "outputs" / "daily").mkdir(parents=True, exist_ok=True)
    (root / "outputs" / "daily" / "daily-report.md").write_text("# Daily", encoding="utf-8")
    write_json(
        root / "outputs" / "morning" / "morning-brief.json",
        {
            "brief_id": "morning_alpha",
            "created_at": NOW,
            "evidence_count": 2,
            "top_findings": [{"finding_id": "finding_alpha"}],
            "top_theses": [{"thesis_id": "thesis_alpha"}],
            "risks_or_gaps": ["Evidence gap: source coverage"],
            "recommended_next_actions": ["Review evidence graph."],
        },
    )
    write_json(
        root / "outputs" / "memory" / "latest-snapshot.json",
        {
            "snapshot_id": "snapshot_alpha",
            "label": "daily",
            "created_at": NOW,
            "intake_counts": {},
            "google_drive_sync_counts": {},
            "evidence_count": 2,
            "graph_node_count": 3,
            "graph_edge_count": 2,
            "findings_count": 1,
            "thesis_count": 2,
            "intelligence_brief_id": None,
            "morning_brief_id": "morning_alpha",
            "top_thesis_ids": ["thesis_alpha"],
            "top_finding_ids": ["finding_alpha"],
            "source_document_references": ["source.md"],
            "artifact_references": [],
            "limitations": [],
            "provenance_references": {},
        },
    )
    write_json(
        root / "outputs" / "memory" / "latest-delta.json",
        {
            "prior_snapshot_id": "snapshot_prior",
            "current_snapshot_id": "snapshot_alpha",
            "evidence_count_change": 1,
            "graph_node_change": 1,
            "graph_edge_change": 1,
            "findings_count_change": 1,
            "thesis_count_change": 1,
            "new_thesis_ids": ["thesis_alpha"],
            "removed_thesis_ids": [],
            "new_finding_ids": ["finding_alpha"],
            "removed_finding_ids": [],
            "new_source_references": ["source.md"],
            "removed_source_references": [],
            "summary": "Evidence +1, thesis +1.",
            "limitations": [],
        },
    )
    write_json(
        root / "outputs" / "evidence-graph" / "evidence-graph.json",
        {
            "graph_id": "evidence_graph_alpha",
            "created_at": NOW,
            "node_count": 3,
            "edge_count": 2,
            "nodes": [
                {"node_id": "eg_evidence_ev_1", "node_type": "evidence", "label": "Evidence", "references": ["ev_1"], "metadata": {}},
                {"node_id": "eg_source_source", "node_type": "source", "label": "source.md", "references": ["source.md"], "metadata": {}},
                {"node_id": "eg_thesis_thesis_alpha", "node_type": "thesis", "label": "Thesis", "references": ["thesis_alpha"], "metadata": {}},
            ],
            "edges": [],
            "limitations": [],
            "provenance": {},
        },
    )
    write_json(
        root / "outputs" / "thesis" / "theses.json",
        {
            "schema_version": "3.6.0",
            "created_at": NOW,
            "theses": [
                {
                    "thesis_id": "thesis_alpha",
                    "title": "Alpha",
                    "category": "strategic_theme",
                    "created_at": NOW,
                    "updated_at": NOW,
                    "status": "strengthening",
                    "supporting_evidence_ids": ["ev_1"],
                    "conflicting_evidence_ids": [],
                    "finding_ids": ["finding_alpha"],
                    "source_ids": ["source.md"],
                    "memory_snapshot_ids": ["snapshot_alpha"],
                    "morning_brief_ids": ["morning_alpha"],
                    "confidence": {
                        "label": "high",
                        "support_count": 1,
                        "conflict_count": 0,
                        "repeated_confirmation_count": 1,
                        "explicit_contradiction_count": 0,
                        "rule": "test",
                    },
                    "metadata": {},
                },
                {
                    "thesis_id": "thesis_beta",
                    "title": "Beta",
                    "category": "risk",
                    "created_at": NOW,
                    "updated_at": NOW,
                    "status": "active",
                    "supporting_evidence_ids": ["ev_2"],
                    "conflicting_evidence_ids": [],
                    "finding_ids": [],
                    "source_ids": ["source.md"],
                    "memory_snapshot_ids": [],
                    "morning_brief_ids": [],
                    "confidence": {
                        "label": "medium",
                        "support_count": 1,
                        "conflict_count": 0,
                        "repeated_confirmation_count": 0,
                        "explicit_contradiction_count": 0,
                        "rule": "test",
                    },
                    "metadata": {},
                },
            ],
        },
    )
    (root / "outputs" / "thesis" / "thesis-report.md").parent.mkdir(parents=True, exist_ok=True)
    (root / "outputs" / "thesis" / "thesis-report.md").write_text("# Thesis", encoding="utf-8")
    write_json(root / "outputs" / "google-drive" / "google-drive-sync-manifest.json", {"sync_id": "sync_alpha", "downloaded_files": [], "skipped_files": [], "errors": []})
    write_json(root / "outputs" / "intake" / "intake-manifest.json", {"manifest_id": "manifest_alpha", "counts": {"imported": 1, "duplicates": 0, "errors": 0}})


if __name__ == "__main__":
    unittest.main()
