from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from constellation.messages import MessageBus
from constellation.models import Party
from constellation.registry import AgentRegistry
from constellation.workflows import WorkflowLoader


ROOT = Path(__file__).resolve().parents[1]


class MessageBusTests(unittest.TestCase):
    def test_creates_standardized_message_and_persists_log(self) -> None:
        registry = AgentRegistry.load_from(ROOT / "agents")
        workflow = WorkflowLoader(registry).load(ROOT / "workflows" / "examples" / "ceo-research-qa-docs.yaml")
        step = workflow.steps[0]

        with tempfile.TemporaryDirectory() as temp_dir:
            bus = MessageBus(Path(temp_dir), "run_test")
            message = bus.create_for_step(
                workflow,
                step,
                sender=Party(type="workflow", id=workflow.id, name=workflow.name),
                receiver=Party(type="agent", id="ceo", name="CEO"),
                context={"summary": "test"},
            )

            self.assertEqual(message.workflow_id, workflow.id)
            self.assertEqual(message.requested_action, "frame_objective")
            self.assertEqual(message.status, "sent")
            self.assertTrue(bus.log_path.exists())

            logged = json.loads(bus.log_path.read_text(encoding="utf-8").strip())
            for field in [
                "id",
                "timestamp",
                "workflow_id",
                "sender",
                "receiver",
                "task",
                "context",
                "assumptions",
                "reasoning_summary",
                "evidence",
                "confidence",
                "requested_action",
                "status",
            ]:
                self.assertIn(field, logged)


if __name__ == "__main__":
    unittest.main()
