from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from .cross_document import CrossDocumentAnalysisStore, CrossDocumentError
from .evidence import EvidenceStore
from .io import read_json, write_json
from .knowledge_graph import KnowledgeGraphStore
from .models import JsonMap, utc_now_iso
from .thesis import Thesis, ThesisError, ThesisStore


class IntelligenceError(RuntimeError):
    pass


BRIEF_STATUSES = {"draft", "proposed", "approved", "rejected"}
UPSTREAM_SEQUENCE = "Required sequence: 1. Build graph 2. Run graph analyze 3. Generate theses 4. Generate intelligence."


@dataclass(frozen=True)
class IntelligenceBrief:
    brief_id: str
    title: str
    summary: str
    status: str
    generated_from: JsonMap
    thesis_ids: list[str]
    finding_ids: list[str]
    evidence_ids: list[str]
    node_ids: list[str]
    source_ids: list[str]
    workflow_run_ids: list[str]
    strategic_themes: list[JsonMap]
    emerging_risks: list[JsonMap]
    repeated_recommendations: list[JsonMap]
    consensus_signals: list[JsonMap]
    contradiction_watches: list[JsonMap]
    evidence_gaps: list[JsonMap]
    confidence_assessment: JsonMap
    executive_recommendations: list[str]
    open_questions: list[str]
    limitations: list[str]
    approval_note: str
    metadata: JsonMap
    created_at: str
    updated_at: str

    def __post_init__(self) -> None:
        if self.status not in BRIEF_STATUSES:
            raise IntelligenceError(f"Unsupported intelligence brief status: {self.status}")

    def to_dict(self) -> JsonMap:
        return {
            "brief_id": self.brief_id,
            "title": self.title,
            "summary": self.summary,
            "status": self.status,
            "generated_from": self.generated_from,
            "thesis_ids": self.thesis_ids,
            "finding_ids": self.finding_ids,
            "evidence_ids": self.evidence_ids,
            "node_ids": self.node_ids,
            "source_ids": self.source_ids,
            "workflow_run_ids": self.workflow_run_ids,
            "strategic_themes": self.strategic_themes,
            "emerging_risks": self.emerging_risks,
            "repeated_recommendations": self.repeated_recommendations,
            "consensus_signals": self.consensus_signals,
            "contradiction_watches": self.contradiction_watches,
            "evidence_gaps": self.evidence_gaps,
            "confidence_assessment": self.confidence_assessment,
            "executive_recommendations": self.executive_recommendations,
            "open_questions": self.open_questions,
            "limitations": self.limitations,
            "approval_note": self.approval_note,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "IntelligenceBrief":
        return cls(
            brief_id=_require_str(data, "brief_id"),
            title=_require_str(data, "title"),
            summary=_require_str(data, "summary"),
            status=_require_str(data, "status"),
            generated_from=data.get("generated_from", {}) if isinstance(data.get("generated_from", {}), dict) else {},
            thesis_ids=_string_list(data.get("thesis_ids", [])),
            finding_ids=_string_list(data.get("finding_ids", [])),
            evidence_ids=_string_list(data.get("evidence_ids", [])),
            node_ids=_string_list(data.get("node_ids", [])),
            source_ids=_string_list(data.get("source_ids", [])),
            workflow_run_ids=_string_list(data.get("workflow_run_ids", [])),
            strategic_themes=_map_list(data.get("strategic_themes", [])),
            emerging_risks=_map_list(data.get("emerging_risks", [])),
            repeated_recommendations=_map_list(data.get("repeated_recommendations", [])),
            consensus_signals=_map_list(data.get("consensus_signals", [])),
            contradiction_watches=_map_list(data.get("contradiction_watches", [])),
            evidence_gaps=_map_list(data.get("evidence_gaps", [])),
            confidence_assessment=data.get("confidence_assessment", {}) if isinstance(data.get("confidence_assessment", {}), dict) else {},
            executive_recommendations=_string_list(data.get("executive_recommendations", [])),
            open_questions=_string_list(data.get("open_questions", [])),
            limitations=_string_list(data.get("limitations", [])),
            approval_note=_require_str(data, "approval_note"),
            metadata=data.get("metadata", {}) if isinstance(data.get("metadata", {}), dict) else {},
            created_at=_require_str(data, "created_at"),
            updated_at=_require_str(data, "updated_at"),
        )


class IntelligenceEngine:
    def generate(
        self,
        *,
        theses: list[Thesis],
        analysis_id: str,
        graph_node_ids: list[str],
        graph_edge_count: int,
        evidence_records: list[JsonMap],
    ) -> IntelligenceBrief:
        now = utc_now_iso()
        thesis_ids = sorted(thesis.thesis_id for thesis in theses)
        finding_ids = sorted({finding_id for thesis in theses for finding_id in thesis.supporting_finding_ids})
        evidence_ids = sorted({evidence_id for thesis in theses for evidence_id in thesis.supporting_evidence_ids})
        node_ids = sorted({node_id for thesis in theses for node_id in thesis.supporting_node_ids})
        source_ids = sorted({source_id for thesis in theses for source_id in thesis.source_ids})
        workflow_run_ids = sorted({run_id for thesis in theses for run_id in thesis.workflow_run_ids})
        source_ids = sorted(set(source_ids) | _source_ids_from_evidence(evidence_records, evidence_ids))
        brief_id = f"brief_{_digest('|'.join(thesis_ids) + '|' + analysis_id)}"
        confidence = _confidence_assessment(theses)
        return IntelligenceBrief(
            brief_id=brief_id,
            title="Institutional Intelligence Brief",
            summary=_summary(theses, confidence),
            status="proposed",
            generated_from={
                "theses": "outputs/theses/theses.json",
                "analysis": "outputs/analysis/cross-document-analysis.json",
                "graph": "memory/graph/graph.json",
                "evidence": "memory/evidence/",
                "analysis_id": analysis_id,
            },
            thesis_ids=thesis_ids,
            finding_ids=finding_ids,
            evidence_ids=evidence_ids,
            node_ids=sorted(set(node_ids) | set(graph_node_ids).intersection(node_ids)),
            source_ids=source_ids,
            workflow_run_ids=workflow_run_ids,
            strategic_themes=_brief_items(theses, "strategic_theme"),
            emerging_risks=_brief_items(theses, "emerging_risk"),
            repeated_recommendations=_brief_items(theses, "repeated_recommendation"),
            consensus_signals=_brief_items(theses, "source_consensus"),
            contradiction_watches=_brief_items(theses, "contradiction_watch"),
            evidence_gaps=_brief_items(theses, "evidence_gap"),
            confidence_assessment=confidence,
            executive_recommendations=_executive_recommendations(theses),
            open_questions=sorted({question for thesis in theses for question in thesis.open_questions}),
            limitations=[
                "Generated only from existing deterministic theses, findings, graph nodes, and evidence records.",
                "No LLM inference, semantic similarity, embeddings, web retrieval, provider calls, or external database was used.",
                "Human review is required before treating this brief as an institutional position.",
            ],
            approval_note="Status is proposed. A human authority must review and approve before institutional adoption.",
            metadata={
                "source": "IntelligenceEngine",
                "deterministic": True,
                "schema_version": "3.0.0",
                "graph_node_count": len(graph_node_ids),
                "graph_edge_count": graph_edge_count,
                "evidence_record_count": len(evidence_records),
            },
            created_at=now,
            updated_at=now,
        )


class IntelligenceStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "outputs" / "intelligence"
        self.json_path = self.directory / "institutional-intelligence.json"
        self.markdown_path = self.directory / "institutional-intelligence.md"

    def generate(self, *, overwrite: bool = False) -> IntelligenceBrief:
        if (self.json_path.exists() or self.markdown_path.exists()) and not overwrite:
            raise IntelligenceError("Institutional intelligence brief already exists. Use --overwrite to replace it.")
        analysis = self._load_analysis()
        graph = self._load_graph()
        theses = self._load_theses()
        evidence_records = EvidenceStore(self.root).list()
        brief = IntelligenceEngine().generate(
            theses=theses,
            analysis_id=analysis.analysis_id,
            graph_node_ids=sorted(graph.nodes),
            graph_edge_count=len(graph.edges),
            evidence_records=evidence_records,
        )
        self.save(brief)
        return brief

    def save(self, brief: IntelligenceBrief) -> None:
        write_json(self.json_path, brief.to_dict())
        self.markdown_path.parent.mkdir(parents=True, exist_ok=True)
        self.markdown_path.write_text(render_intelligence_markdown(brief), encoding="utf-8")

    def load(self) -> IntelligenceBrief:
        if not self.json_path.exists():
            raise IntelligenceError("No institutional intelligence brief found. Run intelligence generate first.")
        return IntelligenceBrief.from_dict(read_json(self.json_path))

    def export(self) -> Path:
        brief = self.load()
        self.markdown_path.parent.mkdir(parents=True, exist_ok=True)
        self.markdown_path.write_text(render_intelligence_markdown(brief), encoding="utf-8")
        return self.markdown_path

    def _load_analysis(self):
        try:
            return CrossDocumentAnalysisStore(self.root).load()
        except CrossDocumentError as exc:
            raise IntelligenceError(f"Missing cross-document analysis. {UPSTREAM_SEQUENCE}") from exc

    def _load_graph(self):
        graph_store = KnowledgeGraphStore(self.root)
        if not graph_store.graph_path.exists():
            raise IntelligenceError(f"Missing knowledge graph. {UPSTREAM_SEQUENCE}")
        graph = graph_store.load()
        if not graph.nodes:
            raise IntelligenceError(f"Knowledge graph is empty. {UPSTREAM_SEQUENCE}")
        return graph

    def _load_theses(self) -> list[Thesis]:
        try:
            return ThesisStore(self.root).load()
        except ThesisError as exc:
            raise IntelligenceError(f"Missing theses. {UPSTREAM_SEQUENCE}") from exc


def render_intelligence_markdown(brief: IntelligenceBrief) -> str:
    lines = [
        "# Institutional Intelligence Brief",
        "",
        f"Brief ID: `{brief.brief_id}`",
        f"Status: `{brief.status}`",
        "",
        "## Executive Summary",
        "",
        brief.summary,
        "",
        "## Strategic Themes",
        "",
        *_markdown_items(brief.strategic_themes),
        "## Emerging Risks",
        "",
        *_markdown_items(brief.emerging_risks),
        "## Consensus Signals",
        "",
        *_markdown_items(brief.consensus_signals),
        "## Repeated Recommendations",
        "",
        *_markdown_items(brief.repeated_recommendations),
        "## Contradiction Watches",
        "",
        *_markdown_items(brief.contradiction_watches),
        "## Evidence Gaps",
        "",
        *_markdown_items(brief.evidence_gaps),
        "## Confidence Assessment",
        "",
        f"- High: {brief.confidence_assessment.get('high_count', 0)}",
        f"- Medium: {brief.confidence_assessment.get('medium_count', 0)}",
        f"- Low: {brief.confidence_assessment.get('low_count', 0)}",
        f"- Overall: `{brief.confidence_assessment.get('overall_label', 'low')}`",
        "",
        "## Supporting Evidence IDs",
        "",
        *_markdown_string_list(brief.evidence_ids),
        "## Source References",
        "",
        *_markdown_string_list(brief.source_ids),
        "## Open Questions",
        "",
        *_markdown_string_list(brief.open_questions),
        "## Limitations",
        "",
        *_markdown_string_list(brief.limitations),
        "## Recommended Next Actions",
        "",
        *_markdown_string_list(brief.executive_recommendations),
        "## Human Review Note",
        "",
        brief.approval_note,
        "",
    ]
    return "\n".join(lines)


def _brief_items(theses: list[Thesis], thesis_type: str) -> list[JsonMap]:
    return [
        {
            "thesis_id": thesis.thesis_id,
            "title": thesis.title,
            "summary": thesis.summary,
            "confidence": thesis.confidence,
            "finding_ids": thesis.supporting_finding_ids,
            "evidence_ids": thesis.supporting_evidence_ids,
            "source_ids": thesis.source_ids,
        }
        for thesis in sorted(theses, key=lambda item: (item.title, item.thesis_id))
        if thesis.thesis_type == thesis_type
    ]


def _confidence_assessment(theses: list[Thesis]) -> JsonMap:
    high_count = sum(1 for thesis in theses if thesis.confidence == "high")
    medium_count = sum(1 for thesis in theses if thesis.confidence == "medium")
    low_count = sum(1 for thesis in theses if thesis.confidence == "low")
    if high_count > 0 and low_count == 0:
        overall = "high"
    elif high_count + medium_count > low_count:
        overall = "medium"
    else:
        overall = "low"
    return {"high_count": high_count, "medium_count": medium_count, "low_count": low_count, "overall_label": overall}


def _summary(theses: list[Thesis], confidence: JsonMap) -> str:
    return (
        f"Deterministic synthesis of {len(theses)} proposed theses. "
        f"Overall confidence is `{confidence.get('overall_label', 'low')}` based on thesis confidence counts."
    )


def _executive_recommendations(theses: list[Thesis]) -> list[str]:
    recommendations = {recommendation for thesis in theses for recommendation in thesis.recommendations}
    recommendations.add("Review this proposed intelligence brief before treating it as institutional position.")
    return sorted(recommendations)


def _source_ids_from_evidence(evidence_records: list[JsonMap], evidence_ids: list[str]) -> set[str]:
    wanted = set(evidence_ids)
    return {
        str(record.get("source_identifier"))
        for record in evidence_records
        if record.get("evidence_id") in wanted and record.get("source_identifier")
    }


def _markdown_items(items: list[JsonMap]) -> list[str]:
    if not items:
        return ["- None", ""]
    lines: list[str] = []
    for item in items:
        lines.extend(
            [
                f"- `{item.get('thesis_id', 'unknown')}` {item.get('title', 'Untitled')} ({item.get('confidence', 'unknown')})",
                f"  Findings: {', '.join(_string_list(item.get('finding_ids', []))) or 'None'}",
                f"  Evidence: {', '.join(_string_list(item.get('evidence_ids', []))) or 'None'}",
            ]
        )
    lines.append("")
    return lines


def _markdown_string_list(items: list[str]) -> list[str]:
    if not items:
        return ["- None", ""]
    return [*[f"- `{item}`" for item in items], ""]


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:16]


def _map_list(value: Any) -> list[JsonMap]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _require_str(data: JsonMap, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise IntelligenceError(f"Intelligence brief field {key} must be a string")
    return value
