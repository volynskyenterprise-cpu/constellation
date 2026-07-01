from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal
from uuid import uuid4


JsonMap = dict[str, Any]
Confidence = Literal["low", "medium", "high", "unknown"]


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex}"


def utc_now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


@dataclass(frozen=True)
class AgentDefinition:
    id: str
    name: str
    version: str
    status: str
    mission: str
    authority: JsonMap
    methods: list[str]
    inputs: JsonMap
    outputs: list[str]
    escalation_triggers: list[str]
    quality_bar: list[str]
    source_path: str


@dataclass(frozen=True)
class WorkflowStep:
    id: str
    agent: str
    type: str
    output: str
    instructions: str | None = None
    input_from: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ApprovalGate:
    id: str
    after_step: str
    required_by: str
    question: str | None = None


@dataclass(frozen=True)
class WorkflowDefinition:
    id: str
    name: str
    version: str
    purpose: str
    agents: list[str]
    steps: list[WorkflowStep]
    approval_gates: list[ApprovalGate]
    validation: JsonMap
    memory_updates: JsonMap | list[str]
    source_path: str


@dataclass(frozen=True)
class Party:
    type: str
    id: str
    name: str

    def to_dict(self) -> JsonMap:
        return {"type": self.type, "id": self.id, "name": self.name}


@dataclass(frozen=True)
class Message:
    id: str
    timestamp: str
    workflow_id: str
    sender: Party
    receiver: Party
    task: JsonMap
    context: JsonMap
    assumptions: list[str]
    reasoning_summary: str
    evidence: list[JsonMap]
    confidence: Confidence
    requested_action: str
    status: str

    def to_dict(self) -> JsonMap:
        return {
            "id": self.id,
            "timestamp": self.timestamp,
            "workflow_id": self.workflow_id,
            "sender": self.sender.to_dict(),
            "receiver": self.receiver.to_dict(),
            "task": self.task,
            "context": self.context,
            "assumptions": self.assumptions,
            "reasoning_summary": self.reasoning_summary,
            "evidence": self.evidence,
            "confidence": self.confidence,
            "requested_action": self.requested_action,
            "status": self.status,
        }


@dataclass(frozen=True)
class Event:
    id: str
    type: str
    timestamp: str
    workflow_id: str | None
    workflow_run_id: str | None
    actor: JsonMap
    subject: JsonMap
    summary: str
    data: JsonMap
    references: list[JsonMap]
    correlation_id: str | None
    causation_id: str | None
    severity: str = "info"

    def to_dict(self) -> JsonMap:
        return {
            "id": self.id,
            "type": self.type,
            "timestamp": self.timestamp,
            "workflow_id": self.workflow_id,
            "workflow_run_id": self.workflow_run_id,
            "actor": self.actor,
            "subject": self.subject,
            "summary": self.summary,
            "data": self.data,
            "references": self.references,
            "correlation_id": self.correlation_id,
            "causation_id": self.causation_id,
            "severity": self.severity,
        }
