from __future__ import annotations

import html
import json
import re
from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from .io import read_json, write_json
from .models import JsonMap
from .real_estate import RealEstateAssignmentStore, assignment_directory


class CanonicalAssignmentError(RuntimeError):
    pass


MIGRATION_CATEGORIES = {"safe_merge", "preserve_alias", "blocked_by_conflict", "ambiguous", "orphan", "already_migrated"}
APPLY_ELIGIBLE_MIGRATION_CATEGORIES = {"safe_merge", "preserve_alias"}


@dataclass(frozen=True)
class CanonicalAssignmentAlias:
    alias: str
    alias_type: str
    canonical_assignment_id: str
    source_paths: list[str]
    first_seen: str
    last_seen: str
    status: str

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class CanonicalAssignmentSource:
    source_path: str
    artifact_id: str
    artifact_type: str
    source_type: str
    checksum: str
    imported_at: str
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class CanonicalAssignment:
    canonical_assignment_id: str
    aliases: list[JsonMap]
    explicit_assignment_ids: list[str]
    order_ids: list[str]
    loan_numbers: list[str]
    normalized_addresses: list[str]
    subject: JsonMap
    status: str
    assignment_type: str
    property_type: str
    client: str
    lender: str
    amc: str
    due_date: str
    effective_date: str
    report_type: str
    intended_use: str
    scope: JsonMap
    facts: list[JsonMap]
    conflicts: list[JsonMap]
    risks: list[JsonMap]
    missing_items: list[JsonMap]
    source_artifacts: list[JsonMap]
    source_companions: list[JsonMap]
    knowledge_pack_paths: list[str]
    reviewer_note_paths: list[str]
    created_at: str
    updated_at: str
    first_seen: str
    last_seen: str
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class CanonicalAssignmentResolution:
    requested_alias: str
    resolved: bool
    canonical_assignment_id: str
    alias_type: str
    ambiguous: bool
    matches: list[JsonMap]
    evidence: list[JsonMap]

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class CanonicalAssignmentMigrationPlan:
    migration_id: str
    created_at: str
    actions: list[JsonMap]
    counts: JsonMap
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class CanonicalAssignmentMigrationResult:
    migration_id: str
    applied: bool
    created_at: str
    actions: list[JsonMap]
    counts: JsonMap
    backup_manifest_path: str
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class CanonicalMigrationScope:
    ready_only: bool = False
    category: str = ""
    canonical_assignment_id: str = ""
    source_assignment_id: str = ""
    dry_run: bool = True
    apply: bool = False
    list_selected: bool = False

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class CanonicalMigrationSelection:
    migration_id: str
    created_at: str
    selected_entries: list[JsonMap]
    skipped_entries: list[JsonMap]
    blocked_entries: list[JsonMap]
    invalid_entries: list[JsonMap]
    selection_reason: str
    scope: JsonMap
    counts: JsonMap
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class CanonicalMigrationApplySummary:
    migration_id: str
    selected_count: int
    applied_count: int
    skipped_count: int
    refused_count: int
    already_migrated_count: int
    blocked_count: int
    ambiguous_count: int
    orphan_count: int
    remaining_pending_count: int
    remaining_ready_count: int
    remaining_blocked_count: int
    remaining_orphan_count: int
    backup_manifest_path: str
    applied_entries: list[JsonMap]
    skipped_entries: list[JsonMap]
    refused_entries: list[JsonMap]
    failed_entries: list[JsonMap]
    started_at: str
    completed_at: str
    applied: bool
    error: str
    scope: JsonMap
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class CanonicalAssignmentSnapshot:
    snapshot_id: str
    created_at: str
    assignments: list[CanonicalAssignment]
    aliases: list[CanonicalAssignmentAlias]
    delta: JsonMap
    counts: JsonMap
    limitations: list[str]

    def to_dict(self) -> JsonMap:
        return {
            "snapshot_id": self.snapshot_id,
            "created_at": self.created_at,
            "assignments": [item.to_dict() for item in self.assignments],
            "aliases": [item.to_dict() for item in self.aliases],
            "delta": self.delta,
            "counts": self.counts,
            "limitations": self.limitations,
        }


@dataclass(frozen=True)
class CanonicalAssignmentDelta:
    canonical_assignments_created: list[str]
    canonical_assignments_updated: list[str]
    aliases_added: list[str]
    aliases_removed: list[str]
    alias_directories_detected: list[str]
    alias_directories_migrated: list[str]
    fields_normalized: list[str]
    false_conflicts_resolved: list[str]
    true_conflicts_added: list[str]
    sources_merged: list[str]
    assignments_split: list[str]
    assignments_merged: list[str]

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


class CanonicalAssignmentStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "outputs" / "real-estate" / "canonical"
        self.assignments_json = self.directory / "canonical-assignments.json"
        self.assignments_md = self.directory / "canonical-assignments.md"
        self.alias_index_json = self.directory / "assignment-alias-index.json"
        self.alias_index_md = self.directory / "assignment-alias-index.md"
        self.migration_plan_json = self.directory / "canonical-migration-plan.json"
        self.migration_plan_md = self.directory / "canonical-migration-plan.md"
        self.migration_history_json = self.directory / "canonical-migration-history.json"
        self.backup_manifest_json = self.directory / "canonical-migration-backup-manifest.json"
        self.scoped_selection_json = self.directory / "scoped-migration-selection.json"
        self.scoped_selection_md = self.directory / "scoped-migration-selection.md"
        self.scoped_result_json = self.directory / "scoped-migration-result.json"
        self.scoped_result_md = self.directory / "scoped-migration-result.md"
        self.delta_json = self.directory / "canonical-assignment-delta.json"
        self.report_md = self.directory / "canonical-assignment-report.md"

    def save(self, snapshot: CanonicalAssignmentSnapshot) -> None:
        data = snapshot.to_dict()
        write_json(self.assignments_json, data)
        write_json(self.alias_index_json, {"aliases": data["aliases"], "counts": snapshot.counts, "created_at": snapshot.created_at})
        write_json(self.delta_json, data["delta"])
        self.assignments_md.parent.mkdir(parents=True, exist_ok=True)
        self.assignments_md.write_text(render_canonical_assignments_markdown(snapshot), encoding="utf-8")
        self.alias_index_md.write_text(render_alias_index_markdown(snapshot.aliases), encoding="utf-8")
        self.report_md.write_text(render_canonical_report_markdown(snapshot), encoding="utf-8")
        self._write_assignment_sidecars(snapshot)

    def load(self) -> JsonMap:
        return read_json(self.assignments_json) if self.assignments_json.exists() else {}

    def load_assignments(self) -> list[JsonMap]:
        return _map_list(self.load().get("assignments", []))

    def load_aliases(self) -> list[JsonMap]:
        if self.alias_index_json.exists():
            return _map_list(read_json(self.alias_index_json).get("aliases", []))
        return _map_list(self.load().get("aliases", []))

    def save_migration_plan(self, plan: CanonicalAssignmentMigrationPlan) -> None:
        write_json(self.migration_plan_json, plan.to_dict())
        self.migration_plan_md.parent.mkdir(parents=True, exist_ok=True)
        self.migration_plan_md.write_text(render_migration_plan_markdown(plan), encoding="utf-8")

    def save_migration_result(self, result: CanonicalAssignmentMigrationResult) -> None:
        write_json(self.backup_manifest_json, {"migration_id": result.migration_id, "created_at": result.created_at, "actions": result.actions})
        history = {"migrations": []}
        if self.migration_history_json.exists():
            history = read_json(self.migration_history_json)
        migrations = _map_list(history.get("migrations", []))
        if not migrations or migrations[-1].get("migration_id") != result.migration_id or result.applied:
            migrations.append(result.to_dict())
        write_json(self.migration_history_json, {"migrations": migrations})

    def save_scoped_selection(self, selection: CanonicalMigrationSelection) -> None:
        write_json(self.scoped_selection_json, selection.to_dict())
        self.scoped_selection_md.parent.mkdir(parents=True, exist_ok=True)
        self.scoped_selection_md.write_text(render_scoped_selection_markdown(selection), encoding="utf-8")

    def save_scoped_result(self, summary: CanonicalMigrationApplySummary) -> None:
        write_json(self.scoped_result_json, summary.to_dict())
        self.scoped_result_md.parent.mkdir(parents=True, exist_ok=True)
        self.scoped_result_md.write_text(render_scoped_result_markdown(summary), encoding="utf-8")
        history = {"migrations": []}
        if self.migration_history_json.exists():
            history = read_json(self.migration_history_json)
        migrations = _map_list(history.get("migrations", []))
        migrations.append(summary.to_dict())
        write_json(self.migration_history_json, {"migrations": migrations})

    def _write_assignment_sidecars(self, snapshot: CanonicalAssignmentSnapshot) -> None:
        by_assignment: dict[str, list[JsonMap]] = {}
        for alias in snapshot.aliases:
            by_assignment.setdefault(alias.canonical_assignment_id, []).append(alias.to_dict())
        for assignment in snapshot.assignments:
            out = self.root / "outputs" / "real-estate" / "assignments" / assignment.canonical_assignment_id
            write_json(out / "aliases.json", {"aliases": by_assignment.get(assignment.canonical_assignment_id, [])})
            write_json(
                out / "canonical-resolution.json",
                {
                    "canonical_assignment_id": assignment.canonical_assignment_id,
                    "aliases": by_assignment.get(assignment.canonical_assignment_id, []),
                    "provenance": {"source": "CanonicalAssignmentStore"},
                },
            )


