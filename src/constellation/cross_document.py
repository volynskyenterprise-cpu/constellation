from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from .io import read_json, write_json
from .knowledge_graph import GraphNode, KnowledgeGraph, KnowledgeGraphError, KnowledgeGraphStore
from .models import JsonMap, utc_now_iso


class CrossDocumentError(RuntimeError):
    pass


FINDING_TYPES = {
    "repeated_concept",
    "repeated_theme",
    "repeated_risk",
    "repeated_assumption",
    "repeated_recommendation",
    "source_cluster",
    "possible_contradiction",
    "missing_evidence",
    "confidence_signal",
}


@dataclass(frozen=True)
class CrossDocumentFinding:
    finding_id: str
    finding_type: str
    title: str
    summary: str
    node_ids: list[str]
    evidence_ids: list[str]
    source_ids: list[str]
    workflow_run_ids: list[str]
    confidence: str
    rationale: str
    metadata: JsonMap
    created_at: str

    def to_dict(self) -> JsonMap:
        return {
            "finding_id": self.finding_id,
            "finding_type": self.finding_type,
            "title": self.title,
            "summary": self.summary,
            "node_ids": self.node_ids,
            "evidence_ids": self.evidence_ids,
            "source_ids": self.source_ids,
            "workflow_run_ids": self.workflow_run_ids,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


@dataclass(frozen=True)
class CrossDocumentAnalysis:
    analysis_id: str
    graph_version: str
    findings: list[CrossDocumentFinding]
    created_at: str
    metadata: JsonMap

    def to_dict(self) -> JsonMap:
        return {
            "analysis_id": self.analysis_id,
            "graph_version": self.graph_version,
            "findings": [finding.to_dict() for finding in self.findings],
            "created_at": self.created_at,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "CrossDocumentAnalysis":
        return cls(
            analysis_id=_require_str(data, "analysis_id"),
            graph_version=_require_str(data, "graph_version"),
            findings=[_finding_from_dict(item) for item in data.get("findings", []) if isinstance(item, dict)],
            created_at=_require_str(data, "created_at"),
            metadata=data.get("metadata", {}) if isinstance(data.get("metadata", {}), dict) else {},
        )


class CrossDocumentAnalyzer:
    def analyze(self, graph: KnowledgeGraph) -> CrossDocumentAnalysis:
        now = utc_now_iso()
        findings: list[CrossDocumentFinding] = []
        findings.extend(_repeated_label_findings(graph, now))
        findings.extend(_source_cluster_findings(graph, now))
        findings.extend(_explicit_contradiction_findings(graph, now))
        findings.extend(_missing_evidence_findings(graph, now))
        findings.extend(_confidence_signal_findings(graph, now))
        findings = sorted({finding.finding_id: finding for finding in findings}.values(), key=lambda item: (item.finding_type, item.title, item.finding_id))
        analysis_id = f"analysis_{_digest('|'.join(finding.finding_id for finding in findings))}"
        return CrossDocumentAnalysis(
            analysis_id=analysis_id,
            graph_version=_digest(_graph_fingerprint(graph)),
            findings=findings,
            created_at=now,
            metadata={"source": "CrossDocumentAnalyzer", "deterministic": True},
        )


class CrossDocumentAnalysisStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "outputs" / "analysis"
        self.json_path = self.directory / "cross-document-analysis.json"
        self.markdown_path = self.directory / "cross-document-analysis.md"

    def analyze_graph(self, *, overwrite: bool = False) -> CrossDocumentAnalysis:
        graph_store = KnowledgeGraphStore(self.root)
        if not graph_store.graph_path.exists():
            raise CrossDocumentError("No knowledge graph found. Run graph build RUN_ID first.")
        if (self.json_path.exists() or self.markdown_path.exists()) and not overwrite:
            raise CrossDocumentError("Cross-document analysis already exists. Use --overwrite to replace it.")
        analysis = CrossDocumentAnalyzer().analyze(graph_store.load())
        self.save(analysis)
        return analysis

    def save(self, analysis: CrossDocumentAnalysis) -> None:
        write_json(self.json_path, analysis.to_dict())
        self.markdown_path.parent.mkdir(parents=True, exist_ok=True)
        self.markdown_path.write_text(render_analysis_markdown(analysis), encoding="utf-8")

    def load(self) -> CrossDocumentAnalysis:
        if not self.json_path.exists():
            raise CrossDocumentError("No cross-document analysis found. Run graph analyze first.")
        return CrossDocumentAnalysis.from_dict(read_json(self.json_path))

    def list_findings(self) -> list[CrossDocumentFinding]:
        return self.load().findings

    def show_finding(self, finding_id: str) -> CrossDocumentFinding:
        for finding in self.list_findings():
            if finding.finding_id == finding_id:
                return finding
        raise CrossDocumentError(f"Unknown cross-document finding: {finding_id}")

    def export(self) -> Path:
        analysis = self.load()
        self.markdown_path.parent.mkdir(parents=True, exist_ok=True)
        self.markdown_path.write_text(render_analysis_markdown(analysis), encoding="utf-8")
        return self.markdown_path


def render_analysis_markdown(analysis: CrossDocumentAnalysis) -> str:
    lines = [
        "# Cross-Document Analysis",
        "",
        f"Analysis ID: `{analysis.analysis_id}`",
        f"Graph version: `{analysis.graph_version}`",
        f"Findings: {len(analysis.findings)}",
        "",
    ]
    for finding in analysis.findings:
        lines.extend(
            [
                f"## {finding.title}",
                "",
                f"- ID: `{finding.finding_id}`",
                f"- Type: `{finding.finding_type}`",
                f"- Confidence: `{finding.confidence}`",
                f"- Sources: {', '.join(finding.source_ids) if finding.source_ids else 'None'}",
                f"- Evidence: {', '.join(finding.evidence_ids) if finding.evidence_ids else 'None'}",
                "",
                finding.summary,
                "",
                f"Rationale: {finding.rationale}",
                "",
            ]
        )
    return "\n".join(lines)


def _repeated_label_findings(graph: KnowledgeGraph, now: str) -> list[CrossDocumentFinding]:
    mapping = {
        "concept": "repeated_concept",
        "theme": "repeated_theme",
        "risk": "repeated_risk",
        "assumption": "repeated_assumption",
        "recommendation": "repeated_recommendation",
    }
    findings: list[CrossDocumentFinding] = []
    for node_type, finding_type in mapping.items():
        for label, nodes in _nodes_by_label(graph, node_type).items():
            source_ids = _collect_sources(nodes)
            workflow_run_ids = _collect_workflows(nodes)
            if len(source_ids) > 1 or len(workflow_run_ids) > 1:
                findings.append(
                    _finding(
                        finding_type=finding_type,
                        title=f"Repeated {node_type}: {label}",
                        summary=f"The {node_type} label `{label}` appears across multiple sources or workflow runs.",
                        nodes=nodes,
                        confidence=_confidence_for_sources(source_ids),
                        rationale="Deterministic repeated-label rule matched more than one source or workflow run.",
                        metadata={"label": label, "node_type": node_type},
                        created_at=now,
                    )
                )
    return findings


def _source_cluster_findings(graph: KnowledgeGraph, now: str) -> list[CrossDocumentFinding]:
    label_sources: dict[str, set[str]] = {}
    label_nodes: dict[str, list[GraphNode]] = {}
    for node_type in ["concept", "theme", "risk", "recommendation"]:
        for node in graph.find_nodes(node_type=node_type):
            key = f"{node_type}:{node.label.lower()}"
            label_sources.setdefault(key, set()).update(node.source_ids)
            label_nodes.setdefault(key, []).append(node)
    findings = []
    for key, source_ids in sorted(label_sources.items()):
        if len(source_ids) > 1:
            nodes = label_nodes[key]
            findings.append(
                _finding(
                    finding_type="source_cluster",
                    title=f"Source cluster: {key}",
                    summary=f"Multiple sources share `{key}`.",
                    nodes=nodes,
                    confidence=_confidence_for_sources(sorted(source_ids)),
                    rationale="Deterministic source-cluster rule matched a shared explicit label.",
                    metadata={"shared_label": key},
                    created_at=now,
                )
            )
    return findings


def _explicit_contradiction_findings(graph: KnowledgeGraph, now: str) -> list[CrossDocumentFinding]:
    findings = []
    for node in graph.find_nodes(node_type="risk"):
        if node.metadata.get("explicit_contradiction_marker") is True:
            findings.append(
                _finding(
                    finding_type="possible_contradiction",
                    title=f"Possible contradiction: {node.label}",
                    summary="An explicit contradiction marker appeared in source text.",
                    nodes=[node],
                    confidence="medium",
                    rationale="Only explicit markers such as Contradiction, Conflicts with, Opposes, or Disputes trigger this finding.",
                    metadata={"marker": node.metadata.get("contradiction_marker")},
                    created_at=now,
                )
            )
    return findings


def _missing_evidence_findings(graph: KnowledgeGraph, now: str) -> list[CrossDocumentFinding]:
    findings = []
    for node_type in ["concept", "theme", "risk", "recommendation"]:
        for node in graph.find_nodes(node_type=node_type):
            if not node.evidence_ids:
                findings.append(
                    _finding(
                        finding_type="missing_evidence",
                        title=f"Missing evidence: {node.label}",
                        summary=f"The {node_type} node `{node.label}` has no evidence IDs.",
                        nodes=[node],
                        confidence="low",
                        rationale="Deterministic missing-evidence rule found an empty evidence_ids list.",
                        metadata={"node_type": node_type},
                        created_at=now,
                    )
                )
    return findings


def _confidence_signal_findings(graph: KnowledgeGraph, now: str) -> list[CrossDocumentFinding]:
    findings = []
    for node_type in ["concept", "theme", "risk", "recommendation"]:
        for label, nodes in _nodes_by_label(graph, node_type).items():
            source_ids = _collect_sources(nodes)
            if len(source_ids) > 1:
                findings.append(
                    _finding(
                        finding_type="confidence_signal",
                        title=f"Confidence signal: {label}",
                        summary=f"`{label}` appears across {len(source_ids)} independent source files.",
                        nodes=nodes,
                        confidence=_confidence_for_sources(source_ids),
                        rationale="Confidence increases deterministically when the same explicit label appears across independent sources.",
                        metadata={"label": label, "node_type": node_type, "source_count": len(source_ids)},
                        created_at=now,
                    )
                )
    return findings


def _finding(
    *,
    finding_type: str,
    title: str,
    summary: str,
    nodes: list[GraphNode],
    confidence: str,
    rationale: str,
    metadata: JsonMap,
    created_at: str,
) -> CrossDocumentFinding:
    if finding_type not in FINDING_TYPES:
        raise CrossDocumentError(f"Unsupported finding type: {finding_type}")
    node_ids = sorted(node.node_id for node in nodes)
    evidence_ids = _collect_evidence(nodes)
    source_ids = _collect_sources(nodes)
    workflow_run_ids = _collect_workflows(nodes)
    finding_id = f"finding_{_digest(finding_type + '|' + '|'.join(node_ids) + '|' + title)}"
    return CrossDocumentFinding(
        finding_id=finding_id,
        finding_type=finding_type,
        title=title,
        summary=summary,
        node_ids=node_ids,
        evidence_ids=evidence_ids,
        source_ids=source_ids,
        workflow_run_ids=workflow_run_ids,
        confidence=confidence,
        rationale=rationale,
        metadata=metadata,
        created_at=created_at,
    )


def _nodes_by_label(graph: KnowledgeGraph, node_type: str) -> dict[str, list[GraphNode]]:
    grouped: dict[str, list[GraphNode]] = {}
    for node in graph.find_nodes(node_type=node_type):
        grouped.setdefault(node.label.lower(), []).append(node)
    return grouped


def _collect_evidence(nodes: list[GraphNode]) -> list[str]:
    return sorted({evidence_id for node in nodes for evidence_id in node.evidence_ids})


def _collect_sources(nodes: list[GraphNode]) -> list[str]:
    return sorted({source_id for node in nodes for source_id in node.source_ids})


def _collect_workflows(nodes: list[GraphNode]) -> list[str]:
    return sorted({workflow_run_id for node in nodes for workflow_run_id in node.workflow_run_ids})


def _confidence_for_sources(source_ids: list[str]) -> str:
    count = len(set(source_ids))
    if count >= 3:
        return "high"
    if count == 2:
        return "medium"
    return "low"


def _graph_fingerprint(graph: KnowledgeGraph) -> str:
    return "|".join(sorted(list(graph.nodes) + list(graph.edges)))


def _finding_from_dict(data: JsonMap) -> CrossDocumentFinding:
    return CrossDocumentFinding(
        finding_id=_require_str(data, "finding_id"),
        finding_type=_require_str(data, "finding_type"),
        title=_require_str(data, "title"),
        summary=_require_str(data, "summary"),
        node_ids=_string_list(data.get("node_ids", [])),
        evidence_ids=_string_list(data.get("evidence_ids", [])),
        source_ids=_string_list(data.get("source_ids", [])),
        workflow_run_ids=_string_list(data.get("workflow_run_ids", [])),
        confidence=_require_str(data, "confidence"),
        rationale=_require_str(data, "rationale"),
        metadata=data.get("metadata", {}) if isinstance(data.get("metadata", {}), dict) else {},
        created_at=_require_str(data, "created_at"),
    )


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:16]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _require_str(data: JsonMap, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise CrossDocumentError(f"Analysis field {key} must be a string")
    return value
