from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from constellation.canonical_assignments import CanonicalAssignmentEngine, CanonicalAssignmentError
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

    def make_scoped_migration_fixture(self) -> dict[str, Path]:
        self.import_file("ready-a.json", {"order_id": "READY-1", "subject_address": "100 Ready Street"})
        self.import_file("ready-b.json", {"order_id": "READY-2", "subject_address": "200 Ready Street"})
        self.import_file("ready-c.json", {"order_id": "READY-3", "subject_address": "300 Ready Street"})
        self.import_file("blocked-a.json", {"order_id": "BLOCKED-1", "subject_address": "400 Blocked Street"})
        self.import_file("blocked-b.json", {"order_id": "BLOCKED-1", "subject_address": "401 Blocked Street"})
        ready_one = self.create_alias_directory("100-ready-st", "100 Ready St", extra_file=False)
        ready_two = self.create_alias_directory("200-ready-st", "200 Ready St", extra_file=False)
        ready_three = self.create_alias_directory("300-ready-st", "300 Ready St", extra_file=False)
        blocked = self.create_alias_directory("400-blocked-st", "400 Blocked St", extra_file=False)
        orphan = self.create_alias_directory("orphan-assignment", "999 Orphan Road", extra_file=False)
        migrated = self.create_alias_directory("100-ready-street", "100 Ready Street", extra_file=False)
        write_json(migrated / "canonical-migration.json", {"status": "migrated_alias_directory"})
        return {
            "ready_one": ready_one,
            "ready_two": ready_two,
            "ready_three": ready_three,
            "blocked": blocked,
            "orphan": orphan,
            "migrated": migrated,
        }

    def test_migrate_help_shows_scope_flags(self) -> None:
        output = io.StringIO()
        with self.assertRaises(SystemExit) as cm, contextlib.redirect_stdout(output):
            main(["real-estate", "--root", str(self.root), "canonical", "migrate", "--help"])
        self.assertEqual(cm.exception.code, 0)
        text = output.getvalue()
        for flag in ["--ready-only", "--category", "--assignment", "--source-assignment", "--list-selected"]:
            self.assertIn(flag, text)

    def test_ready_only_selection_excludes_blocked_orphan_and_already_migrated(self) -> None:
        self.make_scoped_migration_fixture()
        engine = CanonicalAssignmentEngine(self.root)
        selection = engine.select_migration_entries(ready_only=True)

        self.assertEqual(selection.counts["selected_count"], 3)
        self.assertTrue(all(item["migration_category"] == "preserve_alias" for item in selection.selected_entries))
        skipped_categories = {item["migration_category"] for item in selection.skipped_entries}
        self.assertIn("blocked_by_conflict", skipped_categories)
        self.assertIn("orphan", skipped_categories)
        self.assertIn("already_migrated", skipped_categories)

    def test_category_assignment_source_and_list_selected_scopes(self) -> None:
        self.make_scoped_migration_fixture()
        engine = CanonicalAssignmentEngine(self.root)

        by_category = engine.select_migration_entries(category="preserve_alias")
        self.assertEqual(by_category.counts["selected_count"], 3)

        by_assignment = engine.select_migration_entries(canonical_assignment_id="100-ready-st")
        self.assertGreaterEqual(by_assignment.counts["selected_count"], 1)
        self.assertTrue(all(item["target_canonical_assignment_id"] == "ready-1" for item in by_assignment.selected_entries))

        by_source = engine.select_migration_entries(source_assignment_id="200-ready-st")
        self.assertEqual(by_source.counts["selected_count"], 1)
        self.assertEqual(by_source.selected_entries[0]["source_assignment_id"], "200-ready-st")

        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            code = main(["real-estate", "--root", str(self.root), "canonical", "migrate", "--ready-only", "--list-selected"])
        self.assertEqual(code, 0, output.getvalue())
        self.assertIn("100-ready-st -> ready-1", output.getvalue())
        self.assertFalse((self.root / "real-estate" / "assignments" / "100-ready-st" / "canonical-migration.json").exists())

    def test_invalid_category_and_ambiguous_assignment_scope_fail_safely(self) -> None:
        self.import_file("amb-a.json", {"order_id": "AMB-1", "subject_address": "1 Ambiguous Street"})
        self.import_file("amb-b.json", {"order_id": "AMB-2", "subject_address": "1 Ambiguous Street"})
        with self.assertRaises(CanonicalAssignmentError):
            CanonicalAssignmentEngine(self.root).select_migration_entries(category="not_a_category")
        with self.assertRaises(CanonicalAssignmentError):
            CanonicalAssignmentEngine(self.root).select_migration_entries(canonical_assignment_id="1-ambiguous-st")

    def test_unscoped_mixed_apply_is_refused_and_dry_run_does_not_modify_files(self) -> None:
        paths = self.make_scoped_migration_fixture()
        engine = CanonicalAssignmentEngine(self.root)
        dry_run = engine.migrate(apply=False, ready_only=True)
        self.assertFalse(dry_run.applied)
        self.assertFalse((paths["ready_one"] / "canonical-migration.json").exists())

        result = engine.migrate(apply=True)
        self.assertFalse(result.applied)
        self.assertIn("refused", result.error.lower())
        self.assertFalse((paths["ready_one"] / "canonical-migration.json").exists())
        self.assertTrue((self.root / "outputs" / "real-estate" / "canonical" / "scoped-migration-selection.json").exists())
        self.assertTrue((self.root / "outputs" / "real-estate" / "canonical" / "scoped-migration-result.md").exists())

    def test_ready_only_apply_is_safe_idempotent_and_synchronizes_state(self) -> None:
        paths = self.make_scoped_migration_fixture()
        engine = CanonicalAssignmentEngine(self.root)

        result = engine.migrate(apply=True, ready_only=True)
        self.assertTrue(result.applied)
        self.assertEqual(result.applied_count, 3)
        self.assertEqual(result.remaining_blocked_count, 1)
        self.assertEqual(result.remaining_orphan_count, 1)
        self.assertTrue(Path(result.backup_manifest_path).exists())
        self.assertTrue((paths["ready_one"] / "canonical-migration.json").exists())
        self.assertTrue(paths["ready_one"].exists())
        self.assertFalse((paths["blocked"] / "canonical-migration.json").exists())
        self.assertFalse((paths["orphan"] / "canonical-migration.json").exists())

        status = CanonicalOperationsEngine(self.root).status()
        dashboard = ExecutiveDashboardBuilder(self.root).build().real_estate_assignment_summary
        self.assertEqual(status["pending_migration_count"], dashboard["pending_migration_count"])
        self.assertEqual(status["migration_ready_count"], dashboard["migration_ready_count"])

        second = engine.migrate(apply=True, ready_only=True)
        self.assertFalse(second.applied)
        self.assertEqual(second.applied_count, 0)
        self.assertEqual(second.already_migrated_count, 4)

    def test_blocked_orphan_ambiguous_and_already_migrated_are_never_applied_by_category(self) -> None:
        paths = self.make_scoped_migration_fixture()
        engine = CanonicalAssignmentEngine(self.root)
        for category, path_key in [("blocked_by_conflict", "blocked"), ("orphan", "orphan"), ("already_migrated", "migrated")]:
            result = engine.migrate(apply=True, category=category)
            self.assertFalse(result.applied)
            self.assertEqual(result.applied_count, 0)
            if category != "already_migrated":
                self.assertFalse((paths[path_key] / "canonical-migration.json").exists())


if __name__ == "__main__":
    unittest.main()
