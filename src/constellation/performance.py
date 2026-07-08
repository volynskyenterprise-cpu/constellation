from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from . import __version__
from .io import read_json, write_json
from .models import JsonMap


class PerformanceIntelligenceError(RuntimeError):
    pass


PERFORMANCE_INPUTS = {
    "decision_journal": Path("outputs/ai-markets/decisions/decision-journal.json"),
    "decision_entries": Path("outputs/ai-markets/decisions/decision-entries.json"),
    "decision_review_queue": Path("outputs/ai-markets/decisions/decision-review-queue.json"),
    "decision_outcomes": Path("outputs/ai-markets/decisions/decision-outcomes.json"),
    "decision_delta": Path("outputs/ai-markets/decisions/decision-delta.json"),
    "morning_brief": Path("outputs/ai-markets/briefings/morning-brief.json"),
    "research_agenda": Path("outputs/ai-markets/briefings/research-agenda.json"),
    "theme_lifecycle": Path("outputs/ai-markets/theme-lifecycle.json"),
    "theme_history": Path("outputs/ai-markets/theme-history.json"),
    "theme_transitions": Path("outputs/ai-markets/theme-transitions.json"),
    "catalyst_monitor": Path("outputs/ai-markets/catalysts/catalyst-monitor.json"),
    "catalyst_delta": Path("outputs/ai-markets/catalysts/catalyst-delta.json"),
    "catalyst_transitions": Path("outputs/ai-markets/catalysts/catalyst-transitions.json"),
    "portfolio_intelligence": Path("outputs/ai-markets/portfolio/portfolio-intelligence.json"),
    "portfolio_delta": Path("outputs/ai-markets/portfolio/portfolio-delta.json"),
    "portfolio_risks": Path("outputs/ai-markets/portfolio/portfolio-risks.json"),
    "ai_markets": Path("outputs/ai-markets/ai-markets.json"),
    "dashboard": Path("outputs/dashboard/dashboard.json"),
    "latest_report": Path("outputs/reports/latest-report.json"),
    "evidence_graph": Path("outputs/evidence-graph/evidence-graph.json"),
    "theses": Path("outputs/thesis/theses.json"),
    "evolution": Path("outputs/evolution/evolution.json"),
    "source_monitor": Path("outputs/source-monitor/latest-monitor.json"),
}


OUTCOME_PRIORITY = {
    "review_overdue": 0,
    "review_due": 1,
    "user_contradicted": 2,
    "user_challenged": 3,
    "lesson_recorded": 4,
    "user_confirmed": 5,
    "no_outcome_recorded": 6,
    "pending": 7,
}

SEVERITY_PRIORITY = {"high": 0, "medium": 1, "low": 2}


@dataclass(frozen=True)
class DecisionOutcomeLink:
    link_type: str
    target_id: str
    title: str
    source_path: str
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class DecisionOutcome:
    outcome_id: str
    entry_id: str
    title: str
    decision_type: str
    entry_type: str
    status: str
    outcome_status: str
    review_status: str
    created_at: str
    review_at: str | None
    related_themes: list[str]
    related_entities: list[str]
    related_catalysts: list[str]
    related_risks: list[str]
    linked_lifecycle_changes: list[JsonMap]
    linked_catalyst_changes: list[JsonMap]
    linked_portfolio_changes: list[JsonMap]
    linked_risk_changes: list[JsonMap]
    user_recorded_outcome: str
    user_recorded_lessons: str
    system_observations: list[str]
    follow_up_needed: bool
    follow_up_reason: str
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class PerformanceSignal:
    signal_id: str
    signal_type: str
    title: str
    description: str
    related_decision_ids: list[str]
    related_themes: list[str]
    related_entities: list[str]
    related_catalysts: list[str]
    severity: str
    evidence_count: int
    source_paths: list[str]
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ProcessLesson:
    lesson_id: str
    lesson_type: str
    title: str
    description: str
    related_decision_ids: list[str]
    related_themes: list[str]
    related_entities: list[str]
    evidence: list[str]
    created_at: str
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class LearningLoopSnapshot:
    snapshot_id: str
    created_at: str
    available: bool
    decision_count: int
    reviewed_decision_count: int
    open_decision_count: int
    due_review_count: int
    overdue_review_count: int
    outcome_count: int
    pending_outcome_count: int
    lesson_count: int
    performance_signal_count: int
    high_severity_signal_count: int
    linked_theme_count: int
    linked_entity_count: int
    linked_catalyst_count: int
    linked_risk_count: int
    source_artifacts_available: list[str]
    source_artifacts_missing: list[str]
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class PerformanceDelta:
    new_decision_outcomes: list[str]
    removed_decision_outcomes: list[str]
    outcome_status_changes: list[JsonMap]
    new_performance_signals: list[str]
    removed_performance_signals: list[str]
    new_process_lessons: list[str]
    review_count_changes: JsonMap
    source_artifact_availability_changes: list[str]

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class PerformanceReview:
    review_id: str
    created_at: str
    decision_outcome_ids: list[str]
    performance_signal_ids: list[str]
    process_lesson_ids: list[str]
    summary: str
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class PerformanceIntelligenceReport:
    report_id: str
    created_at: str
    version: str
    review: PerformanceReview
    learning_loop: LearningLoopSnapshot
    decision_outcomes: list[DecisionOutcome]
    performance_signals: list[PerformanceSignal]
    process_lessons: list[ProcessLesson]
    delta: PerformanceDelta
    recommended_process_improvements: list[str]
    limitations: list[str]
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return {
            "report_id": self.report_id,
            "created_at": self.created_at,
            "version": self.version,
            "review": self.review.to_dict(),
            "learning_loop": self.learning_loop.to_dict(),
            "decision_outcomes": [item.to_dict() for item in self.decision_outcomes],
            "performance_signals": [item.to_dict() for item in self.performance_signals],
            "process_lessons": [item.to_dict() for item in self.process_lessons],
            "delta": self.delta.to_dict(),
            "recommended_process_improvements": self.recommended_process_improvements,
            "limitations": self.limitations,
            "provenance": self.provenance,
            **self.learning_loop.to_dict(),
        }


