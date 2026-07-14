from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from constellation.canonical_assignments import (
    CanonicalAssignmentEngine,
    CanonicalAssignmentResolver,
    normalize_address,
    normalize_date,
    normalize_path,
    postal_codes_compatible,
)
from constellation.cli import main
from constellation.dashboard import ExecutiveDashboardBuilder
from constellation.real_estate_intake import RealEstateIntakeEngine


def setup_root(root: Path, intake_root: Path) -> None:
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "config" / "real-estate-assignment.example.yaml").write_text("real_estate_assignment:\n  default_root: real-estate/assignments\n", encoding="utf-8")
    (root / "config" / "real-estate-intake.local.yaml").write_text(
        "real_estate_intake:\n"
        "  enabled: true\n"
        "  assignment_root: real-estate/assignments\n"
        "  source_mode: reference\n"
        "  sources:\n"
        "    - id: canonical_test\n"
        "      enabled: true\n"
        "      source_type: local_directory\n"
        f"      root_path: {intake_root.as_posix()}\n"
        "      include_patterns:\n"
        "        - incoming/*.json\n"
        "        - incoming/*.md\n"
        "      archive_processed: false\n",
        encoding="utf-8",
    )


def write_json(path: Path, data: dict) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return path


class CanonicalAssignmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name) / "repo"
        self.intake_root = Path(self.tempdir.name) / "intake"
        self.root.mkdir()
        setup_root(self.root, self.intake_root)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def import_file(self, name: str, data: dict) -> Path:
        path = write_json(self.intake_root / "incoming" / name, data)
        result = RealEstateIntakeEngine(self.root).import_candidates(file_path=path)
        self.assertEqual(result.manifest.counts["errors"], 0, result.to_dict())
        return path

    def test_normalization_helpers(self) -> None:
        self.assertEqual(normalize_address("&nbsp;430 S Rodeo Drive #312"), "430 s rodeo dr unit 312")
        self.assertEqual(normalize_address("430 S Rodeo Dr Unit 312"), "430 s rodeo dr unit 312")
        self.assertEqual(normalize_date("07/13/2026"), "2026-07-13")
        self.assertEqual(normalize_date("2026-07-13T09:00:00"), "2026-07-13")
        self.assertTrue(postal_codes_compatible("90212", "90212-4220"))
        self.assertEqual(normalize_path(r"C:\\Users\\Test\\file.md"), r"C:\Users\Test\file.md")

    def test_clean_import_creates_one_canonical_directory_per_order(self) -> None:
        self.import_file("gmail-laurel.json", {"source_type": "gmail", "order_id": "2617501513", "subject_address": "524 Laurel Avenue"})
        self.import_file("axis-laurel.json", {"source_type": "axis", "subject_address": "524 Laurel Ave"})
        snapshot = CanonicalAssignmentEngine(self.root).build()
        self.assertEqual(snapshot.counts["canonical_assignment_count"], 1)
        self.assertTrue((self.root / "real-estate" / "assignments" / "2617501513").exists())
        self.assertFalse((self.root / "real-estate" / "assignments" / "524-laurel-ave").exists())

    def test_alias_resolution_for_source_generated_and_address_alias(self) -> None:
        self.import_file("gmail-laurel.json", {"source_type": "gmail", "order_id": "2617501513", "subject_address": "524 Laurel Avenue"})
        CanonicalAssignmentEngine(self.root).build()
        resolver = CanonicalAssignmentResolver(self.root)
        self.assertEqual(resolver.resolve("2617501513").canonical_assignment_id, "2617501513")
        self.assertEqual(resolver.resolve("524-laurel-ave").canonical_assignment_id, "2617501513")

    def test_cazador_address_alias_resolves_to_dated_canonical(self) -> None:
        self.import_file("gmail-cazador.json", {"source_type": "gmail", "subject_address": "3770 Cazador St", "effective_date": "7/17/2026"})
        CanonicalAssignmentEngine(self.root).build()
        resolution = CanonicalAssignmentResolver(self.root).resolve("3770-cazador-st")
        self.assertTrue(resolution.resolved)
        self.assertEqual(resolution.canonical_assignment_id, "3770-cazador-st-2026-07-17")

    def test_html_address_and_equivalent_dates_do_not_conflict(self) -> None:
        self.import_file("clean.json", {"order_id": "RODEO-1", "subject_address": "430 S Rodeo Dr", "effective_date": "07/13/2026"})
        self.import_file("html.json", {"source_type": "gmail", "subject_address": "&nbsp;430 S Rodeo Dr", "effective_date": "2026-07-13"})
        snapshot = CanonicalAssignmentEngine(self.root).build()
        self.assertEqual(snapshot.counts["canonical_assignment_count"], 1)
        self.assertEqual(snapshot.counts["true_assignment_conflict_count"], 0)

    def test_different_units_remain_separate(self) -> None:
        self.import_file("u209.json", {"subject_address": "12222 Wilshire Blvd Unit 209"})
        self.import_file("u307.json", {"subject_address": "12222 Wilshire Blvd #307"})
        snapshot = CanonicalAssignmentEngine(self.root).build()
        self.assertEqual(snapshot.counts["canonical_assignment_count"], 2)

    def test_ambiguous_alias_does_not_guess(self) -> None:
        self.import_file("a.json", {"order_id": "A1", "subject_address": "1 Alpha Street"})
        self.import_file("b.json", {"order_id": "B1", "subject_address": "1 Alpha Street"})
        CanonicalAssignmentEngine(self.root).build()
        resolution = CanonicalAssignmentResolver(self.root).resolve("1-alpha-st")
        self.assertTrue(resolution.ambiguous)
        self.assertFalse(resolution.resolved)

    def test_migration_dry_run_and_apply_are_non_destructive(self) -> None:
        self.import_file("canonical.json", {"order_id": "ORDER-1", "subject_address": "100 Main Street"})
        alias_dir = self.root / "real-estate" / "assignments" / "100-main-st"
        alias_dir.mkdir(parents=True)
        (alias_dir / "assignment.yaml").write_text("assignment:\n  assignment_id: 100-main-st\n  status: intake\n  subject:\n    address: 100 Main St\n", encoding="utf-8")
        engine = CanonicalAssignmentEngine(self.root)
        engine.build()
        plan = engine.migration_plan()
        self.assertGreaterEqual(plan.counts["pending_migration_count"], 1)
        self.assertTrue(alias_dir.exists())
        result = engine.migrate(apply=True)
        self.assertTrue(result.applied)
        self.assertTrue((alias_dir / "canonical-migration.json").exists())
        self.assertTrue(alias_dir.exists())

    def test_assignment_cli_resolves_alias_and_open_is_non_fatal(self) -> None:
        self.import_file("gmail-cazador.json", {"source_type": "gmail", "subject_address": "3770 Cazador St", "effective_date": "7/17/2026"})
        CanonicalAssignmentEngine(self.root).build()
        with patch("constellation.cli.subprocess.run", side_effect=OSError("no code")):
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = main(["real-estate", "--root", str(self.root), "assignment", "show", "3770-cazador-st", "--open"])
        self.assertEqual(code, 0, buffer.getvalue())
        self.assertIn("canonical_assignment_id: 3770-cazador-st-2026-07-17", buffer.getvalue())

    def test_assignments_list_is_canonical_only_with_optional_aliases(self) -> None:
        self.import_file("gmail-laurel.json", {"source_type": "gmail", "order_id": "2617501513", "subject_address": "524 Laurel Avenue"})
        self.import_file("axis-laurel.json", {"source_type": "axis", "subject_address": "524 Laurel Ave"})
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = main(["real-estate", "--root", str(self.root), "assignments", "--include-aliases"])
        self.assertEqual(code, 0, buffer.getvalue())
        self.assertEqual(buffer.getvalue().count("2617501513 status="), 1)
        self.assertIn("alias:", buffer.getvalue())

    def test_dashboard_uses_canonical_counts(self) -> None:
        self.import_file("a.json", {"order_id": "DASH-1", "subject_address": "10 Dashboard Street"})
        self.import_file("b.json", {"source_type": "gmail", "subject_address": "10 Dashboard St"})
        summary = ExecutiveDashboardBuilder(self.root).build().real_estate_assignment_summary
        self.assertEqual(summary["canonical_assignment_count"], 1)
        self.assertEqual(summary["artifact_count"], 2)
        self.assertGreater(summary["alias_count"], 0)

    def test_canonical_cli_commands(self) -> None:
        self.import_file("order.json", {"order_id": "CLI-200", "subject_address": "200 CLI Street"})
        commands = [
            ["real-estate", "--root", str(self.root), "canonical", "status"],
            ["real-estate", "--root", str(self.root), "canonical", "assignments"],
            ["real-estate", "--root", str(self.root), "canonical", "aliases"],
            ["real-estate", "--root", str(self.root), "canonical", "resolve", "CLI-200"],
            ["real-estate", "--root", str(self.root), "canonical", "migration-plan"],
            ["real-estate", "--root", str(self.root), "canonical", "migrate", "--dry-run"],
            ["real-estate", "--root", str(self.root), "canonical", "export"],
        ]
        for command in commands:
            with self.subTest(command=command):
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    code = main(command)
                self.assertEqual(code, 0, buffer.getvalue())

    def test_no_provider_external_calls_or_valuation_conclusions(self) -> None:
        self.import_file("safe.json", {"order_id": "SAFE-1", "subject_address": "1 Safe Street"})
        with patch("subprocess.run") as runner:
            snapshot = CanonicalAssignmentEngine(self.root).build()
        runner.assert_not_called()
        report = (self.root / "outputs" / "real-estate" / "canonical" / "canonical-assignment-report.md").read_text(encoding="utf-8").lower()
        for phrase in ["opinion of value", "recommended comparable", "adjustment amount", "uspap compliant opinion"]:
            self.assertNotIn(phrase, report)
        self.assertEqual(snapshot.counts["canonical_assignment_count"], 1)


if __name__ == "__main__":
    unittest.main()
