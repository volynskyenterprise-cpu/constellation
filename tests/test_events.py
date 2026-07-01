from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from constellation.events import EventBus


class EventBusTests(unittest.TestCase):
    def test_emits_and_persists_event(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            bus = EventBus(Path(temp_dir), "run_test")
            event = bus.emit(
                "WorkflowStarted",
                workflow_id="example",
                actor={"type": "system", "id": "kernel", "name": "Kernel"},
                subject={"type": "workflow", "id": "example", "name": "Example"},
                summary="Started workflow.",
            )

            self.assertEqual(event.type, "WorkflowStarted")
            self.assertTrue(bus.log_path.exists())
            logged = json.loads(bus.log_path.read_text(encoding="utf-8").strip())
            self.assertEqual(logged["type"], "WorkflowStarted")
            self.assertEqual(logged["workflow_run_id"], "run_test")


if __name__ == "__main__":
    unittest.main()
