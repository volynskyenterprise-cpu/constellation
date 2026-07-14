from __future__ import annotations

import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from constellation.cli import main
from constellation.real_estate import RealEstateAssignmentStore
from constellation.real_estate_intake import RealEstateIntakeEngine, RealEstateIntakeStore


def write_intake_config(root: Path, intake_root: Path, *, enabled: bool = True, source_mode: str = "reference") -> None:
    (root / "config").mkdir(parents=True, exist_ok=True)
    (root / "config" / "real-estate-assignment.example.yaml").write_text(
        "real_estate_assignment:\n"
        "  default_root: real-estate/assignments\n",
        encoding="utf-8",
    )
    (root / "config" / "real-estate-intake.local.yaml").write_text(
        "real_estate_intake:\n"
        "  enabled: true\n"
        "  assignment_root: real-estate/assignments\n"
        f"  source_mode: {source_mode}\n"
        "  sources:\n"
        "    - id: local_test\n"
        f"      enabled: {'true' if enabled else 'false'}\n"
        "      source_type: local_directory\n"
        f"      root_path: {intake_root.as_posix()}\n"
        "      include_patterns:\n"
        "        - incoming/*.json\n"
        "        - incoming/*.yaml\n"
        "        - incoming/*.yml\n"
        "        - incoming/*.md\n"
        "        - incoming/*.txt\n"
        "      archive_processed: false\n",
        encoding="utf-8",
    )


def write_json_intake(path: Path, **overrides) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = {
        "order_id": "ORDER-1001",
        "loan_number": "LN-2002",
        "subject_address": "123 Example Street",
        "city": "Los Angeles",
        "state": "CA",
        "postal_code": "90000",
        "client_name": "Example Client",
        "lender": "Example Lender",
        "amc": "Example AMC",
        "due_date": "2026-07-18",
        "effective_date": "2026-07-14",
        "assignment_type": "appraisal",
        "property_type": "single_family_residential",
        "report_type": "appraisal_report",
        "intended_use": "mortgage_lending",
        "inspection_type": "interior_and_exterior",
        "ownership_interest": "fee_simple",
    }
    data.update(overrides)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return path


class RealEstateIntakeTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name) / "repo"
        self.root.mkdir()
        self.intake_root = Path(self.tempdir.name) / "intake"
        (self.intake_root / "incoming").mkdir(parents=True)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_missing_config_behavior(self) -> None:
        status = RealEstateIntakeEngine(self.root).status()
        self.assertFalse(status["config_available"])
        self.assertEqual(status["detected_candidate_count"], 0)

    def test_disabled_source_behavior(self) -> None:
        write_intake_config(self.root, self.intake_root, enabled=False)
        write_json_intake(self.intake_root / "incoming" / "order.json")
        self.assertEqual(RealEstateIntakeEngine(self.root).scan(), [])

    def test_scan_empty_directory(self) -> None:
        write_intake_config(self.root, self.intake_root)
        self.assertEqual(RealEstateIntakeEngine(self.root).scan(), [])

    def test_json_intake_parsing_and_scan(self) -> None:
        write_intake_config(self.root, self.intake_root)
        write_json_intake(self.intake_root / "incoming" / "order.json")
        candidates = RealEstateIntakeEngine(self.root).scan()
        self.assertEqual(len(candidates), 1)
        self.assertEqual(candidates[0].detected_assignment_id, "order-1001")
        self.assertGreaterEqual(len(candidates[0].field_mappings), 10)

    def test_yaml_intake_parsing(self) -> None:
        write_intake_config(self.root, self.intake_root)
        (self.intake_root / "incoming" / "order.yaml").write_text(
            "order_id: YAML-1001\n"
            "property_address: 456 Example Road\n"
            "zip: \"90001\"\n"
            "client: YAML Client\n"
            "report_due: 2026-07-19\n",
            encoding="utf-8",
        )
        candidate = RealEstateIntakeEngine(self.root).scan()[0]
        self.assertEqual(candidate.detected_assignment_id, "yaml-1001")
        self.assertIn("address", [item.target_field for item in candidate.field_mappings])
        self.assertIn("postal_code", [item.target_field for item in candidate.field_mappings])

    def test_markdown_front_matter_parsing(self) -> None:
        write_intake_config(self.root, self.intake_root)
        (self.intake_root / "incoming" / "order.md").write_text(
            "---\n"
            "order_id: MD-1001\n"
            "subject_address: 789 Example Lane\n"
            "client_name: Markdown Client\n"
            "---\n"
            "Narrative text ignored.\n",
            encoding="utf-8",
        )
        self.assertEqual(RealEstateIntakeEngine(self.root).scan()[0].detected_assignment_id, "md-1001")

    def test_markdown_labeled_field_parsing(self) -> None:
        write_intake_config(self.root, self.intake_root)
        (self.intake_root / "incoming" / "order.txt").write_text(
            "Order ID: TXT-1001\n"
            "Subject Address: 789 Example Lane\n"
            "Client Name: Text Client\n",
            encoding="utf-8",
        )
        self.assertEqual(RealEstateIntakeEngine(self.root).scan()[0].detected_assignment_id, "txt-1001")

    def test_assignment_id_priority_rules_and_normalization(self) -> None:
        write_intake_config(self.root, self.intake_root)
        write_json_intake(self.intake_root / "incoming" / "order.json", assignment_id="Custom ID/ABC", order_id="ORDER-SHOULD-NOT-WIN")
        candidate = RealEstateIntakeEngine(self.root).scan()[0]
        self.assertEqual(candidate.detected_assignment_id, "custom-id-abc")

    def test_address_based_assignment_id_fallback(self) -> None:
        write_intake_config(self.root, self.intake_root)
        write_json_intake(self.intake_root / "incoming" / "order.json", order_id="", loan_number="", subject_address="321 Fallback Street")
        self.assertEqual(RealEstateIntakeEngine(self.root).scan()[0].detected_assignment_id, "321-fallback-street-2026-07-18")

    def test_field_alias_mapping_and_roles_preserved(self) -> None:
        write_intake_config(self.root, self.intake_root)
        write_json_intake(self.intake_root / "incoming" / "order.json")
        result = RealEstateIntakeEngine(self.root).import_candidates()
        record = result.manifest.records[0]
        self.assertIn("client_name", record.fields_mapped)
        assignment_text = (self.root / "real-estate" / "assignments" / "order-1001" / "assignment.yaml").read_text(encoding="utf-8")
        self.assertIn("Intake role preserved: lender=Example Lender", assignment_text)
        self.assertIn("Intake role preserved: amc=Example AMC", assignment_text)

    def test_assignment_creation_and_automatic_build(self) -> None:
        write_intake_config(self.root, self.intake_root)
        write_json_intake(self.intake_root / "incoming" / "order.json")
        result = RealEstateIntakeEngine(self.root).import_candidates()
        record = result.manifest.records[0]
        self.assertEqual(record.import_status, "imported")
        self.assertTrue(Path(record.assignment_path).exists())
        self.assertTrue(Path(record.assignment_brief_path).exists())
        self.assertTrue((self.root / "outputs" / "dashboard" / "dashboard.json").exists())

    def test_source_reference_mode(self) -> None:
        write_intake_config(self.root, self.intake_root, source_mode="reference")
        intake_path = write_json_intake(self.intake_root / "incoming" / "order.json")
        result = RealEstateIntakeEngine(self.root).import_candidates()
        record = result.manifest.records[0]
        self.assertIn(str(intake_path), record.sources_linked)

    def test_source_copy_mode(self) -> None:
        write_intake_config(self.root, self.intake_root, source_mode="copy")
        write_json_intake(self.intake_root / "incoming" / "order.json")
        result = RealEstateIntakeEngine(self.root).import_candidates()
        record = result.manifest.records[0]
        self.assertIn("sources/order.json", record.sources_linked)
        self.assertTrue((self.root / "real-estate" / "assignments" / "order-1001" / "sources" / "order.json").exists())

    def test_duplicate_detection_repeated_import(self) -> None:
        write_intake_config(self.root, self.intake_root)
        write_json_intake(self.intake_root / "incoming" / "order.json")
        engine = RealEstateIntakeEngine(self.root)
        first = engine.import_candidates()
        second = engine.import_candidates()
        self.assertEqual(first.manifest.counts["imported"], 1)
        self.assertEqual(second.manifest.counts["skipped_duplicate"], 1)

    def test_existing_assignment_merge_no_overwrite_and_conflict_fact(self) -> None:
        write_intake_config(self.root, self.intake_root)
        assignment_store = RealEstateAssignmentStore(self.root)
        assignment_store.create_template("order-1001")
        assignment_path = self.root / "real-estate" / "assignments" / "order-1001" / "assignment.yaml"
        text = assignment_path.read_text(encoding="utf-8").replace('    address: ""', "    address: 999 Existing Avenue")
        assignment_path.write_text(text, encoding="utf-8")
        write_json_intake(self.intake_root / "incoming" / "order.json", subject_address="123 New Avenue")
        result = RealEstateIntakeEngine(self.root).import_candidates()
        self.assertIn("subject.address", result.manifest.records[0].conflicts_created)
        data = assignment_store.load("order-1001")
        self.assertEqual(data["assignment"]["subject"]["address"], "999 Existing Avenue")
        self.assertGreater(data["conflict_count"], 0)

    def test_new_source_merge(self) -> None:
        write_intake_config(self.root, self.intake_root)
        write_json_intake(self.intake_root / "incoming" / "order.json")
        engine = RealEstateIntakeEngine(self.root)
        engine.import_candidates()
        write_json_intake(self.intake_root / "incoming" / "order2.json", order_id="ORDER-1001", due_date="2026-07-20")
        engine.import_candidates(file_path=self.intake_root / "incoming" / "order2.json")
        data = RealEstateAssignmentStore(self.root).load("order-1001")
        self.assertGreaterEqual(data["source_count"], 2)

    def test_intake_manifest_and_history_persistence(self) -> None:
        write_intake_config(self.root, self.intake_root)
        write_json_intake(self.intake_root / "incoming" / "order.json")
        RealEstateIntakeEngine(self.root).import_candidates()
        store = RealEstateIntakeStore(self.root)
        self.assertTrue(store.manifest_path.exists())
        self.assertTrue(store.markdown_path.exists())
        self.assertTrue(store.history_path.exists())
        self.assertEqual(len(store.history()), 1)

    def test_cli_status_scan_import_file_history_show(self) -> None:
        write_intake_config(self.root, self.intake_root)
        file_path = write_json_intake(self.intake_root / "incoming" / "order.json")
        for command in [
            ["real-estate", "--root", str(self.root), "intake", "status"],
            ["real-estate", "--root", str(self.root), "intake", "scan"],
            ["real-estate", "--root", str(self.root), "intake", "import", "--file", str(file_path)],
            ["real-estate", "--root", str(self.root), "intake", "history"],
        ]:
            with self.subTest(command=command):
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    code = main(command)
                self.assertEqual(code, 0, buffer.getvalue())
        intake_id = RealEstateIntakeStore(self.root).history()[0]["records"][0]["intake_id"]
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = main(["real-estate", "--root", str(self.root), "intake", "show", intake_id])
        self.assertEqual(code, 0)
        self.assertIn("order-1001", buffer.getvalue())

    def test_cli_open_flag_does_not_affect_success(self) -> None:
        write_intake_config(self.root, self.intake_root)
        file_path = write_json_intake(self.intake_root / "incoming" / "order.json")
        with patch("constellation.real_estate_intake.subprocess.run", side_effect=OSError("no code")):
            buffer = io.StringIO()
            with contextlib.redirect_stdout(buffer):
                code = main(["real-estate", "--root", str(self.root), "intake", "import", "--file", str(file_path), "--open"])
        self.assertEqual(code, 0, buffer.getvalue())

    def test_private_paths_gitignored(self) -> None:
        gitignore = Path(__file__).resolve().parents[1] / ".gitignore"
        text = gitignore.read_text(encoding="utf-8")
        self.assertIn("config/real-estate-intake.yaml", text)
        self.assertIn("config/real-estate-intake.local.yaml", text)
        self.assertIn("real-estate/assignments/**", text)
        self.assertIn("outputs/real-estate/", text)

    def test_deterministic_repeated_scan(self) -> None:
        write_intake_config(self.root, self.intake_root)
        write_json_intake(self.intake_root / "incoming" / "order.json")
        engine = RealEstateIntakeEngine(self.root)
        first = [candidate.to_dict() for candidate in engine.scan()]
        second = [candidate.to_dict() for candidate in engine.scan()]
        self.assertEqual(first, second)

    def test_no_provider_external_calls_or_valuation_language(self) -> None:
        write_intake_config(self.root, self.intake_root)
        write_json_intake(self.intake_root / "incoming" / "order.json")
        with patch("constellation.real_estate_intake.subprocess.run") as runner:
            RealEstateIntakeEngine(self.root).import_candidates()
        runner.assert_not_called()
        brief = (self.root / "outputs" / "real-estate" / "assignments" / "order-1001" / "assignment-brief.md").read_text(encoding="utf-8").lower()
        for phrase in ["opinion of value", "recommended comparable", "adjustment amount", "uspap compliant opinion"]:
            self.assertNotIn(phrase, brief)


if __name__ == "__main__":
    unittest.main()