class CanonicalAssignmentResolver:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.store = CanonicalAssignmentStore(root)

    def resolve(self, alias: str, *, build_if_missing: bool = True, allow_directory_fallback: bool = True) -> CanonicalAssignmentResolution:
        if build_if_missing and not self.store.alias_index_json.exists():
            try:
                CanonicalAssignmentEngine(self.root).build()
            except Exception:
                pass
        aliases = self.store.load_aliases()
        keys = _alias_keys(alias)
        matches = []
        for record in aliases:
            record_alias = str(record.get("alias") or "")
            record_keys = _alias_keys(record_alias)
            if keys & record_keys:
                matches.append(record)
        by_canonical: dict[str, JsonMap] = {}
        for match in matches:
            by_canonical[str(match.get("canonical_assignment_id"))] = match
        if len(by_canonical) == 1:
            match = next(iter(by_canonical.values()))
            return CanonicalAssignmentResolution(
                requested_alias=alias,
                resolved=True,
                canonical_assignment_id=str(match.get("canonical_assignment_id") or ""),
                alias_type=str(match.get("alias_type") or "alias"),
                ambiguous=False,
                matches=matches,
                evidence=[{"rule": "alias_index_match", "alias_keys": sorted(keys), "matched_alias": match.get("alias")}],
            )
        if len(by_canonical) > 1:
            return CanonicalAssignmentResolution(alias, False, "", "ambiguous", True, matches, [{"rule": "ambiguous_alias_index_match", "alias_keys": sorted(keys)}])
        assignment_dir = assignment_directory(self.root, _safe_id(alias))
        if allow_directory_fallback and assignment_dir.exists():
            return CanonicalAssignmentResolution(alias, True, assignment_dir.name, "canonical_assignment_id", False, [], [{"rule": "assignment_directory_exists"}])
        return CanonicalAssignmentResolution(alias, False, "", "", False, [], [{"rule": "no_deterministic_alias_match", "alias_keys": sorted(keys)}])

    def resolve_fields(self, fields: JsonMap, source_alias: str = "", source_path: str = "") -> CanonicalAssignmentResolution:
        aliases = []
        aliases.extend(aliases_from_fields(fields, source_alias=source_alias, source_path=source_path))
        for alias in aliases:
            resolution = self.resolve(alias["alias"], build_if_missing=False, allow_directory_fallback=False)
            if resolution.resolved or resolution.ambiguous:
                return resolution
        canonical = canonical_id_from_fields(fields, source_alias=source_alias, source_path=source_path)
        return CanonicalAssignmentResolution(
            requested_alias=source_alias or canonical,
            resolved=True,
            canonical_assignment_id=canonical,
            alias_type="new_canonical_assignment_id",
            ambiguous=False,
            matches=[],
            evidence=[{"rule": "canonical_id_priority", "aliases_considered": aliases}],
        )


