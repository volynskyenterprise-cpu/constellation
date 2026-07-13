from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
from typing import Any

from . import __version__
from .io import read_json, write_json
from .models import JsonMap


class ThesisAccuracyError(RuntimeError):
    pass


THESIS_ACCURACY_INPUTS = {
    "thesis_intelligence": Path("outputs/thesis/theses.json"),
    "theme_lifecycle": Path("outputs/ai-markets/theme-lifecycle.json"),
    "decision_journal": Path("outputs/ai-markets/decisions/decision-journal.json"),
    "decision_outcomes": Path("outputs/performance/decision-outcomes.json"),
    "performance_intelligence": Path("outputs/performance/performance-intelligence.json"),
    "catalyst_monitor": Path("outputs/ai-markets/catalysts/catalyst-monitor.json"),
    "ai_markets": Path("outputs/ai-markets/ai-markets.json"),
    "executive_brief": Path("outputs/ai-markets/briefings/morning-brief.json"),
    "evidence_graph": Path("outputs/evidence-graph/evidence-graph.json"),
    "institutional_memory": Path("outputs/memory/latest-snapshot.json"),
    "knowledge_evolution": Path("outputs/evolution/evolution.json"),
}


@dataclass(frozen=True)
class ThesisAccuracyScore:
    thesis_id: str
    title: str
    category: str
    confidence: str
    evidence_count: int
    decision_count: int
    confirmed_count: int
    challenged_count: int
    contradicted_count: int
    unresolved_count: int
    catalyst_count: int
    related_themes: list[str]
    related_entities: list[str]
    accuracy_score: int
    quality_score: int
    process_score: int
    review_priority: str
    rationale: list[str]
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ThesisOutcomeSummary:
    thesis_count: int
    average_accuracy_score: int
    average_quality_score: int
    average_process_score: int
    needs_review_count: int
    highest_accuracy_theses: list[JsonMap]
    lowest_accuracy_theses: list[JsonMap]
    most_improved_theses: list[JsonMap]
    most_degraded_theses: list[JsonMap]
    process_weaknesses: list[str]

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ThesisAccuracyDelta:
    prior_snapshot_id: str | None
    current_snapshot_id: str
    new_thesis_ids: list[str]
    removed_thesis_ids: list[str]
    accuracy_score_changes: list[JsonMap]
    quality_score_changes: list[JsonMap]
    process_score_changes: list[JsonMap]
    review_priority_changes: list[JsonMap]
    average_accuracy_score_change: int
    summary: str

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class ThesisAccuracySnapshot:
    snapshot_id: str
    created_at: str
    version: str
    scores: list[ThesisAccuracyScore]
    summary: ThesisOutcomeSummary
    provenance: JsonMap
    limitations: list[str]

    def to_dict(self) -> JsonMap:
        return {
            "snapshot_id": self.snapshot_id,
            "created_at": self.created_at,
            "version": self.version,
            "scores": [score.to_dict() for score in self.scores],
            "summary": self.summary.to_dict(),
            "provenance": self.provenance,
            "limitations": self.limitations,
            **self.summary.to_dict(),
        }


@dataclass(frozen=True)
class ThesisAccuracyReport:
    report_id: str
    created_at: str
    version: str
    snapshot: ThesisAccuracySnapshot
    delta: ThesisAccuracyDelta
    recommendations_for_research_process: list[str]
    limitations: list[str]
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return {
            "report_id": self.report_id,
            "created_at": self.created_at,
            "version": self.version,
            "snapshot": self.snapshot.to_dict(),
            "delta": self.delta.to_dict(),
            "scores": [score.to_dict() for score in self.snapshot.scores],
            "summary": self.snapshot.summary.to_dict(),
            "recommendations_for_research_process": self.recommendations_for_research_process,
            "limitations": self.limitations,
            "provenance": self.provenance,
            **self.snapshot.summary.to_dict(),
        }


