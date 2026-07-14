from __future__ import annotations

import json
import html
import re
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from .io import read_json, write_json
from .models import JsonMap
from .real_estate import RealEstateAssignmentStore
from .real_estate_intake import RealEstateIntakeEngine, RealEstateIntakeStore
from .canonical_assignments import normalize_date


class AssignmentConsolidationError(RuntimeError):
    pass


RELATIONSHIP_TYPES = {"same_assignment", "source_companion", "possible_duplicate", "conflicting_assignment", "unrelated", "unassigned"}
CONFIDENCE_LEVELS = {"deterministic_high", "deterministic_medium", "deterministic_low"}


@dataclass(frozen=True)
class AssignmentArtifact:
    artifact_id: str
    artifact_type: str
    source_path: str
    source_type: str
    assignment_id: str
    order_id: str
    loan_number: str
    property_address: str
    normalized_address: str
    city: str
    state: str
    client: str
    lender: str
    amc: str
    effective_date: str
    imported_at: str
    source_stem: str
    source_generated_alias: str
    address_derived_alias: str
    hash_fallback_alias: str
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AssignmentRelationship:
    relationship_id: str
    artifact_a: str
    artifact_b: str
    relationship_type: str
    confidence: str
    reason: str

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AssignmentMergeDecision:
    artifact_id: str
    canonical_assignment_id: str
    decision: str
    reason: str

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AssignmentCluster:
    canonical_assignment_id: str
    artifact_count: int
    source_types: list[str]
    first_seen: str
    last_seen: str
    assignment_status: str
    property_address: str
    city: str
    state: str
    client: str
    lender: str
    amc: str
    assignment_aliases: list[str]
    explicit_assignment_ids: list[str]
    order_ids: list[str]
    loan_numbers: list[str]
    source_generated_ids: list[str]
    normalized_addresses: list[str]
    canonical_identifiers: JsonMap
    identity_sources: list[JsonMap]
    evidence_count: int
    knowledge_pack_available: bool
    reviewer_notes_available: bool
    conflicts: list[JsonMap]
    artifacts: list[JsonMap]
    relationships: list[str]
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AssignmentConsolidationSnapshot:
    snapshot_id: str
    created_at: str
    clusters: list[AssignmentCluster]
    artifacts: list[AssignmentArtifact]
    relationships: list[AssignmentRelationship]
    conflicts: list[JsonMap]
    unassigned_artifacts: list[JsonMap]
    aliases: list[JsonMap]
    merge_decisions: list[AssignmentMergeDecision]
    delta: JsonMap
    counts: JsonMap
    limitations: list[str]

    def to_dict(self) -> JsonMap:
        return {
            "snapshot_id": self.snapshot_id,
            "created_at": self.created_at,
            "clusters": [item.to_dict() for item in self.clusters],
            "artifacts": [item.to_dict() for item in self.artifacts],
            "relationships": [item.to_dict() for item in self.relationships],
            "conflicts": self.conflicts,
            "unassigned_artifacts": self.unassigned_artifacts,
            "aliases": self.aliases,
            "merge_decisions": [item.to_dict() for item in self.merge_decisions],
            "delta": self.delta,
            "counts": self.counts,
            "limitations": self.limitations,
        }


class AssignmentConsolidationStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "outputs" / "real-estate" / "consolidation"
        self.clusters_json = self.directory / "assignment-clusters.json"
        self.clusters_md = self.directory / "assignment-clusters.md"
        self.relationships_json = self.directory / "assignment-relationships.json"
        self.conflicts_json = self.directory / "assignment-conflicts.json"
        self.unassigned_json = self.directory / "unassigned-artifacts.json"
        self.unassigned_md = self.directory / "unassigned-artifacts.md"
        self.aliases_json = self.directory / "assignment-aliases.json"
        self.identity_report_md = self.directory / "identity-resolution-report.md"
        self.history_json = self.directory / "assignment-consolidation-history.json"
        self.delta_json = self.directory / "assignment-consolidation-delta.json"

    def save(self, snapshot: AssignmentConsolidationSnapshot) -> None:
        data = snapshot.to_dict()
        write_json(self.clusters_json, {"clusters": data["clusters"], "counts": snapshot.counts, "snapshot_id": snapshot.snapshot_id, "created_at": snapshot.created_at})
        write_json(self.relationships_json, {"relationships": data["relationships"]})
        write_json(self.conflicts_json, {"conflicts": data["conflicts"]})
        write_json(self.unassigned_json, {"unassigned_artifacts": data["unassigned_artifacts"]})
        write_json(self.aliases_json, {"aliases": data["aliases"]})
        write_json(self.delta_json, data["delta"])
        history = {"snapshots": []}
        if self.history_json.exists():
            history = read_json(self.history_json)
        snapshots = _map_list(history.get("snapshots", []))
        if not snapshots or snapshots[-1].get("snapshot_id") != snapshot.snapshot_id:
            snapshots.append(data)
        write_json(self.history_json, {"snapshots": snapshots})
        self.clusters_md.parent.mkdir(parents=True, exist_ok=True)
        self.clusters_md.write_text(render_consolidation_markdown(snapshot), encoding="utf-8")
        self.unassigned_md.write_text(render_unassigned_markdown(snapshot), encoding="utf-8")
        self.identity_report_md.write_text(render_identity_report_markdown(snapshot), encoding="utf-8")

    def load(self) -> JsonMap:
        if not self.clusters_json.exists():
            return {}
        return read_json(self.clusters_json)

    def history(self) -> list[JsonMap]:
        if not self.history_json.exists():
            return []
        return _map_list(read_json(self.history_json).get("snapshots", []))