class CanonicalAssignmentEngine:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.store = CanonicalAssignmentStore(root)

    def build(self) -> CanonicalAssignmentSnapshot:
        clusters = self._clusters()
        assignments = [self._assignment_from_cluster(cluster) for cluster in clusters]
        aliases = self._aliases(assignments)
        previous = self.store.load()
        provisional_counts = {
            "canonical_assignment_count": len(assignments),
            "artifact_count": sum(len(item.source_artifacts) for item in assignments),
            "alias_count": len(aliases),
            "source_count": sum(len(item.source_artifacts) for item in assignments),
            "source_companion_count": sum(len(item.source_companions) for item in assignments),
            "knowledge_pack_count": sum(1 for item in assignments if item.knowledge_pack_paths),
            "assignments_with_reviewer_notes": sum(1 for item in assignments if item.reviewer_note_paths),
            "true_assignment_conflict_count": sum(len(item.conflicts) for item in assignments),
            "pending_migration_count": 0,
            "migrated_alias_directory_count": 0,
            "ambiguous_alias_count": _ambiguous_alias_count(aliases),
        }
        provisional_snapshot = CanonicalAssignmentSnapshot(
            snapshot_id=_snapshot_id(assignments, aliases),
            created_at=_now_iso(),
            assignments=assignments,
            aliases=aliases,
            delta={},
            counts=provisional_counts,
            limitations=[
                "Canonical Assignment Model uses deterministic IDs, aliases, normalized addresses, and explicit source fields only.",
                "No fuzzy matching, semantic similarity, LLM inference, web retrieval, comparable selection, or valuation opinion is used.",
                "Migration is non-destructive; alias directories are never deleted.",
            ],
        )
        self.store.save(provisional_snapshot)
        plan = self.migration_plan(save=True)
        delta = _snapshot_delta(previous, assignments, aliases, plan)
        counts = {
            "canonical_assignment_count": len(assignments),
            "artifact_count": sum(len(item.source_artifacts) for item in assignments),
            "alias_count": len(aliases),
            "source_count": sum(len(item.source_artifacts) for item in assignments),
            "source_companion_count": sum(len(item.source_companions) for item in assignments),
            "knowledge_pack_count": sum(1 for item in assignments if item.knowledge_pack_paths),
            "assignments_with_reviewer_notes": sum(1 for item in assignments if item.reviewer_note_paths),
            "true_assignment_conflict_count": sum(len(item.conflicts) for item in assignments),
            "pending_migration_count": plan.counts.get("pending_migration_count", 0),
            "migrated_alias_directory_count": plan.counts.get("migrated_alias_directory_count", 0),
            "ambiguous_alias_count": _ambiguous_alias_count(aliases),
            "migration_ready_count": plan.counts.get("migration_ready_count", 0),
            "safe_merge_count": plan.counts.get("safe_merge_count", 0),
            "preserve_alias_count": plan.counts.get("preserve_alias_count", 0),
            "blocked_by_conflict_count": plan.counts.get("blocked_by_conflict_count", 0),
            "orphan_count": plan.counts.get("orphan_count", 0),
            "already_migrated_count": plan.counts.get("already_migrated_count", 0),
        }
        snapshot = CanonicalAssignmentSnapshot(
            snapshot_id=_snapshot_id(assignments, aliases),
            created_at=_now_iso(),
            assignments=assignments,
            aliases=aliases,
            delta=delta.to_dict(),
            counts=counts,
            limitations=[
                "Canonical Assignment Model uses deterministic IDs, aliases, normalized addresses, and explicit source fields only.",
                "No fuzzy matching, semantic similarity, LLM inference, web retrieval, comparable selection, or valuation opinion is used.",
                "Migration is non-destructive; alias directories are never deleted.",
            ],
        )
        self.store.save(snapshot)
        self.store.save_migration_plan(plan)
        return snapshot

    def status(self) -> JsonMap:
        if not self.store.assignments_json.exists():
            self.build()
        data = self.store.load()
        counts = _map(data.get("counts"))
        return {
            "available": bool(data),
            "canonical_assignment_count": counts.get("canonical_assignment_count", 0),
            "artifact_count": counts.get("artifact_count", 0),
            "alias_count": counts.get("alias_count", 0),
            "pending_migration_count": counts.get("pending_migration_count", 0),
            "migrated_alias_directory_count": counts.get("migrated_alias_directory_count", 0),
            "true_assignment_conflict_count": counts.get("true_assignment_conflict_count", 0),
            "migration_ready_count": counts.get("migration_ready_count", 0),
            "safe_merge_count": counts.get("safe_merge_count", 0),
            "preserve_alias_count": counts.get("preserve_alias_count", 0),
            "blocked_by_conflict_count": counts.get("blocked_by_conflict_count", 0),
            "orphan_count": counts.get("orphan_count", 0),
            "already_migrated_count": counts.get("already_migrated_count", 0),
            "canonical_assignments_path": str(self.store.assignments_json),
            "alias_index_path": str(self.store.alias_index_json),
        }

    def migration_plan(self, *, save: bool = True) -> CanonicalAssignmentMigrationPlan:
        aliases = self.store.load_aliases()
        alias_by_name: dict[str, list[JsonMap]] = {}
        for alias in aliases:
            for key in _alias_keys(str(alias.get("alias") or "")):
                alias_by_name.setdefault(key, []).append(alias)
        canonical_ids = {str(alias.get("canonical_assignment_id") or "") for alias in aliases if alias.get("canonical_assignment_id")}
        assignments_by_id = {str(item.get("canonical_assignment_id") or ""): item for item in self.store.load_assignments()}
        store = RealEstateAssignmentStore(self.root)
        actions = []
        for assignment_id in store.list_assignment_ids():
            directory = store.assignment_root() / assignment_id
            if assignment_id in canonical_ids:
                continue
            matches_by_canonical: dict[str, JsonMap] = {}
            for key in _alias_keys(assignment_id):
                for match in alias_by_name.get(key, []):
                    target = str(match.get("canonical_assignment_id") or "")
                    if target and target != assignment_id:
                        matches_by_canonical[target] = match
            if len(matches_by_canonical) > 1:
                actions.append(_migration_action(assignment_id, "", directory, directory, "ambiguous_alias", "ambiguous", "review_required", "ambiguous"))
                continue
            if len(matches_by_canonical) == 1:
                target, match = next(iter(matches_by_canonical.items()))
                marker = directory / "canonical-migration.json"
                target_assignment = _map(assignments_by_id.get(target))
                if marker.exists():
                    category = "already_migrated"
                    action = "preserve_as_alias"
                    status = "already_migrated"
                elif _map_list(target_assignment.get("conflicts")):
                    category = "blocked_by_conflict"
                    action = "blocked_by_conflict"
                    status = "blocked"
                else:
                    files = [path for path in directory.rglob("*") if path.is_file()] if directory.exists() else []
                    category = "preserve_alias" if len(files) <= 1 else "safe_merge"
                    action = "preserve_as_alias" if category == "preserve_alias" else "merge_into_canonical"
                    status = "planned"
                actions.append(_migration_action(assignment_id, target, directory, store.assignment_root() / target, str(match.get("alias_type") or "alias"), action, status, category))
            elif assignment_id:
                actions.append(_migration_action(assignment_id, "", directory, directory, "unknown", "orphan", "review_required", "orphan"))
        counts = _migration_counts(actions)
        plan = CanonicalAssignmentMigrationPlan(f"canonical_migration_{_digest(json.dumps(actions, sort_keys=True))}", _now_iso(), actions, counts, {"rule": "non_destructive_alias_directory_detection"})
        if save:
            self.store.save_migration_plan(plan)
        return plan

    def select_migration_entries(
        self,
        *,
        ready_only: bool = False,
        category: str = "",
        canonical_assignment_id: str = "",
        source_assignment_id: str = "",
        apply: bool = False,
        list_selected: bool = False,
        save: bool = True,
    ) -> CanonicalMigrationSelection:
        plan = self.migration_plan(save=True)
        resolved_canonical = ""
        invalid_entries: list[JsonMap] = []
        if category and category not in MIGRATION_CATEGORIES:
            raise CanonicalAssignmentError(f"invalid migration category: {category}")
        if canonical_assignment_id:
            resolution = CanonicalAssignmentResolver(self.root).resolve(canonical_assignment_id)
            if resolution.ambiguous:
                raise CanonicalAssignmentError(f"ambiguous assignment alias: {canonical_assignment_id}")
            if not resolution.resolved:
                raise CanonicalAssignmentError(f"assignment alias did not resolve: {canonical_assignment_id}")
            resolved_canonical = resolution.canonical_assignment_id
        scope = CanonicalMigrationScope(
            ready_only=ready_only,
            category=category,
            canonical_assignment_id=resolved_canonical,
            source_assignment_id=source_assignment_id,
            dry_run=not apply,
            apply=apply,
            list_selected=list_selected,
        )
        selected: list[JsonMap] = []
        skipped: list[JsonMap] = []
        blocked: list[JsonMap] = []
        for entry in plan.actions:
            item = dict(entry)
            item["apply_eligible"] = is_migration_entry_apply_eligible(item)
            reason = _selection_skip_reason(item, scope)
            if reason:
                item["selection_status"] = "skipped"
                item["selection_reason"] = reason
                skipped.append(item)
                continue
            item["selection_status"] = "selected"
            item["selection_reason"] = _selection_reason(scope)
            selected.append(item)
            if not item["apply_eligible"]:
                blocked.append(item)
        if apply and not ready_only and not category and not resolved_canonical and not source_assignment_id:
            non_ready = [item for item in selected if item.get("migration_category") not in APPLY_ELIGIBLE_MIGRATION_CATEGORIES and item.get("migration_category") != "already_migrated"]
            if non_ready:
                invalid_entries.extend(_refusal(item, "unscoped apply refused because the plan contains blocked, ambiguous, or orphan entries.") for item in non_ready)
        counts = _selection_counts(selected, skipped, blocked, invalid_entries)
        selection = CanonicalMigrationSelection(
            migration_id=plan.migration_id,
            created_at=_now_iso(),
            selected_entries=selected,
            skipped_entries=skipped,
            blocked_entries=blocked,
            invalid_entries=invalid_entries,
            selection_reason=_selection_reason(scope),
            scope=scope.to_dict(),
            counts=counts,
            provenance={"migration_plan": str(self.store.migration_plan_json), "rule": "scoped_deterministic_selection"},
        )
        if save:
            self.store.save_scoped_selection(selection)
        return selection

    def migrate(
        self,
        *,
        apply: bool = False,
        ready_only: bool = False,
        category: str = "",
        canonical_assignment_id: str = "",
        source_assignment_id: str = "",
        list_selected: bool = False,
    ) -> CanonicalMigrationApplySummary:
        started = _now_iso()
        selection = self.select_migration_entries(
            ready_only=ready_only,
            category=category,
            canonical_assignment_id=canonical_assignment_id,
            source_assignment_id=source_assignment_id,
            apply=apply,
            list_selected=list_selected,
            save=True,
        )
        if not apply or list_selected:
            summary = _apply_summary_from_selection(selection, applied=False, started_at=started, completed_at=_now_iso(), backup_manifest_path="", error="")
            self.store.save_scoped_result(summary)
            return summary
        refused = list(selection.invalid_entries)
        if refused:
            summary = _apply_summary_from_selection(selection, applied=False, started_at=started, completed_at=_now_iso(), backup_manifest_path="", error="Scoped migration refused for safety.")
            self.store.save_scoped_result(summary)
            return summary
        applied_actions = []
        skipped_entries = list(selection.skipped_entries)
        refused_entries = []
        failed_entries = []
        initial_backup_manifest = {
            "migration_id": selection.migration_id,
            "created_at": started,
            "scope": selection.scope,
            "selected_entries": selection.selected_entries,
            "applied_entries": [],
            "refused_entries": [],
            "failed_entries": [],
            "deletion": "not_supported",
            "status": "started",
        }
        write_json(self.store.backup_manifest_json, initial_backup_manifest)
        for action in selection.selected_entries:
            if not is_migration_entry_apply_eligible(action):
                refused_entries.append(_refusal(action, "selected entry is not apply eligible"))
                continue
            source = Path(str(action.get("source_directory")))
            target = Path(str(action.get("target_directory")))
            try:
                target.mkdir(parents=True, exist_ok=True)
                marker = {
                    "source_assignment_id": action.get("source_assignment_id"),
                    "target_canonical_assignment_id": action.get("target_canonical_assignment_id"),
                    "migration_id": selection.migration_id,
                    "migrated_at": _now_iso(),
                    "status": "migrated_alias_directory",
                    "migration_scope": selection.scope,
                    "note": "Alias directory preserved; future writes should target canonical directory.",
                }
                write_json(source / "canonical-migration.json", marker)
                updated = dict(action)
                updated["status"] = "already_migrated"
                updated["migration_category"] = "already_migrated"
                updated["action"] = "preserve_as_alias"
                applied_actions.append(updated)
            except Exception as exc:
                failed = dict(action)
                failed["failure"] = str(exc)
                failed_entries.append(failed)
        backup_manifest = {
            "migration_id": selection.migration_id,
            "created_at": started,
            "scope": selection.scope,
            "selected_entries": selection.selected_entries,
            "applied_entries": applied_actions,
            "refused_entries": refused_entries,
            "failed_entries": failed_entries,
            "deletion": "not_supported",
            "status": "completed",
        }
        write_json(self.store.backup_manifest_json, backup_manifest)
        self.build()
        remaining_plan = self.migration_plan(save=True)
        remaining_counts = remaining_plan.counts
        apply_error = ""
        if failed_entries:
            apply_error = "One or more selected entries failed during marker write."
        elif refused_entries and not applied_actions:
            apply_error = "Selected entries are not apply eligible."
        summary = CanonicalMigrationApplySummary(
            migration_id=selection.migration_id,
            selected_count=len(selection.selected_entries),
            applied_count=len(applied_actions),
            skipped_count=len(skipped_entries),
            refused_count=len(refused_entries),
            already_migrated_count=remaining_counts.get("already_migrated_count", 0),
            blocked_count=remaining_counts.get("blocked_by_conflict_count", 0),
            ambiguous_count=remaining_counts.get("ambiguous_count", 0),
            orphan_count=remaining_counts.get("orphan_count", 0),
            remaining_pending_count=remaining_counts.get("pending_migration_count", 0),
            remaining_ready_count=remaining_counts.get("migration_ready_count", 0),
            remaining_blocked_count=remaining_counts.get("blocked_by_conflict_count", 0),
            remaining_orphan_count=remaining_counts.get("orphan_count", 0),
            backup_manifest_path=str(self.store.backup_manifest_json),
            applied_entries=applied_actions,
            skipped_entries=skipped_entries,
            refused_entries=refused_entries,
            failed_entries=failed_entries,
            started_at=started,
            completed_at=_now_iso(),
            applied=bool(applied_actions) and not failed_entries,
            error=apply_error,
            scope=selection.scope,
            provenance={"mode": "apply", "operator_triggered": True, "deletion": "not_supported"},
        )
        self.store.save_scoped_result(summary)
        try:
            from .canonical_operations import CanonicalOperationsEngine

            CanonicalOperationsEngine(self.root).build(save=True)
        except Exception:
            pass
        try:
            from .dashboard import ExecutiveDashboardStore

            ExecutiveDashboardStore(self.root).generate(overwrite=True)
        except Exception:
            pass
        return summary

    def _clusters(self) -> list[JsonMap]:
        from .assignment_consolidation import AssignmentConsolidationEngine

        data = AssignmentConsolidationEngine(self.root).build().to_dict()
        clusters = _map_list(data.get("clusters", []))
        return clusters or _assignment_directory_clusters(self.root)

    def _assignment_from_cluster(self, cluster: JsonMap) -> CanonicalAssignment:
        canonical_id = str(cluster.get("canonical_assignment_id") or "")
        output = _read_assignment_output(self.root, canonical_id)
        assignment = _map(output.get("assignment"))
        subject = _map(assignment.get("subject"))
        scope = _map(assignment.get("scope"))
        artifacts = _map_list(cluster.get("artifacts", []))
        aliases = [alias.to_dict() for alias in _aliases_for_cluster(cluster)]
        sources = [
            CanonicalAssignmentSource(
                source_path=normalize_path(str(artifact.get("source_path") or "")),
                artifact_id=str(artifact.get("artifact_id") or ""),
                artifact_type=str(artifact.get("artifact_type") or ""),
                source_type=str(artifact.get("source_type") or ""),
                checksum=str(_map(_map(artifact.get("provenance")).get("record")).get("checksum") or ""),
                imported_at=str(artifact.get("imported_at") or ""),
                provenance={"artifact": artifact},
            ).to_dict()
            for artifact in artifacts
        ]
        return CanonicalAssignment(
            canonical_assignment_id=canonical_id,
            aliases=aliases,
            explicit_assignment_ids=_string_list(cluster.get("explicit_assignment_ids", [])),
            order_ids=_string_list(cluster.get("order_ids", [])),
            loan_numbers=_string_list(cluster.get("loan_numbers", [])),
            normalized_addresses=_string_list(cluster.get("normalized_addresses", [])),
            subject={
                "address": subject.get("address") or cluster.get("property_address") or "",
                "city": subject.get("city") or cluster.get("city") or "",
                "state": subject.get("state") or cluster.get("state") or "",
                "postal_code": subject.get("postal_code") or "",
            },
            status=str(output.get("status") or cluster.get("assignment_status") or "unknown"),
            assignment_type=str(assignment.get("assignment_type") or ""),
            property_type=str(output.get("property_type") or assignment.get("property_type") or ""),
            client=str(assignment.get("client_name") or cluster.get("client") or ""),
            lender=str(cluster.get("lender") or ""),
            amc=str(cluster.get("amc") or ""),
            due_date=str(assignment.get("due_date") or ""),
            effective_date=str(assignment.get("effective_date") or ""),
            report_type=str(assignment.get("report_type") or ""),
            intended_use=str(assignment.get("intended_use") or ""),
            scope=scope,
            facts=_map_list(output.get("facts", [])),
            conflicts=_map_list(cluster.get("conflicts", [])) + _map_list(output.get("conflicts", [])),
            risks=_map_list(output.get("risks", [])),
            missing_items=_map_list(output.get("missing_items", [])),
            source_artifacts=sources,
            source_companions=[{"relationship_id": rel} for rel in _string_list(cluster.get("relationships", []))],
            knowledge_pack_paths=sorted({normalize_path(str(item.get("source_path") or "")) for item in artifacts if item.get("artifact_type") == "knowledge_pack"}),
            reviewer_note_paths=sorted({normalize_path(str(item.get("source_path") or "")) for item in artifacts if str(item.get("artifact_type")) in {"review_markdown", "review_json"}}),
            created_at=str(assignment.get("created_at") or cluster.get("first_seen") or ""),
            updated_at=_now_iso(),
            first_seen=str(cluster.get("first_seen") or ""),
            last_seen=str(cluster.get("last_seen") or ""),
            provenance={"source": "assignment_consolidation", "cluster_id": canonical_id},
        )

    def _aliases(self, assignments: list[CanonicalAssignment]) -> list[CanonicalAssignmentAlias]:
        rows: dict[str, CanonicalAssignmentAlias] = {}
        for assignment in assignments:
            source_paths = sorted({str(source.get("source_path") or "") for source in assignment.source_artifacts if source.get("source_path")})
            for alias in assignment.aliases:
                name = str(alias.get("alias") or "")
                if not name:
                    continue
                key = name + "|" + assignment.canonical_assignment_id
                rows[key] = CanonicalAssignmentAlias(
                    alias=name,
                    alias_type=str(alias.get("alias_type") or "alias"),
                    canonical_assignment_id=assignment.canonical_assignment_id,
                    source_paths=source_paths,
                    first_seen=assignment.first_seen,
                    last_seen=assignment.last_seen,
                    status="active",
                )
        return sorted(rows.values(), key=lambda item: (item.canonical_assignment_id, item.alias_type, item.alias))