class ThesisAccuracyEngine:
    def __init__(self, root: Path) -> None:
        self.root = root

    def build(self, history: list[JsonMap]) -> ThesisAccuracyReport:
        artifacts = _artifacts(self.root)
        theses = _map_list(_map(artifacts.get("thesis_intelligence")).get("theses", []))
        decisions = _decision_outcomes(artifacts)
        signals = _map_list(_map(artifacts.get("performance_intelligence")).get("performance_signals", []))
        catalysts = _map_list(_map(artifacts.get("catalyst_monitor")).get("catalysts", []))
        scores = sorted(
            (_score_thesis(thesis, decisions, signals, catalysts, artifacts) for thesis in theses),
            key=lambda item: ({"high": 0, "medium": 1, "low": 2}.get(item.review_priority, 3), item.thesis_id),
        )
        previous = history[-1] if history else {}
        delta = _delta(previous, scores)
        summary = _summary(scores, delta)
        snapshot_seed = _scores_seed(scores)
        now = _now_iso()
        snapshot = ThesisAccuracySnapshot(
            snapshot_id=f"thesis_accuracy_{_digest(snapshot_seed)}",
            created_at=now,
            version=__version__,
            scores=scores,
            summary=summary,
            provenance={"consumed_artifacts": {name: str(path) for name, path in THESIS_ACCURACY_INPUTS.items()}},
            limitations=_limitations(),
        )
        recommendations = _process_recommendations(scores)
        report = ThesisAccuracyReport(
            report_id=f"thesis_accuracy_report_{_digest(snapshot.snapshot_id + delta.summary)}",
            created_at=now,
            version=__version__,
            snapshot=snapshot,
            delta=delta,
            recommendations_for_research_process=recommendations,
            limitations=_limitations(),
            provenance=snapshot.provenance,
        )
        return report


class ThesisAccuracyStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "outputs" / "performance"
        self.json_path = self.directory / "thesis-accuracy.json"
        self.markdown_path = self.directory / "thesis-accuracy.md"
        self.scoreboard_path = self.directory / "thesis-scoreboard.md"
        self.history_path = self.directory / "thesis-history.json"
        self.delta_path = self.directory / "thesis-delta.json"

    def build(self) -> ThesisAccuracyReport:
        report = ThesisAccuracyEngine(self.root).build(self.history())
        self.save(report)
        return report

    def load(self) -> JsonMap:
        if not self.json_path.exists():
            raise ThesisAccuracyError("No Thesis Accuracy report found. Run `python -m constellation performance thesis` first.")
        return read_json(self.json_path)

    def history(self) -> list[JsonMap]:
        if not self.history_path.exists():
            return []
        return _map_list(read_json(self.history_path).get("snapshots", []))

    def save(self, report: ThesisAccuracyReport) -> None:
        data = report.to_dict()
        write_json(self.json_path, data)
        write_json(self.delta_path, report.delta.to_dict())
        history = self.history()
        snapshot = report.snapshot.to_dict()
        if not history or history[-1].get("snapshot_id") != snapshot["snapshot_id"]:
            history.append(snapshot)
        write_json(self.history_path, {"snapshots": history})
        self.markdown_path.parent.mkdir(parents=True, exist_ok=True)
        self.markdown_path.write_text(render_thesis_accuracy_report(report), encoding="utf-8")
        self.scoreboard_path.write_text(render_thesis_scoreboard(report.snapshot.scores), encoding="utf-8")

    def status(self) -> JsonMap:
        if not self.json_path.exists():
            return {
                "thesis_accuracy_available": False,
                "thesis_accuracy_report_path": str(self.markdown_path),
                "thesis_scoreboard_path": str(self.scoreboard_path),
            }
        data = self.load()
        summary = _map(data.get("summary"))
        return {
            "thesis_accuracy_available": True,
            "snapshot_id": _map(data.get("snapshot")).get("snapshot_id"),
            "thesis_count": summary.get("thesis_count", 0),
            "average_accuracy_score": summary.get("average_accuracy_score", 0),
            "average_quality_score": summary.get("average_quality_score", 0),
            "average_process_score": summary.get("average_process_score", 0),
            "needs_review_count": summary.get("needs_review_count", 0),
            "highest_accuracy_theses": summary.get("highest_accuracy_theses", []),
            "lowest_accuracy_theses": summary.get("lowest_accuracy_theses", []),
            "thesis_accuracy_report_path": str(self.markdown_path),
            "thesis_scoreboard_path": str(self.scoreboard_path),
        }

    def export(self) -> Path:
        data = self.load()
        report = _report_from_data(data)
        self.markdown_path.parent.mkdir(parents=True, exist_ok=True)
        self.markdown_path.write_text(render_thesis_accuracy_report(report), encoding="utf-8")
        self.scoreboard_path.write_text(render_thesis_scoreboard(report.snapshot.scores), encoding="utf-8")
        return self.markdown_path


