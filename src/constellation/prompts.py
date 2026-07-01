from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .crew import CrewLoader, agent_id_to_crew_role
from .io import read_json, write_json
from .models import JsonMap, WorkflowDefinition, WorkflowStep, utc_now_iso
from .runs import _tail_jsonl
from .state import WorkflowRunState, WorkflowStateError, WorkflowStateStore
from .workflows import WorkflowLoader


class PromptAssemblyError(RuntimeError):
    pass


class PromptUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class PromptPackage:
    prompt_id: str
    workflow_run_id: str
    workflow_id: str
    step_id: str
    agent_id: str
    crew_role: str
    system_prompt: str
    task_prompt: str
    context_sections: JsonMap
    output_contract: JsonMap
    constraints: list[str]
    evidence_requirements: list[str]
    uncertainty_requirements: list[str]
    approval_requirements: JsonMap
    metadata: JsonMap
    created_at: str

    def to_dict(self) -> JsonMap:
        return {
            "prompt_id": self.prompt_id,
            "workflow_run_id": self.workflow_run_id,
            "workflow_id": self.workflow_id,
            "step_id": self.step_id,
            "agent_id": self.agent_id,
            "crew_role": self.crew_role,
            "system_prompt": self.system_prompt,
            "task_prompt": self.task_prompt,
            "context_sections": self.context_sections,
            "output_contract": self.output_contract,
            "constraints": self.constraints,
            "evidence_requirements": self.evidence_requirements,
            "uncertainty_requirements": self.uncertainty_requirements,
            "approval_requirements": self.approval_requirements,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


class PromptAssembler:
    def __init__(self, root: Path, workflow_loader: WorkflowLoader, crew_loader: CrewLoader) -> None:
        self.root = root
        self.workflow_loader = workflow_loader
        self.crew_loader = crew_loader
        self.state_store = WorkflowStateStore(root)

    def assemble(self, workflow_run_id: str, step_id: str | None = None) -> PromptPackage:
        state = self.state_store.load(workflow_run_id)
        workflow = self.workflow_loader.load(_resolve_path(self.root, Path(state.workflow_path)))
        step = self._select_step(workflow, state, step_id)
        crew_role = agent_id_to_crew_role(step.agent)
        doctrine = self.crew_loader.load(crew_role)
        prompt = PromptPackage(
            prompt_id=f"prompt_{workflow_run_id}_{step.id}",
            workflow_run_id=workflow_run_id,
            workflow_id=workflow.id,
            step_id=step.id,
            agent_id=step.agent,
            crew_role=crew_role,
            system_prompt=_build_system_prompt(doctrine.to_dict()),
            task_prompt=_build_task_prompt(workflow, step, doctrine.to_dict()),
            context_sections={
                "crew_profile": doctrine.profile,
                "responsibilities": doctrine.responsibilities,
                "authority": doctrine.authority,
                "communication": doctrine.communication,
                "methodologies": doctrine.methodologies,
                "memory_rules": doctrine.memory,
                "prompt_templates": doctrine.prompts,
                "previous_messages": _tail_jsonl(self.root / "logs" / "runs" / workflow_run_id / "messages.jsonl", 10),
                "recent_events": _tail_jsonl(self.root / "logs" / "runs" / workflow_run_id / "events.jsonl", 10),
                "working_memory": _read_json_or_empty(self.root / "memory" / "runs" / f"{workflow_run_id}-working.json"),
                "project_memory": _read_json_or_empty(self.root / "memory" / "project" / "kernel-project-memory.json"),
                "provider_routing_config": _provider_routing_config(self.root),
            },
            output_contract={
                "expected_output": step.output,
                "status_values": ["completed", "completed_with_warnings", "blocked", "failed"],
                "required_fields": [
                    "summary",
                    "findings",
                    "recommendations",
                    "risks",
                    "assumptions",
                    "evidence_used",
                    "next_steps",
                ],
            },
            constraints=[
                "Do not fabricate evidence.",
                "Preserve human authority.",
                "Follow the crew role authority boundaries.",
                "Do not perform external actions.",
            ],
            evidence_requirements=[
                "Identify evidence used.",
                "Distinguish evidence from interpretation.",
                "State when evidence is missing or weak.",
            ],
            uncertainty_requirements=[
                "State uncertainty explicitly.",
                "Identify assumptions.",
                "Escalate material unknowns.",
            ],
            approval_requirements=_approval_requirements(workflow, step),
            metadata={
                "schema_version": "0.9.0",
                "workflow_name": workflow.name,
                "step_type": step.type,
                "source": "PromptAssembler",
            },
            created_at=utc_now_iso(),
        )
        self.persist(prompt)
        return prompt

    def persist(self, prompt: PromptPackage) -> None:
        path = self.root / "logs" / "runs" / prompt.workflow_run_id / "prompts" / f"{prompt.prompt_id}.json"
        write_json(path, prompt.to_dict())

    @staticmethod
    def _select_step(workflow: WorkflowDefinition, state: WorkflowRunState, step_id: str | None) -> WorkflowStep:
        if step_id is not None:
            for step in workflow.steps:
                if step.id == step_id:
                    return step
            raise PromptAssemblyError(f"Unknown workflow step: {step_id}")
        if state.pending_approval_id:
            raise PromptUnavailable("No agent prompt is available until approval is resolved.")
        if state.status == "completed":
            raise PromptUnavailable("No agent prompt is available for a completed run.")
        if state.next_step_index >= len(workflow.steps):
            raise PromptUnavailable("No current executable step is available.")
        return workflow.steps[state.next_step_index]


def _build_system_prompt(doctrine: JsonMap) -> str:
    return "\n\n".join(
        [
            "You are operating as a Constellation professional role.",
            doctrine["profile"],
            doctrine["authority"],
            doctrine["communication"],
            doctrine["methodologies"],
            "Methodology overrides convenience. Evidence must be traceable. Uncertainty must be explicit.",
        ]
    )


def _build_task_prompt(workflow: WorkflowDefinition, step: WorkflowStep, doctrine: JsonMap) -> str:
    instructions = step.instructions or f"Perform workflow step {step.id}."
    return "\n\n".join(
        [
            f"Workflow: {workflow.name}",
            f"Workflow purpose: {workflow.purpose}",
            f"Step: {step.id}",
            f"Requested action: {step.type}",
            f"Instructions: {instructions}",
            f"Expected output: {step.output}",
            doctrine["prompts"],
        ]
    )


def _approval_requirements(workflow: WorkflowDefinition, step: WorkflowStep) -> JsonMap:
    gates = [
        {
            "id": gate.id,
            "after_step": gate.after_step,
            "required_by": gate.required_by,
            "question": gate.question,
        }
        for gate in workflow.approval_gates
        if gate.after_step == step.id
    ]
    return {"gates_after_step": gates, "human_approval_required_after_step": bool(gates)}


def _provider_routing_config(root: Path) -> JsonMap:
    from .simple_yaml import load_yaml

    data = load_yaml(root / "config" / "providers.yaml")
    routing = data.get("routing", {})
    return routing if isinstance(routing, dict) else {}


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
