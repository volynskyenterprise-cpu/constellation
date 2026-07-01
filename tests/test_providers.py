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


if __name__ == "__main__":
    unittest.main()
