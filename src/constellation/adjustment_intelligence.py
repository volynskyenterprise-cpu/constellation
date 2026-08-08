from __future__ import annotations

import json
import math
import os
import statistics
import csv
from dataclasses import dataclass, field
from datetime import date, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from . import __version__
from .comparable_intelligence import ComparableStore, validate_scenario_id
from .io import read_json, write_json
from .models import JsonMap
from .real_estate import assignment_directory
from .simple_yaml import load_yaml


class AdjustmentIntelligenceError(RuntimeError):
    pass


EVIDENCE_METHODS = {
    "matched_pair",
    "grouped_comparison",
    "repeat_sale",
    "sensitivity_analysis",
    "market_extraction",
    "appraiser_entered_support",
    "external_study",
    "informational_reference",
}
DECISION_STATUSES = {"unreviewed", "selected", "deferred", "no_adjustment", "rejected"}
EVIDENCE_CLASSIFICATIONS = {
    "independent_market_evidence",
    "appraiser_decision_reference",
    "contextual_reference",
    "unsupported",
}
FACTOR_DEFINITIONS: JsonMap = {
    "market_conditions": {"field": "sale_date", "basis": "time_percentage", "unit": "percent_per_month"},
    "gross_living_area": {"field": "gross_living_area", "basis": "per_unit", "unit": "dollars_per_square_foot"},
    "lot_size": {"field": "lot_size", "basis": "per_unit", "unit": "dollars_per_square_foot"},
    "bedroom_count": {"field": "bedroom_count", "basis": "lump_sum", "unit": "dollars_per_bedroom"},
    "bathroom_count": {"field": "bathroom_count", "basis": "lump_sum", "unit": "dollars_per_bathroom"},
    "condition": {"field": "condition", "basis": "ordinal_step", "unit": "dollars_per_step"},
    "quality": {"field": "quality", "basis": "ordinal_step", "unit": "dollars_per_step"},
    "garage_count": {"field": "garage_count", "basis": "per_unit", "unit": "dollars_per_space"},
    "parking_count": {"field": "parking_count", "basis": "per_unit", "unit": "dollars_per_space"},
    "pool": {"field": "pool", "basis": "lump_sum", "unit": "dollars"},
    "spa": {"field": "spa", "basis": "lump_sum", "unit": "dollars"},
    "view": {"field": "view", "basis": "informational_only", "unit": "dollars"},
    "location": {"field": "location", "basis": "informational_only", "unit": "dollars"},
    "design_style": {"field": "design_style", "basis": "informational_only", "unit": "dollars"},
    "effective_age": {"field": "effective_age", "basis": "per_unit", "unit": "dollars_per_year"},
    "accessory_unit": {"field": "accessory_unit", "basis": "lump_sum", "unit": "dollars"},
    "unit_count": {"field": "unit_count", "basis": "lump_sum", "unit": "dollars_per_unit"},
    "concessions": {"field": "concessions", "basis": "lump_sum", "unit": "dollars"},
}
NUMERIC_FACTORS = {
    "gross_living_area",
    "lot_size",
    "bedroom_count",
    "bathroom_count",
    "garage_count",
    "parking_count",
    "effective_age",
    "unit_count",
}
CATEGORICAL_FACTORS = {"pool", "spa", "accessory_unit", "view", "location", "design_style", "concessions"}
ORDINAL_PREFIXES = {"condition": "c", "quality": "q"}


@dataclass(frozen=True)
class AdjustmentFactor:
    factor_id: str
    canonical_field: str
    label: str
    adjustment_basis: str
    unit: str
    directionality: str
    scenario_id: str
    enabled: bool = True
    configuration: JsonMap = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AdjustmentAnalysis:
    assignment_id: str
    valuation_scenario: str
    created_at: str
    version: str
    factors: list[JsonMap]
    differences: list[JsonMap]
    evidence: list[JsonMap]
    indications: list[JsonMap]
    ranges: list[JsonMap]
    decisions: JsonMap
    applications: list[JsonMap]
    sensitivity: list[JsonMap]
    diagnostics: list[JsonMap]
    conflicts: list[JsonMap]
    coverage: JsonMap
    review_queue: list[JsonMap]
    counts: JsonMap
    provenance: JsonMap
    limitations: list[str]

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


class AdjustmentStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def input_dir(self, assignment_id: str, scenario: str) -> Path:
        return assignment_directory(self.root, assignment_id) / "adjustments" / "scenarios" / validate_scenario_id(scenario)

    def input_path(self, assignment_id: str, scenario: str) -> Path:
        return self.input_dir(assignment_id, scenario) / "adjustment-evidence.yaml"

    def decision_path(self, assignment_id: str, scenario: str) -> Path:
        return self.input_dir(assignment_id, scenario) / "adjustment-decisions.json"

    def output_dir(self, assignment_id: str, scenario: str) -> Path:
        return self.root / "outputs" / "real-estate" / "assignments" / assignment_id / "adjustments" / "scenarios" / validate_scenario_id(scenario)

    def scenario_ids(self, assignment_id: str) -> list[str]:
        base = assignment_directory(self.root, assignment_id) / "adjustments" / "scenarios"
        if not base.exists():
            return []
        return sorted(path.name for path in base.iterdir() if path.is_dir() and self.input_path(assignment_id, path.name).exists())

    def load_input(self, assignment_id: str, scenario: str) -> JsonMap:
        path = self.input_path(assignment_id, scenario)
        if not path.exists():
            raise AdjustmentIntelligenceError(f"No adjustment evidence exists for scenario '{scenario}'.")
        data = load_yaml(path)
        declared = _text(data.get("valuation_scenario"))
        if declared and declared != scenario:
            raise AdjustmentIntelligenceError(f"Adjustment evidence declares scenario '{declared}', not '{scenario}'.")
        return data

    def load(self, assignment_id: str, scenario: str) -> JsonMap:
        path = self.output_dir(assignment_id, scenario) / "adjustment-analysis.json"
        return read_json(path) if path.exists() else {}

    def load_decisions(self, assignment_id: str, scenario: str) -> JsonMap:
        path = self.decision_path(assignment_id, scenario)
        if not path.exists():
            return {"assignment_id": assignment_id, "valuation_scenario": scenario, "decisions": {}, "history": []}
        return read_json(path)

    def save_decisions(self, assignment_id: str, scenario: str, state: JsonMap) -> bool:
        return _write_json_if_changed(self.decision_path(assignment_id, scenario), state)

    def save(self, analysis: AdjustmentAnalysis, previous: JsonMap) -> None:
        directory = self.output_dir(analysis.assignment_id, analysis.valuation_scenario)
        data = analysis.to_dict()
        delta = adjustment_delta(previous, data)
        write_json(directory / "adjustment-analysis.json", data)
        write_json(directory / "adjustment-support.json", _support_payload(data))
        write_json(directory / "adjustment-conflicts.json", {"conflicts": data["conflicts"]})
        write_json(directory / "adjustment-delta.json", delta)
        _write_json_if_changed(directory / "adjustment-decisions.json", data["decisions"])
        (directory / "adjustment-analysis.md").write_text(render_analysis_markdown(data), encoding="utf-8")
        (directory / "adjustment-support.md").write_text(render_support_markdown(data), encoding="utf-8")
        (directory / "adjustment-review-queue.md").write_text(render_review_markdown(data), encoding="utf-8")
        history_path = directory / "adjustment-history.json"
        history = _list(_map(read_json(history_path)).get("snapshots")) if history_path.exists() else []
        snapshot = adjustment_snapshot_id(data)
        if not history or history[-1].get("snapshot_id") != snapshot:
            history.append({"snapshot_id": snapshot, "created_at": data["created_at"], "counts": data["counts"], "delta": delta})
        _write_json_if_changed(history_path, {"snapshots": history})

    def create_template(self, assignment_id: str, scenario: str) -> Path:
        path = self.input_path(assignment_id, scenario)
        if path.exists():
            raise AdjustmentIntelligenceError(f"Adjustment evidence already exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_template_text(assignment_id, scenario), encoding="utf-8")
        return path

    def summary(self) -> JsonMap:
        base = self.root / "outputs" / "real-estate" / "assignments"
        analyses: list[JsonMap] = []
        if base.exists():
            for path in base.glob("*/adjustments/scenarios/*/adjustment-analysis.json"):
                try:
                    analyses.append(read_json(path))
                except Exception:
                    continue
        return {
            "assignments_with_adjustment_intelligence": len({item.get("assignment_id") for item in analyses}),
            "total_adjustment_scenarios": len(analyses),
            "factors_with_evidence": sum(int(_map(item.get("counts")).get("factors_with_evidence", 0)) for item in analyses),
            "factors_with_selected_decisions": sum(int(_map(item.get("counts")).get("factors_with_selected_decisions", 0)) for item in analyses),
            "adjustment_conflicts_open": sum(int(_map(item.get("counts")).get("open_conflicts", 0)) for item in analyses),
            "adjustment_review_items": sum(int(_map(item.get("counts")).get("review_items", 0)) for item in analyses),
            "scenarios_with_limited_adjustment_support": sum(1 for item in analyses if any(_map(value).get("coverage") in {"limited", "absent", "conflicted"} for value in _map(item.get("coverage")).values())),
            "latest_adjustment_run_at": max((_text(item.get("created_at")) for item in analyses), default=""),
        }


class AdjustmentIntelligenceEngine:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.store = AdjustmentStore(root)
        self.comparables = ComparableStore(root)

    def build(self, assignment_id: str, *, scenario: str, overwrite: bool = False) -> AdjustmentAnalysis:
        scenario = validate_scenario_id(scenario)
        evidence_document = self.store.load_input(assignment_id, scenario)
        evidence_document = _with_local_evidence_sources(evidence_document, self.store.input_path(assignment_id, scenario).parent)
        comparable = self.comparables.load(assignment_id, scenario)
        if not comparable:
            raise AdjustmentIntelligenceError(f"Comparable Intelligence must be built first for {assignment_id}::{scenario}.")
        previous = self.store.load(assignment_id, scenario)
        if previous and not overwrite:
            raise AdjustmentIntelligenceError("Adjustment analysis already exists; pass --overwrite to rebuild it.")
        subject = _resolved_subject(comparable)
        factors = _factors(evidence_document, scenario)
        differences = _differences(subject, _list(comparable.get("comparables")), factors)
        evidence, indications, evidence_reviews = _evidence_and_indications(evidence_document, comparable, scenario)
        ranges, aggregation_conflicts, aggregation_reviews = _aggregate(indications)
        decisions = self.store.load_decisions(assignment_id, scenario)
        applications, diagnostics, application_reviews = _applications(subject, _list(comparable.get("comparables")), factors, decisions, evidence_document)
        sensitivity = _sensitivity(subject, _list(comparable.get("comparables")), evidence_document)
        conflicts = aggregation_conflicts + _evidence_conflicts(evidence, indications, decisions, ranges, scenario)
        coverage = _coverage(factors, differences, evidence, indications, decisions, conflicts)
        review_queue = _review_queue(factors, differences, evidence, indications, decisions, ranges, conflicts, evidence_reviews + aggregation_reviews + application_reviews)
        counts = {
            "factor_count": len(factors),
            "factors_with_differences": len({item["factor"] for item in differences if item.get("difference_status") == "available" and _nonzero_difference(item.get("difference"))}),
            "factors_with_evidence": len({item["factor"] for item in evidence}),
            "indication_count": len(indications),
            "factors_with_selected_decisions": sum(1 for value in _map(decisions.get("decisions")).values() if _map(value).get("status") in {"selected", "no_adjustment"}),
            "application_count": len(applications),
            "open_conflicts": sum(1 for item in conflicts if item.get("status") == "open"),
            "review_items": len(review_queue),
        }
        created_at = _now_iso()
        input_files = [self.store.input_path(assignment_id, scenario)]
        decision_path = self.store.decision_path(assignment_id, scenario)
        if decision_path.exists():
            input_files.append(decision_path)
        analysis = AdjustmentAnalysis(
            assignment_id=assignment_id,
            valuation_scenario=scenario,
            created_at=created_at,
            version=__version__,
            factors=factors,
            differences=differences,
            evidence=evidence,
            indications=indications,
            ranges=ranges,
            decisions=decisions,
            applications=applications,
            sensitivity=sensitivity,
            diagnostics=diagnostics,
            conflicts=conflicts,
            coverage=coverage,
            review_queue=review_queue,
            counts=counts,
            provenance={
                "engine": "AdjustmentIntelligenceEngine",
                "version": __version__,
                "input_files": [str(path) for path in input_files],
                "input_fingerprint": _fingerprint(input_files),
                "comparable_input_fingerprint": _map(comparable.get("provenance")).get("input_fingerprint", ""),
                "comparable_universe_path": str(self.comparables.output_dir(assignment_id, scenario) / "comparable-universe.json"),
            },
            limitations=[
                "Adjustment Intelligence calculates evidence and arithmetic; it does not select a final adjustment rate.",
                "No causality, legal-unit, permitting, GLA-treatment, comparable-selection, reconciliation, or value conclusion is generated.",
                "Appraiser judgment and explicit decision state govern any deterministic grid application.",
            ],
        )
        self.store.save(analysis, previous)
        return analysis

    def set_decision(
        self,
        assignment_id: str,
        factor: str,
        *,
        scenario: str,
        status: str,
        value: float | None = None,
        unit: str = "",
        reason: str,
        selected_by: str = "appraiser",
        confirm: bool = False,
    ) -> JsonMap:
        scenario = validate_scenario_id(scenario)
        if not confirm:
            raise AdjustmentIntelligenceError("Explicit --confirm is required for adjustment decisions.")
        if factor not in FACTOR_DEFINITIONS:
            raise AdjustmentIntelligenceError(f"Unsupported adjustment factor: {factor}")
        if status not in DECISION_STATUSES:
            raise AdjustmentIntelligenceError(f"Unsupported decision status: {status}")
        if status in {"selected", "no_adjustment"} and not reason.strip():
            raise AdjustmentIntelligenceError("An appraiser rationale is required.")
        if status == "selected" and value is None:
            raise AdjustmentIntelligenceError("A selected decision requires --value.")
        state = self.store.load_decisions(assignment_id, scenario)
        decisions = _map(state.setdefault("decisions", {}))
        record = {
            "factor": factor,
            "status": status,
            "adjustment_value": value if status == "selected" else 0 if status == "no_adjustment" else None,
            "unit": unit or FACTOR_DEFINITIONS[factor]["unit"],
            "selected_by": selected_by,
            "rationale": reason.strip(),
            "reviewed_at": _now_iso(),
        }
        decisions[factor] = record
        state["decisions"] = decisions
        state.setdefault("history", []).append({"action": status, **record})
        self.store.save_decisions(assignment_id, scenario, state)
        return record

    def reset_decision(self, assignment_id: str, factor: str, *, scenario: str, confirm: bool = False) -> JsonMap:
        if not confirm:
            raise AdjustmentIntelligenceError("Explicit --confirm is required to reset an adjustment decision.")
        state = self.store.load_decisions(assignment_id, scenario)
        previous = _map(state.setdefault("decisions", {})).pop(factor, None)
        state.setdefault("history", []).append({"action": "reset", "factor": factor, "previous": previous, "reviewed_at": _now_iso()})
        self.store.save_decisions(assignment_id, scenario, state)
        return {"factor": factor, "status": "unreviewed", "previous": previous}


def _factors(document: JsonMap, scenario: str) -> list[JsonMap]:
    configuration = _map(document.get("factors"))
    records = []
    for factor_id, definition in FACTOR_DEFINITIONS.items():
        configured = _map(configuration.get(factor_id))
        status = _text(configured.get("status") or ("informational_only" if definition["basis"] == "informational_only" else "active"))
        records.append(
            AdjustmentFactor(
                factor_id=factor_id,
                canonical_field=definition["field"],
                label=_text(configured.get("label") or factor_id.replace("_", " ").title()),
                adjustment_basis=_text(configured.get("adjustment_basis") or definition["basis"]),
                unit=_text(configured.get("unit") or definition["unit"]),
                directionality="adjustment_to_comparable",
                scenario_id=scenario,
                enabled=status != "unavailable" and configured.get("enabled", True) is not False,
                configuration=configured,
                notes=[status],
            ).to_dict()
        )
    return records


def _with_local_evidence_sources(document: JsonMap, input_directory: Path) -> JsonMap:
    """Merge only explicitly configured local structured evidence files."""
    expanded = json.loads(json.dumps(document))
    blocks = _map(expanded.setdefault("adjustment_evidence", {}))
    for source_value in _list(document.get("evidence_sources")):
        source = _map(source_value)
        configured_path = _text(source.get("path"))
        if not configured_path:
            continue
        path = Path(configured_path)
        if not path.is_absolute():
            path = (input_directory / path).resolve()
        if not path.exists() or not path.is_file():
            raise AdjustmentIntelligenceError(f"Configured local adjustment evidence does not exist: {configured_path}")
        suffix = path.suffix.lower()
        if suffix == ".csv":
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                rows = list(csv.DictReader(handle))
            for index, row in enumerate(rows):
                factor = _text(row.get("factor"))
                if not factor:
                    continue
                indication_value = _number(row.get("indication_value"))
                difference_value = _number(row.get("difference_value"))
                record: JsonMap = {
                    "evidence_id": _text(row.get("evidence_id") or f"{path.stem}-{index + 1}"),
                    "method": _text(row.get("method")),
                    "source_type": _text(row.get("source_type") or source.get("source_type") or "local_csv"),
                    "source_path": configured_path,
                    "source_checksum": sha256(path.read_bytes()).hexdigest(),
                    "source_record_id": _text(row.get("source_record_id") or str(index + 1)),
                    "verification_status": _text(row.get("verification_status") or source.get("verification_status")),
                    "evidence_classification": _text(row.get("evidence_classification") or source.get("evidence_classification")),
                    "valuation_scenario": _text(row.get("valuation_scenario")),
                    "price_difference": _number(row.get("price_difference")),
                    "governed_pair": _text(row.get("governed_pair")).lower() in {"true", "yes", "1"},
                    "notes": _text(row.get("notes")),
                }
                if difference_value is not None:
                    record["difference"] = {factor: difference_value}
                if indication_value is not None:
                    record["indication"] = {"value": indication_value, "unit": _text(row.get("unit") or FACTOR_DEFINITIONS.get(factor, {}).get("unit"))}
                _append_evidence(blocks, factor, record)
        elif suffix in {".yaml", ".yml", ".json"}:
            payload = json.loads(path.read_text(encoding="utf-8")) if suffix == ".json" else load_yaml(path)
            for factor, block_value in _map(payload.get("adjustment_evidence", payload)).items():
                for record_value in _list(_map(block_value).get("evidence")):
                    record = _map(record_value).copy()
                    record.setdefault("source_path", configured_path)
                    record.setdefault("source_checksum", sha256(path.read_bytes()).hexdigest())
                    record.setdefault("source_type", source.get("source_type", f"local_{suffix.lstrip('.')}"))
                    record.setdefault("verification_status", source.get("verification_status", ""))
                    record.setdefault("evidence_classification", source.get("evidence_classification", ""))
                    _append_evidence(blocks, factor, record)
        else:
            raise AdjustmentIntelligenceError(f"Unsupported local adjustment evidence format: {path.suffix}")
    expanded["adjustment_evidence"] = blocks
    return expanded


def _append_evidence(blocks: JsonMap, factor: str, record: JsonMap) -> None:
    block = blocks.setdefault(factor, {})
    if not isinstance(block, dict):
        raise AdjustmentIntelligenceError(f"Adjustment evidence block for {factor} must be a mapping.")
    existing = block.get("evidence")
    if existing is None or existing == "" or existing == "[]":
        existing = []
        block["evidence"] = existing
    if not isinstance(existing, list):
        raise AdjustmentIntelligenceError(f"Adjustment evidence list for {factor} must be a list.")
    existing.append(record)


def _resolved_subject(comparable: JsonMap) -> JsonMap:
    fields = _map(_map(comparable.get("subject_resolution")).get("fields"))
    subject = _map(comparable.get("subject")).copy()
    for name, detail in fields.items():
        value = _map(detail).get("normalized_value")
        if _available(value):
            subject[name] = value
    if "sale_or_effective_date" in subject:
        subject["effective_date"] = subject["sale_or_effective_date"]
    return subject


def _differences(subject: JsonMap, comparables: list[JsonMap], factors: list[JsonMap]) -> list[JsonMap]:
    results = []
    for record in comparables:
        for factor in factors:
            if not factor.get("enabled"):
                continue
            factor_id = factor["factor_id"]
            field_name = factor["canonical_field"]
            subject_value = subject.get(field_name)
            comparable_value = record.get(field_name)
            difference, status, reason = _difference(factor_id, subject_value, comparable_value, subject, record)
            results.append(
                {
                    "comparable_id": record.get("comparable_id"),
                    "factor": factor_id,
                    "canonical_field": field_name,
                    "subject_value": subject_value,
                    "comparable_value": comparable_value,
                    "difference": difference,
                    "difference_status": status,
                    "reason": reason,
                    "sign_convention": "subject minus comparable; positive adjusts an inferior comparable upward",
                    "potential_adjustment_factor": factor["adjustment_basis"],
                }
            )
    return results


def _difference(factor: str, subject_value: Any, comparable_value: Any, subject: JsonMap, comparable: JsonMap) -> tuple[Any, str, str]:
    if factor == "market_conditions":
        return _month_difference(comparable.get("sale_date"), subject.get("effective_date"))
    if not _available(subject_value) or not _available(comparable_value):
        return None, "unavailable", "A factual source value is unavailable."
    if factor in NUMERIC_FACTORS:
        try:
            return float(subject_value) - float(comparable_value), "available", "Factual subject-minus-comparable difference."
        except (TypeError, ValueError):
            return None, "review_required", "Numeric values could not be deterministically compared."
    if factor in ORDINAL_PREFIXES:
        subject_step = _ordinal(subject_value, ORDINAL_PREFIXES[factor])
        comparable_step = _ordinal(comparable_value, ORDINAL_PREFIXES[factor])
        if subject_step is None or comparable_step is None:
            return None, "review_required", "Ordinal codes are unavailable or invalid."
        return subject_step - comparable_step, "available", "Deterministic ordinal-code difference; no market adjustment is implied."
    if factor in CATEGORICAL_FACTORS:
        if subject_value == comparable_value:
            return 0, "available", "Explicit categorical facts match."
        if isinstance(subject_value, bool) and isinstance(comparable_value, bool):
            return (1 if subject_value else -1), "available", "Explicit categorical difference."
        return {"subject": subject_value, "comparable": comparable_value}, "available", "Explicit categorical difference; direction requires a governed decision basis."
    return None, "unavailable", "No deterministic difference rule is configured."


def _evidence_and_indications(document: JsonMap, comparable: JsonMap, scenario: str) -> tuple[list[JsonMap], list[JsonMap], list[JsonMap]]:
    evidence_records: list[JsonMap] = []
    indications: list[JsonMap] = []
    reviews: list[JsonMap] = []
    blocks = _map(document.get("adjustment_evidence"))
    for factor, block_value in blocks.items():
        if factor not in FACTOR_DEFINITIONS:
            reviews.append(_review("unsupported_factor", factor, "Unsupported adjustment factor in evidence input.", "medium"))
            continue
        block = _map(block_value)
        for index, raw in enumerate(_list(block.get("evidence"))):
            item = _map(raw).copy()
            evidence_id = _text(item.get("evidence_id") or f"{factor}-evidence-{index + 1}")
            method = _text(item.get("method"))
            declared_scenario = _text(item.get("valuation_scenario") or scenario)
            classification = _classification(item)
            source_paths = _source_paths(item)
            record = {
                **item,
                "evidence_id": evidence_id,
                "factor": factor,
                "method": method,
                "valuation_scenario": declared_scenario,
                "evidence_classification": classification,
                "source_paths": source_paths,
                "source_fingerprint": _digest(json.dumps(item, sort_keys=True, default=str)),
            }
            evidence_records.append(record)
            if method not in EVIDENCE_METHODS:
                reviews.append(_review("unsupported_evidence_method", factor, f"Evidence {evidence_id} uses an unsupported method.", "medium", evidence_id=evidence_id))
                continue
            if declared_scenario != scenario:
                reviews.append(_review("scenario_mismatch", factor, f"Evidence {evidence_id} belongs to scenario '{declared_scenario}'.", "high", evidence_id=evidence_id))
                continue
            if not source_paths:
                reviews.append(_review("missing_provenance", factor, f"Evidence {evidence_id} has no source provenance.", "medium", evidence_id=evidence_id))
            if classification != "independent_market_evidence":
                if classification == "appraiser_decision_reference":
                    reviews.append(_review("circular_evidence_guard", factor, f"Evidence {evidence_id} is an appraiser decision reference and cannot independently support itself.", "medium", evidence_id=evidence_id))
                continue
            indication, issue = _indication(record, comparable)
            if indication:
                indications.append(indication)
            if issue:
                reviews.append(_review(issue[0], factor, issue[1], issue[2], evidence_id=evidence_id))
    return evidence_records, indications, reviews


def _classification(item: JsonMap) -> str:
    declared = _text(item.get("evidence_classification"))
    source_type = _text(item.get("source_type")).lower()
    if source_type in {"appraisal_grid", "appraisal_grid_export", "subject_appraisal", "current_appraisal_adjustment"}:
        return "appraiser_decision_reference"
    if declared in EVIDENCE_CLASSIFICATIONS:
        return declared
    if _text(item.get("method")) == "informational_reference":
        return "contextual_reference"
    if item.get("verification_status") in {"appraiser_verified", "governed", "verified"}:
        return "independent_market_evidence"
    return "unsupported"


def _indication(record: JsonMap, comparable: JsonMap) -> tuple[JsonMap | None, tuple[str, str, str] | None]:
    factor = record["factor"]
    method = record["method"]
    value = None
    unit = _text(_map(record.get("indication")).get("unit") or FACTOR_DEFINITIONS[factor]["unit"])
    calculation = ""
    limitations = _strings(record.get("limitations"))
    unresolved = _strings(record.get("unresolved_differences"))
    if method == "matched_pair":
        governed = bool(record.get("governed_pair") or record.get("pair_status") in {"approved", "governed"} or record.get("verification_status") == "appraiser_verified")
        if not governed:
            return None, ("unapproved_potential_pair", f"Pair {record['evidence_id']} remains potential_pair until explicitly governed or approved.", "medium")
        focal = _map(record.get("difference")).get(factor)
        price_difference = record.get("price_difference")
        try:
            denominator = float(focal)
            numerator = float(price_difference)
        except (TypeError, ValueError):
            return None, ("incomplete_pair_arithmetic", f"Pair {record['evidence_id']} lacks explicit focal and price differences.", "medium")
        if denominator == 0:
            return None, ("zero_pair_denominator", f"Pair {record['evidence_id']} has a zero focal difference.", "high")
        value = numerator / denominator
        calculation = f"{numerator} / {denominator} = {value}"
        if unresolved:
            limitations.append("Other material pair differences remain unresolved; causality is not established.")
    elif method == "grouped_comparison":
        group_a = _numeric_values(_map(record.get("group_a")).get("values"))
        group_b = _numeric_values(_map(record.get("group_b")).get("values"))
        if not group_a or not group_b:
            return None, ("incomplete_group_evidence", f"Grouped comparison {record['evidence_id']} lacks explicit numeric groups.", "medium")
        a_median, b_median = statistics.median(group_a), statistics.median(group_b)
        value = a_median - b_median
        calculation = f"median(group_a) {a_median} - median(group_b) {b_median} = {value}"
        limitations.extend(_strings(record.get("uncontrolled_differences")))
    else:
        explicit = _map(record.get("indication")).get("value")
        if explicit is None:
            return None, ("missing_indication", f"Evidence {record['evidence_id']} contains no explicit calculable indication.", "low")
        try:
            value = float(explicit)
        except (TypeError, ValueError):
            return None, ("invalid_indication", f"Evidence {record['evidence_id']} has a nonnumeric indication.", "medium")
        calculation = _text(_map(record.get("indication")).get("calculation") or "Explicit appraiser-governed indication.")
    indication = {
        "indication_id": f"indication_{_digest(record['evidence_id'] + factor + str(value))}",
        "factor": factor,
        "valuation_scenario": record["valuation_scenario"],
        "method": method,
        "amount": value,
        "unit": unit,
        "direction": "observed_raw_indication",
        "evidence_ids": [record["evidence_id"]],
        "source_paths": record["source_paths"],
        "calculation": calculation,
        "sample_count": int(record.get("sample_count") or (2 if method == "matched_pair" else 1)),
        "verification_status": record.get("verification_status", "unreviewed"),
        "limitations": limitations + ["Observed evidence does not prove causality or select a final adjustment."],
        "unresolved_differences": unresolved,
        "appraiser_review_status": _text(record.get("appraiser_review_status") or "unreviewed"),
    }
    issue = ("unresolved_pair_differences", f"Indication {indication['indication_id']} retains unresolved secondary differences.", "medium") if unresolved else None
    return indication, issue


def _aggregate(indications: list[JsonMap]) -> tuple[list[JsonMap], list[JsonMap], list[JsonMap]]:
    ranges, conflicts, reviews = [], [], []
    by_factor: dict[str, list[JsonMap]] = {}
    for item in indications:
        by_factor.setdefault(item["factor"], []).append(item)
    for factor, items in sorted(by_factor.items()):
        units = sorted({_text(item.get("unit")) for item in items})
        if len(units) != 1:
            conflicts.append(_conflict("incompatible_units", factor, "Compatible indication aggregation requires one unit.", items))
            continue
        values = [float(item["amount"]) for item in items]
        weights = [item.get("weight") for item in items]
        weighted_mean = None
        if all(value is not None for value in weights) and sum(float(value) for value in weights) != 0:
            weighted_mean = sum(value * float(weight) for value, weight in zip(values, weights)) / sum(float(weight) for weight in weights)
        record = {
            "factor": factor,
            "unit": units[0],
            "count": len(values),
            "minimum": min(values),
            "maximum": max(values),
            "median": statistics.median(values),
            "mean": statistics.fmean(values),
            "weighted_mean": weighted_mean,
            "standard_deviation": statistics.pstdev(values) if len(values) > 1 else 0.0,
            "interquartile_range": _iqr(values),
            "indication_ids": [item["indication_id"] for item in items],
            "outliers_discarded": False,
            "selection_status": "not_selected",
        }
        ranges.append(record)
        if len(values) < 2:
            reviews.append(_review("thin_sample", factor, "Only one usable indication is available; appraiser review is required.", "low"))
        spread = max(values) - min(values)
        if len(values) > 1 and abs(statistics.fmean(values)) > 0 and spread / abs(statistics.fmean(values)) > 0.75:
            reviews.append(_review("high_dispersion", factor, "Indications have high dispersion; no outlier was discarded.", "medium"))
        if any(value < 0 for value in values) and any(value > 0 for value in values):
            conflicts.append(_conflict("conflicting_direction", factor, "Indications contain conflicting directions.", items))
    return ranges, conflicts, reviews


def _applications(subject: JsonMap, comparables: list[JsonMap], factors: list[JsonMap], decisions: JsonMap, document: JsonMap) -> tuple[list[JsonMap], list[JsonMap], list[JsonMap]]:
    applications, reviews = [], []
    factor_map = {item["factor_id"]: item for item in factors}
    rounding = _map(document.get("rounding"))
    for factor, decision_value in _map(decisions.get("decisions")).items():
        decision = _map(decision_value)
        if decision.get("status") != "selected":
            continue
        if not _text(decision.get("rationale")):
            reviews.append(_review("selected_without_rationale", factor, "Selected rate has no appraiser rationale.", "high"))
        rate = _number(decision.get("adjustment_value"))
        if rate is None:
            reviews.append(_review("invalid_selected_rate", factor, "Selected decision has no numeric rate.", "high"))
            continue
        definition = factor_map.get(factor, {"adjustment_basis": FACTOR_DEFINITIONS.get(factor, {}).get("basis", "informational_only"), "canonical_field": factor})
        for comparable in comparables:
            difference, status, _ = _difference(factor, subject.get(definition["canonical_field"]), comparable.get(definition["canonical_field"]), subject, comparable)
            if status != "available" or not isinstance(difference, (int, float)):
                continue
            raw = _application_amount(definition["adjustment_basis"], difference, rate, comparable)
            if raw is None:
                continue
            rounded = _round_to(raw, _number(rounding.get("adjustment_amount_nearest")) or 100)
            applications.append(
                {
                    "application_id": f"application_{_digest(str(comparable.get('comparable_id')) + factor + str(rate))}",
                    "comparable_id": comparable.get("comparable_id"),
                    "factor": factor,
                    "difference_for_adjustment": difference,
                    "selected_rate": rate,
                    "unit": decision.get("unit"),
                    "raw_adjustment": raw,
                    "rounded_adjustment": rounded,
                    "sign_convention": "subject minus comparable; comparable inferior to subject is positive",
                    "statement": f"Calculated application using appraiser-selected rate: {raw:+.2f}",
                }
            )
    diagnostics = []
    by_comparable: dict[str, list[JsonMap]] = {}
    for application in applications:
        by_comparable.setdefault(_text(application.get("comparable_id")), []).append(application)
    for comparable in comparables:
        comparable_id = _text(comparable.get("comparable_id"))
        sale_price = _number(comparable.get("sale_price"))
        items = by_comparable.get(comparable_id, [])
        if not sale_price or not items:
            continue
        gross = sum(abs(float(item["raw_adjustment"])) for item in items) / sale_price
        net = sum(float(item["raw_adjustment"]) for item in items) / sale_price
        diagnostics.append({"comparable_id": comparable_id, "gross_adjustment_percentage": gross, "net_adjustment_percentage": net, "mathematical_diagnostic_only": True})
    return applications, diagnostics, reviews


def _application_amount(basis: str, difference: float, rate: float, comparable: JsonMap) -> float | None:
    if basis in {"per_unit", "lump_sum", "ordinal_step"}:
        return difference * rate
    if basis == "percentage":
        sale_price = _number(comparable.get("sale_price"))
        return sale_price * rate if sale_price is not None else None
    if basis == "time_percentage":
        sale_price = _number(comparable.get("sale_price"))
        return sale_price * rate * difference if sale_price is not None else None
    return None


def _sensitivity(subject: JsonMap, comparables: list[JsonMap], document: JsonMap) -> list[JsonMap]:
    results = []
    for factor, block_value in _map(document.get("adjustment_evidence")).items():
        rates = _numeric_values(_map(block_value).get("candidate_rates"))
        if not rates or factor not in FACTOR_DEFINITIONS:
            continue
        field_name = FACTOR_DEFINITIONS[factor]["field"]
        basis = FACTOR_DEFINITIONS[factor]["basis"]
        for rate in rates:
            effects = []
            for comparable in comparables:
                difference, status, _ = _difference(factor, subject.get(field_name), comparable.get(field_name), subject, comparable)
                if status == "available" and isinstance(difference, (int, float)):
                    amount = _application_amount(basis, difference, rate, comparable)
                    if amount is not None:
                        effects.append({"comparable_id": comparable.get("comparable_id"), "difference": difference, "raw_adjustment": amount})
            adjusted = [float(comp.get("sale_price")) + item["raw_adjustment"] for item in effects for comp in comparables if comp.get("comparable_id") == item["comparable_id"] and _number(comp.get("sale_price")) is not None]
            results.append({"factor": factor, "candidate_rate": rate, "effects": effects, "adjusted_sale_price_spread": max(adjusted) - min(adjusted) if adjusted else None, "automatic_winner": None})
    return results


def _evidence_conflicts(evidence: list[JsonMap], indications: list[JsonMap], decisions: JsonMap, ranges: list[JsonMap], scenario: str) -> list[JsonMap]:
    conflicts = []
    for item in evidence:
        if item.get("valuation_scenario") != scenario:
            conflicts.append(_conflict("scenario_mismatch", item["factor"], "Adjustment evidence belongs to a different scenario.", [item]))
    range_map = {item["factor"]: item for item in ranges}
    for factor, raw in _map(decisions.get("decisions")).items():
        decision = _map(raw)
        if decision.get("status") != "selected" or factor not in range_map:
            continue
        value = _number(decision.get("adjustment_value"))
        range_item = range_map[factor]
        if value is not None and not (range_item["minimum"] <= value <= range_item["maximum"]):
            conflicts.append(_conflict("selected_rate_outside_evidence_range", factor, "The explicitly selected rate is outside the observed evidence range; appraiser confirmation and rationale are preserved.", [decision, range_item]))
    return conflicts


def _coverage(factors: list[JsonMap], differences: list[JsonMap], evidence: list[JsonMap], indications: list[JsonMap], decisions: JsonMap, conflicts: list[JsonMap]) -> JsonMap:
    result = {}
    for factor in factors:
        factor_id = factor["factor_id"]
        factor_differences = [item for item in differences if item["factor"] == factor_id and item.get("difference_status") == "available"]
        factor_evidence = [item for item in evidence if item["factor"] == factor_id]
        factor_indications = [item for item in indications if item["factor"] == factor_id]
        factor_conflicts = [item for item in conflicts if item["factor"] == factor_id and item.get("status") == "open"]
        decision = _map(_map(decisions.get("decisions")).get(factor_id))
        if factor_conflicts:
            level = "conflicted"
        elif len(factor_indications) >= 3:
            level = "strong"
        elif len(factor_indications) >= 2:
            level = "adequate"
        elif factor_indications:
            level = "limited"
        elif factor_evidence:
            level = "limited"
        elif factor_differences:
            level = "absent"
        else:
            level = "unavailable"
        result[factor_id] = {
            "coverage": level,
            "subject_difference_exists": any(_nonzero_difference(item.get("difference")) for item in factor_differences),
            "comparable_difference_count": len(factor_differences),
            "evidence_record_count": len(factor_evidence),
            "usable_indication_count": len(factor_indications),
            "appraiser_decision_status": decision.get("status", "unreviewed"),
            "application_status": "applied" if decision.get("status") == "selected" else "not_applied",
            "evidence_limitations": sum((_strings(item.get("limitations")) for item in factor_indications), []),
        }
    return result


def _review_queue(factors: list[JsonMap], differences: list[JsonMap], evidence: list[JsonMap], indications: list[JsonMap], decisions: JsonMap, ranges: list[JsonMap], conflicts: list[JsonMap], seeded: list[JsonMap]) -> list[JsonMap]:
    reviews = list(seeded)
    evidence_factors = {item["factor"] for item in evidence}
    indication_factors = {item["factor"] for item in indications}
    decision_map = _map(decisions.get("decisions"))
    for factor in factors:
        factor_id = factor["factor_id"]
        has_difference = any(item["factor"] == factor_id and item.get("difference_status") == "available" and _nonzero_difference(item.get("difference")) for item in differences)
        if has_difference and factor_id not in evidence_factors and factor.get("adjustment_basis") != "informational_only":
            reviews.append(_review("difference_without_evidence", factor_id, "A factual subject-to-comparable difference exists without adjustment evidence.", "low"))
        if factor_id in evidence_factors and factor_id not in indication_factors:
            reviews.append(_review("evidence_without_usable_indication", factor_id, "Evidence exists but provides no usable independent indication.", "medium"))
        if has_difference and not _map(decision_map.get(factor_id)).get("status"):
            reviews.append(_review("adjustment_decision_unreviewed", factor_id, "Adjustment decision remains explicitly unreviewed.", "low"))
    for conflict in conflicts:
        reviews.append(_review(_text(conflict.get("conflict_type")), _text(conflict.get("factor")), _text(conflict.get("reason")), _text(conflict.get("severity") or "medium"), conflict_id=conflict.get("conflict_id")))
    unique: dict[str, JsonMap] = {}
    for item in reviews:
        key = json.dumps({key: item.get(key) for key in ("item_type", "factor", "evidence_id", "conflict_id", "reason")}, sort_keys=True)
        unique.setdefault(key, item)
    return list(unique.values())


def _review(item_type: str, factor: str, reason: str, severity: str, **extra: Any) -> JsonMap:
    return {"item_id": f"adjustment_review_{_digest(item_type + factor + reason + json.dumps(extra, sort_keys=True, default=str))}", "item_type": item_type, "factor": factor, "reason": reason, "severity": severity, "status": "open", **extra}


def _conflict(conflict_type: str, factor: str, reason: str, assertions: list[JsonMap]) -> JsonMap:
    return {"conflict_id": f"adjustment_conflict_{_digest(conflict_type + factor + json.dumps(assertions, sort_keys=True, default=str))}", "conflict_type": conflict_type, "factor": factor, "reason": reason, "severity": "medium", "status": "open", "assertions": assertions}


def adjustment_delta(previous: JsonMap, current: JsonMap) -> JsonMap:
    previous_conflicts = {_text(item.get("conflict_id")) for item in _list(previous.get("conflicts"))}
    current_conflicts = {_text(item.get("conflict_id")) for item in _list(current.get("conflicts"))}
    previous_indications = {_text(item.get("indication_id")): item for item in _list(previous.get("indications"))}
    current_indications = {_text(item.get("indication_id")): item for item in _list(current.get("indications"))}
    return {
        "conflicts_opened": sorted(current_conflicts - previous_conflicts),
        "conflicts_resolved": sorted(previous_conflicts - current_conflicts),
        "indications_added": sorted(set(current_indications) - set(previous_indications)),
        "indications_removed": sorted(set(previous_indications) - set(current_indications)),
        "indications_changed": sorted(key for key in set(previous_indications) & set(current_indications) if previous_indications[key] != current_indications[key]),
    }


def adjustment_snapshot_id(data: JsonMap) -> str:
    stable = {key: data.get(key) for key in ("assignment_id", "valuation_scenario", "factors", "differences", "evidence", "indications", "ranges", "decisions", "applications", "sensitivity", "diagnostics", "conflicts", "coverage", "review_queue", "counts", "provenance", "limitations")}
    return f"adjustment_snapshot_{_digest(json.dumps(stable, sort_keys=True, default=str))}"


def render_analysis_markdown(data: JsonMap) -> str:
    counts = _map(data.get("counts"))
    lines = [
        "# Adjustment Intelligence",
        "",
        "## 1. Assignment and Scenario",
        "",
        f"- Assignment: `{data.get('assignment_id')}`",
        f"- Scenario: `{data.get('valuation_scenario')}`",
        "",
        "## 2. Adjustment Intelligence Summary",
        "",
        f"- Factors with differences: `{counts.get('factors_with_differences', 0)}`",
        f"- Factors with evidence: `{counts.get('factors_with_evidence', 0)}`",
        f"- Factors with selected decisions: `{counts.get('factors_with_selected_decisions', 0)}`",
        f"- Open conflicts: `{counts.get('open_conflicts', 0)}`",
        f"- Review items: `{counts.get('review_items', 0)}`",
        "",
        "## 3. Subject-to-Comparable Differences",
        "",
    ]
    for item in _list(data.get("differences")):
        if item.get("difference_status") == "available" and _nonzero_difference(item.get("difference")):
            lines.append(f"- `{item.get('comparable_id')}` {item.get('factor')}: difference=`{item.get('difference')}` (factual difference, not an adjustment)")
    lines.extend(["", "## 4. Adjustment Factor Coverage", ""])
    for factor, detail in _map(data.get("coverage")).items():
        lines.append(f"- {factor}: `{_map(detail).get('coverage')}` evidence=`{_map(detail).get('evidence_record_count', 0)}` indications=`{_map(detail).get('usable_indication_count', 0)}` decision=`{_map(detail).get('appraiser_decision_status')}`")
    lines.extend(["", "## 5. Market Evidence by Factor", ""])
    for item in _list(data.get("evidence")):
        lines.append(f"- {item.get('factor')} / `{item.get('evidence_id')}` method=`{item.get('method')}` classification=`{item.get('evidence_classification')}` source(s)=`{'; '.join(_strings(item.get('source_paths'))) or 'unavailable'}`")
    lines.extend(["", "## 6. Matched-Pair Evidence", ""])
    for item in _list(data.get("indications")):
        if item.get("method") == "matched_pair":
            lines.append(f"- {item.get('factor')}: `{item.get('amount')}` {item.get('unit')} — raw pair indication; causality is not established.")
    lines.extend(["", "## 7. Grouped Evidence", ""])
    for item in _list(data.get("indications")):
        if item.get("method") == "grouped_comparison":
            lines.append(f"- {item.get('factor')}: observed group difference `{item.get('amount')}` {item.get('unit')}; not automatically an adjustment.")
    lines.extend(["", "## 8. Adjustment Indications", ""])
    for item in _list(data.get("indications")):
        lines.append(f"- `{item.get('indication_id')}` {item.get('factor')}: `{item.get('amount')}` {item.get('unit')} review=`{item.get('appraiser_review_status')}`")
    lines.extend(["", "## 9. Indication Ranges and Dispersion", ""])
    for item in _list(data.get("ranges")):
        lines.append(f"- {item.get('factor')}: range `{item.get('minimum')}`–`{item.get('maximum')}`, median `{item.get('median')}`, mean `{item.get('mean')}`, count `{item.get('count')}`; no rate selected automatically.")
    lines.extend(["", "## 10. Appraiser Decisions", ""])
    if not _map(data.get("decisions")).get("decisions"):
        lines.append("- No appraiser-selected adjustment decisions are recorded.")
    for factor, decision in _map(_map(data.get("decisions")).get("decisions")).items():
        lines.append(f"- {factor}: status=`{_map(decision).get('status')}` value=`{_map(decision).get('adjustment_value')}` unit=`{_map(decision).get('unit')}` rationale=`{_map(decision).get('rationale')}`")
    lines.extend(["", "## 11. Deterministic Applications", ""])
    lines.extend(f"- {item.get('comparable_id')} {item.get('factor')}: raw `{item.get('raw_adjustment')}` rounded `{item.get('rounded_adjustment')}` — calculated using appraiser-selected rate." for item in _list(data.get("applications")))
    if not _list(data.get("applications")):
        lines.append("- None; no appraiser-selected rate is available for deterministic application.")
    lines.extend(["", "## 12. Sensitivity Analysis", ""])
    lines.extend(f"- {item.get('factor')} candidate rate `{item.get('candidate_rate')}` adjusted-price spread=`{item.get('adjusted_sale_price_spread')}`; no automatic winner." for item in _list(data.get("sensitivity")))
    lines.extend(["", "## 13. Gross/Net Adjustment Diagnostics", ""])
    lines.extend(f"- {item.get('comparable_id')}: gross `{item.get('gross_adjustment_percentage')}` net `{item.get('net_adjustment_percentage')}` (mathematical diagnostic only)." for item in _list(data.get("diagnostics")))
    lines.extend(["", "## 14. Adjustment Conflicts", ""])
    lines.extend(f"- {item.get('severity')}: {item.get('factor')} — {item.get('reason')}" for item in _list(data.get("conflicts")))
    lines.extend(["", "## 15. Review Queue", ""])
    lines.extend(f"- {item.get('severity')}: {item.get('item_type')} / {item.get('factor')} — {item.get('reason')}" for item in _list(data.get("review_queue")))
    lines.extend(["", "## 16. Provenance", ""])
    for key, value in _map(data.get("provenance")).items():
        lines.append(f"- {key}: `{value}`")
    lines.extend(["", "## 17. Professional-Judgment Limitations", ""])
    lines.extend(f"- {item}" for item in _strings(data.get("limitations")))
    return "\n".join(lines).rstrip() + "\n"


def _support_payload(data: JsonMap) -> JsonMap:
    ranges = {item["factor"]: item for item in _list(data.get("ranges"))}
    decisions = _map(_map(data.get("decisions")).get("decisions"))
    return {
        "assignment_id": data.get("assignment_id"),
        "valuation_scenario": data.get("valuation_scenario"),
        "factors": {
            factor: {
                "observed_range": item,
                "appraiser_decision": decisions.get(factor, {"status": "unreviewed"}),
                "support_statement": _support_statement(factor, item, _map(decisions.get(factor))),
            }
            for factor, item in ranges.items()
        },
        "limitations": data.get("limitations", []),
    }


def _support_statement(factor: str, range_item: JsonMap, decision: JsonMap) -> str:
    base = f"Explicit market evidence for {factor.replace('_', ' ')} produced {range_item.get('count')} indication(s), ranging from approximately {range_item.get('minimum')} to {range_item.get('maximum')} {range_item.get('unit')}, with a median of {range_item.get('median')}."
    if decision.get("status") == "selected":
        return base + f" After reviewing the evidence, the appraiser selected {decision.get('adjustment_value')} {decision.get('unit')}."
    return base + " No appraiser-selected adjustment is recorded."


def render_support_markdown(data: JsonMap) -> str:
    payload = _support_payload(data)
    lines = ["# Adjustment Support", "", f"Assignment: `{data.get('assignment_id')}`", f"Scenario: `{data.get('valuation_scenario')}`", ""]
    for factor, detail in _map(payload.get("factors")).items():
        lines.extend([f"## {factor.replace('_', ' ').title()}", "", _text(_map(detail).get("support_statement")), ""])
    lines.extend(["## Professional Boundary", "", "- Evidence summaries distinguish calculated market indications from explicit appraiser decisions.", "- No final rate, comparable weight, reconciliation, or value conclusion is generated."])
    return "\n".join(lines).rstrip() + "\n"


def render_review_markdown(data: JsonMap) -> str:
    lines = ["# Adjustment Review Queue", "", f"Assignment: `{data.get('assignment_id')}`", f"Scenario: `{data.get('valuation_scenario')}`", ""]
    for item in _list(data.get("review_queue")):
        lines.append(f"- {item.get('severity')}: `{item.get('item_type')}` factor=`{item.get('factor')}` — {item.get('reason')}")
    lines.extend(["", "## Professional Boundary", "", "- Review items do not select adjustment rates or make legality, permitting, GLA-treatment, comparable-selection, reconciliation, or value conclusions."])
    return "\n".join(lines).rstrip() + "\n"


def _template_text(assignment_id: str, scenario: str) -> str:
    return f"""assignment_id: {assignment_id}
valuation_scenario: {scenario}

rounding:
  adjustment_amount_nearest: 100

adjustment_evidence:
  gross_living_area:
    candidate_rates: []
    evidence: []
"""


def _write_json_if_changed(path: Path, value: JsonMap) -> bool:
    payload = json.dumps(value, indent=2, sort_keys=True).replace("\n", os.linesep).encode("utf-8")
    if path.exists() and path.read_bytes() == payload:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)
    return True


