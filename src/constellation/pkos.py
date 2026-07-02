from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .artifacts import ArtifactStore
from .io import read_json, write_json
from .kernel import ConstellationKernel, KernelRunResult
from .memory import MemoryManager
from .models import utc_now_iso
from .state import WorkflowStateStore


class PKOSError(RuntimeError):
    pass


SUPPORTED_PKOS_INPUTS = {".md", ".txt"}
PKOS_WORKFLOW_PATH = Path("workflows/pkos/pkos-ingestion.yaml")
PKOS_PACKAGE_FILES = [
    "source-summary.md",
    "evidence-table.md",
    "proposed-concepts.md",
    "proposed-synthesis.md",
    "proposed-map.md",
    "proposed-source-record.md",
    "validation-review.md",
    "release-notes.md",
    "review-package.md",
    "manifest.json",
]


@dataclass(frozen=True)
class PKOSInput:
    path: Path
    title: str
    text: str
    format: str

    def to_memory_entry(self) -> dict[str, object]:
        return {
            "key": "pkos_source_document",
            "value": {
                "path": str(self.path),
                "title": self.title,
                "format": self.format,
                "text": self.text,
                "character_count": len(self.text),
            },
        }


class PKOSKnowledgeOrganization:
    def __init__(self, root: Path) -> None:
        self.root = root

    def ingest(self, input_path: Path) -> KernelRunResult:
        pkos_input = self.load_input(input_path)
        kernel = ConstellationKernel(self.root)
        return kernel.run_workflow(PKOS_WORKFLOW_PATH, initial_working_entries=[pkos_input.to_memory_entry()])

    def package(self, workflow_run_id: str, *, overwrite: bool = False) -> Path:
        state = WorkflowStateStore(self.root).load(workflow_run_id)
        if state.workflow_id != "pkos_ingestion":
            raise PKOSError(f"Workflow run is not a PKOS ingestion run: {workflow_run_id}")
        output_dir = self._output_dir(workflow_run_id)
        target_paths = [output_dir / name for name in PKOS_PACKAGE_FILES]
        existing = [path for path in target_paths if path.exists()]
        if existing and not overwrite:
            names = ", ".join(path.name for path in existing)
            raise PKOSError(f"PKOS package files already exist. Use --overwrite to replace: {names}")
        output_dir.mkdir(parents=True, exist_ok=True)

        working_memory = read_json(MemoryManager(self.root, workflow_run_id).working_path)
        source = _pkos_source(working_memory)
        artifacts = ArtifactStore(self.root).list(workflow_run_id)
        artifacts_by_output = _artifacts_by_output(artifacts, working_memory)
        approval_status = "approved" if state.status == "completed" else "pending" if state.status == "needs_approval" else state.status

        files = {
            "source-summary.md": _source_summary(source, artifacts_by_output),
            "evidence-table.md": _artifact_markdown("Evidence Table", artifacts_by_output.get("core_claims")),
            "proposed-concepts.md": _proposed_concepts(artifacts_by_output),
            "proposed-synthesis.md": _artifact_markdown("Proposed Synthesis", artifacts_by_output.get("proposed_updates")),
            "proposed-map.md": _artifact_markdown("Proposed Map", artifacts_by_output.get("knowledge_mapping")),
            "proposed-source-record.md": _source_record(source, artifacts_by_output),
            "validation-review.md": _artifact_markdown("Validation Review", artifacts_by_output.get("validation_review")),
            "release-notes.md": _artifact_markdown("Release Notes", artifacts_by_output.get("pkos_release_notes")),
            "review-package.md": _review_package(workflow_run_id, approval_status, source, artifacts_by_output),
        }
        for file_name, content in files.items():
            (output_dir / file_name).write_text(content, encoding="utf-8")

        manifest = {
            "workflow_run_id": workflow_run_id,
            "source_path": source.get("path", "unknown"),
            "source_type": source.get("format", "unknown"),
            "generated_files": PKOS_PACKAGE_FILES,
            "approval_status": approval_status,
            "created_at": utc_now_iso(),
            "warnings": [
                "This package is a proposal only.",
                "No external PKOS or Obsidian vault has been modified.",
            ],
            "limitations": [
                "No PDF parsing.",
                "No web retrieval.",
                "No real citation extraction.",
                "Generated content requires human review.",
            ],
        }
        write_json(output_dir / "manifest.json", manifest)
        return output_dir

    def load_input(self, input_path: Path) -> PKOSInput:
        path = input_path if input_path.is_absolute() else self.root / input_path
        if not path.exists() or not path.is_file():
            raise PKOSError(f"PKOS input file not found: {input_path}")
        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_PKOS_INPUTS:
            raise PKOSError(f"Unsupported PKOS input type: {suffix}. Supported: .md, .txt")
        text = path.read_text(encoding="utf-8")
        return PKOSInput(path=path, title=path.stem.replace("-", " ").replace("_", " ").title(), text=text, format=suffix.removeprefix("."))

    def _output_dir(self, workflow_run_id: str) -> Path:
        return self.root / "outputs" / "pkos" / workflow_run_id


def _pkos_source(working_memory: dict[str, Any]) -> dict[str, Any]:
    entries = working_memory.get("entries", [])
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, dict) and entry.get("key") == "pkos_source_document" and isinstance(entry.get("value"), dict):
                return entry["value"]
    return {"title": "Unknown Source", "path": "unknown", "format": "unknown", "text": "", "character_count": 0}