def aliases_from_fields(fields: JsonMap, *, source_alias: str = "", source_path: str = "") -> list[JsonMap]:
    address = _first(fields, ["subject_address", "property_address", "address"])
    effective_date = normalize_date(_first(fields, ["effective_date", "valuation_date"]))
    due_date = normalize_date(_first(fields, ["due_date", "delivery_date", "report_due"]))
    values = [
        ("explicit_assignment_id", _clean_text(str(fields.get("assignment_id") or ""))),
        ("explicit_order_id", _clean_text(str(fields.get("order_id") or ""))),
        ("explicit_loan_number", _clean_text(str(fields.get("loan_number") or ""))),
        ("source_generated_alias", source_alias),
    ]
    normalized_address = normalize_address(address)
    if normalized_address and effective_date:
        values.append(("normalized_address_effective_date", _safe_id(f"{normalized_address}-{effective_date}")))
    if normalized_address and due_date:
        values.append(("normalized_address_due_date", _safe_id(f"{normalized_address}-{due_date}")))
    if normalized_address:
        values.append(("normalized_property_address", normalized_address))
        values.append(("address_derived_alias", _safe_id(normalized_address)))
    if source_path:
        values.append(("hash_fallback_alias", f"hash-{_digest(normalize_path(source_path))}"))
    result = []
    seen = set()
    for alias_type, alias in values:
        alias = _clean_text(str(alias or ""))
        if not alias or alias in seen:
            continue
        seen.add(alias)
        result.append({"alias": alias, "alias_type": alias_type})
        safe = _safe_id(alias)
        if safe and safe != alias and safe not in seen:
            seen.add(safe)
            result.append({"alias": safe, "alias_type": alias_type + "_safe_id"})
    return result