class PerformanceIntelligenceEngine:
    def __init__(self, root: Path) -> None:
        self.root = root

    def build(self, history: list[JsonMap]) -> PerformanceIntelligenceReport:
        artifacts = _performance_artifacts(self.root)
        available = sorted(name for name, value in artifacts.items() if value)
        missing = sorted(name for name, value in artifacts.items() if not value)
        decision_entries = _decision_entries(artifacts)
        decision_outcomes = sorted((_decision_outcome(entry, artifacts) for entry in decision_entries), key=_decision_outcome_sort_key)
        signals = sorted(_performance_signals(decision_outcomes, artifacts), key=_signal_sort_key)
        lessons = sorted(_process_lessons(decision_outcomes, signals), key=_lesson_sort_key)
        snapshot = _learning_loop_snapshot(decision_outcomes, signals, lessons, available, missing)
        previous = history[-1] if history else {}
        delta = _performance_delta(previous, decision_outcomes, signals, lessons, snapshot)
        review = PerformanceReview(
            review_id=f"performance_review_{_digest(snapshot.snapshot_id)}",
            created_at=snapshot.created_at,
            decision_outcome_ids=[item.outcome_id for item in decision_outcomes],
            performance_signal_ids=[item.signal_id for item in signals],
            process_lesson_ids=[item.lesson_id for item in lessons],
            summary=_review_summary(snapshot),
            provenance={"source": "outputs/performance/learning-loop.json"},
        )
        improvements = _process_improvements(decision_outcomes, signals)
        limitations = [
            "Performance Intelligence is a deterministic learning layer.",
            "It does not calculate returns, evaluate client performance, make allocation changes, or produce investment instructions.",
            "Missing source artifacts are reported as unavailable rather than inferred.",
        ]
        provenance = {"consumed_artifacts": {key: str(path) for key, path in PERFORMANCE_INPUTS.items()}}
        return PerformanceIntelligenceReport(
            report_id=f"performance_{_digest(snapshot.snapshot_id + review.summary)}",
            created_at=snapshot.created_at,
            version=__version__,
            review=review,
            learning_loop=snapshot,
            decision_outcomes=decision_outcomes,
            performance_signals=signals,
            process_lessons=lessons,
            delta=delta,
            recommended_process_improvements=improvements,
            limitations=limitations,
            provenance=provenance,
        )


class PerformanceIntelligenceStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "outputs" / "performance"
        self.report_json_path = self.directory / "performance-intelligence.json"
        self.report_markdown_path = self.directory / "performance-intelligence.md"
        self.decision_outcomes_json_path = self.directory / "decision-outcomes.json"
        self.decision_outcomes_markdown_path = self.directory / "decision-outcomes.md"
        self.signals_json_path = self.directory / "performance-signals.json"
        self.signals_markdown_path = self.directory / "performance-signals.md"
        self.lessons_json_path = self.directory / "process-lessons.json"
        self.lessons_markdown_path = self.directory / "process-lessons.md"
        self.learning_loop_json_path = self.directory / "learning-loop.json"
        self.learning_loop_markdown_path = self.directory / "learning-loop.md"
        self.history_path = self.directory / "performance-history.json"
        self.delta_path = self.directory / "performance-delta.json"

    def build(self) -> PerformanceIntelligenceReport:
        report = PerformanceIntelligenceEngine(self.root).build(self.history())
        self.save(report)
        return report

    def load(self) -> JsonMap:
        if not self.report_json_path.exists():
            raise PerformanceIntelligenceError("No Performance Intelligence report found. Run `python -m constellation performance` first.")
        return read_json(self.report_json_path)

    def history(self) -> list[JsonMap]:
        if not self.history_path.exists():
            return []
        return _map_list(read_json(self.history_path).get("reports", []))

    def save(self, report: PerformanceIntelligenceReport) -> None:
        data = report.to_dict()
        write_json(self.report_json_path, data)
        write_json(self.decision_outcomes_json_path, {"decision_outcomes": data["decision_outcomes"]})
        write_json(self.signals_json_path, {"performance_signals": data["performance_signals"]})
        write_json(self.lessons_json_path, {"process_lessons": data["process_lessons"]})
        write_json(self.learning_loop_json_path, data["learning_loop"])
        write_json(self.delta_path, data["delta"])
        history = self.history()
        if not history or history[-1].get("report_id") != report.report_id:
            history.append(data)
        write_json(self.history_path, {"reports": history})
        self.report_markdown_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_markdown_path.write_text(render_performance_report(report), encoding="utf-8")
        self.decision_outcomes_markdown_path.write_text(render_decision_outcomes(report.decision_outcomes), encoding="utf-8")
        self.signals_markdown_path.write_text(render_performance_signals(report.performance_signals), encoding="utf-8")
        self.lessons_markdown_path.write_text(render_process_lessons(report.process_lessons), encoding="utf-8")
        self.learning_loop_markdown_path.write_text(render_learning_loop(report.learning_loop), encoding="utf-8")

    def status(self) -> JsonMap:
        if not self.report_json_path.exists():
            return {
                "available": False,
                "report_path": str(self.report_markdown_path),
                "learning_loop_path": str(self.learning_loop_markdown_path),
            }
        data = self.load()
        return {
            "available": True,
            "snapshot_id": data.get("snapshot_id"),
            "decision_count": data.get("decision_count", 0),
            "reviewed_decision_count": data.get("reviewed_decision_count", 0),
            "open_decision_count": data.get("open_decision_count", 0),
            "due_review_count": data.get("due_review_count", 0),
            "overdue_review_count": data.get("overdue_review_count", 0),
            "outcome_count": data.get("outcome_count", 0),
            "pending_outcome_count": data.get("pending_outcome_count", 0),
            "lesson_count": data.get("lesson_count", 0),
            "performance_signal_count": data.get("performance_signal_count", 0),
            "high_severity_signal_count": data.get("high_severity_signal_count", 0),
            "report_path": str(self.report_markdown_path),
            "learning_loop_path": str(self.learning_loop_markdown_path),
        }

    def export(self) -> Path:
        report = self.load()
        obj = _report_from_data(report)
        self.report_markdown_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_markdown_path.write_text(render_performance_report(obj), encoding="utf-8")
        return self.report_markdown_path


def render_performance_report(report: PerformanceIntelligenceReport) -> str:
    snapshot = report.learning_loop
    return "\n".join(
        [
            "# Performance Intelligence",
            "",
            f"Report ID: `{report.report_id}`",
            f"Created: `{report.created_at}`",
            "",
            "## Executive Summary",
            "",
            f"- Decisions reviewed by the learning layer: {snapshot.decision_count}",
            f"- Outcomes recorded: {snapshot.outcome_count}",
            f"- Pending outcomes: {snapshot.pending_outcome_count}",
            f"- Process lessons: {snapshot.lesson_count}",
            f"- High-severity process signals: {snapshot.high_severity_signal_count}",
            "",
            "## Learning Loop Snapshot",
            "",
            *_summary_lines(snapshot.to_dict()),
            "## Decision Outcome Review",
            "",
            *_decision_lines(report.decision_outcomes),
            "## Reviews Due / Overdue",
            "",
            *_decision_lines([item for item in report.decision_outcomes if item.review_status in {"due", "overdue"}]),
            "## Performance Signals",
            "",
            *_signal_lines(report.performance_signals),
            "## Process Lessons",
            "",
            *_lesson_lines(report.process_lessons),
            "## Theme / Catalyst / Portfolio Follow-Ups",
            "",
            *_follow_up_lines(report.decision_outcomes),
            "## Missing Review Inputs",
            "",
            *_missing_input_lines(report.decision_outcomes),
            "## Recommended Process Improvements",
            "",
            *_string_lines(report.recommended_process_improvements),
            "## Limitations",
            "",
            *_string_lines(report.limitations),
            "## Provenance",
            "",
            *_summary_lines(report.provenance),
        ]
    )


def render_decision_outcomes(outcomes: list[DecisionOutcome]) -> str:
    return "\n".join(["# Decision Outcomes", "", *_decision_lines(outcomes)])


def render_performance_signals(signals: list[PerformanceSignal]) -> str:
    return "\n".join(["# Performance Signals", "", *_signal_lines(signals)])


def render_process_lessons(lessons: list[ProcessLesson]) -> str:
    return "\n".join(["# Process Lessons", "", *_lesson_lines(lessons)])


def render_learning_loop(snapshot: LearningLoopSnapshot) -> str:
    return "\n".join(["# Learning Loop Snapshot", "", *_summary_lines(snapshot.to_dict())])


def _performance_artifacts(root: Path) -> dict[str, JsonMap]:
    return {name: _read_optional_json(root / path) for name, path in PERFORMANCE_INPUTS.items()}


def _decision_entries(artifacts: dict[str, JsonMap]) -> list[JsonMap]:
    journal_entries = _map_list(_map(artifacts.get("decision_journal")).get("entries", []))
    entries_file = _map_list(_map(artifacts.get("decision_entries")).get("entries", []))
    entries = journal_entries or entries_file
    by_id = {str(item.get("entry_id")): item for item in entries if item.get("entry_id")}
    return [by_id[key] for key in sorted(by_id)]


