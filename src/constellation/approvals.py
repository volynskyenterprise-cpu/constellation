from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .io import read_json, write_json
from .models import ApprovalGate, new_id, utc_now_iso


class ApprovalRequired(RuntimeError):
    def __init__(self, approval: "ApprovalRequest") -> None:
        self.approval = approval
        super().__init__(f"Human approval required: {approval.id}")


@dataclass(frozen=True)
class ApprovalRequest:
    id: str
    workflow_run_id: str
    workflow_id: str
    gate_id: str
    after_step: str
    required_by: str
    question: str
    status: str
    created_at: str
    path: str

    def to_dict(self) -> dict[str, str]:
        return {
            "id": self.id,
            "workflow_run_id": self.workflow_run_id,
            "workflow_id": self.workflow_id,
            "gate_id": self.gate_id,
            "after_step": self.after_step,
            "required_by": self.required_by,
            "question": self.question,
            "status": self.status,
            "created_at": self.created_at,
            "path": self.path,
        }


class ApprovalManager:
    def __init__(self, root: Path, workflow_run_id: str) -> None:
        self.root = root
        self.workflow_run_id = workflow_run_id

    def create_request(self, workflow_id: str, gate: ApprovalGate) -> ApprovalRequest:
        approval_id = new_id("appr")
        path = self.root / "approvals" / "pending" / f"{approval_id}.json"
        request = ApprovalRequest(
            id=approval_id,
            workflow_run_id=self.workflow_run_id,
            workflow_id=workflow_id,
            gate_id=gate.id,
            after_step=gate.after_step,
            required_by=gate.required_by,
            question=gate.question or "Human approval required to continue.",
            status="pending",
            created_at=utc_now_iso(),
            path=str(path),
        )
        write_json(path, request.to_dict())
        return request

    def list_pending(self) -> list[dict[str, object]]:
        pending_dir = self.root / "approvals" / "pending"
        if not pending_dir.exists():
            return []
        approvals = [read_json(path) for path in sorted(pending_dir.glob("*.json"))]
        return approvals

    def approval_path(self, approval_id: str, status: str = "pending") -> Path:
        return self.root / "approvals" / status / f"{approval_id}.json"

    def is_approved(self, approval_id: str) -> bool:
        path = self.approval_path(approval_id, "accepted")
        if not path.exists():
            return False
        data = read_json(path)
        return data.get("status") == "approved"

    def approve(self, approval_id: str) -> dict[str, object]:
        pending_path = self.approval_path(approval_id, "pending")
        accepted_path = self.approval_path(approval_id, "accepted")
        if accepted_path.exists():
            return read_json(accepted_path)
        if not pending_path.exists():
            raise FileNotFoundError(f"Pending approval not found: {approval_id}")

        data = read_json(pending_path)
        data["status"] = "approved"
        data["approved_at"] = utc_now_iso()
        data["explicit_human_approval"] = True
        data["path"] = str(accepted_path)
        write_json(accepted_path, data)
        pending_path.unlink()
        return data
