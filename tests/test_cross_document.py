from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from constellation.cli import main
from constellation.cross_document import (
    CrossDocumentAnalysis,
    CrossDocumentAnalysisStore,
    CrossDocumentAnalyzer,
    CrossDocumentError,
    CrossDocumentFinding,
)
from constellation.knowledge_graph import GraphNode, KnowledgeGraph, KnowledgeGraphBuilder, KnowledgeGraphStore
from constellation.research import ResearchOrganization


ROOT = Path(__file__).resolve().parents[1]


class CrossDocumentReasoningTests(unittest.TestCase):
    def test_cross_document_finding_creation(self) -> None:
        finding = _finding("finding_test", "repeated_concept")

        self.assertEqual(finding.finding_type, "repeated_concept")
        self.assertEqual(finding.to_dict()["finding_id"], "finding_test")

    def test_cross_document_analysis_creation(self) -> None:
        analysis = CrossDocumentAnalysis(
            analysis_id="analysis_test",
            graph_version="graph_test",
            findings=[_finding("finding_test", "repeated_theme")],
            created_at="2026-07-05T09:00:00-07:00",
            metadata={},
        )

        self.assertEqual(analysis.to_dict()["analysis_id"], "analysis_test")
        self.assertEqual(len(analysis.findings), 1)

    def test_repeated_concept_detection(self) -> None:
        analysis = CrossDocumentAnalyzer().analyze(_manual_graph("concept", "Shared"))

        self.assertTrue(any(finding.finding_type == "repeated_concept" for finding in analysis.findings))

    def test_repeated_theme_detection(self) -> None:
        analysis = CrossDocumentAnalyzer().analyze(_manual_graph("theme", "Shared Theme"))

        self.assertTrue(any(finding.finding_type == "repeated_theme" for finding in analysis.findings))

    def test_repeated_risk_detection(self) -> None:
        analysis = CrossDocumentAnalyzer().analyze(_manual_graph("risk", "Shared Risk"))

        self.assertTrue(any(finding.finding_type == "repeated_risk" for finding in analysis.findings))

    def test_repeated_recommendation_detection(self) -> None:
        analysis = CrossDocumentAnalyzer().analyze(_manual_graph("recommendation", "Shared Recommendation"))

        self.assertTrue(any(finding.finding_type == "repeated_recommendation" for finding in analysis.findings))

    def test_source_clustering(self) -> None:
        analysis = CrossDocumentAnalyzer().analyze(_manual_graph("concept", "Cluster Label"))

        self.assertTrue(any(finding.finding_type == "source_cluster" for finding in analysis.findings))

    def test_explicit_contradiction_marker_detection(self) -> None:
        graph = KnowledgeGraph()
        graph.add_node(
            _node(
                "node_risk_contradiction",
                "risk",
                "earlier claim",
                source_ids=["source.md"],
                evidence_ids=["ev_1"],
                metadata={"explicit_contradiction_marker": True, "contradiction_marker": "Contradiction"},
            )
        )

        analysis = CrossDocumentAnalyzer().analyze(graph)

        self.assertTrue(any(finding.finding_type == "possible_contradiction" for finding in analysis.findings))

    def test_no_inferred_contradiction_without_marker(self) -> None:
        graph = KnowledgeGraph()
        graph.add_node(_node("node_risk_plain", "risk", "opposing semantic idea", source_ids=["source.md"], evidence_ids=["ev_1"]))

        analysis = CrossDocumentAnalyzer().analyze(graph)

        self.assertFalse(any(finding.finding_type == "possible_contradiction" for finding in analysis.findings))

    def test_missing_evidence_detection(self) -> None:
        graph = KnowledgeGraph()
        graph.add_node(_node("node_concept_missing", "concept", "Unsupported Concept", source_ids=["source.md"], evidence_ids=[]))

        analysis = CrossDocumentAnalyzer().analyze(graph)

        self.assertTrue(any(finding.finding_type == "missing_evidence" for finding in analysis.findings))

    def test_confidence_signal_assignment(self) -> None:
        analysis = CrossDocumentAnalyzer().analyze(_manual_graph("concept", "Confidence Label"))
        signal = next(finding for finding in analysis.findings if finding.finding_type == "confidence_signal")

        self.assertEqual(signal.confidence, "medium")

    def test_graph_analyze_and_findings_cli(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            _build_two_research_runs(temp_root)

            analyze_output = io.StringIO()
            with redirect_stdout(analyze_output):
                analyze_exit = main(["graph", "--root", str(temp_root), "analyze"])
            findings_output = io.StringIO()
            with redirect_stdout(findings_output):
                findings_exit = main(["graph", "--root", str(temp_root), "findings"])
            finding_id = CrossDocumentAnalysisStore(temp_root).list_findings()[0].finding_id
            show_output = io.StringIO()
            with redirect_stdout(show_output):
                show_exit = main(["graph", "--root", str(temp_root), "findings", "show", finding_id])
            export_output = io.StringIO()
            with redirect_stdout(export_output):
                export_exit = main(["graph", "--root", str(temp_root), "findings", "export"])

            self.assertEqual(analyze_exit, 0)
            self.assertIn("findings:", analyze_output.getvalue())
            self.assertEqual(findings_exit, 0)
            self.assertIn("finding_", findings_output.getvalue())
            self.assertEqual(show_exit, 0)
            self.assertEqual(json.loads(show_output.getvalue())["finding_id"], finding_id)
            self.assertEqual(export_exit, 0)
            self.assertTrue((temp_root / "outputs" / "analysis" / "cross-document-analysis.md").exists())

    def test_no_graph_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["graph", "--root", str(temp_root), "analyze"])

            self.assertEqual(exit_code, 1)
            self.assertIn("No knowledge graph found", output.getvalue())

    def test_overwrite_protection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            _build_two_research_runs(temp_root)
            store = CrossDocumentAnalysisStore(temp_root)

            store.analyze_graph()
            with self.assertRaises(CrossDocumentError):
                store.analyze_graph()
            analysis = store.analyze_graph(overwrite=True)

            self.assertTrue(analysis.findings)

    def test_deterministic_repeatability(self) -> None:
        graph = _manual_graph("concept", "Repeatable")

        first = CrossDocumentAnalyzer().analyze(graph)
        second = CrossDocumentAnalyzer().analyze(graph)

        self.assertEqual([finding.finding_id for finding in first.findings], [finding.finding_id for finding in second.findings])


