from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from . import __version__
from .assignment_consolidation import AssignmentConsolidationEngine
from .canonical_assignments import CanonicalAssignmentEngine, CanonicalAssignmentStore
from .canonical_operations import CanonicalOperationsEngine, CanonicalOperationsStore
from .comparable_intelligence import ComparableIntelligenceEngine, ComparableStore
from .dashboard import ExecutiveDashboardStore
from .io import read_json, write_json
from .models import JsonMap
from .real_estate import RealEstateAssignmentStore
from .real_estate_intake import RealEstateIntakeEngine, RealEstateIntakeStore


class RealEstateDailyError(RuntimeError):
    pass


@dataclass(frozen=True)
class RealEstateDailySummary:
    status: str
    intake_candidates: int
    artifacts_imported: int
    artifacts_updated: int
    canonical_assignments_created: int
    canonical_assignments_updated: int
    assignments_built: int
    review_item_count: int
    warning_count: int
    error_count: int

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class RealEstateDailyStage:
    name: str
    status: str
    started_at: str
    completed_at: str
    counts: JsonMap
    warnings: list[str]
    errors: list[str]
    output_paths: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class RealEstateDailyRun:
    run_id: str
    started_at: str
    completed_at: str
    status: str
    stages: list[RealEstateDailyStage]
    intake_candidates: int
    artifacts_imported: int
    artifacts_updated: int
    duplicate_artifacts_skipped: int
    canonical_assignments_created: int
    canonical_assignments_updated: int
    assignments_built: int
    aliases_resolved: int
    migrated_aliases_detected: int
    blocked_migrations: int
    orphan_artifacts: int
    true_conflicts: int
    missing_critical_assignments: int
    comparable_inputs_changed: int
    comparable_assignments_built: int
    comparable_records_added: int
    comparable_records_updated: int
    comparable_conflicts_opened: int
    comparable_review_items: int
    limited_coverage_assignments: int
    comparable_scenarios_detected: int
    comparable_scenarios_changed: int
    comparable_scenarios_built: int
    comparable_scenario_records_added: int
    comparable_scenario_records_updated: int
    comparable_scenario_conflicts_opened: int
    comparable_scenario_review_items: int
    limited_coverage_scenarios: int
    review_item_count: int
    warning_count: int
    error_count: int
    output_paths: JsonMap
    provenance: JsonMap
    version: str

    @property
    def summary(self) -> RealEstateDailySummary:
        return RealEstateDailySummary(
            status=self.status,
            intake_candidates=self.intake_candidates,
            artifacts_imported=self.artifacts_imported,
            artifacts_updated=self.artifacts_updated,
            canonical_assignments_created=self.canonical_assignments_created,
            canonical_assignments_updated=self.canonical_assignments_updated,
            assignments_built=self.assignments_built,
            review_item_count=self.review_item_count,
            warning_count=self.warning_count,
            error_count=self.error_count,
        )

    def to_dict(self) -> JsonMap:
        data = self.__dict__.copy()
        data["stages"] = [stage.to_dict() for stage in self.stages]
        data["summary"] = self.summary.to_dict()
        return data


class RealEstateDailyStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "outputs" / "real-estate" / "daily"
        self.latest_json = self.directory / "latest-real-estate-daily-run.json"
        self.report_md = self.directory / "real-estate-daily-report.md"
        self.history_json = self.directory / "real-estate-daily-history.json"
        self.delta_json = self.directory / "real-estate-daily-delta.json"

    def load(self) -> JsonMap:
        return read_json(self.latest_json) if self.latest_json.exists() else {}

    def history(self) -> list[JsonMap]:
        if not self.history_json.exists():
            return []
        return _map_list(read_json(self.history_json).get("runs", []))

    def save(self, run: RealEstateDailyRun, delta: JsonMap) -> None:
        data = run.to_dict()
        write_json(self.latest_json, data)
        history = self.history()
        if not history or history[-1].get("run_id") != run.run_id:
            history.append(data)
        write_json(self.history_json, {"runs": history})
        write_json(self.delta_json, delta)
        self.report_md.parent.mkdir(parents=True, exist_ok=True)
        self.report_md.write_text(render_real_estate_daily_report(run, delta), encoding="utf-8")