def _decision_outcome(entry: JsonMap, artifacts: dict[str, JsonMap]) -> DecisionOutcome:
    entry_id = str(entry.get("entry_id", ""))
    review = _map(entry.get("review"))
    outcome = _map(entry.get("outcome"))
    review_status = str(review.get("review_status") or "no_review_date")
    raw_outcome = str(outcome.get("status") or "pending")
    lessons = str(entry.get("lessons") or "")
    outcome_status = _outcome_status(raw_outcome, review_status, str(entry.get("status", "")), lessons)
    lifecycle_links = _lifecycle_links(entry, artifacts)
    catalyst_links = _catalyst_links(entry, artifacts)
    portfolio_links = _portfolio_links(entry, artifacts)
    risk_links = _risk_links(entry, artifacts)
    observations = _system_observations(entry, outcome_status, lifecycle_links, catalyst_links, portfolio_links, risk_links)
    follow_up_needed, follow_up_reason = _follow_up(outcome_status, review_status, entry, lifecycle_links, catalyst_links, portfolio_links)
    return DecisionOutcome(
        outcome_id=f"decision_outcome_{_digest(entry_id + outcome_status)}",
        entry_id=entry_id,
        title=_short(str(entry.get("title") or entry_id)),
        decision_type=str(entry.get("decision_type") or "unknown"),
        entry_type=str(entry.get("entry_type") or "unknown"),
        status=str(entry.get("status") or "unknown"),
        outcome_status=outcome_status,
        review_status=review_status,
        created_at=str(entry.get("created_at") or ""),
        review_at=review.get("review_at") if isinstance(review.get("review_at"), str) else entry.get("review_at"),
        related_themes=_string_list(entry.get("related_themes", [])),
        related_entities=_string_list(entry.get("related_entities", [])),
        related_catalysts=_string_list(entry.get("related_catalysts", [])),
        related_risks=_string_list(entry.get("related_risks", [])),
        linked_lifecycle_changes=lifecycle_links,
        linked_catalyst_changes=catalyst_links,
        linked_portfolio_changes=portfolio_links,
        linked_risk_changes=risk_links,
        user_recorded_outcome=str(outcome.get("text") or ""),
        user_recorded_lessons=lessons,
        system_observations=observations,
        follow_up_needed=follow_up_needed,
        follow_up_reason=follow_up_reason,
        provenance={"source_path": entry.get("source_path"), "source_artifact": "outputs/ai-markets/decisions/decision-journal.json"},
    )


def _outcome_status(raw_outcome: str, review_status: str, status: str, lessons: str) -> str:
    if raw_outcome in {"user_confirmed", "user_challenged", "user_contradicted"}:
        return raw_outcome
    if lessons.strip() or raw_outcome == "lesson_recorded":
        return "lesson_recorded"
    if review_status == "overdue":
        return "review_overdue"
    if review_status == "due":
        return "review_due"
    if raw_outcome == "no_outcome_recorded" and status in {"reviewed", "archived"}:
        return "no_outcome_recorded"
    if status in {"open", "monitoring"}:
        return "pending"
    return raw_outcome if raw_outcome in OUTCOME_PRIORITY else "pending"


def _lifecycle_links(entry: JsonMap, artifacts: dict[str, JsonMap]) -> list[JsonMap]:
    themes = set(_string_list(entry.get("related_themes", [])))
    rows = []
    for theme in _map_list(_map(artifacts.get("theme_lifecycle")).get("themes", [])):
        name = str(theme.get("theme_name") or theme.get("name") or "")
        status = str(theme.get("current_status") or theme.get("status") or "")
        if name in themes or status in _string_list(entry.get("linked_theme_lifecycle_statuses", [])):
            rows.append({"theme": name, "status": status, "source_path": "outputs/ai-markets/theme-lifecycle.json"})
    for change in _map_list(_map(artifacts.get("theme_lifecycle")).get("transitions", [])) + _map_list(_map(artifacts.get("theme_transitions")).get("transitions", [])):
        name = str(change.get("theme_name") or change.get("theme") or "")
        if name in themes:
            rows.append({"theme": name, "status": str(change.get("current_status") or change.get("to_status") or ""), "transition": change, "source_path": "outputs/ai-markets/theme-transitions.json"})
    return _unique_maps(rows, "theme", "status")


def _catalyst_links(entry: JsonMap, artifacts: dict[str, JsonMap]) -> list[JsonMap]:
    catalysts = set(_string_list(entry.get("related_catalysts", [])))
    rows = []
    for item in _map_list(_map(artifacts.get("catalyst_monitor")).get("catalysts", [])):
        cid = str(item.get("catalyst_id") or "")
        category = str(item.get("category") or "")
        title = str(item.get("title") or category or cid)
        if cid in catalysts or category in catalysts or title in catalysts:
            rows.append({"catalyst_id": cid, "title": title, "priority": item.get("priority"), "source_path": "outputs/ai-markets/catalysts/catalyst-monitor.json"})
    for change in _map_list(_map(artifacts.get("catalyst_delta")).get("new_catalysts", [])) + _map_list(_map(artifacts.get("catalyst_transitions")).get("transitions", [])):
        cid = str(change.get("catalyst_id") or "")
        category = str(change.get("category") or "")
        if cid in catalysts or category in catalysts:
            rows.append({"catalyst_id": cid, "title": str(change.get("title") or category), "priority": change.get("priority"), "source_path": "outputs/ai-markets/catalysts/catalyst-delta.json"})
    return _unique_maps(rows, "catalyst_id", "title")


