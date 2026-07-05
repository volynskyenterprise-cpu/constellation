from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .providers import ProviderRegistry
from .registry import AgentRegistry
from .simple_yaml import load_yaml
from .validation import CrewValidator
from .workflows import WorkflowLoader


REQUIRED_CONFIG_FILES = [
    "agents.yaml",
    "constellation.yaml",
    "policies.yaml",
    "providers.yaml",
    "workflows.yaml",
]

RUNTIME_DIRECTORIES = [
    "logs",
    "logs/runs",
    "memory",
    "memory/runs",
    "memory/evidence",
    "approvals",
    "approvals/pending",
    "approvals/accepted",
    "archive",
    "archive/runs",
]


@dataclass(frozen=True)
class HealthCheck:
    name: str
    status: str
    message: str
    details: dict[str, object]

    @property
    def ok(self) -> bool:
        return self.status in {"ok", "warn"}

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "status": self.status,
            "message": self.message,
            "details": self.details,
        }


@dataclass(frozen=True)
class HealthReport:
    status: str
    checks: list[HealthCheck]

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    def to_dict(self) -> dict[str, object]:
        return {"status": self.status, "checks": [check.to_dict() for check in self.checks]}


class SystemHealthChecker:
    def __init__(self, root: Path) -> None:
        self.root = root

    def check(self) -> HealthReport:
        checks = [
            self._run_check("constitution", self._check_constitution),
            self._run_check("config", self._check_config),
            self._run_check("agents", self._check_agents),
            self._run_check("workflows", self._check_workflows),
            self._run_check("crew", self._check_crew),
            self._run_check("providers", self._check_providers),
            self._run_check("runtime_directories", self._check_runtime_directories),
            self._run_check("provider_execution_default", self._check_provider_execution_default),
        ]
        failed = any(check.status == "failed" for check in checks)
        return HealthReport("failed" if failed else "ok", checks)

    def _run_check(self, name: str, callback: Callable[[], HealthCheck]) -> HealthCheck:
        try:
            return callback()
        except Exception as exc:
            return HealthCheck(name, "failed", str(exc), {})

    def _check_constitution(self) -> HealthCheck:
        path = self.root / "constitution"
        if not path.exists() or not path.is_dir():
            return HealthCheck("constitution", "failed", "Constitution folder is missing.", {"path": str(path)})
        return HealthCheck("constitution", "ok", "Constitution folder exists.", {"path": str(path)})

    def _check_config(self) -> HealthCheck:
        missing = [name for name in REQUIRED_CONFIG_FILES if not (self.root / "config" / name).exists()]
        if missing:
            return HealthCheck("config", "failed", f"Missing required config files: {', '.join(missing)}", {"missing": missing})
        return HealthCheck("config", "ok", "Required config files exist.", {"files": REQUIRED_CONFIG_FILES})

    def _check_agents(self) -> HealthCheck:
        registry = AgentRegistry.load_from(self.root / "agents")
        agents = [agent.id for agent in registry.all()]
        if not agents:
            return HealthCheck("agents", "failed", "No agents loaded.", {})
        return HealthCheck("agents", "ok", f"Loaded {len(agents)} agents.", {"agents": agents})

    def _check_workflows(self) -> HealthCheck:
        registry = AgentRegistry.load_from(self.root / "agents")
        loader = WorkflowLoader(registry)
        workflow_paths = sorted((self.root / "workflows").rglob("*.yaml"))
        if not workflow_paths:
            return HealthCheck("workflows", "failed", "No workflow YAML files found.", {})
        workflow_ids = []
        for path in workflow_paths:
            workflow_ids.append(loader.load(path).id)
        return HealthCheck("workflows", "ok", f"Loaded {len(workflow_ids)} workflows.", {"workflows": workflow_ids})

    def _check_crew(self) -> HealthCheck:
        report = CrewValidator(self.root).validate()
        if not report.ok:
            return HealthCheck("crew", "failed", "Crew validation failed.", {"issues": [issue.to_dict() for issue in report.issues]})
        return HealthCheck("crew", "ok", "Crew validation passed.", {"checked_count": len(report.checked)})

    def _check_providers(self) -> HealthCheck:
        registry = ProviderRegistry.load_from(self.root / "config" / "providers.yaml")
        providers = [provider.id for provider in registry.all()]
        if not providers:
            return HealthCheck("providers", "failed", "No providers loaded.", {})
        return HealthCheck("providers", "ok", f"Loaded {len(providers)} providers.", {"providers": providers})

    def _check_runtime_directories(self) -> HealthCheck:
        created: list[str] = []
        for directory in RUNTIME_DIRECTORIES:
            path = self.root / directory
            if not path.exists():
                path.mkdir(parents=True, exist_ok=True)
                created.append(directory)
            if not path.is_dir():
                return HealthCheck("runtime_directories", "failed", f"Runtime path is not a directory: {directory}", {"path": str(path)})
        return HealthCheck("runtime_directories", "ok", "Runtime directories exist or were created.", {"created": created})

    def _check_provider_execution_default(self) -> HealthCheck:
        data = load_yaml(self.root / "config" / "providers.yaml")
        routing = data.get("routing", {})
        invoke = routing.get("invoke_provider_during_kernel_run") if isinstance(routing, dict) else None
        if invoke is True:
            return HealthCheck(
                "provider_execution_default",
                "warn",
                "Provider execution is explicitly enabled.",
                {"invoke_provider_during_kernel_run": True},
            )
        return HealthCheck(
            "provider_execution_default",
            "ok",
            "Provider execution is disabled by default.",
            {"invoke_provider_during_kernel_run": invoke},
        )
