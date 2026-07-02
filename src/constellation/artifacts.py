from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .io import read_json, write_json
from .models import JsonMap, utc_now_iso


class ArtifactError(RuntimeError):
    pass


@dataclass(frozen=True)
class AgentArtifact:
    artifact_id: str
    workflow_run_id: str
    workflow_id: str
    step_id: str
    agent_id: str
    crew_role: str
    artifact_type: str
    title: str
    summary: str
    findings: list[JsonMap]
    recommendations: list[str]
    risks: list[str]
    assumptions: list[str]
    evidence_used: list[JsonMap]
    next_steps: list[str]
    confidence: str
    status: str
    provider_result_id: str | None
    prompt_package_id: str | None
    created_at: str
    key_findings: list[str] = field(default_factory=list)
    contradictions: list[str] = field(default_factory=list)
    open_questions: list[str] = field(default_factory=list)
    implications: list[str] = field(default_factory=list)
    proposed_files: list[str] = field(default_factory=list)
    knowledge_actions: list[str] = field(default_factory=list)

    def to_dict(self) -> JsonMap:
        return {
            "artifact_id": self.artifact_id,
            "workflow_run_id": self.workflow_run_id,
            "workflow_id": self.workflow_id,
            "step_id": self.step_id,
            "agent_id": self.agent_id,
            "crew_role": self.crew_role,
            "artifact_type": self.artifact_type,
            "title": self.title,
            "summary": self.summary,
            "findings": self.findings,
            "recommendations": self.recommendations,
            "risks": self.risks,
            "assumptions": self.assumptions,
            "evidence_used": self.evidence_used,
            "next_steps": self.next_steps,
            "confidence": self.confidence,
            "status": self.status,
            "provider_result_id": self.provider_result_id,
            "prompt_package_id": self.prompt_package_id,
            "created_at": self.created_at,
            "key_findings": self.key_findings,
            "contradictions": self.contradictions,
            "open_questions": self.open_questions,
            "implications": self.implications,
            "proposed_files": self.proposed_files,
            "knowledge_actions": self.knowledge_actions,
        }