def _portfolio_links(entry: JsonMap, artifacts: dict[str, JsonMap]) -> list[JsonMap]:
    entities = set(_string_list(entry.get("related_entities", [])))
    themes = set(_string_list(entry.get("related_themes", [])))
    rows = []
    portfolio = _map(artifacts.get("portfolio_intelligence"))
    for item in _map_list(portfolio.get("positions", [])) + _map_list(portfolio.get("watchlist", [])) + _map_list(portfolio.get("detected_entities", [])):
        symbol = str(item.get("symbol") or "")
        if symbol in entities:
            rows.append({"symbol": symbol, "research_priority": item.get("research_priority"), "source_path": "outputs/ai-markets/portfolio/portfolio-intelligence.json"})
    for exposure in _map_list(portfolio.get("exposures", [])):
        theme = str(exposure.get("theme_name") or "")
        if theme in themes:
            rows.append({"theme": theme, "research_priority": exposure.get("research_priority"), "source_path": "outputs/ai-markets/portfolio/portfolio-intelligence.json"})
    return _unique_maps(rows, "symbol", "theme")


def _risk_links(entry: JsonMap, artifacts: dict[str, JsonMap]) -> list[JsonMap]:
    risks = set(_string_list(entry.get("related_risks", [])))
    rows = []
    for risk in _map_list(_map(artifacts.get("ai_markets")).get("risks", [])) + _map_list(_map(artifacts.get("portfolio_risks")).get("risks", [])):
        rid = str(risk.get("risk_id") or "")
        description = str(risk.get("description") or "")
        if rid in risks or any(value and value.lower() in description.lower() for value in risks):
            rows.append({"risk_id": rid, "description": _short(description), "source_path": "outputs/ai-markets/ai-markets.json"})
    return _unique_maps(rows, "risk_id", "description")


def _system_observations(entry: JsonMap, outcome_status: str, lifecycle_links: list[JsonMap], catalyst_links: list[JsonMap], portfolio_links: list[JsonMap], risk_links: list[JsonMap]) -> list[str]:
    observations = []
    if outcome_status in {"review_due", "review_overdue"}:
        observations.append("Decision needs outcome review.")
    if lifecycle_links:
        observations.append("Decision links to theme lifecycle records.")
    if catalyst_links:
        observations.append("Decision links to catalyst records.")
    if portfolio_links:
        observations.append("Decision links to portfolio or watchlist review records.")
    if risk_links:
        observations.append("Decision links to risk records.")
    if not str(entry.get("rationale") or "").strip():
        observations.append("Decision entry is missing rationale.")
    if not str(entry.get("uncertainties") or "").strip():
        observations.append("Decision entry is missing uncertainty notes.")
    return observations or ["No deterministic follow-up signal found."]


def _follow_up(outcome_status: str, review_status: str, entry: JsonMap, lifecycle_links: list[JsonMap], catalyst_links: list[JsonMap], portfolio_links: list[JsonMap]) -> tuple[bool, str]:
    if outcome_status in {"review_due", "review_overdue", "user_challenged", "user_contradicted"}:
        return True, f"Decision outcome status is {outcome_status}."
    if not str(entry.get("review_at") or "").strip():
        return True, "Decision entry has no review date."
    if any(str(item.get("status")) in {"weakening", "contradicted"} for item in lifecycle_links):
        return True, "Linked theme lifecycle status requires review."
    if any(str(item.get("priority")) == "high" for item in catalyst_links + portfolio_links):
        return True, "Linked catalyst or review priority is high."
    return False, "No immediate follow-up required."


def _performance_signals(outcomes: list[DecisionOutcome], artifacts: dict[str, JsonMap]) -> list[PerformanceSignal]:
    signals = []
    for outcome in outcomes:
        if outcome.outcome_status == "review_overdue":
            signals.append(_signal("decision_overdue", "Overdue decision review", outcome.follow_up_reason, [outcome], "high"))
        elif outcome.outcome_status == "review_due":
            signals.append(_signal("decision_due", "Decision review due", outcome.follow_up_reason, [outcome], "medium"))
        if outcome.outcome_status == "no_outcome_recorded":
            signals.append(_signal("decision_without_outcome", "Reviewed decision without outcome", "Reviewed or archived decision lacks an outcome record.", [outcome], "medium"))
        if not outcome.review_at:
            signals.append(_signal("missing_review_date", "Missing review date", "Decision entry should include a review date for future review discipline.", [outcome], "medium"))
        source_entry = _entry_by_id(artifacts, outcome.entry_id)
        if source_entry and not str(source_entry.get("rationale") or "").strip():
            signals.append(_signal("missing_rationale", "Missing rationale", "Decision entry should include rationale.", [outcome], "medium"))
        if source_entry and not str(source_entry.get("uncertainties") or "").strip():
            signals.append(_signal("missing_uncertainty", "Missing uncertainty notes", "Decision entry should include uncertainty notes.", [outcome], "medium"))
        if source_entry and not str(source_entry.get("follow_up") or "").strip():
            signals.append(_signal("missing_follow_up", "Missing follow-up notes", "Decision entry should include follow-up notes.", [outcome], "medium"))
        if outcome.outcome_status in {"user_challenged", "user_contradicted"}:
            signals.append(_signal("risk_follow_up_needed", "Outcome needs process review", "User-recorded outcome should be reviewed for process lessons.", [outcome], "high"))
        if outcome.user_recorded_lessons.strip():
            signals.append(_signal("lesson_available", "User-recorded lesson available", "Decision entry includes a user-recorded lesson.", [outcome], "low"))
        if any(str(item.get("status")) in {"weakening", "contradicted"} for item in outcome.linked_lifecycle_changes):
            signals.append(_signal("repeated_theme_review", "Linked theme needs review", "Decision links to weakening or contradicted theme status.", [outcome], "high"))
        if any(str(item.get("priority")) == "high" for item in outcome.linked_catalyst_changes):
            signals.append(_signal("catalyst_follow_up_needed", "High-priority catalyst follow-up", "Decision links to a high-priority catalyst.", [outcome], "medium"))
    reviewed_without_outcome = [item for item in outcomes if item.outcome_status == "no_outcome_recorded"]
    if len(reviewed_without_outcome) >= 3:
        signals.append(_signal("decision_without_outcome", "Repeated missing outcomes", "Three or more reviewed decisions are missing outcome records.", reviewed_without_outcome, "high"))
    overdue = [item for item in outcomes if item.outcome_status == "review_overdue"]
    if len(overdue) >= 3:
        signals.append(_signal("decision_overdue", "Repeated overdue reviews", "Three or more decisions are overdue for review.", overdue, "high"))
    return _unique_signals(signals)


