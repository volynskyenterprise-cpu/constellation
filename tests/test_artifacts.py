from __future__ import annotations

import io
import json
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from constellation.artifacts import AgentArtifact, ArtifactParser, ArtifactStore
from constellation.cli import main
from constellation.kernel import ConstellationKernel
from constellation.models import utc_now_iso


ROOT = Path(__file__).resolve().parents[1]


class ArtifactTests(unittest.TestCase):
    def test_agent_artifact_schema_creation(self) -> None:
        artifact = AgentArtifact(
            artifact_id="artifact_run_test_frame_request",
            workflow_run_id="run_test",
            workflow_id="workflow_test",
            step_id="frame_request",
            agent_id="ceo",
            crew_role="ceo",
            artifact_type="frame_objective",
            title="CEO artifact",
            summary="summary",
            findings=[{"label": "finding", "value": "value"}],
            recommendations=["recommendation"],
            risks=["risk"],
            assumptions=["assumption"],
            evidence_used=[{"type": "prompt_package", "id": "prompt_test"}],
            next_steps=["next"],
            confidence="medium",
            status="completed",
            provider_result_id="provider_result_msg_echo",
            prompt_package_id="prompt_test",
            created_at=utc_now_iso(),
        )

        payload = artifact.to_dict()

        self.assertEqual(payload["artifact_id"], "artifact_run_test_frame_request")
        self.assertEqual(payload["provider_result_id"], "provider_result_msg_echo")
        self.assertEqual(payload["status"], "completed")

    def test_provider_response_parsing(self) -> None:
        artifact = ArtifactParser().parse(
            provider_result={
                "provider_result_id": "provider_result_msg_echo",
                "provider_name": "echo",
                "model": "echo-v0",
                "input_message_id": "msg_echo",
                "output_text": "echo:msg_echo:frame_objective:prompt=prompt_run_test_frame_request:role=ceo:step=frame_request",
                "status": "completed",
                "error": None,
                "metadata": {},
                "created_at": utc_now_iso(),
            },
            prompt_package=_prompt_package(),
        )

        self.assertEqual(artifact.status, "completed")
        self.assertEqual(artifact.artifact_id, "artifact_run_test_frame_request")
        self.assertEqual(artifact.prompt_package_id, "prompt_run_test_frame_request")
        self.assertEqual(artifact.provider_result_id, "provider_result_msg_echo")
        self.assertEqual(artifact.findings[0]["label"], "provider_output")

    def test_artifact_persistence(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            artifact = ArtifactParser().parse(
                provider_result={
                    "provider_result_id": "provider_result_msg_echo",
                    "provider_name": "echo",
                    "model": "echo-v0",
                    "input_message_id": "msg_echo",
                    "output_text": "echo output",
                    "status": "completed",
                    "error": None,
                    "metadata": {},
                    "created_at": utc_now_iso(),
                },
                prompt_package=_prompt_package(),
            )
            store = ArtifactStore(root)

            path = store.persist(artifact)
            listed = store.list("run_test")
            shown = store.show("run_test", artifact.artifact_id)

            self.assertTrue(path.exists())
            self.assertEqual(len(listed), 1)
            self.assertEqual(shown["artifact_id"], artifact.artifact_id)

    def test_artifacts_list_and_show_cli(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            _write_provider_config(temp_root)
            result = ConstellationKernel(temp_root).run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))
            artifact_id = f"artifact_{result.workflow_run_id}_frame_request"

            list_output = io.StringIO()
            with redirect_stdout(list_output):
                list_exit = main(["artifacts", "--root", str(temp_root), "list", result.workflow_run_id])
            show_output = io.StringIO()
            with redirect_stdout(show_output):
                show_exit = main(["artifacts", "--root", str(temp_root), "show", result.workflow_run_id, artifact_id])

            self.assertEqual(list_exit, 0)
            self.assertIn(artifact_id, list_output.getvalue())
            self.assertEqual(show_exit, 0)
            self.assertEqual(json.loads(show_output.getvalue())["artifact_id"], artifact_id)

    def test_provider_backed_workflow_produces_structured_artifacts(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            _write_provider_config(temp_root)

            result = ConstellationKernel(temp_root).run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))
            artifacts = ArtifactStore(temp_root).list(result.workflow_run_id)
            memory = json.loads(result.working_memory.read_text(encoding="utf-8"))
            messages = _jsonl(result.message_log)
            events = _jsonl(result.event_log)

            self.assertEqual(result.status, "needs_approval")
            self.assertEqual(len(artifacts), 4)
            self.assertIn("agent_artifact", memory["artifacts"]["objective_brief"])
            self.assertEqual(memory["artifacts"]["objective_brief"]["agent_artifact"]["status"], "completed")
            self.assertTrue(any(record.get("record_type") == "agent_artifact" for record in messages))
            self.assertTrue(any(event.get("type") == "AgentArtifactCreated" for event in events))

    def test_approval_still_blocks_and_resume_completes(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            _write_provider_config(temp_root)
            kernel = ConstellationKernel(temp_root)

            result = kernel.run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))
            approvals = kernel.list_pending_approvals()
            approval = kernel.approve(str(approvals[0]["id"]))
            resumed = kernel.resume_workflow(result.workflow_run_id)

            self.assertEqual(result.status, "needs_approval")
            self.assertEqual(approval["status"], "approved")
            self.assertEqual(resumed.status, "completed")

    def test_default_placeholder_behavior_remains_unchanged(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))

            result = ConstellationKernel(temp_root).run_workflow(Path("workflows/examples/ceo-research-qa-docs.yaml"))
            memory = json.loads(result.working_memory.read_text(encoding="utf-8"))
            artifacts = ArtifactStore(temp_root).list(result.workflow_run_id)

            self.assertEqual(memory["artifacts"]["objective_brief"]["status"], "placeholder")
            self.assertIsNone(memory["artifacts"]["objective_brief"]["provider_result"])
            self.assertIsNone(memory["artifacts"]["objective_brief"]["agent_artifact"])
            self.assertEqual(artifacts, [])


def _prompt_package() -> dict[str, object]:
    return {
        "prompt_id": "prompt_run_test_frame_request",
        "workflow_run_id": "run_test",
        "workflow_id": "workflow_test",
        "step_id": "frame_request",
        "agent_id": "ceo",
        "crew_role": "ceo",
        "output_contract": {"expected_output": "objective_brief"},
        "metadata": {"step_type": "frame_objective"},
    }


def _copy_runtime_tree(temp_root: Path) -> Path:
    for name in ["agents", "workflows", "config", "memory", "logs", "approvals", "crew"]:
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


def _write_provider_config(root: Path) -> None:
    content = """providers:
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
  invoke_provider_during_kernel_run: true
  default_provider: echo
  per_agent_provider:
    none: none
  allow_fallback: false
  fallback_provider: "null"
"""
    (root / "config" / "providers.yaml").write_text(content, encoding="utf-8")


def _jsonl(path: Path) -> list[dict[str, object]]:
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


if __name__ == "__main__":
    unittest.main()
