from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from . import __version__
from .io import read_json, write_json
from .models import JsonMap


class InstitutionalResearchReportError(RuntimeError):
    pass


EXPECTED_REPORT_INPUTS = {
    "dashboard": Path("outputs/dashboard/dashboard.json"),
    "daily": Path("outputs/daily/daily-run.json"),
    "morning": Path("outputs/morning/morning-brief.json"),
    "evolution": Path("outputs/evolution/evolution.json"),
    "evolution_trends": Path("outputs/evolution/trend-report.md"),
    "thesis": Path("outputs/thesis/theses.json"),
    "thesis_report": Path("outputs/thesis/thesis-report.md"),
    "evidence_graph": Path("outputs/evidence-graph/evidence-graph.json"),
    "memory_snapshot": Path("outputs/memory/latest-snapshot.json"),
    "source_monitor": Path("outputs/source-monitor/latest-monitor.json"),
    "workflow": Path("outputs/workflows/latest-workflow.json"),
    "intake": Path("outputs/intake/intake-manifest.json"),
    "google_drive": Path("outputs/google-drive/google-drive-sync-manifest.json"),
}


@dataclass(frozen=True)
class ReportSection:
    title: str
    summary: str
    items: list[str]
    available: bool

    def to_dict(self) -> JsonMap:
        return {"title": self.title, "summary": self.summary, "items": self.items, "available": self.available}

    @classmethod
    def from_dict(cls, data: JsonMap) -> "ReportSection":
        return cls(
            title=_require_str(data, "title"),
            summary=_require_str(data, "summary"),
            items=_string_list(data.get("items", [])),
            available=bool(data.get("available")),
        )


