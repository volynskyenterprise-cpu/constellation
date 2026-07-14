from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from .canonical_assignments import CanonicalAssignmentEngine, CanonicalAssignmentStore
from .io import read_json, write_json
from .models import JsonMap


class CanonicalOperationsError(RuntimeError):
    pass


MIGRATION_CATEGORIES = {"safe_merge", "preserve_alias", "blocked_by_conflict", "ambiguous", "orphan", "already_migrated"}


@dataclass(frozen=True)
class CanonicalOperationsState:
    state_id: str
    created_at: str
    summary: JsonMap
    migration_summary: JsonMap
    review_queue: list[JsonMap]
    ready_assignments: list[JsonMap]
    blocked_assignments: list[JsonMap]
    ambiguous_assignments: list[JsonMap]
    conflicts: list[JsonMap]
    provenance: JsonMap
    limitations: list[str]

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


class CanonicalOperationsStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "outputs" / "real-estate" / "canonical"
        self.operations_report_md = self.directory / "canonical-operations-report.md"
        self.review_queue_md = self.directory / "review-queue.md"
        self.migration_summary_json = self.directory / "migration-summary.json"
        self.migration_summary_md = self.directory / "migration-summary.md"
        self.blocked_assignments_md = self.directory / "blocked-assignments.md"
        self.safe_migrations_md = self.directory / "safe-migrations.md"
        self.ambiguous_assignments_md = self.directory / "ambiguous-assignments.md"

    def save(self, state: CanonicalOperationsState) -> None:
        write_json(self.migration_summary_json, state.migration_summary)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.migration_summary_md.write_text(render_migration_summary_markdown(state), encoding="utf-8")
        self.review_queue_md.write_text(render_review_queue_markdown(state), encoding="utf-8")
        self.blocked_assignments_md.write_text(render_assignment_list_markdown("Blocked Canonical Assignments", state.blocked_assignments), encoding="utf-8")
        self.safe_migrations_md.write_text(render_safe_migrations_markdown(state), encoding="utf-8")
        self.ambiguous_assignments_md.write_text(render_assignment_list_markdown("Ambiguous Canonical Assignments", state.ambiguous_assignments), encoding="utf-8")
        self.operations_report_md.write_text(render_operations_report_markdown(state), encoding="utf-8")


class CanonicalOperationsEngine:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.assignment_engine = CanonicalAssignmentEngine(root)
        self.assignment_store = CanonicalAssignmentStore(root)
        self.store = CanonicalOperationsStore(root)

    def build(self, *, save: bool = True) -> CanonicalOperationsState:
        snapshot = self.assignment_engine.build()
        plan = self.assignment_engine.migration_plan(save=True)
        canonical_data = self.assignment_store.load()
        assignments = _map_list(canonical_data.get("assignments", []))
        aliases = self.assignment_store.load_aliases()
        migration_summary = _migration_summary(plan.actions)
        conflicts = _conflict_records(assignments)
        unassigned = _unassigned_artifacts(self.root)
        review_queue = _review_queue(assignments, plan.actions, aliases, conflicts, unassigned)
        blocked = _blocked_assignments(assignments, plan.actions, conflicts, review_queue)
        ambiguous = _ambiguous_assignments(plan.actions, aliases, review_queue)
        ready = _ready_assignments(assignments, plan.actions, conflicts, review_queue)
        summary = _summary(canonical_data, plan.actions, migration_summary, review_queue, ready, blocked, ambiguous, conflicts, unassigned)
        state = CanonicalOperationsState(
            state_id=_state_id(canonical_data, plan.to_dict(), review_queue),
            created_at=_now_iso(),
            summary=summary,
            migration_summary=migration_summary,
            review_queue=review_queue,
            ready_assignments=ready,
            blocked_assignments=blocked,
            ambiguous_assignments=ambiguous,
            conflicts=conflicts,
            provenance={
                "canonical_assignments": str(self.assignment_store.assignments_json),
                "migration_plan": str(self.assignment_store.migration_plan_json),
                "alias_index": str(self.assignment_store.alias_index_json),
            },
            limitations=[
                "Canonical Operations reports deterministic local state only.",
                "Suggested review actions are advisory and are never executed automatically.",
                "No providers, LLM inference, embeddings, semantic matching, web retrieval, or valuation conclusions are used.",
            ],
        )
        if save:
            self.store.save(state)
        return state

    def status(self) -> JsonMap:
        return self.build(save=True).summary