class RealEstateDailyEngine:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.store = RealEstateDailyStore(root)

    def run(self, *, overwrite: bool = False, open_review: bool = False, full_refresh: bool = False) -> RealEstateDailyRun:
        if self.store.latest_json.exists() and not overwrite:
            previous = self.store.load()
        else:
            previous = self.store.load()
        started_at = _now_iso()
        stages: list[RealEstateDailyStage] = []
        warnings: list[str] = []
        errors: list[str] = []
        output_paths: JsonMap = {}
        affected_assignments: set[str] = set()

        intake_engine = RealEstateIntakeEngine(self.root)
        config = intake_engine.store.load_config()
        enabled_sources = [source.id for source in intake_engine.store.sources() if source.enabled]
        try:
            candidates = intake_engine.scan()
            intake_status_warnings = []
            stages.append(_stage("Real Estate Intake Status", {"intake_candidates": len(candidates), "enabled_sources": len(enabled_sources)}, intake_status_warnings, []))
            warnings.extend(intake_status_warnings)
        except Exception as exc:
            raise RealEstateDailyError(f"Real Estate intake status failed: {exc}") from exc

        try:
            intake_result = intake_engine.import_candidates()
            manifest = intake_result.manifest
            imported_records = [record for record in manifest.records if record.import_status in {"imported", "updated"}]
            affected_assignments.update(record.detected_assignment_id for record in imported_records if record.detected_assignment_id)
            aliases_resolved = sum(1 for record in manifest.records if _map(record.provenance).get("original_identifier"))
            stages.append(
                _stage(
                    "Real Estate Intake Import",
                    {"imported": manifest.counts.get("imported", 0), "updated": manifest.counts.get("updated", 0), "skipped_duplicate": manifest.counts.get("skipped_duplicate", 0), "errors": manifest.counts.get("errors", 0)},
                    [],
                    [str(error.get("error") or error) for error in manifest.errors],
                )
            )
            errors.extend(str(error.get("error") or error) for error in manifest.errors)
            output_paths["intake_manifest"] = str(RealEstateIntakeStore(self.root).manifest_path)
        except Exception as exc:
            raise RealEstateDailyError(f"Real Estate intake import failed: {exc}") from exc

        try:
            consolidation = AssignmentConsolidationEngine(self.root).build()
            stages.append(_stage("Real Estate Consolidation Refresh", {"canonical_assignments": consolidation.counts.get("canonical_assignment_count", 0), "artifacts": consolidation.counts.get("artifact_count", 0), "aliases": consolidation.counts.get("alias_count", 0)}, [], []))
            output_paths["consolidation"] = str(self.root / "outputs" / "real-estate" / "consolidation" / "assignment-clusters.json")
        except Exception as exc:
            raise RealEstateDailyError(f"Real Estate consolidation refresh failed: {exc}") from exc

        try:
            canonical_engine = CanonicalAssignmentEngine(self.root)
            before_canonical = _map(previous.get("canonical_counts"))
            canonical = canonical_engine.build()
            canonical_ids = {item.canonical_assignment_id for item in canonical.assignments}
            if full_refresh:
                affected_assignments.update(canonical_ids)
            if before_canonical:
                created = max(0, int(canonical.counts.get("canonical_assignment_count", 0)) - int(before_canonical.get("canonical_assignment_count", 0)))
            else:
                created = len(affected_assignments & canonical_ids)
            updated = len(affected_assignments & canonical_ids)
            stages.append(_stage("Canonical Assignment Refresh", {"created": created, "updated": updated, **canonical.counts}, [], []))
            output_paths["canonical_assignments"] = str(CanonicalAssignmentStore(self.root).assignments_json)
        except Exception as exc:
            raise RealEstateDailyError(f"Canonical assignment refresh failed: {exc}") from exc

        built_assignments: list[str] = []
        build_errors: list[str] = []
        assignment_store = RealEstateAssignmentStore(self.root)
        for assignment_id in sorted(affected_assignments):
            if assignment_id not in canonical_ids:
                continue
            try:
                assignment_store.build(assignment_id)
                built_assignments.append(assignment_id)
            except Exception as exc:
                build_errors.append(f"{assignment_id}: {exc}")
        stages.append(_stage("Real Estate Assignment Intelligence", {"assignments_built": len(built_assignments)}, [f"Assignment build failures: {len(build_errors)}"] if build_errors else [], build_errors))
        warnings.extend(f"Assignment build failures: {len(build_errors)}" for _ in [0] if build_errors)

        comparable_builds: list[str] = []
        comparable_errors: list[str] = []
        comparable_records_added = 0
        comparable_records_updated = 0
        comparable_conflicts_opened = 0
        comparable_review_items = 0
        limited_coverage_assignments = 0
        comparable_store = ComparableStore(self.root)
        previous_comparable_checksums = _map(_map(previous.get("provenance")).get("comparable_input_checksums"))
        comparable_input_checksums = _comparable_input_checksums(comparable_store, sorted(canonical_ids))
        changed_comparable_scenarios = [
            scenario_key
            for scenario_key, checksum in comparable_input_checksums.items()
            if full_refresh or previous_comparable_checksums.get(scenario_key) != checksum
        ]
        comparable_engine = ComparableIntelligenceEngine(self.root)
        for scenario_key in changed_comparable_scenarios:
            assignment_id, scenario = scenario_key.split("::", 1)
            try:
                before = comparable_store.load(assignment_id, scenario)
                universe = comparable_engine.build(assignment_id, scenario=None if scenario == "default" else scenario, overwrite=True)
                scenario_output = comparable_store.output_dir(assignment_id, scenario)
                delta = _map(read_json(scenario_output / "comparable-delta.json")) if (scenario_output / "comparable-delta.json").exists() else {}
                comparable_builds.append(scenario_key)
                comparable_records_added += len(delta.get("new_candidates", []) or [])
                comparable_records_updated += len(delta.get("updated_candidates", []) or [])
                comparable_conflicts_opened += int(universe.counts.get("open_conflict_count", 0) or 0) - int(_map(before.get("counts")).get("open_conflict_count", 0) or 0)
                comparable_review_items += int(universe.counts.get("review_item_count", 0) or 0)
                if any(level in {"limited", "absent"} for level in universe.coverage.levels.values()):
                    limited_coverage_assignments += 1
            except Exception as exc:
                comparable_errors.append(f"{assignment_id}: {exc}")
        stages.append(
            _stage(
                "Comparable Intelligence",
                {
                    "comparable_scenarios_detected": len(comparable_input_checksums),
                    "comparable_scenarios_changed": len(changed_comparable_scenarios),
                    "comparable_scenarios_built": len(comparable_builds),
                    "comparable_scenario_records_added": comparable_records_added,
                    "comparable_scenario_records_updated": comparable_records_updated,
                    "comparable_scenario_conflicts_opened": comparable_conflicts_opened,
                    "comparable_scenario_review_items": comparable_review_items,
                    "limited_coverage_scenarios": limited_coverage_assignments,
                    "comparable_inputs_changed": len(changed_comparable_scenarios),
                    "assignments_built": len({item.split('::', 1)[0] for item in comparable_builds}),
                    "records_added": comparable_records_added,
                    "records_updated": comparable_records_updated,
                    "conflicts_opened": comparable_conflicts_opened,
                    "review_items": comparable_review_items,
                    "limited_coverage_assignments": limited_coverage_assignments,
                },
                [],
                comparable_errors,
            )
        )
        errors.extend(comparable_errors)

        try:
            operations = CanonicalOperationsEngine(self.root).build(save=True)
            operations_summary = operations.summary
            review_queue = operations.review_queue
            review_warnings = _review_warnings(operations_summary)
            stages.append(_stage("Canonical Operations", operations_summary, review_warnings, []))
            warnings.extend(review_warnings)
            output_paths["review_queue"] = str(CanonicalOperationsStore(self.root).review_queue_md)
            output_paths["operations_report"] = str(CanonicalOperationsStore(self.root).operations_report_md)
        except Exception as exc:
            raise RealEstateDailyError(f"Canonical operations refresh failed: {exc}") from exc

        try:
            dashboard = ExecutiveDashboardStore(self.root).generate(overwrite=True)
            stages.append(_stage("Dashboard Refresh", {"dashboard_id": dashboard.dashboard_id}, [], []))
            output_paths["dashboard"] = str(self.root / "outputs" / "dashboard" / "dashboard.json")
        except Exception as exc:
            raise RealEstateDailyError(f"Dashboard refresh failed: {exc}") from exc

        completed_at = _now_iso()
        status = "failed" if errors else "completed_with_warnings" if warnings else "completed"
        canonical_counts = _map(canonical.counts if "canonical" in locals() else {})
        run = RealEstateDailyRun(
            run_id=f"real_estate_daily_{_digest(started_at + completed_at + str(len(stages)))}",
            started_at=started_at,
            completed_at=completed_at,
            status=status,
            stages=stages,
            intake_candidates=len(candidates) if "candidates" in locals() else 0,
            artifacts_imported=int(manifest.counts.get("imported", 0)) if "manifest" in locals() else 0,
            artifacts_updated=int(manifest.counts.get("updated", 0)) if "manifest" in locals() else 0,
            duplicate_artifacts_skipped=int(manifest.counts.get("skipped_duplicate", 0)) if "manifest" in locals() else 0,
            canonical_assignments_created=created if "created" in locals() else 0,
            canonical_assignments_updated=updated if "updated" in locals() else 0,
            assignments_built=len(built_assignments),
            aliases_resolved=aliases_resolved if "aliases_resolved" in locals() else 0,
            migrated_aliases_detected=int(canonical_counts.get("already_migrated_count", 0)),
            blocked_migrations=int(canonical_counts.get("blocked_by_conflict_count", 0)),
            orphan_artifacts=int(canonical_counts.get("orphan_count", 0)),
            true_conflicts=int(canonical_counts.get("true_assignment_conflict_count", 0)),
            missing_critical_assignments=_missing_critical_count(review_queue if "review_queue" in locals() else []),
            comparable_inputs_changed=len(changed_comparable_scenarios) if "changed_comparable_scenarios" in locals() else 0,
            comparable_assignments_built=len({item.split('::', 1)[0] for item in comparable_builds}) if "comparable_builds" in locals() else 0,
            comparable_records_added=comparable_records_added if "comparable_records_added" in locals() else 0,
            comparable_records_updated=comparable_records_updated if "comparable_records_updated" in locals() else 0,
            comparable_conflicts_opened=comparable_conflicts_opened if "comparable_conflicts_opened" in locals() else 0,
            comparable_review_items=comparable_review_items if "comparable_review_items" in locals() else 0,
            limited_coverage_assignments=limited_coverage_assignments if "limited_coverage_assignments" in locals() else 0,
            comparable_scenarios_detected=len(comparable_input_checksums) if "comparable_input_checksums" in locals() else 0,
            comparable_scenarios_changed=len(changed_comparable_scenarios) if "changed_comparable_scenarios" in locals() else 0,
            comparable_scenarios_built=len(comparable_builds) if "comparable_builds" in locals() else 0,
            comparable_scenario_records_added=comparable_records_added if "comparable_records_added" in locals() else 0,
            comparable_scenario_records_updated=comparable_records_updated if "comparable_records_updated" in locals() else 0,
            comparable_scenario_conflicts_opened=comparable_conflicts_opened if "comparable_conflicts_opened" in locals() else 0,
            comparable_scenario_review_items=comparable_review_items if "comparable_review_items" in locals() else 0,
            limited_coverage_scenarios=limited_coverage_assignments if "limited_coverage_assignments" in locals() else 0,
            review_item_count=len(review_queue) if "review_queue" in locals() else 0,
            warning_count=len(warnings),
            error_count=len(errors),
            output_paths={**output_paths, "daily_report": str(self.store.report_md), "latest_run": str(self.store.latest_json)},
            provenance={"engine": "RealEstateDailyEngine", "version": __version__, "canonical_counts": canonical_counts, "migration_applied": 0, "comparable_input_checksums": comparable_input_checksums if "comparable_input_checksums" in locals() else {}},
            version=__version__,
        )
        delta = _delta(previous, run)
        self.store.save(run, delta)
        if open_review and _should_open_real_estate_report(run, delta):
            _open_review_files(run)
        return run


