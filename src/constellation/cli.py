from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from .artifacts import ArtifactError
from .ai_markets import AIMarketsBriefStore, AIMarketsCatalystStore, AIMarketsDecisionJournalStore, AIMarketsError, AIMarketsPortfolioStore, AIMarketsStore, AIMarketsThemeLifecycleStore
from .assignment_consolidation import AssignmentConsolidationEngine, AssignmentConsolidationError, AssignmentConsolidationStore
from .canonical_assignments import MIGRATION_CATEGORIES, CanonicalAssignmentEngine, CanonicalAssignmentError, CanonicalAssignmentResolver, CanonicalAssignmentStore
from .canonical_operations import CanonicalOperationsEngine, CanonicalOperationsError, CanonicalOperationsStore
from .cross_document import CrossDocumentAnalysisStore, CrossDocumentError
from .daily import DailyPipelineError, DailyPipelineStore
from .dashboard import ExecutiveDashboardError, ExecutiveDashboardStore
from .evidence import EvidenceError, EvidenceStore
from .evidence_graph import EvidenceGraphError, EvidenceGraphStore
from .evolution import KnowledgeEvolutionError, KnowledgeEvolutionStore
from .google_drive import GoogleDriveConnector, GoogleDriveDependencyError, GoogleDriveError
from .intake import IntakeEngine, IntakeError
from .intelligence import IntelligenceError, IntelligenceStore
from .io import read_json
from .kernel import ConstellationKernel
from .knowledge_graph import KnowledgeGraphBuilder, KnowledgeGraphError, KnowledgeGraphStore, show_graph_item
from .memory import InstitutionalMemoryError, InstitutionalMemoryStore
from .morning import MorningExecutiveError, MorningExecutiveStore
from .pkos import PKOSError, PKOSKnowledgeOrganization
from .performance import PerformanceIntelligenceError, PerformanceIntelligenceStore
from .thesis_accuracy import ThesisAccuracyError, ThesisAccuracyStore
from .prompts import PromptUnavailable
from .real_estate_intake import RealEstateIntakeEngine, RealEstateIntakeError, RealEstateIntakeStore
from .real_estate import RealEstateAssignmentStore, RealEstateError
from .reports import InstitutionalResearchReportError, InstitutionalResearchReportStore, report_summary
from .research import ResearchError, ResearchOrganization
from .source_monitor import SourceMonitorError, SourceMonitorStore
from .state import WorkflowStateError
from .thesis import ThesisError, ThesisStore
from .thesis_intelligence import ThesisIntelligenceError, ThesisStore as ThesisIntelligenceStore
from .workflow import WorkflowAutomationError, WorkflowStore


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m constellation")
    subparsers = parser.add_subparsers(dest="command", required=True)

    run_parser = subparsers.add_parser("run", help="Run a workflow until completion or approval gate.")
    run_parser.add_argument("workflow", type=Path, help="Path to workflow YAML file.")
    run_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")

    approvals_parser = subparsers.add_parser("approvals", help="Manage approval records.")
    approvals_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    approvals_subparsers = approvals_parser.add_subparsers(dest="approvals_command", required=True)
    approvals_subparsers.add_parser("list", help="List pending approvals.")
    approve_parser = approvals_subparsers.add_parser("approve", help="Explicitly approve a pending approval.")
    approve_parser.add_argument("approval_id", help="Actual approval ID from the pending approval record.")

    resume_parser = subparsers.add_parser("resume", help="Resume a workflow run after approval.")
    resume_parser.add_argument("workflow_run_id", help="Actual workflow run ID.")
    resume_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")

    runs_parser = subparsers.add_parser("runs", help="Inspect workflow runs.")
    runs_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    runs_subparsers = runs_parser.add_subparsers(dest="runs_command", required=True)
    runs_subparsers.add_parser("list", help="List known workflow runs.")
    show_parser = runs_subparsers.add_parser("show", help="Show one workflow run.")
    show_parser.add_argument("workflow_run_id", help="Actual workflow run ID.")
    archive_parser = runs_subparsers.add_parser("archive", help="Archive one workflow run.")
    archive_parser.add_argument("workflow_run_id", help="Actual workflow run ID.")
    delete_parser = runs_subparsers.add_parser("delete", help="Delete one workflow run after confirmation.")
    delete_parser.add_argument("workflow_run_id", help="Actual workflow run ID.")
    delete_parser.add_argument("--yes", action="store_true", help="Confirm deletion without prompting.")
    prune_parser = runs_subparsers.add_parser("prune", help="Archive or delete old workflow runs.")
    prune_parser.add_argument("--older-than", type=int, required=True, help="Age threshold in days.")
    prune_parser.add_argument("--delete", action="store_true", help="Delete instead of archiving old runs.")
    prune_parser.add_argument("--yes", action="store_true", help="Confirm prune deletion without prompting.")

    providers_parser = subparsers.add_parser("providers", help="Inspect configured model providers.")
    providers_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    providers_subparsers = providers_parser.add_subparsers(dest="providers_command", required=True)
    providers_subparsers.add_parser("list", help="List configured providers.")
    provider_show_parser = providers_subparsers.add_parser("show", help="Show one provider.")
    provider_show_parser.add_argument("provider_name", help="Provider name from config/providers.yaml.")
    providers_subparsers.add_parser("health", help="Check provider health.")

    context_parser = subparsers.add_parser("context", help="Inspect assembled execution context.")
    context_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    context_subparsers = context_parser.add_subparsers(dest="context_command", required=True)
    context_show_parser = context_subparsers.add_parser("show", help="Show assembled context for a run.")
    context_show_parser.add_argument("workflow_run_id", help="Actual workflow run ID.")

    prompt_parser = subparsers.add_parser("prompt", help="Assemble provider-ready prompt packages.")
    prompt_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    prompt_subparsers = prompt_parser.add_subparsers(dest="prompt_command", required=True)
    prompt_show_parser = prompt_subparsers.add_parser("show", help="Show prompt package for a run.")
    prompt_show_parser.add_argument("workflow_run_id", help="Actual workflow run ID.")
    prompt_show_parser.add_argument("--step", help="Optional workflow step ID.")

    artifacts_parser = subparsers.add_parser("artifacts", help="Inspect structured agent artifacts.")
    artifacts_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    artifacts_subparsers = artifacts_parser.add_subparsers(dest="artifacts_command", required=True)
    artifacts_list_parser = artifacts_subparsers.add_parser("list", help="List artifacts for a workflow run.")
    artifacts_list_parser.add_argument("workflow_run_id", help="Actual workflow run ID.")
    artifacts_show_parser = artifacts_subparsers.add_parser("show", help="Show one structured artifact.")
    artifacts_show_parser.add_argument("workflow_run_id", help="Actual workflow run ID.")
    artifacts_show_parser.add_argument("artifact_id", help="Actual artifact ID.")

    validate_parser = subparsers.add_parser("validate", help="Validate Constellation configuration and doctrine.")
    validate_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    validate_subparsers = validate_parser.add_subparsers(dest="validate_command", required=True)
    validate_crew_parser = validate_subparsers.add_parser("crew", help="Validate crew doctrine and agent mappings.")
    validate_crew_parser.add_argument("--allow-orphans", action="store_true", help="Allow crew folders without matching agents.")

    health_parser = subparsers.add_parser("health", help="Run deterministic system health checks.")
    health_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")

    research_parser = subparsers.add_parser("research", help="Run and export institutional research workflows.")
    research_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    research_subparsers = research_parser.add_subparsers(dest="research_command", required=True)
    research_run_parser = research_subparsers.add_parser("run", help="Run institutional research on a markdown or text file.")
    research_run_parser.add_argument("input_path", type=Path, help="Path to a .md or .txt research input.")
    research_export_parser = research_subparsers.add_parser("export", help="Export an executive research report for a run.")
    research_export_parser.add_argument("workflow_run_id", help="Actual workflow run ID.")

    pkos_parser = subparsers.add_parser("pkos", help="Run and package PKOS knowledge update proposals.")
    pkos_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    pkos_subparsers = pkos_parser.add_subparsers(dest="pkos_command", required=True)
    pkos_ingest_parser = pkos_subparsers.add_parser("ingest", help="Run PKOS ingestion on a markdown or text file.")
    pkos_ingest_parser.add_argument("input_path", type=Path, help="Path to a .md or .txt PKOS input.")
    pkos_package_parser = pkos_subparsers.add_parser("package", help="Export a PKOS review package for a run.")
    pkos_package_parser.add_argument("workflow_run_id", help="Actual workflow run ID.")
    pkos_package_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing package files.")

    evidence_parser = subparsers.add_parser("evidence", help="Inspect and export evidence records.")
    evidence_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    evidence_subparsers = evidence_parser.add_subparsers(dest="evidence_command", required=True)
    evidence_subparsers.add_parser("list", help="List evidence records.")
    evidence_show_parser = evidence_subparsers.add_parser("show", help="Show one evidence record.")
    evidence_show_parser.add_argument("evidence_id", help="Actual evidence ID.")
    evidence_export_parser = evidence_subparsers.add_parser("export", help="Export evidence report for a workflow run.")
    evidence_export_parser.add_argument("workflow_run_id", help="Actual workflow run ID.")

    evidence_graph_parser = subparsers.add_parser("evidence-graph", help="Build and inspect deterministic evidence relationships.")
    evidence_graph_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    evidence_graph_subparsers = evidence_graph_parser.add_subparsers(dest="evidence_graph_command", required=True)
    evidence_graph_subparsers.add_parser("build", help="Build the evidence graph from local artifacts.")
    evidence_graph_subparsers.add_parser("nodes", help="List evidence graph nodes.")
    evidence_graph_subparsers.add_parser("edges", help="List evidence graph edges.")
    evidence_graph_show_parser = evidence_graph_subparsers.add_parser("show", help="Show one evidence graph node or edge.")
    evidence_graph_show_parser.add_argument("item_id", help="Evidence graph node ID, edge ID, or referenced artifact ID.")
    evidence_graph_subparsers.add_parser("export", help="Export evidence graph markdown.")

    graph_parser = subparsers.add_parser("graph", help="Build and inspect the deterministic knowledge graph.")
    graph_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    graph_subparsers = graph_parser.add_subparsers(dest="graph_command", required=True)
    graph_build_parser = graph_subparsers.add_parser("build", help="Build or update graph from one workflow run.")
    graph_build_parser.add_argument("workflow_run_id", help="Actual workflow run ID.")
    graph_subparsers.add_parser("nodes", help="List graph nodes.")
    graph_subparsers.add_parser("edges", help="List graph edges.")
    graph_show_parser = graph_subparsers.add_parser("show", help="Show one graph node or edge.")
    graph_show_parser.add_argument("item_id", help="Graph node ID or edge ID.")
    graph_subparsers.add_parser("export", help="Export graph markdown.")
    graph_analyze_parser = graph_subparsers.add_parser("analyze", help="Run deterministic cross-document analysis.")
    graph_analyze_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing analysis outputs.")
    graph_findings_parser = graph_subparsers.add_parser("findings", help="List or inspect cross-document findings.")
    graph_findings_subparsers = graph_findings_parser.add_subparsers(dest="graph_findings_command")
    graph_findings_show_parser = graph_findings_subparsers.add_parser("show", help="Show one finding.")
    graph_findings_show_parser.add_argument("finding_id", help="Actual finding ID.")
    graph_findings_subparsers.add_parser("export", help="Export findings markdown.")

    thesis_parser = subparsers.add_parser("thesis", help="Generate and inspect institutional theses.")
    thesis_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    thesis_subparsers = thesis_parser.add_subparsers(dest="thesis_command", required=True)
    thesis_subparsers.add_parser("build", help="Build deterministic thesis intelligence records.")
    thesis_generate_parser = thesis_subparsers.add_parser("generate", help="Generate theses from cross-document analysis.")
    thesis_generate_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing thesis outputs.")
    thesis_subparsers.add_parser("list", help="List generated theses.")
    thesis_show_parser = thesis_subparsers.add_parser("show", help="Show one thesis.")
    thesis_show_parser.add_argument("thesis_id", help="Actual thesis ID.")
    thesis_timeline_parser = thesis_subparsers.add_parser("timeline", help="Show thesis intelligence timeline.")
    thesis_timeline_parser.add_argument("thesis_id", help="Actual thesis ID.")
    thesis_subparsers.add_parser("export", help="Export theses markdown.")

    intelligence_parser = subparsers.add_parser("intelligence", help="Generate and inspect institutional intelligence briefs.")
    intelligence_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    intelligence_subparsers = intelligence_parser.add_subparsers(dest="intelligence_command", required=True)
    intelligence_generate_parser = intelligence_subparsers.add_parser("generate", help="Generate institutional intelligence brief.")
    intelligence_generate_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing intelligence output.")
    intelligence_subparsers.add_parser("show", help="Show current intelligence brief as JSON.")
    intelligence_subparsers.add_parser("export", help="Export current intelligence brief as markdown.")

    intake_parser = subparsers.add_parser("intake", help="Scan and import local operational intake files.")
    intake_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    intake_subparsers = intake_parser.add_subparsers(dest="intake_command", required=True)
    intake_subparsers.add_parser("scan", help="Report available local intake files.")
    intake_subparsers.add_parser("import", help="Import local intake files into dated research inputs.")
    intake_subparsers.add_parser("status", help="Show intake manifest counts.")

    drive_parser = subparsers.add_parser("drive", help="Stage files from configured Google Drive sources.")
    drive_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    drive_subparsers = drive_parser.add_subparsers(dest="drive_command", required=True)
    drive_subparsers.add_parser("status", help="Check Google Drive connector configuration.")
    drive_subparsers.add_parser("list", help="List files from enabled Google Drive sources.")
    drive_sync_parser = drive_subparsers.add_parser("sync", help="Download files into the Google Drive intake inbox.")
    drive_sync_parser.add_argument("--source", help="Optional source ID from config/sources.yaml.")
    drive_sync_parser.add_argument("--dry-run", action="store_true", help="Show what would be downloaded without downloading.")

    morning_parser = subparsers.add_parser("morning", help="Generate a deterministic morning executive intelligence brief.")
    morning_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    morning_parser.add_argument("--export", action="store_true", help="Export the current morning brief markdown.")
    morning_parser.add_argument("--overwrite", action="store_true", help="Overwrite an existing morning brief.")

    memory_parser = subparsers.add_parser("memory", help="Capture and compare institutional memory snapshots.")
    memory_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    memory_subparsers = memory_parser.add_subparsers(dest="memory_command", required=True)
    memory_snapshot_parser = memory_subparsers.add_parser("snapshot", help="Capture current local intelligence state.")
    memory_snapshot_parser.add_argument("--label", help="Optional human-readable snapshot label.")
    memory_subparsers.add_parser("list", help="List institutional memory snapshots.")
    memory_show_parser = memory_subparsers.add_parser("show", help="Show one snapshot as JSON.")
    memory_show_parser.add_argument("snapshot_id", help="Snapshot ID.")
    memory_diff_parser = memory_subparsers.add_parser("diff", help="Diff latest two snapshots or explicit snapshot IDs.")
    memory_diff_parser.add_argument("snapshot_ids", nargs="*", help="Optional pair of snapshot IDs.")
    memory_subparsers.add_parser("export", help="Export institutional memory markdown report.")

    daily_parser = subparsers.add_parser("daily", help="Run or inspect the deterministic daily intelligence pipeline.")
    daily_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    daily_parser.add_argument("--overwrite", action="store_true", help="Overwrite the current daily run output.")
    daily_subparsers = daily_parser.add_subparsers(dest="daily_command")
    daily_subparsers.add_parser("status", help="Show latest daily run status.")
    daily_subparsers.add_parser("history", help="Show daily run history.")
    daily_subparsers.add_parser("export", help="Export latest daily markdown report.")

    dashboard_parser = subparsers.add_parser("dashboard", help="Generate or inspect the deterministic executive dashboard.")
    dashboard_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    dashboard_parser.add_argument("--export", action="store_true", help="Export dashboard markdown.")
    dashboard_parser.add_argument("--overwrite", action="store_true", help="Overwrite existing dashboard outputs.")
    dashboard_subparsers = dashboard_parser.add_subparsers(dest="dashboard_command")
    dashboard_subparsers.add_parser("status", help="Report expected dashboard input artifact availability.")

    monitor_parser = subparsers.add_parser("monitor", help="Run or inspect deterministic source monitoring.")
    monitor_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    monitor_parser.add_argument("--overwrite", action="store_true", help="Overwrite current monitor output.")
    monitor_subparsers = monitor_parser.add_subparsers(dest="monitor_command")
    monitor_subparsers.add_parser("status", help="Show latest source monitor status.")
    monitor_subparsers.add_parser("history", help="Show source monitor history.")
    monitor_subparsers.add_parser("export", help="Export source monitor markdown.")

    workflow_parser = subparsers.add_parser("workflow", help="Run deterministic workflow automations.")
    workflow_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    workflow_subparsers = workflow_parser.add_subparsers(dest="workflow_command", required=True)
    workflow_subparsers.add_parser("list", help="List built-in workflow automations.")
    workflow_run_parser = workflow_subparsers.add_parser("run", help="Run one workflow automation by name.")
    workflow_run_parser.add_argument("workflow_name", help="Workflow name, such as Morning.")
    workflow_subparsers.add_parser("history", help="Show workflow automation run history.")
    workflow_show_parser = workflow_subparsers.add_parser("show", help="Show one workflow automation definition.")
    workflow_show_parser.add_argument("workflow_name", help="Workflow name, such as Morning.")
    workflow_subparsers.add_parser("export", help="Export latest workflow automation report.")

    evolution_parser = subparsers.add_parser("evolution", help="Generate and inspect deterministic knowledge evolution.")
    evolution_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    evolution_subparsers = evolution_parser.add_subparsers(dest="evolution_command")
    evolution_subparsers.add_parser("status", help="Show latest knowledge evolution status.")
    evolution_subparsers.add_parser("history", help="Show knowledge evolution history.")
    evolution_subparsers.add_parser("export", help="Export latest knowledge evolution markdown reports.")
    evolution_compare_parser = evolution_subparsers.add_parser("compare", help="Compare two institutional memory snapshot IDs.")
    evolution_compare_parser.add_argument("snapshot_id_a", help="Prior institutional memory snapshot ID.")
    evolution_compare_parser.add_argument("snapshot_id_b", help="Current institutional memory snapshot ID.")

    report_parser = subparsers.add_parser("report", help="Generate and inspect deterministic institutional research reports.")
    report_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    report_subparsers = report_parser.add_subparsers(dest="report_command", required=True)
    report_latest_parser = report_subparsers.add_parser("latest", help="Generate the latest institutional research report.")
    report_latest_parser.add_argument("--export", action="store_true", help="Write Markdown report after generation.")
    report_subparsers.add_parser("status", help="Show report input artifact availability.")
    report_subparsers.add_parser("history", help="List report history.")
    report_show_parser = report_subparsers.add_parser("show", help="Show one report summary as JSON.")
    report_show_parser.add_argument("report_id", help="Report ID from report history.")

    performance_parser = subparsers.add_parser("performance", help="Build and inspect deterministic Performance Intelligence.")
    performance_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    performance_subparsers = performance_parser.add_subparsers(dest="performance_command")
    performance_subparsers.add_parser("review", help="Show review queue and follow-up needs.")
    performance_subparsers.add_parser("decisions", help="List decision outcomes.")
    performance_subparsers.add_parser("signals", help="List performance signals.")
    performance_subparsers.add_parser("lessons", help="List process lessons.")
    performance_subparsers.add_parser("export", help="Export Performance Intelligence markdown.")
    performance_subparsers.add_parser("history", help="List Performance Intelligence history.")
    performance_subparsers.add_parser("delta", help="Show Performance Intelligence delta JSON.")
    performance_thesis_parser = performance_subparsers.add_parser("thesis", help="Build and inspect deterministic thesis accuracy.")
    performance_thesis_parser.add_argument("--history", action="store_true", help="List Thesis Accuracy history.")
    performance_thesis_parser.add_argument("--delta", action="store_true", help="Show Thesis Accuracy delta JSON.")
    performance_thesis_parser.add_argument("--scoreboard", action="store_true", help="Show Thesis Accuracy scoreboard.")
    performance_thesis_parser.add_argument("--export", action="store_true", help="Export Thesis Accuracy markdown.")

    ai_markets_parser = subparsers.add_parser("ai-markets", help="Build and inspect deterministic AI & Markets intelligence.")
    ai_markets_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    ai_markets_subparsers = ai_markets_parser.add_subparsers(dest="ai_markets_command", required=True)
    ai_markets_subparsers.add_parser("build", help="Build deterministic AI & Markets intelligence.")
    ai_markets_subparsers.add_parser("status", help="Show AI & Markets status.")
    ai_markets_subparsers.add_parser("themes", help="List AI & Markets themes.")
    ai_markets_theme_parser = ai_markets_subparsers.add_parser("theme", help="Show one AI & Markets theme.")
    ai_markets_theme_parser.add_argument("theme_id", help="AI & Markets theme ID.")
    ai_markets_subparsers.add_parser("entities", help="List AI & Markets entities.")
    ai_markets_catalysts_parser = ai_markets_subparsers.add_parser("catalysts", help="Show AI & Markets catalyst monitoring.")
    ai_markets_catalysts_parser.add_argument("--monitor", action="store_true", help="Show catalyst monitor status.")
    ai_markets_catalysts_parser.add_argument("--priorities", action="store_true", help="List high and medium priority catalysts.")
    ai_markets_catalysts_parser.add_argument("--calendar", action="store_true", help="Show catalyst calendar groups.")
    ai_markets_catalysts_parser.add_argument("--history", action="store_true", help="List catalyst monitor history.")
    ai_markets_catalysts_parser.add_argument("--delta", action="store_true", help="Show catalyst delta JSON.")
    ai_markets_catalysts_parser.add_argument("--transitions", action="store_true", help="List catalyst transitions.")
    ai_markets_catalysts_parser.add_argument("--export", action="store_true", help="Export catalyst monitor Markdown.")
    ai_markets_decisions_parser = ai_markets_subparsers.add_parser("decisions", help="Show AI & Markets decision journal.")
    ai_markets_decisions_parser.add_argument("--entries", action="store_true", help="List decision entries.")
    ai_markets_decisions_parser.add_argument("--queue", action="store_true", help="Show decision review queue.")
    ai_markets_decisions_parser.add_argument("--timeline", action="store_true", help="Show decision timeline.")
    ai_markets_decisions_parser.add_argument("--outcomes", action="store_true", help="List decision outcomes.")
    ai_markets_decisions_parser.add_argument("--history", action="store_true", help="List decision journal history.")
    ai_markets_decisions_parser.add_argument("--delta", action="store_true", help="Show decision delta JSON.")
    ai_markets_decisions_parser.add_argument("--export", action="store_true", help="Export decision journal Markdown.")
    ai_markets_decisions_parser.add_argument("--create-template", action="store_true", help="Create a private local decision entry template.")
    ai_markets_brief_parser = ai_markets_subparsers.add_parser("brief", help="Show AI & Markets executive morning brief.")
    ai_markets_brief_parser.add_argument("--export", action="store_true", help="Export executive brief Markdown.")
    ai_markets_brief_parser.add_argument("--agenda", action="store_true", help="Show research agenda.")
    ai_markets_brief_parser.add_argument("--history", action="store_true", help="List brief history.")
    ai_markets_brief_parser.add_argument("--delta", action="store_true", help="Show brief delta JSON.")
    ai_markets_subparsers.add_parser("risks", help="List AI & Markets risks.")
    ai_markets_questions_parser = ai_markets_subparsers.add_parser("questions", help="List AI & Markets open questions.")
    ai_markets_questions_parser.add_argument("--executive", action="store_true", help="Show only prioritized executive questions.")
    ai_markets_lifecycle_parser = ai_markets_subparsers.add_parser("lifecycle", help="Show AI & Markets theme lifecycle.")
    ai_markets_lifecycle_parser.add_argument("--export", action="store_true", help="Export lifecycle Markdown.")
    ai_markets_lifecycle_parser.add_argument("--history", action="store_true", help="Show lifecycle history.")
    ai_markets_lifecycle_parser.add_argument("--transitions", action="store_true", help="Show lifecycle transitions.")
    ai_markets_portfolio_parser = ai_markets_subparsers.add_parser("portfolio", help="Show AI & Markets portfolio intelligence.")
    ai_markets_portfolio_parser.add_argument("--export", action="store_true", help="Export portfolio Markdown.")
    ai_markets_portfolio_parser.add_argument("--exposures", action="store_true", help="List portfolio theme exposures.")
    ai_markets_portfolio_parser.add_argument("--risks", action="store_true", help="List portfolio-linked risks.")
    ai_markets_portfolio_parser.add_argument("--watchlist", action="store_true", help="List portfolio/watchlist items.")
    ai_markets_portfolio_parser.add_argument("--questions", action="store_true", help="List portfolio-linked questions.")
    ai_markets_portfolio_parser.add_argument("--history", action="store_true", help="List portfolio history.")
    ai_markets_portfolio_parser.add_argument("--delta", action="store_true", help="Show latest portfolio delta.")
    ai_markets_subparsers.add_parser("report", help="Print AI & Markets report path.")
    ai_markets_subparsers.add_parser("export", help="Export AI & Markets Markdown outputs.")

    real_estate_parser = subparsers.add_parser("real-estate", help="Build and inspect deterministic Real Estate Intelligence.")
    real_estate_parser.add_argument("--root", type=Path, default=Path.cwd(), help="Constellation repository root.")
    real_estate_subparsers = real_estate_parser.add_subparsers(dest="real_estate_command", required=True)
    real_estate_assignments_parser = real_estate_subparsers.add_parser("assignments", help="List canonical Real Estate assignments.")
    real_estate_assignments_parser.add_argument("--include-aliases", action="store_true", help="Show aliases grouped under each canonical assignment.")
    real_estate_assignment_parser = real_estate_subparsers.add_parser("assignment", help="Build and inspect one Real Estate assignment.")
    real_estate_assignment_subparsers = real_estate_assignment_parser.add_subparsers(dest="real_estate_assignment_command", required=True)
    for command_name, help_text in [
        ("build", "Build Assignment Intelligence for an assignment."),
        ("status", "Show assignment status."),
        ("show", "Show assignment snapshot JSON."),
        ("sources", "List assignment sources."),
        ("missing", "List missing assignment information."),
        ("risks", "List assignment risks."),
        ("timeline", "List assignment timeline events."),
        ("export", "Export assignment brief markdown."),
        ("create-template", "Create a private local assignment template."),
    ]:
        command_parser = real_estate_assignment_subparsers.add_parser(command_name, help=help_text)
        command_parser.add_argument("assignment_id", help="Assignment ID.")
        if command_name == "show":
            command_parser.add_argument("--open", action="store_true", help="Open the canonical assignment brief in VS Code if available.")
    real_estate_intake_parser = real_estate_subparsers.add_parser("intake", help="Auto-ingest Real Estate assignments from structured local intake.")
    real_estate_intake_subparsers = real_estate_intake_parser.add_subparsers(dest="real_estate_intake_command", required=True)
    real_estate_intake_subparsers.add_parser("status", help="Show Real Estate intake status.")
    real_estate_intake_scan_parser = real_estate_intake_subparsers.add_parser("scan", help="Scan configured Real Estate intake sources.")
    real_estate_intake_scan_parser.add_argument("--source", help="Optional source ID.")
    real_estate_intake_import_parser = real_estate_intake_subparsers.add_parser("import", help="Import structured Real Estate intake files.")
    real_estate_intake_import_parser.add_argument("--source", help="Optional source ID.")
    real_estate_intake_import_parser.add_argument("--file", type=Path, help="Explicit structured intake file.")
    real_estate_intake_import_parser.add_argument("--open", action="store_true", help="Open generated assignment brief in VS Code if available.")
    real_estate_intake_subparsers.add_parser("history", help="List Real Estate intake history.")
    real_estate_intake_show_parser = real_estate_intake_subparsers.add_parser("show", help="Show one intake record.")
    real_estate_intake_show_parser.add_argument("intake_id", help="Intake ID.")
    real_estate_consolidation_parser = real_estate_subparsers.add_parser("consolidation", help="Consolidate Real Estate assignment artifacts.")
    real_estate_consolidation_subparsers = real_estate_consolidation_parser.add_subparsers(dest="real_estate_consolidation_command")
    real_estate_consolidation_subparsers.add_parser("status", help="Show Assignment Consolidation status.")
    real_estate_consolidation_subparsers.add_parser("clusters", help="List consolidated assignment clusters.")
    real_estate_consolidation_subparsers.add_parser("conflicts", help="List assignment consolidation conflicts.")
    real_estate_consolidation_subparsers.add_parser("relationships", help="List assignment relationships.")
    real_estate_consolidation_subparsers.add_parser("aliases", help="List assignment aliases.")
    real_estate_consolidation_subparsers.add_parser("unassigned", help="List unassigned assignment artifacts.")
    real_estate_consolidation_subparsers.add_parser("identity-report", help="Print identity resolution report path.")
    real_estate_consolidation_subparsers.add_parser("export", help="Export assignment consolidation Markdown.")
    real_estate_canonical_parser = real_estate_subparsers.add_parser("canonical", help="Inspect and migrate canonical Real Estate assignments.")
    real_estate_canonical_subparsers = real_estate_canonical_parser.add_subparsers(dest="real_estate_canonical_command", required=True)
    real_estate_canonical_subparsers.add_parser("status", help="Show canonical assignment status.")
    real_estate_canonical_subparsers.add_parser("assignments", help="List canonical assignments.")
    real_estate_canonical_subparsers.add_parser("aliases", help="List canonical aliases.")
    real_estate_canonical_resolve = real_estate_canonical_subparsers.add_parser("resolve", help="Resolve an assignment alias.")
    real_estate_canonical_resolve.add_argument("alias", help="Alias, address, source-generated ID, order ID, or canonical assignment ID.")
    real_estate_canonical_subparsers.add_parser("migration-plan", help="Generate non-destructive canonical migration plan.")
    real_estate_canonical_migrate = real_estate_canonical_subparsers.add_parser("migrate", help="Run canonical migration dry-run or apply.")
    real_estate_canonical_migrate.add_argument("--dry-run", action="store_true", help="Inspect migration without modifying files.")
    real_estate_canonical_migrate.add_argument("--apply", action="store_true", help="Apply non-destructive alias migration markers.")
    real_estate_canonical_migrate.add_argument("--ready-only", action="store_true", help="Select only safe_merge and preserve_alias entries.")
    real_estate_canonical_migrate.add_argument("--category", choices=sorted(MIGRATION_CATEGORIES), help="Select one migration category.")
    real_estate_canonical_migrate.add_argument("--assignment", help="Select entries targeting one canonical assignment or resolvable alias.")
    real_estate_canonical_migrate.add_argument("--source-assignment", help="Select one source alias assignment directory.")
    real_estate_canonical_migrate.add_argument("--list-selected", action="store_true", help="Print selected entries without applying.")
    real_estate_canonical_subparsers.add_parser("export", help="Print canonical assignment output paths.")
    real_estate_canonical_review = real_estate_canonical_subparsers.add_parser("review", help="Show canonical operations review queue.")
    real_estate_canonical_review.add_argument("--blocked", action="store_true", help="Show blocked assignments only.")
    real_estate_canonical_review.add_argument("--safe", action="store_true", help="Show safe migration items only.")
    real_estate_canonical_review.add_argument("--ambiguous", action="store_true", help="Show ambiguous assignments only.")
    real_estate_canonical_subparsers.add_parser("report", help="Print canonical operations report paths.")
    real_estate_canonical_subparsers.add_parser("operations", help="Show canonical operations summary.")
    real_estate_canonical_subparsers.add_parser("conflicts", help="List normalized canonical identity conflicts.")

    args = parser.parse_args(argv)
    if args.command == "run":
        kernel = ConstellationKernel(args.root.resolve())
        result = kernel.run_workflow(args.workflow)
        _print_result(result)
        return 0
    if args.command == "approvals":
        kernel = ConstellationKernel(args.root.resolve())
        if args.approvals_command == "list":
            approvals = kernel.list_pending_approvals()
            if not approvals:
                print("No pending approvals.")
                return 0
            for approval in approvals:
                print(
                    f"{approval['id']} workflow_run_id={approval['workflow_run_id']} "
                    f"workflow_id={approval['workflow_id']} gate={approval['gate_id']} "
                    f"status={approval['status']}"
                )
            return 0
        if args.approvals_command == "approve":
            approval = kernel.approve(args.approval_id)
            print(f"approval_id: {approval['id']}")
            print(f"workflow_run_id: {approval['workflow_run_id']}")
            print(f"status: {approval['status']}")
            return 0
    if args.command == "resume":
        kernel = ConstellationKernel(args.root.resolve())
        try:
            result = kernel.resume_workflow(args.workflow_run_id)
        except WorkflowStateError as exc:
            print(f"error: {exc}")
            return 1
        _print_result(result)
        return 0
    if args.command == "runs":
        kernel = ConstellationKernel(args.root.resolve())
        if args.runs_command == "list":
            runs = kernel.list_runs()
            if not runs:
                print("No workflow runs found.")
                return 0
            for run in runs:
                print(
                    f"{run.workflow_run_id} workflow_id={run.workflow_id} status={run.status} "
                    f"current_step={run.current_step} created_at={run.created_at} updated_at={run.updated_at}"
                )
            return 0
        if args.runs_command == "show":
            try:
                details = kernel.show_run(args.workflow_run_id)
            except WorkflowStateError as exc:
                print(f"error: {exc}")
                return 1
            _print_run_details(details)
            return 0
        if args.runs_command == "archive":
            try:
                result = kernel.archive_run(args.workflow_run_id)
            except WorkflowStateError as exc:
                print(f"error: {exc}")
                return 1
            _print_lifecycle_result(result)
            return 0
        if args.runs_command == "delete":
            if not args.yes and not _confirm_delete(args.workflow_run_id):
                print("delete_aborted")
                return 1
            try:
                result = kernel.delete_run(args.workflow_run_id)
            except WorkflowStateError as exc:
                print(f"error: {exc}")
                return 1
            _print_lifecycle_result(result)
            return 0
        if args.runs_command == "prune":
            action = "delete" if args.delete else "archive"
            if action == "delete" and not args.yes and not _confirm_delete(f"runs older than {args.older_than} days"):
                print("prune_aborted")
                return 1
            try:
                results = kernel.prune_runs(args.older_than, action)
            except ValueError as exc:
                print(f"error: {exc}")
                return 1
            print(f"pruned_count: {len(results)}")
            for result in results:
                _print_lifecycle_result(result)
            return 0
    if args.command == "providers":
        kernel = ConstellationKernel(args.root.resolve())
        if args.providers_command == "list":
            for provider in kernel.list_providers():
                print(
                    f"{provider.id} enabled={provider.enabled} type={provider.provider_type} "
                    f"model={provider.model} capabilities={','.join(provider.capabilities)}"
                )
            return 0
        if args.providers_command == "show":
            try:
                provider = kernel.show_provider(args.provider_name)
            except Exception as exc:
                print(f"error: {exc}")
                return 1
            print(f"name: {provider.id}")
            print(f"enabled: {provider.enabled}")
            print(f"type: {provider.provider_type}")
            print(f"model: {provider.model}")
            print(f"role: {provider.role}")
            print(f"capabilities: {','.join(provider.capabilities)}")
            return 0
        if args.providers_command == "health":
            for result in kernel.provider_health():
                print(
                    f"{result.get('provider_name')} status={result.get('status')} "
                    f"enabled={result.get('enabled')}"
                )
            return 0
    if args.command == "context":
        kernel = ConstellationKernel(args.root.resolve())
        if args.context_command == "show":
            try:
                context = kernel.show_context(args.workflow_run_id)
            except Exception as exc:
                print(f"error: {exc}")
                return 1
            print(json.dumps(context.to_dict(), indent=2, sort_keys=True))
            return 0
    if args.command == "prompt":
        kernel = ConstellationKernel(args.root.resolve())
        if args.prompt_command == "show":
            try:
                prompt = kernel.show_prompt(args.workflow_run_id, args.step)
            except PromptUnavailable as exc:
                print(str(exc))
                return 0
            except Exception as exc:
                print(f"error: {exc}")
                return 1
            print(json.dumps(prompt.to_dict(), indent=2, sort_keys=True))
            return 0
    if args.command == "artifacts":
        kernel = ConstellationKernel(args.root.resolve())
        if args.artifacts_command == "list":
            artifacts = kernel.list_artifacts(args.workflow_run_id)
            if not artifacts:
                print("No artifacts found.")
                return 0
            for artifact in artifacts:
                print(
                    f"{artifact.get('artifact_id')} step_id={artifact.get('step_id')} "
                    f"agent_id={artifact.get('agent_id')} status={artifact.get('status')} "
                    f"title={artifact.get('title')}"
                )
            return 0
        if args.artifacts_command == "show":
            try:
                artifact = kernel.show_artifact(args.workflow_run_id, args.artifact_id)
            except ArtifactError as exc:
                print(f"error: {exc}")
                return 1
            print(json.dumps(artifact, indent=2, sort_keys=True))
            return 0
    if args.command == "validate":
        kernel = ConstellationKernel(args.root.resolve())
        if args.validate_command == "crew":
            report = kernel.validate_crew(allow_orphans=args.allow_orphans)
            _print_validation_report(report)
            return 0 if report.ok else 1
    if args.command == "health":
        kernel = ConstellationKernel(args.root.resolve())
        report = kernel.health()
        _print_health_report(report)
        return 0 if report.ok else 1
    if args.command == "research":
        organization = ResearchOrganization(args.root.resolve())
        if args.research_command == "run":
            try:
                result = organization.run(args.input_path)
            except ResearchError as exc:
                print(f"error: {exc}")
                return 1
            _print_result(result)
            return 0
        if args.research_command == "export":
            try:
                output_path = organization.export(args.workflow_run_id)
            except (ResearchError, WorkflowStateError) as exc:
                print(f"error: {exc}")
                return 1
            print(f"report: {output_path}")
            return 0
    if args.command == "pkos":
        organization = PKOSKnowledgeOrganization(args.root.resolve())
        if args.pkos_command == "ingest":
            try:
                result = organization.ingest(args.input_path)
            except PKOSError as exc:
                print(f"error: {exc}")
                return 1
            _print_result(result)
            return 0
        if args.pkos_command == "package":
            try:
                output_dir = organization.package(args.workflow_run_id, overwrite=args.overwrite)
            except (PKOSError, WorkflowStateError) as exc:
                print(f"error: {exc}")
                return 1
            print(f"package: {output_dir}")
            return 0
    if args.command == "evidence":
        store = EvidenceStore(args.root.resolve())
        if args.evidence_command == "list":
            records = store.list()
            if not records:
                print("No evidence records found.")
                return 0
            for record in records:
                print(
                    f"{record.get('evidence_id')} workflow_run_id={record.get('workflow_run_id')} "
                    f"source={record.get('source_identifier')} location={record.get('source_location')} "
                    f"confidence={record.get('confidence')}"
                )
            return 0
        if args.evidence_command == "show":
            try:
                record = store.show(args.evidence_id)
            except EvidenceError as exc:
                print(f"error: {exc}")
                return 1
            print(json.dumps(record, indent=2, sort_keys=True))
            return 0
        if args.evidence_command == "export":
            output_path = store.export_report(args.workflow_run_id)
            print(f"evidence_report: {output_path}")
            return 0
    if args.command == "evidence-graph":
        store = EvidenceGraphStore(args.root.resolve())
        try:
            if args.evidence_graph_command == "build":
                graph = store.build()
                print(f"evidence_graph: {store.graph_path}")
                print(f"nodes: {len(graph.nodes)}")
                print(f"edges: {len(graph.edges)}")
                return 0
            if args.evidence_graph_command == "nodes":
                graph = store.load()
                if not graph.nodes:
                    print("No evidence graph nodes found.")
                    return 0
                for node in graph.list_nodes():
                    print(f"{node.node_id} type={node.node_type} label={node.label}")
                return 0
            if args.evidence_graph_command == "edges":
                graph = store.load()
                if not graph.edges:
                    print("No evidence graph edges found.")
                    return 0
                for edge in graph.list_edges():
                    print(f"{edge.edge_id} {edge.source_node_id} --{edge.edge_type}--> {edge.target_node_id}")
                return 0
            if args.evidence_graph_command == "show":
                print(json.dumps(store.show(args.item_id), indent=2, sort_keys=True))
                return 0
            if args.evidence_graph_command == "export":
                output_path = store.export()
                print(f"evidence_graph_export: {output_path}")
                return 0
        except EvidenceGraphError as exc:
            print(f"error: {exc}")
            return 1
    if args.command == "graph":
        root = args.root.resolve()
        store = KnowledgeGraphStore(root)
        if args.graph_command == "build":
            try:
                graph = KnowledgeGraphBuilder(root).build_run(args.workflow_run_id)
            except (KnowledgeGraphError, WorkflowStateError) as exc:
                print(f"error: {exc}")
                return 1
            print(f"graph: {store.graph_path}")
            print(f"nodes: {len(graph.nodes)}")
            print(f"edges: {len(graph.edges)}")
            return 0
        if args.graph_command == "nodes":
            graph = store.load()
            if not graph.nodes:
                print("No graph nodes found.")
                return 0
            for node in graph.list_nodes():
                print(f"{node.node_id} type={node.node_type} label={node.label} confidence={node.confidence}")
            return 0
        if args.graph_command == "edges":
            graph = store.load()
            if not graph.edges:
                print("No graph edges found.")
                return 0
            for edge in graph.list_edges():
                print(f"{edge.edge_id} {edge.source_node_id} --{edge.relationship_type}--> {edge.target_node_id}")
            return 0
        if args.graph_command == "show":
            try:
                item = show_graph_item(root, args.item_id)
            except KnowledgeGraphError as exc:
                print(f"error: {exc}")
                return 1
            print(json.dumps(item, indent=2, sort_keys=True))
            return 0
        if args.graph_command == "export":
            output_path = store.export()
            print(f"graph_export: {output_path}")
            return 0
        if args.graph_command == "analyze":
            try:
                analysis = CrossDocumentAnalysisStore(root).analyze_graph(overwrite=args.overwrite)
            except CrossDocumentError as exc:
                print(f"error: {exc}")
                return 1
            print(f"analysis: {CrossDocumentAnalysisStore(root).json_path}")
            print(f"findings: {len(analysis.findings)}")
            return 0
        if args.graph_command == "findings":
            analysis_store = CrossDocumentAnalysisStore(root)
            if args.graph_findings_command == "show":
                try:
                    finding = analysis_store.show_finding(args.finding_id)
                except CrossDocumentError as exc:
                    print(f"error: {exc}")
                    return 1
                print(json.dumps(finding.to_dict(), indent=2, sort_keys=True))
                return 0
            if args.graph_findings_command == "export":
                try:
                    output_path = analysis_store.export()
                except CrossDocumentError as exc:
                    print(f"error: {exc}")
                    return 1
                print(f"findings_export: {output_path}")
                return 0
            try:
                findings = analysis_store.list_findings()
            except CrossDocumentError as exc:
                print(f"error: {exc}")
                return 1
            if not findings:
                print("No cross-document findings found.")
                return 0
            for finding in findings:
                print(f"{finding.finding_id} type={finding.finding_type} confidence={finding.confidence} title={finding.title}")
            return 0
    if args.command == "thesis":
        store = ThesisStore(args.root.resolve())
        intelligence_store = ThesisIntelligenceStore(args.root.resolve())
        if args.thesis_command == "build":
            try:
                records = intelligence_store.build()
            except ThesisIntelligenceError as exc:
                print(f"error: {exc}")
                return 1
            print(f"thesis_intelligence: {intelligence_store.theses_path}")
            print(f"count: {len(records)}")
            print(f"supporting_relationships: {sum(len(record.supporting_evidence_ids) for record in records)}")
            print(f"conflicts: {sum(len(record.conflicting_evidence_ids) for record in records)}")
            return 0
        if args.thesis_command == "generate":
            try:
                theses = store.generate(overwrite=args.overwrite)
            except ThesisError as exc:
                print(f"error: {exc}")
                return 1
            print(f"theses: {store.json_path}")
            print(f"count: {len(theses)}")
            return 0
        if args.thesis_command == "list":
            if intelligence_store.theses_path.exists():
                try:
                    records = intelligence_store.list()
                except ThesisIntelligenceError as exc:
                    print(f"error: {exc}")
                    return 1
                if not records:
                    print("No thesis intelligence records found.")
                    return 0
                for record in records:
                    print(
                        f"{record.thesis_id} category={record.category} status={record.status} "
                        f"confidence={record.confidence.label} support={len(record.supporting_evidence_ids)} "
                        f"conflicts={len(record.conflicting_evidence_ids)} title={record.title}"
                    )
                return 0
            try:
                theses = store.list_theses()
            except ThesisError as exc:
                print(f"error: {exc}")
                return 1
            if not theses:
                print("No theses found.")
                return 0
            for thesis in theses:
                print(f"{thesis.thesis_id} type={thesis.thesis_type} status={thesis.status} confidence={thesis.confidence} title={thesis.title}")
            return 0
        if args.thesis_command == "show":
            if intelligence_store.theses_path.exists():
                try:
                    record = intelligence_store.show(args.thesis_id)
                except ThesisIntelligenceError as exc:
                    print(f"error: {exc}")
                    return 1
                print(json.dumps(record.to_dict(), indent=2, sort_keys=True))
                return 0
            try:
                thesis = store.show(args.thesis_id)
            except ThesisError as exc:
                print(f"error: {exc}")
                return 1
            print(json.dumps(thesis.to_dict(), indent=2, sort_keys=True))
            return 0
        if args.thesis_command == "timeline":
            try:
                events = intelligence_store.timeline(args.thesis_id)
            except ThesisIntelligenceError as exc:
                print(f"error: {exc}")
                return 1
            if not events:
                print("No thesis timeline events found.")
                return 0
            for event in events:
                print(f"{event.timestamp} {event.thesis_id} {event.event_type} reason={event.reason}")
            return 0
        if args.thesis_command == "export":
            if intelligence_store.theses_path.exists():
                try:
                    output_path = intelligence_store.export()
                except ThesisIntelligenceError as exc:
                    print(f"error: {exc}")
                    return 1
                print(f"thesis_export: {output_path}")
                return 0
            try:
                output_path = store.export()
            except ThesisError as exc:
                print(f"error: {exc}")
                return 1
            print(f"thesis_export: {output_path}")
            return 0
    if args.command == "intelligence":
        store = IntelligenceStore(args.root.resolve())
        if args.intelligence_command == "generate":
            try:
                brief = store.generate(overwrite=args.overwrite)
            except IntelligenceError as exc:
                print(f"error: {exc}")
                return 1
            print(f"intelligence: {store.json_path}")
            print(f"brief_id: {brief.brief_id}")
            print(f"status: {brief.status}")
            return 0
        if args.intelligence_command == "show":
            try:
                brief = store.load()
            except IntelligenceError as exc:
                print(f"error: {exc}")
                return 1
            print(json.dumps(brief.to_dict(), indent=2, sort_keys=True))
            return 0
        if args.intelligence_command == "export":
            try:
                output_path = store.export()
            except IntelligenceError as exc:
                print(f"error: {exc}")
                return 1
            print(f"intelligence_report: {output_path}")
            return 0
    if args.command == "intake":
        engine = IntakeEngine(args.root.resolve())
        if args.intake_command == "scan":
            try:
                items = engine.scan()
            except IntakeError as exc:
                print(f"error: {exc}")
                return 1
            if not items:
                print("No intake files found.")
                return 0
            for item in items:
                print(f"{item.item_id} channel={item.source_channel} path={item.original_path} sha256={item.file_hash}")
            return 0
        if args.intake_command == "import":
            try:
                manifest = engine.import_items()
            except IntakeError as exc:
                print(f"error: {exc}")
                return 1
            print(f"manifest: {engine.json_path}")
            _print_intake_counts(manifest.counts)
            return 0
        if args.intake_command == "status":
            try:
                counts = engine.status()
            except IntakeError as exc:
                print(f"error: {exc}")
                return 1
            _print_intake_counts(counts)
            return 0
    if args.command == "drive":
        connector = GoogleDriveConnector(args.root.resolve())
        if args.drive_command == "status":
            status = connector.status()
            print(f"config_present: {status.get('config_present')}")
            print(f"config_path: {status.get('config_path')}")
            print(f"dependencies_installed: {status.get('dependencies_installed')}")
            print(f"credentials_path_configured: {status.get('credentials_path_configured')}")
            print(f"token_path_configured: {status.get('token_path_configured')}")
            print(f"enabled_sources: {','.join(status.get('enabled_sources', []))}")
            if status.get("config_error"):
                print(f"config_error: {status.get('config_error')}")
            return 0
        if args.drive_command == "list":
            try:
                files = connector.list_files()
            except (GoogleDriveDependencyError, GoogleDriveError) as exc:
                print(f"error: {exc}")
                return 1
            if not files:
                print("No Google Drive files found.")
                return 0
            for file in files:
                print(f"{file.file_id} name={file.name} mime_type={file.mime_type} folder={file.source_folder_id}")
            return 0
        if args.drive_command == "sync":
            try:
                manifest = connector.sync(source_id=args.source, dry_run=args.dry_run)
            except (GoogleDriveDependencyError, GoogleDriveError) as exc:
                print(f"error: {exc}")
                return 1
            print(f"manifest: {connector.json_path}")
            print(f"downloaded: {len(manifest.downloaded_files)}")
            print(f"skipped: {len(manifest.skipped_files)}")
            print(f"duplicates: {len(manifest.duplicate_files)}")
            print(f"errors: {len(manifest.errors)}")
            return 0
    if args.command == "morning":
        store = MorningExecutiveStore(args.root.resolve())
        try:
            if args.export and store.json_path.exists() and not args.overwrite:
                output_path = store.export()
                print(f"morning_brief: {output_path}")
                return 0
            brief = store.generate(overwrite=args.overwrite)
            print(f"morning_brief: {store.json_path}")
            print(f"brief_id: {brief.brief_id}")
            print(f"created_at: {brief.created_at}")
            print(f"evidence_count: {brief.evidence_count}")
            print(f"graph_nodes: {brief.graph_node_count}")
            print(f"graph_edges: {brief.graph_edge_count}")
            if args.export:
                print(f"morning_markdown: {store.markdown_path}")
            return 0
        except MorningExecutiveError as exc:
            print(f"error: {exc}")
            return 1
    if args.command == "memory":
        store = InstitutionalMemoryStore(args.root.resolve())
        try:
            if args.memory_command == "snapshot":
                snapshot = store.create_snapshot(args.label)
                print(f"snapshot_id: {snapshot.snapshot_id}")
                print(f"label: {snapshot.label or ''}")
                print(f"created_at: {snapshot.created_at}")
                print(f"evidence_count: {snapshot.evidence_count}")
                print(f"thesis_count: {snapshot.thesis_count}")
                return 0
            if args.memory_command == "list":
                snapshots = store.list_snapshots()
                if not snapshots:
                    print("No institutional memory snapshots found.")
                    return 0
                for snapshot in snapshots:
                    print(f"{snapshot.snapshot_id} label={snapshot.label or ''} created_at={snapshot.created_at} evidence={snapshot.evidence_count} theses={snapshot.thesis_count}")
                return 0
            if args.memory_command == "show":
                snapshot = store.show_snapshot(args.snapshot_id)
                print(json.dumps(snapshot.to_dict(), indent=2, sort_keys=True))
                return 0
            if args.memory_command == "diff":
                if len(args.snapshot_ids) not in {0, 2}:
                    print("error: provide either zero snapshot IDs or exactly two snapshot IDs")
                    return 1
                delta = store.diff(*args.snapshot_ids) if args.snapshot_ids else store.diff()
                print(json.dumps(delta.to_dict(), indent=2, sort_keys=True))
                return 0
            if args.memory_command == "export":
                output_path = store.export()
                print(f"institutional_memory: {output_path}")
                return 0
        except InstitutionalMemoryError as exc:
            print(f"error: {exc}")
            return 1
    if args.command == "daily":
        store = DailyPipelineStore(args.root.resolve())
        try:
            if args.daily_command is None:
                run = store.run(overwrite=args.overwrite)
                _print_daily_run(run)
                return 0
            if args.daily_command == "status":
                run = store.load()
                _print_daily_run(run)
                return 0
            if args.daily_command == "history":
                runs = store.history()
                if not runs:
                    print("No daily pipeline runs found.")
                    return 0
                for run in runs:
                    print(f"{run.run_id} status={run.status} completed_at={run.completed_at} version={run.version}")
                return 0
            if args.daily_command == "export":
                output_path = store.export()
                print(f"daily_report: {output_path}")
                return 0
        except DailyPipelineError as exc:
            print(f"error: {exc}")
            return 1
    if args.command == "dashboard":
        store = ExecutiveDashboardStore(args.root.resolve())
        try:
            if args.dashboard_command == "status":
                _print_dashboard_status(store.status())
                return 0
            if args.export and store.json_path.exists() and not args.overwrite:
                output_path = store.export()
                print(f"dashboard: {output_path}")
                return 0
            dashboard = store.generate(overwrite=args.overwrite or store.json_path.exists() or store.markdown_path.exists())
            _print_dashboard_summary(dashboard)
            if args.export:
                print(f"dashboard_markdown: {store.markdown_path}")
            return 0
        except ExecutiveDashboardError as exc:
            print(f"error: {exc}")
            return 1
    if args.command == "monitor":
        store = SourceMonitorStore(args.root.resolve())
        try:
            if args.monitor_command is None:
                run = store.run(overwrite=args.overwrite)
                _print_monitor_run(run)
                return 0
            if args.monitor_command == "status":
                _print_monitor_status(store.status())
                return 0
            if args.monitor_command == "history":
                runs = store.history()
                if not runs:
                    print("No source monitor runs found.")
                    return 0
                for run in runs:
                    print(f"{run.monitor_id} created_at={run.created_at} sources={run.summary.get('sources_checked', 0)} changed={run.summary.get('sources_changed', 0)} failed={run.summary.get('sources_failed', 0)}")
                return 0
            if args.monitor_command == "export":
                output_path = store.export()
                print(f"source_monitor: {output_path}")
                return 0
        except SourceMonitorError as exc:
            print(f"error: {exc}")
            return 1
    if args.command == "workflow":
        store = WorkflowStore(args.root.resolve())
        try:
            if args.workflow_command == "list":
                for definition in store.definitions():
                    print(f"{definition.name} id={definition.id} enabled={definition.enabled} steps={len(definition.steps)}")
                return 0
            if args.workflow_command == "run":
                run = store.run(args.workflow_name)
                _print_workflow_run(run)
                return 0
            if args.workflow_command == "history":
                runs = store.history()
                if not runs:
                    print("No workflow automation runs found.")
                    return 0
                for run in runs:
                    print(f"{run.run_id} workflow={run.workflow_name} status={run.status} completed_at={run.completed_at} duration={run.duration}")
                return 0
            if args.workflow_command == "show":
                definition = store.get(args.workflow_name)
                print(json.dumps(definition.to_dict(), indent=2, sort_keys=True))
                return 0
            if args.workflow_command == "export":
                output_path = store.export()
                print(f"workflow_report: {output_path}")
                return 0
        except WorkflowAutomationError as exc:
            print(f"error: {exc}")
            return 1
    if args.command == "evolution":
        store = KnowledgeEvolutionStore(args.root.resolve())
        try:
            if args.evolution_command is None:
                delta = store.generate()
                _print_evolution_delta(delta)
                return 0
            if args.evolution_command == "status":
                _print_evolution_status(store.status())
                return 0
            if args.evolution_command == "history":
                history = store.history()
                if not history:
                    print("No knowledge evolution history found.")
                    return 0
                for item in history:
                    delta = item["delta"]
                    print(f"{delta.delta_id} current={delta.current_snapshot_id} evidence_gained={len(delta.evidence_gained)} graph_nodes={delta.graph_node_growth:+} health={delta.longitudinal_health_score}")
                return 0
            if args.evolution_command == "export":
                output_path = store.export()
                print(f"evolution_report: {output_path}")
                print(f"trend_report: {store.trend_report_path}")
                return 0
            if args.evolution_command == "compare":
                delta = store.compare(args.snapshot_id_a, args.snapshot_id_b)
                print(json.dumps(delta.to_dict(), indent=2, sort_keys=True))
                return 0
        except KnowledgeEvolutionError as exc:
            print(f"error: {exc}")
            return 1
    if args.command == "report":
        store = InstitutionalResearchReportStore(args.root.resolve())
        try:
            if args.report_command == "latest":
                report = store.generate()
                _print_report_summary(report, store)
                if args.export:
                    print(f"report_markdown: {store.export(report)}")
                return 0
            if args.report_command == "status":
                _print_report_status(store.status())
                return 0
            if args.report_command == "history":
                history = store.history()
                if not history:
                    print("No institutional research reports found.")
                    return 0
                for report in history:
                    print(f"{report.report_id} created_at={report.created_at} sections={len(report.sections)} evidence={len(report.evidence_references)}")
                return 0
            if args.report_command == "show":
                report = store.show(args.report_id)
                print(json.dumps(report_summary(report), indent=2, sort_keys=True))
                return 0
        except InstitutionalResearchReportError as exc:
            print(f"error: {exc}")
            return 1
    if args.command == "performance":
        store = PerformanceIntelligenceStore(args.root.resolve())
        try:
            if args.performance_command is None:
                report = store.build()
                _print_performance_status(store.status())
                return 0
            if args.performance_command == "review":
                report = store.build()
                for item in report.decision_outcomes:
                    if item.follow_up_needed or item.review_status in {"due", "overdue"}:
                        print(f"{item.outcome_status}: {item.entry_id} title={item.title} follow_up={item.follow_up_reason}")
                return 0
            if args.performance_command == "decisions":
                report = store.build()
                for item in report.decision_outcomes:
                    print(f"{item.outcome_id} entry={item.entry_id} outcome={item.outcome_status} review={item.review_status} title={item.title}")
                return 0
            if args.performance_command == "signals":
                report = store.build()
                for item in report.performance_signals:
                    print(f"{item.signal_id} severity={item.severity} type={item.signal_type} decisions={len(item.related_decision_ids)} title={item.title}")
                return 0
            if args.performance_command == "lessons":
                report = store.build()
                for item in report.process_lessons:
                    print(f"{item.lesson_id} type={item.lesson_type} decisions={len(item.related_decision_ids)} title={item.title}")
                return 0
            if args.performance_command == "export":
                if not store.report_json_path.exists():
                    store.build()
                print(f"performance_report: {store.export()}")
                return 0
            if args.performance_command == "history":
                history = store.history()
                if not history:
                    print("No Performance Intelligence history found.")
                    return 0
                for item in history:
                    print(f"{item.get('report_id')} snapshot={item.get('snapshot_id')} decisions={item.get('decision_count', 0)} signals={item.get('performance_signal_count', 0)}")
                return 0
            if args.performance_command == "delta":
                if not store.delta_path.exists():
                    store.build()
                print(json.dumps(_map(read_json(store.delta_path)), indent=2, sort_keys=True))
                return 0
            if args.performance_command == "thesis":
                thesis_store = ThesisAccuracyStore(args.root.resolve())
                try:
                    if args.history:
                        history = thesis_store.history()
                        if not history:
                            print("No Thesis Accuracy history found.")
                            return 0
                        for item in history:
                            summary = _map(item.get("summary"))
                            print(f"{item.get('snapshot_id')} theses={summary.get('thesis_count', 0)} average_accuracy={summary.get('average_accuracy_score', 0)} created_at={item.get('created_at', '')}")
                        return 0
                    if args.delta:
                        if not thesis_store.delta_path.exists():
                            thesis_store.build()
                        print(json.dumps(_map(read_json(thesis_store.delta_path)), indent=2, sort_keys=True))
                        return 0
                    if args.scoreboard:
                        if not thesis_store.json_path.exists():
                            thesis_store.build()
                        data = thesis_store.load()
                        for item in _map_list(data.get("scores", [])):
                            print(f"{item.get('thesis_id')} accuracy={item.get('accuracy_score')} process={item.get('process_score')} quality={item.get('quality_score')} priority={item.get('review_priority')} title={item.get('title')}")
                        return 0
                    report = thesis_store.build()
                    if args.export:
                        print(f"thesis_accuracy_report: {thesis_store.export()}")
                        print(f"thesis_scoreboard: {thesis_store.scoreboard_path}")
                        return 0
                    _print_thesis_accuracy_status(thesis_store.status())
                    print(f"report_id: {report.report_id}")
                    return 0
                except ThesisAccuracyError as exc:
                    print(f"error: {exc}")
                    return 1
        except PerformanceIntelligenceError as exc:
            print(f"error: {exc}")
            return 1
    if args.command == "ai-markets":
        store = AIMarketsStore(args.root.resolve())
        try:
            if args.ai_markets_command == "build":
                report = store.build()
                _print_ai_markets_summary(report, store)
                return 0
            if args.ai_markets_command == "status":
                _print_ai_markets_status(store.status())
                return 0
            if args.ai_markets_command == "themes":
                lifecycle = AIMarketsThemeLifecycleStore(args.root.resolve()).load() if (args.root.resolve() / "outputs" / "ai-markets" / "theme-lifecycle.json").exists() else {}
                lifecycle_by_id = {str(item.get("theme_id")): item for item in _map_list(_map(lifecycle).get("themes", []))}
                for theme in store.load().themes:
                    lifecycle_status = _map(lifecycle_by_id.get(theme.theme_id)).get("current_status") or ""
                    print(f"{theme.theme_id} name={theme.name} lifecycle={lifecycle_status} status={theme.status} confidence={theme.confidence} evidence={theme.evidence_count}")
                return 0
            if args.ai_markets_command == "theme":
                lifecycle_store = AIMarketsThemeLifecycleStore(args.root.resolve())
                if not lifecycle_store.lifecycle_path.exists():
                    lifecycle_store.build(store.load())
                theme = lifecycle_store.theme(args.theme_id)
                print(f"theme_id: {theme.get('theme_id')}")
                print(f"theme_name: {theme.get('theme_name')}")
                print(f"current_lifecycle_status: {theme.get('current_status')}")
                print(f"confidence: {theme.get('confidence')}")
                print(f"evidence_count: {theme.get('evidence_count')}")
                print(f"source_count: {theme.get('source_count')}")
                print(f"entity_count: {theme.get('entity_count')}")
                print(f"risk_count: {theme.get('risk_count')}")
                print(f"status_reason: {theme.get('lifecycle_reason')}")
                print(f"related_entities: {', '.join(_string_list(theme.get('related_entities', [])))}")
                print(f"related_risks: {', '.join(_string_list(theme.get('related_risks', [])))}")
                return 0
            if args.ai_markets_command == "entities":
                for entity in store.load().entities:
                    print(f"{entity.entity_id} symbol={entity.symbol} name={entity.name} evidence={entity.evidence_count}")
                return 0
            if args.ai_markets_command == "catalysts":
                catalyst_store = AIMarketsCatalystStore(args.root.resolve())
                if args.history:
                    for snapshot in catalyst_store.history():
                        print(f"{snapshot.get('snapshot_id')} catalysts={snapshot.get('total_catalyst_count', 0)} created_at={snapshot.get('created_at', '')}")
                    return 0
                if args.delta:
                    print(json.dumps(_map(catalyst_store.load().get("delta")), indent=2, sort_keys=True))
                    return 0
                if args.transitions:
                    for item in _map_list(catalyst_store.load().get("transitions", [])):
                        print(f"{item.get('transition_id')} catalyst={item.get('catalyst_id')} type={item.get('transition_type')} previous={item.get('previous_value')} current={item.get('current_value')}")
                    return 0
                if args.priorities:
                    for item in _map_list(catalyst_store.load().get("catalysts", [])):
                        if item.get("priority") in {"high", "medium"}:
                            print(f"{item.get('catalyst_id')} priority={item.get('priority')} horizon={item.get('time_horizon')} category={item.get('category')} title={item.get('title')}")
                    return 0
                if args.calendar:
                    data = catalyst_store.load()
                    for horizon in ["immediate", "near_term", "medium_term", "long_term", "unknown"]:
                        print(f"{horizon}:")
                        for item in _map_list(data.get("catalysts", [])):
                            if item.get("time_horizon") == horizon:
                                print(f"  {item.get('catalyst_id')} priority={item.get('priority')} title={item.get('title')}")
                    return 0
                if args.export or args.monitor or not catalyst_store.json_path.exists():
                    catalyst_store.build(store.load())
                _print_ai_markets_catalyst_status(catalyst_store.status())
                return 0
            if args.ai_markets_command == "decisions":
                decision_store = AIMarketsDecisionJournalStore(args.root.resolve())
                if args.create_template:
                    print(f"decision_template: {decision_store.create_template()}")
                    return 0
                if args.history:
                    for snapshot in decision_store.history():
                        print(f"{snapshot.get('snapshot_id')} entries={snapshot.get('entry_count', 0)} created_at={snapshot.get('created_at', '')}")
                    return 0
                if args.delta:
                    print(json.dumps(_map(decision_store.load().get("delta")), indent=2, sort_keys=True))
                    return 0
                if args.entries:
                    for item in _map_list(decision_store.load().get("entries", [])):
                        print(f"{item.get('entry_id')} status={item.get('status')} review={_map(item.get('review')).get('review_status')} title={item.get('title')}")
                    return 0
                if args.queue:
                    for item in _map_list(decision_store.load().get("entries", [])):
                        print(f"{_map(item.get('review')).get('review_status')}: {item.get('entry_id')} title={item.get('title')} review_at={item.get('review_at')}")
                    return 0
                if args.timeline:
                    for item in _map_list(decision_store.load().get("entries", [])):
                        print(f"{item.get('created_at')} {item.get('entry_id')} status={item.get('status')} title={item.get('title')}")
                    return 0
                if args.outcomes:
                    for item in _map_list(decision_store.load().get("entries", [])):
                        print(f"{item.get('entry_id')} outcome={_map(item.get('outcome')).get('status')} title={item.get('title')}")
                    return 0
                if args.export or not decision_store.json_path.exists():
                    decision_store.build()
                _print_ai_markets_decision_status(decision_store.status())
                return 0
            if args.ai_markets_command == "brief":
                brief_store = AIMarketsBriefStore(args.root.resolve())
                if args.history:
                    for snapshot in brief_store.history():
                        print(f"{snapshot.get('brief_id')} agenda={snapshot.get('research_agenda_count', 0)} created_at={snapshot.get('created_at', '')}")
                    return 0
                if args.delta:
                    print(json.dumps(_map(brief_store.load().get("delta")), indent=2, sort_keys=True))
                    return 0
                if args.agenda:
                    for item in _map_list(brief_store.load().get("research_agenda", [])):
                        print(f"{item.get('priority')}: {item.get('agenda_id')} source={item.get('source_type')} title={item.get('title')}")
                    return 0
                brief_store.build()
                _print_ai_markets_brief_status(brief_store.status())
                return 0
            if args.ai_markets_command == "risks":
                for risk in store.load().risks:
                    print(f"{risk.risk_id} severity={risk.severity} description={risk.description}")
                return 0
            if args.ai_markets_command == "questions":
                report = store.load()
                questions = report.executive_questions if args.executive else report.open_questions
                print(f"total_open_questions: {sum(int(question.provenance.get('variant_count', 1)) for question in report.open_questions)}")
                print(f"deduplicated_open_questions: {len(report.open_questions)}")
                print(f"executive_questions: {len(report.executive_questions)}")
                print("top_executive_questions:")
                for question in report.executive_questions[:10]:
                    print(f"{question.question_id} priority={question.priority} evidence={len(question.evidence_ids)} themes={len(question.related_themes)} question={question.question}")
                if not args.executive:
                    print("all_deduplicated_questions:")
                for question in questions:
                    print(f"{question.question_id} priority={question.priority} question={question.question}")
                return 0
            if args.ai_markets_command == "lifecycle":
                lifecycle_store = AIMarketsThemeLifecycleStore(args.root.resolve())
                if args.history:
                    for snapshot in lifecycle_store.history():
                        print(f"{snapshot.get('snapshot_id')} themes={snapshot.get('theme_count', 0)} created_at={snapshot.get('created_at', '')}")
                    return 0
                if args.transitions:
                    data = lifecycle_store.load()
                    for transition in _map_list(data.get("transitions", [])):
                        print(f"{transition.get('transition_id')} theme={transition.get('theme_name')} type={transition.get('transition_type')} previous={transition.get('previous_value')} current={transition.get('current_value')}")
                    return 0
                snapshot = lifecycle_store.build(store.load()) if args.export or not lifecycle_store.lifecycle_path.exists() else lifecycle_store.load()
                _print_ai_markets_lifecycle_status(lifecycle_store.status())
                return 0
            if args.ai_markets_command == "portfolio":
                portfolio_store = AIMarketsPortfolioStore(args.root.resolve())
                if args.history:
                    for snapshot in portfolio_store.history():
                        print(f"{snapshot.get('snapshot_id')} mode={snapshot.get('mode')} exposures={snapshot.get('theme_exposure_count', 0)} created_at={snapshot.get('created_at', '')}")
                    return 0
                if args.delta:
                    data = portfolio_store.load()
                    print(json.dumps(_map(data.get("delta")), indent=2, sort_keys=True))
                    return 0
                if args.exposures:
                    for item in _map_list(portfolio_store.load().get("exposures", [])):
                        print(f"{item.get('theme_id')} theme={item.get('theme_name')} lifecycle={item.get('lifecycle_status')} priority={item.get('research_priority')} symbols={','.join(_string_list(item.get('related_symbols', [])))}")
                    return 0
                if args.risks:
                    for item in _map_list(portfolio_store.load().get("risks", [])):
                        print(f"{item.get('risk_id')} priority={item.get('priority')} severity={item.get('severity')} symbols={','.join(_string_list(item.get('related_symbols', [])))} description={item.get('description')}")
                    return 0
                if args.watchlist:
                    data = portfolio_store.load()
                    for item in _map_list(data.get("positions", [])) + _map_list(data.get("watchlist", [])) + _map_list(data.get("detected_entities", [])):
                        print(f"{item.get('symbol')} name={item.get('name')} source={item.get('source')} priority={item.get('research_priority')}")
                    return 0
                if args.questions:
                    for item in _map_list(portfolio_store.load().get("questions", [])):
                        print(f"{item.get('question_id')} priority={item.get('priority')} symbols={','.join(_string_list(item.get('related_symbols', [])))} question={item.get('question')}")
                    return 0
                if args.export or not portfolio_store.json_path.exists():
                    portfolio_store.build(store.load())
                _print_ai_markets_portfolio_status(portfolio_store.status())
                return 0
            if args.ai_markets_command == "report":
                report = store.load()
                print(f"ai_markets_report_id: {report.report_id}")
                print(f"ai_markets_report: {store.report_path}")
                return 0
            if args.ai_markets_command == "export":
                output_path = store.export()
                print(f"ai_markets_report: {output_path}")
                print(f"watchlist: {store.watchlist_path}")
                print(f"content_ideas: {store.content_ideas_path}")
                print(f"executive_questions: {store.executive_questions_path}")
                return 0
        except AIMarketsError as exc:
            print(f"error: {exc}")
            return 1
    if args.command == "real-estate":
        store = RealEstateAssignmentStore(args.root.resolve())
        try:
            if args.real_estate_command == "intake":
                engine = RealEstateIntakeEngine(args.root.resolve())
                intake_store = RealEstateIntakeStore(args.root.resolve())
                if args.real_estate_intake_command == "status":
                    _print_real_estate_intake_status(engine.status())
                    return 0
                if args.real_estate_intake_command == "scan":
                    candidates = engine.scan(source_id=args.source)
                    if not candidates:
                        print("No Real Estate intake candidates found.")
                        return 0
                    for candidate in candidates:
                        print(
                            f"{candidate.intake_id} assignment_id={candidate.detected_assignment_id} "
                            f"source={candidate.source_id} already_imported={candidate.already_imported} "
                            f"mapped={len(candidate.field_mappings)} warnings={len(candidate.warnings)} path={candidate.source_path}"
                        )
                    return 0
                if args.real_estate_intake_command == "import":
                    result = engine.import_candidates(source_id=args.source, file_path=args.file, open_brief=args.open)
                    _print_real_estate_intake_manifest(result.manifest.to_dict(), result.dashboard_refreshed)
                    return 0
                if args.real_estate_intake_command == "history":
                    for manifest in intake_store.history():
                        counts = _map(manifest.get("counts"))
                        print(f"{manifest.get('intake_run_id')} imported={counts.get('imported', 0)} duplicates={counts.get('skipped_duplicate', 0)} errors={counts.get('errors', 0)} created_at={manifest.get('created_at')}")
                    return 0
                if args.real_estate_intake_command == "show":
                    for manifest in intake_store.history():
                        for record in _map_list(manifest.get("records", [])):
                            if record.get("intake_id") == args.intake_id:
                                print(json.dumps(record, indent=2, sort_keys=True))
                                return 0
                    print(f"error: intake record not found: {args.intake_id}")
                    return 1
            if args.real_estate_command == "consolidation":
                consolidation_store = AssignmentConsolidationStore(args.root.resolve())
                if args.real_estate_consolidation_command is None:
                    snapshot = AssignmentConsolidationEngine(args.root.resolve()).build()
                    _print_assignment_consolidation_summary(snapshot.to_dict())
                    return 0
                if args.real_estate_consolidation_command == "status":
                    _print_assignment_consolidation_status(AssignmentConsolidationEngine(args.root.resolve()).status())
                    return 0
                if args.real_estate_consolidation_command == "clusters":
                    data = consolidation_store.load()
                    for cluster in _map_list(data.get("clusters", [])):
                        print(f"{cluster.get('canonical_assignment_id')} artifacts={cluster.get('artifact_count', 0)} property={cluster.get('property_address', '')} conflicts={len(_map_list(cluster.get('conflicts', [])))}")
                    return 0
                if args.real_estate_consolidation_command == "conflicts":
                    path = consolidation_store.conflicts_json
                    data = read_json(path) if path.exists() else {"conflicts": []}
                    for conflict in _map_list(data.get("conflicts", [])):
                        print(f"{conflict.get('conflict_id')} assignment={conflict.get('canonical_assignment_id')} field={conflict.get('field')} values={conflict.get('values')}")
                    return 0
                if args.real_estate_consolidation_command == "relationships":
                    path = consolidation_store.relationships_json
                    data = read_json(path) if path.exists() else {"relationships": []}
                    for relationship in _map_list(data.get("relationships", [])):
                        print(f"{relationship.get('relationship_id')} type={relationship.get('relationship_type')} confidence={relationship.get('confidence')} reason={relationship.get('reason')}")
                    return 0
                if args.real_estate_consolidation_command == "aliases":
                    path = consolidation_store.aliases_json
                    data = read_json(path) if path.exists() else {"aliases": []}
                    for alias in _map_list(data.get("aliases", [])):
                        print(f"{alias.get('canonical_assignment_id')} alias={alias.get('alias')} type={alias.get('alias_type')}")
                    return 0
                if args.real_estate_consolidation_command == "unassigned":
                    path = consolidation_store.unassigned_json
                    data = read_json(path) if path.exists() else {"unassigned_artifacts": []}
                    for artifact in _map_list(data.get("unassigned_artifacts", [])):
                        print(f"{artifact.get('artifact_id')} type={artifact.get('artifact_type')} source={artifact.get('source_path')}")
                    return 0
                if args.real_estate_consolidation_command == "identity-report":
                    print(f"identity_resolution_report: {consolidation_store.identity_report_md}")
                    return 0
                if args.real_estate_consolidation_command == "export":
                    print(f"assignment_clusters: {consolidation_store.clusters_md}")
                    print(f"identity_resolution_report: {consolidation_store.identity_report_md}")
                    return 0
            if args.real_estate_command == "canonical":
                canonical_engine = CanonicalAssignmentEngine(args.root.resolve())
                canonical_store = CanonicalAssignmentStore(args.root.resolve())
                operations_engine = CanonicalOperationsEngine(args.root.resolve())
                operations_store = CanonicalOperationsStore(args.root.resolve())
                if args.real_estate_canonical_command == "status":
                    _print_canonical_assignment_status(operations_engine.status())
                    return 0
                if args.real_estate_canonical_command == "assignments":
                    if not canonical_store.assignments_json.exists():
                        canonical_engine.build()
                    for assignment in _map_list(canonical_store.load().get("assignments", [])):
                        subject = _map(assignment.get("subject"))
                        print(
                            f"{assignment.get('canonical_assignment_id')} status={assignment.get('status')} "
                            f"subject={subject.get('address', '')} artifacts={len(_map_list(assignment.get('source_artifacts', [])))} "
                            f"aliases={len(_map_list(assignment.get('aliases', [])))} risks={len(_map_list(assignment.get('risks', [])))} "
                            f"conflicts={len(_map_list(assignment.get('conflicts', [])))}"
                        )
                    return 0
                if args.real_estate_canonical_command == "aliases":
                    if not canonical_store.alias_index_json.exists():
                        canonical_engine.build()
                    for alias in canonical_store.load_aliases():
                        print(f"{alias.get('alias')} -> {alias.get('canonical_assignment_id')} type={alias.get('alias_type')} status={alias.get('status')}")
                    return 0
                if args.real_estate_canonical_command == "resolve":
                    resolution = CanonicalAssignmentResolver(args.root.resolve()).resolve(args.alias)
                    print(f"requested_alias: {resolution.requested_alias}")
                    print(f"resolved: {resolution.resolved}")
                    print(f"canonical_assignment_id: {resolution.canonical_assignment_id}")
                    print(f"alias_type: {resolution.alias_type}")
                    print(f"ambiguous: {resolution.ambiguous}")
                    if resolution.matches:
                        print("matches:")
                        for match in resolution.matches:
                            print(f"- {match.get('alias')} -> {match.get('canonical_assignment_id')} type={match.get('alias_type')}")
                    return 0 if resolution.resolved and not resolution.ambiguous else 1
                if args.real_estate_canonical_command == "migration-plan":
                    state = operations_engine.build(save=True)
                    plan = canonical_engine.migration_plan()
                    print(f"migration_id: {plan.migration_id}")
                    for key in [
                        "pending_migration_count",
                        "migration_ready_count",
                        "safe_merge_count",
                        "preserve_alias_count",
                        "blocked_by_conflict_count",
                        "ambiguous_count",
                        "orphan_count",
                        "already_migrated_count",
                    ]:
                        print(f"{key}: {state.migration_summary.get(key, plan.counts.get(key, 0))}")
                    print(f"migration_plan: {canonical_store.migration_plan_json}")
                    print(f"migration_summary: {operations_store.migration_summary_json}")
                    return 0
                if args.real_estate_canonical_command == "migrate":
                    apply = bool(args.apply)
                    result = canonical_engine.migrate(
                        apply=apply,
                        ready_only=bool(args.ready_only),
                        category=args.category or "",
                        canonical_assignment_id=args.assignment or "",
                        source_assignment_id=args.source_assignment or "",
                        list_selected=bool(args.list_selected),
                    )
                    print(f"migration_id: {result.migration_id}")
                    print(f"scope: {_scope_text(result.scope)}")
                    print(f"selected_count: {result.selected_count}")
                    selected_report = read_json(canonical_store.scoped_selection_json) if canonical_store.scoped_selection_json.exists() else {}
                    selected_entries = _map_list(selected_report.get("selected_entries", []))
                    print(f"eligible_count: {sum(1 for item in selected_entries if item.get('apply_eligible'))}")
                    print(f"refused_count: {result.refused_count}")
                    print(f"blocked_count: {result.blocked_count}")
                    print(f"orphan_count: {result.orphan_count}")
                    print(f"ambiguous_count: {result.ambiguous_count}")
                    print(f"already_migrated_count: {result.already_migrated_count}")
                    print(f"applied: {result.applied}")
                    print(f"applied_count: {result.applied_count}")
                    print(f"skipped_count: {result.skipped_count}")
                    print(f"remaining_pending_count: {result.remaining_pending_count}")
                    print(f"remaining_ready_count: {result.remaining_ready_count}")
                    print(f"remaining_blocked_count: {result.remaining_blocked_count}")
                    print(f"remaining_orphan_count: {result.remaining_orphan_count}")
                    if result.error:
                        print(f"error: {result.error}")
                        print("guidance: use --ready-only, --category preserve_alias, --assignment, or --source-assignment to scope migration safely.")
                    if args.list_selected:
                        for entry in selected_entries:
                            print(
                                f"{entry.get('source_assignment_id')} -> {entry.get('target_canonical_assignment_id')} "
                                f"category={entry.get('migration_category')} action={entry.get('action')} status={entry.get('status')} risk={entry.get('risk_level')}"
                            )
                    if result.backup_manifest_path:
                        print(f"backup_manifest: {result.backup_manifest_path}")
                    print(f"selection_report: {canonical_store.scoped_selection_md}")
                    print(f"result_report: {canonical_store.scoped_result_md}")
                    return 0
                if args.real_estate_canonical_command == "export":
                    operations_engine.build(save=True)
                    print(f"canonical_assignments: {canonical_store.assignments_md}")
                    print(f"alias_index: {canonical_store.alias_index_md}")
                    print(f"canonical_report: {canonical_store.report_md}")
                    print(f"operations_report: {operations_store.operations_report_md}")
                    print(f"review_queue: {operations_store.review_queue_md}")
                    print(f"migration_summary: {operations_store.migration_summary_md}")
                    return 0
                if args.real_estate_canonical_command == "review":
                    state = operations_engine.build(save=True)
                    if args.blocked:
                        items = state.blocked_assignments
                        for item in items:
                            print(f"{item.get('canonical_assignment_id')} status=blocked reason={item.get('reason')}")
                    elif args.safe:
                        items = [item for item in _map_list(state.migration_summary.get("items", [])) if item.get("migration_category") in {"safe_merge", "preserve_alias"}]
                        for item in items:
                            print(f"{item.get('source_assignment_id')} -> {item.get('target_canonical_assignment_id')} category={item.get('migration_category')} action={item.get('suggested_operator_action')}")
                    elif args.ambiguous:
                        items = state.ambiguous_assignments
                        for item in items:
                            print(f"{item.get('canonical_assignment_id')} status=ambiguous reason={item.get('reason')}")
                    else:
                        items = state.review_queue
                        for item in items:
                            print(f"{item.get('review_item_id')} category={item.get('category')} assignment={item.get('canonical_assignment_id')} reason={item.get('reason')}")
                    if not items:
                        print("No canonical review items.")
                    print(f"review_queue: {operations_store.review_queue_md}")
                    return 0
                if args.real_estate_canonical_command == "operations":
                    state = operations_engine.build(save=True)
                    _print_canonical_assignment_status(state.summary)
                    print(f"operations_report: {operations_store.operations_report_md}")
                    print(f"review_queue: {operations_store.review_queue_md}")
                    print(f"migration_summary: {operations_store.migration_summary_json}")
                    return 0
                if args.real_estate_canonical_command == "report":
                    operations_engine.build(save=True)
                    print(f"operations_report: {operations_store.operations_report_md}")
                    print(f"review_queue: {operations_store.review_queue_md}")
                    print(f"migration_summary: {operations_store.migration_summary_md}")
                    print(f"blocked_assignments: {operations_store.blocked_assignments_md}")
                    print(f"safe_migrations: {operations_store.safe_migrations_md}")
                    print(f"ambiguous_assignments: {operations_store.ambiguous_assignments_md}")
                    return 0
                if args.real_estate_canonical_command == "conflicts":
                    state = operations_engine.build(save=True)
                    for conflict in state.conflicts:
                        print(
                            f"{conflict.get('conflict_id')} assignment={conflict.get('canonical_assignment_id')} "
                            f"field={conflict.get('field')} existing={conflict.get('existing_value')} incoming={conflict.get('incoming_value')} "
                            f"reason={conflict.get('reason_conflict_remains')} action={conflict.get('suggested_operator_action')}"
                        )
                    if not state.conflicts:
                        print("No canonical identity conflicts.")
                    return 0
            if args.real_estate_command == "assignments":
                canonical_engine = CanonicalAssignmentEngine(args.root.resolve())
                canonical_store = CanonicalAssignmentStore(args.root.resolve())
                if not canonical_store.assignments_json.exists():
                    canonical_engine.build()
                assignments = _map_list(canonical_store.load().get("assignments", []))
                if not assignments:
                    print("No Real Estate assignments found.")
                    return 0
                for assignment in assignments:
                    assignment_id = str(assignment.get("canonical_assignment_id") or "")
                    subject = _map(assignment.get("subject"))
                    print(
                        f"{assignment_id} status={assignment.get('status')} property_type={assignment.get('property_type')} "
                        f"subject={subject.get('address') or ''} due={assignment.get('due_date') or ''} "
                        f"artifacts={len(_map_list(assignment.get('source_artifacts', [])))} aliases={len(_map_list(assignment.get('aliases', [])))} "
                        f"sources={len(_map_list(assignment.get('source_artifacts', [])))} risks={len(_map_list(assignment.get('risks', [])))} "
                        f"missing={len(_map_list(assignment.get('missing_items', [])))} conflicts={len(_map_list(assignment.get('conflicts', [])))} "
                        f"last_activity={assignment.get('last_seen') or assignment.get('updated_at') or ''}"
                    )
                    if args.include_aliases:
                        for alias in _map_list(assignment.get("aliases", [])):
                            print(f"  alias: {alias.get('alias')} type={alias.get('alias_type')}")
                return 0
            assignment_id = args.assignment_id
            if args.real_estate_assignment_command == "create-template":
                path = store.create_template(assignment_id)
                print(f"assignment_template: {path}")
                print("warning: Private local assignment data. Do not commit.")
                return 0
            resolution = _resolve_real_estate_assignment(args.root.resolve(), assignment_id)
            if resolution.ambiguous:
                print(f"requested_alias: {assignment_id}")
                print("resolved: False")
                print("ambiguous: True")
                for match in resolution.matches:
                    print(f"- {match.get('canonical_assignment_id')} alias={match.get('alias')} type={match.get('alias_type')}")
                return 1
            if resolution.resolved:
                assignment_id = resolution.canonical_assignment_id
                print(f"requested_alias: {resolution.requested_alias}")
                print(f"canonical_assignment_id: {resolution.canonical_assignment_id}")
                print(f"alias_type: {resolution.alias_type}")
                print("resolved: True")
            if args.real_estate_assignment_command == "build":
                snapshot = store.build(assignment_id)
                _print_real_estate_assignment_status(snapshot.to_dict(), store.output_dir(assignment_id) / "assignment-brief.md")
                return 0
            if args.real_estate_assignment_command == "status":
                if not (store.output_dir(assignment_id) / "assignment.json").exists():
                    store.build(assignment_id)
                _print_real_estate_assignment_status(store.load(assignment_id), store.output_dir(assignment_id) / "assignment-brief.md")
                return 0
            if args.real_estate_assignment_command == "show":
                if not (store.output_dir(assignment_id) / "assignment.json").exists():
                    store.build(assignment_id)
                print(json.dumps(store.load(assignment_id), indent=2, sort_keys=True))
                if args.open:
                    _open_in_code(store.output_dir(assignment_id) / "assignment-brief.md")
                return 0
            if args.real_estate_assignment_command == "sources":
                data = store.build(assignment_id).to_dict()
                for source in _map_list(data.get("sources", [])):
                    print(f"{source.get('source_id')} category={source.get('source_category')} file={source.get('filename')} checksum={source.get('checksum')}")
                return 0
            if args.real_estate_assignment_command == "missing":
                data = store.build(assignment_id).to_dict()
                for item in _map_list(data.get("missing_items", [])):
                    print(f"{item.get('severity')}: {item.get('field_name')} - {item.get('resolution_guidance')}")
                return 0
            if args.real_estate_assignment_command == "risks":
                data = store.build(assignment_id).to_dict()
                for risk in _map_list(data.get("risks", [])):
                    print(f"{risk.get('severity')}: {risk.get('risk_type')} - {risk.get('description')}")
                return 0
            if args.real_estate_assignment_command == "timeline":
                data = store.build(assignment_id).to_dict()
                for event in _map_list(data.get("timeline", [])):
                    print(f"{event.get('occurred_at')} {event.get('event_type')}: {event.get('title')}")
                return 0
            if args.real_estate_assignment_command == "export":
                store.build(assignment_id)
                print(f"assignment_brief: {store.output_dir(assignment_id) / 'assignment-brief.md'}")
                print(f"source_manifest: {store.output_dir(assignment_id) / 'source-manifest.md'}")
                print(f"evidence_index: {store.output_dir(assignment_id) / 'evidence-index.md'}")
                return 0
        except (RealEstateError, RealEstateIntakeError, AssignmentConsolidationError, CanonicalAssignmentError, CanonicalOperationsError) as exc:
            print(f"error: {exc}")
            return 1
    return 2


