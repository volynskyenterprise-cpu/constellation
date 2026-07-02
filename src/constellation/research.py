from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .artifacts import ArtifactStore
from .io import read_json
from .kernel import ConstellationKernel, KernelRunResult
from .memory import MemoryManager
from .state import WorkflowStateStore


class ResearchError(RuntimeError):
    pass


SUPPORTED_RESEARCH_INPUTS = {".md", ".txt"}
RESEARCH_WORKFLOW_PATH = Path("workflows/research/institutional-research.yaml")


@dataclass(frozen=True)
class ResearchInput:
    path: Path
    title: str
    text: str
    format: str

    def to_memory_entry(self) -> dict[str, object]:
        return {
            "key": "research_source_document",
            "value": {
                "path": str(self.path),
                "title": self.title,
                "format": self.format,
                "text": self.text,
                "character_count": len(self.text),
            },
        }


class ResearchOrganization:
    def __init__(self, root: Path) -> None:
        self.root = root

    def run(self, input_path: Path) -> KernelRunResult:
        research_input = self.load_input(input_path)
        kernel = ConstellationKernel(self.root)
        return kernel.run_workflow(RESEARCH_WORKFLOW_PATH, initial_working_entries=[research_input.to_memory_entry()])

    def export(self, workflow_run_id: str) -> Path:
        state = WorkflowStateStore(self.root).load(workflow_run_id)
        if state.workflow_id != "institutional_research":
            raise ResearchError(f"Workflow run is not an institutional research run: {workflow_run_id}")
        artifacts = ArtifactStore(self.root).list(workflow_run_id)
        working_memory = read_json(MemoryManager(self.root, workflow_run_id).working_path)
        source = _research_source(working_memory)
        approval_status = "approved" if state.status == "completed" else "pending" if state.status == "needs_approval" else state.status
        report = _render_report(
            workflow_run_id=workflow_run_id,
            approval_status=approval_status,
            source=source,
            artifacts_by_step={str(item.get("step_id")): item for item in artifacts},
            memory_artifacts=working_memory.get("artifacts", {}) if isinstance(working_memory.get("artifacts"), dict) else {},
        )
        output_path = self.root / "outputs" / "research" / f"{workflow_run_id}-report.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        return output_path

    def load_input(self, input_path: Path) -> ResearchInput:
        path = input_path if input_path.is_absolute() else self.root / input_path
        if not path.exists() or not path.is_file():
            raise ResearchError(f"Research input file not found: {input_path}")
        suffix = path.suffix.lower()
        if suffix not in SUPPORTED_RESEARCH_INPUTS:
            raise ResearchError(f"Unsupported research input type: {suffix}. Supported: .md, .txt")
        text = path.read_text(encoding="utf-8")
        return ResearchInput(path=path, title=path.stem.replace("-", " ").replace("_", " ").title(), text=text, format=suffix.removeprefix("."))


def _research_source(working_memory: dict[str, Any]) -> dict[str, Any]:
    entries = working_memory.get("entries", [])
    if isinstance(entries, list):
        for entry in entries:
            if isinstance(entry, dict) and entry.get("key") == "research_source_document" and isinstance(entry.get("value"), dict):
                return entry["value"]
    return {"title": "Unknown Source", "path": "unknown", "text": "", "character_count": 0}


def _render_report(
    *,
    workflow_run_id: str,
    approval_status: str,
    source: dict[str, Any],
    artifacts_by_step: dict[str, dict[str, Any]],
    memory_artifacts: dict[str, Any],
) -> str:
    report = artifacts_by_step.get("produce_research_report", {})
    evidence = artifacts_by_step.get("extract_evidence", {})
    implications = artifacts_by_step.get("map_knowledge_implications", {})
    challenge = artifacts_by_step.get("challenge_findings", {})
    objective = artifacts_by_step.get("frame_research_objective", {})
    lines = [
        f"# Executive Research Report: {source.get('title', 'Untitled Source')}",
        "",
        f"Workflow run: `{workflow_run_id}`",
        f"Approval status: `{approval_status}`",
        "",
        "## Executive Summary",
        _summary(report, memory_artifacts.get("executive_research_report")),
        "",
        "## Source Document Reference",
        f"- Path: `{source.get('path', 'unknown')}`",
        f"- Format: `{source.get('format', 'unknown')}`",
        f"- Characters: `{source.get('character_count', 0)}`",
        "",
        "## Research Objective",
        _summary(objective, memory_artifacts.get("research_objective_brief")),
        "",
        "## Evidence Table",
        _artifact_section(evidence, memory_artifacts.get("evidence_table")),
        "",
        "## Knowledge Implications",
        _artifact_section(implications, memory_artifacts.get("knowledge_implications")),
        "",
        "## QA Challenge",
        _artifact_section(challenge, memory_artifacts.get("validation_challenge")),
        "",
        "## Final Recommendations",
        _list(report.get("recommendations")),
        "",
        "## Risks And Uncertainty",
        _list(report.get("risks")) + "\n" + _list(report.get("contradictions")),
        "",
        "## Open Questions",
        _list(report.get("open_questions")),
        "",
        "## Next Steps",
        _list(report.get("next_steps")),
        "",
        "## Approval Status",
        approval_status,
        "",
    ]
    return "\n".join(lines)


def _artifact_section(artifact: dict[str, Any], memory_value: Any) -> str:
    if artifact:
        parts = [
            _summary(artifact, memory_value),
            "",
            "Key findings:",
            _list(artifact.get("key_findings")),
            "",
            "Evidence used:",
            _list(_format_evidence(artifact.get("evidence_used"))),
            "",
            "Implications:",
            _list(artifact.get("implications")),
        ]
        return "\n".join(parts)
    return _summary({}, memory_value)


def _summary(artifact: dict[str, Any], memory_value: Any) -> str:
    summary = artifact.get("summary")
    if isinstance(summary, str) and summary:
        return summary
    if isinstance(memory_value, dict):
        status = memory_value.get("status", "unknown")
        step_id = memory_value.get("step_id", "unknown")
        return f"Placeholder output recorded for step `{step_id}` with status `{status}`."
    return "No artifact was available."


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
