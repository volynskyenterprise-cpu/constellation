from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from .io import read_json, write_json
from .models import JsonMap, utc_now_iso


class MemoryManager:
    def __init__(self, root: Path, workflow_run_id: str) -> None:
        self.root = root
        self.workflow_run_id = workflow_run_id
        self.working_path = root / "memory" / "runs" / f"{workflow_run_id}-working.json"
        self.project_path = root / "memory" / "project" / "kernel-project-memory.json"
        self.knowledge_path = root / "memory" / "knowledge" / "kernel-knowledge-memory.json"
        self.long_term_path = root / "memory" / "long-term" / "kernel-long-term-memory.json"

    def initialize(self, objective: str) -> None:
        if not self.working_path.exists():
            write_json(
                self.working_path,
                {
                    "workflow_run_id": self.workflow_run_id,
                    "objective": objective,
                    "entries": [],
                    "artifacts": {},
                },
            )
        self._ensure_store(self.project_path, "project")
        self._ensure_store(self.knowledge_path, "knowledge")
        self._ensure_store(self.long_term_path, "long_term")

    def add_working_entry(self, key: str, value: Any) -> None:
        data = read_json(self.working_path)
        entries = data.setdefault("entries", [])
        entries.append({"key": key, "value": value})
        write_json(self.working_path, data)

    def set_artifact(self, name: str, value: Any) -> None:
        data = read_json(self.working_path)
        artifacts = data.setdefault("artifacts", {})
        artifacts[name] = value
        write_json(self.working_path, data)

    def context_for_step(self, step_id: str) -> dict[str, Any]:
        working = read_json(self.working_path)
        project = read_json(self.project_path)
        return {
            "summary": f"Working context for step {step_id}.",
            "workflow_state": "Execution",
            "working_memory": working,
            "project_memory": project,
            "memory_references": [
                {"layer": "working", "location": str(self.working_path)},
                {"layer": "project", "location": str(self.project_path)},
            ],
            "artifacts": working.get("artifacts", {}),
            "open_questions": [],
        }

    def project_memory(self) -> dict[str, Any]:
        return read_json(self.project_path)

    def _ensure_store(self, path: Path, layer: str) -> None:
        if not path.exists():
            write_json(path, {"layer": layer, "entries": [], "status": "stub" if layer != "project" else "active"})


class InstitutionalMemoryError(RuntimeError):
    pass