class ArtifactParser:
    def parse(self, *, provider_result: JsonMap, prompt_package: JsonMap) -> AgentArtifact:
        try:
            return self._parse(provider_result=provider_result, prompt_package=prompt_package)
        except Exception as exc:
            return self.failed_artifact(provider_result=provider_result, prompt_package=prompt_package, error=str(exc))

    def failed_artifact(self, *, provider_result: JsonMap, prompt_package: JsonMap, error: str) -> AgentArtifact:
        return AgentArtifact(
            artifact_id=_artifact_id(prompt_package),
            workflow_run_id=_string(prompt_package.get("workflow_run_id"), "unknown_run"),
            workflow_id=_string(prompt_package.get("workflow_id"), "unknown_workflow"),
            step_id=_string(prompt_package.get("step_id"), "unknown_step"),
            agent_id=_string(prompt_package.get("agent_id"), "unknown_agent"),
            crew_role=_string(prompt_package.get("crew_role"), "unknown_role"),
            artifact_type=_artifact_type(prompt_package),
            title=f"Failed artifact for {_string(prompt_package.get('step_id'), 'unknown_step')}",
            summary=f"Provider output could not be parsed into a structured artifact: {error}",
            findings=[],
            recommendations=["Review provider output and rerun the workflow step."],
            risks=[error],
            assumptions=[],
            evidence_used=[],
            next_steps=["Resolve the provider or parser failure before using this artifact."],
            confidence="none",
            status="failed",
            provider_result_id=_provider_result_id(provider_result),
            prompt_package_id=_string_or_none(prompt_package.get("prompt_id")),
            created_at=utc_now_iso(),
            key_findings=[],
            contradictions=[error],
            open_questions=["What caused the provider output parsing failure?"],
            implications=["This artifact should not be used for professional judgment until repaired."],
            proposed_files=[],
            knowledge_actions=[],
        )

    def _parse(self, *, provider_result: JsonMap, prompt_package: JsonMap) -> AgentArtifact:
        output_text = provider_result.get("output_text")
        if not isinstance(output_text, str):
            raise ArtifactError("provider output_text must be a string")
        if provider_result.get("status") != "completed":
            return self.failed_artifact(
                provider_result=provider_result,
                prompt_package=prompt_package,
                error=_string(provider_result.get("error"), "provider did not complete"),
            )
        step_id = _required_string(prompt_package, "step_id")
        agent_id = _required_string(prompt_package, "agent_id")
        crew_role = _required_string(prompt_package, "crew_role")
        workflow_run_id = _required_string(prompt_package, "workflow_run_id")
        workflow_id = _required_string(prompt_package, "workflow_id")
        prompt_id = _required_string(prompt_package, "prompt_id")
        expected_output = _expected_output(prompt_package)
        key_findings = [
            f"{crew_role} completed {expected_output}.",
            "Output was generated through the configured provider path.",
        ]
        proposed_files = _proposed_files(expected_output)
        knowledge_actions = _knowledge_actions(expected_output)
        return AgentArtifact(
            artifact_id=_artifact_id(prompt_package),
            workflow_run_id=workflow_run_id,
            workflow_id=workflow_id,
            step_id=step_id,
            agent_id=agent_id,
            crew_role=crew_role,
            artifact_type=_artifact_type(prompt_package),
            title=f"{crew_role} artifact for {expected_output}",
            summary=f"Deterministic {provider_result.get('provider_name')} output for workflow step {step_id}.",
            findings=[
                {
                    "label": "provider_output",
                    "value": output_text,
                    "source": _string(provider_result.get("provider_name"), "provider"),
                },
                {
                    "label": "crew_role",
                    "value": crew_role,
                    "source": "prompt_package",
                },
                {
                    "label": "expected_output",
                    "value": expected_output,
                    "source": "workflow_step",
                },
            ],
            recommendations=[
                f"Review {expected_output} against {crew_role} authority and methodology.",
            ],
            risks=[
                "EchoProvider is deterministic and does not perform real external reasoning.",
            ],
            assumptions=[
                "Provider-backed execution is operating in stub mode.",
                "The prompt package is the authoritative execution context for this artifact.",
            ],
            evidence_used=[
                {"type": "prompt_package", "id": prompt_id},
                {"type": "provider_result", "id": _provider_result_id(provider_result)},
            ],
            next_steps=[
                "Proceed to the next workflow step or required human approval gate.",
            ],
            confidence="medium",
            status="completed",
            provider_result_id=_provider_result_id(provider_result),
            prompt_package_id=prompt_id,
            created_at=utc_now_iso(),
            key_findings=key_findings,
            contradictions=[],
            open_questions=["What evidence should be verified by a human reviewer before relying on this output?"],
            implications=[f"{expected_output} is available for downstream workflow steps."],
            proposed_files=proposed_files,
            knowledge_actions=knowledge_actions,
        )


class ArtifactStore:
    def __init__(self, root: Path) -> None:
        self.root = root

    def persist(self, artifact: AgentArtifact) -> Path:
        path = self.path_for(artifact.workflow_run_id, artifact.artifact_id)
        write_json(path, artifact.to_dict())
        return path

    def list(self, workflow_run_id: str) -> list[JsonMap]:
        directory = self.root / "logs" / "runs" / workflow_run_id / "artifacts"
        if not directory.exists():
            return []
        artifacts: list[JsonMap] = []
        for path in sorted(directory.glob("*.json")):
            try:
                data = read_json(path)
            except Exception:
                continue
            if isinstance(data, dict):
                artifacts.append(data)
        return sorted(artifacts, key=lambda item: str(item.get("created_at", "")), reverse=True)

    def show(self, workflow_run_id: str, artifact_id: str) -> JsonMap:
        path = self.path_for(workflow_run_id, artifact_id.removesuffix(".json"))
        if not path.exists():
            raise ArtifactError(f"Unknown artifact for run {workflow_run_id}: {artifact_id}")
        data = read_json(path)
        if not isinstance(data, dict):
            raise ArtifactError(f"Artifact is corrupt: {artifact_id}")
        return data

    def path_for(self, workflow_run_id: str, artifact_id: str) -> Path:
        return self.root / "logs" / "runs" / workflow_run_id / "artifacts" / f"{artifact_id}.json"