def render_migration_summary_markdown(state: CanonicalOperationsState) -> str:
    summary = state.migration_summary
    lines = ["# Canonical Migration Summary", "", "## Counts", ""]
    for key in ["pending_migration_count", "safe_merge_count", "preserve_alias_count", "blocked_by_conflict_count", "ambiguous_count", "orphan_count", "already_migrated_count"]:
        lines.append(f"- {key}: `{summary.get(key, 0)}`")
    lines.extend(["", "## Migration Items", ""])
    if not summary.get("items"):
        lines.append("- None")
    for item in _map_list(summary.get("items", [])):
        lines.append(f"- `{item.get('source_assignment_id')}` -> `{item.get('target_canonical_assignment_id')}` category={item.get('migration_category')} risk={item.get('risk_level')} action={item.get('suggested_operator_action')}")
    lines.append("")
    return "\n".join(lines)


def render_review_queue_markdown(state: CanonicalOperationsState) -> str:
    lines = ["# Canonical Assignment Review Queue", "", "Only assignments requiring human attention are listed.", ""]
    if not state.review_queue:
        lines.append("- No review items.")
    for item in state.review_queue:
        lines.extend(
            [
                f"## {item.get('category')} - {item.get('canonical_assignment_id') or item.get('source_assignment_id') or 'unassigned'}",
                "",
                f"- Reason: {item.get('reason')}",
                f"- Recommended review action: {item.get('recommended_review_action')}",
                f"- Supporting artifacts: {', '.join(_string_list(item.get('supporting_artifacts', []))) or 'None'}",
                f"- Provenance: `{json.dumps(_map(item.get('provenance')), sort_keys=True)}`",
                "",
            ]
        )
    return "\n".join(lines)


def render_assignment_list_markdown(title: str, assignments: list[JsonMap]) -> str:
    lines = [f"# {title}", ""]
    if not assignments:
        lines.append("- None")
    for item in assignments:
        lines.append(f"- `{item.get('canonical_assignment_id')}` readiness={item.get('migration_readiness')} reason={item.get('reason', '')}")
    lines.append("")
    return "\n".join(lines)


def render_safe_migrations_markdown(state: CanonicalOperationsState) -> str:
    items = [item for item in _map_list(state.migration_summary.get("items", [])) if item.get("migration_category") in {"safe_merge", "preserve_alias"}]
    lines = ["# Safe Canonical Migrations", ""]
    if not items:
        lines.append("- None")
    for item in items:
        lines.append(f"- `{item.get('source_assignment_id')}` -> `{item.get('target_canonical_assignment_id')}` category={item.get('migration_category')} action={item.get('suggested_operator_action')}")
    lines.append("")
    return "\n".join(lines)


def render_operations_report_markdown(state: CanonicalOperationsState) -> str:
    summary = state.summary
    lines = [
        "# Canonical Operations Report",
        "",
        "## Executive Summary",
        "",
        f"- Assignments: `{summary.get('canonical_assignment_count', 0)}`",
        f"- Artifacts: `{summary.get('artifact_count', 0)}`",
        f"- Aliases: `{summary.get('alias_count', 0)}`",
        f"- Pending review: `{summary.get('pending_review_count', 0)}`",
        f"- Migration ready: `{summary.get('migration_ready_count', 0)}`",
        f"- Blocked: `{summary.get('blocked_count', 0)}`",
        f"- Ambiguous: `{summary.get('ambiguous_count', 0)}`",
        "",
        "## Migration Status",
        "",
    ]
    for key in ["pending_migration_count", "safe_merge_count", "preserve_alias_count", "blocked_by_conflict_count", "ambiguous_count", "orphan_count", "already_migrated_count"]:
        lines.append(f"- {key}: `{state.migration_summary.get(key, 0)}`")
    lines.extend(["", "## Review Queue", ""])
    if not state.review_queue:
        lines.append("- No review items.")
    else:
        lines.extend(f"- `{item.get('category')}` assignment=`{item.get('canonical_assignment_id') or item.get('source_assignment_id')}` reason={item.get('reason')}" for item in state.review_queue)
    lines.extend(["", "## Ready Assignments", ""])
    if state.ready_assignments:
        lines.extend(f"- `{item.get('canonical_assignment_id')}`" for item in state.ready_assignments[:25])
    else:
        lines.append("- None")
    lines.extend(["", "## Blocked Assignments", ""])
    if state.blocked_assignments:
        lines.extend(f"- `{item.get('canonical_assignment_id')}` reason={item.get('reason')}" for item in state.blocked_assignments)
    else:
        lines.append("- None")
    lines.extend(["", "## Ambiguous Assignments", ""])
    if state.ambiguous_assignments:
        lines.extend(f"- `{item.get('canonical_assignment_id')}` reason={item.get('reason')}" for item in state.ambiguous_assignments)
    else:
        lines.append("- None")
    lines.extend(["", "## Identity Conflicts", ""])
    if state.conflicts:
        lines.extend(f"- `{item.get('canonical_assignment_id')}` field={item.get('field')} reason={item.get('reason_conflict_remains')}" for item in state.conflicts)
    else:
        lines.append("- None")
    lines.extend(["", "## Unassigned Artifacts", ""])
    unassigned = _map_list(summary.get("unassigned_artifacts", []))
    if unassigned:
        lines.extend(f"- `{item.get('artifact_id')}` source={item.get('source_path')}" for item in unassigned)
    else:
        lines.append("- None")
    lines.extend(["", "## Operational Metrics", ""])
    lines.extend(f"- {key}: `{value}`" for key, value in sorted(summary.items()) if not isinstance(value, (list, dict)))
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in state.limitations)
    lines.extend(["", "## Provenance", ""])
    lines.extend(f"- {key}: `{value}`" for key, value in state.provenance.items())
    lines.append("")
    return "\n".join(lines)


