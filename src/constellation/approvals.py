from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .io import write_json
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
