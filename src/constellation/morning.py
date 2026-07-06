from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from .cross_document import CrossDocumentAnalysisStore, CrossDocumentError
from .evidence import EvidenceStore
from .intelligence import IntelligenceError, IntelligenceStore
from .io import read_json, write_json
from .knowledge_graph import KnowledgeGraphStore
from .models import JsonMap, utc_now_iso
from .thesis import ThesisError, ThesisStore


class MorningExecutiveError(RuntimeError):
    pass


@dataclass(frozen=True)
class MorningExecutiveBrief:
    brief_id: str
    created_at: str
    intake_summary: JsonMap
    google_drive_sync_summary: JsonMap
    new_documents_detected: list[JsonMap]
    evidence_count: int
    graph_node_count: int
    graph_edge_count: int
    top_findings: list[JsonMap]
    top_theses: list[JsonMap]
    intelligence_summary: JsonMap
    risks_or_gaps: list[str]
    recommended_next_actions: list[str]
    provenance_references: JsonMap
    limitations: list[str]

    def to_dict(self) -> JsonMap:
        return {
            "brief_id": self.brief_id,
            "created_at": self.created_at,
            "intake_summary": self.intake_summary,
            "google_drive_sync_summary": self.google_drive_sync_summary,
            "new_documents_detected": self.new_documents_detected,
            "evidence_count": self.evidence_count,
            "graph_node_count": self.graph_node_count,
            "graph_edge_count": self.graph_edge_count,
            "top_findings": self.top_findings,
            "top_theses": self.top_theses,
            "intelligence_summary": self.intelligence_summary,
            "risks_or_gaps": self.risks_or_gaps,
            "recommended_next_actions": self.recommended_next_actions,
            "provenance_references": self.provenance_references,
            "limitations": self.limitations,
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "MorningExecutiveBrief":
        return cls(
            brief_id=_require_str(data, "brief_id"),
            created_at=_require_str(data, "created_at"),
            intake_summary=_map(data.get("intake_summary")),
            google_drive_sync_summary=_map(data.get("google_drive_sync_summary")),
            new_documents_detected=_map_list(data.get("new_documents_detected", [])),
            evidence_count=_int(data.get("evidence_count")),
            graph_node_count=_int(data.get("graph_node_count")),
            graph_edge_count=_int(data.get("graph_edge_count")),
            top_findings=_map_list(data.get("top_findings", [])),
            top_theses=_map_list(data.get("top_theses", [])),
            intelligence_summary=_map(data.get("intelligence_summary")),
            risks_or_gaps=_string_list(data.get("risks_or_gaps", [])),
            recommended_next_actions=_string_list(data.get("recommended_next_actions", [])),
            provenance_references=_map(data.get("provenance_references")),
            limitations=_string_list(data.get("limitations", [])),
        )


class MorningExecutiveEngine:
    def __init__(self, root: Path) -> None:
        self.root = root

    def generate(self) -> MorningExecutiveBrief:
        created_at = utc_now_iso()
        intake_manifest = _read_optional_json(self.root / "outputs" / "intake" / "intake-manifest.json")
        drive_manifest = _read_optional_json(self.root / "outputs" / "google-drive" / "google-drive-sync-manifest.json")
        evidence_records = EvidenceStore(self.root).list()
        graph = KnowledgeGraphStore(self.root).load()
        findings = self._load_findings()
        theses = self._load_theses()
        intelligence = self._load_intelligence()
        new_documents = _new_documents(intake_manifest, drive_manifest)
        limitations = _limitations(intake_manifest, drive_manifest, evidence_records, graph.nodes, findings, theses, intelligence)
        actions = _recommended_actions(intake_manifest, drive_manifest, evidence_records, graph.nodes, findings, theses, intelligence)
        brief_id = _brief_id(intake_manifest, drive_manifest, evidence_records, graph.nodes, graph.edges, findings, theses, intelligence)
        return MorningExecutiveBrief(
            brief_id=brief_id,
            created_at=created_at,
            intake_summary=_intake_summary(intake_manifest),
            google_drive_sync_summary=_drive_summary(drive_manifest),
            new_documents_detected=new_documents,
            evidence_count=len(evidence_records),
            graph_node_count=len(graph.nodes),
            graph_edge_count=len(graph.edges),
            top_findings=_top_findings(findings),
            top_theses=_top_theses(theses),
            intelligence_summary=_intelligence_summary(intelligence),
            risks_or_gaps=_risks_or_gaps(findings, theses, intelligence),
            recommended_next_actions=actions,
            provenance_references={
                "intake_manifest": "outputs/intake/intake-manifest.json" if intake_manifest else None,
                "google_drive_sync_manifest": "outputs/google-drive/google-drive-sync-manifest.json" if drive_manifest else None,
                "evidence": "memory/evidence/",
                "knowledge_graph": "memory/graph/graph.json",
                "cross_document_analysis": "outputs/analysis/cross-document-analysis.json" if findings else None,
                "theses": "outputs/theses/theses.json" if theses else None,
                "intelligence": "outputs/intelligence/institutional-intelligence.json" if intelligence else None,
            },
            limitations=limitations,
        )

    def _load_findings(self) -> list[JsonMap]:
        try:
            return [finding.to_dict() for finding in CrossDocumentAnalysisStore(self.root).list_findings()]
        except CrossDocumentError:
            return []

    def _load_theses(self) -> list[JsonMap]:
        try:
            return [thesis.to_dict() for thesis in ThesisStore(self.root).load()]
        except ThesisError:
            return []

    def _load_intelligence(self) -> JsonMap | None:
        try:
            return IntelligenceStore(self.root).load().to_dict()
        except IntelligenceError:
            return None


class MorningExecutiveStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "outputs" / "morning"
        self.json_path = self.directory / "morning-brief.json"
        self.markdown_path = self.directory / "morning-brief.md"

    def generate(self, *, overwrite: bool = False) -> MorningExecutiveBrief:
        if (self.json_path.exists() or self.markdown_path.exists()) and not overwrite:
            raise MorningExecutiveError("Morning brief already exists. Use --overwrite to replace it.")
        brief = MorningExecutiveEngine(self.root).generate()
        self.save(brief)
        return brief

    def save(self, brief: MorningExecutiveBrief) -> None:
        write_json(self.json_path, brief.to_dict())
        self.markdown_path.parent.mkdir(parents=True, exist_ok=True)
        self.markdown_path.write_text(render_morning_markdown(brief), encoding="utf-8")

    def load(self) -> MorningExecutiveBrief:
        if not self.json_path.exists():
            raise MorningExecutiveError("No morning brief found. Run morning first.")
        return MorningExecutiveBrief.from_dict(read_json(self.json_path))

    def export(self) -> Path:
        brief = self.load()
        self.markdown_path.parent.mkdir(parents=True, exist_ok=True)
        self.markdown_path.write_text(render_morning_markdown(brief), encoding="utf-8")
        return self.markdown_path


def render_morning_markdown(brief: MorningExecutiveBrief) -> str:
    lines = [
        "# Morning Executive Intelligence",
        "",
        f"Brief ID: `{brief.brief_id}`",
        f"Created: `{brief.created_at}`",
        "",
        "## Intake Summary",
        "",
        *_summary_lines(brief.intake_summary),
        "## Google Drive Sync Summary",
        "",
        *_summary_lines(brief.google_drive_sync_summary),
        "## New Documents Detected",
        "",
        *_item_lines(brief.new_documents_detected, "name"),
        "## Evidence",
        "",
        f"- Evidence records: {brief.evidence_count}",
        "",
        "## Knowledge Graph",
        "",
        f"- Nodes: {brief.graph_node_count}",
        f"- Edges: {brief.graph_edge_count}",
        "",
        "## Top Findings",
        "",
        *_item_lines(brief.top_findings, "title"),
        "## Top Theses",
        "",
        *_item_lines(brief.top_theses, "title"),
        "## Intelligence Summary",
        "",
        *_summary_lines(brief.intelligence_summary),
        "## Risks Or Gaps",
        "",
        *_string_lines(brief.risks_or_gaps),
        "## Recommended Next Actions",
        "",
        *_string_lines(brief.recommended_next_actions),
        "## Provenance References",
        "",
        *_summary_lines(brief.provenance_references),
        "## Limitations",
        "",
        *_string_lines(brief.limitations),
    ]
    return "\n".join(lines)


def _intake_summary(manifest: JsonMap | None) -> JsonMap:
    if not manifest:
        return {"present": False, "imported": 0, "skipped": 0, "duplicates": 0, "errors": 0, "total": 0}
    counts = _map(manifest.get("counts"))
    return {
        "present": True,
        "manifest_id": manifest.get("manifest_id"),
        "updated_at": manifest.get("updated_at"),
        "imported": counts.get("imported", 0),
        "skipped": counts.get("skipped", 0),
        "duplicates": counts.get("duplicates", 0),
        "errors": counts.get("errors", 0),
        "total": counts.get("total", 0),
    }


def _drive_summary(manifest: JsonMap | None) -> JsonMap:
    if not manifest:
        return {"present": False, "downloaded": 0, "skipped": 0, "duplicates": 0, "errors": 0}
    return {
        "present": True,
        "sync_id": manifest.get("sync_id"),
        "created_at": manifest.get("created_at"),
        "downloaded": len(_list(manifest.get("downloaded_files"))),
        "skipped": len(_list(manifest.get("skipped_files"))),
        "duplicates": len(_list(manifest.get("duplicate_files"))),
        "errors": len(_list(manifest.get("errors"))),
    }


def _new_documents(intake_manifest: JsonMap | None, drive_manifest: JsonMap | None) -> list[JsonMap]:
    docs: list[JsonMap] = []
    if drive_manifest:
        for item in _list(drive_manifest.get("downloaded_files")):
            if isinstance(item, dict):
                docs.append({"name": item.get("name"), "source": "google-drive", "status": item.get("status"), "path": item.get("destination_path")})
    if intake_manifest:
        for item in _list(intake_manifest.get("items")):
            if isinstance(item, dict) and item.get("status") == "imported":
                docs.append({"name": Path(str(item.get("destination_path") or item.get("original_path") or "")).name, "source": item.get("source_channel"), "status": "imported", "path": item.get("destination_path")})
    return sorted(docs, key=lambda item: (str(item.get("source")), str(item.get("name")), str(item.get("path"))))[:10]


def _top_findings(findings: list[JsonMap]) -> list[JsonMap]:
    return [
        {
            "finding_id": finding.get("finding_id"),
            "finding_type": finding.get("finding_type"),
            "title": finding.get("title"),
            "confidence": finding.get("confidence"),
        }
        for finding in sorted(findings, key=lambda item: (_confidence_rank(str(item.get("confidence"))), str(item.get("title"))))[:5]
    ]


def _top_theses(theses: list[JsonMap]) -> list[JsonMap]:
    return [
        {
            "thesis_id": thesis.get("thesis_id"),
            "thesis_type": thesis.get("thesis_type"),
            "title": thesis.get("title"),
            "confidence": thesis.get("confidence"),
            "status": thesis.get("status"),
        }
        for thesis in sorted(theses, key=lambda item: (_confidence_rank(str(item.get("confidence"))), str(item.get("title"))))[:5]
    ]


def _intelligence_summary(brief: JsonMap | None) -> JsonMap:
    if not brief:
        return {"present": False, "summary": "No institutional intelligence brief found."}
    return {
        "present": True,
        "brief_id": brief.get("brief_id"),
        "status": brief.get("status"),
        "summary": brief.get("summary"),
        "overall_confidence": _map(brief.get("confidence_assessment")).get("overall_label"),
    }


def _risks_or_gaps(findings: list[JsonMap], theses: list[JsonMap], intelligence: JsonMap | None) -> list[str]:
    risks = []
    for finding in findings:
        if finding.get("finding_type") in {"repeated_risk", "missing_evidence", "possible_contradiction"}:
            risks.append(str(finding.get("title", "Untitled finding")))
    for thesis in theses:
        if thesis.get("thesis_type") in {"emerging_risk", "evidence_gap", "contradiction_watch"}:
            risks.append(str(thesis.get("title", "Untitled thesis")))
    if intelligence:
        risks.extend(_string_list(intelligence.get("limitations", [])))
    return sorted(set(risks))[:10]


def _limitations(
    intake_manifest: JsonMap | None,
    drive_manifest: JsonMap | None,
    evidence_records: list[JsonMap],
    graph_nodes: dict[str, Any],
    findings: list[JsonMap],
    theses: list[JsonMap],
    intelligence: JsonMap | None,
) -> list[str]:
    limitations = ["Generated only from existing deterministic local artifacts; no upstream workflow was run."]
    if not intake_manifest:
        limitations.append("No intake manifest found.")
    if not drive_manifest:
        limitations.append("No Google Drive sync manifest found.")
    if not evidence_records:
        limitations.append("No evidence records found.")
    if not graph_nodes:
        limitations.append("No knowledge graph nodes found.")
    if not findings:
        limitations.append("No cross-document findings found.")
    if not theses:
        limitations.append("No institutional theses found.")
    if not intelligence:
        limitations.append("No institutional intelligence brief found.")
    return limitations


def _recommended_actions(
    intake_manifest: JsonMap | None,
    drive_manifest: JsonMap | None,
    evidence_records: list[JsonMap],
    graph_nodes: dict[str, Any],
    findings: list[JsonMap],
    theses: list[JsonMap],
    intelligence: JsonMap | None,
) -> list[str]:
    actions = ["Review this morning brief before making operational decisions."]
    if not drive_manifest:
        actions.append("Run `python -m constellation drive sync --dry-run` if Google Drive sources are configured.")
    if not intake_manifest:
        actions.append("Run `python -m constellation intake scan` and `python -m constellation intake import` when local intake files are ready.")
    if not evidence_records:
        actions.append("Run a research or PKOS workflow to create evidence records.")
    if not graph_nodes:
        actions.append("Run `python -m constellation graph build RUN_ID` after workflow execution.")
    if not findings:
        actions.append("Run `python -m constellation graph analyze` after building graph records.")
    if not theses:
        actions.append("Run `python -m constellation thesis generate` after cross-document analysis.")
    if not intelligence:
        actions.append("Run `python -m constellation intelligence generate` after thesis generation.")
    return actions


def _brief_id(
    intake_manifest: JsonMap | None,
    drive_manifest: JsonMap | None,
    evidence_records: list[JsonMap],
    graph_nodes: dict[str, Any],
    graph_edges: dict[str, Any],
    findings: list[JsonMap],
    theses: list[JsonMap],
    intelligence: JsonMap | None,
) -> str:
    fingerprint = "|".join(
        [
            str(_map(intake_manifest).get("manifest_id")),
            str(_map(drive_manifest).get("sync_id")),
            ",".join(sorted(str(item.get("evidence_id")) for item in evidence_records)),
            ",".join(sorted(graph_nodes)),
            ",".join(sorted(graph_edges)),
            ",".join(sorted(str(item.get("finding_id")) for item in findings)),
            ",".join(sorted(str(item.get("thesis_id")) for item in theses)),
            str(_map(intelligence).get("brief_id")),
        ]
    )
    return f"morning_{sha256(fingerprint.encode('utf-8')).hexdigest()[:16]}"


def _read_optional_json(path: Path) -> JsonMap | None:
    if not path.exists():
        return None
    try:
        return read_json(path)
    except Exception:
        return None


def _summary_lines(summary: JsonMap) -> list[str]:
    if not summary:
        return ["- None", ""]
    return [*[f"- {key}: `{value}`" for key, value in summary.items()], ""]


def _item_lines(items: list[JsonMap], label_key: str) -> list[str]:
    if not items:
        return ["- None", ""]
    lines = []
    for item in items:
        label = item.get(label_key) or item.get("id") or item.get("brief_id") or "unknown"
        lines.append(f"- `{label}`")
    lines.append("")
    return lines


def _string_lines(items: list[str]) -> list[str]:
    if not items:
        return ["- None", ""]
    return [*[f"- {item}" for item in items], ""]


def _confidence_rank(value: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(value, 3)


def _map(value: Any) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _list(value: Any) -> list[Any]:
    return value if isinstance(value, list) else []


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
        raise MorningExecutiveError(f"Morning brief field {key} must be a string")
    return value
