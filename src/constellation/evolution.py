from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from . import __version__
from .io import read_json, write_json
from .memory import InstitutionalMemorySnapshot, InstitutionalMemoryStore
from .models import JsonMap


class KnowledgeEvolutionError(RuntimeError):
    pass


@dataclass(frozen=True)
class TrendRecord:
    trend_id: str
    trend_type: str
    subject: str
    direction: str
    magnitude: int
    summary: str
    evidence: JsonMap

    def to_dict(self) -> JsonMap:
        return {
            "trend_id": self.trend_id,
            "trend_type": self.trend_type,
            "subject": self.subject,
            "direction": self.direction,
            "magnitude": self.magnitude,
            "summary": self.summary,
            "evidence": self.evidence,
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "TrendRecord":
        return cls(
            trend_id=_require_str(data, "trend_id"),
            trend_type=_require_str(data, "trend_type"),
            subject=_require_str(data, "subject"),
            direction=_require_str(data, "direction"),
            magnitude=_int(data.get("magnitude")),
            summary=_require_str(data, "summary"),
            evidence=_map(data.get("evidence")),
        )


@dataclass(frozen=True)
class TrendTimeline:
    created_at: str
    records: list[TrendRecord]

    def to_dict(self) -> JsonMap:
        return {"created_at": self.created_at, "records": [record.to_dict() for record in self.records]}

    @classmethod
    def from_dict(cls, data: JsonMap) -> "TrendTimeline":
        return cls(created_at=_require_str(data, "created_at"), records=[TrendRecord.from_dict(item) for item in _map_list(data.get("records", []))])


@dataclass(frozen=True)
class EvolutionSnapshot:
    snapshot_id: str
    created_at: str
    source_memory_snapshot_id: str | None
    evidence_ids: list[str]
    source_ids: list[str]
    thesis_states: JsonMap
    graph_node_count: int
    graph_edge_count: int
    evidence_count: int
    thesis_count: int
    findings_count: int
    source_activity: JsonMap
    research_volume: JsonMap
    workflow_activity: JsonMap
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return {
            "snapshot_id": self.snapshot_id,
            "created_at": self.created_at,
            "source_memory_snapshot_id": self.source_memory_snapshot_id,
            "evidence_ids": self.evidence_ids,
            "source_ids": self.source_ids,
            "thesis_states": self.thesis_states,
            "graph_node_count": self.graph_node_count,
            "graph_edge_count": self.graph_edge_count,
            "evidence_count": self.evidence_count,
            "thesis_count": self.thesis_count,
            "findings_count": self.findings_count,
            "source_activity": self.source_activity,
            "research_volume": self.research_volume,
            "workflow_activity": self.workflow_activity,
            "provenance": self.provenance,
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "EvolutionSnapshot":
        return cls(
            snapshot_id=_require_str(data, "snapshot_id"),
            created_at=_require_str(data, "created_at"),
            source_memory_snapshot_id=_optional_str(data.get("source_memory_snapshot_id")),
            evidence_ids=_string_list(data.get("evidence_ids", [])),
            source_ids=_string_list(data.get("source_ids", [])),
            thesis_states=_map(data.get("thesis_states")),
            graph_node_count=_int(data.get("graph_node_count")),
            graph_edge_count=_int(data.get("graph_edge_count")),
            evidence_count=_int(data.get("evidence_count")),
            thesis_count=_int(data.get("thesis_count")),
            findings_count=_int(data.get("findings_count")),
            source_activity=_map(data.get("source_activity")),
            research_volume=_map(data.get("research_volume")),
            workflow_activity=_map(data.get("workflow_activity")),
            provenance=_map(data.get("provenance")),
        )


@dataclass(frozen=True)
class EvolutionDelta:
    delta_id: str
    prior_snapshot_id: str | None
    current_snapshot_id: str
    created_at: str
    evidence_gained: list[str]
    evidence_removed: list[str]
    graph_node_growth: int
    graph_edge_growth: int
    thesis_confidence_changes: list[JsonMap]
    thesis_status_changes: list[JsonMap]
    source_activity_trends: list[TrendRecord]
    research_volume_trends: list[TrendRecord]
    workflow_execution_trends: list[TrendRecord]
    trend_records: list[TrendRecord]
    longitudinal_health_score: int
    summary: str
    limitations: list[str]

    def to_dict(self) -> JsonMap:
        return {
            "delta_id": self.delta_id,
            "prior_snapshot_id": self.prior_snapshot_id,
            "current_snapshot_id": self.current_snapshot_id,
            "created_at": self.created_at,
            "evidence_gained": self.evidence_gained,
            "evidence_removed": self.evidence_removed,
            "graph_node_growth": self.graph_node_growth,
            "graph_edge_growth": self.graph_edge_growth,
            "thesis_confidence_changes": self.thesis_confidence_changes,
            "thesis_status_changes": self.thesis_status_changes,
            "source_activity_trends": [record.to_dict() for record in self.source_activity_trends],
            "research_volume_trends": [record.to_dict() for record in self.research_volume_trends],
            "workflow_execution_trends": [record.to_dict() for record in self.workflow_execution_trends],
            "trend_records": [record.to_dict() for record in self.trend_records],
            "longitudinal_health_score": self.longitudinal_health_score,
            "summary": self.summary,
            "limitations": self.limitations,
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "EvolutionDelta":
        return cls(
            delta_id=_require_str(data, "delta_id"),
            prior_snapshot_id=_optional_str(data.get("prior_snapshot_id")),
            current_snapshot_id=_require_str(data, "current_snapshot_id"),
            created_at=_require_str(data, "created_at"),
            evidence_gained=_string_list(data.get("evidence_gained", [])),
            evidence_removed=_string_list(data.get("evidence_removed", [])),
            graph_node_growth=_int(data.get("graph_node_growth")),
            graph_edge_growth=_int(data.get("graph_edge_growth")),
            thesis_confidence_changes=_map_list(data.get("thesis_confidence_changes", [])),
            thesis_status_changes=_map_list(data.get("thesis_status_changes", [])),
            source_activity_trends=[TrendRecord.from_dict(item) for item in _map_list(data.get("source_activity_trends", []))],
            research_volume_trends=[TrendRecord.from_dict(item) for item in _map_list(data.get("research_volume_trends", []))],
            workflow_execution_trends=[TrendRecord.from_dict(item) for item in _map_list(data.get("workflow_execution_trends", []))],
            trend_records=[TrendRecord.from_dict(item) for item in _map_list(data.get("trend_records", []))],
            longitudinal_health_score=_int(data.get("longitudinal_health_score")),
            summary=_require_str(data, "summary"),
            limitations=_string_list(data.get("limitations", [])),
        )


class KnowledgeEvolutionEngine:
    def __init__(self, root: Path) -> None:
        self.root = root

    def current_snapshot(self, memory_snapshot: InstitutionalMemorySnapshot | None = None) -> EvolutionSnapshot:
        memory_snapshot = memory_snapshot or _latest_memory_snapshot(self.root)
        evidence = _read_evidence(self.root)
        graph = _read_optional_json(self.root / "memory" / "graph" / "graph.json")
        graph_nodes = _as_collection(_map(graph).get("nodes"))
        graph_edges = _as_collection(_map(graph).get("edges"))
        theses = _read_theses(self.root)
        findings = _map_list(_map(_read_optional_json(self.root / "outputs" / "analysis" / "cross-document-analysis.json")).get("findings", []))
        source_ids = sorted({str(item.get("source_identifier")) for item in evidence if item.get("source_identifier")} | set(memory_snapshot.source_document_references if memory_snapshot else []))
        source_activity = _source_activity(self.root)
        research_volume = _research_volume(self.root)
        workflow_activity = _workflow_activity(self.root)
        evidence_ids = sorted(str(item.get("evidence_id")) for item in evidence if item.get("evidence_id"))
        thesis_states = _thesis_states(theses)
        snapshot_id = _evolution_snapshot_id(evidence_ids, source_ids, thesis_states, len(graph_nodes), len(graph_edges), memory_snapshot.snapshot_id if memory_snapshot else None)
        return EvolutionSnapshot(
            snapshot_id=snapshot_id,
            created_at=_now_iso(),
            source_memory_snapshot_id=memory_snapshot.snapshot_id if memory_snapshot else None,
            evidence_ids=evidence_ids,
            source_ids=source_ids,
            thesis_states=thesis_states,
            graph_node_count=len(graph_nodes) or (memory_snapshot.graph_node_count if memory_snapshot else 0),
            graph_edge_count=len(graph_edges) or (memory_snapshot.graph_edge_count if memory_snapshot else 0),
            evidence_count=len(evidence_ids) or (memory_snapshot.evidence_count if memory_snapshot else 0),
            thesis_count=len(thesis_states) or (memory_snapshot.thesis_count if memory_snapshot else 0),
            findings_count=len(findings) or (memory_snapshot.findings_count if memory_snapshot else 0),
            source_activity=source_activity,
            research_volume=research_volume,
            workflow_activity=workflow_activity,
            provenance={
                "institutional_memory": "outputs/memory/snapshots.json",
                "evidence": "memory/evidence/",
                "knowledge_graph": "memory/graph/graph.json",
                "thesis_intelligence": "outputs/thesis/theses.json",
                "source_monitor": "outputs/source-monitor/source-history.json",
                "daily_pipeline": "outputs/daily/daily-history.json",
                "workflow_automation": "outputs/workflows/workflow-history.json",
            },
        )

    def compare(self, prior: EvolutionSnapshot | None, current: EvolutionSnapshot) -> EvolutionDelta:
        created_at = _now_iso()
        evidence_gained = sorted(set(current.evidence_ids) - set(prior.evidence_ids if prior else []))
        evidence_removed = sorted(set(prior.evidence_ids if prior else []) - set(current.evidence_ids))
        graph_node_growth = current.graph_node_count - (prior.graph_node_count if prior else 0)
        graph_edge_growth = current.graph_edge_count - (prior.graph_edge_count if prior else 0)
        confidence_changes = _thesis_confidence_changes(_map(prior.thesis_states) if prior else {}, current.thesis_states)
        status_changes = _thesis_status_changes(_map(prior.thesis_states) if prior else {}, current.thesis_states)
        source_trends = _activity_trends("source_activity", _map(prior.source_activity) if prior else {}, current.source_activity)
        research_trends = _volume_trends(_map(prior.research_volume) if prior else {}, current.research_volume)
        workflow_trends = _workflow_trends(_map(prior.workflow_activity) if prior else {}, current.workflow_activity)
        thesis_trends = _thesis_trends(confidence_changes, status_changes)
        records = sorted(source_trends + research_trends + workflow_trends + thesis_trends, key=lambda item: (item.trend_type, item.subject, item.trend_id))
        health = _health_score(current, evidence_gained, evidence_removed, graph_node_growth, graph_edge_growth, confidence_changes, status_changes)
        delta_id = _delta_id(prior.snapshot_id if prior else None, current.snapshot_id, records, evidence_gained, evidence_removed)
        summary = (
            f"Compared `{prior.snapshot_id if prior else 'none'}` to `{current.snapshot_id}`: "
            f"evidence {len(evidence_gained)} gained/{len(evidence_removed)} removed; "
            f"graph nodes {graph_node_growth:+}; graph edges {graph_edge_growth:+}; "
            f"thesis confidence changes {len(confidence_changes)}; thesis status changes {len(status_changes)}."
        )
        return EvolutionDelta(
            delta_id=delta_id,
            prior_snapshot_id=prior.snapshot_id if prior else None,
            current_snapshot_id=current.snapshot_id,
            created_at=created_at,
            evidence_gained=evidence_gained,
            evidence_removed=evidence_removed,
            graph_node_growth=graph_node_growth,
            graph_edge_growth=graph_edge_growth,
            thesis_confidence_changes=confidence_changes,
            thesis_status_changes=status_changes,
            source_activity_trends=source_trends,
            research_volume_trends=research_trends,
            workflow_execution_trends=workflow_trends,
            trend_records=records,
            longitudinal_health_score=health,
            summary=summary,
            limitations=[
                "Knowledge Evolution uses deterministic local artifacts only.",
                "Trend records are based on explicit counts, IDs, statuses, and timestamps; no semantic inference is performed.",
            ],
        )


class KnowledgeEvolutionStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "outputs" / "evolution"
        self.json_path = self.directory / "evolution.json"
        self.markdown_path = self.directory / "evolution.md"
        self.trend_report_path = self.directory / "trend-report.md"
        self.history_path = self.directory / "trend-history.json"

    def generate(self) -> EvolutionDelta:
        history = self.history()
        prior = history[-1]["snapshot"] if history else None
        current = KnowledgeEvolutionEngine(self.root).current_snapshot()
        delta = KnowledgeEvolutionEngine(self.root).compare(prior, current)
        self.save(current, delta)
        return delta

    def compare(self, snapshot_id_a: str, snapshot_id_b: str) -> EvolutionDelta:
        memory = InstitutionalMemoryStore(self.root)
        prior = KnowledgeEvolutionEngine(self.root).current_snapshot(memory.show_snapshot(snapshot_id_a))
        current = KnowledgeEvolutionEngine(self.root).current_snapshot(memory.show_snapshot(snapshot_id_b))
        return KnowledgeEvolutionEngine(self.root).compare(prior, current)

    def save(self, snapshot: EvolutionSnapshot, delta: EvolutionDelta) -> None:
        write_json(self.json_path, {"snapshot": snapshot.to_dict(), "delta": delta.to_dict()})
        history = self.history()
        history.append({"snapshot": snapshot, "delta": delta})
        write_json(
            self.history_path,
            {
                "runs": [
                    {"snapshot": item["snapshot"].to_dict(), "delta": item["delta"].to_dict()}
                    for item in history
                ]
            },
        )
        self.export(delta)

    def load(self) -> EvolutionDelta:
        if not self.json_path.exists():
            raise KnowledgeEvolutionError("No knowledge evolution report found. Run `python -m constellation evolution` first.")
        return EvolutionDelta.from_dict(_map(read_json(self.json_path).get("delta")))

    def status(self) -> JsonMap:
        if not self.json_path.exists():
            return {"available": False, "history_count": len(self.history())}
        data = read_json(self.json_path)
        delta = EvolutionDelta.from_dict(_map(data.get("delta")))
        return {
            "available": True,
            "delta_id": delta.delta_id,
            "current_snapshot_id": delta.current_snapshot_id,
            "prior_snapshot_id": delta.prior_snapshot_id,
            "evidence_gained": len(delta.evidence_gained),
            "evidence_removed": len(delta.evidence_removed),
            "graph_node_growth": delta.graph_node_growth,
            "graph_edge_growth": delta.graph_edge_growth,
            "trend_count": len(delta.trend_records),
            "longitudinal_health_score": delta.longitudinal_health_score,
            "history_count": len(self.history()),
        }

    def history(self) -> list[JsonMap]:
        if not self.history_path.exists():
            return []
        data = read_json(self.history_path)
        items = []
        for item in _map_list(data.get("runs", [])):
            items.append({"snapshot": EvolutionSnapshot.from_dict(_map(item.get("snapshot"))), "delta": EvolutionDelta.from_dict(_map(item.get("delta")))})
        return items

    def export(self, delta: EvolutionDelta | None = None) -> Path:
        delta = delta or self.load()
        self.markdown_path.parent.mkdir(parents=True, exist_ok=True)
        markdown = render_evolution_markdown(delta)
        self.markdown_path.write_text(markdown, encoding="utf-8")
        self.trend_report_path.write_text(render_trend_report(delta), encoding="utf-8")
        return self.markdown_path


def render_evolution_markdown(delta: EvolutionDelta) -> str:
    lines = [
        "# Knowledge Evolution",
        "",
        f"- Delta ID: `{delta.delta_id}`",
        f"- Prior snapshot: `{delta.prior_snapshot_id or ''}`",
        f"- Current snapshot: `{delta.current_snapshot_id}`",
        f"- Created: `{delta.created_at}`",
        f"- Longitudinal health score: {delta.longitudinal_health_score}",
        "",
        "## Summary",
        "",
        delta.summary,
        "",
        "## Evidence",
        "",
        f"- Gained: {len(delta.evidence_gained)}",
        f"- Removed: {len(delta.evidence_removed)}",
        "",
        "## Graph Growth",
        "",
        f"- Node growth: {delta.graph_node_growth:+}",
        f"- Edge growth: {delta.graph_edge_growth:+}",
        "",
        "## Thesis Changes",
        "",
        f"- Confidence changes: {len(delta.thesis_confidence_changes)}",
        f"- Status changes: {len(delta.thesis_status_changes)}",
        "",
        "## Trend Records",
        "",
        *_trend_lines(delta.trend_records),
        "## Limitations",
        "",
        *_string_lines(delta.limitations),
    ]
    return "\n".join(lines)


def render_trend_report(delta: EvolutionDelta) -> str:
    lines = [
        "# Knowledge Evolution Trend Report",
        "",
        "## Source Activity Trends",
        "",
        *_trend_lines(delta.source_activity_trends),
        "## Research Volume Trends",
        "",
        *_trend_lines(delta.research_volume_trends),
        "## Workflow Execution Trends",
        "",
        *_trend_lines(delta.workflow_execution_trends),
        "## Recent Thesis Changes",
        "",
    ]
    if not delta.thesis_confidence_changes and not delta.thesis_status_changes:
        lines.extend(["- None", ""])
    for change in delta.thesis_confidence_changes:
        lines.append(f"- `{change.get('thesis_id')}` confidence `{change.get('from')}` -> `{change.get('to')}`")
    for change in delta.thesis_status_changes:
        lines.append(f"- `{change.get('thesis_id')}` status `{change.get('from')}` -> `{change.get('to')}`")
    lines.append("")
    return "\n".join(lines)


def _latest_memory_snapshot(root: Path) -> InstitutionalMemorySnapshot | None:
    snapshots = InstitutionalMemoryStore(root).list_snapshots()
    return snapshots[-1] if snapshots else None


def _read_evidence(root: Path) -> list[JsonMap]:
    records = []
    directory = root / "memory" / "evidence"
    if not directory.exists():
        return []
    for path in sorted(directory.glob("ev_*.json")):
        try:
            data = read_json(path)
        except Exception:
            continue
        if isinstance(data, dict):
            records.append(data)
    return records


def _read_theses(root: Path) -> list[JsonMap]:
    for path in [root / "outputs" / "thesis" / "theses.json", root / "outputs" / "theses" / "theses.json"]:
        data = _read_optional_json(path)
        theses = _map_list(_map(data).get("theses", []))
        if theses:
            return theses
    return []


def _thesis_states(theses: list[JsonMap]) -> JsonMap:
    states: JsonMap = {}
    for thesis in theses:
        thesis_id = thesis.get("thesis_id")
        if not isinstance(thesis_id, str):
            continue
        confidence = thesis.get("confidence")
        states[thesis_id] = {
            "title": thesis.get("title"),
            "status": thesis.get("status"),
            "confidence": _map(confidence).get("label") if isinstance(confidence, dict) else confidence,
            "supporting_evidence_count": len(_string_list(thesis.get("supporting_evidence_ids", []))),
            "conflicting_evidence_count": len(_string_list(thesis.get("conflicting_evidence_ids", []))),
            "source_count": len(_string_list(thesis.get("source_ids", []))),
        }
    return states


def _source_activity(root: Path) -> JsonMap:
    data = _read_optional_json(root / "outputs" / "source-monitor" / "source-history.json")
    runs = _map_list(_map(data).get("runs", []))
    activity: JsonMap = {}
    for run in runs[-5:]:
        for change in _map_list(run.get("changes", [])):
            source_id = str(change.get("source_id", "unknown"))
            record = activity.setdefault(source_id, {"events": 0, "new_items": 0, "removed_items": 0, "updated_items": 0, "failed_items": 0})
            record["events"] += 1
            record["new_items"] += len(_list(change.get("new_items")))
            record["removed_items"] += len(_list(change.get("removed_items")))
            record["updated_items"] += len(_list(change.get("updated_items")))
            record["failed_items"] += len(_list(change.get("failed_items")))
    return activity


def _research_volume(root: Path) -> JsonMap:
    workflow = _read_optional_json(root / "outputs" / "workflows" / "latest-workflow.json")
    research_step = next((step for step in _map_list(_map(workflow).get("executed_steps", [])) if step.get("command") == "process research"), {})
    details = _map(research_step.get("details"))
    return {
        "new_research_files_detected": _int(details.get("new_research_files_detected")),
        "research_runs_created": _int(details.get("research_runs_created")),
        "graph_builds_completed": _int(details.get("graph_builds_completed")),
        "graph_builds_failed": _int(details.get("graph_builds_failed")),
    }


def _workflow_activity(root: Path) -> JsonMap:
    data = _read_optional_json(root / "outputs" / "workflows" / "workflow-history.json")
    runs = _map_list(_map(data).get("runs", []))
    return {
        "run_count": len(runs),
        "completed": sum(1 for run in runs if run.get("status") == "completed"),
        "failed": sum(1 for run in runs if run.get("status") == "failed"),
        "completed_with_failures": sum(1 for run in runs if run.get("status") == "completed_with_failures"),
        "latest_status": _map(runs[-1]).get("status") if runs else None,
    }


def _activity_trends(trend_type: str, prior: JsonMap, current: JsonMap) -> list[TrendRecord]:
    records = []
    for source_id in sorted(set(prior) | set(current)):
        before = sum(_int(value) for key, value in _map(prior.get(source_id)).items() if key != "events")
        after = sum(_int(value) for key, value in _map(current.get(source_id)).items() if key != "events")
        change = after - before
        if change != 0:
            records.append(_trend(trend_type, source_id, change, {"prior": _map(prior.get(source_id)), "current": _map(current.get(source_id))}))
    return records


def _volume_trends(prior: JsonMap, current: JsonMap) -> list[TrendRecord]:
    records = []
    for key in ["new_research_files_detected", "research_runs_created", "graph_builds_completed", "graph_builds_failed"]:
        change = _int(current.get(key)) - _int(prior.get(key))
        if change != 0:
            records.append(_trend("research_volume", key, change, {"prior": _int(prior.get(key)), "current": _int(current.get(key))}))
    return records


def _workflow_trends(prior: JsonMap, current: JsonMap) -> list[TrendRecord]:
    records = []
    for key in ["run_count", "completed", "failed", "completed_with_failures"]:
        change = _int(current.get(key)) - _int(prior.get(key))
        if change != 0:
            records.append(_trend("workflow_execution", key, change, {"prior": _int(prior.get(key)), "current": _int(current.get(key))}))
    return records


def _thesis_trends(confidence_changes: list[JsonMap], status_changes: list[JsonMap]) -> list[TrendRecord]:
    records = []
    for change in confidence_changes:
        records.append(_trend("thesis_confidence", str(change.get("thesis_id")), _confidence_rank(str(change.get("to"))) - _confidence_rank(str(change.get("from"))), change))
    for change in status_changes:
        records.append(_trend("thesis_status", str(change.get("thesis_id")), 1, change))
    return records


def _thesis_confidence_changes(prior: JsonMap, current: JsonMap) -> list[JsonMap]:
    changes = []
    for thesis_id in sorted(set(prior).intersection(current)):
        before = _map(prior.get(thesis_id)).get("confidence")
        after = _map(current.get(thesis_id)).get("confidence")
        if before != after:
            changes.append({"thesis_id": thesis_id, "from": before, "to": after})
    return changes


def _thesis_status_changes(prior: JsonMap, current: JsonMap) -> list[JsonMap]:
    changes = []
    for thesis_id in sorted(set(prior).intersection(current)):
        before = _map(prior.get(thesis_id)).get("status")
        after = _map(current.get(thesis_id)).get("status")
        if before != after:
            changes.append({"thesis_id": thesis_id, "from": before, "to": after})
    return changes


def _trend(trend_type: str, subject: str, magnitude: int, evidence: JsonMap) -> TrendRecord:
    direction = "up" if magnitude > 0 else "down" if magnitude < 0 else "flat"
    summary = f"{subject} moved {direction} by {abs(magnitude)}."
    return TrendRecord(
        trend_id=f"trend_{_digest(trend_type + '|' + subject + '|' + str(magnitude) + '|' + repr(evidence))}",
        trend_type=trend_type,
        subject=subject,
        direction=direction,
        magnitude=magnitude,
        summary=summary,
        evidence=evidence,
    )


def _health_score(current: EvolutionSnapshot, evidence_gained: list[str], evidence_removed: list[str], node_growth: int, edge_growth: int, confidence_changes: list[JsonMap], status_changes: list[JsonMap]) -> int:
    score = 50
    score += min(20, len(evidence_gained))
    score -= min(20, len(evidence_removed) * 2)
    score += min(10, max(0, node_growth))
    score += min(10, max(0, edge_growth))
    score += min(5, len(confidence_changes))
    score += min(5, len(status_changes))
    if current.evidence_count == 0:
        score -= 20
    return max(0, min(100, score))


def _evolution_snapshot_id(evidence_ids: list[str], source_ids: list[str], thesis_states: JsonMap, node_count: int, edge_count: int, memory_snapshot_id: str | None) -> str:
    payload = "|".join([memory_snapshot_id or "", ",".join(evidence_ids), ",".join(source_ids), repr(sorted(thesis_states.items())), str(node_count), str(edge_count)])
    return f"evolution_snapshot_{_digest(payload)}"


def _delta_id(prior_id: str | None, current_id: str, records: list[TrendRecord], evidence_gained: list[str], evidence_removed: list[str]) -> str:
    payload = "|".join([prior_id or "", current_id, ",".join(record.trend_id for record in records), ",".join(evidence_gained), ",".join(evidence_removed)])
    return f"evolution_delta_{_digest(payload)}"


def _read_optional_json(path: Path) -> JsonMap:
    if not path.exists():
        return {}
    try:
        data = read_json(path)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _as_collection(value: Any) -> list[JsonMap]:
    if isinstance(value, dict):
        return [item for item in value.values() if isinstance(item, dict)]
    return _map_list(value)


def _trend_lines(records: list[TrendRecord]) -> list[str]:
    if not records:
        return ["- None", ""]
    return [*[f"- `{record.trend_type}` {record.subject}: {record.direction} {abs(record.magnitude)}" for record in records], ""]


def _string_lines(items: list[str]) -> list[str]:
    if not items:
        return ["- None", ""]
    return [*[f"- {item}" for item in items], ""]


def _confidence_rank(value: str) -> int:
    return {"low": 1, "medium": 2, "high": 3}.get(value, 0)


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:16]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _map(value: Any) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _map_list(value: Any) -> list[JsonMap]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


def _require_str(data: JsonMap, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise KnowledgeEvolutionError(f"Knowledge evolution field {key} must be a string")
    return value