def render_real_estate_daily_report(run: RealEstateDailyRun, delta: JsonMap) -> str:
    lines = [
        "# Real Estate Daily Automation",
        "",
        "## Executive Summary",
        "",
        f"- Run ID: `{run.run_id}`",
        f"- Status: `{run.status}`",
        f"- Intake candidates: `{run.intake_candidates}`",
        f"- Imported artifacts: `{run.artifacts_imported}`",
        f"- Updated artifacts: `{run.artifacts_updated}`",
        f"- Assignments built: `{run.assignments_built}`",
        f"- Review items: `{run.review_item_count}`",
        f"- Warnings: `{run.warning_count}`",
        f"- Errors: `{run.error_count}`",
        "",
        "## Intake Activity",
        "",
        f"- Duplicate artifacts skipped: `{run.duplicate_artifacts_skipped}`",
        f"- Aliases resolved: `{run.aliases_resolved}`",
        "",
        "## Canonical Assignment Activity",
        "",
        f"- Canonical assignments created: `{run.canonical_assignments_created}`",
        f"- Canonical assignments updated: `{run.canonical_assignments_updated}`",
        f"- Migrated aliases detected: `{run.migrated_aliases_detected}`",
        f"- Blocked migrations: `{run.blocked_migrations}`",
        f"- Orphan artifacts: `{run.orphan_artifacts}`",
        f"- True conflicts: `{run.true_conflicts}`",
        "",
        "## Assignment Intelligence Builds",
        "",
        f"- Assignment briefs built: `{run.assignments_built}`",
        "",
        "## Comparable Intelligence",
        "",
        f"- Comparable scenarios detected: `{run.comparable_scenarios_detected}`",
        f"- Comparable scenarios changed: `{run.comparable_scenarios_changed}`",
        f"- Comparable scenarios built: `{run.comparable_scenarios_built}`",
        f"- Scenario records added: `{run.comparable_scenario_records_added}`",
        f"- Scenario records updated: `{run.comparable_scenario_records_updated}`",
        f"- Scenario conflicts opened: `{run.comparable_scenario_conflicts_opened}`",
        f"- Scenario review items: `{run.comparable_scenario_review_items}`",
        f"- Limited coverage scenarios: `{run.limited_coverage_scenarios}`",
        f"- Comparable inputs changed: `{run.comparable_inputs_changed}`",
        f"- Comparable assignments built: `{run.comparable_assignments_built}`",
        f"- Comparable records added: `{run.comparable_records_added}`",
        f"- Comparable records updated: `{run.comparable_records_updated}`",
        f"- Comparable conflicts opened: `{run.comparable_conflicts_opened}`",
        f"- Comparable review items: `{run.comparable_review_items}`",
        f"- Limited coverage assignments: `{run.limited_coverage_assignments}`",
        "",
        "## Review Queue",
        "",
        f"- Review items: `{run.review_item_count}`",
        f"- Missing critical assignments: `{run.missing_critical_assignments}`",
        f"- Review queue: `{run.output_paths.get('review_queue', '')}`",
        "",
        "## Warnings",
        "",
    ]
    warning_lines = [warning for stage in run.stages for warning in stage.warnings]
    lines.extend(f"- {item}" for item in warning_lines or ["None"])
    lines.extend(["", "## Errors", ""])
    error_lines = [error for stage in run.stages for error in stage.errors]
    lines.extend(f"- {item}" for item in error_lines or ["None"])
    lines.extend(["", "## Key Assignment Briefs", ""])
    lines.append("- Assignment briefs are built only for affected canonical assignments.")
    lines.extend(["", "## No-Change Summary", ""])
    lines.append(f"- No-change run: `{delta.get('no_change', False)}`")
    lines.append(f"- Canonical counts changed: `{delta.get('canonical_counts_changed', False)}`")
    lines.extend(["", "## Limitations", ""])
    lines.append("- This automation performs deterministic intake, identity, canonical, operations, and dashboard refresh only.")
    lines.append("- It does not generate valuation opinions, select comparables, create adjustments, resolve conflicts, or apply migrations.")
    lines.extend(["", "## Provenance", ""])
    for key, value in run.output_paths.items():
        lines.append(f"- {key}: `{value}`")
    lines.append("")
    return "\n".join(lines)