def render_thesis_accuracy_report(report: ThesisAccuracyReport) -> str:
    scores = report.snapshot.scores
    summary = report.snapshot.summary
    needs_review = [score for score in scores if score.review_priority == "high"]
    return "\n".join(
        [
            "# Thesis Accuracy",
            "",
            f"Report ID: `{report.report_id}`",
            f"Created: `{report.created_at}`",
            "",
            "## Executive Summary",
            "",
            *_summary_lines(summary.to_dict()),
            "## Highest Accuracy Theses",
            "",
            *_score_lines(_top(scores, "accuracy_score")),
            "## Lowest Accuracy Theses",
            "",
            *_score_lines(_bottom(scores, "accuracy_score")),
            "## Most Improved",
            "",
            *_change_lines(summary.most_improved_theses),
            "## Most Degraded",
            "",
            *_change_lines(summary.most_degraded_theses),
            "## Needs Review",
            "",
            *_score_lines(needs_review),
            "## Process Weaknesses",
            "",
            *_string_lines(summary.process_weaknesses),
            "## Evidence Summary",
            "",
            f"- Total evidence references: {sum(score.evidence_count for score in scores)}",
            f"- Total contradictory references: {sum(score.contradicted_count for score in scores)}",
            f"- Total unresolved decisions: {sum(score.unresolved_count for score in scores)}",
            "",
            "## Recommendations for Research Process",
            "",
            *_string_lines(report.recommendations_for_research_process),
            "## Limitations",
            "",
            *_string_lines(report.limitations),
            "## Provenance",
            "",
            *_summary_lines(report.provenance),
        ]
    )


def render_thesis_scoreboard(scores: list[ThesisAccuracyScore]) -> str:
    lines = [
        "# Thesis Accuracy Scoreboard",
        "",
        "| Thesis | Accuracy | Quality | Process | Review Priority | Evidence | Decisions |",
        "| --- | ---: | ---: | ---: | --- | ---: | ---: |",
    ]
    for score in sorted(scores, key=lambda item: (-item.accuracy_score, item.thesis_id)):
        lines.append(
            f"| {score.title} | {score.accuracy_score} | {score.quality_score} | {score.process_score} | {score.review_priority} | {score.evidence_count} | {score.decision_count} |"
        )
    if not scores:
        lines.append("| None | 0 | 0 | 0 | low | 0 | 0 |")
    return "\n".join(lines)


