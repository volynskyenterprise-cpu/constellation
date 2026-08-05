from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from constellation.comparable_intelligence import (
    ComparableIntelligenceError,
    ComparableIntelligenceEngine,
    ComparableStore,
    comparable_dashboard_summary,
    code_number,
    load_comparable_file,
    normalize_address,
    normalize_date,
    normalize_distance_fields,
    normalize_status,
    to_number,
    validate_scenario_id,
)
from constellation.real_estate import RealEstateAssignmentStore, _render_comparable_section
from constellation.real_estate_daily import _comparable_input_checksums


class ComparableIntelligenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="comparable-intelligence-test-"))
        self.assignment_id = "test-assignment"
        assignment_dir = self.tmp / "real-estate" / "assignments" / self.assignment_id
        assignment_dir.mkdir(parents=True)
        (assignment_dir / "assignment.yaml").write_text(
            """assignment:
  assignment_id: test-assignment
  status: analysis
  assignment_type: appraisal
  property_type: single_family_residential
  effective_date: 2026-07-15
  due_date: 2026-07-30
  subject:
    address: 100 Fictional Avenue
    city: Testville
    state: CA
  scope:
    inspection_type: interior
    valuation_premise: market_value
  facts:
    - field_name: gross_living_area
      value: 2450
    - field_name: lot_size
      value: 7200
    - field_name: bedroom_count
      value: 4
    - field_name: bathroom_count
      value: 3
    - field_name: condition
      value: C3
    - field_name: quality
      value: Q3
    - field_name: year_built
      value: 1995
""",
            encoding="utf-8",
        )
        comp_dir = assignment_dir / "comparables"
        comp_dir.mkdir()
        (comp_dir / "comparables.yaml").write_text(self._yaml_comparables(), encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _yaml_comparables(self) -> str:
        return """assignment_id: test-assignment
comparables:
  - comparable_id: comp-001
    source_type: mls_export
    listing_id: L1
    address: 500 Example Avenue
    status: closed_sale
    sale_date: 2026-05-01
    sale_price: 1850000
    property_type: single_family_residential
    gross_living_area: 2350
    lot_size: 7000
    condition: C3
    quality: Q3
    bedrooms: 4
    bathrooms: 3
    year_built: 1998
    distance_miles: 0.4
  - comparable_id: comp-002
    source_type: mls_export
    listing_id: L2
    address: 510 Example Avenue
    status: closed_sale
    sale_date: 2026-04-15
    sale_price: 1875000
    property_type: single_family_residential
    gross_living_area: 2525
    lot_size: 7600
    condition: C3
    quality: Q3
    bedrooms: 4
    bathrooms: 3
    year_built: 1994
    distance_miles: 0.7
  - comparable_id: comp-003
    source_type: mls_export
    listing_id: L3
    address: 520 Example Avenue
    status: closed_sale
    sale_date: 2026-03-20
    sale_price: 1810000
    property_type: single_family_residential
    gross_living_area: 2440
    lot_size: 7300
    condition: C3
    quality: Q3
    bedrooms: 4
    bathrooms: 3
    year_built: 1996
    distance_miles: 0.8
  - comparable_id: comp-004
    source_type: mls_export
    listing_id: L4
    address: 900 Context Road
    status: active
    current_list_price: 2200000
    property_type: single_family_residential
    gross_living_area: 3000
    lot_size: 9000
    condition: C2
    quality: Q2
    bedrooms: 5
    bathrooms: 4
    year_built: 2015
    distance_miles: 2.5
  - comparable_id: comp-005
    source_type: public_record
    parcel_number: APN-5
    address: 700 Older Street
    status: closed_sale
    sale_date: 2024-01-01
    sale_price: 1500000
    property_type: single_family_residential
    gross_living_area: 1900
    lot_size: 6000
    condition: C4
    quality: Q4
    bedrooms: 3
    bathrooms: 2
    year_built: 1970
    distance_miles: 4.5
  - comparable_id: comp-006
    source_type: mls_export
    listing_id: L1
    address: 500 Example Ave.
    status: closed_sale
    sale_date: 2026-05-01
    sale_price: 1860000
    property_type: single_family_residential
    gross_living_area: 2350
    lot_size: 7000
    condition: C3
    quality: Q3
    bedrooms: 4
    bathrooms: 3
    year_built: 1998
    distance_miles: 0.4
  - comparable_id: comp-007
    source_type: appraiser_entry
    address: 800 Missing Lane
    status: closed_sale
    property_type: single_family_residential
  - comparable_id: comp-008
    source_type: mls_export
    listing_id: L8
    address: 950 Large Court
    status: closed_sale
    sale_date: 2026-02-01
    sale_price: 2300000
    property_type: single_family_residential
    gross_living_area: 3100
    lot_size: 12000
    condition: C3
    quality: Q3
    bedrooms: 5
    bathrooms: 4
    year_built: 2005
    distance_miles: 2.8
"""

    def test_normalization_helpers(self) -> None:
        self.assertEqual(normalize_address("&nbsp;500 Example Avenue."), "500 example ave")
        self.assertEqual(normalize_date("7/15/2026"), "2026-07-15")
        self.assertEqual(normalize_status("Sold"), "closed_sale")
        self.assertEqual(to_number("$1,850,000"), 1850000)
        self.assertEqual(code_number("C3", "c"), 3)

    def test_yaml_json_and_csv_import(self) -> None:
        path = ComparableStore(self.tmp).input_dir(self.assignment_id) / "comparables.yaml"
        self.assertEqual(len(load_comparable_file(path)), 8)
        json_path = path.with_suffix(".json")
        json_path.write_text(json.dumps({"comparables": [{"comparable_id": "json-1", "address": "1 JSON St"}]}), encoding="utf-8")
        csv_path = path.with_name("sales.csv")
        csv_path.write_text("comparable_id,address,status\ncsv-1,1 CSV St,closed\n", encoding="utf-8")
        self.assertEqual(len(load_comparable_file(json_path)), 1)
        self.assertEqual(len(load_comparable_file(csv_path)), 1)

    def test_build_universe_outputs_and_tiers(self) -> None:
        universe = ComparableIntelligenceEngine(self.tmp).build(self.assignment_id, overwrite=True)
        counts = universe.counts
        self.assertEqual(counts["comparable_count"], 8)
        self.assertGreaterEqual(counts["primary_candidate"], 2)
        self.assertGreaterEqual(counts["secondary_candidate"], 1)
        self.assertGreaterEqual(counts["contextual_candidate"], 1)
        self.assertGreaterEqual(counts["review_item_count"], 1)
        self.assertFalse(any(record.appraiser_selected for record in universe.comparables))
        self.assertTrue((ComparableStore(self.tmp).output_dir(self.assignment_id) / "comparable-universe.md").exists())
        self.assertTrue((ComparableStore(self.tmp).output_dir(self.assignment_id) / "comparable-coverage.md").exists())

    def test_duplicate_and_conflict_are_preserved(self) -> None:
        universe = ComparableIntelligenceEngine(self.tmp).build(self.assignment_id, overwrite=True)
        self.assertGreaterEqual(universe.counts["open_conflict_count"], 1)
        self.assertTrue(any(conflict.field_name in {"identity", "sale_price"} for conflict in universe.conflicts))

    def test_coverage_and_bracketing(self) -> None:
        universe = ComparableIntelligenceEngine(self.tmp).build(self.assignment_id, overwrite=True)
        coverage = universe.coverage.to_dict()
        self.assertIn(coverage["levels"]["gross_living_area"], {"excellent", "adequate"})
        self.assertIn(coverage["bracketing"]["gross_living_area"]["bracketing"], {"fully_bracketed", "partially_bracketed"})
        self.assertTrue(coverage["research_questions"])

    def test_review_state_select_exclude_reset(self) -> None:
        engine = ComparableIntelligenceEngine(self.tmp)
        engine.build(self.assignment_id, overwrite=True)
        with self.assertRaises(Exception):
            engine.select(self.assignment_id, "comp-001")
        engine.select(self.assignment_id, "comp-001", confirm=True, reviewer="tester")
        engine.build(self.assignment_id, overwrite=True)
        selected = [record for record in engine.store.load(self.assignment_id)["comparables"] if record["comparable_id"] == "comp-001"][0]
        self.assertTrue(selected["appraiser_selected"])
        engine.exclude(self.assignment_id, "comp-002", reason="Appraiser reviewed as contextual only.", confirm=True)
        engine.reset_review(self.assignment_id, "comp-002", confirm=True)
        state = engine.store.load_review_state(self.assignment_id)
        self.assertNotIn("comp-002", state["comparables"])

    def test_idempotent_rebuild(self) -> None:
        engine = ComparableIntelligenceEngine(self.tmp)
        first = engine.build(self.assignment_id, overwrite=True).to_dict()
        second = engine.build(self.assignment_id, overwrite=True).to_dict()
        self.assertEqual(first["counts"], second["counts"])
        self.assertEqual([item["comparable_id"] for item in first["comparables"]], [item["comparable_id"] for item in second["comparables"]])


class ComparableScenarioTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="comparable-scenarios-test-"))
        self.assignment_id = "fictional-two-value-assignment"
        assignment_dir = self.tmp / "real-estate" / "assignments" / self.assignment_id
        assignment_dir.mkdir(parents=True)
        (assignment_dir / "assignment.yaml").write_text(
            """assignment:
  assignment_id: fictional-two-value-assignment
  property_type: single_family_residential
  effective_date: 2026-07-10
  subject:
    address: 100 Fictional Avenue
  facts:
    - field_name: gross_living_area
      value: 1600
    - field_name: lot_size
      value: 6,531 sqft.
    - field_name: bedroom_count
      value: 2
    - field_name: bathroom_count
      value: 2
""",
            encoding="utf-8",
        )
        self._write_scenario("as_is", self._as_is_yaml())
        self._write_scenario("arv", self._arv_yaml())

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write_scenario(self, scenario: str, text: str) -> Path:
        directory = self.tmp / "real-estate" / "assignments" / self.assignment_id / "comparables" / "scenarios" / scenario
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "comparables.yaml"
        path.write_text(text, encoding="utf-8")
        return path

    def _as_is_yaml(self) -> str:
        return """assignment_id: fictional-two-value-assignment
valuation_scenario: as_is
scenario_label: As-Is
subject:
  address: 100 Fictional Ave.
  property_type: single_family_residential
  gross_living_area: 1,452 square feet
  lot_size: 6531
  condition: Average
  quality: Average
  bedrooms: 2
  bathrooms: 2
  sale_or_effective_date: 2026-07-10
comparables:
  - comparable_id: shared-comp
    address: 101 Fictional Street
    status: closed_sale
    sale_date: 2026-03-04
    sale_price: 1800000
    property_type: single_family_residential
    gross_living_area: 1187
    lot_size: 5850
    bedrooms: 2
    bathrooms: 1
    distance_miles: 0.4
  - comparable_id: recent-above
    address: 102 Fictional Street
    status: closed_sale
    sale_date: 2026-04-14
    sale_price: 1885000
    property_type: single_family_residential
    gross_living_area: 1605
    lot_size: 5850
    bedrooms: 3
    bathrooms: 2
    distance_from_subject_miles: 0.7
  - comparable_id: recent-missing-distance
    address: 103 Fictional Street
    status: closed_sale
    sale_date: 2026-04-17
    sale_price: 1526000
    property_type: single_family_residential
    gross_living_area: 1284
    lot_size: 6550
    bedrooms: 3
    bathrooms: 1
  - comparable_id: old-sale
    address: 104 Fictional Street
    status: closed_sale
    sale_date: 2002-06-26
    sale_price: 720000
    property_type: single_family_residential
    gross_living_area: 1400
    lot_size: 5081
    bedrooms: 3
    bathrooms: 2
    distance_from_subject: 1 kilometer
"""

    def _arv_yaml(self) -> str:
        return """assignment_id: fictional-two-value-assignment
valuation_scenario: arv
scenario_label: ARV
subject:
  address: 100 Fictional Avenue
  property_type: single_family_residential
  gross_living_area: 2450
  lot_size: 6531
  condition: C2
  quality: Q3
  bedrooms: 4
  bathrooms: 4
  sale_or_effective_date: 2026-07-10
comparables:
  - comparable_id: shared-comp
    address: 201 Imaginary Road
    status: closed_sale
    sale_date: 2026-05-01
    sale_price: 2800000
    property_type: single_family_residential
    gross_living_area: 2400
    lot_size: 6400
    bedrooms: 4
    bathrooms: 4
    distance_from_subject_miles: 0.5
  - comparable_id: arv-two
    address: 202 Imaginary Road
    status: closed_sale
    sale_date: 2026-04-01
    sale_price: 2900000
    property_type: single_family_residential
    gross_living_area: 2550
    lot_size: 6700
    bedrooms: 4
    bathrooms: 4
    distance_from_subject_miles: 0.8
  - comparable_id: arv-three
    address: 203 Imaginary Road
    status: closed_sale
    sale_date: 2026-03-01
    sale_price: 2750000
    property_type: single_family_residential
    gross_living_area: 2350
    lot_size: 6200
    bedrooms: 4
    bathrooms: 3
    distance_from_subject_miles: 1.1
"""

    def test_multiple_scenarios_require_explicit_selection(self) -> None:
        with self.assertRaisesRegex(ComparableIntelligenceError, "Multiple comparable scenarios"):
            ComparableStore(self.tmp).resolve_scenario(self.assignment_id)

    def test_scenario_paths_and_subjects_are_isolated(self) -> None:
        engine = ComparableIntelligenceEngine(self.tmp)
        as_is = engine.build(self.assignment_id, scenario="as_is", overwrite=True)
        arv = engine.build(self.assignment_id, scenario="arv", overwrite=True)
        self.assertEqual(as_is.subject["gross_living_area"], 1452)
        self.assertEqual(arv.subject["gross_living_area"], 2450)
        self.assertEqual(as_is.counts["comparable_count"], 4)
        self.assertEqual(arv.counts["comparable_count"], 3)
        self.assertNotEqual(ComparableStore(self.tmp).output_dir(self.assignment_id, "as_is"), ComparableStore(self.tmp).output_dir(self.assignment_id, "arv"))
        self.assertFalse(any(record.property_address.startswith("2") for record in as_is.comparables))

    def test_subject_resolution_precedence_and_conflict(self) -> None:
        universe = ComparableIntelligenceEngine(self.tmp).build(self.assignment_id, scenario="as_is", overwrite=True)
        self.assertEqual(universe.subject["gross_living_area"], 1452)
        self.assertTrue(any(item.conflict_id.startswith("subject_fact_conflict") and item.field_name == "gross_living_area" for item in universe.conflicts))
        detail = universe.subject_resolution["fields"]["gross_living_area"]
        self.assertEqual(detail["selected_source"], "private_scenario_input")
        self.assertEqual(detail["conflict_status"], "open")

    def test_equivalent_formatted_subject_value_has_no_conflict(self) -> None:
        universe = ComparableIntelligenceEngine(self.tmp).build(self.assignment_id, scenario="as_is", overwrite=True)
        self.assertFalse(any(item.field_name == "lot_size" and item.comparable_id == "subject" for item in universe.conflicts))

    def test_blank_private_value_falls_back_to_canonical(self) -> None:
        path = ComparableStore(self.tmp).input_dir(self.assignment_id, "as_is") / "comparables.yaml"
        text = path.read_text(encoding="utf-8").replace("  lot_size: 6531", "  lot_size:")
        path.write_text(text, encoding="utf-8")
        universe = ComparableIntelligenceEngine(self.tmp).build(self.assignment_id, scenario="as_is", overwrite=True)
        self.assertEqual(universe.subject["lot_size"], 6531)
        self.assertTrue(universe.subject_resolution["fields"]["lot_size"]["fallback_used"])

    def test_effective_date_is_scenario_specific(self) -> None:
        universe = ComparableIntelligenceEngine(self.tmp).build(self.assignment_id, scenario="as_is", overwrite=True)
        self.assertEqual(universe.subject["sale_or_effective_date"], "2026-07-10")
        self.assertEqual(universe.subject_resolution["fields"]["sale_or_effective_date"]["selected_source"], "private_scenario_input")

    def test_live_shape_bracketing_and_tiers(self) -> None:
        universe = ComparableIntelligenceEngine(self.tmp).build(self.assignment_id, scenario="as_is", overwrite=True)
        gla = universe.coverage.bracketing["gross_living_area"]
        lot = universe.coverage.bracketing["lot_size"]
        self.assertEqual((gla["bracketing"], gla["below"], gla["above"]), ("fully_bracketed", 3, 1))
        self.assertEqual((lot["bracketing"], lot["below"], lot["above"]), ("fully_bracketed", 3, 1))
        missing_distance = next(item for item in universe.comparables if item.comparable_id == "recent-missing-distance")
        old_sale = next(item for item in universe.comparables if item.comparable_id == "old-sale")
        self.assertEqual(missing_distance.candidate_status, "secondary_candidate")
        self.assertEqual(old_sale.candidate_status, "contextual_candidate")
        self.assertFalse(old_sale.appraiser_selected)
        self.assertNotEqual(old_sale.appraiser_review_status, "excluded")

    def test_sanitized_property_alias_closes_only_property_conflict(self) -> None:
        engine = ComparableIntelligenceEngine(self.tmp)
        baseline = engine.build(self.assignment_id, scenario="as_is", overwrite=True)
        tier_keys = ["primary_candidate", "secondary_candidate", "contextual_candidate", "review_required", "insufficient_data", "potential_duplicate"]
        baseline_tiers = {key: baseline.counts.get(key, 0) for key in tier_keys}
        review_path = engine.store.review_state_path(self.assignment_id, "as_is")
        self.assertFalse(review_path.exists())

        assignment_path = self.tmp / "real-estate" / "assignments" / self.assignment_id / "assignment.yaml"
        assignment_text = assignment_path.read_text(encoding="utf-8")
        assignment_text = assignment_text.replace("property_type: single_family_residential", "property_type: Single Family", 1)
        assignment_path.write_text(assignment_text, encoding="utf-8")
        scenario_path = engine.store.input_dir(self.assignment_id, "as_is") / "comparables.yaml"
        scenario_path.write_text(scenario_path.read_text(encoding="utf-8").replace("address: 100 Fictional Ave.", "address: 100 N. Fictional Ave.", 1), encoding="utf-8")

        canonical = RealEstateAssignmentStore(self.tmp).build(self.assignment_id).to_dict()
        universe = engine.build(self.assignment_id, scenario="as_is", overwrite=True)

        self.assertEqual(canonical["property_type"], "single_family_residential")
        self.assertNotEqual(canonical["property_type"], "other")
        self.assertFalse(any(item.field_name == "property_type" and item.comparable_id == "subject" for item in universe.conflicts))
        address_conflicts = [item for item in universe.conflicts if item.field_name == "address" and item.comparable_id == "subject"]
        self.assertEqual(len(address_conflicts), 1)
        self.assertEqual(address_conflicts[0].status, "open")
        self.assertEqual(universe.subject["address"], "100 N. Fictional Ave.")
        self.assertEqual(universe.subject["property_type"], "single_family_residential")
        property_detail = universe.subject_resolution["fields"]["property_type"]
        self.assertEqual(property_detail["selected_source"], "private_scenario_input")
        self.assertEqual(property_detail["conflict_status"], "none")
        canonical_provenance = next(item for item in property_detail["alternate_values"] if item["source"] == "canonical_assignment")
        self.assertEqual(canonical_provenance["value"], "Single Family")
        self.assertEqual(canonical_provenance["normalized_value"], "single_family_residential")
        self.assertEqual(universe.counts["comparable_count"], baseline.counts["comparable_count"])
        self.assertEqual({key: universe.counts.get(key, 0) for key in tier_keys}, baseline_tiers)
        self.assertFalse(review_path.exists())

    def test_review_state_is_scenario_specific_for_same_id(self) -> None:
        engine = ComparableIntelligenceEngine(self.tmp)
        engine.build(self.assignment_id, scenario="as_is", overwrite=True)
        engine.build(self.assignment_id, scenario="arv", overwrite=True)
        engine.select(self.assignment_id, "shared-comp", scenario="as_is", reviewer="tester", confirm=True)
        engine.build(self.assignment_id, scenario="as_is", overwrite=True)
        engine.build(self.assignment_id, scenario="arv", overwrite=True)
        self.assertTrue(next(item for item in engine.store.load(self.assignment_id, "as_is")["comparables"] if item["comparable_id"] == "shared-comp")["appraiser_selected"])
        self.assertFalse(next(item for item in engine.store.load(self.assignment_id, "arv")["comparables"] if item["comparable_id"] == "shared-comp")["appraiser_selected"])

    def test_single_scenario_resolves_without_explicit_selection(self) -> None:
        shutil.rmtree(ComparableStore(self.tmp).input_dir(self.assignment_id, "arv"))
        context = ComparableStore(self.tmp).resolve_scenario(self.assignment_id)
        self.assertEqual(context.resolved_scenario, "as_is")
        self.assertEqual(context.resolution_reason, "single_available_scenario")

    def test_invalid_scenario_ids_are_rejected(self) -> None:
        for value in ["../arv", "As_Is", "a/b", "a\\b", ""]:
            with self.subTest(value=value), self.assertRaises(ComparableIntelligenceError):
                validate_scenario_id(value)

    def test_distance_aliases_units_zero_and_conflict(self) -> None:
        self.assertEqual(normalize_distance_fields({"distance_miles": 0})[0], 0)
        self.assertAlmostEqual(normalize_distance_fields({"distance_from_subject": "1 km"})[0], 0.621371, places=6)
        self.assertAlmostEqual(normalize_distance_fields({"distance_from_subject": "528 feet"})[0], 0.1, places=6)
        self.assertIsNone(normalize_distance_fields({"distance_from_subject": 1})[0])
        value, provenance, conflicts = normalize_distance_fields({"distance_miles": 1, "distance_from_subject_miles": "1.0"})
        self.assertEqual(value, 1)
        self.assertFalse(conflicts)
        self.assertEqual(provenance["conflict_status"], "none")
        self.assertTrue(normalize_distance_fields({"distance_miles": 1, "distance_from_subject_miles": 2})[2])

    def test_distance_conflict_requires_review(self) -> None:
        path = ComparableStore(self.tmp).input_dir(self.assignment_id, "as_is") / "comparables.yaml"
        path.write_text(path.read_text(encoding="utf-8").replace("    distance_miles: 0.4", "    distance_miles: 0.4\n    distance_from_subject_miles: 1.4"), encoding="utf-8")
        universe = ComparableIntelligenceEngine(self.tmp).build(self.assignment_id, scenario="as_is", overwrite=True)
        record = next(item for item in universe.comparables if item.comparable_id == "shared-comp")
        self.assertEqual(record.candidate_status, "review_required")
        self.assertTrue(any(item.field_name == "distance_from_subject_miles" for item in universe.conflicts))

    def test_unresolved_identity_requires_review(self) -> None:
        path = ComparableStore(self.tmp).input_dir(self.assignment_id, "as_is") / "identity-missing.json"
        path.write_text(
            json.dumps(
                {
                    "comparables": [
                        {
                            "status": "closed_sale",
                            "sale_date": "2026-05-01",
                            "sale_price": 1000000,
                            "property_type": "single_family_residential",
                            "gross_living_area": 1400,
                            "distance_from_subject_miles": 0.5,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        universe = ComparableIntelligenceEngine(self.tmp).build(self.assignment_id, scenario="as_is", overwrite=True)
        record = next(item for item in universe.comparables if item.source_path == str(path))
        self.assertEqual(record.candidate_status, "review_required")

    def test_closed_sale_missing_price_is_insufficient(self) -> None:
        path = ComparableStore(self.tmp).input_dir(self.assignment_id, "as_is") / "price-missing.json"
        path.write_text(
            json.dumps(
                {
                    "comparables": [
                        {
                            "comparable_id": "price-missing",
                            "address": "105 Fictional Street",
                            "status": "closed_sale",
                            "sale_date": "2026-05-01",
                            "property_type": "single_family_residential",
                            "gross_living_area": 1400,
                            "distance_from_subject_miles": 0.5,
                        }
                    ]
                }
            ),
            encoding="utf-8",
        )
        universe = ComparableIntelligenceEngine(self.tmp).build(self.assignment_id, scenario="as_is", overwrite=True)
        record = next(item for item in universe.comparables if item.comparable_id == "price-missing")
        self.assertEqual(record.candidate_status, "insufficient_data")

    def test_dashboard_and_assignment_brief_are_scenario_specific(self) -> None:
        engine = ComparableIntelligenceEngine(self.tmp)
        as_is = engine.build(self.assignment_id, scenario="as_is", overwrite=True).to_dict()
        arv = engine.build(self.assignment_id, scenario="arv", overwrite=True).to_dict()
        summary = comparable_dashboard_summary([as_is, arv])
        self.assertEqual(summary["total_comparable_scenarios"], 2)
        self.assertEqual(summary["as_is_scenario_count"], 1)
        self.assertEqual(summary["arv_scenario_count"], 1)
        brief = _render_comparable_section(self.tmp, self.assignment_id)
        self.assertIn("### As-Is", brief)
        self.assertIn("### ARV", brief)

    def test_daily_fingerprints_scenarios_independently(self) -> None:
        store = ComparableStore(self.tmp)
        first = _comparable_input_checksums(store, [self.assignment_id])
        self.assertEqual(set(first), {f"{self.assignment_id}::as_is", f"{self.assignment_id}::arv"})
        path = store.input_dir(self.assignment_id, "as_is") / "comparables.yaml"
        path.write_text(path.read_text(encoding="utf-8") + "\n", encoding="utf-8")
        second = _comparable_input_checksums(store, [self.assignment_id])
        self.assertNotEqual(first[f"{self.assignment_id}::as_is"], second[f"{self.assignment_id}::as_is"])
        self.assertEqual(first[f"{self.assignment_id}::arv"], second[f"{self.assignment_id}::arv"])

    def test_rebuild_preserves_review_state_and_is_idempotent(self) -> None:
        engine = ComparableIntelligenceEngine(self.tmp)
        first = engine.build(self.assignment_id, scenario="as_is", overwrite=True)
        engine.select(self.assignment_id, "shared-comp", scenario="as_is", confirm=True)
        second = engine.build(self.assignment_id, scenario="as_is", overwrite=True)
        third = engine.build(self.assignment_id, scenario="as_is", overwrite=True)
        self.assertEqual(second.counts, third.counts)
        self.assertTrue(next(item for item in third.comparables if item.comparable_id == "shared-comp").appraiser_selected)
        self.assertEqual([item.comparable_id for item in first.comparables], [item.comparable_id for item in third.comparables])


class ComparableLegacyScenarioTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="comparable-legacy-test-"))
        self.assignment_id = "legacy-fictional-assignment"
        directory = self.tmp / "real-estate" / "assignments" / self.assignment_id
        directory.mkdir(parents=True)
        (directory / "assignment.yaml").write_text("assignment:\n  assignment_id: legacy-fictional-assignment\n  property_type: single_family_residential\n", encoding="utf-8")
        comp_dir = directory / "comparables"
        comp_dir.mkdir()
        self.legacy = comp_dir / "comparables.yaml"
        self.legacy.write_text("assignment_id: legacy-fictional-assignment\nsubject:\n  gross_living_area: 1400\ncomparables: []\n", encoding="utf-8")

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_legacy_defaults_without_scenario_inference(self) -> None:
        context = ComparableStore(self.tmp).resolve_scenario(self.assignment_id)
        self.assertEqual(context.resolved_scenario, "default")
        self.assertFalse(context.legacy_fallback_used)

    def test_explicit_legacy_fallback_records_requested_scenario(self) -> None:
        context = ComparableStore(self.tmp).resolve_scenario(self.assignment_id, "as_is")
        self.assertEqual(context.resolved_scenario, "as_is")
        self.assertTrue(context.legacy_fallback_used)

    def test_initialize_from_legacy_preserves_original_and_receipt(self) -> None:
        store = ComparableStore(self.tmp)
        before = self.legacy.read_bytes()
        receipt = store.initialize_from_legacy(self.assignment_id, "as_is", confirm=True)
        target = store.input_dir(self.assignment_id, "as_is") / "comparables.yaml"
        self.assertEqual(self.legacy.read_bytes(), before)
        self.assertIn("valuation_scenario: as_is", target.read_text(encoding="utf-8"))
        self.assertTrue((target.parent / "migration-receipt.json").exists())
        self.assertEqual(receipt["source_checksum"], __import__("hashlib").sha256(before).hexdigest())
        with self.assertRaises(ComparableIntelligenceError):
            store.initialize_from_legacy(self.assignment_id, "as_is", confirm=True)

    def test_initialize_requires_confirmation(self) -> None:
        with self.assertRaises(ComparableIntelligenceError):
            ComparableStore(self.tmp).initialize_from_legacy(self.assignment_id, "as_is")


if __name__ == "__main__":
    unittest.main()
