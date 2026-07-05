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
from constellation.intelligence import IntelligenceBrief, IntelligenceEngine, IntelligenceError, IntelligenceStore
from constellation.knowledge_graph import GraphNode, KnowledgeGraph, KnowledgeGraphStore
from constellation.thesis import Thesis, ThesisStore


class IntelligencePlatformTests(unittest.TestCase):
    def test_intelligence_brief_creation(self) -> None:
        brief = _brief("brief_test")

        self.assertEqual(brief.status, "proposed")
        self.assertEqual(brief.to_dict()["brief_id"], "brief_test")

    def test_intelligence_generation_from_theses(self) -> None:
        brief = IntelligenceEngine().generate(
            theses=[
                _thesis("thesis_theme", "strategic_theme", confidence="high"),
                _thesis("thesis_risk", "emerging_risk", confidence="medium"),
            ],
            analysis_id="analysis_test",
            graph_node_ids=["node_1"],
            graph_edge_count=0,
            evidence_records=[],
        )

        self.assertEqual(len(brief.strategic_themes), 1)
        self.assertEqual(len(brief.emerging_risks), 1)

    def test_missing_thesis_output_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_analysis(root)
            _write_graph(root)

            with self.assertRaisesRegex(IntelligenceError, "Generate theses"):
                IntelligenceStore(root).generate()

    def test_missing_analysis_output_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_graph(root)
            ThesisStore(root).save([_thesis("thesis_theme", "strategic_theme")])

            with self.assertRaisesRegex(IntelligenceError, "Run graph analyze"):
                IntelligenceStore(root).generate()

    def test_confidence_assessment(self) -> None:
        brief = IntelligenceEngine().generate(
            theses=[
                _thesis("thesis_high", "strategic_theme", confidence="high"),
                _thesis("thesis_medium", "emerging_risk", confidence="medium"),
                _thesis("thesis_low", "evidence_gap", confidence="low"),
            ],
            analysis_id="analysis_test",
            graph_node_ids=[],
            graph_edge_count=0,
            evidence_records=[],
        )

        self.assertEqual(brief.confidence_assessment["high_count"], 1)
        self.assertEqual(brief.confidence_assessment["medium_count"], 1)
        self.assertEqual(brief.confidence_assessment["low_count"], 1)
        self.assertEqual(brief.confidence_assessment["overall_label"], "medium")

    def test_markdown_export(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = IntelligenceStore(root)
            store.save(_brief("brief_test"))

            output_path = store.export()

            self.assertTrue(output_path.exists())
            self.assertIn("Executive Summary", output_path.read_text(encoding="utf-8"))

    def test_overwrite_protection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_upstream(root)
            store = IntelligenceStore(root)

            store.generate()
            with self.assertRaises(IntelligenceError):
                store.generate()
            regenerated = store.generate(overwrite=True)

            self.assertEqual(regenerated.status, "proposed")

    def test_cli_generate_show_export(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_upstream(root)

            generate_output = io.StringIO()
            with redirect_stdout(generate_output):
                generate_exit = main(["intelligence", "--root", str(root), "generate"])
            show_output = io.StringIO()
            with redirect_stdout(show_output):
                show_exit = main(["intelligence", "--root", str(root), "show"])
            export_output = io.StringIO()
            with redirect_stdout(export_output):
                export_exit = main(["intelligence", "--root", str(root), "export"])

            self.assertEqual(generate_exit, 0)
            self.assertIn("status: proposed", generate_output.getvalue())
            self.assertEqual(show_exit, 0)
            self.assertEqual(json.loads(show_output.getvalue())["status"], "proposed")
            self.assertEqual(export_exit, 0)
            self.assertTrue((root / "outputs" / "intelligence" / "institutional-intelligence.md").exists())

    def test_deterministic_repeatability(self) -> None:
        kwargs = {
            "theses": [_thesis("thesis_theme", "strategic_theme", confidence="high")],
            "analysis_id": "analysis_test",
            "graph_node_ids": ["node_1"],
            "graph_edge_count": 0,
            "evidence_records": [],
        }

        first = IntelligenceEngine().generate(**kwargs)
        second = IntelligenceEngine().generate(**kwargs)

        self.assertEqual(first.brief_id, second.brief_id)

    def test_generation_does_not_call_providers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_upstream(root)

            with patch("constellation.providers.EchoProvider.generate", side_effect=AssertionError("provider called")):
                brief = IntelligenceStore(root).generate()

            self.assertEqual(brief.status, "proposed")

    def test_status_defaults_to_proposed(self) -> None:
        brief = IntelligenceEngine().generate(
            theses=[_thesis("thesis_theme", "strategic_theme")],
            analysis_id="analysis_test",
            graph_node_ids=[],
            graph_edge_count=0,
            evidence_records=[],
        )

        self.assertEqual(brief.status, "proposed")

    def test_ids_are_preserved(self) -> None:
        thesis = _thesis("thesis_theme", "strategic_theme", evidence_ids=["ev_1"], source_ids=["source.md"])
        brief = IntelligenceEngine().generate(
            theses=[thesis],
            analysis_id="analysis_test",
            graph_node_ids=["node_1"],
            graph_edge_count=0,
            evidence_records=[{"evidence_id": "ev_1", "source_identifier": "source.md"}],
        )

        self.assertEqual(brief.thesis_ids, ["thesis_theme"])
        self.assertEqual(brief.finding_ids, ["finding_thesis_theme"])
        self.assertEqual(brief.evidence_ids, ["ev_1"])
        self.assertEqual(brief.node_ids, ["node_1"])
        self.assertEqual(brief.source_ids, ["source.md"])


def _write_upstream(root: Path) -> None:
    _write_analysis(root)
    _write_graph(root)
    _write_evidence(root)
    ThesisStore(root).save(
        [
            _thesis("thesis_theme", "strategic_theme", confidence="high"),
            _thesis("thesis_risk", "emerging_risk", confidence="medium"),
            _thesis("thesis_recommendation", "repeated_recommendation", confidence="medium"),
            _thesis("thesis_consensus", "source_consensus", confidence="high"),
            _thesis("thesis_contradiction", "contradiction_watch", confidence="medium"),
            _thesis("thesis_gap", "evidence_gap", confidence="low"),
        ]
    )


def _write_analysis(root: Path) -> None:
    CrossDocumentAnalysisStore(root).save(
        CrossDocumentAnalysis(
            analysis_id="analysis_test",
            graph_version="graph_test",
            findings=[
                CrossDocumentFinding(
                    finding_id="finding_thesis_theme",
                    finding_type="repeated_theme",
                    title="Finding",
                    summary="Summary",
                    node_ids=["node_1"],
                    evidence_ids=["ev_1"],
                    source_ids=["source.md"],
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


def _write_graph(root: Path) -> None:
    graph = KnowledgeGraph()
    graph.add_node(
        GraphNode(
            node_id="node_1",
            node_type="theme",
            label="Theme",
            description="Theme",
            source_ids=["source.md"],
            evidence_ids=["ev_1"],
            artifact_ids=[],
            workflow_run_ids=["run_1"],
            confidence="deterministic",
            metadata={},
            created_at="2026-07-05T09:00:00-07:00",
            updated_at="2026-07-05T09:00:00-07:00",
        )
    )
    KnowledgeGraphStore(root).save(graph)


def _write_evidence(root: Path) -> None:
    EvidenceStore(root).save(
        EvidenceItem(
            evidence_id="ev_1",
            workflow_run_id="run_1",
            claim="Claim",
            supporting_quote="Theme: Theme",
            source_identifier="source.md",
            source_location="line 1",
            confidence="source_provided",
            provenance={},
            created_at="2026-07-05T09:00:00-07:00",
            updated_at="2026-07-05T09:00:00-07:00",
        )
    )


def _brief(brief_id: str) -> IntelligenceBrief:
    return IntelligenceBrief(
        brief_id=brief_id,
        title="Institutional Intelligence Brief",
        summary="Summary",
        status="proposed",
        generated_from={},
        thesis_ids=["thesis_1"],
        finding_ids=["finding_1"],
        evidence_ids=["ev_1"],
        node_ids=["node_1"],
        source_ids=["source.md"],
        workflow_run_ids=["run_1"],
        strategic_themes=[],
        emerging_risks=[],
        repeated_recommendations=[],
        consensus_signals=[],
        contradiction_watches=[],
        evidence_gaps=[],
        confidence_assessment={"high_count": 0, "medium_count": 1, "low_count": 0, "overall_label": "medium"},
        executive_recommendations=["review"],
        open_questions=["question"],
        limitations=["limitation"],
        approval_note="Human review required.",
        metadata={},
        created_at="2026-07-05T09:00:00-07:00",
        updated_at="2026-07-05T09:00:00-07:00",
    )


def _thesis(
    thesis_id: str,
    thesis_type: str,
    *,
    confidence: str = "high",
    evidence_ids: list[str] | None = None,
    source_ids: list[str] | None = None,
) -> Thesis:
    return Thesis(
        thesis_id=thesis_id,
        title=f"Thesis {thesis_id}",
        summary="Summary",
        thesis_type=thesis_type,
        status="proposed",
        confidence=confidence,
        supporting_finding_ids=[f"finding_{thesis_id}"],
        supporting_evidence_ids=evidence_ids if evidence_ids is not None else ["ev_1"],
        supporting_node_ids=["node_1"],
        source_ids=source_ids if source_ids is not None else ["source.md"],
        workflow_run_ids=["run_1"],
        counterpoint_finding_ids=[],
        risks=[],
        assumptions=["test"],
        recommendations=[f"Review {thesis_id}."],
        open_questions=[f"Open question {thesis_id}?"],
        rationale="test",
        metadata={},
        created_at="2026-07-05T09:00:00-07:00",
        updated_at="2026-07-05T09:00:00-07:00",
    )


if __name__ == "__main__":
    unittest.main()