def _print_result(result) -> None:
    print(f"workflow_run_id: {result.workflow_run_id}")
    print(f"workflow_id: {result.workflow_id}")
    print(f"status: {result.status}")
    print(f"message_log: {result.message_log}")
    print(f"event_log: {result.event_log}")
    print(f"working_memory: {result.working_memory}")
    if result.approval_path:
        print(f"approval_required: {result.approval_path}")


def _print_run_details(details) -> None:
    summary = details.summary
    print(f"workflow_run_id: {summary.workflow_run_id}")
    print(f"workflow_id: {summary.workflow_id}")
    print(f"status: {summary.status}")
    print(f"current_step: {summary.current_step}")
    print(f"created_at: {summary.created_at}")
    print(f"updated_at: {summary.updated_at}")
    print(f"approval_status: {details.approval_status}")
    print(f"message_log: {details.message_log_path}")
    print(f"event_log: {details.event_log_path}")
    print(f"working_memory: {details.working_memory_path}")
    print("recent_events:")
    for event in details.recent_events:
        print(f"  {event.get('timestamp', 'unknown')} {event.get('type', 'unknown')} {event.get('summary', '')}")
    print("recent_messages:")
    for message in details.recent_messages:
        receiver = message.get("receiver", {})
        receiver_name = receiver.get("name", "unknown") if isinstance(receiver, dict) else "unknown"
        print(
            f"  {message.get('timestamp', 'unknown')} {message.get('requested_action', 'unknown')} "
            f"receiver={receiver_name} status={message.get('status', 'unknown')}"
        )