def _artifacts_by_output(artifacts: list[dict[str, Any]], working_memory: dict[str, Any]) -> dict[str, dict[str, Any]]:
    by_output = {str(item.get("artifact_type")): item for item in artifacts}
    memory_artifacts = working_memory.get("artifacts", {})
    if isinstance(memory_artifacts, dict):
        for output_name, value in memory_artifacts.items():
            if output_name not in by_output and isinstance(value, dict):
                by_output[output_name] = {
                    "artifact_type": output_name,
                    "summary": f"Placeholder output recorded for step `{value.get('step_id', 'unknown')}` with status `{value.get('status', 'unknown')}`.",
                    "key_findings": [],
                    "evidence_used": [],
                    "confidence": "unknown",
                    "assumptions": [],
                    "contradictions": [],
                    "open_questions": [],
                    "implications": [],
                    "recommendations": [],
                    "next_steps": [],
                    "proposed_files": [],
                    "knowledge_actions": [],
                }
    return by_output


def _source_summary(source: dict[str, Any], artifacts: dict[str, dict[str, Any]]) -> str:
    return "\n".join(
        [
            f"# Source Summary: {source.get('title', 'Untitled Source')}",
            "",
            f"- Source path: `{source.get('path', 'unknown')}`",
            f"- Source type: `{source.get('format', 'unknown')}`",
            f"- Characters: `{source.get('character_count', 0)}`",
            "",
            "## Classification",
            _summary(artifacts.get("source_classification")),
            "",
        ]
    )


def _source_record(source: dict[str, Any], artifacts: dict[str, dict[str, Any]]) -> str:
    return "\n".join(
        [
            f"# Proposed Source Record: {source.get('title', 'Untitled Source')}",
            "",
            f"- Path: `{source.get('path', 'unknown')}`",
            f"- Type: `{source.get('format', 'unknown')}`",
            "",
            "## Evidence",
            _list(_format_evidence(artifacts.get("core_claims", {}).get("evidence_used"))),
            "",
            "## Proposed Actions",
            _list(artifacts.get("proposed_updates", {}).get("knowledge_actions")),
            "",
        ]
    )


def _proposed_concepts(artifacts: dict[str, dict[str, Any]]) -> str:
    proposed = artifacts.get("proposed_updates")
    return "\n".join(
        [
            "# Proposed Concepts",
            "",
            _artifact_body(proposed),
            "",
            "## Knowledge Actions",
            _list(proposed.get("knowledge_actions") if proposed else None),
            "",
        ]
    )


def _review_package(workflow_run_id: str, approval_status: str, source: dict[str, Any], artifacts: dict[str, dict[str, Any]]) -> str:
    return "\n".join(
        [
            f"# PKOS Review Package: {source.get('title', 'Untitled Source')}",
            "",
            f"Workflow run: `{workflow_run_id}`",
            f"Approval status: `{approval_status}`",
            "",
            "## Safety Notice",
            "This package is a proposal only. It has not modified any external PKOS or Obsidian vault.",
            "",
            "## Proposed Files",
            _list(_collect(artifacts, "proposed_files")),
            "",
            "## Knowledge Actions",
            _list(_collect(artifacts, "knowledge_actions")),
            "",
            "## Recommendations",
            _list(_collect(artifacts, "recommendations")),
            "",
            "## Open Questions",
            _list(_collect(artifacts, "open_questions")),
            "",
        ]
    )


def _artifact_markdown(title: str, artifact: dict[str, Any] | None) -> str:
    return "\n".join(["# " + title, "", _artifact_body(artifact), ""])


def _artifact_body(artifact: dict[str, Any] | None) -> str:
    return "\n".join(
        [
            "## Summary",
            _summary(artifact),
            "",
            "## Key Findings",
            _list(artifact.get("key_findings") if artifact else None),
            "",
            "## Evidence Used",
            _list(_format_evidence(artifact.get("evidence_used") if artifact else None)),
            "",
            "## Assumptions",
            _list(artifact.get("assumptions") if artifact else None),
            "",
            "## Contradictions",
            _list(artifact.get("contradictions") if artifact else None),
            "",
            "## Implications",
            _list(artifact.get("implications") if artifact else None),
            "",
            "## Recommendations",
            _list(artifact.get("recommendations") if artifact else None),
            "",
            "## Next Steps",
            _list(artifact.get("next_steps") if artifact else None),
            "",
        ]
    )


def _summary(artifact: dict[str, Any] | None) -> str:
    if not artifact:
        return "No artifact was available."
    summary = artifact.get("summary")
    return summary if isinstance(summary, str) and summary else "No summary was recorded."


def _collect(artifacts: dict[str, dict[str, Any]], key: str) -> list[str]:
    collected: list[str] = []
    for artifact in artifacts.values():
        values = artifact.get(key)
        if isinstance(values, list):
            collected.extend(_stringify(value) for value in values)
    return sorted(set(collected))


def _list(value: Any) -> str:
    if not value:
        return "- None recorded."
    if isinstance(value, list):
        return "\n".join(f"- {_stringify(item)}" for item in value)
    return f"- {_stringify(value)}"


def _format_evidence(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [_stringify(item) for item in value]


def _stringify(value: Any) -> str:
    if isinstance(value, dict):
        return ", ".join(f"{key}={item}" for key, item in value.items())
    return str(value)
