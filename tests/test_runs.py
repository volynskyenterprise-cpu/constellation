from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from constellation.kernel import ConstellationKernel
from constellation.state import WorkflowStateError


ROOT = Path(__file__).resolve().parents[1]


class RunInspectionTests(unittest.TestCase):
    def test_lists_paused_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            kernel = ConstellationKernel(temp_root)
            result = kernel.run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))

            runs = kernel.list_runs()

            self.assertEqual(len(runs), 1)
            self.assertEqual(runs[0].workflow_run_id, result.workflow_run_id)
            self.assertEqual(runs[0].status, "needs_approval")
            self.assertTrue(runs[0].current_step.startswith("approval:"))
            self.assertNotEqual(runs[0].created_at, "unknown")

    def test_shows_paused_run_details(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            kernel = ConstellationKernel(temp_root)
            result = kernel.run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))

            details = kernel.show_run(result.workflow_run_id)

            self.assertEqual(details.summary.status, "needs_approval")
            self.assertEqual(details.approval_status, "pending")
            self.assertTrue(details.message_log_path.exists())
            self.assertTrue(details.event_log_path.exists())
            self.assertTrue(details.working_memory_path.exists())
            self.assertGreater(len(details.recent_events), 0)
            self.assertGreater(len(details.recent_messages), 0)

    def test_missing_run_id_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            kernel = ConstellationKernel(temp_root)

            with self.assertRaises(WorkflowStateError):
                kernel.show_run("run_missing")

    def test_completed_run_is_visible(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            kernel = ConstellationKernel(temp_root)
            result = kernel.run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))
            approval_id = result.approval_path.stem

            kernel.approve(approval_id)
            kernel.resume_workflow(result.workflow_run_id)
            runs = kernel.list_runs()
            details = kernel.show_run(result.workflow_run_id)

            self.assertEqual(runs[0].status, "completed")
            self.assertEqual(runs[0].current_step, "Complete")
            self.assertEqual(details.summary.status, "completed")
            self.assertEqual(details.approval_status, "approved")

    def test_corrupt_state_file_is_listed_gracefully(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            corrupt_dir = temp_root / "logs" / "runs" / "run_corrupt"
            corrupt_dir.mkdir(parents=True)
            (corrupt_dir / "state.json").write_text("{not-json", encoding="utf-8")
            kernel = ConstellationKernel(temp_root)

            runs = kernel.list_runs()

            self.assertEqual(runs[0].workflow_run_id, "run_corrupt")
            self.assertEqual(runs[0].status, "invalid_state")


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
