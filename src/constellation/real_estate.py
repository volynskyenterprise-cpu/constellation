from __future__ import annotations

import json
import html
import re
from dataclasses import dataclass
from datetime import date, datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from . import __version__
from .io import read_json, write_json
from .models import JsonMap
from .simple_yaml import load_yaml


class RealEstateError(RuntimeError):
    pass


VALID_STATUSES = {"intake", "active", "waiting_for_information", "analysis", "review", "completed", "archived"}
VALID_ASSIGNMENT_TYPES = {"appraisal", "appraisal_review", "consultation", "litigation_support", "retrospective_appraisal", "prospective_appraisal", "market_study", "other"}
VALID_PROPERTY_TYPES = {"single_family_residential", "condominium", "cooperative", "two_to_four_unit", "land", "commercial", "industrial", "mixed_use", "hospitality", "other"}
PROPERTY_TYPE_ALIASES = {
    "sfr": "single_family_residential",
    "single_family": "single_family_residential",
    "single_family_residential": "single_family_residential",
    "detached_single_family": "single_family_residential",
    "detached_single_family_residential": "single_family_residential",
    "condo": "condominium",
}
ADDRESS_SUFFIX_ALIASES = {
    "ave": "avenue",
    "avenue": "avenue",
    "st": "street",
    "street": "street",
    "rd": "road",
    "road": "road",
    "dr": "drive",
    "drive": "drive",
    "blvd": "boulevard",
    "boulevard": "boulevard",
    "ln": "lane",
    "lane": "lane",
    "ct": "court",
    "court": "court",
    "cir": "circle",
    "circle": "circle",
    "pl": "place",
    "place": "place",
    "ter": "terrace",
    "terrace": "terrace",
    "pkwy": "parkway",
    "parkway": "parkway",
    "hwy": "highway",
    "highway": "highway",
}
ADDRESS_DIRECTIONAL_ALIASES = {
    "n": "north",
    "north": "north",
    "s": "south",
    "south": "south",
    "e": "east",
    "east": "east",
    "w": "west",
    "west": "west",
    "ne": "northeast",
    "northeast": "northeast",
    "nw": "northwest",
    "northwest": "northwest",
    "se": "southeast",
    "southeast": "southeast",
    "sw": "southwest",
    "southwest": "southwest",
}
ADDRESS_UNIT_ALIASES = {"unit": "unit", "apt": "unit", "apartment": "unit", "suite": "unit", "ste": "unit"}
ADDRESS_STATE_ALIASES = {"ca": "ca", "california": "ca"}
ADDRESS_COMPONENTS = [
    "street_number",
    "predirectional",
    "street_name",
    "street_suffix",
    "postdirectional",
    "unit_type",
    "unit_identifier",
    "city",
    "state",
    "postal_code",
]
VALID_VERIFICATION = {"verified", "client_provided", "source_reported", "unverified", "conflicting", "unavailable"}
VALID_CONFIDENCE = {"high", "medium", "low", "unknown"}
SUPPORTED_SOURCE_EXTENSIONS = {".md", ".txt", ".yaml", ".yml", ".json", ".csv", ".pdf", ".jpg", ".jpeg", ".png", ".heic", ".tif", ".tiff"}


@dataclass(frozen=True)
class RealEstateSubject:
    address: str
    city: str
    state: str
    postal_code: str
    county: str
    assessor_parcel_number: str

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class RealEstateAssignmentScope:
    inspection_type: str
    valuation_premise: str
    ownership_interest: str

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class RealEstateAssignment:
    assignment_id: str
    status: str
    assignment_type: str
    property_type: str
    property_type_raw: str
    property_type_normalization_status: str
    intended_use: str
    client_name: str
    effective_date: str
    due_date: str
    report_type: str
    subject: RealEstateSubject
    scope: RealEstateAssignmentScope
    source_paths: list[str]
    notes: list[str]
    facts: list[JsonMap]
    created_at: str
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return {
            "assignment_id": self.assignment_id,
            "status": self.status,
            "assignment_type": self.assignment_type,
            "property_type": self.property_type,
            "property_type_raw": self.property_type_raw,
            "property_type_normalization_status": self.property_type_normalization_status,
            "intended_use": self.intended_use,
            "client_name": self.client_name,
            "effective_date": self.effective_date,
            "due_date": self.due_date,
            "report_type": self.report_type,
            "subject": self.subject.to_dict(),
            "scope": self.scope.to_dict(),
            "source_paths": self.source_paths,
            "notes": self.notes,
            "facts": self.facts,
            "created_at": self.created_at,
            "provenance": self.provenance,
        }


@dataclass(frozen=True)
class RealEstateSourceRecord:
    source_id: str
    assignment_id: str
    source_path: str
    filename: str
    extension: str
    size_bytes: int
    modified_at: str
    source_category: str
    checksum: str
    status: str
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class RealEstateFact:
    fact_id: str
    assignment_id: str
    fact_type: str
    field_name: str
    value: str
    verification_status: str
    source_ids: list[str]
    confidence: str
    conflict_ids: list[str]
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class RealEstateFactConflict:
    conflict_id: str
    assignment_id: str
    field_name: str
    values: list[str]
    source_ids: list[str]
    severity: str
    status: str
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class RealEstateMissingItem:
    missing_item_id: str
    field_name: str
    description: str
    severity: str
    required_for: str
    resolution_guidance: str
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class RealEstateAssignmentRisk:
    risk_id: str
    assignment_id: str
    risk_type: str
    severity: str
    description: str
    related_field: str
    source_ids: list[str]
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class RealEstateAssignmentTimelineEvent:
    event_id: str
    assignment_id: str
    event_type: str
    occurred_at: str
    title: str
    description: str
    source_ids: list[str]
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class RealEstateAssignmentDelta:
    new_sources: list[str]
    removed_sources: list[str]
    changed_sources: list[str]
    new_facts: list[str]
    changed_facts: list[str]
    new_missing_items: list[str]
    resolved_missing_items: list[str]
    new_conflicts: list[str]
    resolved_conflicts: list[str]
    new_risks: list[str]
    resolved_risks: list[str]
    status_changes: list[JsonMap]

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class RealEstateAssignmentSnapshot:
    snapshot_id: str
    created_at: str
    version: str
    assignment: RealEstateAssignment
    sources: list[RealEstateSourceRecord]
    facts: list[RealEstateFact]
    conflicts: list[RealEstateFactConflict]
    missing_items: list[RealEstateMissingItem]
    risks: list[RealEstateAssignmentRisk]
    timeline: list[RealEstateAssignmentTimelineEvent]
    delta: RealEstateAssignmentDelta
    limitations: list[str]
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return {
            "snapshot_id": self.snapshot_id,
            "created_at": self.created_at,
            "version": self.version,
            "assignment": self.assignment.to_dict(),
            "assignment_id": self.assignment.assignment_id,
            "status": self.assignment.status,
            "property_type": self.assignment.property_type,
            "property_type_raw": self.assignment.property_type_raw,
            "property_type_normalization_status": self.assignment.property_type_normalization_status,
            "subject_address": _subject_address(self.assignment.subject),
            "due_date": self.assignment.due_date,
            "sources": [item.to_dict() for item in self.sources],
            "source_count": len(self.sources),
            "facts": [item.to_dict() for item in self.facts],
            "fact_count": len(self.facts),
            "verified_fact_count": sum(1 for item in self.facts if item.verification_status == "verified"),
            "conflicts": [item.to_dict() for item in self.conflicts],
            "conflict_count": len(self.conflicts),
            "missing_items": [item.to_dict() for item in self.missing_items],
            "missing_item_count": len(self.missing_items),
            "risks": [item.to_dict() for item in self.risks],
            "risk_count": len(self.risks),
            "timeline": [item.to_dict() for item in self.timeline],
            "delta": self.delta.to_dict(),
            "limitations": self.limitations,
            "provenance": self.provenance,
        }


