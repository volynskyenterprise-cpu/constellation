from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .crew import REQUIRED_CREW_FILES, agent_id_to_crew_role
from .registry import AgentRegistry


FOUNDING_CREW_ROLES = [
    "ceo",
    "research-lead",
    "knowledge-engineer",
    "engineering-manager",
    "designer",
    "qa-lead",
    "documentation-engineer",
    "release-manager",
]


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    message: str
    path: str | None = None

    def to_dict(self) -> dict[str, str | None]:
        return {"code": self.code, "message": self.message, "path": self.path}


@dataclass(frozen=True)
class ValidationReport:
    name: str
    status: str
    checked: list[str]
    issues: list[ValidationIssue]

    @property
    def ok(self) -> bool:
        return self.status == "ok"

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "status": self.status,
            "checked": self.checked,
            "issues": [issue.to_dict() for issue in self.issues],
        }


class CrewValidator:
    def __init__(self, root: Path) -> None:
        self.root = root

    def validate(self, *, allow_orphans: bool = False) -> ValidationReport:
        checked: list[str] = []
        issues: list[ValidationIssue] = []
        crew_dir = self.root / "crew"
        agents_dir = self.root / "agents"
        checked.append(str(crew_dir))

        if not crew_dir.exists() or not crew_dir.is_dir():
            issues.append(ValidationIssue("crew_folder_missing", "Crew folder is missing.", str(crew_dir)))
            return ValidationReport("crew", "failed", checked, issues)

        for role in FOUNDING_CREW_ROLES:
            role_path = crew_dir / role
            checked.append(str(role_path))
            if not role_path.exists() or not role_path.is_dir():
                issues.append(ValidationIssue("founding_crew_folder_missing", f"Founding crew folder is missing: {role}", str(role_path)))
                continue
            for file_name in REQUIRED_CREW_FILES:
                file_path = role_path / file_name
                checked.append(str(file_path))
                if not file_path.exists():
                    issues.append(ValidationIssue("crew_file_missing", f"Crew role {role} missing required file: {file_name}", str(file_path)))

        try:
            registry = AgentRegistry.load_from(agents_dir)
        except Exception as exc:
            issues.append(ValidationIssue("agents_load_failed", f"Agents could not load: {exc}", str(agents_dir)))
            return ValidationReport("crew", "failed", checked, issues)

        mapped_roles = set()
        for agent in registry.all():
            role = agent_id_to_crew_role(agent.id)
            mapped_roles.add(role)
            role_path = crew_dir / role
            checked.append(str(role_path))
            if not role_path.exists() or not role_path.is_dir():
                issues.append(
                    ValidationIssue(
                        "agent_unmapped_to_crew",
                        f"Agent {agent.id} does not map to a crew folder: {role}",
                        agent.source_path,
                    )
                )

        crew_folders = {path.name for path in crew_dir.iterdir() if path.is_dir()}
        orphan_roles = sorted(crew_folders - mapped_roles)
        if orphan_roles and not allow_orphans:
            for role in orphan_roles:
                issues.append(
                    ValidationIssue(
                        "orphan_crew_folder",
                        f"Crew folder has no matching agent definition: {role}",
                        str(crew_dir / role),
                    )
                )

        return ValidationReport("crew", "ok" if not issues else "failed", checked, issues)
