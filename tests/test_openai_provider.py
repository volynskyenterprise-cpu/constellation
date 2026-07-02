from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from constellation.models import Message, Party
from constellation.providers import OpenAIProvider, ProviderDefinition, ProviderError, ProviderRegistry


class OpenAIProviderTests(unittest.TestCase):
    def test_openai_provider_config_validation(self) -> None:
        provider = OpenAIProvider(_definition(enabled=False))

        provider.validate_config()

        with self.assertRaises(ProviderError):
            OpenAIProvider(_definition(config={"api_key_env": "", "timeout_seconds": 30, "max_output_tokens": 2000})).validate_config()
        with self.assertRaises(ProviderError):
            OpenAIProvider(_definition(config={"api_key_env": "OPENAI_API_KEY", "timeout_seconds": 0, "max_output_tokens": 2000})).validate_config()
        with self.assertRaises(ProviderError):
            OpenAIProvider(_definition(config={"api_key_env": "OPENAI_API_KEY", "timeout_seconds": 30, "max_output_tokens": 0})).validate_config()

    def test_disabled_provider_health_behavior(self) -> None:
        provider = OpenAIProvider(_definition(enabled=False))

        health = provider.health_check()

        self.assertEqual(health["status"], "disabled")
        self.assertEqual(health["detail"], "skipped")

    def test_missing_api_key_behavior(self) -> None:
        provider = OpenAIProvider(_definition(enabled=True))

        with patch.dict(os.environ, {}, clear=True):
            health = provider.health_check()
            with self.assertRaises(ProviderError):
                provider.generate(_message(), _prompt_package())

        self.assertEqual(health["status"], "missing_api_key")
        self.assertNotIn("sk-", str(health))

    def test_missing_sdk_behavior(self) -> None:
        provider = OpenAIProvider(_definition(enabled=True))

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            with patch.object(OpenAIProvider, "_client_class", side_effect=ProviderError("OpenAI Python SDK is not installed.")):
                health = provider.health_check()
                with self.assertRaises(ProviderError):
                    provider.generate(_message(), _prompt_package())

        self.assertEqual(health["status"], "missing_sdk")
        self.assertIn("SDK", health["detail"])
        self.assertNotIn("test-key", str(health))

    def test_mocked_successful_generation(self) -> None:
        provider = OpenAIProvider(_definition(enabled=True))

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            with patch.object(OpenAIProvider, "_client_class", return_value=FakeOpenAI):
                result = provider.generate(_message(), _prompt_package())

        self.assertEqual(result.provider_name, "openai")
        self.assertEqual(result.model, "gpt-test")
        self.assertEqual(result.input_message_id, "msg_openai")
        self.assertEqual(result.output_text, '{"summary":"ok"}')
        self.assertEqual(result.status, "completed")
        self.assertIsNone(result.error)
        self.assertEqual(result.metadata["provider_type"], "openai")
        self.assertEqual(result.metadata["prompt_id"], "prompt_test")
        self.assertEqual(result.metadata["response_id"], "resp_test")
        self.assertTrue(result.provider_result_id.startswith("provider_result_msg_openai_openai"))

    def test_provider_result_schema(self) -> None:
        provider = OpenAIProvider(_definition(enabled=True))

        with patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"}, clear=True):
            with patch.object(OpenAIProvider, "_client_class", return_value=FakeOpenAI):
                payload = provider.generate(_message(), _prompt_package()).to_dict()

        expected = {
            "provider_result_id",
            "provider_name",
            "model",
            "input_message_id",
            "output_text",
            "status",
            "error",
            "metadata",
            "created_at",
        }
        self.assertEqual(set(payload), expected)

    def test_existing_echo_provider_behavior_unchanged(self) -> None:
        provider = ProviderRegistry.load_from(_repo_providers_path()).get("echo")

        result = provider.generate(_message("msg_echo"))

        self.assertEqual(result.provider_name, "echo")
        self.assertEqual(result.output_text, "echo:msg_echo:frame_objective")

    def test_default_health_check_passes_with_openai_disabled(self) -> None:
        registry = ProviderRegistry.load_from(_repo_providers_path())

        health = registry.health()

        openai_health = next(item for item in health if item["provider_name"] == "openai")
        self.assertEqual(openai_health["status"], "disabled")


class FakeResponse:
    id = "resp_test"
    output_text = '{"summary":"ok"}'


class FakeResponses:
    def create(self, **kwargs):
        assert kwargs["model"] == "gpt-test"
        assert "system prompt" in kwargs["instructions"]
        assert "output_contract" in kwargs["input"]
        assert "evidence_requirements" in kwargs["input"]
        assert "uncertainty_requirements" in kwargs["input"]
        assert "context_sections" in kwargs["input"]
        assert kwargs["max_output_tokens"] == 123
        return FakeResponse()


class FakeModels:
    def retrieve(self, model: str):
        return {"id": model}


class FakeOpenAI:
    def __init__(self, *, api_key: str, timeout: int) -> None:
        assert api_key == "test-key"
        assert timeout == 7
        self.responses = FakeResponses()
        self.models = FakeModels()


def _definition(*, enabled: bool = True, config: dict[str, object] | None = None) -> ProviderDefinition:
    return ProviderDefinition(
        id="openai",
        enabled=enabled,
        role="model_provider",
        capabilities=["reasoning", "structured_output"],
        provider_type="openai",
        model="gpt-test",
        config=config
        or {
            "api_key_env": "OPENAI_API_KEY",
            "timeout_seconds": 7,
            "max_output_tokens": 123,
            "health_check_mode": "config_only",
        },
    )


def _message(message_id: str = "msg_openai") -> Message:
    return Message(
        id=message_id,
        timestamp="2026-07-02T09:00:00-07:00",
        workflow_id="workflow_test",
        sender=Party(type="workflow", id="workflow_test", name="Workflow Test"),
        receiver=Party(type="agent", id="ceo", name="CEO"),
        task={"objective": "test", "instructions": "test", "expected_output": "test"},
        context={"summary": "test"},
        assumptions=[],
        reasoning_summary="test",
        evidence=[],
        confidence="unknown",
        requested_action="frame_objective",
        status="sent",
    )


def _prompt_package() -> dict[str, object]:
    return {
        "prompt_id": "prompt_test",
        "workflow_run_id": "run_test",
        "workflow_id": "workflow_test",
        "step_id": "frame_request",
        "agent_id": "ceo",
        "crew_role": "ceo",
        "system_prompt": "system prompt",
        "task_prompt": "task prompt",
        "output_contract": {"expected_output": "objective_brief"},
        "evidence_requirements": ["cite evidence"],
        "uncertainty_requirements": ["state uncertainty"],
        "context_sections": {"working_memory": {}},
    }


def _repo_providers_path():
    from pathlib import Path

    return Path(__file__).resolve().parents[1] / "config" / "providers.yaml"


if __name__ == "__main__":
    unittest.main()