class AssignmentConsolidationEngine:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.store = AssignmentConsolidationStore(root)

    def build(self) -> AssignmentConsolidationSnapshot:
        artifacts = _dedupe_artifacts(_intake_artifacts(self.root))
        relationships = _relationships(artifacts)
        clusters, decisions, conflicts, unassigned = _clusters(artifacts, relationships, self.root)
        aliases = _aliases(clusters)
        previous = self.store.history()[-1] if self.store.history() else {}
        delta = _delta(previous, clusters, relationships, conflicts, unassigned, aliases)
        counts = {
            "assignment_count": len(clusters),
            "artifact_count": len(artifacts),
            "canonical_assignment_count": len(clusters),
            "alias_count": len(aliases),
            "source_companion_count": sum(1 for item in relationships if item.relationship_type == "source_companion"),
            "unassigned_artifact_count": len(unassigned),
            "true_identity_conflict_count": len(conflicts),
            "knowledge_pack_count": sum(1 for item in artifacts if item.artifact_type == "knowledge_pack"),
            "assignments_with_reviewer_notes": sum(1 for item in clusters if item.reviewer_notes_available),
            "assignments_with_conflicts": sum(1 for item in clusters if item.conflicts),
            "relationship_count": len(relationships),
            "conflict_count": len(conflicts),
        }
        snapshot = AssignmentConsolidationSnapshot(
            snapshot_id=_snapshot_id(artifacts, relationships, conflicts),
            created_at=_now_iso(),
            clusters=clusters,
            artifacts=artifacts,
            relationships=relationships,
            conflicts=conflicts,
            unassigned_artifacts=[item.to_dict() for item in unassigned],
            aliases=aliases,
            merge_decisions=decisions,
            delta=delta,
            counts=counts,
            limitations=[
                "Assignment Consolidation uses exact IDs, normalized addresses, dates, and structured field overlap only.",
                "No semantic similarity, LLM inference, web retrieval, or valuation judgment is used.",
                "Conflicts are preserved explicitly and are not silently merged.",
            ],
        )
        self.store.save(snapshot)
        return snapshot

    def status(self) -> JsonMap:
        data = self.store.load()
        counts = _map(data.get("counts"))
        return {
            "available": bool(data),
            "assignment_count": counts.get("assignment_count", 0),
            "artifact_count": counts.get("artifact_count", 0),
            "knowledge_pack_count": counts.get("knowledge_pack_count", 0),
            "assignments_with_reviewer_notes": counts.get("assignments_with_reviewer_notes", 0),
            "assignments_with_conflicts": counts.get("assignments_with_conflicts", 0),
            "alias_count": counts.get("alias_count", 0),
            "source_companion_count": counts.get("source_companion_count", 0),
            "unassigned_artifact_count": counts.get("unassigned_artifact_count", 0),
            "true_identity_conflict_count": counts.get("true_identity_conflict_count", 0),
            "clusters_path": str(self.store.clusters_json),
        }


def normalize_address(value: str) -> str:
    text = _clean_text(value).lower()
    text = re.sub(r"#\s*([a-z0-9-]+)", r" unit \1", text)
    text = re.sub(r"\b(apt|apartment|ste|suite)\s+([a-z0-9-]+)", r"unit \2", text)
    text = re.sub(r"[^\w\s]", " ", text)
    replacements = {
        "street": "st",
        "avenue": "ave",
        "boulevard": "blvd",
        "drive": "dr",
        "road": "rd",
        "lane": "ln",
        "court": "ct",
        "place": "pl",
        "circle": "cir",
        "unit": "unit",
    }
    words = [replacements.get(word, word) for word in text.split()]
    return " ".join(words)


