from __future__ import annotations

from pathlib import Path

from .models import AgentDefinition
from .simple_yaml import load_yaml


class RegistryError(ValueError):
    pass


REQUIRED_AGENT_FIELDS = {
    "id",
    "name",
    "version",
    "status",
    "mission",
    "authority",
    "methods",
    "inputs",
    "outputs",
    "escalation_triggers",
    "quality_bar",
}


class AgentRegistry:
    def __init__(self) -> None:
        self._agents: dict[str, AgentDefinition] = {}

    @classmethod
    def load_from(cls, agents_dir: Path) -> "AgentRegistry":
        registry = cls()
        for path in sorted(agents_dir.glob("*.yaml")):
            registry.register(load_agent(path))
        return registry

    def register(self, agent: AgentDefinition) -> None:
        if agent.id in self._agents:
            raise RegistryError(f"Duplicate agent id: {agent.id}")
        self._agents[agent.id] = agent

    def get(self, agent_id: str) -> AgentDefinition:
        try:
            return self._agents[agent_id]
        except KeyError as exc:
            raise RegistryError(f"Unknown agent id: {agent_id}") from exc

    def has(self, agent_id: str) -> bool:
        return agent_id in self._agents

    def all(self) -> list[AgentDefinition]:
        return list(self._agents.values())


def load_agent(path: Path) -> AgentDefinition:
    data = load_yaml(path)
    missing = REQUIRED_AGENT_FIELDS - set(data)
    if missing:
        raise RegistryError(f"{path} missing required fields: {', '.join(sorted(missing))}")
    return AgentDefinition(
        id=_require_str(data, "id", path),
        name=_require_str(data, "name", path),
        version=_require_str(data, "version", path),
        status=_require_str(data, "status", path),
        mission=_require_str(data, "mission", path),
        authority=_require_dict(data, "authority", path),
        methods=_require_str_list(data, "methods", path),
        inputs=_require_dict(data, "inputs", path),
        outputs=_require_str_list(data, "outputs", path),
        escalation_triggers=_require_str_list(data, "escalation_triggers", path),
        quality_bar=_require_str_list(data, "quality_bar", path),
        source_path=str(path),
    )


def _require_str(data: dict[str, object], key: str, path: Path) -> str:
    value = data[key]
    if not isinstance(value, str):
        raise RegistryError(f"{path} field {key} must be a string")
    return value


def _require_dict(data: dict[str, object], key: str, path: Path) -> dict[str, object]:
    value = data[key]
    if not isinstance(value, dict):
        raise RegistryError(f"{path} field {key} must be a mapping")
    return value


def _require_str_list(data: dict[str, object], key: str, path: Path) -> list[str]:
    value = data[key]
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise RegistryError(f"{path} field {key} must be a list of strings")
    return value
