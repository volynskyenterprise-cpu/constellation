from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any

from .cross_document import CrossDocumentAnalysisStore, CrossDocumentError
from .evidence import EvidenceStore
from .io import read_json, write_json
from .memory import InstitutionalMemoryError, InstitutionalMemoryStore
from .models import JsonMap, utc_now_iso
from .morning import MorningExecutiveError, MorningExecutiveStore
from .thesis import ThesisError, ThesisStore


class EvidenceGraphError(RuntimeError):
    pass


@dataclass(frozen=True)
class EvidenceGraphNode:
    node_id: str
    node_type: str
    label: str
    references: list[str] = field(default_factory=list)
    metadata: JsonMap = field(default_factory=dict)

    def to_dict(self) -> JsonMap:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "label": self.label,
            "references": self.references,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "EvidenceGraphNode":
        return cls(
            node_id=_require_str(data, "node_id"),
            node_type=_require_str(data, "node_type"),
            label=_require_str(data, "label"),
            references=_string_list(data.get("references", [])),
            metadata=_map(data.get("metadata")),
        )


@dataclass(frozen=True)
class EvidenceGraphEdge:
    edge_id: str
    source_node_id: str
    target_node_id: str
    edge_type: str
    evidence_ids: list[str]
    metadata: JsonMap

    def to_dict(self) -> JsonMap:
        return {
            "edge_id": self.edge_id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "edge_type": self.edge_type,
            "evidence_ids": self.evidence_ids,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "EvidenceGraphEdge":
        return cls(
            edge_id=_require_str(data, "edge_id"),
            source_node_id=_require_str(data, "source_node_id"),
            target_node_id=_require_str(data, "target_node_id"),
            edge_type=_require_str(data, "edge_type"),
            evidence_ids=_string_list(data.get("evidence_ids", [])),
            metadata=_map(data.get("metadata")),
        )


@dataclass
class EvidenceGraph:
    graph_id: str
    created_at: str
    nodes: dict[str, EvidenceGraphNode] = field(default_factory=dict)
    edges: dict[str, EvidenceGraphEdge] = field(default_factory=dict)
    limitations: list[str] = field(default_factory=list)
    provenance: JsonMap = field(default_factory=dict)

    def add_node(self, node: EvidenceGraphNode) -> None:
        self.nodes.setdefault(node.node_id, node)

    def add_edge(
        self,
        *,
        source_node_id: str,
        target_node_id: str,
        edge_type: str,
        evidence_ids: list[str] | None = None,
        metadata: JsonMap | None = None,
    ) -> None:
        if source_node_id not in self.nodes or target_node_id not in self.nodes:
            return
        evidence = sorted(set(evidence_ids or []))
        edge_id = _edge_id(source_node_id, edge_type, target_node_id, evidence)
        self.edges.setdefault(
            edge_id,
            EvidenceGraphEdge(
                edge_id=edge_id,
                source_node_id=source_node_id,
                target_node_id=target_node_id,
                edge_type=edge_type,
                evidence_ids=evidence,
                metadata=metadata or {},
            ),
        )

    def list_nodes(self) -> list[EvidenceGraphNode]:
        return sorted(self.nodes.values(), key=lambda item: (item.node_type, item.label, item.node_id))

    def list_edges(self) -> list[EvidenceGraphEdge]:
        return sorted(self.edges.values(), key=lambda item: (item.edge_type, item.source_node_id, item.target_node_id, item.edge_id))

    def to_dict(self) -> JsonMap:
        return {
            "graph_id": self.graph_id,
            "created_at": self.created_at,
            "node_count": len(self.nodes),
            "edge_count": len(self.edges),
            "nodes": [node.to_dict() for node in self.list_nodes()],
            "edges": [edge.to_dict() for edge in self.list_edges()],
            "limitations": self.limitations,
            "provenance": self.provenance,
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "EvidenceGraph":
        graph = cls(
            graph_id=_require_str(data, "graph_id"),
            created_at=_require_str(data, "created_at"),
            limitations=_string_list(data.get("limitations", [])),
            provenance=_map(data.get("provenance")),
        )
        for node in _map_list(data.get("nodes", [])):
            graph.add_node(EvidenceGraphNode.from_dict(node))
        for edge in _map_list(data.get("edges", [])):
            parsed = EvidenceGraphEdge.from_dict(edge)
            graph.edges[parsed.edge_id] = parsed
        return graph


class EvidenceGraphBuilder:
    def __init__(self, root: Path) -> None:
        self.root = root

    def build(self) -> EvidenceGraph:
        evidence = EvidenceStore(self.root).list()
        artifacts = _read_artifacts(self.root)
        findings = _read_findings(self.root)
        theses = _read_theses(self.root)
        morning = _read_morning(self.root)
        snapshots = _read_snapshots(self.root)
        graph = EvidenceGraph(
            graph_id=_graph_id(evidence, artifacts, findings, theses, morning, snapshots),
            created_at=utc_now_iso(),
            limitations=_limitations(evidence, artifacts, findings, theses, morning, snapshots),
            provenance={
                "evidence": "memory/evidence/",
                "artifacts": "logs/runs/*/artifacts/",
                "cross_document_analysis": "outputs/analysis/cross-document-analysis.json" if findings else None,
                "theses": "outputs/theses/theses.json" if theses else None,
                "morning": "outputs/morning/morning-brief.json" if morning else None,
                "institutional_memory": "outputs/memory/snapshots.json" if snapshots else None,
                "build_rule": "Exact IDs and explicit references only; no semantic inference.",
            },
        )
        self._add_nodes(graph, evidence, artifacts, findings, theses, morning, snapshots)
        self._add_edges(graph, evidence, artifacts, findings, theses, morning, snapshots)
        return graph

    def _add_nodes(
        self,
        graph: EvidenceGraph,
        evidence: list[JsonMap],
        artifacts: list[JsonMap],
        findings: list[JsonMap],
        theses: list[JsonMap],
        morning: JsonMap | None,
        snapshots: list[JsonMap],
    ) -> None:
        for record in evidence:
            evidence_id = _optional_str(record.get("evidence_id"))
            if evidence_id:
                graph.add_node(
                    EvidenceGraphNode(
                        node_id=_node_id("evidence", evidence_id),
                        node_type="evidence",
                        label=str(record.get("claim") or evidence_id),
                        references=[evidence_id],
                        metadata={
                            "workflow_run_id": record.get("workflow_run_id"),
                            "source_identifier": record.get("source_identifier"),
                            "source_location": record.get("source_location"),
                            "confidence": record.get("confidence"),
                        },
                    )
                )
                _add_source_node(graph, _optional_str(record.get("source_identifier")), "Evidence source_identifier")
                workflow_run_id = _optional_str(record.get("workflow_run_id"))
                if workflow_run_id:
                    _add_workflow_node(graph, workflow_run_id)
        for artifact in artifacts:
            artifact_id = _optional_str(artifact.get("artifact_id"))
            if artifact_id:
                graph.add_node(
                    EvidenceGraphNode(
                        node_id=_node_id("artifact", artifact_id),
                        node_type="artifact",
                        label=str(artifact.get("title") or artifact_id),
                        references=[artifact_id],
                        metadata={
                            "workflow_run_id": artifact.get("workflow_run_id"),
                            "workflow_id": artifact.get("workflow_id"),
                            "artifact_type": artifact.get("artifact_type"),
                            "path": artifact.get("_path"),
                        },
                    )
                )
                workflow_run_id = _optional_str(artifact.get("workflow_run_id"))
                if workflow_run_id:
                    _add_workflow_node(graph, workflow_run_id)
        for finding in findings:
            finding_id = _optional_str(finding.get("finding_id"))
            if finding_id:
                graph.add_node(
                    EvidenceGraphNode(
                        node_id=_node_id("finding", finding_id),
                        node_type="finding",
                        label=str(finding.get("title") or finding_id),
                        references=[finding_id],
                        metadata={"finding_type": finding.get("finding_type"), "confidence": finding.get("confidence")},
                    )
                )
            for source_id in _string_list(finding.get("source_ids", [])):
                _add_source_node(graph, source_id, "Finding source_ids")
            for workflow_run_id in _string_list(finding.get("workflow_run_ids", [])):
                _add_workflow_node(graph, workflow_run_id)
        for thesis in theses:
            thesis_id = _optional_str(thesis.get("thesis_id"))
            if thesis_id:
                graph.add_node(
                    EvidenceGraphNode(
                        node_id=_node_id("thesis", thesis_id),
                        node_type="thesis",
                        label=str(thesis.get("title") or thesis_id),
                        references=[thesis_id],
                        metadata={"thesis_type": thesis.get("thesis_type"), "status": thesis.get("status"), "confidence": thesis.get("confidence")},
                    )
                )
            for source_id in _string_list(thesis.get("source_ids", [])):
                _add_source_node(graph, source_id, "Thesis source_ids")
            for workflow_run_id in _string_list(thesis.get("workflow_run_ids", [])):
                _add_workflow_node(graph, workflow_run_id)
        if morning:
            brief_id = _optional_str(morning.get("brief_id"))
            if brief_id:
                graph.add_node(
                    EvidenceGraphNode(
                        node_id=_node_id("morning_brief", brief_id),
                        node_type="morning_brief",
                        label=brief_id,
                        references=[brief_id],
                        metadata={"created_at": morning.get("created_at")},
                    )
                )
            for document in _map_list(morning.get("new_documents_detected", [])):
                _add_source_node(graph, _optional_str(document.get("path")), "Morning new_documents_detected.path")
        for snapshot in snapshots:
            snapshot_id = _optional_str(snapshot.get("snapshot_id"))
            if snapshot_id:
                graph.add_node(
                    EvidenceGraphNode(
                        node_id=_node_id("memory_snapshot", snapshot_id),
                        node_type="memory_snapshot",
                        label=str(snapshot.get("label") or snapshot_id),
                        references=[snapshot_id],
                        metadata={"created_at": snapshot.get("created_at")},
                    )
                )
            for source_id in _string_list(snapshot.get("source_document_references", [])):
                _add_source_node(graph, source_id, "Snapshot source_document_references")

    def _add_edges(
        self,
        graph: EvidenceGraph,
        evidence: list[JsonMap],
        artifacts: list[JsonMap],
        findings: list[JsonMap],
        theses: list[JsonMap],
        morning: JsonMap | None,
        snapshots: list[JsonMap],
    ) -> None:
        for record in evidence:
            evidence_id = _optional_str(record.get("evidence_id"))
            if not evidence_id:
                continue
            evidence_node = _node_id("evidence", evidence_id)
            source = _optional_str(record.get("source_identifier"))
            if source:
                graph.add_edge(
                    source_node_id=evidence_node,
                    target_node_id=_node_id("source", source),
                    edge_type="derived_from",
                    evidence_ids=[evidence_id],
                    metadata={"reason": "Evidence record has exact source_identifier.", "relationship_basis": "exact_source_identifier"},
                )
            workflow_run_id = _optional_str(record.get("workflow_run_id"))
            if workflow_run_id:
                graph.add_edge(
                    source_node_id=evidence_node,
                    target_node_id=_node_id("workflow", workflow_run_id),
                    edge_type="appears_in",
                    evidence_ids=[evidence_id],
                    metadata={"reason": "Evidence record has exact workflow_run_id.", "relationship_basis": "exact_workflow_run_id"},
                )
        for artifact in artifacts:
            artifact_id = _optional_str(artifact.get("artifact_id"))
            if not artifact_id:
                continue
            for evidence_id in _artifact_evidence_ids(artifact):
                graph.add_edge(
                    source_node_id=_node_id("evidence", evidence_id),
                    target_node_id=_node_id("artifact", artifact_id),
                    edge_type="referenced_by",
                    evidence_ids=[evidence_id],
                    metadata={"reason": "Artifact evidence_used includes exact evidence ID.", "relationship_basis": "exact_evidence_id", "artifact_path": artifact.get("_path")},
                )
        for finding in findings:
            finding_id = _optional_str(finding.get("finding_id"))
            if not finding_id:
                continue
            finding_type = str(finding.get("finding_type") or "")
            relationship = "supports"
            if finding_type == "possible_contradiction":
                relationship = "conflicts_with"
            elif finding_type.startswith("repeated_"):
                relationship = "repeats"
            for evidence_id in _string_list(finding.get("evidence_ids", [])):
                graph.add_edge(
                    source_node_id=_node_id("evidence", evidence_id),
                    target_node_id=_node_id("finding", finding_id),
                    edge_type=relationship,
                    evidence_ids=[evidence_id],
                    metadata={"reason": "Finding evidence_ids includes exact evidence ID.", "relationship_basis": "exact_evidence_id", "finding_type": finding_type},
                )
        for thesis in theses:
            thesis_id = _optional_str(thesis.get("thesis_id"))
            if not thesis_id:
                continue
            for evidence_id in _string_list(thesis.get("supporting_evidence_ids", [])):
                graph.add_edge(
                    source_node_id=_node_id("evidence", evidence_id),
                    target_node_id=_node_id("thesis", thesis_id),
                    edge_type="supports",
                    evidence_ids=[evidence_id],
                    metadata={"reason": "Thesis supporting_evidence_ids includes exact evidence ID.", "relationship_basis": "exact_evidence_id"},
                )
            for finding_id in _string_list(thesis.get("supporting_finding_ids", [])):
                graph.add_edge(
                    source_node_id=_node_id("finding", finding_id),
                    target_node_id=_node_id("thesis", thesis_id),
                    edge_type="contributes_to",
                    evidence_ids=_string_list(thesis.get("supporting_evidence_ids", [])),
                    metadata={"reason": "Thesis supporting_finding_ids includes exact finding ID.", "relationship_basis": "exact_finding_id"},
                )
            for finding_id in _string_list(thesis.get("counterpoint_finding_ids", [])):
                graph.add_edge(
                    source_node_id=_node_id("finding", finding_id),
                    target_node_id=_node_id("thesis", thesis_id),
                    edge_type="conflicts_with",
                    evidence_ids=[],
                    metadata={"reason": "Thesis counterpoint_finding_ids includes exact finding ID.", "relationship_basis": "exact_counterpoint_finding_id"},
                )
        if morning:
            brief_id = _optional_str(morning.get("brief_id"))
            if brief_id:
                for thesis_ref in _map_list(morning.get("top_theses", [])):
                    thesis_id = _optional_str(thesis_ref.get("thesis_id"))
                    if thesis_id:
                        graph.add_edge(
                            source_node_id=_node_id("thesis", thesis_id),
                            target_node_id=_node_id("morning_brief", brief_id),
                            edge_type="summarized_by",
                            evidence_ids=[],
                            metadata={"reason": "Morning brief top_theses includes exact thesis ID.", "relationship_basis": "exact_thesis_id"},
                        )
                for document in _map_list(morning.get("new_documents_detected", [])):
                    source_path = _optional_str(document.get("path"))
                    if source_path:
                        graph.add_edge(
                            source_node_id=_node_id("source", source_path),
                            target_node_id=_node_id("morning_brief", brief_id),
                            edge_type="summarized_by",
                            evidence_ids=[],
                            metadata={"reason": "Morning brief new_documents_detected includes exact source path.", "relationship_basis": "exact_source_path"},
                        )
        for snapshot in snapshots:
            snapshot_id = _optional_str(snapshot.get("snapshot_id"))
            if not snapshot_id:
                continue
            for thesis_id in _string_list(snapshot.get("top_thesis_ids", [])):
                graph.add_edge(
                    source_node_id=_node_id("thesis", thesis_id),
                    target_node_id=_node_id("memory_snapshot", snapshot_id),
                    edge_type="preserved_in",
                    evidence_ids=[],
                    metadata={"reason": "Memory snapshot top_thesis_ids includes exact thesis ID.", "relationship_basis": "exact_thesis_id"},
                )
            for source_id in _string_list(snapshot.get("source_document_references", [])):
                graph.add_edge(
                    source_node_id=_node_id("source", source_id),
                    target_node_id=_node_id("memory_snapshot", snapshot_id),
                    edge_type="preserved_in",
                    evidence_ids=[],
                    metadata={"reason": "Memory snapshot source_document_references includes exact source reference.", "relationship_basis": "exact_source_reference"},
                )


class EvidenceGraphStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "outputs" / "evidence-graph"
        self.graph_path = self.directory / "evidence-graph.json"
        self.markdown_path = self.directory / "evidence-graph.md"

    def build(self) -> EvidenceGraph:
        graph = EvidenceGraphBuilder(self.root).build()
        self.save(graph)
        return graph

    def save(self, graph: EvidenceGraph) -> None:
        write_json(self.graph_path, graph.to_dict())
        self.export(graph)

    def load(self) -> EvidenceGraph:
        if not self.graph_path.exists():
            raise EvidenceGraphError("No evidence graph found. Run evidence-graph build first.")
        data = read_json(self.graph_path)
        if not isinstance(data, dict):
            raise EvidenceGraphError("Evidence graph file is corrupt.")
        return EvidenceGraph.from_dict(data)

    def show(self, item_id: str) -> JsonMap:
        graph = self.load()
        if item_id in graph.nodes:
            return graph.nodes[item_id].to_dict()
        if item_id in graph.edges:
            return graph.edges[item_id].to_dict()
        for node in graph.nodes.values():
            if item_id in node.references:
                return node.to_dict()
        raise EvidenceGraphError(f"Unknown evidence graph node or edge: {item_id}")

    def export(self, graph: EvidenceGraph | None = None) -> Path:
        graph = graph or self.load()
        self.markdown_path.parent.mkdir(parents=True, exist_ok=True)
        self.markdown_path.write_text(render_evidence_graph_markdown(graph), encoding="utf-8")
        return self.markdown_path


def render_evidence_graph_markdown(graph: EvidenceGraph) -> str:
    node_counts = _counts_by([node.node_type for node in graph.nodes.values()])
    edge_counts = _counts_by([edge.edge_type for edge in graph.edges.values()])
    lines = [
        "# Evidence Graph",
        "",
        f"Graph ID: `{graph.graph_id}`",
        f"Created: `{graph.created_at}`",
        f"Nodes: {len(graph.nodes)}",
        f"Edges: {len(graph.edges)}",
        "",
        "## Counts By Node Type",
        "",
        *_count_lines(node_counts),
        "## Counts By Edge Type",
        "",
        *_count_lines(edge_counts),
        "## Top Evidence-Connected Theses",
        "",
        *_thesis_connection_lines(graph),
        "## Evidence-To-Thesis Paths",
        "",
        *_evidence_to_thesis_lines(graph),
        "## Orphan Evidence Records",
        "",
        *_orphan_evidence_lines(graph),
        "## Orphan Theses",
        "",
        *_orphan_thesis_lines(graph),
        "## Limitations",
        "",
        *_string_lines(graph.limitations),
    ]
    return "\n".join(lines)


def _read_artifacts(root: Path) -> list[JsonMap]:
    artifacts: list[JsonMap] = []
    for path in sorted((root / "logs" / "runs").glob("run_*/artifacts/*.json")):
        try:
            record = read_json(path)
        except Exception:
            continue
        if isinstance(record, dict):
            artifacts.append({**record, "_path": str(path.relative_to(root))})
    return sorted(artifacts, key=lambda item: str(item.get("artifact_id", "")))


def _read_findings(root: Path) -> list[JsonMap]:
    try:
        return [finding.to_dict() for finding in CrossDocumentAnalysisStore(root).list_findings()]
    except CrossDocumentError:
        return []


def _read_theses(root: Path) -> list[JsonMap]:
    try:
        return [thesis.to_dict() for thesis in ThesisStore(root).load()]
    except ThesisError:
        return []


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


def _add_source_node(graph: EvidenceGraph, source_id: str | None, reason: str) -> None:
    if not source_id:
        return
    graph.add_node(
        EvidenceGraphNode(
            node_id=_node_id("source", source_id),
            node_type="source",
            label=source_id,
            references=[source_id],
            metadata={"source_reference_basis": reason},
        )
    )


def _add_workflow_node(graph: EvidenceGraph, workflow_run_id: str) -> None:
    graph.add_node(
        EvidenceGraphNode(
            node_id=_node_id("workflow", workflow_run_id),
            node_type="workflow",
            label=workflow_run_id,
            references=[workflow_run_id],
            metadata={"reference_type": "workflow_run_id"},
        )
    )


def _artifact_evidence_ids(artifact: JsonMap) -> list[str]:
    ids: list[str] = []
    for item in _list(artifact.get("evidence_used", [])):
        if isinstance(item, dict) and item.get("type") == "evidence" and isinstance(item.get("id"), str):
            ids.append(item["id"])
        elif isinstance(item, str) and item.startswith("ev_"):
            ids.append(item)
    return sorted(set(ids))


def _graph_id(evidence: list[JsonMap], artifacts: list[JsonMap], findings: list[JsonMap], theses: list[JsonMap], morning: JsonMap | None, snapshots: list[JsonMap]) -> str:
    fingerprint = "|".join(
        [
            ",".join(sorted(str(item.get("evidence_id")) for item in evidence)),
            ",".join(sorted(str(item.get("artifact_id")) for item in artifacts)),
            ",".join(sorted(str(item.get("finding_id")) for item in findings)),
            ",".join(sorted(str(item.get("thesis_id")) for item in theses)),
            str(_map(morning).get("brief_id")),
            ",".join(sorted(str(item.get("snapshot_id")) for item in snapshots)),
        ]
    )
    return f"evidence_graph_{sha256(fingerprint.encode('utf-8')).hexdigest()[:16]}"


def _limitations(evidence: list[JsonMap], artifacts: list[JsonMap], findings: list[JsonMap], theses: list[JsonMap], morning: JsonMap | None, snapshots: list[JsonMap]) -> list[str]:
    limitations = [
        "Evidence Graph uses exact IDs and explicit source references only.",
        "No semantic similarity, embeddings, provider calls, or LLM inference are used.",
        "Unproven relationships are omitted rather than inferred.",
    ]
    for present, message in [
        (evidence, "No evidence records found."),
        (artifacts, "No structured artifacts found."),
        (findings, "No cross-document findings found."),
        (theses, "No institutional theses found."),
        (morning, "No morning brief found."),
        (snapshots, "No institutional memory snapshots found."),
    ]:
        if not present:
            limitations.append(message)
    return limitations


def _node_id(node_type: str, reference: str) -> str:
    if node_type in {"evidence", "workflow", "artifact", "finding", "thesis", "morning_brief", "memory_snapshot"}:
        return f"eg_{node_type}_{reference}"
    return f"eg_{node_type}_{sha256(reference.encode('utf-8')).hexdigest()[:16]}"


def _edge_id(source_node_id: str, edge_type: str, target_node_id: str, evidence_ids: list[str]) -> str:
    digest = sha256(f"{source_node_id}|{edge_type}|{target_node_id}|{','.join(evidence_ids)}".encode("utf-8")).hexdigest()[:16]
    return f"eg_edge_{digest}"


def _counts_by(values: list[str]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return dict(sorted(counts.items()))


def _count_lines(counts: dict[str, int]) -> list[str]:
    if not counts:
        return ["- None", ""]
    return [*[f"- {key}: {value}" for key, value in counts.items()], ""]


def _thesis_connection_lines(graph: EvidenceGraph) -> list[str]:
    counts: dict[str, int] = {}
    for edge in graph.edges.values():
        if edge.edge_type == "supports" and edge.target_node_id.startswith("eg_thesis_"):
            counts[edge.target_node_id] = counts.get(edge.target_node_id, 0) + len(edge.evidence_ids or [""])
    if not counts:
        return ["- None", ""]
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0]))[:10]
    return [*[f"- `{node_id}`: {count} evidence connection(s)" for node_id, count in ranked], ""]


