from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from . import __version__
from .io import read_json, write_json
from .models import JsonMap
from .real_estate import RealEstateAssignmentStore


class ExecutiveDashboardError(RuntimeError):
    pass


EXPECTED_ARTIFACTS = {
    "daily_run": Path("outputs/daily/daily-run.json"),
    "daily_report": Path("outputs/daily/daily-report.md"),
    "morning_brief": Path("outputs/morning/morning-brief.json"),
    "latest_snapshot": Path("outputs/memory/latest-snapshot.json"),
    "latest_delta": Path("outputs/memory/latest-delta.json"),
    "evidence_graph": Path("outputs/evidence-graph/evidence-graph.json"),
    "thesis_records": Path("outputs/thesis/theses.json"),
    "thesis_report": Path("outputs/thesis/thesis-report.md"),
    "google_drive_sync": Path("outputs/google-drive/google-drive-sync-manifest.json"),
    "intake_manifest": Path("outputs/intake/intake-manifest.json"),
    "source_monitor": Path("outputs/source-monitor/latest-monitor.json"),
    "latest_workflow": Path("outputs/workflows/latest-workflow.json"),
    "knowledge_evolution": Path("outputs/evolution/evolution.json"),
    "institutional_report": Path("outputs/reports/latest-report.json"),
    "ai_markets": Path("outputs/ai-markets/ai-markets.json"),
    "performance": Path("outputs/performance/performance-intelligence.json"),
    "thesis_accuracy": Path("outputs/performance/thesis-accuracy.json"),
}