class RealEstateAssignmentEngine:
    def __init__(self, root: Path) -> None:
        self.root = root

    def build(self, assignment_id: str, history: list[JsonMap]) -> RealEstateAssignmentSnapshot:
        assignment_path = assignment_directory(self.root, assignment_id) / "assignment.yaml"
        if not assignment_path.exists():
            raise RealEstateError(f"No assignment.yaml found for assignment: {assignment_id}")
        assignment = _read_assignment(assignment_path)
        sources = _source_records(self.root, assignment)
        facts = _facts(assignment, sources)
        conflicts = _conflicts(assignment.assignment_id, facts)
        facts = _facts_with_conflicts(facts, conflicts)
        missing = _missing_items(assignment, sources)
        risks = _risks(assignment, facts, conflicts, missing, sources)
        timeline = _timeline(assignment, sources)
        snapshot_id = _snapshot_id(assignment, sources, facts, conflicts, missing, risks)
        delta = _delta(history[-1] if history else {}, snapshot_id, assignment, sources, facts, conflicts, missing, risks)
        return RealEstateAssignmentSnapshot(
            snapshot_id=snapshot_id,
            created_at=_now_iso(),
            version=__version__,
            assignment=assignment,
            sources=sources,
            facts=facts,
            conflicts=conflicts,
            missing_items=missing,
            risks=risks,
            timeline=timeline,
            delta=delta,
            limitations=[
                "Assignment Intelligence organizes local assignment facts and source metadata only.",
                "It does not generate value opinions, comparable selections, adjustments, USPAP opinions, or appraisal report conclusions.",
                "Property facts are not verified unless directly supported by explicit structured source metadata or file existence.",
            ],
            provenance={"assignment_path": str(assignment_path), "assignment_directory": str(assignment_path.parent)},
        )


class RealEstateAssignmentStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def assignment_root(self) -> Path:
        config = _read_assignment_config(self.root)
        return self.root / str(config.get("default_root") or "real-estate/assignments")

    def list_assignment_ids(self, *, include_migrated_aliases: bool = False) -> list[str]:
        root = self.assignment_root()
        if not root.exists():
            return []
        ids = []
        for path in root.iterdir():
            if not path.is_dir() or not (path / "assignment.yaml").exists():
                continue
            if not include_migrated_aliases and is_migrated_alias_directory(path):
                continue
            ids.append(path.name)
        return sorted(ids)

    def output_dir(self, assignment_id: str) -> Path:
        return self.root / "outputs" / "real-estate" / "assignments" / assignment_id

    def build(self, assignment_id: str) -> RealEstateAssignmentSnapshot:
        snapshot = RealEstateAssignmentEngine(self.root).build(assignment_id, self.history(assignment_id))
        self.save(snapshot)
        return snapshot

    def load(self, assignment_id: str) -> JsonMap:
        path = self.output_dir(assignment_id) / "assignment.json"
        if not path.exists():
            raise RealEstateError(f"No Assignment Intelligence output found for assignment: {assignment_id}")
        return read_json(path)

    def history(self, assignment_id: str) -> list[JsonMap]:
        path = self.output_dir(assignment_id) / "assignment-history.json"
        if not path.exists():
            return []
        return _map_list(read_json(path).get("snapshots", []))

    def save(self, snapshot: RealEstateAssignmentSnapshot) -> None:
        directory = self.output_dir(snapshot.assignment.assignment_id)
        data = snapshot.to_dict()
        write_json(directory / "assignment.json", data)
        write_json(directory / "source-manifest.json", {"sources": data["sources"]})
        write_json(directory / "evidence-index.json", {"facts": data["facts"], "sources": data["sources"], "conflicts": data["conflicts"]})
        write_json(directory / "missing-information.json", {"missing_items": data["missing_items"]})
        write_json(directory / "assignment-risks.json", {"risks": data["risks"]})
        write_json(directory / "assignment-timeline.json", {"timeline": data["timeline"]})
        write_json(directory / "assignment-delta.json", data["delta"])
        history = self.history(snapshot.assignment.assignment_id)
        if not history or history[-1].get("snapshot_id") != snapshot.snapshot_id:
            history.append(data)
        write_json(directory / "assignment-history.json", {"snapshots": history})
        directory.mkdir(parents=True, exist_ok=True)
        (directory / "assignment-brief.md").write_text(
            render_assignment_brief(snapshot)
            + _render_consolidation_section(self.root, snapshot.assignment.assignment_id)
            + _render_comparable_section(self.root, snapshot.assignment.assignment_id),
            encoding="utf-8",
        )
        (directory / "source-manifest.md").write_text(render_source_manifest(snapshot), encoding="utf-8")
        (directory / "evidence-index.md").write_text(render_evidence_index(snapshot), encoding="utf-8")
        (directory / "missing-information.md").write_text(render_missing_information(snapshot), encoding="utf-8")
        (directory / "assignment-risks.md").write_text(render_assignment_risks(snapshot), encoding="utf-8")
        (directory / "assignment-timeline.md").write_text(render_assignment_timeline(snapshot), encoding="utf-8")

    def create_template(self, assignment_id: str) -> Path:
        directory = assignment_directory(self.root, assignment_id)
        assignment_path = directory / "assignment.yaml"
        if assignment_path.exists():
            raise RealEstateError(f"Assignment template already exists: {assignment_path}")
        for child in ["sources", "notes", "evidence"]:
            (directory / child).mkdir(parents=True, exist_ok=True)
        assignment_path.write_text(_assignment_template(assignment_id), encoding="utf-8")
        return assignment_path

    def summary(self) -> JsonMap:
        assignments = []
        for assignment_id in self.list_assignment_ids():
            try:
                if not (self.output_dir(assignment_id) / "assignment.json").exists():
                    self.build(assignment_id)
                assignments.append(self.load(assignment_id))
            except RealEstateError:
                continue
        active = [item for item in assignments if item.get("status") == "active"]
        waiting = [item for item in assignments if item.get("status") == "waiting_for_information"]
        review = [item for item in assignments if item.get("status") == "review"]
        overdue = [item for item in assignments if _is_overdue(str(item.get("due_date", "")), str(item.get("status", "")))]
        high_priority = sorted(assignments, key=_assignment_summary_sort_key)[:5]
        return {
            "real_estate_assignment_intelligence_available": bool(assignments),
            "active_assignment_count": len(active),
            "waiting_assignment_count": len(waiting),
            "review_assignment_count": len(review),
            "overdue_assignment_count": len(overdue),
            "total_assignment_risk_count": sum(_int(item.get("risk_count")) for item in assignments),
            "total_missing_item_count": sum(_int(item.get("missing_item_count")) for item in assignments),
            "highest_priority_assignments": [{"assignment_id": item.get("assignment_id"), "status": item.get("status"), "risk_count": item.get("risk_count", 0), "missing_item_count": item.get("missing_item_count", 0), "due_date": item.get("due_date")} for item in high_priority],
            "latest_assignment_brief_paths": [str(Path("outputs/real-estate/assignments") / str(item.get("assignment_id")) / "assignment-brief.md") for item in high_priority],
        }


