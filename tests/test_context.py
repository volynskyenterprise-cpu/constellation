from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from constellation.cli import main
from constellation.crew import CrewError, CrewLoader
from constellation.kernel import ConstellationKernel
from constellation.state import WorkflowStateStore


ROOT = Path(__file__).resolve().parents[1]


class ContextEngineTests(unittest.TestCase):
    def test_crew_doctrine_loading(self) -> None:
        doctrine = CrewLoader(ROOT).load("qa-lead")

        self.assertEqual(doctrine.role, "qa-lead")
        self.assertIn("QA Lead", doctrine.profile)
        self.assertIn("Acceptance criteria", doctrine.responsibilities)
        self.assertIn("Base Role Prompt", doctrine.prompts)

    def test_missing_crew_file_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            (temp_root / "crew" / "ceo" / "profile.md").unlink()

            with self.assertRaises(CrewError):
                CrewLoader(temp_root).load("ceo")

    def test_context_assembly_for_current_run_state(self) -> None:
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

            context = kernel.show_context(result.workflow_run_id)

            self.assertEqual(context.current_step, "research_evidence")
            self.assertEqual(context.agent_id, "research_lead")
            self.assertEqual(context.crew_role, "research-lead")
            self.assertIsNotNone(context.crew_doctrine)
            self.assertEqual(context.workflow_definition.id, "example_ceo_research_qa_docs")
            self.assertIn("default_provider", context.provider_routing_config)
            self.assertGreater(len(context.previous_messages), 0)
            self.assertGreater(len(context.recent_events), 0)

    def test_paused_run_context_includes_approval_state(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            kernel = ConstellationKernel(temp_root)
            result = kernel.run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))

            context = kernel.show_context(result.workflow_run_id)

            self.assertTrue(context.current_step.startswith("approval:"))
            self.assertIsNone(context.agent_id)
            self.assertIsNone(context.crew_role)
            self.assertIsNotNone(context.approval_state)
            self.assertEqual(context.approval_state["status"], "pending")
            self.assertEqual(context.working_memory["workflow_run_id"], result.workflow_run_id)

    def test_completed_run_context(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            kernel = ConstellationKernel(temp_root)
            result = kernel.run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))
            kernel.approve(result.approval_path.stem)
            kernel.resume_workflow(result.workflow_run_id)

            context = kernel.show_context(result.workflow_run_id)

            self.assertEqual(context.current_step, "Complete")
            self.assertIsNone(context.agent_id)
            self.assertIsNone(context.crew_doctrine)
            self.assertIsNone(context.approval_state)

    def test_cli_context_show_outputs_json(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            result = ConstellationKernel(temp_root).run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))
            output = io.StringIO()

            with redirect_stdout(output):
                exit_code = main(["context", "--root", str(temp_root), "show", result.workflow_run_id])

            self.assertEqual(exit_code, 0)
            payload = json.loads(output.getvalue())
            self.assertEqual(payload["workflow_run_id"], result.workflow_run_id)
            self.assertEqual(payload["workflow_id"], "example_ceo_research_qa_docs")
            self.assertIn("working_memory", payload)
            self.assertIn("provider_routing_config", payload)


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


if __name__ == "__main__":
    unittest.main()
