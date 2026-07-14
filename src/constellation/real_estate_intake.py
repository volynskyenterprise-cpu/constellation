from __future__ import annotations

import fnmatch
import json
import re
import shutil
import subprocess
from dataclasses import dataclass, replace
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from .dashboard import ExecutiveDashboardStore
from .canonical_assignments import CanonicalAssignmentEngine, CanonicalAssignmentResolver, normalize_address, normalize_date, normalize_path, normalize_postal_code
from .io import read_json, write_json
from .models import JsonMap
from .real_estate import RealEstateAssignmentStore, assignment_directory
from .simple_yaml import load_yaml


class RealEstateIntakeError(RuntimeError):
    pass


SUPPORTED_INTAKE_EXTENSIONS = {".json", ".yaml", ".yml", ".md", ".txt"}


FIELD_ALIASES = {
    "assignment_id": ["assignment_id"],
    "order_id": ["order_id"],
    "loan_number": ["loan_number"],
    "address": ["subject_address", "property_address", "address"],
    "city": ["city", "property_city", "subject_city"],
    "state": ["state", "property_state", "subject_state"],
    "postal_code": ["postal_code", "zip", "zipcode", "property_zip", "subject_zip"],
    "client_name": ["client_name", "client"],
    "lender": ["lender"],
    "amc": ["amc"],
    "due_date": ["due_date", "delivery_date", "report_due"],
    "effective_date": ["effective_date", "valuation_date"],
    "assignment_type": ["assignment_type", "order_type", "service_type"],
    "property_type": ["property_type"],
    "report_type": ["report_type"],
    "intended_use": ["intended_use"],
    "inspection_type": ["inspection_type"],
    "ownership_interest": ["ownership_interest"],
    "source_files": ["source_files", "attachments", "attachment_paths"],
    "knowledge_pack_path": ["knowledge_pack_path"],
}


@dataclass(frozen=True)
class RealEstateIntakeSource:
    id: str
    enabled: bool
    source_type: str
    root_path: str
    include_patterns: list[str]
    archive_processed: bool

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class RealEstateFieldMapping:
    target_field: str
    source_key: str
    value: Any

    def to_dict(self) -> JsonMap:
        return {"target_field": self.target_field, "source_key": self.source_key, "value": self.value}


@dataclass(frozen=True)
class RealEstateSourceAttachment:
    original_path: str
    assignment_source_path: str
    checksum: str
    mode: str
    status: str

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class RealEstateAssignmentCandidate:
    intake_id: str
    source_id: str
    source_path: str
    checksum: str
    detected_assignment_id: str
    original_identifier: str
    source_type: str
    structured_data: JsonMap
    field_mappings: list[RealEstateFieldMapping]
    fields_unmapped: list[str]
    warnings: list[str]
    already_imported: bool

    def to_dict(self) -> JsonMap:
        return {
            "intake_id": self.intake_id,
            "source_id": self.source_id,
            "source_path": self.source_path,
            "checksum": self.checksum,
            "detected_assignment_id": self.detected_assignment_id,
            "original_identifier": self.original_identifier,
            "source_type": self.source_type,
            "structured_data": self.structured_data,
            "field_mappings": [item.to_dict() for item in self.field_mappings],
            "fields_mapped": [item.target_field for item in self.field_mappings],
            "fields_unmapped": self.fields_unmapped,
            "warnings": self.warnings,
            "already_imported": self.already_imported,
        }


@dataclass(frozen=True)
class RealEstateIntakeRecord:
    intake_id: str
    source_id: str
    source_path: str
    checksum: str
    detected_assignment_id: str
    import_status: str
    assignment_path: str
    assignment_brief_path: str
    fields_mapped: list[str]
    fields_unmapped: list[str]
    conflicts_created: list[str]
    sources_linked: list[str]
    imported_at: str
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class RealEstateIntakeManifest:
    intake_run_id: str
    created_at: str
    records: list[RealEstateIntakeRecord]
    errors: list[JsonMap]
    counts: JsonMap

    def to_dict(self) -> JsonMap:
        return {
            "intake_run_id": self.intake_run_id,
            "created_at": self.created_at,
            "records": [item.to_dict() for item in self.records],
            "errors": self.errors,
            "counts": self.counts,
        }


