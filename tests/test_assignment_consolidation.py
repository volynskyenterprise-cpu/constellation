from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from constellation.assignment_consolidation import AssignmentConsolidationEngine, normalize_address
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
        "    - id: test_source\n"
        "      enabled: true\n"
        "      source_type: local_directory\n"
        f"      root_path: {intake_root.as_posix()}\n"
        "      include_patterns:\n"
        "        - incoming/*.json\n"
        "        - incoming/*.md\n"
        "      archive_processed: false\n",
        encoding="utf-8",
    )


def write_artifacts(intake_root: Path, *, conflict: bool = False) -> list[Path]:
    incoming = intake_root / "incoming"
    incoming.mkdir(parents=True, exist_ok=True)
    files = []
    records = [
        ("gmail-order.json", {"source_type": "gmail", "order_id": "ORDER-1", "subject_address": "123 Example Street", "city": "Los Angeles", "state": "CA", "client_name": "Client A"}),
        ("axis-order.json", {"source_type": "axis", "order_id": "ORDER-1", "subject_address": "123 Example St.", "city": "Los Angeles", "state": "CA", "lender": "Lender A"}),
        ("knowledge-pack.json", {"source_type": "knowledge_pack", "order_id": "ORDER-1", "subject_address": "123 Example Street", "city": "Los Angeles", "state": "CA"}),
    ]
    if conflict:
        records.append(("review.json", {"source_type": "review", "order_id": "ORDER-1", "subject_address": "999 Conflict Road", "city": "Los Angeles", "state": "CA"}))
    else:
        records.append(("review.md", {"order_id": "ORDER-1", "subject_address": "123 Example Street", "city": "Los Angeles", "state": "CA"}))
    for name, data in records:
        path = incoming / name
        if path.suffix == ".json":
            path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        else:
            path.write_text("\n".join(f"{key}: {value}" for key, value in data.items()), encoding="utf-8")
        files.append(path)
    return files


def write_json_artifact(intake_root: Path, name: str, data: dict) -> Path:
    path = intake_root / "incoming" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return path


def write_md_artifact(intake_root: Path, name: str, data: dict | None = None) -> Path:
    path = intake_root / "incoming" / name
    path.parent.mkdir(parents=True, exist_ok=True)
    if data is None:
        path.write_text("# Review\n\nNo structured assignment fields.\n", encoding="utf-8")
    else:
        path.write_text("\n".join(f"{key}: {value}" for key, value in data.items()), encoding="utf-8")
    return path


class AssignmentConsolidationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name) / "repo"
        self.intake_root = Path(self.tempdir.name) / "intake"
        self.root.mkdir()
        setup_root(self.root, self.intake_root)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_address_normalization(self) -> None:
        self.assertEqual(normalize_address("123 Example Street, Unit 4"), "123 example st unit 4")
        self.assertEqual(normalize_address("123 Example St."), "123 example st")
        self.assertEqual(normalize_address("&nbsp;&nbsp;&nbsp;430 S Rodeo Dr &nbsp; &nbsp;"), "430 s rodeo dr")
        self.assertEqual(normalize_address("12222 Wilshire Blvd #312"), "12222 wilshire blvd unit 312")
        self.assertEqual(normalize_address("12222 Wilshire Boulevard Apt 312"), "12222 wilshire blvd unit 312")

    def test_assignment_clustering_and_duplicate_grouping(self) -> None:
        for path in write_artifacts(self.intake_root):
            RealEstateIntakeEngine(self.root).import_candidates(file_path=path)
        snapshot = AssignmentConsolidationEngine(self.root).build()
        self.assertEqual(snapshot.counts["artifact_count"], 4)
        self.assertEqual(snapshot.counts["assignment_count"], 1)
        self.assertEqual(snapshot.clusters[0].artifact_count, 4)

    def test_relationship_generation(self) -> None:
        for path in write_artifacts(self.intake_root):
            RealEstateIntakeEngine(self.root).import_candidates(file_path=path)
        snapshot = AssignmentConsolidationEngine(self.root).build()
        self.assertGreaterEqual(snapshot.counts["relationship_count"], 3)
        self.assertTrue(all(item.relationship_type in {"same_assignment", "possible_duplicate"} for item in snapshot.relationships))

    def test_conflict_detection(self) -> None:
        for path in write_artifacts(self.intake_root, conflict=True):
            RealEstateIntakeEngine(self.root).import_candidates(file_path=path)
        snapshot = AssignmentConsolidationEngine(self.root).build()
        self.assertEqual(snapshot.counts["assignment_count"], 1)
        self.assertGreater(snapshot.counts["conflict_count"], 0)
        self.assertIn("property_address", {item["field"] for item in snapshot.conflicts})

    def test_canonical_assignment_selection(self) -> None:
        for path in write_artifacts(self.intake_root):
            RealEstateIntakeEngine(self.root).import_candidates(file_path=path)
        snapshot = AssignmentConsolidationEngine(self.root).build()
        self.assertEqual(snapshot.clusters[0].canonical_assignment_id, "order-1")

    def test_dashboard_summary(self) -> None:
        for path in write_artifacts(self.intake_root):
            RealEstateIntakeEngine(self.root).import_candidates(file_path=path)
        AssignmentConsolidationEngine(self.root).build()
        dashboard = ExecutiveDashboardBuilder(self.root).build()
        summary = dashboard.real_estate_assignment_summary
        self.assertEqual(summary["consolidated_assignment_count"], 1)
        self.assertEqual(summary["consolidated_artifact_count"], 4)
        self.assertEqual(summary["consolidated_knowledge_pack_count"], 1)

    def test_deterministic_repeated_runs(self) -> None:
        for path in write_artifacts(self.intake_root):
            RealEstateIntakeEngine(self.root).import_candidates(file_path=path)
        first = AssignmentConsolidationEngine(self.root).build().snapshot_id
        second = AssignmentConsolidationEngine(self.root).build().snapshot_id
        self.assertEqual(first, second)

    def test_no_semantic_matching(self) -> None:
        incoming = self.intake_root / "incoming"
        incoming.mkdir(parents=True, exist_ok=True)
        (incoming / "a.json").write_text(json.dumps({"order_id": "A1", "subject_address": "1 Alpha Street"}), encoding="utf-8")
        (incoming / "b.json").write_text(json.dumps({"order_id": "B1", "subject_address": "2 Beta Street"}), encoding="utf-8")
        RealEstateIntakeEngine(self.root).import_candidates(file_path=incoming / "a.json")
        RealEstateIntakeEngine(self.root).import_candidates(file_path=incoming / "b.json")
        snapshot = AssignmentConsolidationEngine(self.root).build()
        self.assertEqual(snapshot.counts["assignment_count"], 2)

    def test_cli_commands(self) -> None:
        for path in write_artifacts(self.intake_root):
            RealEstateIntakeEngine(self.root).import_candidates(file_path=path)
        commands = [
            ["real-estate", "--root", str(self.root), "consolidation"],
            ["real-estate", "--root", str(self.root), "consolidation", "status"],
            ["real-estate", "--root", str(self.root), "consolidation", "clusters"],
            ["real-estate", "--root", str(self.root), "consolidation", "relationships"],
            ["real-estate", "--root", str(self.root), "consolidation", "conflicts"],
            ["real-estate", "--root", str(self.root), "consolidation", "export"],
        ]
        for command in commands:
            with self.subTest(command=command):
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    code = main(command)
                self.assertEqual(code, 0, buffer.getvalue())

    def test_no_provider_calls_or_valuation_conclusions(self) -> None:
        for path in write_artifacts(self.intake_root):
            RealEstateIntakeEngine(self.root).import_candidates(file_path=path)
        with patch("subprocess.run") as runner:
            snapshot = AssignmentConsolidationEngine(self.root).build()
        runner.assert_not_called()
        text = (self.root / "outputs" / "real-estate" / "consolidation" / "assignment-clusters.md").read_text(encoding="utf-8").lower()
        for phrase in ["opinion of value", "recommended comparable", "adjustment amount", "uspap compliant opinion"]:
            self.assertNotIn(phrase, text)
        self.assertEqual(snapshot.counts["artifact_count"], 4)

    def test_html_entity_cleanup_suppresses_false_address_conflict(self) -> None:
        paths = [
            write_json_artifact(self.intake_root, "clean.json", {"order_id": "RODEO-1", "subject_address": "430 S Rodeo Dr", "city": "Beverly Hills", "state": "CA"}),
            write_json_artifact(self.intake_root, "html.json", {"source_type": "gmail", "subject_address": "&nbsp;&nbsp;430 S Rodeo Dr&nbsp;", "city": "Beverly Hills", "state": "CA"}),
        ]
        for path in paths:
            RealEstateIntakeEngine(self.root).import_candidates(file_path=path)
        snapshot = AssignmentConsolidationEngine(self.root).build()
        self.assertEqual(snapshot.counts["assignment_count"], 1)
        self.assertEqual(snapshot.counts["true_identity_conflict_count"], 0)

    def test_exact_json_markdown_basename_pairing_and_empty_markdown_attached(self) -> None:
        paths = [
            write_json_artifact(self.intake_root, "gmail-abc123.json", {"source_type": "gmail", "order_id": "PAIR-1", "subject_address": "10 Paired Street"}),
            write_md_artifact(self.intake_root, "gmail-abc123.md"),
        ]
        for path in paths:
            RealEstateIntakeEngine(self.root).import_candidates(file_path=path)
        snapshot = AssignmentConsolidationEngine(self.root).build()
        self.assertEqual(snapshot.counts["assignment_count"], 1)
        self.assertEqual(snapshot.counts["artifact_count"], 2)
        self.assertEqual(snapshot.counts["source_companion_count"], 1)
        self.assertEqual(snapshot.counts["unassigned_artifact_count"], 0)
        self.assertIn("source_companion", {item.relationship_type for item in snapshot.relationships})

    def test_unpaired_empty_markdown_becomes_unassigned(self) -> None:
        path = write_md_artifact(self.intake_root, "lonely-review.md")
        RealEstateIntakeEngine(self.root).import_candidates(file_path=path)
        snapshot = AssignmentConsolidationEngine(self.root).build()
        self.assertEqual(snapshot.counts["assignment_count"], 0)
        self.assertEqual(snapshot.counts["unassigned_artifact_count"], 1)

    def test_source_generated_gmail_and_axis_ids_are_aliases_not_conflicts(self) -> None:
        paths = [
            write_json_artifact(self.intake_root, "gmail-laurel.json", {"source_type": "gmail", "subject_address": "524 Laurel Avenue", "city": "Los Angeles", "state": "CA"}),
            write_json_artifact(self.intake_root, "axis-laurel.json", {"source_type": "axis", "order_id": "524-LAUREL", "subject_address": "524 Laurel Ave", "city": "Los Angeles", "state": "CA"}),
        ]
        for path in paths:
            RealEstateIntakeEngine(self.root).import_candidates(file_path=path)
        snapshot = AssignmentConsolidationEngine(self.root).build()
        cluster = snapshot.clusters[0]
        self.assertEqual(snapshot.counts["assignment_count"], 1)
        self.assertGreater(snapshot.counts["alias_count"], 0)
        self.assertEqual(snapshot.counts["true_identity_conflict_count"], 0)
        self.assertIn("524-laurel", cluster.source_generated_ids)

    def test_address_derived_alias_preserved(self) -> None:
        path = write_json_artifact(self.intake_root, "gmail-cazador.json", {"source_type": "gmail", "subject_address": "3770 Cazador St", "effective_date": "2026-07-14"})
        RealEstateIntakeEngine(self.root).import_candidates(file_path=path)
        snapshot = AssignmentConsolidationEngine(self.root).build()
        self.assertTrue(snapshot.clusters[0].assignment_aliases)
        self.assertIn("3770-cazador-st-2026-07-14", snapshot.clusters[0].assignment_aliases)

    def test_explicit_identifier_priority(self) -> None:
        cases = [
            ("explicit-assignment.json", {"assignment_id": "ASSIGN-9", "order_id": "ORDER-9", "loan_number": "LOAN-9"}, "assign-9"),
            ("explicit-order.json", {"order_id": "ORDER-10", "loan_number": "LOAN-10"}, "order-10"),
            ("explicit-loan.json", {"loan_number": "LOAN-11"}, "loan-11"),
        ]
        for filename, data, expected in cases:
            with self.subTest(filename=filename):
                self.tearDown()
                self.setUp()
                path = write_json_artifact(self.intake_root, filename, data)
                RealEstateIntakeEngine(self.root).import_candidates(file_path=path)
                snapshot = AssignmentConsolidationEngine(self.root).build()
                self.assertEqual(snapshot.clusters[0].canonical_assignment_id, expected)

    def test_true_explicit_order_conflict_retained(self) -> None:
        paths = [
            write_json_artifact(self.intake_root, "a.json", {"order_id": "ORDER-A", "subject_address": "100 Conflict Street"}),
            write_json_artifact(self.intake_root, "b.json", {"order_id": "ORDER-B", "subject_address": "100 Conflict Street"}),
        ]
        for path in paths:
            RealEstateIntakeEngine(self.root).import_candidates(file_path=path)
        snapshot = AssignmentConsolidationEngine(self.root).build()
        self.assertEqual(snapshot.counts["assignment_count"], 2)
        self.assertGreaterEqual(len([r for r in snapshot.relationships if r.relationship_type == "conflicting_assignment"]), 1)

    def test_true_explicit_loan_conflict_retained(self) -> None:
        paths = [
            write_json_artifact(self.intake_root, "a.json", {"loan_number": "LOAN-A", "subject_address": "101 Conflict Street"}),
            write_json_artifact(self.intake_root, "b.json", {"loan_number": "LOAN-B", "subject_address": "101 Conflict Street"}),
        ]
        for path in paths:
            RealEstateIntakeEngine(self.root).import_candidates(file_path=path)
        snapshot = AssignmentConsolidationEngine(self.root).build()
        self.assertEqual(snapshot.counts["assignment_count"], 2)

    def test_exact_address_merge_with_missing_city_state(self) -> None:
        paths = [
            write_json_artifact(self.intake_root, "a.json", {"subject_address": "652 Broadway", "city": "Santa Monica", "state": "CA"}),
            write_json_artifact(self.intake_root, "b.json", {"source_type": "gmail", "subject_address": "652 Broadway"}),
        ]
        for path in paths:
            RealEstateIntakeEngine(self.root).import_candidates(file_path=path)
        self.assertEqual(AssignmentConsolidationEngine(self.root).build().counts["assignment_count"], 1)

    def test_different_units_remain_separate(self) -> None:
        paths = [
            write_json_artifact(self.intake_root, "u209.json", {"subject_address": "12222 Wilshire Blvd Unit 209"}),
            write_json_artifact(self.intake_root, "u307.json", {"subject_address": "12222 Wilshire Blvd #307"}),
        ]
        for path in paths:
            RealEstateIntakeEngine(self.root).import_candidates(file_path=path)
        self.assertEqual(AssignmentConsolidationEngine(self.root).build().counts["assignment_count"], 2)

    def test_alias_and_unassigned_outputs_and_identity_report(self) -> None:
        paths = [
            write_json_artifact(self.intake_root, "gmail-abc.json", {"source_type": "gmail", "order_id": "OUT-1", "subject_address": "20 Output Street"}),
            write_md_artifact(self.intake_root, "orphan.md"),
        ]
        for path in paths:
            RealEstateIntakeEngine(self.root).import_candidates(file_path=path)
        AssignmentConsolidationEngine(self.root).build()
        base = self.root / "outputs" / "real-estate" / "consolidation"
        self.assertTrue((base / "assignment-aliases.json").exists())
        self.assertTrue((base / "unassigned-artifacts.json").exists())
        self.assertTrue((base / "unassigned-artifacts.md").exists())
        self.assertTrue((base / "identity-resolution-report.md").exists())

    def test_dashboard_identity_summary_and_cli_new_commands(self) -> None:
        paths = [
            write_json_artifact(self.intake_root, "gmail-abc123.json", {"source_type": "gmail", "order_id": "CLI-1", "subject_address": "10 CLI Street"}),
            write_md_artifact(self.intake_root, "gmail-abc123.md"),
        ]
        for path in paths:
            RealEstateIntakeEngine(self.root).import_candidates(file_path=path)
        AssignmentConsolidationEngine(self.root).build()
        summary = ExecutiveDashboardBuilder(self.root).build().real_estate_assignment_summary
        self.assertEqual(summary["canonical_assignment_count"], 1)
        self.assertGreater(summary["alias_count"], 0)
        self.assertEqual(summary["source_companion_count"], 1)
        for command in [
            ["real-estate", "--root", str(self.root), "consolidation", "aliases"],
            ["real-estate", "--root", str(self.root), "consolidation", "unassigned"],
            ["real-estate", "--root", str(self.root), "consolidation", "identity-report"],
        ]:
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = main(command)
            self.assertEqual(code, 0, buffer.getvalue())

    def test_history_and_delta_generation(self) -> None:
        path = write_json_artifact(self.intake_root, "a.json", {"order_id": "DELTA-1", "subject_address": "30 Delta Street"})
        RealEstateIntakeEngine(self.root).import_candidates(file_path=path)
        engine = AssignmentConsolidationEngine(self.root)
        first = engine.build()
        second = engine.build()
        self.assertEqual(first.snapshot_id, second.snapshot_id)
        history = json.loads((self.root / "outputs" / "real-estate" / "consolidation" / "assignment-consolidation-history.json").read_text(encoding="utf-8"))
        self.assertEqual(len(history["snapshots"]), 1)
        delta = json.loads((self.root / "outputs" / "real-estate" / "consolidation" / "assignment-consolidation-delta.json").read_text(encoding="utf-8"))
        self.assertIn("newly_resolved_aliases", delta)


if __name__ == "__main__":
    unittest.main()
