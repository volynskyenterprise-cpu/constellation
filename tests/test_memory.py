from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from constellation.memory import MemoryManager


class MemoryManagerTests(unittest.TestCase):
    def test_initializes_working_project_and_stub_memory(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            memory = MemoryManager(Path(temp_dir), "run_test")
            memory.initialize("Test objective")
            memory.add_working_entry("note", "hello")
            memory.set_artifact("artifact", {"status": "placeholder"})

            context = memory.context_for_step("step_one")

            self.assertTrue(memory.working_path.exists())
            self.assertTrue(memory.project_path.exists())
            self.assertTrue(memory.knowledge_path.exists())
            self.assertTrue(memory.long_term_path.exists())
            self.assertEqual(context["working_memory"]["objective"], "Test objective")
            self.assertEqual(context["artifacts"]["artifact"]["status"], "placeholder")
            self.assertEqual(memory.project_memory()["layer"], "project")


if __name__ == "__main__":
    unittest.main()
