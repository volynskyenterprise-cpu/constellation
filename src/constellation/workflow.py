from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from . import __version__
from .ai_markets import AIMarketsStore
from .cross_document import CrossDocumentAnalysisStore, CrossDocumentError
from .daily import DailyPipelineStore
from .dashboard import ExecutiveDashboardStore
from .evidence_graph import EvidenceGraphStore
from .google_drive import GoogleDriveConnector, GoogleDriveDependencyError, GoogleDriveError
from .intake import IntakeEngine, IntakeManifest
from .io import read_json, write_json
from .knowledge_graph import KnowledgeGraphBuilder, KnowledgeGraphError
from .memory import InstitutionalMemoryStore
from .models import JsonMap
from .morning import MorningExecutiveStore
from .research import ResearchError, ResearchOrganization, SUPPORTED_RESEARCH_INPUTS
from .reports import InstitutionalResearchReportStore
from .source_monitor import SourceMonitorStore
from .thesis import ThesisError, ThesisStore
from .thesis_intelligence import ThesisStore as ThesisIntelligenceStore


class WorkflowAutomationError(RuntimeError):
    pass


@dataclass(frozen=True)
class WorkflowStep:
    name: str
    command: str
    arguments: JsonMap
    enabled: bool
    continue_on_failure: bool

    def to_dict(self) -> JsonMap:
        return {
            "name": self.name,
            "command": self.command,
            "arguments": self.arguments,
            "enabled": self.enabled,
            "continue_on_failure": self.continue_on_failure,
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "WorkflowStep":
        return cls(
            name=_require_str(data, "name"),
            command=_require_str(data, "command"),
            arguments=_map(data.get("arguments")),
            enabled=bool(data.get("enabled", True)),
            continue_on_failure=bool(data.get("continue_on_failure", False)),
        )


@dataclass(frozen=True)
class WorkflowDefinition:
    id: str
    name: str
    description: str
    enabled: bool
    created_at: str
    updated_at: str
    steps: list[WorkflowStep]

    def to_dict(self) -> JsonMap:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "steps": [step.to_dict() for step in self.steps],
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "WorkflowDefinition":
        return cls(
            id=_require_str(data, "id"),
            name=_require_str(data, "name"),
            description=_require_str(data, "description"),
            enabled=bool(data.get("enabled", True)),
            created_at=_require_str(data, "created_at"),
            updated_at=_require_str(data, "updated_at"),
            steps=[WorkflowStep.from_dict(item) for item in _map_list(data.get("steps", []))],
        )


@dataclass(frozen=True)
class WorkflowRun:
    run_id: str
    workflow_id: str
    workflow_name: str
    started_at: str
    completed_at: str
    duration: float
    status: str
    executed_steps: list[JsonMap]
    failed_steps: list[JsonMap]
    version: str

    def to_dict(self) -> JsonMap:
        return {
            "run_id": self.run_id,
            "workflow_id": self.workflow_id,
            "workflow_name": self.workflow_name,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "duration": self.duration,
            "status": self.status,
            "executed_steps": self.executed_steps,
            "failed_steps": self.failed_steps,
            "version": self.version,
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "WorkflowRun":
        return cls(
            run_id=_require_str(data, "run_id"),
            workflow_id=_require_str(data, "workflow_id"),
            workflow_name=_require_str(data, "workflow_name"),
            started_at=_require_str(data, "started_at"),
            completed_at=_require_str(data, "completed_at"),
            duration=float(data.get("duration", 0)),
            status=_require_str(data, "status"),
            executed_steps=_map_list(data.get("executed_steps", [])),
            failed_steps=_map_list(data.get("failed_steps", [])),
            version=_require_str(data, "version"),
        )


class WorkflowEngine:
    def __init__(self, root: Path) -> None:
        self.root = root
        self._handlers: dict[str, Callable[[JsonMap], JsonMap]] = {
            "monitor": self._monitor,
            "drive sync": self._drive_sync,
            "intake scan": self._intake_scan,
            "intake import": self._intake_import,
            "process research": self._process_research,
            "graph analyze": self._graph_analyze,
            "thesis generate": self._thesis_generate,
            "morning": self._morning,
            "memory snapshot": self._memory_snapshot,
            "evidence-graph build": self._evidence_graph_build,
            "thesis build": self._thesis_build,
            "daily": self._daily,
            "dashboard": self._dashboard,
            "report latest": self._report_latest,
            "ai-markets build": self._ai_markets_build,
        }

    def run(self, definition: WorkflowDefinition) -> WorkflowRun:
        if not definition.enabled:
            raise WorkflowAutomationError(f"Workflow is disabled: {definition.name}")
        started_at = _now_iso()
        start = perf_counter()
        executed_steps: list[JsonMap] = []
        failed_steps: list[JsonMap] = []
        blocked = False
        for step in definition.steps:
            result = self._execute_step(step)
            executed_steps.append(result)
            if result["status"] == "failed":
                failed_steps.append(result)
                if not step.continue_on_failure:
                    blocked = True
                    break
        completed_at = _now_iso()
        duration = round(perf_counter() - start, 6)
        if blocked:
            status = "failed"
        elif failed_steps:
            status = "completed_with_failures"
        else:
            status = "completed"
        run_seed = "|".join([definition.id, started_at, completed_at, ",".join(str(step.get("status")) for step in executed_steps)])
        return WorkflowRun(
            run_id=f"workflow_{_digest(run_seed)}",
            workflow_id=definition.id,
            workflow_name=definition.name,
            started_at=started_at,
            completed_at=completed_at,
            duration=duration,
            status=status,
            executed_steps=executed_steps,
            failed_steps=failed_steps,
            version=__version__,
        )

    def _execute_step(self, step: WorkflowStep) -> JsonMap:
        started_at = _now_iso()
        start = perf_counter()
        if not step.enabled:
            return {
                "name": step.name,
                "command": step.command,
                "status": "skipped",
                "started_at": started_at,
                "completed_at": _now_iso(),
                "duration": 0,
                "details": {"reason": "step disabled"},
                "error": None,
            }
        handler = self._handlers.get(step.command)
        if handler is None:
            return self._step_result(step, started_at, start, "failed", {}, f"Unsupported workflow command: {step.command}")
        try:
            details = handler(step.arguments)
        except Exception as exc:
            return self._step_result(step, started_at, start, "failed", {}, str(exc))
        return self._step_result(step, started_at, start, str(details.pop("status", "completed")), details, None)

    def _step_result(self, step: WorkflowStep, started_at: str, start: float, status: str, details: JsonMap, error: str | None) -> JsonMap:
        return {
            "name": step.name,
            "command": step.command,
            "status": status,
            "started_at": started_at,
            "completed_at": _now_iso(),
            "duration": round(perf_counter() - start, 6),
            "details": details,
            "error": error,
            "continue_on_failure": step.continue_on_failure,
        }

    def _monitor(self, arguments: JsonMap) -> JsonMap:
        run = SourceMonitorStore(self.root).run(overwrite=bool(arguments.get("overwrite", False)))
        return {"status": "completed", "monitor_id": run.monitor_id, **run.summary}

    def _drive_sync(self, arguments: JsonMap) -> JsonMap:
        connector = GoogleDriveConnector(self.root)
        status = connector.status()
        if not _drive_ready(status):
            return {"status": "skipped", "reason": _drive_skip_reason(status), "connector_status": status}
        try:
            manifest = connector.sync(source_id=_optional_str(arguments.get("source")), dry_run=bool(arguments.get("dry_run", False)))
        except (GoogleDriveDependencyError, GoogleDriveError) as exc:
            return {"status": "failed", "error": str(exc)}
        return {
            "status": "completed",
            "sync_id": manifest.sync_id,
            "downloaded": len(manifest.downloaded_files),
            "skipped": len(manifest.skipped_files),
            "duplicates": len(manifest.duplicate_files),
            "errors": len(manifest.errors),
        }

    def _intake_scan(self, arguments: JsonMap) -> JsonMap:
        items = IntakeEngine(self.root).scan()
        return {"status": "completed", "available": len(items)}

    def _intake_import(self, arguments: JsonMap) -> JsonMap:
        manifest = IntakeEngine(self.root).import_items()
        return {"status": "completed", "manifest_id": manifest.manifest_id, **manifest.counts}

    def _process_research(self, arguments: JsonMap) -> JsonMap:
        return process_new_research_inputs(self.root)

    def _graph_analyze(self, arguments: JsonMap) -> JsonMap:
        if not (self.root / "memory" / "graph" / "graph.json").exists():
            return {"status": "skipped", "reason": "no knowledge graph found"}
        try:
            analysis = CrossDocumentAnalysisStore(self.root).analyze_graph(overwrite=bool(arguments.get("overwrite", False)))
        except CrossDocumentError as exc:
            return {"status": "failed", "error": str(exc)}
        return {"status": "completed", "analysis_id": analysis.analysis_id, "findings": len(analysis.findings)}

    def _thesis_generate(self, arguments: JsonMap) -> JsonMap:
        if not (self.root / "outputs" / "analysis" / "cross-document-analysis.json").exists():
            return {"status": "skipped", "reason": "no cross-document analysis found"}
        try:
            theses = ThesisStore(self.root).generate(overwrite=bool(arguments.get("overwrite", False)))
        except ThesisError as exc:
            return {"status": "failed", "error": str(exc)}
        return {"status": "completed", "thesis_count": len(theses)}

    def _morning(self, arguments: JsonMap) -> JsonMap:
        brief = MorningExecutiveStore(self.root).generate(overwrite=bool(arguments.get("overwrite", False)))
        return {"status": "completed", "brief_id": brief.brief_id}

    def _memory_snapshot(self, arguments: JsonMap) -> JsonMap:
        snapshot = InstitutionalMemoryStore(self.root).create_snapshot(_optional_str(arguments.get("label")))
        return {"status": "completed", "snapshot_id": snapshot.snapshot_id}

    def _evidence_graph_build(self, arguments: JsonMap) -> JsonMap:
        graph = EvidenceGraphStore(self.root).build()
        return {"status": "completed", "graph_id": graph.graph_id, "nodes": len(graph.nodes), "edges": len(graph.edges)}

    def _thesis_build(self, arguments: JsonMap) -> JsonMap:
        if not (self.root / "outputs" / "thesis").exists() and not (self.root / "outputs" / "theses" / "theses.json").exists():
            return {"status": "skipped", "reason": "no thesis inputs found"}
        records = ThesisIntelligenceStore(self.root).build()
        return {"status": "completed", "thesis_count": len(records)}

    def _daily(self, arguments: JsonMap) -> JsonMap:
        run = DailyPipelineStore(self.root).run(overwrite=bool(arguments.get("overwrite", False)))
        return {"status": run.status, "daily_run_id": run.run_id, "pipeline_status": run.status}

    def _dashboard(self, arguments: JsonMap) -> JsonMap:
        dashboard = ExecutiveDashboardStore(self.root).generate(overwrite=bool(arguments.get("overwrite", False)))
        return {"status": "completed", "dashboard_id": dashboard.dashboard_id}

    def _report_latest(self, arguments: JsonMap) -> JsonMap:
        report = InstitutionalResearchReportStore(self.root).generate()
        return {"status": "completed", "report_id": report.report_id, "sections": len(report.sections), "evidence_references": len(report.evidence_references)}

    def _ai_markets_build(self, arguments: JsonMap) -> JsonMap:
        report = AIMarketsStore(self.root).build()
        total_questions = sum(_int(_map(question.provenance).get("variant_count")) or 1 for question in report.open_questions)
        return {
            "status": "completed",
            "report_id": report.report_id,
            "theme_count": len(report.themes),
            "entity_count": len(report.entities),
            "risk_count": len(report.risks),
            "total_open_question_count": total_questions,
            "executive_question_count": len(report.executive_questions),
        }


class WorkflowStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "outputs" / "workflows"
        self.definitions_path = self.directory / "workflow-definitions.json"
        self.history_path = self.directory / "workflow-history.json"
        self.latest_path = self.directory / "latest-workflow.json"
        self.report_path = self.directory / "workflow-report.md"

    def definitions(self) -> list[WorkflowDefinition]:
        definitions = _built_in_workflows()
        self._write_definitions(definitions)
        return definitions

    def get(self, name: str) -> WorkflowDefinition:
        normalized = _normalize_name(name)
        for definition in self.definitions():
            if _normalize_name(definition.name) == normalized or _normalize_name(definition.id) == normalized:
                return definition
        raise WorkflowAutomationError(f"Unknown workflow: {name}")

    def run(self, name: str) -> WorkflowRun:
        definition = self.get(name)
        run = WorkflowEngine(self.root).run(definition)
        self.save_run(run)
        return run

    def history(self) -> list[WorkflowRun]:
        if not self.history_path.exists():
            return []
        data = read_json(self.history_path)
        return [WorkflowRun.from_dict(item) for item in _map_list(data.get("runs", []))]

    def latest(self) -> WorkflowRun:
        if not self.latest_path.exists():
            raise WorkflowAutomationError("No workflow automation run found. Run `python -m constellation workflow run Morning` first.")
        return WorkflowRun.from_dict(read_json(self.latest_path))

    def save_run(self, run: WorkflowRun) -> None:
        write_json(self.latest_path, run.to_dict())
        history = self.history()
        history.append(run)
        write_json(self.history_path, {"runs": [item.to_dict() for item in history]})
        self.export(run)

    def export(self, run: WorkflowRun | None = None) -> Path:
        run = run or self.latest()
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(render_workflow_report(run), encoding="utf-8")
        return self.report_path

    def _write_definitions(self, definitions: list[WorkflowDefinition]) -> None:
        write_json(self.definitions_path, {"workflows": [definition.to_dict() for definition in definitions]})


def render_workflow_report(run: WorkflowRun) -> str:
    lines = [
        "# Workflow Automation Report",
        "",
        f"- Run ID: `{run.run_id}`",
        f"- Workflow: `{run.workflow_name}`",
        f"- Status: `{run.status}`",
        f"- Started: `{run.started_at}`",
        f"- Completed: `{run.completed_at}`",
        f"- Duration: `{run.duration}` seconds",
        f"- Version: `{run.version}`",
        "",
        "## Steps",
        "",
    ]
    for step in run.executed_steps:
        lines.append(f"- `{step.get('name')}` (`{step.get('command')}`): `{step.get('status')}`")
        if step.get("error"):
            lines.append(f"  Error: {step.get('error')}")
    research_steps = [step for step in run.executed_steps if step.get("command") == "process research"]
    if research_steps:
        details = _map(research_steps[-1].get("details"))
        lines.extend(
            [
                "",
                "## Research Processing",
                "",
                f"- New research files detected: {details.get('new_research_files_detected', 0)}",
                f"- Research runs created: {details.get('research_runs_created', 0)}",
                f"- Graph builds completed: {details.get('graph_builds_completed', 0)}",
                f"- Graph builds failed: {details.get('graph_builds_failed', 0)}",
                f"- Skipped files: {details.get('skipped_files_count', 0)}",
                f"- Errors: {len(_map_list(details.get('errors', [])))}",
                "",
            ]
        )
    report_steps = [step for step in run.executed_steps if step.get("command") == "report latest"]
    if report_steps:
        details = _map(report_steps[-1].get("details"))
        lines.extend(
            [
                "",
                "## Institutional Research Report",
                "",
                f"- Latest report ID: `{details.get('report_id', '')}`",
                f"- Sections: {details.get('sections', 0)}",
                f"- Evidence references: {details.get('evidence_references', 0)}",
                "",
            ]
        )
    ai_markets_steps = [step for step in run.executed_steps if step.get("command") == "ai-markets build"]
    if ai_markets_steps:
        details = _map(ai_markets_steps[-1].get("details"))
        lines.extend(
            [
                "",
                "## AI & Markets Intelligence",
                "",
                f"- Latest AI & Markets report ID: `{details.get('report_id', '')}`",
                f"- Themes: {details.get('theme_count', 0)}",
                f"- Entities: {details.get('entity_count', 0)}",
                f"- Risks: {details.get('risk_count', 0)}",
                f"- Total open questions: {details.get('total_open_question_count', 0)}",
                f"- Executive questions: {details.get('executive_question_count', 0)}",
                "",
            ]
        )
    lines.extend(["", "## Failed Steps", ""])
    if not run.failed_steps:
        lines.extend(["- None", ""])
    else:
        for step in run.failed_steps:
            lines.append(f"- `{step.get('name')}`: {step.get('error') or 'failed'}")
        lines.append("")
    lines.extend(
        [
            "## Safety",
            "",
            "- Workflow Automation invokes existing deterministic modules only.",
            "- It does not call providers, OpenAI, Gmail, web retrieval, embeddings, semantic search, scheduling, or autonomous execution.",
            "",
        ]
    )
    return "\n".join(lines)


def _built_in_workflows() -> list[WorkflowDefinition]:
    timestamp = "2026-07-06T00:00:00-07:00"
    return [
        WorkflowDefinition(
            id="morning",
            name="Morning",
            description="Full deterministic morning intelligence package.",
            enabled=True,
            created_at=timestamp,
            updated_at=timestamp,
            steps=[
                _step("Source Monitor", "monitor", {"overwrite": True}),
                _step("Google Drive Sync", "drive sync", {}, continue_on_failure=True),
                _step("Intake Import", "intake import"),
                _step("Research Auto Processing", "process research"),
                _step("Cross Document Analysis", "graph analyze", {"overwrite": True}),
                _step("Thesis Generation", "thesis generate", {"overwrite": True}),
                _step("Thesis Intelligence Build", "thesis build"),
                _step("Evidence Graph Build", "evidence-graph build"),
                _step("Daily Intelligence Pipeline", "daily", {"overwrite": True}),
                _step("Executive Dashboard", "dashboard", {"overwrite": True}),
                _step("Institutional Research Report", "report latest"),
                _step("AI & Markets Intelligence", "ai-markets build"),
            ],
        ),
        WorkflowDefinition(
            id="research-refresh",
            name="Research Refresh",
            description="Refresh deterministic source, graph, thesis, and dashboard state after research intake.",
            enabled=True,
            created_at=timestamp,
            updated_at=timestamp,
            steps=[
                _step("Source Monitor", "monitor", {"overwrite": True}),
                _step("Google Drive Sync", "drive sync", {}, continue_on_failure=True),
                _step("Intake Scan", "intake scan"),
                _step("Evidence Graph Build", "evidence-graph build"),
                _step("Thesis Intelligence Build", "thesis build"),
                _step("Executive Dashboard", "dashboard", {"overwrite": True}),
            ],
        ),
        WorkflowDefinition(
            id="executive-snapshot",
            name="Executive Snapshot",
            description="Create a concise deterministic executive state snapshot.",
            enabled=True,
            created_at=timestamp,
            updated_at=timestamp,
            steps=[
                _step("Morning Executive Brief", "morning", {"overwrite": True}),
                _step("Institutional Memory Snapshot", "memory snapshot", {"label": "workflow-executive-snapshot"}),
                _step("Executive Dashboard", "dashboard", {"overwrite": True}),
            ],
        ),
    ]


def _step(name: str, command: str, arguments: JsonMap | None = None, *, continue_on_failure: bool = False) -> WorkflowStep:
    return WorkflowStep(name=name, command=command, arguments=arguments or {}, enabled=True, continue_on_failure=continue_on_failure)


def detect_new_research_inputs(root: Path) -> list[JsonMap]:
    manifest_path = root / "outputs" / "intake" / "intake-manifest.json"
    if not manifest_path.exists():
        return []
    manifest = IntakeManifest.from_dict(read_json(manifest_path))
    registry = _research_processing_registry(root)
    processed_hashes = {str(item.get("file_hash")) for item in _map_list(registry.get("processed_files", []))}
    inputs: list[JsonMap] = []
    for item in manifest.items:
        if item.status != "imported" or not item.destination_path:
            continue
        path = Path(item.destination_path)
        if not path.is_absolute():
            path = root / path
        if not _is_research_input(root, path):
            continue
        if item.file_hash in processed_hashes:
            continue
        inputs.append(
            {
                "item_id": item.item_id,
                "source_channel": item.source_channel,
                "destination_path": str(path),
                "file_hash": item.file_hash,
                "import_timestamp": item.import_timestamp,
            }
        )
    return sorted(inputs, key=lambda value: str(value.get("destination_path")))


def process_new_research_inputs(root: Path) -> JsonMap:
    inputs = detect_new_research_inputs(root)
    processed_records: list[JsonMap] = []
    skipped_files = _skipped_research_inputs(root)
    errors: list[JsonMap] = []
    research_run_ids: list[str] = []
    graph_builds_completed = 0
    graph_builds_failed = 0
    for item in inputs:
        path = Path(str(item["destination_path"]))
        try:
            result = ResearchOrganization(root).run(path)
            research_run_id = result.workflow_run_id
            research_run_ids.append(research_run_id)
            graph_status = "not_run"
            graph_error = None
            try:
                KnowledgeGraphBuilder(root).build_run(research_run_id)
                graph_status = "completed"
                graph_builds_completed += 1
            except KnowledgeGraphError as exc:
                graph_status = "failed"
                graph_error = str(exc)
                graph_builds_failed += 1
            record = {
                **item,
                "workflow_run_id": research_run_id,
                "research_status": result.status,
                "graph_status": graph_status,
                "graph_error": graph_error,
                "processed_at": _now_iso(),
            }
            processed_records.append(record)
        except ResearchError as exc:
            errors.append({**item, "error": str(exc)})
        except Exception as exc:
            errors.append({**item, "error": str(exc)})
    _append_research_processing_registry(root, processed_records)
    status = "completed" if not errors and graph_builds_failed == 0 else "completed_with_errors"
    return {
        "status": status,
        "new_research_files_detected": len(inputs),
        "research_runs_created": len(research_run_ids),
        "research_run_ids": research_run_ids,
        "graph_builds_completed": graph_builds_completed,
        "graph_builds_failed": graph_builds_failed,
        "skipped_files_count": len(skipped_files),
        "skipped_files": skipped_files,
        "processed_files": processed_records,
        "errors": errors,
    }


def collect_research_run_ids(root: Path) -> list[str]:
    registry = _research_processing_registry(root)
    return sorted({str(item.get("workflow_run_id")) for item in _map_list(registry.get("processed_files", [])) if item.get("workflow_run_id")})


def _skipped_research_inputs(root: Path) -> list[JsonMap]:
    manifest_path = root / "outputs" / "intake" / "intake-manifest.json"
    if not manifest_path.exists():
        return []
    manifest = IntakeManifest.from_dict(read_json(manifest_path))
    processed_hashes = {str(item.get("file_hash")) for item in _map_list(_research_processing_registry(root).get("processed_files", []))}
    skipped = []
    for item in manifest.items:
        if item.status != "imported" or not item.destination_path:
            continue
        path = Path(item.destination_path)
        if not path.is_absolute():
            path = root / path
        if _is_research_input(root, path) and item.file_hash in processed_hashes:
            skipped.append({"destination_path": str(path), "file_hash": item.file_hash, "reason": "already processed"})
    return sorted(skipped, key=lambda value: str(value.get("destination_path")))


def _research_processing_registry_path(root: Path) -> Path:
    return root / "outputs" / "workflows" / "research-processing.json"


def _research_processing_registry(root: Path) -> JsonMap:
    path = _research_processing_registry_path(root)
    if not path.exists():
        return {"processed_files": []}
    try:
        data = read_json(path)
    except Exception:
        return {"processed_files": []}
    return data if isinstance(data, dict) else {"processed_files": []}


def _append_research_processing_registry(root: Path, records: list[JsonMap]) -> None:
    if not records:
        return
    registry = _research_processing_registry(root)
    existing = _map_list(registry.get("processed_files", []))
    by_hash = {str(item.get("file_hash")): item for item in existing}
    for record in records:
        if record.get("graph_status") == "completed":
            by_hash[str(record.get("file_hash"))] = record
    write_json(_research_processing_registry_path(root), {"processed_files": [by_hash[key] for key in sorted(by_hash)]})


def _is_research_input(root: Path, path: Path) -> bool:
    try:
        path.relative_to(root / "research_inputs")
    except ValueError:
        return False
    return path.suffix.lower() in SUPPORTED_RESEARCH_INPUTS and path.exists() and path.is_file()


def _drive_ready(status: JsonMap) -> bool:
    return (
        status.get("config_present") is True
        and status.get("dependencies_installed") is True
        and status.get("credentials_path_configured") is True
        and status.get("token_path_configured") is True
        and bool(status.get("enabled_sources"))
    )


def _drive_skip_reason(status: JsonMap) -> str:
    if not status.get("config_present"):
        return "configuration missing"
    if not status.get("dependencies_installed"):
        return "optional dependencies missing"
    if not status.get("credentials_path_configured") or not status.get("token_path_configured"):
        return "credentials or token path not configured"
    if not status.get("enabled_sources"):
        return "no enabled Google Drive sources"
    return "not ready"


def _normalize_name(value: str) -> str:
    return value.strip().lower().replace("_", "-").replace(" ", "-")


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:16]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _map(value: Any) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


def _map_list(value: Any) -> list[JsonMap]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _require_str(data: JsonMap, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise WorkflowAutomationError(f"Workflow field {key} must be a string")
    return value
