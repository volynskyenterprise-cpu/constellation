from __future__ import annotations

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from constellation.pkos_smart_sync import (
    PkosSmartSyncEngine,
    PkosSmartSyncError,
    PkosSyncPolicy,
    classify_path,
)


def run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=True)


class PkosSmartSyncTests(unittest.TestCase):
    def setUp(self) -> None:
        self.tmp = Path(tempfile.mkdtemp(prefix="pkos-smart-sync-test-"))
        self.constellation = self.tmp / "constellation"
        self.pkos = self.tmp / "pkos"
        self.constellation.mkdir()
        self.pkos.mkdir()
        run(["git", "init", "-b", "main"], self.pkos)
        run(["git", "config", "user.email", "test@example.com"], self.pkos)
        run(["git", "config", "user.name", "Smart Sync Test"], self.pkos)
        bare = self.tmp / "remote.git"
        run(["git", "init", "--bare", str(bare)], self.tmp)
        run(["git", "remote", "add", "origin", str(bare)], self.pkos)
        self._write("07-tools/lint_wiki.py", "print('lint ok')\n")
        run(["git", "add", "--", "07-tools/lint_wiki.py"], self.pkos)
        run(["git", "commit", "-m", "initial"], self.pkos)
        self.policy = PkosSyncPolicy(
            repository_path=self.pkos,
            lint_command=["python", "07-tools/lint_wiki.py"],
            remote="origin",
            branch="main",
        )

    def tearDown(self) -> None:
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, rel: str, text: str) -> None:
        path = self.pkos / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")

    def _engine(self) -> PkosSmartSyncEngine:
        return PkosSmartSyncEngine(self.constellation, self.policy)

    def _smoke_changes(self) -> None:
        self._write("00-system/index.md", "production\n")
        self._write("00-system/framework-registry.md", "production\n")
        self._write("00-system/pkos-executive-command-center.md", "production\n")
        self._write("03-operations/aoc/01-dashboard/appraisal-operations-brief.md", "ops\n")
        self._write("03-operations/aoc/05-knowledge/packs/example-knowledge-pack.md", "ops\n")
        self._write("08-research/draft-note.md", "draft\n")
        self._write("08-research/working-analysis.md", "draft\n")
        self._write("misc/new-note.md", "unknown\n")
        self._write("03-operations/aoc/07-automation/intake/incoming/item.json", "{}\n")
        self._write("logs/run.log", "generated\n")
        self._write("00-system/token-secret.md", "api_key = 'do-not-print'\n")

    def test_path_classification(self) -> None:
        self.assertEqual(classify_path("00-system/index.md")[0], "production_knowledge")
        self.assertEqual(classify_path("03-operations/aoc/01-dashboard/brief.md")[0], "governed_operations")
        self.assertEqual(classify_path("03-operations/aoc/brief.md")[0], "unknown")
        self.assertEqual(classify_path("03-operations/aoc/07-automation/intake/incoming/item.json")[0], "runtime_artifact")
        self.assertEqual(classify_path("03-operations/aoc/07-automation/intake/review/item.md")[0], "runtime_artifact")
        self.assertEqual(classify_path("03-operations/aoc/07-automation/intake/approved/item.md")[0], "governed_operations")
        self.assertEqual(classify_path(".obsidian/graph.json")[0], "configuration")
        self.assertEqual(classify_path("2026-07-15.md")[0], "unknown")
        self.assertEqual(classify_path("08-research/draft.md")[0], "draft_research")
        self.assertEqual(classify_path("logs/run.log")[0], "temporary_file")
        self.assertEqual(classify_path("misc/file.md")[0], "unknown")

    def test_preview_counts_and_manifests(self) -> None:
        self._smoke_changes()
        preview = self._engine().preview()
        self.assertEqual(preview.ready_count, 5)
        self.assertEqual(preview.review_count, 3)
        self.assertEqual(preview.excluded_count, 2)
        self.assertEqual(preview.blocked_count, 1)
        output = self.constellation / "outputs" / "pkos-smart-sync"
        self.assertTrue((output / "latest-preview.json").exists())
        self.assertTrue((output / "blocked-manifest.json").exists())
        self.assertNotIn("do-not-print", (output / "latest-preview.md").read_text(encoding="utf-8"))

    def test_repeated_preview_has_stable_id(self) -> None:
        self._smoke_changes()
        engine = self._engine()
        first = engine.preview()
        second = engine.preview()
        self.assertEqual(first.preview_id, second.preview_id)

    def test_stage_only_approved_paths(self) -> None:
        self._write("00-system/index.md", "production\n")
        self._write("03-operations/aoc/01-dashboard/brief.md", "ops\n")
        self._write("08-research/draft-note.md", "draft\n")
        engine = self._engine()
        preview = engine.preview()
        self.assertEqual(preview.ready_count, 2)
        run_result = engine.stage()
        staged = run(["git", "diff", "--cached", "--name-only"], self.pkos).stdout.splitlines()
        self.assertEqual(sorted(staged), sorted(run_result.staged_files))
        self.assertIn("00-system/index.md", staged)
        self.assertIn("03-operations/aoc/01-dashboard/brief.md", staged)
        self.assertNotIn("08-research/draft-note.md", staged)

    def test_specific_runtime_exclusion_wins_over_broad_aoc_stage_override(self) -> None:
        self._write("03-operations/aoc/07-automation/intake/incoming/item.json", "{}\n")
        policy = PkosSyncPolicy(
            repository_path=self.pkos,
            lint_command=["python", "07-tools/lint_wiki.py"],
            remote="origin",
            branch="main",
            overrides=[
                {"pattern": "03-operations/aoc/**", "classification": "governed_operations", "action": "stage", "priority": 10},
                {"pattern": "03-operations/aoc/07-automation/intake/incoming/**", "classification": "runtime_artifact", "action": "exclude", "priority": 100},
            ],
        )
        preview = PkosSmartSyncEngine(self.constellation, policy).preview()
        change = preview.changes[0]
        self.assertEqual(change.classification, "runtime_artifact")
        self.assertEqual(change.recommended_action, "exclude")

    def test_specific_stage_override_wins_over_broad_review_fallback(self) -> None:
        self._write("03-operations/aoc/05-knowledge/packs/final-pack.md", "knowledge\n")
        policy = PkosSyncPolicy(
            repository_path=self.pkos,
            lint_command=["python", "07-tools/lint_wiki.py"],
            remote="origin",
            branch="main",
            overrides=[
                {"pattern": "03-operations/aoc/05-knowledge/packs/**", "classification": "governed_operations", "action": "stage", "priority": 80},
                {"pattern": "03-operations/aoc/**", "classification": "unknown", "action": "review", "priority": 10},
            ],
        )
        preview = PkosSmartSyncEngine(self.constellation, policy).preview()
        change = preview.changes[0]
        self.assertEqual(change.classification, "governed_operations")
        self.assertEqual(change.recommended_action, "stage")

    def test_broad_aoc_override_warning(self) -> None:
        for index in range(21):
            self._write(f"03-operations/aoc/99-broad/file-{index}.md", "ops\n")
        policy = PkosSyncPolicy(
            repository_path=self.pkos,
            lint_command=["python", "07-tools/lint_wiki.py"],
            remote="origin",
            branch="main",
            overrides=[{"pattern": "03-operations/aoc/**", "classification": "governed_operations", "action": "stage", "priority": 10}],
        )
        preview = PkosSmartSyncEngine(self.constellation, policy).preview()
        self.assertTrue(any("03-operations/aoc/**" in warning for warning in preview.warnings))

    def test_preview_contains_subtree_and_reason_summaries(self) -> None:
        self._smoke_changes()
        preview = self._engine().preview()
        self.assertIn("AOC", preview.summary_by_subtree)
        self.assertTrue(preview.top_review_reasons)
        self.assertTrue(preview.top_exclusion_reasons)

    def test_secret_diagnostics_are_redacted_with_line_number(self) -> None:
        self._write("07-tools/aoc_email/gmail_client.py", "client_secret = 'do-not-print'\n")
        preview = self._engine().preview()
        change = preview.changes[0]
        self.assertEqual(change.recommended_action, "block")
        self.assertTrue(any("secret-content:credential-field:line-1" in rule for rule in change.classification_rules))
        report = (self.constellation / "outputs" / "pkos-smart-sync" / "latest-preview.md").read_text(encoding="utf-8")
        self.assertNotIn("do-not-print", report)

    def test_stage_never_stages_blocked_secret(self) -> None:
        self._write("00-system/index.md", "production\n")
        self._write("00-system/token-secret.md", "api_key = 'do-not-print'\n")
        engine = self._engine()
        engine.preview()
        engine.stage()
        staged = run(["git", "diff", "--cached", "--name-only"], self.pkos).stdout.splitlines()
        self.assertIn("00-system/index.md", staged)
        self.assertNotIn("00-system/token-secret.md", staged)

    def test_commit_requires_approval_and_matching_staged_manifest(self) -> None:
        self._write("00-system/index.md", "production\n")
        engine = self._engine()
        engine.preview()
        with self.assertRaises(PkosSmartSyncError):
            engine.commit()
        engine.stage()
        self._write("00-system/extra.md", "extra\n")
        run(["git", "add", "--", "00-system/extra.md"], self.pkos)
        with self.assertRaises(PkosSmartSyncError):
            engine.commit()

    def test_commit_and_local_push(self) -> None:
        self._write("00-system/index.md", "production\n")
        engine = self._engine()
        engine.preview()
        engine.stage()
        commit = engine.commit()
        self.assertEqual(commit.status, "succeeded")
        pushed = engine.push()
        self.assertEqual(pushed.status, "succeeded")

    def test_run_refuses_review_items_without_manual_review(self) -> None:
        self._write("08-research/draft-note.md", "draft\n")
        with self.assertRaises(PkosSmartSyncError):
            self._engine().run(yes=True)

    def test_lint_failure_refuses_stage(self) -> None:
        self._write("07-tools/lint_wiki.py", "import sys\nsys.exit(1)\n")
        self._write("00-system/index.md", "production\n")
        engine = self._engine()
        preview = engine.preview()
        self.assertEqual(preview.lint_result["status"], "failed")
        with self.assertRaises(PkosSmartSyncError):
            engine.stage()

    def test_preexisting_staged_changes_refuse_automatic_stage(self) -> None:
        self._write("00-system/preexisting.md", "production\n")
        run(["git", "add", "--", "00-system/preexisting.md"], self.pkos)
        self._write("00-system/second.md", "production\n")
        engine = self._engine()
        preview = engine.preview()
        self.assertTrue(preview.existing_staged_changes)
        with self.assertRaises(PkosSmartSyncError):
            engine.stage()

    def test_no_change_commit_after_empty_preview(self) -> None:
        engine = self._engine()
        preview = engine.preview()
        self.assertEqual(preview.ready_count, 0)
        engine.stage()
        commit = engine.commit()
        self.assertEqual(commit.status, "no_changes")


if __name__ == "__main__":
    unittest.main()