def _clean_text(value: str) -> str:
    text = html.unescape(str(value or "")).replace("\xa0", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"^[\s,.;:|/\\-]+|[\s,.;:|/\\-]+$", "", text)
    text = re.sub(r"[-_,;:|/\\]{2,}", " ", text)
    return text.strip()


def render_consolidation_markdown(snapshot: AssignmentConsolidationSnapshot) -> str:
    lines = [
        "# Real Estate Assignment Consolidation",
        "",
        f"Snapshot: `{snapshot.snapshot_id}`",
        f"Created: `{snapshot.created_at}`",
        "",
        "## Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in snapshot.counts.items())
    lines.extend(["", "## Assignment Clusters", ""])
    for cluster in snapshot.clusters:
        lines.append(f"- `{cluster.canonical_assignment_id}` property=`{cluster.property_address}` artifacts={cluster.artifact_count} status={cluster.assignment_status} evidence={cluster.evidence_count} last_activity=`{cluster.last_seen}`")
    lines.extend(["", "## Conflicts", ""])
    if snapshot.conflicts:
        lines.extend(f"- `{item.get('conflict_id')}` assignment=`{item.get('canonical_assignment_id')}` field=`{item.get('field')}` values=`{item.get('values')}`" for item in snapshot.conflicts)
    else:
        lines.append("- None")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in snapshot.limitations)
    lines.append("")
    return "\n".join(lines)


def render_unassigned_markdown(snapshot: AssignmentConsolidationSnapshot) -> str:
    lines = ["# Unassigned Real Estate Artifacts", ""]
    if not snapshot.unassigned_artifacts:
        lines.append("- None")
    for artifact in snapshot.unassigned_artifacts:
        lines.append(f"- `{artifact.get('artifact_id')}` type=`{artifact.get('artifact_type')}` source=`{artifact.get('source_path')}`")
    lines.append("")
    return "\n".join(lines)


def render_identity_report_markdown(snapshot: AssignmentConsolidationSnapshot) -> str:
    lines = [
        "# Real Estate Assignment Identity Resolution Report",
        "",
        "## Executive Summary",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in snapshot.counts.items())
    lines.extend(["", "## Canonical Assignments", ""])
    for cluster in snapshot.clusters:
        lines.append(f"- `{cluster.canonical_assignment_id}` aliases={len(cluster.assignment_aliases)} artifacts={cluster.artifact_count} property=`{cluster.property_address}`")
    lines.extend(["", "## Artifact Aliases", ""])
    if snapshot.aliases:
        lines.extend(f"- `{item.get('canonical_assignment_id')}` alias=`{item.get('alias')}` type={item.get('alias_type')}" for item in snapshot.aliases)
    else:
        lines.append("- None")
    lines.extend(["", "## Source Companion Relationships", ""])
    companions = [item for item in snapshot.relationships if item.relationship_type == "source_companion"]
    if companions:
        lines.extend(f"- `{item.relationship_id}` {item.artifact_a} <-> {item.artifact_b}: {item.reason}" for item in companions)
    else:
        lines.append("- None")
    lines.extend(["", "## True Identity Conflicts", ""])
    if snapshot.conflicts:
        lines.extend(f"- `{item.get('conflict_id')}` field=`{item.get('field')}` values=`{item.get('values')}`" for item in snapshot.conflicts)
    else:
        lines.append("- None")
    lines.extend(["", "## Unassigned Artifacts", ""])
    if snapshot.unassigned_artifacts:
        lines.extend(f"- `{item.get('artifact_id')}` source=`{item.get('source_path')}`" for item in snapshot.unassigned_artifacts)
    else:
        lines.append("- None")
    lines.extend(["", "## Address Normalization Summary", ""])
    for cluster in snapshot.clusters:
        if cluster.normalized_addresses:
            lines.append(f"- `{cluster.canonical_assignment_id}`: {', '.join(cluster.normalized_addresses)}")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in snapshot.limitations)
    lines.extend(["", "## Provenance", "", "- Generated from local Real Estate intake and assignment artifacts only.", ""])
    return "\n".join(lines)