def _finding(finding_id: str, finding_type: str) -> CrossDocumentFinding:
    return CrossDocumentFinding(
        finding_id=finding_id,
        finding_type=finding_type,
        title="Finding",
        summary="Summary",
        node_ids=["node_1"],
        evidence_ids=["ev_1"],
        source_ids=["source.md"],
        workflow_run_ids=["run_1"],
        confidence="medium",
        rationale="test",
        metadata={},
        created_at="2026-07-05T09:00:00-07:00",
    )


def _manual_graph(node_type: str, label: str) -> KnowledgeGraph:
    graph = KnowledgeGraph()
    graph.add_node(_node(f"node_{node_type}_a", node_type, label, source_ids=["source-a.md"], evidence_ids=["ev_a"], workflows=["run_a"]))
    graph.add_node(_node(f"node_{node_type}_b", node_type, label, source_ids=["source-b.md"], evidence_ids=["ev_b"], workflows=["run_b"]))
    return graph


def _node(
    node_id: str,
    node_type: str,
    label: str,
    *,
    source_ids: list[str],
    evidence_ids: list[str],
    workflows: list[str] | None = None,
    metadata: dict[str, object] | None = None,
) -> GraphNode:
    return GraphNode(
        node_id=node_id,
        node_type=node_type,
        label=label,
        description=label,
        source_ids=source_ids,
        evidence_ids=evidence_ids,
        artifact_ids=[],
        workflow_run_ids=workflows or ["run_test"],
        confidence="deterministic",
        metadata=metadata or {},
        created_at="2026-07-05T09:00:00-07:00",
        updated_at="2026-07-05T09:00:00-07:00",
    )


def _copy_runtime_tree(temp_root: Path) -> Path:
    for name in ["agents", "workflows", "config", "memory", "logs", "approvals", "crew", "research_inputs", "pkos_inputs"]:
        shutil.copytree(ROOT / name, temp_root / name)
    for path in (temp_root / "approvals" / "pending").glob("*.json"):
        path.unlink()
    for path in (temp_root / "approvals" / "accepted").glob("*.json"):
        path.unlink()
    for path in (temp_root / "logs" / "runs").glob("run_*"):
        shutil.rmtree(path)
    for path in (temp_root / "memory" / "runs").glob("run_*-working.json"):
        path.unlink()
    for path in (temp_root / "memory" / "evidence").glob("ev_*.json"):
        path.unlink()
    for path in [temp_root / "memory" / "evidence" / "index.json", temp_root / "memory" / "graph" / "graph.json"]:
        if path.exists():
            path.unlink()
    analysis_dir = temp_root / "outputs" / "analysis"
    if analysis_dir.exists():
        shutil.rmtree(analysis_dir)
    return temp_root


def _build_two_research_runs(temp_root: Path) -> None:
    first = ResearchOrganization(temp_root).run(_write_research_input(temp_root, "first.md", "Concept: Shared Concept\nTheme: Shared Theme\nRisk: Shared Risk"))
    second = ResearchOrganization(temp_root).run(_write_research_input(temp_root, "second.md", "Concept: Shared Concept\nTheme: Shared Theme\nRecommendation: Shared Recommendation\nContradiction: Shared Risk"))
    builder = KnowledgeGraphBuilder(temp_root)
    builder.build_run(first.workflow_run_id)
    builder.build_run(second.workflow_run_id)


def _write_research_input(root: Path, name: str, content: str) -> Path:
    path = root / "research_inputs" / name
    path.write_text(f"# Cross Document\n\n{content}", encoding="utf-8")
    return path


if __name__ == "__main__":
    unittest.main()
