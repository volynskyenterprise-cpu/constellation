from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import Any

from .io import read_json, write_json
from .models import JsonMap, utc_now_iso


class EvidenceError(RuntimeError):
    pass


@dataclass(frozen=True)
class EvidenceItem:
    evidence_id: str
    workflow_run_id: str
    claim: str
    supporting_quote: str
    source_identifier: str
    source_location: str
    confidence: str
    provenance: JsonMap
    created_at: str
    updated_at: str

    def to_dict(self) -> JsonMap:
        return {
            "evidence_id": self.evidence_id,
            "workflow_run_id": self.workflow_run_id,
            "claim": self.claim,
            "supporting_quote": self.supporting_quote,
            "source_identifier": self.source_identifier,
            "source_location": self.source_location,
            "confidence": self.confidence,
            "provenance": self.provenance,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


class EvidenceStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "memory" / "evidence"
        self.index_path = self.directory / "index.json"

    def save(self, item: EvidenceItem) -> Path:
        path = self.path_for(item.evidence_id)
        write_json(path, item.to_dict())
        index = self._index()
        ids = index.setdefault("evidence_ids", [])
        if item.evidence_id not in ids:
            ids.append(item.evidence_id)
        write_json(self.index_path, index)
        return path

    def save_many(self, items: list[EvidenceItem]) -> list[Path]:
        return [self.save(item) for item in items]

    def list(self, workflow_run_id: str | None = None) -> list[JsonMap]:
        if not self.directory.exists():
            return []
        records: list[JsonMap] = []
        for path in sorted(self.directory.glob("ev_*.json")):
            try:
                record = read_json(path)
            except Exception:
                continue
            if workflow_run_id is None or record.get("workflow_run_id") == workflow_run_id:
                records.append(record)
        return sorted(records, key=lambda item: str(item.get("created_at", "")), reverse=True)

    def show(self, evidence_id: str) -> JsonMap:
        path = self.path_for(evidence_id.removesuffix(".json"))
        if not path.exists():
            raise EvidenceError(f"Unknown evidence item: {evidence_id}")
        record = read_json(path)
        if not isinstance(record, dict):
            raise EvidenceError(f"Evidence item is corrupt: {evidence_id}")
        return record

    def query(self, *, workflow_run_id: str | None = None, source_identifier: str | None = None) -> list[JsonMap]:
        records = self.list(workflow_run_id)
        if source_identifier is not None:
            records = [record for record in records if record.get("source_identifier") == source_identifier]
        return records

    def export_report(self, workflow_run_id: str, output_path: Path | None = None) -> Path:
        records = self.list(workflow_run_id)
        if output_path is None:
            output_path = self.root / "outputs" / "evidence" / f"{workflow_run_id}-evidence.md"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            f"# Evidence Report: {workflow_run_id}",
            "",
            f"Evidence items: {len(records)}",
            "",
        ]
        for record in records:
            lines.extend(
                [
                    f"## {record.get('evidence_id', 'unknown')}",
                    "",
                    f"- Claim: {record.get('claim', '')}",
                    f"- Source: `{record.get('source_identifier', '')}`",
                    f"- Location: `{record.get('source_location', '')}`",
                    f"- Confidence: `{record.get('confidence', '')}`",
                    "",
                    "> " + str(record.get("supporting_quote", "")).replace("\n", " "),
                    "",
                ]
            )
        output_path.write_text("\n".join(lines), encoding="utf-8")
        return output_path

    def path_for(self, evidence_id: str) -> Path:
        return self.directory / f"{evidence_id}.json"

    def _index(self) -> JsonMap:
        if not self.index_path.exists():
            return {"evidence_ids": []}
        try:
            index = read_json(self.index_path)
        except Exception:
            return {"evidence_ids": []}
        return index if isinstance(index, dict) else {"evidence_ids": []}


def evidence_from_text(
    *,
    workflow_run_id: str,
    source_identifier: str,
    source_text: str,
    provenance: JsonMap,
) -> list[EvidenceItem]:
    items: list[EvidenceItem] = []
    now = utc_now_iso()
    for line_number, raw_line in enumerate(source_text.splitlines(), start=1):
        quote = raw_line.strip()
        if not quote:
            continue
        claim = _claim_from_quote(quote)
        evidence_id = _evidence_id(workflow_run_id, source_identifier, line_number, quote)
        items.append(
            EvidenceItem(
                evidence_id=evidence_id,
                workflow_run_id=workflow_run_id,
                claim=claim,
                supporting_quote=quote,
                source_identifier=source_identifier,
                source_location=f"line {line_number}",
                confidence="source_provided",
                provenance={
                    **provenance,
                    "extraction_method": "deterministic_non_empty_line",
                    "line_number": line_number,
                },
                created_at=now,
                updated_at=now,
            )
        )
    return items


def _claim_from_quote(quote: str) -> str:
    stripped = quote.lstrip("#").strip()
    return stripped.rstrip(".") if stripped else quote


def _evidence_id(workflow_run_id: str, source_identifier: str, line_number: int, quote: str) -> str:
    digest = sha256(f"{workflow_run_id}|{source_identifier}|{line_number}|{quote}".encode("utf-8")).hexdigest()[:16]
    return f"ev_{digest}"
