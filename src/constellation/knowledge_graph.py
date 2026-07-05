from __future__ import annotations

from dataclasses import dataclass, field
from hashlib import sha256
from pathlib import Path
from typing import Any

from .artifacts import ArtifactStore
from .evidence import EvidenceStore
from .io import read_json, write_json
from .memory import MemoryManager
from .models import JsonMap, utc_now_iso
from .state import WorkflowStateStore


class KnowledgeGraphError(RuntimeError):
    pass


SUPPORTED_NODE_TYPES = {
    "evidence",
    "concept",
    "topic",
    "theme",
    "workflow",
    "artifact",
    "source",
    "assumption",
    "risk",
    "recommendation",
}

SUPPORTED_RELATIONSHIP_TYPES = {
    "supports",
    "contradicts",
    "relates_to",
    "derived_from",
    "references",
    "strengthens",
    "weakens",
    "updates",
    "supersedes",
    "depends_on",
    "produces",
    "belongs_to",
}


@dataclass(frozen=True)
class GraphNode:
    node_id: str
    node_type: str
    label: str
    description: str
    source_ids: list[str]
    evidence_ids: list[str]
    artifact_ids: list[str]
    workflow_run_ids: list[str]
    confidence: str
    metadata: JsonMap
    created_at: str
    updated_at: str

    def to_dict(self) -> JsonMap:
        return {
            "node_id": self.node_id,
            "node_type": self.node_type,
            "label": self.label,
            "description": self.description,
            "source_ids": self.source_ids,
            "evidence_ids": self.evidence_ids,
            "artifact_ids": self.artifact_ids,
            "workflow_run_ids": self.workflow_run_ids,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass(frozen=True)
class GraphEdge:
    edge_id: str
    source_node_id: str
    target_node_id: str
    relationship_type: str
    evidence_ids: list[str]
    confidence: str
    metadata: JsonMap
    created_at: str
    updated_at: str

    def to_dict(self) -> JsonMap:
        return {
            "edge_id": self.edge_id,
            "source_node_id": self.source_node_id,
            "target_node_id": self.target_node_id,
            "relationship_type": self.relationship_type,
            "evidence_ids": self.evidence_ids,
            "confidence": self.confidence,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class KnowledgeGraph:
    nodes: dict[str, GraphNode] = field(default_factory=dict)
    edges: dict[str, GraphEdge] = field(default_factory=dict)

    def add_node(self, node: GraphNode) -> None:
        _validate_node_type(node.node_type)
        existing = self.nodes.get(node.node_id)
        if existing is not None:
            node = GraphNode(
                node_id=node.node_id,
                node_type=node.node_type,
                label=node.label,
                description=node.description,
                source_ids=_merge(existing.source_ids, node.source_ids),
                evidence_ids=_merge(existing.evidence_ids, node.evidence_ids),
                artifact_ids=_merge(existing.artifact_ids, node.artifact_ids),
                workflow_run_ids=_merge(existing.workflow_run_ids, node.workflow_run_ids),
                confidence=node.confidence,
                metadata={**existing.metadata, **node.metadata},
                created_at=existing.created_at,
                updated_at=node.updated_at,
            )
        self.nodes[node.node_id] = node

    def add_edge(self, edge: GraphEdge) -> None:
        _validate_relationship_type(edge.relationship_type)
        existing = self.edges.get(edge.edge_id)
        if existing is not None:
            edge = GraphEdge(
                edge_id=edge.edge_id,
                source_node_id=edge.source_node_id,
                target_node_id=edge.target_node_id,
                relationship_type=edge.relationship_type,
                evidence_ids=_merge(existing.evidence_ids, edge.evidence_ids),
                confidence=edge.confidence,
                metadata={**existing.metadata, **edge.metadata},
                created_at=existing.created_at,
                updated_at=edge.updated_at,
            )
        self.edges[edge.edge_id] = edge

    def list_nodes(self) -> list[GraphNode]:
        return sorted(self.nodes.values(), key=lambda node: (node.node_type, node.label, node.node_id))

    def list_edges(self) -> list[GraphEdge]:
        return sorted(self.edges.values(), key=lambda edge: (edge.relationship_type, edge.source_node_id, edge.target_node_id))

    def get_node(self, node_id: str) -> GraphNode:
        try:
            return self.nodes[node_id]
        except KeyError as exc:
            raise KnowledgeGraphError(f"Unknown graph node: {node_id}") from exc

    def get_edge(self, edge_id: str) -> GraphEdge:
        try:
            return self.edges[edge_id]
        except KeyError as exc:
            raise KnowledgeGraphError(f"Unknown graph edge: {edge_id}") from exc

    def find_nodes(self, *, node_type: str | None = None, label_contains: str | None = None) -> list[GraphNode]:
        nodes = self.list_nodes()
        if node_type is not None:
            nodes = [node for node in nodes if node.node_type == node_type]
        if label_contains is not None:
            needle = label_contains.lower()
            nodes = [node for node in nodes if needle in node.label.lower()]
        return nodes

    def find_edges(self, *, relationship_type: str | None = None, node_id: str | None = None) -> list[GraphEdge]:
        edges = self.list_edges()
        if relationship_type is not None:
            edges = [edge for edge in edges if edge.relationship_type == relationship_type]
        if node_id is not None:
            edges = [edge for edge in edges if edge.source_node_id == node_id or edge.target_node_id == node_id]
        return edges

    def to_dict(self) -> JsonMap:
        return {
            "nodes": [node.to_dict() for node in self.list_nodes()],
            "edges": [edge.to_dict() for edge in self.list_edges()],
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "KnowledgeGraph":
        graph = cls()
        for node_data in data.get("nodes", []):
            if isinstance(node_data, dict):
                graph.add_node(_node_from_dict(node_data))
        for edge_data in data.get("edges", []):
            if isinstance(edge_data, dict):
                graph.add_edge(_edge_from_dict(edge_data))
        return graph

    def export_markdown(self) -> str:
        lines = [
            "# Knowledge Graph",
            "",
            f"Nodes: {len(self.nodes)}",
            f"Edges: {len(self.edges)}",
            "",
            "## Nodes",
            "",
        ]
        for node in self.list_nodes():
            lines.extend(
                [
                    f"### {node.label}",
                    "",
                    f"- ID: `{node.node_id}`",
                    f"- Type: `{node.node_type}`",
                    f"- Confidence: `{node.confidence}`",
                    f"- Evidence: {', '.join(node.evidence_ids) if node.evidence_ids else 'None'}",
                    f"- Workflows: {', '.join(node.workflow_run_ids) if node.workflow_run_ids else 'None'}",
                    "",
                    node.description or "No description.",
                    "",
                ]
            )
        lines.extend(["## Edges", ""])
        for edge in self.list_edges():
            lines.extend(
                [
                    f"- `{edge.edge_id}`: `{edge.source_node_id}` --{edge.relationship_type}--> `{edge.target_node_id}`",
                ]
            )
        return "\n".join(lines)


class KnowledgeGraphStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "memory" / "graph"
        self.graph_path = self.directory / "graph.json"

    def load(self) -> KnowledgeGraph:
        if not self.graph_path.exists():
            return KnowledgeGraph()
        data = read_json(self.graph_path)
        return KnowledgeGraph.from_dict(data)

    def save(self, graph: KnowledgeGraph) -> Path:
        write_json(self.graph_path, graph.to_dict())
        return self.graph_path

    def export(self, output_path: Path | None = None) -> Path:
        graph = self.load()
        if output_path is None:
            output_path = self.root / "outputs" / "graph" / "knowledge-graph.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(graph.export_markdown(), encoding="utf-8")
        return output_path


class KnowledgeGraphBuilder:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.store = KnowledgeGraphStore(root)

    def build_run(self, workflow_run_id: str) -> KnowledgeGraph:
        state = WorkflowStateStore(self.root).load(workflow_run_id)
        graph = self.store.load()
        now = utc_now_iso()
        workflow_node_id = _node_id("workflow", workflow_run_id)
        graph.add_node(
            GraphNode(
                node_id=workflow_node_id,
                node_type="workflow",
                label=f"{state.workflow_id} ({workflow_run_id})",
                description=f"Workflow run {workflow_run_id} with status {state.status}.",
                source_ids=[],
                evidence_ids=[],
                artifact_ids=[],
                workflow_run_ids=[workflow_run_id],
                confidence="system_record",
                metadata={"workflow_id": state.workflow_id, "status": state.status},
                created_at=now,
                updated_at=now,
            )
        )

        evidence_records = EvidenceStore(self.root).list(workflow_run_id)
        source_node_ids: dict[str, str] = {}
        for evidence in evidence_records:
            evidence_id = _require_str(evidence, "evidence_id")
            evidence_node_id = _node_id("evidence", evidence_id)
            source_identifier = str(evidence.get("source_identifier", "unknown"))
            source_node_id = source_node_ids.setdefault(source_identifier, _node_id("source", source_identifier))
            graph.add_node(_source_node(source_node_id, source_identifier, workflow_run_id, now))
            graph.add_node(_evidence_node(evidence_node_id, evidence, workflow_run_id, now))
            graph.add_edge(_edge(evidence_node_id, source_node_id, "derived_from", [evidence_id], now))
            graph.add_edge(_edge(workflow_node_id, evidence_node_id, "references", [evidence_id], now))
            for extracted in _deterministic_nodes_from_evidence(evidence, workflow_run_id, now):
                graph.add_node(extracted)
                graph.add_edge(_edge(extracted.node_id, evidence_node_id, "derived_from", [evidence_id], now))
                graph.add_edge(_edge(extracted.node_id, source_node_id, "derived_from", [evidence_id], now))

        working_memory = _read_working_memory(self.root, workflow_run_id)
        artifact_records = _artifact_records(self.root, workflow_run_id, working_memory)
        for artifact in artifact_records:
            artifact_id = str(artifact.get("artifact_id") or f"artifact_{workflow_run_id}_{artifact.get('artifact_type', 'unknown')}")
            artifact_node_id = _node_id("artifact", artifact_id)
            evidence_ids = _artifact_evidence_ids(artifact)
            graph.add_node(
                GraphNode(
                    node_id=artifact_node_id,
                    node_type="artifact",
                    label=str(artifact.get("title") or artifact.get("artifact_type") or artifact_id),
                    description=str(artifact.get("summary") or ""),
                    source_ids=[],
                    evidence_ids=evidence_ids,
                    artifact_ids=[artifact_id],
                    workflow_run_ids=[workflow_run_id],
                    confidence=str(artifact.get("confidence", "unknown")),
                    metadata={"artifact_type": artifact.get("artifact_type"), "status": artifact.get("status")},
                    created_at=now,
                    updated_at=now,
                )
            )
            graph.add_edge(_edge(workflow_node_id, artifact_node_id, "produces", evidence_ids, now))
            for evidence_id in evidence_ids:
                graph.add_edge(_edge(artifact_node_id, _node_id("evidence", evidence_id), "references", [evidence_id], now))

        self.store.save(graph)
        return graph


def show_graph_item(root: Path, item_id: str) -> JsonMap:
    graph = KnowledgeGraphStore(root).load()
    if item_id in graph.nodes:
        return graph.nodes[item_id].to_dict()
    if item_id in graph.edges:
        return graph.edges[item_id].to_dict()
    raise KnowledgeGraphError(f"Unknown graph node or edge: {item_id}")


def _source_node(node_id: str, source_identifier: str, workflow_run_id: str, now: str) -> GraphNode:
    return GraphNode(
        node_id=node_id,
        node_type="source",
        label=Path(source_identifier).name,
        description=source_identifier,
        source_ids=[source_identifier],
        evidence_ids=[],
        artifact_ids=[],
        workflow_run_ids=[workflow_run_id],
        confidence="source_provided",
        metadata={"source_identifier": source_identifier},
        created_at=now,
        updated_at=now,
    )


def _evidence_node(node_id: str, evidence: JsonMap, workflow_run_id: str, now: str) -> GraphNode:
    evidence_id = _require_str(evidence, "evidence_id")
    return GraphNode(
        node_id=node_id,
        node_type="evidence",
        label=str(evidence.get("claim", evidence_id)),
        description=str(evidence.get("supporting_quote", "")),
        source_ids=[str(evidence.get("source_identifier", ""))],
        evidence_ids=[evidence_id],
        artifact_ids=[],
        workflow_run_ids=[workflow_run_id],
        confidence=str(evidence.get("confidence", "unknown")),
        metadata={"source_location": evidence.get("source_location"), "provenance": evidence.get("provenance", {})},
        created_at=now,
        updated_at=now,
    )


def _deterministic_nodes_from_evidence(evidence: JsonMap, workflow_run_id: str, now: str) -> list[GraphNode]:
    quote = str(evidence.get("supporting_quote", "")).strip()
    evidence_id = _require_str(evidence, "evidence_id")
    source_identifier = str(evidence.get("source_identifier", ""))
    extracted: list[tuple[str, str, JsonMap]] = []
    if quote.startswith("#"):
        label = quote.lstrip("#").strip()
        if label:
            extracted.append(("topic", label, {"extraction_rule": "markdown_heading"}))
    prefixes = {
        "Concept:": "concept",
        "Theme:": "theme",
        "Risk:": "risk",
        "Assumption:": "assumption",
        "Recommendation:": "recommendation",
    }
    for prefix, node_type in prefixes.items():
        if quote.startswith(prefix):
            label = quote.removeprefix(prefix).strip()
            if label:
                extracted.append((node_type, label, {"extraction_rule": "explicit_prefix", "prefix": prefix}))
    contradiction_prefixes = ["Contradiction:", "Conflicts with:", "Opposes:", "Disputes:"]
    for prefix in contradiction_prefixes:
        if quote.startswith(prefix):
            label = quote.removeprefix(prefix).strip()
            if label:
                extracted.append(
                    (
                        "risk",
                        label,
                        {
                            "extraction_rule": "explicit_contradiction_prefix",
                            "prefix": prefix,
                            "explicit_contradiction_marker": True,
                            "contradiction_marker": prefix.removesuffix(":"),
                        },
                    )
                )
    nodes = []
    for node_type, label, metadata in extracted:
        nodes.append(
            GraphNode(
                node_id=_node_id(node_type, f"{workflow_run_id}|{source_identifier}|{evidence_id}|{label}"),
                node_type=node_type,
                label=label,
                description=f"Deterministically extracted from explicit source text: {quote}",
                source_ids=[source_identifier],
                evidence_ids=[evidence_id],
                artifact_ids=[],
                workflow_run_ids=[workflow_run_id],
                confidence="deterministic_extraction",
                metadata=metadata,
                created_at=now,
                updated_at=now,
            )
        )
    return nodes


def _artifact_records(root: Path, workflow_run_id: str, working_memory: JsonMap) -> list[JsonMap]:
    records = ArtifactStore(root).list(workflow_run_id)
    if records:
        return records
    artifacts = working_memory.get("artifacts", {})
    if not isinstance(artifacts, dict):
        return []
    placeholder_records: list[JsonMap] = []
    for output_name, value in artifacts.items():
        if isinstance(value, dict):
            placeholder_records.append(
                {
                    "artifact_id": f"artifact_{workflow_run_id}_{output_name}",
                    "artifact_type": output_name,
                    "title": output_name,
                    "summary": f"Placeholder artifact for {output_name}.",
                    "status": value.get("status", "unknown"),
                    "confidence": "unknown",
                    "evidence_used": [],
                }
            )
    return placeholder_records


def _artifact_evidence_ids(artifact: JsonMap) -> list[str]:
    evidence_ids: list[str] = []
    evidence_used = artifact.get("evidence_used", [])
    if isinstance(evidence_used, list):
        for item in evidence_used:
            if isinstance(item, dict) and item.get("type") == "evidence" and isinstance(item.get("id"), str):
                evidence_ids.append(item["id"])
    return sorted(set(evidence_ids))


def _edge(source_node_id: str, target_node_id: str, relationship_type: str, evidence_ids: list[str], now: str) -> GraphEdge:
    return GraphEdge(
        edge_id=_edge_id(source_node_id, target_node_id, relationship_type),
        source_node_id=source_node_id,
        target_node_id=target_node_id,
        relationship_type=relationship_type,
        evidence_ids=sorted(set(evidence_ids)),
        confidence="deterministic",
        metadata={"builder": "KnowledgeGraphBuilder"},
        created_at=now,
        updated_at=now,
    )


def _read_working_memory(root: Path, workflow_run_id: str) -> JsonMap:
    path = MemoryManager(root, workflow_run_id).working_path
    if not path.exists():
        return {}
    try:
        return read_json(path)
    except Exception:
        return {}


def _node_from_dict(data: JsonMap) -> GraphNode:
    return GraphNode(
        node_id=_require_str(data, "node_id"),
        node_type=_require_str(data, "node_type"),
        label=_require_str(data, "label"),
        description=str(data.get("description", "")),
        source_ids=_string_list(data.get("source_ids", [])),
        evidence_ids=_string_list(data.get("evidence_ids", [])),
        artifact_ids=_string_list(data.get("artifact_ids", [])),
        workflow_run_ids=_string_list(data.get("workflow_run_ids", [])),
        confidence=str(data.get("confidence", "unknown")),
        metadata=data.get("metadata", {}) if isinstance(data.get("metadata", {}), dict) else {},
        created_at=str(data.get("created_at", "")),
        updated_at=str(data.get("updated_at", "")),
    )


def _edge_from_dict(data: JsonMap) -> GraphEdge:
    return GraphEdge(
        edge_id=_require_str(data, "edge_id"),
        source_node_id=_require_str(data, "source_node_id"),
        target_node_id=_require_str(data, "target_node_id"),
        relationship_type=_require_str(data, "relationship_type"),
        evidence_ids=_string_list(data.get("evidence_ids", [])),
        confidence=str(data.get("confidence", "unknown")),
        metadata=data.get("metadata", {}) if isinstance(data.get("metadata", {}), dict) else {},
        created_at=str(data.get("created_at", "")),
        updated_at=str(data.get("updated_at", "")),
    )


def _node_id(node_type: str, key: str) -> str:
    return f"node_{node_type}_{_digest(key)}"


def _edge_id(source_node_id: str, target_node_id: str, relationship_type: str) -> str:
    return f"edge_{_digest(source_node_id + '|' + relationship_type + '|' + target_node_id)}"


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:16]


def _merge(first: list[str], second: list[str]) -> list[str]:
    return sorted(set(first) | set(second))


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _require_str(data: JsonMap, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise KnowledgeGraphError(f"Graph field {key} must be a string")
    return value


def _validate_node_type(node_type: str) -> None:
    if node_type not in SUPPORTED_NODE_TYPES:
        raise KnowledgeGraphError(f"Unsupported graph node type: {node_type}")


def _validate_relationship_type(relationship_type: str) -> None:
    if relationship_type not in SUPPORTED_RELATIONSHIP_TYPES:
        raise KnowledgeGraphError(f"Unsupported graph relationship type: {relationship_type}")