def _intake_artifacts(root: Path) -> list[AssignmentArtifact]:
    artifacts: list[AssignmentArtifact] = []
    store = RealEstateIntakeStore(root)
    for manifest in store.history():
        for record in _map_list(manifest.get("records", [])):
            artifacts.append(_artifact_from_intake_record(record))
    try:
        for candidate in RealEstateIntakeEngine(root).scan():
            artifacts.append(
                AssignmentArtifact(
                    artifact_id=candidate.intake_id,
                    artifact_type=_artifact_type(candidate.source_path, candidate.source_id, candidate.structured_data),
                    source_path=candidate.source_path,
                    source_type=candidate.source_id,
                    assignment_id=_clean_text(str(candidate.structured_data.get("assignment_id") or "")),
                    order_id=_clean_text(str(candidate.structured_data.get("order_id") or "")),
                    loan_number=_clean_text(str(candidate.structured_data.get("loan_number") or "")),
                    property_address=_first(candidate.structured_data, ["subject_address", "property_address", "address"]),
                    normalized_address=normalize_address(_first(candidate.structured_data, ["subject_address", "property_address", "address"])),
                    city=_clean_text(str(candidate.structured_data.get("city") or "")),
                    state=_clean_text(str(candidate.structured_data.get("state") or "")),
                    client=_first(candidate.structured_data, ["client_name", "client"]),
                    lender=_clean_text(str(candidate.structured_data.get("lender") or "")),
                    amc=_clean_text(str(candidate.structured_data.get("amc") or "")),
                    effective_date=normalize_date(candidate.structured_data.get("effective_date") or ""),
                    imported_at="",
                    source_stem=_source_stem(candidate.source_path),
                    source_generated_alias=candidate.detected_assignment_id,
                    address_derived_alias=_address_alias(candidate.structured_data),
                    hash_fallback_alias=f"hash-{_digest(candidate.source_path)}",
                    provenance={"source": "intake_scan", "fields": candidate.structured_data},
                )
            )
    except Exception:
        pass
    return artifacts


def _artifact_from_intake_record(record: JsonMap) -> AssignmentArtifact:
    path = str(record.get("source_path") or "")
    fields = _load_source_fields(path)
    assignment_id = _clean_text(str(fields.get("assignment_id") or ""))
    return AssignmentArtifact(
        artifact_id=str(record.get("intake_id") or f"artifact_{_digest(path)}"),
        artifact_type=_artifact_type(path, str(record.get("source_id") or ""), fields),
        source_path=path,
        source_type=str(record.get("source_id") or ""),
        assignment_id=assignment_id,
        order_id=_clean_text(str(fields.get("order_id") or "")),
        loan_number=_clean_text(str(fields.get("loan_number") or "")),
        property_address=_first(fields, ["subject_address", "property_address", "address"]),
        normalized_address=normalize_address(_first(fields, ["subject_address", "property_address", "address"])),
        city=_clean_text(str(fields.get("city") or "")),
        state=_clean_text(str(fields.get("state") or "")),
        client=_first(fields, ["client_name", "client"]),
        lender=_clean_text(str(fields.get("lender") or "")),
        amc=_clean_text(str(fields.get("amc") or "")),
        effective_date=normalize_date(fields.get("effective_date") or ""),
        imported_at=str(record.get("imported_at") or ""),
        source_stem=_source_stem(path),
        source_generated_alias=str(record.get("detected_assignment_id") or ""),
        address_derived_alias=_address_alias(fields),
        hash_fallback_alias=f"hash-{_digest(path)}",
        provenance={"source": "intake_history", "record": record, "fields": fields},
    )


def _assignment_artifacts(root: Path) -> list[AssignmentArtifact]:
    artifacts = []
    store = RealEstateAssignmentStore(root)
    for assignment_id in store.list_assignment_ids():
        path = store.assignment_root() / assignment_id / "assignment.yaml"
        try:
            data = _map(__import__("constellation.simple_yaml", fromlist=["load_yaml"]).load_yaml(path).get("assignment"))
        except Exception:
            data = {}
        subject = _map(data.get("subject"))
        artifacts.append(
            AssignmentArtifact(
                artifact_id=f"assignment_{_digest(str(path))}",
                artifact_type="assignment_yaml",
                source_path=str(path),
                source_type="assignment",
                assignment_id=str(data.get("assignment_id") or assignment_id),
                order_id="",
                loan_number="",
                property_address=str(subject.get("address") or ""),
                normalized_address=normalize_address(str(subject.get("address") or "")),
                city=str(subject.get("city") or ""),
                state=str(subject.get("state") or ""),
                client=str(data.get("client_name") or ""),
                lender="",
                amc="",
                effective_date=normalize_date(data.get("effective_date") or ""),
                imported_at=str(data.get("created_at") or ""),
                source_stem=_source_stem(str(path)),
                source_generated_alias=assignment_id,
                address_derived_alias=_address_alias(subject),
                hash_fallback_alias=f"hash-{_digest(str(path))}",
                provenance={"source": "assignment_yaml"},
            )
        )
    return artifacts