def _signal(signal_type: str, title: str, description: str, outcomes: list[DecisionOutcome], severity: str) -> PerformanceSignal:
    related_ids = sorted({item.entry_id for item in outcomes})
    seed = "|".join([signal_type, title, ",".join(related_ids)])
    return PerformanceSignal(
        signal_id=f"performance_signal_{_digest(seed)}",
        signal_type=signal_type,
        title=title,
        description=description,
        related_decision_ids=related_ids,
        related_themes=sorted({theme for item in outcomes for theme in item.related_themes}),
        related_entities=sorted({entity for item in outcomes for entity in item.related_entities}),
        related_catalysts=sorted({catalyst for item in outcomes for catalyst in item.related_catalysts}),
        severity=severity,
        evidence_count=len(outcomes),
        source_paths=sorted({str(item.provenance.get("source_artifact")) for item in outcomes}),
        provenance={"rule": signal_type},
    )


def _process_lessons(outcomes: list[DecisionOutcome], signals: list[PerformanceSignal]) -> list[ProcessLesson]:
    lessons = []
    for outcome in outcomes:
        if outcome.user_recorded_lessons.strip():
            lessons.append(_lesson("user_recorded", f"User lesson: {outcome.title}", _short(outcome.user_recorded_lessons), [outcome], [outcome.user_recorded_lessons]))
    missing_outcome = [item for item in outcomes if item.outcome_status == "no_outcome_recorded"]
    if len(missing_outcome) >= 3:
        lessons.append(_lesson("outcome_tracking", "Record outcomes for reviewed decisions", "Repeated reviewed decisions lack outcome records.", missing_outcome, [item.entry_id for item in missing_outcome]))
    overdue = [item for item in outcomes if item.outcome_status == "review_overdue"]
    if len(overdue) >= 3:
        lessons.append(_lesson("review_discipline", "Improve review discipline", "Repeated overdue reviews indicate a process gap.", overdue, [item.entry_id for item in overdue]))
    missing_rationale = [signal for signal in signals if signal.signal_type == "missing_rationale"]
    if len(missing_rationale) >= 3:
        ids = sorted({decision_id for signal in missing_rationale for decision_id in signal.related_decision_ids})
        related = [item for item in outcomes if item.entry_id in ids]
        lessons.append(_lesson("process_gap", "Add rationale to future decisions", "Repeated decisions are missing rationale.", related, ids))
    return _unique_lessons(lessons)


def _lesson(lesson_type: str, title: str, description: str, outcomes: list[DecisionOutcome], evidence: list[str]) -> ProcessLesson:
    seed = "|".join([lesson_type, title, ",".join(sorted(item.entry_id for item in outcomes))])
    return ProcessLesson(
        lesson_id=f"process_lesson_{_digest(seed)}",
        lesson_type=lesson_type,
        title=title,
        description=description,
        related_decision_ids=sorted({item.entry_id for item in outcomes}),
        related_themes=sorted({theme for item in outcomes for theme in item.related_themes}),
        related_entities=sorted({entity for item in outcomes for entity in item.related_entities}),
        evidence=sorted(set(evidence)),
        created_at=_now_iso(),
        provenance={"rule": lesson_type},
    )