def assignment_directory(root: Path, assignment_id: str) -> Path:
    config = _read_assignment_config(root)
    return root / str(config.get("default_root") or "real-estate/assignments") / assignment_id


def load_alias_migration_marker(directory: Path) -> JsonMap:
    marker = directory / "canonical-migration.json"
    if not marker.exists():
        return {}
    try:
        data = read_json(marker)
    except Exception:
        return {}
    if str(data.get("status") or "") != "migrated_alias_directory":
        return {}
    return data


def is_migrated_alias_directory(directory: Path) -> bool:
    return bool(load_alias_migration_marker(directory))


def resolve_assignment_directory_role(directory: Path) -> str:
    if is_migrated_alias_directory(directory):
        return "migrated_alias"
    if directory.is_dir() and (directory / "assignment.yaml").exists():
        return "canonical_assignment"
    return "not_assignment"


def render_assignment_brief(snapshot: RealEstateAssignmentSnapshot) -> str:
    a = snapshot.assignment
    return "\n".join(
        [
            "# Real Estate Assignment Brief",
            "",
            "## Assignment Header",
            "",
            f"- Assignment ID: `{a.assignment_id}`",
            f"- Status: `{a.status}`",
            f"- Assignment type: `{a.assignment_type}`",
            f"- Property type: `{a.property_type}`",
            f"- Due date: `{a.due_date}`",
            "",
            "## Subject Property",
            "",
            *_summary_lines(a.subject.to_dict()),
            "## Assignment Scope",
            "",
            *_summary_lines(a.scope.to_dict()),
            "## Assignment Status",
            "",
            f"- Sources: {len(snapshot.sources)}",
            f"- Facts: {len(snapshot.facts)}",
            f"- Missing items: {len(snapshot.missing_items)}",
            f"- Conflicts: {len(snapshot.conflicts)}",
            f"- Risks: {len(snapshot.risks)}",
            "",
            "## Verified and Reported Facts",
            "",
            *_fact_lines(snapshot.facts),
            "## Available Sources",
            "",
            *_source_lines(snapshot.sources),
            "## Missing Information",
            "",
            *_missing_lines(snapshot.missing_items),
            "## Conflicts",
            "",
            *_conflict_lines(snapshot.conflicts),
            "## Assignment Risks",
            "",
            *_risk_lines(snapshot.risks),
            "## Timeline",
            "",
            *_timeline_lines(snapshot.timeline),
            "## Recommended Next Review Steps",
            "",
            *_review_steps(snapshot),
            "## Limitations",
            "",
            *_bullet(snapshot.limitations),
            "## Provenance",
            "",
            *_summary_lines(snapshot.provenance),
        ]
    )


def _render_consolidation_section(root: Path, assignment_id: str) -> str:
    path = root / "outputs" / "real-estate" / "consolidation" / "assignment-clusters.json"
    if not path.exists():
        return ""
    try:
        data = read_json(path)
    except Exception:
        return ""
    for cluster in _map_list(data.get("clusters", [])):
        if cluster.get("canonical_assignment_id") != assignment_id:
            continue
        lines = [
            "",
            "## Assignment Consolidation",
            "",
            f"- Artifacts: {cluster.get('artifact_count', 0)}",
            f"- Knowledge pack available: {cluster.get('knowledge_pack_available', False)}",
            f"- Reviewer notes available: {cluster.get('reviewer_notes_available', False)}",
            f"- Relationships: {len(cluster.get('relationships', [])) if isinstance(cluster.get('relationships'), list) else 0}",
            f"- Conflicts: {len(_map_list(cluster.get('conflicts', [])))}",
            "",
            "### Artifacts",
            "",
        ]
        for artifact in _map_list(cluster.get("artifacts", [])):
            lines.append(f"- `{artifact.get('artifact_type')}` source=`{artifact.get('source_path')}`")
        lines.extend(["", "### Consolidation Conflicts", ""])
        conflicts = _map_list(cluster.get("conflicts", []))
        if conflicts:
            lines.extend(f"- `{item.get('field')}` values=`{item.get('values')}`" for item in conflicts)
        else:
            lines.append("- None")
        lines.append("")
        return "\n".join(lines)
    return ""


def _render_comparable_section(root: Path, assignment_id: str) -> str:
    base = root / "outputs" / "real-estate" / "assignments" / assignment_id / "comparables"
    paths = []
    legacy = base / "comparable-universe.json"
    if legacy.exists():
        paths.append(legacy)
    paths.extend(sorted((base / "scenarios").glob("*/comparable-universe.json")) if (base / "scenarios").exists() else [])
    if not paths:
        return "\n\n## Comparable Intelligence\n\n- Comparable Intelligence: unavailable\n- Report path: \n"
    lines = ["", "## Comparable Intelligence", ""]
    for path in paths:
        try:
            data = read_json(path)
        except Exception:
            continue
        counts = _map(data.get("counts"))
        coverage = _map(_map(data.get("coverage")).get("bracketing"))
        scenario = str(data.get("valuation_scenario") or "default")
        label = str(data.get("scenario_label") or {"as_is": "As-Is", "arv": "ARV", "default": "Legacy Default"}.get(scenario, scenario))
        lines.extend(
            [
                f"### {label}",
                "",
                f"- Scenario: `{scenario}`",
                f"- Records: `{counts.get('comparable_count', 0)}`",
                f"- Primary: `{counts.get('primary_candidate', 0)}`",
                f"- Secondary: `{counts.get('secondary_candidate', 0)}`",
                f"- Contextual: `{counts.get('contextual_candidate', 0)}`",
                f"- Review required: `{counts.get('review_required', 0)}`",
                f"- GLA coverage: `{_map(coverage.get('gross_living_area')).get('bracketing', 'unavailable')}`",
                f"- Lot-size coverage: `{_map(coverage.get('lot_size')).get('bracketing', 'unavailable')}`",
                f"- Open conflicts: `{counts.get('open_conflict_count', 0)}`",
                f"- Report path: `{path.with_suffix('.md')}`",
                "",
            ]
        )
    lines.append("- Appraiser selection, adjustment development, reconciliation, and value conclusion remain outside automation.")
    lines.append("")
    return "\n".join(lines)


def render_source_manifest(snapshot: RealEstateAssignmentSnapshot) -> str:
    return "\n".join(["# Source Manifest", "", *_source_lines(snapshot.sources)])


def render_evidence_index(snapshot: RealEstateAssignmentSnapshot) -> str:
    return "\n".join(["# Evidence Index", "", *_fact_lines(snapshot.facts), "## Conflicts", "", *_conflict_lines(snapshot.conflicts)])


def render_missing_information(snapshot: RealEstateAssignmentSnapshot) -> str:
    return "\n".join(["# Missing Information", "", *_missing_lines(snapshot.missing_items)])


def render_assignment_risks(snapshot: RealEstateAssignmentSnapshot) -> str:
    return "\n".join(["# Assignment Risks", "", *_risk_lines(snapshot.risks)])


def render_assignment_timeline(snapshot: RealEstateAssignmentSnapshot) -> str:
    return "\n".join(["# Assignment Timeline", "", *_timeline_lines(snapshot.timeline)])


