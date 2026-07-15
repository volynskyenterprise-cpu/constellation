from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from constellation.cli import main
from constellation.dashboard import ExecutiveDashboardStore
from constellation.io import read_json, write_json
from constellation.thesis_accuracy import ThesisAccuracyStore
from constellation.workflow import WorkflowStore


class ThesisAccuracyTests(unittest.TestCase):
    def test_empty_state_build(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)

            report = ThesisAccuracyStore(root).build()

            self.assertEqual(report.snapshot.summary.thesis_count, 0)
            self.assertEqual(report.snapshot.summary.average_accuracy_score, 0)
            self.assertTrue((root / "outputs" / "performance" / "thesis-accuracy.md").exists())

    def test_deterministic_scoring_for_supported_confirmed_thesis(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_theses(root, [_thesis("thesis_ai", support=["ev_1", "ev_2"], sources=["source_a", "source_b"])])
            _write_performance(root, [_decision("decision_ai", "user_confirmed")])

            score = ThesisAccuracyStore(root).build().snapshot.scores[0]

            self.assertEqual(score.thesis_id, "thesis_ai")
            self.assertGreater(score.accuracy_score, 60)
            self.assertEqual(score.review_priority, "low")

    def test_contradiction_degrades_score_and_sets_high_priority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_theses(root, [_thesis("thesis_ai", support=["ev_1"], conflicts=["ev_conflict"])])
            _write_performance(root, [_decision("decision_ai", "user_contradicted")])

            score = ThesisAccuracyStore(root).build().snapshot.scores[0]

            self.assertLess(score.accuracy_score, 45)
            self.assertEqual(score.review_priority, "high")
            self.assertEqual(score.contradicted_count, 2)

    def test_delta_tracks_score_improvement_and_degradation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = ThesisAccuracyStore(root)
            _write_theses(root, [_thesis("thesis_ai", support=["ev_1"], conflicts=["ev_conflict"])])
            _write_performance(root, [_decision("decision_ai", "user_contradicted")])
            first = store.build()

            _write_theses(root, [_thesis("thesis_ai", support=["ev_1", "ev_2", "ev_3"], sources=["source_a", "source_b"])])
            _write_performance(root, [_decision("decision_ai", "user_confirmed")])
            second = store.build()

            self.assertNotEqual(first.snapshot.snapshot_id, second.snapshot.snapshot_id)
            self.assertGreater(second.delta.average_accuracy_score_change, 0)
            self.assertEqual(len(store.history()), 2)

    def test_history_avoids_duplicate_identical_snapshot(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            store = ThesisAccuracyStore(root)
            _write_theses(root, [_thesis("thesis_ai", support=["ev_1"])])
            _write_performance(root, [_decision("decision_ai", "pending")])

            first = store.build()
            second = store.build()

            self.assertEqual(first.snapshot.snapshot_id, second.snapshot.snapshot_id)
            self.assertEqual(len(store.history()), 1)

    def test_markdown_outputs_do_not_include_advice_language(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_theses(root, [_thesis("thesis_ai", support=["ev_1"])])
            _write_performance(root, [_decision("decision_ai", "user_confirmed")])

            ThesisAccuracyStore(root).build()
            text = (root / "outputs" / "performance" / "thesis-accuracy.md").read_text(encoding="utf-8").lower()

            for forbidden in ["buy ", "sell ", "hold ", "price target", "expected return", "trade recommendation"]:
                self.assertNotIn(forbidden, text)

    def test_dashboard_integration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_theses(root, [_thesis("thesis_ai", support=["ev_1", "ev_2"])])
            _write_performance(root, [_decision("decision_ai", "user_confirmed")])
            ThesisAccuracyStore(root).build()

            dashboard = ExecutiveDashboardStore(root).generate(overwrite=True)

            self.assertTrue(dashboard.thesis_accuracy_summary["thesis_accuracy_available"])
            self.assertIn("average_accuracy_score", dashboard.thesis_accuracy_summary)

    def test_workflow_integration_adds_twentieth_morning_step(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            _write_theses(root, [_thesis("thesis_ai", support=["ev_1"])])
            _write_performance(root, [_decision("decision_ai", "user_confirmed")])

            run = WorkflowStore(root).run("Morning")
            commands = [step["command"] for step in run.executed_steps]

            self.assertEqual(len(commands), 20)
            self.assertEqual(commands[-1], "performance thesis")
            self.assertIn("Thesis Accuracy", (root / "outputs" / "workflows" / "workflow-report.md").read_text(encoding="utf-8"))

    def test_cli_performance_thesis_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_theses(root, [_thesis("thesis_ai", support=["ev_1"])])
            _write_performance(root, [_decision("decision_ai", "user_confirmed")])

            for command in [["thesis"], ["thesis", "--history"], ["thesis", "--delta"], ["thesis", "--scoreboard"], ["thesis", "--export"]]:
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = main(["performance", "--root", str(root), *command])
                self.assertEqual(exit_code, 0)
                self.assertTrue(output.getvalue())

    def test_deterministic_output_structure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_theses(root, [_thesis("thesis_ai", support=["ev_1"], sources=["source_a"])])
            _write_performance(root, [_decision("decision_ai", "user_confirmed")])
            store = ThesisAccuracyStore(root)

            first = store.build().to_dict()
            second = store.build().to_dict()

            self.assertEqual(first["snapshot"]["snapshot_id"], second["snapshot"]["snapshot_id"])
            self.assertEqual(first["scores"], second["scores"])

    def test_no_provider_or_external_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_theses(root, [_thesis("thesis_ai", support=["ev_1"])])
            _write_performance(root, [_decision("decision_ai", "user_confirmed")])

            with patch("constellation.thesis_accuracy._read_optional_json", wraps=__import__("constellation.thesis_accuracy", fromlist=["_read_optional_json"])._read_optional_json) as reader:
                ThesisAccuracyStore(root).build()

            self.assertGreater(reader.call_count, 0)

    def test_scoreboard_output_exists(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_theses(root, [_thesis("thesis_ai", support=["ev_1"])])
            _write_performance(root, [_decision("decision_ai", "user_confirmed")])

            ThesisAccuracyStore(root).build()
            scoreboard = (root / "outputs" / "performance" / "thesis-scoreboard.md").read_text(encoding="utf-8")

            self.assertIn("Thesis Accuracy Scoreboard", scoreboard)
            self.assertIn("thesis_ai", read_json(root / "outputs" / "performance" / "thesis-accuracy.json")["scores"][0]["thesis_id"])


def _thesis(thesis_id: str, *, support: list[str], conflicts: list[str] | None = None, sources: list[str] | None = None) -> dict:
    return {
        "thesis_id": thesis_id,
        "title": "AI Infrastructure thesis",
        "category": "strategic_theme",
        "created_at": "2026-07-01T00:00:00-07:00",
        "updated_at": "2026-07-01T00:00:00-07:00",
        "status": "active",
        "supporting_evidence_ids": support,
        "conflicting_evidence_ids": conflicts or [],
        "finding_ids": ["finding_ai"],
        "source_ids": sources or ["source_a"],
        "memory_snapshot_ids": ["memory_1"],
        "morning_brief_ids": ["brief_1"],
        "confidence": {"label": "medium", "support_count": len(support), "conflict_count": len(conflicts or []), "repeated_confirmation_count": 0, "explicit_contradiction_count": len(conflicts or []), "rule": "test"},
        "metadata": {"related_themes": ["AI Infrastructure"], "related_entities": ["NVDA"]},
    }


def _decision(entry_id: str, outcome_status: str) -> dict:
    return {
        "outcome_id": f"outcome_{entry_id}",
        "entry_id": entry_id,
        "title": "AI Infrastructure decision review",
        "decision_type": "research_review",
        "entry_type": "thesis_review",
        "status": "open",
        "outcome_status": outcome_status,
        "review_status": "reviewed",
        "created_at": "2026-07-01",
        "review_at": "2026-07-02",
        "related_themes": ["AI Infrastructure"],
        "related_entities": ["NVDA"],
        "related_catalysts": ["earnings"],
        "related_risks": [],
        "linked_lifecycle_changes": [],
        "linked_catalyst_changes": [],
        "linked_portfolio_changes": [],
        "linked_risk_changes": [],
        "user_recorded_outcome": outcome_status,
        "user_recorded_lessons": "",
        "system_observations": [],
        "follow_up_needed": outcome_status in {"pending", "user_challenged", "user_contradicted"},
        "follow_up_reason": "",
        "provenance": {"source": "test"},
    }


def _write_theses(root: Path, theses: list[dict]) -> None:
    write_json(root / "outputs" / "thesis" / "theses.json", {"theses": theses})


def _write_performance(root: Path, decisions: list[dict]) -> None:
    signal = {
        "signal_id": "signal_missing_rationale",
        "signal_type": "missing_rationale",
        "related_decision_ids": [str(item["entry_id"]) for item in decisions if item["outcome_status"] != "user_confirmed"],
        "severity": "medium",
    }
    data = {"decision_outcomes": decisions, "performance_signals": [signal], "learning_loop": {"snapshot_id": "loop_1"}}
    write_json(root / "outputs" / "performance" / "performance-intelligence.json", data)
    write_json(root / "outputs" / "performance" / "decision-outcomes.json", {"decision_outcomes": decisions})


def _create_minimal_tree(root: Path) -> None:
    for relative in [
        "inbox/google-drive/incoming",
        "inbox/gmail/incoming",
        "inbox/manual/incoming",
        "config",
        "memory/evidence",
        "memory/graph",
        "logs/runs",
    ]:
        (root / relative).mkdir(parents=True, exist_ok=True)
    (root / "config" / "sources.yaml").write_text("sources: []\n", encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