def canonical_id_from_fields(fields: JsonMap, *, source_alias: str = "", source_path: str = "") -> str:
    for key in ["assignment_id", "order_id", "loan_number"]:
        value = _clean_text(str(fields.get(key) or ""))
        if value:
            return _safe_id(value)
    address = normalize_address(_first(fields, ["subject_address", "property_address", "address"]))
    effective = normalize_date(_first(fields, ["effective_date", "valuation_date"]))
    if address and effective:
        return _safe_id(f"{address}-{effective}")
    if address:
        return _safe_id(address)
    if source_alias:
        return _safe_id(source_alias)
    return f"assignment-{_digest(normalize_path(source_path) or json.dumps(fields, sort_keys=True))}"


def normalize_text(value: Any) -> str:
    return _clean_text(str(value or ""))


def normalize_address(value: Any) -> str:
    text = _clean_text(str(value or "")).lower()
    text = re.sub(r"#\s*([a-z0-9-]+)", r" unit \1", text)
    text = re.sub(r"\b(apt|apartment|ste|suite)\s+([a-z0-9-]+)", r"unit \2", text)
    text = re.sub(r"[^\w\s]", " ", text)
    replacements = {
        "street": "st",
        "avenue": "ave",
        "boulevard": "blvd",
        "drive": "dr",
        "road": "rd",
        "lane": "ln",
        "court": "ct",
        "place": "pl",
        "circle": "cir",
        "unit": "unit",
    }
    return " ".join(replacements.get(word, word) for word in text.split())


def normalize_date(value: Any) -> str:
    text = _clean_text(str(value or ""))
    if not text:
        return ""
    iso = re.match(r"^(\d{4})-(\d{2})-(\d{2})(?:[tT ].*)?$", text)
    if iso:
        return f"{iso.group(1)}-{iso.group(2)}-{iso.group(3)}"
    us = re.match(r"^(\d{1,2})[/-](\d{1,2})[/-](\d{4})$", text)
    if us:
        month, day, year = int(us.group(1)), int(us.group(2)), int(us.group(3))
        if 1 <= month <= 12 and 1 <= day <= 31:
            return f"{year:04d}-{month:02d}-{day:02d}"
    return text


def normalize_postal_code(value: Any) -> str:
    text = _clean_text(str(value or ""))
    match = re.match(r"^(\d{5})(?:[-\s]?(\d{4}))?$", text)
    if not match:
        return text
    return match.group(1) + (f"-{match.group(2)}" if match.group(2) else "")


def postal_codes_compatible(a: Any, b: Any) -> bool:
    left, right = normalize_postal_code(a), normalize_postal_code(b)
    if not left or not right:
        return True
    return left == right or left[:5] == right[:5]