def _read_assignment(path: Path) -> RealEstateAssignment:
    data = _map(load_yaml(path).get("assignment"))
    if not data:
        raise RealEstateError(f"assignment.yaml must contain an assignment mapping: {path}")
    subject = _map(data.get("subject"))
    scope = _map(data.get("scope"))
    assignment_id = str(data.get("assignment_id") or path.parent.name)
    status = _valid_or_default(str(data.get("status") or "intake"), VALID_STATUSES, "intake")
    assignment_type = _valid_or_default(str(data.get("assignment_type") or "other"), VALID_ASSIGNMENT_TYPES, "other")
    property_type_raw = str(data.get("property_type") or "")
    property_type = normalize_property_type(property_type_raw)
    property_type_status = property_type_normalization_status(property_type_raw)
    return RealEstateAssignment(
        assignment_id=assignment_id,
        status=status,
        assignment_type=assignment_type,
        property_type=property_type,
        property_type_raw=property_type_raw,
        property_type_normalization_status=property_type_status,
        intended_use=str(data.get("intended_use") or ""),
        client_name=str(data.get("client_name") or ""),
        effective_date=str(data.get("effective_date") or ""),
        due_date=str(data.get("due_date") or ""),
        report_type=str(data.get("report_type") or ""),
        subject=RealEstateSubject(
            address=str(subject.get("address") or ""),
            city=str(subject.get("city") or ""),
            state=str(subject.get("state") or ""),
            postal_code=str(subject.get("postal_code") or ""),
            county=str(subject.get("county") or ""),
            assessor_parcel_number=str(subject.get("assessor_parcel_number") or ""),
        ),
        scope=RealEstateAssignmentScope(
            inspection_type=str(scope.get("inspection_type") or ""),
            valuation_premise=str(scope.get("valuation_premise") or ""),
            ownership_interest=str(scope.get("ownership_interest") or ""),
        ),
        source_paths=_string_list(data.get("source_paths", [])) or ["sources/"],
        notes=_string_list(data.get("notes", [])),
        facts=_map_list(data.get("facts", [])),
        created_at=str(data.get("created_at") or ""),
        provenance={"source_path": str(path)},
    )


def _source_records(root: Path, assignment: RealEstateAssignment) -> list[RealEstateSourceRecord]:
    base = assignment_directory(root, assignment.assignment_id)
    files: list[Path] = []
    for source_path in assignment.source_paths + ["notes", "evidence"]:
        candidate = Path(source_path)
        path = candidate if candidate.is_absolute() else base / source_path
        if path.is_file():
            files.append(path)
        elif path.exists():
            files.extend(item for item in path.rglob("*") if item.is_file() and item.suffix.lower() in SUPPORTED_SOURCE_EXTENSIONS)
    records = []
    seen = set()
    for path in sorted(files, key=lambda item: _source_sort_path(item, base)):
        try:
            rel = str(path.relative_to(base))
        except ValueError:
            rel = str(path)
        if rel in seen:
            continue
        seen.add(rel)
        stat = path.stat()
        checksum = _file_checksum(path)
        records.append(
            RealEstateSourceRecord(
                source_id=f"source_{_digest(assignment.assignment_id + rel)}",
                assignment_id=assignment.assignment_id,
                source_path=rel,
                filename=path.name,
                extension=path.suffix.lower(),
                size_bytes=stat.st_size,
                modified_at=datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds"),
                source_category=_source_category(path.name),
                checksum=checksum,
                status="available",
                provenance={"metadata_only": True, "content_read_for_checksum": True},
            )
        )
    return sorted(records, key=lambda item: (item.source_category, item.filename.lower(), item.source_id))


def _facts(assignment: RealEstateAssignment, sources: list[RealEstateSourceRecord]) -> list[RealEstateFact]:
    facts: list[RealEstateFact] = []
    source_ids_by_path = {item.source_path.replace("\\", "/"): item.source_id for item in sources}
    fields = {
        "assignment_id": assignment.assignment_id,
        "assignment_type": assignment.assignment_type,
        "intended_use": assignment.intended_use,
        "client_name": assignment.client_name,
        "effective_date": assignment.effective_date,
        "due_date": assignment.due_date,
        "report_type": assignment.report_type,
        "subject.address": assignment.subject.address,
        "subject.city": assignment.subject.city,
        "subject.state": assignment.subject.state,
        "subject.postal_code": assignment.subject.postal_code,
        "subject.county": assignment.subject.county,
        "subject.assessor_parcel_number": assignment.subject.assessor_parcel_number,
        "scope.inspection_type": assignment.scope.inspection_type,
        "scope.valuation_premise": assignment.scope.valuation_premise,
        "scope.ownership_interest": assignment.scope.ownership_interest,
    }
    for field, value in fields.items():
        if field in {"assignment_type", "report_type"} and str(value).strip().lower() == "other":
            continue
        if value:
            facts.append(_fact(assignment.assignment_id, "assignment_yaml", field, value, "client_provided", [], "medium", {"source": "assignment.yaml"}))
    if assignment.property_type_raw.strip():
        facts.append(
            _fact(
                assignment.assignment_id,
                "assignment_yaml",
                "property_type",
                assignment.property_type_raw,
                "unverified" if assignment.property_type_normalization_status == "review_required" else "client_provided",
                [],
                "low" if assignment.property_type_normalization_status == "review_required" else "medium",
                {
                    "source": "assignment.yaml",
                    "raw_value": assignment.property_type_raw,
                    "normalized_value": assignment.property_type,
                    "normalization_status": assignment.property_type_normalization_status,
                },
            )
        )
    for source in sources:
        facts.append(_fact(assignment.assignment_id, "file_metadata", f"source.{source.source_id}.exists", "true", "verified", [source.source_id], "high", {"source_path": source.source_path}))
        facts.append(_fact(assignment.assignment_id, "file_metadata", f"source.{source.source_id}.checksum", source.checksum, "verified", [source.source_id], "high", {"source_path": source.source_path}))
    for item in assignment.facts:
        field = str(item.get("field_name") or "")
        if not field:
            continue
        if not _has_explicit_fact_value(item):
            continue
        status = _valid_or_default(str(item.get("verification_status") or "client_provided"), VALID_VERIFICATION, "client_provided")
        confidence = _valid_or_default(str(item.get("confidence") or ("high" if status == "verified" else "medium")), VALID_CONFIDENCE, "unknown")
        linked = [source_ids_by_path.get(path.replace("\\", "/"), path) for path in _string_list(item.get("source_paths", []))]
        value = _normalize_fact_value(item.get("value"))
        facts.append(_fact(assignment.assignment_id, "structured_fact", field, value, status, sorted(set(linked)), confidence, {"notes": item.get("notes", ""), "unit": item.get("unit")}))
    return sorted(facts, key=lambda item: (item.field_name, item.fact_id))


def _fact(assignment_id: str, fact_type: str, field_name: str, value: str, verification_status: str, source_ids: list[str], confidence: str, provenance: JsonMap) -> RealEstateFact:
    return RealEstateFact(
        fact_id=f"fact_{_digest('|'.join([assignment_id, fact_type, field_name, value, ','.join(source_ids)]))}",
        assignment_id=assignment_id,
        fact_type=fact_type,
        field_name=field_name,
        value=str(value),
        verification_status=verification_status,
        source_ids=source_ids,
        confidence=confidence,
        conflict_ids=[],
        provenance=provenance,
    )


