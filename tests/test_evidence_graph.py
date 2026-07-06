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
from constellation.evidence import EvidenceItem, EvidenceStore
from constellation.evidence_graph import EvidenceGraphBuilder, EvidenceGraphStore
from constellation.io import read_json, write_json
from constellation.thesis import Thesis, ThesisStore


NOW = "2026-07-06T09:00:00-07:00"


class EvidenceGraphTests(unittest.TestCase):
    def test_empty_state_build(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            graph = EvidenceGraphStore(Path(temp_dir)).build()

            self.assertEqual(graph.to_dict()["node_count"], 0)
            self.assertEqual(graph.to_dict()["edge_count"], 0)
            self.assertIn("No evidence records found.", graph.limitations)

    def test_node_creation_from_evidence_records(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _save_evidence(root)

            graph = EvidenceGraphStore(root).build()
            node_types = {node.node_type for node in graph.nodes.values()}
            edge_types = {edge.edge_type for edge in graph.edges.values()}

            self.assertIn("evidence", node_types)
            self.assertIn("source", node_types)
            self.assertIn("workflow", node_types)
            self.assertIn("derived_from", edge_types)
            self.assertIn("appears_in", edge_types)

    def test_source_workflow_and_artifact_nodes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _save_evidence(root)
            _save_artifact(root)

            graph = EvidenceGraphStore(root).build()
            self.assertIn("eg_artifact_artifact_run_alpha_extract", graph.nodes)
            self.assertTrue(
                any(edge.edge_type == "referenced_by" and edge.target_node_id == "eg_artifact_artifact_run_alpha_extract" for edge in graph.edges.values())
            )

    def test_finding_and_thesis_relationships_from_exact_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _save_evidence(root)
            _save_findings(root)
            _save_theses(root, include_support=True)

            graph = EvidenceGraphStore(root).build()
            edges = {(edge.source_node_id, edge.edge_type, edge.target_node_id) for edge in graph.edges.values()}

            self.assertIn(("eg_evidence_ev_alpha", "repeats", "eg_finding_finding_repeat"), edges)
            self.assertIn(("eg_evidence_ev_alpha", "supports", "eg_thesis_thesis_alpha"), edges)
            self.assertIn(("eg_finding_finding_repeat", "contributes_to", "eg_thesis_thesis_alpha"), edges)

    def test_no_inferred_semantic_edges(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _save_evidence(root)
            _save_theses(root, include_support=False)

            graph = EvidenceGraphStore(root).build()
            self.assertFalse(
                any(edge.source_node_id == "eg_evidence_ev_alpha" and edge.target_node_id == "eg_thesis_thesis_alpha" for edge in graph.edges.values())
            )

    def test_morning_and_memory_relationships(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _save_evidence(root)
            _save_theses(root, include_support=True)
            _save_morning(root)
            _save_snapshots(root)

            graph = EvidenceGraphStore(root).build()
            edges = {(edge.source_node_id, edge.edge_type, edge.target_node_id) for edge in graph.edges.values()}

            self.assertIn(("eg_thesis_thesis_alpha", "summarized_by", "eg_morning_brief_morning_alpha"), edges)
            self.assertIn(("eg_thesis_thesis_alpha", "preserved_in", "eg_memory_snapshot_snapshot_alpha"), edges)
            self.assertIn(("eg_source_8525de3327292fa2", "preserved_in", "eg_memory_snapshot_snapshot_alpha"), edges)

    def test_orphan_detection_and_markdown_export(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _save_evidence(root)
            _save_theses(root, include_support=False)

            store = EvidenceGraphStore(root)
            graph = store.build()
            markdown = store.markdown_path.read_text(encoding="utf-8")

            self.assertTrue(store.markdown_path.exists())
            self.assertIn("## Orphan Evidence Records", markdown)
            self.assertIn("eg_evidence_ev_alpha", markdown)
            self.assertIn("## Orphan Theses", markdown)
            self.assertIn("eg_thesis_thesis_alpha", markdown)
            self.assertEqual(read_json(store.graph_path)["graph_id"], graph.graph_id)

    def test_cli_build_nodes_edges_show_export(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _save_evidence(root)

            build_output = io.StringIO()
            with redirect_stdout(build_output):
                build_exit = main(["evidence-graph", "--root", str(root), "build"])
            nodes_output = io.StringIO()
            with redirect_stdout(nodes_output):
                nodes_exit = main(["evidence-graph", "--root", str(root), "nodes"])
            edges_output = io.StringIO()
            with redirect_stdout(edges_output):
                edges_exit = main(["evidence-graph", "--root", str(root), "edges"])
            show_output = io.StringIO()
            with redirect_stdout(show_output):
                show_exit = main(["evidence-graph", "--root", str(root), "show", "ev_alpha"])
            export_output = io.StringIO()
            with redirect_stdout(export_output):
                export_exit = main(["evidence-graph", "--root", str(root), "export"])

            self.assertEqual(build_exit, 0)
            self.assertIn("nodes:", build_output.getvalue())
            self.assertEqual(nodes_exit, 0)
            self.assertIn("eg_evidence_ev_alpha", nodes_output.getvalue())
            self.assertEqual(edges_exit, 0)
            self.assertIn("--derived_from-->", edges_output.getvalue())
            self.assertEqual(show_exit, 0)
            self.assertEqual(json.loads(show_output.getvalue())["references"], ["ev_alpha"])
            self.assertEqual(export_exit, 0)
            self.assertIn("evidence_graph_export:", export_output.getvalue())

    def test_deterministic_output_structure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _save_evidence(root)
            _save_artifact(root)
            first = EvidenceGraphBuilder(root).build().to_dict()
            second = EvidenceGraphBuilder(root).build().to_dict()

            self.assertEqual(first["graph_id"], second["graph_id"])
            self.assertEqual(first["nodes"], second["nodes"])
            self.assertEqual(first["edges"], second["edges"])

    def test_no_provider_execution_or_external_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _save_evidence(root)
            with patch("constellation.providers.EchoProvider.generate") as generate:
                EvidenceGraphStore(root).build()

            generate.assert_not_called()


def _save_evidence(root: Path) -> None:
    EvidenceStore(root).save(
        EvidenceItem(
            evidence_id="ev_alpha",
            workflow_run_id="run_alpha",
            claim="Evidence alpha",
            supporting_quote="Evidence alpha quote.",
            source_identifier="source-alpha.md",
            source_location="line 1",
            confidence="source_provided",
            provenance={"test": True},
            created_at=NOW,
            updated_at=NOW,
        )
    )


def _save_artifact(root: Path) -> None:
    write_json(
        root / "logs" / "runs" / "run_alpha" / "artifacts" / "artifact_run_alpha_extract.json",
        {
            "artifact_id": "artifact_run_alpha_extract",
            "workflow_run_id": "run_alpha",
            "workflow_id": "research",
            "artifact_type": "evidence_table",
            "title": "Evidence Table",
            "evidence_used": [{"type": "evidence", "id": "ev_alpha"}],
        },
    )


def _save_findings(root: Path) -> None:
    analysis = CrossDocumentAnalysis(
        analysis_id="analysis_alpha",
        graph_version="graph_alpha",
        findings=[
            CrossDocumentFinding(
                finding_id="finding_repeat",
                finding_type="repeated_theme",
                title="Repeated theme",
                summary="Theme repeats across explicit nodes.",
                node_ids=["node_alpha"],
                evidence_ids=["ev_alpha"],
                source_ids=["source-alpha.md"],
                workflow_run_ids=["run_alpha"],
                confidence="high",
                rationale="Exact repeated label.",
                metadata={},
                created_at=NOW,
            )
        ],
        created_at=NOW,
        metadata={"test": True},
    )
    CrossDocumentAnalysisStore(root).save(analysis)


def _save_theses(root: Path, *, include_support: bool) -> None:
    ThesisStore(root).save(
        [
            Thesis(
                thesis_id="thesis_alpha",
                title="Strategic theme: alpha",
                summary="Alpha thesis.",
                thesis_type="strategic_theme",
                status="proposed",
                confidence="high",
                supporting_finding_ids=["finding_repeat"] if include_support else [],
                supporting_evidence_ids=["ev_alpha"] if include_support else [],
                supporting_node_ids=[],
                source_ids=["source-alpha.md"],
                workflow_run_ids=["run_alpha"],
                counterpoint_finding_ids=[],
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


def _save_morning(root: Path) -> None:
    write_json(
        root / "outputs" / "morning" / "morning-brief.json",
        {
            "brief_id": "morning_alpha",
            "created_at": NOW,
            "intake_summary": {},
            "google_drive_sync_summary": {},
            "new_documents_detected": [{"name": "source-alpha.md", "source": "manual", "status": "imported", "path": "source-alpha.md"}],
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


def _save_snapshots(root: Path) -> None:
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
                    "top_finding_ids": ["finding_repeat"],
                    "source_document_references": ["source-alpha.md"],
                    "artifact_references": [],
                    "limitations": [],
                    "provenance_references": {},
                }
            ]
        },
    )


if __name__ == "__main__":
    unittest.main()
