from __future__ import annotations

import argparse
import json
from pathlib import Path

from .artifacts import ArtifactError
from .cross_document import CrossDocumentAnalysisStore, CrossDocumentError
from .evidence import EvidenceError, EvidenceStore
from .evidence_graph import EvidenceGraphError, EvidenceGraphStore
from .google_drive import GoogleDriveConnector, GoogleDriveDependencyError, GoogleDriveError
from .intake import IntakeEngine, IntakeError
from .intelligence import IntelligenceError, IntelligenceStore
from .kernel import ConstellationKernel
from .knowledge_graph import KnowledgeGraphBuilder, KnowledgeGraphError, KnowledgeGraphStore, show_graph_item
from .memory import InstitutionalMemoryError, InstitutionalMemoryStore
from .morning import MorningExecutiveError, MorningExecutiveStore
from .pkos import PKOSError, PKOSKnowledgeOrganization
from .prompts import PromptUnavailable
from .research import ResearchError, ResearchOrganization
from .state import WorkflowStateError
from .thesis import ThesisError, ThesisStore
from .thesis_intelligence import ThesisIntelligenceError, ThesisStore as ThesisIntelligenceStore


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
