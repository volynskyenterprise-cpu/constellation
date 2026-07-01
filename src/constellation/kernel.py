from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .approvals import ApprovalManager
from .config import ConfigurationLoader
from .events import EventBus
from .lifecycle import LifecycleResult, PruneAction, RunLifecycleManager
from .memory import MemoryManager
from .messages import MessageBus
from .models import Party, WorkflowDefinition, new_id
from .providers import ProviderError, ProviderRegistry
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
        self.provider_registry = ProviderRegistry.load_from(root / "config" / "providers.yaml")

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

    def archive_run(self, workflow_run_id: str) -> LifecycleResult:
        return RunLifecycleManager(self.root).archive(workflow_run_id)

    def delete_run(self, workflow_run_id: str) -> LifecycleResult:
        return RunLifecycleManager(self.root).delete(workflow_run_id)

    def prune_runs(self, older_than_days: int, action: PruneAction = "archive") -> list[LifecycleResult]:
        return RunLifecycleManager(self.root).prune(older_than_days, action)

    def list_providers(self):
        return self.provider_registry.all()

    def show_provider(self, provider_name: str):
        return self.provider_registry.get_definition(provider_name)

    def provider_health(self) -> list[dict[str, object]]:
        return self.provider_registry.health()

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
            provider_result = self._maybe_invoke_provider(
                message=message,
                step_id=step.id,
                agent_id=agent.id,
                event_bus=event_bus,
                message_bus=message_bus,
                workflow_id=workflow.id,
                workflow_run_id=workflow_run_id,
            )
            step_status = "provider_backed" if provider_result else "placeholder"
            if provider_result and provider_result.get("status") == "failed":
                step_status = "failed"
            last_message_id = message.id
            memory.set_artifact(
                step.output,
                {
                    "status": step_status,
                    "produced_by": agent.id,
                    "step_id": step.id,
                    "message_id": message.id,
                    "provider_result": provider_result,
                    "output_text": provider_result.get("output_text") if provider_result else None,
                    "note": "Kernel v0.1 placeholder path." if provider_result is None else "Provider-backed deterministic output.",
                },
            )
            if step_status == "failed":
                self.state_store.save(
                    workflow_run_id=workflow_run_id,
                    workflow_id=workflow.id,
                    workflow_path=workflow_path,
                    status="failed",
                    next_step_index=index,
                    pending_approval_id=None,
                )
                event_bus.emit(
                    "WorkflowBlocked",
                    workflow_id=workflow.id,
                    actor={"type": "system", "id": "kernel", "name": "Constellation Kernel"},
                    subject={"type": "workflow_run", "id": workflow_run_id, "name": workflow.name},
                    summary=f"Workflow failed at step {step.id}.",
                    data={"step_id": step.id, "provider_result": provider_result},
                    correlation_id=workflow_run_id,
                    causation_id=message.id,
                    severity="error",
                )
                return KernelRunResult(
                    workflow_run_id=workflow_run_id,
                    workflow_id=workflow.id,
                    status="failed",
                    message_log=message_bus.log_path,
                    event_log=event_bus.log_path,
                    working_memory=memory.working_path,
                )
            event_bus.emit(
                "AgentResponded",
                workflow_id=workflow.id,
                actor=receiver.to_dict(),
                subject={"type": "artifact", "id": step.output, "name": step.output},
                summary=f"Recorded {step_status} output {step.output}.",
                data={"step_id": step.id, "message_id": message.id, "provider_result": provider_result},
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

    def _maybe_invoke_provider(
        self,
        *,
        message,
        step_id: str,
        agent_id: str,
        event_bus: EventBus,
        message_bus: MessageBus,
        workflow_id: str,
        workflow_run_id: str,
    ) -> dict[str, object] | None:
        providers_config = self.config.files.get("providers", {})
        routing = providers_config.get("routing", {}) if isinstance(providers_config, dict) else {}
        if not isinstance(routing, dict) or routing.get("invoke_provider_during_kernel_run") is not True:
            return None
        provider_name = self._select_provider_name(agent_id, routing)
        provider_result = self._invoke_selected_provider(
            provider_name=provider_name,
            message=message,
            step_id=step_id,
            agent_id=agent_id,
            event_bus=event_bus,
            message_bus=message_bus,
            workflow_id=workflow_id,
            workflow_run_id=workflow_run_id,
            fallback=False,
        )
        if provider_result.get("status") != "failed":
            return provider_result
        if routing.get("allow_fallback") is not True:
            return provider_result
        fallback_provider = routing.get("fallback_provider", "null")
        if not isinstance(fallback_provider, str):
            fallback_provider = "null"
        fallback_result = self._invoke_selected_provider(
            provider_name=fallback_provider,
            message=message,
            step_id=step_id,
            agent_id=agent_id,
            event_bus=event_bus,
            message_bus=message_bus,
            workflow_id=workflow_id,
            workflow_run_id=workflow_run_id,
            fallback=True,
            fallback_from=provider_name,
        )
        return fallback_result

    def _select_provider_name(self, agent_id: str, routing: dict[str, object]) -> str:
        per_agent = routing.get("per_agent_provider", {})
        if isinstance(per_agent, dict):
            override = per_agent.get(agent_id)
            if isinstance(override, str):
                return override
        default_provider = routing.get("default_provider", "echo")
        return default_provider if isinstance(default_provider, str) else "echo"

    def _invoke_selected_provider(
        self,
        *,
        provider_name: str,
        message,
        step_id: str,
        agent_id: str,
        event_bus: EventBus,
        message_bus: MessageBus,
        workflow_id: str,
        workflow_run_id: str,
        fallback: bool,
        fallback_from: str | None = None,
    ) -> dict[str, object]:
        definition = self.provider_registry.get_definition(provider_name)
        if not definition.enabled:
            result = self._failed_provider_result(provider_name, definition.model, message.id, "Provider is disabled", fallback)
            self._record_provider_failure(event_bus, message_bus, workflow_id, workflow_run_id, step_id, agent_id, message.id, result)
            return result
        event_bus.emit(
            "ProviderSelected",
            workflow_id=workflow_id,
            actor={"type": "system", "id": "kernel", "name": "Constellation Kernel"},
            subject={"type": "provider", "id": provider_name, "name": provider_name},
            summary=f"Selected provider {provider_name} for agent {agent_id}.",
            data={"step_id": step_id, "agent_id": agent_id, "fallback": fallback},
            correlation_id=workflow_run_id,
            causation_id=message.id,
        )
        try:
            result = self.provider_registry.get(provider_name).generate(message).to_dict()
        except ProviderError as exc:
            result = self._failed_provider_result(provider_name, definition.model, message.id, str(exc), fallback)
            self._record_provider_failure(event_bus, message_bus, workflow_id, workflow_run_id, step_id, agent_id, message.id, result)
            return result
        if isinstance(result.get("metadata"), dict):
            result["metadata"]["fallback"] = fallback
            result["metadata"]["agent_id"] = agent_id
            result["metadata"]["step_id"] = step_id
            if fallback_from:
                result["metadata"]["fallback_from"] = fallback_from
        message_bus.persist_provider_result(
            message_id=message.id,
            step_id=step_id,
            agent_id=agent_id,
            provider_result=result,
        )
        event_bus.emit(
            "ProviderRequestCompleted",
            workflow_id=workflow_id,
            actor={"type": "provider", "id": provider_name, "name": provider_name},
            subject={"type": "message", "id": message.id, "name": step_id},
            summary=f"Provider {provider_name} completed step {step_id}.",
            data={"provider_result": result},
            correlation_id=workflow_run_id,
            causation_id=message.id,
        )
        return result

    def _record_provider_failure(
        self,
        event_bus: EventBus,
        message_bus: MessageBus,
        workflow_id: str,
        workflow_run_id: str,
        step_id: str,
        agent_id: str,
        message_id: str,
        result: dict[str, object],
    ) -> None:
        message_bus.persist_provider_result(
            message_id=message_id,
            step_id=step_id,
            agent_id=agent_id,
            provider_result=result,
        )
        event_bus.emit(
            "ProviderFailed",
            workflow_id=workflow_id,
            actor={"type": "provider", "id": str(result["provider_name"]), "name": str(result["provider_name"])},
            subject={"type": "message", "id": message_id, "name": step_id},
            summary=f"Provider {result['provider_name']} failed step {step_id}.",
            data={"provider_result": result},
            correlation_id=workflow_run_id,
            causation_id=message_id,
            severity="error",
        )

    @staticmethod
    def _failed_provider_result(provider_name: str, model: str, message_id: str, error: str, fallback: bool) -> dict[str, object]:
        from .models import utc_now_iso

        return {
            "provider_name": provider_name,
            "model": model,
            "input_message_id": message_id,
            "output_text": "",
            "status": "failed",
            "error": error,
            "metadata": {"fallback": fallback},
            "created_at": utc_now_iso(),
        }

    @staticmethod
    def _gate_after_step(workflow: WorkflowDefinition, step_id: str):
        for gate in workflow.approval_gates:
            if gate.after_step == step_id:
                return gate
        return None
