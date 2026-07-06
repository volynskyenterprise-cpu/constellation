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
from constellation.dashboard import ExecutiveDashboardStore
from constellation.evolution import KnowledgeEvolutionEngine, KnowledgeEvolutionStore
from constellation.io import write_json


class KnowledgeEvolutionTests(unittest.TestCase):
    def test_empty_state_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)

            delta = KnowledgeEvolutionStore(root).generate()

            self.assertEqual(delta.evidence_gained, [])
            self.assertEqual(delta.graph_node_growth, 0)
            self.assertTrue((root / "outputs" / "evolution" / "evolution.json").exists())

    def test_snapshot_reads_current_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            _write_evidence(root, "ev_1", "source-a")
            _write_graph(root, nodes=2, edges=1)
            _write_theses(root, [{"thesis_id": "thesis_1", "confidence": {"label": "medium"}, "status": "active"}])

            snapshot = KnowledgeEvolutionEngine(root).current_snapshot()

            self.assertEqual(snapshot.evidence_count, 1)
            self.assertEqual(snapshot.graph_node_count, 2)
            self.assertIn("thesis_1", snapshot.thesis_states)

    def test_evidence_gained_between_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            store = KnowledgeEvolutionStore(root)
            store.generate()
            _write_evidence(root, "ev_1", "source-a")

            delta = store.generate()

            self.assertEqual(delta.evidence_gained, ["ev_1"])

    def test_evidence_removed_between_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            _write_evidence(root, "ev_1", "source-a")
            store = KnowledgeEvolutionStore(root)
            store.generate()
            (root / "memory" / "evidence" / "ev_1.json").unlink()

            delta = store.generate()

            self.assertEqual(delta.evidence_removed, ["ev_1"])

    def test_graph_growth(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            _write_graph(root, nodes=1, edges=1)
            store = KnowledgeEvolutionStore(root)
            store.generate()
            _write_graph(root, nodes=3, edges=4)

            delta = store.generate()

            self.assertEqual(delta.graph_node_growth, 2)
            self.assertEqual(delta.graph_edge_growth, 3)

    def test_thesis_confidence_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            _write_theses(root, [{"thesis_id": "thesis_1", "confidence": {"label": "low"}, "status": "active"}])
            store = KnowledgeEvolutionStore(root)
            store.generate()
            _write_theses(root, [{"thesis_id": "thesis_1", "confidence": {"label": "high"}, "status": "active"}])

            delta = store.generate()

            self.assertEqual(delta.thesis_confidence_changes[0]["thesis_id"], "thesis_1")

    def test_thesis_status_change(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            _write_theses(root, [{"thesis_id": "thesis_1", "confidence": {"label": "medium"}, "status": "active"}])
            store = KnowledgeEvolutionStore(root)
            store.generate()
            _write_theses(root, [{"thesis_id": "thesis_1", "confidence": {"label": "medium"}, "status": "weakening"}])

            delta = store.generate()

            self.assertEqual(delta.thesis_status_changes[0]["to"], "weakening")

    def test_source_activity_trends(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            store = KnowledgeEvolutionStore(root)
            store.generate()
            _write_source_history(root, new_items=2)

            delta = store.generate()

            self.assertTrue(delta.source_activity_trends)

    def test_research_volume_trends(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            store = KnowledgeEvolutionStore(root)
            store.generate()
            _write_workflow_history(root, research_runs=3)

            delta = store.generate()

            self.assertTrue(any(record.trend_type == "research_volume" for record in delta.trend_records))

    def test_workflow_execution_trends(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            store = KnowledgeEvolutionStore(root)
            store.generate()
            _write_workflow_history(root, research_runs=0)

            delta = store.generate()

            self.assertTrue(any(record.trend_type == "workflow_execution" for record in delta.trend_records))

    def test_export_writes_markdown_reports(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            store = KnowledgeEvolutionStore(root)
            store.generate()

            output = store.export()

            self.assertTrue(output.exists())
            self.assertTrue((root / "outputs" / "evolution" / "trend-report.md").exists())

    def test_cli_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)

            run_out = io.StringIO()
            with redirect_stdout(run_out):
                run_exit = main(["evolution", "--root", str(root)])
            status_out = io.StringIO()
            with redirect_stdout(status_out):
                status_exit = main(["evolution", "--root", str(root), "status"])
            history_out = io.StringIO()
            with redirect_stdout(history_out):
                history_exit = main(["evolution", "--root", str(root), "history"])
            export_out = io.StringIO()
            with redirect_stdout(export_out):
                export_exit = main(["evolution", "--root", str(root), "export"])

            self.assertEqual(run_exit, 0)
            self.assertEqual(status_exit, 0)
            self.assertEqual(history_exit, 0)
            self.assertEqual(export_exit, 0)
            self.assertIn("delta_id:", run_out.getvalue())
            self.assertIn("evolution_report:", export_out.getvalue())

    def test_compare_cli_with_memory_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            first = _write_memory_snapshot(root, "snapshot_a", 1)
            second = _write_memory_snapshot(root, "snapshot_b", 2, append=True)

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["evolution", "--root", str(root), "compare", first, second])

            self.assertEqual(exit_code, 0)
            self.assertIn('"current_snapshot_id"', output.getvalue())

    def test_dashboard_integration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            KnowledgeEvolutionStore(root).generate()

            dashboard = ExecutiveDashboardStore(root).generate(overwrite=True)

            self.assertTrue(dashboard.knowledge_evolution_summary["available"])
            self.assertIn("longitudinal_health_score", dashboard.knowledge_evolution_summary)

    def test_daily_pipeline_integration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)

            run = DailyPipelineStore(root).run()

            self.assertIn("knowledge_evolution", [stage["name"] for stage in run.stages])
            self.assertTrue((root / "outputs" / "evolution" / "evolution.json").exists())

    def test_no_provider_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)

            with patch("constellation.providers.EchoProvider.generate") as generate:
                KnowledgeEvolutionStore(root).generate()

            generate.assert_not_called()


def _create_minimal_tree(root: Path) -> None:
    for relative in [
        "config",
        "memory/evidence",
        "memory/graph",
        "outputs/memory",
        "outputs/source-monitor",
        "outputs/workflows",
        "outputs/thesis",
        "outputs/daily",
        "inbox/google-drive/incoming",
        "inbox/gmail/incoming",
        "inbox/manual/incoming",
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


def _write_evidence(root: Path, evidence_id: str, source: str) -> None:
    write_json(root / "memory" / "evidence" / f"{evidence_id}.json", {"evidence_id": evidence_id, "source_identifier": source})


def _write_graph(root: Path, *, nodes: int, edges: int) -> None:
    write_json(
        root / "memory" / "graph" / "graph.json",
        {
            "nodes": [{"node_id": f"node_{index}", "node_type": "concept"} for index in range(nodes)],
            "edges": [{"edge_id": f"edge_{index}"} for index in range(edges)],
        },
    )


def _write_theses(root: Path, theses: list[dict]) -> None:
    normalized = []
    for thesis in theses:
        normalized.append(
            {
                "thesis_id": thesis["thesis_id"],
                "title": thesis["thesis_id"],
                "status": thesis.get("status", "active"),
                "confidence": thesis.get("confidence", {"label": "medium"}),
                "supporting_evidence_ids": [],
                "conflicting_evidence_ids": [],
                "source_ids": [],
            }
        )
    write_json(root / "outputs" / "thesis" / "theses.json", {"theses": normalized})


def _write_source_history(root: Path, *, new_items: int) -> None:
    write_json(
        root / "outputs" / "source-monitor" / "source-history.json",
        {
            "runs": [
                {
                    "changes": [
                        {
                            "source_id": "source-a",
                            "new_items": [f"item_{index}" for index in range(new_items)],
                            "removed_items": [],
                            "updated_items": [],
                            "failed_items": [],
                        }
                    ]
                }
            ]
        },
    )


def _write_workflow_history(root: Path, *, research_runs: int) -> None:
    run = {
        "run_id": "workflow_a",
        "workflow_id": "morning",
        "workflow_name": "Morning",
        "status": "completed",
        "executed_steps": [
            {
                "command": "process research",
                "details": {
                    "new_research_files_detected": research_runs,
                    "research_runs_created": research_runs,
                    "graph_builds_completed": research_runs,
                    "graph_builds_failed": 0,
                },
            }
        ],
    }
    write_json(root / "outputs" / "workflows" / "workflow-history.json", {"runs": [run]})
    write_json(root / "outputs" / "workflows" / "latest-workflow.json", run)


def _write_memory_snapshot(root: Path, snapshot_id: str, evidence_count: int, *, append: bool = False) -> str:
    path = root / "outputs" / "memory" / "snapshots.json"
    existing = []
    if append and path.exists():
        existing = json.loads(path.read_text(encoding="utf-8")).get("snapshots", [])
    snapshot = {
        "snapshot_id": snapshot_id,
        "label": None,
        "created_at": "2026-07-06T00:00:00-07:00",
        "intake_counts": {},
        "google_drive_sync_counts": {},
        "evidence_count": evidence_count,
        "graph_node_count": evidence_count,
        "graph_edge_count": evidence_count,
        "findings_count": 0,
        "thesis_count": 0,
        "intelligence_brief_id": None,
        "morning_brief_id": None,
        "top_thesis_ids": [],
        "top_finding_ids": [],
        "source_document_references": [f"source_{evidence_count}"],
        "artifact_references": [],
        "limitations": [],
        "provenance_references": {},
    }
    write_json(path, {"snapshots": [*existing, snapshot]})
    return snapshot_id


if __name__ == "__main__":
    unittest.main()
