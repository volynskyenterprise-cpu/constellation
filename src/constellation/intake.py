from __future__ import annotations

import shutil
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from .io import read_json, write_json
from .models import JsonMap


class IntakeError(RuntimeError):
    pass


INTAKE_CHANNELS = {
    "google-drive": Path("inbox/google-drive/incoming"),
    "gmail": Path("inbox/gmail/incoming"),
    "manual": Path("inbox/manual/incoming"),
}


@dataclass(frozen=True)
class IntakeItem:
    item_id: str
    source_channel: str
    original_path: str
    destination_path: str | None
    file_hash: str
    import_timestamp: str | None
    status: str
    error: str | None = None

    def to_dict(self) -> JsonMap:
        return {
            "item_id": self.item_id,
            "source_channel": self.source_channel,
            "original_path": self.original_path,
            "destination_path": self.destination_path,
            "file_hash": self.file_hash,
            "import_timestamp": self.import_timestamp,
            "status": self.status,
            "error": self.error,
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "IntakeItem":
        return cls(
            item_id=_require_str(data, "item_id"),
            source_channel=_require_str(data, "source_channel"),
            original_path=_require_str(data, "original_path"),
            destination_path=_optional_str(data.get("destination_path")),
            file_hash=_require_str(data, "file_hash"),
            import_timestamp=_optional_str(data.get("import_timestamp")),
            status=_require_str(data, "status"),
            error=_optional_str(data.get("error")),
        )


@dataclass(frozen=True)
class IntakeManifest:
    manifest_id: str
    created_at: str
    updated_at: str
    items: list[IntakeItem]
    counts: JsonMap

    def to_dict(self) -> JsonMap:
        return {
            "manifest_id": self.manifest_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "counts": self.counts,
            "items": [item.to_dict() for item in self.items],
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "IntakeManifest":
        return cls(
            manifest_id=_require_str(data, "manifest_id"),
            created_at=_require_str(data, "created_at"),
            updated_at=_require_str(data, "updated_at"),
            counts=data.get("counts", {}) if isinstance(data.get("counts", {}), dict) else {},
            items=[IntakeItem.from_dict(item) for item in data.get("items", []) if isinstance(item, dict)],
        )


class IntakeEngine:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.output_dir = root / "outputs" / "intake"
        self.json_path = self.output_dir / "intake-manifest.json"
        self.markdown_path = self.output_dir / "intake-manifest.md"

    def scan(self) -> list[IntakeItem]:
        items: list[IntakeItem] = []
        for channel, relative_dir in INTAKE_CHANNELS.items():
            incoming_dir = self.root / relative_dir
            if not incoming_dir.exists():
                continue
            for path in sorted(incoming_dir.iterdir(), key=lambda item: item.name.lower()):
                if not path.is_file() or path.name == "README.md":
                    continue
                file_hash = _file_hash(path)
                items.append(
                    IntakeItem(
                        item_id=_item_id(channel, str(path.resolve()), file_hash),
                        source_channel=channel,
                        original_path=str(path),
                        destination_path=None,
                        file_hash=file_hash,
                        import_timestamp=None,
                        status="available",
                    )
                )
        return sorted(items, key=lambda item: (item.source_channel, Path(item.original_path).name.lower(), item.file_hash))

    def import_items(self) -> IntakeManifest:
        now = _now_iso()
        import_date = _today()
        destination_dir = self.root / "research_inputs" / import_date
        previous = self.load_or_empty(now)
        imported_hashes = {item.file_hash for item in previous.items if item.status == "imported"}
        items = list(previous.items)
        for scanned in self.scan():
            source_path = Path(scanned.original_path)
            destination_path = destination_dir / source_path.name
            if scanned.file_hash in imported_hashes:
                items.append(_with_status(scanned, "duplicate", str(destination_path), now))
                continue
            if destination_path.exists():
                if _file_hash(destination_path) == scanned.file_hash:
                    items.append(_with_status(scanned, "duplicate", str(destination_path), now))
                    imported_hashes.add(scanned.file_hash)
                    continue
                items.append(_with_status(scanned, "error", str(destination_path), now, "Destination exists with different content; refusing to overwrite."))
                continue
            try:
                destination_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_path, destination_path)
            except Exception as exc:
                items.append(_with_status(scanned, "error", str(destination_path), now, str(exc)))
                continue
            imported_hashes.add(scanned.file_hash)
            items.append(_with_status(scanned, "imported", str(destination_path), now))
        manifest = IntakeManifest(
            manifest_id=f"manifest_{_digest('|'.join(item.item_id + ':' + item.status for item in items))}",
            created_at=previous.created_at,
            updated_at=now,
            items=items,
            counts=_counts(items),
        )
        self.save(manifest)
        return manifest

    def status(self) -> JsonMap:
        manifest = self.load_or_empty(_now_iso())
        return manifest.counts

    def load_or_empty(self, now: str) -> IntakeManifest:
        if not self.json_path.exists():
            return IntakeManifest(
                manifest_id="manifest_empty",
                created_at=now,
                updated_at=now,
                items=[],
                counts={"available": 0, "imported": 0, "skipped": 0, "duplicates": 0, "errors": 0, "total": 0},
            )
        try:
            return IntakeManifest.from_dict(read_json(self.json_path))
        except Exception as exc:
            raise IntakeError(f"Intake manifest is corrupt: {exc}") from exc

    def save(self, manifest: IntakeManifest) -> None:
        write_json(self.json_path, manifest.to_dict())
        self.markdown_path.parent.mkdir(parents=True, exist_ok=True)
        self.markdown_path.write_text(render_manifest_markdown(manifest), encoding="utf-8")


def render_manifest_markdown(manifest: IntakeManifest) -> str:
    lines = [
        "# Intake Manifest",
        "",
        f"Manifest ID: `{manifest.manifest_id}`",
        f"Created: `{manifest.created_at}`",
        f"Updated: `{manifest.updated_at}`",
        "",
        "## Counts",
        "",
    ]
    for key in ["imported", "skipped", "duplicates", "errors", "total"]:
        lines.append(f"- {key}: {manifest.counts.get(key, 0)}")
    lines.extend(["", "## Items", ""])
    if not manifest.items:
        lines.extend(["No intake items recorded.", ""])
        return "\n".join(lines)
    for item in manifest.items:
        lines.extend(
            [
                f"### {Path(item.original_path).name}",
                "",
                f"- ID: `{item.item_id}`",
                f"- Channel: `{item.source_channel}`",
                f"- Status: `{item.status}`",
                f"- Original: `{item.original_path}`",
                f"- Destination: `{item.destination_path or ''}`",
                f"- SHA-256: `{item.file_hash}`",
                f"- Imported: `{item.import_timestamp or ''}`",
            ]
        )
        if item.error:
            lines.append(f"- Error: {item.error}")
        lines.append("")
    return "\n".join(lines)


def _with_status(item: IntakeItem, status: str, destination_path: str, timestamp: str, error: str | None = None) -> IntakeItem:
    return IntakeItem(
        item_id=item.item_id,
        source_channel=item.source_channel,
        original_path=item.original_path,
        destination_path=destination_path,
        file_hash=item.file_hash,
        import_timestamp=timestamp,
        status=status,
        error=error,
    )


def _counts(items: list[IntakeItem]) -> JsonMap:
    imported = sum(1 for item in items if item.status == "imported")
    duplicates = sum(1 for item in items if item.status == "duplicate")
    errors = sum(1 for item in items if item.status == "error")
    skipped = duplicates
    return {
        "available": 0,
        "imported": imported,
        "skipped": skipped,
        "duplicates": duplicates,
        "errors": errors,
        "total": len(items),
    }


def _file_hash(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _item_id(channel: str, original_path: str, file_hash: str) -> str:
    return f"intake_{_digest(channel + '|' + original_path + '|' + file_hash)}"


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:16]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _today() -> str:
    return datetime.now().astimezone().date().isoformat()


def _optional_str(value: Any) -> str | None:
    return value if isinstance(value, str) else None


def _require_str(data: JsonMap, key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str):
        raise IntakeError(f"Intake field {key} must be a string")
    return value
