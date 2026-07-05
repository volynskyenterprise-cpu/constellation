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
from constellation.thesis import Thesis, ThesisEngine, ThesisError, ThesisStore


class ThesisEngineTests(unittest.TestCase):
    def test_thesis_creation(self) -> None:
        thesis = _thesis("thesis_test", "strategic_theme")

        self.assertEqual(thesis.thesis_type, "strategic_theme")
        self.assertEqual(thesis.status, "proposed")
        self.assertEqual(thesis.to_dict()["thesis_id"], "thesis_test")

    def test_thesis_store_save_load(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            store = ThesisStore(Path(temp_dir))
            thesis = _thesis("thesis_test", "emerging_risk")

            store.save([thesis])
            loaded = store.load()

            self.assertEqual(loaded[0].thesis_id, "thesis_test")
            self.assertTrue(store.markdown_path.exists())

    def test_strategic_theme_generation(self) -> None:
        theses = ThesisEngine().generate(_analysis([_finding("finding_theme", "repeated_theme", confidence="high")]))

        self.assertEqual(theses[0].thesis_type, "strategic_theme")

    def test_repeated_concept_requires_high_confidence_for_strategic_theme(self) -> None:
        theses = ThesisEngine().generate(_analysis([_finding("finding_concept", "repeated_concept", confidence="medium")]))

        self.assertEqual(theses, [])

    def test_emerging_risk_generation(self) -> None:
        theses = ThesisEngine().generate(_analysis([_finding("finding_risk", "repeated_risk", confidence="medium")]))

        self.assertEqual(theses[0].thesis_type, "emerging_risk")

    def test_repeated_recommendation_generation(self) -> None:
        theses = ThesisEngine().generate(_analysis([_finding("finding_recommendation", "repeated_recommendation")]))

        self.assertEqual(theses[0].thesis_type, "repeated_recommendation")

    def test_evidence_gap_generation(self) -> None:
        theses = ThesisEngine().generate(_analysis([_finding("finding_gap", "missing_evidence", confidence="low", evidence_ids=[])]))

        self.assertEqual(theses[0].thesis_type, "evidence_gap")

    def test_source_consensus_generation(self) -> None:
        theses = ThesisEngine().generate(_analysis([_finding("finding_cluster", "source_cluster", confidence="high")]))

        self.assertEqual(theses[0].thesis_type, "source_consensus")

    def test_contradiction_watch_generation(self) -> None:
        theses = ThesisEngine().generate(_analysis([_finding("finding_contradiction", "possible_contradiction", confidence="medium")]))

        self.assertEqual(theses[0].thesis_type, "contradiction_watch")

    def test_no_analysis_error(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            with self.assertRaises(ThesisError):
                ThesisStore(Path(temp_dir)).generate()

    def test_overwrite_protection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            CrossDocumentAnalysisStore(root).save(_analysis([_finding("finding_risk", "repeated_risk")]))
            store = ThesisStore(root)

            store.generate()
            with self.assertRaises(ThesisError):
                store.generate()
            regenerated = store.generate(overwrite=True)

            self.assertEqual(len(regenerated), 1)

    def test_deterministic_repeatability(self) -> None:
        analysis = _analysis([_finding("finding_risk", "repeated_risk")])

        first = ThesisEngine().generate(analysis)
        second = ThesisEngine().generate(analysis)

        self.assertEqual([item.thesis_id for item in first], [item.thesis_id for item in second])

    def test_thesis_cli_generate_list_show_export(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            CrossDocumentAnalysisStore(root).save(_analysis([_finding("finding_risk", "repeated_risk")]))

            generate_output = io.StringIO()
            with redirect_stdout(generate_output):
                generate_exit = main(["thesis", "--root", str(root), "generate"])
            list_output = io.StringIO()
            with redirect_stdout(list_output):
                list_exit = main(["thesis", "--root", str(root), "list"])
            thesis_id = ThesisStore(root).load()[0].thesis_id
            show_output = io.StringIO()
            with redirect_stdout(show_output):
                show_exit = main(["thesis", "--root", str(root), "show", thesis_id])
            export_output = io.StringIO()
            with redirect_stdout(export_output):
                export_exit = main(["thesis", "--root", str(root), "export"])

            self.assertEqual(generate_exit, 0)
            self.assertIn("count: 1", generate_output.getvalue())
            self.assertEqual(list_exit, 0)
            self.assertIn("thesis_", list_output.getvalue())
            self.assertEqual(show_exit, 0)
            self.assertEqual(json.loads(show_output.getvalue())["thesis_id"], thesis_id)
            self.assertEqual(export_exit, 0)
            self.assertTrue((root / "outputs" / "theses" / "theses.md").exists())

    def test_theses_reference_finding_ids_and_evidence_ids(self) -> None:
        thesis = ThesisEngine().generate(_analysis([_finding("finding_risk", "repeated_risk", evidence_ids=["ev_a", "ev_b"])]))[0]

        self.assertEqual(thesis.supporting_finding_ids, ["finding_risk"])
        self.assertEqual(thesis.supporting_evidence_ids, ["ev_a", "ev_b"])

    def test_generated_theses_default_to_proposed_status(self) -> None:
        theses = ThesisEngine().generate(
            _analysis(
                [
                    _finding("finding_risk", "repeated_risk"),
                    _finding("finding_recommendation", "repeated_recommendation"),
                ]
            )
        )

        self.assertTrue(all(thesis.status == "proposed" for thesis in theses))

    def test_generation_does_not_call_providers(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            CrossDocumentAnalysisStore(root).save(_analysis([_finding("finding_risk", "repeated_risk")]))

            with patch("constellation.providers.EchoProvider.generate", side_effect=AssertionError("provider called")):
                theses = ThesisStore(root).generate()

            self.assertEqual(len(theses), 1)


def _thesis(thesis_id: str, thesis_type: str) -> Thesis:
    return Thesis(
        thesis_id=thesis_id,
        title="Thesis",
        summary="Summary",
        thesis_type=thesis_type,
        status="proposed",
        confidence="medium",
        supporting_finding_ids=["finding_1"],
        supporting_evidence_ids=["ev_1"],
        supporting_node_ids=["node_1"],
        source_ids=["source.md"],
        workflow_run_ids=["run_1"],
        counterpoint_finding_ids=[],
        risks=[],
        assumptions=["test"],
        recommendations=["review"],
        open_questions=["question"],
        rationale="test",
        metadata={},
        created_at="2026-07-05T09:00:00-07:00",
        updated_at="2026-07-05T09:00:00-07:00",
    )


def _analysis(findings: list[CrossDocumentFinding]) -> CrossDocumentAnalysis:
    return CrossDocumentAnalysis(
        analysis_id="analysis_test",
        graph_version="graph_test",
        findings=findings,
        created_at="2026-07-05T09:00:00-07:00",
        metadata={},
    )


def _finding(
    finding_id: str,
    finding_type: str,
    *,
    confidence: str = "high",
    evidence_ids: list[str] | None = None,
) -> CrossDocumentFinding:
    return CrossDocumentFinding(
        finding_id=finding_id,
        finding_type=finding_type,
        title="Finding",
        summary="Summary",
        node_ids=["node_1"],
        evidence_ids=evidence_ids if evidence_ids is not None else ["ev_1"],
        source_ids=["source-a.md", "source-b.md", "source-c.md"],
        workflow_run_ids=["run_1", "run_2"],
        confidence=confidence,
        rationale="test rationale",
        metadata={},
        created_at="2026-07-05T09:00:00-07:00",
    )


if __name__ == "__main__":
    unittest.main()
