from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from constellation.ai_markets import AIMarketsBriefStore, AIMarketsCatalystStore, AIMarketsDecisionJournalStore, AIMarketsPortfolioStore, AIMarketsStore, AIMarketsThemeLifecycleStore, _normalize_question
from constellation.cli import main
from constellation.dashboard import ExecutiveDashboardStore
from constellation.io import write_json
from constellation.workflow import WorkflowStore


class AIMarketsTests(unittest.TestCase):
    def test_empty_state_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)

            report = AIMarketsStore(root).build()

            self.assertEqual(report.themes, [])
            self.assertTrue(report.limitations)

    def test_build_from_existing_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_artifacts(root)

            report = AIMarketsStore(root).build()

            self.assertGreaterEqual(len(report.themes), 2)
            self.assertTrue((root / "outputs" / "ai-markets" / "ai-markets.json").exists())

    def test_deterministic_theme_classification(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_artifacts(root)

            report = AIMarketsStore(root).build()

            names = [theme.name for theme in report.themes]
            self.assertIn("Semiconductors", names)
            self.assertIn("AI Infrastructure", names)

    def test_deterministic_entity_detection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_artifacts(root)

            report = AIMarketsStore(root).build()

            symbols = [entity.symbol for entity in report.entities]
            self.assertIn("NVDA", symbols)
            self.assertIn("BTC", symbols)

    def test_confidence_rules(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_artifacts(root, repeated=True)

            report = AIMarketsStore(root).build()
            semi = next(theme for theme in report.themes if theme.name == "Semiconductors")

            self.assertEqual(semi.confidence, "high")

    def test_risks_and_open_questions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_artifacts(root)

            report = AIMarketsStore(root).build()

            self.assertTrue(report.risks)
            self.assertTrue(report.open_questions)

    def test_question_normalization(self) -> None:
        self.assertEqual(_normalize_question("Is is NVDA power a bottleneck??"), "is nvda power a bottleneck?")
        self.assertEqual(_normalize_question("What evidence confirms BTC liquidity?"), "what evidence confirms btc liquidity?")

    def test_duplicate_question_collapse(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_question_artifacts(root)

            report = AIMarketsStore(root).build()

            normalized = [question.normalized_question for question in report.open_questions]
            self.assertEqual(normalized.count("what evidence confirms btc liquidity?"), 1)
            btc_question = next(question for question in report.open_questions if question.normalized_question == "what evidence confirms btc liquidity?")
            self.assertGreaterEqual(len(btc_question.supporting_text), 2)

    def test_executive_question_ranking_and_priority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_question_artifacts(root)

            report = AIMarketsStore(root).build()

            self.assertLessEqual(len(report.executive_questions), 10)
            self.assertEqual(report.executive_questions[0].priority, "high")
            self.assertTrue(any(question.priority == "high" and "power" in question.question.lower() for question in report.executive_questions))

    def test_expanded_ticker_and_company_detection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_entity_artifacts(root)

            report = AIMarketsStore(root).build()

            symbols = {entity.symbol for entity in report.entities}
            self.assertIn("AMD", symbols)
            self.assertIn("GOOGL", symbols)
            self.assertIn("COIN", symbols)
            self.assertIn("ETH", symbols)

    def test_ticker_false_positive_avoidance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            write_json(
                root / "outputs" / "reports" / "latest-report.json",
                {"evidence_references": [{"evidence_id": "ev_noise", "source_id": "source-n", "summary": "The random word advancement should not create a ticker match."}]},
            )

            report = AIMarketsStore(root).build()

            self.assertNotIn("AMD", {entity.symbol for entity in report.entities})

    def test_executive_question_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_question_artifacts(root)

            AIMarketsStore(root).build()

            self.assertTrue((root / "outputs" / "ai-markets" / "executive-questions.json").exists())
            self.assertTrue((root / "outputs" / "ai-markets" / "executive-questions.md").exists())

    def test_report_export(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_artifacts(root)
            store = AIMarketsStore(root)
            store.build()

            output = store.export()

            self.assertTrue(output.exists())
            self.assertTrue((root / "outputs" / "ai-markets" / "watchlist.md").exists())
            self.assertTrue((root / "outputs" / "ai-markets" / "content-ideas.md").exists())

    def test_cli_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_artifacts(root)

            build_out = io.StringIO()
            with redirect_stdout(build_out):
                build_exit = main(["ai-markets", "--root", str(root), "build"])
            status_out = io.StringIO()
            with redirect_stdout(status_out):
                status_exit = main(["ai-markets", "--root", str(root), "status"])
            themes_out = io.StringIO()
            with redirect_stdout(themes_out):
                themes_exit = main(["ai-markets", "--root", str(root), "themes"])
            report_out = io.StringIO()
            with redirect_stdout(report_out):
                report_exit = main(["ai-markets", "--root", str(root), "report"])
            export_out = io.StringIO()
            with redirect_stdout(export_out):
                export_exit = main(["ai-markets", "--root", str(root), "export"])

            self.assertEqual(build_exit, 0)
            self.assertEqual(status_exit, 0)
            self.assertEqual(themes_exit, 0)
            self.assertEqual(report_exit, 0)
            self.assertEqual(export_exit, 0)
            self.assertIn("theme_count:", build_out.getvalue())
            self.assertIn("Semiconductors", themes_out.getvalue())

    def test_dashboard_integration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_artifacts(root)
            AIMarketsStore(root).build()

            dashboard = ExecutiveDashboardStore(root).generate(overwrite=True)

            self.assertTrue(dashboard.ai_markets_summary["available"])
            self.assertGreater(dashboard.ai_markets_summary["entity_count"], 0)
            self.assertIn("executive_question_count", dashboard.ai_markets_summary)
            self.assertIn("top_executive_questions", dashboard.ai_markets_summary)

    def test_workflow_integration(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)

            run = WorkflowStore(root).run("Morning")

            self.assertIn("ai-markets build", [step["command"] for step in run.executed_steps])
            self.assertTrue((root / "outputs" / "ai-markets" / "ai-markets.json").exists())
            ai_step = next(step for step in run.executed_steps if step["command"] == "ai-markets build")
            self.assertIn("executive_question_count", ai_step["details"])

    def test_cli_questions_executive(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_question_artifacts(root)
            AIMarketsStore(root).build()

            output = io.StringIO()
            with redirect_stdout(output):
                exit_code = main(["ai-markets", "--root", str(root), "questions", "--executive"])

            self.assertEqual(exit_code, 0)
            self.assertIn("executive_questions:", output.getvalue())

    def test_deterministic_output_across_repeated_runs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_question_artifacts(root)
            store = AIMarketsStore(root)

            first = store.build()
            second = store.build()

            self.assertEqual([item.question_id for item in first.open_questions], [item.question_id for item in second.open_questions])
            self.assertEqual([item.question_id for item in first.executive_questions], [item.question_id for item in second.executive_questions])

    def test_lifecycle_snapshot_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_artifacts(root)

            AIMarketsStore(root).build()
            lifecycle = AIMarketsThemeLifecycleStore(root).load()

            self.assertTrue(lifecycle["snapshot_id"])
            self.assertTrue(lifecycle["themes"])
            self.assertTrue((root / "outputs" / "ai-markets" / "theme-lifecycle.md").exists())

    def test_lifecycle_status_assignment(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_artifacts(root, repeated=True)

            AIMarketsStore(root).build()
            themes = AIMarketsThemeLifecycleStore(root).load()["themes"]
            statuses = {theme["current_status"] for theme in themes}

            self.assertTrue(statuses.intersection({"emerging", "active", "high_conviction"}))

    def test_strengthening_transition_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_artifacts(root)
            AIMarketsStore(root).build()
            _write_artifacts(root, repeated=True)

            AIMarketsStore(root).build()
            lifecycle = AIMarketsThemeLifecycleStore(root).load()

            self.assertTrue(any(item["transition_type"] == "evidence_changed" for item in lifecycle["transitions"]))

    def test_high_conviction_theme_detection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_high_conviction_artifacts(root)

            AIMarketsStore(root).build()
            lifecycle = AIMarketsThemeLifecycleStore(root).load()

            self.assertTrue(any(theme["current_status"] == "high_conviction" for theme in lifecycle["themes"]))

    def test_contradicted_theme_detection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_contradiction_artifacts(root)

            AIMarketsStore(root).build()
            lifecycle = AIMarketsThemeLifecycleStore(root).load()

            self.assertTrue(any(theme["current_status"] == "contradicted" for theme in lifecycle["themes"]))

    def test_archived_theme_detection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_artifacts(root)
            AIMarketsStore(root).build()
            write_json(root / "outputs" / "reports" / "latest-report.json", {"report_id": "empty_1", "evidence_references": [], "sections": []})

            AIMarketsStore(root).build()
            write_json(root / "outputs" / "reports" / "latest-report.json", {"report_id": "empty_2", "evidence_references": [], "sections": []})
            AIMarketsStore(root).build()
            write_json(root / "outputs" / "reports" / "latest-report.json", {"report_id": "empty_3", "evidence_references": [], "sections": []})
            AIMarketsStore(root).build()

            lifecycle = AIMarketsThemeLifecycleStore(root).load()
            self.assertTrue(any(theme["current_status"] == "archived" for theme in lifecycle["themes"]))

    def test_lifecycle_history_duplicate_avoidance(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_artifacts(root)
            store = AIMarketsStore(root)

            store.build()
            store.build()
            history = AIMarketsThemeLifecycleStore(root).history()

            self.assertEqual(len(history), 1)

    def test_cli_lifecycle_and_theme_detail(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_artifacts(root)
            AIMarketsStore(root).build()
            theme_id = AIMarketsThemeLifecycleStore(root).load()["themes"][0]["theme_id"]

            lifecycle_out = io.StringIO()
            with redirect_stdout(lifecycle_out):
                lifecycle_exit = main(["ai-markets", "--root", str(root), "lifecycle"])
            theme_out = io.StringIO()
            with redirect_stdout(theme_out):
                theme_exit = main(["ai-markets", "--root", str(root), "theme", theme_id])

            self.assertEqual(lifecycle_exit, 0)
            self.assertEqual(theme_exit, 0)
            self.assertIn("lifecycle_available:", lifecycle_out.getvalue())
            self.assertIn("current_lifecycle_status:", theme_out.getvalue())

    def test_report_dashboard_and_workflow_lifecycle_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_artifacts(root)
            AIMarketsStore(root).build()

            report_text = (root / "outputs" / "ai-markets" / "ai-markets-report.md").read_text(encoding="utf-8")
            dashboard = ExecutiveDashboardStore(root).generate(overwrite=True)

            self.assertIn("## Theme Lifecycle", report_text)
            self.assertTrue(dashboard.ai_markets_summary["lifecycle_available"])
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            run = WorkflowStore(root).run("Morning")
            ai_step = next(step for step in run.executed_steps if step["command"] == "ai-markets build")
            self.assertIn("high_conviction_theme_count", ai_step["details"])

    def test_lifecycle_deterministic_sorting(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_high_conviction_artifacts(root)

            AIMarketsStore(root).build()
            themes = AIMarketsThemeLifecycleStore(root).load()["themes"]
            sort_keys = [(theme["current_status"], -theme["evidence_count"], theme["theme_name"]) for theme in themes]

            self.assertEqual(sort_keys, sorted(sort_keys, key=lambda item: ({"high_conviction": 0, "strengthening": 1, "active": 2, "emerging": 3, "weakening": 4, "contradicted": 5, "archived": 6}[item[0]], item[1], item[2])))

    def test_portfolio_config_missing_detected_entities_only(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_artifacts(root)

            AIMarketsStore(root).build()
            portfolio = AIMarketsPortfolioStore(root).load()

            self.assertFalse(portfolio["config_available"])
            self.assertEqual(portfolio["mode"], "detected_entities_only")
            self.assertGreater(portfolio["detected_entity_count"], 0)

    def test_portfolio_config_parsing_and_watchlist_mode(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_artifacts(root)
            _write_portfolio_config(root, positions=False)

            AIMarketsStore(root).build()
            portfolio = AIMarketsPortfolioStore(root).load()

            self.assertTrue(portfolio["config_available"])
            self.assertEqual(portfolio["mode"], "watchlist")
            self.assertEqual(portfolio["watchlist_count"], 2)

    def test_portfolio_theme_exposure_risk_question_mapping(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_question_artifacts(root)
            _write_portfolio_config(root)

            AIMarketsStore(root).build()
            portfolio = AIMarketsPortfolioStore(root).load()

            self.assertTrue(portfolio["exposures"])
            self.assertTrue(portfolio["risks"])
            self.assertTrue(portfolio["questions"])

    def test_portfolio_priority_and_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_contradiction_artifacts(root)
            _write_portfolio_config(root)

            AIMarketsStore(root).build()
            portfolio = AIMarketsPortfolioStore(root).load()

            self.assertGreaterEqual(portfolio["high_priority_review_count"], 1)
            self.assertTrue((root / "outputs" / "ai-markets" / "portfolio" / "portfolio-intelligence.md").exists())
            self.assertTrue((root / "outputs" / "ai-markets" / "portfolio" / "portfolio-exposures.json").exists())

    def test_portfolio_cli_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_artifacts(root)
            AIMarketsStore(root).build()

            for option in [[], ["--exposures"], ["--risks"], ["--watchlist"], ["--questions"]]:
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = main(["ai-markets", "--root", str(root), "portfolio", *option])
                self.assertEqual(exit_code, 0)

    def test_portfolio_dashboard_and_workflow_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_artifacts(root)
            AIMarketsStore(root).build()

            dashboard = ExecutiveDashboardStore(root).generate(overwrite=True)
            self.assertIn("portfolio_intelligence_available", dashboard.ai_markets_summary)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            run = WorkflowStore(root).run("Morning")
            self.assertIn("ai-markets portfolio", [step["command"] for step in run.executed_steps])

    def test_portfolio_history_delta_and_determinism(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_artifacts(root)
            store = AIMarketsStore(root)

            store.build()
            first = AIMarketsPortfolioStore(root).load()
            store.build()
            second = AIMarketsPortfolioStore(root).load()

            self.assertEqual(first["snapshot_id"], second["snapshot_id"])
            self.assertEqual(len(AIMarketsPortfolioStore(root).history()), 1)
            self.assertIn("delta", second)

    def test_portfolio_report_has_no_engine_generated_trading_advice(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_artifacts(root)

            AIMarketsStore(root).build()
            text = (root / "outputs" / "ai-markets" / "portfolio" / "portfolio-intelligence.md").read_text(encoding="utf-8").lower()

            self.assertNotIn("buy ", text)
            self.assertNotIn("sell ", text)
            self.assertNotIn("financial advice", text.replace("not financial advice", ""))

    def test_catalyst_monitor_build_and_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_catalyst_artifacts(root)

            AIMarketsStore(root).build()
            data = AIMarketsCatalystStore(root).load()

            self.assertTrue(data["snapshot_id"])
            self.assertGreater(data["total_catalyst_count"], 0)
            self.assertTrue((root / "outputs" / "ai-markets" / "catalysts" / "catalyst-monitor.md").exists())
            self.assertTrue((root / "outputs" / "ai-markets" / "catalysts" / "catalyst-calendar.md").exists())

    def test_catalyst_category_time_horizon_and_priority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_catalyst_artifacts(root)
            _write_portfolio_config(root)

            AIMarketsStore(root).build()
            catalysts = AIMarketsCatalystStore(root).load()["catalysts"]

            self.assertTrue(any(item["category"] == "earnings" for item in catalysts))
            self.assertTrue(any(item["time_horizon"] == "near_term" for item in catalysts))
            self.assertTrue(any(item["priority"] == "high" for item in catalysts))

    def test_catalyst_linking_and_delta_transitions(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_catalyst_artifacts(root)

            AIMarketsStore(root).build()
            first = AIMarketsCatalystStore(root).load()
            write_json(root / "outputs" / "reports" / "latest-report.json", {"report_id": "empty", "evidence_references": [], "sections": []})
            AIMarketsStore(root).build()
            second = AIMarketsCatalystStore(root).load()

            self.assertTrue(first["delta"]["new_catalysts"])
            self.assertTrue(second["delta"]["status_changes"] or second["delta"]["removed_catalysts"])
            self.assertTrue(second["transitions"])

    def test_catalyst_cli_commands(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_catalyst_artifacts(root)
            AIMarketsStore(root).build()

            for option in [[], ["--priorities"], ["--calendar"], ["--history"], ["--delta"], ["--transitions"]]:
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = main(["ai-markets", "--root", str(root), "catalysts", *option])
                self.assertEqual(exit_code, 0)

    def test_catalyst_dashboard_and_workflow_fields(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_catalyst_artifacts(root)
            AIMarketsStore(root).build()

            dashboard = ExecutiveDashboardStore(root).generate(overwrite=True)
            self.assertIn("catalyst_monitor_available", dashboard.ai_markets_summary)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            run = WorkflowStore(root).run("Morning")
            self.assertIn("ai-markets catalysts", [step["command"] for step in run.executed_steps])

    def test_catalyst_determinism_sorting_and_safety_language(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_catalyst_artifacts(root)
            store = AIMarketsStore(root)

            store.build()
            first = AIMarketsCatalystStore(root).load()
            store.build()
            second = AIMarketsCatalystStore(root).load()
            text = (root / "outputs" / "ai-markets" / "catalysts" / "catalyst-monitor.md").read_text(encoding="utf-8").lower()

            self.assertEqual(first["snapshot_id"], second["snapshot_id"])
            self.assertNotIn("buy ", text)
            self.assertNotIn("sell ", text)
            self.assertNotIn("price target", text)

    def test_decision_journal_empty_and_outputs(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_artifacts(root)

            AIMarketsStore(root).build()
            data = AIMarketsDecisionJournalStore(root).load()

            self.assertFalse(data["config_available"])
            self.assertEqual(data["entry_count"], 0)
            self.assertTrue((root / "outputs" / "ai-markets" / "decisions" / "decision-journal.md").exists())

    def test_decision_entry_parsing_linking_review_and_outcome(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_catalyst_artifacts(root)
            _write_decision_entry(root, review_at="2020-01-01", status="confirmed", outcome=True)

            AIMarketsStore(root).build()
            entry = AIMarketsDecisionJournalStore(root).load()["entries"][0]

            self.assertEqual(entry["review"]["review_status"], "reviewed")
            self.assertEqual(entry["outcome"]["status"], "user_confirmed")
            self.assertIn("AI Infrastructure", entry["related_themes"])
            self.assertIn("NVDA", entry["related_entities"])
            self.assertTrue(entry["related_catalysts"])

    def test_decision_due_overdue_and_no_review_date(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_artifacts(root)
            _write_decision_entry(root, review_at="2020-01-01")
            _write_decision_entry(root, filename="no-review.md", title="No Review", review_at="")

            AIMarketsStore(root).build()
            statuses = {entry["review"]["review_status"] for entry in AIMarketsDecisionJournalStore(root).load()["entries"]}

            self.assertIn("overdue", statuses)
            self.assertIn("no_review_date", statuses)

    def test_decision_cli_dashboard_workflow_and_template(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_artifacts(root)
            AIMarketsStore(root).build()

            for option in [[], ["--entries"], ["--queue"], ["--timeline"], ["--outcomes"], ["--history"], ["--delta"], ["--create-template"]]:
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = main(["ai-markets", "--root", str(root), "decisions", *option])
                self.assertEqual(exit_code, 0)
            dashboard = ExecutiveDashboardStore(root).generate(overwrite=True)
            self.assertIn("decision_journal_available", dashboard.ai_markets_summary)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            run = WorkflowStore(root).run("Morning")
            self.assertIn("ai-markets decisions", [step["command"] for step in run.executed_steps])

    def test_decision_history_delta_determinism_and_safety(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_artifacts(root)
            _write_decision_entry(root)
            store = AIMarketsStore(root)

            store.build()
            first = AIMarketsDecisionJournalStore(root).load()
            store.build()
            second = AIMarketsDecisionJournalStore(root).load()
            text = (root / "outputs" / "ai-markets" / "decisions" / "decision-journal.md").read_text(encoding="utf-8").lower()

            self.assertEqual(first["snapshot_id"], second["snapshot_id"])
            self.assertEqual(len(AIMarketsDecisionJournalStore(root).history()), 1)
            self.assertIn("delta", second)
            self.assertNotIn("buy ", text)
            self.assertNotIn("sell ", text)
            self.assertNotIn("price target", text)

    def test_executive_brief_empty_and_existing_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)

            snapshot = AIMarketsBriefStore(root).build()

            self.assertTrue(snapshot.brief_id)
            self.assertTrue((root / "outputs" / "ai-markets" / "briefings" / "morning-brief.md").exists())
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_catalyst_artifacts(root)

            AIMarketsStore(root).build()
            data = AIMarketsBriefStore(root).load()

            self.assertGreater(data["research_agenda_count"], 0)

    def test_executive_brief_agenda_sources_and_priority(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_catalyst_artifacts(root)
            _write_portfolio_config(root)
            _write_decision_entry(root, review_at="2020-01-01")

            AIMarketsStore(root).build()
            agenda = AIMarketsBriefStore(root).load()["research_agenda"]
            source_types = {item["source_type"] for item in agenda}

            self.assertIn("decision_review", source_types)
            self.assertIn("catalyst", source_types)
            self.assertIn("portfolio_review", source_types)
            self.assertTrue(any(item["priority"] == "high" for item in agenda))
            brief = AIMarketsBriefStore(root).load()
            self.assertGreater(brief["morning_priority_count"], 0)
            self.assertEqual(brief["morning_priorities"][0]["priority"], "high")

    def test_executive_brief_cli_dashboard_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_artifacts(root)
            AIMarketsStore(root).build()

            for option in [[], ["--agenda"], ["--history"], ["--delta"]]:
                output = io.StringIO()
                with redirect_stdout(output):
                    exit_code = main(["ai-markets", "--root", str(root), "brief", *option])
                self.assertEqual(exit_code, 0)
            dashboard = ExecutiveDashboardStore(root).generate(overwrite=True)
            self.assertIn("executive_brief_available", dashboard.ai_markets_summary)
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            run = WorkflowStore(root).run("Morning")
            self.assertIn("ai-markets brief", [step["command"] for step in run.executed_steps])

    def test_executive_brief_history_delta_determinism_and_safety(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_catalyst_artifacts(root)
            store = AIMarketsStore(root)

            store.build()
            first = AIMarketsBriefStore(root).load()
            store.build()
            second = AIMarketsBriefStore(root).load()
            text = (root / "outputs" / "ai-markets" / "briefings" / "morning-brief.md").read_text(encoding="utf-8").lower()

            self.assertEqual(first["brief_id"], second["brief_id"])
            self.assertEqual(len(AIMarketsBriefStore(root).history()), 1)
            self.assertIn("delta", second)
            self.assertNotIn("buy ", text)
            self.assertNotIn("sell ", text)
            self.assertNotIn("price target", text)

    def test_no_provider_calls(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            _create_tree(root)
            _write_artifacts(root)

            with patch("constellation.providers.EchoProvider.generate") as generate:
                AIMarketsStore(root).build()

            generate.assert_not_called()


def _create_tree(root: Path) -> None:
    for relative in [
        "config",
        "outputs/reports",
        "outputs/dashboard",
        "outputs/evidence-graph",
        "outputs/thesis",
        "outputs/evolution",
        "outputs/source-monitor",
        "outputs/intake",
        "outputs/google-drive",
        "outputs/daily",
        "outputs/morning",
        "outputs/memory",
        "outputs/workflows",
        "memory/evidence",
        "memory/graph",
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


def _write_artifacts(root: Path, *, repeated: bool = False) -> None:
    refs = [
        {"evidence_id": "ev_1", "source_id": "source-a", "summary": "NVDA GPU data center compute catalyst for AI infrastructure."},
        {"evidence_id": "ev_2", "source_id": "source-b", "summary": "BTC liquidity question? Digital asset risk and catalyst."},
        {"evidence_id": "ev_3", "source_id": "source-c", "summary": "Power grid constraint risk for data center buildout."},
    ]
    if repeated:
        refs.extend(
            [
                {"evidence_id": "ev_4", "source_id": "source-d", "summary": "NVDA semiconductor chip demand."},
                {"evidence_id": "ev_5", "source_id": "source-e", "summary": "AVGO semiconductor AI accelerator demand."},
            ]
        )
    write_json(
        root / "outputs" / "reports" / "latest-report.json",
        {
            "report_id": "report_1",
            "evidence_references": refs,
            "sections": [{"title": "Open Questions", "summary": "What evidence confirms BTC liquidity?", "items": ["What evidence confirms BTC liquidity?"]}],
            "risks_gaps": ["Power grid constraint risk."],
        },
    )
    write_json(root / "outputs" / "dashboard" / "dashboard.json", {"dashboard_id": "dashboard_1", "current_risks_gaps": ["AI infrastructure risk."]})
    write_json(root / "outputs" / "evidence-graph" / "evidence-graph.json", {"nodes": [{"node_id": "ev_1", "node_type": "evidence", "label": "NVDA GPU compute", "source_ids": ["source-a"]}], "edges": []})
    write_json(root / "outputs" / "thesis" / "theses.json", {"theses": [{"thesis_id": "thesis_1", "title": "AI infrastructure semiconductor thesis", "status": "active", "confidence": {"label": "medium"}, "supporting_evidence_ids": ["ev_1"], "source_ids": ["source-a"]}]})
    write_json(root / "outputs" / "evolution" / "evolution.json", {"delta": {"delta_id": "delta_1", "trend_records": []}})
    write_json(root / "outputs" / "source-monitor" / "latest-monitor.json", {"monitor_id": "monitor_1"})
    write_json(root / "outputs" / "intake" / "intake-manifest.json", {"manifest_id": "manifest_1"})
    write_json(root / "outputs" / "google-drive" / "google-drive-sync-manifest.json", {"sync_id": "sync_1"})


def _write_question_artifacts(root: Path) -> None:
    refs = [
        {"evidence_id": "ev_q1", "source_id": "source-a", "summary": "Is NVDA power a bottleneck for AI infrastructure?"},
        {"evidence_id": "ev_q2", "source_id": "source-b", "summary": "Does NVDA power bottleneck create data center risk?"},
        {"evidence_id": "ev_q3", "source_id": "source-c", "summary": "What evidence confirms BTC liquidity?"},
        {"evidence_id": "ev_q4", "source_id": "source-d", "summary": "What evidence confirms BTC liquidity??"},
        {"evidence_id": "ev_q5", "source_id": "source-e", "summary": "Open question: does robotics adoption accelerate?"},
    ]
    write_json(root / "outputs" / "reports" / "latest-report.json", {"report_id": "report_q", "evidence_references": refs, "sections": []})


def _write_entity_artifacts(root: Path) -> None:
    refs = [
        {"evidence_id": "ev_e1", "source_id": "source-a", "summary": "Advanced Micro Devices competes in AI accelerators."},
        {"evidence_id": "ev_e2", "source_id": "source-b", "summary": "Google and Alphabet expand AI infrastructure capex."},
        {"evidence_id": "ev_e3", "source_id": "source-c", "summary": "Coinbase supports crypto market structure."},
        {"evidence_id": "ev_e4", "source_id": "source-d", "summary": "Ethereum and ETH adoption remains an open question?"},
    ]
    write_json(root / "outputs" / "reports" / "latest-report.json", {"report_id": "report_e", "evidence_references": refs, "sections": []})


def _write_high_conviction_artifacts(root: Path) -> None:
    refs = [
        {"evidence_id": "ev_h1", "source_id": "source-a", "summary": "NVDA GPU compute supports AI infrastructure."},
        {"evidence_id": "ev_h2", "source_id": "source-b", "summary": "AMD accelerator demand supports AI infrastructure."},
        {"evidence_id": "ev_h3", "source_id": "source-c", "summary": "AVGO chip demand supports AI infrastructure."},
        {"evidence_id": "ev_h4", "source_id": "source-d", "summary": "Data center semiconductor demand supports AI infrastructure."},
    ]
    write_json(root / "outputs" / "reports" / "latest-report.json", {"report_id": "report_h", "evidence_references": refs, "sections": []})


def _write_contradiction_artifacts(root: Path) -> None:
    refs = [
        {"evidence_id": "ev_c1", "source_id": "source-a", "summary": "AI infrastructure demand faces contradiction risk."},
        {"evidence_id": "ev_c2", "source_id": "source-b", "summary": "AI infrastructure conflict risk."},
    ]
    write_json(root / "outputs" / "reports" / "latest-report.json", {"report_id": "report_c", "evidence_references": refs, "sections": []})


def _write_portfolio_config(root: Path, *, positions: bool = True) -> None:
    text = (
        "portfolio:\n"
        "  name: test_portfolio\n"
        "  description: Test only.\n"
        "  base_currency: USD\n"
        "  positions:\n"
    )
    if positions:
        text += (
            "    - symbol: NVDA\n"
            "      name: Nvidia\n"
            "      asset_type: equity\n"
            "      category: AI Infrastructure\n"
            "      conviction: watchlist\n"
            "      notes: Test only.\n"
        )
    text += (
        "  watchlist:\n"
        "    - symbol: BTC\n"
        "      name: Bitcoin\n"
        "      asset_type: crypto\n"
        "    - symbol: GLD\n"
        "      name: Gold ETF\n"
        "      asset_type: etf\n"
    )
    (root / "config" / "portfolio.yaml").write_text(text, encoding="utf-8")


def _write_catalyst_artifacts(root: Path) -> None:
    refs = [
        {"evidence_id": "ev_cat1", "source_id": "source-a", "summary": "NVDA earnings and guidance next week may affect AI infrastructure capex."},
        {"evidence_id": "ev_cat2", "source_id": "source-b", "summary": "FOMC liquidity catalyst this week creates macro liquidity risk."},
        {"evidence_id": "ev_cat3", "source_id": "source-c", "summary": "Power bottleneck risk for data center energy demand."},
    ]
    write_json(root / "outputs" / "reports" / "latest-report.json", {"report_id": "report_cat", "evidence_references": refs, "sections": []})


def _write_decision_entry(root: Path, *, filename: str = "entry.md", title: str = "Review AI Infrastructure", review_at: str = "2099-01-01", status: str = "open", outcome: bool = False) -> None:
    directory = root / "journal" / "ai-markets"
    directory.mkdir(parents=True, exist_ok=True)
    outcome_text = "Confirmed by user note." if outcome else ""
    (directory / filename).write_text(
        "---\n"
        "domain: ai_markets\n"
        "entry_type: thesis_review\n"
        f"title: {title}\n"
        f"status: {status}\n"
        "created_at: 2026-07-07\n"
        f"review_at: {review_at}\n"
        "related_themes:\n"
        "  - AI Infrastructure\n"
        "related_entities:\n"
        "  - NVDA\n"
        "related_catalysts:\n"
        "  - earnings\n"
        "related_risks:\n"
        "  - risk\n"
        "decision_type: research_review\n"
        "confidence: medium\n"
        "---\n\n"
        "## Decision / Review\n\nReview AI Infrastructure.\n\n"
        "## Rationale\n\nEvidence increased.\n\n"
        "## Uncertainties\n\nPower remains a risk.\n\n"
        "## Follow-Up\n\nReview later.\n\n"
        f"## Outcome\n\n{outcome_text}\n\n"
        "## Lessons\n\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