def _print_lifecycle_result(result) -> None:
    print(f"workflow_run_id: {result.workflow_run_id}")
    print(f"action: {result.action}")
    print(f"status: {result.status}")
    if result.location:
        print(f"location: {result.location}")


def _confirm_delete(target: str) -> bool:
    response = input(f"Type DELETE to confirm deletion of {target}: ")
    return response == "DELETE"


def _print_validation_report(report) -> None:
    print(f"{report.name}: {report.status}")
    if report.ok:
        print(f"checked: {len(report.checked)}")
        return
    for issue in report.issues:
        location = f" path={issue.path}" if issue.path else ""
        print(f"error: {issue.code}: {issue.message}{location}")


def _print_health_report(report) -> None:
    print(f"health: {report.status}")
    for check in report.checks:
        print(f"{check.status}: {check.name}: {check.message}")


def _print_intake_counts(counts) -> None:
    print(f"imported: {counts.get('imported', 0)}")
    print(f"skipped: {counts.get('skipped', 0)}")
    print(f"duplicates: {counts.get('duplicates', 0)}")
    print(f"errors: {counts.get('errors', 0)}")


def _print_daily_run(run) -> None:
    manifest = run.manifest
    print(f"daily_run_id: {run.run_id}")
    print(f"status: {run.status}")
    print(f"completed_at: {run.completed_at}")
    print(f"version: {run.version}")
    print(f"intake_files_processed: {manifest.get('intake_files_processed', 0)}")
    print(f"morning_brief_id: {manifest.get('morning_brief_id') or ''}")
    print(f"memory_snapshot_id: {manifest.get('memory_snapshot_id') or ''}")
    print(f"evidence_graph_id: {manifest.get('evidence_graph_id') or ''}")
    print(f"thesis_count: {manifest.get('thesis_count', 0)}")


