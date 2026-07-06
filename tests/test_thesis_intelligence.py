from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from constellation.cli import main
from constellation.cross_document import CrossDocumentAnalysis, CrossDocumentAnalysisStore, CrossDocumentFinding
from constellation.io import write_json
from constellation.thesis import Thesis, ThesisStore as GeneratedThesisStore
from constellation.thesis_intelligence import ThesisEngine, ThesisStore


NOW = "2026-07-06T09:00:00-07:00"


class ThesisIntelligenceTests(unittest.TestCase):
    def test_empty_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            records = ThesisStore(Path(temp_dir)).build()

            self.assertEqual(records, [])

    def test_build_from_generated_theses(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _save_generated_thesis(root, support=["ev_1"])

            records = ThesisStore(root).build()

            self.assertEqual(len(records), 1)
            self.assertEqual(records[0].thesis_id, "thesis_alpha")
            self.assertEqual(records[0].status, "active")
            self.assertEqual(records[0].confidence.label, "medium")
            self.assertEqual(records[0].supporting_evidence_ids, ["ev_1"])

    def test_confidence_rules(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _save_generated_thesis(root, support=["ev_1", "ev_2", "ev_3"])
            _save_findings(root, [_finding("finding_repeat", "repeated_theme", ["ev_1", "ev_2", "ev_3"])])

            record = ThesisStore(root).build()[0]

            self.assertEqual(record.confidence.label, "high")
            self.assertEqual(record.status, "strengthening")
            self.assertEqual(record.confidence.rule, "support_count_or_repeated_confirmations")

    def test_timeline_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _save_generated_thesis(root, support=["ev_1"])

            store = ThesisStore(root)
            records = store.build()
            events = store.timeline(records[0].thesis_id)

            self.assertEqual(events[0].event_type, "created")
            self.assertEqual(events[0].affected_evidence_ids, ["ev_1"])

    def test_export(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _save_generated_thesis(root, support=["ev_1"])

            store = ThesisStore(root)
            store.build()
            output_path = store.export()

            self.assertTrue(output_path.exists())
            markdown = output_path.read_text(encoding="utf-8")
            self.assertIn("# Thesis Intelligence", markdown)
            self.assertIn("Supporting relationships: 1", markdown)

    def test_cli(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _save_generated_thesis(root, support=["ev_1"])

            build_output = io.StringIO()
            with redirect_stdout(build_output):
                build_exit = main(["thesis", "--root", str(root), "build"])
            list_output = io.StringIO()
            with redirect_stdout(list_output):
                list_exit = main(["thesis", "--root", str(root), "list"])
            show_output = io.StringIO()
            with redirect_stdout(show_output):
                show_exit = main(["thesis", "--root", str(root), "show", "thesis_alpha"])
            timeline_output = io.StringIO()
            with redirect_stdout(timeline_output):
                timeline_exit = main(["thesis", "--root", str(root), "timeline", "thesis_alpha"])
            export_output = io.StringIO()
            with redirect_stdout(export_output):
                export_exit = main(["thesis", "--root", str(root), "export"])

            self.assertEqual(build_exit, 0)
            self.assertIn("count: 1", build_output.getvalue())
            self.assertEqual(list_exit, 0)
            self.assertIn("support=1", list_output.getvalue())
            self.assertEqual(show_exit, 0)
            self.assertEqual(json.loads(show_output.getvalue())["thesis_id"], "thesis_alpha")
            self.assertEqual(timeline_exit, 0)
            self.assertIn("created", timeline_output.getvalue())
            self.assertEqual(export_exit, 0)
            self.assertIn("thesis-report.md", export_output.getvalue())

    def test_deterministic_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _save_generated_thesis(root, support=["ev_1"])

            first = ThesisEngine(root).build([])[0][0].to_dict()
            second = ThesisEngine(root).build([])[0][0].to_dict()

            first.pop("created_at")
            first.pop("updated_at")
            second.pop("created_at")
            second.pop("updated_at")
            self.assertEqual(first, second)

    def test_conflict_handling(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _save_generated_thesis(root, support=["ev_1"], counterpoints=["finding_conflict"])
            _save_findings(root, [_finding("finding_conflict", "possible_contradiction", ["ev_conflict"])])

            record = ThesisStore(root).build()[0]

            self.assertEqual(record.conflicting_evidence_ids, ["ev_conflict"])
            self.assertEqual(record.status, "weakening")
            self.assertEqual(record.confidence.rule, "explicit_contradiction_or_conflict")

    def test_strengthening(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _save_generated_thesis(root, support=["ev_1"])
            store = ThesisStore(root)
            store.build()

            _save_generated_thesis(root, support=["ev_1", "ev_2"])
            records = store.build()
            events = store.timeline("thesis_alpha")

            self.assertEqual(records[0].status, "strengthening")
            self.assertTrue(any(event.event_type == "strengthened" for event in events))

    def test_weakening(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _save_generated_thesis(root, support=["ev_1"])
            store = ThesisStore(root)
            store.build()

            _save_generated_thesis(root, support=["ev_1"], counterpoints=["finding_conflict"])
            _save_findings(root, [_finding("finding_conflict", "possible_contradiction", ["ev_conflict"])])
            records = store.build()
            events = store.timeline("thesis_alpha")

            self.assertEqual(records[0].status, "weakening")
            self.assertTrue(any(event.event_type == "weakened" for event in events))

    def test_archiving(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _save_generated_thesis(root, support=["ev_1"])
            store = ThesisStore(root)
            store.build()

            (root / "outputs" / "theses" / "theses.json").unlink()
            records = store.build()

            self.assertEqual(records[0].status, "archived")
            self.assertTrue(any(event.event_type == "archived" for event in store.timeline("thesis_alpha")))

    def test_morning_memory_and_evidence_graph_integration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _save_generated_thesis(root, support=["ev_1"])
            _save_morning(root)
            _save_memory(root)
            _save_evidence_graph(root)

            record = ThesisStore(root).build()[0]

            self.assertEqual(record.morning_brief_ids, ["morning_alpha"])
            self.assertEqual(record.memory_snapshot_ids, ["snapshot_alpha"])
            self.assertEqual(record.supporting_evidence_ids, ["ev_1", "ev_2"])

    def test_no_provider_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _save_generated_thesis(root, support=["ev_1"])
            with patch("constellation.providers.EchoProvider.generate") as generate:
                ThesisStore(root).build()

            generate.assert_not_called()


def _save_generated_thesis(root: Path, *, support: list[str], counterpoints: list[str] | None = None) -> None:
    GeneratedThesisStore(root).save(
        [
            Thesis(
                thesis_id="thesis_alpha",
                title="Strategic theme: alpha",
                summary="Alpha thesis.",
                thesis_type="strategic_theme",
                status="proposed",
                confidence="medium",
                supporting_finding_ids=["finding_repeat"],
                supporting_evidence_ids=support,
                supporting_node_ids=[],
                source_ids=["source-alpha.md"],
                workflow_run_ids=["run_alpha"],
                counterpoint_finding_ids=counterpoints or [],
                risks=[],
                assumptions=[],
                recommendations=["Review alpha."],
                open_questions=[],
                rationale="Exact test thesis.",
                metadata={},
                created_at=NOW,
                updated_at=NOW,
            )
        ],
        metadata={"test": True},
    )


def _save_findings(root: Path, findings: list[CrossDocumentFinding]) -> None:
    CrossDocumentAnalysisStore(root).save(
        CrossDocumentAnalysis(
            analysis_id="analysis_alpha",
            graph_version="graph_alpha",
            findings=findings,
            created_at=NOW,
            metadata={"test": True},
        )
    )


def _finding(finding_id: str, finding_type: str, evidence_ids: list[str]) -> CrossDocumentFinding:
    return CrossDocumentFinding(
        finding_id=finding_id,
        finding_type=finding_type,
        title="Finding",
        summary="Summary",
        node_ids=["node_alpha"],
        evidence_ids=evidence_ids,
        source_ids=["source-alpha.md"],
        workflow_run_ids=["run_alpha"],
        confidence="high",
        rationale="Exact test finding.",
        metadata={},
        created_at=NOW,
    )


def _save_morning(root: Path) -> None:
    write_json(
        root / "outputs" / "morning" / "morning-brief.json",
        {
            "brief_id": "morning_alpha",
            "created_at": NOW,
            "intake_summary": {},
            "google_drive_sync_summary": {},
            "new_documents_detected": [],
            "evidence_count": 1,
            "graph_node_count": 0,
            "graph_edge_count": 0,
            "top_findings": [],
            "top_theses": [{"thesis_id": "thesis_alpha", "title": "Strategic theme: alpha"}],
            "intelligence_summary": {},
            "risks_or_gaps": [],
            "recommended_next_actions": [],
            "provenance_references": {},
            "limitations": [],
        },
    )


def _save_memory(root: Path) -> None:
    write_json(
        root / "outputs" / "memory" / "snapshots.json",
        {
            "snapshots": [
                {
                    "snapshot_id": "snapshot_alpha",
                    "label": "alpha",
                    "created_at": NOW,
                    "intake_counts": {},
                    "google_drive_sync_counts": {},
                    "evidence_count": 1,
                    "graph_node_count": 0,
                    "graph_edge_count": 0,
                    "findings_count": 1,
                    "thesis_count": 1,
                    "intelligence_brief_id": None,
                    "morning_brief_id": "morning_alpha",
                    "top_thesis_ids": ["thesis_alpha"],
                    "top_finding_ids": [],
                    "source_document_references": ["source-alpha.md"],
                    "artifact_references": [],
                    "limitations": [],
                    "provenance_references": {},
                }
            ]
        },
    )


def _save_evidence_graph(root: Path) -> None:
    write_json(
        root / "outputs" / "evidence-graph" / "evidence-graph.json",
        {
            "graph_id": "evidence_graph_alpha",
            "created_at": NOW,
            "node_count": 2,
            "edge_count": 3,
            "nodes": [
                {"node_id": "eg_evidence_ev_2", "node_type": "evidence", "label": "Evidence 2", "references": ["ev_2"], "metadata": {}},
                {"node_id": "eg_thesis_thesis_alpha", "node_type": "thesis", "label": "Strategic theme: alpha", "references": ["thesis_alpha"], "metadata": {}},
                {"node_id": "eg_morning_brief_morning_alpha", "node_type": "morning_brief", "label": "morning_alpha", "references": ["morning_alpha"], "metadata": {}},
                {"node_id": "eg_memory_snapshot_snapshot_alpha", "node_type": "memory_snapshot", "label": "snapshot_alpha", "references": ["snapshot_alpha"], "metadata": {}},
            ],
            "edges": [
                {
                    "edge_id": "edge_support",
                    "source_node_id": "eg_evidence_ev_2",
                    "target_node_id": "eg_thesis_thesis_alpha",
                    "edge_type": "supports",
                    "evidence_ids": ["ev_2"],
                    "metadata": {},
                },
                {
                    "edge_id": "edge_morning",
                    "source_node_id": "eg_thesis_thesis_alpha",
                    "target_node_id": "eg_morning_brief_morning_alpha",
                    "edge_type": "summarized_by",
                    "evidence_ids": [],
                    "metadata": {},
                },
                {
                    "edge_id": "edge_memory",
                    "source_node_id": "eg_thesis_thesis_alpha",
                    "target_node_id": "eg_memory_snapshot_snapshot_alpha",
                    "edge_type": "preserved_in",
                    "evidence_ids": [],
                    "metadata": {},
                },
            ],
            "limitations": [],
            "provenance": {},
        },
    )


if __name__ == "__main__":
    unittest.main()
