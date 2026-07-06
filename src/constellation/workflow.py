from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any, Callable

from . import __version__
from .daily import DailyPipelineStore
from .dashboard import ExecutiveDashboardStore
from .evidence_graph import EvidenceGraphStore
from .google_drive import GoogleDriveConnector, GoogleDriveDependencyError, GoogleDriveError
from .intake import IntakeEngine
from .io import read_json, write_json
from .memory import InstitutionalMemoryStore
from .models import JsonMap
from .morning import MorningExecutiveStore
from .source_monitor import SourceMonitorStore
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
            "morning": self._morning,
            "memory snapshot": self._memory_snapshot,
            "evidence-graph build": self._evidence_graph_build,
            "thesis build": self._thesis_build,
            "daily": self._daily,
            "dashboard": self._dashboard,
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
        records = ThesisIntelligenceStore(self.root).build()
        return {"status": "completed", "thesis_count": len(records)}

    def _daily(self, arguments: JsonMap) -> JsonMap:
        run = DailyPipelineStore(self.root).run(overwrite=bool(arguments.get("overwrite", False)))
        return {"status": run.status, "daily_run_id": run.run_id, "pipeline_status": run.status}

    def _dashboard(self, arguments: JsonMap) -> JsonMap:
        dashboard = ExecutiveDashboardStore(self.root).generate(overwrite=bool(arguments.get("overwrite", False)))
        return {"status": "completed", "dashboard_id": dashboard.dashboard_id}


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
                _step("Intake Scan", "intake scan"),
                _step("Morning Executive Brief", "morning", {"overwrite": True}),
                _step("Institutional Memory Snapshot", "memory snapshot", {"label": "workflow-morning"}),
                _step("Evidence Graph Build", "evidence-graph build"),
                _step("Thesis Intelligence Build", "thesis build"),
                _step("Daily Intelligence Pipeline", "daily", {"overwrite": True}),
                _step("Executive Dashboard", "dashboard", {"overwrite": True}),
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