def _print_dashboard_summary(dashboard) -> None:
    summary = dashboard.executive_summary
    daily = dashboard.daily_pipeline_status
    thesis = dashboard.thesis_intelligence_summary
    print(f"dashboard_id: {dashboard.dashboard_id}")
    print(f"created_at: {dashboard.created_at}")
    print(f"daily_status: {daily.get('status')}")
    print(f"evidence_count: {summary.get('evidence_count')}")
    print(f"active_or_strengthening_theses: {summary.get('active_or_strengthening_theses')}")
    print(f"current_gaps_or_risks: {summary.get('current_gaps_or_risks')}")
    print(f"thesis_count: {thesis.get('thesis_count')}")
    print(f"key_files: {len(dashboard.key_output_files)}")


def _print_dashboard_status(status) -> None:
    available = sum(1 for item in status.values() if item.get("exists"))
    total = len(status)
    print(f"dashboard_inputs: {available}/{total} available")
    for name, item in status.items():
        state = "available" if item.get("exists") else "unavailable"
        print(f"{state}: {name}: {item.get('path')}")


def _print_real_estate_assignment_status(data, report_path: Path) -> None:
    print(f"available: {bool(data)}")
    print(f"assignment_id: {data.get('assignment_id') or ''}")
    print(f"status: {data.get('status') or ''}")
    print(f"subject_address: {data.get('subject_address') or ''}")
    print(f"source_count: {data.get('source_count', 0)}")
    print(f"fact_count: {data.get('fact_count', 0)}")
    print(f"verified_fact_count: {data.get('verified_fact_count', 0)}")
    print(f"missing_item_count: {data.get('missing_item_count', 0)}")
    print(f"conflict_count: {data.get('conflict_count', 0)}")
    print(f"risk_count: {data.get('risk_count', 0)}")
    print(f"report_path: {report_path}")