def _learning_loop_snapshot(outcomes: list[DecisionOutcome], signals: list[PerformanceSignal], lessons: list[ProcessLesson], available: list[str], missing: list[str]) -> LearningLoopSnapshot:
    payload = "|".join(
        [
            ",".join(item.outcome_id + item.outcome_status for item in outcomes),
            ",".join(item.signal_id for item in signals),
            ",".join(item.lesson_id for item in lessons),
            ",".join(available),
            ",".join(missing),
        ]
    )
    return LearningLoopSnapshot(
        snapshot_id=f"learning_loop_{_digest(payload)}",
        created_at=_now_iso(),
        available=True,
        decision_count=len(outcomes),
        reviewed_decision_count=sum(1 for item in outcomes if item.review_status == "reviewed"),
        open_decision_count=sum(1 for item in outcomes if item.status == "open"),
        due_review_count=sum(1 for item in outcomes if item.outcome_status == "review_due"),
        overdue_review_count=sum(1 for item in outcomes if item.outcome_status == "review_overdue"),
        outcome_count=sum(1 for item in outcomes if item.outcome_status in {"user_confirmed", "user_challenged", "user_contradicted", "lesson_recorded"}),
        pending_outcome_count=sum(1 for item in outcomes if item.outcome_status in {"pending", "review_due", "review_overdue", "no_outcome_recorded"}),
        lesson_count=len(lessons),
        performance_signal_count=len(signals),
        high_severity_signal_count=sum(1 for item in signals if item.severity == "high"),
        linked_theme_count=len({theme for item in outcomes for theme in item.related_themes}),
        linked_entity_count=len({entity for item in outcomes for entity in item.related_entities}),
        linked_catalyst_count=len({catalyst for item in outcomes for catalyst in item.related_catalysts}),
        linked_risk_count=len({risk for item in outcomes for risk in item.related_risks}),
        source_artifacts_available=available,
        source_artifacts_missing=missing,
        provenance={"source_artifacts": sorted(PERFORMANCE_INPUTS)},
    )


def _performance_delta(previous: JsonMap, outcomes: list[DecisionOutcome], signals: list[PerformanceSignal], lessons: list[ProcessLesson], snapshot: LearningLoopSnapshot) -> PerformanceDelta:
    prev_outcomes = {str(item.get("outcome_id")): item for item in _map_list(previous.get("decision_outcomes", []))}
    current_outcomes = {item.outcome_id: item for item in outcomes}
    changes = [
        {"outcome_id": key, "previous_value": prev_outcomes[key].get("outcome_status"), "current_value": item.outcome_status}
        for key, item in current_outcomes.items()
        if key in prev_outcomes and prev_outcomes[key].get("outcome_status") != item.outcome_status
    ]
    prev_signals = {str(item.get("signal_id")) for item in _map_list(previous.get("performance_signals", []))}
    current_signals = {item.signal_id for item in signals}
    prev_lessons = {str(item.get("lesson_id")) for item in _map_list(previous.get("process_lessons", []))}
    current_lessons = {item.lesson_id for item in lessons}
    prev_available = set(_string_list(previous.get("source_artifacts_available", [])))
    return PerformanceDelta(
        new_decision_outcomes=sorted(set(current_outcomes) - set(prev_outcomes)),
        removed_decision_outcomes=sorted(set(prev_outcomes) - set(current_outcomes)),
        outcome_status_changes=sorted(changes, key=lambda item: str(item.get("outcome_id"))),
        new_performance_signals=sorted(current_signals - prev_signals),
        removed_performance_signals=sorted(prev_signals - current_signals),
        new_process_lessons=sorted(current_lessons - prev_lessons),
        review_count_changes={
            "decision_count_change": snapshot.decision_count - _int(previous.get("decision_count")),
            "due_review_count_change": snapshot.due_review_count - _int(previous.get("due_review_count")),
            "overdue_review_count_change": snapshot.overdue_review_count - _int(previous.get("overdue_review_count")),
            "outcome_count_change": snapshot.outcome_count - _int(previous.get("outcome_count")),
        },
        source_artifact_availability_changes=sorted(set(snapshot.source_artifacts_available).symmetric_difference(prev_available)),
    )


def _process_improvements(outcomes: list[DecisionOutcome], signals: list[PerformanceSignal]) -> list[str]:
    improvements = []
    if any(item.signal_type == "missing_review_date" for item in signals):
        improvements.append("Add a review date to open decisions without one.")
    if any(item.signal_type == "decision_without_outcome" for item in signals):
        improvements.append("Record an outcome for reviewed decisions.")
    if any(item.signal_type == "missing_uncertainty" for item in signals):
        improvements.append("Add uncertainty notes to future decision entries.")
    if any(item.signal_type == "decision_overdue" for item in signals):
        improvements.append("Follow up on overdue reviews.")
    if any(not item.related_themes and not item.related_catalysts for item in outcomes):
        improvements.append("Link future decisions to explicit themes and catalysts.")
    return improvements or ["Continue recording decision rationale, uncertainty, review timing, and outcome notes."]


def _review_summary(snapshot: LearningLoopSnapshot) -> str:
    if snapshot.decision_count == 0:
        return "No decision records are available for Performance Intelligence review."
    return f"{snapshot.decision_count} decisions reviewed by the learning layer, with {snapshot.outcome_count} recorded outcomes and {snapshot.performance_signal_count} process signals."


def _read_optional_json(path: Path) -> JsonMap:
    if not path.exists():
        return {}
    try:
        return read_json(path)
    except Exception:
        return {}


def _entry_by_id(artifacts: dict[str, JsonMap], entry_id: str) -> JsonMap:
    for entry in _decision_entries(artifacts):
        if entry.get("entry_id") == entry_id:
            return entry
    return {}