def _stage(name: str, counts: JsonMap, warnings: list[str], errors: list[str]) -> RealEstateDailyStage:
    now = _now_iso()
    return RealEstateDailyStage(name=name, status="failed" if errors else "completed_with_warnings" if warnings else "completed", started_at=now, completed_at=now, counts=counts, warnings=warnings, errors=errors, output_paths={})


def _review_warnings(summary: JsonMap) -> list[str]:
    warnings = []
    for key, label in [
        ("blocked_by_conflict_count", "blocked migration entries"),
        ("orphan_count", "orphan artifacts"),
        ("true_assignment_conflict_count", "true assignment conflicts"),
    ]:
        count = int(summary.get(key, 0) or 0)
        if count:
            warnings.append(f"{label}: {count}")
    return warnings


def _missing_critical_count(review_queue: list[JsonMap]) -> int:
    return sum(1 for item in review_queue if item.get("category") == "missing_critical_fields")


def _delta(previous: JsonMap, run: RealEstateDailyRun) -> JsonMap:
    prev_provenance = _map(previous.get("provenance"))
    prev_counts = _map(prev_provenance.get("canonical_counts"))
    cur_counts = _map(run.provenance.get("canonical_counts"))
    no_activity = run.artifacts_imported == 0 and run.artifacts_updated == 0 and run.assignments_built == 0 and run.canonical_assignments_created == 0 and run.canonical_assignments_updated == 0
    return {
        "previous_run_id": previous.get("run_id", ""),
        "current_run_id": run.run_id,
        "no_change": bool(no_activity),
        "canonical_counts_changed": bool(prev_counts and prev_counts != cur_counts),
        "artifacts_imported_change": run.artifacts_imported - int(previous.get("artifacts_imported", 0) or 0),
        "assignments_built_change": run.assignments_built - int(previous.get("assignments_built", 0) or 0),
        "review_item_count_change": run.review_item_count - int(previous.get("review_item_count", 0) or 0),
        "created_at": _now_iso(),
    }