def _print_real_estate_intake_status(status) -> None:
    print(f"config_available: {status.get('config_available')}")
    print(f"config_path: {status.get('config_path') or ''}")
    print(f"assignment_root: {status.get('assignment_root')}")
    print(f"enabled_sources: {','.join(_string_list(status.get('enabled_sources', [])))}")
    print(f"detected_candidate_count: {status.get('detected_candidate_count', 0)}")
    print(f"imported_count: {status.get('imported_count', 0)}")
    print(f"skipped_duplicate_count: {status.get('skipped_duplicate_count', 0)}")
    print(f"error_count: {status.get('error_count', 0)}")
    print(f"manifest_path: {status.get('manifest_path')}")


def _print_real_estate_intake_manifest(manifest, dashboard_refreshed: bool) -> None:
    counts = _map(manifest.get("counts"))
    print(f"intake_run_id: {manifest.get('intake_run_id')}")
    print(f"imported: {counts.get('imported', 0)}")
    print(f"updated: {counts.get('updated', 0)}")
    print(f"skipped_duplicate: {counts.get('skipped_duplicate', 0)}")
    print(f"errors: {counts.get('errors', 0)}")
    print(f"dashboard_refreshed: {dashboard_refreshed}")
    for record in _map_list(manifest.get("records", [])):
        print(
            f"assignment_id: {record.get('detected_assignment_id')} status={record.get('import_status')} "
            f"mapped={len(_string_list(record.get('fields_mapped', [])))} conflicts={len(_string_list(record.get('conflicts_created', [])))} "
            f"brief={record.get('assignment_brief_path')}"
        )