@dataclass(frozen=True)
class InstitutionalMemorySnapshot:
    snapshot_id: str
    label: str | None
    created_at: str
    intake_counts: JsonMap
    google_drive_sync_counts: JsonMap
    evidence_count: int
    graph_node_count: int
    graph_edge_count: int
    findings_count: int
    thesis_count: int
    intelligence_brief_id: str | None
    morning_brief_id: str | None
    top_thesis_ids: list[str]
    top_finding_ids: list[str]
    source_document_references: list[str]
    artifact_references: list[str]
    limitations: list[str]
    provenance_references: JsonMap

    def to_dict(self) -> JsonMap:
        return {
            "snapshot_id": self.snapshot_id,
            "label": self.label,
            "created_at": self.created_at,
            "intake_counts": self.intake_counts,
            "google_drive_sync_counts": self.google_drive_sync_counts,
            "evidence_count": self.evidence_count,
            "graph_node_count": self.graph_node_count,
            "graph_edge_count": self.graph_edge_count,
            "findings_count": self.findings_count,
            "thesis_count": self.thesis_count,
            "intelligence_brief_id": self.intelligence_brief_id,
            "morning_brief_id": self.morning_brief_id,
            "top_thesis_ids": self.top_thesis_ids,
            "top_finding_ids": self.top_finding_ids,
            "source_document_references": self.source_document_references,
            "artifact_references": self.artifact_references,
            "limitations": self.limitations,
            "provenance_references": self.provenance_references,
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "InstitutionalMemorySnapshot":
        return cls(
            snapshot_id=_require_str(data, "snapshot_id"),
            label=_optional_str(data.get("label")),
            created_at=_require_str(data, "created_at"),
            intake_counts=_map(data.get("intake_counts")),
            google_drive_sync_counts=_map(data.get("google_drive_sync_counts")),
            evidence_count=_int(data.get("evidence_count")),
            graph_node_count=_int(data.get("graph_node_count")),
            graph_edge_count=_int(data.get("graph_edge_count")),
            findings_count=_int(data.get("findings_count")),
            thesis_count=_int(data.get("thesis_count")),
            intelligence_brief_id=_optional_str(data.get("intelligence_brief_id")),
            morning_brief_id=_optional_str(data.get("morning_brief_id")),
            top_thesis_ids=_string_list(data.get("top_thesis_ids", [])),
            top_finding_ids=_string_list(data.get("top_finding_ids", [])),
            source_document_references=_string_list(data.get("source_document_references", [])),
            artifact_references=_string_list(data.get("artifact_references", [])),
            limitations=_string_list(data.get("limitations", [])),
            provenance_references=_map(data.get("provenance_references")),
        )


@dataclass(frozen=True)
class InstitutionalMemoryDelta:
    prior_snapshot_id: str
    current_snapshot_id: str
    evidence_count_change: int
    graph_node_change: int
    graph_edge_change: int
    findings_count_change: int
    thesis_count_change: int
    new_thesis_ids: list[str]
    removed_thesis_ids: list[str]
    new_finding_ids: list[str]
    removed_finding_ids: list[str]
    new_source_references: list[str]
    removed_source_references: list[str]
    summary: str
    limitations: list[str]

    def to_dict(self) -> JsonMap:
        return {
            "prior_snapshot_id": self.prior_snapshot_id,
            "current_snapshot_id": self.current_snapshot_id,
            "evidence_count_change": self.evidence_count_change,
            "graph_node_change": self.graph_node_change,
            "graph_edge_change": self.graph_edge_change,
            "findings_count_change": self.findings_count_change,
            "thesis_count_change": self.thesis_count_change,
            "new_thesis_ids": self.new_thesis_ids,
            "removed_thesis_ids": self.removed_thesis_ids,
            "new_finding_ids": self.new_finding_ids,
            "removed_finding_ids": self.removed_finding_ids,
            "new_source_references": self.new_source_references,
            "removed_source_references": self.removed_source_references,
            "summary": self.summary,
            "limitations": self.limitations,
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "InstitutionalMemoryDelta":
        return cls(
            prior_snapshot_id=_require_str(data, "prior_snapshot_id"),
            current_snapshot_id=_require_str(data, "current_snapshot_id"),
            evidence_count_change=_int(data.get("evidence_count_change")),
            graph_node_change=_int(data.get("graph_node_change")),
            graph_edge_change=_int(data.get("graph_edge_change")),
            findings_count_change=_int(data.get("findings_count_change")),
            thesis_count_change=_int(data.get("thesis_count_change")),
            new_thesis_ids=_string_list(data.get("new_thesis_ids", [])),
            removed_thesis_ids=_string_list(data.get("removed_thesis_ids", [])),
            new_finding_ids=_string_list(data.get("new_finding_ids", [])),
            removed_finding_ids=_string_list(data.get("removed_finding_ids", [])),
            new_source_references=_string_list(data.get("new_source_references", [])),
            removed_source_references=_string_list(data.get("removed_source_references", [])),
            summary=_require_str(data, "summary"),
            limitations=_string_list(data.get("limitations", [])),
        )


class InstitutionalMemoryEngine:
    def __init__(self, root: Path) -> None:
        self.root = root

    def snapshot(self, label: str | None = None) -> InstitutionalMemorySnapshot:
        intake = _read_optional_json(self.root / "outputs" / "intake" / "intake-manifest.json")
        drive = _read_optional_json(self.root / "outputs" / "google-drive" / "google-drive-sync-manifest.json")
        evidence_records = _read_evidence_records(self.root)
        graph = _read_optional_json(self.root / "memory" / "graph" / "graph.json") or {}
        findings_data = _read_optional_json(self.root / "outputs" / "analysis" / "cross-document-analysis.json")
        theses_data = _read_optional_json(self.root / "outputs" / "theses" / "theses.json")
        intelligence = _read_optional_json(self.root / "outputs" / "intelligence" / "institutional-intelligence.json")
        morning = _read_optional_json(self.root / "outputs" / "morning" / "morning-brief.json")
        artifacts = _read_artifact_references(self.root)
        findings = _map_list(_map(findings_data).get("findings", []))
        theses = _map_list(_map(theses_data).get("theses", []))
        nodes = _map_list(_map(graph).get("nodes", []))
        edges = _map_list(_map(graph).get("edges", []))
        source_refs = _source_references(evidence_records, nodes, theses, findings)
        limitations = _snapshot_limitations(intake, drive, evidence_records, nodes, findings, theses, intelligence, morning)
        snapshot_id = _snapshot_id(label, evidence_records, nodes, edges, findings, theses, intelligence, morning, source_refs)
        return InstitutionalMemorySnapshot(
            snapshot_id=snapshot_id,
            label=label,
            created_at=utc_now_iso(),
            intake_counts=_map(_map(intake).get("counts")),
            google_drive_sync_counts=_drive_counts(drive),
            evidence_count=len(evidence_records),
            graph_node_count=len(nodes),
            graph_edge_count=len(edges),
            findings_count=len(findings),
            thesis_count=len(theses),
            intelligence_brief_id=_optional_str(_map(intelligence).get("brief_id")),
            morning_brief_id=_optional_str(_map(morning).get("brief_id")),
            top_thesis_ids=_top_ids(theses, "thesis_id", "confidence"),
            top_finding_ids=_top_ids(findings, "finding_id", "confidence"),
            source_document_references=source_refs,
            artifact_references=artifacts,
            limitations=limitations,
            provenance_references={
                "intake_manifest": "outputs/intake/intake-manifest.json" if intake else None,
                "google_drive_sync_manifest": "outputs/google-drive/google-drive-sync-manifest.json" if drive else None,
                "evidence": "memory/evidence/",
                "knowledge_graph": "memory/graph/graph.json" if graph else None,
                "cross_document_analysis": "outputs/analysis/cross-document-analysis.json" if findings_data else None,
                "theses": "outputs/theses/theses.json" if theses_data else None,
                "intelligence": "outputs/intelligence/institutional-intelligence.json" if intelligence else None,
                "morning": "outputs/morning/morning-brief.json" if morning else None,
            },
        )

    def diff(self, prior: InstitutionalMemorySnapshot, current: InstitutionalMemorySnapshot) -> InstitutionalMemoryDelta:
        new_theses = sorted(set(current.top_thesis_ids) - set(prior.top_thesis_ids))
        removed_theses = sorted(set(prior.top_thesis_ids) - set(current.top_thesis_ids))
        new_findings = sorted(set(current.top_finding_ids) - set(prior.top_finding_ids))
        removed_findings = sorted(set(prior.top_finding_ids) - set(current.top_finding_ids))
        new_sources = sorted(set(current.source_document_references) - set(prior.source_document_references))
        removed_sources = sorted(set(prior.source_document_references) - set(current.source_document_references))
        return InstitutionalMemoryDelta(
            prior_snapshot_id=prior.snapshot_id,
            current_snapshot_id=current.snapshot_id,
            evidence_count_change=current.evidence_count - prior.evidence_count,
            graph_node_change=current.graph_node_count - prior.graph_node_count,
            graph_edge_change=current.graph_edge_count - prior.graph_edge_count,
            findings_count_change=current.findings_count - prior.findings_count,
            thesis_count_change=current.thesis_count - prior.thesis_count,
            new_thesis_ids=new_theses,
            removed_thesis_ids=removed_theses,
            new_finding_ids=new_findings,
            removed_finding_ids=removed_findings,
            new_source_references=new_sources,
            removed_source_references=removed_sources,
            summary=_delta_summary(prior, current, new_theses, new_findings, new_sources),
            limitations=["Delta compares captured snapshot fields only; it does not infer semantic meaning."],
        )


class InstitutionalMemoryStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "outputs" / "memory"
        self.snapshots_path = self.directory / "snapshots.json"
        self.latest_snapshot_path = self.directory / "latest-snapshot.json"
        self.latest_delta_path = self.directory / "latest-delta.json"
        self.markdown_path = self.directory / "institutional-memory.md"

    def create_snapshot(self, label: str | None = None) -> InstitutionalMemorySnapshot:
        snapshot = InstitutionalMemoryEngine(self.root).snapshot(label)
        snapshots = self.list_snapshots()
        snapshots.append(snapshot)
        self._write_snapshots(snapshots)
        write_json(self.latest_snapshot_path, snapshot.to_dict())
        self.export()
        return snapshot

    def list_snapshots(self) -> list[InstitutionalMemorySnapshot]:
        if not self.snapshots_path.exists():
            return []
        data = read_json(self.snapshots_path)
        return [InstitutionalMemorySnapshot.from_dict(item) for item in data.get("snapshots", []) if isinstance(item, dict)]

    def show_snapshot(self, snapshot_id: str) -> InstitutionalMemorySnapshot:
        for snapshot in self.list_snapshots():
            if snapshot.snapshot_id == snapshot_id:
                return snapshot
        raise InstitutionalMemoryError(f"Unknown institutional memory snapshot: {snapshot_id}")

    def diff(self, snapshot_id_a: str | None = None, snapshot_id_b: str | None = None) -> InstitutionalMemoryDelta:
        snapshots = self.list_snapshots()
        if snapshot_id_a is None and snapshot_id_b is None:
            if len(snapshots) < 2:
                raise InstitutionalMemoryError("At least two snapshots are required for diff.")
            prior, current = snapshots[-2], snapshots[-1]
        elif snapshot_id_a is not None and snapshot_id_b is not None:
            prior = self.show_snapshot(snapshot_id_a)
            current = self.show_snapshot(snapshot_id_b)
        else:
            raise InstitutionalMemoryError("Provide both snapshot IDs or neither.")
        delta = InstitutionalMemoryEngine(self.root).diff(prior, current)
        write_json(self.latest_delta_path, delta.to_dict())
        self.export()
        return delta

    def export(self) -> Path:
        snapshots = self.list_snapshots()
        delta = None
        if self.latest_delta_path.exists():
            delta = InstitutionalMemoryDelta.from_dict(read_json(self.latest_delta_path))
        self.markdown_path.parent.mkdir(parents=True, exist_ok=True)
        self.markdown_path.write_text(render_institutional_memory_markdown(snapshots, delta), encoding="utf-8")
        return self.markdown_path

    def _write_snapshots(self, snapshots: list[InstitutionalMemorySnapshot]) -> None:
        write_json(self.snapshots_path, {"snapshots": [snapshot.to_dict() for snapshot in snapshots]})


def render_institutional_memory_markdown(snapshots: list[InstitutionalMemorySnapshot], delta: InstitutionalMemoryDelta | None = None) -> str:
    lines = ["# Institutional Memory", "", f"Snapshots: {len(snapshots)}", ""]
    for snapshot in snapshots:
        lines.extend(
            [
                f"## {snapshot.snapshot_id}",
                "",
                f"- Label: `{snapshot.label or ''}`",
                f"- Created: `{snapshot.created_at}`",
                f"- Evidence: {snapshot.evidence_count}",
                f"- Graph nodes: {snapshot.graph_node_count}",
                f"- Graph edges: {snapshot.graph_edge_count}",
                f"- Findings: {snapshot.findings_count}",
                f"- Theses: {snapshot.thesis_count}",
                f"- Intelligence brief: `{snapshot.intelligence_brief_id or ''}`",
                f"- Morning brief: `{snapshot.morning_brief_id or ''}`",
                "",
            ]
        )
    if delta is not None:
        lines.extend(
            [
                "## Latest Delta",
                "",
                f"- Prior: `{delta.prior_snapshot_id}`",
                f"- Current: `{delta.current_snapshot_id}`",
                f"- Evidence change: {delta.evidence_count_change}",
                f"- Graph node change: {delta.graph_node_change}",
                f"- Graph edge change: {delta.graph_edge_change}",
                f"- Findings change: {delta.findings_count_change}",
                f"- Thesis change: {delta.thesis_count_change}",
                "",
                delta.summary,
                "",
            ]
        )
    return "\n".join(lines)


def _drive_counts(manifest: JsonMap | None) -> JsonMap:
    if not manifest:
        return {"downloaded": 0, "skipped": 0, "duplicates": 0, "errors": 0}
    return {
        "downloaded": len(_list(manifest.get("downloaded_files"))),
        "skipped": len(_list(manifest.get("skipped_files"))),
        "duplicates": len(_list(manifest.get("duplicate_files"))),
        "errors": len(_list(manifest.get("errors"))),
    }


def _snapshot_limitations(intake, drive, evidence, nodes, findings, theses, intelligence, morning) -> list[str]:
    limitations = ["Snapshot records current local deterministic artifacts only."]
    for present, message in [
        (intake, "No intake manifest found."),
        (drive, "No Google Drive sync manifest found."),
        (evidence, "No evidence records found."),
        (nodes, "No knowledge graph nodes found."),
        (findings, "No cross-document findings found."),
        (theses, "No institutional theses found."),
        (intelligence, "No institutional intelligence brief found."),
        (morning, "No morning brief found."),
    ]:
        if not present:
            limitations.append(message)
    return limitations


def _read_evidence_records(root: Path) -> list[JsonMap]:
    directory = root / "memory" / "evidence"
    if not directory.exists():
        return []
    records = []
    for path in sorted(directory.glob("ev_*.json")):
        try:
            records.append(read_json(path))
        except Exception:
            continue
    return records


def _read_artifact_references(root: Path) -> list[str]:
    references = []
    for path in sorted((root / "logs" / "runs").glob("run_*/artifacts/*.json")):
        try:
            artifact = read_json(path)
        except Exception:
            continue
        artifact_id = artifact.get("artifact_id")
        if isinstance(artifact_id, str):
            references.append(artifact_id)
    return sorted(set(references))


def _source_references(evidence: list[JsonMap], nodes: list[JsonMap], theses: list[JsonMap], findings: list[JsonMap]) -> list[str]:
    refs = set()
    for record in evidence:
        if isinstance(record.get("source_identifier"), str):
            refs.add(record["source_identifier"])
    for collection in [nodes, theses, findings]:
        for item in collection:
            for source_id in _string_list(item.get("source_ids", [])):
                refs.add(source_id)
    return sorted(refs)


def _top_ids(items: list[JsonMap], id_key: str, confidence_key: str) -> list[str]:
    sorted_items = sorted(items, key=lambda item: (_confidence_rank(str(item.get(confidence_key))), str(item.get(id_key))))
    return [str(item[id_key]) for item in sorted_items[:10] if isinstance(item.get(id_key), str)]


def _snapshot_id(label, evidence, nodes, edges, findings, theses, intelligence, morning, sources) -> str:
    fingerprint = "|".join(
        [
            str(label or ""),
            ",".join(sorted(str(item.get("evidence_id")) for item in evidence)),
            ",".join(sorted(str(item.get("node_id")) for item in nodes)),
            ",".join(sorted(str(item.get("edge_id")) for item in edges)),
            ",".join(sorted(str(item.get("finding_id")) for item in findings)),
            ",".join(sorted(str(item.get("thesis_id")) for item in theses)),
            str(_map(intelligence).get("brief_id")),
            str(_map(morning).get("brief_id")),
            ",".join(sources),
        ]
    )
    return f"snapshot_{sha256(fingerprint.encode('utf-8')).hexdigest()[:16]}"


def _delta_summary(prior, current, new_theses, new_findings, new_sources) -> str:
    return (
        f"Compared `{prior.snapshot_id}` to `{current.snapshot_id}`: "
        f"evidence {current.evidence_count - prior.evidence_count:+}, "
        f"graph nodes {current.graph_node_count - prior.graph_node_count:+}, "
        f"findings {current.findings_count - prior.findings_count:+}, "
        f"theses {current.thesis_count - prior.thesis_count:+}. "
        f"New theses: {len(new_theses)}; new findings: {len(new_findings)}; new sources: {len(new_sources)}."
    )


def _read_optional_json(path: Path) -> JsonMap | None:
    if not path.exists():
        return None
    try:
        return read_json(path)
    except Exception:
        return None


def _confidence_rank(value: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(value, 3)


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


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _require_str(data: JsonMap, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise InstitutionalMemoryError(f"Institutional memory field {key} must be a string")
    return value
