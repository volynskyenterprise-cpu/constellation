from __future__ import annotations

import json
import shutil
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

from .events import EventBus
from .io import append_jsonl, read_json
from .models import utc_now_iso
from .state import WorkflowStateError, WorkflowStateStore


PruneAction = Literal["archive", "delete"]


@dataclass(frozen=True)
class LifecycleResult:
    workflow_run_id: str
    action: str
    status: str
    location: Path | None = None


class RunLifecycleManager:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.state_store = WorkflowStateStore(root)

    def archive(self, workflow_run_id: str) -> LifecycleResult:
        state = self.state_store.load(workflow_run_id)
        run_dir = self.root / "logs" / "runs" / workflow_run_id
        if not run_dir.exists():
            raise WorkflowStateError(f"Run artifacts not found: {workflow_run_id}")

        event_bus = EventBus(self.root, workflow_run_id)
        event_bus.emit(
            "WorkflowArchived",
            workflow_id=state.workflow_id,
            actor={"type": "system", "id": "kernel", "name": "Constellation Kernel"},
            subject={"type": "workflow_run", "id": workflow_run_id, "name": state.workflow_id},
            summary=f"Archived workflow run {workflow_run_id}.",
            data={"archived_at": utc_now_iso()},
            correlation_id=workflow_run_id,
        )
        self.state_store.save(
            workflow_run_id=workflow_run_id,
            workflow_id=state.workflow_id,
            workflow_path=state.workflow_path,
            status="archived",
            next_step_index=state.next_step_index,
            pending_approval_id=state.pending_approval_id,
        )

        archive_root = self.root / "archive" / "runs" / workflow_run_id
        if archive_root.exists():
            raise WorkflowStateError(f"Archive already exists for run: {workflow_run_id}")
        (archive_root / "logs").parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(run_dir), str(archive_root / "logs"))

        self._move_if_exists(
            self.root / "memory" / "runs" / f"{workflow_run_id}-working.json",
            archive_root / "memory" / f"{workflow_run_id}-working.json",
        )
        self._move_approval_records(workflow_run_id, archive_root)
        self._write_lifecycle_event("RunArchived", workflow_run_id, "archived", archive_root)
        return LifecycleResult(workflow_run_id, "archive", "archived", archive_root)

    def delete(self, workflow_run_id: str) -> LifecycleResult:
        active_run_dir = self.root / "logs" / "runs" / workflow_run_id
        archive_root = self.root / "archive" / "runs" / workflow_run_id
        if not active_run_dir.exists() and not archive_root.exists():
            raise WorkflowStateError(f"Unknown workflow run: {workflow_run_id}")

        workflow_id = self._workflow_id_for_lifecycle(workflow_run_id)
        self._write_lifecycle_event("RunDeleted", workflow_run_id, "deleted", None, workflow_id=workflow_id)

        if active_run_dir.exists():
            shutil.rmtree(active_run_dir)
        if archive_root.exists():
            shutil.rmtree(archive_root)
        self._remove_if_exists(self.root / "memory" / "runs" / f"{workflow_run_id}-working.json")
        self._remove_approval_records(workflow_run_id)
        return LifecycleResult(workflow_run_id, "delete", "deleted", None)

    def prune(self, older_than_days: int, action: PruneAction = "archive") -> list[LifecycleResult]:
        if older_than_days < 0:
            raise ValueError("older_than_days must be non-negative")
        cutoff = datetime.now().astimezone() - timedelta(days=older_than_days)
        results: list[LifecycleResult] = []
        for state in self._active_states():
            updated_at = _parse_timestamp(state.updated_at)
            if updated_at is None or updated_at >= cutoff:
                continue
            if action == "delete":
                results.append(self.delete(state.workflow_run_id))
            else:
                results.append(self.archive(state.workflow_run_id))
        return results

    def _active_states(self):
        runs_dir = self.root / "logs" / "runs"
        if not runs_dir.exists():
            return []
        states = []
        for run_dir in runs_dir.iterdir():
            if not run_dir.is_dir():
                continue
            try:
                states.append(self.state_store.load(run_dir.name))
            except Exception:
                continue
        return states

    def _workflow_id_for_lifecycle(self, workflow_run_id: str) -> str | None:
        active_state = self.root / "logs" / "runs" / workflow_run_id / "state.json"
        archived_state = self.root / "archive" / "runs" / workflow_run_id / "logs" / "state.json"
        for path in [active_state, archived_state]:
            if path.exists():
                try:
                    data = read_json(path)
                except Exception:
                    continue
                workflow_id = data.get("workflow_id")
                if isinstance(workflow_id, str):
                    return workflow_id
        return None

    def _move_approval_records(self, workflow_run_id: str, archive_root: Path) -> None:
        for status in ["pending", "accepted", "rejected"]:
            source_dir = self.root / "approvals" / status
            for path in source_dir.glob("*.json"):
                if _record_workflow_run_id(path) != workflow_run_id:
                    continue
                self._move_if_exists(path, archive_root / "approvals" / status / path.name)

    def _remove_approval_records(self, workflow_run_id: str) -> None:
        for status in ["pending", "accepted", "rejected"]:
            for path in (self.root / "approvals" / status).glob("*.json"):
                if _record_workflow_run_id(path) == workflow_run_id:
                    path.unlink()

    def _write_lifecycle_event(
        self,
        event_type: str,
        workflow_run_id: str,
        status: str,
        location: Path | None,
        *,
        workflow_id: str | None = None,
    ) -> None:
        append_jsonl(
            self.root / "logs" / "lifecycle.jsonl",
            {
                "id": f"{event_type}_{workflow_run_id}",
                "type": event_type,
                "timestamp": utc_now_iso(),
                "workflow_run_id": workflow_run_id,
                "workflow_id": workflow_id,
                "status": status,
                "location": str(location) if location else None,
            },
        )

    @staticmethod
    def _move_if_exists(source: Path, destination: Path) -> None:
        if not source.exists():
            return
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(str(source), str(destination))

    @staticmethod
    def _remove_if_exists(path: Path) -> None:
        if path.exists():
            path.unlink()


def _record_workflow_run_id(path: Path) -> str | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return None
    workflow_run_id = data.get("workflow_run_id")
    return workflow_run_id if isinstance(workflow_run_id, str) else None


def _parse_timestamp(value: str) -> datetime | None:
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None