def _score_thesis(thesis: JsonMap, decisions: list[JsonMap], signals: list[JsonMap], catalysts: list[JsonMap], artifacts: dict[str, JsonMap]) -> ThesisAccuracyScore:
    thesis_id = str(thesis.get("thesis_id", ""))
    title = str(thesis.get("title") or thesis_id)
    category = str(thesis.get("category") or thesis.get("thesis_type") or "uncategorized")
    confidence = str(_map(thesis.get("confidence")).get("label") or thesis.get("confidence") or "unknown")
    supporting_ids = _string_list(thesis.get("supporting_evidence_ids", []))
    conflicting_ids = _string_list(thesis.get("conflicting_evidence_ids", []))
    evidence_count = len(set(supporting_ids + conflicting_ids))
    related_themes = _related_themes(thesis, artifacts)
    related_entities = _related_entities(thesis, artifacts)
    linked_decisions = [decision for decision in decisions if _links_to_thesis(decision, thesis_id, title, related_themes, related_entities)]
    linked_decision_ids = [str(decision.get("entry_id") or decision.get("outcome_id")) for decision in linked_decisions]
    confirmed = _count_status(linked_decisions, "user_confirmed")
    challenged = _count_status(linked_decisions, "user_challenged")
    contradicted = _count_status(linked_decisions, "user_contradicted") + len(conflicting_ids)
    unresolved = sum(1 for decision in linked_decisions if str(decision.get("outcome_status")) in {"pending", "review_due", "review_overdue", "no_outcome_recorded"})
    source_count = len(set(_string_list(thesis.get("source_ids", []))))
    catalyst_count = len(_linked_catalysts(linked_decisions, catalysts, related_themes, related_entities))
    linked_signals = [signal for signal in signals if set(_string_list(signal.get("related_decision_ids", []))) & set(linked_decision_ids)]
    gap_penalty = sum(1 for signal in linked_signals if signal.get("signal_type") in {"missing_rationale", "missing_uncertainty", "missing_follow_up", "missing_review_date"})
    accuracy_score = _clamp(50 + confirmed * 10 + len(supporting_ids) * 3 + source_count * 2 - challenged * 12 - contradicted * 18 - unresolved * 4)
    process_score = _clamp(70 + confirmed * 5 - gap_penalty * 6 - unresolved * 5 - challenged * 5 - contradicted * 8)
    evidence_component = _clamp(40 + len(supporting_ids) * 5 + source_count * 5 - len(conflicting_ids) * 12)
    quality_score = _clamp(round((accuracy_score + process_score + evidence_component) / 3))
    review_priority = _review_priority(accuracy_score, process_score, challenged, contradicted, unresolved)
    return ThesisAccuracyScore(
        thesis_id=thesis_id,
        title=title,
        category=category,
        confidence=confidence,
        evidence_count=evidence_count,
        decision_count=len(linked_decisions),
        confirmed_count=confirmed,
        challenged_count=challenged,
        contradicted_count=contradicted,
        unresolved_count=unresolved,
        catalyst_count=catalyst_count,
        related_themes=related_themes,
        related_entities=related_entities,
        accuracy_score=accuracy_score,
        quality_score=quality_score,
        process_score=process_score,
        review_priority=review_priority,
        rationale=_rationale(confirmed, challenged, contradicted, unresolved, evidence_count, source_count, gap_penalty),
        provenance={
            "thesis_id": thesis_id,
            "supporting_evidence_ids": supporting_ids,
            "conflicting_evidence_ids": conflicting_ids,
            "linked_decision_ids": linked_decision_ids,
            "formula": "deterministic_counts_only",
        },
    )


def _summary(scores: list[ThesisAccuracyScore], delta: ThesisAccuracyDelta) -> ThesisOutcomeSummary:
    return ThesisOutcomeSummary(
        thesis_count=len(scores),
        average_accuracy_score=_average([score.accuracy_score for score in scores]),
        average_quality_score=_average([score.quality_score for score in scores]),
        average_process_score=_average([score.process_score for score in scores]),
        needs_review_count=sum(1 for score in scores if score.review_priority == "high"),
        highest_accuracy_theses=[_score_ref(score) for score in _top(scores, "accuracy_score")],
        lowest_accuracy_theses=[_score_ref(score) for score in _bottom(scores, "accuracy_score")],
        most_improved_theses=[item for item in delta.accuracy_score_changes if _int(item.get("change")) > 0][:5],
        most_degraded_theses=sorted([item for item in delta.accuracy_score_changes if _int(item.get("change")) < 0], key=lambda item: _int(item.get("change")))[:5],
        process_weaknesses=_process_weaknesses(scores),
    )


