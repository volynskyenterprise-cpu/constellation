from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from constellation.canonical_assignments import CanonicalAssignmentEngine
from constellation.canonical_operations import CanonicalOperationsEngine, CanonicalOperationsStore
from constellation.cli import main
from constellation.dashboard import ExecutiveDashboardBuilder
from constellation.real_estate_intake import RealEstateIntakeEngine


def setup_root(root: Path, intake_root: Path) -> None:
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "config" / "real-estate-assignment.example.yaml").write_text(
        "real_estate_assignment:\n  default_root: real-estate/assignments\n",
        encoding="utf-8",
    )
    (root / "config" / "real-estate-intake.local.yaml").write_text(
        "real_estate_intake:\n"
        "  enabled: true\n"
        "  assignment_root: real-estate/assignments\n"
        "  source_mode: reference\n"
        "  sources:\n"
        "    - id: canonical_operations_test\n"
        "      enabled: true\n"
        "      source_type: local_directory\n"
        f"      root_path: {intake_root.as_posix()}\n"
        "      include_patterns:\n"
        "        - incoming/*.json\n"
        "      archive_processed: false\n",
        encoding="utf-8",
    )


def write_json(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return path


class CanonicalOperationsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name) / "repo"
        self.intake_root = Path(self.tempdir.name) / "intake"
        self.root.mkdir()
        setup_root(self.root, self.intake_root)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def import_file(self, name: str, data: dict) -> None:
        path = write_json(self.intake_root / "incoming" / name, data)
        result = RealEstateIntakeEngine(self.root).import_candidates(file_path=path)
        self.assertEqual(result.manifest.counts["errors"], 0, result.to_dict())

    def create_alias_directory(self, assignment_id: str, address: str, *, extra_file: bool = True) -> Path:
        directory = self.root / "real-estate" / "assignments" / assignment_id
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "assignment.yaml").write_text(
            "assignment:\n"
            f"  assignment_id: {assignment_id}\n"
            "  status: intake\n"
            "  subject:\n"
            f"    address: {address}\n",
            encoding="utf-8",
        )
        if extra_file:
            (directory / "source-note.md").write_text("source artifact", encoding="utf-8")
        return directory

    def test_migration_state_synchronized_across_status_plan_and_dashboard(self) -> None:
        self.import_file("canonical.json", {"order_id": "SYNC-1", "subject_address": "100 Sync Street"})
        self.create_alias_directory("100-sync-st", "100 Sync St")

        state = CanonicalOperationsEngine(self.root).build()
        status = CanonicalOperationsEngine(self.root).status()
        plan = CanonicalAssignmentEngine(self.root).migration_plan()
        dashboard = ExecutiveDashboardBuilder(self.root).build().real_estate_assignment_summary

        self.assertEqual(state.summary["pending_migration_count"], plan.counts["pending_migration_count"])
        self.assertEqual(status["pending_migration_count"], plan.counts["pending_migration_count"])
        self.assertEqual(dashboard["pending_migration_count"], plan.counts["pending_migration_count"])
        self.assertEqual(state.migration_summary["safe_merge_count"], 1)

    def test_review_queue_and_operations_outputs_are_written(self) -> None:
        self.import_file("canonical.json", {"order_id": "REVIEW-1", "subject_address": "200 Review Street"})
        self.create_alias_directory("review-orphan", "999 Unknown Road")

        state = CanonicalOperationsEngine(self.root).build()
        store = CanonicalOperationsStore(self.root)

        self.assertGreaterEqual(state.summary["pending_review_count"], 1)
        self.assertTrue(store.review_queue_md.exists())
        self.assertTrue(store.operations_report_md.exists())
        self.assertTrue(store.migration_summary_json.exists())
        self.assertIn("unassigned_artifact", store.review_queue_md.read_text(encoding="utf-8"))

    def test_migration_summary_categories_are_exactly_one_per_item(self) -> None:
        self.import_file("safe.json", {"order_id": "SAFE-1", "subject_address": "300 Safe Street"})
        self.create_alias_directory("300-safe-st", "300 Safe St")
        self.create_alias_directory("unknown-alias", "404 Missing Place", extra_file=False)

        state = CanonicalOperationsEngine(self.root).build()
        categories = [item["migration_category"] for item in state.migration_summary["items"]]

        self.assertIn("safe_merge", categories)
        self.assertIn("orphan", categories)
        self.assertTrue(all(category in {"safe_merge", "preserve_alias", "blocked_by_conflict", "ambiguous", "orphan", "already_migrated"} for category in categories))
        self.assertEqual(len(categories), len(state.migration_summary["items"]))

    def test_blocked_and_ambiguous_reporting(self) -> None:
        self.import_file("conflict-a.json", {"order_id": "BLOCK-1", "subject_address": "400 Block Street"})
        self.import_file("conflict-b.json", {"order_id": "BLOCK-1", "subject_address": "401 Block Street"})
        self.create_alias_directory("400-block-st", "400 Block St")
        self.import_file("amb-a.json", {"order_id": "AMB-A", "subject_address": "500 Ambiguous Street"})
        self.import_file("amb-b.json", {"order_id": "AMB-B", "subject_address": "500 Ambiguous Street"})
        self.create_alias_directory("500-ambiguous-st", "500 Ambiguous St")

        state = CanonicalOperationsEngine(self.root).build()

        self.assertGreaterEqual(state.summary["blocked_count"], 1)
        self.assertGreaterEqual(state.summary["ambiguous_count"], 1)
        self.assertTrue(any(item["category"] == "migration_blocked" for item in state.review_queue))
        self.assertTrue(any(item["category"] == "ambiguous_alias" for item in state.review_queue))

    def test_cli_review_operations_report_conflicts_and_migration_summary(self) -> None:
        self.import_file("cli.json", {"order_id": "CLI-OPS", "subject_address": "600 CLI Street"})
        self.create_alias_directory("600-cli-st", "600 CLI St")
        commands = [
            ["real-estate", "--root", str(self.root), "canonical", "status"],
            ["real-estate", "--root", str(self.root), "canonical", "review"],
            ["real-estate", "--root", str(self.root), "canonical", "review", "--safe"],
            ["real-estate", "--root", str(self.root), "canonical", "review", "--blocked"],
            ["real-estate", "--root", str(self.root), "canonical", "review", "--ambiguous"],
            ["real-estate", "--root", str(self.root), "canonical", "operations"],
            ["real-estate", "--root", str(self.root), "canonical", "report"],
            ["real-estate", "--root", str(self.root), "canonical", "conflicts"],
            ["real-estate", "--root", str(self.root), "canonical", "migration-plan"],
        ]
        for command in commands:
            with self.subTest(command=command):
                output = io.StringIO()
                with contextlib.redirect_stdout(output):
                    code = main(command)
                self.assertEqual(code, 0, output.getvalue())

    def test_deterministic_repeated_runs_ignore_timestamps(self) -> None:
        self.import_file("det.json", {"order_id": "DET-1", "subject_address": "700 Deterministic Street"})
        self.create_alias_directory("700-deterministic-st", "700 Deterministic St")

        first = CanonicalOperationsEngine(self.root).build().to_dict()
        second = CanonicalOperationsEngine(self.root).build().to_dict()
        for data in [first, second]:
            data.pop("created_at", None)
            data.pop("state_id", None)

        self.assertEqual(first, second)

    def test_no_provider_external_calls_or_valuation_conclusions(self) -> None:
        self.import_file("safe.json", {"order_id": "NOAI-1", "subject_address": "800 No AI Street"})
        with patch("subprocess.run") as runner:
            state = CanonicalOperationsEngine(self.root).build()
        runner.assert_not_called()
        report = CanonicalOperationsStore(self.root).operations_report_md.read_text(encoding="utf-8").lower()
        for phrase in ["opinion of value", "price target", "recommended comparable", "adjustment amount", "uspap conclusion"]:
            self.assertNotIn(phrase, report)
        self.assertEqual(state.summary["canonical_assignment_count"], 1)


if __name__ == "__main__":
    unittest.main()
