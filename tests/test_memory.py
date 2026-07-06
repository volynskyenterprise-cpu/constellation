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
from constellation.intelligence import IntelligenceBrief, IntelligenceStore
from constellation.knowledge_graph import GraphNode, KnowledgeGraph, KnowledgeGraphStore
from constellation.memory import InstitutionalMemoryError, InstitutionalMemoryStore
from constellation.morning import MorningExecutiveStore
from constellation.thesis import Thesis, ThesisStore


class InstitutionalMemoryTests(unittest.TestCase):
    def test_empty_state_snapshot_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            snapshot = InstitutionalMemoryStore(Path(temp_dir)).create_snapshot("empty")

            self.assertEqual(snapshot.evidence_count, 0)
            self.assertEqual(snapshot.graph_node_count, 0)
            self.assertIn("No evidence records found.", snapshot.limitations)

    def test_snapshot_creation_from_existing_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_state(root, "base")

            snapshot = InstitutionalMemoryStore(root).create_snapshot("baseline")

            self.assertEqual(snapshot.label, "baseline")
            self.assertEqual(snapshot.evidence_count, 1)
            self.assertEqual(snapshot.graph_node_count, 1)
            self.assertEqual(snapshot.findings_count, 1)
            self.assertEqual(snapshot.thesis_count, 1)
            self.assertEqual(snapshot.intelligence_brief_id, "brief_base")
            self.assertTrue(snapshot.morning_brief_id)

    def test_snapshot_list(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = InstitutionalMemoryStore(Path(temp_dir))

            first = store.create_snapshot("one")
            second = store.create_snapshot("two")
            snapshots = store.list_snapshots()

            self.assertEqual([item.snapshot_id for item in snapshots], [first.snapshot_id, second.snapshot_id])

    def test_snapshot_show(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = InstitutionalMemoryStore(Path(temp_dir))
            snapshot = store.create_snapshot("show")

            shown = store.show_snapshot(snapshot.snapshot_id)

            self.assertEqual(shown.snapshot_id, snapshot.snapshot_id)

    def test_default_diff_between_latest_two_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = InstitutionalMemoryStore(root)
            _write_state(root, "one")
            first = store.create_snapshot("one")
            _write_state(root, "two", extra_evidence=True)
            second = store.create_snapshot("two")

            delta = store.diff()

            self.assertEqual(delta.prior_snapshot_id, first.snapshot_id)
            self.assertEqual(delta.current_snapshot_id, second.snapshot_id)
            self.assertEqual(delta.evidence_count_change, 2)

    def test_explicit_diff_between_snapshot_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = InstitutionalMemoryStore(root)
            _write_state(root, "one")
            first = store.create_snapshot("one")
            _write_state(root, "two", extra_thesis=True)
            second = store.create_snapshot("two")

            delta = store.diff(first.snapshot_id, second.snapshot_id)

            self.assertEqual(delta.thesis_count_change, 1)
            self.assertIn("thesis_two_extra", delta.new_thesis_ids)

    def test_diff_requires_two_snapshots(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = InstitutionalMemoryStore(Path(temp_dir))
            store.create_snapshot("only")

            with self.assertRaisesRegex(InstitutionalMemoryError, "At least two snapshots"):
                store.diff()

    def test_markdown_export(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = InstitutionalMemoryStore(Path(temp_dir))
            store.create_snapshot("export")

            output_path = store.export()

            self.assertTrue(output_path.exists())
            self.assertIn("Institutional Memory", output_path.read_text(encoding="utf-8"))

    def test_cli_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_state(root, "one")
            snapshot_output = io.StringIO()
            with redirect_stdout(snapshot_output):
                snapshot_exit = main(["memory", "--root", str(root), "snapshot", "--label", "baseline"])
            _write_state(root, "two", extra_evidence=True)
            with redirect_stdout(io.StringIO()):
                second_exit = main(["memory", "--root", str(root), "snapshot", "--label", "second"])
            list_output = io.StringIO()
            with redirect_stdout(list_output):
                list_exit = main(["memory", "--root", str(root), "list"])
            snapshot_id = InstitutionalMemoryStore(root).list_snapshots()[0].snapshot_id
            show_output = io.StringIO()
            with redirect_stdout(show_output):
                show_exit = main(["memory", "--root", str(root), "show", snapshot_id])
            diff_output = io.StringIO()
            with redirect_stdout(diff_output):
                diff_exit = main(["memory", "--root", str(root), "diff"])
            export_output = io.StringIO()
            with redirect_stdout(export_output):
                export_exit = main(["memory", "--root", str(root), "export"])

            self.assertEqual(snapshot_exit, 0)
            self.assertEqual(second_exit, 0)
            self.assertIn("snapshot_id:", snapshot_output.getvalue())
            self.assertEqual(list_exit, 0)
            self.assertIn("snapshot_", list_output.getvalue())
            self.assertEqual(show_exit, 0)
            self.assertEqual(json.loads(show_output.getvalue())["snapshot_id"], snapshot_id)
            self.assertEqual(diff_exit, 0)
            self.assertIn("evidence_count_change", diff_output.getvalue())
            self.assertEqual(export_exit, 0)
            self.assertIn("institutional_memory:", export_output.getvalue())

    def test_deterministic_output_structure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_state(root, "base")
            first = InstitutionalMemoryStore(root).create_snapshot("same")
            second = InstitutionalMemoryStore(root).create_snapshot("same")

            self.assertEqual(first.snapshot_id, second.snapshot_id)
            self.assertEqual(set(first.to_dict()), set(second.to_dict()))

    def test_no_provider_execution_or_external_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_state(root, "base")

            with patch("constellation.providers.EchoProvider.generate", side_effect=AssertionError("provider called")):
                snapshot = InstitutionalMemoryStore(root).create_snapshot("safe")

            self.assertEqual(snapshot.evidence_count, 1)


def _write_state(root: Path, suffix: str, *, extra_evidence: bool = False, extra_thesis: bool = False) -> None:
    evidence_store = EvidenceStore(root)
    evidence_store.save(_evidence(f"ev_{suffix}", suffix))
    if extra_evidence:
        evidence_store.save(_evidence(f"ev_{suffix}_extra", suffix))
    graph = KnowledgeGraph()
    graph.add_node(_node(f"node_{suffix}", suffix))
    KnowledgeGraphStore(root).save(graph)
    CrossDocumentAnalysisStore(root).save(
        CrossDocumentAnalysis(
            analysis_id=f"analysis_{suffix}",
            graph_version=f"graph_{suffix}",
            findings=[
                CrossDocumentFinding(
                    finding_id=f"finding_{suffix}",
                    finding_type="repeated_theme",
                    title=f"Finding {suffix}",
                    summary="summary",
                    node_ids=[f"node_{suffix}"],
                    evidence_ids=[f"ev_{suffix}"],
                    source_ids=[f"source_{suffix}.md"],
                    workflow_run_ids=[f"run_{suffix}"],
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
    theses = [_thesis(f"thesis_{suffix}", suffix)]
    if extra_thesis:
        theses.append(_thesis(f"thesis_{suffix}_extra", suffix))
    ThesisStore(root).save(theses)
    IntelligenceStore(root).save(_intelligence(f"brief_{suffix}", suffix, [item.thesis_id for item in theses]))
    MorningExecutiveStore(root).generate(overwrite=True)


def _evidence(evidence_id: str, suffix: str) -> EvidenceItem:
    return EvidenceItem(
        evidence_id=evidence_id,
        workflow_run_id=f"run_{suffix}",
        claim=f"Claim {suffix}",
        supporting_quote=f"Theme: {suffix}",
        source_identifier=f"source_{suffix}.md",
        source_location="line 1",
        confidence="source_provided",
        provenance={},
        created_at="2026-07-05T09:00:00-07:00",
        updated_at="2026-07-05T09:00:00-07:00",
    )


def _node(node_id: str, suffix: str) -> GraphNode:
    return GraphNode(
        node_id=node_id,
        node_type="theme",
        label=f"Theme {suffix}",
        description="desc",
        source_ids=[f"source_{suffix}.md"],
        evidence_ids=[f"ev_{suffix}"],
        artifact_ids=[],
        workflow_run_ids=[f"run_{suffix}"],
        confidence="deterministic",
        metadata={},
        created_at="2026-07-05T09:00:00-07:00",
        updated_at="2026-07-05T09:00:00-07:00",
    )


def _thesis(thesis_id: str, suffix: str) -> Thesis:
    return Thesis(
        thesis_id=thesis_id,
        title=f"Thesis {suffix}",
        summary="summary",
        thesis_type="strategic_theme",
        status="proposed",
        confidence="high",
        supporting_finding_ids=[f"finding_{suffix}"],
        supporting_evidence_ids=[f"ev_{suffix}"],
        supporting_node_ids=[f"node_{suffix}"],
        source_ids=[f"source_{suffix}.md"],
        workflow_run_ids=[f"run_{suffix}"],
        counterpoint_finding_ids=[],
        risks=[],
        assumptions=[],
        recommendations=[],
        open_questions=[],
        rationale="test",
        metadata={},
        created_at="2026-07-05T09:00:00-07:00",
        updated_at="2026-07-05T09:00:00-07:00",
    )


def _intelligence(brief_id: str, suffix: str, thesis_ids: list[str]) -> IntelligenceBrief:
    return IntelligenceBrief(
        brief_id=brief_id,
        title="Institutional Intelligence Brief",
        summary="summary",
        status="proposed",
        generated_from={},
        thesis_ids=thesis_ids,
        finding_ids=[f"finding_{suffix}"],
        evidence_ids=[f"ev_{suffix}"],
        node_ids=[f"node_{suffix}"],
        source_ids=[f"source_{suffix}.md"],
        workflow_run_ids=[f"run_{suffix}"],
        strategic_themes=[],
        emerging_risks=[],
        repeated_recommendations=[],
        consensus_signals=[],
        contradiction_watches=[],
        evidence_gaps=[],
        confidence_assessment={"overall_label": "high"},
        executive_recommendations=[],
        open_questions=[],
        limitations=[],
        approval_note="review",
        metadata={},
        created_at="2026-07-05T09:00:00-07:00",
        updated_at="2026-07-05T09:00:00-07:00",
    )


if __name__ == "__main__":
    unittest.main()