def normalize_path(value: Any) -> str:
    text = str(value or "").strip().strip('"')
    if not text:
        return ""
    try:
        return str(Path(text))
    except Exception:
        return text.replace("\\\\", "\\")


def render_canonical_assignments_markdown(snapshot: CanonicalAssignmentSnapshot) -> str:
    lines = ["# Canonical Real Estate Assignments", "", f"Snapshot: `{snapshot.snapshot_id}`", f"Created: `{snapshot.created_at}`", "", "## Summary", ""]
    lines.extend(f"- {key}: `{value}`" for key, value in snapshot.counts.items())
    lines.extend(["", "## Assignments", ""])
    if not snapshot.assignments:
        lines.append("- None")
    for item in snapshot.assignments:
        subject = _map(item.subject)
        lines.append(f"- `{item.canonical_assignment_id}` subject=`{subject.get('address', '')}` artifacts={len(item.source_artifacts)} aliases={len(item.aliases)} risks={len(item.risks)} conflicts={len(item.conflicts)}")
    lines.append("")
    return "\n".join(lines)


def render_alias_index_markdown(aliases: list[CanonicalAssignmentAlias]) -> str:
    lines = ["# Canonical Assignment Alias Index", ""]
    if not aliases:
        lines.append("- None")
    for alias in aliases:
        lines.append(f"- `{alias.alias}` -> `{alias.canonical_assignment_id}` type={alias.alias_type} status={alias.status}")
    lines.append("")
    return "\n".join(lines)


def render_canonical_report_markdown(snapshot: CanonicalAssignmentSnapshot) -> str:
    lines = ["# Canonical Assignment Model Report", "", "## Architecture", "", "- Assignment Consolidation decides which artifacts belong together.", "- Canonical Assignment Model persists one operational assignment object per cluster.", "- Assignment Intelligence analyzes canonical assignment directories.", "", "## Counts", ""]
    lines.extend(f"- {key}: `{value}`" for key, value in snapshot.counts.items())
    lines.extend(["", "## Limitations", ""])
    lines.extend(f"- {item}" for item in snapshot.limitations)
    lines.append("")
    return "\n".join(lines)


def render_migration_plan_markdown(plan: CanonicalAssignmentMigrationPlan) -> str:
    lines = ["# Canonical Assignment Migration Plan", "", f"Migration: `{plan.migration_id}`", f"Created: `{plan.created_at}`", "", "## Counts", ""]
    lines.extend(f"- {key}: `{value}`" for key, value in plan.counts.items())
    lines.extend(["", "## Actions", ""])
    if not plan.actions:
        lines.append("- None")
    for action in plan.actions:
        lines.append(f"- `{action.get('source_assignment_id')}` -> `{action.get('target_canonical_assignment_id')}` action={action.get('action')} status={action.get('status')}")
    lines.append("")
    return "\n".join(lines)


def render_scoped_selection_markdown(selection: CanonicalMigrationSelection) -> str:
    lines = ["# Scoped Canonical Migration Selection", "", "## Scope", ""]
    lines.extend(f"- {key}: `{value}`" for key, value in selection.scope.items())
    lines.extend(["", "## Counts", ""])
    lines.extend(f"- {key}: `{value}`" for key, value in selection.counts.items())
    for title, entries in [
        ("Selected Entries", selection.selected_entries),
        ("Excluded Ready Entries", [item for item in selection.skipped_entries if item.get("migration_category") in APPLY_ELIGIBLE_MIGRATION_CATEGORIES]),
        ("Blocked Entries", [item for item in selection.skipped_entries + selection.blocked_entries if item.get("migration_category") == "blocked_by_conflict"]),
        ("Ambiguous Entries", [item for item in selection.skipped_entries + selection.blocked_entries if item.get("migration_category") == "ambiguous"]),
        ("Orphan Entries", [item for item in selection.skipped_entries + selection.blocked_entries if item.get("migration_category") == "orphan"]),
        ("Already Migrated Entries", [item for item in selection.skipped_entries if item.get("migration_category") == "already_migrated"]),
    ]:
        lines.extend(["", f"## {title}", ""])
        if not entries:
            lines.append("- None")
        for item in entries:
            lines.append(_migration_entry_line(item))
    lines.extend(["", "## Safety Notes", "", "- Only `safe_merge` and `preserve_alias` entries are apply eligible.", "- Blocked, ambiguous, orphan, and already migrated entries are never applied.", "- Alias directories are preserved and never deleted.", "", "## Provenance", ""])
    lines.extend(f"- {key}: `{value}`" for key, value in selection.provenance.items())
    lines.append("")
    return "\n".join(lines)


def render_scoped_result_markdown(summary: CanonicalMigrationApplySummary) -> str:
    lines = [
        "# Scoped Canonical Migration Result",
        "",
        "## Executive Summary",
        "",
        f"- migration_id: `{summary.migration_id}`",
        f"- applied: `{summary.applied}`",
        f"- selected_count: `{summary.selected_count}`",
        f"- applied_count: `{summary.applied_count}`",
        f"- skipped_count: `{summary.skipped_count}`",
        f"- refused_count: `{summary.refused_count}`",
        f"- remaining_pending_count: `{summary.remaining_pending_count}`",
        f"- remaining_ready_count: `{summary.remaining_ready_count}`",
        f"- error: `{summary.error}`",
        "",
        "## Scope Applied",
        "",
    ]
    lines.extend(f"- {key}: `{value}`" for key, value in summary.scope.items())
    for title, entries in [
        ("Applied Entries", summary.applied_entries),
        ("Skipped Entries", summary.skipped_entries),
        ("Refused Entries", summary.refused_entries),
        ("Failures", summary.failed_entries),
    ]:
        lines.extend(["", f"## {title}", ""])
        if not entries:
            lines.append("- None")
        for item in entries:
            lines.append(_migration_entry_line(item))
    lines.extend(["", "## Backup Manifest", "", f"- `{summary.backup_manifest_path or 'not created'}`", "", "## Remaining Migration State", ""])
    for key in ["remaining_pending_count", "remaining_ready_count", "remaining_blocked_count", "remaining_orphan_count", "already_migrated_count"]:
        lines.append(f"- {key}: `{getattr(summary, key)}`")
    lines.extend(["", "## Safety Notes", "", "- No alias directories are deleted.", "- Blocked, ambiguous, orphan, and already migrated entries are not applied.", "- No conflicts are resolved automatically.", "", "## Provenance", ""])
    lines.extend(f"- {key}: `{value}`" for key, value in summary.provenance.items())
    lines.append("")
    return "\n".join(lines)


def _migration_entry_line(item: JsonMap) -> str:
    return (
        f"- `{item.get('source_assignment_id')}` -> `{item.get('target_canonical_assignment_id')}` "
        f"category={item.get('migration_category')} action={item.get('action')} status={item.get('status')} "
        f"risk={item.get('risk_level')} reason={item.get('selection_reason') or item.get('reason', '')}"
    )


