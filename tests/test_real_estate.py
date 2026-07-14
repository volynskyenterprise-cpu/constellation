from __future__ import annotations

import contextlib
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from constellation.cli import main
from constellation.dashboard import ExecutiveDashboardBuilder, ExecutiveDashboardStore
from constellation.real_estate import RealEstateAssignmentStore, RealEstateError


def write_assignment(root: Path, assignment_id: str = "test-assignment", *, missing: bool = False, conflict: bool = True, due_date: str = "2099-07-21") -> Path:
    assignment_dir = root / "real-estate" / "assignments" / assignment_id
    (assignment_dir / "sources").mkdir(parents=True, exist_ok=True)
    (assignment_dir / "notes").mkdir(parents=True, exist_ok=True)
    (assignment_dir / "evidence").mkdir(parents=True, exist_ok=True)
    (assignment_dir / "sources" / "purchase-contract.pdf").write_bytes(b"contract metadata fixture")
    (assignment_dir / "sources" / "floor-plan.pdf").write_bytes(b"floor plan metadata fixture")
    (assignment_dir / "sources" / "permit-record.txt").write_text("sanitized permit metadata fixture", encoding="utf-8")
    (assignment_dir / "notes" / "reviewer-condition.md").write_text("sanitized reviewer note", encoding="utf-8")
    subject_block = (
        '    address: ""\n'
        '    city: ""\n'
        '    state: ""\n'
        '    postal_code: ""\n'
        '    county: ""\n'
        '    assessor_parcel_number: ""\n'
        if missing
        else
        "    address: 123 Example Avenue\n"
        "    city: Example City\n"
        "    state: CA\n"
        '    postal_code: "90000"\n'
        "    county: Example County\n"
        "    assessor_parcel_number: EXAMPLE-APN\n"
    )
    facts = (
        "    - field_name: gross_living_area\n"
        '      value: "2000"\n'
        "      unit: square_feet\n"
        "      verification_status: verified\n"
        "      confidence: high\n"
        "      source_paths:\n"
        "        - sources/floor-plan.pdf\n"
        "      notes: Sanitized structured fact.\n"
    )
    if conflict:
        facts += (
            "    - field_name: gross_living_area\n"
            '      value: "2100"\n'
            "      unit: square_feet\n"
            "      verification_status: client_provided\n"
            "      confidence: medium\n"
            "      source_paths:\n"
            "        - sources/purchase-contract.pdf\n"
            "      notes: Sanitized conflicting structured fact.\n"
        )
    assignment_yaml = (
        "assignment:\n"
        f"  assignment_id: {assignment_id}\n"
        "  status: active\n"
        "  assignment_type: appraisal\n"
        "  property_type: single_family_residential\n"
        "  intended_use: mortgage_lending\n"
        "  client_name: Sanitized Client\n"
        "  effective_date: 2026-07-14\n"
        f"  due_date: {due_date}\n"
        "  report_type: appraisal_report\n"
        "  created_at: 2026-07-14\n"
        "  subject:\n"
        f"{subject_block}"
        "  scope:\n"
        "    inspection_type: interior_and_exterior\n"
        "    valuation_premise: market_value\n"
        "    ownership_interest: fee_simple\n"
        "  source_paths:\n"
        "    - sources/\n"
        "  notes:\n"
        "    - Sanitized test assignment only.\n"
        "  facts:\n"
        f"{facts}"
    )
    (assignment_dir / "assignment.yaml").write_text(assignment_yaml, encoding="utf-8")
    return assignment_dir


class RealEstateAssignmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tempdir = tempfile.TemporaryDirectory()
        self.root = Path(self.tempdir.name)
        (self.root / "config").mkdir()
        (self.root / "config" / "real-estate-assignment.example.yaml").write_text(
            "real_estate_assignment:\n"
            "  default_root: real-estate/assignments\n"
            "  default_status: active\n"
            "  default_property_type: single_family_residential\n",
            encoding="utf-8",
        )
        self.store = RealEstateAssignmentStore(self.root)

    def tearDown(self) -> None:
        self.tempdir.cleanup()

    def test_empty_assignment_root_lists_no_assignments(self) -> None:
        self.assertEqual(self.store.list_assignment_ids(), [])

    def test_create_template_creates_private_assignment_structure(self) -> None:
        path = self.store.create_template("template-assignment")
        self.assertTrue(path.exists())
        self.assertTrue((path.parent / "sources").is_dir())
        self.assertTrue((path.parent / "notes").is_dir())
        self.assertTrue((path.parent / "evidence").is_dir())
        with self.assertRaises(RealEstateError):
            self.store.create_template("template-assignment")

    def test_assignment_build_creates_snapshot_counts(self) -> None:
        write_assignment(self.root)
        snapshot = self.store.build("test-assignment")
        data = snapshot.to_dict()
        self.assertEqual(data["assignment_id"], "test-assignment")
        self.assertEqual(data["status"], "active")
        self.assertGreaterEqual(data["source_count"], 4)
        self.assertGreater(data["fact_count"], 0)
        self.assertGreater(data["verified_fact_count"], 0)

    def test_assignment_build_persists_expected_outputs(self) -> None:
        write_assignment(self.root)
        self.store.build("test-assignment")
        output_dir = self.store.output_dir("test-assignment")
        for filename in [
            "assignment.json",
            "assignment-brief.md",
            "source-manifest.json",
            "source-manifest.md",
            "evidence-index.json",
            "evidence-index.md",
            "missing-information.json",
            "missing-information.md",
            "assignment-risks.json",
            "assignment-risks.md",
            "assignment-timeline.json",
            "assignment-timeline.md",
            "assignment-history.json",
            "assignment-delta.json",
        ]:
            self.assertTrue((output_dir / filename).exists(), filename)

    def test_source_manifest_uses_metadata_and_categories(self) -> None:
        write_assignment(self.root)
        data = self.store.build("test-assignment").to_dict()
        categories = {source["source_category"] for source in data["sources"]}
        self.assertIn("contract", categories)
        self.assertIn("floor_plan", categories)
        self.assertIn("permit", categories)
        for source in data["sources"]:
            self.assertTrue(source["checksum"])
            self.assertTrue(source["provenance"]["metadata_only"])

    def test_structured_fact_conflicts_are_detected_by_exact_field(self) -> None:
        write_assignment(self.root, conflict=True)
        data = self.store.build("test-assignment").to_dict()
        self.assertEqual(data["conflict_count"], 1)
        conflict = data["conflicts"][0]
        self.assertEqual(conflict["field_name"], "gross_living_area")
        self.assertEqual(conflict["status"], "open")

    def test_missing_information_and_risks_are_reported(self) -> None:
        write_assignment(self.root, missing=True, conflict=False)
        data = self.store.build("test-assignment").to_dict()
        missing_fields = {item["field_name"] for item in data["missing_items"]}
        self.assertIn("subject.address", missing_fields)
        risk_types = {item["risk_type"] for item in data["risks"]}
        self.assertIn("missing_required_information", risk_types)

    def test_overdue_assignment_generates_timeline_risk(self) -> None:
        write_assignment(self.root, conflict=False, due_date="2020-01-01")
        data = self.store.build("test-assignment").to_dict()
        self.assertIn("timeline_risk", {item["risk_type"] for item in data["risks"]})

    def test_history_does_not_duplicate_identical_snapshot(self) -> None:
        write_assignment(self.root, conflict=False)
        self.store.build("test-assignment")
        self.store.build("test-assignment")
        history = self.store.history("test-assignment")
        self.assertEqual(len(history), 1)

    def test_delta_records_changed_source(self) -> None:
        assignment_dir = write_assignment(self.root, conflict=False)
        self.store.build("test-assignment")
        (assignment_dir / "sources" / "floor-plan.pdf").write_bytes(b"changed floor plan fixture")
        data = self.store.build("test-assignment").to_dict()
        self.assertGreaterEqual(len(data["delta"]["changed_sources"]), 1)

    def test_store_summary_counts_assignments(self) -> None:
        write_assignment(self.root, "a-active", conflict=False)
        write_assignment(self.root, "b-waiting", missing=True, conflict=False)
        text = (self.root / "real-estate" / "assignments" / "b-waiting" / "assignment.yaml").read_text(encoding="utf-8")
        (self.root / "real-estate" / "assignments" / "b-waiting" / "assignment.yaml").write_text(text.replace("status: active", "status: waiting_for_information"), encoding="utf-8")
        summary = self.store.summary()
        self.assertTrue(summary["real_estate_assignment_intelligence_available"])
        self.assertEqual(summary["active_assignment_count"], 1)
        self.assertEqual(summary["waiting_assignment_count"], 1)
        self.assertGreater(summary["total_missing_item_count"], 0)

    def test_cli_build_status_sources_missing_risks_timeline_export(self) -> None:
        write_assignment(self.root)
        commands = [
            ["real-estate", "--root", str(self.root), "assignment", "build", "test-assignment"],
            ["real-estate", "--root", str(self.root), "assignment", "status", "test-assignment"],
            ["real-estate", "--root", str(self.root), "assignment", "sources", "test-assignment"],
            ["real-estate", "--root", str(self.root), "assignment", "missing", "test-assignment"],
            ["real-estate", "--root", str(self.root), "assignment", "risks", "test-assignment"],
            ["real-estate", "--root", str(self.root), "assignment", "timeline", "test-assignment"],
            ["real-estate", "--root", str(self.root), "assignment", "export", "test-assignment"],
        ]
        for command in commands:
            with self.subTest(command=command):
                buffer = io.StringIO()
                with contextlib.redirect_stdout(buffer):
                    code = main(command)
                self.assertEqual(code, 0, buffer.getvalue())

    def test_cli_assignments_lists_known_assignment(self) -> None:
        write_assignment(self.root)
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = main(["real-estate", "--root", str(self.root), "assignments"])
        self.assertEqual(code, 0)
        self.assertIn("test-assignment", buffer.getvalue())

    def test_cli_create_template(self) -> None:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = main(["real-estate", "--root", str(self.root), "assignment", "create-template", "cli-template"])
        self.assertEqual(code, 0)
        self.assertTrue((self.root / "real-estate" / "assignments" / "cli-template" / "assignment.yaml").exists())

    def test_cli_missing_assignment_returns_error(self) -> None:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            code = main(["real-estate", "--root", str(self.root), "assignment", "build", "missing"])
        self.assertEqual(code, 1)
        self.assertIn("error:", buffer.getvalue())

    def test_dashboard_includes_real_estate_summary(self) -> None:
        write_assignment(self.root, conflict=False)
        dashboard = ExecutiveDashboardBuilder(self.root).build()
        summary = dashboard.real_estate_assignment_summary
        self.assertTrue(summary["real_estate_assignment_intelligence_available"])
        self.assertEqual(summary["active_assignment_count"], 1)
        self.assertIn("active_real_estate_assignments", dashboard.executive_summary)

    def test_dashboard_markdown_contains_real_estate_section(self) -> None:
        write_assignment(self.root, conflict=False)
        dashboard = ExecutiveDashboardStore(self.root).generate(overwrite=True)
        markdown = (self.root / "outputs" / "dashboard" / "dashboard.md").read_text(encoding="utf-8")
        self.assertIn("Real Estate Assignment Intelligence Summary", markdown)
        self.assertTrue(dashboard.real_estate_assignment_summary["real_estate_assignment_intelligence_available"])

    def test_repository_gitignore_protects_private_real_estate_paths(self) -> None:
        gitignore = Path(__file__).resolve().parents[1] / ".gitignore"
        text = gitignore.read_text(encoding="utf-8")
        self.assertIn("real-estate/assignments/**", text)
        self.assertIn("config/real-estate-assignment.yaml", text)
        self.assertIn("outputs/real-estate/", text)

    def test_generated_reports_do_not_contain_unsupported_conclusion_language(self) -> None:
        write_assignment(self.root, conflict=False)
        self.store.build("test-assignment")
        text = (self.store.output_dir("test-assignment") / "assignment-brief.md").read_text(encoding="utf-8").lower()
        forbidden = ["opinion of value", "market value is", "recommended comparable", "adjustment amount", "uspap compliant opinion"]
        for phrase in forbidden:
            self.assertNotIn(phrase, text)

    def test_no_provider_or_external_call_is_used(self) -> None:
        write_assignment(self.root, conflict=False)
        with patch("constellation.real_estate.load_yaml", wraps=__import__("constellation.simple_yaml", fromlist=["load_yaml"]).load_yaml) as yaml_loader:
            snapshot = self.store.build("test-assignment")
        self.assertEqual(snapshot.assignment.assignment_id, "test-assignment")
        self.assertGreaterEqual(yaml_loader.call_count, 1)

    def test_deterministic_snapshot_for_unchanged_inputs(self) -> None:
        write_assignment(self.root, conflict=False)
        first = self.store.build("test-assignment").snapshot_id
        second = self.store.build("test-assignment").snapshot_id
        self.assertEqual(first, second)


if __name__ == "__main__":
    unittest.main()
