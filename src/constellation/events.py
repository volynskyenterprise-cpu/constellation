from __future__ import annotations

from pathlib import Path
from typing import Any

from .io import append_jsonl
from .models import Event, new_id, utc_now_iso


class EventBus:
    def __init__(self, root: Path, workflow_run_id: str) -> None:
        self.root = root
        self.workflow_run_id = workflow_run_id
        self.log_path = root / "logs" / "runs" / workflow_run_id / "events.jsonl"

    def emit(
        self,
        event_type: str,
        *,
        workflow_id: str | None,
        actor: dict[str, Any],
        subject: dict[str, Any],
        summary: str,
        data: dict[str, Any] | None = None,
        references: list[dict[str, Any]] | None = None,
        correlation_id: str | None = None,
        causation_id: str | None = None,
        severity: str = "info",
    ) -> Event:
        event = Event(
            id=new_id("evt"),
            type=event_type,
            timestamp=utc_now_iso(),
            workflow_id=workflow_id,
            workflow_run_id=self.workflow_run_id,
            actor=actor,
            subject=subject,
            summary=summary,
            data=data or {},
            references=references or [],
            correlation_id=correlation_id,
            causation_id=causation_id,
            severity=severity,
        )
        append_jsonl(self.log_path, event.to_dict())
        return event