def _aliases_for_cluster(cluster: JsonMap) -> list[CanonicalAssignmentAlias]:
    canonical_id = str(cluster.get("canonical_assignment_id") or "")
    rows = []
    raw_aliases = _string_list(cluster.get("assignment_aliases", []))
    raw_aliases.append(canonical_id)
    for alias in sorted(set(item for item in raw_aliases if item)):
        rows.append(
            CanonicalAssignmentAlias(
                alias=alias,
                alias_type=_alias_type(alias, cluster),
                canonical_assignment_id=canonical_id,
                source_paths=sorted({normalize_path(str(item.get("source_path") or "")) for item in _map_list(cluster.get("artifacts", []))}),
                first_seen=str(cluster.get("first_seen") or ""),
                last_seen=str(cluster.get("last_seen") or ""),
                status="active",
            )
        )
        safe = _safe_id(alias)
        if safe and safe != alias:
            rows.append(CanonicalAssignmentAlias(safe, _alias_type(alias, cluster) + "_safe_id", canonical_id, rows[-1].source_paths, rows[-1].first_seen, rows[-1].last_seen, "active"))
    return sorted({item.alias + "|" + item.canonical_assignment_id: item for item in rows}.values(), key=lambda item: item.alias)


def _alias_type(alias: str, cluster: JsonMap) -> str:
    if alias == str(cluster.get("canonical_assignment_id") or ""):
        return "canonical_assignment_id"
    if alias in _string_list(cluster.get("explicit_assignment_ids", [])):
        return "explicit_assignment_id"
    if alias in _string_list(cluster.get("order_ids", [])):
        return "explicit_order_id"
    if alias in _string_list(cluster.get("loan_numbers", [])):
        return "explicit_loan_number"
    if alias in _string_list(cluster.get("source_generated_ids", [])):
        return "source_generated_alias"
    if alias in _string_list(cluster.get("normalized_addresses", [])):
        return "normalized_address"
    if alias.startswith("hash-"):
        return "hash_fallback_alias"
    return "address_derived_alias"


def _alias_keys(value: str) -> set[str]:
    text = _clean_text(value)
    keys = {text, _safe_id(text)}
    normalized_address = normalize_address(text)
    if normalized_address:
        keys.add(normalized_address)
        keys.add(_safe_id(normalized_address))
    return {item for item in keys if item}


def is_migration_entry_apply_eligible(entry: JsonMap) -> bool:
    return str(entry.get("migration_category") or "") in APPLY_ELIGIBLE_MIGRATION_CATEGORIES and str(entry.get("status") or "") == "planned"


def _selection_skip_reason(entry: JsonMap, scope: CanonicalMigrationScope) -> str:
    category = str(entry.get("migration_category") or "")
    if scope.ready_only and category not in APPLY_ELIGIBLE_MIGRATION_CATEGORIES:
        return "excluded by ready_only scope"
    if scope.category and category != scope.category:
        return f"excluded by category scope `{scope.category}`"
    if scope.canonical_assignment_id and str(entry.get("target_canonical_assignment_id") or "") != scope.canonical_assignment_id:
        return f"excluded by assignment scope `{scope.canonical_assignment_id}`"
    if scope.source_assignment_id and str(entry.get("source_assignment_id") or "") != scope.source_assignment_id:
        return f"excluded by source assignment scope `{scope.source_assignment_id}`"
    if scope.apply and category == "already_migrated":
        return "already migrated entries are never reapplied"
    return ""


def _selection_reason(scope: CanonicalMigrationScope) -> str:
    parts = []
    if scope.ready_only:
        parts.append("ready_only")
    if scope.category:
        parts.append(f"category={scope.category}")
    if scope.canonical_assignment_id:
        parts.append(f"assignment={scope.canonical_assignment_id}")
    if scope.source_assignment_id:
        parts.append(f"source_assignment={scope.source_assignment_id}")
    if not parts:
        parts.append("all migration entries")
    return ", ".join(parts)


def _selection_counts(selected: list[JsonMap], skipped: list[JsonMap], blocked: list[JsonMap], invalid: list[JsonMap]) -> JsonMap:
    all_entries = selected + skipped
    counts = _migration_counts(all_entries)
    counts.update(
        {
            "selected_count": len(selected),
            "eligible_count": sum(1 for item in selected if item.get("apply_eligible")),
            "skipped_count": len(skipped),
            "refused_count": len(blocked) + len(invalid),
            "blocked_count": sum(1 for item in all_entries if item.get("migration_category") == "blocked_by_conflict"),
            "orphan_count": sum(1 for item in all_entries if item.get("migration_category") == "orphan"),
            "ambiguous_count": sum(1 for item in all_entries if item.get("migration_category") == "ambiguous"),
            "already_migrated_count": sum(1 for item in all_entries if item.get("migration_category") == "already_migrated"),
        }
    )
    return counts


def _refusal(entry: JsonMap, reason: str) -> JsonMap:
    item = dict(entry)
    item["refusal_reason"] = reason
    item["selection_status"] = "refused"
    return item


def _apply_summary_from_selection(
    selection: CanonicalMigrationSelection,
    *,
    applied: bool,
    started_at: str,
    completed_at: str,
    backup_manifest_path: str,
    error: str,
    extra_refused: list[JsonMap] | None = None,
) -> CanonicalMigrationApplySummary:
    refused = list(selection.blocked_entries) + list(selection.invalid_entries) + list(extra_refused or [])
    counts = selection.counts
    return CanonicalMigrationApplySummary(
        migration_id=selection.migration_id,
        selected_count=len(selection.selected_entries),
        applied_count=0,
        skipped_count=len(selection.skipped_entries),
        refused_count=len(refused),
        already_migrated_count=counts.get("already_migrated_count", 0),
        blocked_count=counts.get("blocked_count", 0),
        ambiguous_count=counts.get("ambiguous_count", 0),
        orphan_count=counts.get("orphan_count", 0),
        remaining_pending_count=counts.get("pending_migration_count", 0),
        remaining_ready_count=counts.get("migration_ready_count", 0),
        remaining_blocked_count=counts.get("blocked_count", 0),
        remaining_orphan_count=counts.get("orphan_count", 0),
        backup_manifest_path=backup_manifest_path,
        applied_entries=[],
        skipped_entries=selection.skipped_entries,
        refused_entries=refused,
        failed_entries=[],
        started_at=started_at,
        completed_at=completed_at,
        applied=applied,
        error=error,
        scope=selection.scope,
        provenance={"mode": "dry_run" if not applied else "apply", "deletion": "not_supported"},
    )


def _migration_counts(actions: list[JsonMap]) -> JsonMap:
    categories = ["safe_merge", "preserve_alias", "blocked_by_conflict", "ambiguous", "orphan", "already_migrated"]
    counts = {category + "_count": sum(1 for item in actions if item.get("migration_category") == category) for category in categories}
    counts["action_count"] = len(actions)
    counts["pending_migration_count"] = sum(1 for item in actions if item.get("migration_category") != "already_migrated")
    counts["migration_ready_count"] = counts["safe_merge_count"] + counts["preserve_alias_count"]
    counts["migrated_alias_directory_count"] = counts["already_migrated_count"]
    return counts


