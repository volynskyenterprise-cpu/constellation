from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from constellation.cli import main
from constellation.kernel import ConstellationKernel
from constellation.models import Message, Party
from constellation.providers import ProviderError, ProviderRegistry


ROOT = Path(__file__).resolve().parents[1]


class ProviderTests(unittest.TestCase):
    def test_provider_registry_loads_configured_providers(self) -> None:
        registry = ProviderRegistry.load_from(ROOT / "config" / "providers.yaml")

        provider_names = [provider.id for provider in registry.all()]
        self.assertIn("echo", provider_names)
        self.assertIn("null", provider_names)
        self.assertIn("failure", provider_names)

    def test_enabled_and_disabled_providers(self) -> None:
        registry = ProviderRegistry.load_from(ROOT / "config" / "providers.yaml")

        enabled = {provider.id for provider in registry.enabled()}
        self.assertIn("echo", enabled)
        self.assertIn("null", enabled)
        self.assertNotIn("failure", enabled)

    def test_echo_provider_response_is_deterministic(self) -> None:
        provider = ProviderRegistry.load_from(ROOT / "config" / "providers.yaml").get("echo")
        message = _message("msg_echo")

        result = provider.generate(message)

        self.assertEqual(result.provider_name, "echo")
        self.assertEqual(result.model, "echo-v0")
        self.assertEqual(result.input_message_id, "msg_echo")
        self.assertEqual(result.output_text, "echo:msg_echo:frame_objective")
        self.assertEqual(result.status, "completed")
        self.assertIsNone(result.error)

    def test_null_provider_response_is_deterministic_noop(self) -> None:
        provider = ProviderRegistry.load_from(ROOT / "config" / "providers.yaml").get("null")

        result = provider.generate(_message("msg_null"))

        self.assertEqual(result.provider_name, "null")
        self.assertEqual(result.model, "null-v0")
        self.assertEqual(result.input_message_id, "msg_null")
        self.assertEqual(result.output_text, "")
        self.assertEqual(result.status, "completed")

    def test_failure_provider_raises_controlled_error(self) -> None:
        provider = ProviderRegistry.load_from(ROOT / "config" / "providers.yaml").get("failure")

        with self.assertRaises(ProviderError):
            provider.generate(_message("msg_failure"))

    def test_provider_cli_output(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            output = io.StringIO()

            with redirect_stdout(output):
                exit_code = main(["providers", "--root", str(temp_root), "list"])

            self.assertEqual(exit_code, 0)
            text = output.getvalue()
            self.assertIn("echo enabled=True", text)
            self.assertIn("failure enabled=False", text)

    def test_kernel_behavior_remains_unchanged_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            result = ConstellationKernel(temp_root).run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))
            memory = json.loads(result.working_memory.read_text(encoding="utf-8"))

            artifacts = memory["artifacts"]
            self.assertIsNone(artifacts["objective_brief"]["provider_result"])

    def test_provider_enabled_agent_output_uses_echo(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            _write_provider_config(temp_root, invoke=True, default_provider="echo")

            result = ConstellationKernel(temp_root).run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))
            memory = json.loads(result.working_memory.read_text(encoding="utf-8"))
            events = _jsonl(result.event_log)
            messages = _jsonl(result.message_log)

            artifact = memory["artifacts"]["objective_brief"]
            provider_result = artifact["provider_result"]
            self.assertEqual(artifact["status"], "provider_backed")
            self.assertEqual(provider_result["provider_name"], "echo")
            self.assertTrue(provider_result["output_text"].startswith("echo:"))
            self.assertIn("ProviderRequestCompleted", [event["type"] for event in events])
            self.assertTrue(any(record.get("record_type") == "provider_result" for record in messages))

    def test_per_agent_provider_override(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            _write_provider_config(
                temp_root,
                invoke=True,
                default_provider="echo",
                per_agent={"qa_lead": "null"},
            )

            result = ConstellationKernel(temp_root).run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))
            memory = json.loads(result.working_memory.read_text(encoding="utf-8"))

            self.assertEqual(memory["artifacts"]["objective_brief"]["provider_result"]["provider_name"], "echo")
            self.assertEqual(memory["artifacts"]["validation_summary"]["provider_result"]["provider_name"], "null")
            self.assertEqual(memory["artifacts"]["validation_summary"]["provider_result"]["output_text"], "")

    def test_provider_failure_marks_workflow_failed_without_fallback(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            _write_provider_config(temp_root, invoke=True, default_provider="failure", failure_enabled=True)

            result = ConstellationKernel(temp_root).run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))
            memory = json.loads(result.working_memory.read_text(encoding="utf-8"))
            events = _jsonl(result.event_log)

            self.assertEqual(result.status, "failed")
            self.assertEqual(memory["artifacts"]["objective_brief"]["status"], "failed")
            self.assertEqual(memory["artifacts"]["objective_brief"]["provider_result"]["status"], "failed")
            self.assertIn("ProviderFailed", [event["type"] for event in events])

    def test_provider_failure_can_fallback_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            _write_provider_config(
                temp_root,
                invoke=True,
                default_provider="failure",
                failure_enabled=True,
                allow_fallback=True,
                fallback_provider="null",
            )

            result = ConstellationKernel(temp_root).run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))
            memory = json.loads(result.working_memory.read_text(encoding="utf-8"))
            events = _jsonl(result.event_log)

            self.assertEqual(result.status, "needs_approval")
            provider_result = memory["artifacts"]["objective_brief"]["provider_result"]
            self.assertEqual(provider_result["provider_name"], "null")
            self.assertEqual(provider_result["status"], "completed")
            self.assertEqual(provider_result["metadata"]["fallback_from"], "failure")
            self.assertIn("ProviderFailed", [event["type"] for event in events])


