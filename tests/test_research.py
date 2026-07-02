from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from constellation.artifacts import ArtifactStore
from constellation.cli import main
from constellation.kernel import ConstellationKernel
from constellation.registry import AgentRegistry
from constellation.research import ResearchError, ResearchOrganization
from constellation.workflows import WorkflowLoader


ROOT = Path(__file__).resolve().parents[1]


class ResearchOrganizationTests(unittest.TestCase):
    def test_research_workflow_loads(self) -> None:
        registry = AgentRegistry.load_from(ROOT / "agents")
        workflow = WorkflowLoader(registry).load(ROOT / "workflows" / "research" / "institutional-research.yaml")

        self.assertEqual(workflow.id, "institutional_research")
        self.assertEqual([step.id for step in workflow.steps][0], "frame_research_objective")
        self.assertEqual(workflow.steps[-1].output, "executive_research_report")

    def test_research_input_ingestion_from_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            input_path = temp_root / "research_inputs" / "brief.md"
            input_path.write_text("# Brief\n\nEvidence line.", encoding="utf-8")

            research_input = ResearchOrganization(temp_root).load_input(input_path)

            self.assertEqual(research_input.format, "md")
            self.assertIn("Evidence line.", research_input.text)

    def test_research_input_ingestion_from_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            input_path = temp_root / "research_inputs" / "brief.txt"
            input_path.write_text("Plain text research brief.", encoding="utf-8")

            research_input = ResearchOrganization(temp_root).load_input(input_path)

            self.assertEqual(research_input.format, "txt")
            self.assertIn("Plain text", research_input.text)

    def test_unsupported_file_type_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            input_path = temp_root / "research_inputs" / "brief.pdf"
            input_path.write_text("not parsed", encoding="utf-8")

            with self.assertRaises(ResearchError):
                ResearchOrganization(temp_root).load_input(input_path)

    def test_research_cli_run(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            input_path = _write_research_input(temp_root, "brief.md")
            output = io.StringIO()

            with redirect_stdout(output):
                exit_code = main(["research", "--root", str(temp_root), "run", str(input_path)])

            self.assertEqual(exit_code, 0)
            self.assertIn("workflow_id: institutional_research", output.getvalue())
            self.assertIn("status: needs_approval", output.getvalue())

    def test_research_artifacts_created_when_echo_provider_enabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            _write_provider_config(temp_root, invoke=True)
            input_path = _write_research_input(temp_root, "brief.md")

            result = ResearchOrganization(temp_root).run(input_path)
            artifacts = ArtifactStore(temp_root).list(result.workflow_run_id)

            self.assertEqual(result.status, "needs_approval")
            self.assertEqual(len(artifacts), 5)
            artifact_types = {artifact["artifact_type"] for artifact in artifacts}
            self.assertIn("evidence_table", artifact_types)
            self.assertIn("executive_research_report", artifact_types)

    def test_research_workflow_pauses_at_approval_gate(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            result = ResearchOrganization(temp_root).run(_write_research_input(temp_root, "brief.txt"))

            approvals = ConstellationKernel(temp_root).list_pending_approvals()

            self.assertEqual(result.status, "needs_approval")
            self.assertEqual(len(approvals), 1)
            self.assertEqual(approvals[0]["gate_id"], "approve_executive_research_report")

    def test_research_export_creates_markdown_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            _write_provider_config(temp_root, invoke=True)
            result = ResearchOrganization(temp_root).run(_write_research_input(temp_root, "brief.md"))

            report_path = ResearchOrganization(temp_root).export(result.workflow_run_id)
            report = report_path.read_text(encoding="utf-8")

            self.assertTrue(report_path.exists())
            self.assertIn("# Executive Research Report", report)
            self.assertIn("## Evidence Table", report)
            self.assertIn("## Knowledge Implications", report)
            self.assertIn("## QA Challenge", report)
            self.assertIn("## Approval Status", report)
            self.assertIn("pending", report)

    def test_default_behavior_remains_safe_when_providers_disabled(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            result = ResearchOrganization(temp_root).run(_write_research_input(temp_root, "brief.md"))
            memory = json.loads(result.working_memory.read_text(encoding="utf-8"))
            artifacts = ArtifactStore(temp_root).list(result.workflow_run_id)

            self.assertEqual(result.status, "needs_approval")
            self.assertEqual(artifacts, [])
            self.assertEqual(memory["artifacts"]["executive_research_report"]["status"], "placeholder")
            self.assertIsNone(memory["artifacts"]["executive_research_report"]["provider_result"])
            self.assertEqual(memory["entries"][0]["key"], "research_source_document")


def _copy_runtime_tree(temp_root: Path) -> Path:
    for name in ["agents", "workflows", "config", "memory", "logs", "approvals", "crew", "research_inputs"]:
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


def _write_research_input(root: Path, name: str) -> Path:
    path = root / "research_inputs" / name
    path.write_text(
        "# Market Brief\n\nObserved fact: customer teams need faster evidence review.\n\nUnknown: budget impact.",
        encoding="utf-8",
    )
    return path


def _write_provider_config(root: Path, *, invoke: bool) -> None:
    content = f"""providers:
  - id: echo
    enabled: true
    role: deterministic_stub_provider
    provider_type: echo
    model: echo-v0
    capabilities:
      - reasoning
      - structured_output
  - id: "null"
    enabled: true
    role: deterministic_noop_provider
    provider_type: "null"
    model: null-v0
    capabilities:
      - reasoning
      - structured_output

routing:
  invoke_provider_during_kernel_run: {str(invoke).lower()}
  default_provider: echo
  per_agent_provider:
    none: none
  allow_fallback: false
  fallback_provider: "null"
"""
    (root / "config" / "providers.yaml").write_text(content, encoding="utf-8")


if __name__ == "__main__":
    unittest.main()