def _print_assignment_consolidation_summary(snapshot) -> None:
    counts = _map(snapshot.get("counts"))
    print(f"snapshot_id: {snapshot.get('snapshot_id')}")
    print(f"assignments: {counts.get('assignment_count', 0)}")
    print(f"artifacts: {counts.get('artifact_count', 0)}")
    print(f"knowledge_packs: {counts.get('knowledge_pack_count', 0)}")
    print(f"assignments_with_reviewer_notes: {counts.get('assignments_with_reviewer_notes', 0)}")
    print(f"assignments_with_conflicts: {counts.get('assignments_with_conflicts', 0)}")
    print(f"aliases: {counts.get('alias_count', 0)}")
    print(f"source_companions: {counts.get('source_companion_count', 0)}")
    print(f"unassigned_artifacts: {counts.get('unassigned_artifact_count', 0)}")
    print(f"true_identity_conflicts: {counts.get('true_identity_conflict_count', 0)}")
    print(f"relationships: {counts.get('relationship_count', 0)}")


def _print_assignment_consolidation_status(status) -> None:
    print(f"available: {status.get('available')}")
    print(f"assignments: {status.get('assignment_count', 0)}")
    print(f"artifacts: {status.get('artifact_count', 0)}")
    print(f"knowledge_packs: {status.get('knowledge_pack_count', 0)}")
    print(f"assignments_with_reviewer_notes: {status.get('assignments_with_reviewer_notes', 0)}")
    print(f"assignments_with_conflicts: {status.get('assignments_with_conflicts', 0)}")
    print(f"aliases: {status.get('alias_count', 0)}")
    print(f"source_companions: {status.get('source_companion_count', 0)}")
    print(f"unassigned_artifacts: {status.get('unassigned_artifact_count', 0)}")
    print(f"true_identity_conflicts: {status.get('true_identity_conflict_count', 0)}")
    print(f"clusters_path: {status.get('clusters_path')}")