@dataclass(frozen=True)
class RealEstateIntakeResult:
    manifest: RealEstateIntakeManifest
    dashboard_refreshed: bool

    def to_dict(self) -> JsonMap:
        data = self.manifest.to_dict()
        data["dashboard_refreshed"] = self.dashboard_refreshed
        return data


class RealEstateIntakeStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "outputs" / "real-estate" / "intake"
        self.manifest_path = self.directory / "intake-manifest.json"
        self.markdown_path = self.directory / "intake-manifest.md"
        self.history_path = self.directory / "intake-history.json"
        self.latest_path = self.directory / "latest-intake.json"
        self.errors_path = self.directory / "intake-errors.json"

    def load_config(self) -> JsonMap:
        for path in [self.root / "config" / "real-estate-intake.local.yaml", self.root / "config" / "real-estate-intake.yaml", self.root / "config" / "real-estate-intake.example.yaml"]:
            if path.exists():
                data = load_yaml(path)
                config = _map(data.get("real_estate_intake"))
                config["config_path"] = str(path)
                return config
        return {"enabled": False, "assignment_root": "real-estate/assignments", "sources": [], "source_mode": "reference", "config_path": None}

    def sources(self) -> list[RealEstateIntakeSource]:
        config = self.load_config()
        sources = []
        for item in _map_list(config.get("sources", [])):
            sources.append(
                RealEstateIntakeSource(
                    id=str(item.get("id") or "unknown"),
                    enabled=bool(item.get("enabled")),
                    source_type=str(item.get("source_type") or "local_directory"),
                    root_path=str(item.get("root_path") or ""),
                    include_patterns=_string_list(item.get("include_patterns", [])),
                    archive_processed=bool(item.get("archive_processed")),
                )
            )
        return sources

    def imported_keys(self) -> set[str]:
        if not self.history_path.exists():
            return set()
        data = read_json(self.history_path)
        keys = set()
        for manifest in _map_list(data.get("manifests", [])):
            for record in _map_list(manifest.get("records", [])):
                keys.add(_record_key(record.get("source_path"), record.get("checksum"), record.get("detected_assignment_id")))
        return keys

    def save(self, manifest: RealEstateIntakeManifest) -> None:
        data = manifest.to_dict()
        write_json(self.manifest_path, data)
        write_json(self.latest_path, data)
        write_json(self.errors_path, {"errors": manifest.errors})
        history = {"manifests": []}
        if self.history_path.exists():
            history = read_json(self.history_path)
        manifests = _map_list(history.get("manifests", []))
        if not manifests or manifests[-1].get("intake_run_id") != manifest.intake_run_id:
            manifests.append(data)
        write_json(self.history_path, {"manifests": manifests})
        self.markdown_path.parent.mkdir(parents=True, exist_ok=True)
        self.markdown_path.write_text(render_intake_manifest_markdown(manifest), encoding="utf-8")

    def latest(self) -> JsonMap:
        return read_json(self.latest_path) if self.latest_path.exists() else {}

    def history(self) -> list[JsonMap]:
        if not self.history_path.exists():
            return []
        return _map_list(read_json(self.history_path).get("manifests", []))


