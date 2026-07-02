from __future__ import annotations

import json
import os
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


class OpenAIProvider(BaseProvider):
    def validate_config(self) -> None:
        super().validate_config()
        api_key_env = self.definition.config.get("api_key_env", "OPENAI_API_KEY")
        if not isinstance(api_key_env, str) or not api_key_env:
            raise ProviderError("OpenAI provider config api_key_env must be a non-empty string")
        if _positive_int(self.definition.config.get("timeout_seconds", 30)) is None:
            raise ProviderError("OpenAI provider config timeout_seconds must be a positive integer")
        if _positive_int(self.definition.config.get("max_output_tokens", 2000)) is None:
            raise ProviderError("OpenAI provider config max_output_tokens must be a positive integer")

    def generate(self, message: Message, prompt_package: JsonMap | None = None) -> ProviderResult:
        api_key = self._api_key()
        if not api_key:
            raise ProviderError(f"OpenAI API key is missing from environment variable {self._api_key_env()}")
        client_class = self._client_class()
        request = self._provider_request(message, prompt_package)
        try:
            client = client_class(api_key=api_key, timeout=self._timeout_seconds())
            response = client.responses.create(
                model=self.definition.model,
                instructions=request["system_prompt"],
                input=request["input"],
                max_output_tokens=self._max_output_tokens(),
            )
        except Exception as exc:
            raise ProviderError(f"OpenAI provider request failed: {exc}") from exc
        return self._result(
            message,
            output_text=_response_text(response),
            metadata={
                "provider_type": "openai",
                "model": self.definition.model,
                "received_prompt_package": prompt_package is not None,
                "prompt_id": prompt_package.get("prompt_id") if prompt_package else None,
                "request_shape": "responses.create",
                "response_id": getattr(response, "id", None),
            },
        )

    def health_check(self) -> dict[str, Any]:
        if not self.definition.enabled:
            return {"provider_name": self.name, "status": "disabled", "enabled": False, "detail": "skipped"}
        if not self._api_key():
            return {
                "provider_name": self.name,
                "status": "missing_api_key",
                "enabled": True,
                "detail": f"Set {self._api_key_env()} to enable OpenAI requests.",
            }
        try:
            client_class = self._client_class()
        except ProviderError as exc:
            return {"provider_name": self.name, "status": "missing_sdk", "enabled": True, "detail": str(exc)}
        if self.definition.config.get("health_check_mode") == "api":
            try:
                client = client_class(api_key=self._api_key(), timeout=self._timeout_seconds())
                client.models.retrieve(self.definition.model)
            except Exception as exc:
                return {"provider_name": self.name, "status": "api_unavailable", "enabled": True, "detail": str(exc)}
            return {"provider_name": self.name, "status": "ok", "enabled": True, "detail": "API model probe succeeded."}
        return {
            "provider_name": self.name,
            "status": "configured",
            "enabled": True,
            "detail": "SDK and API key are available; external health probe skipped.",
        }

    def _provider_request(self, message: Message, prompt_package: JsonMap | None) -> JsonMap:
        if prompt_package is None:
            prompt_package = {
                "system_prompt": "You are a Constellation provider executing a standardized agent message.",
                "task_prompt": json.dumps(message.task, sort_keys=True),
                "context_sections": message.context,
                "output_contract": {"expected_output": message.task.get("expected_output")},
                "evidence_requirements": message.evidence,
                "uncertainty_requirements": ["State uncertainty explicitly."],
            }
        artifact_fields = [
            "artifact_id",
            "workflow_run_id",
            "workflow_id",
            "step_id",
            "agent_id",
            "crew_role",
            "artifact_type",
            "title",
            "summary",
            "findings",
            "recommendations",
            "risks",
            "assumptions",
            "evidence_used",
            "next_steps",
            "confidence",
            "status",
            "provider_result_id",
            "prompt_package_id",
            "created_at",
        ]
        request = {
            "system_prompt": prompt_package.get("system_prompt", ""),
            "task_prompt": prompt_package.get("task_prompt", ""),
            "output_contract": prompt_package.get("output_contract", {}),
            "evidence_requirements": prompt_package.get("evidence_requirements", []),
            "uncertainty_requirements": prompt_package.get("uncertainty_requirements", []),
            "context_sections": prompt_package.get("context_sections", {}),
            "artifact_schema": {
                "format": "json_object",
                "required_fields": artifact_fields,
                "instruction": "Return JSON-like structured output matching these AgentArtifact fields where possible.",
            },
        }
        return {
            "system_prompt": str(request["system_prompt"]),
            "input": json.dumps(request, indent=2, sort_keys=True, default=str),
        }

    def _api_key_env(self) -> str:
        return str(self.definition.config.get("api_key_env", "OPENAI_API_KEY"))

    def _api_key(self) -> str | None:
        return os.environ.get(self._api_key_env())

    def _timeout_seconds(self) -> int:
        value = _positive_int(self.definition.config.get("timeout_seconds", 30))
        return value if value is not None else 30

    def _max_output_tokens(self) -> int:
        value = _positive_int(self.definition.config.get("max_output_tokens", 2000))
        return value if value is not None else 2000

    @staticmethod
    def _client_class():
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ProviderError("OpenAI Python SDK is not installed. Install with: pip install 'constellation-kernel[openai]'") from exc
        return OpenAI


PROVIDER_TYPES = {
    "echo": EchoProvider,
    "null": NullProvider,
    "failure": FailureProvider,
    "openai": OpenAIProvider,
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


def _response_text(response: Any) -> str:
    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str):
        return output_text
    if hasattr(response, "model_dump"):
        return json.dumps(response.model_dump(), sort_keys=True, default=str)
    if hasattr(response, "to_dict"):
        return json.dumps(response.to_dict(), sort_keys=True, default=str)
    return str(response)


def _positive_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value if value > 0 else None
    if isinstance(value, str) and value.isdigit():
        parsed = int(value)
        return parsed if parsed > 0 else None
    return None