def _delta(previous: JsonMap, scores: list[ThesisAccuracyScore]) -> ThesisAccuracyDelta:
    previous_scores = {str(item.get("thesis_id")): item for item in _map_list(previous.get("scores", []))}
    current_scores = {score.thesis_id: score for score in scores}
    changes: list[JsonMap] = []
    quality_changes: list[JsonMap] = []
    process_changes: list[JsonMap] = []
    priority_changes: list[JsonMap] = []
    for thesis_id in sorted(set(previous_scores) & set(current_scores)):
        old = previous_scores[thesis_id]
        current = current_scores[thesis_id]
        accuracy_change = current.accuracy_score - _int(old.get("accuracy_score"))
        quality_change = current.quality_score - _int(old.get("quality_score"))
        process_change = current.process_score - _int(old.get("process_score"))
        if accuracy_change:
            changes.append({"thesis_id": thesis_id, "title": current.title, "change": accuracy_change, "from": old.get("accuracy_score"), "to": current.accuracy_score})
        if quality_change:
            quality_changes.append({"thesis_id": thesis_id, "title": current.title, "change": quality_change, "from": old.get("quality_score"), "to": current.quality_score})
        if process_change:
            process_changes.append({"thesis_id": thesis_id, "title": current.title, "change": process_change, "from": old.get("process_score"), "to": current.process_score})
        if old.get("review_priority") != current.review_priority:
            priority_changes.append({"thesis_id": thesis_id, "title": current.title, "from": old.get("review_priority"), "to": current.review_priority})
    current_avg = _average([score.accuracy_score for score in scores])
    previous_avg = _int(_map(previous.get("summary")).get("average_accuracy_score"))
    new_ids = sorted(set(current_scores) - set(previous_scores))
    removed_ids = sorted(set(previous_scores) - set(current_scores))
    summary = f"Thesis accuracy average changed {current_avg - previous_avg:+}; new theses {len(new_ids)}, removed theses {len(removed_ids)}."
    return ThesisAccuracyDelta(
        prior_snapshot_id=str(previous.get("snapshot_id")) if previous else None,
        current_snapshot_id=f"thesis_accuracy_{_digest(_scores_seed(scores))}",
        new_thesis_ids=new_ids,
        removed_thesis_ids=removed_ids,
        accuracy_score_changes=sorted(changes, key=lambda item: (-abs(_int(item.get("change"))), str(item.get("thesis_id")))),
        quality_score_changes=sorted(quality_changes, key=lambda item: (-abs(_int(item.get("change"))), str(item.get("thesis_id")))),
        process_score_changes=sorted(process_changes, key=lambda item: (-abs(_int(item.get("change"))), str(item.get("thesis_id")))),
        review_priority_changes=priority_changes,
        average_accuracy_score_change=current_avg - previous_avg,
        summary=summary,
    )


def _report_from_data(data: JsonMap) -> ThesisAccuracyReport:
    scores = [ThesisAccuracyScore(**item) for item in _map_list(data.get("scores", []))]
    summary = ThesisOutcomeSummary(**_map(data.get("summary")))
    snapshot_data = _map(data.get("snapshot"))
    snapshot = ThesisAccuracySnapshot(
        snapshot_id=str(snapshot_data.get("snapshot_id", "")),
        created_at=str(snapshot_data.get("created_at", "")),
        version=str(snapshot_data.get("version", "")),
        scores=scores,
        summary=summary,
        provenance=_map(snapshot_data.get("provenance")),
        limitations=_string_list(snapshot_data.get("limitations", [])),
    )
    delta = ThesisAccuracyDelta(**_map(data.get("delta")))
    return ThesisAccuracyReport(
        report_id=str(data.get("report_id", "")),
        created_at=str(data.get("created_at", "")),
        version=str(data.get("version", "")),
        snapshot=snapshot,
        delta=delta,
        recommendations_for_research_process=_string_list(data.get("recommendations_for_research_process", [])),
        limitations=_string_list(data.get("limitations", [])),
        provenance=_map(data.get("provenance")),
    )


def _artifacts(root: Path) -> dict[str, JsonMap]:
    return {name: _read_optional_json(root / path) for name, path in THESIS_ACCURACY_INPUTS.items()}


def _decision_outcomes(artifacts: dict[str, JsonMap]) -> list[JsonMap]:
    direct = _map_list(_map(artifacts.get("decision_outcomes")).get("decision_outcomes", []))
    if direct:
        return direct
    return _map_list(_map(artifacts.get("performance_intelligence")).get("decision_outcomes", []))


def _related_themes(thesis: JsonMap, artifacts: dict[str, JsonMap]) -> list[str]:
    items = set(_string_list(_map(thesis.get("metadata")).get("related_themes", [])))
    items.update(_string_list(thesis.get("related_themes", [])))
    title = str(thesis.get("title", ""))
    for theme in _map_list(_map(artifacts.get("theme_lifecycle")).get("themes", [])):
        name = str(theme.get("theme_name") or theme.get("name") or "")
        if name and _norm(name) in _norm(title):
            items.add(name)
    return sorted(items)