def _month_difference(start: Any, end: Any) -> tuple[Any, str, str]:
    try:
        start_date = date.fromisoformat(_text(start)[:10])
        end_date = date.fromisoformat(_text(end)[:10])
    except (TypeError, ValueError):
        return None, "unavailable", "Sale or effective date is unavailable."
    days = (end_date - start_date).days
    return days / (365.2425 / 12), "available", "Simple elapsed months using actual days and a 365.2425-day year; no compounding."


def _ordinal(value: Any, prefix: str) -> int | None:
    text = _text(value).strip().lower()
    if len(text) < 2 or not text.startswith(prefix):
        return None
    try:
        number = int(text[1:])
    except ValueError:
        return None
    return -number


def _iqr(values: list[float]) -> float:
    if len(values) < 4:
        return 0.0
    quartiles = statistics.quantiles(sorted(values), n=4, method="inclusive")
    return quartiles[2] - quartiles[0]


def _round_to(value: float, nearest: float) -> float:
    if nearest <= 0:
        return value
    return math.floor(value / nearest + 0.5) * nearest if value >= 0 else math.ceil(value / nearest - 0.5) * nearest


def _source_paths(item: JsonMap) -> list[str]:
    paths = _strings(item.get("source_paths"))
    single = _text(item.get("source_path"))
    if single and single not in paths:
        paths.insert(0, single)
    return paths


def _fingerprint(paths: list[Path]) -> str:
    digest = sha256()
    for path in sorted(paths, key=str):
        digest.update(str(path).encode("utf-8"))
        digest.update(path.read_bytes())
    return digest.hexdigest()


def _numeric_values(value: Any) -> list[float]:
    result = []
    for item in _list(value):
        number = _number(item)
        if number is not None:
            result.append(number)
    return result


def _number(value: Any) -> float | None:
    if isinstance(value, bool) or value in {None, ""}:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _available(value: Any) -> bool:
    return value is not None and value != "" and value != [] and value != {}


def _nonzero_difference(value: Any) -> bool:
    if isinstance(value, dict):
        return bool(value)
    return value not in {0, 0.0, False, None, ""}


def _map(value: Any) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _strings(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _text(value: Any) -> str:
    return "" if value is None else str(value).strip()


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:16]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
