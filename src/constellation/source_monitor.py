from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from . import __version__
from .io import read_json, write_json
from .models import JsonMap
from .simple_yaml import load_yaml


class SourceMonitorError(RuntimeError):
    pass


STATUS_UNCHANGED = "UNCHANGED"
STATUS_NEW = "NEW ITEMS"
STATUS_REMOVED = "REMOVED ITEMS"
STATUS_UPDATED = "UPDATED ITEMS"
STATUS_FAILED = "FAILED"
STATUS_UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class SourceSnapshot:
    source_id: str
    source_type: str
    timestamp: str
    item_count: int
    newest_modified_timestamp: str | None
    fingerprint: str
    previous_fingerprint: str | None
    status: str
    items: list[JsonMap]
    metadata: JsonMap

    def to_dict(self) -> JsonMap:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "timestamp": self.timestamp,
            "item_count": self.item_count,
            "newest_modified_timestamp": self.newest_modified_timestamp,
            "fingerprint": self.fingerprint,
            "previous_fingerprint": self.previous_fingerprint,
            "status": self.status,
            "items": self.items,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "SourceSnapshot":
        return cls(
            source_id=_require_str(data, "source_id"),
            source_type=_require_str(data, "source_type"),
            timestamp=_require_str(data, "timestamp"),
            item_count=_int(data.get("item_count")),
            newest_modified_timestamp=_optional_str(data.get("newest_modified_timestamp")),
            fingerprint=_require_str(data, "fingerprint"),
            previous_fingerprint=_optional_str(data.get("previous_fingerprint")),
            status=_require_str(data, "status"),
            items=_map_list(data.get("items", [])),
            metadata=_map(data.get("metadata")),
        )