@dataclass(frozen=True)
class ReportEvidenceReference:
    evidence_id: str
    source_id: str | None
    thesis_ids: list[str]
    artifact_ids: list[str]
    summary: str

    def to_dict(self) -> JsonMap:
        return {
            "evidence_id": self.evidence_id,
            "source_id": self.source_id,
            "thesis_ids": self.thesis_ids,
            "artifact_ids": self.artifact_ids,
            "summary": self.summary,
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "ReportEvidenceReference":
        return cls(
            evidence_id=_require_str(data, "evidence_id"),
            source_id=_optional_str(data.get("source_id")),
            thesis_ids=_string_list(data.get("thesis_ids", [])),
            artifact_ids=_string_list(data.get("artifact_ids", [])),
            summary=_require_str(data, "summary"),
        )


@dataclass(frozen=True)
class InstitutionalResearchReport:
    report_id: str
    created_at: str
    version: str
    title: str
    sections: list[ReportSection]
    evidence_references: list[ReportEvidenceReference]
    thesis_references: list[str]
    source_documents: list[str]
    risks_gaps: list[str]
    open_questions: list[str]
    recommended_next_actions: list[str]
    missing_artifacts: list[str]
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return {
            "report_id": self.report_id,
            "created_at": self.created_at,
            "version": self.version,
            "title": self.title,
            "sections": [section.to_dict() for section in self.sections],
            "evidence_references": [reference.to_dict() for reference in self.evidence_references],
            "thesis_references": self.thesis_references,
            "source_documents": self.source_documents,
            "risks_gaps": self.risks_gaps,
            "open_questions": self.open_questions,
            "recommended_next_actions": self.recommended_next_actions,
            "missing_artifacts": self.missing_artifacts,
            "provenance": self.provenance,
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "InstitutionalResearchReport":
        return cls(
            report_id=_require_str(data, "report_id"),
            created_at=_require_str(data, "created_at"),
            version=_require_str(data, "version"),
            title=_require_str(data, "title"),
            sections=[ReportSection.from_dict(item) for item in _map_list(data.get("sections", []))],
            evidence_references=[ReportEvidenceReference.from_dict(item) for item in _map_list(data.get("evidence_references", []))],
            thesis_references=_string_list(data.get("thesis_references", [])),
            source_documents=_string_list(data.get("source_documents", [])),
            risks_gaps=_string_list(data.get("risks_gaps", [])),
            open_questions=_string_list(data.get("open_questions", [])),
            recommended_next_actions=_string_list(data.get("recommended_next_actions", [])),
            missing_artifacts=_string_list(data.get("missing_artifacts", [])),
            provenance=_map(data.get("provenance")),
        )


class InstitutionalResearchReportBuilder:
    def __init__(self, root: Path) -> None:
        self.root = root

    def build(self) -> InstitutionalResearchReport:
        artifacts = {name: _read_optional_json(self.root / path) for name, path in EXPECTED_REPORT_INPUTS.items() if path.suffix == ".json"}
        status = self.status()
        missing = sorted(name for name, item in status.items() if not item["exists"])
        dashboard = _map(artifacts.get("dashboard"))
        daily = _map(artifacts.get("daily"))
        morning = _map(artifacts.get("morning"))
        evolution = _map(artifacts.get("evolution"))
        thesis = _map(artifacts.get("thesis"))
        evidence_graph = _map(artifacts.get("evidence_graph"))
        memory = _map(artifacts.get("memory_snapshot"))
        monitor = _map(artifacts.get("source_monitor"))
        workflow = _map(artifacts.get("workflow"))
        intake = _map(artifacts.get("intake"))
        drive = _map(artifacts.get("google_drive"))
        evidence_refs = _evidence_references(evidence_graph, thesis)
        thesis_ids = _thesis_ids(thesis, evidence_graph)
        source_docs = _source_documents(memory, intake, drive, evidence_graph)
        risks = _risks_gaps(dashboard, morning, thesis)
        questions = _open_questions(morning, thesis)
        actions = _actions(dashboard, morning)
        sections = [
            _executive_summary(dashboard, daily, evolution, evidence_refs, thesis_ids, risks),
            _what_changed(evolution, daily),
            _key_evidence(evidence_refs),
            _thesis_intelligence(thesis),
            _knowledge_evolution(evolution),
            _source_activity(monitor, drive, intake),
            ReportSection("Risks and Gaps", f"{len(risks)} risks or gaps identified from available artifacts.", risks, bool(risks)),
            ReportSection("Open Questions", f"{len(questions)} open questions identified.", questions, bool(questions)),
            ReportSection("Recommended Next Actions", f"{len(actions)} recommended next actions identified.", actions, bool(actions)),
            _evidence_reference_section(evidence_refs),
            ReportSection("Source Documents", f"{len(source_docs)} source document references found.", source_docs, bool(source_docs)),
            ReportSection("Limitations", "Missing artifacts are reported as unavailable; values are not fabricated.", _limitations(missing), True),
            ReportSection("Provenance", "Report generated from local deterministic Constellation artifacts.", [f"{key}: {path}" for key, path in _provenance().items()], True),
        ]
        report_id = _report_id(artifacts, evidence_refs, thesis_ids, source_docs, risks, questions, actions)
        return InstitutionalResearchReport(
            report_id=report_id,
            created_at=_now_iso(),
            version=__version__,
            title="Institutional Research Report",
            sections=sections,
            evidence_references=evidence_refs,
            thesis_references=thesis_ids,
            source_documents=source_docs,
            risks_gaps=risks,
            open_questions=questions,
            recommended_next_actions=actions,
            missing_artifacts=missing,
            provenance=_provenance(),
        )

    def status(self) -> JsonMap:
        return {
            name: {"path": str(path), "exists": (self.root / path).exists(), "kind": "json" if path.suffix == ".json" else "markdown"}
            for name, path in EXPECTED_REPORT_INPUTS.items()
        }


class InstitutionalResearchReportStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "outputs" / "reports"
        self.json_path = self.directory / "latest-report.json"
        self.markdown_path = self.directory / "latest-report.md"
        self.history_path = self.directory / "report-history.json"

    def generate(self) -> InstitutionalResearchReport:
        report = InstitutionalResearchReportBuilder(self.root).build()
        self.save(report)
        return report

    def save(self, report: InstitutionalResearchReport) -> None:
        write_json(self.json_path, report.to_dict())
        self.markdown_path.parent.mkdir(parents=True, exist_ok=True)
        self.markdown_path.write_text(render_report_markdown(report), encoding="utf-8")
        history = self.history()
        history.append(report)
        write_json(self.history_path, {"reports": [item.to_dict() for item in history]})

    def load(self) -> InstitutionalResearchReport:
        if not self.json_path.exists():
            raise InstitutionalResearchReportError("No institutional research report found. Run `python -m constellation report latest` first.")
        return InstitutionalResearchReport.from_dict(read_json(self.json_path))

    def history(self) -> list[InstitutionalResearchReport]:
        if not self.history_path.exists():
            return []
        data = read_json(self.history_path)
        return [InstitutionalResearchReport.from_dict(item) for item in _map_list(data.get("reports", []))]

    def show(self, report_id: str) -> InstitutionalResearchReport:
        for report in self.history():
            if report.report_id == report_id:
                return report
        current = self.load()
        if current.report_id == report_id:
            return current
        raise InstitutionalResearchReportError(f"Unknown report ID: {report_id}")

    def export(self, report: InstitutionalResearchReport | None = None) -> Path:
        report = report or self.load()
        self.markdown_path.parent.mkdir(parents=True, exist_ok=True)
        self.markdown_path.write_text(render_report_markdown(report), encoding="utf-8")
        return self.markdown_path

    def status(self) -> JsonMap:
        status = InstitutionalResearchReportBuilder(self.root).status()
        available = sum(1 for item in status.values() if item["exists"])
        return {
            "inputs": status,
            "available_inputs": available,
            "total_inputs": len(status),
            "latest_report_exists": self.json_path.exists(),
            "latest_report_path": str(self.json_path),
            "markdown_path": str(self.markdown_path),
        }


def render_report_markdown(report: InstitutionalResearchReport) -> str:
    lines = [
        f"# {report.title}",
        "",
        f"- Report ID: `{report.report_id}`",
        f"- Created: `{report.created_at}`",
        f"- Version: `{report.version}`",
        "",
    ]
    for section in report.sections:
        lines.extend([f"## {section.title}", "", section.summary, ""])
        lines.extend(_bullet_lines(section.items))
    return "\n".join(lines)


def report_summary(report: InstitutionalResearchReport) -> JsonMap:
    return {
        "report_id": report.report_id,
        "created_at": report.created_at,
        "sections_available": sum(1 for section in report.sections if section.available),
        "section_count": len(report.sections),
        "risks_gaps_count": len(report.risks_gaps),
        "open_questions_count": len(report.open_questions),
        "evidence_references_count": len(report.evidence_references),
        "thesis_references_count": len(report.thesis_references),
        "missing_artifacts": report.missing_artifacts,
        "report_path": "outputs/reports/latest-report.md",
    }


def _executive_summary(dashboard: JsonMap, daily: JsonMap, evolution: JsonMap, evidence_refs: list[ReportEvidenceReference], thesis_ids: list[str], risks: list[str]) -> ReportSection:
    summary = _map(dashboard.get("executive_summary"))
    items = [
        f"Daily status: {_map(daily).get('status', summary.get('status', 'unavailable'))}",
        f"Evidence references: {len(evidence_refs)}",
        f"Thesis references: {len(thesis_ids)}",
        f"Risks or gaps: {len(risks)}",
        f"Longitudinal health score: {_map(_map(evolution).get('delta')).get('longitudinal_health_score', 'unavailable')}",
    ]
    return ReportSection("Executive Summary", "Current institutional research state generated from deterministic local artifacts.", items, bool(dashboard or daily or evolution))


def _what_changed(evolution: JsonMap, daily: JsonMap) -> ReportSection:
    delta = _map(evolution.get("delta"))
    items = [
        f"Evidence gained: {len(_list(delta.get('evidence_gained')))}",
        f"Evidence removed: {len(_list(delta.get('evidence_removed')))}",
        f"Graph node growth: {_int(delta.get('graph_node_growth')):+}",
        f"Graph edge growth: {_int(delta.get('graph_edge_growth')):+}",
        f"Daily run: {_map(daily).get('run_id', 'unavailable')}",
    ]
    return ReportSection("What Changed", delta.get("summary", "No knowledge evolution delta is available."), items, bool(delta))


def _key_evidence(references: list[ReportEvidenceReference]) -> ReportSection:
    items = [f"{ref.evidence_id}: {ref.summary}" for ref in references[:12]]
    return ReportSection("Key Evidence", f"{len(references)} evidence references are available.", items, bool(references))


def _thesis_intelligence(thesis: JsonMap) -> ReportSection:
    theses = _map_list(thesis.get("theses", []))
    items = []
    for item in theses[:12]:
        confidence = item.get("confidence")
        label = _map(confidence).get("label") if isinstance(confidence, dict) else confidence
        items.append(f"{item.get('thesis_id')}: {item.get('status', 'unknown')} confidence={label or 'unknown'}")
    return ReportSection("Thesis Intelligence", f"{len(theses)} thesis records are available.", items, bool(theses))


def _knowledge_evolution(evolution: JsonMap) -> ReportSection:
    delta = _map(evolution.get("delta"))
    items = [
        f"Delta ID: {delta.get('delta_id', 'unavailable')}",
        f"Trend records: {len(_map_list(delta.get('trend_records', [])))}",
        f"Thesis confidence changes: {len(_map_list(delta.get('thesis_confidence_changes', [])))}",
        f"Thesis status changes: {len(_map_list(delta.get('thesis_status_changes', [])))}",
    ]
    return ReportSection("Knowledge Evolution", delta.get("summary", "No knowledge evolution report is available."), items, bool(delta))


def _source_activity(monitor: JsonMap, drive: JsonMap, intake: JsonMap) -> ReportSection:
    summary = _map(monitor.get("summary"))
    counts = _map(intake.get("counts"))
    items = [
        f"Sources checked: {summary.get('sources_checked', 0)}",
        f"Sources changed: {summary.get('sources_changed', 0)}",
        f"Intake imported: {counts.get('imported', 0)}",
        f"Google Drive downloaded: {len(_list(drive.get('downloaded_files')))}",
    ]
    return ReportSection("Source Activity", "Source activity is summarized from local source monitor, intake, and Google Drive manifests.", items, bool(monitor or drive or intake))


def _evidence_reference_section(references: list[ReportEvidenceReference]) -> ReportSection:
    items = []
    for reference in references[:25]:
        thesis_text = ", ".join(reference.thesis_ids) if reference.thesis_ids else "none"
        items.append(f"{reference.evidence_id} source={reference.source_id or 'unknown'} theses={thesis_text}")
    return ReportSection("Evidence References", f"{len(references)} evidence references are included.", items, bool(references))


def _evidence_references(evidence_graph: JsonMap, thesis_store: JsonMap) -> list[ReportEvidenceReference]:
    nodes = _map_list(evidence_graph.get("nodes", []))
    edges = _map_list(evidence_graph.get("edges", []))
    thesis_by_evidence: dict[str, set[str]] = {}
    artifact_by_evidence: dict[str, set[str]] = {}
    for thesis in _map_list(thesis_store.get("theses", [])):
        thesis_id = thesis.get("thesis_id")
        if not isinstance(thesis_id, str):
            continue
        for evidence_id in _string_list(thesis.get("supporting_evidence_ids", [])) + _string_list(thesis.get("conflicting_evidence_ids", [])):
            thesis_by_evidence.setdefault(evidence_id, set()).add(thesis_id)
    for edge in edges:
        edge_type = edge.get("edge_type") or edge.get("relationship_type")
        if edge_type not in {"supports", "references", "derived_from", "contributes_to"}:
            continue
        evidence_ids = _string_list(edge.get("evidence_ids", []))
        source = str(edge.get("source_node_id", ""))
        target = str(edge.get("target_node_id", ""))
        for evidence_id in evidence_ids:
            for value in [source, target]:
                if "thesis" in value:
                    thesis_by_evidence.setdefault(evidence_id, set()).add(value)
                if "artifact" in value:
                    artifact_by_evidence.setdefault(evidence_id, set()).add(value)
    references = []
    for node in nodes:
        if node.get("node_type") != "evidence":
            continue
        evidence_id = str(node.get("metadata", {}).get("evidence_id") or node.get("evidence_id") or node.get("node_id"))
        references.append(
            ReportEvidenceReference(
                evidence_id=evidence_id,
                source_id=_first(_string_list(node.get("source_ids", []))),
                thesis_ids=sorted(thesis_by_evidence.get(evidence_id, set())),
                artifact_ids=sorted(artifact_by_evidence.get(evidence_id, set()) | set(_string_list(node.get("artifact_ids", [])))),
                summary=str(node.get("label") or node.get("description") or evidence_id),
            )
        )
    if references:
        return sorted(references, key=lambda item: item.evidence_id)
    for thesis in _map_list(thesis_store.get("theses", [])):
        thesis_id = thesis.get("thesis_id")
        if not isinstance(thesis_id, str):
            continue
        for evidence_id in _string_list(thesis.get("supporting_evidence_ids", [])):
            references.append(ReportEvidenceReference(evidence_id, None, [thesis_id], [], f"Referenced by thesis {thesis_id}."))
    return sorted(references, key=lambda item: item.evidence_id)


def _thesis_ids(thesis: JsonMap, evidence_graph: JsonMap) -> list[str]:
    ids = {str(item.get("thesis_id")) for item in _map_list(thesis.get("theses", [])) if item.get("thesis_id")}
    for node in _map_list(evidence_graph.get("nodes", [])):
        if node.get("node_type") == "thesis":
            ids.add(str(node.get("node_id")))
    return sorted(ids)


def _source_documents(memory: JsonMap, intake: JsonMap, drive: JsonMap, evidence_graph: JsonMap) -> list[str]:
    docs = set(_string_list(memory.get("source_document_references", [])))
    for item in _map_list(intake.get("items", [])):
        path = item.get("destination_path") or item.get("original_path")
        if isinstance(path, str):
            docs.add(path)
    for item in _map_list(drive.get("downloaded_files", [])):
        path = item.get("destination_path") or item.get("name")
        if isinstance(path, str):
            docs.add(path)
    for node in _map_list(evidence_graph.get("nodes", [])):
        for source_id in _string_list(node.get("source_ids", [])):
            docs.add(source_id)
    return sorted(docs)


def _risks_gaps(dashboard: JsonMap, morning: JsonMap, thesis: JsonMap) -> list[str]:
    risks = set(_string_list(dashboard.get("current_risks_gaps", [])) + _string_list(morning.get("risks_or_gaps", [])))
    for item in _map_list(thesis.get("theses", [])):
        if item.get("status") == "weakening":
            risks.add(f"Weakening thesis: {item.get('title') or item.get('thesis_id')}")
        confidence = item.get("confidence")
        label = _map(confidence).get("label") if isinstance(confidence, dict) else confidence
        if label == "low":
            risks.add(f"Low-confidence thesis: {item.get('title') or item.get('thesis_id')}")
    return sorted(risks)


def _open_questions(morning: JsonMap, thesis: JsonMap) -> list[str]:
    questions = set()
    for item in _string_list(morning.get("open_questions", [])):
        questions.add(item)
    for thesis_item in _map_list(thesis.get("theses", [])):
        if not thesis_item.get("supporting_evidence_ids"):
            questions.add(f"What evidence is needed to support thesis {thesis_item.get('thesis_id')}?")
    return sorted(questions)


def _actions(dashboard: JsonMap, morning: JsonMap) -> list[str]:
    return sorted(set(_string_list(dashboard.get("recommended_next_actions", [])) + _string_list(morning.get("recommended_next_actions", []))))


def _limitations(missing: list[str]) -> list[str]:
    items = [
        "Report is generated from existing local deterministic artifacts only.",
        "Missing artifacts are marked unavailable.",
        "No claims are created beyond available evidence, thesis, dashboard, memory, and evolution records.",
    ]
    if missing:
        items.append("Unavailable artifacts: " + ", ".join(missing) + ".")
    return items


def _provenance() -> JsonMap:
    return {name: str(path) for name, path in EXPECTED_REPORT_INPUTS.items()}


def _report_id(artifacts: JsonMap, evidence_refs: list[ReportEvidenceReference], thesis_ids: list[str], source_docs: list[str], risks: list[str], questions: list[str], actions: list[str]) -> str:
    identifiers = []
    for artifact in artifacts.values():
        if isinstance(artifact, dict):
            identifiers.append(str(artifact.get("dashboard_id") or artifact.get("run_id") or artifact.get("brief_id") or artifact.get("delta_id") or artifact.get("monitor_id") or artifact.get("manifest_id") or artifact.get("sync_id") or ""))
            if isinstance(artifact.get("delta"), dict):
                identifiers.append(str(artifact["delta"].get("delta_id", "")))
    payload = "|".join([",".join(sorted(identifiers)), ",".join(ref.evidence_id for ref in evidence_refs), ",".join(thesis_ids), ",".join(source_docs), ",".join(risks), ",".join(questions), ",".join(actions)])
    return f"report_{_digest(payload)}"


def _read_optional_json(path: Path) -> JsonMap:
    if not path.exists():
        return {}
    try:
        data = read_json(path)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _bullet_lines(items: list[str]) -> list[str]:
    if not items:
        return ["- None", ""]
    return [*[f"- {item}" for item in items], ""]


def _first(items: list[str]) -> str | None:
    return items[0] if items else None


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
        raise InstitutionalResearchReportError(f"Institutional research report field {key} must be a string")
    return value