def _migration_summary(actions: list[JsonMap]) -> JsonMap:
    enriched = [_enrich_migration_item(item) for item in actions]
    counts = {category + "_count": sum(1 for item in enriched if item.get("migration_category") == category) for category in sorted(MIGRATION_CATEGORIES)}
    counts["pending_migration_count"] = sum(1 for item in enriched if item.get("migration_category") != "already_migrated")
    counts["migration_ready_count"] = counts.get("safe_merge_count", 0) + counts.get("preserve_alias_count", 0)
    counts["items"] = enriched
    return counts


def _enrich_migration_item(item: JsonMap) -> JsonMap:
    category = str(item.get("migration_category") or _legacy_category(item))
    source_files = _string_list(item.get("source_files", []))
    enriched = dict(item)
    enriched["migration_category"] = category
    enriched["affected_source_count"] = len(source_files)
    enriched["risk_level"] = _risk_level(category)
    enriched["reason"] = _migration_reason(category, enriched)
    enriched["suggested_operator_action"] = _suggested_action(category)
    enriched["canonical_directory"] = enriched.get("target_directory")
    enriched["source_directory"] = enriched.get("source_directory")
    return enriched


def _legacy_category(item: JsonMap) -> str:
    action = str(item.get("action") or "")
    status = str(item.get("status") or "")
    if status == "already_migrated":
        return "already_migrated"
    if action == "merge_into_canonical":
        return "safe_merge"
    if action == "preserve_as_alias":
        return "preserve_alias"
    if action == "blocked_by_conflict":
        return "blocked_by_conflict"
    if action == "ambiguous":
        return "ambiguous"
    if action == "orphan":
        return "orphan"
    return "preserve_alias"


def _risk_level(category: str) -> str:
    return {"safe_merge": "low", "preserve_alias": "low", "already_migrated": "low", "ambiguous": "high", "blocked_by_conflict": "high", "orphan": "medium"}.get(category, "medium")


def _migration_reason(category: str, item: JsonMap) -> str:
    return {
        "safe_merge": "Alias directory resolves deterministically to a canonical assignment.",
        "preserve_alias": "Alias directory should be preserved as an alias without deletion.",
        "blocked_by_conflict": "Conflicting assignment metadata requires human review before migration.",
        "ambiguous": "Alias matches multiple canonical assignments and cannot be resolved automatically.",
        "orphan": "Directory does not match a canonical assignment or known alias.",
        "already_migrated": "Alias directory has already been marked migrated.",
    }.get(category, "Review migration item.")


def _suggested_action(category: str) -> str:
    return {
        "safe_merge": "Run migration apply only after reviewing source and canonical directories.",
        "preserve_alias": "Preserve alias and verify future writes target the canonical assignment.",
        "blocked_by_conflict": "Compare order IDs, loan numbers, addresses, and effective dates manually.",
        "ambiguous": "Use the explicit canonical assignment ID after human review.",
        "orphan": "Review source document and decide whether to attach, archive, or leave unassigned.",
        "already_migrated": "No action required unless rollback review is needed.",
    }.get(category, "Resolve manually.")