class RealEstateIntakeEngine:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.store = RealEstateIntakeStore(root)
        self.assignment_store = RealEstateAssignmentStore(root)

    def status(self) -> JsonMap:
        candidates = self.scan()
        latest = self.store.latest()
        counts = _map(latest.get("counts"))
        config = self.store.load_config()
        return {
            "config_available": bool(config.get("config_path")),
            "config_path": config.get("config_path"),
            "enabled_sources": [source.id for source in self.store.sources() if source.enabled],
            "assignment_root": str(self.root / str(config.get("assignment_root") or "real-estate/assignments")),
            "detected_candidate_count": len(candidates),
            "imported_count": counts.get("imported", 0),
            "skipped_duplicate_count": counts.get("skipped_duplicate", 0),
            "error_count": counts.get("errors", 0),
            "manifest_path": str(self.store.manifest_path),
        }

    def scan(self, *, source_id: str | None = None, file_path: Path | None = None) -> list[RealEstateAssignmentCandidate]:
        keys = self.store.imported_keys()
        paths: list[tuple[str, Path, str]] = []
        if file_path is not None:
            paths.append(("explicit_file", file_path, "explicit_file"))
        else:
            for source in self.store.sources():
                if source_id and source.id != source_id:
                    continue
                if not source.enabled:
                    continue
                paths.extend((source.id, path, source.source_type) for path in _source_files(source))
        candidates = []
        for source, path, source_type in sorted(paths, key=lambda item: (item[0], str(item[1]).lower())):
            try:
                candidate = self._candidate(source, path, source_type, keys)
            except Exception:
                continue
            candidates.append(candidate)
        return candidates

    def import_candidates(self, *, source_id: str | None = None, file_path: Path | None = None, open_brief: bool = False) -> RealEstateIntakeResult:
        records: list[RealEstateIntakeRecord] = []
        errors: list[JsonMap] = []
        imported_keys = self.store.imported_keys()
        candidates = sorted(self.scan(source_id=source_id, file_path=file_path), key=_candidate_import_sort_key)
        try:
            CanonicalAssignmentEngine(self.root).build()
        except Exception:
            pass
        for candidate in candidates:
            try:
                candidate = self._canonical_candidate(candidate)
                duplicate = _record_key(candidate.source_path, candidate.checksum, candidate.detected_assignment_id) in imported_keys
                if duplicate and assignment_directory(self.root, candidate.detected_assignment_id).exists():
                    records.append(self._record(candidate, "skipped_duplicate", [], [], []))
                    continue
                record = self._import_candidate(candidate)
                records.append(record)
                try:
                    CanonicalAssignmentEngine(self.root).build()
                except Exception:
                    pass
                if open_brief and record.assignment_brief_path:
                    _open_in_code(Path(record.assignment_brief_path))
            except Exception as exc:
                errors.append({"source_path": candidate.source_path, "error": str(exc)})
                records.append(self._record(candidate, "error", [], [], []))
        counts = {
            "imported": sum(1 for record in records if record.import_status in {"imported", "updated"}),
            "updated": sum(1 for record in records if record.import_status == "updated"),
            "skipped_duplicate": sum(1 for record in records if record.import_status == "skipped_duplicate"),
            "errors": len(errors) + sum(1 for record in records if record.import_status == "error"),
        }
        manifest = RealEstateIntakeManifest(f"real_estate_intake_{_digest('|'.join(record.intake_id for record in records) + _now_iso())}", _now_iso(), records, errors, counts)
        self.store.save(manifest)
        try:
            CanonicalAssignmentEngine(self.root).build()
        except Exception:
            pass
        dashboard_refreshed = False
        try:
            ExecutiveDashboardStore(self.root).generate(overwrite=True)
            dashboard_refreshed = True
        except Exception:
            dashboard_refreshed = False
        return RealEstateIntakeResult(manifest, dashboard_refreshed)

    def _candidate(self, source_id: str, path: Path, source_type: str, imported_keys: set[str]) -> RealEstateAssignmentCandidate:
        if not path.exists() or path.suffix.lower() not in SUPPORTED_INTAKE_EXTENSIONS:
            raise RealEstateIntakeError(f"Unsupported intake file: {path}")
        data = _parse_intake_file(path)
        mappings, unmapped = _field_mappings(data)
        checksum = _file_checksum(path)
        assignment_id, original_identifier = _assignment_id(path, data)
        intake_id = f"intake_{_digest(source_id + str(path) + checksum)}"
        already_imported = _record_key(str(path), checksum, assignment_id) in imported_keys
        warnings = [] if mappings else ["No supported assignment fields detected."]
        return RealEstateAssignmentCandidate(intake_id, source_id, str(path), checksum, assignment_id, original_identifier, source_type, data, mappings, unmapped, warnings, already_imported)

    def _import_candidate(self, candidate: RealEstateAssignmentCandidate) -> RealEstateIntakeRecord:
        assignment_dir = assignment_directory(self.root, candidate.detected_assignment_id)
        assignment_path = assignment_dir / "assignment.yaml"
        assignment_dir.mkdir(parents=True, exist_ok=True)
        for child in ["sources", "notes", "evidence"]:
            (assignment_dir / child).mkdir(parents=True, exist_ok=True)
        existing = _read_existing_assignment(assignment_path)
        merged, conflicts = _merge_assignment(existing, candidate)
        source_mode = str(self.store.load_config().get("source_mode") or "reference")
        sources = self._link_sources(candidate, source_mode)
        source_paths = sorted(set(normalize_path(item) for item in _string_list(_map(merged.get("assignment")).get("source_paths", [])) + [item.assignment_source_path for item in sources] if item))
        merged["assignment"]["source_paths"] = source_paths
        merged["assignment"]["provenance"] = {"auto_ingested_from": normalize_path(candidate.source_path), "original_identifier": candidate.original_identifier, "canonical_assignment_id": candidate.detected_assignment_id}
        _write_assignment_yaml(assignment_path, merged["assignment"])
        snapshot = self.assignment_store.build(candidate.detected_assignment_id)
        status = "updated" if existing else "imported"
        return self._record(candidate, status, conflicts, [item.to_dict() for item in sources], [str(item.assignment_source_path) for item in sources], snapshot.to_dict())

    def _canonical_candidate(self, candidate: RealEstateAssignmentCandidate) -> RealEstateAssignmentCandidate:
        resolution = CanonicalAssignmentResolver(self.root).resolve_fields(
            candidate.structured_data,
            source_alias=candidate.detected_assignment_id,
            source_path=candidate.source_path,
        )
        canonical_id = resolution.canonical_assignment_id or candidate.detected_assignment_id
        if canonical_id == candidate.detected_assignment_id:
            return candidate
        data = dict(candidate.structured_data)
        data.setdefault("source_generated_alias", candidate.detected_assignment_id)
        data.setdefault("canonical_assignment_id", canonical_id)
        warnings = list(candidate.warnings)
        warnings.append(f"Resolved alias {candidate.detected_assignment_id} to canonical assignment {canonical_id}.")
        return replace(
            candidate,
            detected_assignment_id=canonical_id,
            original_identifier=candidate.original_identifier or candidate.detected_assignment_id,
            structured_data=data,
            warnings=warnings,
            already_imported=False,
        )

    def _link_sources(self, candidate: RealEstateAssignmentCandidate, source_mode: str) -> list[RealEstateSourceAttachment]:
        config = self.store.load_config()
        roots = [Path(str(source.root_path)).resolve() for source in self.store.sources() if source.root_path]
        if candidate.source_id == "explicit_file":
            roots.append(Path(candidate.source_path).resolve().parent)
        raw_paths = [candidate.source_path] + _attachment_paths(candidate.structured_data)
        result = []
        assignment_sources = assignment_directory(self.root, candidate.detected_assignment_id) / "sources"
        for raw in raw_paths:
            path = Path(raw)
            if not path.is_absolute():
                path = Path(candidate.source_path).parent / raw
            if not path.exists() or path.is_dir():
                continue
            checksum = _file_checksum(path)
            if source_mode == "copy":
                if not _inside_any(path.resolve(), roots):
                    result.append(RealEstateSourceAttachment(str(path), "", checksum, "copy", "skipped_outside_configured_roots"))
                    continue
                destination = assignment_sources / path.name
                if not destination.exists():
                    shutil.copy2(path, destination)
                result.append(RealEstateSourceAttachment(str(path), (Path("sources") / destination.name).as_posix(), checksum, "copy", "linked"))
            else:
                result.append(RealEstateSourceAttachment(str(path), str(path.resolve()), checksum, "reference", "linked"))
        by_path = {item.assignment_source_path: item for item in result if item.status == "linked" and item.assignment_source_path}
        return [by_path[key] for key in sorted(by_path)]

    def _record(self, candidate: RealEstateAssignmentCandidate, status: str, conflicts: list[str], source_records: list[JsonMap], sources_linked: list[str], snapshot: JsonMap | None = None) -> RealEstateIntakeRecord:
        assignment_path = assignment_directory(self.root, candidate.detected_assignment_id) / "assignment.yaml"
        brief_path = self.assignment_store.output_dir(candidate.detected_assignment_id) / "assignment-brief.md"
        return RealEstateIntakeRecord(
            intake_id=candidate.intake_id,
            source_id=candidate.source_id,
            source_path=candidate.source_path,
            checksum=candidate.checksum,
            detected_assignment_id=candidate.detected_assignment_id,
            import_status=status,
            assignment_path=str(assignment_path),
            assignment_brief_path=str(brief_path if brief_path.exists() else ""),
            fields_mapped=[item.target_field for item in candidate.field_mappings],
            fields_unmapped=candidate.fields_unmapped,
            conflicts_created=conflicts,
            sources_linked=sources_linked,
            imported_at=_now_iso(),
            provenance={"source_records": source_records, "snapshot_id": _map(snapshot).get("snapshot_id"), "original_identifier": candidate.original_identifier},
        )