def _artifact_id(prompt_package: JsonMap) -> str:
    return f"artifact_{_string(prompt_package.get('workflow_run_id'), 'unknown_run')}_{_string(prompt_package.get('step_id'), 'unknown_step')}"


def _artifact_type(prompt_package: JsonMap) -> str:
    expected_output = _expected_output(prompt_package)
    research_types = {
        "research_objective_brief",
        "evidence_table",
        "knowledge_implications",
        "validation_challenge",
        "executive_research_report",
        "source_classification",
        "core_claims",
        "knowledge_mapping",
        "proposed_updates",
        "pkos_review_package",
        "pkos_release_notes",
    }
    if expected_output in research_types:
        return expected_output
    metadata = prompt_package.get("metadata")
    if isinstance(metadata, dict):
        step_type = metadata.get("step_type")
        if isinstance(step_type, str) and step_type:
            return step_type
    return "agent_output"


def _expected_output(prompt_package: JsonMap) -> str:
    output_contract = prompt_package.get("output_contract")
    if isinstance(output_contract, dict):
        expected_output = output_contract.get("expected_output")
        if isinstance(expected_output, str) and expected_output:
            return expected_output
    return _string(prompt_package.get("step_id"), "agent_output")


def _provider_result_id(provider_result: JsonMap) -> str | None:
    result_id = provider_result.get("provider_result_id")
    if isinstance(result_id, str):
        return result_id
    metadata = provider_result.get("metadata")
    if isinstance(metadata, dict) and isinstance(metadata.get("provider_result_id"), str):
        return metadata["provider_result_id"]
    provider_name = provider_result.get("provider_name")
    message_id = provider_result.get("input_message_id")
    if isinstance(provider_name, str) and isinstance(message_id, str):
        return f"provider_result_{message_id}_{provider_name}"
    return None


def _proposed_files(expected_output: str) -> list[str]:
    files_by_output = {
        "source_classification": ["source-summary.md"],
        "core_claims": ["evidence-table.md"],
        "knowledge_mapping": ["proposed-map.md"],
        "proposed_updates": ["proposed-concepts.md", "proposed-synthesis.md", "proposed-map.md", "proposed-source-record.md"],
        "validation_review": ["validation-review.md"],
        "pkos_review_package": ["review-package.md"],
        "pkos_release_notes": ["release-notes.md"],
    }
    return files_by_output.get(expected_output, [])


def _knowledge_actions(expected_output: str) -> list[str]:
    actions_by_output = {
        "source_classification": ["add_source_record"],
        "core_claims": ["strengthen_concept"],
        "knowledge_mapping": ["update_map"],
        "proposed_updates": ["create_concept", "update_concept", "create_synthesis", "create_map", "add_source_record"],
        "validation_review": ["strengthen_concept", "weaken_concept"],
        "pkos_review_package": ["create_concept", "create_synthesis", "create_map", "add_source_record"],
        "pkos_release_notes": ["add_source_record"],
    }
    return actions_by_output.get(expected_output, [])


def _required_string(mapping: JsonMap, key: str) -> str:
    value = mapping.get(key)
    if not isinstance(value, str) or not value:
        raise ArtifactError(f"prompt package missing required field: {key}")
    return value


def _string(value: Any, default: str) -> str:
    return value if isinstance(value, str) and value else default


def _string_or_none(value: Any) -> str | None:
    return value if isinstance(value, str) and value else None
