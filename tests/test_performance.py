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
from constellation.performance import PerformanceIntelligenceStore
from constellation.workflow import WorkflowStore


class PerformanceIntelligenceTests(unittest.TestCase):
    def test_empty_performance_build_and_missing_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            report = PerformanceIntelligenceStore(root).build()

            self.assertTrue(report.learning_loop.available)
            self.assertEqual(report.learning_loop.decision_count, 0)
            self.assertTrue((root / "outputs" / "performance" / "performance-intelligence.md").exists())
            self.assertGreater(len(report.learning_loop.source_artifacts_missing), 0)

    def test_decision_outcome_generation_and_pending_classification(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_decisions(root, [_entry("pending", status="open", review_status="not_due", review_at="2099-01-01")])

            data = PerformanceIntelligenceStore(root).build().to_dict()

            self.assertEqual(data["decision_count"], 1)
            self.assertEqual(data["decision_outcomes"][0]["outcome_status"], "pending")

    def test_review_due_and_overdue_classification(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_decisions(
                root,
                [
                    _entry("due", review_status="due", review_at="2026-07-08"),
                    _entry("overdue", review_status="overdue", review_at="2020-01-01"),
                ],
            )

            outcomes = PerformanceIntelligenceStore(root).build().decision_outcomes
            statuses = [item.outcome_status for item in outcomes]

            self.assertEqual(statuses[:2], ["review_overdue", "review_due"])

    def test_user_outcome_classifications(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_decisions(
                root,
                [
                    _entry("confirmed", status="confirmed", outcome_status="user_confirmed", outcome_text="Confirmed by explicit note."),
                    _entry("challenged", status="challenged", outcome_status="user_challenged", outcome_text="Challenged by explicit note."),
                    _entry("contradicted", status="contradicted", outcome_status="user_contradicted", outcome_text="Contradicted by explicit note."),
                    _entry("lesson", lessons="Record uncertainty earlier.", outcome_status="lesson_recorded", outcome_text="Lesson was recorded."),
                ],
            )

            statuses = {item.entry_id: item.outcome_status for item in PerformanceIntelligenceStore(root).build().decision_outcomes}

            self.assertEqual(statuses["confirmed"], "user_confirmed")
            self.assertEqual(statuses["challenged"], "user_challenged")
            self.assertEqual(statuses["contradicted"], "user_contradicted")
            self.assertEqual(statuses["lesson"], "lesson_recorded")

    def test_reviewed_without_outcome_classification(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_decisions(root, [_entry("reviewed", status="reviewed", review_status="reviewed", outcome_status="no_outcome_recorded")])

            outcome = PerformanceIntelligenceStore(root).build().decision_outcomes[0]

            self.assertEqual(outcome.outcome_status, "no_outcome_recorded")

    def test_missing_review_date_rationale_uncertainty_and_overdue_signals(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_decisions(root, [_entry("gap", review_status="no_review_date", review_at=None, rationale="", uncertainties="", follow_up="")])

            report = PerformanceIntelligenceStore(root).build()
            signal_types = {item.signal_type for item in report.performance_signals}

            self.assertIn("missing_review_date", signal_types)
            self.assertIn("missing_rationale", signal_types)
            self.assertIn("missing_uncertainty", signal_types)
            self.assertIn("missing_follow_up", signal_types)

    def test_explicit_and_repeated_process_lessons(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            entries = [_entry(f"missing-{idx}", status="reviewed", review_status="reviewed", outcome_status="no_outcome_recorded") for idx in range(3)]
            entries.append(_entry("lesson", lessons="Use clearer review prompts.", outcome_status="lesson_recorded", outcome_text="Lesson was recorded."))
            _write_decisions(root, entries)

            lessons = PerformanceIntelligenceStore(root).build().process_lessons
            types = {item.lesson_type for item in lessons}

            self.assertIn("user_recorded", types)
            self.assertIn("outcome_tracking", types)

    def test_theme_catalyst_portfolio_and_risk_linking(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_decisions(root, [_entry("linked")])
            _write_link_artifacts(root)

            outcome = PerformanceIntelligenceStore(root).build().decision_outcomes[0]

            self.assertTrue(outcome.linked_lifecycle_changes)
            self.assertTrue(outcome.linked_catalyst_changes)
            self.assertTrue(outcome.linked_portfolio_changes)
            self.assertTrue(outcome.linked_risk_changes)

    def test_markdown_outputs_history_delta_and_duplicate_snapshot_avoidance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_decisions(root, [_entry("one")])
            store = PerformanceIntelligenceStore(root)

            first = store.build()
            second = store.build()

            self.assertEqual(first.report_id, second.report_id)
            self.assertEqual(len(store.history()), 1)
            self.assertTrue((root / "outputs" / "performance" / "decision-outcomes.md").exists())
            self.assertTrue((root / "outputs" / "performance" / "performance-signals.md").exists())
            self.assertTrue((root / "outputs" / "performance" / "process-lessons.md").exists())
            self.assertTrue((root / "outputs" / "performance" / "learning-loop.md").exists())
            self.assertIn("new_decision_outcomes", read_json(root / "outputs" / "performance" / "performance-delta.json"))

    def test_dashboard_performance_summary_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_decisions(root, [_entry("one")])
            PerformanceIntelligenceStore(root).build()

            dashboard = ExecutiveDashboardStore(root).generate(overwrite=True)

            self.assertTrue(dashboard.performance_intelligence_summary["performance_intelligence_available"])
            self.assertIn("performance_snapshot_id", dashboard.performance_intelligence_summary)

    def test_workflow_performance_fields_and_morning_step(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_minimal_tree(root)
            _write_decisions(root, [_entry("one")])

            run = WorkflowStore(root).run("Morning")
            commands = [step["command"] for step in run.executed_steps]
            perf_step = next(step for step in run.executed_steps if step["command"] == "performance")

            self.assertEqual(len(commands), 19)
            self.assertIn("decision_count", perf_step["details"])
            self.assertIn("performance_snapshot_id", perf_step["details"])
            self.assertIn("Performance Intelligence", (root / "outputs" / "workflows" / "workflow-report.md").read_text(encoding="utf-8"))

    def test_cli_performance_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_decisions(root, [_entry("one")])

            for command in [[], ["review"], ["decisions"], ["signals"], ["lessons"], ["export"], ["history"], ["delta"]]:
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = main(["performance", "--root", str(root), *command])
                self.assertEqual(exit_code, 0)

    def test_deterministic_sorting_and_repeated_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_decisions(root, [_entry("z", review_status="not_due", review_at="2099-01-01"), _entry("a", review_status="overdue", review_at="2020-01-01")])
            store = PerformanceIntelligenceStore(root)

            first = [item.entry_id for item in store.build().decision_outcomes]
            second = [item.entry_id for item in store.build().decision_outcomes]

            self.assertEqual(first, ["a", "z"])
            self.assertEqual(first, second)

    def test_no_provider_execution_or_external_calls_and_no_advice_language(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _write_decisions(root, [_entry("one", lessons="Improve review discipline.")])

            with patch("constellation.performance._read_optional_json", wraps=__import__("constellation.performance", fromlist=["_read_optional_json"])._read_optional_json) as reader:
                PerformanceIntelligenceStore(root).build()

            text = (root / "outputs" / "performance" / "performance-intelligence.md").read_text(encoding="utf-8").lower()
            self.assertGreater(reader.call_count, 0)
            for forbidden in ["buy ", "sell ", "hold ", "price target", "expected return", "trade recommendation"]:
                self.assertNotIn(forbidden, text)

    def test_private_journal_content_not_read_directly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            (root / "journal" / "ai-markets").mkdir(parents=True)
            (root / "journal" / "ai-markets" / "private.md").write_text("PRIVATE SECRET SHOULD NOT APPEAR", encoding="utf-8")
            _write_decisions(root, [_entry("one")])

            PerformanceIntelligenceStore(root).build()
            text = (root / "outputs" / "performance" / "performance-intelligence.md").read_text(encoding="utf-8")

            self.assertNotIn("PRIVATE SECRET", text)


def _entry(
    entry_id: str,
    *,
    status: str = "open",
    review_status: str = "not_due",
    review_at: str | None = "2099-01-01",
    outcome_status: str = "pending",
    outcome_text: str = "",
    rationale: str = "Evidence supports monitoring.",
    uncertainties: str = "Uncertainty remains.",
    follow_up: str = "Review later.",
    lessons: str = "",
) -> dict:
    return {
        "entry_id": entry_id,
        "title": f"Decision {entry_id}",
        "domain": "ai_markets",
        "entry_type": "thesis_review",
        "decision_type": "research_review",
        "status": status,
        "created_at": "2026-07-07",
        "updated_at": "2026-07-07",
        "review_at": review_at,
        "confidence": "medium",
        "related_themes": ["AI Infrastructure"],
        "related_entities": ["NVDA"],
        "related_catalysts": ["earnings"],
        "related_risks": ["risk"],
        "related_questions": [],
        "related_evidence_ids": [],
        "linked_theme_lifecycle_statuses": [],
        "linked_portfolio_exposures": [],
        "linked_catalyst_priorities": [],
        "rationale": rationale,
        "uncertainties": uncertainties,
        "follow_up": follow_up,
        "lessons": lessons,
        "outcome": {"status": outcome_status, "text": outcome_text},
        "review": {"review_status": review_status, "review_at": review_at},
        "source_path": "outputs/ai-markets/decisions/decision-journal.json",
        "user_provided": True,
        "provenance": {"source": "test"},
    }


def _write_decisions(root: Path, entries: list[dict]) -> None:
    data = {
        "snapshot_id": "decisions_test",
        "created_at": "2026-07-07T00:00:00-07:00",
        "entry_count": len(entries),
        "entries": entries,
    }
    write_json(root / "outputs" / "ai-markets" / "decisions" / "decision-journal.json", data)
    write_json(root / "outputs" / "ai-markets" / "decisions" / "decision-entries.json", {"entries": entries})


def _write_link_artifacts(root: Path) -> None:
    write_json(root / "outputs" / "ai-markets" / "theme-lifecycle.json", {"themes": [{"theme_name": "AI Infrastructure", "current_status": "weakening"}]})
    write_json(root / "outputs" / "ai-markets" / "catalysts" / "catalyst-monitor.json", {"catalysts": [{"catalyst_id": "cat_1", "category": "earnings", "title": "Earnings", "priority": "high"}]})
    write_json(root / "outputs" / "ai-markets" / "portfolio" / "portfolio-intelligence.json", {"watchlist": [{"symbol": "NVDA", "research_priority": "high"}], "exposures": [{"theme_name": "AI Infrastructure", "research_priority": "high"}]})
    write_json(root / "outputs" / "ai-markets" / "ai-markets.json", {"risks": [{"risk_id": "risk_1", "description": "risk remains unresolved"}]})


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
