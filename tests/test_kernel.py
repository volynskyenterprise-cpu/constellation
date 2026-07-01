from __future__ import annotations

import shutil
import tempfile
import unittest
from pathlib import Path

from constellation.kernel import ConstellationKernel


ROOT = Path(__file__).resolve().parents[1]


class KernelRunTests(unittest.TestCase):
    def test_example_workflow_runs_until_approval_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = Path(temp_dir)
            for name in ["agents", "workflows", "config", "memory", "logs", "approvals"]:
                shutil.copytree(ROOT / name, temp_root / name)

            result = ConstellationKernel(temp_root).run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))

            self.assertEqual(result.workflow_id, "example_ceo_research_qa_docs")
            self.assertEqual(result.status, "needs_approval")
            self.assertIsNotNone(result.approval_path)
            self.assertTrue(result.message_log.exists())
            self.assertTrue(result.event_log.exists())
            self.assertTrue(result.working_memory.exists())


if __name__ == "__main__":
    unittest.main()
