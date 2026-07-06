from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from time import perf_counter
from typing import Any

from . import __version__
from .evidence_graph import EvidenceGraphStore
from .google_drive import GoogleDriveConnector, GoogleDriveDependencyError, GoogleDriveError
from .intake import IntakeEngine, IntakeError
from .io import read_json, write_json
from .memory import InstitutionalMemoryStore
from .models import JsonMap
from .morning import MorningExecutiveError, MorningExecutiveStore
from .source_monitor import SourceMonitorStore
from .thesis_intelligence import ThesisStore as ThesisIntelligenceStore


class DailyPipelineError(RuntimeError):
    pass


@dataclass(frozen=True)
class DailyPipelineRun:
    run_id: str
    status: str
    created_at: str
    completed_at: str
    runtime_seconds: float
    version: str
    stages: list[JsonMap]
    manifest: JsonMap
    limitations: list[str]

    def to_dict(self) -> JsonMap:
        return {
            "run_id": self.run_id,
            "status": self.status,
            "created_at": self.created_at,
            "completed_at": self.completed_at,
            "runtime_seconds": self.runtime_seconds,
            "version": self.version,
            "stages": self.stages,
            "manifest": self.manifest,
            "limitations": self.limitations,
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "DailyPipelineRun":
        return cls(
            run_id=_require_str(data, "run_id"),
            status=_require_str(data, "status"),
            created_at=_require_str(data, "created_at"),
            completed_at=_require_str(data, "completed_at"),
            runtime_seconds=float(data.get("runtime_seconds", 0)),
            version=_require_str(data, "version"),
            stages=_map_list(data.get("stages", [])),
            manifest=_map(data.get("manifest")),
            limitations=_string_list(data.get("limitations", [])),
        )


class DailyPipeline:
    def __init__(self, root: Path) -> None:
        self.root = root

    def run(self, *, overwrite: bool = False) -> DailyPipelineRun:
        start = perf_counter()
        created_at = _now_iso()
        stages: list[JsonMap] = []
        limitations = [
            "Daily Pipeline orchestrates existing deterministic modules only.",
            "No providers, LLM inference, embeddings, semantic search, web retrieval, Gmail, or autonomous decisions are used.",
        ]
        source_monitor = self._source_monitor(stages)
        intake_items = self._intake_scan(stages)
        drive_summary = self._google_drive_sync(stages, limitations)
        morning = self._morning(stages, overwrite)
        snapshot = self._memory_snapshot(stages)
        evidence_graph = self._evidence_graph(stages)
        theses = self._thesis_intelligence(stages)
        completed_at = _now_iso()
        runtime_seconds = round(perf_counter() - start, 6)
        manifest = _manifest(
            intake_items=intake_items,
            drive_summary=drive_summary,
            source_monitor=source_monitor,
            morning=morning,
            snapshot=snapshot,
            evidence_graph=evidence_graph,
            theses=theses,
            runtime_seconds=runtime_seconds,
            created_at=created_at,
            completed_at=completed_at,
        )
        run_id = _run_id(manifest)
        status = "completed" if all(stage["status"] in {"completed", "skipped"} for stage in stages) else "failed"
        return DailyPipelineRun(
            run_id=run_id,
            status=status,
            created_at=created_at,
            completed_at=completed_at,
            runtime_seconds=runtime_seconds,
            version=__version__,
            stages=stages,
            manifest=manifest,
            limitations=limitations,
        )

    def _source_monitor(self, stages: list[JsonMap]) -> JsonMap:
        run = SourceMonitorStore(self.root).run(overwrite=True)
        stages.append(_stage("source_monitoring", "completed", run.summary))
        return run.to_dict()

    def _intake_scan(self, stages: list[JsonMap]) -> list[JsonMap]:
        try:
            items = IntakeEngine(self.root).scan()
        except IntakeError as exc:
            stages.append(_stage("intake_scan", "failed", {"error": str(exc)}))
            return []
        stages.append(_stage("intake_scan", "completed", {"available": len(items)}))
        return [item.to_dict() for item in items]

    def _google_drive_sync(self, stages: list[JsonMap], limitations: list[str]) -> JsonMap:
        connector = GoogleDriveConnector(self.root)
        status = connector.status()
        if not _drive_ready(status):
            reason = _drive_skip_reason(status)
            stages.append(_stage("google_drive_sync", "skipped", {"reason": reason, "status": status}))
            limitations.append(f"Google Drive sync skipped: {reason}")
            return {"status": "skipped", "reason": reason, "downloaded": 0, "skipped": 0, "duplicates": 0, "errors": 0}
        try:
            manifest = connector.sync()
        except (GoogleDriveDependencyError, GoogleDriveError) as exc:
            stages.append(_stage("google_drive_sync", "failed", {"error": str(exc)}))
            return {"status": "failed", "error": str(exc), "downloaded": 0, "skipped": 0, "duplicates": 0, "errors": 1}
        summary = {
            "status": "completed",
            "sync_id": manifest.sync_id,
            "downloaded": len(manifest.downloaded_files),
            "skipped": len(manifest.skipped_files),
            "duplicates": len(manifest.duplicate_files),
            "errors": len(manifest.errors),
        }
        stages.append(_stage("google_drive_sync", "completed", summary))
        return summary

    def _morning(self, stages: list[JsonMap], overwrite: bool) -> JsonMap:
        store = MorningExecutiveStore(self.root)
        try:
            if store.json_path.exists() and not overwrite:
                brief = store.load()
                stages.append(_stage("morning_brief", "completed", {"brief_id": brief.brief_id, "mode": "existing"}))
                return brief.to_dict()
            brief = store.generate(overwrite=overwrite)
        except MorningExecutiveError as exc:
            stages.append(_stage("morning_brief", "failed", {"error": str(exc)}))
            return {}
        stages.append(_stage("morning_brief", "completed", {"brief_id": brief.brief_id, "mode": "generated"}))
        return brief.to_dict()

    def _memory_snapshot(self, stages: list[JsonMap]) -> JsonMap:
        snapshot = InstitutionalMemoryStore(self.root).create_snapshot("daily")
        stages.append(_stage("memory_snapshot", "completed", {"snapshot_id": snapshot.snapshot_id}))
        return snapshot.to_dict()

    def _evidence_graph(self, stages: list[JsonMap]) -> JsonMap:
        graph = EvidenceGraphStore(self.root).build()
        stages.append(_stage("evidence_graph", "completed", {"graph_id": graph.graph_id, "nodes": len(graph.nodes), "edges": len(graph.edges)}))
        return graph.to_dict()

    def _thesis_intelligence(self, stages: list[JsonMap]) -> list[JsonMap]:
        records = ThesisIntelligenceStore(self.root).build()
        stages.append(
            _stage(
                "thesis_intelligence",
                "completed",
                {
                    "thesis_count": len(records),
                    "supporting_relationships": sum(len(record.supporting_evidence_ids) for record in records),
                    "conflicts": sum(len(record.conflicting_evidence_ids) for record in records),
                },
            )
        )
        return [record.to_dict() for record in records]


class DailyPipelineStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "outputs" / "daily"
        self.run_path = self.directory / "daily-run.json"
        self.report_path = self.directory / "daily-report.md"
        self.history_path = self.directory / "daily-history.json"
        self.manifest_path = self.directory / "daily-manifest.json"

    def run(self, *, overwrite: bool = False) -> DailyPipelineRun:
        if self.run_path.exists() and not overwrite:
            raise DailyPipelineError("Daily run already exists. Use --overwrite to replace the current daily-run.json.")
        run = DailyPipeline(self.root).run(overwrite=overwrite)
        self.save(run)
        return run

    def save(self, run: DailyPipelineRun) -> None:
        write_json(self.run_path, run.to_dict())
        write_json(self.manifest_path, run.manifest)
        history = self.history()
        history.append(run)
        write_json(self.history_path, {"runs": [item.to_dict() for item in history]})
        self.export(run)

    def load(self) -> DailyPipelineRun:
        if not self.run_path.exists():
            raise DailyPipelineError("No daily pipeline run found. Run `python -m constellation daily` first.")
        return DailyPipelineRun.from_dict(read_json(self.run_path))

    def history(self) -> list[DailyPipelineRun]:
        if not self.history_path.exists():
            return []
        data = read_json(self.history_path)
        return [DailyPipelineRun.from_dict(item) for item in _map_list(data.get("runs", []))]

    def export(self, run: DailyPipelineRun | None = None) -> Path:
        run = run or self.load()
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(render_daily_report(run), encoding="utf-8")
        return self.report_path


def render_daily_report(run: DailyPipelineRun) -> str:
    manifest = run.manifest
    lines = [
        "# Daily Intelligence Pipeline",
        "",
        f"- Run ID: `{run.run_id}`",
        f"- Status: `{run.status}`",
        f"- Timestamp: `{run.completed_at}`",
        f"- Runtime: `{run.runtime_seconds}` seconds",
        f"- Version: `{run.version}`",
        "",
        "## Summary",
        "",
        f"- Sources checked: {_map(manifest.get('source_monitor_summary')).get('sources_checked', 0)}",
        f"- Sources changed: {_map(manifest.get('source_monitor_summary')).get('sources_changed', 0)}",
        f"- Intake files processed: {manifest.get('intake_files_processed', 0)}",
        f"- Google Drive sync: `{_map(manifest.get('google_drive_sync')).get('status', 'unknown')}`",
        f"- Morning brief ID: `{manifest.get('morning_brief_id') or ''}`",
        f"- Memory snapshot ID: `{manifest.get('memory_snapshot_id') or ''}`",
        f"- Evidence graph ID: `{manifest.get('evidence_graph_id') or ''}`",
        f"- Thesis count: {manifest.get('thesis_count', 0)}",
        f"- Evidence count: {manifest.get('evidence_count', 0)}",
        f"- Graph nodes: {manifest.get('graph_nodes', 0)}",
        f"- Graph edges: {manifest.get('graph_edges', 0)}",
        "",
        "## Stages",
        "",
    ]
    for stage in run.stages:
        lines.append(f"- `{stage.get('name')}`: `{stage.get('status')}`")
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in run.limitations)
    lines.append("")
    return "\n".join(lines)