def _summary(canonical_data: JsonMap, actions: list[JsonMap], migration_summary: JsonMap, review_queue: list[JsonMap], ready: list[JsonMap], blocked: list[JsonMap], ambiguous: list[JsonMap], conflicts: list[JsonMap], unassigned: list[JsonMap]) -> JsonMap:
    counts = _map(canonical_data.get("counts"))
    return {
        "available": bool(canonical_data),
        "canonical_assignment_count": counts.get("canonical_assignment_count", 0),
        "artifact_count": counts.get("artifact_count", 0),
        "alias_count": counts.get("alias_count", 0),
        "source_companion_count": counts.get("source_companion_count", 0),
        "knowledge_pack_count": counts.get("knowledge_pack_count", 0),
        "reviewer_note_count": counts.get("assignments_with_reviewer_notes", 0),
        "true_assignment_conflict_count": len(conflicts),
        "pending_migration_count": migration_summary.get("pending_migration_count", 0),
        "migration_ready_count": migration_summary.get("migration_ready_count", 0),
        "blocked_count": len(blocked),
        "ambiguous_count": len(ambiguous),
        "pending_review_count": len(review_queue),
        "safe_merge_count": migration_summary.get("safe_merge_count", 0),
        "preserve_alias_count": migration_summary.get("preserve_alias_count", 0),
        "blocked_by_conflict_count": migration_summary.get("blocked_by_conflict_count", 0),
        "orphan_count": migration_summary.get("orphan_count", 0),
        "already_migrated_count": migration_summary.get("already_migrated_count", 0),
        "migrated_alias_directory_count": migration_summary.get("already_migrated_count", 0),
        "unassigned_artifact_count": len(unassigned),
        "unassigned_artifacts": unassigned,
        "migration_state": "needs_review" if review_queue else "ready",
        "canonical_assignments_path": "outputs/real-estate/canonical/canonical-assignments.json",
        "alias_index_path": "outputs/real-estate/canonical/assignment-alias-index.json",
        "operations_report_path": "outputs/real-estate/canonical/canonical-operations-report.md",
        "review_queue_path": "outputs/real-estate/canonical/review-queue.md",
    }


def _review_queue(assignments: list[JsonMap], actions: list[JsonMap], aliases: list[JsonMap], conflicts: list[JsonMap], unassigned: list[JsonMap]) -> list[JsonMap]:
    items = []
    for conflict in conflicts:
        items.append(_review_item("identity_conflict", conflict.get("canonical_assignment_id"), "Identity or fact conflict remains after normalization.", "Compare order IDs, loan numbers, property address, and effective date.", conflict.get("supporting_artifacts", []), {"conflict": conflict}))
    for action in [_enrich_migration_item(item) for item in actions]:
        category = action.get("migration_category")
        if category == "blocked_by_conflict":
            items.append(_review_item("migration_blocked", action.get("target_canonical_assignment_id"), action.get("reason"), action.get("suggested_operator_action"), action.get("source_files", []), {"migration": action}))
        elif category == "ambiguous":
            items.append(_review_item("ambiguous_alias", action.get("target_canonical_assignment_id"), action.get("reason"), action.get("suggested_operator_action"), action.get("source_files", []), {"migration": action}))
        elif category == "orphan":
            items.append(_review_item("unassigned_artifact", action.get("target_canonical_assignment_id"), action.get("reason"), action.get("suggested_operator_action"), action.get("source_files", []), {"migration": action}))
    for assignment in assignments:
        critical = [item for item in _map_list(assignment.get("missing_items", [])) if item.get("severity") in {"critical", "high"}]
        if critical:
            items.append(_review_item("missing_critical_fields", assignment.get("canonical_assignment_id"), "Assignment has missing critical or high-priority fields.", "Review source document and complete explicit assignment metadata.", [source.get("source_path") for source in _map_list(assignment.get("source_artifacts", []))], {"missing_items": critical}))
    for artifact in unassigned:
        items.append(_review_item("unassigned_artifact", "", "Artifact is not assigned to a canonical assignment.", "Review source document and attach manually if appropriate.", [artifact.get("source_path")], {"artifact": artifact}))
    return sorted(_dedupe(items), key=lambda item: (str(item.get("category")), str(item.get("canonical_assignment_id")), str(item.get("reason"))))


def _review_item(category: str, canonical_id: Any, reason: Any, action: Any, artifacts: Any, provenance: JsonMap) -> JsonMap:
    return {
        "review_item_id": f"review_{_digest('|'.join([str(category), str(canonical_id), str(reason)]))}",
        "category": category,
        "canonical_assignment_id": str(canonical_id or ""),
        "reason": str(reason or ""),
        "recommended_review_action": str(action or "Resolve manually."),
        "supporting_artifacts": _string_list(artifacts if isinstance(artifacts, list) else [artifacts]),
        "provenance": provenance,
    }