def render_intake_manifest_markdown(manifest: RealEstateIntakeManifest) -> str:
    lines = ["# Real Estate Intake Manifest", "", f"Intake run: `{manifest.intake_run_id}`", f"Created: `{manifest.created_at}`", "", "## Counts", ""]
    lines.extend(f"- {key}: `{value}`" for key, value in manifest.counts.items())
    lines.extend(["", "## Records", ""])
    if not manifest.records:
        lines.append("- No records.")
    for record in manifest.records:
        lines.append(f"- `{record.detected_assignment_id}` status={record.import_status} source=`{record.source_path}` brief=`{record.assignment_brief_path}`")
    if manifest.errors:
        lines.extend(["", "## Errors", ""])
        lines.extend(f"- `{item.get('source_path')}`: {item.get('error')}" for item in manifest.errors)
    lines.append("")
    return "\n".join(lines)


def _source_files(source: RealEstateIntakeSource) -> list[Path]:
    root = Path(source.root_path)
    if not root.exists() or source.source_type != "local_directory":
        return []
    paths = []
    for pattern in source.include_patterns:
        paths.extend(path for path in root.glob(pattern) if path.is_file() and path.suffix.lower() in SUPPORTED_INTAKE_EXTENSIONS)
    return sorted(set(paths), key=lambda item: str(item).lower())