def _print_canonical_assignment_status(status) -> None:
    print(f"available: {status.get('available')}")
    print(f"canonical_assignments: {status.get('canonical_assignment_count', 0)}")
    print(f"artifacts: {status.get('artifact_count', 0)}")
    print(f"aliases: {status.get('alias_count', 0)}")
    print(f"pending_migration: {status.get('pending_migration_count', 0)}")
    print(f"migration_ready: {status.get('migration_ready_count', 0)}")
    print(f"pending_review: {status.get('pending_review_count', 0)}")
    print(f"blocked: {status.get('blocked_count', 0)}")
    print(f"ambiguous: {status.get('ambiguous_count', 0)}")
    print(f"safe_merge: {status.get('safe_merge_count', 0)}")
    print(f"preserve_alias: {status.get('preserve_alias_count', 0)}")
    print(f"blocked_by_conflict: {status.get('blocked_by_conflict_count', 0)}")
    print(f"orphans: {status.get('orphan_count', 0)}")
    print(f"already_migrated: {status.get('already_migrated_count', 0)}")
    print(f"migrated_alias_directories: {status.get('migrated_alias_directory_count', 0)}")
    print(f"true_assignment_conflicts: {status.get('true_assignment_conflict_count', 0)}")
    print(f"canonical_assignments_path: {status.get('canonical_assignments_path')}")
    print(f"alias_index_path: {status.get('alias_index_path')}")
    if status.get("operations_report_path"):
        print(f"operations_report: {status.get('operations_report_path')}")
    if status.get("review_queue_path"):
        print(f"review_queue: {status.get('review_queue_path')}")


def _scope_text(scope) -> str:
    data = _map(scope)
    parts = []
    for key in ["ready_only", "category", "canonical_assignment_id", "source_assignment_id", "dry_run", "apply", "list_selected"]:
        value = data.get(key)
        if value not in {"", None, False}:
            parts.append(f"{key}={value}")
    return ",".join(parts) if parts else "all"


def _resolve_real_estate_assignment(root: Path, assignment_id: str):
    resolution = CanonicalAssignmentResolver(root).resolve(assignment_id)
    if resolution.resolved or resolution.ambiguous:
        return resolution
    if (RealEstateAssignmentStore(root).assignment_root() / assignment_id / "assignment.yaml").exists():
        return type(resolution)(assignment_id, True, assignment_id, "assignment_directory", False, [], [{"rule": "assignment_directory_fallback"}])
    return resolution


