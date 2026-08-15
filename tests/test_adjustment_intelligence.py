from __future__ import annotations

import json
import io
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from constellation.adjustment_intelligence import (
    AdjustmentIntelligenceEngine,
    AdjustmentIntelligenceError,
    AdjustmentStore,
    _aggregate,
    _application_amount,
    _difference,
    _indication,
    _round_to,
)
from constellation.io import read_json, write_json
from constellation.cli import main
from constellation.real_estate import _render_adjustment_section
from constellation.real_estate_daily import _adjustment_input_checksums


class AdjustmentIntelligenceTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.assignment_id = "fictional-adjustment-001"
        self.scenario = "as_is"
        self.store = AdjustmentStore(self.root)
        self.engine = AdjustmentIntelligenceEngine(self.root)
        self._write_comparable_universe(self.scenario)
        self._write_evidence(self.scenario)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write_comparable_universe(self, scenario: str) -> None:
        subject_values = {
            "property_type": "single_family_residential",
            "gross_living_area": 1500,
            "lot_size": 6000,
            "bedroom_count": 4,
            "bathroom_count": 3,
            "condition": "C2",
            "quality": "Q3",
            "garage_count": 2,
            "parking_count": 2,
            "pool": True,
            "spa": False,
            "view": "residential",
            "design_style": "two story",
            "effective_age": 10,
            "accessory_unit": False,
            "unit_count": 1,
            "sale_or_effective_date": "2026-07-01",
        }
        fields = {key: {"normalized_value": value} for key, value in subject_values.items()}
        comparables = [
            {
                "comparable_id": "fictional-comp-001",
                "sale_price": 1_800_000,
                "sale_date": "2026-04-01",
                "gross_living_area": 1300,
                "lot_size": 5500,
                "bedroom_count": 3,
                "bathroom_count": 2,
                "condition": "C3",
                "quality": "Q3",
                "garage_count": 1,
                "parking_count": 2,
                "pool": False,
                "spa": False,
                "view": "residential",
                "design_style": "one story",
                "effective_age": 20,
                "accessory_unit": False,
                "unit_count": 1,
                "concessions": "",
            },
            {
                "comparable_id": "fictional-comp-002",
                "sale_price": 1_950_000,
                "sale_date": "2026-05-01",
                "gross_living_area": 1700,
                "lot_size": 6500,
                "bedroom_count": 5,
                "bathroom_count": 4,
                "condition": "C1",
                "quality": "Q2",
                "garage_count": 3,
                "parking_count": 3,
                "pool": True,
                "spa": True,
                "view": "city",
                "design_style": "two story",
                "effective_age": 5,
                "accessory_unit": True,
                "unit_count": 2,
                "concessions": "none",
            },
            {
                "comparable_id": "fictional-comp-003",
                "sale_price": 1_725_000,
                "sale_date": "2026-03-15",
                "gross_living_area": 1450,
                "lot_size": 5750,
                "bedroom_count": 4,
                "bathroom_count": 3,
                "condition": "C2",
                "quality": "Q3",
                "garage_count": 2,
                "parking_count": 2,
                "pool": False,
                "spa": False,
                "view": "residential",
                "design_style": "two story",
                "effective_age": 12,
                "accessory_unit": False,
                "unit_count": 1,
                "concessions": "none",
            },
            {
                "comparable_id": "fictional-comp-004",
                "sale_price": 2_050_000,
                "sale_date": "2026-02-01",
                "gross_living_area": 1550,
                "lot_size": 6250,
                "bedroom_count": 4,
                "bathroom_count": 3.5,
                "condition": "C2",
                "quality": "Q3",
                "garage_count": 2,
                "parking_count": 2,
                "pool": True,
                "spa": False,
                "view": "residential",
                "design_style": "two story",
                "effective_age": 8,
                "accessory_unit": False,
                "unit_count": 1,
                "concessions": "none",
            },
        ]
        output = self.root / "outputs" / "real-estate" / "assignments" / self.assignment_id / "comparables" / "scenarios" / scenario
        write_json(
            output / "comparable-universe.json",
            {
                "assignment_id": self.assignment_id,
                "valuation_scenario": scenario,
                "subject": subject_values,
                "subject_resolution": {"fields": fields},
                "comparables": comparables,
                "provenance": {"input_fingerprint": f"fictional-{scenario}-fingerprint"},
            },
        )

    def _write_evidence(self, scenario: str, *, include_pairs: bool = True) -> Path:
        path = self.store.input_path(self.assignment_id, scenario)
        path.parent.mkdir(parents=True, exist_ok=True)
        pairs = ""
        if include_pairs:
            pairs = """
      - evidence_id: fictional-gla-pair-001
        method: matched_pair
        source_type: appraiser_verified_pair
        source_path: sources/fictional-pairs.csv
        verification_status: appraiser_verified
        governed_pair: true
        difference:
          gross_living_area: 200
        price_difference: 60000
      - evidence_id: fictional-gla-pair-002
        method: matched_pair
        source_type: appraiser_verified_pair
        source_path: sources/fictional-pairs.csv
        verification_status: appraiser_verified
        governed_pair: true
        difference:
          gross_living_area: 200
        price_difference: 50000
      - evidence_id: fictional-gla-pair-003
        method: matched_pair
        source_type: appraiser_verified_pair
        source_path: sources/fictional-pairs.csv
        verification_status: appraiser_verified
        governed_pair: true
        difference:
          gross_living_area: 200
        price_difference: 70000
"""
        path.write_text(
            f"""assignment_id: {self.assignment_id}
valuation_scenario: {scenario}

rounding:
  adjustment_amount_nearest: 100

adjustment_evidence:
  gross_living_area:
    candidate_rates:
      - 250
      - 300
      - 350
    evidence:{pairs if pairs else ' []'}
  lot_size:
    evidence:
      - evidence_id: fictional-lot-001
        method: appraiser_entered_support
        source_path: sources/fictional-lot-study.csv
        verification_status: appraiser_verified
        indication:
          value: 10
          unit: dollars_per_square_foot
      - evidence_id: fictional-lot-002
        method: market_extraction
        source_path: sources/fictional-lot-study.csv
        verification_status: appraiser_verified
        indication:
          value: 12
          unit: dollars_per_square_foot
  pool:
    evidence:
      - evidence_id: fictional-pool-context
        method: informational_reference
        source_path: sources/fictional-pool-note.txt
        evidence_classification: contextual_reference
        indication:
          value: 50000
          unit: dollars
  condition:
    evidence:
      - evidence_id: fictional-grid-reference
        method: appraiser_entered_support
        source_type: appraisal_grid
        source_path: sources/fictional-grid.csv
        verification_status: appraiser_verified
        indication:
          value: 25000
          unit: dollars_per_step
""",
            encoding="utf-8",
        )
        return path

    def _write_source_grid_reference(
        self,
        *,
        source_subject_gla: float | None = 1500,
        explicit_rate: float | None = 325,
        rows: list[tuple[str, float, float, str | None]] | None = None,
        source_scenario: str = "as_is",
        evidence_scenario: str = "as_is",
        evidence_classification: str = "appraiser_decision_reference",
        source_property_type: str | None = None,
        absolute_tolerance: float = 1.0,
        relative_tolerance_percent: float = 1.0,
    ) -> Path:
        rows = rows if rows is not None else [("supplemental-source-1", 1300, 65000, None)]
        subject_lines = []
        if source_subject_gla is not None:
            subject_lines.append(f"            gross_living_area: {source_subject_gla}")
        if source_property_type is not None:
            subject_lines.append(f"            property_type: {source_property_type}")
        row_lines = []
        for source_id, gla, amount, governed_id in rows:
            row_lines.extend(
                [
                    f"            - source_comparable_id: {source_id}",
                    *( [f"              governed_comparable_id: {governed_id}"] if governed_id else [] ),
                    f"              gross_living_area: {gla}",
                    f"              displayed_adjustment_amount: {amount}",
                ]
            )
        displayed_rate = f"            explicit_rate: {explicit_rate}" if explicit_rate is not None else ""
        path = self.store.input_path(self.assignment_id, self.scenario)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"""assignment_id: {self.assignment_id}
valuation_scenario: {self.scenario}
source_rate_consistency:
  absolute_tolerance: {absolute_tolerance}
  relative_tolerance_percent: {relative_tolerance_percent}
adjustment_evidence:
  gross_living_area:
    evidence:
      - evidence_id: fictional-source-grid-reference
        method: informational_reference
        source_type: appraisal_grid_export
        source_path: sources/fictional-grid.pdf
        source_page: 12
        source_location: Supplemental fictional grid, living area row
        source_checksum: fictional-checksum
        verification_status: source_reported
        evidence_classification: {evidence_classification}
        valuation_scenario: {evidence_scenario}
        source_grid:
          valuation_scenario: {source_scenario}
          subject:
{chr(10).join(subject_lines) if subject_lines else '            unavailable: null'}
          comparables:
{chr(10).join(row_lines)}
          displayed_adjustment:
            factor: gross_living_area
{displayed_rate}
            unit: dollars_per_square_foot
""",
            encoding="utf-8",
        )
        return path

    def test_numeric_differences_use_subject_minus_comparable_sign(self) -> None:
        positive = _difference("gross_living_area", 1500, 1300, {}, {})
        negative = _difference("gross_living_area", 1500, 1700, {}, {})
        equal = _difference("gross_living_area", 1500, 1500, {}, {})
        self.assertEqual(positive[0], 200)
        self.assertEqual(negative[0], -200)
        self.assertEqual(equal[0], 0)

    def test_ordinal_and_categorical_differences_are_deterministic(self) -> None:
        self.assertEqual(_difference("condition", "C2", "C3", {}, {})[0], 1)
        self.assertEqual(_difference("quality", "Q3", "Q2", {}, {})[0], -1)
        self.assertEqual(_difference("pool", True, False, {}, {})[0], 1)
        self.assertEqual(_difference("pool", False, True, {}, {})[0], -1)

    def test_unavailable_difference_is_not_an_adjustment(self) -> None:
        value, status, _ = _difference("gross_living_area", 1500, None, {}, {})
        self.assertIsNone(value)
        self.assertEqual(status, "unavailable")

    def test_approved_pair_calculates_raw_indication(self) -> None:
        indication, issue = _indication(
            {
                "evidence_id": "pair-001",
                "factor": "gross_living_area",
                "method": "matched_pair",
                "valuation_scenario": "as_is",
                "governed_pair": True,
                "verification_status": "appraiser_verified",
                "difference": {"gross_living_area": 200},
                "price_difference": 60000,
                "source_paths": ["sources/fictional.csv"],
            },
            {},
        )
        self.assertIsNone(issue)
        self.assertEqual(indication["amount"], 300)
        self.assertIn("does not prove causality", " ".join(indication["limitations"]))

    def test_unapproved_pair_remains_potential_pair(self) -> None:
        indication, issue = _indication(
            {"evidence_id": "pair", "factor": "gross_living_area", "method": "matched_pair", "valuation_scenario": "as_is", "difference": {"gross_living_area": 200}, "price_difference": 60000, "source_paths": []},
            {},
        )
        self.assertIsNone(indication)
        self.assertEqual(issue[0], "unapproved_potential_pair")

    def test_zero_pair_denominator_is_review_required(self) -> None:
        indication, issue = _indication(
            {"evidence_id": "pair", "factor": "gross_living_area", "method": "matched_pair", "valuation_scenario": "as_is", "governed_pair": True, "difference": {"gross_living_area": 0}, "price_difference": 10, "source_paths": []},
            {},
        )
        self.assertIsNone(indication)
        self.assertEqual(issue[0], "zero_pair_denominator")

    def test_grouped_comparison_reports_observed_difference(self) -> None:
        indication, issue = _indication(
            {"evidence_id": "group", "factor": "pool", "method": "grouped_comparison", "valuation_scenario": "as_is", "group_a": {"values": [100, 120, 110]}, "group_b": {"values": [80, 90, 85]}, "source_paths": []},
            {},
        )
        self.assertIsNone(issue)
        self.assertEqual(indication["amount"], 25)

    def test_aggregation_preserves_outliers_and_statistics(self) -> None:
        indications = [{"factor": "gross_living_area", "unit": "dollars_per_square_foot", "amount": value, "indication_id": str(value)} for value in [250, 300, 800]]
        ranges, _, reviews = _aggregate(indications)
        self.assertEqual(ranges[0]["minimum"], 250)
        self.assertEqual(ranges[0]["maximum"], 800)
        self.assertFalse(ranges[0]["outliers_discarded"])
        self.assertTrue(any(item["item_type"] == "high_dispersion" for item in reviews))

    def test_mixed_units_are_not_aggregated(self) -> None:
        ranges, conflicts, _ = _aggregate([
            {"factor": "pool", "unit": "dollars", "amount": 10, "indication_id": "a"},
            {"factor": "pool", "unit": "percent", "amount": 1, "indication_id": "b"},
        ])
        self.assertEqual(ranges, [])
        self.assertEqual(conflicts[0]["conflict_type"], "incompatible_units")

    def test_build_calculates_ranges_without_selecting_rate(self) -> None:
        analysis = self.engine.build(self.assignment_id, scenario=self.scenario).to_dict()
        self.assertEqual(analysis["counts"]["indication_count"], 5)
        self.assertEqual(analysis["counts"]["factors_with_selected_decisions"], 0)
        self.assertEqual(analysis["applications"], [])
        gla_range = next(item for item in analysis["ranges"] if item["factor"] == "gross_living_area")
        self.assertEqual((gla_range["minimum"], gla_range["median"], gla_range["maximum"]), (250, 300, 350))

    def test_circular_grid_reference_is_not_independent_support(self) -> None:
        analysis = self.engine.build(self.assignment_id, scenario=self.scenario).to_dict()
        grid = next(item for item in analysis["evidence"] if item["evidence_id"] == "fictional-grid-reference")
        self.assertEqual(grid["evidence_classification"], "appraiser_decision_reference")
        self.assertFalse(any(item["factor"] == "condition" for item in analysis["indications"]))
        self.assertTrue(any(item["item_type"] == "circular_evidence_guard" for item in analysis["review_queue"]))

    def test_source_grid_mixed_scenario_and_rate_conflicts_remain_references(self) -> None:
        self._write_source_grid_reference(
            source_subject_gla=4600,
            explicit_rate=150,
            rows=[
                ("fictional-grid-1", 3200, 455000, None),
                ("fictional-grid-2", 2500, 682500, None),
                ("fictional-grid-3", 2600, 650000, None),
            ],
        )
        analysis = self.engine.build(self.assignment_id, scenario=self.scenario).to_dict()
        reference = analysis["evidence"][0]
        conflicts = {item["conflict_type"]: item for item in analysis["conflicts"]}
        self.assertEqual(reference["evidence_classification"], "appraiser_decision_reference")
        self.assertEqual(reference["decision_reference_usability"], "scenario_and_source_inconsistent")
        self.assertEqual(reference["valuation_scenario"], "as_is")
        self.assertEqual(reference["source_grid"]["subject"]["gross_living_area"], "4600")
        self.assertEqual(set(conflicts), {"scenario_mismatch", "source_internal_inconsistency"})
        self.assertEqual(conflicts["scenario_mismatch"]["severity"], "high")
        self.assertEqual(conflicts["scenario_mismatch"]["resolved_scenario_value"], 1500)
        self.assertEqual(conflicts["scenario_mismatch"]["source_grid_value"], 4600)
        self.assertEqual(conflicts["source_internal_inconsistency"]["derived_diagnostic_rates"], [325, 325, 325])
        self.assertEqual(analysis["counts"]["indication_count"], 0)
        self.assertEqual(analysis["counts"]["factors_with_selected_decisions"], 0)
        self.assertEqual(analysis["applications"], [])
        self.assertNotIn("market_value", analysis)
        self.assertTrue(all(item["evidence_id"] == "fictional-source-grid-reference" for item in analysis["conflicts"]))

    def test_clean_and_rounded_source_rates_remain_conflict_free(self) -> None:
        for amount, classification in ((65000, "appraiser_decision_reference"), (65040, "derived_appraiser_decision_reference")):
            with self.subTest(amount=amount, classification=classification):
                self._write_source_grid_reference(explicit_rate=325, rows=[("fictional-grid-1", 1300, amount, None)], evidence_classification=classification)
                analysis = self.engine.build(self.assignment_id, scenario=self.scenario, overwrite=bool(self.store.load(self.assignment_id, self.scenario))).to_dict()
                reference = analysis["evidence"][0]
                self.assertEqual(reference["source_grid_resolution"]["scenario_consistency"]["status"], "aligned")
                self.assertEqual(reference["source_grid_resolution"]["rate_consistency"]["status"], "aligned")
                self.assertEqual(analysis["conflicts"], [])
                self.assertEqual(reference["evidence_classification"], classification)

    def test_property_type_mismatch_is_detected_without_inferred_missing_gla(self) -> None:
        self._write_source_grid_reference(source_subject_gla=None, explicit_rate=None, rows=[], source_property_type="duplex")
        analysis = self.engine.build(self.assignment_id, scenario=self.scenario).to_dict()
        reference = analysis["evidence"][0]
        comparisons = reference["source_grid_resolution"]["scenario_consistency"]["field_comparisons"]
        self.assertEqual([item["field"] for item in comparisons], ["property_type"])
        self.assertEqual(comparisons[0]["status"], "mismatch")
        self.assertEqual([item["conflict_type"] for item in analysis["conflicts"]], ["scenario_mismatch"])
        self.assertNotIn("gross_living_area", [item["field"] for item in comparisons])

    def test_multiple_inconsistent_derived_rates_and_zero_denominator_are_reviewable(self) -> None:
        self._write_source_grid_reference(
            explicit_rate=325,
            rows=[
                ("fictional-grid-1", 1300, 65000, None),
                ("fictional-grid-2", 1400, 40000, None),
                ("fictional-grid-zero", 1500, 1000, None),
            ],
        )
        analysis = self.engine.build(self.assignment_id, scenario=self.scenario).to_dict()
        rate = analysis["evidence"][0]["source_grid_resolution"]["rate_consistency"]
        self.assertEqual(rate["derived_rate_summary"]["count"], 2)
        self.assertFalse(rate["derived_rate_summary"]["mutually_consistent_within_tolerance"])
        self.assertEqual(rate["calculations"][2]["status"], "zero_difference")
        self.assertTrue(any(item["item_type"] == "source_grid_zero_difference" for item in analysis["review_queue"]))
        self.assertTrue(any(item["conflict_type"] == "source_internal_inconsistency" for item in analysis["conflicts"]))

    def test_source_grid_sign_handling_preserves_negative_row_arithmetic(self) -> None:
        self._write_source_grid_reference(explicit_rate=325, rows=[("fictional-grid-superior", 1700, -65000, None)])
        analysis = self.engine.build(self.assignment_id, scenario=self.scenario).to_dict()
        calculation = analysis["evidence"][0]["source_grid_resolution"]["rate_consistency"]["calculations"][0]
        self.assertEqual(calculation["difference"], -200)
        self.assertEqual(calculation["difference_sign"], "negative")
        self.assertEqual(calculation["adjustment_sign"], "negative")
        self.assertEqual(calculation["derived_rate"], 325)
        self.assertEqual(analysis["conflicts"], [])

    def test_distinct_supplemental_comparable_set_is_administrative_only(self) -> None:
        self._write_source_grid_reference(rows=[("supplemental-a", 1300, 65000, None), ("supplemental-b", 1700, -65000, None)])
        analysis = self.engine.build(self.assignment_id, scenario=self.scenario).to_dict()
        comparable_set = analysis["evidence"][0]["source_grid_resolution"]["comparable_set"]
        self.assertEqual(comparable_set["status"], "distinct_source_set")
        self.assertFalse(comparable_set["automatic_import"])
        self.assertFalse(any(item["item_type"] == "unresolved_governed_comparable_link" for item in analysis["review_queue"]))
        self.assertEqual(analysis["indications"], [])
        self._write_source_grid_reference(rows=[("supplemental-a", 1300, 65000, "missing-governed-id")])
        claimed = self.engine.build(self.assignment_id, scenario=self.scenario, overwrite=True).to_dict()
        self.assertTrue(any(item["item_type"] == "unresolved_governed_comparable_link" for item in claimed["review_queue"]))
        self.assertEqual(claimed["indications"], [])

    def test_declared_textual_scenario_mismatch_remains_conflict_and_review(self) -> None:
        self._write_source_grid_reference(source_scenario="arv", evidence_scenario="arv")
        analysis = self.engine.build(self.assignment_id, scenario=self.scenario).to_dict()
        self.assertEqual([item["conflict_type"] for item in analysis["conflicts"]], ["scenario_mismatch"])
        self.assertTrue(any(item["item_type"] == "scenario_mismatch" for item in analysis["review_queue"]))
        self.assertEqual(analysis["indications"], [])

    def test_legacy_top_level_grid_fields_receive_consistency_validation(self) -> None:
        path = self.store.input_path(self.assignment_id, self.scenario)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            f"""assignment_id: {self.assignment_id}
valuation_scenario: as_is
adjustment_evidence:
  gross_living_area:
    evidence:
      - evidence_id: fictional-legacy-grid
        method: informational_reference
        source_type: appraisal_grid_export
        source_path: sources/fictional-legacy-grid.pdf
        valuation_scenario: as_is
        explicit_displayed_rate: 150
        rate_unit: dollars_per_square_foot
        grid_subject_gross_living_area: 4600
        grid_entries:
          - source_comparable_id: fictional-source-1
            comparable_gross_living_area: 3200
            displayed_adjustment_amount: 455000
""",
            encoding="utf-8",
        )
        analysis = self.engine.build(self.assignment_id, scenario=self.scenario).to_dict()
        reference = analysis["evidence"][0]
        self.assertEqual(reference["source_grid_resolution"]["schema_origin"], "legacy_top_level_grid_fields")
        self.assertEqual(reference["decision_reference_usability"], "scenario_and_source_inconsistent")
        self.assertEqual({item["conflict_type"] for item in analysis["conflicts"]}, {"scenario_mismatch", "source_internal_inconsistency"})

    def test_decision_reference_integrity_is_reported_without_market_support(self) -> None:
        self._write_source_grid_reference(source_subject_gla=4600, explicit_rate=150, rows=[("fictional-grid-1", 3200, 455000, None)])
        self.engine.build(self.assignment_id, scenario=self.scenario)
        output = self.store.output_dir(self.assignment_id, self.scenario)
        analysis_text = (output / "adjustment-analysis.md").read_text(encoding="utf-8")
        support_text = (output / "adjustment-support.md").read_text(encoding="utf-8")
        review_text = (output / "adjustment-review-queue.md").read_text(encoding="utf-8")
        conflicts = read_json(output / "adjustment-conflicts.json")["conflicts"]
        self.assertIn("Existing Appraisal Decision-Reference Integrity", analysis_text)
        self.assertIn("scenario_and_source_inconsistent", analysis_text)
        self.assertIn("No independent market support is generated", support_text)
        self.assertIn("scenario_mismatch", review_text)
        self.assertTrue(all(item["status"] == "open" for item in conflicts))
        self.assertNotIn("Recommended adjustment", analysis_text)

    def test_source_integrity_conflicts_are_deterministic_and_noop_stable(self) -> None:
        self._write_source_grid_reference(source_subject_gla=4600, explicit_rate=150, rows=[("fictional-grid-1", 3200, 455000, None)])
        first = self.engine.build(self.assignment_id, scenario=self.scenario).to_dict()
        output = self.store.output_dir(self.assignment_id, self.scenario)
        first_ids = [item["conflict_id"] for item in first["conflicts"]]
        history_before = (output / "adjustment-history.json").read_bytes()
        decisions_before = (output / "adjustment-decisions.json").read_bytes()
        decision_mtime_before = (output / "adjustment-decisions.json").stat().st_mtime_ns
        second = self.engine.build(self.assignment_id, scenario=self.scenario, overwrite=True).to_dict()
        self.assertEqual(first_ids, [item["conflict_id"] for item in second["conflicts"]])
        self.assertEqual(len(first_ids), len(set(first_ids)))
        self.assertEqual(history_before, (output / "adjustment-history.json").read_bytes())
        self.assertEqual(decisions_before, (output / "adjustment-decisions.json").read_bytes())
        self.assertEqual(decision_mtime_before, (output / "adjustment-decisions.json").stat().st_mtime_ns)
        self.assertEqual(second["counts"]["factors_with_selected_decisions"], 0)
        self.assertEqual(second["applications"], [])

    def test_explicit_selection_applies_positive_and_negative_signs(self) -> None:
        with self.assertRaises(AdjustmentIntelligenceError):
            self.engine.set_decision(self.assignment_id, "gross_living_area", scenario=self.scenario, status="selected", value=300, unit="dollars_per_square_foot", reason="Supported by fictional evidence.")
        self.engine.set_decision(self.assignment_id, "gross_living_area", scenario=self.scenario, status="selected", value=300, unit="dollars_per_square_foot", reason="Supported by fictional evidence.", confirm=True)
        analysis = self.engine.build(self.assignment_id, scenario=self.scenario).to_dict()
        amounts = {item["comparable_id"]: item["raw_adjustment"] for item in analysis["applications"] if item["factor"] == "gross_living_area"}
        self.assertEqual(amounts["fictional-comp-001"], 60000)
        self.assertEqual(amounts["fictional-comp-002"], -60000)
        self.assertGreater(len(analysis["diagnostics"]), 0)

    def test_no_adjustment_and_reset_are_explicit_and_scenario_isolated(self) -> None:
        self._write_comparable_universe("arv")
        self._write_evidence("arv", include_pairs=False)
        self.engine.set_decision(self.assignment_id, "pool", scenario="arv", status="no_adjustment", reason="Fictional evidence did not support an adjustment.", confirm=True)
        self.assertEqual(self.store.load_decisions(self.assignment_id, "arv")["decisions"]["pool"]["status"], "no_adjustment")
        self.assertEqual(self.store.load_decisions(self.assignment_id, "as_is")["decisions"], {})
        self.engine.reset_decision(self.assignment_id, "pool", scenario="arv", confirm=True)
        self.assertNotIn("pool", self.store.load_decisions(self.assignment_id, "arv")["decisions"])

    def test_percentage_time_and_rounding_arithmetic(self) -> None:
        self.assertEqual(_application_amount("percentage", 1, 0.05, {"sale_price": 1_000_000}), 50_000)
        self.assertEqual(_application_amount("time_percentage", 3, 0.01, {"sale_price": 1_000_000}), 30_000)
        self.assertEqual(_round_to(53_249, 100), 53_200)
        self.assertEqual(_round_to(-53_249, 100), -53_200)
        months, status, reason = _difference("market_conditions", None, None, {"effective_date": "2026-07-01"}, {"sale_date": "2026-04-01"})
        self.assertEqual(status, "available")
        self.assertGreater(months, 2.9)
        self.assertIn("no compounding", reason)

    def test_sensitivity_has_no_automatic_winner(self) -> None:
        analysis = self.engine.build(self.assignment_id, scenario=self.scenario).to_dict()
        self.assertEqual([item["candidate_rate"] for item in analysis["sensitivity"]], [250, 300, 350])
        self.assertTrue(all(item["automatic_winner"] is None for item in analysis["sensitivity"]))

    def test_reports_preserve_professional_boundaries(self) -> None:
        self.engine.build(self.assignment_id, scenario=self.scenario)
        output = self.store.output_dir(self.assignment_id, self.scenario)
        analysis_text = (output / "adjustment-analysis.md").read_text(encoding="utf-8")
        support_text = (output / "adjustment-support.md").read_text(encoding="utf-8")
        self.assertIn("does not select a final adjustment rate", analysis_text)
        self.assertIn("No appraiser-selected adjustment is recorded", support_text)
        self.assertNotIn("Recommended adjustment", analysis_text)

    def test_idempotent_build_preserves_history_and_decision_state(self) -> None:
        self.engine.build(self.assignment_id, scenario=self.scenario)
        output = self.store.output_dir(self.assignment_id, self.scenario)
        first_history = (output / "adjustment-history.json").read_bytes()
        self.engine.build(self.assignment_id, scenario=self.scenario, overwrite=True)
        self.assertEqual(first_history, (output / "adjustment-history.json").read_bytes())
        history = read_json(output / "adjustment-history.json")["snapshots"]
        self.assertEqual(len(history), 1)

    def test_template_is_private_scenario_specific_and_nonselecting(self) -> None:
        other = "custom_scenario"
        path = self.store.create_template(self.assignment_id, other)
        text = path.read_text(encoding="utf-8")
        self.assertIn("valuation_scenario: custom_scenario", text)
        self.assertNotIn("selected", text)

    def test_selected_rate_outside_range_is_reviewable_not_blocked(self) -> None:
        self.engine.set_decision(self.assignment_id, "gross_living_area", scenario=self.scenario, status="selected", value=500, unit="dollars_per_square_foot", reason="Explicit fictional appraiser decision.", confirm=True)
        analysis = self.engine.build(self.assignment_id, scenario=self.scenario).to_dict()
        self.assertTrue(any(item["conflict_type"] == "selected_rate_outside_evidence_range" for item in analysis["conflicts"]))
        self.assertTrue(any(item["item_type"] == "selected_rate_outside_evidence_range" for item in analysis["review_queue"]))
        self.assertEqual(analysis["decisions"]["decisions"]["gross_living_area"]["adjustment_value"], 500)

    def test_adjustment_summary_exposes_administrative_counts_only(self) -> None:
        self.engine.build(self.assignment_id, scenario=self.scenario)
        summary = self.store.summary()
        self.assertEqual(summary["assignments_with_adjustment_intelligence"], 1)
        self.assertEqual(summary["total_adjustment_scenarios"], 1)
        self.assertEqual(summary["factors_with_evidence"], 4)
        self.assertNotIn("rates", summary)

    def test_assignment_brief_summary_keeps_scenarios_separate(self) -> None:
        self.engine.build(self.assignment_id, scenario=self.scenario)
        text = _render_adjustment_section(self.root, self.assignment_id)
        self.assertIn("### As Is", text)
        self.assertIn("Factors with evidence", text)
        self.assertIn("does not reconcile value", text)

    def test_daily_fingerprint_changes_only_with_adjustment_scenario_state(self) -> None:
        before = _adjustment_input_checksums(self.store, [self.assignment_id])
        self.engine.set_decision(self.assignment_id, "pool", scenario=self.scenario, status="no_adjustment", reason="Explicit fictional decision.", confirm=True)
        after = _adjustment_input_checksums(self.store, [self.assignment_id])
        self.assertEqual(set(before), {f"{self.assignment_id}::{self.scenario}"})
        self.assertNotEqual(before, after)

    def test_missing_provenance_remains_review_required(self) -> None:
        path = self.store.input_path(self.assignment_id, self.scenario)
        text = path.read_text(encoding="utf-8").replace("        source_path: sources/fictional-pairs.csv\n", "", 1)
        path.write_text(text, encoding="utf-8")
        analysis = self.engine.build(self.assignment_id, scenario=self.scenario).to_dict()
        self.assertTrue(any(item["item_type"] == "missing_provenance" for item in analysis["review_queue"]))

    def test_cli_build_and_diagnostics_are_scenario_specific(self) -> None:
        output = io.StringIO()
        with redirect_stdout(output):
            result = main(["real-estate", "--root", str(self.root), "adjustments", "build", self.assignment_id, "--scenario", self.scenario])
        self.assertEqual(result, 0)
        self.assertIn("valuation_scenario: as_is", output.getvalue())
        output = io.StringIO()
        with redirect_stdout(output):
            result = main(["real-estate", "--root", str(self.root), "adjustments", "indications", self.assignment_id, "--scenario", self.scenario])
        self.assertEqual(result, 0)
        self.assertIn("dollars_per_square_foot", output.getvalue())

    def test_cli_decision_requires_confirmation(self) -> None:
        with redirect_stdout(io.StringIO()):
            result = main(["real-estate", "--root", str(self.root), "adjustments", "select", self.assignment_id, "gross_living_area", "--scenario", self.scenario, "--value", "300", "--unit", "dollars_per_square_foot", "--reason", "Fictional evidence reviewed."])
        self.assertEqual(result, 1)
        with redirect_stdout(io.StringIO()):
            result = main(["real-estate", "--root", str(self.root), "adjustments", "select", self.assignment_id, "gross_living_area", "--scenario", self.scenario, "--value", "300", "--unit", "dollars_per_square_foot", "--reason", "Fictional evidence reviewed.", "--confirm"])
        self.assertEqual(result, 0)

    def test_explicit_local_csv_is_extracted_with_provenance(self) -> None:
        input_dir = self.store.input_dir(self.assignment_id, self.scenario)
        source = input_dir / "sources" / "fictional-adjustments.csv"
        source.parent.mkdir(parents=True, exist_ok=True)
        source.write_text(
            "factor,evidence_id,method,indication_value,unit,source_type,verification_status,evidence_classification\n"
            "gross_living_area,csv-gla-001,market_extraction,325,dollars_per_square_foot,local_market_export,appraiser_verified,independent_market_evidence\n",
            encoding="utf-8",
        )
        self.store.input_path(self.assignment_id, self.scenario).write_text(
            f"""assignment_id: {self.assignment_id}
valuation_scenario: {self.scenario}
evidence_sources:
  - path: sources/fictional-adjustments.csv
    source_type: local_market_export
    verification_status: appraiser_verified
    evidence_classification: independent_market_evidence
adjustment_evidence:
  gross_living_area:
    evidence: []
""",
            encoding="utf-8",
        )
        analysis = self.engine.build(self.assignment_id, scenario=self.scenario).to_dict()
        evidence = next(item for item in analysis["evidence"] if item["evidence_id"] == "csv-gla-001")
        indication = next(item for item in analysis["indications"] if item["evidence_ids"] == ["csv-gla-001"])
        self.assertEqual(evidence["source_paths"], ["sources/fictional-adjustments.csv"])
        self.assertTrue(evidence["source_checksum"])
        self.assertEqual(indication["amount"], 325)


if __name__ == "__main__":
    unittest.main()
