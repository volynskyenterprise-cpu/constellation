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
from constellation.pkos import PKOSKnowledgeOrganization, PKOSError
from constellation.registry import AgentRegistry
from constellation.workflows import WorkflowLoader


ROOT = Path(__file__).resolve().parents[1]


class PKOSKnowledgeOrganizationTests(unittest.TestCase):
    def test_pkos_workflow_loads(self) -> None:
        registry = AgentRegistry.load_from(ROOT / "agents")
        workflow = WorkflowLoader(registry).load(ROOT / "workflows" / "pkos" / "pkos-ingestion.yaml")

        self.assertEqual(workflow.id, "pkos_ingestion")
        self.assertEqual(workflow.steps[0].id, "classify_source")
        self.assertEqual(workflow.steps[-1].output, "pkos_release_notes")

    def test_pkos_input_ingestion_from_markdown(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            input_path = _write_pkos_input(temp_root, "source.md")

            pkos_input = PKOSKnowledgeOrganization(temp_root).load_input(input_path)

            self.assertEqual(pkos_input.format, "md")
            self.assertIn("Source claim", pkos_input.text)

    def test_pkos_input_ingestion_from_text(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            input_path = _write_pkos_input(temp_root, "source.txt")

            pkos_input = PKOSKnowledgeOrganization(temp_root).load_input(input_path)

            self.assertEqual(pkos_input.format, "txt")
            self.assertIn("Source claim", pkos_input.text)

    def test_unsupported_file_type_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            input_path = temp_root / "pkos_inputs" / "source.pdf"
            input_path.write_text("not supported", encoding="utf-8")

            with self.assertRaises(PKOSError):
                PKOSKnowledgeOrganization(temp_root).load_input(input_path)

    def test_pkos_cli_ingest(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            input_path = _write_pkos_input(temp_root, "source.md")
            output = io.StringIO()

            with redirect_stdout(output):
                exit_code = main(["pkos", "--root", str(temp_root), "ingest", str(input_path)])

            self.assertEqual(exit_code, 0)
            self.assertIn("workflow_id: pkos_ingestion", output.getvalue())
            self.assertIn("status: needs_approval", output.getvalue())

    def test_pkos_package_export_and_manifest_creation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            result = PKOSKnowledgeOrganization(temp_root).ingest(_write_pkos_input(temp_root, "source.md"))

            output_dir = PKOSKnowledgeOrganization(temp_root).package(result.workflow_run_id)
            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))

            self.assertTrue((output_dir / "review-package.md").exists())
            self.assertTrue((output_dir / "source-summary.md").exists())
            self.assertEqual(manifest["workflow_run_id"], result.workflow_run_id)
            self.assertEqual(manifest["source_type"], "md")
            self.assertIn("review-package.md", manifest["generated_files"])
            self.assertEqual(manifest["approval_status"], "pending")

    def test_overwrite_protection(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            organization = PKOSKnowledgeOrganization(temp_root)
            result = organization.ingest(_write_pkos_input(temp_root, "source.md"))

            output_dir = organization.package(result.workflow_run_id)
            original = (output_dir / "review-package.md").read_text(encoding="utf-8")
            with self.assertRaises(PKOSError):
                organization.package(result.workflow_run_id)
            output_dir = organization.package(result.workflow_run_id, overwrite=True)

            self.assertEqual((output_dir / "review-package.md").read_text(encoding="utf-8"), original)

    def test_safety_no_external_vault_mutation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            external_vault = Path(temp_dir) / "external-pkos-vault"
            external_vault.mkdir()
            sentinel = external_vault / "Concept.md"
            sentinel.write_text("original", encoding="utf-8")
            result = PKOSKnowledgeOrganization(temp_root).ingest(_write_pkos_input(temp_root, "source.md"))

            output_dir = PKOSKnowledgeOrganization(temp_root).package(result.workflow_run_id)

            self.assertEqual(sentinel.read_text(encoding="utf-8"), "original")
            self.assertTrue(str(output_dir).startswith(str(temp_root / "outputs" / "pkos")))

    def test_approval_gate_is_required(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            result = PKOSKnowledgeOrganization(temp_root).ingest(_write_pkos_input(temp_root, "source.md"))
            approvals = ConstellationKernel(temp_root).list_pending_approvals()

            self.assertEqual(result.status, "needs_approval")
            self.assertEqual(approvals[0]["gate_id"], "approve_pkos_update_package")

    def test_default_provider_disabled_behavior_remains_safe(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            result = PKOSKnowledgeOrganization(temp_root).ingest(_write_pkos_input(temp_root, "source.md"))
            memory = json.loads(result.working_memory.read_text(encoding="utf-8"))
            artifacts = ArtifactStore(temp_root).list(result.workflow_run_id)

            self.assertEqual(result.status, "needs_approval")
            self.assertEqual(artifacts, [])
            self.assertEqual(memory["artifacts"]["pkos_release_notes"]["status"], "placeholder")
            self.assertIsNone(memory["artifacts"]["pkos_release_notes"]["provider_result"])
            self.assertEqual(memory["entries"][0]["key"], "pkos_source_document")

    def test_echo_provider_deterministic_package_behavior(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            _write_provider_config(temp_root, invoke=True)
            result = PKOSKnowledgeOrganization(temp_root).ingest(_write_pkos_input(temp_root, "source.md"))
            artifacts = ArtifactStore(temp_root).list(result.workflow_run_id)

            output_dir = PKOSKnowledgeOrganization(temp_root).package(result.workflow_run_id)
            review = (output_dir / "review-package.md").read_text(encoding="utf-8")
            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))

            self.assertEqual(len(artifacts), 7)
            self.assertIn("create_concept", review)
            self.assertIn("add_source_record", review)
            self.assertEqual(manifest["approval_status"], "pending")


def _copy_runtime_tree(temp_root: Path) -> Path:
    for name in ["agents", "workflows", "config", "memory", "logs", "approvals", "crew", "pkos_inputs"]:
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


def _write_pkos_input(root: Path, name: str) -> Path:
    path = root / "pkos_inputs" / name
    path.write_text(
        "# Source Note\n\nSource claim: durable knowledge should be proposed before application.\n\nUncertainty: source truth is not assumed.",
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