def _conflicts(assignment_id: str, facts: list[RealEstateFact]) -> list[RealEstateFactConflict]:
    by_field: dict[str, list[RealEstateFact]] = {}
    for fact in facts:
        if fact.value:
            by_field.setdefault(fact.field_name, []).append(fact)
    conflicts = []
    for field, items in by_field.items():
        by_normalized: dict[str, set[str]] = {}
        for item in items:
            by_normalized.setdefault(_conflict_compare_value(field, item.value), set()).add(item.value)
        by_normalized = {key: values for key, values in by_normalized.items() if key}
        if len(by_normalized) <= 1:
            continue
        values = sorted({value for values in by_normalized.values() for value in values})
        source_ids = sorted({source for item in items for source in item.source_ids})
        conflicts.append(
            RealEstateFactConflict(
                conflict_id=f"conflict_{_digest(assignment_id + field + '|'.join(values))}",
                assignment_id=assignment_id,
                field_name=field,
                values=values,
                source_ids=source_ids,
                severity=_conflict_severity(field),
                status="open",
                provenance={"rule": "normalized_structured_field_value_conflict", "normalized_values": sorted(by_normalized)},
            )
        )
    return sorted(conflicts, key=lambda item: (_severity_rank(item.severity), item.field_name, item.conflict_id))


def _facts_with_conflicts(facts: list[RealEstateFact], conflicts: list[RealEstateFactConflict]) -> list[RealEstateFact]:
    by_field = {conflict.field_name: conflict.conflict_id for conflict in conflicts}
    result = []
    for fact in facts:
        conflict_id = by_field.get(fact.field_name)
        if conflict_id:
            result.append(RealEstateFact(fact.fact_id, fact.assignment_id, fact.fact_type, fact.field_name, fact.value, "conflicting", fact.source_ids, fact.confidence, [conflict_id], fact.provenance))
        else:
            result.append(fact)
    return result


def _missing_items(assignment: RealEstateAssignment, sources: list[RealEstateSourceRecord]) -> list[RealEstateMissingItem]:
    required = [
        ("assignment_id", assignment.assignment_id, "critical", "assignment setup", "Add assignment_id to assignment.yaml."),
        ("subject.address", assignment.subject.address, "critical", "subject identification", "Confirm subject address."),
        ("subject.city", assignment.subject.city, "high", "subject identification", "Confirm subject city."),
        ("subject.state", assignment.subject.state, "high", "subject identification", "Confirm subject state."),
        ("subject.postal_code", assignment.subject.postal_code, "medium", "subject identification", "Confirm postal code."),
        ("client_name", assignment.client_name, "high", "assignment terms", "Confirm client name."),
        ("intended_use", assignment.intended_use, "high", "assignment terms", "Confirm intended use."),
        ("effective_date", assignment.effective_date, "high", "valuation date", "Confirm effective date."),
        ("due_date", assignment.due_date, "medium", "timeline", "Confirm assignment due date."),
        ("assignment_type", assignment.assignment_type if assignment.assignment_type != "other" else "", "high", "scope", "Confirm assignment type."),
        ("report_type", assignment.report_type, "medium", "report setup", "Confirm report type."),
        ("scope.inspection_type", assignment.scope.inspection_type, "high", "scope", "Confirm inspection scope."),
        ("scope.ownership_interest", assignment.scope.ownership_interest, "high", "scope", "Confirm ownership interest."),
        ("subject.assessor_parcel_number", assignment.subject.assessor_parcel_number, "medium", "public records", "Confirm APN if applicable."),
        ("source_documents", str(bool(sources)), "high", "evidence", "Add source documents under the assignment sources directory."),
    ]
    items = []
    if assignment.property_type_normalization_status in {"unavailable", "review_required"}:
        review_required = assignment.property_type_normalization_status == "review_required"
        items.append(
            RealEstateMissingItem(
                missing_item_id=f"missing_{_digest(assignment.assignment_id + 'property_type')}",
                field_name="property_type",
                description=(
                    f"Unrecognized property type requires review: {assignment.property_type_raw}."
                    if review_required
                    else "Missing required assignment information: property_type."
                ),
                severity="high",
                required_for="scope",
                resolution_guidance="Map the explicit source classification to a supported property type through governed review." if review_required else "Confirm property type.",
                provenance={
                    "rule": "unrecognized_property_type" if review_required else "required_assignment_field",
                    "raw_value": assignment.property_type_raw,
                    "normalized_value": assignment.property_type,
                    "normalization_status": assignment.property_type_normalization_status,
                    "source": "assignment.yaml",
                },
            )
        )
    for field, value, severity, required_for, guidance in required:
        if not value:
            items.append(
                RealEstateMissingItem(
                    missing_item_id=f"missing_{_digest(assignment.assignment_id + field)}",
                    field_name=field,
                    description=f"Missing required assignment information: {field}.",
                    severity=severity,
                    required_for=required_for,
                    resolution_guidance=guidance,
                    provenance={"rule": "required_assignment_field"},
                )
            )
    return sorted(items, key=lambda item: (_missing_rank(item.severity), item.field_name))


def _risks(assignment: RealEstateAssignment, facts: list[RealEstateFact], conflicts: list[RealEstateFactConflict], missing: list[RealEstateMissingItem], sources: list[RealEstateSourceRecord]) -> list[RealEstateAssignmentRisk]:
    risks = []
    for item in missing:
        risks.append(_risk(assignment.assignment_id, "missing_required_information", _risk_severity_from_missing(item.severity), item.description, item.field_name, [], {"missing_item_id": item.missing_item_id}))
    for conflict in conflicts:
        risks.append(_risk(assignment.assignment_id, "conflicting_property_fact", conflict.severity, f"Conflicting structured values for {conflict.field_name}.", conflict.field_name, conflict.source_ids, {"conflict_id": conflict.conflict_id}))
    if _is_overdue(assignment.due_date, assignment.status):
        risks.append(_risk(assignment.assignment_id, "timeline_risk", "high", "Due date has passed and assignment is not completed.", "due_date", [], {"due_date": assignment.due_date}))
    if not assignment.scope.inspection_type:
        risks.append(_risk(assignment.assignment_id, "scope_ambiguity", "high", "Inspection type is missing.", "scope.inspection_type", [], {"rule": "missing_inspection_type"}))
    for fact in facts:
        if fact.fact_type == "structured_fact" and fact.verification_status in {"client_provided", "unverified"} and not fact.source_ids:
            risks.append(_risk(assignment.assignment_id, "unsupported_fact", "medium", f"Structured fact has no linked source: {fact.field_name}.", fact.field_name, [], {"fact_id": fact.fact_id}))
    if not sources:
        risks.append(_risk(assignment.assignment_id, "missing_source_document", "high", "No source documents were found for this assignment.", "source_documents", [], {"rule": "empty_source_manifest"}))
    by_id = {risk.risk_id: risk for risk in risks}
    return sorted(by_id.values(), key=lambda item: (_severity_rank(item.severity), item.risk_type, item.risk_id))


def _risk(assignment_id: str, risk_type: str, severity: str, description: str, related_field: str, source_ids: list[str], provenance: JsonMap) -> RealEstateAssignmentRisk:
    return RealEstateAssignmentRisk(f"risk_{_digest('|'.join([assignment_id, risk_type, related_field, description]))}", assignment_id, risk_type, severity, description, related_field, source_ids, provenance)