def _relationships(artifacts: list[AssignmentArtifact]) -> list[AssignmentRelationship]:
    relationships = []
    for index, a in enumerate(artifacts):
        for b in artifacts[index + 1 :]:
            relationship_type, confidence, reason = _relationship(a, b)
            if relationship_type == "unrelated":
                continue
            relationships.append(
                AssignmentRelationship(
                    relationship_id=f"relationship_{_digest('|'.join(sorted([a.artifact_id, b.artifact_id])) + relationship_type)}",
                    artifact_a=a.artifact_id,
                    artifact_b=b.artifact_id,
                    relationship_type=relationship_type,
                    confidence=confidence,
                    reason=reason,
                )
            )
    return sorted(relationships, key=lambda item: item.relationship_id)


def _relationship(a: AssignmentArtifact, b: AssignmentArtifact) -> tuple[str, str, str]:
    if a.source_stem and b.source_stem and a.source_stem == b.source_stem:
        return "source_companion", "deterministic_high", "exact_source_stem_match"
    strong_conflict = _strong_id_conflict(a, b)
    if strong_conflict:
        return "conflicting_assignment", "deterministic_high", strong_conflict
    for field in ["assignment_id", "order_id", "loan_number"]:
        av = getattr(a, field)
        bv = getattr(b, field)
        if av and bv and av == bv:
            return "same_assignment", "deterministic_high", f"matching {field}"
    if a.normalized_address and b.normalized_address and a.normalized_address == b.normalized_address:
        if not _compatible_location(a, b):
            return "conflicting_assignment", "deterministic_high", "same normalized address with incompatible city/state"
        if a.effective_date and b.effective_date and a.effective_date != b.effective_date:
            return "possible_duplicate", "deterministic_medium", "matching normalized address with different effective dates"
        return "same_assignment", "deterministic_medium", "matching normalized property address"
    overlap = _structured_overlap(a, b)
    if overlap >= 4:
        return "possible_duplicate", "deterministic_low", f"structured field overlap={overlap}"
    return "unrelated", "deterministic_low", "no deterministic relationship"


def _strong_id_conflict(a: AssignmentArtifact, b: AssignmentArtifact) -> str:
    if a.order_id and b.order_id and a.order_id != b.order_id:
        return "conflicting explicit order_id"
    if a.loan_number and b.loan_number and a.loan_number != b.loan_number:
        return "conflicting explicit loan_number"
    if a.assignment_id and b.assignment_id and a.assignment_id != b.assignment_id and not _shared_stronger_identity(a, b):
        return "conflicting explicit assignment_id"
    return ""


def _shared_stronger_identity(a: AssignmentArtifact, b: AssignmentArtifact) -> bool:
    return bool((a.order_id and a.order_id == b.order_id) or (a.loan_number and a.loan_number == b.loan_number))


def _compatible_location(a: AssignmentArtifact, b: AssignmentArtifact) -> bool:
    for field in ["city", "state"]:
        av = _clean_text(str(getattr(a, field)))
        bv = _clean_text(str(getattr(b, field)))
        if av and bv and av.lower() != bv.lower():
            return False
    return True


def _clusters(artifacts: list[AssignmentArtifact], relationships: list[AssignmentRelationship], root: Path) -> tuple[list[AssignmentCluster], list[AssignmentMergeDecision], list[JsonMap], list[AssignmentArtifact]]:
    parent = {item.artifact_id: item.artifact_id for item in artifacts}

    def find(x: str) -> str:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    def union(a: str, b: str) -> None:
        ra, rb = find(a), find(b)
        if ra != rb:
            parent[rb] = ra

    for relationship in relationships:
        if relationship.relationship_type in {"same_assignment", "source_companion"}:
            union(relationship.artifact_a, relationship.artifact_b)
    by_root: dict[str, list[AssignmentArtifact]] = {}
    for artifact in artifacts:
        by_root.setdefault(find(artifact.artifact_id), []).append(artifact)
    rel_by_artifact: dict[str, list[str]] = {}
    for relationship in relationships:
        rel_by_artifact.setdefault(relationship.artifact_a, []).append(relationship.relationship_id)
        rel_by_artifact.setdefault(relationship.artifact_b, []).append(relationship.relationship_id)
    clusters = []
    decisions = []
    all_conflicts = []
    unassigned = []
    for items in by_root.values():
        if not _cluster_has_identity(items):
            unassigned.extend(items)
            continue
        canonical = _canonical_id(items)
        conflicts = _conflicts(canonical, items)
        all_conflicts.extend(conflicts)
        assignment_data = _assignment_output(root, canonical)
        identifiers = _cluster_identifiers(items)
        cluster = AssignmentCluster(
            canonical_assignment_id=canonical,
            artifact_count=len(items),
            source_types=sorted({item.artifact_type for item in items}),
            first_seen=min([item.imported_at for item in items if item.imported_at] or [""]),
            last_seen=max([item.imported_at for item in items if item.imported_at] or [""]),
            assignment_status=str(assignment_data.get("status") or "unknown"),
            property_address=_choose(items, "property_address"),
            city=_choose(items, "city"),
            state=_choose(items, "state"),
            client=_choose(items, "client"),
            lender=_choose(items, "lender"),
            amc=_choose(items, "amc"),
            assignment_aliases=identifiers["assignment_aliases"],
            explicit_assignment_ids=identifiers["explicit_assignment_ids"],
            order_ids=identifiers["order_ids"],
            loan_numbers=identifiers["loan_numbers"],
            source_generated_ids=identifiers["source_generated_ids"],
            normalized_addresses=identifiers["normalized_addresses"],
            canonical_identifiers=identifiers["canonical_identifiers"],
            identity_sources=identifiers["identity_sources"],
            evidence_count=int(assignment_data.get("fact_count") or 0),
            knowledge_pack_available=any(item.artifact_type == "knowledge_pack" for item in items),
            reviewer_notes_available=any(item.artifact_type in {"review_markdown", "review_json"} for item in items),
            conflicts=conflicts,
            artifacts=[item.to_dict() for item in sorted(items, key=lambda artifact: artifact.artifact_id)],
            relationships=sorted({rel for item in items for rel in rel_by_artifact.get(item.artifact_id, [])}),
            provenance={"rule": "deterministic_assignment_consolidation"},
        )
        clusters.append(cluster)
        for item in items:
            decisions.append(AssignmentMergeDecision(item.artifact_id, canonical, "assigned_to_cluster", "deterministic relationship rules"))
    return sorted(clusters, key=lambda item: item.canonical_assignment_id), sorted(decisions, key=lambda item: item.artifact_id), sorted(all_conflicts, key=lambda item: item["conflict_id"]), sorted(unassigned, key=lambda item: item.artifact_id)


def _conflicts(canonical: str, artifacts: list[AssignmentArtifact]) -> list[JsonMap]:
    conflicts = []
    for field in ["property_address", "assignment_id", "order_id", "loan_number"]:
        values = sorted({str(getattr(item, field)) for item in artifacts if str(getattr(item, field))})
        normalized = sorted({normalize_address(value) if field == "property_address" else value for value in values})
        if field == "assignment_id" and _shared_cluster_stronger_identity(artifacts):
            continue
        if len(normalized) > 1:
            conflicts.append(
                {
                    "conflict_id": f"assignment_conflict_{_digest(canonical + field + '|'.join(normalized))}",
                    "canonical_assignment_id": canonical,
                    "field": field,
                    "values": values,
                    "status": "open",
                    "provenance": {"rule": "conflicting_structured_assignment_fields"},
                }
            )
    return conflicts


def _cluster_has_identity(items: list[AssignmentArtifact]) -> bool:
    return any(item.assignment_id or item.order_id or item.loan_number or item.normalized_address for item in items)


def _cluster_identifiers(items: list[AssignmentArtifact]) -> JsonMap:
    explicit_assignment_ids = sorted({item.assignment_id for item in items if item.assignment_id})
    order_ids = sorted({item.order_id for item in items if item.order_id})
    loan_numbers = sorted({item.loan_number for item in items if item.loan_number})
    source_generated_ids = sorted({item.source_generated_alias for item in items if item.source_generated_alias})
    address_aliases = sorted({item.address_derived_alias for item in items if item.address_derived_alias})
    hash_aliases = sorted({item.hash_fallback_alias for item in items if item.hash_fallback_alias})
    normalized_addresses = sorted({item.normalized_address for item in items if item.normalized_address})
    aliases = sorted(set(explicit_assignment_ids + order_ids + loan_numbers + source_generated_ids + address_aliases + hash_aliases + normalized_addresses))
    return {
        "assignment_aliases": aliases,
        "explicit_assignment_ids": explicit_assignment_ids,
        "order_ids": order_ids,
        "loan_numbers": loan_numbers,
        "source_generated_ids": source_generated_ids,
        "normalized_addresses": normalized_addresses,
        "canonical_identifiers": {
            "explicit_assignment_id": explicit_assignment_ids[0] if explicit_assignment_ids else None,
            "explicit_order_id": order_ids[0] if order_ids else None,
            "explicit_loan_number": loan_numbers[0] if loan_numbers else None,
            "address_derived_alias": address_aliases[0] if address_aliases else None,
            "source_generated_alias": source_generated_ids[0] if source_generated_ids else None,
            "hash_fallback_alias": hash_aliases[0] if hash_aliases else None,
        },
        "identity_sources": [
            {
                "artifact_id": item.artifact_id,
                "explicit_assignment_id": item.assignment_id,
                "order_id": item.order_id,
                "loan_number": item.loan_number,
                "source_generated_alias": item.source_generated_alias,
                "address_derived_alias": item.address_derived_alias,
            }
            for item in items
        ],
    }


def _aliases(clusters: list[AssignmentCluster]) -> list[JsonMap]:
    rows = []
    for cluster in clusters:
        for alias in cluster.assignment_aliases:
            rows.append({"canonical_assignment_id": cluster.canonical_assignment_id, "alias": alias, "alias_type": _alias_type(alias, cluster)})
    return sorted(rows, key=lambda item: (str(item["canonical_assignment_id"]), str(item["alias"])))


def _alias_type(alias: str, cluster: AssignmentCluster) -> str:
    if alias in cluster.explicit_assignment_ids:
        return "explicit_assignment_id"
    if alias in cluster.order_ids:
        return "explicit_order_id"
    if alias in cluster.loan_numbers:
        return "explicit_loan_number"
    if alias in cluster.source_generated_ids:
        return "source_generated_alias"
    if alias in cluster.normalized_addresses:
        return "normalized_address"
    if alias.startswith("hash-"):
        return "hash_fallback_alias"
    return "address_derived_alias"


def _shared_cluster_stronger_identity(artifacts: list[AssignmentArtifact]) -> bool:
    order_ids = {item.order_id for item in artifacts if item.order_id}
    loan_numbers = {item.loan_number for item in artifacts if item.loan_number}
    return len(order_ids) == 1 or len(loan_numbers) == 1


def _delta(previous: JsonMap, clusters: list[AssignmentCluster], relationships: list[AssignmentRelationship], conflicts: list[JsonMap], unassigned: list[AssignmentArtifact], aliases: list[JsonMap]) -> JsonMap:
    prev_clusters = {str(item.get("canonical_assignment_id")) for item in _map_list(previous.get("clusters", []))}
    cur_clusters = {item.canonical_assignment_id for item in clusters}
    prev_artifacts = {str(artifact.get("artifact_id")) for cluster in _map_list(previous.get("clusters", [])) for artifact in _map_list(cluster.get("artifacts", []))}
    cur_artifacts = {str(artifact.get("artifact_id")) for cluster in clusters for artifact in cluster.artifacts}
    prev_conflicts = {str(item.get("conflict_id")) for item in _map_list(previous.get("conflicts", []))}
    cur_conflicts = {str(item.get("conflict_id")) for item in conflicts}
    prev_relationships = {str(item.get("relationship_id")) for item in _map_list(previous.get("relationships", []))}
    cur_relationships = {item.relationship_id for item in relationships}
    prev_unassigned = {str(item.get("artifact_id")) for item in _map_list(previous.get("unassigned_artifacts", []))}
    cur_unassigned = {item.artifact_id for item in unassigned}
    prev_aliases = {str(item.get("canonical_assignment_id")) + "|" + str(item.get("alias")) for item in _map_list(previous.get("aliases", []))}
    cur_aliases = {str(item.get("canonical_assignment_id")) + "|" + str(item.get("alias")) for item in aliases}
    return {
        "newly_merged_artifacts": sorted(cur_artifacts - prev_artifacts),
        "newly_split_assignments": sorted(prev_clusters - cur_clusters),
        "new_conflicts": sorted(cur_conflicts - prev_conflicts),
        "resolved_conflicts": sorted(prev_conflicts - cur_conflicts),
        "new_relationships": sorted(cur_relationships - prev_relationships),
        "newly_resolved_aliases": sorted(cur_aliases - prev_aliases),
        "newly_attached_companions": sorted(item.relationship_id for item in relationships if item.relationship_type == "source_companion"),
        "newly_unassigned_artifacts": sorted(cur_unassigned - prev_unassigned),
        "new_identity_conflicts": sorted(cur_conflicts - prev_conflicts),
        "resolved_identity_conflicts": sorted(prev_conflicts - cur_conflicts),
        "newly_merged_clusters": sorted(cur_clusters - prev_clusters),
        "split_clusters": sorted(prev_clusters - cur_clusters),
    }


def _dedupe_artifacts(artifacts: list[AssignmentArtifact]) -> list[AssignmentArtifact]:
    by_id = {}
    for item in artifacts:
        key = item.source_path or item.artifact_id
        by_id[key] = item
    return [by_id[key] for key in sorted(by_id)]


def _artifact_type(path: str, source_type: str, fields: JsonMap) -> str:
    text = " ".join([path, source_type, str(fields.get("source_type") or "")]).lower()
    if "knowledge" in text or "pack" in text:
        return "knowledge_pack"
    if "gmail" in text:
        return "gmail_intake_json"
    if "axis" in text:
        return "axis_intake_json"
    if "review" in text and path.lower().endswith(".json"):
        return "review_json"
    if "review" in text:
        return "review_markdown"
    if path.lower().endswith((".yaml", ".yml")):
        return "structured_intake_yaml"
    if path.lower().endswith(".md"):
        return "assignment_markdown"
    return "structured_intake_json" if path.lower().endswith(".json") else "future_connector"


def _load_source_fields(path: str) -> JsonMap:
    source = Path(path)
    if not source.exists():
        return {}
    try:
        if source.suffix.lower() == ".json":
            data = json.loads(source.read_text(encoding="utf-8"))
        elif source.suffix.lower() in {".yaml", ".yml"}:
            from .simple_yaml import load_yaml

            data = load_yaml(source)
        else:
            data = _parse_labeled(source.read_text(encoding="utf-8"))
    except Exception:
        return {}
    if isinstance(data, dict):
        child = data.get("assignment") or data.get("order") or data.get("intake")
        if isinstance(child, dict):
            merged = data.copy()
            merged.update(child)
            return merged
        return data
    return {}


def _parse_labeled(text: str) -> JsonMap:
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            text = parts[1]
    data: JsonMap = {}
    for line in text.splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            data[_normalize_key(key)] = value.strip()
    return data


def _canonical_id(items: list[AssignmentArtifact]) -> str:
    for field in ["assignment_id", "order_id", "loan_number"]:
        values = sorted({str(getattr(item, field)) for item in items if str(getattr(item, field))})
        if values:
            return _safe_id(values[0])
    address_dates = sorted({f"{item.normalized_address}-{item.effective_date}" for item in items if item.normalized_address and item.effective_date})
    if address_dates:
        return _safe_id(address_dates[0])
    addresses = sorted({item.normalized_address for item in items if item.normalized_address})
    if addresses:
        return _safe_id(addresses[0])
    source_aliases = sorted({item.source_generated_alias for item in items if item.source_generated_alias})
    if source_aliases:
        return _safe_id(source_aliases[0])
    hash_aliases = sorted({item.hash_fallback_alias for item in items if item.hash_fallback_alias})
    return _safe_id(hash_aliases[0]) if hash_aliases else f"assignment-{_digest('|'.join(item.artifact_id for item in items))}"


def _assignment_output(root: Path, assignment_id: str) -> JsonMap:
    try:
        return RealEstateAssignmentStore(root).load(assignment_id)
    except Exception:
        return {}


def _structured_overlap(a: AssignmentArtifact, b: AssignmentArtifact) -> int:
    count = 0
    for field in ["property_address", "city", "state", "client", "lender", "amc", "effective_date"]:
        av = str(getattr(a, field))
        bv = str(getattr(b, field))
        if av and bv and av == bv:
            count += 1
    return count


def _choose(items: list[AssignmentArtifact], field: str) -> str:
    values = [str(getattr(item, field)) for item in items if str(getattr(item, field))]
    return sorted(values, key=lambda value: (-len(value), value))[0] if values else ""


def _first(data: JsonMap, keys: list[str]) -> str:
    for key in keys:
        value = data.get(key)
        if value:
            return _clean_text(str(value))
    return ""


def _source_stem(path: str) -> str:
    stem = Path(path).stem.lower()
    stem = re.sub(r"-(incoming|review|artifact|intake)$", "", stem)
    return stem


def _address_alias(data: JsonMap) -> str:
    address = _first(data, ["subject_address", "property_address", "address"])
    effective = normalize_date(data.get("effective_date") or data.get("due_date") or "")
    if address and effective:
        return _safe_id(f"{normalize_address(address)}-{effective}")
    if address:
        return _safe_id(normalize_address(address))
    return ""


def _normalize_key(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


def _safe_id(value: str) -> str:
    text = value.lower().strip()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "assignment"


def _snapshot_id(artifacts: list[AssignmentArtifact], relationships: list[AssignmentRelationship], conflicts: list[JsonMap]) -> str:
    payload = "|".join([*(item.artifact_id for item in artifacts), *(item.relationship_id for item in relationships), *(str(item.get("conflict_id")) for item in conflicts)])
    return f"assignment_consolidation_{_digest(payload)}"


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:16]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _map(value: Any) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _map_list(value: Any) -> list[JsonMap]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []
