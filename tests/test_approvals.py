from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from constellation.approvals import ApprovalManager
from constellation.kernel import ConstellationKernel


ROOT = Path(__file__).resolve().parents[1]


class ApprovalManagerTests(unittest.TestCase):
    def test_lists_and_approves_pending_approval(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))

            result = ConstellationKernel(temp_root).run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))
            approval_id = result.approval_path.stem
            manager = ApprovalManager(temp_root, result.workflow_run_id)

            pending = manager.list_pending()
            self.assertEqual(len(pending), 1)
            self.assertEqual(pending[0]["id"], approval_id)

            approved = manager.approve(approval_id)
            self.assertEqual(approved["id"], approval_id)
            self.assertEqual(approved["status"], "approved")
            self.assertTrue(approved["explicit_human_approval"])
            self.assertTrue(manager.is_approved(approval_id))


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
