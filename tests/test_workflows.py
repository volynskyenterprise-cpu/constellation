from __future__ import annotations

import unittest
from pathlib import Path

from constellation.registry import AgentRegistry
from constellation.workflows import WorkflowLoader


ROOT = Path(__file__).resolve().parents[1]


class WorkflowLoaderTests(unittest.TestCase):
    def test_loads_example_workflow(self) -> None:
        registry = AgentRegistry.load_from(ROOT / "agents")
        workflow = WorkflowLoader(registry).load(ROOT / "workflows" / "examples" / "ceo-research-qa-docs.yaml")

        self.assertEqual(workflow.id, "example_ceo_research_qa_docs")
        self.assertEqual([step.agent for step in workflow.steps], ["ceo", "research_lead", "qa_lead", "documentation_engineer"])
        self.assertEqual(workflow.approval_gates[0].after_step, "produce_documentation")

    def test_every_step_references_registered_agent(self) -> None:
        registry = AgentRegistry.load_from(ROOT / "agents")
        workflow = WorkflowLoader(registry).load(ROOT / "workflows" / "release-readiness.yaml")

        for step in workflow.steps:
            self.assertTrue(registry.has(step.agent), step.agent)


if __name__ == "__main__":
    unittest.main()
