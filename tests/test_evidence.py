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
from constellation.evidence import EvidenceItem, EvidenceStore, evidence_from_text
from constellation.pkos import PKOSKnowledgeOrganization
from constellation.research import ResearchOrganization


ROOT = Path(__file__).resolve().parents[1]


class EvidenceEngineTests(unittest.TestCase):
    def test_evidence_item_schema_and_store(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            item = EvidenceItem(
                evidence_id="ev_test",
                workflow_run_id="run_test",
                claim="claim",
                supporting_quote="supporting quote",
                source_identifier="source.md",
                source_location="line 1",
                confidence="source_provided",
                provenance={"method": "test"},
                created_at="2026-07-05T09:00:00-07:00",
                updated_at="2026-07-05T09:00:00-07:00",
            )

            store = EvidenceStore(root)
            store.save(item)

            self.assertEqual(store.show("ev_test")["claim"], "claim")
            self.assertEqual(store.list("run_test")[0]["evidence_id"], "ev_test")
            self.assertEqual(store.query(source_identifier="source.md")[0]["source_location"], "line 1")

    def test_evidence_from_text_is_deterministic(self) -> None:
        first = evidence_from_text(
            workflow_run_id="run_test",
            source_identifier="source.md",
            source_text="# Title\n\nClaim one.\nClaim two.",
            provenance={"organization": "test"},
        )
        second = evidence_from_text(
            workflow_run_id="run_test",
            source_identifier="source.md",
            source_text="# Title\n\nClaim one.\nClaim two.",
            provenance={"organization": "test"},
        )

        self.assertEqual([item.evidence_id for item in first], [item.evidence_id for item in second])
        self.assertEqual(len(first), 3)
        self.assertEqual(first[0].source_location, "line 1")

    def test_evidence_cli_list_show_export(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            result = ResearchOrganization(temp_root).run(_write_input(temp_root / "research_inputs" / "brief.md"))
            evidence = EvidenceStore(temp_root).list(result.workflow_run_id)

            list_output = io.StringIO()
            with redirect_stdout(list_output):
                list_exit = main(["evidence", "--root", str(temp_root), "list"])
            show_output = io.StringIO()
            with redirect_stdout(show_output):
                show_exit = main(["evidence", "--root", str(temp_root), "show", evidence[0]["evidence_id"]])
            export_output = io.StringIO()
            with redirect_stdout(export_output):
                export_exit = main(["evidence", "--root", str(temp_root), "export", result.workflow_run_id])

            self.assertEqual(list_exit, 0)
            self.assertIn("ev_", list_output.getvalue())
            self.assertEqual(show_exit, 0)
            self.assertEqual(json.loads(show_output.getvalue())["workflow_run_id"], result.workflow_run_id)
            self.assertEqual(export_exit, 0)
            self.assertTrue((temp_root / "outputs" / "evidence" / f"{result.workflow_run_id}-evidence.md").exists())

    def test_research_persists_evidence_and_export_writes_evidence_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            result = ResearchOrganization(temp_root).run(_write_input(temp_root / "research_inputs" / "brief.md"))

            report_path = ResearchOrganization(temp_root).export(result.workflow_run_id)
            evidence_records = EvidenceStore(temp_root).list(result.workflow_run_id)

            self.assertTrue(evidence_records)
            self.assertEqual(evidence_records[0]["provenance"]["organization"], "research")
            self.assertTrue(report_path.exists())
            self.assertTrue((temp_root / "outputs" / "research" / f"{result.workflow_run_id}-evidence.md").exists())

    def test_pkos_persists_evidence_and_package_writes_evidence_report(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            result = PKOSKnowledgeOrganization(temp_root).ingest(_write_input(temp_root / "pkos_inputs" / "source.md"))

            output_dir = PKOSKnowledgeOrganization(temp_root).package(result.workflow_run_id)
            manifest = json.loads((output_dir / "manifest.json").read_text(encoding="utf-8"))
            evidence_records = EvidenceStore(temp_root).list(result.workflow_run_id)

            self.assertTrue(evidence_records)
            self.assertEqual(evidence_records[0]["provenance"]["organization"], "pkos")
            self.assertTrue((output_dir / "evidence-report.md").exists())
            self.assertEqual(sorted(manifest["evidence_ids"]), sorted(record["evidence_id"] for record in evidence_records))

    def test_provider_artifacts_reference_evidence_ids(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            _write_provider_config(temp_root, invoke=True)
            result = ResearchOrganization(temp_root).run(_write_input(temp_root / "research_inputs" / "brief.md"))

            evidence_ids = {record["evidence_id"] for record in EvidenceStore(temp_root).list(result.workflow_run_id)}
            artifacts = ArtifactStore(temp_root).list(result.workflow_run_id)
            used = {
                evidence["id"]
                for artifact in artifacts
                for evidence in artifact.get("evidence_used", [])
                if evidence.get("type") == "evidence"
            }

            self.assertTrue(evidence_ids)
            self.assertTrue(evidence_ids.issubset(used))


def _copy_runtime_tree(temp_root: Path) -> Path:
    for name in ["agents", "workflows", "config", "memory", "logs", "approvals", "crew", "research_inputs", "pkos_inputs"]:
        shutil.copytree(ROOT / name, temp_root / name)
    for path in (temp_root / "approvals" / "pending").glob("*.json"):
        path.unlink()
    for path in (temp_root / "approvals" / "accepted").glob("*.json"):
        path.unlink()
    for path in (temp_root / "logs" / "runs").glob("run_*"):
        shutil.rmtree(path)
    for path in (temp_root / "memory" / "runs").glob("run_*-working.json"):
        path.unlink()
    for path in (temp_root / "memory" / "evidence").glob("ev_*.json"):
        path.unlink()
    index = temp_root / "memory" / "evidence" / "index.json"
    if index.exists():
        index.unlink()
    return temp_root


def _write_input(path: Path) -> Path:
    path.write_text("# Source\n\nObserved fact: evidence must be traceable.\nOpen question: who approves?", encoding="utf-8")
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
