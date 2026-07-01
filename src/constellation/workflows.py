from __future__ import annotations

from pathlib import Path
from typing import Any

from .models import ApprovalGate, WorkflowDefinition, WorkflowStep
from .registry import AgentRegistry
from .simple_yaml import load_yaml


class WorkflowError(ValueError):
    pass


REQUIRED_WORKFLOW_FIELDS = {
    "id",
    "name",
    "version",
    "purpose",
    "agents",
    "steps",
    "approval_gates",
    "validation",
    "memory_updates",
}


class WorkflowLoader:
    def __init__(self, registry: AgentRegistry) -> None:
        self.registry = registry

    def load(self, path: Path) -> WorkflowDefinition:
        data = load_yaml(path)
        missing = REQUIRED_WORKFLOW_FIELDS - set(data)
        if missing:
            raise WorkflowError(f"{path} missing required fields: {', '.join(sorted(missing))}")

        agents = _string_list(data["agents"], "agents", path)
        for agent_id in agents:
            if not self.registry.has(agent_id):
                raise WorkflowError(f"{path} references unknown agent: {agent_id}")

        steps = [_parse_step(item, path) for item in _mapping_list(data["steps"], "steps", path)]
        for step in steps:
            if step.agent not in agents:
                raise WorkflowError(f"{path} step {step.id} uses agent not declared in workflow: {step.agent}")
            if not self.registry.has(step.agent):
                raise WorkflowError(f"{path} step {step.id} references unknown agent: {step.agent}")

        approval_gates = [
            _parse_approval_gate(item, path)
            for item in _mapping_list(data["approval_gates"], "approval_gates", path)
        ]
        step_ids = {step.id for step in steps}
        for gate in approval_gates:
            if gate.after_step not in step_ids:
                raise WorkflowError(f"{path} approval gate {gate.id} references unknown step: {gate.after_step}")

        validation = data["validation"]
        if not isinstance(validation, dict):
            raise WorkflowError(f"{path} validation must be a mapping")

        memory_updates = data["memory_updates"]
        if not isinstance(memory_updates, (dict, list)):
            raise WorkflowError(f"{path} memory_updates must be a mapping or list")

        return WorkflowDefinition(
            id=_string(data["id"], "id", path),
            name=_string(data["name"], "name", path),
            version=_string(data["version"], "version", path),
            purpose=_string(data["purpose"], "purpose", path),
            agents=agents,
            steps=steps,
            approval_gates=approval_gates,
            validation=validation,
            memory_updates=memory_updates,
            source_path=str(path),
        )


def _parse_step(data: dict[str, Any], path: Path) -> WorkflowStep:
    required = {"id", "agent", "type", "output"}
    missing = required - set(data)
    if missing:
        raise WorkflowError(f"{path} workflow step missing fields: {', '.join(sorted(missing))}")
    input_from = data.get("input_from", [])
    if input_from is None:
        input_from = []
    if not isinstance(input_from, list) or not all(isinstance(item, str) for item in input_from):
        raise WorkflowError(f"{path} input_from must be a list of strings")
    instructions = data.get("instructions")
    if instructions is not None and not isinstance(instructions, str):
        raise WorkflowError(f"{path} instructions must be a string")
    return WorkflowStep(
        id=_string(data["id"], "step.id", path),
        agent=_string(data["agent"], "step.agent", path),
        type=_string(data["type"], "step.type", path),
        output=_string(data["output"], "step.output", path),
        instructions=instructions,
        input_from=input_from,
    )


def _parse_approval_gate(data: dict[str, Any], path: Path) -> ApprovalGate:
    required = {"id", "after_step", "required_by"}
    missing = required - set(data)
    if missing:
        raise WorkflowError(f"{path} approval gate missing fields: {', '.join(sorted(missing))}")
    question = data.get("question")
    if question is not None and not isinstance(question, str):
        raise WorkflowError(f"{path} approval question must be a string")
    return ApprovalGate(
        id=_string(data["id"], "approval.id", path),
        after_step=_string(data["after_step"], "approval.after_step", path),
        required_by=_string(data["required_by"], "approval.required_by", path),
        question=question,
    )


def _string(value: Any, field: str, path: Path) -> str:
    if not isinstance(value, str):
        raise WorkflowError(f"{path} field {field} must be a string")
    return value


def _string_list(value: Any, field: str, path: Path) -> list[str]:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise WorkflowError(f"{path} field {field} must be a list of strings")
    return value


def _mapping_list(value: Any, field: str, path: Path) -> list[dict[str, Any]]:
    if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
        raise WorkflowError(f"{path} field {field} must be a list of mappings")
    return value