def _open_in_code(path: Path) -> None:
    try:
        subprocess.run(["code", "-r", str(path)], check=False, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception:
        return


def _print_monitor_run(run) -> None:
    print(f"monitor_id: {run.monitor_id}")
    print(f"created_at: {run.created_at}")
    _print_monitor_summary(run.summary)


def _print_monitor_status(status) -> None:
    print(f"available: {status.get('available')}")
    if status.get("monitor_id"):
        print(f"monitor_id: {status.get('monitor_id')}")
        print(f"created_at: {status.get('created_at')}")
    _print_monitor_summary(status.get("summary", {}))


def _print_monitor_summary(summary) -> None:
    print(f"sources_checked: {summary.get('sources_checked', 0)}")
    print(f"sources_changed: {summary.get('sources_changed', 0)}")
    print(f"sources_unchanged: {summary.get('sources_unchanged', 0)}")
    print(f"sources_failed: {summary.get('sources_failed', 0)}")
    print(f"sources_unknown: {summary.get('sources_unknown', 0)}")
    print(f"new_items: {summary.get('new_items', 0)}")
    print(f"removed_items: {summary.get('removed_items', 0)}")
    print(f"updated_items: {summary.get('updated_items', 0)}")


def _print_workflow_run(run) -> None:
    print(f"workflow_run_id: {run.run_id}")
    print(f"workflow_id: {run.workflow_id}")
    print(f"workflow_name: {run.workflow_name}")
    print(f"status: {run.status}")
    print(f"started_at: {run.started_at}")
    print(f"completed_at: {run.completed_at}")
    print(f"duration: {run.duration}")
    print(f"completed_steps: {sum(1 for step in run.executed_steps if step.get('status') in {'completed', 'skipped'})}")
    print(f"failed_steps: {len(run.failed_steps)}")


def _print_evolution_delta(delta) -> None:
    print(f"delta_id: {delta.delta_id}")
    print(f"prior_snapshot_id: {delta.prior_snapshot_id or ''}")
    print(f"current_snapshot_id: {delta.current_snapshot_id}")
    print(f"evidence_gained: {len(delta.evidence_gained)}")
    print(f"evidence_removed: {len(delta.evidence_removed)}")
    print(f"graph_node_growth: {delta.graph_node_growth}")
    print(f"graph_edge_growth: {delta.graph_edge_growth}")
    print(f"thesis_confidence_changes: {len(delta.thesis_confidence_changes)}")
    print(f"thesis_status_changes: {len(delta.thesis_status_changes)}")
    print(f"trend_records: {len(delta.trend_records)}")
    print(f"longitudinal_health_score: {delta.longitudinal_health_score}")


def _print_evolution_status(status) -> None:
    print(f"available: {status.get('available')}")
    print(f"history_count: {status.get('history_count', 0)}")
    if status.get("available"):
        print(f"delta_id: {status.get('delta_id')}")
        print(f"current_snapshot_id: {status.get('current_snapshot_id')}")
        print(f"evidence_gained: {status.get('evidence_gained')}")
        print(f"evidence_removed: {status.get('evidence_removed')}")
        print(f"graph_node_growth: {status.get('graph_node_growth')}")
        print(f"graph_edge_growth: {status.get('graph_edge_growth')}")
        print(f"trend_count: {status.get('trend_count')}")
        print(f"longitudinal_health_score: {status.get('longitudinal_health_score')}")


def _print_report_summary(report, store) -> None:
    summary = report_summary(report)
    print(f"report_id: {summary['report_id']}")
    print(f"created_at: {summary['created_at']}")
    print(f"sections_available: {summary['sections_available']}")
    print(f"section_count: {summary['section_count']}")
    print(f"risks_gaps_count: {summary['risks_gaps_count']}")
    print(f"open_questions_count: {summary['open_questions_count']}")
    print(f"evidence_references_count: {summary['evidence_references_count']}")
    print(f"thesis_references_count: {summary['thesis_references_count']}")
    print(f"report_path: {store.markdown_path}")


def _print_report_status(status) -> None:
    print(f"latest_report_exists: {status.get('latest_report_exists')}")
    print(f"available_inputs: {status.get('available_inputs')}/{status.get('total_inputs')}")
    print(f"latest_report_path: {status.get('latest_report_path')}")
    for name, item in status.get("inputs", {}).items():
        state = "available" if item.get("exists") else "unavailable"
        print(f"{state}: {name}: {item.get('path')}")


def _print_performance_status(status) -> None:
    print(f"available: {status.get('available')}")
    print(f"snapshot_id: {status.get('snapshot_id') or ''}")
    print(f"decision_count: {status.get('decision_count', 0)}")
    print(f"reviewed_decision_count: {status.get('reviewed_decision_count', 0)}")
    print(f"open_decision_count: {status.get('open_decision_count', 0)}")
    print(f"due_review_count: {status.get('due_review_count', 0)}")
    print(f"overdue_review_count: {status.get('overdue_review_count', 0)}")
    print(f"outcome_count: {status.get('outcome_count', 0)}")
    print(f"pending_outcome_count: {status.get('pending_outcome_count', 0)}")
    print(f"lesson_count: {status.get('lesson_count', 0)}")
    print(f"performance_signal_count: {status.get('performance_signal_count', 0)}")
    print(f"high_severity_signal_count: {status.get('high_severity_signal_count', 0)}")
    print(f"report_path: {status.get('report_path')}")
    print(f"learning_loop_path: {status.get('learning_loop_path')}")


def _print_thesis_accuracy_status(status) -> None:
    print(f"thesis_accuracy_available: {status.get('thesis_accuracy_available')}")
    print(f"snapshot_id: {status.get('snapshot_id') or ''}")
    print(f"thesis_count: {status.get('thesis_count', 0)}")
    print(f"average_accuracy_score: {status.get('average_accuracy_score', 0)}")
    print(f"average_quality_score: {status.get('average_quality_score', 0)}")
    print(f"average_process_score: {status.get('average_process_score', 0)}")
    print(f"needs_review_count: {status.get('needs_review_count', 0)}")
    print(f"thesis_accuracy_report_path: {status.get('thesis_accuracy_report_path')}")
    print(f"thesis_scoreboard_path: {status.get('thesis_scoreboard_path')}")


def _print_ai_markets_summary(report, store) -> None:
    print(f"ai_markets_report_id: {report.report_id}")
    print(f"theme_count: {len(report.themes)}")
    print(f"entity_count: {len(report.entities)}")
    print(f"risk_count: {len(report.risks)}")
    print(f"total_open_question_count: {sum(int(question.provenance.get('variant_count', 1)) for question in report.open_questions)}")
    print(f"deduplicated_open_question_count: {len(report.open_questions)}")
    print(f"executive_question_count: {len(report.executive_questions)}")
    print(f"report_path: {store.report_path}")
    print(f"executive_questions_path: {store.executive_questions_path}")


def _print_ai_markets_status(status) -> None:
    print(f"available: {status.get('available')}")
    print(f"report_id: {status.get('report_id') or ''}")
    print(f"theme_count: {status.get('theme_count', 0)}")
    print(f"entity_count: {status.get('entity_count', 0)}")
    print(f"high_confidence_entity_count: {status.get('high_confidence_entity_count', 0)}")
    print(f"risk_count: {status.get('risk_count', 0)}")
    print(f"total_open_question_count: {status.get('total_open_question_count', 0)}")
    print(f"deduplicated_open_question_count: {status.get('deduplicated_open_question_count', 0)}")
    print(f"executive_question_count: {status.get('executive_question_count', 0)}")
    print(f"lifecycle_available: {status.get('lifecycle_available', False)}")
    print(f"report_path: {status.get('report_path')}")
    print(f"executive_questions_path: {status.get('executive_questions_path')}")
    print(f"theme_lifecycle_report_path: {status.get('theme_lifecycle_report_path')}")
    print(f"portfolio_intelligence_available: {status.get('portfolio_intelligence_available', False)}")
    print(f"portfolio_mode: {status.get('portfolio_mode') or ''}")
    print(f"position_count: {status.get('position_count', 0)}")
    print(f"watchlist_count: {status.get('watchlist_count', 0)}")
    print(f"portfolio_theme_exposure_count: {status.get('portfolio_theme_exposure_count', 0)}")
    print(f"portfolio_risk_count: {status.get('portfolio_risk_count', 0)}")
    print(f"high_priority_review_count: {status.get('high_priority_review_count', 0)}")
    print(f"portfolio_report_path: {status.get('portfolio_report_path')}")
    print(f"catalyst_monitor_available: {status.get('catalyst_monitor_available', False)}")
    print(f"total_catalyst_count: {status.get('total_catalyst_count', 0)}")
    print(f"high_priority_catalyst_count: {status.get('high_priority_catalyst_count', 0)}")
    print(f"near_term_catalyst_count: {status.get('near_term_catalyst_count', 0)}")
    print(f"portfolio_linked_catalyst_count: {status.get('portfolio_linked_catalyst_count', 0)}")
    print(f"risk_linked_catalyst_count: {status.get('risk_linked_catalyst_count', 0)}")
    print(f"new_catalyst_count: {status.get('new_catalyst_count', 0)}")
    print(f"stale_catalyst_count: {status.get('stale_catalyst_count', 0)}")
    print(f"catalyst_monitor_report_path: {status.get('catalyst_monitor_report_path')}")
    print(f"catalyst_calendar_path: {status.get('catalyst_calendar_path')}")
    print(f"decision_journal_available: {status.get('decision_journal_available', False)}")
    print(f"decision_entry_count: {status.get('decision_entry_count', 0)}")
    print(f"open_decision_count: {status.get('open_decision_count', 0)}")
    print(f"due_review_count: {status.get('due_review_count', 0)}")
    print(f"overdue_review_count: {status.get('overdue_review_count', 0)}")
    print(f"outcome_count: {status.get('outcome_count', 0)}")
    print(f"decision_journal_report_path: {status.get('decision_journal_report_path')}")
    print(f"decision_review_queue_path: {status.get('decision_review_queue_path')}")
    print(f"executive_brief_available: {status.get('executive_brief_available', False)}")
    print(f"executive_brief_id: {status.get('executive_brief_id') or ''}")
    print(f"executive_brief_path: {status.get('executive_brief_path')}")
    print(f"research_agenda_path: {status.get('research_agenda_path')}")
    print(f"research_agenda_count: {status.get('research_agenda_count', 0)}")
    print(f"high_priority_agenda_count: {status.get('high_priority_agenda_count', 0)}")


def _print_ai_markets_lifecycle_status(status) -> None:
    print(f"lifecycle_available: {status.get('available')}")
    print(f"snapshot_id: {status.get('snapshot_id') or ''}")
    print(f"theme_count: {status.get('theme_count', 0)}")
    print(f"high_conviction_count: {status.get('high_conviction_theme_count', 0)}")
    print(f"strengthening_count: {status.get('strengthening_theme_count', 0)}")
    print(f"active_count: {status.get('active_theme_count', 0)}")
    print(f"emerging_count: {status.get('emerging_theme_count', 0)}")
    print(f"weakening_count: {status.get('weakening_theme_count', 0)}")
    print(f"contradicted_count: {status.get('contradicted_theme_count', 0)}")
    print(f"archived_count: {status.get('archived_theme_count', 0)}")
    print(f"recent_transitions: {status.get('recent_transition_count', 0)}")
    print(f"theme_lifecycle_report_path: {status.get('report_path')}")


def _print_ai_markets_portfolio_status(status) -> None:
    print(f"available: {status.get('available')}")
    print(f"snapshot_id: {status.get('snapshot_id') or ''}")
    print(f"mode: {status.get('mode') or ''}")
    print(f"config_available: {status.get('config_available')}")
    print(f"position_count: {status.get('position_count', 0)}")
    print(f"watchlist_count: {status.get('watchlist_count', 0)}")
    print(f"detected_entity_count: {status.get('detected_entity_count', 0)}")
    print(f"theme_exposure_count: {status.get('theme_exposure_count', 0)}")
    print(f"risk_count: {status.get('risk_count', 0)}")
    print(f"high_priority_review_count: {status.get('high_priority_review_count', 0)}")
    print(f"report_path: {status.get('report_path')}")


def _print_ai_markets_catalyst_status(status) -> None:
    print(f"available: {status.get('available')}")
    print(f"snapshot_id: {status.get('snapshot_id') or ''}")
    print(f"total_catalyst_count: {status.get('total_catalyst_count', 0)}")
    print(f"high_priority_catalyst_count: {status.get('high_priority_catalyst_count', 0)}")
    print(f"near_term_catalyst_count: {status.get('near_term_catalyst_count', 0)}")
    print(f"portfolio_linked_catalyst_count: {status.get('portfolio_linked_catalyst_count', 0)}")
    print(f"risk_linked_catalyst_count: {status.get('risk_linked_catalyst_count', 0)}")
    print(f"new_catalyst_count: {status.get('new_catalyst_count', 0)}")
    print(f"stale_catalyst_count: {status.get('stale_catalyst_count', 0)}")
    print(f"report_path: {status.get('report_path')}")
    print(f"calendar_path: {status.get('calendar_path')}")


def _print_ai_markets_decision_status(status) -> None:
    print(f"available: {status.get('available')}")
    print(f"snapshot_id: {status.get('snapshot_id') or ''}")
    print(f"config_available: {status.get('config_available')}")
    print(f"entry_count: {status.get('entry_count', 0)}")
    print(f"open_decision_count: {status.get('open_decision_count', 0)}")
    print(f"monitoring_decision_count: {status.get('monitoring_decision_count', 0)}")
    print(f"reviewed_decision_count: {status.get('reviewed_decision_count', 0)}")
    print(f"due_review_count: {status.get('due_review_count', 0)}")
    print(f"overdue_review_count: {status.get('overdue_review_count', 0)}")
    print(f"linked_theme_decision_count: {status.get('linked_theme_decision_count', 0)}")
    print(f"linked_entity_decision_count: {status.get('linked_entity_decision_count', 0)}")
    print(f"linked_catalyst_decision_count: {status.get('linked_catalyst_decision_count', 0)}")
    print(f"linked_risk_decision_count: {status.get('linked_risk_decision_count', 0)}")
    print(f"outcome_count: {status.get('outcome_count', 0)}")
    print(f"report_path: {status.get('report_path')}")
    print(f"review_queue_path: {status.get('review_queue_path')}")


def _print_ai_markets_brief_status(status) -> None:
    print(f"available: {status.get('available')}")
    print(f"brief_id: {status.get('brief_id') or ''}")
    print(f"theme_count: {status.get('theme_count', 0)}")
    print(f"watchlist_count: {status.get('watchlist_count', 0)}")
    print(f"total_catalyst_count: {status.get('total_catalyst_count', 0)}")
    print(f"high_priority_catalyst_count: {status.get('high_priority_catalyst_count', 0)}")
    print(f"open_decision_count: {status.get('open_decision_count', 0)}")
    print(f"due_review_count: {status.get('due_review_count', 0)}")
    print(f"overdue_review_count: {status.get('overdue_review_count', 0)}")
    print(f"research_agenda_count: {status.get('research_agenda_count', 0)}")
    print(f"high_priority_agenda_count: {status.get('high_priority_agenda_count', 0)}")
    print(f"top_priority_count: {status.get('top_priority_count', 0)}")
    print(f"remaining_high_priority_count: {status.get('remaining_high_priority_count', 0)}")
    print(f"medium_priority_count: {status.get('medium_priority_count', 0)}")
    print(f"low_priority_count: {status.get('low_priority_count', 0)}")
    print(f"brief_path: {status.get('brief_path')}")
    print(f"agenda_path: {status.get('agenda_path')}")


def _map(value):
    return value if isinstance(value, dict) else {}


def _map_list(value):
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_list(value):
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]
