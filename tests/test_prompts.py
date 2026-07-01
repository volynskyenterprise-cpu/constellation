from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from constellation.cli import main
from constellation.crew import CrewError
from constellation.kernel import ConstellationKernel
from constellation.prompts import PromptUnavailable
from constellation.state import WorkflowStateStore


ROOT = Path(__file__).resolve().parents[1]


class PromptAssemblyTests(unittest.TestCase):
    def test_prompt_package_assembly_for_ceo_step(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            kernel = ConstellationKernel(temp_root)
            result = kernel.run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))

            prompt = kernel.show_prompt(result.workflow_run_id, "frame_request")

            self.assertEqual(prompt.step_id, "frame_request")
            self.assertEqual(prompt.agent_id, "ceo")
            self.assertEqual(prompt.crew_role, "ceo")
            self.assertIn("CEO Profile", prompt.system_prompt)
            self.assertIn("Clarify the objective", prompt.task_prompt)
            self.assertIn("crew_profile", prompt.context_sections)
            self.assertTrue((temp_root / "logs" / "runs" / result.workflow_run_id / "prompts" / f"{prompt.prompt_id}.json").exists())

    def test_prompt_package_assembly_for_research_lead_current_step(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            kernel = ConstellationKernel(temp_root)
            result = kernel.run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))
            state = WorkflowStateStore(temp_root).load(result.workflow_run_id)
            WorkflowStateStore(temp_root).save(
                workflow_run_id=state.workflow_run_id,
                workflow_id=state.workflow_id,
                workflow_path=state.workflow_path,
                status="running",
                next_step_index=1,
                pending_approval_id=None,
            )

            prompt = kernel.show_prompt(result.workflow_run_id)

            self.assertEqual(prompt.step_id, "research_evidence")
            self.assertEqual(prompt.agent_id, "research_lead")
            self.assertEqual(prompt.crew_role, "research-lead")
            self.assertIn("Research Lead Profile", prompt.system_prompt)
            self.assertIn("Gather and summarize evidence", prompt.task_prompt)

    def test_paused_approval_run_has_no_current_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            result = ConstellationKernel(temp_root).run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))

            with self.assertRaises(PromptUnavailable):
                ConstellationKernel(temp_root).show_prompt(result.workflow_run_id)

    def test_missing_crew_doctrine_error_handling(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            shutil.rmtree(temp_root / "crew" / "ceo")
            result = ConstellationKernel(temp_root).run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))

            with self.assertRaises(CrewError):
                ConstellationKernel(temp_root).show_prompt(result.workflow_run_id, "frame_request")

    def test_cli_prompt_show_outputs_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            result = ConstellationKernel(temp_root).run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))
            output = io.StringIO()

            with redirect_stdout(output):
                exit_code = main(["prompt", "--root", str(temp_root), "show", result.workflow_run_id, "--step", "frame_request"])

            self.assertEqual(exit_code, 0)
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["step_id"], "frame_request")
            self.assertEqual(payload["agent_id"], "ceo")
            self.assertIn("system_prompt", payload)

    def test_provider_receives_prompt_package_when_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            _write_provider_config(temp_root)

            result = ConstellationKernel(temp_root).run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))
            memory = json.loads(result.working_memory.read_text(encoding="utf-8"))
            messages = _jsonl(result.message_log)
            events = _jsonl(result.event_log)
            provider_result = memory["artifacts"]["objective_brief"]["provider_result"]

            self.assertEqual(memory["artifacts"]["objective_brief"]["status"], "provider_backed")
            self.assertIn("prompt=", provider_result["output_text"])
            self.assertIn("role=ceo", provider_result["output_text"])
            self.assertEqual(provider_result["metadata"]["received_prompt_package"], True)
            self.assertIn("prompt_package_id", provider_result["metadata"])
            self.assertTrue(any(record.get("record_type") == "prompt_package" for record in messages))
            self.assertTrue(any(event.get("data", {}).get("prompt_package_id") for event in events))

    def test_default_behavior_remains_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))

            result = ConstellationKernel(temp_root).run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))
            memory = json.loads(result.working_memory.read_text(encoding="utf-8"))

            self.assertEqual(memory["artifacts"]["objective_brief"]["status"], "placeholder")
            self.assertIsNone(memory["artifacts"]["objective_brief"]["provider_result"])
            self.assertIsNone(memory["artifacts"]["objective_brief"]["prompt_package_id"])


def _copy_runtime_tree(temp_root: Path) -> Path:
    for name in ["agents", "workflows", "config", "memory", "logs", "approvals", "crew"]:
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


def _write_provider_config(root: Path) -> None:
    content = """providers:
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

routing:
  invoke_provider_during_kernel_run: true
  default_provider: echo
  per_agent_provider:
    none: none
  allow_fallback: false
  fallback_provider: "null"
"""
    (root / "config" / "providers.yaml").write_text(content, encoding="utf-8")


def _jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


if __name__ == "__main__":
    unittest.main()
