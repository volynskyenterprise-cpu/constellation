from __future__ import annotations

import csv
import html
import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from . import __version__
from .io import read_json, write_json
from .models import JsonMap
from .real_estate import RealEstateAssignmentStore, assignment_directory
from .simple_yaml import load_yaml


class ComparableIntelligenceError(RuntimeError):
    pass


CANDIDATE_STATUSES = {
    "primary_candidate",
    "secondary_candidate",
    "contextual_candidate",
    "insufficient_data",
    "potential_duplicate",
    "review_required",
    "appraiser_selected",
    "appraiser_excluded",
}

ASSESSMENTS = {"strong_match", "acceptable_match", "meaningful_difference", "major_difference", "unavailable", "review_required"}
CORE_FIELDS = ["property_address", "property_type", "sale_date", "sale_price", "gross_living_area", "distance_from_subject"]
ORDERED_CODE_PREFIXES = {"condition": "c", "quality": "q"}


@dataclass(frozen=True)
class ComparableSource:
    source_type: str
    source_path: str
    source_checksum: str
    imported_at: str
    row_number: int = 0
    metadata: JsonMap = field(default_factory=dict)

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ComparableDifference:
    component: str
    subject_value: Any
    comparable_value: Any
    difference: Any
    normalized_difference: Any
    assessment: str
    severity: str
    reason: str
    source_references: list[str]

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ComparableConflict:
    conflict_id: str
    comparable_id: str
    field_name: str
    values: list[Any]
    source_paths: list[str]
    severity: str
    status: str
    preferred_source: str
    reason: str

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ComparableRecord:
    comparable_id: str
    source_record_id: str
    source_type: str
    source_path: str
    source_checksum: str
    listing_id: str
    parcel_number: str
    property_address: str
    normalized_address: str
    property_status: str
    sale_date: str
    sale_price: float | None
    list_date: str
    original_list_price: float | None
    current_list_price: float | None
    pending_date: str
    days_on_market: int | None
    financing_type: str
    concessions: str
    arms_length_status: str
    property_type: str
    design_style: str
    year_built: int | None
    effective_age: int | None
    condition: str
    quality: str
    gross_living_area: float | None
    lot_size: float | None
    bedroom_count: float | None
    bathroom_count: float | None
    garage_count: float | None
    parking_count: float | None
    pool: bool | None
    spa: bool | None
    view: str
    accessory_unit: bool | None
    basement: bool | None
    location_features: list[str]
    zoning: str
    ownership_interest: str
    city: str
    neighborhood: str
    market_area: str
    latitude: float | None
    longitude: float | None
    distance_from_subject: float | None
    source_paths: list[str]
    source_fields: JsonMap
    verification_status: str
    confidence: str
    notes: list[str]
    missing_fields: list[str]
    conflicts: list[JsonMap]
    candidate_status: str
    appraiser_review_status: str
    appraiser_selected: bool
    appraiser_exclusion_reason: str
    reviewed_at: str
    reviewed_by: str

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ComparableAssessment:
    comparable_id: str
    candidate_status: str
    differences: list[ComparableDifference]
    limitations: list[str]
    review_items: list[JsonMap]

    def to_dict(self) -> JsonMap:
        return {
            "comparable_id": self.comparable_id,
            "candidate_status": self.candidate_status,
            "differences": [item.to_dict() for item in self.differences],
            "limitations": self.limitations,
            "review_items": self.review_items,
        }


@dataclass(frozen=True)
class ComparableCoverage:
    assignment_id: str
    levels: JsonMap
    bracketing: JsonMap
    limitations: list[str]
    research_questions: list[str]

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ComparableUniverse:
    assignment_id: str
    canonical_assignment_id: str
    created_at: str
    version: str
    subject: JsonMap
    comparables: list[ComparableRecord]
    assessments: list[ComparableAssessment]
    conflicts: list[ComparableConflict]
    coverage: ComparableCoverage
    review_queue: list[JsonMap]
    counts: JsonMap
    limitations: list[str]
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return {
            "assignment_id": self.assignment_id,
            "canonical_assignment_id": self.canonical_assignment_id,
            "created_at": self.created_at,
            "version": self.version,
            "subject": self.subject,
            "comparables": [item.to_dict() for item in self.comparables],
            "assessments": [item.to_dict() for item in self.assessments],
            "conflicts": [item.to_dict() for item in self.conflicts],
            "coverage": self.coverage.to_dict(),
            "review_queue": self.review_queue,
            "counts": self.counts,
            "limitations": self.limitations,
            "provenance": self.provenance,
        }


class ComparableStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def input_dir(self, assignment_id: str) -> Path:
        return assignment_directory(self.root, assignment_id) / "comparables"

    def output_dir(self, assignment_id: str) -> Path:
        return self.root / "outputs" / "real-estate" / "assignments" / assignment_id / "comparables"

    def config_path(self) -> Path:
        local = self.root / "config" / "comparable-intelligence.local.yaml"
        return local if local.exists() else self.root / "config" / "comparable-intelligence.example.yaml"

    def config(self) -> JsonMap:
        path = self.config_path()
        if not path.exists():
            return default_config()
        data = load_yaml(path)
        config = data.get("comparable_intelligence", data)
        return {**default_config(), **_map(config)}

    def input_files(self, assignment_id: str) -> list[Path]:
        directory = self.input_dir(assignment_id)
        if not directory.exists():
            return []
        return sorted(
            path for path in directory.rglob("*") if path.is_file() and path.suffix.lower() in {".yaml", ".yml", ".json", ".csv"}
        )

    def load(self, assignment_id: str) -> JsonMap:
        path = self.output_dir(assignment_id) / "comparable-universe.json"
        if not path.exists():
            return {}
        return read_json(path)

    def review_state_path(self, assignment_id: str) -> Path:
        return self.input_dir(assignment_id) / "review-state.json"

    def load_review_state(self, assignment_id: str) -> JsonMap:
        path = self.review_state_path(assignment_id)
        return read_json(path) if path.exists() else {"comparables": {}}

    def save_review_state(self, assignment_id: str, state: JsonMap) -> None:
        write_json(self.review_state_path(assignment_id), state)

    def save(self, universe: ComparableUniverse, previous: JsonMap) -> None:
        directory = self.output_dir(universe.assignment_id)
        data = universe.to_dict()
        delta = comparable_delta(previous, data)
        write_json(directory / "comparable-universe.json", data)
        write_json(directory / "comparable-coverage.json", data["coverage"])
        write_json(directory / "comparable-conflicts.json", {"conflicts": data["conflicts"]})
        write_json(directory / "comparable-delta.json", delta)
        history_path = directory / "comparable-history.json"
        history = _map_list(read_json(history_path).get("snapshots", [])) if history_path.exists() else []
        if not history or history[-1].get("snapshot_id") != snapshot_id(data):
            history.append({"snapshot_id": snapshot_id(data), "created_at": data["created_at"], "counts": data["counts"], "delta": delta})
        write_json(history_path, {"snapshots": history})
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "comparable-universe.md").write_text(render_universe_markdown(universe), encoding="utf-8")
        (directory / "comparable-coverage.md").write_text(render_coverage_markdown(universe), encoding="utf-8")
        (directory / "comparable-review-queue.md").write_text(render_review_queue_markdown(universe), encoding="utf-8")

    def summary(self) -> JsonMap:
        base = self.root / "outputs" / "real-estate" / "assignments"
        universes: list[JsonMap] = []
        if base.exists():
            for path in sorted(base.glob("*/comparables/comparable-universe.json")):
                try:
                    universes.append(read_json(path))
                except Exception:
                    continue
        return comparable_dashboard_summary(universes)

    def create_template(self, assignment_id: str) -> Path:
        path = self.input_dir(assignment_id) / "comparables.yaml"
        if path.exists():
            raise ComparableIntelligenceError(f"Comparable template already exists: {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(_comparable_template(assignment_id), encoding="utf-8")
        return path


class ComparableIntelligenceEngine:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.store = ComparableStore(root)

    def build(self, assignment_id: str, *, overwrite: bool = False) -> ComparableUniverse:
        output = self.store.output_dir(assignment_id) / "comparable-universe.json"
        if output.exists() and not overwrite:
            return universe_from_dict(read_json(output))
        assignment = _load_assignment_snapshot(self.root, assignment_id)
        subject = comparable_subject(assignment)
        config = self.store.config()
        review_state = self.store.load_review_state(assignment_id)
        records, source_errors = self._load_records(assignment_id, review_state)
        records, duplicate_conflicts = detect_duplicates(records)
        conflicts = duplicate_conflicts + detect_value_conflicts(records, config)
        assessments = [assess_comparable(subject, record, config, conflicts) for record in records]
        by_id = {assessment.comparable_id: assessment for assessment in assessments}
        records = [apply_assessment_status(record, by_id.get(record.comparable_id), review_state) for record in records]
        coverage = assess_coverage(assignment_id, subject, records, config)
        review_queue = build_review_queue(records, assessments, conflicts, coverage)
        counts = comparable_counts(records, conflicts, review_queue)
        limitations = [
            "Comparable Intelligence organizes evidence and does not select final comparables.",
            "No valuation opinion, indicated value, or appraisal adjustment is generated.",
        ]
        if not records:
            limitations.append("No comparable input data was found.")
        limitations.extend(source_errors)
        universe = ComparableUniverse(
            assignment_id=assignment_id,
            canonical_assignment_id=assignment_id,
            created_at=_now_iso(),
            version=__version__,
            subject=subject,
            comparables=records,
            assessments=assessments,
            conflicts=conflicts,
            coverage=coverage,
            review_queue=review_queue,
            counts=counts,
            limitations=limitations,
            provenance={
                "engine": "ComparableIntelligenceEngine",
                "version": __version__,
                "input_files": [str(path) for path in self.store.input_files(assignment_id)],
                "config_path": str(self.store.config_path()),
            },
        )
        previous = self.store.load(assignment_id)
        self.store.save(universe, previous)
        return universe

    def status(self, assignment_id: str) -> JsonMap:
        data = self.store.load(assignment_id)
        if not data:
            return {"available": False, "assignment_id": assignment_id, "input_count": len(self.store.input_files(assignment_id))}
        return {"available": True, "assignment_id": assignment_id, **_map(data.get("counts")), "report_path": str(self.store.output_dir(assignment_id) / "comparable-universe.md")}

    def select(self, assignment_id: str, comparable_id: str, *, reviewer: str = "appraiser", confirm: bool = False) -> JsonMap:
        if not confirm:
            raise ComparableIntelligenceError("Selection requires --confirm.")
        return self._update_review_state(assignment_id, comparable_id, {"appraiser_selected": True, "appraiser_review_status": "selected", "appraiser_exclusion_reason": "", "reviewed_by": reviewer})

    def exclude(self, assignment_id: str, comparable_id: str, *, reason: str, reviewer: str = "appraiser", confirm: bool = False) -> JsonMap:
        if not confirm:
            raise ComparableIntelligenceError("Exclusion requires --confirm.")
        if not reason:
            raise ComparableIntelligenceError("Exclusion requires a reason.")
        return self._update_review_state(assignment_id, comparable_id, {"appraiser_selected": False, "appraiser_review_status": "excluded", "appraiser_exclusion_reason": reason, "reviewed_by": reviewer})

    def reset_review(self, assignment_id: str, comparable_id: str) -> JsonMap:
        state = self.store.load_review_state(assignment_id)
        comps = _map(state.get("comparables"))
        comps.pop(comparable_id, None)
        state["comparables"] = comps
        state.setdefault("history", []).append({"comparable_id": comparable_id, "action": "reset_review", "at": _now_iso()})
        self.store.save_review_state(assignment_id, state)
        return state

    def _update_review_state(self, assignment_id: str, comparable_id: str, values: JsonMap) -> JsonMap:
        universe = self.store.load(assignment_id)
        ids = {str(item.get("comparable_id")) for item in _map_list(universe.get("comparables", []))}
        if comparable_id not in ids:
            raise ComparableIntelligenceError(f"Unknown comparable ID: {comparable_id}")
        state = self.store.load_review_state(assignment_id)
        comps = _map(state.get("comparables"))
        record = _map(comps.get(comparable_id))
        record.update(values)
        record["reviewed_at"] = _now_iso()
        comps[comparable_id] = record
        state["comparables"] = comps
        state.setdefault("history", []).append({"comparable_id": comparable_id, "action": record.get("appraiser_review_status"), "at": record["reviewed_at"], "reason": record.get("appraiser_exclusion_reason", "")})
        self.store.save_review_state(assignment_id, state)
        return state

    def _load_records(self, assignment_id: str, review_state: JsonMap) -> tuple[list[ComparableRecord], list[str]]:
        records: list[ComparableRecord] = []
        errors: list[str] = []
        for path in self.store.input_files(assignment_id):
            try:
                records.extend(load_comparable_file(path, review_state))
            except Exception as exc:
                errors.append(f"{path}: {exc}")
        return sorted(records, key=lambda item: item.comparable_id), errors


def load_comparable_file(path: Path, review_state: JsonMap | None = None) -> list[ComparableRecord]:
    suffix = path.suffix.lower()
    if suffix in {".yaml", ".yml"}:
        data = load_yaml(path)
        rows = _map_list(data.get("comparables", []))
    elif suffix == ".json":
        data = read_json(path)
        rows = _map_list(data.get("comparables", data if isinstance(data, list) else []))
    elif suffix == ".csv":
        with path.open("r", encoding="utf-8", newline="") as handle:
            rows = [dict(row) for row in csv.DictReader(handle)]
    else:
        return []
    records = []
    checksum = _file_checksum(path)
    for index, row in enumerate(rows, start=1):
        records.append(record_from_row(row, path, checksum, index, review_state or {}))
    return records


def record_from_row(row: JsonMap, path: Path, checksum: str, row_number: int, review_state: JsonMap) -> ComparableRecord:
    source_type = _str(row.get("source_type") or "structured_file")
    raw_id = _str(row.get("comparable_id") or row.get("listing_id") or row.get("parcel_number") or row.get("address") or row.get("property_address") or f"{path.stem}-{row_number}")
    comparable_id = _slug(raw_id)
    address = _str(row.get("property_address") or row.get("address"))
    sale_date = normalize_date(row.get("sale_date"))
    missing = [field for field in CORE_FIELDS if not _field_available(row, field)]
    review = _map(_map(review_state.get("comparables")).get(comparable_id))
    source_path = str(path)
    return ComparableRecord(
        comparable_id=comparable_id,
        source_record_id=_str(row.get("source_record_id") or f"{path.name}:{row_number}"),
        source_type=source_type,
        source_path=source_path,
        source_checksum=checksum,
        listing_id=_str(row.get("listing_id")),
        parcel_number=_str(row.get("parcel_number") or row.get("apn")),
        property_address=address,
        normalized_address=normalize_address(address),
        property_status=normalize_status(row.get("property_status") or row.get("status")),
        sale_date=sale_date,
        sale_price=to_number(row.get("sale_price")),
        list_date=normalize_date(row.get("list_date")),
        original_list_price=to_number(row.get("original_list_price")),
        current_list_price=to_number(row.get("current_list_price") or row.get("list_price")),
        pending_date=normalize_date(row.get("pending_date")),
        days_on_market=to_int(row.get("days_on_market")),
        financing_type=_str(row.get("financing_type")),
        concessions=_str(row.get("concessions")),
        arms_length_status=normalize_status(row.get("arms_length_status")),
        property_type=normalize_property_type(row.get("property_type")),
        design_style=_str(row.get("design_style")),
        year_built=to_int(row.get("year_built")),
        effective_age=to_int(row.get("effective_age")),
        condition=normalize_code(row.get("condition"), "c"),
        quality=normalize_code(row.get("quality"), "q"),
        gross_living_area=to_number(row.get("gross_living_area") or row.get("gla")),
        lot_size=to_number(row.get("lot_size")),
        bedroom_count=to_number(row.get("bedroom_count") or row.get("bedrooms")),
        bathroom_count=to_number(row.get("bathroom_count") or row.get("bathrooms")),
        garage_count=to_number(row.get("garage_count")),
        parking_count=to_number(row.get("parking_count")),
        pool=to_bool(row.get("pool")),
        spa=to_bool(row.get("spa")),
        view=_str(row.get("view")),
        accessory_unit=to_bool(row.get("accessory_unit") or row.get("adu")),
        basement=to_bool(row.get("basement")),
        location_features=_string_list(row.get("location_features")),
        zoning=_str(row.get("zoning")),
        ownership_interest=_str(row.get("ownership_interest")),
        city=_str(row.get("city")),
        neighborhood=_str(row.get("neighborhood")),
        market_area=_str(row.get("market_area")),
        latitude=to_number(row.get("latitude")),
        longitude=to_number(row.get("longitude")),
        distance_from_subject=to_number(row.get("distance_from_subject") or row.get("distance_miles")),
        source_paths=_string_list(row.get("source_paths")) or [source_path],
        source_fields={key: value for key, value in row.items() if key not in {"comparables"}},
        verification_status=_str(row.get("verification_status") or "source_reported"),
        confidence=_str(row.get("confidence") or "unknown"),
        notes=_string_list(row.get("notes")),
        missing_fields=missing,
        conflicts=[],
        candidate_status=_str(review.get("candidate_status") or "review_required"),
        appraiser_review_status=_str(review.get("appraiser_review_status") or "not_reviewed"),
        appraiser_selected=bool(review.get("appraiser_selected", False)),
        appraiser_exclusion_reason=_str(review.get("appraiser_exclusion_reason")),
        reviewed_at=_str(review.get("reviewed_at")),
        reviewed_by=_str(review.get("reviewed_by")),
    )


def assess_comparable(subject: JsonMap, record: ComparableRecord, config: JsonMap, conflicts: list[ComparableConflict]) -> ComparableAssessment:
    differences = [
        categorical_component("property_type_match", subject.get("property_type"), record.property_type, record.source_paths),
        numeric_component("geographic_relevance", 0, record.distance_from_subject, config.get("distance", {}), "miles", record.source_paths),
        recency_component(subject.get("sale_or_effective_date") or subject.get("effective_date"), record.sale_date, config.get("recency", {}), record.source_paths),
        numeric_component("gross_living_area_similarity", subject.get("gross_living_area"), record.gross_living_area, config.get("gross_living_area", {}), "percent", record.source_paths),
        numeric_component("lot_size_similarity", subject.get("lot_size"), record.lot_size, config.get("lot_size", {}), "percent", record.source_paths),
        count_component("bedroom_similarity", subject.get("bedroom_count"), record.bedroom_count, record.source_paths),
        count_component("bathroom_similarity", subject.get("bathroom_count"), record.bathroom_count, record.source_paths),
        age_component(subject, record, record.source_paths),
        code_component("quality_similarity", subject.get("quality"), record.quality, "q", record.source_paths),
        code_component("condition_similarity", subject.get("condition"), record.condition, "c", record.source_paths),
        boolean_component("pool", subject.get("pool"), record.pool, record.source_paths),
        data_completeness_component(record),
    ]
    limitations = []
    if record.property_status and record.property_status not in {"closed_sale", "sold"}:
        limitations.append("Listing or non-closed status retained as contextual evidence.")
    if record.arms_length_status in {"non_arms_length", "not_arms_length"}:
        limitations.append("Reported non-arm's-length transaction.")
    if record.missing_fields:
        limitations.append(f"Missing core fields: {', '.join(record.missing_fields)}")
    if any(conflict.comparable_id == record.comparable_id for conflict in conflicts):
        limitations.append("Open comparable conflict requires review.")
    status = tier_for(record, differences, limitations)
    return ComparableAssessment(record.comparable_id, status, differences, limitations, review_items_for(record, status, limitations))


def tier_for(record: ComparableRecord, differences: list[ComparableDifference], limitations: list[str]) -> str:
    if record.property_status not in {"closed_sale", "sold"} and record.gross_living_area is not None:
        return "contextual_candidate"
    if record.missing_fields:
        return "insufficient_data"
    if "Open comparable conflict requires review." in limitations:
        return "review_required"
    if any(item.assessment == "major_difference" for item in differences if item.component in {"property_type_match", "geographic_relevance", "transaction_recency", "gross_living_area_similarity"}):
        return "secondary_candidate"
    if any(item.assessment in {"meaningful_difference", "major_difference"} for item in differences):
        return "secondary_candidate"
    return "primary_candidate"


def apply_assessment_status(record: ComparableRecord, assessment: ComparableAssessment | None, review_state: JsonMap) -> ComparableRecord:
    review = _map(_map(review_state.get("comparables")).get(record.comparable_id))
    status = record.candidate_status
    if review.get("appraiser_review_status") == "selected":
        status = "appraiser_selected"
    elif review.get("appraiser_review_status") == "excluded":
        status = "appraiser_excluded"
    elif assessment:
        status = assessment.candidate_status
    return ComparableRecord(**{**record.to_dict(), "candidate_status": status})


def comparable_subject(assignment: JsonMap) -> JsonMap:
    subject = _map(assignment.get("subject"))
    facts = _map_list(assignment.get("facts", []))
    fact_map = {str(item.get("field_name")): item.get("value") for item in facts}
    return {
        "address": _str(subject.get("address") or assignment.get("subject_address")),
        "property_type": normalize_property_type(assignment.get("property_type") or fact_map.get("property_type")),
        "gross_living_area": to_number(fact_map.get("gross_living_area") or fact_map.get("gla") or assignment.get("gross_living_area")),
        "lot_size": to_number(fact_map.get("lot_size") or assignment.get("lot_size")),
        "condition": normalize_code(fact_map.get("condition") or assignment.get("condition"), "c"),
        "quality": normalize_code(fact_map.get("quality") or assignment.get("quality"), "q"),
        "bedroom_count": to_number(fact_map.get("bedroom_count") or fact_map.get("bedrooms")),
        "bathroom_count": to_number(fact_map.get("bathroom_count") or fact_map.get("bathrooms")),
        "year_built": to_int(fact_map.get("year_built")),
        "effective_date": normalize_date(assignment.get("effective_date")),
        "sale_or_effective_date": normalize_date(fact_map.get("sale_or_effective_date") or assignment.get("effective_date")),
        "pool": to_bool(fact_map.get("pool")),
    }


def detect_duplicates(records: list[ComparableRecord]) -> tuple[list[ComparableRecord], list[ComparableConflict]]:
    conflicts: list[ComparableConflict] = []
    seen: dict[str, str] = {}
    duplicate_ids: set[str] = set()
    for record in records:
        keys = [key for key in duplicate_keys(record) if key]
        for key in keys:
            if key in seen and seen[key] != record.comparable_id:
                duplicate_ids.update({seen[key], record.comparable_id})
                conflicts.append(
                    ComparableConflict(
                        conflict_id=_stable_id("comp_duplicate", [key, seen[key], record.comparable_id]),
                        comparable_id=record.comparable_id,
                        field_name="identity",
                        values=[seen[key], record.comparable_id],
                        source_paths=record.source_paths,
                        severity="medium",
                        status="open",
                        preferred_source="",
                        reason="Potential duplicate based on deterministic comparable identity.",
                    )
                )
            else:
                seen[key] = record.comparable_id
    updated = []
    for record in records:
        if record.comparable_id in duplicate_ids:
            updated.append(ComparableRecord(**{**record.to_dict(), "candidate_status": "potential_duplicate"}))
        else:
            updated.append(record)
    return updated, conflicts


def duplicate_keys(record: ComparableRecord) -> list[str]:
    return [
        f"listing:{record.listing_id}" if record.listing_id else "",
        f"parcel-date:{record.parcel_number}:{record.sale_date}" if record.parcel_number and record.sale_date else "",
        f"address-date:{record.normalized_address}:{record.sale_date}" if record.normalized_address and record.sale_date else "",
        f"address-price:{record.normalized_address}:{record.sale_price}" if record.normalized_address and record.sale_price is not None else "",
        f"source:{record.source_record_id}" if record.source_record_id else "",
    ]


def detect_value_conflicts(records: list[ComparableRecord], config: JsonMap) -> list[ComparableConflict]:
    conflicts = []
    by_identity: dict[str, list[ComparableRecord]] = {}
    for record in records:
        key = record.listing_id or f"{record.normalized_address}:{record.sale_date}"
        if key:
            by_identity.setdefault(key, []).append(record)
    for items in by_identity.values():
        if len(items) < 2:
            continue
        for field_name in ["sale_price", "sale_date", "gross_living_area", "lot_size", "property_status", "listing_id", "parcel_number", "condition", "quality"]:
            values = sorted({_str(getattr(item, field_name)) for item in items if _str(getattr(item, field_name))})
            if len(values) > 1:
                conflicts.append(
                    ComparableConflict(
                        conflict_id=_stable_id("comp_conflict", [field_name, *values]),
                        comparable_id=items[0].comparable_id,
                        field_name=field_name,
                        values=values,
                        source_paths=sorted({path for item in items for path in item.source_paths}),
                        severity="high" if field_name in {"sale_price", "sale_date"} else "medium",
                        status="open",
                        preferred_source=_preferred_source(items, config),
                        reason="Structured source values conflict; appraiser review required.",
                    )
                )
    return conflicts


def assess_coverage(assignment_id: str, subject: JsonMap, records: list[ComparableRecord], config: JsonMap) -> ComparableCoverage:
    usable = [item for item in records if item.candidate_status in {"primary_candidate", "secondary_candidate", "contextual_candidate"}]
    dimensions = {
        "property_type": categorical_coverage(subject.get("property_type"), [r.property_type for r in usable]),
        "location": numeric_coverage(0, [r.distance_from_subject for r in usable], lower_is_better=True),
        "sale_date": recency_coverage(subject.get("sale_or_effective_date"), [r.sale_date for r in usable], _map(config.get("recency"))),
        "gross_living_area": bracket_coverage(subject.get("gross_living_area"), [r.gross_living_area for r in usable]),
        "lot_size": bracket_coverage(subject.get("lot_size"), [r.lot_size for r in usable]),
        "bedroom_count": bracket_coverage(subject.get("bedroom_count"), [r.bedroom_count for r in usable]),
        "bathroom_count": bracket_coverage(subject.get("bathroom_count"), [r.bathroom_count for r in usable]),
        "age": bracket_coverage(subject.get("year_built"), [r.year_built for r in usable], inverse=True),
        "quality": code_coverage(subject.get("quality"), [r.quality for r in usable], "q"),
        "condition": code_coverage(subject.get("condition"), [r.condition for r in usable], "c"),
        "pool": categorical_coverage(subject.get("pool"), [r.pool for r in usable]),
        "accessory_unit": categorical_coverage(subject.get("accessory_unit"), [r.accessory_unit for r in usable]),
    }
    limitations = [f"{key} coverage is {value['coverage']}." for key, value in dimensions.items() if value.get("coverage") in {"limited", "absent", "unavailable"}]
    questions = research_questions(dimensions)
    return ComparableCoverage(assignment_id, {key: value["coverage"] for key, value in dimensions.items()}, dimensions, limitations, questions)


def comparable_counts(records: list[ComparableRecord], conflicts: list[ComparableConflict], review_queue: list[JsonMap]) -> JsonMap:
    counts = {status: sum(1 for item in records if item.candidate_status == status) for status in sorted(CANDIDATE_STATUSES)}
    return {
        "comparable_count": len(records),
        **counts,
        "open_conflict_count": sum(1 for item in conflicts if item.status == "open"),
        "review_item_count": len(review_queue),
        "appraiser_selected_count": sum(1 for item in records if item.appraiser_selected),
    }


def build_review_queue(records: list[ComparableRecord], assessments: list[ComparableAssessment], conflicts: list[ComparableConflict], coverage: ComparableCoverage) -> list[JsonMap]:
    queue = []
    for record in records:
        for field in record.missing_fields:
            queue.append(_review_item(record.comparable_id, "missing_field", field, "medium", f"Missing {field}."))
        if record.candidate_status == "potential_duplicate":
            queue.append(_review_item(record.comparable_id, "duplicate_candidate", "identity", "medium", "Potential duplicate comparable."))
        if record.appraiser_review_status == "not_reviewed":
            queue.append(_review_item(record.comparable_id, "appraiser_selection_not_reviewed", "review_state", "low", "Appraiser review state has not been recorded."))
    for conflict in conflicts:
        queue.append(_review_item(conflict.comparable_id, "source_conflict", conflict.field_name, conflict.severity, conflict.reason))
    for dimension, level in coverage.levels.items():
        if level in {"limited", "absent"}:
            queue.append(_review_item("", "coverage_gap", dimension, "medium", f"{dimension} coverage is {level}."))
    return sorted(queue, key=lambda item: (item["severity"], item["item_type"], item["comparable_id"]))


def review_items_for(record: ComparableRecord, status: str, limitations: list[str]) -> list[JsonMap]:
    return [_review_item(record.comparable_id, "candidate_limitation", status, "low", item) for item in limitations]


def comparable_delta(previous: JsonMap, current: JsonMap) -> JsonMap:
    prev = {str(item.get("comparable_id")): item for item in _map_list(previous.get("comparables", []))}
    cur = {str(item.get("comparable_id")): item for item in _map_list(current.get("comparables", []))}
    return {
        "new_candidates": sorted(set(cur) - set(prev)),
        "updated_candidates": sorted(item for item in set(cur) & set(prev) if cur[item] != prev[item]),
        "removed_source_references": sorted(set(prev) - set(cur)),
        "candidate_tier_changes": sorted(item for item in set(cur) & set(prev) if cur[item].get("candidate_status") != prev[item].get("candidate_status")),
        "conflict_count_change": int(_map(current.get("counts")).get("open_conflict_count", 0)) - int(_map(previous.get("counts")).get("open_conflict_count", 0) or 0),
        "coverage_changed": _map(previous.get("coverage")).get("levels") != _map(current.get("coverage")).get("levels"),
        "created_at": _now_iso(),
    }


def comparable_dashboard_summary(universes: list[JsonMap]) -> JsonMap:
    records = [record for universe in universes for record in _map_list(universe.get("comparables", []))]
    counts = [_map(universe.get("counts")) for universe in universes]
    limited = [universe for universe in universes if any(level in {"limited", "absent"} for level in _map(_map(universe.get("coverage")).get("levels")).values())]
    return {
        "assignments_with_comparable_data": sum(1 for universe in universes if _map(universe.get("counts")).get("comparable_count", 0)),
        "total_comparable_records": len(records),
        "primary_candidate_count": sum(int(item.get("primary_candidate", 0) or 0) for item in counts),
        "secondary_candidate_count": sum(int(item.get("secondary_candidate", 0) or 0) for item in counts),
        "contextual_candidate_count": sum(int(item.get("contextual_candidate", 0) or 0) for item in counts),
        "review_required_count": sum(int(item.get("review_required", 0) or 0) + int(item.get("insufficient_data", 0) or 0) + int(item.get("potential_duplicate", 0) or 0) for item in counts),
        "open_comparable_conflict_count": sum(int(item.get("open_conflict_count", 0) or 0) for item in counts),
        "assignments_with_limited_coverage": len(limited),
        "latest_comparable_run_at": max([str(universe.get("created_at", "")) for universe in universes] or [""]),
        "key_comparable_report_paths": [str(Path("outputs/real-estate/assignments") / str(universe.get("assignment_id")) / "comparables" / "comparable-universe.md") for universe in universes[:5]],
    }


def default_config() -> JsonMap:
    return {
        "recency": {"strong_days": 180, "acceptable_days": 365, "review_days": 730},
        "gross_living_area": {"strong_percent": 10, "acceptable_percent": 20, "major_percent": 35},
        "lot_size": {"strong_percent": 15, "acceptable_percent": 30, "major_percent": 50},
        "distance": {"strong_miles": 1, "acceptable_miles": 3, "review_miles": 10},
        "source_priority": ["appraiser_verified", "signed_engagement", "mls_export", "public_record", "client_provided", "derived"],
    }


def numeric_component(component: str, subject_value: Any, comparable_value: Any, thresholds: Any, mode: str, sources: list[str]) -> ComparableDifference:
    s = to_number(subject_value)
    c = to_number(comparable_value)
    if s is None or c is None:
        return ComparableDifference(component, subject_value, comparable_value, "", "", "unavailable", "medium", "Required numeric data is unavailable.", sources)
    diff = c - s
    normalized = abs(diff) / abs(s) * 100 if mode == "percent" and s else abs(diff)
    config = _map(thresholds)
    if mode == "miles":
        assessment = threshold_assessment(normalized, float(config.get("strong_miles", 1)), float(config.get("acceptable_miles", 3)), float(config.get("review_miles", 10)))
    else:
        assessment = threshold_assessment(normalized, float(config.get("strong_percent", 10)), float(config.get("acceptable_percent", 20)), float(config.get("major_percent", 35)))
    return ComparableDifference(component, s, c, diff, round(normalized, 2), assessment, severity_for(assessment), f"{component} difference is {round(normalized, 2)} {mode}.", sources)


def recency_component(subject_date: Any, sale_date: Any, thresholds: Any, sources: list[str]) -> ComparableDifference:
    sd = parse_date(subject_date) or date.today()
    cd = parse_date(sale_date)
    if not cd:
        return ComparableDifference("transaction_recency", str(subject_date or ""), str(sale_date or ""), "", "", "unavailable", "high", "Sale date is unavailable.", sources)
    days = abs((sd - cd).days)
    config = _map(thresholds)
    assessment = threshold_assessment(days, int(config.get("strong_days", 180)), int(config.get("acceptable_days", 365)), int(config.get("review_days", 730)))
    return ComparableDifference("transaction_recency", sd.isoformat(), cd.isoformat(), days, days, assessment, severity_for(assessment), f"Sale date is {days} days from the subject effective date.", sources)


def categorical_component(component: str, subject_value: Any, comparable_value: Any, sources: list[str]) -> ComparableDifference:
    s = _str(subject_value)
    c = _str(comparable_value)
    if not s or not c:
        return ComparableDifference(component, s, c, "", "", "unavailable", "medium", "Categorical data is unavailable.", sources)
    assessment = "strong_match" if s == c else "major_difference"
    return ComparableDifference(component, s, c, "", "", assessment, severity_for(assessment), "Exact categorical comparison only.", sources)


def count_component(component: str, subject_value: Any, comparable_value: Any, sources: list[str]) -> ComparableDifference:
    s = to_number(subject_value)
    c = to_number(comparable_value)
    if s is None or c is None:
        return ComparableDifference(component, subject_value, comparable_value, "", "", "unavailable", "low", "Count data is unavailable.", sources)
    diff = c - s
    assessment = "strong_match" if diff == 0 else "acceptable_match" if abs(diff) <= 1 else "meaningful_difference"
    return ComparableDifference(component, s, c, diff, diff, assessment, severity_for(assessment), f"Count difference is {diff}.", sources)


def code_component(component: str, subject_value: Any, comparable_value: Any, prefix: str, sources: list[str]) -> ComparableDifference:
    s = code_number(subject_value, prefix)
    c = code_number(comparable_value, prefix)
    if s is None or c is None:
        return ComparableDifference(component, subject_value, comparable_value, "", "", "unavailable", "low", "Ordered code data is unavailable.", sources)
    diff = c - s
    assessment = "strong_match" if diff == 0 else "acceptable_match" if abs(diff) == 1 else "meaningful_difference"
    return ComparableDifference(component, subject_value, comparable_value, diff, diff, assessment, severity_for(assessment), "Ordinal code difference only; no adjustment inferred.", sources)


def boolean_component(component: str, subject_value: Any, comparable_value: Any, sources: list[str]) -> ComparableDifference:
    s = to_bool(subject_value)
    c = to_bool(comparable_value)
    if s is None or c is None:
        return ComparableDifference(component, subject_value, comparable_value, "", "", "unavailable", "low", "Amenity data is unavailable.", sources)
    assessment = "strong_match" if s == c else "meaningful_difference"
    return ComparableDifference(component, s, c, "", "", assessment, severity_for(assessment), "Boolean amenity comparison only.", sources)


def age_component(subject: JsonMap, record: ComparableRecord, sources: list[str]) -> ComparableDifference:
    return count_component("age_similarity", subject.get("year_built"), record.year_built, sources)


def data_completeness_component(record: ComparableRecord) -> ComparableDifference:
    missing = len(record.missing_fields)
    assessment = "strong_match" if missing == 0 else "review_required" if missing >= 3 else "acceptable_match"
    return ComparableDifference("data_completeness", "required core fields", f"{missing} missing", missing, missing, assessment, severity_for(assessment), f"{missing} core fields missing.", record.source_paths)


def threshold_assessment(value: float, strong: float, acceptable: float, major: float) -> str:
    if value <= strong:
        return "strong_match"
    if value <= acceptable:
        return "acceptable_match"
    if value <= major:
        return "meaningful_difference"
    return "major_difference"


def severity_for(assessment: str) -> str:
    return {"strong_match": "low", "acceptable_match": "low", "meaningful_difference": "medium", "major_difference": "high", "review_required": "medium"}.get(assessment, "low")


def bracket_coverage(subject_value: Any, values: list[Any], inverse: bool = False) -> JsonMap:
    s = to_number(subject_value)
    nums = sorted(item for item in (to_number(v) for v in values) if item is not None)
    if s is None:
        return {"coverage": "unavailable", "below": 0, "above": 0, "matching": 0, "candidate_count": len(nums), "bracketing": "unavailable"}
    below = sum(1 for item in nums if item < s)
    above = sum(1 for item in nums if item > s)
    matching = sum(1 for item in nums if item == s)
    level = "excellent" if below and above else "adequate" if matching or below or above else "absent"
    return {"coverage": level, "below": below, "above": above, "matching": matching, "candidate_count": len(nums), "bracketing": "fully_bracketed" if below and above else "partially_bracketed" if below or above or matching else "not_bracketed"}


def categorical_coverage(subject_value: Any, values: list[Any]) -> JsonMap:
    s = _str(subject_value)
    vals = [_str(v) for v in values if _str(v)]
    if not s:
        return {"coverage": "unavailable", "matching": 0, "candidate_count": len(vals)}
    matching = sum(1 for item in vals if item == s)
    return {"coverage": "excellent" if matching >= 3 else "adequate" if matching else "limited" if vals else "absent", "matching": matching, "candidate_count": len(vals)}


def numeric_coverage(subject_value: Any, values: list[Any], *, lower_is_better: bool = False) -> JsonMap:
    nums = [item for item in (to_number(v) for v in values) if item is not None]
    if not nums:
        return {"coverage": "absent", "candidate_count": 0}
    if lower_is_better:
        close = sum(1 for item in nums if item <= 3)
        return {"coverage": "excellent" if close >= 3 else "adequate" if close else "limited", "candidate_count": len(nums), "matching": close}
    return bracket_coverage(subject_value, nums)


def recency_coverage(subject_date: Any, values: list[Any], config: JsonMap) -> JsonMap:
    sd = parse_date(subject_date) or date.today()
    days = [abs((sd - cd).days) for cd in (parse_date(value) for value in values) if cd]
    if not days:
        return {"coverage": "absent", "candidate_count": 0}
    recent = sum(1 for item in days if item <= int(config.get("acceptable_days", 365)))
    return {"coverage": "excellent" if recent >= 3 else "adequate" if recent else "limited", "candidate_count": len(days), "matching": recent}


def code_coverage(subject_value: Any, values: list[Any], prefix: str) -> JsonMap:
    s = code_number(subject_value, prefix)
    nums = [item for item in (code_number(value, prefix) for value in values) if item is not None]
    return bracket_coverage(s, nums)


def research_questions(dimensions: JsonMap) -> list[str]:
    questions = []
    if _map(dimensions.get("gross_living_area")).get("bracketing") != "fully_bracketed":
        questions.append("Obtain one additional sale above or below the subject's GLA if available.")
    if _map(dimensions.get("sale_date")).get("coverage") in {"limited", "absent"}:
        questions.append("Verify whether a more recent closed sale is available.")
    if _map(dimensions.get("property_type")).get("coverage") in {"limited", "absent"}:
        questions.append("Confirm that candidate property types match the subject.")
    return questions or ["Verify source details for any candidate used in the appraisal analysis."]


def normalize_address(value: Any) -> str:
    text = html.unescape(_str(value)).replace("\u00a0", " ").lower()
    text = re.sub(r"[,.]", " ", text)
    replacements = {"street": "st", "avenue": "ave", "boulevard": "blvd", "drive": "dr", "road": "rd", "lane": "ln", "court": "ct", "place": "pl", "circle": "cir", "#": "unit "}
    for old, new in replacements.items():
        text = re.sub(rf"\b{re.escape(old)}\b", new, text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_date(value: Any) -> str:
    parsed = parse_date(value)
    return parsed.isoformat() if parsed else ""


def parse_date(value: Any) -> date | None:
    text = _str(value)
    if not text:
        return None
    text = text.split("T", 1)[0]
    for fmt in ["%Y-%m-%d", "%m/%d/%Y", "%m-%d-%Y", "%Y/%m/%d"]:
        try:
            return datetime.strptime(text, fmt).date()
        except ValueError:
            pass
    return None


def normalize_status(value: Any) -> str:
    text = re.sub(r"[^a-z0-9]+", "_", _str(value).lower()).strip("_")
    synonyms = {"sold": "closed_sale", "closed": "closed_sale", "closed_sale": "closed_sale", "active": "active_listing", "listing": "active_listing", "pending": "pending_sale", "arm_s_length": "arms_length", "arms_length": "arms_length"}
    return synonyms.get(text, text)


def normalize_property_type(value: Any) -> str:
    text = _slug(_str(value))
    return {"sfr": "single_family_residential", "single_family": "single_family_residential", "single_family_residential": "single_family_residential", "condo": "condominium"}.get(text, text)


def normalize_code(value: Any, prefix: str) -> str:
    text = _str(value).upper().replace(" ", "")
    if re.fullmatch(rf"{prefix.upper()}[1-6]", text):
        return text
    if re.fullmatch(r"[1-6]", text):
        return f"{prefix.upper()}{text}"
    return text


def code_number(value: Any, prefix: str) -> int | None:
    text = normalize_code(value, prefix)
    match = re.fullmatch(rf"{prefix.upper()}([1-6])", text)
    return int(match.group(1)) if match else None


def to_number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    text = _str(value)
    if not text:
        return None
    text = re.sub(r"[$,]", "", text)
    text = re.sub(r"\s*(sf|sqft|sq ft|miles|mi)\b", "", text, flags=re.I)
    try:
        return float(text)
    except ValueError:
        return None


def to_int(value: Any) -> int | None:
    number = to_number(value)
    return int(number) if number is not None else None


def to_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    text = _str(value).lower()
    if text in {"yes", "true", "y", "1"}:
        return True
    if text in {"no", "false", "n", "0"}:
        return False
    return None


def render_universe_markdown(universe: ComparableUniverse) -> str:
    data = universe.to_dict()
    lines = [
        "# Comparable Universe",
        "",
        "## Assignment Header",
        "",
        f"- Assignment ID: `{universe.assignment_id}`",
        f"- Comparable records: `{universe.counts.get('comparable_count', 0)}`",
        "",
        "## Subject Summary",
        "",
        *[f"- {key}: `{value}`" for key, value in universe.subject.items()],
        "",
        "## Executive Comparable Summary",
        "",
        f"- Primary candidates: `{universe.counts.get('primary_candidate', 0)}`",
        f"- Secondary candidates: `{universe.counts.get('secondary_candidate', 0)}`",
        f"- Contextual candidates: `{universe.counts.get('contextual_candidate', 0)}`",
        f"- Review-required candidates: `{universe.counts.get('review_required', 0)}`",
        f"- Open conflicts: `{universe.counts.get('open_conflict_count', 0)}`",
        "",
    ]
    for title, status in [("Primary Candidates", "primary_candidate"), ("Secondary Candidates", "secondary_candidate"), ("Contextual Evidence", "contextual_candidate"), ("Review-Required Candidates", "review_required")]:
        lines.extend([f"## {title}", ""])
        subset = [record for record in universe.comparables if record.candidate_status == status]
        lines.extend(_record_lines(subset) or ["None."])
        lines.append("")
    lines.extend(["## Comparable Detail Matrix", ""])
    lines.extend(_record_lines(universe.comparables) or ["None."])
    lines.extend(["", "## Coverage and Bracketing", ""])
    for key, value in universe.coverage.bracketing.items():
        lines.append(f"- {key}: `{value.get('coverage')}` / `{value.get('bracketing', '')}`")
    lines.extend(["", "## Data Conflicts", ""])
    lines.extend(f"- {item.field_name}: {', '.join(str(v) for v in item.values)} ({item.reason})" for item in universe.conflicts) or lines.append("None.")
    lines.extend(["", "## Missing Data", ""])
    missing = [f"- {record.comparable_id}: {', '.join(record.missing_fields)}" for record in universe.comparables if record.missing_fields]
    lines.extend(missing or ["None."])
    lines.extend(["", "## Appraiser Review State", ""])
    lines.extend(f"- {record.comparable_id}: `{record.appraiser_review_status}` selected=`{record.appraiser_selected}` reason=`{record.appraiser_exclusion_reason}`" for record in universe.comparables)
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in universe.limitations)
    lines.extend(["", "## Provenance", ""])
    for path in universe.provenance.get("input_files", []):
        lines.append(f"- `{path}`")
    return "\n".join(lines) + "\n"


def render_coverage_markdown(universe: ComparableUniverse) -> str:
    lines = ["# Comparable Coverage", "", "## Coverage Summary", ""]
    for key, level in universe.coverage.levels.items():
        lines.append(f"- {key}: `{level}`")
    for section in ["Recency", "Geography", "GLA", "Lot Size", "Bed/Bath", "Age", "Quality", "Condition", "Amenities", "Special Features"]:
        lines.extend(["", f"## {section}", ""])
        key = section.lower().replace("/", "_").replace(" ", "_")
        related = {k: v for k, v in universe.coverage.bracketing.items() if key in k or (section == "GLA" and k == "gross_living_area")}
        lines.extend(f"- {k}: `{v}`" for k, v in related.items()) if related else lines.append("See coverage summary.")
    lines.extend(["", "## Coverage Gaps", ""])
    lines.extend(f"- {item}" for item in universe.coverage.limitations or ["None."])
    lines.extend(["", "## Recommended Research Questions", ""])
    lines.extend(f"- {item}" for item in universe.coverage.research_questions)
    lines.extend(["", "## Limitations", "", "- Coverage identifies factual gaps only. It does not recommend value or adjustments."])
    return "\n".join(lines) + "\n"


def render_review_queue_markdown(universe: ComparableUniverse) -> str:
    lines = ["# Comparable Review Queue", ""]
    for item in universe.review_queue:
        lines.append(f"- {item.get('severity')}: {item.get('item_type')} {item.get('comparable_id')} - {item.get('reason')}")
    if not universe.review_queue:
        lines.append("None.")
    return "\n".join(lines) + "\n"


def _record_lines(records: list[ComparableRecord]) -> list[str]:
    return [
        f"- `{record.comparable_id}` {record.property_address} status=`{record.property_status}` sale_date=`{record.sale_date}` price=`{record.sale_price}` GLA=`{record.gross_living_area}` distance=`{record.distance_from_subject}`"
        for record in records
    ]


def _review_item(comparable_id: str, item_type: str, field: str, severity: str, reason: str) -> JsonMap:
    return {"item_id": _stable_id("comp_review", [comparable_id, item_type, field, reason]), "comparable_id": comparable_id, "item_type": item_type, "field": field, "severity": severity, "reason": reason, "status": "open"}


def _load_assignment_snapshot(root: Path, assignment_id: str) -> JsonMap:
    store = RealEstateAssignmentStore(root)
    path = store.output_dir(assignment_id) / "assignment.json"
    if not path.exists():
        try:
            store.build(assignment_id)
        except Exception:
            pass
    if path.exists():
        return read_json(path)
    assignment_path = assignment_directory(root, assignment_id) / "assignment.yaml"
    if not assignment_path.exists():
        raise ComparableIntelligenceError(f"No canonical assignment found: {assignment_id}")
    data = load_yaml(assignment_path)
    assignment = _map(data.get("assignment"))
    return {"assignment_id": assignment_id, **assignment}


def universe_from_dict(data: JsonMap) -> ComparableUniverse:
    records = [record_from_dict(item) for item in _map_list(data.get("comparables", []))]
    assessments = [
        ComparableAssessment(str(item.get("comparable_id", "")), str(item.get("candidate_status", "")), [ComparableDifference(**diff) for diff in _map_list(item.get("differences", []))], _string_list(item.get("limitations")), _map_list(item.get("review_items")))
        for item in _map_list(data.get("assessments", []))
    ]
    conflicts = [ComparableConflict(**item) for item in _map_list(data.get("conflicts", []))]
    coverage = ComparableCoverage(**_map(data.get("coverage")))
    return ComparableUniverse(str(data.get("assignment_id")), str(data.get("canonical_assignment_id")), str(data.get("created_at")), str(data.get("version")), _map(data.get("subject")), records, assessments, conflicts, coverage, _map_list(data.get("review_queue", [])), _map(data.get("counts")), _string_list(data.get("limitations")), _map(data.get("provenance")))


def record_from_dict(data: JsonMap) -> ComparableRecord:
    fields = {field.name for field in ComparableRecord.__dataclass_fields__.values()}  # type: ignore[attr-defined]
    return ComparableRecord(**{key: data.get(key) for key in fields})


def snapshot_id(data: JsonMap) -> str:
    return _stable_id("comparable_snapshot", [json.dumps(data.get("counts", {}), sort_keys=True), json.dumps(data.get("comparables", []), sort_keys=True)])


def _preferred_source(items: list[ComparableRecord], config: JsonMap) -> str:
    priority = [str(item) for item in _map(config).get("source_priority", [])]
    for source_type in priority:
        for item in items:
            if item.source_type == source_type:
                return source_type
    return items[0].source_type if items else ""


def _field_available(row: JsonMap, field: str) -> bool:
    aliases = {"property_address": ["property_address", "address"], "gross_living_area": ["gross_living_area", "gla"], "distance_from_subject": ["distance_from_subject", "distance_miles"]}
    keys = aliases.get(field, [field])
    return any(_str(row.get(key)) for key in keys)


def _comparable_template(assignment_id: str) -> str:
    return f"""assignment_id: {assignment_id}
subject:
  address:
  property_type:
  gross_living_area:
  lot_size:
  condition:
  quality:
  bedrooms:
  bathrooms:
  sale_or_effective_date:
comparables: []
"""


def _file_checksum(path: Path) -> str:
    return sha256(path.read_bytes()).hexdigest()


def _stable_id(prefix: str, parts: list[str]) -> str:
    return f"{prefix}_{sha256('|'.join(str(part) for part in parts).encode('utf-8')).hexdigest()[:16]}"


def _slug(value: str) -> str:
    text = normalize_address(value)
    text = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return text or "unknown"


def _now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def _map(value: Any) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _map_list(value: Any) -> list[JsonMap]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value]
    if value in {None, ""}:
        return []
    return [str(value)]


def _str(value: Any) -> str:
    return "" if value is None else str(value).strip()
