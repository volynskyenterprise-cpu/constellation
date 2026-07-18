from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from constellation.comparable_intelligence import (
    ComparableIntelligenceEngine,
    ComparableStore,
    code_number,
    load_comparable_file,
    normalize_address,
    normalize_date,
    normalize_status,
    to_number,
)


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
    address: 524 Laurel Avenue
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
        engine.reset_review(self.assignment_id, "comp-002")
        state = engine.store.load_review_state(self.assignment_id)
        self.assertNotIn("comp-002", state["comparables"])

    def test_idempotent_rebuild(self) -> None:
        engine = ComparableIntelligenceEngine(self.tmp)
        first = engine.build(self.assignment_id, overwrite=True).to_dict()
        second = engine.build(self.assignment_id, overwrite=True).to_dict()
        self.assertEqual(first["counts"], second["counts"])
        self.assertEqual([item["comparable_id"] for item in first["comparables"]], [item["comparable_id"] for item in second["comparables"]])


if __name__ == "__main__":
    unittest.main()