def _related_entities(thesis: JsonMap, artifacts: dict[str, JsonMap]) -> list[str]:
    items = set(_string_list(_map(thesis.get("metadata")).get("related_entities", [])))
    items.update(_string_list(thesis.get("related_entities", [])))
    title = str(thesis.get("title", ""))
    for entity in _map_list(_map(artifacts.get("ai_markets")).get("entities", [])):
        symbol = str(entity.get("symbol") or entity.get("entity") or entity.get("name") or "")
        if symbol and _norm(symbol) in _norm(title):
            items.add(symbol)
    return sorted(items)


def _links_to_thesis(decision: JsonMap, thesis_id: str, title: str, themes: list[str], entities: list[str]) -> bool:
    decision_text = _norm(" ".join([str(decision.get("title", "")), str(decision.get("entry_id", "")), str(decision.get("outcome_id", ""))]))
    if thesis_id and _norm(thesis_id) in decision_text:
        return True
    if title and _norm(title) in decision_text:
        return True
    decision_themes = {_norm(item) for item in _string_list(decision.get("related_themes", []))}
    decision_entities = {_norm(item) for item in _string_list(decision.get("related_entities", []))}
    return bool(decision_themes & {_norm(item) for item in themes}) or bool(decision_entities & {_norm(item) for item in entities})


def _linked_catalysts(decisions: list[JsonMap], catalysts: list[JsonMap], themes: list[str], entities: list[str]) -> list[str]:
    items = set()
    for decision in decisions:
        items.update(_string_list(decision.get("related_catalysts", [])))
    haystack = {_norm(item) for item in themes + entities}
    for catalyst in catalysts:
        category = str(catalyst.get("category", ""))
        title = str(catalyst.get("title", ""))
        if _norm(category) in haystack or any(item and item in _norm(title) for item in haystack):
            items.add(str(catalyst.get("catalyst_id") or title or category))
    return sorted(items)


def _count_status(decisions: list[JsonMap], status: str) -> int:
    return sum(1 for decision in decisions if decision.get("outcome_status") == status)


def _rationale(confirmed: int, challenged: int, contradicted: int, unresolved: int, evidence_count: int, source_count: int, gap_penalty: int) -> list[str]:
    items = [f"Evidence references: {evidence_count}.", f"Source references: {source_count}."]
    if confirmed:
        items.append(f"Confirmed decision outcomes: {confirmed}.")
    if challenged:
        items.append(f"Challenged decision outcomes: {challenged}.")
    if contradicted:
        items.append(f"Contradictions or explicit conflicts: {contradicted}.")
    if unresolved:
        items.append(f"Unresolved decision outcomes: {unresolved}.")
    if gap_penalty:
        items.append(f"Process completeness gaps: {gap_penalty}.")
    return items


def _review_priority(accuracy: int, process: int, challenged: int, contradicted: int, unresolved: int) -> str:
    if contradicted > 0 or challenged >= 2 or accuracy < 45 or process < 45 or unresolved >= 3:
        return "high"
    if challenged > 0 or unresolved > 0 or accuracy < 65 or process < 65:
        return "medium"
    return "low"


def _process_weaknesses(scores: list[ThesisAccuracyScore]) -> list[str]:
    weaknesses = []
    if any(score.unresolved_count for score in scores):
        weaknesses.append("Some thesis-linked decisions remain unresolved.")
    if any(score.contradicted_count for score in scores):
        weaknesses.append("Some theses have explicit contradictions or conflicting evidence.")
    if any(score.process_score < 65 for score in scores):
        weaknesses.append("Some theses need stronger rationale, uncertainty, or follow-up records.")
    if not weaknesses:
        weaknesses.append("No deterministic thesis process weaknesses detected from available records.")
    return weaknesses


