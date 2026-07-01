from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .approvals import ApprovalManager
from .config import ConfigurationLoader
from .events import EventBus
from .memory import MemoryManager
from .messages import MessageBus
from .models import Party, WorkflowDefinition, new_id
from .registry import AgentRegistry
from .runs import RunDetails, RunInspector, RunSummary
from .state import WorkflowStateError, WorkflowStateStore
from .workflows import WorkflowLoader


@dataclass(frozen=True)
class KernelRunResult:
    workflow_run_id: str
    workflow_id: str
    status: str
    message_log: Path
    event_log: Path
    working_memory: Path
    approval_path: Path | None = None


class ConstellationKernel:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.config = ConfigurationLoader(root).load()
        self.registry = AgentRegistry.load_from(root / "agents")
        self.workflow_loader = WorkflowLoader(self.registry)
        self.state_store = WorkflowStateStore(root)

    def run_workflow(self, workflow_path: Path) -> KernelRunResult:
        workflow = self.workflow_loader.load(self._resolve_path(workflow_path))
        workflow_run_id = new_id("run")
        relative_workflow_path = str(workflow_path)
        event_bus = EventBus(self.root, workflow_run_id)
        message_bus = MessageBus(self.root, workflow_run_id)
        memory = MemoryManager(self.root, workflow_run_id)
        approvals = ApprovalManager(self.root, workflow_run_id)

        memory.initialize(workflow.purpose)
        self.state_store.save(
            workflow_run_id=workflow_run_id,
            workflow_id=workflow.id,
            workflow_path=relative_workflow_path,
            status="running",
            next_step_index=0,
            pending_approval_id=None,
        )
        event_bus.emit(
            "WorkflowStarted",
            workflow_id=workflow.id,
            actor={"type": "system", "id": "kernel", "name": "Constellation Kernel"},
            subject={"type": "workflow", "id": workflow.id, "name": workflow.name},
            summary=f"Started workflow {workflow.name}.",
            data={"source_path": workflow.source_path},
            correlation_id=workflow_run_id,
        )

        for agent_id in workflow.agents:
            agent = self.registry.get(agent_id)
            event_bus.emit(
                "AgentAssigned",
                workflow_id=workflow.id,
                actor={"type": "system", "id": "kernel", "name": "Constellation Kernel"},
                subject={"type": "agent", "id": agent.id, "name": agent.name},
                summary=f"Assigned agent {agent.name}.",
                correlation_id=workflow_run_id,
            )

        return self._execute_from(
            workflow=workflow,
            workflow_run_id=workflow_run_id,
            workflow_path=relative_workflow_path,
            start_index=0,
            last_message_id=None,
            resumed=False,
        )

    def resume_workflow(self, workflow_run_id: str) -> KernelRunResult:
        state = self.state_store.load(workflow_run_id)
        if state.status != "needs_approval":
            raise WorkflowStateError(f"Workflow run {workflow_run_id} is not waiting for approval")
        if state.pending_approval_id is None:
            raise WorkflowStateError(f"Workflow run {workflow_run_id} has no pending approval recorded")

        approvals = ApprovalManager(self.root, workflow_run_id)
        if not approvals.is_approved(state.pending_approval_id):
            raise WorkflowStateError(f"Approval has not been granted: {state.pending_approval_id}")

        workflow = self.workflow_loader.load(self._resolve_path(Path(state.workflow_path)))
        return self._execute_from(
            workflow=workflow,
            workflow_run_id=workflow_run_id,
            workflow_path=state.workflow_path,
            start_index=state.next_step_index,
            last_message_id=state.pending_approval_id,
            resumed=True,
        )

    def approve(self, approval_id: str) -> dict[str, object]:
        approvals = ApprovalManager(self.root, "")
        approval = approvals.approve(approval_id)
        workflow_run_id = str(approval["workflow_run_id"])
        workflow_id = str(approval["workflow_id"])
        event_bus = EventBus(self.root, workflow_run_id)
        event_bus.emit(
            "ApprovalGranted",
            workflow_id=workflow_id,
            actor={"type": "human", "id": "local_user", "name": "Local User"},
            subject={"type": "approval", "id": approval_id, "name": str(approval["gate_id"])},
            summary=f"Approval granted for {approval_id}.",
            data=approval,
            correlation_id=workflow_run_id,
        )
        return approval

    def list_pending_approvals(self) -> list[dict[str, object]]:
        return ApprovalManager(self.root, "").list_pending()

    def list_runs(self) -> list[RunSummary]:
        return RunInspector(self.root, self.workflow_loader).list_runs()

    def show_run(self, workflow_run_id: str) -> RunDetails:
        return RunInspector(self.root, self.workflow_loader).show_run(workflow_run_id)

    def _execute_from(
        self,
        *,
        workflow: WorkflowDefinition,
        workflow_run_id: str,
        workflow_path: str,
        start_index: int,
        last_message_id: str | None,
        resumed: bool,
    ) -> KernelRunResult:
        event_bus = EventBus(self.root, workflow_run_id)
        message_bus = MessageBus(self.root, workflow_run_id)
        memory = MemoryManager(self.root, workflow_run_id)
        approvals = ApprovalManager(self.root, workflow_run_id)

        if resumed:
            self.state_store.save(
                workflow_run_id=workflow_run_id,
                workflow_id=workflow.id,
                workflow_path=workflow_path,
                status="running",
                next_step_index=start_index,
                pending_approval_id=None,
            )
            event_bus.emit(
                "WorkflowResumed",
                workflow_id=workflow.id,
                actor={"type": "system", "id": "kernel", "name": "Constellation Kernel"},
                subject={"type": "workflow_run", "id": workflow_run_id, "name": workflow.name},
                summary=f"Resumed workflow {workflow.name}.",
                data={"start_step_index": start_index},
                correlation_id=workflow_run_id,
                causation_id=last_message_id,
            )

        for index, step in enumerate(workflow.steps[start_index:], start=start_index):
            agent = self.registry.get(step.agent)
            sender = Party(type="workflow", id=workflow.id, name=workflow.name)
            receiver = Party(type="agent", id=agent.id, name=agent.name)
            event_bus.emit(
                "AgentInvoked",
                workflow_id=workflow.id,
                actor=sender.to_dict(),
                subject=receiver.to_dict(),
                summary=f"Invoked {agent.name} for step {step.id}.",
                data={"step_id": step.id, "step_type": step.type},
                correlation_id=workflow_run_id,
                causation_id=last_message_id,
            )
            message = message_bus.create_for_step(
                workflow=workflow,
                step=step,
                sender=sender,
                receiver=receiver,
                context=memory.context_for_step(step.id),
            )
            last_message_id = message.id
            memory.set_artifact(
                step.output,
                {
                    "status": "placeholder",
                    "produced_by": agent.id,
                    "step_id": step.id,
                    "message_id": message.id,
                    "note": "Kernel v0.1 does not call AI providers; this is a lifecycle placeholder.",
                },
            )
            event_bus.emit(
                "AgentResponded",
                workflow_id=workflow.id,
                actor=receiver.to_dict(),
                subject={"type": "artifact", "id": step.output, "name": step.output},
                summary=f"Recorded placeholder output {step.output}.",
                data={"step_id": step.id, "message_id": message.id},
                references=[{"type": "message", "id": message.id}],
                correlation_id=workflow_run_id,
                causation_id=message.id,
            )

            gate = self._gate_after_step(workflow, step.id)
            if gate is not None:
                approval = approvals.create_request(workflow.id, gate)
                self.state_store.save(
                    workflow_run_id=workflow_run_id,
                    workflow_id=workflow.id,
                    workflow_path=workflow_path,
                    status="needs_approval",
                    next_step_index=index + 1,
                    pending_approval_id=approval.id,
                )
                event_bus.emit(
                    "ApprovalRequested",
                    workflow_id=workflow.id,
                    actor={"type": "system", "id": "kernel", "name": "Constellation Kernel"},
                    subject={"type": "approval", "id": approval.id, "name": gate.id},
                    summary=f"Approval required for gate {gate.id}.",
                    data=approval.to_dict(),
                    correlation_id=workflow_run_id,
                    causation_id=last_message_id,
                )
                event_bus.emit(
                    "WorkflowBlocked",
                    workflow_id=workflow.id,
                    actor={"type": "system", "id": "kernel", "name": "Constellation Kernel"},
                    subject={"type": "workflow_run", "id": workflow_run_id, "name": workflow.name},
                    summary="Workflow blocked pending human approval.",
                    data={"approval_id": approval.id},
                    correlation_id=workflow_run_id,
                )
                return KernelRunResult(
                    workflow_run_id=workflow_run_id,
                    workflow_id=workflow.id,
                    status="needs_approval",
                    message_log=message_bus.log_path,
                    event_log=event_bus.log_path,
                    working_memory=memory.working_path,
                    approval_path=Path(approval.path),
                )
            self.state_store.save(
                workflow_run_id=workflow_run_id,
                workflow_id=workflow.id,
                workflow_path=workflow_path,
                status="running",
                next_step_index=index + 1,
                pending_approval_id=None,
            )

        event_bus.emit(
            "WorkflowCompleted",
            workflow_id=workflow.id,
            actor={"type": "system", "id": "kernel", "name": "Constellation Kernel"},
            subject={"type": "workflow_run", "id": workflow_run_id, "name": workflow.name},
            summary=f"Completed workflow {workflow.name}.",
            correlation_id=workflow_run_id,
        )
        self.state_store.save(
            workflow_run_id=workflow_run_id,
            workflow_id=workflow.id,
            workflow_path=workflow_path,
            status="completed",
            next_step_index=len(workflow.steps),
            pending_approval_id=None,
        )
        return KernelRunResult(
            workflow_run_id=workflow_run_id,
            workflow_id=workflow.id,
            status="completed",
            message_log=message_bus.log_path,
            event_log=event_bus.log_path,
            working_memory=memory.working_path,
        )

    def _resolve_path(self, path: Path) -> Path:
        if path.is_absolute():
            return path
        return self.root / path

    @staticmethod
    def _gate_after_step(workflow: WorkflowDefinition, step_id: str):
        for gate in workflow.approval_gates:
            if gate.after_step == step_id:
                return gate
        return None
