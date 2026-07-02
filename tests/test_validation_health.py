from __future__ import annotations

import io
import shutil
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path

from constellation.cli import main
from constellation.health import SystemHealthChecker
from constellation.validation import CrewValidator


ROOT = Path(__file__).resolve().parents[1]


class ValidationHealthTests(unittest.TestCase):
    def test_valid_crew(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))

            report = CrewValidator(temp_root).validate()

            self.assertTrue(report.ok)
            self.assertEqual(report.status, "ok")
            self.assertEqual(report.issues, [])

    def test_missing_crew_file(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            (temp_root / "crew" / "ceo" / "profile.md").unlink()

            report = CrewValidator(temp_root).validate()

            self.assertFalse(report.ok)
            self.assertEqual(report.issues[0].code, "crew_file_missing")
            self.assertIn("profile.md", report.issues[0].message)

    def test_missing_crew_folder(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            shutil.rmtree(temp_root / "crew" / "ceo")

            report = CrewValidator(temp_root).validate()

            self.assertFalse(report.ok)
            self.assertTrue(any(issue.code == "founding_crew_folder_missing" for issue in report.issues))
            self.assertTrue(any(issue.code == "agent_unmapped_to_crew" for issue in report.issues))

    def test_unmapped_agent(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            _write_agent(temp_root / "agents" / "investment-strategist.yaml", "investment_strategist")

            report = CrewValidator(temp_root).validate()

            self.assertFalse(report.ok)
            self.assertTrue(any(issue.code == "agent_unmapped_to_crew" for issue in report.issues))

    def test_validate_crew_cli_failure_exit_code(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            (temp_root / "crew" / "ceo" / "profile.md").unlink()
            output = io.StringIO()

            with redirect_stdout(output):
                exit_code = main(["validate", "--root", str(temp_root), "crew"])

            self.assertEqual(exit_code, 1)
            self.assertIn("crew: failed", output.getvalue())
            self.assertIn("crew_file_missing", output.getvalue())

    def test_health_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))

            report = SystemHealthChecker(temp_root).check()

            self.assertTrue(report.ok)
            self.assertEqual(report.status, "ok")
            self.assertTrue(any(check.name == "crew" and check.status == "ok" for check in report.checks))
            self.assertTrue(any(check.name == "provider_execution_default" and check.status == "ok" for check in report.checks))

    def test_health_failure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            shutil.rmtree(temp_root / "constitution")

            report = SystemHealthChecker(temp_root).check()

            self.assertFalse(report.ok)
            self.assertEqual(report.status, "failed")
            self.assertTrue(any(check.name == "constitution" and check.status == "failed" for check in report.checks))

    def test_health_cli_success(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_root = _copy_runtime_tree(Path(temp_dir))
            output = io.StringIO()

            with redirect_stdout(output):
                exit_code = main(["health", "--root", str(temp_root)])

            self.assertEqual(exit_code, 0)
            self.assertIn("health: ok", output.getvalue())
            self.assertIn("ok: crew: Crew validation passed.", output.getvalue())


def _copy_runtime_tree(temp_root: Path) -> Path:
    for name in ["agents", "workflows", "config", "memory", "logs", "approvals", "crew", "constitution", "archive"]:
        shutil.copytree(ROOT / name, temp_root / name)
    for path in (temp_root / "approvals" / "pending").glob("*.json"):
        path.unlink()
    for path in (temp_root / "approvals" / "accepted").glob("*.json"):
        path.unlink()
    for path in (temp_root / "logs" / "runs").glob("run_*"):
        shutil.rmtree(path)
    for path in (temp_root / "memory" / "runs").glob("run_*-working.json"):
        path.unlink()
    for path in (temp_root / "archive" / "runs").glob("run_*"):
        if path.is_dir():
            shutil.rmtree(path)
    return temp_root


def _write_agent(path: Path, agent_id: str) -> None:
    path.write_text(
        f"""id: {agent_id}
name: Investment Strategist
version: 0.1.0
status: active
mission: Test unmapped agent validation.
authority:
  can_decide:
    - test
methods:
  - test
inputs:
  required:
    - test
outputs:
  - test
escalation_triggers:
  - test
quality_bar:
  - test
""",
        encoding="utf-8",
    )


if __name__ == "__main__":
    unittest.main()