def _timeline(assignment: RealEstateAssignment, sources: list[RealEstateSourceRecord]) -> list[RealEstateAssignmentTimelineEvent]:
    events = []
    if assignment.created_at:
        events.append(_event(assignment.assignment_id, "assignment_created", assignment.created_at, "Assignment created", "Created date from assignment.yaml.", [], {"source": "assignment.yaml"}))
    if assignment.effective_date:
        events.append(_event(assignment.assignment_id, "effective_date", assignment.effective_date, "Effective date", "Effective date from assignment.yaml.", [], {"source": "assignment.yaml"}))
    if assignment.due_date:
        events.append(_event(assignment.assignment_id, "due_date", assignment.due_date, "Due date", "Due date from assignment.yaml.", [], {"source": "assignment.yaml"}))
    for source in sources:
        events.append(_event(assignment.assignment_id, "source_modified", source.modified_at, f"Source modified: {source.filename}", "File metadata timestamp.", [source.source_id], {"source_path": source.source_path}))
    events.append(_event(assignment.assignment_id, "snapshot_created", _now_iso(), "Assignment snapshot created", "Assignment Intelligence snapshot generated.", [], {"source": "RealEstateAssignmentEngine"}))
    return sorted(events, key=lambda item: (item.occurred_at, item.event_type, item.event_id))


def _event(assignment_id: str, event_type: str, occurred_at: str, title: str, description: str, source_ids: list[str], provenance: JsonMap) -> RealEstateAssignmentTimelineEvent:
    source_fingerprint = ",".join(source_ids) + str(provenance.get("source_path", ""))
    return RealEstateAssignmentTimelineEvent(f"event_{_digest('|'.join([assignment_id, event_type, occurred_at, title, source_fingerprint]))}", assignment_id, event_type, occurred_at, title, description, source_ids, provenance)


def _delta(previous: JsonMap, snapshot_id: str, assignment: RealEstateAssignment, sources: list[RealEstateSourceRecord], facts: list[RealEstateFact], conflicts: list[RealEstateFactConflict], missing: list[RealEstateMissingItem], risks: list[RealEstateAssignmentRisk]) -> RealEstateAssignmentDelta:
    prev_sources = {str(item.get("source_id")): item for item in _map_list(previous.get("sources", []))}
    cur_sources = {item.source_id: item.to_dict() for item in sources}
    prev_facts = {str(item.get("fact_id")): item for item in _map_list(previous.get("facts", []))}
    cur_facts = {item.fact_id: item.to_dict() for item in facts}
    prev_missing = {str(item.get("missing_item_id")) for item in _map_list(previous.get("missing_items", []))}
    cur_missing = {item.missing_item_id for item in missing}
    prev_conflicts = {str(item.get("conflict_id")) for item in _map_list(previous.get("conflicts", []))}
    cur_conflicts = {item.conflict_id for item in conflicts}
    prev_risks = {str(item.get("risk_id")) for item in _map_list(previous.get("risks", []))}
    cur_risks = {item.risk_id for item in risks}
    status_changes = []
    if previous and previous.get("status") != assignment.status:
        status_changes.append({"from": previous.get("status"), "to": assignment.status})
    return RealEstateAssignmentDelta(
        new_sources=sorted(set(cur_sources) - set(prev_sources)),
        removed_sources=sorted(set(prev_sources) - set(cur_sources)),
        changed_sources=sorted(key for key in set(cur_sources) & set(prev_sources) if cur_sources[key].get("checksum") != prev_sources[key].get("checksum")),
        new_facts=sorted(set(cur_facts) - set(prev_facts)),
        changed_facts=sorted(key for key in set(cur_facts) & set(prev_facts) if cur_facts[key].get("value") != prev_facts[key].get("value") or cur_facts[key].get("verification_status") != prev_facts[key].get("verification_status")),
        new_missing_items=sorted(cur_missing - prev_missing),
        resolved_missing_items=sorted(prev_missing - cur_missing),
        new_conflicts=sorted(cur_conflicts - prev_conflicts),
        resolved_conflicts=sorted(prev_conflicts - cur_conflicts),
        new_risks=sorted(cur_risks - prev_risks),
        resolved_risks=sorted(prev_risks - cur_risks),
        status_changes=status_changes,
    )


def _snapshot_id(assignment: RealEstateAssignment, sources: list[RealEstateSourceRecord], facts: list[RealEstateFact], conflicts: list[RealEstateFactConflict], missing: list[RealEstateMissingItem], risks: list[RealEstateAssignmentRisk]) -> str:
    payload = "|".join(
        [
            assignment.assignment_id,
            assignment.status,
            assignment.property_type,
            assignment.due_date,
            ",".join(item.source_id + item.checksum for item in sources),
            ",".join(item.fact_id + item.value + item.verification_status for item in facts),
            ",".join(item.conflict_id for item in conflicts),
            ",".join(item.missing_item_id for item in missing),
            ",".join(item.risk_id for item in risks),
        ]
    )
    return f"real_estate_assignment_{_digest(payload)}"


def _read_assignment_config(root: Path) -> JsonMap:
    for path in [root / "config" / "real-estate-assignment.local.yaml", root / "config" / "real-estate-assignment.yaml", root / "config" / "real-estate-assignment.example.yaml"]:
        if path.exists():
            return _map(load_yaml(path).get("real_estate_assignment"))
    return {"default_root": "real-estate/assignments", "default_status": "active", "default_property_type": "residential"}


def _source_category(filename: str) -> str:
    name = filename.lower().replace("_", " ").replace("-", " ")
    rules = [
        ("purchase agreement", "contract"),
        ("contract", "contract"),
        ("permit", "permit"),
        ("floor plan", "floor_plan"),
        ("floorplan", "floor_plan"),
        ("sketch", "sketch"),
        ("reviewer", "reviewer_comment"),
        ("condition", "reviewer_comment"),
        ("prior appraisal", "prior_appraisal"),
        ("appraisal", "prior_appraisal"),
        ("mls", "comparable_export"),
        ("comparable", "comparable_export"),
        ("comp", "comparable_export"),
        ("title", "title"),
        ("escrow", "escrow"),
        ("client", "client_instruction"),
        ("engagement", "engagement_letter"),
        ("instruction", "client_instruction"),
        ("market study", "market_study"),
        ("photo", "photograph"),
        ("image", "photograph"),
        ("note", "note"),
        ("correspondence", "correspondence"),
    ]
    for needle, category in rules:
        if needle in name:
            return category
    return "unknown"


def _file_checksum(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _source_sort_path(path: Path, base: Path) -> str:
    try:
        return str(path.relative_to(base)).lower()
    except ValueError:
        return str(path).lower()


def _has_explicit_fact_value(item: JsonMap) -> bool:
    if "value" not in item:
        return False
    value = item.get("value")
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, bool):
        return True
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _normalize_fact_value(value: Any) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, (list, dict)):
        return json.dumps(value, sort_keys=True)
    return str(value)


def _assignment_template(assignment_id: str) -> str:
    return (
        "# Private local assignment data. Do not commit.\n"
        "assignment:\n"
        f"  assignment_id: {assignment_id}\n"
        "  status: intake\n"
        "  assignment_type: appraisal\n"
        "  property_type: single_family_residential\n"
        "  intended_use: \"\"\n"
        "  client_name: \"\"\n"
        "  effective_date: \"\"\n"
        "  due_date: \"\"\n"
        "  report_type: appraisal_report\n"
        "  subject:\n"
        "    address: \"\"\n"
        "    city: \"\"\n"
        "    state: \"\"\n"
        "    postal_code: \"\"\n"
        "    county: \"\"\n"
        "    assessor_parcel_number: \"\"\n"
        "  scope:\n"
        "    inspection_type: \"\"\n"
        "    valuation_premise: \"\"\n"
        "    ownership_interest: \"\"\n"
        "  source_paths:\n"
        "    - sources/\n"
        "  notes:\n"
        "    - Private local assignment data. Do not commit.\n"
        "  facts: []\n"
    )


