from __future__ import annotations

import shutil
import tempfile
import unittest
from datetime import datetime, timedelta
from pathlib import Path

from constellation.kernel import ConstellationKernel
from constellation.state import WorkflowStateError, WorkflowStateStore


ROOT = Path(__file__).resolve().parents[1]


class RunLifecycleTests(unittest.TestCase):
    def test_archive_moves_run_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            kernel = ConstellationKernel(temp_root)
            result = kernel.run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))

            archived = kernel.archive_run(result.workflow_run_id)

            self.assertEqual(archived.status, "archived")
            self.assertFalse((temp_root / "logs" / "runs" / result.workflow_run_id).exists())
            self.assertTrue((temp_root / "archive" / "runs" / result.workflow_run_id / "logs" / "state.json").exists())
            self.assertTrue((temp_root / "archive" / "runs" / result.workflow_run_id / "logs" / "events.jsonl").exists())
            self.assertTrue((temp_root / "archive" / "runs" / result.workflow_run_id / "memory").exists())
            self.assertTrue((temp_root / "logs" / "lifecycle.jsonl").exists())

    def test_delete_removes_active_run_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            kernel = ConstellationKernel(temp_root)
            result = kernel.run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))

            deleted = kernel.delete_run(result.workflow_run_id)

            self.assertEqual(deleted.status, "deleted")
            self.assertFalse((temp_root / "logs" / "runs" / result.workflow_run_id).exists())
            self.assertFalse((temp_root / "memory" / "runs" / f"{result.workflow_run_id}-working.json").exists())
            self.assertFalse(result.approval_path.exists())
            self.assertTrue((temp_root / "logs" / "lifecycle.jsonl").exists())

    def test_delete_removes_archived_run_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            kernel = ConstellationKernel(temp_root)
            result = kernel.run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))
            kernel.archive_run(result.workflow_run_id)

            kernel.delete_run(result.workflow_run_id)

            self.assertFalse((temp_root / "archive" / "runs" / result.workflow_run_id).exists())

    def test_missing_run_id_is_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            kernel = ConstellationKernel(temp_root)

            with self.assertRaises(WorkflowStateError):
                kernel.archive_run("run_missing")
            with self.assertRaises(WorkflowStateError):
                kernel.delete_run("run_missing")

    def test_prune_archives_old_runs_by_default(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            kernel = ConstellationKernel(temp_root)
            result = kernel.run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))
            _age_run(temp_root, result.workflow_run_id, days=10)

            pruned = kernel.prune_runs(older_than_days=7)

            self.assertEqual(len(pruned), 1)
            self.assertEqual(pruned[0].action, "archive")
            self.assertTrue((temp_root / "archive" / "runs" / result.workflow_run_id).exists())

    def test_prune_can_delete_old_runs_explicitly(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            kernel = ConstellationKernel(temp_root)
            result = kernel.run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))
            _age_run(temp_root, result.workflow_run_id, days=10)

            pruned = kernel.prune_runs(older_than_days=7, action="delete")

            self.assertEqual(len(pruned), 1)
            self.assertEqual(pruned[0].action, "delete")
            self.assertFalse((temp_root / "logs" / "runs" / result.workflow_run_id).exists())


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


def _age_run(root: Path, workflow_run_id: str, days: int) -> None:
    store = WorkflowStateStore(root)
    state = store.load(workflow_run_id)
    old_time = (datetime.now().astimezone() - timedelta(days=days)).isoformat(timespec="seconds")
    path = store.path_for(workflow_run_id)
    data = state.to_dict()
    data["created_at"] = old_time
    data["updated_at"] = old_time
    import json

    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