def _report_from_data(data: JsonMap) -> PerformanceIntelligenceReport:
    return PerformanceIntelligenceReport(
        report_id=str(data.get("report_id")),
        created_at=str(data.get("created_at")),
        version=str(data.get("version")),
        review=PerformanceReview(**_map(data.get("review"))),
        learning_loop=LearningLoopSnapshot(**_map(data.get("learning_loop"))),
        decision_outcomes=[DecisionOutcome(**item) for item in _map_list(data.get("decision_outcomes", []))],
        performance_signals=[PerformanceSignal(**item) for item in _map_list(data.get("performance_signals", []))],
        process_lessons=[ProcessLesson(**item) for item in _map_list(data.get("process_lessons", []))],
        delta=PerformanceDelta(**_map(data.get("delta"))),
        recommended_process_improvements=_string_list(data.get("recommended_process_improvements", [])),
        limitations=_string_list(data.get("limitations", [])),
        provenance=_map(data.get("provenance")),
    )


def _decision_outcome_sort_key(item: DecisionOutcome) -> tuple[Any, ...]:
    review_at = item.review_at or "9999-12-31"
    return (OUTCOME_PRIORITY.get(item.outcome_status, 99), review_at, _reverse_text(item.created_at), item.title, item.outcome_id)


def _signal_sort_key(item: PerformanceSignal) -> tuple[Any, ...]:
    return (SEVERITY_PRIORITY.get(item.severity, 99), item.signal_type, -len(item.related_decision_ids), item.title, item.signal_id)


def _lesson_sort_key(item: ProcessLesson) -> tuple[Any, ...]:
    return (item.lesson_type, _reverse_text(item.created_at), item.title, item.lesson_id)


def _reverse_text(value: str) -> str:
    return "".join(chr(0x10FFFF - ord(ch)) for ch in value)


def _unique_maps(items: list[JsonMap], *keys: str) -> list[JsonMap]:
    seen = {}
    for item in items:
        seed = "|".join(str(item.get(key, "")) for key in keys)
        seen[seed] = item
    return [seen[key] for key in sorted(seen)]


def _unique_signals(items: list[PerformanceSignal]) -> list[PerformanceSignal]:
    by_id = {item.signal_id: item for item in items}
    return [by_id[key] for key in sorted(by_id)]


def _unique_lessons(items: list[ProcessLesson]) -> list[ProcessLesson]:
    by_id = {item.lesson_id: item for item in items}
    return [by_id[key] for key in sorted(by_id)]


def _summary_lines(data: JsonMap) -> list[str]:
    return [f"- {key}: {value}" for key, value in data.items() if key not in {"provenance"}]


def _decision_lines(outcomes: list[DecisionOutcome]) -> list[str]:
    if not outcomes:
        return ["- No decision outcomes available.", ""]
    lines = []
    for item in outcomes:
        lines.append(f"- `{item.outcome_status}` {item.title} ({item.entry_id})")
        if item.follow_up_needed:
            lines.append(f"  - Follow-up: {item.follow_up_reason}")
    lines.append("")
    return lines


def _signal_lines(signals: list[PerformanceSignal]) -> list[str]:
    if not signals:
        return ["- No performance signals available.", ""]
    return [f"- `{item.severity}` {item.signal_type}: {item.title} ({len(item.related_decision_ids)} decisions)" for item in signals] + [""]


def _lesson_lines(lessons: list[ProcessLesson]) -> list[str]:
    if not lessons:
        return ["- No process lessons available.", ""]
    return [f"- `{item.lesson_type}` {item.title}: {item.description}" for item in lessons] + [""]


def _follow_up_lines(outcomes: list[DecisionOutcome]) -> list[str]:
    lines = []
    for item in outcomes:
        if item.linked_lifecycle_changes or item.linked_catalyst_changes or item.linked_portfolio_changes:
            lines.append(f"- {item.title}: lifecycle={len(item.linked_lifecycle_changes)}, catalysts={len(item.linked_catalyst_changes)}, portfolio={len(item.linked_portfolio_changes)}")
    return lines + [""] if lines else ["- No deterministic theme, catalyst, or portfolio follow-ups available.", ""]


def _missing_input_lines(outcomes: list[DecisionOutcome]) -> list[str]:
    lines = []
    for item in outcomes:
        if not item.review_at:
            lines.append(f"- {item.title}: missing review date.")
        if "Decision entry is missing rationale." in item.system_observations:
            lines.append(f"- {item.title}: missing rationale.")
        if "Decision entry is missing uncertainty notes." in item.system_observations:
            lines.append(f"- {item.title}: missing uncertainty notes.")
    return lines + [""] if lines else ["- No missing review inputs detected.", ""]


def _string_lines(values: list[str]) -> list[str]:
    return [f"- {value}" for value in values] + [""]


def _short(value: str, limit: int = 180) -> str:
    text = " ".join(value.split())
    return text if len(text) <= limit else text[:limit].rstrip()


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:16]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")


def _map(value: Any) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _map_list(value: Any) -> list[JsonMap]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item) for item in value if item not in (None, "")]
    if value in (None, ""):
        return []
    return [str(value)]


def _int(value: Any) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0
