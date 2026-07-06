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
from constellation.google_drive import GoogleDriveFile, GoogleDriveSyncManifest, GoogleDriveConnector
from constellation.intake import IntakeItem, IntakeManifest, IntakeEngine
from constellation.intelligence import IntelligenceBrief, IntelligenceStore
from constellation.knowledge_graph import GraphEdge, GraphNode, KnowledgeGraph, KnowledgeGraphStore
from constellation.morning import MorningExecutiveEngine, MorningExecutiveStore
from constellation.thesis import Thesis, ThesisStore


class MorningExecutiveTests(unittest.TestCase):
    def test_empty_state_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            brief = MorningExecutiveEngine(Path(temp_dir)).generate()

            self.assertEqual(brief.evidence_count, 0)
            self.assertEqual(brief.graph_node_count, 0)
            self.assertIn("No intake manifest found.", brief.limitations)
            self.assertIn("Run `python -m constellation intake scan`", " ".join(brief.recommended_next_actions))

    def test_brief_generation_from_existing_manifests(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_artifacts(root)

            brief = MorningExecutiveEngine(root).generate()

            self.assertEqual(brief.intake_summary["imported"], 1)
            self.assertEqual(brief.google_drive_sync_summary["downloaded"], 1)
            self.assertEqual(brief.evidence_count, 1)
            self.assertEqual(brief.graph_node_count, 2)
            self.assertEqual(brief.graph_edge_count, 1)
            self.assertEqual(brief.top_findings[0]["finding_id"], "finding_1")
            self.assertEqual(brief.top_theses[0]["thesis_id"], "thesis_1")
            self.assertTrue(brief.intelligence_summary["present"])

    def test_markdown_export(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_artifacts(root)
            store = MorningExecutiveStore(root)

            store.generate()
            output_path = store.export()

            self.assertTrue(output_path.exists())
            self.assertIn("Morning Executive Intelligence", output_path.read_text(encoding="utf-8"))

    def test_cli_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_artifacts(root)

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["morning", "--root", str(root)])
            export_output = io.StringIO()
            with redirect_stdout(export_output):
                export_exit = main(["morning", "--root", str(root), "--export"])
            overwrite_output = io.StringIO()
            with redirect_stdout(overwrite_output):
                overwrite_exit = main(["morning", "--root", str(root), "--overwrite"])

            self.assertEqual(exit_code, 0)
            self.assertIn("brief_id:", output.getvalue())
            self.assertEqual(export_exit, 0)
            self.assertIn("morning_brief:", export_output.getvalue())
            self.assertEqual(overwrite_exit, 0)

    def test_overwrite_protection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = MorningExecutiveStore(root)

            store.generate()
            with self.assertRaises(Exception):
                store.generate()
            replacement = store.generate(overwrite=True)

            self.assertTrue(replacement.brief_id.startswith("morning_"))

    def test_no_provider_execution(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_artifacts(root)

            with patch("constellation.providers.EchoProvider.generate", side_effect=AssertionError("provider called")):
                brief = MorningExecutiveStore(root).generate()

            self.assertEqual(brief.evidence_count, 1)

    def test_deterministic_output_structure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_artifacts(root)

            first = MorningExecutiveEngine(root).generate()
            second = MorningExecutiveEngine(root).generate()

            self.assertEqual(first.brief_id, second.brief_id)
            self.assertEqual(set(first.to_dict()), set(second.to_dict()))


def _write_artifacts(root: Path) -> None:
    IntakeEngine(root).save(
        IntakeManifest(
            manifest_id="manifest_1",
            created_at="2026-07-05T09:00:00-07:00",
            updated_at="2026-07-05T09:01:00-07:00",
            counts={"imported": 1, "skipped": 0, "duplicates": 0, "errors": 0, "total": 1},
            items=[
                IntakeItem(
                    item_id="intake_1",
                    source_channel="manual",
                    original_path=str(root / "inbox" / "manual" / "incoming" / "brief.md"),
                    destination_path=str(root / "research_inputs" / "2026-07-05" / "brief.md"),
                    file_hash="hash",
                    import_timestamp="2026-07-05T09:01:00-07:00",
                    status="imported",
                )
            ],
        )
    )
    GoogleDriveConnector(root).write_manifest(
        GoogleDriveSyncManifest(
            sync_id="sync_1",
            source_folder_id="folder_1",
            downloaded_files=[
                GoogleDriveFile(
                    file_id="file_1",
                    name="drive-brief.md",
                    mime_type="text/markdown",
                    modified_time="2026-07-05T09:00:00Z",
                    size="10",
                    sha256="sha",
                    source_folder_id="folder_1",
                    destination_path=str(root / "inbox" / "google-drive" / "incoming" / "drive-brief.md"),
                    status="downloaded",
                    metadata={},
                )
            ],
            skipped_files=[],
            duplicate_files=[],
            errors=[],
            created_at="2026-07-05T09:00:00-07:00",
        )
    )
    EvidenceStore(root).save(
        EvidenceItem(
            evidence_id="ev_1",
            workflow_run_id="run_1",
            claim="Claim",
            supporting_quote="Theme: Traceability",
            source_identifier="brief.md",
            source_location="line 1",
            confidence="source_provided",
            provenance={},
            created_at="2026-07-05T09:00:00-07:00",
            updated_at="2026-07-05T09:00:00-07:00",
        )
    )
    graph = KnowledgeGraph()
    graph.add_node(_node("node_1", "theme", "Traceability"))
    graph.add_node(_node("node_2", "evidence", "Claim"))
    graph.add_edge(
        GraphEdge(
            edge_id="edge_1",
            source_node_id="node_1",
            target_node_id="node_2",
            relationship_type="derived_from",
            evidence_ids=["ev_1"],
            confidence="deterministic",
            metadata={},
            created_at="2026-07-05T09:00:00-07:00",
            updated_at="2026-07-05T09:00:00-07:00",
        )
    )
    KnowledgeGraphStore(root).save(graph)
    CrossDocumentAnalysisStore(root).save(
        CrossDocumentAnalysis(
            analysis_id="analysis_1",
            graph_version="graph_1",
            findings=[
                CrossDocumentFinding(
                    finding_id="finding_1",
                    finding_type="repeated_theme",
                    title="Repeated theme: Traceability",
                    summary="Traceability repeats.",
                    node_ids=["node_1"],
                    evidence_ids=["ev_1"],
                    source_ids=["brief.md"],
                    workflow_run_ids=["run_1"],
                    confidence="high",
                    rationale="test",
                    metadata={},
                    created_at="2026-07-05T09:00:00-07:00",
                )
            ],
            created_at="2026-07-05T09:00:00-07:00",
            metadata={},
        )
    )
    ThesisStore(root).save(
        [
            Thesis(
                thesis_id="thesis_1",
                title="Strategic theme: Traceability",
                summary="Traceability matters.",
                thesis_type="strategic_theme",
                status="proposed",
                confidence="high",
                supporting_finding_ids=["finding_1"],
                supporting_evidence_ids=["ev_1"],
                supporting_node_ids=["node_1"],
                source_ids=["brief.md"],
                workflow_run_ids=["run_1"],
                counterpoint_finding_ids=[],
                risks=[],
                assumptions=[],
                recommendations=["Review traceability."],
                open_questions=[],
                rationale="test",
                metadata={},
                created_at="2026-07-05T09:00:00-07:00",
                updated_at="2026-07-05T09:00:00-07:00",
            )
        ]
    )
    IntelligenceStore(root).save(
        IntelligenceBrief(
            brief_id="brief_1",
            title="Institutional Intelligence Brief",
            summary="Executive summary.",
            status="proposed",
            generated_from={},
            thesis_ids=["thesis_1"],
            finding_ids=["finding_1"],
            evidence_ids=["ev_1"],
            node_ids=["node_1"],
            source_ids=["brief.md"],
            workflow_run_ids=["run_1"],
            strategic_themes=[],
            emerging_risks=[],
            repeated_recommendations=[],
            consensus_signals=[],
            contradiction_watches=[],
            evidence_gaps=[],
            confidence_assessment={"overall_label": "high"},
            executive_recommendations=["Review."],
            open_questions=[],
            limitations=["Human review required."],
            approval_note="Review required.",
            metadata={},
            created_at="2026-07-05T09:00:00-07:00",
            updated_at="2026-07-05T09:00:00-07:00",
        )
    )


def _node(node_id: str, node_type: str, label: str) -> GraphNode:
    return GraphNode(
        node_id=node_id,
        node_type=node_type,
        label=label,
        description=label,
        source_ids=["brief.md"],
        evidence_ids=["ev_1"],
        artifact_ids=[],
        workflow_run_ids=["run_1"],
        confidence="deterministic",
        metadata={},
        created_at="2026-07-05T09:00:00-07:00",
        updated_at="2026-07-05T09:00:00-07:00",
    )


if __name__ == "__main__":
    unittest.main()