def _should_open_real_estate_report(run: RealEstateDailyRun, delta: JsonMap) -> bool:
    return any([run.artifacts_imported, run.artifacts_updated, run.canonical_assignments_created, run.canonical_assignments_updated, run.assignments_built, run.warning_count, run.error_count, not delta.get("no_change", False)])


def _open_review_files(run: RealEstateDailyRun) -> None:
    import subprocess

    paths = [run.output_paths.get("daily_report")]
    if run.review_item_count:
        paths.append(run.output_paths.get("review_queue"))
    for path in [item for item in paths if item]:
        try:
            subprocess.run(["code", "-r", str(path)], check=False)
        except Exception:
            pass


def _now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:16]


def _comparable_input_checksums(store: ComparableStore, assignment_ids: list[str]) -> JsonMap:
    checksums: JsonMap = {}
    for assignment_id in assignment_ids:
        for context in store.available_contexts(assignment_id):
            parts = []
            for path in context.input_files:
                try:
                    parts.append(f"{path.name}:{sha256(path.read_bytes()).hexdigest()}")
                except OSError:
                    parts.append(f"{path.name}:unreadable")
            checksums[f"{assignment_id}::{context.resolved_scenario}"] = _digest("|".join(parts))
    return checksums


def _map(value: Any) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _map_list(value: Any) -> list[JsonMap]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []
