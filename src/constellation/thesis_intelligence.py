from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .cross_document import CrossDocumentAnalysisStore, CrossDocumentError
from .evidence_graph import EvidenceGraphError, EvidenceGraphStore
from .io import read_json, write_json
from .knowledge_graph import KnowledgeGraphStore
from .memory import InstitutionalMemoryError, InstitutionalMemoryStore
from .models import JsonMap, utc_now_iso
from .morning import MorningExecutiveError, MorningExecutiveStore
from .thesis import ThesisError, ThesisStore as GeneratedThesisStore


class ThesisIntelligenceError(RuntimeError):
    pass


VALID_STATUSES = {"active", "strengthening", "weakening", "archived"}
VALID_CONFIDENCE = {"low", "medium", "high"}


@dataclass(frozen=True)
class ThesisEvidence:
    thesis_id: str
    evidence_id: str
    relationship: str
    source: str
    reason: str

    def to_dict(self) -> JsonMap:
        return {
            "thesis_id": self.thesis_id,
            "evidence_id": self.evidence_id,
            "relationship": self.relationship,
            "source": self.source,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ThesisConflict:
    thesis_id: str
    evidence_id: str
    finding_id: str | None
    source: str
    reason: str

    def to_dict(self) -> JsonMap:
        return {
            "thesis_id": self.thesis_id,
            "evidence_id": self.evidence_id,
            "finding_id": self.finding_id,
            "source": self.source,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ThesisConfidence:
    label: str
    support_count: int
    conflict_count: int
    repeated_confirmation_count: int
    explicit_contradiction_count: int
    rule: str

    def __post_init__(self) -> None:
        if self.label not in VALID_CONFIDENCE:
            raise ThesisIntelligenceError(f"Unsupported thesis confidence: {self.label}")

    def to_dict(self) -> JsonMap:
        return {
            "label": self.label,
            "support_count": self.support_count,
            "conflict_count": self.conflict_count,
            "repeated_confirmation_count": self.repeated_confirmation_count,
            "explicit_contradiction_count": self.explicit_contradiction_count,
            "rule": self.rule,
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "ThesisConfidence":
        return cls(
            label=_require_str(data, "label"),
            support_count=_int(data.get("support_count")),
            conflict_count=_int(data.get("conflict_count")),
            repeated_confirmation_count=_int(data.get("repeated_confirmation_count")),
            explicit_contradiction_count=_int(data.get("explicit_contradiction_count")),
            rule=_require_str(data, "rule"),
        )


@dataclass(frozen=True)
class ThesisTimeline:
    thesis_id: str
    timestamp: str
    event_type: str
    reason: str
    affected_evidence_ids: list[str]

    def to_dict(self) -> JsonMap:
        return {
            "thesis_id": self.thesis_id,
            "timestamp": self.timestamp,
            "event_type": self.event_type,
            "reason": self.reason,
            "affected_evidence_ids": self.affected_evidence_ids,
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "ThesisTimeline":
        return cls(
            thesis_id=_require_str(data, "thesis_id"),
            timestamp=_require_str(data, "timestamp"),
            event_type=_require_str(data, "event_type"),
            reason=_require_str(data, "reason"),
            affected_evidence_ids=_string_list(data.get("affected_evidence_ids", [])),
        )


@dataclass(frozen=True)
class ThesisRecord:
    thesis_id: str
    title: str
    category: str
    created_at: str
    updated_at: str
    status: str
    supporting_evidence_ids: list[str]
    conflicting_evidence_ids: list[str]
    finding_ids: list[str]
    source_ids: list[str]
    memory_snapshot_ids: list[str]
    morning_brief_ids: list[str]
    confidence: ThesisConfidence
    metadata: JsonMap

    def __post_init__(self) -> None:
        if self.status not in VALID_STATUSES:
            raise ThesisIntelligenceError(f"Unsupported thesis status: {self.status}")

    def to_dict(self) -> JsonMap:
        return {
            "thesis_id": self.thesis_id,
            "title": self.title,
            "category": self.category,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "status": self.status,
            "supporting_evidence_ids": self.supporting_evidence_ids,
            "conflicting_evidence_ids": self.conflicting_evidence_ids,
            "finding_ids": self.finding_ids,
            "source_ids": self.source_ids,
            "memory_snapshot_ids": self.memory_snapshot_ids,
            "morning_brief_ids": self.morning_brief_ids,
            "confidence": self.confidence.to_dict(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "ThesisRecord":
        return cls(
            thesis_id=_require_str(data, "thesis_id"),
            title=_require_str(data, "title"),
            category=_require_str(data, "category"),
            created_at=_require_str(data, "created_at"),
            updated_at=_require_str(data, "updated_at"),
            status=_require_str(data, "status"),
            supporting_evidence_ids=_string_list(data.get("supporting_evidence_ids", [])),
            conflicting_evidence_ids=_string_list(data.get("conflicting_evidence_ids", [])),
            finding_ids=_string_list(data.get("finding_ids", [])),
            source_ids=_string_list(data.get("source_ids", [])),
            memory_snapshot_ids=_string_list(data.get("memory_snapshot_ids", [])),
            morning_brief_ids=_string_list(data.get("morning_brief_ids", [])),
            confidence=ThesisConfidence.from_dict(_map(data.get("confidence"))),
            metadata=_map(data.get("metadata")),
        )


class ThesisEngine:
    def __init__(self, root: Path) -> None:
        self.root = root

    def build(self, previous: list[ThesisRecord] | None = None) -> tuple[list[ThesisRecord], list[ThesisTimeline]]:
        now = utc_now_iso()
        previous_by_id = {record.thesis_id: record for record in previous or []}
        generated = _read_generated_theses(self.root)
        findings = _read_findings(self.root)
        evidence_graph = _read_evidence_graph(self.root)
        knowledge_graph = KnowledgeGraphStore(self.root).load()
        morning = _read_morning(self.root)
        snapshots = _read_snapshots(self.root)
        thesis_ids = sorted(set(generated) | _thesis_ids_from_evidence_graph(evidence_graph))
        records: list[ThesisRecord] = []
        timeline: list[ThesisTimeline] = []
        for thesis_id in thesis_ids:
            base = generated.get(thesis_id, {})
            support_ids = _supporting_evidence_ids(thesis_id, base, evidence_graph)
            conflict_ids = _conflicting_evidence_ids(thesis_id, base, findings, evidence_graph)
            finding_ids = _finding_ids(thesis_id, base, evidence_graph)
            source_ids = _source_ids(base, findings, finding_ids, knowledge_graph)
            memory_snapshot_ids = _memory_snapshot_ids(thesis_id, snapshots, evidence_graph)
            morning_brief_ids = _morning_brief_ids(thesis_id, morning, evidence_graph)
            confidence = _confidence(support_ids, conflict_ids, findings, finding_ids)
            previous_record = previous_by_id.get(thesis_id)
            status = _status(previous_record, support_ids, conflict_ids, confidence)
            created_at = previous_record.created_at if previous_record else now
            title = str(base.get("title") or _label_from_evidence_graph(thesis_id, evidence_graph) or thesis_id)
            record = ThesisRecord(
                thesis_id=thesis_id,
                title=title,
                category=str(base.get("thesis_type") or _map(_graph_node(thesis_id, evidence_graph)).get("metadata", {}).get("thesis_type") or "uncategorized"),
                created_at=created_at,
                updated_at=now,
                status=status,
                supporting_evidence_ids=support_ids,
                conflicting_evidence_ids=conflict_ids,
                finding_ids=finding_ids,
                source_ids=source_ids,
                memory_snapshot_ids=memory_snapshot_ids,
                morning_brief_ids=morning_brief_ids,
                confidence=confidence,
                metadata={
                    "source": "ThesisEngine",
                    "deterministic": True,
                    "generated_thesis_present": thesis_id in generated,
                    "knowledge_graph_node_count": len(knowledge_graph.nodes),
                },
            )
            records.append(record)
            timeline.extend(_timeline_events(previous_record, record, now))
        archived = set(previous_by_id) - set(thesis_ids)
        for thesis_id in sorted(archived):
            prior = previous_by_id[thesis_id]
            record = ThesisRecord(
                thesis_id=prior.thesis_id,
                title=prior.title,
                category=prior.category,
                created_at=prior.created_at,
                updated_at=now,
                status="archived",
                supporting_evidence_ids=prior.supporting_evidence_ids,
                conflicting_evidence_ids=prior.conflicting_evidence_ids,
                finding_ids=prior.finding_ids,
                source_ids=prior.source_ids,
                memory_snapshot_ids=prior.memory_snapshot_ids,
                morning_brief_ids=prior.morning_brief_ids,
                confidence=prior.confidence,
                metadata={**prior.metadata, "archive_reason": "Thesis no longer appears in local thesis or evidence graph outputs."},
            )
            records.append(record)
            timeline.append(
                ThesisTimeline(
                    thesis_id=thesis_id,
                    timestamp=now,
                    event_type="archived",
                    reason="Thesis no longer appears in local thesis or evidence graph outputs.",
                    affected_evidence_ids=[],
                )
            )
        return sorted(records, key=lambda item: (item.status, item.title, item.thesis_id)), timeline


class ThesisStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "outputs" / "thesis"
        self.theses_path = self.directory / "theses.json"
        self.history_path = self.directory / "thesis-history.json"
        self.markdown_path = self.directory / "thesis-report.md"

    def build(self) -> list[ThesisRecord]:
        previous = self.list() if self.theses_path.exists() else []
        prior_history = self.timeline()
        records, events = ThesisEngine(self.root).build(previous)
        write_json(self.theses_path, {"schema_version": "3.6.0", "created_at": utc_now_iso(), "theses": [record.to_dict() for record in records]})
        write_json(self.history_path, {"schema_version": "3.6.0", "events": [event.to_dict() for event in [*prior_history, *events]]})
        self.export(records)
        return records

    def list(self) -> list[ThesisRecord]:
        if not self.theses_path.exists():
            raise ThesisIntelligenceError("No thesis intelligence records found. Run thesis build first.")
        data = read_json(self.theses_path)
        return [ThesisRecord.from_dict(item) for item in _map_list(data.get("theses", []))]

    def show(self, thesis_id: str) -> ThesisRecord:
        for record in self.list():
            if record.thesis_id == thesis_id:
                return record
        raise ThesisIntelligenceError(f"Unknown thesis intelligence record: {thesis_id}")

    def timeline(self, thesis_id: str | None = None) -> list[ThesisTimeline]:
        if not self.history_path.exists():
            return []
        data = read_json(self.history_path)
        events = [ThesisTimeline.from_dict(item) for item in _map_list(data.get("events", []))]
        if thesis_id is not None:
            events = [event for event in events if event.thesis_id == thesis_id]
        return sorted(events, key=lambda item: (item.timestamp, item.thesis_id, item.event_type))

    def export(self, records: list[ThesisRecord] | None = None) -> Path:
        records = records if records is not None else self.list()
        self.markdown_path.parent.mkdir(parents=True, exist_ok=True)
        self.markdown_path.write_text(render_thesis_report(records, self.timeline()), encoding="utf-8")
        return self.markdown_path


def render_thesis_report(records: list[ThesisRecord], timeline: list[ThesisTimeline]) -> str:
    by_status = {status: [record for record in records if record.status == status] for status in sorted(VALID_STATUSES)}
    lines = [
        "# Thesis Intelligence",
        "",
        "## Summary",
        "",
        f"- Theses: {len(records)}",
        f"- Supporting relationships: {sum(len(record.supporting_evidence_ids) for record in records)}",
        f"- Conflicts: {sum(len(record.conflicting_evidence_ids) for record in records)}",
        "",
        "## Active Theses",
        "",
        *_record_lines(by_status["active"]),
        "## Strengthening Theses",
        "",
        *_record_lines(by_status["strengthening"]),
        "## Weakening Theses",
        "",
        *_record_lines(by_status["weakening"]),
        "## Archived Theses",
        "",
        *_record_lines(by_status["archived"]),
        "## Recent Timeline Events",
        "",
        *_timeline_lines(timeline[-10:]),
        "## Morning Brief References",
        "",
        *_reference_lines(records, "morning_brief_ids"),
        "## Memory Snapshot References",
        "",
        *_reference_lines(records, "memory_snapshot_ids"),
        "## Limitations",
        "",
        "- Confidence is deterministic, rule-based, and not probabilistic.",
        "- The engine consumes existing local artifacts only.",
        "- No AI, LLM, embedding, semantic similarity, provider, web, or Gmail calls are used.",
        "- Relationships absent from exact IDs or explicit records are omitted.",
    ]
    return "\n".join(lines)


def _read_generated_theses(root: Path) -> dict[str, JsonMap]:
    try:
        return {thesis.thesis_id: thesis.to_dict() for thesis in GeneratedThesisStore(root).load()}
    except ThesisError:
        return {}


def _read_findings(root: Path) -> dict[str, JsonMap]:
    try:
        return {finding.finding_id: finding.to_dict() for finding in CrossDocumentAnalysisStore(root).list_findings()}
    except CrossDocumentError:
        return {}


def _read_evidence_graph(root: Path) -> JsonMap:
    try:
        return EvidenceGraphStore(root).load().to_dict()
    except EvidenceGraphError:
        return {"nodes": [], "edges": []}


def _read_morning(root: Path) -> JsonMap | None:
    try:
        return MorningExecutiveStore(root).load().to_dict()
    except MorningExecutiveError:
        return None


def _read_snapshots(root: Path) -> list[JsonMap]:
    try:
        return [snapshot.to_dict() for snapshot in InstitutionalMemoryStore(root).list_snapshots()]
    except InstitutionalMemoryError:
        return []


def _thesis_ids_from_evidence_graph(graph: JsonMap) -> set[str]:
    ids = set()
    for node in _map_list(graph.get("nodes", [])):
        if node.get("node_type") == "thesis":
            for reference in _string_list(node.get("references", [])):
                ids.add(reference)
    return ids


def _supporting_evidence_ids(thesis_id: str, base: JsonMap, graph: JsonMap) -> list[str]:
    ids = set(_string_list(base.get("supporting_evidence_ids", [])))
    thesis_node = f"eg_thesis_{thesis_id}"
    for edge in _map_list(graph.get("edges", [])):
        if edge.get("target_node_id") == thesis_node and edge.get("edge_type") == "supports":
            ids.update(_string_list(edge.get("evidence_ids", [])))
    return sorted(ids)


def _conflicting_evidence_ids(thesis_id: str, base: JsonMap, findings: dict[str, JsonMap], graph: JsonMap) -> list[str]:
    ids = set()
    for finding_id in _string_list(base.get("counterpoint_finding_ids", [])):
        ids.update(_string_list(_map(findings.get(finding_id)).get("evidence_ids", [])))
    thesis_node = f"eg_thesis_{thesis_id}"
    for edge in _map_list(graph.get("edges", [])):
        if edge.get("target_node_id") == thesis_node and edge.get("edge_type") == "conflicts_with":
            ids.update(_string_list(edge.get("evidence_ids", [])))
    for finding in findings.values():
        if finding.get("finding_type") == "possible_contradiction" and thesis_id in _string_list(finding.get("metadata", {}).get("thesis_ids", [])):
            ids.update(_string_list(finding.get("evidence_ids", [])))
    return sorted(ids)


def _finding_ids(thesis_id: str, base: JsonMap, graph: JsonMap) -> list[str]:
    ids = set(_string_list(base.get("supporting_finding_ids", [])))
    ids.update(_string_list(base.get("counterpoint_finding_ids", [])))
    thesis_node = f"eg_thesis_{thesis_id}"
    for edge in _map_list(graph.get("edges", [])):
        if edge.get("target_node_id") == thesis_node and str(edge.get("source_node_id", "")).startswith("eg_finding_"):
            ids.add(str(edge["source_node_id"]).removeprefix("eg_finding_"))
    return sorted(ids)


def _source_ids(base: JsonMap, findings: dict[str, JsonMap], finding_ids: list[str], knowledge_graph) -> list[str]:
    ids = set(_string_list(base.get("source_ids", [])))
    for finding_id in finding_ids:
        ids.update(_string_list(_map(findings.get(finding_id)).get("source_ids", [])))
    for node in knowledge_graph.nodes.values():
        if set(node.evidence_ids) & set(_string_list(base.get("supporting_evidence_ids", []))):
            ids.update(node.source_ids)
    return sorted(ids)


def _memory_snapshot_ids(thesis_id: str, snapshots: list[JsonMap], graph: JsonMap) -> list[str]:
    ids = {snapshot["snapshot_id"] for snapshot in snapshots if isinstance(snapshot.get("snapshot_id"), str) and thesis_id in _string_list(snapshot.get("top_thesis_ids", []))}
    thesis_node = f"eg_thesis_{thesis_id}"
    for edge in _map_list(graph.get("edges", [])):
        target = str(edge.get("target_node_id", ""))
        if edge.get("source_node_id") == thesis_node and edge.get("edge_type") == "preserved_in" and target.startswith("eg_memory_snapshot_"):
            ids.add(target.removeprefix("eg_memory_snapshot_"))
    return sorted(ids)


def _morning_brief_ids(thesis_id: str, morning: JsonMap | None, graph: JsonMap) -> list[str]:
    ids = set()
    if morning and thesis_id in [item.get("thesis_id") for item in _map_list(morning.get("top_theses", []))]:
        brief_id = morning.get("brief_id")
        if isinstance(brief_id, str):
            ids.add(brief_id)
    thesis_node = f"eg_thesis_{thesis_id}"
    for edge in _map_list(graph.get("edges", [])):
        target = str(edge.get("target_node_id", ""))
        if edge.get("source_node_id") == thesis_node and edge.get("edge_type") == "summarized_by" and target.startswith("eg_morning_brief_"):
            ids.add(target.removeprefix("eg_morning_brief_"))
    return sorted(ids)


def _confidence(support_ids: list[str], conflict_ids: list[str], findings: dict[str, JsonMap], finding_ids: list[str]) -> ThesisConfidence:
    repeated = sum(1 for finding_id in finding_ids if str(_map(findings.get(finding_id)).get("finding_type", "")).startswith("repeated_"))
    contradictions = sum(1 for finding_id in finding_ids if _map(findings.get(finding_id)).get("finding_type") == "possible_contradiction")
    if conflict_ids or contradictions:
        label = "low" if len(conflict_ids) >= len(support_ids) else "medium"
        rule = "explicit_contradiction_or_conflict"
    elif len(support_ids) >= 3 or repeated >= 2:
        label = "high"
        rule = "support_count_or_repeated_confirmations"
    elif support_ids:
        label = "medium"
        rule = "has_supporting_evidence"
    else:
        label = "low"
        rule = "no_supporting_evidence"
    return ThesisConfidence(label, len(support_ids), len(conflict_ids), repeated, contradictions, rule)


def _status(previous: ThesisRecord | None, support_ids: list[str], conflict_ids: list[str], confidence: ThesisConfidence) -> str:
    if not support_ids and not conflict_ids:
        return "archived"
    if previous:
        if len(conflict_ids) > len(previous.conflicting_evidence_ids):
            return "weakening"
        if len(support_ids) > len(previous.supporting_evidence_ids) and not conflict_ids:
            return "strengthening"
    if conflict_ids:
        return "weakening"
    if confidence.label == "high":
        return "strengthening"
    return "active"


def _timeline_events(previous: ThesisRecord | None, record: ThesisRecord, now: str) -> list[ThesisTimeline]:
    if previous is None:
        return [
            ThesisTimeline(
                thesis_id=record.thesis_id,
                timestamp=now,
                event_type="created",
                reason="Thesis appeared in existing thesis or evidence graph outputs.",
                affected_evidence_ids=record.supporting_evidence_ids + record.conflicting_evidence_ids,
            )
        ]
    if record.status == "strengthening" and len(record.supporting_evidence_ids) > len(previous.supporting_evidence_ids):
        return [ThesisTimeline(record.thesis_id, now, "strengthened", "Supporting evidence count increased.", _new_ids(previous.supporting_evidence_ids, record.supporting_evidence_ids))]
    if record.status == "weakening" and len(record.conflicting_evidence_ids) > len(previous.conflicting_evidence_ids):
        return [ThesisTimeline(record.thesis_id, now, "weakened", "Conflicting evidence count increased.", _new_ids(previous.conflicting_evidence_ids, record.conflicting_evidence_ids))]
    if record.status == "archived" and previous.status != "archived":
        return [ThesisTimeline(record.thesis_id, now, "archived", "Thesis has no supporting or conflicting evidence.", [])]
    return [ThesisTimeline(record.thesis_id, now, "updated", "Thesis intelligence record refreshed from local deterministic artifacts.", [])]


def _new_ids(previous: list[str], current: list[str]) -> list[str]:
    return sorted(set(current) - set(previous))


def _graph_node(thesis_id: str, graph: JsonMap) -> JsonMap:
    for node in _map_list(graph.get("nodes", [])):
        if thesis_id in _string_list(node.get("references", [])):
            return node
    return {}


def _label_from_evidence_graph(thesis_id: str, graph: JsonMap) -> str | None:
    node = _graph_node(thesis_id, graph)
    label = node.get("label")
    return label if isinstance(label, str) else None


def _record_lines(records: list[ThesisRecord]) -> list[str]:
    if not records:
        return ["- None", ""]
    lines = []
    for record in sorted(records, key=lambda item: (item.title, item.thesis_id)):
        lines.append(
            f"- `{record.thesis_id}` {record.title} "
            f"(confidence={record.confidence.label}, support={len(record.supporting_evidence_ids)}, conflicts={len(record.conflicting_evidence_ids)})"
        )
    lines.append("")
    return lines


def _timeline_lines(events: list[ThesisTimeline]) -> list[str]:
    if not events:
        return ["- None", ""]
    return [*[f"- `{event.timestamp}` `{event.thesis_id}` {event.event_type}: {event.reason}" for event in events], ""]


def _reference_lines(records: list[ThesisRecord], field_name: str) -> list[str]:
    refs = sorted({ref for record in records for ref in getattr(record, field_name)})
    if not refs:
        return ["- None", ""]
    return [*[f"- `{ref}`" for ref in refs], ""]


def _map(value: Any) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _map_list(value: Any) -> list[JsonMap]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


def _require_str(data: JsonMap, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise ThesisIntelligenceError(f"Thesis intelligence field {key} must be a string")
    return value
