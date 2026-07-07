from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

from constellation.ai_markets import AIMarketsStore, _normalize_question
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


if __name__ == "__main__":
    unittest.main()