@dataclass(frozen=True)
class SourceChange:
    source_id: str
    source_type: str
    status: str
    new_items: list[str]
    removed_items: list[str]
    updated_items: list[str]
    failed_items: list[str]
    recommended_refreshes: list[str]

    def to_dict(self) -> JsonMap:
        return {
            "source_id": self.source_id,
            "source_type": self.source_type,
            "status": self.status,
            "new_items": self.new_items,
            "removed_items": self.removed_items,
            "updated_items": self.updated_items,
            "failed_items": self.failed_items,
            "recommended_refreshes": self.recommended_refreshes,
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "SourceChange":
        return cls(
            source_id=_require_str(data, "source_id"),
            source_type=_require_str(data, "source_type"),
            status=_require_str(data, "status"),
            new_items=_string_list(data.get("new_items", [])),
            removed_items=_string_list(data.get("removed_items", [])),
            updated_items=_string_list(data.get("updated_items", [])),
            failed_items=_string_list(data.get("failed_items", [])),
            recommended_refreshes=_string_list(data.get("recommended_refreshes", [])),
        )


@dataclass(frozen=True)
class SourceMonitorRun:
    monitor_id: str
    created_at: str
    version: str
    snapshots: list[SourceSnapshot]
    changes: list[SourceChange]
    summary: JsonMap
    limitations: list[str]

    def to_dict(self) -> JsonMap:
        return {
            "monitor_id": self.monitor_id,
            "created_at": self.created_at,
            "version": self.version,
            "snapshots": [snapshot.to_dict() for snapshot in self.snapshots],
            "changes": [change.to_dict() for change in self.changes],
            "summary": self.summary,
            "limitations": self.limitations,
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "SourceMonitorRun":
        return cls(
            monitor_id=_require_str(data, "monitor_id"),
            created_at=_require_str(data, "created_at"),
            version=_require_str(data, "version"),
            snapshots=[SourceSnapshot.from_dict(item) for item in _map_list(data.get("snapshots", []))],
            changes=[SourceChange.from_dict(item) for item in _map_list(data.get("changes", []))],
            summary=_map(data.get("summary")),
            limitations=_string_list(data.get("limitations", [])),
        )


class SourceMonitor:
    def __init__(self, root: Path) -> None:
        self.root = root

    def run(self, previous: SourceMonitorRun | None = None) -> SourceMonitorRun:
        created_at = _now_iso()
        previous_by_id = {snapshot.source_id: snapshot for snapshot in previous.snapshots} if previous else {}
        snapshots: list[SourceSnapshot] = []
        changes: list[SourceChange] = []
        for source in self._sources():
            snapshot = self._snapshot(source, created_at, previous_by_id.get(source["source_id"]))
            change = _change_for(snapshot, previous_by_id.get(source["source_id"]))
            snapshots.append(snapshot)
            changes.append(change)
        summary = _summary(changes)
        monitor_id = _monitor_id(snapshots, changes)
        return SourceMonitorRun(
            monitor_id=monitor_id,
            created_at=created_at,
            version=__version__,
            snapshots=sorted(snapshots, key=lambda item: item.source_id),
            changes=sorted(changes, key=lambda item: item.source_id),
            summary=summary,
            limitations=[
                "Source Monitoring is deterministic and local.",
                "Google Drive sources are monitored from configuration only; no remote API call is made.",
                "No providers, LLM inference, embeddings, semantic search, web retrieval, Gmail, scheduling, or autonomous workflow execution are used.",
            ],
        )

    def _sources(self) -> list[JsonMap]:
        sources = [
            {"source_id": "local_intake_google_drive", "source_type": "local_intake_folder", "path": "inbox/google-drive/incoming"},
            {"source_id": "local_intake_gmail", "source_type": "local_intake_folder", "path": "inbox/gmail/incoming"},
            {"source_id": "local_intake_manual", "source_type": "local_intake_folder", "path": "inbox/manual/incoming"},
            {"source_id": "local_evidence_files", "source_type": "local_evidence_files", "path": "memory/evidence"},
            {"source_id": "local_thesis_files", "source_type": "local_thesis_files", "paths": ["outputs/thesis", "outputs/theses"]},
            {"source_id": "local_configuration_files", "source_type": "local_configuration_files", "path": "config"},
        ]
        sources.extend(self._configured_google_drive_sources())
        return sorted(sources, key=lambda item: str(item["source_id"]))

    def _configured_google_drive_sources(self) -> list[JsonMap]:
        path = self.root / "config" / "sources.yaml"
        if not path.exists():
            return []
        try:
            data = load_yaml(path)
        except Exception:
            return [{"source_id": "configured_sources", "source_type": "configuration", "status_override": STATUS_FAILED, "error": "config/sources.yaml could not be parsed"}]
        configured = []
        for source in data.get("sources", []):
            if isinstance(source, dict) and source.get("source_type") == "google_drive":
                source_id = str(source.get("id") or "unknown")
                configured.append(
                    {
                        "source_id": f"google_drive_{source_id}",
                        "source_type": "google_drive_folder",
                        "config": source,
                        "status_override": STATUS_UNKNOWN,
                    }
                )
        return configured

    def _snapshot(self, source: JsonMap, timestamp: str, previous: SourceSnapshot | None) -> SourceSnapshot:
        if source.get("status_override") == STATUS_UNKNOWN:
            item = _config_item(source.get("config", {}))
            fingerprint = _fingerprint([item])
            return SourceSnapshot(
                source_id=str(source["source_id"]),
                source_type=str(source["source_type"]),
                timestamp=timestamp,
                item_count=1,
                newest_modified_timestamp=None,
                fingerprint=fingerprint,
                previous_fingerprint=previous.fingerprint if previous else None,
                status=STATUS_UNKNOWN,
                items=[item],
                metadata={"reason": "Configured Google Drive source; remote content is not inspected."},
            )
        if source.get("status_override") == STATUS_FAILED:
            return SourceSnapshot(
                source_id=str(source["source_id"]),
                source_type=str(source["source_type"]),
                timestamp=timestamp,
                item_count=0,
                newest_modified_timestamp=None,
                fingerprint="failed",
                previous_fingerprint=previous.fingerprint if previous else None,
                status=STATUS_FAILED,
                items=[],
                metadata={"error": source.get("error", "source failed")},
            )
        try:
            paths = [self.root / str(path) for path in source.get("paths", [])] if isinstance(source.get("paths"), list) else [self.root / str(source.get("path", ""))]
            items = _scan_paths(self.root, paths)
            fingerprint = _fingerprint(items)
            status = _status_for(items, fingerprint, previous)
            return SourceSnapshot(
                source_id=str(source["source_id"]),
                source_type=str(source["source_type"]),
                timestamp=timestamp,
                item_count=len(items),
                newest_modified_timestamp=_newest_modified(items),
                fingerprint=fingerprint,
                previous_fingerprint=previous.fingerprint if previous else None,
                status=status,
                items=items,
                metadata={"paths": [str(path.relative_to(self.root)) if path.exists() else str(path) for path in paths]},
            )
        except Exception as exc:
            return SourceSnapshot(
                source_id=str(source["source_id"]),
                source_type=str(source["source_type"]),
                timestamp=timestamp,
                item_count=0,
                newest_modified_timestamp=None,
                fingerprint="failed",
                previous_fingerprint=previous.fingerprint if previous else None,
                status=STATUS_FAILED,
                items=[],
                metadata={"error": str(exc)},
            )


class SourceMonitorStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "outputs" / "source-monitor"
        self.json_path = self.directory / "source-monitor.json"
        self.markdown_path = self.directory / "source-monitor.md"
        self.history_path = self.directory / "source-history.json"
        self.latest_path = self.directory / "latest-monitor.json"

    def run(self, *, overwrite: bool = False) -> SourceMonitorRun:
        if self.json_path.exists() and not overwrite:
            raise SourceMonitorError("Source monitor output already exists. Use --overwrite to replace it.")
        previous = self.latest() if self.latest_path.exists() else None
        run = SourceMonitor(self.root).run(previous)
        self.save(run)
        return run

    def save(self, run: SourceMonitorRun) -> None:
        write_json(self.json_path, run.to_dict())
        write_json(self.latest_path, run.to_dict())
        history = self.history()
        history.append(run)
        write_json(self.history_path, {"runs": [item.to_dict() for item in history]})
        self.export(run)

    def latest(self) -> SourceMonitorRun:
        if not self.latest_path.exists():
            raise SourceMonitorError("No source monitor run found. Run monitor first.")
        return SourceMonitorRun.from_dict(read_json(self.latest_path))

    def history(self) -> list[SourceMonitorRun]:
        if not self.history_path.exists():
            return []
        data = read_json(self.history_path)
        return [SourceMonitorRun.from_dict(item) for item in _map_list(data.get("runs", []))]

    def export(self, run: SourceMonitorRun | None = None) -> Path:
        run = run or self.latest()
        self.markdown_path.parent.mkdir(parents=True, exist_ok=True)
        self.markdown_path.write_text(render_source_monitor_markdown(run), encoding="utf-8")
        return self.markdown_path

    def status(self) -> JsonMap:
        if not self.latest_path.exists():
            return {"available": False, "summary": _empty_summary()}
        run = self.latest()
        return {"available": True, "monitor_id": run.monitor_id, "created_at": run.created_at, "summary": run.summary}


def render_source_monitor_markdown(run: SourceMonitorRun) -> str:
    lines = [
        "# Source Monitor",
        "",
        f"Monitor ID: `{run.monitor_id}`",
        f"Created: `{run.created_at}`",
        f"Version: `{run.version}`",
        "",
        "## Summary",
        "",
        *_summary_lines(run.summary),
        "## Sources",
        "",
    ]
    for snapshot in run.snapshots:
        lines.extend(
            [
                f"### {snapshot.source_id}",
                "",
                f"- Type: `{snapshot.source_type}`",
                f"- Status: `{snapshot.status}`",
                f"- Items: {snapshot.item_count}",
                f"- Newest modified: `{snapshot.newest_modified_timestamp or ''}`",
                f"- Fingerprint: `{snapshot.fingerprint}`",
                f"- Previous fingerprint: `{snapshot.previous_fingerprint or ''}`",
                "",
            ]
        )
    lines.extend(["## Recommended Refreshes", ""])
    refreshes = sorted({refresh for change in run.changes for refresh in change.recommended_refreshes})
    lines.extend(_string_lines(refreshes))
    lines.extend(["## Limitations", ""])
    lines.extend(_string_lines(run.limitations))
    return "\n".join(lines)


def _scan_paths(root: Path, paths: list[Path]) -> list[JsonMap]:
    items: list[JsonMap] = []
    for path in paths:
        if not path.exists():
            raise FileNotFoundError(f"Missing source path: {path}")
        if path.is_file():
            items.append(_file_item(root, path))
            continue
        for child in sorted(path.rglob("*")):
            if child.is_file() and child.name != "README.md":
                items.append(_file_item(root, child))
    return sorted(items, key=lambda item: str(item["item_id"]))


def _file_item(root: Path, path: Path) -> JsonMap:
    stat = path.stat()
    rel = str(path.relative_to(root))
    return {
        "item_id": rel,
        "path": rel,
        "checksum": _file_hash(path),
        "modified_timestamp": datetime.fromtimestamp(stat.st_mtime).astimezone().isoformat(timespec="seconds"),
        "size": stat.st_size,
    }


def _config_item(config: Any) -> JsonMap:
    text = repr(_map(config))
    return {"item_id": str(_map(config).get("id", "configured_source")), "path": "config/sources.yaml", "checksum": _digest(text), "modified_timestamp": None, "size": len(text)}


def _change_for(snapshot: SourceSnapshot, previous: SourceSnapshot | None) -> SourceChange:
    previous_items = {str(item.get("item_id")): item for item in (previous.items if previous else [])}
    current_items = {str(item.get("item_id")): item for item in snapshot.items}
    new_items = sorted(set(current_items) - set(previous_items)) if previous else ([item["item_id"] for item in snapshot.items] if snapshot.status == STATUS_NEW else [])
    removed_items = sorted(set(previous_items) - set(current_items)) if previous else []
    updated_items = sorted(
        item_id
        for item_id in set(current_items).intersection(previous_items)
        if current_items[item_id].get("checksum") != previous_items[item_id].get("checksum")
    )
    failed_items = [snapshot.source_id] if snapshot.status == STATUS_FAILED else []
    return SourceChange(
        source_id=snapshot.source_id,
        source_type=snapshot.source_type,
        status=snapshot.status,
        new_items=new_items,
        removed_items=removed_items,
        updated_items=updated_items,
        failed_items=failed_items,
        recommended_refreshes=_refreshes_for(snapshot, new_items, removed_items, updated_items),
    )


def _status_for(items: list[JsonMap], fingerprint: str, previous: SourceSnapshot | None) -> str:
    if previous is None:
        return STATUS_NEW if items else STATUS_UNCHANGED
    if previous.status == STATUS_FAILED:
        return STATUS_NEW if items else STATUS_UNCHANGED
    if previous.fingerprint == fingerprint:
        return STATUS_UNCHANGED
    previous_items = {str(item.get("item_id")): item for item in previous.items}
    current_items = {str(item.get("item_id")): item for item in items}
    updated = any(current_items[item_id].get("checksum") != previous_items[item_id].get("checksum") for item_id in set(current_items).intersection(previous_items))
    if updated:
        return STATUS_UPDATED
    if set(current_items) - set(previous_items):
        return STATUS_NEW
    if set(previous_items) - set(current_items):
        return STATUS_REMOVED
    return STATUS_UPDATED


def _refreshes_for(snapshot: SourceSnapshot, new_items: list[str], removed_items: list[str], updated_items: list[str]) -> list[str]:
    if snapshot.status in {STATUS_UNCHANGED, STATUS_UNKNOWN}:
        return []
    if snapshot.status == STATUS_FAILED:
        return ["Review source monitoring failure before running downstream refresh."]
    refreshes = []
    if snapshot.source_type in {"local_intake_folder", "google_drive_folder"} and (new_items or updated_items):
        refreshes.append("Run intake import and downstream research workflows if the new source files are relevant.")
    if snapshot.source_type in {"local_evidence_files", "local_thesis_files"} and (new_items or removed_items or updated_items):
        refreshes.append("Refresh Evidence Graph, Thesis Intelligence, Daily Pipeline, and Executive Dashboard.")
    if snapshot.source_type == "local_configuration_files" and (new_items or removed_items or updated_items):
        refreshes.append("Run health check and review configuration-dependent connectors.")
    return refreshes


def _summary(changes: list[SourceChange]) -> JsonMap:
    changed = [change for change in changes if change.status in {STATUS_NEW, STATUS_REMOVED, STATUS_UPDATED}]
    failed = [change for change in changes if change.status == STATUS_FAILED]
    return {
        "sources_checked": len(changes),
        "sources_changed": len(changed),
        "sources_unchanged": sum(1 for change in changes if change.status == STATUS_UNCHANGED),
        "sources_failed": len(failed),
        "sources_unknown": sum(1 for change in changes if change.status == STATUS_UNKNOWN),
        "new_items": sum(len(change.new_items) for change in changes),
        "removed_items": sum(len(change.removed_items) for change in changes),
        "updated_items": sum(len(change.updated_items) for change in changes),
        "failures": sum(len(change.failed_items) for change in changes),
        "recommended_refreshes": sorted({refresh for change in changes for refresh in change.recommended_refreshes}),
    }


def _empty_summary() -> JsonMap:
    return {"sources_checked": 0, "sources_changed": 0, "sources_unchanged": 0, "sources_failed": 0, "sources_unknown": 0, "new_items": 0, "removed_items": 0, "updated_items": 0, "failures": 0, "recommended_refreshes": []}


def _fingerprint(items: list[JsonMap]) -> str:
    payload = "|".join(f"{item.get('item_id')}:{item.get('checksum')}" for item in sorted(items, key=lambda item: str(item.get("item_id"))))
    return f"source_fp_{_digest(payload)}"


def _newest_modified(items: list[JsonMap]) -> str | None:
    timestamps = sorted(str(item.get("modified_timestamp")) for item in items if item.get("modified_timestamp"))
    return timestamps[-1] if timestamps else None


def _monitor_id(snapshots: list[SourceSnapshot], changes: list[SourceChange]) -> str:
    fingerprint = "|".join(f"{snapshot.source_id}:{snapshot.fingerprint}:{snapshot.status}" for snapshot in sorted(snapshots, key=lambda item: item.source_id))
    fingerprint += "|" + "|".join(f"{change.source_id}:{change.status}" for change in sorted(changes, key=lambda item: item.source_id))
    return f"monitor_{_digest(fingerprint)}"


def _file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:16]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _summary_lines(summary: JsonMap) -> list[str]:
    return [*[f"- {key}: `{value}`" for key, value in summary.items()], ""]


def _string_lines(items: list[str]) -> list[str]:
    if not items:
        return ["- None", ""]
    return [*[f"- {item}" for item in items], ""]


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


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


def _require_str(data: JsonMap, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise SourceMonitorError(f"Source monitor field {key} must be a string")
    return value
