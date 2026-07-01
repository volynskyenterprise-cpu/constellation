from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import read_json, write_json


class MemoryManager:
    def __init__(self, root: Path, workflow_run_id: str) -> None:
        self.root = root
        self.workflow_run_id = workflow_run_id
        self.working_path = root / "memory" / "runs" / f"{workflow_run_id}-working.json"
        self.project_path = root / "memory" / "project" / "kernel-project-memory.json"
        self.knowledge_path = root / "memory" / "knowledge" / "kernel-knowledge-memory.json"
        self.long_term_path = root / "memory" / "long-term" / "kernel-long-term-memory.json"

    def initialize(self, objective: str) -> None:
        if not self.working_path.exists():
            write_json(
                self.working_path,
                {
                    "workflow_run_id": self.workflow_run_id,
                    "objective": objective,
                    "entries": [],
                    "artifacts": {},
                },
            )
        self._ensure_store(self.project_path, "project")
        self._ensure_store(self.knowledge_path, "knowledge")
        self._ensure_store(self.long_term_path, "long_term")

    def add_working_entry(self, key: str, value: Any) -> None:
        data = read_json(self.working_path)
        entries = data.setdefault("entries", [])
        entries.append({"key": key, "value": value})
        write_json(self.working_path, data)

    def set_artifact(self, name: str, value: Any) -> None:
        data = read_json(self.working_path)
        artifacts = data.setdefault("artifacts", {})
        artifacts[name] = value
        write_json(self.working_path, data)

    def context_for_step(self, step_id: str) -> dict[str, Any]:
        working = read_json(self.working_path)
        project = read_json(self.project_path)
        return {
            "summary": f"Working context for step {step_id}.",
            "workflow_state": "Execution",
            "working_memory": working,
            "project_memory": project,
            "memory_references": [
                {"layer": "working", "location": str(self.working_path)},
                {"layer": "project", "location": str(self.project_path)},
            ],
            "artifacts": working.get("artifacts", {}),
            "open_questions": [],
        }

    def project_memory(self) -> dict[str, Any]:
        return read_json(self.project_path)

    def _ensure_store(self, path: Path, layer: str) -> None:
        if not path.exists():
            write_json(path, {"layer": layer, "entries": [], "status": "stub" if layer != "project" else "active"})
