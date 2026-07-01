from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator, Protocol

from .models import JsonMap, Message, utc_now_iso
from .simple_yaml import load_yaml


class ProviderError(RuntimeError):
    pass


@dataclass(frozen=True)
class ProviderDefinition:
    id: str
    enabled: bool
    role: str
    capabilities: list[str]
    provider_type: str
    model: str
    config: dict[str, Any]


@dataclass(frozen=True)
class ProviderResult:
    provider_result_id: str
    provider_name: str
    model: str
    input_message_id: str
    output_text: str
    status: str
    error: str | None
    metadata: dict[str, Any]
    created_at: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "provider_result_id": self.provider_result_id,
            "provider_name": self.provider_name,
            "model": self.model,
            "input_message_id": self.input_message_id,
            "output_text": self.output_text,
            "status": self.status,
            "error": self.error,
            "metadata": self.metadata,
            "created_at": self.created_at,
        }


class Provider(Protocol):
    @property
    def name(self) -> str:
        ...

    @property
    def capabilities(self) -> list[str]:
        ...

    def validate_config(self) -> None:
        ...

    def generate(self, message: Message, prompt_package: JsonMap | None = None) -> ProviderResult:
        ...

    def stream(self, message: Message, prompt_package: JsonMap | None = None) -> Iterator[str]:
        ...

    def health_check(self) -> dict[str, Any]:
        ...


class BaseProvider:
    def __init__(self, definition: ProviderDefinition) -> None:
        self.definition = definition

    @property
    def name(self) -> str:
        return self.definition.id

    @property
    def capabilities(self) -> list[str]:
        return self.definition.capabilities

    def validate_config(self) -> None:
        if not self.definition.id:
            raise ProviderError("Provider id is required")
        if not self.definition.model:
            raise ProviderError(f"Provider model is required: {self.definition.id}")

    def stream(self, message: Message, prompt_package: JsonMap | None = None) -> Iterator[str]:
        yield self.generate(message, prompt_package).output_text

    def health_check(self) -> dict[str, Any]:
        return {"provider_name": self.name, "status": "ok", "enabled": self.definition.enabled}

    def _result(
        self,
        message: Message,
        *,
        output_text: str,
        status: str = "completed",
        error: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ProviderResult:
        return ProviderResult(
            provider_result_id=f"provider_result_{message.id}_{self.name}",
            provider_name=self.name,
            model=self.definition.model,
            input_message_id=message.id,
            output_text=output_text,
            status=status,
            error=error,
            metadata=metadata or {},
            created_at=utc_now_iso(),
        )


class EchoProvider(BaseProvider):
    def generate(self, message: Message, prompt_package: JsonMap | None = None) -> ProviderResult:
        if prompt_package is not None:
            output_text = (
                f"echo:{message.id}:{message.requested_action}:"
                f"prompt={prompt_package.get('prompt_id')}:"
                f"role={prompt_package.get('crew_role')}:"
                f"step={prompt_package.get('step_id')}"
            )
            metadata = {
                "stub": "echo",
                "deterministic": True,
                "received_prompt_package": True,
                "prompt_id": prompt_package.get("prompt_id"),
                "crew_role": prompt_package.get("crew_role"),
                "step_id": prompt_package.get("step_id"),
            }
            return self._result(message, output_text=output_text, metadata=metadata)
        return self._result(
            message,
            output_text=f"echo:{message.id}:{message.requested_action}",
            metadata={"stub": "echo", "deterministic": True},
        )


class NullProvider(BaseProvider):
    def generate(self, message: Message, prompt_package: JsonMap | None = None) -> ProviderResult:
        return self._result(
            message,
            output_text="",
            status="completed",
            metadata={
                "stub": "null",
                "deterministic": True,
                "received_prompt_package": prompt_package is not None,
                "prompt_id": prompt_package.get("prompt_id") if prompt_package else None,
            },
        )


class FailureProvider(BaseProvider):
    def generate(self, message: Message, prompt_package: JsonMap | None = None) -> ProviderResult:
        raise ProviderError(f"FailureProvider intentional failure for message {message.id}")

    def health_check(self) -> dict[str, Any]:
        return {"provider_name": self.name, "status": "failing", "enabled": self.definition.enabled}


PROVIDER_TYPES = {
    "echo": EchoProvider,
    "null": NullProvider,
    "failure": FailureProvider,
}


class ProviderRegistry:
    def __init__(self) -> None:
        self._definitions: dict[str, ProviderDefinition] = {}
        self._providers: dict[str, Provider] = {}

    @classmethod
    def load_from(cls, config_path: Path) -> "ProviderRegistry":
        data = load_yaml(config_path)
        providers = data.get("providers")
        if not isinstance(providers, list):
            raise ProviderError(f"{config_path} must define a providers list")
        registry = cls()
        for item in providers:
            if not isinstance(item, dict):
                raise ProviderError(f"{config_path} provider entries must be mappings")
            definition = _parse_definition(item, config_path)
            registry.register(definition)
        return registry

    def register(self, definition: ProviderDefinition) -> None:
        if definition.id in self._definitions:
            raise ProviderError(f"Duplicate provider id: {definition.id}")
        provider_class = PROVIDER_TYPES.get(definition.provider_type, NullProvider)
        provider = provider_class(definition)
        provider.validate_config()
        self._definitions[definition.id] = definition
        self._providers[definition.id] = provider

    def all(self) -> list[ProviderDefinition]:
        return list(self._definitions.values())

    def enabled(self) -> list[ProviderDefinition]:
        return [provider for provider in self._definitions.values() if provider.enabled]

    def get(self, provider_name: str) -> Provider:
        try:
            return self._providers[provider_name]
        except KeyError as exc:
            raise ProviderError(f"Unknown provider: {provider_name}") from exc

    def get_definition(self, provider_name: str) -> ProviderDefinition:
        try:
            return self._definitions[provider_name]
        except KeyError as exc:
            raise ProviderError(f"Unknown provider: {provider_name}") from exc

    def is_enabled(self, provider_name: str) -> bool:
        return self.get_definition(provider_name).enabled

    def health(self) -> list[dict[str, Any]]:
        results = []
        for provider in self._providers.values():
            results.append(provider.health_check())
        return results


def _parse_definition(data: dict[str, Any], path: Path) -> ProviderDefinition:
    for field in ["id", "enabled", "role", "capabilities"]:
        if field not in data:
            raise ProviderError(f"{path} provider missing required field: {field}")
    provider_id = _string(data["id"], "id", path)
    provider_type = _string(data.get("provider_type", provider_id), "provider_type", path)
    model = _string(data.get("model", f"{provider_id}-stub"), "model", path)
    capabilities = data["capabilities"]
    if not isinstance(capabilities, list) or not all(isinstance(item, str) for item in capabilities):
        raise ProviderError(f"{path} capabilities must be a list of strings")
    enabled = data["enabled"]
    if not isinstance(enabled, bool):
        raise ProviderError(f"{path} enabled must be a boolean")
    config = data.get("config", {})
    if config is None:
        config = {}
    if not isinstance(config, dict):
        raise ProviderError(f"{path} config must be a mapping")
    return ProviderDefinition(
        id=provider_id,
        enabled=enabled,
        role=_string(data["role"], "role", path),
        capabilities=capabilities,
        provider_type=provider_type,
        model=model,
        config=config,
    )


def _string(value: Any, field: str, path: Path) -> str:
    if not isinstance(value, str):
        raise ProviderError(f"{path} provider field {field} must be a string")
    return value