def _conflict_records(assignments: list[JsonMap]) -> list[JsonMap]:
    records = []
    for assignment in assignments:
        canonical_id = str(assignment.get("canonical_assignment_id") or "")
        for conflict in _map_list(assignment.get("conflicts", [])):
            values = _string_list(conflict.get("values", []))
            normalized_values = _string_list(_map(conflict.get("provenance")).get("normalized_values", []))
            records.append(
                {
                    "conflict_id": str(conflict.get("conflict_id") or f"conflict_{_digest(canonical_id + str(conflict))}"),
                    "canonical_assignment_id": canonical_id,
                    "field": conflict.get("field") or conflict.get("field_name"),
                    "existing_value": values[0] if values else "",
                    "incoming_value": values[1] if len(values) > 1 else "",
                    "values": values,
                    "normalized_values": normalized_values,
                    "reason_conflict_remains": "Normalized substantive values differ.",
                    "suggested_operator_action": "Review source document and resolve manually.",
                    "supporting_artifacts": [source.get("source_path") for source in _map_list(assignment.get("source_artifacts", []))],
                    "provenance": conflict,
                }
            )
    return sorted(records, key=lambda item: item["conflict_id"])


def _ready_assignments(assignments: list[JsonMap], actions: list[JsonMap], conflicts: list[JsonMap], review_queue: list[JsonMap]) -> list[JsonMap]:
    blocked_ids = {str(item.get("canonical_assignment_id")) for item in _blocked_assignments(assignments, actions, conflicts, review_queue)}
    review_ids = {str(item.get("canonical_assignment_id")) for item in review_queue if item.get("canonical_assignment_id")}
    return [
        {"canonical_assignment_id": assignment.get("canonical_assignment_id"), "migration_readiness": "Ready", "reason": "No deterministic review blockers detected."}
        for assignment in assignments
        if str(assignment.get("canonical_assignment_id")) not in blocked_ids | review_ids
    ]


def _blocked_assignments(assignments: list[JsonMap], actions: list[JsonMap], conflicts: list[JsonMap], review_queue: list[JsonMap]) -> list[JsonMap]:
    ids = {str(item.get("canonical_assignment_id")) for item in conflicts if item.get("canonical_assignment_id")}
    for action in [_enrich_migration_item(item) for item in actions]:
        if action.get("migration_category") == "blocked_by_conflict":
            ids.add(str(action.get("target_canonical_assignment_id") or action.get("source_assignment_id") or ""))
    return [{"canonical_assignment_id": item, "migration_readiness": "Blocked", "reason": "Conflict or blocked migration requires human review."} for item in sorted(ids) if item]


def _ambiguous_assignments(actions: list[JsonMap], aliases: list[JsonMap], review_queue: list[JsonMap]) -> list[JsonMap]:
    ids = set()
    for item in actions:
        enriched = _enrich_migration_item(item)
        if enriched.get("migration_category") == "ambiguous":
            ids.add(str(enriched.get("target_canonical_assignment_id") or enriched.get("source_assignment_id") or ""))
    ids.update(str(item.get("canonical_assignment_id")) for item in review_queue if item.get("category") == "ambiguous_alias" and item.get("canonical_assignment_id"))
    return [{"canonical_assignment_id": item, "migration_readiness": "Needs Review", "reason": "Alias resolution is ambiguous."} for item in sorted(ids) if item]


def _unassigned_artifacts(root: Path) -> list[JsonMap]:
    path = root / "outputs" / "real-estate" / "consolidation" / "unassigned-artifacts.json"
    if not path.exists():
        return []
    try:
        return _map_list(read_json(path).get("unassigned_artifacts", []))
    except Exception:
        return []


def _dedupe(items: list[JsonMap]) -> list[JsonMap]:
    by_id = {str(item.get("review_item_id")): item for item in items}
    return [by_id[key] for key in sorted(by_id)]


def _state_id(canonical_data: JsonMap, migration_plan: JsonMap, review_queue: list[JsonMap]) -> str:
    payload = json.dumps({"canonical": canonical_data.get("snapshot_id"), "migration": migration_plan.get("migration_id"), "review": [item.get("review_item_id") for item in review_queue]}, sort_keys=True)
    return f"canonical_operations_{_digest(payload)}"


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:16]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _map(value: Any) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _map_list(value: Any) -> list[JsonMap]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    return [str(item) for item in value if item is not None] if isinstance(value, list) else []