def _parse_intake_file(path: Path) -> JsonMap:
    suffix = path.suffix.lower()
    if suffix == ".json":
        data = json.loads(path.read_text(encoding="utf-8"))
    elif suffix in {".yaml", ".yml"}:
        data = load_yaml(path)
    else:
        data = _parse_markdown_or_text(path)
    if not isinstance(data, dict):
        raise RealEstateIntakeError(f"Structured intake must be a mapping: {path}")
    return _flatten_assignment_wrapper(data)


def _parse_markdown_or_text(path: Path) -> JsonMap:
    text = path.read_text(encoding="utf-8")
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            front = parts[1].strip()
            return _parse_labeled_text(front)
    return _parse_labeled_text(text)


def _parse_labeled_text(text: str) -> JsonMap:
    data: JsonMap = {}
    for line in text.splitlines():
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        normalized = _normalize_key(key)
        if normalized in {alias for aliases in FIELD_ALIASES.values() for alias in aliases}:
            data[normalized] = value.strip()
    return data


def _flatten_assignment_wrapper(data: JsonMap) -> JsonMap:
    for key in ["assignment", "order", "intake"]:
        child = data.get(key)
        if isinstance(child, dict):
            merged = data.copy()
            merged.update(child)
            return merged
    return data


def _field_mappings(data: JsonMap) -> tuple[list[RealEstateFieldMapping], list[str]]:
    mappings = []
    used = set()
    for target, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            if alias in data and _has_value(data.get(alias)):
                mappings.append(RealEstateFieldMapping(target, alias, data.get(alias)))
                used.add(alias)
                break
    unmapped = sorted(str(key) for key, value in data.items() if key not in used and _has_value(value))
    return mappings, unmapped


def _assignment_id(path: Path, data: JsonMap) -> tuple[str, str]:
    for key in ["assignment_id", "order_id", "loan_number"]:
        if _has_value(data.get(key)):
            return _safe_id(str(data[key])), str(data[key])
    address = _first_value(data, ["subject_address", "property_address", "address"])
    due_date = _first_value(data, ["due_date", "delivery_date", "report_due", "effective_date"])
    if address:
        identifier = f"{address}-{due_date or path.stem}"
        return _safe_id(identifier), identifier
    payload = str(path.resolve()) + json.dumps(data, sort_keys=True)
    return f"assignment-{_digest(payload)}", str(path)