def _review_steps(snapshot: RealEstateAssignmentSnapshot) -> list[str]:
    steps = []
    for item in snapshot.missing_items[:6]:
        steps.append(item.resolution_guidance)
    for conflict in snapshot.conflicts[:4]:
        steps.append(f"Resolve conflicting {conflict.field_name} values.")
    for risk in snapshot.risks[:4]:
        if risk.risk_type == "unsupported_fact":
            steps.append(f"Verify {risk.related_field} against source documents.")
        if risk.risk_type == "timeline_risk":
            steps.append("Confirm assignment due date and current status.")
        if risk.risk_type == "scope_ambiguity":
            steps.append("Confirm inspection scope.")
    if any(source.source_category == "contract" for source in snapshot.sources):
        steps.append("Review contract terms.")
    if any(source.source_category == "permit" for source in snapshot.sources):
        steps.append("Review available permit documents.")
    return _bullet(sorted(set(steps)) or ["Review assignment file for missing source documents and scope information."])


def _subject_address(subject: RealEstateSubject) -> str:
    return ", ".join(part for part in [subject.address, subject.city, subject.state, subject.postal_code] if part)


def _is_overdue(due_date: str, status: str) -> bool:
    if status in {"completed", "archived"} or not due_date:
        return False
    try:
        return date.fromisoformat(due_date) < date.today()
    except ValueError:
        return False


def _assignment_summary_sort_key(item: JsonMap):
    return (0 if _is_overdue(str(item.get("due_date", "")), str(item.get("status", ""))) else 1, _status_rank(str(item.get("status", ""))), str(item.get("due_date", "9999-99-99")), str(item.get("assignment_id", "")))


def _status_rank(status: str) -> int:
    return {"waiting_for_information": 0, "active": 1, "analysis": 2, "review": 3, "intake": 4, "completed": 5, "archived": 6}.get(status, 7)


def _conflict_severity(field: str) -> str:
    if field in {"subject.address", "effective_date", "intended_use", "client_name", "property_type", "assignment_type"}:
        return "high"
    if field in {"gross_living_area", "site_area", "bedroom_count", "bathroom_count", "year_built", "subject.assessor_parcel_number", "scope.ownership_interest"}:
        return "medium"
    return "low"


def _conflict_compare_value(field: str, value: str) -> str:
    text = html.unescape(str(value or "")).replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text).strip()
    if field == "property_type":
        return normalize_property_type(text)
    if field in {"subject.address", "address"}:
        parsed = structured_address(text)
        return str(parsed.get("normalized_street_identity") or _address_surface_value(text))
    if field in {"effective_date", "due_date"}:
        iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})(?:[tT ].*)?$", text)
        if iso:
            return f"{iso.group(1)}-{iso.group(2)}-{iso.group(3)}"
        us = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", text)
        if us:
            month, day, year = int(us.group(1)), int(us.group(2)), int(us.group(3))
            if 1 <= month <= 12 and 1 <= day <= 31:
                return f"{year:04d}-{month:02d}-{day:02d}"
    if field in {"subject.postal_code", "postal_code"}:
        match = re.match(r"^(\d{5})(?:[-\s]?\d{4})?$", text)
        if match:
            return match.group(1)
    return text


def _risk_severity_from_missing(severity: str) -> str:
    return "high" if severity in {"critical", "high"} else "medium" if severity == "medium" else "low"