def _message(message_id: str) -> Message:
    return Message(
        id=message_id,
        timestamp="2026-07-01T09:00:00-07:00",
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


def _copy_runtime_tree(temp_root: Path) -> Path:
    for name in ["agents", "workflows", "config", "memory", "logs", "approvals"]:
        shutil.copytree(ROOT / name, temp_root / name)
    for path in (temp_root / "approvals" / "pending").glob("*.json"):
        path.unlink()
    for path in (temp_root / "approvals" / "accepted").glob("*.json"):
        path.unlink()
    for path in (temp_root / "logs" / "runs").glob("run_*"):
        shutil.rmtree(path)
    for path in (temp_root / "memory" / "runs").glob("run_*-working.json"):
        path.unlink()
    return temp_root


def _write_provider_config(
    root: Path,
    *,
    invoke: bool,
    default_provider: str,
    per_agent: dict[str, str] | None = None,
    failure_enabled: bool = False,
    allow_fallback: bool = False,
    fallback_provider: str = "null",
) -> None:
    per_agent = per_agent or {}
    per_agent_lines = ["  per_agent_provider:"]
    if per_agent:
        per_agent_lines.extend([f"    {agent}: \"{provider}\"" for agent, provider in per_agent.items()])
    else:
        per_agent_lines.append("    none: none")
    content = f"""providers:
  - id: echo
    enabled: true
    role: deterministic_stub_provider
    provider_type: echo
    model: echo-v0
    capabilities:
      - reasoning
      - structured_output
  - id: "null"
    enabled: true
    role: deterministic_noop_provider
    provider_type: "null"
    model: null-v0
    capabilities:
      - reasoning
      - structured_output
  - id: failure
    enabled: {str(failure_enabled).lower()}
    role: deterministic_failure_provider
    provider_type: failure
    model: failure-v0
    capabilities:
      - reasoning
      - structured_output

routing:
  invoke_provider_during_kernel_run: {str(invoke).lower()}
  default_provider: {default_provider}
{chr(10).join(per_agent_lines)}
  allow_fallback: {str(allow_fallback).lower()}
  fallback_provider: "{fallback_provider}"
"""
    (root / "config" / "providers.yaml").write_text(content, encoding="utf-8")


def _jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


if __name__ == "__main__":
    unittest.main()