def _manifest(
    *,
    intake_items: list[JsonMap],
    drive_summary: JsonMap,
    source_monitor: JsonMap,
    morning: JsonMap,
    snapshot: JsonMap,
    evidence_graph: JsonMap,
    theses: list[JsonMap],
    runtime_seconds: float,
    created_at: str,
    completed_at: str,
) -> JsonMap:
    evidence_count = _int(morning.get("evidence_count"))
    return {
        "manifest_id": _daily_manifest_id(intake_items, drive_summary, source_monitor, morning, snapshot, evidence_graph, theses),
        "created_at": created_at,
        "completed_at": completed_at,
        "version": __version__,
        "intake_files_processed": len(intake_items),
        "source_monitor_id": source_monitor.get("monitor_id"),
        "source_monitor_summary": source_monitor.get("summary", {}),
        "google_drive_sync": drive_summary,
        "morning_brief_id": morning.get("brief_id"),
        "memory_snapshot_id": snapshot.get("snapshot_id"),
        "evidence_graph_id": evidence_graph.get("graph_id"),
        "thesis_count": len(theses),
        "evidence_count": evidence_count,
        "graph_nodes": evidence_graph.get("node_count", 0),
        "graph_edges": evidence_graph.get("edge_count", 0),
        "runtime_seconds": runtime_seconds,
    }


