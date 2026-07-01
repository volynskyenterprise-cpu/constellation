from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .approvals import ApprovalManager
from .crew import CrewDoctrine, CrewLoader, agent_id_to_crew_role
from .io import read_json
from .models import JsonMap, WorkflowDefinition, WorkflowStep
from .runs import _tail_jsonl
from .state import WorkflowRunState, WorkflowStateError, WorkflowStateStore
from .workflows import WorkflowLoader


@dataclass(frozen=True)
class ExecutionContext:
    workflow_run_id: str
    workflow_id: str
    current_step: str
    agent_id: str | None
    crew_role: str | None
    crew_doctrine: CrewDoctrine | None
    workflow_definition: WorkflowDefinition
    previous_messages: list[JsonMap]
    recent_events: list[JsonMap]
    working_memory: JsonMap
    project_memory: JsonMap
    provider_routing_config: JsonMap
    approval_state: JsonMap | None

    def to_dict(self) -> JsonMap:
        return {
            "workflow_run_id": self.workflow_run_id,
            "workflow_id": self.workflow_id,
            "current_step": self.current_step,
            "agent_id": self.agent_id,
            "crew_role": self.crew_role,
            "crew_doctrine": self.crew_doctrine.to_dict() if self.crew_doctrine else None,
            "workflow_definition": _workflow_to_dict(self.workflow_definition),
            "previous_messages": self.previous_messages,
            "recent_events": self.recent_events,
            "working_memory": self.working_memory,
            "project_memory": self.project_memory,
            "provider_routing_config": self.provider_routing_config,
            "approval_state": self.approval_state,
        }


class ContextAssembler:
    def __init__(self, root: Path, workflow_loader: WorkflowLoader, crew_loader: CrewLoader) -> None:
        self.root = root
        self.workflow_loader = workflow_loader
        self.crew_loader = crew_loader
        self.state_store = WorkflowStateStore(root)

    def assemble(self, workflow_run_id: str) -> ExecutionContext:
        state = self.state_store.load(workflow_run_id)
        workflow = self.workflow_loader.load(_resolve_path(self.root, Path(state.workflow_path)))
        step = self._current_step(workflow, state)
        current_step = _current_step_name(workflow, state, step)
        agent_id = step.agent if step else None
        crew_role = agent_id_to_crew_role(agent_id) if agent_id else None
        crew_doctrine = self.crew_loader.load(crew_role) if crew_role else None
        return ExecutionContext(
            workflow_run_id=state.workflow_run_id,
            workflow_id=state.workflow_id,
            current_step=current_step,
            agent_id=agent_id,
            crew_role=crew_role,
            crew_doctrine=crew_doctrine,
            workflow_definition=workflow,
            previous_messages=_tail_jsonl(self.root / "logs" / "runs" / workflow_run_id / "messages.jsonl", 10),
            recent_events=_tail_jsonl(self.root / "logs" / "runs" / workflow_run_id / "events.jsonl", 10),
            working_memory=_read_json_or_empty(self.root / "memory" / "runs" / f"{workflow_run_id}-working.json"),
            project_memory=_read_json_or_empty(self.root / "memory" / "project" / "kernel-project-memory.json"),
            provider_routing_config=self._provider_routing_config(),
            approval_state=self._approval_state(state),
        )

    @staticmethod
    def _current_step(workflow: WorkflowDefinition, state: WorkflowRunState) -> WorkflowStep | None:
        if state.status == "completed":
            return None
        if state.pending_approval_id:
            return None
        if state.next_step_index >= len(workflow.steps):
            return None
        return workflow.steps[state.next_step_index]

    def _provider_routing_config(self) -> JsonMap:
        path = self.root / "config" / "providers.yaml"
        from .simple_yaml import load_yaml

        data = load_yaml(path)
        routing = data.get("routing", {})
        return routing if isinstance(routing, dict) else {}

    def _approval_state(self, state: WorkflowRunState) -> JsonMap | None:
        if not state.pending_approval_id:
            return None
        approvals = ApprovalManager(self.root, state.workflow_run_id)
        approval_id = state.pending_approval_id
        status = "approved" if approvals.is_approved(approval_id) else "pending"
        path = approvals.approval_path(approval_id, "accepted" if status == "approved" else "pending")
        data = _read_json_or_empty(path)
        return {"approval_id": approval_id, "status": status, "record": data}


def _current_step_name(workflow: WorkflowDefinition, state: WorkflowRunState, step: WorkflowStep | None) -> str:
    if state.status == "completed":
        return "Complete"
    if state.pending_approval_id:
        return f"approval:{state.pending_approval_id}"
    if step is None:
        return "end"
    return step.id


def _workflow_to_dict(workflow: WorkflowDefinition) -> JsonMap:
    return {
        "id": workflow.id,
        "name": workflow.name,
        "version": workflow.version,
        "purpose": workflow.purpose,
        "agents": workflow.agents,
        "steps": [
            {
                "id": step.id,
                "agent": step.agent,
                "type": step.type,
                "output": step.output,
                "instructions": step.instructions,
                "input_from": step.input_from,
            }
            for step in workflow.steps
        ],
        "approval_gates": [
            {
                "id": gate.id,
                "after_step": gate.after_step,
                "required_by": gate.required_by,
                "question": gate.question,
            }
            for gate in workflow.approval_gates
        ],
        "validation": workflow.validation,
        "memory_updates": workflow.memory_updates,
        "source_path": workflow.source_path,
    }


def _read_json_or_empty(path: Path) -> JsonMap:
    if not path.exists():
        return {}
    try:
        data = read_json(path)
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def _resolve_path(root: Path, path: Path) -> Path:
    if path.is_absolute():
        return path
    return root / path
