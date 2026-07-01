from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .approvals import ApprovalManager
from .models import JsonMap
from .state import WorkflowRunState, WorkflowStateError, WorkflowStateStore
from .workflows import WorkflowLoader


@dataclass(frozen=True)
class RunSummary:
    workflow_run_id: str
    workflow_id: str
    status: str
    current_step: str
    created_at: str
    updated_at: str
    state_valid: bool = True


@dataclass(frozen=True)
class RunDetails:
    summary: RunSummary
    approval_status: str
    message_log_path: Path
    event_log_path: Path
    working_memory_path: Path
    recent_events: list[JsonMap]
    recent_messages: list[JsonMap]


class RunInspector:
    def __init__(self, root: Path, workflow_loader: WorkflowLoader) -> None:
        self.root = root
        self.workflow_loader = workflow_loader
        self.state_store = WorkflowStateStore(root)

    def list_runs(self) -> list[RunSummary]:
        summaries: list[RunSummary] = []
        runs_dir = self.root / "logs" / "runs"
        if not runs_dir.exists():
            return []

        for run_dir in runs_dir.iterdir():
            if not run_dir.is_dir():
                continue
            state_path = run_dir / "state.json"
            if not state_path.exists():
                continue
            summaries.append(self._summary_from_path(run_dir.name, state_path))

        return sorted(
            summaries,
            key=lambda item: (item.state_valid, item.updated_at if item.updated_at != "unknown" else ""),
            reverse=True,
        )

    def show_run(self, workflow_run_id: str) -> RunDetails:
        state_path = self.state_store.path_for(workflow_run_id)
        if not state_path.exists():
            raise WorkflowStateError(f"Unknown workflow run: {workflow_run_id}")
        summary = self._summary_from_path(workflow_run_id, state_path)
        if not summary.state_valid:
            raise WorkflowStateError(f"Workflow run has invalid state: {workflow_run_id}")

        state = self.state_store.load(workflow_run_id)
        approval_status = self._approval_status(state)
        run_dir = self.root / "logs" / "runs" / workflow_run_id
        message_log = run_dir / "messages.jsonl"
        event_log = run_dir / "events.jsonl"
        working_memory = self.root / "memory" / "runs" / f"{workflow_run_id}-working.json"
        return RunDetails(
            summary=summary,
            approval_status=approval_status,
            message_log_path=message_log,
            event_log_path=event_log,
            working_memory_path=working_memory,
            recent_events=_tail_jsonl(event_log, 5),
            recent_messages=_tail_jsonl(message_log, 5),
        )

    def _summary_from_path(self, workflow_run_id: str, state_path: Path) -> RunSummary:
        try:
            state = self.state_store.load(workflow_run_id)
        except Exception:
            return RunSummary(
                workflow_run_id=workflow_run_id,
                workflow_id="unknown",
                status="invalid_state",
                current_step="unknown",
                created_at="unknown",
                updated_at="unknown",
                state_valid=False,
            )
        return RunSummary(
            workflow_run_id=state.workflow_run_id,
            workflow_id=state.workflow_id,
            status=state.status,
            current_step=self._current_step(state),
            created_at=state.created_at,
            updated_at=state.updated_at,
        )

    def _current_step(self, state: WorkflowRunState) -> str:
        if state.status == "completed":
            return "Complete"
        if state.pending_approval_id:
            return f"approval:{state.pending_approval_id}"
        try:
            workflow = self.workflow_loader.load(_resolve_path(self.root, Path(state.workflow_path)))
        except Exception:
            return f"step_index:{state.next_step_index}"
        if state.next_step_index >= len(workflow.steps):
            return "Complete" if state.status == "completed" else "end"
        return workflow.steps[state.next_step_index].id

    def _approval_status(self, state: WorkflowRunState) -> str:
        if not state.pending_approval_id:
            for path in (self.root / "approvals" / "accepted").glob("*.json"):
                try:
                    data = json.loads(path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    continue
                if data.get("workflow_run_id") == state.workflow_run_id and data.get("status") == "approved":
                    return "approved"
            return "not_applicable"
        approvals = ApprovalManager(self.root, state.workflow_run_id)
        if approvals.is_approved(state.pending_approval_id):
            return "approved"
        if approvals.approval_path(state.pending_approval_id, "pending").exists():
            return "pending"
        return "missing"


def _resolve_path(root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return root / path


def _tail_jsonl(path: Path, limit: int) -> list[JsonMap]:
    if not path.exists():
        return []
    records: list[JsonMap] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            value = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(value, dict):
            records.append(value)
    return records[-limit:]