def _evidence_to_thesis_lines(graph: EvidenceGraph) -> list[str]:
    paths = []
    for edge in graph.list_edges():
        if edge.edge_type == "supports" and edge.source_node_id.startswith("eg_evidence_") and edge.target_node_id.startswith("eg_thesis_"):
            paths.append(f"- `{edge.source_node_id}` -> `{edge.target_node_id}` via `{edge.edge_id}`")
    return [*paths, ""] if paths else ["- None", ""]


def _orphan_evidence_lines(graph: EvidenceGraph) -> list[str]:
    connected = {
        edge.source_node_id
        for edge in graph.edges.values()
        if edge.source_node_id.startswith("eg_evidence_") and edge.edge_type in {"supports", "conflicts_with", "repeats", "referenced_by"}
    }
    orphans = [node.node_id for node in graph.list_nodes() if node.node_type == "evidence" and node.node_id not in connected]
    return [*[f"- `{node_id}`" for node_id in orphans], ""] if orphans else ["- None", ""]


def _orphan_thesis_lines(graph: EvidenceGraph) -> list[str]:
    supported = {
        edge.target_node_id
        for edge in graph.edges.values()
        if edge.target_node_id.startswith("eg_thesis_") and edge.edge_type in {"supports", "contributes_to"}
    }
    orphans = [node.node_id for node in graph.list_nodes() if node.node_type == "thesis" and node.node_id not in supported]
    return [*[f"- `{node_id}`" for node_id in orphans], ""] if orphans else ["- None", ""]


def _string_lines(items: list[str]) -> list[str]:
    if not items:
        return ["- None", ""]
    return [*[f"- {item}" for item in items], ""]


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
    return value if isinstance(value, str) and value else None


def _require_str(data: JsonMap, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise EvidenceGraphError(f"Evidence graph field {key} must be a string")
    return value
