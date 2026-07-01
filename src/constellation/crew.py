from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


class CrewError(RuntimeError):
    pass


REQUIRED_CREW_FILES = [
    "profile.md",
    "responsibilities.md",
    "authority.md",
    "communication.md",
    "methodologies.md",
    "memory.md",
    "prompts.md",
]


@dataclass(frozen=True)
class CrewDoctrine:
    role: str
    source_path: str
    profile: str
    responsibilities: str
    authority: str
    communication: str
    methodologies: str
    memory: str
    prompts: str

    def to_dict(self) -> dict[str, str]:
        return {
            "role": self.role,
            "source_path": self.source_path,
            "profile": self.profile,
            "responsibilities": self.responsibilities,
            "authority": self.authority,
            "communication": self.communication,
            "methodologies": self.methodologies,
            "memory": self.memory,
            "prompts": self.prompts,
        }


class CrewLoader:
    def __init__(self, root: Path) -> None:
        self.root = root

    def load(self, role: str) -> CrewDoctrine:
        role_path = self.root / "crew" / role
        if not role_path.exists() or not role_path.is_dir():
            raise CrewError(f"Unknown crew role: {role}")
        missing = [file_name for file_name in REQUIRED_CREW_FILES if not (role_path / file_name).exists()]
        if missing:
            raise CrewError(f"Crew role {role} missing files: {', '.join(missing)}")
        return CrewDoctrine(
            role=role,
            source_path=str(role_path),
            profile=_read(role_path / "profile.md"),
            responsibilities=_read(role_path / "responsibilities.md"),
            authority=_read(role_path / "authority.md"),
            communication=_read(role_path / "communication.md"),
            methodologies=_read(role_path / "methodologies.md"),
            memory=_read(role_path / "memory.md"),
            prompts=_read(role_path / "prompts.md"),
        )


def agent_id_to_crew_role(agent_id: str) -> str:
    return agent_id.replace("_", "-")


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")