def _merge_assignment(existing: JsonMap, candidate: RealEstateAssignmentCandidate) -> tuple[JsonMap, list[str]]:
    assignment = _default_assignment(candidate.detected_assignment_id)
    if existing:
        assignment.update(_map(existing.get("assignment", existing)))
        assignment["subject"] = {**_map(_default_assignment(candidate.detected_assignment_id).get("subject")), **_map(_map(existing.get("assignment", existing)).get("subject"))}
        assignment["scope"] = {**_map(_default_assignment(candidate.detected_assignment_id).get("scope")), **_map(_map(existing.get("assignment", existing)).get("scope"))}
    conflicts = []
    target_values = {mapping.target_field: mapping.value for mapping in candidate.field_mappings}
    roles = []
    for role in ["lender", "amc"]:
        if role in target_values:
            roles.append({"role": role, "name": str(target_values[role])})
    scalar_targets = {
        "assignment_type": "assignment_type",
        "property_type": "property_type",
        "intended_use": "intended_use",
        "client_name": "client_name",
        "due_date": "due_date",
        "effective_date": "effective_date",
        "report_type": "report_type",
    }
    subject_targets = {"address": "address", "city": "city", "state": "state", "postal_code": "postal_code"}
    scope_targets = {"inspection_type": "inspection_type", "ownership_interest": "ownership_interest"}
    for target, field in scalar_targets.items():
        if target in target_values:
            _merge_value(assignment, field, target_values[target], candidate, conflicts)
    for target, field in subject_targets.items():
        if target in target_values:
            _merge_value(assignment["subject"], field, target_values[target], candidate, conflicts, prefix="subject.")
    for target, field in scope_targets.items():
        if target in target_values:
            _merge_value(assignment["scope"], field, target_values[target], candidate, conflicts, prefix="scope.")
    if roles:
        notes = _string_list(assignment.get("notes", []))
        for role in roles:
            note = f"Intake role preserved: {role['role']}={role['name']}"
            if note not in notes:
                notes.append(note)
        assignment["notes"] = notes
    assignment["facts"] = _merge_conflict_facts(_map(existing.get("assignment", existing)).get("facts", []), candidate, conflicts)
    return {"assignment": assignment}, conflicts


def _merge_value(container: JsonMap, field: str, incoming: Any, candidate: RealEstateAssignmentCandidate, conflicts: list[str], prefix: str = "") -> None:
    incoming_value = str(incoming).strip()
    existing = str(container.get(field) or "").strip()
    if not existing or existing in {"unknown", "other"}:
        container[field] = incoming_value
    elif _merge_compare_value(prefix + field, existing) != _merge_compare_value(prefix + field, incoming_value):
        conflicts.append(prefix + field)


def _merge_conflict_facts(existing_facts: Any, candidate: RealEstateAssignmentCandidate, conflicts: list[str]) -> list[JsonMap]:
    facts = _map_list(existing_facts)
    present = {(str(item.get("field_name")), str(item.get("value"))) for item in facts}
    source_path = normalize_path(candidate.source_path)
    for field in conflicts:
        incoming = next((mapping.value for mapping in candidate.field_mappings if _field_matches(mapping.target_field, field)), None)
        if incoming is None:
            continue
        record = {
            "field_name": field,
            "value": str(incoming),
            "verification_status": "source_reported",
            "confidence": "medium",
            "source_paths": [source_path],
            "notes": "Incoming intake value conflicts with existing non-empty assignment field.",
        }
        key = (str(record["field_name"]), str(record["value"]))
        if key not in present:
            facts.append(record)
            present.add(key)
    return facts


def _field_matches(target: str, field: str) -> bool:
    return target == field or field.endswith("." + target)


def _default_assignment(assignment_id: str) -> JsonMap:
    return {
        "assignment_id": assignment_id,
        "status": "intake",
        "assignment_type": "other",
        "property_type": "other",
        "intended_use": "",
        "client_name": "",
        "effective_date": "",
        "due_date": "",
        "report_type": "",
        "created_at": _today(),
        "subject": {"address": "", "city": "", "state": "", "postal_code": "", "county": "", "assessor_parcel_number": ""},
        "scope": {"inspection_type": "", "valuation_premise": "", "ownership_interest": ""},
        "source_paths": [],
        "notes": ["Auto-ingested from structured local intake. Review before valuation analysis."],
        "facts": [],
        "value_origin": {
            "assignment_type": "system_placeholder",
            "property_type": "system_placeholder",
        },
    }