def _process_recommendations(scores: list[ThesisAccuracyScore]) -> list[str]:
    recommendations = []
    if any(score.review_priority == "high" for score in scores):
        recommendations.append("Review high-priority theses and record explicit thesis review outcomes.")
    if any(score.unresolved_count for score in scores):
        recommendations.append("Close unresolved decision reviews with evidence-backed outcome notes.")
    if any(score.contradicted_count for score in scores):
        recommendations.append("Document how contradictions affect thesis status and future review cadence.")
    if not scores:
        recommendations.append("Build thesis intelligence before interpreting thesis accuracy.")
    if not recommendations:
        recommendations.append("Continue periodic thesis review using explicit decision outcomes and evidence IDs.")
    return recommendations


def _limitations() -> list[str]:
    return [
        "Thesis Accuracy is deterministic and uses only existing local Constellation artifacts.",
        "Scores are process and evidence-review indicators, not investment performance, price accuracy, return forecasts, or advice.",
        "Missing artifacts are reported through provenance and are not inferred.",
    ]


def _score_ref(score: ThesisAccuracyScore) -> JsonMap:
    return {
        "thesis_id": score.thesis_id,
        "title": score.title,
        "accuracy_score": score.accuracy_score,
        "quality_score": score.quality_score,
        "process_score": score.process_score,
        "review_priority": score.review_priority,
    }


def _top(scores: list[ThesisAccuracyScore], field: str) -> list[ThesisAccuracyScore]:
    return sorted(scores, key=lambda item: (-int(getattr(item, field)), item.thesis_id))[:5]


def _bottom(scores: list[ThesisAccuracyScore], field: str) -> list[ThesisAccuracyScore]:
    return sorted(scores, key=lambda item: (int(getattr(item, field)), item.thesis_id))[:5]


def _scores_seed(scores: list[ThesisAccuracyScore]) -> str:
    return "|".join(
        f"{score.thesis_id}:{score.accuracy_score}:{score.quality_score}:{score.process_score}:{score.review_priority}:{score.confirmed_count}:{score.challenged_count}:{score.contradicted_count}:{score.unresolved_count}"
        for score in sorted(scores, key=lambda item: item.thesis_id)
    )


def _score_lines(scores: list[ThesisAccuracyScore]) -> list[str]:
    if not scores:
        return ["- None", ""]
    return [*[f"- `{score.thesis_id}` {score.title}: accuracy `{score.accuracy_score}`, process `{score.process_score}`, priority `{score.review_priority}`" for score in scores], ""]


def _change_lines(items: list[JsonMap]) -> list[str]:
    if not items:
        return ["- None", ""]
    return [*[f"- `{item.get('thesis_id')}` {item.get('title', '')}: {item.get('change', 0):+}" for item in items], ""]


def _summary_lines(summary: JsonMap) -> list[str]:
    if not summary:
        return ["- None", ""]
    return [*[f"- {key}: `{value}`" for key, value in summary.items() if key not in {"highest_accuracy_theses", "lowest_accuracy_theses", "most_improved_theses", "most_degraded_theses", "process_weaknesses"}], ""]


def _string_lines(items: list[str]) -> list[str]:
    if not items:
        return ["- None", ""]
    return [*[f"- {item}" for item in items], ""]


def _read_optional_json(path: Path) -> JsonMap:
    if not path.exists():
        return {}
    try:
        data = read_json(path)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _map(value: Any) -> JsonMap:
    return value if isinstance(value, dict) else {}


def _map_list(value: Any) -> list[JsonMap]:
    if not isinstance(value, list):
        return []
    return [item for item in value if isinstance(item, dict)]


def _string_list(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if isinstance(item, str)]


def _int(value: Any) -> int:
    return value if isinstance(value, int) else 0


def _average(values: list[int]) -> int:
    if not values:
        return 0
    return round(sum(values) / len(values))


def _clamp(value: int) -> int:
    return max(0, min(100, int(value)))


def _norm(value: str) -> str:
    return " ".join(value.lower().replace("_", " ").replace("-", " ").split())


def _digest(value: str) -> str:
    return sha256(value.encode("utf-8")).hexdigest()[:16]


def _now_iso() -> str:
    return datetime.now().astimezone().isoformat(timespec="seconds")
