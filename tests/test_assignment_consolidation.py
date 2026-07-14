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


if __name__ == "__main__":
    unittest.main()