def _severity_rank(severity: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(severity, 3)


def _missing_rank(severity: str) -> int:
    return {"critical": 0, "high": 1, "medium": 2, "low": 3}.get(severity, 4)


def _valid_or_default(value: str, valid: set[str], default: str) -> str:
    return value if value in valid else default


def structured_address(
    value: Any,
    *,
    city: Any = "",
    state: Any = "",
    postal_code: Any = "",
) -> JsonMap:
    """Parse explicit address components for deterministic comparison only."""
    raw_value = html.unescape(str(value or "")).replace("\xa0", " ").strip()
    source_fields = {
        "address": raw_value,
        "city": str(city or "").strip(),
        "state": str(state or "").strip(),
        "postal_code": str(postal_code or "").strip(),
    }
    components = {name: "" for name in ADDRESS_COMPONENTS}
    raw_components: JsonMap = {**source_fields, "street_suffix": "", "predirectional": "", "postdirectional": "", "unit_type": "", "unit_identifier": ""}
    errors: list[str] = []
    if not raw_value:
        return {
            "raw_value": raw_value,
            "source_fields": source_fields,
            "structured_value": components,
            "raw_components": raw_components,
            "normalized_street_identity": "",
            "supplied_components": [],
            "omitted_components": ADDRESS_COMPONENTS.copy(),
            "parse_status": "unavailable",
            "parse_errors": ["blank_address"],
        }

    parts = [re.sub(r"\s+", " ", part).strip() for part in raw_value.split(",")]
    street_text = parts[0]
    locality_parts = parts[1:]
    if locality_parts and re.match(r"(?i)^(?:unit|apt|apartment|suite|ste|#)\s*[a-z0-9-]+$", locality_parts[0]):
        street_text += " " + locality_parts.pop(0)
    derived_city = locality_parts[0] if len(locality_parts) > 0 else ""
    derived_state = locality_parts[1] if len(locality_parts) > 1 else ""
    derived_postal = locality_parts[2] if len(locality_parts) > 2 else ""
    if len(locality_parts) == 2:
        state_zip = re.fullmatch(r"\s*([A-Za-z. ]+?)\s+(\d{5}(?:-\d{4})?)\s*", locality_parts[1])
        if state_zip:
            derived_state, derived_postal = state_zip.groups()
    locality_city = source_fields["city"] or derived_city
    locality_state = source_fields["state"] or derived_state
    locality_postal = source_fields["postal_code"] or derived_postal

    prepared = re.sub(r"#\s*", " unit ", street_text.lower())
    prepared = re.sub(r"[^a-z0-9-]+", " ", prepared)
    tokens = prepared.split()
    if not tokens or not re.fullmatch(r"\d+[a-z]?(?:-\d+[a-z]?)?", tokens[0]):
        errors.append("missing_or_malformed_street_number")
    else:
        components["street_number"] = tokens.pop(0)

    if tokens and tokens[0] in ADDRESS_DIRECTIONAL_ALIASES:
        raw_components["predirectional"] = tokens[0]
        components["predirectional"] = ADDRESS_DIRECTIONAL_ALIASES[tokens.pop(0)]

    unit_index = next((index for index, token in enumerate(tokens) if token in ADDRESS_UNIT_ALIASES), None)
    street_tokens = tokens if unit_index is None else tokens[:unit_index]
    if unit_index is not None:
        raw_components["unit_type"] = tokens[unit_index]
        components["unit_type"] = ADDRESS_UNIT_ALIASES[tokens[unit_index]]
        if unit_index + 1 < len(tokens):
            raw_components["unit_identifier"] = tokens[unit_index + 1]
            components["unit_identifier"] = tokens[unit_index + 1]
            if unit_index + 2 < len(tokens):
                errors.append("malformed_unit_identifier")
        else:
            errors.append("missing_unit_identifier")

    if street_tokens and street_tokens[-1] in ADDRESS_DIRECTIONAL_ALIASES:
        raw_components["postdirectional"] = street_tokens[-1]
        components["postdirectional"] = ADDRESS_DIRECTIONAL_ALIASES[street_tokens.pop()]
    if street_tokens and street_tokens[-1] in ADDRESS_SUFFIX_ALIASES:
        raw_components["street_suffix"] = street_tokens[-1]
        components["street_suffix"] = ADDRESS_SUFFIX_ALIASES[street_tokens.pop()]
    else:
        errors.append("unsupported_or_missing_street_suffix")
    components["street_name"] = " ".join(street_tokens)
    if not components["street_name"]:
        errors.append("missing_street_name")

    components["city"] = re.sub(r"[^a-z0-9]+", " ", locality_city.lower()).strip()
    state_token = re.sub(r"[^a-z]", "", locality_state.lower())
    components["state"] = ADDRESS_STATE_ALIASES.get(state_token, state_token)
    postal_match = re.fullmatch(r"(\d{5})(?:[-\s]?\d{4})?", locality_postal.strip())
    components["postal_code"] = postal_match.group(1) if postal_match else re.sub(r"\s+", "", locality_postal.lower())
    if locality_postal and not postal_match:
        errors.append("malformed_postal_code")
    raw_components.update({"city": locality_city, "state": locality_state, "postal_code": locality_postal})

    identity_names = ["street_number", "predirectional", "street_name", "street_suffix", "postdirectional", "unit_type", "unit_identifier"]
    identity = "|".join(components[name] for name in identity_names)
    supplied = [name for name in ADDRESS_COMPONENTS if components[name] != ""]
    return {
        "raw_value": raw_value,
        "source_fields": source_fields,
        "structured_value": components,
        "raw_components": raw_components,
        "normalized_street_identity": identity,
        "supplied_components": supplied,
        "omitted_components": [name for name in ADDRESS_COMPONENTS if name not in supplied],
        "parse_status": "review_required" if errors else "parsed",
        "parse_errors": errors,
    }


def compare_structured_addresses(scenario: JsonMap, canonical: JsonMap) -> JsonMap:
    """Compare parsed subject addresses without inferring omitted facts."""
    scenario_raw = str(scenario.get("raw_value", ""))
    canonical_raw = str(canonical.get("raw_value", ""))
    if not scenario_raw or not canonical_raw:
        return {
            "equivalent": False,
            "equivalence_status": "unavailable",
            "equivalence_reason": "One or both address values are unavailable.",
            "equivalent_components": [],
            "conflicting_components": [],
            "omitted_components": {"scenario": scenario.get("omitted_components", []), "canonical": canonical.get("omitted_components", [])},
        }

    left = dict(scenario.get("structured_value", {}))
    right = dict(canonical.get("structured_value", {}))
    exact_surface = _address_surface_value(scenario_raw) == _address_surface_value(canonical_raw)
    parse_errors = list(scenario.get("parse_errors", [])) + list(canonical.get("parse_errors", []))
    if parse_errors:
        return {
            "equivalent": False,
            "equivalence_status": "unavailable",
            "equivalence_reason": "Deterministic structured equivalence could not be established for a non-empty address.",
            "equivalent_components": [],
            "conflicting_components": ["address_parseability"],
            "omitted_components": {"scenario": scenario.get("omitted_components", []), "canonical": canonical.get("omitted_components", [])},
            "parse_errors": {"scenario": scenario.get("parse_errors", []), "canonical": canonical.get("parse_errors", [])},
        }

    identity_names = ["street_number", "predirectional", "street_name", "street_suffix", "postdirectional", "unit_type", "unit_identifier"]
    locality_names = ["city", "state", "postal_code"]
    equivalent_components: list[str] = []
    conflicting_components: list[str] = []
    for name in identity_names:
        if left.get(name, "") == right.get(name, ""):
            equivalent_components.append(name)
        else:
            conflicting_components.append(name)
    for name in locality_names:
        left_value, right_value = left.get(name, ""), right.get(name, "")
        if left_value and right_value:
            if left_value == right_value:
                equivalent_components.append(name)
            else:
                conflicting_components.append(name)

    omitted = {
        "scenario": [name for name in ADDRESS_COMPONENTS if not left.get(name, "")],
        "canonical": [name for name in ADDRESS_COMPONENTS if not right.get(name, "")],
    }
    if conflicting_components:
        return {
            "equivalent": False,
            "equivalence_status": "conflict",
            "equivalence_reason": "Structured address components conflict: " + ", ".join(conflicting_components) + ".",
            "equivalent_components": equivalent_components,
            "conflicting_components": conflicting_components,
            "omitted_components": omitted,
        }
    locality_omitted = any((left.get(name, "") == "") != (right.get(name, "") == "") for name in locality_names)
    status = "exact" if exact_surface and not locality_omitted else "incomplete_but_non_conflicting" if locality_omitted else "deterministic_equivalent"
    reason = {
        "exact": "Address values are exactly equivalent after harmless surface normalization.",
        "deterministic_equivalent": "Explicit address aliases normalize to the same structured components.",
        "incomplete_but_non_conflicting": "Street identity is equivalent and omitted locality does not contradict supplied locality.",
    }[status]
    return {
        "equivalent": True,
        "equivalence_status": status,
        "equivalence_reason": reason,
        "equivalent_components": equivalent_components,
        "conflicting_components": [],
        "omitted_components": omitted,
    }


def _address_surface_value(value: Any) -> str:
    return re.sub(r"[^a-z0-9]+", " ", html.unescape(str(value or "")).lower()).strip()


def normalize_property_type(value: Any) -> str:
    """Normalize explicit property-type labels without inference."""
    text = html.unescape(str(value or "")).replace("\xa0", " ").strip().lower()
    text = re.sub(r"^[^\w]+|[^\w]+$", "", text)
    token = re.sub(r"[\s_-]+", "_", text).strip("_")
    return PROPERTY_TYPE_ALIASES.get(token, token)


def property_type_normalization_status(value: Any) -> str:
    raw = str(value or "")
    normalized = normalize_property_type(raw)
    if not raw.strip():
        return "unavailable"
    if normalized == "other":
        return "explicit_other"
    if normalized in VALID_PROPERTY_TYPES:
        return "normalized"
    return "review_required"


def _fact_lines(facts: list[RealEstateFact]) -> list[str]:
    return _bullet([f"`{item.field_name}` = `{item.value}` ({item.verification_status}, confidence={item.confidence})" for item in facts] or ["No structured facts found."])


def _source_lines(sources: list[RealEstateSourceRecord]) -> list[str]:
    return _bullet([f"`{item.filename}` category={item.source_category} extension={item.extension} size={item.size_bytes} source_id={item.source_id}" for item in sources] or ["No supported source files found."])


def _missing_lines(items: list[RealEstateMissingItem]) -> list[str]:
    return _bullet([f"{item.severity}: `{item.field_name}` - {item.resolution_guidance}" for item in items] or ["No missing required information detected."])


def _conflict_lines(items: list[RealEstateFactConflict]) -> list[str]:
    return _bullet([f"{item.severity}: `{item.field_name}` values={', '.join(item.values)}" for item in items] or ["No exact structured conflicts detected."])


def _risk_lines(items: list[RealEstateAssignmentRisk]) -> list[str]:
    return _bullet([f"{item.severity}: {item.risk_type} - {item.description}" for item in items] or ["No deterministic assignment risks detected."])


def _timeline_lines(items: list[RealEstateAssignmentTimelineEvent]) -> list[str]:
    return _bullet([f"{item.occurred_at}: {item.title}" for item in items] or ["No timeline events found."])


def _summary_lines(data: JsonMap) -> list[str]:
    return _bullet([f"{key}: `{value}`" for key, value in data.items()] or ["None"])


def _bullet(items: list[str]) -> list[str]:
    return [*[f"- {item}" for item in items], ""]


def _map(value: Any) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _map_list(value: Any) -> list[JsonMap]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:16]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