def _migration_action(source_id: str, target_id: str, source_dir: Path, target_dir: Path, alias_type: str, action: str, status: str, category: str) -> JsonMap:
    files = sorted(str(path) for path in source_dir.rglob("*") if path.is_file()) if source_dir.exists() else []
    reason = {
        "safe_merge": "Alias directory resolves deterministically to a canonical assignment and has source files to preserve.",
        "preserve_alias": "Alias directory resolves deterministically and should be preserved as an alias.",
        "blocked_by_conflict": "Canonical target has explicit conflicts that require review before migration.",
        "ambiguous": "Alias directory matches multiple canonical assignments.",
        "orphan": "Assignment directory does not match a canonical assignment or alias.",
        "already_migrated": "Alias directory is already marked as migrated.",
    }.get(category, "Review migration item.")
    suggested = {
        "safe_merge": "Review source files, then run canonical migrate --apply if acceptable.",
        "preserve_alias": "Preserve alias marker and verify future writes target the canonical assignment.",
        "blocked_by_conflict": "Resolve identity conflicts manually before applying migration.",
        "ambiguous": "Resolve to an explicit canonical assignment ID before migration.",
        "orphan": "Review whether this directory should become a source artifact or remain unassigned.",
        "already_migrated": "No action required.",
    }.get(category, "Resolve manually.")
    return {
        "migration_id": f"migration_{_digest(source_id + target_id + action + category)}",
        "source_assignment_id": source_id,
        "target_canonical_assignment_id": target_id,
        "source_directory": str(source_dir),
        "target_directory": str(target_dir),
        "alias_type": alias_type,
        "source_files": files,
        "source_values": {},
        "target_values": {},
        "conflicts": [],
        "action": action,
        "status": status,
        "migration_category": category,
        "affected_source_count": len(files),
        "reason": reason,
        "risk_level": "high" if category in {"blocked_by_conflict", "ambiguous"} else "medium" if category == "orphan" else "low",
        "suggested_operator_action": suggested,
        "provenance": {"rule": "alias_index_directory_comparison", "category_rule": category},
    }


def _read_assignment_output(root: Path, assignment_id: str) -> JsonMap:
    try:
        store = RealEstateAssignmentStore(root)
        if not (store.output_dir(assignment_id) / "assignment.json").exists():
            store.build(assignment_id)
        return store.load(assignment_id)
    except Exception:
        return {}


def _assignment_directory_clusters(root: Path) -> list[JsonMap]:
    store = RealEstateAssignmentStore(root)
    clusters = []
    for assignment_id in store.list_assignment_ids():
        output = _read_assignment_output(root, assignment_id)
        assignment = _map(output.get("assignment"))
        subject = _map(assignment.get("subject"))
        address = str(subject.get("address") or "")
        normalized = normalize_address(address)
        source_artifacts = [
            {
                "artifact_id": f"assignment_{_digest(assignment_id)}",
                "artifact_type": "assignment_yaml",
                "source_path": str(assignment_directory(root, assignment_id) / "assignment.yaml"),
                "source_type": "assignment_directory",
                "assignment_id": assignment_id,
                "order_id": "",
                "loan_number": "",
                "property_address": address,
                "normalized_address": normalized,
                "city": str(subject.get("city") or ""),
                "state": str(subject.get("state") or ""),
                "client": str(assignment.get("client_name") or ""),
                "lender": "",
                "amc": "",
                "effective_date": str(assignment.get("effective_date") or ""),
                "imported_at": str(assignment.get("created_at") or ""),
                "source_stem": "assignment",
                "source_generated_alias": assignment_id,
                "address_derived_alias": _safe_id(normalized) if normalized else "",
                "hash_fallback_alias": f"hash-{_digest(assignment_id)}",
                "provenance": {"source": "assignment_directory_fallback"},
            }
        ]
        aliases = sorted({assignment_id, normalized, _safe_id(normalized)} - {""})
        clusters.append(
            {
                "canonical_assignment_id": assignment_id,
                "artifact_count": 1,
                "source_types": ["assignment_yaml"],
                "first_seen": str(assignment.get("created_at") or ""),
                "last_seen": str(output.get("created_at") or ""),
                "assignment_status": str(output.get("status") or assignment.get("status") or "unknown"),
                "property_address": address,
                "city": str(subject.get("city") or ""),
                "state": str(subject.get("state") or ""),
                "client": str(assignment.get("client_name") or ""),
                "lender": "",
                "amc": "",
                "assignment_aliases": aliases,
                "explicit_assignment_ids": [assignment_id],
                "order_ids": [],
                "loan_numbers": [],
                "source_generated_ids": [assignment_id],
                "normalized_addresses": [normalized] if normalized else [],
                "canonical_identifiers": {"explicit_assignment_id": assignment_id},
                "identity_sources": [],
                "evidence_count": output.get("fact_count", 0),
                "knowledge_pack_available": False,
                "reviewer_notes_available": False,
                "conflicts": [],
                "artifacts": source_artifacts,
                "relationships": [],
                "provenance": {"source": "assignment_directory_fallback"},
            }
        )
    return clusters


def _snapshot_delta(previous: JsonMap, assignments: list[CanonicalAssignment], aliases: list[CanonicalAssignmentAlias], plan: CanonicalAssignmentMigrationPlan) -> CanonicalAssignmentDelta:
    prev_assignments = {str(item.get("canonical_assignment_id")) for item in _map_list(previous.get("assignments", []))}
    cur_assignments = {item.canonical_assignment_id for item in assignments}
    prev_aliases = {str(item.get("alias")) + "|" + str(item.get("canonical_assignment_id")) for item in _map_list(previous.get("aliases", []))}
    cur_aliases = {item.alias + "|" + item.canonical_assignment_id for item in aliases}
    return CanonicalAssignmentDelta(
        canonical_assignments_created=sorted(cur_assignments - prev_assignments),
        canonical_assignments_updated=sorted(cur_assignments & prev_assignments),
        aliases_added=sorted(cur_aliases - prev_aliases),
        aliases_removed=sorted(prev_aliases - cur_aliases),
        alias_directories_detected=sorted(str(item.get("source_assignment_id")) for item in plan.actions if item.get("action") == "merge_into_canonical"),
        alias_directories_migrated=sorted(str(item.get("source_assignment_id")) for item in plan.actions if item.get("status") == "already_migrated"),
        fields_normalized=[],
        false_conflicts_resolved=[],
        true_conflicts_added=sorted({str(conflict.get("conflict_id")) for assignment in assignments for conflict in assignment.conflicts}),
        sources_merged=sorted({str(source.get("source_path")) for assignment in assignments for source in assignment.source_artifacts if source.get("source_path")}),
        assignments_split=[],
        assignments_merged=[],
    )


def _snapshot_id(assignments: list[CanonicalAssignment], aliases: list[CanonicalAssignmentAlias]) -> str:
    payload = "|".join([*(item.canonical_assignment_id for item in assignments), *(item.alias + item.canonical_assignment_id for item in aliases)])
    return f"canonical_assignment_{_digest(payload)}"


def _ambiguous_alias_count(aliases: list[CanonicalAssignmentAlias]) -> int:
    seen: dict[str, set[str]] = {}
    for alias in aliases:
        seen.setdefault(alias.alias, set()).add(alias.canonical_assignment_id)
    return sum(1 for values in seen.values() if len(values) > 1)


def _first(data: JsonMap, keys: list[str]) -> str:
    for key in keys:
        value = data.get(key)
        if value is not None and str(value).strip():
            return _clean_text(str(value))
    return ""


def _clean_text(value: str) -> str:
    text = html.unescape(str(value or "")).replace("\xa0", " ")
    text = text.replace("&#160;", " ")
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"^[\s,.;:|/\\-]+|[\s,.;:|/\\-]+$", "", text)
    text = re.sub(r"[-_,;:|/\\]{2,}", " ", text)
    return text.strip()


def _safe_id(value: str) -> str:
    text = _clean_text(value).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text)
    text = re.sub(r"-+", "-", text).strip("-")
    return text or "assignment"


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
