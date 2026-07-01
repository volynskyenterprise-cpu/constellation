from __future__ import annotations

import json
import shutil
import tempfile
import unittest
from pathlib import Path

from constellation.kernel import ConstellationKernel
from constellation.state import WorkflowStateError, WorkflowStateStore


ROOT = Path(__file__).resolve().parents[1]


class KernelRunTests(unittest.TestCase):
    def test_example_workflow_runs_until_approval_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))

            result = ConstellationKernel(temp_root).run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))

            self.assertEqual(result.workflow_id, "example_ceo_research_qa_docs")
            self.assertEqual(result.status, "needs_approval")
            self.assertIsNotNone(result.approval_path)
            self.assertTrue(result.message_log.exists())
            self.assertTrue(result.event_log.exists())
            self.assertTrue(result.working_memory.exists())
            self.assertTrue((temp_root / "logs" / "runs" / result.workflow_run_id / "state.json").exists())

    def test_resume_requires_explicit_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))

            kernel = ConstellationKernel(temp_root)
            result = kernel.run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))

            with self.assertRaises(WorkflowStateError):
                kernel.resume_workflow(result.workflow_run_id)

    def test_approve_and_resume_completes_workflow(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))

            kernel = ConstellationKernel(temp_root)
            result = kernel.run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))
            approval_id = result.approval_path.stem

            pending = kernel.list_pending_approvals()
            self.assertEqual([approval["id"] for approval in pending], [approval_id])

            approval = kernel.approve(approval_id)
            self.assertEqual(approval["status"], "approved")
            self.assertFalse((temp_root / "approvals" / "pending" / f"{approval_id}.json").exists())
            self.assertTrue((temp_root / "approvals" / "accepted" / f"{approval_id}.json").exists())

            resumed = kernel.resume_workflow(result.workflow_run_id)
            self.assertEqual(resumed.status, "completed")

            state = WorkflowStateStore(temp_root).load(result.workflow_run_id)
            self.assertEqual(state.status, "completed")

            events = [
                json.loads(line)
                for line in resumed.event_log.read_text(encoding="utf-8").splitlines()
                if line.strip()
            ]
            event_types = [event["type"] for event in events]
            self.assertIn("ApprovalGranted", event_types)
            self.assertIn("WorkflowResumed", event_types)
            self.assertIn("WorkflowCompleted", event_types)


if __name__ == "__main__":
    unittest.main()


def _copy_runtime_tree(temp_root: Path) -> Path:
    for name in ["agents", "workflows", "config", "memory", "logs", "approvals"]:
        shutil.copytree(ROOT / name, temp_root / name)
    for path in (temp_root / "approvals" / "pending").glob("*.json"):
        path.unlink()
    for path in (temp_root / "logs" / "runs").glob("run_*"):
        shutil.rmtree(path)
    for path in (temp_root / "memory" / "runs").glob("run_*-working.json"):
        path.unlink()
    return temp_root
