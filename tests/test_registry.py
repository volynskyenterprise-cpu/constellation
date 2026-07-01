from __future__ import annotations

import unittest
from pathlib import Path

from constellation.registry import AgentRegistry


ROOT = Path(__file__).resolve().parents[1]


class AgentRegistryTests(unittest.TestCase):
    def test_loads_v1_agents(self) -> None:
        registry = AgentRegistry.load_from(ROOT / "agents")

        self.assertTrue(registry.has("ceo"))
        self.assertTrue(registry.has("research_lead"))
        self.assertTrue(registry.has("qa_lead"))
        self.assertTrue(registry.has("documentation_engineer"))
        self.assertGreaterEqual(len(registry.all()), 8)

    def test_agent_required_fields_are_available(self) -> None:
        registry = AgentRegistry.load_from(ROOT / "agents")
        ceo = registry.get("ceo")

        self.assertEqual(ceo.name, "CEO")
        self.assertIn("request_human_approval", ceo.authority["can"])
        self.assertIn("executive_summary", ceo.outputs)


if __name__ == "__main__":
    unittest.main()