@dataclass(frozen=True)
class ExecutiveDashboard:
    dashboard_id: str
    created_at: str
    version: str
    executive_summary: JsonMap
    daily_pipeline_status: JsonMap
    intake_google_drive_summary: JsonMap
    evidence_summary: JsonMap
    evidence_graph_summary: JsonMap
    thesis_intelligence_summary: JsonMap
    institutional_memory_summary: JsonMap
    morning_brief_summary: JsonMap
    source_monitoring_summary: JsonMap
    workflow_automation_summary: JsonMap
    knowledge_evolution_summary: JsonMap
    institutional_research_report_summary: JsonMap
    ai_markets_summary: JsonMap
    performance_intelligence_summary: JsonMap
    thesis_accuracy_summary: JsonMap
    real_estate_assignment_summary: JsonMap
    connector_warning_summary: JsonMap
    current_risks_gaps: list[str]
    recommended_next_actions: list[str]
    key_output_files: list[JsonMap]
    limitations: list[str]
    provenance: JsonMap
    artifact_status: JsonMap

    def to_dict(self) -> JsonMap:
        return {
            "dashboard_id": self.dashboard_id,
            "created_at": self.created_at,
            "version": self.version,
            "executive_summary": self.executive_summary,
            "daily_pipeline_status": self.daily_pipeline_status,
            "intake_google_drive_summary": self.intake_google_drive_summary,
            "evidence_summary": self.evidence_summary,
            "evidence_graph_summary": self.evidence_graph_summary,
            "thesis_intelligence_summary": self.thesis_intelligence_summary,
            "institutional_memory_summary": self.institutional_memory_summary,
            "morning_brief_summary": self.morning_brief_summary,
            "source_monitoring_summary": self.source_monitoring_summary,
            "workflow_automation_summary": self.workflow_automation_summary,
            "knowledge_evolution_summary": self.knowledge_evolution_summary,
            "institutional_research_report_summary": self.institutional_research_report_summary,
            "ai_markets_summary": self.ai_markets_summary,
            "performance_intelligence_summary": self.performance_intelligence_summary,
            "thesis_accuracy_summary": self.thesis_accuracy_summary,
            "real_estate_assignment_summary": self.real_estate_assignment_summary,
            "connector_warning_summary": self.connector_warning_summary,
            "current_risks_gaps": self.current_risks_gaps,
            "recommended_next_actions": self.recommended_next_actions,
            "key_output_files": self.key_output_files,
            "limitations": self.limitations,
            "provenance": self.provenance,
            "artifact_status": self.artifact_status,
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "ExecutiveDashboard":
        return cls(
            dashboard_id=_require_str(data, "dashboard_id"),
            created_at=_require_str(data, "created_at"),
            version=_require_str(data, "version"),
            executive_summary=_map(data.get("executive_summary")),
            daily_pipeline_status=_map(data.get("daily_pipeline_status")),
            intake_google_drive_summary=_map(data.get("intake_google_drive_summary")),
            evidence_summary=_map(data.get("evidence_summary")),
            evidence_graph_summary=_map(data.get("evidence_graph_summary")),
            thesis_intelligence_summary=_map(data.get("thesis_intelligence_summary")),
            institutional_memory_summary=_map(data.get("institutional_memory_summary")),
            morning_brief_summary=_map(data.get("morning_brief_summary")),
            source_monitoring_summary=_map(data.get("source_monitoring_summary")),
            workflow_automation_summary=_map(data.get("workflow_automation_summary")),
            knowledge_evolution_summary=_map(data.get("knowledge_evolution_summary")),
            institutional_research_report_summary=_map(data.get("institutional_research_report_summary")),
            ai_markets_summary=_map(data.get("ai_markets_summary")),
            performance_intelligence_summary=_map(data.get("performance_intelligence_summary")),
            thesis_accuracy_summary=_map(data.get("thesis_accuracy_summary")),
            real_estate_assignment_summary=_map(data.get("real_estate_assignment_summary")),
            connector_warning_summary=_map(data.get("connector_warning_summary")),
            current_risks_gaps=_string_list(data.get("current_risks_gaps", [])),
            recommended_next_actions=_string_list(data.get("recommended_next_actions", [])),
            key_output_files=_map_list(data.get("key_output_files", [])),
            limitations=_string_list(data.get("limitations", [])),
            provenance=_map(data.get("provenance")),
            artifact_status=_map(data.get("artifact_status")),
        )


class ExecutiveDashboardBuilder:
    def __init__(self, root: Path) -> None:
        self.root = root

    def build(self) -> ExecutiveDashboard:
        artifacts = {name: _read_optional_json(self.root / path) for name, path in EXPECTED_ARTIFACTS.items() if path.suffix == ".json"}
        status = self.status()
        daily_run = _map(artifacts.get("daily_run"))
        morning = _map(artifacts.get("morning_brief"))
        snapshot = _map(artifacts.get("latest_snapshot"))
        delta = _map(artifacts.get("latest_delta"))
        evidence_graph = _map(artifacts.get("evidence_graph"))
        thesis_store = _map(artifacts.get("thesis_records"))
        intake = _map(artifacts.get("intake_manifest"))
        drive = _map(artifacts.get("google_drive_sync"))
        monitor = _map(artifacts.get("source_monitor"))
        workflow = _map(artifacts.get("latest_workflow"))
        evolution = _map(artifacts.get("knowledge_evolution"))
        report = _map(artifacts.get("institutional_report"))
        ai_markets = _map(artifacts.get("ai_markets"))
        performance = _map(artifacts.get("performance"))
        thesis_accuracy = _map(artifacts.get("thesis_accuracy"))
        theses = _map_list(thesis_store.get("theses", []))
        graph_nodes = _map_list(evidence_graph.get("nodes", []))
        graph_edges = _map_list(evidence_graph.get("edges", []))
        created_at = _now_iso()
        daily_status = _daily_status(daily_run)
        intake_drive = _intake_drive_summary(intake, drive)
        evidence_summary = _evidence_summary(morning, evidence_graph)
        graph_summary = _graph_summary(evidence_graph, graph_nodes, graph_edges)
        thesis_summary = _thesis_summary(theses)
        memory_summary = _memory_summary(snapshot, delta)
        morning_summary = _morning_summary(morning)
        monitor_summary = _source_monitor_summary(monitor)
        workflow_summary = _workflow_summary(workflow)
        evolution_summary = _evolution_summary(evolution)
        report_summary = _report_summary(report)
        ai_markets_summary = _ai_markets_summary(ai_markets)
        performance_summary = _performance_summary(performance)
        thesis_accuracy_summary = _thesis_accuracy_summary(thesis_accuracy)
        real_estate_summary = RealEstateAssignmentStore(self.root).summary()
        real_estate_summary.update(_real_estate_intake_summary(_read_optional_json(self.root / "outputs" / "real-estate" / "intake" / "latest-intake.json")))
        real_estate_summary.update(_real_estate_consolidation_summary(_read_optional_json(self.root / "outputs" / "real-estate" / "consolidation" / "assignment-clusters.json")))
        connector_warning_summary = _connector_warning_summary(daily_run, workflow)
        risks_gaps = _risks_gaps(morning, theses)
        actions = _actions(morning, status, risks_gaps)
        key_files = _key_files(self.root, status)
        limitations = _limitations(status)
        provenance = {name: str(path) for name, path in EXPECTED_ARTIFACTS.items()}
        executive_summary = {
            "status": daily_status.get("status", "unavailable"),
            "what_changed_today": _what_changed_today(daily_run, snapshot, delta),
            "active_or_strengthening_theses": thesis_summary["active_count"] + thesis_summary["strengthening_count"],
            "evidence_count": evidence_summary["evidence_count"],
            "current_gaps_or_risks": len(risks_gaps),
            "last_workflow_status": workflow_summary.get("status"),
            "longitudinal_health_score": evolution_summary.get("longitudinal_health_score"),
            "latest_report_id": report_summary.get("latest_report_id"),
            "ai_markets_active_themes": ai_markets_summary.get("active_themes"),
            "performance_pending_outcomes": performance_summary.get("pending_outcome_count"),
            "average_thesis_accuracy_score": thesis_accuracy_summary.get("average_accuracy_score"),
            "theses_needing_review": thesis_accuracy_summary.get("needs_review_count"),
            "active_real_estate_assignments": real_estate_summary.get("active_assignment_count", 0),
            "real_estate_missing_items": real_estate_summary.get("total_missing_item_count", 0),
            "connector_warning_count": connector_warning_summary.get("connector_warning_count"),
            "next_files_to_inspect": [item["path"] for item in key_files[:5]],
        }
        dashboard = ExecutiveDashboard(
            dashboard_id=_dashboard_id(daily_run, morning, snapshot, evidence_graph, thesis_store, intake, drive, monitor, workflow, evolution, report, ai_markets, performance, thesis_accuracy),
            created_at=created_at,
            version=__version__,
            executive_summary=executive_summary,
            daily_pipeline_status=daily_status,
            intake_google_drive_summary=intake_drive,
            evidence_summary=evidence_summary,
            evidence_graph_summary=graph_summary,
            thesis_intelligence_summary=thesis_summary,
            institutional_memory_summary=memory_summary,
            morning_brief_summary=morning_summary,
            source_monitoring_summary=monitor_summary,
            workflow_automation_summary=workflow_summary,
            knowledge_evolution_summary=evolution_summary,
            institutional_research_report_summary=report_summary,
            ai_markets_summary=ai_markets_summary,
            performance_intelligence_summary=performance_summary,
            thesis_accuracy_summary=thesis_accuracy_summary,
            real_estate_assignment_summary=real_estate_summary,
            connector_warning_summary=connector_warning_summary,
            current_risks_gaps=risks_gaps,
            recommended_next_actions=actions,
            key_output_files=key_files,
            limitations=limitations,
            provenance=provenance,
            artifact_status=status,
        )
        return dashboard

    def status(self) -> JsonMap:
        statuses: JsonMap = {}
        for name, relative_path in EXPECTED_ARTIFACTS.items():
            path = self.root / relative_path
            statuses[name] = {
                "path": str(relative_path),
                "exists": path.exists(),
                "kind": "json" if relative_path.suffix == ".json" else "markdown",
            }
        return statuses


class ExecutiveDashboardStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "outputs" / "dashboard"
        self.json_path = self.directory / "dashboard.json"
        self.markdown_path = self.directory / "dashboard.md"

    def generate(self, *, overwrite: bool = False) -> ExecutiveDashboard:
        if (self.json_path.exists() or self.markdown_path.exists()) and not overwrite:
            raise ExecutiveDashboardError("Dashboard already exists. Use --overwrite to replace it.")
        dashboard = ExecutiveDashboardBuilder(self.root).build()
        self.save(dashboard)
        return dashboard

    def save(self, dashboard: ExecutiveDashboard) -> None:
        write_json(self.json_path, dashboard.to_dict())
        self.markdown_path.parent.mkdir(parents=True, exist_ok=True)
        self.markdown_path.write_text(render_dashboard_markdown(dashboard), encoding="utf-8")

    def load(self) -> ExecutiveDashboard:
        if not self.json_path.exists():
            raise ExecutiveDashboardError("No dashboard found. Run dashboard first.")
        return ExecutiveDashboard.from_dict(read_json(self.json_path))

    def export(self) -> Path:
        dashboard = self.load()
        self.markdown_path.parent.mkdir(parents=True, exist_ok=True)
        self.markdown_path.write_text(render_dashboard_markdown(dashboard), encoding="utf-8")
        return self.markdown_path

    def status(self) -> JsonMap:
        return ExecutiveDashboardBuilder(self.root).status()


def render_dashboard_markdown(dashboard: ExecutiveDashboard) -> str:
    lines = [
        "# Executive Dashboard",
        "",
        f"Dashboard ID: `{dashboard.dashboard_id}`",
        f"Created: `{dashboard.created_at}`",
        f"Version: `{dashboard.version}`",
        "",
        "## Executive Summary",
        "",
        *_summary_lines(dashboard.executive_summary),
        "## Daily Pipeline Status",
        "",
        *_summary_lines(dashboard.daily_pipeline_status),
        "## Intake / Google Drive Summary",
        "",
        *_summary_lines(dashboard.intake_google_drive_summary),
        "## Evidence Summary",
        "",
        *_summary_lines(dashboard.evidence_summary),
        "## Evidence Graph Summary",
        "",
        *_summary_lines(dashboard.evidence_graph_summary),
        "## Thesis Intelligence Summary",
        "",
        *_summary_lines(dashboard.thesis_intelligence_summary),
        "## Institutional Memory Summary",
        "",
        *_summary_lines(dashboard.institutional_memory_summary),
        "## Morning Brief Summary",
        "",
        *_summary_lines(dashboard.morning_brief_summary),
        "## Source Monitoring Summary",
        "",
        *_summary_lines(dashboard.source_monitoring_summary),
        "## Workflow Automation Summary",
        "",
        *_summary_lines(dashboard.workflow_automation_summary),
        "## Knowledge Evolution Summary",
        "",
        *_summary_lines(dashboard.knowledge_evolution_summary),
        "## Institutional Research Report Summary",
        "",
        *_summary_lines(dashboard.institutional_research_report_summary),
        "## AI & Markets Summary",
        "",
        *_summary_lines(dashboard.ai_markets_summary),
        "## Performance Intelligence Summary",
        "",
        *_summary_lines(dashboard.performance_intelligence_summary),
        "## Thesis Accuracy Summary",
        "",
        *_summary_lines(dashboard.thesis_accuracy_summary),
        "## Real Estate Assignment Intelligence Summary",
        "",
        *_summary_lines(dashboard.real_estate_assignment_summary),
        "## Connector Warning Summary",
        "",
        *_summary_lines(dashboard.connector_warning_summary),
        "## Current Risks / Gaps",
        "",
        *_string_lines(dashboard.current_risks_gaps),
        "## Recommended Next Actions",
        "",
        *_string_lines(dashboard.recommended_next_actions),
        "## Key Output Files",
        "",
        *_file_lines(dashboard.key_output_files),
        "## Limitations",
        "",
        *_string_lines(dashboard.limitations),
        "## Provenance",
        "",
        *_summary_lines(dashboard.provenance),
    ]
    return "\n".join(lines)


def _daily_status(daily_run: JsonMap) -> JsonMap:
    if not daily_run:
        return {"available": False, "status": "unavailable", "run_id": None, "completed_at": None, "version": None}
    manifest = _map(daily_run.get("manifest"))
    return {
        "available": True,
        "status": daily_run.get("status"),
        "run_id": daily_run.get("run_id"),
        "completed_at": daily_run.get("completed_at"),
        "version": daily_run.get("version"),
        "runtime_seconds": daily_run.get("runtime_seconds"),
        "thesis_count": manifest.get("thesis_count", 0),
        "evidence_graph_id": manifest.get("evidence_graph_id"),
    }


def _intake_drive_summary(intake: JsonMap, drive: JsonMap) -> JsonMap:
    counts = _map(intake.get("counts"))
    return {
        "intake_available": bool(intake),
        "intake_manifest_id": intake.get("manifest_id"),
        "intake_imported": counts.get("imported", 0),
        "intake_duplicates": counts.get("duplicates", 0),
        "intake_errors": counts.get("errors", 0),
        "google_drive_available": bool(drive),
        "google_drive_sync_id": drive.get("sync_id"),
        "google_drive_downloaded": len(_list(drive.get("downloaded_files", []))),
        "google_drive_skipped": len(_list(drive.get("skipped_files", []))),
        "google_drive_errors": len(_list(drive.get("errors", []))),
    }


def _evidence_summary(morning: JsonMap, graph: JsonMap) -> JsonMap:
    evidence_nodes = [node for node in _map_list(graph.get("nodes", [])) if node.get("node_type") == "evidence"]
    return {
        "evidence_count": _int(morning.get("evidence_count")) or len(evidence_nodes),
        "evidence_nodes": len(evidence_nodes),
        "source_nodes": sum(1 for node in _map_list(graph.get("nodes", [])) if node.get("node_type") == "source"),
    }


def _graph_summary(graph: JsonMap, nodes: list[JsonMap], edges: list[JsonMap]) -> JsonMap:
    return {
        "available": bool(graph),
        "graph_id": graph.get("graph_id"),
        "node_count": graph.get("node_count", len(nodes)),
        "edge_count": graph.get("edge_count", len(edges)),
        "orphan_evidence_hint": "See outputs/evidence-graph/evidence-graph.md for orphan evidence records.",
    }


def _thesis_summary(theses: list[JsonMap]) -> JsonMap:
    status_counts = _counts(str(item.get("status", "unknown")) for item in theses)
    confidence_counts = _counts(str(_map(item.get("confidence")).get("label", "unknown")) for item in theses)
    return {
        "available": bool(theses),
        "thesis_count": len(theses),
        "active_count": status_counts.get("active", 0),
        "strengthening_count": status_counts.get("strengthening", 0),
        "weakening_count": status_counts.get("weakening", 0),
        "archived_count": status_counts.get("archived", 0),
        "high_confidence_count": confidence_counts.get("high", 0),
        "medium_confidence_count": confidence_counts.get("medium", 0),
        "low_confidence_count": confidence_counts.get("low", 0),
        "supporting_relationships": sum(len(_string_list(item.get("supporting_evidence_ids", []))) for item in theses),
        "conflicts": sum(len(_string_list(item.get("conflicting_evidence_ids", []))) for item in theses),
    }


def _memory_summary(snapshot: JsonMap, delta: JsonMap) -> JsonMap:
    return {
        "snapshot_available": bool(snapshot),
        "snapshot_id": snapshot.get("snapshot_id"),
        "snapshot_label": snapshot.get("label"),
        "evidence_count": snapshot.get("evidence_count", 0),
        "thesis_count": snapshot.get("thesis_count", 0),
        "delta_available": bool(delta),
        "delta_summary": delta.get("summary"),
    }


def _morning_summary(morning: JsonMap) -> JsonMap:
    return {
        "available": bool(morning),
        "brief_id": morning.get("brief_id"),
        "created_at": morning.get("created_at"),
        "top_findings": len(_list(morning.get("top_findings", []))),
        "top_theses": len(_list(morning.get("top_theses", []))),
        "risk_or_gap_count": len(_list(morning.get("risks_or_gaps", []))),
    }


def _source_monitor_summary(monitor: JsonMap) -> JsonMap:
    summary = _map(monitor.get("summary"))
    return {
        "available": bool(monitor),
        "monitor_id": monitor.get("monitor_id"),
        "sources_checked": summary.get("sources_checked", 0),
        "sources_changed": summary.get("sources_changed", 0),
        "sources_unchanged": summary.get("sources_unchanged", 0),
        "sources_failed": summary.get("sources_failed", 0),
        "new_items": summary.get("new_items", 0),
        "removed_items": summary.get("removed_items", 0),
        "updated_items": summary.get("updated_items", 0),
        "recommended_refreshes": summary.get("recommended_refreshes", []),
    }


def _workflow_summary(workflow: JsonMap) -> JsonMap:
    executed_steps = _map_list(workflow.get("executed_steps", []))
    failed_steps = _map_list(workflow.get("failed_steps", []))
    return {
        "available": bool(workflow),
        "run_id": workflow.get("run_id"),
        "workflow_name": workflow.get("workflow_name"),
        "status": workflow.get("status"),
        "duration": workflow.get("duration", 0),
        "completed_steps": sum(1 for step in executed_steps if step.get("status") in {"completed", "skipped"}),
        "failed_steps": len(failed_steps),
        "completed_at": workflow.get("completed_at"),
    }


def _evolution_summary(evolution: JsonMap) -> JsonMap:
    delta = _map(evolution.get("delta"))
    trends = _map_list(delta.get("trend_records", []))
    source_trends = _map_list(delta.get("source_activity_trends", []))
    research_trends = _map_list(delta.get("research_volume_trends", []))
    thesis_changes = _map_list(delta.get("thesis_confidence_changes", [])) + _map_list(delta.get("thesis_status_changes", []))
    return {
        "available": bool(delta),
        "delta_id": delta.get("delta_id"),
        "evidence_growth": len(_list(delta.get("evidence_gained", []))) - len(_list(delta.get("evidence_removed", []))),
        "graph_growth": _int(delta.get("graph_node_growth")) + _int(delta.get("graph_edge_growth")),
        "thesis_changes": len(thesis_changes),
        "fastest_growing_sources": [item.get("subject") for item in source_trends[:5]],
        "most_active_research_areas": [item.get("subject") for item in research_trends[:5]],
        "recent_trend_changes": len(trends),
        "longitudinal_health_score": delta.get("longitudinal_health_score", 0),
    }


def _report_summary(report: JsonMap) -> JsonMap:
    sections = _map_list(report.get("sections", []))
    return {
        "available": bool(report),
        "latest_report_id": report.get("report_id"),
        "report_created_at": report.get("created_at"),
        "sections_available": sum(1 for section in sections if section.get("available")),
        "risks_gaps_count": len(_list(report.get("risks_gaps", []))),
        "open_questions_count": len(_list(report.get("open_questions", []))),
        "evidence_references_count": len(_list(report.get("evidence_references", []))),
        "report_path": "outputs/reports/latest-report.md" if report else None,
    }


def _ai_markets_summary(report: JsonMap) -> JsonMap:
    themes = _map_list(report.get("themes", []))
    entities = _map_list(report.get("entities", []))
    open_questions = _map_list(report.get("open_questions", []))
    executive_questions = _map_list(report.get("executive_questions", []))
    lifecycle = _map(report.get("theme_lifecycle"))
    lifecycle_themes = _map_list(lifecycle.get("themes", []))
    lifecycle_counts = _map(lifecycle.get("counts"))
    portfolio = _map(report.get("portfolio_intelligence"))
    portfolio_exposures = _map_list(portfolio.get("exposures", []))
    portfolio_items = _map_list(portfolio.get("positions", [])) + _map_list(portfolio.get("watchlist", [])) + _map_list(portfolio.get("detected_entities", []))
    catalyst_monitor = _map(report.get("catalyst_monitor"))
    catalysts = _map_list(catalyst_monitor.get("catalysts", []))
    decisions = _map(report.get("decision_journal"))
    brief = _map(report.get("executive_brief"))
    return {
        "available": bool(report),
        "report_id": report.get("report_id"),
        "active_themes": sum(1 for theme in themes if theme.get("status") == "active"),
        "strengthening_themes": sum(1 for theme in themes if theme.get("status") == "strengthening"),
        "weakening_themes": sum(1 for theme in themes if theme.get("status") == "weakening"),
        "high_confidence_themes": sum(1 for theme in themes if theme.get("confidence") == "high"),
        "entity_count": len(entities),
        "high_confidence_entity_count": sum(1 for entity in entities if _int(entity.get("evidence_count")) >= 4),
        "risk_count": len(_list(report.get("risks", []))),
        "total_open_question_count": sum(_int(_map(question.get("provenance")).get("variant_count")) or 1 for question in open_questions),
        "deduplicated_open_question_count": len(open_questions),
        "executive_question_count": len(executive_questions),
        "top_executive_questions": [str(question.get("question", "")) for question in executive_questions[:5] if question.get("question")],
        "latest_ai_markets_report_path": "outputs/ai-markets/ai-markets-report.md" if report else None,
        "executive_questions_path": "outputs/ai-markets/executive-questions.md" if report else None,
        "lifecycle_available": bool(lifecycle),
        "high_conviction_theme_count": lifecycle_counts.get("high_conviction_theme_count", 0),
        "strengthening_theme_count": lifecycle_counts.get("strengthening_theme_count", 0),
        "active_theme_count": lifecycle_counts.get("active_theme_count", 0),
        "emerging_theme_count": lifecycle_counts.get("emerging_theme_count", 0),
        "weakening_theme_count": lifecycle_counts.get("weakening_theme_count", 0),
        "contradicted_theme_count": lifecycle_counts.get("contradicted_theme_count", 0),
        "archived_theme_count": lifecycle_counts.get("archived_theme_count", 0),
        "recent_theme_transition_count": len(_map_list(lifecycle.get("transitions", []))),
        "top_strengthening_themes": [str(theme.get("theme_name", "")) for theme in lifecycle_themes if theme.get("current_status") == "strengthening"][:5],
        "high_conviction_themes": [str(theme.get("theme_name", "")) for theme in lifecycle_themes if theme.get("current_status") == "high_conviction"][:5],
        "weakening_themes": [str(theme.get("theme_name", "")) for theme in lifecycle_themes if theme.get("current_status") == "weakening"][:5],
        "theme_lifecycle_report_path": "outputs/ai-markets/theme-lifecycle.md" if lifecycle else None,
        "portfolio_intelligence_available": bool(portfolio),
        "portfolio_mode": portfolio.get("mode"),
        "position_count": portfolio.get("position_count", 0),
        "watchlist_count": portfolio.get("watchlist_count", 0),
        "portfolio_theme_exposure_count": portfolio.get("theme_exposure_count", 0),
        "portfolio_risk_count": portfolio.get("risk_count", 0),
        "high_priority_review_count": portfolio.get("high_priority_review_count", 0),
        "top_priority_symbols": [str(item.get("symbol", "")) for item in portfolio_items if item.get("research_priority") == "high"][:5],
        "top_priority_themes": [str(item.get("theme_name", "")) for item in portfolio_exposures if item.get("research_priority") == "high"][:5],
        "portfolio_report_path": "outputs/ai-markets/portfolio/portfolio-intelligence.md" if portfolio else None,
        "portfolio_exposures_path": "outputs/ai-markets/portfolio/portfolio-exposures.md" if portfolio else None,
        "catalyst_monitor_available": bool(catalyst_monitor),
        "total_catalyst_count": catalyst_monitor.get("total_catalyst_count", 0),
        "high_priority_catalyst_count": catalyst_monitor.get("high_priority_catalyst_count", 0),
        "near_term_catalyst_count": catalyst_monitor.get("near_term_catalyst_count", 0),
        "portfolio_linked_catalyst_count": catalyst_monitor.get("portfolio_linked_catalyst_count", 0),
        "risk_linked_catalyst_count": catalyst_monitor.get("risk_linked_catalyst_count", 0),
        "new_catalyst_count": catalyst_monitor.get("new_catalyst_count", 0),
        "stale_catalyst_count": catalyst_monitor.get("stale_catalyst_count", 0),
        "top_catalysts": [str(item.get("title", "")) for item in catalysts[:5]],
        "catalyst_monitor_report_path": "outputs/ai-markets/catalysts/catalyst-monitor.md" if catalyst_monitor else None,
        "catalyst_calendar_path": "outputs/ai-markets/catalysts/catalyst-calendar.md" if catalyst_monitor else None,
        "decision_journal_available": bool(decisions),
        "decision_entry_count": decisions.get("entry_count", 0),
        "open_decision_count": decisions.get("open_decision_count", 0),
        "monitoring_decision_count": decisions.get("monitoring_decision_count", 0),
        "reviewed_decision_count": decisions.get("reviewed_decision_count", 0),
        "due_review_count": decisions.get("due_review_count", 0),
        "overdue_review_count": decisions.get("overdue_review_count", 0),
        "linked_theme_decision_count": decisions.get("linked_theme_decision_count", 0),
        "linked_entity_decision_count": decisions.get("linked_entity_decision_count", 0),
        "linked_catalyst_decision_count": decisions.get("linked_catalyst_decision_count", 0),
        "linked_risk_decision_count": decisions.get("linked_risk_decision_count", 0),
        "outcome_count": decisions.get("outcome_count", 0),
        "decision_journal_report_path": "outputs/ai-markets/decisions/decision-journal.md" if decisions else None,
        "decision_review_queue_path": "outputs/ai-markets/decisions/decision-review-queue.md" if decisions else None,
        "executive_brief_available": bool(brief),
        "executive_brief_id": brief.get("brief_id"),
        "executive_brief_path": "outputs/ai-markets/briefings/morning-brief.md" if brief else None,
        "research_agenda_path": "outputs/ai-markets/briefings/research-agenda.md" if brief else None,
        "research_agenda_count": brief.get("research_agenda_count", 0),
        "high_priority_agenda_count": brief.get("high_priority_agenda_count", 0),
        "top_agenda_items": _string_list(brief.get("top_agenda_items", [])),
        "what_matters_today_count": sum(1 for section in _map_list(brief.get("sections", [])) if section.get("title") == "What Matters Today" for _ in _string_list(section.get("items", []))),
    }


def _performance_summary(report: JsonMap) -> JsonMap:
    loop = _map(report.get("learning_loop"))
    return {
        "performance_intelligence_available": bool(report),
        "performance_snapshot_id": report.get("snapshot_id") or loop.get("snapshot_id"),
        "decision_count": report.get("decision_count", 0) or loop.get("decision_count", 0),
        "outcome_count": report.get("outcome_count", 0) or loop.get("outcome_count", 0),
        "pending_outcome_count": report.get("pending_outcome_count", 0) or loop.get("pending_outcome_count", 0),
        "lesson_count": report.get("lesson_count", 0) or loop.get("lesson_count", 0),
        "performance_signal_count": report.get("performance_signal_count", 0) or loop.get("performance_signal_count", 0),
        "high_severity_signal_count": report.get("high_severity_signal_count", 0) or loop.get("high_severity_signal_count", 0),
        "due_review_count": report.get("due_review_count", 0) or loop.get("due_review_count", 0),
        "overdue_review_count": report.get("overdue_review_count", 0) or loop.get("overdue_review_count", 0),
        "performance_report_path": "outputs/performance/performance-intelligence.md" if report else None,
        "learning_loop_path": "outputs/performance/learning-loop.md" if report else None,
    }


def _thesis_accuracy_summary(report: JsonMap) -> JsonMap:
    summary = _map(report.get("summary"))
    return {
        "thesis_accuracy_available": bool(report),
        "average_accuracy_score": summary.get("average_accuracy_score", 0),
        "average_process_score": summary.get("average_process_score", 0),
        "highest_accuracy_theses": summary.get("highest_accuracy_theses", []),
        "lowest_accuracy_theses": summary.get("lowest_accuracy_theses", []),
        "needs_review_count": summary.get("needs_review_count", 0),
        "thesis_accuracy_report_path": "outputs/performance/thesis-accuracy.md" if report else None,
    }


def _connector_warning_summary(daily_run: JsonMap, workflow: JsonMap) -> JsonMap:
    warnings: list[JsonMap] = []
    warnings.extend(_map_list(daily_run.get("connector_warnings", [])))
    for step in _map_list(workflow.get("executed_steps", [])):
        details = _map(step.get("details"))
        warning = _map(details.get("connector_warning"))
        if warning:
            warnings.append(warning)
        warnings.extend(_map_list(details.get("connector_warnings", [])))
    by_key = {}
    for warning in warnings:
        key = "|".join([str(warning.get("connector_name")), str(warning.get("status")), str(warning.get("step_name")), str(warning.get("error_summary"))])
        by_key[key] = warning
    deduped = [by_key[key] for key in sorted(by_key)]
    return {
        "connector_warnings_available": bool(deduped),
        "connector_warning_count": len(deduped),
        "connectors_needing_reauth": sorted({str(item.get("connector_name")) for item in deduped if item.get("status") == "needs_reauth"}),
        "local_artifacts_used": any(bool(item.get("local_artifacts_used")) for item in deduped),
        "connector_warning_report_path": "outputs/workflows/workflow-report.md" if deduped else None,
    }


def _real_estate_intake_summary(intake: JsonMap) -> JsonMap:
    counts = _map(intake.get("counts"))
    records = _map_list(intake.get("records", []))
    return {
        "real_estate_intake_available": bool(intake),
        "latest_real_estate_intake_run_id": intake.get("intake_run_id"),
        "real_estate_intake_imported_count": counts.get("imported", 0),
        "real_estate_intake_duplicate_count": counts.get("skipped_duplicate", 0),
        "real_estate_intake_error_count": counts.get("errors", 0),
        "latest_real_estate_intake_assignment_ids": [str(record.get("detected_assignment_id")) for record in records[:5]],
    }


def _real_estate_consolidation_summary(consolidation: JsonMap) -> JsonMap:
    counts = _map(consolidation.get("counts"))
    clusters = _map_list(consolidation.get("clusters", []))
    return {
        "real_estate_consolidation_available": bool(consolidation),
        "consolidated_assignment_count": counts.get("assignment_count", len(clusters)),
        "consolidated_artifact_count": counts.get("artifact_count", 0),
        "consolidated_knowledge_pack_count": counts.get("knowledge_pack_count", 0),
        "consolidated_assignments_with_reviewer_notes": counts.get("assignments_with_reviewer_notes", 0),
        "consolidated_assignments_with_conflicts": counts.get("assignments_with_conflicts", 0),
        "top_active_assignments": [
            {
                "assignment_id": cluster.get("canonical_assignment_id"),
                "property": cluster.get("property_address"),
                "artifact_count": cluster.get("artifact_count", 0),
                "status": cluster.get("assignment_status"),
                "last_activity": cluster.get("last_seen"),
            }
            for cluster in clusters[:5]
        ],
    }


def _risks_gaps(morning: JsonMap, theses: list[JsonMap]) -> list[str]:
    items = set(_string_list(morning.get("risks_or_gaps", [])))
    for thesis in theses:
        if thesis.get("status") == "weakening":
            items.add(f"Weakening thesis: {thesis.get('title', thesis.get('thesis_id', 'unknown'))}")
        if _map(thesis.get("confidence")).get("label") == "low":
            items.add(f"Low-confidence thesis: {thesis.get('title', thesis.get('thesis_id', 'unknown'))}")
    return sorted(items)[:12]


def _actions(morning: JsonMap, status: JsonMap, risks: list[str]) -> list[str]:
    actions = set(_string_list(morning.get("recommended_next_actions", [])))
    if risks:
        actions.add("Review current risks and gaps before relying on dashboard conclusions.")
    for name, record in status.items():
        if not record.get("exists"):
            actions.add(f"Generate or inspect missing artifact: {record.get('path')}")
    if not actions:
        actions.add("Review key output files before making decisions.")
    return sorted(actions)[:12]


def _key_files(root: Path, status: JsonMap) -> list[JsonMap]:
    files = []
    for name, record in status.items():
        exists = bool(record.get("exists"))
        if exists:
            files.append({"name": name, "path": str(record.get("path")), "exists": exists})
    for name, record in status.items():
        if not record.get("exists"):
            files.append({"name": name, "path": str(record.get("path")), "exists": False})
    return files


def _limitations(status: JsonMap) -> list[str]:
    limitations = [
        "Dashboard is a deterministic presentation layer over existing local artifacts.",
        "Missing artifacts are reported as unavailable; values are not fabricated.",
        "No providers, LLM inference, embeddings, semantic similarity, web retrieval, Gmail, or autonomous decisions are used.",
    ]
    missing = [name for name, record in status.items() if not record.get("exists")]
    if missing:
        limitations.append("Unavailable artifacts: " + ", ".join(sorted(missing)) + ".")
    return limitations


def _what_changed_today(daily_run: JsonMap, snapshot: JsonMap, delta: JsonMap) -> str:
    if delta.get("summary"):
        return str(delta["summary"])
    if daily_run:
        return f"Daily pipeline status is {daily_run.get('status', 'unknown')}."
    if snapshot:
        return f"Latest memory snapshot is {snapshot.get('snapshot_id', 'unknown')}."
    return "No daily pipeline, memory delta, or snapshot artifact is available."


def _dashboard_id(*items: JsonMap) -> str:
    fingerprint = "|".join(
        [
            str(item.get("run_id") or item.get("brief_id") or item.get("snapshot_id") or item.get("graph_id") or item.get("manifest_id") or item.get("sync_id") or len(_map_list(item.get("theses", []))))
            for item in items
        ]
    )
    return f"dashboard_{sha256(fingerprint.encode('utf-8')).hexdigest()[:16]}"


def _read_optional_json(path: Path) -> JsonMap:
    if not path.exists():
        return {}
    try:
        data = read_json(path)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _counts(values) -> dict[str, int]:
    counts: dict[str, int] = {}
    for value in values:
        counts[value] = counts.get(value, 0) + 1
    return counts


def _summary_lines(summary: JsonMap) -> list[str]:
    if not summary:
        return ["- None", ""]
    return [*[f"- {key}: `{value}`" for key, value in summary.items()], ""]


def _string_lines(items: list[str]) -> list[str]:
    if not items:
        return ["- None", ""]
    return [*[f"- {item}" for item in items], ""]


def _file_lines(items: list[JsonMap]) -> list[str]:
    if not items:
        return ["- None", ""]
    return [*[f"- `{item.get('path')}` ({'available' if item.get('exists') else 'unavailable'})" for item in items], ""]


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


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


def _require_str(data: JsonMap, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise ExecutiveDashboardError(f"Dashboard field {key} must be a string")
    return value
