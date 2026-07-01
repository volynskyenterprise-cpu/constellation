from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .io import read_json, write_json
from .models import utc_now_iso


class WorkflowStateError(RuntimeError):
    pass


@dataclass(frozen=True)
class WorkflowRunState:
    workflow_run_id: str
    workflow_id: str
    workflow_path: str
    status: str
    next_step_index: int
    pending_approval_id: str | None
    created_at: str
    updated_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "workflow_run_id": self.workflow_run_id,
            "workflow_id": self.workflow_id,
            "workflow_path": self.workflow_path,
            "status": self.status,
            "next_step_index": self.next_step_index,
            "pending_approval_id": self.pending_approval_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class WorkflowStateStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def path_for(self, workflow_run_id: str) -> Path:
        return self.root / "logs" / "runs" / workflow_run_id / "state.json"

    def save(
        self,
        *,
        workflow_run_id: str,
        workflow_id: str,
        workflow_path: str,
        status: str,
        next_step_index: int,
        pending_approval_id: str | None,
    ) -> WorkflowRunState:
        now = utc_now_iso()
        created_at = now
        path = self.path_for(workflow_run_id)
        if path.exists():
            try:
                created_at = _optional_str(read_json(path), "created_at") or now
            except Exception:
                created_at = now
        state = WorkflowRunState(
            workflow_run_id=workflow_run_id,
            workflow_id=workflow_id,
            workflow_path=workflow_path,
            status=status,
            next_step_index=next_step_index,
            pending_approval_id=pending_approval_id,
            created_at=created_at,
            updated_at=now,
        )
        write_json(path, state.to_dict())
        return state

    def load(self, workflow_run_id: str) -> WorkflowRunState:
        path = self.path_for(workflow_run_id)
        if not path.exists():
            raise WorkflowStateError(f"Unknown workflow run: {workflow_run_id}")
        data = read_json(path)
        return WorkflowRunState(
            workflow_run_id=_require_str(data, "workflow_run_id"),
            workflow_id=_require_str(data, "workflow_id"),
            workflow_path=_require_str(data, "workflow_path"),
            status=_require_str(data, "status"),
            next_step_index=_require_int(data, "next_step_index"),
            pending_approval_id=_optional_str(data, "pending_approval_id"),
            created_at=_optional_str(data, "created_at") or _require_str(data, "updated_at"),
            updated_at=_require_str(data, "updated_at"),
        )


def _require_str(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise WorkflowStateError(f"Run state field {key} must be a string")
    return value


def _optional_str(data: dict[str, Any], key: str) -> str | None:
    value = data.get(key)
    if value is None:
        return None
    if not isinstance(value, str):
        raise WorkflowStateError(f"Run state field {key} must be a string or null")
    return value


def _require_int(data: dict[str, Any], key: str) -> int:
    value = data.get(key)
    if not isinstance(value, int):
        raise WorkflowStateError(f"Run state field {key} must be an integer")
    return value