def _write_assignment_yaml(path: Path, assignment: JsonMap) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = ["# Private local assignment data. Do not commit.", "assignment:"]
    for key in ["assignment_id", "status", "assignment_type", "property_type", "intended_use", "client_name", "effective_date", "due_date", "report_type", "created_at"]:
        lines.append(f"  {key}: {_yaml_scalar(assignment.get(key, ''))}")
    for section in ["subject", "scope"]:
        lines.append(f"  {section}:")
        for key, value in _map(assignment.get(section)).items():
            lines.append(f"    {key}: {_yaml_scalar(value)}")
    lines.append("  source_paths:")
    for item in _string_list(assignment.get("source_paths", [])):
        lines.append(f"    - {_yaml_scalar(item)}")
    lines.append("  notes:")
    notes = _string_list(assignment.get("notes", []))
    if not notes:
        lines.append("    - Auto-ingested from structured local intake. Review before valuation analysis.")
    for note in notes:
        lines.append(f"    - {_yaml_scalar(note)}")
    facts = _map_list(assignment.get("facts", []))
    if not facts:
        lines.append("  facts: []")
    else:
        lines.append("  facts:")
        for fact in facts:
            lines.append(f"    - field_name: {_yaml_scalar(fact.get('field_name', ''))}")
            lines.append(f"      value: {_yaml_scalar(fact.get('value', ''))}")
            lines.append(f"      verification_status: {_yaml_scalar(fact.get('verification_status', 'source_reported'))}")
            lines.append(f"      confidence: {_yaml_scalar(fact.get('confidence', 'medium'))}")
            lines.append("      source_paths:")
            for source_path in _string_list(fact.get("source_paths", [])):
                lines.append(f"        - {_yaml_scalar(source_path)}")
            lines.append(f"      notes: {_yaml_scalar(fact.get('notes', ''))}")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _read_existing_assignment(path: Path) -> JsonMap:
    if not path.exists():
        return {}
    data = load_yaml(path)
    return _map(data.get("assignment", data))


def _attachment_paths(data: JsonMap) -> list[str]:
    values = []
    for key in ["source_files", "attachments", "attachment_paths", "knowledge_pack_path"]:
        value = data.get(key)
        if isinstance(value, list):
            values.extend(str(item) for item in value if item)
        elif value:
            values.append(str(value))
    return values


def _yaml_scalar(value: Any) -> str:
    if value is None:
        return '""'
    text = str(value)
    if text == "":
        return '""'
    if any(char in text for char in [":", "#", "[", "]", "{", "}", ","]) or text.strip() != text or "\\" in text:
        return json.dumps(text)
    return text


def _safe_id(value: str) -> str:
    text = value.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "assignment"


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _first_value(data: JsonMap, keys: list[str]) -> str:
    for key in keys:
        if _has_value(data.get(key)):
            return str(data[key])
    return ""


def _has_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, dict)):
        return bool(value)
    return True


def _inside_any(path: Path, roots: list[Path]) -> bool:
    for root in roots:
        try:
            path.relative_to(root)
            return True
        except ValueError:
            continue
    return False


def _record_key(source_path: Any, checksum: Any, assignment_id: Any) -> str:
    return "|".join([str(source_path or ""), str(checksum or ""), str(assignment_id or "")])


def _merge_compare_value(field: str, value: Any) -> str:
    if field in {"subject.address", "address"}:
        return normalize_address(value)
    if field in {"effective_date", "due_date"}:
        return normalize_date(value)
    if field in {"subject.postal_code", "postal_code"}:
        return normalize_postal_code(value)[:5]
    return str(value or "").strip()


def _file_checksum(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _open_in_code(path: Path) -> None:
    try:
        subprocess.run(["code", "-r", str(path)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        return


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:16]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _today() -> str:
    return datetime.now().date().isoformat()


def _map(value: Any) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _map_list(value: Any) -> list[JsonMap]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if item is not None]


def _candidate_import_sort_key(candidate: RealEstateAssignmentCandidate) -> tuple[int, str, str]:
    data = candidate.structured_data
    if _has_value(data.get("assignment_id")):
        rank = 0
    elif _has_value(data.get("order_id")):
        rank = 1
    elif _has_value(data.get("loan_number")):
        rank = 2
    elif _has_value(_first_value(data, ["subject_address", "property_address", "address"])) and _has_value(_first_value(data, ["effective_date", "valuation_date", "due_date", "delivery_date", "report_due"])):
        rank = 3
    elif _has_value(_first_value(data, ["subject_address", "property_address", "address"])):
        rank = 4
    else:
        rank = 5
    return (rank, candidate.detected_assignment_id, candidate.source_path.lower())
