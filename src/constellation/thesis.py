from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from .cross_document import CrossDocumentAnalysis, CrossDocumentAnalysisStore, CrossDocumentError, CrossDocumentFinding
from .io import read_json, write_json
from .models import JsonMap, utc_now_iso


class ThesisError(RuntimeError):
    pass


THESIS_TYPES = {
    "strategic_theme",
    "emerging_risk",
    "repeated_recommendation",
    "evidence_gap",
    "source_consensus",
    "contradiction_watch",
}

THESIS_STATUSES = {"proposed", "accepted", "rejected", "superseded"}
CONFIDENCE_LABELS = {"low", "medium", "high"}


@dataclass(frozen=True)
class Thesis:
    thesis_id: str
    title: str
    summary: str
    thesis_type: str
    status: str
    confidence: str
    supporting_finding_ids: list[str]
    supporting_evidence_ids: list[str]
    supporting_node_ids: list[str]
    source_ids: list[str]
    workflow_run_ids: list[str]
    counterpoint_finding_ids: list[str]
    risks: list[str]
    assumptions: list[str]
    recommendations: list[str]
    open_questions: list[str]
    rationale: str
    metadata: JsonMap
    created_at: str
    updated_at: str

    def __post_init__(self) -> None:
        if self.thesis_type not in THESIS_TYPES:
            raise ThesisError(f"Unsupported thesis type: {self.thesis_type}")
        if self.status not in THESIS_STATUSES:
            raise ThesisError(f"Unsupported thesis status: {self.status}")
        if self.confidence not in CONFIDENCE_LABELS:
            raise ThesisError(f"Unsupported thesis confidence: {self.confidence}")

    def to_dict(self) -> JsonMap:
        return {
            "thesis_id": self.thesis_id,
            "title": self.title,
            "summary": self.summary,
            "thesis_type": self.thesis_type,
            "status": self.status,
            "confidence": self.confidence,
            "supporting_finding_ids": self.supporting_finding_ids,
            "supporting_evidence_ids": self.supporting_evidence_ids,
            "supporting_node_ids": self.supporting_node_ids,
            "source_ids": self.source_ids,
            "workflow_run_ids": self.workflow_run_ids,
            "counterpoint_finding_ids": self.counterpoint_finding_ids,
            "risks": self.risks,
            "assumptions": self.assumptions,
            "recommendations": self.recommendations,
            "open_questions": self.open_questions,
            "rationale": self.rationale,
            "metadata": self.metadata,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "Thesis":
        return cls(
            thesis_id=_require_str(data, "thesis_id"),
            title=_require_str(data, "title"),
            summary=_require_str(data, "summary"),
            thesis_type=_require_str(data, "thesis_type"),
            status=_require_str(data, "status"),
            confidence=_require_str(data, "confidence"),
            supporting_finding_ids=_string_list(data.get("supporting_finding_ids", [])),
            supporting_evidence_ids=_string_list(data.get("supporting_evidence_ids", [])),
            supporting_node_ids=_string_list(data.get("supporting_node_ids", [])),
            source_ids=_string_list(data.get("source_ids", [])),
            workflow_run_ids=_string_list(data.get("workflow_run_ids", [])),
            counterpoint_finding_ids=_string_list(data.get("counterpoint_finding_ids", [])),
            risks=_string_list(data.get("risks", [])),
            assumptions=_string_list(data.get("assumptions", [])),
            recommendations=_string_list(data.get("recommendations", [])),
            open_questions=_string_list(data.get("open_questions", [])),
            rationale=_require_str(data, "rationale"),
            metadata=data.get("metadata", {}) if isinstance(data.get("metadata", {}), dict) else {},
            created_at=_require_str(data, "created_at"),
            updated_at=_require_str(data, "updated_at"),
        )


class ThesisEngine:
    def generate(self, analysis: CrossDocumentAnalysis) -> list[Thesis]:
        now = utc_now_iso()
        theses = [_thesis_from_finding(analysis, finding, now) for finding in analysis.findings]
        generated = [thesis for thesis in theses if thesis is not None]
        return sorted(generated, key=lambda item: (item.thesis_type, item.title, item.thesis_id))


class ThesisStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "outputs" / "theses"
        self.json_path = self.directory / "theses.json"
        self.markdown_path = self.directory / "theses.md"

    def generate(self, *, overwrite: bool = False) -> list[Thesis]:
        if (self.json_path.exists() or self.markdown_path.exists()) and not overwrite:
            raise ThesisError("Theses already exist. Use --overwrite to replace them.")
        try:
            analysis = CrossDocumentAnalysisStore(self.root).load()
        except CrossDocumentError as exc:
            raise ThesisError(str(exc)) from exc
        theses = ThesisEngine().generate(analysis)
        self.save(theses, metadata={"source_analysis_id": analysis.analysis_id, "graph_version": analysis.graph_version})
        return theses

    def save(self, theses: list[Thesis], metadata: JsonMap | None = None) -> None:
        record = {
            "schema_version": "2.5.0",
            "created_at": utc_now_iso(),
            "metadata": metadata or {},
            "theses": [thesis.to_dict() for thesis in theses],
        }
        write_json(self.json_path, record)
        self.markdown_path.parent.mkdir(parents=True, exist_ok=True)
        self.markdown_path.write_text(render_theses_markdown(theses, record["metadata"]), encoding="utf-8")

    def load(self) -> list[Thesis]:
        if not self.json_path.exists():
            raise ThesisError("No theses found. Run thesis generate first.")
        data = read_json(self.json_path)
        raw_theses = data.get("theses")
        if not isinstance(raw_theses, list):
            raise ThesisError("Thesis store must define a theses list.")
        return [Thesis.from_dict(item) for item in raw_theses if isinstance(item, dict)]

    def list_theses(self) -> list[Thesis]:
        return self.load()

    def show(self, thesis_id: str) -> Thesis:
        for thesis in self.load():
            if thesis.thesis_id == thesis_id:
                return thesis
        raise ThesisError(f"Unknown thesis: {thesis_id}")

    def export(self) -> Path:
        data = read_json(self.json_path) if self.json_path.exists() else {}
        metadata = data.get("metadata", {}) if isinstance(data.get("metadata", {}), dict) else {}
        theses = self.load()
        self.markdown_path.parent.mkdir(parents=True, exist_ok=True)
        self.markdown_path.write_text(render_theses_markdown(theses, metadata), encoding="utf-8")
        return self.markdown_path


def render_theses_markdown(theses: list[Thesis], metadata: JsonMap | None = None) -> str:
    metadata = metadata or {}
    lines = [
        "# Institutional Theses",
        "",
        f"Source analysis: `{metadata.get('source_analysis_id', 'unknown')}`",
        f"Graph version: `{metadata.get('graph_version', 'unknown')}`",
        f"Theses: {len(theses)}",
        "",
        "All theses are proposed until explicitly reviewed and accepted by a human authority.",
        "",
    ]
    for thesis in theses:
        lines.extend(
            [
                f"## {thesis.title}",
                "",
                f"- ID: `{thesis.thesis_id}`",
                f"- Type: `{thesis.thesis_type}`",
                f"- Status: `{thesis.status}`",
                f"- Confidence: `{thesis.confidence}`",
                f"- Findings: {', '.join(thesis.supporting_finding_ids) if thesis.supporting_finding_ids else 'None'}",
                f"- Evidence: {', '.join(thesis.supporting_evidence_ids) if thesis.supporting_evidence_ids else 'None'}",
                f"- Sources: {', '.join(thesis.source_ids) if thesis.source_ids else 'None'}",
                "",
                thesis.summary,
                "",
                f"Rationale: {thesis.rationale}",
                "",
                "Recommendations:",
                *[f"- {item}" for item in thesis.recommendations],
                "",
                "Open questions:",
                *[f"- {item}" for item in thesis.open_questions],
                "",
            ]
        )
    return "\n".join(lines)


def _thesis_from_finding(analysis: CrossDocumentAnalysis, finding: CrossDocumentFinding, now: str) -> Thesis | None:
    thesis_type = _thesis_type_for(finding)
    if thesis_type is None:
        return None
    title_prefix = {
        "strategic_theme": "Strategic theme",
        "emerging_risk": "Emerging risk",
        "repeated_recommendation": "Repeated recommendation",
        "evidence_gap": "Evidence gap",
        "source_consensus": "Source consensus",
        "contradiction_watch": "Contradiction watch",
    }[thesis_type]
    title = f"{title_prefix}: {finding.title}"
    thesis_id = f"thesis_{_digest(thesis_type + '|' + finding.finding_id + '|' + title)}"
    return Thesis(
        thesis_id=thesis_id,
        title=title,
        summary=finding.summary,
        thesis_type=thesis_type,
        status="proposed",
        confidence=_confidence(finding.confidence),
        supporting_finding_ids=[finding.finding_id],
        supporting_evidence_ids=sorted(finding.evidence_ids),
        supporting_node_ids=sorted(finding.node_ids),
        source_ids=sorted(finding.source_ids),
        workflow_run_ids=sorted(finding.workflow_run_ids),
        counterpoint_finding_ids=[],
        risks=_risks_for(thesis_type, finding),
        assumptions=["Generated deterministically from cross-document findings; no unstated inference was added."],
        recommendations=_recommendations_for(thesis_type),
        open_questions=["Should this proposed thesis be accepted, rejected, or superseded after human review?"],
        rationale=_rationale_for(thesis_type, finding),
        metadata={
            "source": "ThesisEngine",
            "deterministic": True,
            "analysis_id": analysis.analysis_id,
            "finding_type": finding.finding_type,
        },
        created_at=now,
        updated_at=now,
    )


def _thesis_type_for(finding: CrossDocumentFinding) -> str | None:
    if finding.finding_type in {"repeated_concept", "repeated_theme"} and finding.confidence == "high":
        return "strategic_theme"
    if finding.finding_type == "repeated_risk":
        return "emerging_risk"
    if finding.finding_type == "repeated_recommendation":
        return "repeated_recommendation"
    if finding.finding_type == "missing_evidence":
        return "evidence_gap"
    if finding.finding_type == "source_cluster" and finding.confidence == "high":
        return "source_consensus"
    if finding.finding_type == "possible_contradiction":
        return "contradiction_watch"
    return None


def _risks_for(thesis_type: str, finding: CrossDocumentFinding) -> list[str]:
    if thesis_type in {"emerging_risk", "contradiction_watch", "evidence_gap"}:
        return [finding.summary]
    return []


def _recommendations_for(thesis_type: str) -> list[str]:
    if thesis_type == "evidence_gap":
        return ["Attach source-backed evidence before accepting this thesis."]
    if thesis_type == "contradiction_watch":
        return ["Review the explicit contradiction marker before accepting or rejecting this thesis."]
    return ["Review the supporting finding and evidence before accepting this thesis."]


def _rationale_for(thesis_type: str, finding: CrossDocumentFinding) -> str:
    return f"{finding.rationale} Thesis rule matched `{finding.finding_type}` as `{thesis_type}`."


def _confidence(value: str) -> str:
    if value in CONFIDENCE_LABELS:
        return value
    return "low"


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:16]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _require_str(data: JsonMap, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise ThesisError(f"Thesis field {key} must be a string")
    return value