def _stage(name: str, status: str, details: JsonMap) -> JsonMap:
    return {"name": name, "status": status, "details": details}


def _drive_ready(status: JsonMap) -> bool:
    return (
        status.get("config_present") is True
        and status.get("dependencies_installed") is True
        and status.get("credentials_path_configured") is True
        and status.get("token_path_configured") is True
        and bool(status.get("enabled_sources"))
    )


def _drive_skip_reason(status: JsonMap) -> str:
    if not status.get("config_present"):
        return "configuration missing"
    if not status.get("dependencies_installed"):
        return "optional dependencies missing"
    if not status.get("credentials_path_configured") or not status.get("token_path_configured"):
        return "credentials or token path not configured"
    if not status.get("enabled_sources"):
        return "no enabled Google Drive sources"
    return "not ready"


def _run_id(manifest: JsonMap) -> str:
    return f"daily_{_digest(str(manifest.get('manifest_id')) + '|' + str(manifest.get('completed_at')))}"


def _daily_manifest_id(
    intake_items: list[JsonMap],
    drive_summary: JsonMap,
    source_monitor: JsonMap,
    morning: JsonMap,
    snapshot: JsonMap,
    evidence_graph: JsonMap,
    theses: list[JsonMap],
) -> str:
    fingerprint = "|".join(
        [
            ",".join(sorted(str(item.get("item_id")) for item in intake_items)),
            str(drive_summary.get("sync_id")),
            str(source_monitor.get("monitor_id")),
            str(morning.get("brief_id")),
            str(snapshot.get("snapshot_id")),
            str(evidence_graph.get("graph_id")),
            ",".join(sorted(str(item.get("thesis_id")) for item in theses)),
        ]
    )
    return f"daily_manifest_{_digest(fingerprint)}"


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:16]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _map(value: Any) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _map_list(value: Any) -> list[JsonMap]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, str)]


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


def _require_str(data: JsonMap, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise DailyPipelineError(f"Daily pipeline field {key} must be a string")
    return value
