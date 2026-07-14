from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from hashlib import sha256
from pathlib import Path
import re
from typing import Any

from . import __version__
from .io import read_json, write_json
from .models import JsonMap
from .simple_yaml import load_yaml


class AIMarketsError(RuntimeError):
    pass


THEME_KEYWORDS = {
    "AI Infrastructure": ["ai infrastructure", "compute", "data center", "gpu", "accelerator", "inference"],
    "Semiconductors": ["semiconductor", "chip", "nvda", "amd", "avgo", "foundry", "wafer"],
    "Power Grid": ["power grid", "grid", "electricity", "transmission", "load growth", "power demand"],
    "Robotics": ["robotics", "robot", "automation", "warehouse automation", "humanoid"],
    "Enterprise AI": ["enterprise ai", "copilot", "productivity ai", "workflow automation", "ai software"],
    "Bitcoin": ["bitcoin", "btc", "digital asset"],
    "Gold": ["gold", "gld", "monetary metal"],
    "Nuclear Energy": ["nuclear", "uranium", "ura", "reactor", "smr"],
    "Defense Technology": ["defense", "drone", "missile", "autonomy", "palantir", "pltr"],
    "Space Infrastructure": ["space", "satellite", "launch", "orbital"],
    "Software Disruption": ["software disruption", "saas", "software", "application layer"],
    "Digital Credit": ["digital credit", "private credit", "stablecoin", "tokenized credit"],
    "Monetary Debasement": ["debasement", "money supply", "fiat", "inflation", "liquidity"],
    "Commodities": ["commodity", "commodities", "copper", "silver", "xme", "copx"],
    "Macro Liquidity": ["macro liquidity", "liquidity", "rates", "fed", "dollar", "treasury"],
}

ENTITY_MAP = {
    "NVDA": ("NVIDIA", "equity"),
    "AMD": ("AMD", "equity"),
    "AVGO": ("Broadcom", "equity"),
    "MSFT": ("Microsoft", "equity"),
    "GOOGL": ("Alphabet", "equity"),
    "GOOG": ("Alphabet", "equity"),
    "AMZN": ("Amazon", "equity"),
    "META": ("Meta", "equity"),
    "TSLA": ("Tesla", "equity"),
    "PLTR": ("Palantir", "equity"),
    "ORCL": ("Oracle", "equity"),
    "CRWV": ("CoreWeave", "equity"),
    "IREN": ("IREN", "equity"),
    "COIN": ("Coinbase", "equity"),
    "MSTR": ("MicroStrategy", "equity"),
    "IBM": ("IBM", "equity"),
    "NOW": ("ServiceNow", "equity"),
    "INTC": ("Intel", "equity"),
    "MRVL": ("Marvell", "equity"),
    "GFS": ("GlobalFoundries", "equity"),
    "AMKR": ("Amkor", "equity"),
    "BTC": ("Bitcoin", "asset"),
    "ETH": ("Ethereum", "asset"),
    "GLD": ("Gold ETF", "fund"),
    "SLV": ("Silver ETF", "fund"),
    "URA": ("Uranium ETF", "fund"),
    "XME": ("Metals and Mining ETF", "fund"),
    "COPX": ("Copper Miners ETF", "fund"),
}

ENTITY_ALIASES = {
    "NVDA": ["nvda", "nvidia"],
    "AMD": ["amd", "advanced micro devices"],
    "AVGO": ["avgo", "broadcom"],
    "MSFT": ["msft", "microsoft"],
    "GOOGL": ["googl", "google", "alphabet"],
    "GOOG": ["goog"],
    "AMZN": ["amzn", "amazon"],
    "META": ["meta"],
    "TSLA": ["tsla", "tesla"],
    "PLTR": ["pltr", "palantir"],
    "ORCL": ["orcl", "oracle"],
    "CRWV": ["crwv", "coreweave"],
    "IREN": ["iren"],
    "COIN": ["coin", "coinbase"],
    "MSTR": ["mstr", "microstrategy", "strategy"],
    "IBM": ["ibm"],
    "NOW": ["now", "servicenow"],
    "INTC": ["intc", "intel"],
    "MRVL": ["mrvl", "marvell"],
    "GFS": ["gfs", "globalfoundries"],
    "AMKR": ["amkr", "amkor"],
    "BTC": ["btc", "bitcoin"],
    "ETH": ["eth", "ethereum"],
    "GLD": ["gld", "gold"],
    "SLV": ["slv", "silver"],
    "URA": ["ura", "uranium"],
    "XME": ["xme"],
    "COPX": ["copx"],
}

HIGH_PRIORITY_ENTITIES = {"NVDA", "AMD", "AVGO", "MSFT", "GOOGL", "GOOG", "AMZN", "META", "TSLA", "BTC", "ETH", "COIN", "MSTR"}
QUESTION_PRIORITY_TERMS = [
    "bottleneck",
    "risk",
    "contradiction",
    "catalyst",
    "weakening",
    "acceleration",
    "slowdown",
    "liquidity",
    "capex",
    "power",
    "margin",
    "regulation",
    "adoption",
]

CATALYST_WORDS = ["catalyst", "launch", "approval", "earnings", "deadline", "buildout", "deployment", "release"]
RISK_WORDS = ["risk", "gap", "constraint", "shortage", "concern", "weakening", "contradiction", "delay"]
QUESTION_WORDS = ["?", "open question", "needs review", "what evidence", "unclear"]

CATALYST_CATEGORY_KEYWORDS = {
    "earnings": ["earnings", "quarterly results", "revenue", "margins", "guidance", "outlook"],
    "fed_policy": ["fed", "fomc", "rate cut", "rate hike", "policy", "powell", "minutes", "sep"],
    "inflation": ["cpi", "pce", "inflation", "disinflation", "price pressure"],
    "employment": ["jobs", "payrolls", "unemployment", "labor market", "wages"],
    "liquidity": ["liquidity", "dollar", "dxy", "yields", "treasury", "qt", "qe", "reserves"],
    "credit": ["spreads", "credit", "default", "refinancing", "debt", "high yield"],
    "capex": ["capex", "capital expenditure", "hyperscaler spend", "data center spend", "ai spend"],
    "product_launch": ["launch", "product release", "model release", "chip launch", "platform release"],
    "regulation": ["regulation", "regulatory", "sec", "doj", "antitrust", "policy risk"],
    "energy_power": ["power", "grid", "energy", "electricity", "data center power", "transformer", "nuclear", "utility"],
    "supply_chain": ["supply chain", "shortage", "bottleneck", "capacity", "foundry", "packaging"],
    "geopolitical": ["tariffs", "export controls", "china", "taiwan", "sanctions", "war", "conflict"],
    "crypto_etf_flows": ["etf flows", "ibit", "spot etf", "inflows", "outflows"],
    "bitcoin_halving_cycle": ["halving", "bitcoin cycle", "four-year cycle"],
    "commodity_supply": ["copper", "uranium", "gold", "silver", "supply deficit", "inventories"],
    "ai_infrastructure": ["ai infrastructure", "data center", "gpu", "compute"],
    "semiconductor_cycle": ["semiconductor", "chip", "foundry", "wafer"],
    "enterprise_ai_adoption": ["enterprise ai", "copilot", "ai adoption"],
    "defense_policy": ["defense", "drone", "missile", "autonomy"],
    "nuclear_policy": ["nuclear", "reactor", "smr", "fusion"],
    "robotics_adoption": ["robotics", "robot", "humanoid", "automation"],
    "technical_breakout": ["breakout", "new high", "resistance", "triangle breakout", "bullish reversal"],
    "technical_breakdown": ["breakdown", "support break", "lower low", "bearish reversal"],
    "risk_event": ["risk", "contradiction", "slowdown", "deterioration", "compression", "overhang", "stress"],
}

HIGH_IMPACT_CATALYST_TERMS = ["fomc", "cpi", "pce", "earnings", "guidance", "capex", "liquidity", "credit", "breakdown", "breakout", "regulation", "power bottleneck", "export controls"]

INPUTS = {
    "institutional_report": Path("outputs/reports/latest-report.json"),
    "institutional_report_markdown": Path("outputs/reports/latest-report.md"),
    "dashboard": Path("outputs/dashboard/dashboard.json"),
    "evidence_graph": Path("outputs/evidence-graph/evidence-graph.json"),
    "thesis": Path("outputs/thesis/theses.json"),
    "evolution": Path("outputs/evolution/evolution.json"),
    "source_monitor": Path("outputs/source-monitor/latest-monitor.json"),
    "intake": Path("outputs/intake/intake-manifest.json"),
    "google_drive": Path("outputs/google-drive/google-drive-sync-manifest.json"),
}

BRIEF_INPUTS = {
    "ai_markets": Path("outputs/ai-markets/ai-markets.json"),
    "lifecycle": Path("outputs/ai-markets/theme-lifecycle.json"),
    "portfolio": Path("outputs/ai-markets/portfolio/portfolio-intelligence.json"),
    "catalysts": Path("outputs/ai-markets/catalysts/catalyst-monitor.json"),
    "decisions": Path("outputs/ai-markets/decisions/decision-journal.json"),
    "dashboard": Path("outputs/dashboard/dashboard.json"),
    "report": Path("outputs/reports/latest-report.json"),
    "morning": Path("outputs/morning/morning-brief.json"),
    "daily": Path("outputs/daily/daily-run.json"),
    "source_monitor": Path("outputs/source-monitor/latest-monitor.json"),
    "intake": Path("outputs/intake/intake-manifest.json"),
    "google_drive": Path("outputs/google-drive/google-drive-sync-manifest.json"),
    "evidence_graph": Path("outputs/evidence-graph/evidence-graph.json"),
    "thesis": Path("outputs/thesis/theses.json"),
    "evolution": Path("outputs/evolution/evolution.json"),
    "performance": Path("outputs/performance/performance-intelligence.json"),
    "thesis_accuracy": Path("outputs/performance/thesis-accuracy.json"),
}


@dataclass(frozen=True)
class AIMarketsTheme:
    theme_id: str
    name: str
    status: str
    confidence: str
    evidence_count: int
    source_count: int
    related_evidence_ids: list[str]
    related_entities: list[str]
    risks: list[str]
    catalysts: list[str]
    open_questions: list[str]
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()

    @classmethod
    def from_dict(cls, data: JsonMap) -> "AIMarketsTheme":
        return cls(
            theme_id=_require_str(data, "theme_id"),
            name=_require_str(data, "name"),
            status=_require_str(data, "status"),
            confidence=_require_str(data, "confidence"),
            evidence_count=_int(data.get("evidence_count")),
            source_count=_int(data.get("source_count")),
            related_evidence_ids=_string_list(data.get("related_evidence_ids", [])),
            related_entities=_string_list(data.get("related_entities", [])),
            risks=_string_list(data.get("risks", [])),
            catalysts=_string_list(data.get("catalysts", [])),
            open_questions=_string_list(data.get("open_questions", [])),
            provenance=_map(data.get("provenance")),
        )


@dataclass(frozen=True)
class AIMarketsEntity:
    entity_id: str
    symbol: str
    name: str
    entity_type: str
    related_themes: list[str]
    evidence_count: int
    latest_mention: str | None
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AIMarketsCatalyst:
    catalyst_id: str
    description: str
    related_themes: list[str]
    related_entities: list[str]
    evidence_ids: list[str]
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AIMarketsRisk:
    risk_id: str
    description: str
    related_themes: list[str]
    related_entities: list[str]
    evidence_ids: list[str]
    severity: str
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AIMarketsOpenQuestion:
    question_id: str
    question: str
    related_themes: list[str]
    priority: str
    evidence_needed: str
    status: str
    provenance: JsonMap
    normalized_question: str
    evidence_ids: list[str]
    source_ids: list[str]
    supporting_text: list[str]
    latest_mention: str | None

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AIMarketsReport:
    report_id: str
    created_at: str
    version: str
    themes: list[AIMarketsTheme]
    entities: list[AIMarketsEntity]
    catalysts: list[AIMarketsCatalyst]
    risks: list[AIMarketsRisk]
    open_questions: list[AIMarketsOpenQuestion]
    executive_questions: list[AIMarketsOpenQuestion]
    evidence_references: list[str]
    provenance: JsonMap
    limitations: list[str]

    def to_dict(self) -> JsonMap:
        return {
            "report_id": self.report_id,
            "created_at": self.created_at,
            "version": self.version,
            "themes": [item.to_dict() for item in self.themes],
            "entities": [item.to_dict() for item in self.entities],
            "catalysts": [item.to_dict() for item in self.catalysts],
            "risks": [item.to_dict() for item in self.risks],
            "open_questions": [item.to_dict() for item in self.open_questions],
            "executive_questions": [item.to_dict() for item in self.executive_questions],
            "evidence_references": self.evidence_references,
            "provenance": self.provenance,
            "limitations": self.limitations,
        }

    @classmethod
    def from_dict(cls, data: JsonMap) -> "AIMarketsReport":
        return cls(
            report_id=_require_str(data, "report_id"),
            created_at=_require_str(data, "created_at"),
            version=_require_str(data, "version"),
            themes=[AIMarketsTheme.from_dict(item) for item in _map_list(data.get("themes", []))],
            entities=[_entity_from_dict(item) for item in _map_list(data.get("entities", []))],
            catalysts=[_catalyst_from_dict(item) for item in _map_list(data.get("catalysts", []))],
            risks=[_risk_from_dict(item) for item in _map_list(data.get("risks", []))],
            open_questions=[_question_from_dict(item) for item in _map_list(data.get("open_questions", []))],
            executive_questions=[_question_from_dict(item) for item in _map_list(data.get("executive_questions", []))],
            evidence_references=_string_list(data.get("evidence_references", [])),
            provenance=_map(data.get("provenance")),
            limitations=_string_list(data.get("limitations", [])),
        )


@dataclass(frozen=True)
class AIMarketsThemeLifecycleDelta:
    evidence_delta: int
    source_delta: int
    entity_delta: int
    risk_delta: int

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AIMarketsThemeTransition:
    transition_id: str
    theme_id: str
    theme_name: str
    transition_type: str
    previous_value: Any
    current_value: Any
    reason: str
    created_at: str
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AIMarketsThemeLifecycleSnapshot:
    snapshot_id: str
    created_at: str
    version: str
    themes: list[JsonMap]
    transitions: list[AIMarketsThemeTransition]
    provenance: JsonMap
    limitations: list[str]

    def to_dict(self) -> JsonMap:
        return {
            "snapshot_id": self.snapshot_id,
            "created_at": self.created_at,
            "version": self.version,
            "theme_count": len(self.themes),
            "themes": self.themes,
            "transitions": [item.to_dict() for item in self.transitions],
            "counts": _lifecycle_counts(self.themes),
            "provenance": self.provenance,
            "limitations": self.limitations,
        }


@dataclass(frozen=True)
class AIMarketsThemeTimeline:
    theme_id: str
    theme_name: str
    transitions: list[AIMarketsThemeTransition]

    def to_dict(self) -> JsonMap:
        return {
            "theme_id": self.theme_id,
            "theme_name": self.theme_name,
            "transitions": [item.to_dict() for item in self.transitions],
        }


class AIMarketsThemeLifecycleEngine:
    def __init__(self, root: Path) -> None:
        self.root = root

    def build(self, report: AIMarketsReport, history: list[JsonMap]) -> AIMarketsThemeLifecycleSnapshot:
        now = _now_iso()
        previous = _latest_snapshot(history)
        previous_themes = {str(item.get("theme_id")): item for item in _map_list(previous.get("themes", []))}
        previous_by_name = {str(item.get("theme_name")): item for item in previous_themes.values()}
        risk_by_id = {risk.risk_id: risk for risk in report.risks}
        current_themes: list[JsonMap] = []
        for theme in report.themes:
            previous_theme = previous_themes.get(theme.theme_id)
            entry = self._theme_entry(theme, report, risk_by_id, previous_theme, previous_by_name.get(theme.name), history, now)
            current_themes.append(entry)
        current_ids = {theme.theme_id for theme in report.themes}
        for previous_theme in previous_themes.values():
            if str(previous_theme.get("theme_id")) not in current_ids:
                current_themes.append(self._absent_theme_entry(previous_theme, history, now))
        current_themes = sorted(current_themes, key=_lifecycle_theme_sort_key)
        transitions = _theme_transitions(current_themes, previous_themes, now)
        snapshot_id = _lifecycle_snapshot_id(current_themes)
        return AIMarketsThemeLifecycleSnapshot(
            snapshot_id=snapshot_id,
            created_at=now,
            version=__version__,
            themes=current_themes,
            transitions=transitions,
            provenance={"ai_markets_report_id": report.report_id, "ai_markets_report_path": "outputs/ai-markets/ai-markets.json"},
            limitations=[
                "Theme lifecycle uses deterministic counts, status changes, and explicit risk or contradiction language only.",
                "No prediction, financial advice, provider call, LLM inference, embeddings, semantic similarity, or web retrieval is used.",
            ],
        )

    def _theme_entry(
        self,
        theme: AIMarketsTheme,
        report: AIMarketsReport,
        risk_by_id: dict[str, AIMarketsRisk],
        previous_theme: JsonMap | None,
        previous_by_name: JsonMap | None,
        history: list[JsonMap],
        now: str,
    ) -> JsonMap:
        previous = previous_theme or previous_by_name or {}
        previous_status = str(previous.get("current_status") or "")
        previous_confidence = str(previous.get("confidence") or "")
        previous_evidence = _int(previous.get("evidence_count"))
        previous_sources = _int(previous.get("source_count"))
        previous_entities = _int(previous.get("entity_count"))
        previous_risks = _int(previous.get("risk_count"))
        entity_count = len(theme.related_entities)
        risk_count = len(theme.risks)
        catalyst_count = len(theme.catalysts)
        open_question_count = len(theme.open_questions)
        risk_descriptions = [risk_by_id[risk_id].description for risk_id in theme.risks if risk_id in risk_by_id]
        status, reason = _lifecycle_status(theme, previous, entity_count, risk_count, risk_descriptions, history)
        confidence = _confidence(theme.evidence_count, theme.source_count)
        first_seen_at = str(previous.get("first_seen_at") or now)
        latest_evidence_at = now if theme.related_evidence_ids else str(previous.get("latest_evidence_at") or "")
        return {
            "theme_id": theme.theme_id,
            "theme_name": theme.name,
            "current_status": status,
            "previous_status": previous_status or None,
            "status_changed": bool(previous_status and previous_status != status),
            "confidence": confidence,
            "previous_confidence": previous_confidence or None,
            "confidence_changed": bool(previous_confidence and previous_confidence != confidence),
            "evidence_count": theme.evidence_count,
            "previous_evidence_count": previous_evidence,
            "evidence_delta": theme.evidence_count - previous_evidence,
            "source_count": theme.source_count,
            "previous_source_count": previous_sources,
            "source_delta": theme.source_count - previous_sources,
            "entity_count": entity_count,
            "previous_entity_count": previous_entities,
            "entity_delta": entity_count - previous_entities,
            "risk_count": risk_count,
            "previous_risk_count": previous_risks,
            "risk_delta": risk_count - previous_risks,
            "catalyst_count": catalyst_count,
            "open_question_count": open_question_count,
            "latest_evidence_at": latest_evidence_at,
            "first_seen_at": first_seen_at,
            "last_seen_at": now,
            "lifecycle_reason": reason,
            "confidence_reason": _confidence_reason(confidence, theme.evidence_count, theme.source_count, entity_count, risk_count, previous_confidence),
            "supporting_evidence_ids": theme.related_evidence_ids,
            "related_entities": theme.related_entities,
            "related_risks": theme.risks,
            "provenance": {"matched_keywords": _string_list(theme.provenance.get("matched_keywords", [])), "risk_descriptions": risk_descriptions},
        }

    def _absent_theme_entry(self, previous_theme: JsonMap, history: list[JsonMap], now: str) -> JsonMap:
        absent_count = _absence_count(str(previous_theme.get("theme_id")), history) + 1
        status = "archived" if absent_count >= 2 else "weakening"
        reason = (
            f"Theme is archived because it has been absent for {absent_count} lifecycle snapshots."
            if status == "archived"
            else "Theme is weakening because it was not seen in the latest AI & Markets build."
        )
        return {
            **previous_theme,
            "current_status": status,
            "previous_status": previous_theme.get("current_status"),
            "status_changed": previous_theme.get("current_status") != status,
            "previous_confidence": previous_theme.get("confidence"),
            "confidence_changed": False,
            "previous_evidence_count": _int(previous_theme.get("evidence_count")),
            "evidence_count": 0,
            "evidence_delta": -_int(previous_theme.get("evidence_count")),
            "previous_source_count": _int(previous_theme.get("source_count")),
            "source_count": 0,
            "source_delta": -_int(previous_theme.get("source_count")),
            "last_seen_at": previous_theme.get("last_seen_at"),
            "lifecycle_reason": reason,
            "provenance": {**_map(previous_theme.get("provenance")), "absence_count": absent_count},
        }


class AIMarketsThemeLifecycleStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "outputs" / "ai-markets"
        self.lifecycle_path = self.directory / "theme-lifecycle.json"
        self.lifecycle_report_path = self.directory / "theme-lifecycle.md"
        self.history_path = self.directory / "theme-history.json"
        self.transitions_path = self.directory / "theme-transitions.json"
        self.timeline_path = self.directory / "theme-timeline.md"

    def build(self, report: AIMarketsReport | None = None) -> AIMarketsThemeLifecycleSnapshot:
        report = report or AIMarketsStore(self.root).load()
        snapshot = AIMarketsThemeLifecycleEngine(self.root).build(report, self.history())
        self.save(snapshot)
        return snapshot

    def load(self) -> JsonMap:
        if not self.lifecycle_path.exists():
            raise AIMarketsError("No AI & Markets theme lifecycle found. Run `python -m constellation ai-markets lifecycle` first.")
        return read_json(self.lifecycle_path)

    def history(self) -> list[JsonMap]:
        if not self.history_path.exists():
            return []
        data = read_json(self.history_path)
        return _map_list(data.get("snapshots", []))

    def save(self, snapshot: AIMarketsThemeLifecycleSnapshot) -> None:
        data = snapshot.to_dict()
        write_json(self.lifecycle_path, data)
        write_json(self.transitions_path, {"transitions": [item.to_dict() for item in snapshot.transitions]})
        history = self.history()
        latest_report_id = _map(_map(history[-1]).get("provenance")).get("ai_markets_report_id") if history else None
        current_report_id = _map(data.get("provenance")).get("ai_markets_report_id")
        if not history or (history[-1].get("snapshot_id") != snapshot.snapshot_id and latest_report_id != current_report_id):
            history.append(data)
        write_json(self.history_path, {"snapshots": history})
        self.lifecycle_report_path.write_text(render_theme_lifecycle(snapshot), encoding="utf-8")
        self.timeline_path.write_text(render_theme_timeline(history), encoding="utf-8")

    def status(self) -> JsonMap:
        if not self.lifecycle_path.exists():
            return {"available": False, "report_path": str(self.lifecycle_report_path)}
        data = self.load()
        counts = _map(data.get("counts"))
        return {
            "available": True,
            "snapshot_id": data.get("snapshot_id"),
            "theme_count": _int(data.get("theme_count")),
            "recent_transition_count": len(_map_list(data.get("transitions", []))),
            "report_path": str(self.lifecycle_report_path),
            **counts,
        }

    def theme(self, theme_id: str) -> JsonMap:
        data = self.load()
        for theme in _map_list(data.get("themes", [])):
            if theme.get("theme_id") == theme_id:
                return theme
        raise AIMarketsError(f"AI & Markets theme not found: {theme_id}")


@dataclass(frozen=True)
class AIMarketsPortfolioPosition:
    symbol: str
    name: str
    asset_type: str
    category: str
    source: str
    related_themes: list[str]
    lifecycle_statuses: list[str]
    related_risks: list[str]
    related_questions: list[str]
    evidence_count: int
    source_count: int
    confidence: str
    research_priority: str
    priority_reason: str
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AIMarketsPortfolioWatchlistItem(AIMarketsPortfolioPosition):
    pass


@dataclass(frozen=True)
class AIMarketsPortfolioExposure:
    theme_id: str
    theme_name: str
    lifecycle_status: str
    confidence: str
    related_symbols: list[str]
    position_symbols: list[str]
    watchlist_symbols: list[str]
    detected_symbols: list[str]
    evidence_count: int
    source_count: int
    risk_count: int
    question_count: int
    exposure_type: str
    research_priority: str
    priority_reason: str
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AIMarketsPortfolioRisk:
    risk_id: str
    description: str
    related_symbols: list[str]
    related_themes: list[str]
    severity: str
    source_risk_id: str
    evidence_ids: list[str]
    priority: str
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AIMarketsPortfolioQuestion:
    question_id: str
    question: str
    related_symbols: list[str]
    related_themes: list[str]
    priority: str
    source_question_id: str
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AIMarketsPortfolioDelta:
    prior_snapshot_id: str | None
    current_snapshot_id: str
    position_count_change: int
    watchlist_count_change: int
    theme_exposure_count_change: int
    risk_count_change: int
    high_priority_review_count_change: int
    new_symbols: list[str]
    removed_symbols: list[str]

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AIMarketsPortfolioSnapshot:
    snapshot_id: str
    created_at: str
    config_available: bool
    config_path: str | None
    mode: str
    positions: list[AIMarketsPortfolioPosition]
    watchlist: list[AIMarketsPortfolioWatchlistItem]
    detected_entities: list[AIMarketsPortfolioWatchlistItem]
    exposures: list[AIMarketsPortfolioExposure]
    risks: list[AIMarketsPortfolioRisk]
    questions: list[AIMarketsPortfolioQuestion]
    delta: AIMarketsPortfolioDelta
    provenance: JsonMap
    limitations: list[str]

    def to_dict(self) -> JsonMap:
        return {
            "snapshot_id": self.snapshot_id,
            "created_at": self.created_at,
            "config_available": self.config_available,
            "config_path": self.config_path,
            "mode": self.mode,
            "position_count": len(self.positions),
            "watchlist_count": len(self.watchlist),
            "detected_entity_count": len(self.detected_entities),
            "theme_exposure_count": len(self.exposures),
            "risk_count": len(self.risks),
            "question_count": len(self.questions),
            "high_priority_review_count": _portfolio_high_priority_count(self.positions + self.watchlist + self.detected_entities, self.exposures, self.risks),
            "positions": [item.to_dict() for item in self.positions],
            "watchlist": [item.to_dict() for item in self.watchlist],
            "detected_entities": [item.to_dict() for item in self.detected_entities],
            "exposures": [item.to_dict() for item in self.exposures],
            "risks": [item.to_dict() for item in self.risks],
            "questions": [item.to_dict() for item in self.questions],
            "delta": self.delta.to_dict(),
            "provenance": self.provenance,
            "limitations": self.limitations,
        }


@dataclass(frozen=True)
class AIMarketsPortfolioReport:
    snapshot: AIMarketsPortfolioSnapshot

    def to_dict(self) -> JsonMap:
        return self.snapshot.to_dict()


class AIMarketsPortfolioEngine:
    def __init__(self, root: Path) -> None:
        self.root = root

    def build(self, report: AIMarketsReport, lifecycle: AIMarketsThemeLifecycleSnapshot | None, history: list[JsonMap]) -> AIMarketsPortfolioSnapshot:
        config, config_path = _portfolio_config(self.root)
        positions_config = _map_list(_map(config.get("portfolio")).get("positions", []))
        watchlist_config = _map_list(_map(config.get("portfolio")).get("watchlist", []))
        config_available = config_path is not None
        lifecycle_data = lifecycle.to_dict() if lifecycle else _read_optional_json(self.root / "outputs" / "ai-markets" / "theme-lifecycle.json")
        lifecycle_by_name = {str(item.get("theme_name")): item for item in _map_list(lifecycle_data.get("themes", []))}
        risks_by_theme = _risks_by_theme(report.risks)
        questions_by_theme = _questions_by_theme(report.open_questions)
        entity_items = [_portfolio_item_from_entity(entity, "detected_entity", report, lifecycle_by_name, risks_by_theme, questions_by_theme) for entity in report.entities]
        positions = [_portfolio_item_from_config(item, "portfolio_config", report, lifecycle_by_name, risks_by_theme, questions_by_theme) for item in positions_config]
        watchlist = [_portfolio_item_from_config(item, "watchlist_config", report, lifecycle_by_name, risks_by_theme, questions_by_theme) for item in watchlist_config]
        configured_symbols = {item.symbol for item in positions + watchlist}
        detected_entities = [item for item in entity_items if item.symbol not in configured_symbols]
        mode = "portfolio" if positions else "watchlist" if watchlist else "detected_entities_only"
        exposures = _portfolio_exposures(report, lifecycle_by_name, positions, watchlist, detected_entities, risks_by_theme, questions_by_theme)
        risks = _portfolio_risks(report.risks, positions + watchlist + detected_entities)
        questions = _portfolio_questions(report.open_questions, positions + watchlist + detected_entities)
        snapshot_id = _portfolio_snapshot_id(mode, positions, watchlist, detected_entities, exposures, risks, questions)
        delta = _portfolio_delta(history[-1] if history else {}, snapshot_id, positions, watchlist, exposures, risks)
        return AIMarketsPortfolioSnapshot(
            snapshot_id=snapshot_id,
            created_at=_now_iso(),
            config_available=config_available,
            config_path=str(config_path) if config_path else None,
            mode=mode,
            positions=sorted(positions, key=_portfolio_item_sort_key),
            watchlist=sorted(watchlist, key=_portfolio_item_sort_key),
            detected_entities=sorted(detected_entities, key=_portfolio_item_sort_key),
            exposures=sorted(exposures, key=_portfolio_exposure_sort_key),
            risks=sorted(risks, key=_portfolio_risk_sort_key),
            questions=sorted(questions, key=_portfolio_question_sort_key),
            delta=delta,
            provenance={
                "ai_markets_report_id": report.report_id,
                "theme_lifecycle_snapshot_id": lifecycle.snapshot_id if lifecycle else lifecycle_data.get("snapshot_id"),
            },
            limitations=[
                "Portfolio Intelligence is research organization only and is not financial advice.",
                "No trading recommendations, provider calls, LLM inference, embeddings, semantic similarity, web retrieval, or external services are used.",
                "Local portfolio config is optional and should not contain private holdings in the repository.",
            ],
        )


class AIMarketsPortfolioStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "outputs" / "ai-markets" / "portfolio"
        self.json_path = self.directory / "portfolio-intelligence.json"
        self.report_path = self.directory / "portfolio-intelligence.md"
        self.exposures_json_path = self.directory / "portfolio-exposures.json"
        self.exposures_path = self.directory / "portfolio-exposures.md"
        self.risks_json_path = self.directory / "portfolio-risks.json"
        self.risks_path = self.directory / "portfolio-risks.md"
        self.watchlist_json_path = self.directory / "portfolio-watchlist.json"
        self.watchlist_path = self.directory / "portfolio-watchlist.md"
        self.questions_json_path = self.directory / "portfolio-questions.json"
        self.questions_path = self.directory / "portfolio-questions.md"
        self.history_path = self.directory / "portfolio-history.json"
        self.delta_path = self.directory / "portfolio-delta.json"

    def build(self, report: AIMarketsReport | None = None, lifecycle: AIMarketsThemeLifecycleSnapshot | None = None) -> AIMarketsPortfolioSnapshot:
        report = report or AIMarketsStore(self.root).load()
        lifecycle = lifecycle or AIMarketsThemeLifecycleStore(self.root).build(report)
        snapshot = AIMarketsPortfolioEngine(self.root).build(report, lifecycle, self.history())
        self.save(snapshot)
        return snapshot

    def load(self) -> JsonMap:
        if not self.json_path.exists():
            raise AIMarketsError("No AI & Markets portfolio intelligence found. Run `python -m constellation ai-markets portfolio` first.")
        return read_json(self.json_path)

    def history(self) -> list[JsonMap]:
        if not self.history_path.exists():
            return []
        return _map_list(read_json(self.history_path).get("snapshots", []))

    def save(self, snapshot: AIMarketsPortfolioSnapshot) -> None:
        data = snapshot.to_dict()
        write_json(self.json_path, data)
        write_json(self.exposures_json_path, {"exposures": [item.to_dict() for item in snapshot.exposures]})
        write_json(self.risks_json_path, {"risks": [item.to_dict() for item in snapshot.risks]})
        write_json(self.watchlist_json_path, {"positions": [item.to_dict() for item in snapshot.positions], "watchlist": [item.to_dict() for item in snapshot.watchlist], "detected_entities": [item.to_dict() for item in snapshot.detected_entities]})
        write_json(self.questions_json_path, {"questions": [item.to_dict() for item in snapshot.questions]})
        write_json(self.delta_path, snapshot.delta.to_dict())
        history = self.history()
        if not history or history[-1].get("snapshot_id") != snapshot.snapshot_id:
            history.append(data)
        write_json(self.history_path, {"snapshots": history})
        self.report_path.write_text(render_portfolio_report(snapshot), encoding="utf-8")
        self.exposures_path.write_text(render_portfolio_exposures(snapshot), encoding="utf-8")
        self.risks_path.write_text(render_portfolio_risks(snapshot), encoding="utf-8")
        self.watchlist_path.write_text(render_portfolio_watchlist(snapshot), encoding="utf-8")
        self.questions_path.write_text(render_portfolio_questions(snapshot), encoding="utf-8")

    def status(self) -> JsonMap:
        if not self.json_path.exists():
            return {"available": False, "report_path": str(self.report_path), "exposures_path": str(self.exposures_path)}
        data = self.load()
        return {
            "available": True,
            "snapshot_id": data.get("snapshot_id"),
            "mode": data.get("mode"),
            "config_available": data.get("config_available"),
            "position_count": data.get("position_count", 0),
            "watchlist_count": data.get("watchlist_count", 0),
            "detected_entity_count": data.get("detected_entity_count", 0),
            "theme_exposure_count": data.get("theme_exposure_count", 0),
            "risk_count": data.get("risk_count", 0),
            "high_priority_review_count": data.get("high_priority_review_count", 0),
            "report_path": str(self.report_path),
            "exposures_path": str(self.exposures_path),
        }


@dataclass(frozen=True)
class AIMarketsCatalystPriority:
    priority: str
    reason: str

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AIMarketsCatalystRecord:
    catalyst_id: str
    title: str
    category: str
    description: str
    time_horizon: str
    priority: str
    status: str
    related_themes: list[str]
    related_entities: list[str]
    related_watchlist_symbols: list[str]
    related_portfolio_symbols: list[str]
    related_lifecycle_statuses: list[str]
    related_risks: list[str]
    related_questions: list[str]
    evidence_ids: list[str]
    source_paths: list[str]
    source_count: int
    evidence_count: int
    first_seen_at: str
    latest_seen_at: str
    priority_reason: str
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AIMarketsCatalystDelta:
    new_catalysts: list[str]
    removed_catalysts: list[str]
    priority_changes: list[JsonMap]
    status_changes: list[JsonMap]
    time_horizon_changes: list[JsonMap]
    related_entity_changes: list[JsonMap]
    related_theme_changes: list[JsonMap]

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AIMarketsCatalystTransition:
    transition_id: str
    catalyst_id: str
    transition_type: str
    previous_value: Any
    current_value: Any
    reason: str
    created_at: str
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AIMarketsCatalystSnapshot:
    snapshot_id: str
    created_at: str
    catalysts: list[AIMarketsCatalystRecord]
    delta: AIMarketsCatalystDelta
    transitions: list[AIMarketsCatalystTransition]
    provenance: JsonMap
    limitations: list[str]

    def to_dict(self) -> JsonMap:
        return {
            "snapshot_id": self.snapshot_id,
            "created_at": self.created_at,
            "total_catalyst_count": len(self.catalysts),
            "high_priority_catalyst_count": sum(1 for item in self.catalysts if item.priority == "high"),
            "near_term_catalyst_count": sum(1 for item in self.catalysts if item.time_horizon == "near_term"),
            "portfolio_linked_catalyst_count": sum(1 for item in self.catalysts if item.related_portfolio_symbols or item.related_watchlist_symbols),
            "risk_linked_catalyst_count": sum(1 for item in self.catalysts if item.related_risks),
            "new_catalyst_count": len(self.delta.new_catalysts),
            "stale_catalyst_count": sum(1 for item in self.catalysts if item.status == "stale"),
            "catalysts": [item.to_dict() for item in self.catalysts],
            "delta": self.delta.to_dict(),
            "transitions": [item.to_dict() for item in self.transitions],
            "provenance": self.provenance,
            "limitations": self.limitations,
        }


class AIMarketsCatalystMonitor:
    def __init__(self, snapshot: AIMarketsCatalystSnapshot) -> None:
        self.snapshot = snapshot


class AIMarketsCatalystEngine:
    def __init__(self, root: Path) -> None:
        self.root = root

    def build(
        self,
        report: AIMarketsReport,
        lifecycle: AIMarketsThemeLifecycleSnapshot | None,
        portfolio: AIMarketsPortfolioSnapshot | None,
        history: list[JsonMap],
    ) -> AIMarketsCatalystSnapshot:
        now = _now_iso()
        lifecycle_data = lifecycle.to_dict() if lifecycle else _read_optional_json(self.root / "outputs" / "ai-markets" / "theme-lifecycle.json")
        lifecycle_by_theme = {str(item.get("theme_name")): item for item in _map_list(lifecycle_data.get("themes", []))}
        portfolio_data = portfolio.to_dict() if portfolio else _read_optional_json(self.root / "outputs" / "ai-markets" / "portfolio" / "portfolio-intelligence.json")
        portfolio_items = _map_list(portfolio_data.get("positions", [])) + _map_list(portfolio_data.get("watchlist", [])) + _map_list(portfolio_data.get("detected_entities", []))
        previous = history[-1] if history else {}
        previous_by_id = {str(item.get("catalyst_id")): item for item in _map_list(previous.get("catalysts", []))}
        catalysts = _catalyst_records(report, lifecycle_by_theme, portfolio_items, now, previous_by_id)
        current_ids = {item.catalyst_id for item in catalysts}
        for prior in previous_by_id.values():
            if str(prior.get("catalyst_id")) not in current_ids:
                catalysts.append(_stale_catalyst(prior, now))
        catalysts = sorted(catalysts, key=_catalyst_sort_key)
        delta = _catalyst_delta(previous_by_id, catalysts)
        transitions = _catalyst_transitions(delta, catalysts, previous_by_id, now)
        return AIMarketsCatalystSnapshot(
            snapshot_id=_catalyst_snapshot_id(catalysts),
            created_at=now,
            catalysts=catalysts,
            delta=delta,
            transitions=transitions,
            provenance={"ai_markets_report_id": report.report_id, "portfolio_snapshot_id": portfolio_data.get("snapshot_id"), "theme_lifecycle_snapshot_id": lifecycle_data.get("snapshot_id")},
            limitations=[
                "Catalyst Monitoring uses deterministic keyword and structured record matching only.",
                "This is research organization only and is not financial advice, market prediction, autonomous monitoring, or trading software.",
            ],
        )


class AIMarketsCatalystStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "outputs" / "ai-markets" / "catalysts"
        self.json_path = self.directory / "catalyst-monitor.json"
        self.report_path = self.directory / "catalyst-monitor.md"
        self.priorities_json_path = self.directory / "catalyst-priorities.json"
        self.priorities_path = self.directory / "catalyst-priorities.md"
        self.history_path = self.directory / "catalyst-history.json"
        self.delta_path = self.directory / "catalyst-delta.json"
        self.transitions_path = self.directory / "catalyst-transitions.json"
        self.calendar_path = self.directory / "catalyst-calendar.md"

    def build(
        self,
        report: AIMarketsReport | None = None,
        lifecycle: AIMarketsThemeLifecycleSnapshot | None = None,
        portfolio: AIMarketsPortfolioSnapshot | None = None,
    ) -> AIMarketsCatalystSnapshot:
        report = report or AIMarketsStore(self.root).load()
        lifecycle = lifecycle or AIMarketsThemeLifecycleStore(self.root).build(report)
        portfolio = portfolio or AIMarketsPortfolioStore(self.root).build(report, lifecycle)
        snapshot = AIMarketsCatalystEngine(self.root).build(report, lifecycle, portfolio, self.history())
        self.save(snapshot)
        return snapshot

    def load(self) -> JsonMap:
        if not self.json_path.exists():
            raise AIMarketsError("No AI & Markets catalyst monitor found. Run `python -m constellation ai-markets catalysts` first.")
        return read_json(self.json_path)

    def history(self) -> list[JsonMap]:
        if not self.history_path.exists():
            return []
        return _map_list(read_json(self.history_path).get("snapshots", []))

    def save(self, snapshot: AIMarketsCatalystSnapshot) -> None:
        data = snapshot.to_dict()
        write_json(self.json_path, data)
        write_json(self.priorities_json_path, {"catalysts": [item.to_dict() for item in snapshot.catalysts if item.priority in {"high", "medium"}]})
        write_json(self.delta_path, snapshot.delta.to_dict())
        write_json(self.transitions_path, {"transitions": [item.to_dict() for item in snapshot.transitions]})
        history = self.history()
        if not history or history[-1].get("snapshot_id") != snapshot.snapshot_id:
            history.append(data)
        write_json(self.history_path, {"snapshots": history})
        self.report_path.write_text(render_catalyst_monitor(snapshot), encoding="utf-8")
        self.priorities_path.write_text(render_catalyst_priorities(snapshot), encoding="utf-8")
        self.calendar_path.write_text(render_catalyst_calendar(snapshot), encoding="utf-8")

    def status(self) -> JsonMap:
        if not self.json_path.exists():
            return {"available": False, "report_path": str(self.report_path), "calendar_path": str(self.calendar_path)}
        data = self.load()
        return {
            "available": True,
            "snapshot_id": data.get("snapshot_id"),
            "total_catalyst_count": data.get("total_catalyst_count", 0),
            "high_priority_catalyst_count": data.get("high_priority_catalyst_count", 0),
            "near_term_catalyst_count": data.get("near_term_catalyst_count", 0),
            "portfolio_linked_catalyst_count": data.get("portfolio_linked_catalyst_count", 0),
            "risk_linked_catalyst_count": data.get("risk_linked_catalyst_count", 0),
            "new_catalyst_count": data.get("new_catalyst_count", 0),
            "stale_catalyst_count": data.get("stale_catalyst_count", 0),
            "report_path": str(self.report_path),
            "calendar_path": str(self.calendar_path),
        }


@dataclass(frozen=True)
class AIMarketsDecisionEvidenceLink:
    link_type: str
    source_id: str
    source_path: str

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AIMarketsDecisionOutcome:
    status: str
    text: str

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AIMarketsDecisionReview:
    review_status: str
    review_at: str | None

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AIMarketsDecisionEntry:
    entry_id: str
    title: str
    domain: str
    entry_type: str
    decision_type: str
    status: str
    created_at: str
    updated_at: str
    review_at: str | None
    confidence: str
    related_themes: list[str]
    related_entities: list[str]
    related_catalysts: list[str]
    related_risks: list[str]
    related_questions: list[str]
    related_evidence_ids: list[str]
    linked_theme_lifecycle_statuses: list[str]
    linked_portfolio_exposures: list[str]
    linked_catalyst_priorities: list[str]
    rationale: str
    uncertainties: str
    follow_up: str
    lessons: str
    outcome: AIMarketsDecisionOutcome
    review: AIMarketsDecisionReview
    source_path: str
    user_provided: bool
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        data = self.__dict__.copy()
        data["outcome"] = self.outcome.to_dict()
        data["review"] = self.review.to_dict()
        return data


@dataclass(frozen=True)
class AIMarketsDecisionDelta:
    new_entries: list[str]
    removed_entries: list[str]
    status_changes: list[JsonMap]
    review_status_changes: list[JsonMap]
    outcome_changes: list[JsonMap]
    link_changes: list[JsonMap]
    newly_due_reviews: list[str]
    newly_overdue_reviews: list[str]

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AIMarketsDecisionTimeline:
    entries: list[AIMarketsDecisionEntry]

    def to_dict(self) -> JsonMap:
        return {"entries": [item.to_dict() for item in self.entries]}


@dataclass(frozen=True)
class AIMarketsDecisionSnapshot:
    snapshot_id: str
    created_at: str
    config_available: bool
    config_path: str | None
    entries: list[AIMarketsDecisionEntry]
    delta: AIMarketsDecisionDelta
    provenance: JsonMap
    limitations: list[str]

    def to_dict(self) -> JsonMap:
        entries = [item.to_dict() for item in self.entries]
        return {
            "snapshot_id": self.snapshot_id,
            "created_at": self.created_at,
            "config_available": self.config_available,
            "config_path": self.config_path,
            "entry_count": len(entries),
            "open_decision_count": sum(1 for item in entries if item.get("status") == "open"),
            "monitoring_decision_count": sum(1 for item in entries if item.get("status") == "monitoring"),
            "reviewed_decision_count": sum(1 for item in entries if _map(item.get("review")).get("review_status") == "reviewed"),
            "due_review_count": sum(1 for item in entries if _map(item.get("review")).get("review_status") == "due"),
            "overdue_review_count": sum(1 for item in entries if _map(item.get("review")).get("review_status") == "overdue"),
            "linked_theme_decision_count": sum(1 for item in entries if item.get("related_themes")),
            "linked_entity_decision_count": sum(1 for item in entries if item.get("related_entities")),
            "linked_catalyst_decision_count": sum(1 for item in entries if item.get("related_catalysts")),
            "linked_risk_decision_count": sum(1 for item in entries if item.get("related_risks")),
            "outcome_count": sum(1 for item in entries if _map(item.get("outcome")).get("status") not in {"pending", "no_outcome_recorded"}),
            "entries": entries,
            "delta": self.delta.to_dict(),
            "provenance": self.provenance,
            "limitations": self.limitations,
        }


class AIMarketsDecisionJournalEngine:
    def __init__(self, root: Path) -> None:
        self.root = root

    def build(self, history: list[JsonMap]) -> AIMarketsDecisionSnapshot:
        config, config_path = _decision_config(self.root)
        paths = _decision_entry_paths(self.root, config)
        artifacts = _decision_artifacts(self.root)
        entries = []
        for directory in paths:
            if directory.exists():
                for path in sorted(directory.glob("*.md")):
                    entries.append(_parse_decision_entry(path, artifacts))
        entries = sorted(entries, key=_decision_entry_sort_key)
        previous = history[-1] if history else {}
        delta = _decision_delta(previous, entries)
        return AIMarketsDecisionSnapshot(
            _decision_snapshot_id(entries),
            _now_iso(),
            config_path is not None,
            str(config_path) if config_path else None,
            entries,
            delta,
            {"entry_paths": [str(path) for path in paths]},
            [
                "Decision Journal is deterministic research memory only.",
                "No financial advice, trading recommendation, provider calls, LLM inference, embeddings, semantic similarity, web retrieval, calendar integration, or autonomous decisions are used.",
            ],
        )


class AIMarketsDecisionJournalStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "outputs" / "ai-markets" / "decisions"
        self.json_path = self.directory / "decision-journal.json"
        self.report_path = self.directory / "decision-journal.md"
        self.entries_path = self.directory / "decision-entries.json"
        self.timeline_path = self.directory / "decision-timeline.md"
        self.queue_json_path = self.directory / "decision-review-queue.json"
        self.queue_path = self.directory / "decision-review-queue.md"
        self.links_path = self.directory / "decision-links.json"
        self.outcomes_path = self.directory / "decision-outcomes.json"
        self.history_path = self.directory / "decision-history.json"
        self.delta_path = self.directory / "decision-delta.json"

    def build(self) -> AIMarketsDecisionSnapshot:
        snapshot = AIMarketsDecisionJournalEngine(self.root).build(self.history())
        self.save(snapshot)
        return snapshot

    def load(self) -> JsonMap:
        if not self.json_path.exists():
            raise AIMarketsError("No AI & Markets decision journal found. Run `python -m constellation ai-markets decisions` first.")
        return read_json(self.json_path)

    def history(self) -> list[JsonMap]:
        if not self.history_path.exists():
            return []
        return _map_list(read_json(self.history_path).get("snapshots", []))

    def save(self, snapshot: AIMarketsDecisionSnapshot) -> None:
        data = snapshot.to_dict()
        write_json(self.json_path, data)
        write_json(self.entries_path, {"entries": data["entries"]})
        write_json(self.queue_json_path, {"entries": [item for item in data["entries"] if _map(item.get("review")).get("review_status") in {"overdue", "due", "not_due", "no_review_date"}]})
        write_json(self.links_path, {"entries": [{"entry_id": item["entry_id"], "themes": item["related_themes"], "entities": item["related_entities"], "catalysts": item["related_catalysts"], "risks": item["related_risks"], "evidence": item["related_evidence_ids"]} for item in data["entries"]]})
        write_json(self.outcomes_path, {"outcomes": [{"entry_id": item["entry_id"], "outcome": item["outcome"]} for item in data["entries"]]})
        write_json(self.delta_path, data["delta"])
        history = self.history()
        if not history or history[-1].get("snapshot_id") != snapshot.snapshot_id:
            history.append(data)
        write_json(self.history_path, {"snapshots": history})
        self.report_path.write_text(render_decision_journal(snapshot), encoding="utf-8")
        self.queue_path.write_text(render_decision_queue(snapshot), encoding="utf-8")
        self.timeline_path.write_text(render_decision_timeline(snapshot), encoding="utf-8")

    def status(self) -> JsonMap:
        if not self.json_path.exists():
            return {"available": False, "report_path": str(self.report_path), "review_queue_path": str(self.queue_path)}
        data = self.load()
        return {
            "available": True,
            "snapshot_id": data.get("snapshot_id"),
            "config_available": data.get("config_available"),
            "entry_count": data.get("entry_count", 0),
            "open_decision_count": data.get("open_decision_count", 0),
            "monitoring_decision_count": data.get("monitoring_decision_count", 0),
            "reviewed_decision_count": data.get("reviewed_decision_count", 0),
            "due_review_count": data.get("due_review_count", 0),
            "overdue_review_count": data.get("overdue_review_count", 0),
            "linked_theme_decision_count": data.get("linked_theme_decision_count", 0),
            "linked_entity_decision_count": data.get("linked_entity_decision_count", 0),
            "linked_catalyst_decision_count": data.get("linked_catalyst_decision_count", 0),
            "linked_risk_decision_count": data.get("linked_risk_decision_count", 0),
            "outcome_count": data.get("outcome_count", 0),
            "report_path": str(self.report_path),
            "review_queue_path": str(self.queue_path),
        }

    def create_template(self) -> Path:
        directory = self.root / "journal" / "ai-markets"
        directory.mkdir(parents=True, exist_ok=True)
        path = directory / "decision-template.md"
        if not path.exists():
            path.write_text(_decision_template_text(), encoding="utf-8")
        return path


@dataclass(frozen=True)
class AIMarketsExecutiveBriefSection:
    title: str
    items: list[str]

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AIMarketsResearchAgendaItem:
    agenda_id: str
    title: str
    priority: str
    reason: str
    source_type: str
    related_themes: list[str]
    related_entities: list[str]
    related_catalysts: list[str]
    related_decisions: list[str]
    related_risks: list[str]
    source_paths: list[str]
    provenance: JsonMap

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AIMarketsMorningPriority:
    priority_id: str
    title: str
    priority: str
    reason: str

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AIMarketsBriefDelta:
    new_agenda_items: list[str]
    removed_agenda_items: list[str]
    priority_changes: list[JsonMap]
    catalyst_count_change: int
    decision_review_count_change: int
    portfolio_review_count_change: int
    lifecycle_count_change: int
    source_artifact_availability_changes: list[str]

    def to_dict(self) -> JsonMap:
        return self.__dict__.copy()


@dataclass(frozen=True)
class AIMarketsBriefSnapshot:
    brief_id: str
    created_at: str
    version: str
    available: bool
    source_artifacts_available: list[str]
    source_artifacts_missing: list[str]
    research_agenda: list[AIMarketsResearchAgendaItem]
    morning_priorities: list[AIMarketsMorningPriority]
    delta: AIMarketsBriefDelta
    sections: list[AIMarketsExecutiveBriefSection]
    metrics: JsonMap
    output_paths: JsonMap
    provenance: JsonMap
    limitations: list[str]

    def to_dict(self) -> JsonMap:
        return {
            "brief_id": self.brief_id,
            "created_at": self.created_at,
            "version": self.version,
            "available": self.available,
            "source_artifacts_available": self.source_artifacts_available,
            "source_artifacts_missing": self.source_artifacts_missing,
            "ai_markets_available": "ai_markets" in self.source_artifacts_available,
            "lifecycle_available": "lifecycle" in self.source_artifacts_available,
            "portfolio_available": "portfolio" in self.source_artifacts_available,
            "catalyst_monitor_available": "catalysts" in self.source_artifacts_available,
            "decision_journal_available": "decisions" in self.source_artifacts_available,
            "dashboard_available": "dashboard" in self.source_artifacts_available,
            "report_available": "report" in self.source_artifacts_available,
            "research_agenda": [item.to_dict() for item in self.research_agenda],
            "research_agenda_count": len(self.research_agenda),
            "high_priority_agenda_count": sum(1 for item in self.research_agenda if item.priority == "high"),
            "medium_priority_count": sum(1 for item in self.research_agenda if item.priority == "medium"),
            "low_priority_count": sum(1 for item in self.research_agenda if item.priority == "low"),
            "top_agenda_items": [item.title for item in self.research_agenda[:5]],
            "top_priorities": [item.to_dict() for item in self.research_agenda[:5]],
            "top_priority_count": min(5, len(self.research_agenda)),
            "remaining_high_priority_count": max(0, sum(1 for item in self.research_agenda if item.priority == "high") - sum(1 for item in self.research_agenda[:5] if item.priority == "high")),
            "morning_priorities": [item.to_dict() for item in self.morning_priorities],
            "morning_priority_count": len(self.morning_priorities),
            "delta": self.delta.to_dict(),
            "sections": [item.to_dict() for item in self.sections],
            **self.metrics,
            "output_paths": self.output_paths,
            "provenance": self.provenance,
            "limitations": self.limitations,
        }


@dataclass(frozen=True)
class AIMarketsExecutiveBrief:
    snapshot: AIMarketsBriefSnapshot

    def to_dict(self) -> JsonMap:
        return self.snapshot.to_dict()


class AIMarketsBriefEngine:
    def __init__(self, root: Path) -> None:
        self.root = root

    def build(self, history: list[JsonMap]) -> AIMarketsBriefSnapshot:
        artifacts = _brief_artifacts(self.root)
        available = sorted(name for name, value in artifacts.items() if value)
        missing = sorted(name for name, value in artifacts.items() if not value)
        agenda = sorted(_brief_agenda(artifacts, missing), key=_agenda_sort_key)
        priorities = _brief_priorities(agenda)
        metrics = _brief_metrics(artifacts, agenda)
        delta = _brief_delta(history[-1] if history else {}, agenda, metrics, available, missing)
        sections = _brief_sections(artifacts, agenda, metrics, missing)
        limitations = [
            "Executive Morning Brief is deterministic and uses local artifacts only.",
            "No web retrieval, external market data, financial advice, trading recommendations, or autonomous decisions are produced.",
        ]
        if _brief_needs_reauth_warning(artifacts):
            limitations.append("Google Drive requires re-authentication; this brief was generated from existing local artifacts.")
        return AIMarketsBriefSnapshot(
            _brief_id(agenda, metrics, available, missing),
            _now_iso(),
            __version__,
            True,
            available,
            missing,
            agenda,
            priorities,
            delta,
            sections,
            metrics,
            {"brief_path": "outputs/ai-markets/briefings/morning-brief.md", "agenda_path": "outputs/ai-markets/briefings/research-agenda.md"},
            {"consumed_artifacts": {key: str(value) for key, value in BRIEF_INPUTS.items()}},
            limitations,
        )


class AIMarketsBriefStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "outputs" / "ai-markets" / "briefings"
        self.json_path = self.directory / "morning-brief.json"
        self.report_path = self.directory / "morning-brief.md"
        self.agenda_json_path = self.directory / "research-agenda.json"
        self.agenda_path = self.directory / "research-agenda.md"
        self.history_path = self.directory / "brief-history.json"
        self.delta_path = self.directory / "brief-delta.json"

    def build(self) -> AIMarketsBriefSnapshot:
        snapshot = AIMarketsBriefEngine(self.root).build(self.history())
        self.save(snapshot)
        return snapshot

    def load(self) -> JsonMap:
        if not self.json_path.exists():
            raise AIMarketsError("No AI & Markets executive brief found. Run `python -m constellation ai-markets brief` first.")
        return read_json(self.json_path)

    def history(self) -> list[JsonMap]:
        if not self.history_path.exists():
            return []
        return _map_list(read_json(self.history_path).get("snapshots", []))

    def save(self, snapshot: AIMarketsBriefSnapshot) -> None:
        data = snapshot.to_dict()
        write_json(self.json_path, data)
        write_json(self.agenda_json_path, {"research_agenda": [item.to_dict() for item in snapshot.research_agenda]})
        write_json(self.delta_path, snapshot.delta.to_dict())
        history = self.history()
        if not history or history[-1].get("brief_id") != snapshot.brief_id:
            history.append(data)
        write_json(self.history_path, {"snapshots": history})
        self.report_path.write_text(render_executive_brief(snapshot), encoding="utf-8")
        self.agenda_path.write_text(render_research_agenda(snapshot), encoding="utf-8")

    def status(self) -> JsonMap:
        if not self.json_path.exists():
            return {"available": False, "brief_path": str(self.report_path), "agenda_path": str(self.agenda_path)}
        data = self.load()
        return {
            "available": True,
            "brief_id": data.get("brief_id"),
            "theme_count": data.get("theme_count", 0),
            "watchlist_count": data.get("watchlist_count", 0),
            "total_catalyst_count": data.get("total_catalyst_count", 0),
            "high_priority_catalyst_count": data.get("high_priority_catalyst_count", 0),
            "open_decision_count": data.get("open_decision_count", 0),
            "due_review_count": data.get("due_review_count", 0),
            "overdue_review_count": data.get("overdue_review_count", 0),
            "research_agenda_count": data.get("research_agenda_count", 0),
            "high_priority_agenda_count": data.get("high_priority_agenda_count", 0),
            "top_priority_count": data.get("top_priority_count", 0),
            "remaining_high_priority_count": data.get("remaining_high_priority_count", 0),
            "medium_priority_count": data.get("medium_priority_count", 0),
            "low_priority_count": data.get("low_priority_count", 0),
            "brief_path": str(self.report_path),
            "agenda_path": str(self.agenda_path),
        }


class AIMarketsEngine:
    def __init__(self, root: Path) -> None:
        self.root = root

    def build(self) -> AIMarketsReport:
        artifacts = {name: _read_optional_json(self.root / path) for name, path in INPUTS.items() if path.suffix == ".json"}
        records = _records(artifacts)
        themes = _themes(records)
        entities = _entities(records, themes)
        catalysts = _catalysts(records)
        risks = _risks(records)
        questions = _questions(records)
        executive_questions = _executive_questions(questions)
        themes = _attach_related(themes, entities, catalysts, risks, questions)
        evidence_refs = sorted({record["evidence_id"] for record in records if record.get("evidence_id")})
        missing = [name for name, path in INPUTS.items() if not (self.root / path).exists()]
        limitations = [
            "AI & Markets Intelligence uses deterministic keyword and ticker matching only.",
            "No investment advice, trading recommendation, prediction, or autonomous decision is produced.",
        ]
        if missing:
            limitations.append("Unavailable artifacts: " + ", ".join(sorted(missing)) + ".")
        report_id = _report_id(themes, entities, catalysts, risks, questions, evidence_refs)
        return AIMarketsReport(
            report_id=report_id,
            created_at=_now_iso(),
            version=__version__,
            themes=themes,
            entities=entities,
            catalysts=catalysts,
            risks=risks,
            open_questions=questions,
            executive_questions=executive_questions,
            evidence_references=evidence_refs,
            provenance={name: str(path) for name, path in INPUTS.items()},
            limitations=limitations,
        )


class AIMarketsStore:
    def __init__(self, root: Path) -> None:
        self.root = root
        self.directory = root / "outputs" / "ai-markets"
        self.json_path = self.directory / "ai-markets.json"
        self.report_path = self.directory / "ai-markets-report.md"
        self.watchlist_path = self.directory / "watchlist.md"
        self.content_ideas_path = self.directory / "content-ideas.md"
        self.executive_questions_path = self.directory / "executive-questions.md"

    def build(self) -> AIMarketsReport:
        report = AIMarketsEngine(self.root).build()
        self.save(report)
        return report

    def save(self, report: AIMarketsReport) -> None:
        write_json(self.json_path, report.to_dict())
        write_json(self.directory / "themes.json", {"themes": [item.to_dict() for item in report.themes]})
        write_json(self.directory / "entities.json", {"entities": [item.to_dict() for item in report.entities]})
        write_json(self.directory / "catalysts.json", {"catalysts": [item.to_dict() for item in report.catalysts]})
        write_json(self.directory / "risks.json", {"risks": [item.to_dict() for item in report.risks]})
        write_json(self.directory / "open-questions.json", {"open_questions": [item.to_dict() for item in report.open_questions]})
        write_json(self.directory / "executive-questions.json", {"executive_questions": [item.to_dict() for item in report.executive_questions]})
        lifecycle = AIMarketsThemeLifecycleStore(self.root).build(report)
        portfolio = AIMarketsPortfolioStore(self.root).build(report, lifecycle)
        catalyst_monitor = AIMarketsCatalystStore(self.root).build(report, lifecycle, portfolio)
        decision_journal = AIMarketsDecisionJournalStore(self.root).build()
        executive_brief = AIMarketsBriefStore(self.root).build()
        report_data = report.to_dict()
        report_data["theme_lifecycle"] = lifecycle.to_dict()
        report_data["portfolio_intelligence"] = portfolio.to_dict()
        report_data["catalyst_monitor"] = catalyst_monitor.to_dict()
        report_data["decision_journal"] = decision_journal.to_dict()
        report_data["executive_brief"] = executive_brief.to_dict()
        write_json(self.json_path, report_data)
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(render_report(report, lifecycle, portfolio, catalyst_monitor, decision_journal, executive_brief), encoding="utf-8")
        self.watchlist_path.write_text(render_watchlist(report, portfolio, catalyst_monitor), encoding="utf-8")
        self.content_ideas_path.write_text(render_content_ideas(report), encoding="utf-8")
        self.executive_questions_path.write_text(render_executive_questions(report), encoding="utf-8")

    def load(self) -> AIMarketsReport:
        if not self.json_path.exists():
            raise AIMarketsError("No AI & Markets report found. Run `python -m constellation ai-markets build` first.")
        return AIMarketsReport.from_dict(read_json(self.json_path))

    def status(self) -> JsonMap:
        exists = self.json_path.exists()
        report = self.load() if exists else None
        lifecycle_status = AIMarketsThemeLifecycleStore(self.root).status()
        portfolio_status = AIMarketsPortfolioStore(self.root).status()
        catalyst_status = AIMarketsCatalystStore(self.root).status()
        decision_status = AIMarketsDecisionJournalStore(self.root).status()
        brief_status = AIMarketsBriefStore(self.root).status()
        return {
            "available": exists,
            "report_id": report.report_id if report else None,
            "theme_count": len(report.themes) if report else 0,
            "entity_count": len(report.entities) if report else 0,
            "high_confidence_entity_count": sum(1 for entity in report.entities if entity.evidence_count >= 4) if report else 0,
            "risk_count": len(report.risks) if report else 0,
            "total_open_question_count": _total_open_question_count(report) if report else 0,
            "deduplicated_open_question_count": len(report.open_questions) if report else 0,
            "executive_question_count": len(report.executive_questions) if report else 0,
            "report_path": str(self.report_path),
            "executive_questions_path": str(self.executive_questions_path),
            "lifecycle_available": lifecycle_status.get("available", False),
            "theme_lifecycle_report_path": lifecycle_status.get("report_path"),
            "portfolio_intelligence_available": portfolio_status.get("available", False),
            "portfolio_mode": portfolio_status.get("mode"),
            "position_count": portfolio_status.get("position_count", 0),
            "watchlist_count": portfolio_status.get("watchlist_count", 0),
            "portfolio_theme_exposure_count": portfolio_status.get("theme_exposure_count", 0),
            "portfolio_risk_count": portfolio_status.get("risk_count", 0),
            "high_priority_review_count": portfolio_status.get("high_priority_review_count", 0),
            "portfolio_report_path": portfolio_status.get("report_path"),
            "catalyst_monitor_available": catalyst_status.get("available", False),
            "total_catalyst_count": catalyst_status.get("total_catalyst_count", 0),
            "high_priority_catalyst_count": catalyst_status.get("high_priority_catalyst_count", 0),
            "near_term_catalyst_count": catalyst_status.get("near_term_catalyst_count", 0),
            "portfolio_linked_catalyst_count": catalyst_status.get("portfolio_linked_catalyst_count", 0),
            "risk_linked_catalyst_count": catalyst_status.get("risk_linked_catalyst_count", 0),
            "new_catalyst_count": catalyst_status.get("new_catalyst_count", 0),
            "stale_catalyst_count": catalyst_status.get("stale_catalyst_count", 0),
            "catalyst_monitor_report_path": catalyst_status.get("report_path"),
            "catalyst_calendar_path": catalyst_status.get("calendar_path"),
            "decision_journal_available": decision_status.get("available", False),
            "decision_entry_count": decision_status.get("entry_count", 0),
            "open_decision_count": decision_status.get("open_decision_count", 0),
            "due_review_count": decision_status.get("due_review_count", 0),
            "overdue_review_count": decision_status.get("overdue_review_count", 0),
            "outcome_count": decision_status.get("outcome_count", 0),
            "decision_journal_report_path": decision_status.get("report_path"),
            "decision_review_queue_path": decision_status.get("review_queue_path"),
            "executive_brief_available": brief_status.get("available", False),
            "executive_brief_id": brief_status.get("brief_id"),
            "executive_brief_path": brief_status.get("brief_path"),
            "research_agenda_path": brief_status.get("agenda_path"),
            "research_agenda_count": brief_status.get("research_agenda_count", 0),
            "high_priority_agenda_count": brief_status.get("high_priority_agenda_count", 0),
        }

    def export(self) -> Path:
        report = self.load()
        lifecycle = AIMarketsThemeLifecycleStore(self.root).build(report)
        portfolio = AIMarketsPortfolioStore(self.root).build(report, lifecycle)
        catalyst_monitor = AIMarketsCatalystStore(self.root).build(report, lifecycle, portfolio)
        decision_journal = AIMarketsDecisionJournalStore(self.root).build()
        executive_brief = AIMarketsBriefStore(self.root).build()
        self.report_path.write_text(render_report(report, lifecycle, portfolio, catalyst_monitor, decision_journal, executive_brief), encoding="utf-8")
        self.watchlist_path.write_text(render_watchlist(report, portfolio, catalyst_monitor), encoding="utf-8")
        self.content_ideas_path.write_text(render_content_ideas(report), encoding="utf-8")
        self.executive_questions_path.write_text(render_executive_questions(report), encoding="utf-8")
        return self.report_path


def render_report(report: AIMarketsReport, lifecycle: AIMarketsThemeLifecycleSnapshot | None = None, portfolio: AIMarketsPortfolioSnapshot | None = None, catalyst_monitor: AIMarketsCatalystSnapshot | None = None, decision_journal: AIMarketsDecisionSnapshot | None = None, executive_brief: AIMarketsBriefSnapshot | None = None) -> str:
    lines = [
        "# AI & Markets Intelligence",
        "",
        f"- Report ID: `{report.report_id}`",
        f"- Created: `{report.created_at}`",
        f"- Version: `{report.version}`",
        "",
        "## Executive Summary",
        "",
        f"- Themes: {len(report.themes)}",
        f"- Entities: {len(report.entities)}",
        f"- Catalysts: {len(report.catalysts)}",
        f"- Risks: {len(report.risks)}",
        f"- Total open question mentions: {_total_open_question_count(report)}",
        f"- Deduplicated open questions: {len(report.open_questions)}",
        f"- Executive questions: {len(report.executive_questions)}",
        "- Executive questions path: `outputs/ai-markets/executive-questions.md`",
        "- Full open question archive: `outputs/ai-markets/open-questions.json`",
        "",
        "## What Changed",
        "",
        *_bullet([item.description for item in report.catalysts[:8]] or ["No explicit catalysts found."]),
        "## Active Themes",
        "",
        *_bullet([f"{theme.name} ({theme.status}, {theme.confidence}) evidence={theme.evidence_count}" for theme in report.themes if theme.status == "active"]),
        "## Strengthening Themes",
        "",
        *_bullet([f"{theme.name} evidence={theme.evidence_count}" for theme in report.themes if theme.status == "strengthening"]),
        "## Key Companies / Assets",
        "",
        *_bullet([f"{entity.symbol} - {entity.name} ({entity.entity_type}) evidence={entity.evidence_count}" for entity in report.entities]),
        "## Catalysts",
        "",
        *_bullet([item.description for item in report.catalysts]),
        "## Risks",
        "",
        *_bullet([f"{item.description} ({item.severity})" for item in report.risks]),
        "## Top Executive Questions",
        "",
        *_bullet([f"{item.question} ({item.priority}, evidence={len(item.evidence_ids)}, themes={len(item.related_themes)})" for item in report.executive_questions[:5]] or ["No executive questions found."]),
        "## Theme Lifecycle",
        "",
        *_theme_lifecycle_report_lines(lifecycle),
        "## Portfolio Intelligence",
        "",
        *_portfolio_report_lines(portfolio),
        "## Catalyst Monitoring",
        "",
        *_catalyst_monitor_report_lines(catalyst_monitor),
        "## Decision Journal",
        "",
        *_decision_journal_report_lines(decision_journal),
        "## Executive Morning Brief",
        "",
        *_executive_brief_report_lines(executive_brief),
        "## Watchlist",
        "",
        *_bullet([entity.symbol for entity in report.entities]),
        "## Content Ideas",
        "",
        *_bullet(_content_ideas(report)),
        "## Evidence References",
        "",
        *_bullet(report.evidence_references[:50]),
        "## Provenance",
        "",
        *_bullet([f"{key}: {value}" for key, value in report.provenance.items()]),
        "## Limitations",
        "",
        *_bullet(report.limitations),
    ]
    return "\n".join(lines)


def render_watchlist(report: AIMarketsReport, portfolio: AIMarketsPortfolioSnapshot | None = None, catalyst_monitor: AIMarketsCatalystSnapshot | None = None) -> str:
    lines = ["# AI & Markets Watchlist", ""]
    lines.extend(_bullet([f"{entity.symbol} - {entity.name}: {', '.join(entity.related_themes) or 'No related theme'}" for entity in report.entities]))
    if portfolio:
        lines.extend(["## Portfolio Intelligence Watchlist", ""])
        lines.extend(_bullet([f"{item.symbol} - {item.name} ({item.source}) priority={item.research_priority}" for item in portfolio.positions + portfolio.watchlist + portfolio.detected_entities]))
    if catalyst_monitor:
        lines.extend(["## Catalyst Watchlist", ""])
        lines.extend(_bullet([f"{item.title} ({item.priority}, {item.time_horizon})" for item in catalyst_monitor.catalysts[:20]]))
    return "\n".join(lines)


def render_content_ideas(report: AIMarketsReport) -> str:
    lines = ["# AI & Markets Content Ideas", ""]
    lines.extend(_bullet(_content_ideas(report)))
    return "\n".join(lines)


def render_executive_questions(report: AIMarketsReport) -> str:
    lines = [
        "# AI & Markets Executive Questions",
        "",
        f"- Report ID: `{report.report_id}`",
        f"- Total open question mentions: {_total_open_question_count(report)}",
        f"- Deduplicated open questions: {len(report.open_questions)}",
        f"- Executive questions: {len(report.executive_questions)}",
        "",
    ]
    for index, question in enumerate(report.executive_questions, start=1):
        lines.extend(
            [
                f"## {index}. {question.question}",
                "",
                f"- Priority: {question.priority}",
                f"- Evidence records: {len(question.evidence_ids)}",
                f"- Related themes: {', '.join(question.related_themes) or 'None'}",
                f"- Source IDs: {', '.join(question.source_ids) or 'None'}",
                "",
            ]
        )
    if not report.executive_questions:
        lines.extend(["No executive questions found.", ""])
    return "\n".join(lines)


def render_theme_lifecycle(snapshot: AIMarketsThemeLifecycleSnapshot) -> str:
    data = snapshot.to_dict()
    lines = [
        "# AI & Markets Theme Lifecycle",
        "",
        f"- Snapshot ID: `{snapshot.snapshot_id}`",
        f"- Created: `{snapshot.created_at}`",
        f"- Theme count: {len(snapshot.themes)}",
        "",
    ]
    lines.extend(_theme_lifecycle_report_lines(snapshot))
    lines.extend(["## Recent Theme Transitions", ""])
    transitions = _map_list(data.get("transitions", []))
    lines.extend(_bullet([f"{item.get('theme_name')} {item.get('transition_type')}: {item.get('reason')}" for item in transitions[:20]] or ["No recent theme transitions."]))
    lines.extend(["## Lifecycle Limitations", ""])
    lines.extend(_bullet(snapshot.limitations))
    return "\n".join(lines)


def render_theme_timeline(history: list[JsonMap]) -> str:
    lines = ["# AI & Markets Theme Timeline", ""]
    for snapshot in reversed(history[-20:]):
        lines.extend([f"## {snapshot.get('snapshot_id', '')}", "", f"- Created: `{snapshot.get('created_at', '')}`", f"- Themes: {snapshot.get('theme_count', 0)}", ""])
        for transition in _map_list(snapshot.get("transitions", []))[:20]:
            lines.append(f"- {transition.get('theme_name')} {transition.get('transition_type')}: {transition.get('previous_value')} -> {transition.get('current_value')}")
        lines.append("")
    if not history:
        lines.extend(["No lifecycle history recorded.", ""])
    return "\n".join(lines)


def render_portfolio_report(snapshot: AIMarketsPortfolioSnapshot) -> str:
    data = snapshot.to_dict()
    lines = [
        "# AI & Markets Portfolio Intelligence",
        "",
        "This is research organization only. This is not financial advice. No trading recommendations are generated.",
        "",
        "## Executive Summary",
        "",
        f"- Snapshot ID: `{snapshot.snapshot_id}`",
        f"- Mode: {snapshot.mode}",
        f"- Config available: {snapshot.config_available}",
        f"- Positions: {len(snapshot.positions)}",
        f"- Watchlist items: {len(snapshot.watchlist)}",
        f"- Detected entities: {len(snapshot.detected_entities)}",
        f"- Theme exposures: {len(snapshot.exposures)}",
        f"- Portfolio-linked risks: {len(snapshot.risks)}",
        f"- High-priority reviews: {data.get('high_priority_review_count', 0)}",
        "",
        "## Portfolio / Watchlist Mode",
        "",
        f"- Mode: {snapshot.mode}",
        f"- Config path: {snapshot.config_path or 'Unavailable'}",
        "",
        "## Theme Exposure",
        "",
        *_bullet([f"{item.theme_name} ({item.lifecycle_status}) symbols={', '.join(item.related_symbols)} priority={item.research_priority}" for item in snapshot.exposures] or ["No theme exposures found."]),
        "## High-Priority Reviews",
        "",
        *_bullet([f"{item.symbol}: {item.priority_reason}" for item in snapshot.positions + snapshot.watchlist + snapshot.detected_entities if item.research_priority == "high"] or ["No high-priority reviews found."]),
        "## Entity / Asset Map",
        "",
        *_bullet([f"{item.symbol} - {item.name}: {', '.join(item.related_themes) or 'No related theme'}" for item in snapshot.positions + snapshot.watchlist + snapshot.detected_entities]),
        "## Lifecycle Exposure",
        "",
        *_bullet([f"{item.theme_name}: {item.lifecycle_status}, {item.confidence}" for item in snapshot.exposures]),
        "## Risk Map",
        "",
        *_bullet([f"{item.risk_id} ({item.priority}): {item.description}" for item in snapshot.risks] or ["No portfolio-linked risks found."]),
        "## Open Questions",
        "",
        *_bullet([f"{item.question_id} ({item.priority}): {item.question}" for item in snapshot.questions] or ["No portfolio-linked questions found."]),
        "## Watchlist",
        "",
        *_bullet([item.symbol for item in snapshot.watchlist + snapshot.detected_entities]),
        "## Recent Changes",
        "",
        *_bullet(_portfolio_delta_lines(snapshot.delta)),
        "## Evidence References",
        "",
        *_bullet(sorted({evidence for item in snapshot.risks for evidence in item.evidence_ids})[:50] or ["No linked evidence IDs found."]),
        "## Limitations",
        "",
        *_bullet(snapshot.limitations),
        "## Provenance",
        "",
        *_bullet([f"{key}: {value}" for key, value in snapshot.provenance.items()]),
    ]
    return "\n".join(lines)


def render_portfolio_exposures(snapshot: AIMarketsPortfolioSnapshot) -> str:
    lines = ["# AI & Markets Portfolio Exposures", ""]
    lines.extend(_bullet([f"{item.theme_name} ({item.lifecycle_status}) symbols={', '.join(item.related_symbols)} priority={item.research_priority}" for item in snapshot.exposures] or ["No theme exposures found."]))
    return "\n".join(lines)


def render_portfolio_risks(snapshot: AIMarketsPortfolioSnapshot) -> str:
    lines = ["# AI & Markets Portfolio Risks", ""]
    lines.extend(_bullet([f"{item.risk_id} severity={item.severity} priority={item.priority} symbols={', '.join(item.related_symbols)} description={item.description}" for item in snapshot.risks] or ["No portfolio-linked risks found."]))
    return "\n".join(lines)


def render_portfolio_watchlist(snapshot: AIMarketsPortfolioSnapshot) -> str:
    lines = ["# AI & Markets Portfolio Watchlist", ""]
    lines.extend(_bullet([f"{item.symbol} - {item.name} ({item.source}) priority={item.research_priority}" for item in snapshot.positions + snapshot.watchlist + snapshot.detected_entities]))
    return "\n".join(lines)


def render_portfolio_questions(snapshot: AIMarketsPortfolioSnapshot) -> str:
    lines = ["# AI & Markets Portfolio Questions", ""]
    lines.extend(_bullet([f"{item.question_id} priority={item.priority} symbols={', '.join(item.related_symbols)} question={item.question}" for item in snapshot.questions] or ["No portfolio-linked questions found."]))
    return "\n".join(lines)


def render_catalyst_monitor(snapshot: AIMarketsCatalystSnapshot) -> str:
    data = snapshot.to_dict()
    lines = [
        "# AI & Markets Catalyst Monitor",
        "",
        "This is deterministic research organization only. It is not financial advice, market prediction, autonomous monitoring, or trading software.",
        "",
        "## Executive Summary",
        "",
        f"- Snapshot ID: `{snapshot.snapshot_id}`",
        f"- Total catalysts: {len(snapshot.catalysts)}",
        f"- High-priority catalysts: {data.get('high_priority_catalyst_count', 0)}",
        f"- Portfolio/watchlist-linked catalysts: {data.get('portfolio_linked_catalyst_count', 0)}",
        f"- Risk-linked catalysts: {data.get('risk_linked_catalyst_count', 0)}",
        f"- New catalysts: {data.get('new_catalyst_count', 0)}",
        f"- Stale catalysts: {data.get('stale_catalyst_count', 0)}",
        "",
        "## High-Priority Catalysts",
        "",
        *_bullet([f"{item.title} ({item.category}, {item.time_horizon}) - {item.priority_reason}" for item in snapshot.catalysts if item.priority == "high"] or ["No high-priority catalysts found."]),
        "## Catalyst Calendar / Time Horizon",
        "",
        *_catalyst_calendar_lines(snapshot),
        "## Theme-Linked Catalysts",
        "",
        *_bullet([f"{item.title}: {', '.join(item.related_themes)}" for item in snapshot.catalysts if item.related_themes] or ["No theme-linked catalysts found."]),
        "## Watchlist / Portfolio-Linked Catalysts",
        "",
        *_bullet([f"{item.title}: {', '.join(sorted(set(item.related_watchlist_symbols + item.related_portfolio_symbols)))}" for item in snapshot.catalysts if item.related_watchlist_symbols or item.related_portfolio_symbols] or ["No watchlist or portfolio-linked catalysts found."]),
        "## Risk-Linked Catalysts",
        "",
        *_bullet([f"{item.title}: {', '.join(item.related_risks)}" for item in snapshot.catalysts if item.related_risks] or ["No risk-linked catalysts found."]),
        "## New Catalysts",
        "",
        *_bullet(snapshot.delta.new_catalysts or ["No new catalysts."]),
        "## Stale or Resolved Catalysts",
        "",
        *_bullet([item.title for item in snapshot.catalysts if item.status in {"stale", "resolved"}] or ["No stale or resolved catalysts."]),
        "## Recent Catalyst Changes",
        "",
        *_bullet([f"{item.transition_type}: {item.catalyst_id}" for item in snapshot.transitions[:20]] or ["No recent catalyst changes."]),
        "## Evidence References",
        "",
        *_bullet(sorted({evidence for item in snapshot.catalysts for evidence in item.evidence_ids})[:50] or ["No linked evidence IDs found."]),
        "## Limitations",
        "",
        *_bullet(snapshot.limitations),
        "## Provenance",
        "",
        *_bullet([f"{key}: {value}" for key, value in snapshot.provenance.items()]),
    ]
    return "\n".join(lines)


def render_catalyst_priorities(snapshot: AIMarketsCatalystSnapshot) -> str:
    lines = ["# AI & Markets Catalyst Priorities", ""]
    lines.extend(_bullet([f"{item.priority}: {item.title} ({item.category}) - {item.priority_reason}" for item in snapshot.catalysts if item.priority in {"high", "medium"}] or ["No high or medium priority catalysts found."]))
    return "\n".join(lines)


def render_catalyst_calendar(snapshot: AIMarketsCatalystSnapshot) -> str:
    return "\n".join(["# AI & Markets Catalyst Calendar", "", *_catalyst_calendar_lines(snapshot)])


def render_decision_journal(snapshot: AIMarketsDecisionSnapshot) -> str:
    data = snapshot.to_dict()
    lines = [
        "# AI & Markets Decision Journal",
        "",
        "This is deterministic research memory only. This is not financial advice, trading software, or an autonomous decision maker.",
        "",
        "## Executive Summary",
        "",
        f"- Snapshot ID: `{snapshot.snapshot_id}`",
        f"- Entries: {len(snapshot.entries)}",
        f"- Open decisions: {data.get('open_decision_count', 0)}",
        f"- Due reviews: {data.get('due_review_count', 0)}",
        f"- Overdue reviews: {data.get('overdue_review_count', 0)}",
        f"- Outcomes recorded: {data.get('outcome_count', 0)}",
        "",
        "## Journal Mode / Config Status",
        "",
        f"- Config available: {snapshot.config_available}",
        f"- Config path: {snapshot.config_path or 'Unavailable'}",
        "",
        "## Open Decisions",
        "",
        *_bullet([f"{item.title} ({item.review.review_status})" for item in snapshot.entries if item.status == "open"] or ["No open decisions."]),
        "## Review Queue",
        "",
        *_decision_queue_lines(snapshot),
        "## Overdue Reviews",
        "",
        *_bullet([item.title for item in snapshot.entries if item.review.review_status == "overdue"] or ["No overdue reviews."]),
        "## Theme-Linked Decisions",
        "",
        *_bullet([f"{item.title}: {', '.join(item.related_themes)}" for item in snapshot.entries if item.related_themes] or ["No theme-linked decisions."]),
        "## Entity / Watchlist-Linked Decisions",
        "",
        *_bullet([f"{item.title}: {', '.join(item.related_entities)}" for item in snapshot.entries if item.related_entities] or ["No entity-linked decisions."]),
        "## Catalyst-Linked Decisions",
        "",
        *_bullet([f"{item.title}: {', '.join(item.related_catalysts)}" for item in snapshot.entries if item.related_catalysts] or ["No catalyst-linked decisions."]),
        "## Risk-Linked Decisions",
        "",
        *_bullet([f"{item.title}: {', '.join(item.related_risks)}" for item in snapshot.entries if item.related_risks] or ["No risk-linked decisions."]),
        "## Outcomes / Lessons",
        "",
        *_bullet([f"{item.title}: {item.outcome.status}" for item in snapshot.entries if item.outcome.status != "no_outcome_recorded"] or ["No outcomes recorded."]),
        "## Recent Changes",
        "",
        *_bullet(_decision_delta_lines(snapshot.delta)),
        "## Evidence / Provenance Links",
        "",
        *_bullet(sorted({evidence for item in snapshot.entries for evidence in item.related_evidence_ids}) or ["No evidence links."]),
        "## Limitations",
        "",
        *_bullet(snapshot.limitations),
        "## Safety Statement",
        "",
        "- Decision Journal preserves user-provided research memory and does not generate financial advice or trading recommendations.",
        "",
    ]
    return "\n".join(lines)


def render_decision_queue(snapshot: AIMarketsDecisionSnapshot) -> str:
    return "\n".join(["# AI & Markets Decision Review Queue", "", *_decision_queue_lines(snapshot)])


def render_decision_timeline(snapshot: AIMarketsDecisionSnapshot) -> str:
    lines = ["# AI & Markets Decision Timeline", ""]
    timeline = sorted(snapshot.entries, key=lambda item: (_date_sort_key(item.created_at, descending=True), item.title, item.entry_id))
    lines.extend(_bullet([f"{item.created_at}: {item.title} ({item.status})" for item in timeline] or ["No decision entries."]))
    return "\n".join(lines)


def render_executive_brief(snapshot: AIMarketsBriefSnapshot) -> str:
    data = snapshot.to_dict()
    top_priorities = _map_list(data.get("top_priorities", []))
    lines = [
        "# AI & Markets Executive Morning Brief",
        "",
        f"- Brief ID: `{snapshot.brief_id}`",
        f"- Generated: `{snapshot.created_at}`",
        f"- Version: `{snapshot.version}`",
        f"- Source artifacts available: {len(snapshot.source_artifacts_available)}",
        f"- Source artifacts missing: {len(snapshot.source_artifacts_missing)}",
        "",
        "## Executive Summary",
        "",
        f"- Themes: {data.get('theme_count', 0)}",
        f"- Watchlist items: {data.get('watchlist_count', 0)}",
        f"- Catalysts: {data.get('total_catalyst_count', 0)}",
        f"- Open decisions: {data.get('open_decision_count', 0)}",
        f"- Research agenda items: {data.get('research_agenda_count', 0)}",
        f"- Top priorities: {data.get('top_priority_count', 0)}",
        f"- Remaining high priority: {data.get('remaining_high_priority_count', 0)}",
        f"- Medium priority: {data.get('medium_priority_count', 0)}",
        f"- Low priority: {data.get('low_priority_count', 0)}",
        f"- Full agenda: `outputs/ai-markets/briefings/research-agenda.md`",
        "",
        "## Top 5 Priorities",
        "",
    ]
    if not top_priorities:
        lines.extend(["- No executive priorities currently identified.", ""])
    for index, item in enumerate(top_priorities[:5], start=1):
        lines.extend(
            [
                f"### {index}. {_clean_brief_text(str(item.get('title') or 'Unclassified Review'))}",
                "",
                f"- Type: {_clean_brief_text(str(item.get('source_type') or 'unknown')).replace('_', ' ').title()}",
                f"- Priority: {str(item.get('priority', '')).title()}",
                f"- Reason: {_clean_brief_text(str(item.get('reason') or 'Priority selected by deterministic rule.'))}",
                f"- Related themes: {', '.join(_string_list(item.get('related_themes', []))) or 'None'}",
                f"- Related entities: {', '.join(_string_list(item.get('related_entities', []))) or 'None'}",
                f"- Related catalyst or risk: {', '.join(_string_list(item.get('related_catalysts', [])) + _string_list(item.get('related_risks', []))) or 'None'}",
                f"- Source: {', '.join(_string_list(item.get('source_paths', []))) or 'None'}",
                "",
            ]
        )
    for section in snapshot.sections:
        lines.extend([f"## {section.title}", ""])
        lines.extend(_bullet(section.items or ["No items."]))
    lines.extend(["## Limitations", ""])
    lines.extend(_bullet(snapshot.limitations))
    lines.extend(["## Provenance", ""])
    lines.extend(_bullet([f"{key}: {value}" for key, value in snapshot.provenance.get("consumed_artifacts", {}).items()]))
    lines.extend(["## Appendix", ""])
    lines.extend(_appendix_lines(snapshot))
    return "\n".join(lines)


def render_research_agenda(snapshot: AIMarketsBriefSnapshot) -> str:
    return "\n".join(["# AI & Markets Research Agenda", "", *_agenda_markdown_lines(snapshot.research_agenda, snapshot.to_dict())])


def _agenda_markdown_lines(items: list[AIMarketsResearchAgendaItem], data: JsonMap | None = None) -> list[str]:
    lines: list[str] = []
    top_ids = {str(item.get("agenda_id")) for item in _map_list((data or {}).get("top_priorities", []))}
    top_items = [item for item in items if item.agenda_id in top_ids][:5]
    lines.extend(["## Top 5 Executive Priorities", ""])
    lines.extend(_agenda_item_lines(top_items) if top_items else ["- No executive priorities currently identified.", ""])
    for priority in ["high", "medium", "low"]:
        title = "Remaining High Priority" if priority == "high" else f"{priority.title()} Priority"
        lines.extend([f"## {title}", ""])
        group = [item for item in items if item.priority == priority and item.agenda_id not in top_ids]
        lines.extend(_agenda_item_lines(group) if group else [f"- No {title.lower()} agenda items.", ""])
    lines.extend(["## Appendix / Provenance", ""])
    lines.extend(_bullet([f"{item.agenda_id}: {', '.join(item.source_paths) or 'No source path'}" for item in items] or ["No agenda provenance."]))
    return lines


def _decision_queue_lines(snapshot: AIMarketsDecisionSnapshot) -> list[str]:
    lines: list[str] = []
    groups = [("overdue", "Overdue"), ("due", "Due"), ("not_due", "Upcoming"), ("no_review_date", "No Review Date"), ("reviewed", "Reviewed")]
    for status, title in groups:
        lines.extend([f"### {title}", ""])
        items = [item for item in snapshot.entries if item.review.review_status == status]
        lines.extend(_bullet([f"{item.title} review_at={item.review_at or 'None'}" for item in items] or [f"No {title.lower()} entries."]))
    return lines


def _catalyst_calendar_lines(snapshot: AIMarketsCatalystSnapshot) -> list[str]:
    lines: list[str] = []
    for horizon in ["immediate", "near_term", "medium_term", "long_term", "unknown"]:
        lines.extend([f"### {horizon}", ""])
        items = [item for item in snapshot.catalysts if item.time_horizon == horizon]
        lines.extend(_bullet([f"{item.title} ({item.priority})" for item in items] or [f"No {horizon} catalysts."]))
    return lines


def _theme_lifecycle_report_lines(lifecycle: AIMarketsThemeLifecycleSnapshot | None) -> list[str]:
    if lifecycle is None:
        return ["- Theme lifecycle has not been generated.", ""]
    groups = {
        "High Conviction Themes": "high_conviction",
        "Strengthening Themes": "strengthening",
        "Active Themes": "active",
        "Emerging Themes": "emerging",
        "Weakening Themes": "weakening",
        "Contradicted Themes": "contradicted",
        "Archived Themes": "archived",
    }
    lines: list[str] = []
    for title, status in groups.items():
        lines.extend([f"### {title}", ""])
        items = [theme for theme in lifecycle.themes if theme.get("current_status") == status]
        lines.extend(_bullet([f"{theme.get('theme_name')} evidence={theme.get('evidence_count')} sources={theme.get('source_count')} reason={theme.get('lifecycle_reason')}" for theme in items] or [f"No {title.lower()}."]))
    lines.extend(["### Recent Theme Transitions", ""])
    lines.extend(_bullet([f"{item.theme_name} {item.transition_type}: {item.reason}" for item in lifecycle.transitions[:10]] or ["No recent theme transitions."]))
    lines.extend(["### Lifecycle Limitations", ""])
    lines.extend(_bullet(lifecycle.limitations))
    return lines


def _portfolio_report_lines(portfolio: AIMarketsPortfolioSnapshot | None) -> list[str]:
    if portfolio is None:
        return ["- Portfolio Intelligence has not been generated.", ""]
    return [
        f"- Mode: {portfolio.mode}",
        f"- Config available: {portfolio.config_available}",
        f"- Positions: {len(portfolio.positions)}",
        f"- Watchlist items: {len(portfolio.watchlist)}",
        f"- Detected entities: {len(portfolio.detected_entities)}",
        f"- Theme exposures: {len(portfolio.exposures)}",
        f"- Portfolio-linked risks: {len(portfolio.risks)}",
        f"- High-priority reviews: {portfolio.to_dict().get('high_priority_review_count', 0)}",
        "- Portfolio report: `outputs/ai-markets/portfolio/portfolio-intelligence.md`",
        "",
    ]


def _catalyst_monitor_report_lines(snapshot: AIMarketsCatalystSnapshot | None) -> list[str]:
    if snapshot is None:
        return ["- Catalyst Monitoring has not been generated.", ""]
    data = snapshot.to_dict()
    return [
        f"- Total catalysts: {len(snapshot.catalysts)}",
        f"- High-priority catalysts: {data.get('high_priority_catalyst_count', 0)}",
        f"- Near-term catalysts: {data.get('near_term_catalyst_count', 0)}",
        f"- Portfolio/watchlist-linked catalysts: {data.get('portfolio_linked_catalyst_count', 0)}",
        f"- Risk-linked catalysts: {data.get('risk_linked_catalyst_count', 0)}",
        f"- New catalysts: {data.get('new_catalyst_count', 0)}",
        f"- Stale catalysts: {data.get('stale_catalyst_count', 0)}",
        "- Catalyst monitor: `outputs/ai-markets/catalysts/catalyst-monitor.md`",
        "- Catalyst calendar: `outputs/ai-markets/catalysts/catalyst-calendar.md`",
        "",
    ]


def _decision_journal_report_lines(snapshot: AIMarketsDecisionSnapshot | None) -> list[str]:
    if snapshot is None:
        return ["- Decision Journal has not been generated.", ""]
    data = snapshot.to_dict()
    return [
        f"- Entries: {data.get('entry_count', 0)}",
        f"- Open decisions: {data.get('open_decision_count', 0)}",
        f"- Due reviews: {data.get('due_review_count', 0)}",
        f"- Overdue reviews: {data.get('overdue_review_count', 0)}",
        f"- Outcomes recorded: {data.get('outcome_count', 0)}",
        "- Decision journal: `outputs/ai-markets/decisions/decision-journal.md`",
        "- Review queue: `outputs/ai-markets/decisions/decision-review-queue.md`",
        "",
    ]


def _executive_brief_report_lines(snapshot: AIMarketsBriefSnapshot | None) -> list[str]:
    if snapshot is None:
        return ["- Executive Morning Brief has not been generated.", ""]
    data = snapshot.to_dict()
    return [
        f"- Brief ID: `{snapshot.brief_id}`",
        f"- Research agenda items: {data.get('research_agenda_count', 0)}",
        f"- High-priority agenda items: {data.get('high_priority_agenda_count', 0)}",
        "- Brief path: `outputs/ai-markets/briefings/morning-brief.md`",
        "- Research agenda path: `outputs/ai-markets/briefings/research-agenda.md`",
        "",
    ]


def _records(artifacts: dict[str, JsonMap]) -> list[JsonMap]:
    records: list[JsonMap] = []
    for ref in _map_list(_map(artifacts.get("institutional_report")).get("evidence_references", [])):
        text = " ".join(str(ref.get(key, "")) for key in ["evidence_id", "source_id", "summary"])
        records.append({"evidence_id": str(ref.get("evidence_id", "")), "source": ref.get("source_id"), "text": text, "provenance": "outputs/reports/latest-report.json"})
    for node in _map_list(_map(artifacts.get("evidence_graph")).get("nodes", [])):
        if node.get("node_type") == "evidence":
            records.append({"evidence_id": str(node.get("metadata", {}).get("evidence_id") or node.get("evidence_id") or node.get("node_id")), "source": _first(_string_list(node.get("source_ids", []))), "text": " ".join(str(node.get(k, "")) for k in ["label", "description", "node_id"]), "provenance": "outputs/evidence-graph/evidence-graph.json"})
    for thesis in _map_list(_map(artifacts.get("thesis")).get("theses", [])):
        records.append({"evidence_id": str(thesis.get("thesis_id", "")), "source": _first(_string_list(thesis.get("source_ids", []))), "text": " ".join(str(thesis.get(k, "")) for k in ["title", "status", "category", "thesis_id"]), "provenance": "outputs/thesis/theses.json"})
    for section in _map_list(_map(artifacts.get("institutional_report")).get("sections", [])):
        records.append({"evidence_id": "", "source": "report_section", "text": " ".join([str(section.get("title", "")), str(section.get("summary", "")), " ".join(_string_list(section.get("items", [])))]), "provenance": "outputs/reports/latest-report.json"})
    for item in _string_list(_map(artifacts.get("dashboard")).get("current_risks_gaps", [])):
        records.append({"evidence_id": "", "source": "dashboard", "text": str(item), "provenance": "outputs/dashboard/dashboard.json"})
    for index, record in enumerate(records):
        record["record_index"] = index
    return records


def _themes(records: list[JsonMap]) -> list[AIMarketsTheme]:
    themes = []
    for name, keywords in THEME_KEYWORDS.items():
        matched = [record for record in records if _contains_any(str(record.get("text", "")), keywords)]
        if not matched:
            continue
        evidence_ids = sorted({str(record.get("evidence_id")) for record in matched if record.get("evidence_id")})
        sources = sorted({str(record.get("source")) for record in matched if record.get("source")})
        status = "strengthening" if len(evidence_ids) >= 4 or len(sources) >= 3 else "active" if len(evidence_ids) >= 2 or len(sources) >= 2 else "emerging"
        themes.append(
            AIMarketsTheme(
                theme_id=f"theme_{_digest(name)}",
                name=name,
                status=status,
                confidence=_confidence(len(evidence_ids), len(sources)),
                evidence_count=len(evidence_ids),
                source_count=len(sources),
                related_evidence_ids=evidence_ids,
                related_entities=[],
                risks=[],
                catalysts=[],
                open_questions=[],
                provenance={"matched_keywords": keywords, "sources": sources},
            )
        )
    return sorted(themes, key=lambda item: item.name)


def _entities(records: list[JsonMap], themes: list[AIMarketsTheme]) -> list[AIMarketsEntity]:
    entities = []
    for symbol, (name, entity_type) in ENTITY_MAP.items():
        matched = [record for record in records if _entity_match(str(record.get("text", "")), symbol)]
        if not matched:
            continue
        evidence_ids = sorted({str(record.get("evidence_id")) for record in matched if record.get("evidence_id")})
        related_themes = sorted(theme.name for theme in themes if set(theme.related_evidence_ids).intersection(evidence_ids) or _contains_any(" ".join(str(record.get("text", "")) for record in matched), THEME_KEYWORDS[theme.name]))
        matched_text = sorted({alias for record in matched for alias in _matched_aliases(str(record.get("text", "")), symbol)})
        sources = sorted({str(record.get("source")) for record in matched if record.get("source")})
        entities.append(AIMarketsEntity(f"entity_{symbol.lower()}", symbol, name, entity_type, related_themes, len(evidence_ids), _now_iso(), {"matched_symbol": symbol, "matched_text": matched_text, "sources": sources}))
    return sorted(entities, key=lambda item: item.symbol)


def _catalysts(records: list[JsonMap]) -> list[AIMarketsCatalyst]:
    results = []
    for record in records:
        text = str(record.get("text", ""))
        if _contains_any(text, CATALYST_WORDS):
            themes = _matched_themes(text)
            entities = _matched_entities(text)
            description = _short(text)
            results.append(AIMarketsCatalyst(f"catalyst_{_digest(description)}", description, themes, entities, _ids(record), {"provenance": record.get("provenance")}))
    return _unique(results, "catalyst_id")


def _risks(records: list[JsonMap]) -> list[AIMarketsRisk]:
    results = []
    for record in records:
        text = str(record.get("text", ""))
        if _contains_any(text, RISK_WORDS):
            themes = _matched_themes(text)
            entities = _matched_entities(text)
            description = _short(text)
            severity = "high" if "critical" in text.lower() or "severe" in text.lower() else "medium" if "risk" in text.lower() or "constraint" in text.lower() else "low"
            results.append(AIMarketsRisk(f"risk_{_digest(description)}", description, themes, entities, _ids(record), severity, {"provenance": record.get("provenance")}))
    return _unique(results, "risk_id")


def _questions(records: list[JsonMap]) -> list[AIMarketsOpenQuestion]:
    grouped: dict[str, list[JsonMap]] = {}
    for record in records:
        text = _strip_url_noise(str(record.get("text", "")))
        if _is_question_text(text):
            question = _short(_question_candidate(text))
            normalized = _normalize_question(question)
            if normalized:
                item = record.copy()
                item["question"] = question
                item["normalized_question"] = normalized
                grouped.setdefault(normalized, []).append(item)
    results = []
    for normalized in sorted(grouped):
        matched = grouped[normalized]
        variants = sorted({str(item.get("question", "")) for item in matched if item.get("question")})
        canonical = sorted(variants, key=lambda value: (len(value), value.lower(), value))[0] if variants else normalized
        themes = sorted({theme for item in matched for theme in _matched_themes(str(item.get("text", "")))})
        entities = sorted({entity for item in matched for entity in _matched_entities(str(item.get("text", "")))})
        evidence_ids = sorted({str(item.get("evidence_id")) for item in matched if item.get("evidence_id")})
        source_ids = sorted({str(item.get("source")) for item in matched if item.get("source")})
        latest_index = max((_int(item.get("record_index")) for item in matched), default=0)
        priority = _question_priority(canonical, themes, entities, evidence_ids)
        results.append(
            AIMarketsOpenQuestion(
                f"question_{_digest(normalized)}",
                canonical,
                themes,
                priority,
                "Additional explicit evidence record or source document.",
                "open",
                {
                    "provenance": sorted({str(item.get("provenance")) for item in matched if item.get("provenance")}),
                    "variant_count": len(variants),
                    "latest_record_index": latest_index,
                    "related_entities": entities,
                },
                normalized,
                evidence_ids,
                source_ids,
                variants,
                str(latest_index),
            )
        )
    return sorted(results, key=_question_sort_key)


def _executive_questions(questions: list[AIMarketsOpenQuestion]) -> list[AIMarketsOpenQuestion]:
    return sorted(questions, key=_question_sort_key)[:10]


def _attach_related(themes, entities, catalysts, risks, questions):
    by_theme = {theme.name: {"entities": [], "catalysts": [], "risks": [], "questions": []} for theme in themes}
    for entity in entities:
        for theme in entity.related_themes:
            if theme in by_theme:
                by_theme[theme]["entities"].append(entity.symbol)
    for catalyst in catalysts:
        for theme in catalyst.related_themes:
            if theme in by_theme:
                by_theme[theme]["catalysts"].append(catalyst.catalyst_id)
    for risk in risks:
        for theme in risk.related_themes:
            if theme in by_theme:
                by_theme[theme]["risks"].append(risk.risk_id)
    for question in questions:
        for theme in question.related_themes:
            if theme in by_theme:
                by_theme[theme]["questions"].append(question.question_id)
    return [
        AIMarketsTheme(theme.theme_id, theme.name, "weakening" if by_theme[theme.name]["risks"] and theme.evidence_count <= 1 else theme.status, theme.confidence, theme.evidence_count, theme.source_count, theme.related_evidence_ids, sorted(by_theme[theme.name]["entities"]), sorted(by_theme[theme.name]["risks"]), sorted(by_theme[theme.name]["catalysts"]), sorted(by_theme[theme.name]["questions"]), theme.provenance)
        for theme in themes
    ]


def _confidence(evidence_count: int, source_count: int) -> str:
    if evidence_count >= 4 or source_count >= 3:
        return "high"
    if evidence_count >= 2 or source_count >= 2:
        return "medium"
    return "low"


def _matched_themes(text: str) -> list[str]:
    return sorted(name for name, keywords in THEME_KEYWORDS.items() if _contains_any(text, keywords))


def _matched_entities(text: str) -> list[str]:
    return sorted(symbol for symbol in ENTITY_MAP if _entity_match(text, symbol))


def _content_ideas(report: AIMarketsReport) -> list[str]:
    return [f"Review evidence behind {theme.name} ({theme.confidence} confidence)." for theme in report.themes[:10]]


def _contains_any(text: str, needles: list[str]) -> bool:
    lower = text.lower()
    return any(needle.lower() in lower for needle in needles)


def _symbol_match(text: str, symbol: str) -> bool:
    return re.search(rf"(?<![A-Z0-9]){re.escape(symbol)}(?![A-Z0-9])", text.upper()) is not None


def _entity_match(text: str, symbol: str) -> bool:
    return bool(_matched_aliases(text, symbol))


def _matched_aliases(text: str, symbol: str) -> list[str]:
    aliases = ENTITY_ALIASES.get(symbol, [symbol])
    return sorted({alias for alias in aliases if _token_match(text, alias)})


def _token_match(text: str, value: str) -> bool:
    return re.search(rf"(?<![A-Za-z0-9]){re.escape(value)}(?![A-Za-z0-9])", text, flags=re.IGNORECASE) is not None


def _normalize_question(question: str) -> str:
    clean = question.lower().replace("?", " ? ")
    clean = re.sub(r"[^\w\s?]", " ", clean)
    clean = re.sub(r"(?:\s*\?\s*)+", "?", clean)
    clean = re.sub(r"\s+", " ", clean).strip()
    prefixes = ["is", "are", "does"]
    changed = True
    while changed:
        changed = False
        for prefix in prefixes:
            repeated = f"{prefix} {prefix} "
            if clean.startswith(repeated):
                clean = clean[len(prefix) + 1 :]
                changed = True
    clean = clean.replace(" ?", "?")
    return clean


def _is_question_text(text: str) -> bool:
    lower = text.lower()
    if "0 open questions identified" in lower or "no open questions" in lower:
        return False
    if any(marker in lower for marker in ["open question", "needs review", "what evidence", "unclear"]):
        return True
    return re.search(r"\b(what|why|how|does|do|can|should|is|are)\b[^?]{0,180}\?", text, flags=re.IGNORECASE) is not None


def _question_candidate(text: str) -> str:
    clean = re.sub(r"\beg_(evidence_)?ev_[A-Za-z0-9_]+\b", " ", text)
    clean = re.sub(r"\bev_[A-Za-z0-9_]+\b", " ", clean)
    clean = " ".join(clean.split())
    match = re.search(r"\b(open question|what|why|how|does|do|can|should|is|are)\b.*", clean, flags=re.IGNORECASE)
    return match.group(0) if match else clean


def _strip_url_noise(text: str) -> str:
    return re.sub(r"https?://\S+", "", text)


def _question_priority(question: str, themes: list[str], entities: list[str], evidence_ids: list[str]) -> str:
    lower = question.lower()
    if (
        len(themes) >= 2
        or len(evidence_ids) >= 2
        or any(entity in HIGH_PRIORITY_ENTITIES for entity in entities)
        or any(term in lower for term in QUESTION_PRIORITY_TERMS)
    ):
        return "high"
    if len(themes) >= 1 and len(evidence_ids) >= 1:
        return "medium"
    if _contains_any(question, [keyword for keywords in THEME_KEYWORDS.values() for keyword in keywords]):
        return "medium"
    return "low"


def _question_sort_key(question: AIMarketsOpenQuestion):
    priority_rank = {"high": 0, "medium": 1, "low": 2}.get(question.priority, 3)
    latest = _int(_map(question.provenance).get("latest_record_index"))
    return (priority_rank, -len(question.evidence_ids), -len(question.related_themes), -latest, question.question_id)


def _total_open_question_count(report: AIMarketsReport) -> int:
    return sum(_int(question.provenance.get("variant_count")) or 1 for question in report.open_questions)


LIFECYCLE_STATUS_PRIORITY = {
    "high_conviction": 0,
    "strengthening": 1,
    "active": 2,
    "emerging": 3,
    "weakening": 4,
    "contradicted": 5,
    "archived": 6,
}


def _lifecycle_status(
    theme: AIMarketsTheme,
    previous: JsonMap,
    entity_count: int,
    risk_count: int,
    risk_descriptions: list[str],
    history: list[JsonMap],
) -> tuple[str, str]:
    previous_evidence = _int(previous.get("evidence_count"))
    previous_sources = _int(previous.get("source_count"))
    previous_entities = _int(previous.get("entity_count"))
    previous_risks = _int(previous.get("risk_count"))
    previous_confidence = str(previous.get("confidence") or "")
    explicit_conflict = any("contradiction" in text.lower() or "conflict" in text.lower() for text in risk_descriptions)
    if explicit_conflict or (risk_count > theme.evidence_count and risk_count >= 2):
        return "contradicted", "Theme is contradicted because explicit conflict language or risk dominance is attached to the theme."
    if previous and theme.evidence_count == previous_evidence and theme.source_count == previous_sources and entity_count == previous_entities and risk_count == previous_risks and previous.get("current_status"):
        return str(previous.get("current_status")), "Theme lifecycle status is unchanged because deterministic counts match the prior snapshot."
    if previous and (theme.evidence_count < previous_evidence or _confidence_rank(theme.confidence) < _confidence_rank(previous_confidence)):
        return "weakening", f"Theme is weakening because evidence or confidence declined from the prior snapshot."
    if previous and risk_count > previous_risks and theme.evidence_count <= previous_evidence:
        return "weakening", "Theme is weakening because risk count increased without new supporting evidence."
    appeared_before = _theme_seen_count(theme.theme_id, history) > 0
    if theme.evidence_count >= 4 and theme.source_count >= 3 and theme.confidence == "high" and risk_count <= theme.evidence_count and (appeared_before or not history):
        return "high_conviction", "Theme is high conviction because evidence_count >= 4, source_count >= 3, confidence is high, and risks do not exceed evidence."
    if previous and (theme.evidence_count > previous_evidence or theme.source_count > previous_sources or entity_count > previous_entities) and risk_count <= theme.evidence_count:
        return "strengthening", f"Theme is strengthening because evidence/source/entity count increased from the prior snapshot."
    if not previous or theme.evidence_count <= 1:
        return "emerging", "Theme is emerging because it is newly detected or has only one supporting evidence item."
    return "active", "Theme is active because it has repeated evidence but does not meet strengthening or high-conviction thresholds."


def _confidence_reason(confidence: str, evidence_count: int, source_count: int, entity_count: int, risk_count: int, previous_confidence: str) -> str:
    prior = previous_confidence or "none"
    if confidence == "high":
        rule = "4+ evidence items or 3+ sources"
    elif confidence == "medium":
        rule = "2-3 evidence items or 2 sources"
    else:
        rule = "1 evidence item or 1 source"
    return f"Confidence is {confidence} using rule {rule}; evidence_count={evidence_count}, source_count={source_count}, entity_count={entity_count}, risk_count={risk_count}, prior_confidence={prior}."


def _theme_transitions(themes: list[JsonMap], previous_themes: dict[str, JsonMap], created_at: str) -> list[AIMarketsThemeTransition]:
    transitions: list[AIMarketsThemeTransition] = []
    for theme in themes:
        theme_id = str(theme.get("theme_id"))
        previous = previous_themes.get(theme_id, {})
        if not previous:
            transitions.append(_transition(theme, "new_theme", None, theme.get("current_status"), "Theme appeared in lifecycle tracking.", created_at))
            continue
        checks = [
            ("status_changed", previous.get("current_status"), theme.get("current_status")),
            ("confidence_changed", previous.get("confidence"), theme.get("confidence")),
            ("evidence_changed", previous.get("evidence_count"), theme.get("evidence_count")),
            ("source_changed", previous.get("source_count"), theme.get("source_count")),
            ("entity_changed", previous.get("entity_count"), theme.get("entity_count")),
            ("risk_changed", previous.get("risk_count"), theme.get("risk_count")),
        ]
        for transition_type, previous_value, current_value in checks:
            if previous_value != current_value:
                transitions.append(_transition(theme, transition_type, previous_value, current_value, f"{transition_type} from {previous_value} to {current_value}.", created_at))
        if theme.get("current_status") == "archived" and previous.get("current_status") != "archived":
            transitions.append(_transition(theme, "archived_theme", previous.get("current_status"), "archived", "Theme reached archived status after repeated absence.", created_at))
    return sorted(transitions, key=_transition_sort_key)


def _transition(theme: JsonMap, transition_type: str, previous_value: Any, current_value: Any, reason: str, created_at: str) -> AIMarketsThemeTransition:
    payload = f"{theme.get('theme_id')}|{transition_type}|{previous_value}|{current_value}"
    return AIMarketsThemeTransition(
        transition_id=f"transition_{_digest(payload)}",
        theme_id=str(theme.get("theme_id", "")),
        theme_name=str(theme.get("theme_name", "")),
        transition_type=transition_type,
        previous_value=previous_value,
        current_value=current_value,
        reason=reason,
        created_at=created_at,
        provenance={"theme_lifecycle_snapshot": "outputs/ai-markets/theme-lifecycle.json"},
    )


def _lifecycle_snapshot_id(themes: list[JsonMap]) -> str:
    payload = "|".join(
        f"{theme.get('theme_id')}:{theme.get('current_status')}:{theme.get('confidence')}:{theme.get('evidence_count')}:{theme.get('source_count')}:{theme.get('entity_count')}:{theme.get('risk_count')}"
        for theme in themes
    )
    return f"ai_markets_lifecycle_{_digest(payload)}"


def _lifecycle_counts(themes: list[JsonMap]) -> JsonMap:
    return {
        "high_conviction_theme_count": sum(1 for theme in themes if theme.get("current_status") == "high_conviction"),
        "strengthening_theme_count": sum(1 for theme in themes if theme.get("current_status") == "strengthening"),
        "active_theme_count": sum(1 for theme in themes if theme.get("current_status") == "active"),
        "emerging_theme_count": sum(1 for theme in themes if theme.get("current_status") == "emerging"),
        "weakening_theme_count": sum(1 for theme in themes if theme.get("current_status") == "weakening"),
        "contradicted_theme_count": sum(1 for theme in themes if theme.get("current_status") == "contradicted"),
        "archived_theme_count": sum(1 for theme in themes if theme.get("current_status") == "archived"),
    }


def _lifecycle_theme_sort_key(theme: JsonMap):
    return (
        LIFECYCLE_STATUS_PRIORITY.get(str(theme.get("current_status")), 99),
        -_int(theme.get("evidence_count")),
        -_int(theme.get("source_count")),
        str(theme.get("theme_name", "")),
        str(theme.get("theme_id", "")),
    )


def _transition_sort_key(transition: AIMarketsThemeTransition):
    return (-_timestamp_key(transition.created_at), transition.transition_type, transition.theme_name, transition.transition_id)


def _timestamp_key(value: str) -> int:
    if not value:
        return 0
    try:
        return int(datetime.fromisoformat(value).timestamp())
    except ValueError:
        return 0


def _latest_snapshot(history: list[JsonMap]) -> JsonMap:
    return history[-1] if history else {}


def _theme_seen_count(theme_id: str, history: list[JsonMap]) -> int:
    return sum(1 for snapshot in history for theme in _map_list(snapshot.get("themes", [])) if theme.get("theme_id") == theme_id and theme.get("current_status") != "archived")


def _absence_count(theme_id: str, history: list[JsonMap]) -> int:
    count = 0
    for snapshot in reversed(history):
        theme = next((item for item in _map_list(snapshot.get("themes", [])) if item.get("theme_id") == theme_id), None)
        if theme and theme.get("current_status") in {"weakening", "archived"} and _int(theme.get("evidence_count")) == 0:
            count += 1
        else:
            break
    return count


def _confidence_rank(confidence: str) -> int:
    return {"low": 0, "medium": 1, "high": 2}.get(confidence, -1)


def _portfolio_config(root: Path) -> tuple[JsonMap, Path | None]:
    for relative in ["config/portfolio.local.yaml", "config/portfolio.yaml"]:
        path = root / relative
        if path.exists():
            return load_yaml(path), path
    return {}, None


def _portfolio_item_from_config(
    data: JsonMap,
    source: str,
    report: AIMarketsReport,
    lifecycle_by_name: dict[str, JsonMap],
    risks_by_theme: dict[str, list[AIMarketsRisk]],
    questions_by_theme: dict[str, list[AIMarketsOpenQuestion]],
) -> AIMarketsPortfolioPosition:
    symbol = str(data.get("symbol", "")).upper()
    entity = next((item for item in report.entities if item.symbol == symbol), None)
    name = str(data.get("name") or (entity.name if entity else symbol))
    asset_type = str(data.get("asset_type") or (entity.entity_type if entity else "unknown"))
    category = str(data.get("category") or "")
    related_themes = entity.related_themes if entity else sorted(name for name in lifecycle_by_name if category.lower() and category.lower() in name.lower())
    return _portfolio_item(symbol, name, asset_type, category, source, related_themes, entity, lifecycle_by_name, risks_by_theme, questions_by_theme, {"config_source": source, "notes": str(data.get("notes", ""))})


def _portfolio_item_from_entity(
    entity: AIMarketsEntity,
    source: str,
    report: AIMarketsReport,
    lifecycle_by_name: dict[str, JsonMap],
    risks_by_theme: dict[str, list[AIMarketsRisk]],
    questions_by_theme: dict[str, list[AIMarketsOpenQuestion]],
) -> AIMarketsPortfolioWatchlistItem:
    item = _portfolio_item(entity.symbol, entity.name, entity.entity_type, "", source, entity.related_themes, entity, lifecycle_by_name, risks_by_theme, questions_by_theme, entity.provenance)
    return AIMarketsPortfolioWatchlistItem(**item.to_dict())


def _portfolio_item(
    symbol: str,
    name: str,
    asset_type: str,
    category: str,
    source: str,
    related_themes: list[str],
    entity: AIMarketsEntity | None,
    lifecycle_by_name: dict[str, JsonMap],
    risks_by_theme: dict[str, list[AIMarketsRisk]],
    questions_by_theme: dict[str, list[AIMarketsOpenQuestion]],
    provenance: JsonMap,
) -> AIMarketsPortfolioPosition:
    lifecycle_statuses = sorted({str(_map(lifecycle_by_name.get(theme)).get("current_status")) for theme in related_themes if lifecycle_by_name.get(theme)})
    related_risks = sorted({risk.risk_id for theme in related_themes for risk in risks_by_theme.get(theme, [])})
    related_questions = sorted({question.question_id for theme in related_themes for question in questions_by_theme.get(theme, [])})
    evidence_count = entity.evidence_count if entity else 0
    source_count = max([_int(_map(lifecycle_by_name.get(theme)).get("source_count")) for theme in related_themes] or [0])
    confidence = _confidence(evidence_count, source_count)
    priority, reason = _portfolio_priority(lifecycle_statuses, len(related_risks), confidence, evidence_count, source != "detected_entity", False)
    return AIMarketsPortfolioPosition(symbol, name, asset_type, category, source, related_themes, lifecycle_statuses, related_risks, related_questions, evidence_count, source_count, confidence, priority, reason, provenance)


def _portfolio_exposures(
    report: AIMarketsReport,
    lifecycle_by_name: dict[str, JsonMap],
    positions: list[AIMarketsPortfolioPosition],
    watchlist: list[AIMarketsPortfolioWatchlistItem],
    detected: list[AIMarketsPortfolioWatchlistItem],
    risks_by_theme: dict[str, list[AIMarketsRisk]],
    questions_by_theme: dict[str, list[AIMarketsOpenQuestion]],
) -> list[AIMarketsPortfolioExposure]:
    items: list[AIMarketsPortfolioExposure] = []
    all_items = positions + watchlist + detected
    for theme in report.themes:
        related = [item for item in all_items if theme.name in item.related_themes]
        if not related:
            continue
        position_symbols = sorted(item.symbol for item in positions if theme.name in item.related_themes)
        watchlist_symbols = sorted(item.symbol for item in watchlist if theme.name in item.related_themes)
        detected_symbols = sorted(item.symbol for item in detected if theme.name in item.related_themes)
        lifecycle = _map(lifecycle_by_name.get(theme.name))
        lifecycle_status = str(lifecycle.get("current_status") or theme.status)
        risk_count = len(risks_by_theme.get(theme.name, []))
        question_count = len(questions_by_theme.get(theme.name, []))
        exposure_type = "configured_position" if position_symbols else "configured_watchlist" if watchlist_symbols else "detected_entity_only"
        changed = bool(lifecycle.get("status_changed") or lifecycle.get("confidence_changed"))
        priority, reason = _portfolio_priority([lifecycle_status], risk_count, theme.confidence, theme.evidence_count, bool(position_symbols or watchlist_symbols), changed, theme.evidence_count == 0)
        items.append(
            AIMarketsPortfolioExposure(
                theme.theme_id,
                theme.name,
                lifecycle_status,
                theme.confidence,
                sorted({item.symbol for item in related}),
                position_symbols,
                watchlist_symbols,
                detected_symbols,
                theme.evidence_count,
                theme.source_count,
                risk_count,
                question_count,
                exposure_type,
                priority,
                reason,
                {"theme_lifecycle_snapshot": lifecycle.get("snapshot_id"), "source": "outputs/ai-markets/ai-markets.json"},
            )
        )
    return items


def _portfolio_risks(risks: list[AIMarketsRisk], items: list[AIMarketsPortfolioPosition]) -> list[AIMarketsPortfolioRisk]:
    results = []
    for risk in risks:
        symbols = sorted({item.symbol for item in items if set(item.related_themes).intersection(risk.related_themes) or item.symbol in risk.related_entities})
        if not symbols:
            continue
        priority = "high" if risk.severity == "high" or len(symbols) >= 2 else "medium" if risk.severity == "medium" else "low"
        results.append(AIMarketsPortfolioRisk(f"portfolio_{risk.risk_id}", risk.description, symbols, risk.related_themes, risk.severity, risk.risk_id, risk.evidence_ids, priority, risk.provenance))
    return results


def _portfolio_questions(questions: list[AIMarketsOpenQuestion], items: list[AIMarketsPortfolioPosition]) -> list[AIMarketsPortfolioQuestion]:
    results = []
    for question in questions:
        symbols = sorted({item.symbol for item in items if set(item.related_themes).intersection(question.related_themes)})
        if not symbols:
            continue
        results.append(AIMarketsPortfolioQuestion(f"portfolio_{question.question_id}", question.question, symbols, question.related_themes, question.priority, question.question_id, question.provenance))
    return results


def _portfolio_priority(statuses: list[str], risk_count: int, confidence: str, evidence_count: int, configured: bool, lifecycle_changed: bool, no_current_evidence: bool = False) -> tuple[str, str]:
    if any(status in {"contradicted", "weakening"} for status in statuses):
        return "high", "Review because a related theme is contradicted or weakening."
    if lifecycle_changed:
        return "high", "Review because lifecycle status or confidence changed recently."
    if risk_count >= 3:
        return "high", "Review because three or more risks are attached."
    if confidence == "high" and risk_count > 0:
        return "high", "Review because high-confidence evidence has attached risk."
    if configured and evidence_count == 0:
        return "medium", "Monitor because configured exposure has no current evidence."
    if configured and any(status == "emerging" for status in statuses):
        return "medium", "Monitor because configured exposure is tied to an emerging theme."
    if any(status == "active" for status in statuses) and evidence_count > 0:
        return "medium", "Monitor because active theme has supporting evidence."
    if confidence == "medium" or 1 <= risk_count <= 2:
        return "medium", "Monitor because medium confidence or limited risks are attached."
    return "low", "Monitor because exposure is detected only or has limited evidence and no attached risks."


def _risks_by_theme(risks: list[AIMarketsRisk]) -> dict[str, list[AIMarketsRisk]]:
    result: dict[str, list[AIMarketsRisk]] = {}
    for risk in risks:
        for theme in risk.related_themes:
            result.setdefault(theme, []).append(risk)
    return result


def _questions_by_theme(questions: list[AIMarketsOpenQuestion]) -> dict[str, list[AIMarketsOpenQuestion]]:
    result: dict[str, list[AIMarketsOpenQuestion]] = {}
    for question in questions:
        for theme in question.related_themes:
            result.setdefault(theme, []).append(question)
    return result


def _portfolio_snapshot_id(mode, positions, watchlist, detected, exposures, risks, questions) -> str:
    payload = "|".join(
        [
            mode,
            ",".join(item.symbol + item.research_priority for item in positions + watchlist + detected),
            ",".join(item.theme_id + item.research_priority for item in exposures),
            ",".join(item.risk_id + item.priority for item in risks),
            ",".join(item.question_id for item in questions),
        ]
    )
    return f"ai_markets_portfolio_{_digest(payload)}"


def _portfolio_delta(previous: JsonMap, snapshot_id: str, positions, watchlist, exposures, risks) -> AIMarketsPortfolioDelta:
    previous_symbols = {str(item.get("symbol")) for item in _map_list(previous.get("positions", [])) + _map_list(previous.get("watchlist", [])) + _map_list(previous.get("detected_entities", []))}
    current_symbols = {item.symbol for item in positions + watchlist}
    return AIMarketsPortfolioDelta(
        previous.get("snapshot_id") if previous else None,
        snapshot_id,
        len(positions) - _int(previous.get("position_count")),
        len(watchlist) - _int(previous.get("watchlist_count")),
        len(exposures) - _int(previous.get("theme_exposure_count")),
        len(risks) - _int(previous.get("risk_count")),
        _portfolio_high_priority_count(positions + watchlist, exposures, risks) - _int(previous.get("high_priority_review_count")),
        sorted(current_symbols - previous_symbols),
        sorted(previous_symbols - current_symbols),
    )


def _portfolio_high_priority_count(items, exposures, risks) -> int:
    return sum(1 for item in items if item.research_priority == "high") + sum(1 for item in exposures if item.research_priority == "high") + sum(1 for item in risks if item.priority == "high")


def _portfolio_delta_lines(delta: AIMarketsPortfolioDelta) -> list[str]:
    return [
        f"Prior snapshot: {delta.prior_snapshot_id or 'None'}",
        f"Position count change: {delta.position_count_change}",
        f"Watchlist count change: {delta.watchlist_count_change}",
        f"Theme exposure count change: {delta.theme_exposure_count_change}",
        f"Risk count change: {delta.risk_count_change}",
        f"High-priority review count change: {delta.high_priority_review_count_change}",
    ]


def _portfolio_item_sort_key(item: AIMarketsPortfolioPosition):
    return (_priority_rank(item.research_priority), -_confidence_rank(item.confidence), -item.evidence_count, item.symbol)


def _portfolio_exposure_sort_key(item: AIMarketsPortfolioExposure):
    return (LIFECYCLE_STATUS_PRIORITY.get(item.lifecycle_status, 99), _priority_rank(item.research_priority), -item.evidence_count, item.theme_name)


def _portfolio_risk_sort_key(item: AIMarketsPortfolioRisk):
    return (_priority_rank(item.priority), _severity_rank(item.severity), -len(item.related_symbols), item.risk_id)


def _portfolio_question_sort_key(item: AIMarketsPortfolioQuestion):
    return (_priority_rank(item.priority), item.question_id)


def _catalyst_records(
    report: AIMarketsReport,
    lifecycle_by_theme: dict[str, JsonMap],
    portfolio_items: list[JsonMap],
    now: str,
    previous_by_id: dict[str, JsonMap],
) -> list[AIMarketsCatalystRecord]:
    records: list[AIMarketsCatalystRecord] = []
    for catalyst in report.catalysts:
        text = catalyst.description
        category = _catalyst_category(text)
        themes = catalyst.related_themes
        entities = catalyst.related_entities
        lifecycle_statuses = sorted({str(_map(lifecycle_by_theme.get(theme)).get("current_status")) for theme in themes if lifecycle_by_theme.get(theme)})
        watchlist_symbols, portfolio_symbols = _catalyst_portfolio_symbols(themes, entities, portfolio_items)
        risks = sorted({risk.risk_id for risk in report.risks if set(risk.related_themes).intersection(themes) or set(risk.related_entities).intersection(entities)})
        questions = sorted({question.question_id for question in report.open_questions if set(question.related_themes).intersection(themes)})
        time_horizon = _catalyst_time_horizon(text)
        priority, reason = _catalyst_priority(themes, risks, lifecycle_statuses, watchlist_symbols, portfolio_symbols, text, catalyst.evidence_ids, catalyst.provenance)
        status = _catalyst_status(text, catalyst.catalyst_id in previous_by_id, bool(watchlist_symbols or portfolio_symbols), lifecycle_statuses)
        previous = _map(previous_by_id.get(catalyst.catalyst_id))
        records.append(
            AIMarketsCatalystRecord(
                catalyst.catalyst_id,
                _short(text),
                category,
                text,
                time_horizon,
                priority,
                status,
                themes,
                entities,
                watchlist_symbols,
                portfolio_symbols,
                lifecycle_statuses,
                risks,
                questions,
                catalyst.evidence_ids,
                _string_list(_map(catalyst.provenance).get("provenance", [])) or [str(_map(catalyst.provenance).get("provenance", "outputs/ai-markets/catalysts.json"))],
                len(set(_string_list(_map(catalyst.provenance).get("provenance", [])))) or 1,
                len(catalyst.evidence_ids),
                str(previous.get("first_seen_at") or now),
                now,
                reason,
                catalyst.provenance,
            )
        )
    return _unique(records, "catalyst_id")


def _stale_catalyst(previous: JsonMap, now: str) -> AIMarketsCatalystRecord:
    return AIMarketsCatalystRecord(
        str(previous.get("catalyst_id")),
        str(previous.get("title")),
        str(previous.get("category", "unknown")),
        str(previous.get("description", "")),
        str(previous.get("time_horizon", "unknown")),
        str(previous.get("priority", "low")),
        "stale",
        _string_list(previous.get("related_themes", [])),
        _string_list(previous.get("related_entities", [])),
        _string_list(previous.get("related_watchlist_symbols", [])),
        _string_list(previous.get("related_portfolio_symbols", [])),
        _string_list(previous.get("related_lifecycle_statuses", [])),
        _string_list(previous.get("related_risks", [])),
        _string_list(previous.get("related_questions", [])),
        _string_list(previous.get("evidence_ids", [])),
        _string_list(previous.get("source_paths", [])),
        _int(previous.get("source_count")),
        _int(previous.get("evidence_count")),
        str(previous.get("first_seen_at", now)),
        str(previous.get("latest_seen_at", now)),
        "Monitor because this catalyst existed historically but is absent from the current snapshot.",
        _map(previous.get("provenance")),
    )


def _catalyst_category(text: str) -> str:
    for category, keywords in CATALYST_CATEGORY_KEYWORDS.items():
        if _contains_any(text, keywords):
            return category
    return "unknown"


def _catalyst_time_horizon(text: str) -> str:
    lower = text.lower()
    if _contains_any(lower, ["today", "tomorrow", "this morning", "this afternoon", "closing bell", "live", "now"]):
        return "immediate"
    if _contains_any(lower, ["this week", "next week", "upcoming", "ahead of", "this month"]):
        return "near_term"
    if _contains_any(lower, ["this quarter", "earnings season", "next quarter", "second half", "h2", "q1", "q2", "q3", "q4"]):
        return "medium_term"
    if _contains_any(lower, ["cycle", "multi-year", "secular", "structural", "long-term"]):
        return "long_term"
    return "unknown"


def _catalyst_priority(themes, risks, statuses, watchlist_symbols, portfolio_symbols, text, evidence_ids, provenance) -> tuple[str, str]:
    linked_config = bool(watchlist_symbols or portfolio_symbols)
    elevated_status = any(status in {"active", "strengthening", "high_conviction", "weakening", "contradicted"} for status in statuses)
    if (linked_config and elevated_status) or len(themes) >= 2 or len(risks) >= 2 or _contains_any(text, HIGH_IMPACT_CATALYST_TERMS):
        return "high", "Monitor because catalyst is linked to configured/detected exposure, multiple themes/risks, or high-impact catalyst terms."
    if len(themes) == 1 or len(evidence_ids) >= 2:
        return "medium", "Monitor because catalyst is linked to one theme or repeated evidence."
    return "low", "Monitor because catalyst is weakly supported or not linked to themes/entities/watchlist."


def _catalyst_status(text: str, repeated: bool, linked: bool, statuses: list[str]) -> str:
    lower = text.lower()
    if _contains_any(lower, ["resolved", "passed", "completed"]):
        return "resolved"
    if linked or any(status == "active" for status in statuses):
        return "monitoring"
    return "active"


def _catalyst_portfolio_symbols(themes: list[str], entities: list[str], portfolio_items: list[JsonMap]) -> tuple[list[str], list[str]]:
    watchlist: set[str] = set()
    positions: set[str] = set()
    for item in portfolio_items:
        symbol = str(item.get("symbol", ""))
        related = set(_string_list(item.get("related_themes", []))).intersection(themes) or symbol in entities
        if not related:
            continue
        if item.get("source") == "portfolio_config":
            positions.add(symbol)
        else:
            watchlist.add(symbol)
    return sorted(watchlist), sorted(positions)


def _catalyst_delta(previous_by_id: dict[str, JsonMap], current: list[AIMarketsCatalystRecord]) -> AIMarketsCatalystDelta:
    current_by_id = {item.catalyst_id: item for item in current}
    new_ids = sorted(set(current_by_id) - set(previous_by_id))
    removed_ids = sorted(set(previous_by_id) - {item.catalyst_id for item in current if item.status != "stale"})
    return AIMarketsCatalystDelta(
        new_ids,
        removed_ids,
        _field_changes(previous_by_id, current_by_id, "priority"),
        _field_changes(previous_by_id, current_by_id, "status"),
        _field_changes(previous_by_id, current_by_id, "time_horizon"),
        _field_changes(previous_by_id, current_by_id, "related_entities"),
        _field_changes(previous_by_id, current_by_id, "related_themes"),
    )


def _field_changes(previous_by_id: dict[str, JsonMap], current_by_id: dict[str, AIMarketsCatalystRecord], field: str) -> list[JsonMap]:
    changes = []
    for catalyst_id, current in current_by_id.items():
        if catalyst_id not in previous_by_id:
            continue
        previous_value = previous_by_id[catalyst_id].get(field)
        current_value = current.to_dict().get(field)
        if previous_value != current_value:
            changes.append({"catalyst_id": catalyst_id, "previous_value": previous_value, "current_value": current_value})
    return sorted(changes, key=lambda item: str(item.get("catalyst_id")))


def _catalyst_transitions(delta: AIMarketsCatalystDelta, catalysts: list[AIMarketsCatalystRecord], previous_by_id: dict[str, JsonMap], now: str) -> list[AIMarketsCatalystTransition]:
    transitions: list[AIMarketsCatalystTransition] = []
    by_id = {item.catalyst_id: item for item in catalysts}
    for catalyst_id in delta.new_catalysts:
        transitions.append(_catalyst_transition(catalyst_id, "new_catalyst", None, catalyst_id, now))
    for catalyst_id in delta.removed_catalysts:
        transitions.append(_catalyst_transition(catalyst_id, "removed_catalyst", catalyst_id, None, now))
    mapping = [
        ("priority_changed", delta.priority_changes),
        ("status_changed", delta.status_changes),
        ("time_horizon_changed", delta.time_horizon_changes),
        ("entity_link_changed", delta.related_entity_changes),
        ("theme_link_changed", delta.related_theme_changes),
    ]
    for transition_type, changes in mapping:
        for change in changes:
            transitions.append(_catalyst_transition(str(change.get("catalyst_id")), transition_type, change.get("previous_value"), change.get("current_value"), now))
    return sorted(transitions, key=lambda item: (item.transition_type, item.catalyst_id, item.transition_id))


def _catalyst_transition(catalyst_id: str, transition_type: str, previous_value: Any, current_value: Any, now: str) -> AIMarketsCatalystTransition:
    return AIMarketsCatalystTransition(
        f"catalyst_transition_{_digest(f'{catalyst_id}|{transition_type}|{previous_value}|{current_value}')}",
        catalyst_id,
        transition_type,
        previous_value,
        current_value,
        f"{transition_type} for {catalyst_id}.",
        now,
        {"source": "outputs/ai-markets/catalysts/catalyst-monitor.json"},
    )


def _catalyst_snapshot_id(catalysts: list[AIMarketsCatalystRecord]) -> str:
    payload = "|".join(f"{item.catalyst_id}:{item.priority}:{item.status}:{item.time_horizon}:{','.join(item.related_themes)}:{','.join(item.related_entities)}" for item in catalysts)
    return f"ai_markets_catalysts_{_digest(payload)}"


def _catalyst_sort_key(item: AIMarketsCatalystRecord):
    return (_priority_rank(item.priority), _time_horizon_rank(item.time_horizon), 0 if item.related_watchlist_symbols or item.related_portfolio_symbols else 1, 0 if item.related_risks else 1, -item.evidence_count, -item.source_count, item.category, item.catalyst_id)


def _time_horizon_rank(value: str) -> int:
    return {"immediate": 0, "near_term": 1, "medium_term": 2, "long_term": 3, "unknown": 4}.get(value, 5)


def _decision_config(root: Path) -> tuple[JsonMap, Path | None]:
    for relative in ["config/decision-journal.local.yaml", "config/decision-journal.yaml"]:
        path = root / relative
        if path.exists():
            return load_yaml(path), path
    return {}, None


def _decision_entry_paths(root: Path, config: JsonMap) -> list[Path]:
    paths = _string_list(_map(config.get("decision_journal")).get("entry_paths", []))
    if not paths:
        paths = ["journal/ai-markets"]
    return [root / path for path in paths]


def _decision_artifacts(root: Path) -> JsonMap:
    return {
        "ai_markets": _read_optional_json(root / "outputs" / "ai-markets" / "ai-markets.json"),
        "lifecycle": _read_optional_json(root / "outputs" / "ai-markets" / "theme-lifecycle.json"),
        "portfolio": _read_optional_json(root / "outputs" / "ai-markets" / "portfolio" / "portfolio-intelligence.json"),
        "catalysts": _read_optional_json(root / "outputs" / "ai-markets" / "catalysts" / "catalyst-monitor.json"),
    }


def _parse_decision_entry(path: Path, artifacts: JsonMap) -> AIMarketsDecisionEntry:
    text = path.read_text(encoding="utf-8")
    front, body = _front_matter(text)
    sections = _markdown_sections(body)
    title = str(front.get("title") or path.stem)
    created_at = str(front.get("created_at") or "")
    entry_id = str(front.get("entry_id") or f"decision_{_digest(str(path) + title + created_at)}")
    status = str(front.get("status") or "open")
    review_at = front.get("review_at") if isinstance(front.get("review_at"), str) else None
    review = AIMarketsDecisionReview(_decision_review_status(status, review_at), review_at)
    outcome = _decision_outcome(status, sections)
    related_themes = _decision_exact_matches(_string_list(front.get("related_themes", [])), [str(item.get("name")) for item in _map_list(_map(artifacts.get("ai_markets")).get("themes", []))])
    related_entities = _decision_exact_matches(_string_list(front.get("related_entities", [])), [str(item.get("symbol")) for item in _map_list(_map(artifacts.get("ai_markets")).get("entities", []))])
    catalyst_records = _map_list(_map(artifacts.get("catalysts")).get("catalysts", []))
    related_catalysts = _decision_catalyst_matches(_string_list(front.get("related_catalysts", [])), catalyst_records)
    risk_records = _map_list(_map(artifacts.get("ai_markets")).get("risks", []))
    related_risks = _decision_risk_matches(_string_list(front.get("related_risks", [])), risk_records)
    related_questions = _decision_exact_matches(_string_list(front.get("related_questions", [])), [str(item.get("question_id")) for item in _map_list(_map(artifacts.get("ai_markets")).get("open_questions", []))])
    related_evidence = _string_list(front.get("related_evidence_ids", []))
    lifecycle_statuses = sorted({str(item.get("current_status")) for item in _map_list(_map(artifacts.get("lifecycle")).get("themes", [])) if item.get("theme_name") in related_themes})
    portfolio_exposures = sorted({str(item.get("theme_name")) for item in _map_list(_map(artifacts.get("portfolio")).get("exposures", [])) if item.get("theme_name") in related_themes})
    catalyst_priorities = sorted({str(item.get("priority")) for item in catalyst_records if item.get("catalyst_id") in related_catalysts or item.get("category") in related_catalysts})
    return AIMarketsDecisionEntry(
        entry_id,
        title,
        str(front.get("domain") or "ai_markets"),
        str(front.get("entry_type") or "research_note"),
        str(front.get("decision_type") or "other"),
        status,
        created_at,
        str(front.get("updated_at") or created_at),
        review_at,
        str(front.get("confidence") or "unknown"),
        related_themes,
        related_entities,
        related_catalysts,
        related_risks,
        related_questions,
        related_evidence,
        lifecycle_statuses,
        portfolio_exposures,
        catalyst_priorities,
        sections.get("rationale", ""),
        sections.get("uncertainties", ""),
        sections.get("follow-up", sections.get("follow up", "")),
        sections.get("lessons", sections.get("lesson", "")),
        outcome,
        review,
        str(path),
        True,
        {"source_path": str(path), "front_matter_keys": sorted(front.keys())},
    )


def _front_matter(text: str) -> tuple[JsonMap, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    front_text = parts[1]
    data: JsonMap = {}
    current_key: str | None = None
    for raw in front_text.splitlines():
        line = raw.rstrip()
        if not line.strip():
            continue
        if line.lstrip().startswith("- ") and current_key:
            data.setdefault(current_key, []).append(line.strip()[2:].strip())
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            current_key = key.strip()
            value = value.strip()
            data[current_key] = [] if value == "" else value
    return data, parts[2]


def _markdown_sections(body: str) -> dict[str, str]:
    sections: dict[str, list[str]] = {}
    current = "body"
    sections[current] = []
    for line in body.splitlines():
        if line.startswith("## "):
            current = line[3:].strip().lower()
            sections[current] = []
        else:
            sections.setdefault(current, []).append(line)
    return {key: "\n".join(value).strip() for key, value in sections.items()}


def _decision_review_status(status: str, review_at: str | None) -> str:
    if status in {"reviewed", "confirmed", "challenged", "contradicted", "archived"}:
        return "reviewed"
    if not review_at:
        return "no_review_date"
    today = datetime.now().astimezone().date()
    try:
        review_date = datetime.fromisoformat(review_at).date()
    except ValueError:
        return "no_review_date"
    if review_date == today:
        return "due"
    if review_date < today:
        return "overdue"
    return "not_due"


def _decision_outcome(status: str, sections: dict[str, str]) -> AIMarketsDecisionOutcome:
    text = sections.get("outcome") or sections.get("result") or sections.get("lesson") or sections.get("lessons") or sections.get("postmortem") or ""
    if not text:
        return AIMarketsDecisionOutcome("no_outcome_recorded", "")
    if status == "confirmed":
        outcome = "user_confirmed"
    elif status == "challenged":
        outcome = "user_challenged"
    elif status == "contradicted":
        outcome = "user_contradicted"
    elif sections.get("lesson") or sections.get("lessons"):
        outcome = "lesson_recorded"
    else:
        outcome = "pending"
    return AIMarketsDecisionOutcome(outcome, text)


def _decision_exact_matches(values: list[str], candidates: list[str]) -> list[str]:
    candidate_set = {item for item in candidates if item}
    return sorted({value for value in values if value in candidate_set})


def _decision_catalyst_matches(values: list[str], catalysts: list[JsonMap]) -> list[str]:
    result = set()
    for value in values:
        for catalyst in catalysts:
            if value == catalyst.get("catalyst_id") or value == catalyst.get("category"):
                result.add(str(catalyst.get("catalyst_id") or value))
    return sorted(result)


def _decision_risk_matches(values: list[str], risks: list[JsonMap]) -> list[str]:
    result = set()
    for value in values:
        for risk in risks:
            if value == risk.get("risk_id") or value in str(risk.get("description", "")):
                result.add(str(risk.get("risk_id") or value))
    return sorted(result)


def _decision_delta(previous: JsonMap, entries: list[AIMarketsDecisionEntry]) -> AIMarketsDecisionDelta:
    previous_by_id = {str(item.get("entry_id")): item for item in _map_list(previous.get("entries", []))}
    current_by_id = {item.entry_id: item for item in entries}
    return AIMarketsDecisionDelta(
        sorted(set(current_by_id) - set(previous_by_id)),
        sorted(set(previous_by_id) - set(current_by_id)),
        _decision_field_changes(previous_by_id, current_by_id, "status"),
        _decision_review_changes(previous_by_id, current_by_id),
        _decision_outcome_changes(previous_by_id, current_by_id),
        _decision_link_changes(previous_by_id, current_by_id),
        sorted(item.entry_id for item in entries if item.review.review_status == "due" and _map(previous_by_id.get(item.entry_id)).get("review", {}).get("review_status") != "due"),
        sorted(item.entry_id for item in entries if item.review.review_status == "overdue" and _map(previous_by_id.get(item.entry_id)).get("review", {}).get("review_status") != "overdue"),
    )


def _decision_field_changes(previous_by_id, current_by_id, field: str) -> list[JsonMap]:
    return sorted([{"entry_id": key, "previous_value": previous_by_id[key].get(field), "current_value": value.to_dict().get(field)} for key, value in current_by_id.items() if key in previous_by_id and previous_by_id[key].get(field) != value.to_dict().get(field)], key=lambda item: item["entry_id"])


def _decision_review_changes(previous_by_id, current_by_id) -> list[JsonMap]:
    return sorted([{"entry_id": key, "previous_value": _map(previous_by_id[key].get("review")).get("review_status"), "current_value": value.review.review_status} for key, value in current_by_id.items() if key in previous_by_id and _map(previous_by_id[key].get("review")).get("review_status") != value.review.review_status], key=lambda item: item["entry_id"])


def _decision_outcome_changes(previous_by_id, current_by_id) -> list[JsonMap]:
    return sorted([{"entry_id": key, "previous_value": _map(previous_by_id[key].get("outcome")).get("status"), "current_value": value.outcome.status} for key, value in current_by_id.items() if key in previous_by_id and _map(previous_by_id[key].get("outcome")).get("status") != value.outcome.status], key=lambda item: item["entry_id"])


def _decision_link_changes(previous_by_id, current_by_id) -> list[JsonMap]:
    fields = ["related_themes", "related_entities", "related_catalysts", "related_risks"]
    changes = []
    for key, value in current_by_id.items():
        if key not in previous_by_id:
            continue
        current = value.to_dict()
        if any(previous_by_id[key].get(field) != current.get(field) for field in fields):
            changes.append({"entry_id": key})
    return sorted(changes, key=lambda item: item["entry_id"])


def _decision_snapshot_id(entries: list[AIMarketsDecisionEntry]) -> str:
    payload = "|".join(f"{item.entry_id}:{item.status}:{item.review.review_status}:{item.outcome.status}:{','.join(item.related_themes)}:{','.join(item.related_entities)}" for item in entries)
    return f"ai_markets_decisions_{_digest(payload)}"


def _decision_entry_sort_key(item: AIMarketsDecisionEntry):
    return (_review_rank(item.review.review_status), _decision_status_rank(item.status), item.review_at or "9999-99-99", _date_sort_key(item.created_at, descending=True), item.title, item.entry_id)


def _review_rank(value: str) -> int:
    return {"overdue": 0, "due": 1, "not_due": 2, "no_review_date": 3, "reviewed": 4}.get(value, 5)


def _decision_status_rank(value: str) -> int:
    return {"open": 0, "monitoring": 1, "challenged": 2, "contradicted": 3, "confirmed": 4, "reviewed": 5, "archived": 6}.get(value, 7)


def _date_sort_key(value: str, *, descending: bool = False) -> int:
    try:
        ordinal = datetime.fromisoformat(value).date().toordinal()
    except ValueError:
        ordinal = 0
    return -ordinal if descending else ordinal


def _decision_delta_lines(delta: AIMarketsDecisionDelta) -> list[str]:
    return [
        f"New entries: {len(delta.new_entries)}",
        f"Removed entries: {len(delta.removed_entries)}",
        f"Status changes: {len(delta.status_changes)}",
        f"Review status changes: {len(delta.review_status_changes)}",
        f"Outcome changes: {len(delta.outcome_changes)}",
        f"Newly due reviews: {len(delta.newly_due_reviews)}",
        f"Newly overdue reviews: {len(delta.newly_overdue_reviews)}",
    ]


def _decision_template_text() -> str:
    today = datetime.now().astimezone().date().isoformat()
    return (
        "---\n"
        "domain: ai_markets\n"
        "entry_type: research_note\n"
        "title: Private local journal entry\n"
        "status: open\n"
        f"created_at: {today}\n"
        "review_at: \n"
        "related_themes:\n"
        "related_entities:\n"
        "related_catalysts:\n"
        "related_risks:\n"
        "decision_type: research_review\n"
        "confidence: medium\n"
        "---\n\n"
        "Private local journal entry. Do not commit.\n\n"
        "## Decision / Review\n\n\n"
        "## Rationale\n\n\n"
        "## Uncertainties\n\n\n"
        "## Follow-Up\n\n\n"
        "## Outcome\n\n\n"
        "## Lessons\n\n"
    )


def _brief_artifacts(root: Path) -> dict[str, JsonMap]:
    return {name: _read_optional_json(root / path) for name, path in BRIEF_INPUTS.items()}


def _brief_needs_reauth_warning(artifacts: dict[str, JsonMap]) -> bool:
    daily = _map(artifacts.get("daily"))
    warnings = _map_list(daily.get("connector_warnings", []))
    return any(item.get("status") == "needs_reauth" for item in warnings)


def _brief_metrics(artifacts: dict[str, JsonMap], agenda: list[AIMarketsResearchAgendaItem]) -> JsonMap:
    ai = _map(artifacts.get("ai_markets"))
    portfolio = _map(artifacts.get("portfolio"))
    catalysts = _map(artifacts.get("catalysts"))
    decisions = _map(artifacts.get("decisions"))
    lifecycle = _map(artifacts.get("lifecycle"))
    performance = _map(artifacts.get("performance"))
    thesis_accuracy = _map(artifacts.get("thesis_accuracy"))
    deduped_catalysts = _dedupe_records(_map_list(catalysts.get("catalysts", [])), _catalyst_dedupe_key)
    suppressed = max(0, len(_map_list(catalysts.get("catalysts", []))) - len(deduped_catalysts))
    top_priorities = [item.to_dict() for item in agenda[:5]]
    return {
        "theme_count": len(_map_list(ai.get("themes", []))),
        "entity_count": len(_map_list(ai.get("entities", []))),
        "risk_count": len(_map_list(ai.get("risks", []))),
        "executive_risk_count": min(5, len(_dedupe_records(_map_list(ai.get("risks", [])), _risk_dedupe_key))),
        "watchlist_count": _int(portfolio.get("watchlist_count")),
        "portfolio_mode": portfolio.get("mode"),
        "high_priority_review_count": _int(portfolio.get("high_priority_review_count")),
        "medium_priority_review_count": _portfolio_medium_review_count(portfolio),
        "total_catalyst_count": _int(catalysts.get("total_catalyst_count")),
        "high_priority_catalyst_count": _int(catalysts.get("high_priority_catalyst_count")),
        "deduplicated_catalyst_count": len(deduped_catalysts),
        "suppressed_duplicate_count": suppressed,
        "due_review_count": _int(decisions.get("due_review_count")),
        "overdue_review_count": _int(decisions.get("overdue_review_count")),
        "open_decision_count": _int(decisions.get("open_decision_count")),
        "pending_outcome_count": _int(performance.get("pending_outcome_count")),
        "performance_signal_count": _int(performance.get("performance_signal_count")),
        "high_severity_signal_count": _int(performance.get("high_severity_signal_count")),
        "thesis_accuracy_average": _int(_map(thesis_accuracy.get("summary")).get("average_accuracy_score")),
        "thesis_review_count": _int(_map(thesis_accuracy.get("summary")).get("needs_review_count")),
        "top_themes": [str(item.get("theme_name")) for item in _map_list(lifecycle.get("themes", []))[:5]],
        "top_entities": [str(item.get("symbol")) for item in _map_list(ai.get("entities", []))[:5]],
        "top_catalysts": [_canonical_catalyst_title(item) for item in deduped_catalysts[:5]],
        "top_risks": [_canonical_risk_title(item) for item in _dedupe_records(_map_list(ai.get("risks", [])), _risk_dedupe_key)[:5]],
        "top_agenda_items": [item.title for item in agenda[:5]],
        "top_priorities": top_priorities,
        "top_priority_count": len(top_priorities),
        "remaining_high_priority_count": max(0, sum(1 for item in agenda if item.priority == "high") - sum(1 for item in agenda[:5] if item.priority == "high")),
        "medium_priority_count": sum(1 for item in agenda if item.priority == "medium"),
        "low_priority_count": sum(1 for item in agenda if item.priority == "low"),
        "appendix_item_count": len(agenda) + len(_string_list(artifacts.get("source_artifacts_missing", []))),
    }


def _brief_agenda(artifacts: dict[str, JsonMap], missing: list[str]) -> list[AIMarketsResearchAgendaItem]:
    items: list[AIMarketsResearchAgendaItem] = []
    portfolio = _map(artifacts.get("portfolio"))
    catalysts = _map(artifacts.get("catalysts"))
    decisions = _map(artifacts.get("decisions"))
    lifecycle = _map(artifacts.get("lifecycle"))
    ai = _map(artifacts.get("ai_markets"))
    for entry in _map_list(decisions.get("entries", [])):
        review_status = _map(entry.get("review")).get("review_status")
        if review_status in {"due", "overdue"}:
            items.append(_agenda_item(f"Decision Review: {_clean_title(entry.get('title'), 'Decision Review')}", "high", f"Decision review is {review_status}.", "decision_review", _string_list(entry.get("related_themes", [])), _string_list(entry.get("related_entities", [])), [], [str(entry.get("entry_id"))], _string_list(entry.get("related_risks", [])), ["outputs/ai-markets/decisions/decision-review-queue.md"]))
    for catalyst in _map_list(catalysts.get("catalysts", [])):
        if catalyst.get("priority") == "high":
            items.append(_agenda_item(_canonical_catalyst_title(catalyst), "high", "High-priority catalyst is present.", "catalyst", _string_list(catalyst.get("related_themes", [])), _string_list(catalyst.get("related_entities", [])), [str(catalyst.get("catalyst_id"))], [], _string_list(catalyst.get("related_risks", [])), ["outputs/ai-markets/catalysts/catalyst-monitor.md"]))
    for item in _map_list(portfolio.get("positions", [])) + _map_list(portfolio.get("watchlist", [])) + _map_list(portfolio.get("detected_entities", [])):
        priority = str(item.get("research_priority") or "low")
        if priority in {"high", "medium"}:
            items.append(_agenda_item(f"Portfolio Review: {_clean_title(item.get('symbol'), 'Unclassified Exposure')}", priority, str(item.get("priority_reason", "Portfolio or watchlist review.")), "portfolio_review", _string_list(item.get("related_themes", [])), [str(item.get("symbol"))], [], [], _string_list(item.get("related_risks", [])), ["outputs/ai-markets/portfolio/portfolio-intelligence.md"]))
    for theme in _map_list(lifecycle.get("themes", [])):
        if theme.get("current_status") in {"contradicted", "weakening"}:
            items.append(_agenda_item(f"Theme Review: {_clean_title(theme.get('theme_name'), 'Unclassified Theme')}", "high", f"Theme lifecycle status is {theme.get('current_status')}.", "theme_lifecycle", [str(theme.get("theme_name"))], _string_list(theme.get("related_entities", [])), [], [], _string_list(theme.get("related_risks", [])), ["outputs/ai-markets/theme-lifecycle.md"]))
    for question in _map_list(ai.get("executive_questions", [])):
        items.append(_agenda_item(f"Open Question: {_clean_title(question.get('question'), 'Executive Question')}", "medium", "Executive open question exists.", "open_question", _string_list(question.get("related_themes", [])), [], [], [], [], ["outputs/ai-markets/executive-questions.md"]))
    for name in missing:
        items.append(_agenda_item(f"Check missing artifact: {name}", "low", "Source artifact was unavailable for the brief.", "missing_artifact", [], [], [], [], [], [str(BRIEF_INPUTS[name])]))
    return _unique_agenda(items)


def _agenda_item(title: str, priority: str, reason: str, source_type: str, themes: list[str], entities: list[str], catalysts: list[str], decisions: list[str], risks: list[str], paths: list[str]) -> AIMarketsResearchAgendaItem:
    clean_title = _clean_title(title, "Unclassified Review")
    clean_reason = _clean_brief_text(reason)
    key = _agenda_dedupe_key(clean_title, source_type, themes, entities, catalysts, decisions, risks)
    agenda_id = f"agenda_{_digest(key)}"
    return AIMarketsResearchAgendaItem(agenda_id, _short(clean_title), priority, clean_reason, source_type, sorted(set(themes)), sorted(set(entities)), sorted(set(catalysts)), sorted(set(decisions)), sorted(set(risks)), sorted(set(paths)), {"source_type": source_type, "dedupe_key": key})


def _unique_agenda(items: list[AIMarketsResearchAgendaItem]) -> list[AIMarketsResearchAgendaItem]:
    by_key: dict[str, AIMarketsResearchAgendaItem] = {}
    for item in sorted(items, key=_agenda_sort_key):
        key = str(_map(item.provenance).get("dedupe_key") or item.agenda_id)
        existing = by_key.get(key)
        if existing is None or _priority_rank(item.priority) < _priority_rank(existing.priority):
            by_key[key] = item
    return [by_key[key] for key in sorted(by_key)]


def _brief_priorities(agenda: list[AIMarketsResearchAgendaItem]) -> list[AIMarketsMorningPriority]:
    priorities: list[AIMarketsMorningPriority] = []
    for item in [agenda_item for agenda_item in agenda if agenda_item.priority == "high"][:5]:
        priorities.append(AIMarketsMorningPriority(f"priority_{_digest(item.agenda_id)}", item.title, item.priority, item.reason))
    return priorities


def _brief_sections(artifacts: dict[str, JsonMap], agenda: list[AIMarketsResearchAgendaItem], metrics: JsonMap, missing: list[str]) -> list[AIMarketsExecutiveBriefSection]:
    lifecycle = _map(artifacts.get("lifecycle"))
    portfolio = _map(artifacts.get("portfolio"))
    catalysts = _map(artifacts.get("catalysts"))
    decisions = _map(artifacts.get("decisions"))
    ai = _map(artifacts.get("ai_markets"))
    performance = _map(artifacts.get("performance"))
    thesis_accuracy = _map(artifacts.get("thesis_accuracy"))
    changed = _brief_changes(artifacts)
    deduped_catalysts = _dedupe_records(_map_list(catalysts.get("catalysts", [])), _catalyst_dedupe_key)
    deduped_risks = _dedupe_records(_map_list(ai.get("risks", [])), _risk_dedupe_key)
    return [
        AIMarketsExecutiveBriefSection("What Changed", changed or ["No new changes detected from available artifacts."]),
        AIMarketsExecutiveBriefSection("Theme Lifecycle Snapshot", _theme_lifecycle_brief_lines(lifecycle)),
        AIMarketsExecutiveBriefSection("Portfolio / Watchlist Review", _portfolio_brief_lines(portfolio)),
        AIMarketsExecutiveBriefSection("Catalyst Monitor", _catalyst_brief_lines(catalysts, deduped_catalysts)),
        AIMarketsExecutiveBriefSection("Decision and Performance Review", _decision_performance_lines(decisions, performance, thesis_accuracy)),
        AIMarketsExecutiveBriefSection("Risks to Monitor", [_canonical_risk_title(item) for item in deduped_risks[:5]] or ["No AI & Markets risks identified."]),
        AIMarketsExecutiveBriefSection("Recommended Reading", ["outputs/ai-markets/briefings/research-agenda.md", "outputs/ai-markets/ai-markets-report.md", "outputs/ai-markets/portfolio/portfolio-intelligence.md", "outputs/ai-markets/catalysts/catalyst-monitor.md", "outputs/performance/learning-loop.md", "outputs/performance/thesis-accuracy.md"]),
    ]


def _theme_lifecycle_brief_lines(lifecycle: JsonMap) -> list[str]:
    themes = _map_list(lifecycle.get("themes", []))
    if not themes:
        return ["Theme lifecycle unavailable."]
    labels = [
        ("Strengthening", "strengthening"),
        ("High Conviction", "high_conviction"),
        ("Active", "active"),
        ("Emerging", "emerging"),
        ("Weakening", "weakening"),
        ("Contradicted", "contradicted"),
    ]
    lines: list[str] = []
    for label, status in labels:
        names = [_clean_title(item.get("theme_name"), "Unclassified Theme") for item in themes if item.get("current_status") == status]
        if names:
            lines.append(f"{label}: {', '.join(names[:5])}")
    return lines or ["No non-empty theme lifecycle groups."]


def _portfolio_brief_lines(portfolio: JsonMap) -> list[str]:
    items = _map_list(portfolio.get("positions", [])) + _map_list(portfolio.get("watchlist", [])) + _map_list(portfolio.get("detected_entities", []))
    top = sorted([item for item in items if item.get("research_priority") in {"high", "medium"}], key=lambda item: (_priority_rank(str(item.get("research_priority"))), str(item.get("symbol"))))[:5]
    return [
        f"Mode: {portfolio.get('mode', 'unavailable')}",
        f"Watchlist count: {portfolio.get('watchlist_count', 0)}",
        f"High-priority reviews: {portfolio.get('high_priority_review_count', 0)}",
        f"Medium-priority reviews: {_portfolio_medium_review_count(portfolio)}",
        "Top review items: " + (", ".join(f"{_clean_title(item.get('symbol'), 'Unclassified')}: {item.get('research_priority')}" for item in top) if top else "None"),
        "Portfolio report: outputs/ai-markets/portfolio/portfolio-intelligence.md",
    ]


def _catalyst_brief_lines(catalysts: JsonMap, deduped: list[JsonMap]) -> list[str]:
    lines = [
        f"Total catalysts: {catalysts.get('total_catalyst_count', 0)}",
        f"High-priority catalysts: {catalysts.get('high_priority_catalyst_count', 0)}",
        f"Deduplicated catalysts shown: {min(5, len(deduped))}",
    ]
    for catalyst in deduped[:5]:
        lines.append(
            f"{_canonical_catalyst_title(catalyst)} - category={catalyst.get('category', 'unknown')} priority={catalyst.get('priority', 'unknown')} horizon={catalyst.get('time_horizon', 'unknown')} themes={', '.join(_string_list(catalyst.get('related_themes', []))) or 'None'} entities={', '.join(_string_list(catalyst.get('related_watchlist_symbols', [])) + _string_list(catalyst.get('related_entities', []))) or 'None'}"
        )
    lines.append("Catalyst monitor: outputs/ai-markets/catalysts/catalyst-monitor.md")
    return lines


def _decision_performance_lines(decisions: JsonMap, performance: JsonMap, thesis_accuracy: JsonMap) -> list[str]:
    thesis_summary = _map(thesis_accuracy.get("summary"))
    return [
        f"Open decisions: {decisions.get('open_decision_count', 0)}",
        f"Due reviews: {decisions.get('due_review_count', 0)}",
        f"Overdue reviews: {decisions.get('overdue_review_count', 0)}",
        f"Pending outcomes: {performance.get('pending_outcome_count', 0)}",
        f"Performance signals: {performance.get('performance_signal_count', 0)}",
        f"High-severity signals: {performance.get('high_severity_signal_count', 0)}",
        f"Thesis Accuracy average: {thesis_summary.get('average_accuracy_score', 0)}",
        f"Thesis review count: {thesis_summary.get('needs_review_count', 0)}",
        "Decision Journal: outputs/ai-markets/decisions/decision-journal.md",
        "Learning Loop: outputs/performance/learning-loop.md",
        "Thesis Accuracy: outputs/performance/thesis-accuracy.md",
    ]


def _agenda_item_lines(items: list[AIMarketsResearchAgendaItem]) -> list[str]:
    if not items:
        return ["- None", ""]
    lines: list[str] = []
    for item in items:
        lines.append(f"- {item.title} ({item.priority}, {item.source_type}) - {item.reason}")
    lines.append("")
    return lines


def _appendix_lines(snapshot: AIMarketsBriefSnapshot) -> list[str]:
    remaining = snapshot.research_agenda[5:]
    lines = [
        "### Remaining Agenda Items",
        "",
        *_agenda_item_lines(remaining),
        "### Evidence / Catalyst / Risk IDs",
        "",
    ]
    ids: list[str] = []
    for item in snapshot.research_agenda:
        ids.extend(item.related_catalysts)
        ids.extend(item.related_risks)
        ids.extend(item.related_decisions)
    lines.extend(_bullet(sorted(set(ids)) or ["No supporting IDs recorded."]))
    lines.extend(["### Source Paths", ""])
    source_paths = sorted({path for item in snapshot.research_agenda for path in item.source_paths})
    lines.extend(_bullet(source_paths or ["No source paths recorded."]))
    lines.extend(["### Unavailable Artifacts", ""])
    lines.extend(_bullet(snapshot.source_artifacts_missing or ["No unavailable artifacts."]))
    lines.extend(["### Deterministic Limitations", ""])
    lines.extend(_bullet(snapshot.limitations))
    return lines


def _brief_changes(artifacts: dict[str, JsonMap]) -> list[str]:
    changes: list[str] = []
    lifecycle_transitions = len(_map_list(_map(artifacts.get("lifecycle")).get("transitions", [])))
    catalyst_new = _int(_map(artifacts.get("catalysts")).get("new_catalyst_count"))
    decision_due = _int(_map(artifacts.get("decisions")).get("due_review_count")) + _int(_map(artifacts.get("decisions")).get("overdue_review_count"))
    if lifecycle_transitions:
        changes.append(f"Theme lifecycle transitions: {lifecycle_transitions}.")
    if catalyst_new:
        changes.append(f"New catalysts: {catalyst_new}.")
    if decision_due:
        changes.append(f"Due or overdue decision reviews: {decision_due}.")
    return changes


def _brief_delta(previous: JsonMap, agenda: list[AIMarketsResearchAgendaItem], metrics: JsonMap, available: list[str], missing: list[str]) -> AIMarketsBriefDelta:
    prev_agenda = {str(item.get("agenda_id")): item for item in _map_list(previous.get("research_agenda", []))}
    current = {item.agenda_id: item for item in agenda}
    priority_changes = [{"agenda_id": key, "previous_value": prev_agenda[key].get("priority"), "current_value": item.priority} for key, item in current.items() if key in prev_agenda and prev_agenda[key].get("priority") != item.priority]
    prev_missing = set(_string_list(previous.get("source_artifacts_missing", [])))
    return AIMarketsBriefDelta(
        sorted(set(current) - set(prev_agenda)),
        sorted(set(prev_agenda) - set(current)),
        sorted(priority_changes, key=lambda item: str(item.get("agenda_id"))),
        _int(metrics.get("total_catalyst_count")) - _int(previous.get("total_catalyst_count")),
        _int(metrics.get("due_review_count")) + _int(metrics.get("overdue_review_count")) - (_int(previous.get("due_review_count")) + _int(previous.get("overdue_review_count"))),
        _int(metrics.get("high_priority_review_count")) - _int(previous.get("high_priority_review_count")),
        _int(metrics.get("theme_count")) - _int(previous.get("theme_count")),
        sorted(set(missing).symmetric_difference(prev_missing)),
    )


def _brief_id(agenda: list[AIMarketsResearchAgendaItem], metrics: JsonMap, available: list[str], missing: list[str]) -> str:
    payload = "|".join([",".join(item.agenda_id + item.priority for item in agenda), ",".join(f"{key}:{metrics.get(key)}" for key in sorted(metrics)), ",".join(available), ",".join(missing)])
    return f"ai_markets_brief_{_digest(payload)}"


def _agenda_sort_key(item: AIMarketsResearchAgendaItem):
    source_rank = {"decision_review": 0, "catalyst": 1, "portfolio_review": 2, "theme_lifecycle": 3, "risk": 4, "open_question": 5, "source_activity": 6, "missing_artifact": 7}.get(item.source_type, 8)
    return (_priority_rank(item.priority), source_rank, -len(item.related_entities), -len(item.related_themes), item.title, item.agenda_id)


def _priority_rank(priority: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(priority, 3)


def _severity_rank(severity: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(severity, 3)


def _short(text: str) -> str:
    clean = " ".join(text.split())
    return clean[:220] if len(clean) > 220 else clean


def _clean_title(value: Any, fallback: str) -> str:
    clean = _clean_brief_text(str(value or ""))
    if not clean or clean.lower() in {"none", "null", "n/a"}:
        return fallback
    clean = re.sub(r"^(monitor catalyst|review exposure|check theme|check evidence for question|review decision):\s*", "", clean, flags=re.IGNORECASE)
    return _short(clean) or fallback


def _clean_brief_text(text: str) -> str:
    clean = re.sub(r"https?://\S+", "", text)
    clean = re.sub(r"\beg_evidence_[A-Za-z0-9_:-]+", "", clean)
    clean = re.sub(r"\bev_[A-Za-z0-9_:-]+", "", clean)
    clean = re.sub(r"\b\d{1,2}:\d{2}(?::\d{2})?\b", "", clean)
    clean = re.sub(r"YouTube.*?(privacy|history|terms|sign in).*", "", clean, flags=re.IGNORECASE)
    clean = clean.replace("* **", "").replace("**", "").replace("*", "")
    clean = re.sub(r"\bNone\b", "", clean)
    clean = clean.strip(" -:|")
    clean = re.sub(r"\s+", " ", clean).strip(" -:|")
    return clean


def _normalize_brief_key(text: str) -> str:
    clean = _clean_brief_text(text).lower()
    clean = re.sub(r"^(monitor catalyst|review exposure|check theme|check evidence for question|review decision)\s+", "", clean)
    clean = re.sub(r"[^\w\s]", " ", clean)
    return re.sub(r"\s+", " ", clean).strip()


def _agenda_dedupe_key(title: str, source_type: str, themes: list[str], entities: list[str], catalysts: list[str], decisions: list[str], risks: list[str]) -> str:
    linked_ids = [] if source_type == "catalyst" else catalysts or decisions or risks
    parts = [
        source_type,
        _normalize_brief_key(title),
        ",".join(sorted(_normalize_brief_key(item) for item in themes)),
        ",".join(sorted(_normalize_brief_key(item) for item in entities)),
        ",".join(sorted(linked_ids)),
    ]
    return "|".join(parts)


def _canonical_catalyst_title(catalyst: JsonMap) -> str:
    category = str(catalyst.get("category") or "").replace("_", " ").title()
    themes = _string_list(catalyst.get("related_themes", []))
    entities = _string_list(catalyst.get("related_watchlist_symbols", [])) or _string_list(catalyst.get("related_entities", []))
    structured = _clean_title(catalyst.get("title"), "")
    if category:
        return f"{category} Catalyst"
    if structured and not _looks_raw_title(structured):
        return structured
    if category and entities:
        return f"{', '.join(entities[:2])} {category} Catalyst"
    if category and themes:
        return f"{themes[0]} - {category} Catalyst"
    if category:
        return f"{category} Catalyst"
    if themes:
        return f"{themes[0]} Catalyst Review"
    return "Unclassified Catalyst Review"


def _canonical_risk_title(risk: JsonMap) -> str:
    description = _clean_title(risk.get("description"), "")
    themes = _string_list(risk.get("related_themes", []))
    entities = _string_list(risk.get("related_entities", []))
    risk_id = str(risk.get("risk_id") or "")
    if description and not _looks_raw_title(description):
        return description
    if themes and entities:
        return f"{themes[0]} Risk - {entities[0]}"
    if themes:
        return f"{themes[0]} Risk"
    return risk_id or "Unclassified Risk Review"


def _looks_raw_title(title: str) -> bool:
    lowered = title.lower()
    return bool(re.search(r"\beg_evidence_|\bev_|youtube|https?://|\*\s*\*\*|\bnone\b", lowered)) or len(title) > 140


def _catalyst_dedupe_key(catalyst: JsonMap) -> str:
    return "|".join(
        [
            _normalize_brief_key(str(catalyst.get("category", ""))),
            ",".join(sorted(_normalize_brief_key(item) for item in _string_list(catalyst.get("related_themes", [])))),
            ",".join(sorted(_normalize_brief_key(item) for item in _string_list(catalyst.get("related_entities", [])) + _string_list(catalyst.get("related_watchlist_symbols", [])))),
        ]
    )


def _risk_dedupe_key(risk: JsonMap) -> str:
    return "|".join(
        [
            _normalize_brief_key(str(risk.get("risk_id", "")) or str(risk.get("description", ""))),
            ",".join(sorted(_normalize_brief_key(item) for item in _string_list(risk.get("related_themes", [])))),
            ",".join(sorted(_normalize_brief_key(item) for item in _string_list(risk.get("related_entities", [])))),
        ]
    )


def _dedupe_records(records: list[JsonMap], key_fn) -> list[JsonMap]:
    by_key: dict[str, JsonMap] = {}
    for record in records:
        key = key_fn(record)
        existing = by_key.get(key)
        if existing is None or _priority_rank(str(record.get("priority"))) < _priority_rank(str(existing.get("priority"))):
            by_key[key] = record
    return [by_key[key] for key in sorted(by_key, key=lambda key: (_priority_rank(str(by_key[key].get("priority"))), key))]


def _portfolio_medium_review_count(portfolio: JsonMap) -> int:
    items = _map_list(portfolio.get("positions", [])) + _map_list(portfolio.get("watchlist", [])) + _map_list(portfolio.get("detected_entities", []))
    exposures = _map_list(portfolio.get("exposures", []))
    return sum(1 for item in items if item.get("research_priority") == "medium") + sum(1 for item in exposures if item.get("research_priority") == "medium")


def _ids(record: JsonMap) -> list[str]:
    evidence_id = record.get("evidence_id")
    return [str(evidence_id)] if evidence_id else []


def _unique(items, attr: str):
    result = {}
    for item in items:
        result[getattr(item, attr)] = item
    return [result[key] for key in sorted(result)]


def _report_id(themes, entities, catalysts, risks, questions, evidence_refs):
    payload = "|".join(
        [
            ",".join(theme.theme_id + theme.status + theme.confidence for theme in themes),
            ",".join(entity.entity_id for entity in entities),
            ",".join(item.catalyst_id for item in catalysts),
            ",".join(item.risk_id for item in risks),
            ",".join(item.question_id for item in questions),
            ",".join(evidence_refs),
        ]
    )
    return f"ai_markets_{_digest(payload)}"


def _entity_from_dict(data):
    return AIMarketsEntity(_require_str(data, "entity_id"), _require_str(data, "symbol"), _require_str(data, "name"), _require_str(data, "entity_type"), _string_list(data.get("related_themes", [])), _int(data.get("evidence_count")), data.get("latest_mention") if isinstance(data.get("latest_mention"), str) else None, _map(data.get("provenance")))


def _catalyst_from_dict(data):
    return AIMarketsCatalyst(_require_str(data, "catalyst_id"), _require_str(data, "description"), _string_list(data.get("related_themes", [])), _string_list(data.get("related_entities", [])), _string_list(data.get("evidence_ids", [])), _map(data.get("provenance")))


def _risk_from_dict(data):
    return AIMarketsRisk(_require_str(data, "risk_id"), _require_str(data, "description"), _string_list(data.get("related_themes", [])), _string_list(data.get("related_entities", [])), _string_list(data.get("evidence_ids", [])), _require_str(data, "severity"), _map(data.get("provenance")))


def _question_from_dict(data):
    question = _require_str(data, "question")
    return AIMarketsOpenQuestion(
        _require_str(data, "question_id"),
        question,
        _string_list(data.get("related_themes", [])),
        _require_str(data, "priority"),
        _require_str(data, "evidence_needed"),
        _require_str(data, "status"),
        _map(data.get("provenance")),
        str(data.get("normalized_question") or _normalize_question(question)),
        _string_list(data.get("evidence_ids", [])),
        _string_list(data.get("source_ids", [])),
        _string_list(data.get("supporting_text", [question])),
        data.get("latest_mention") if isinstance(data.get("latest_mention"), str) else None,
    )


def _read_optional_json(path: Path) -> JsonMap:
    if not path.exists():
        return {}
    try:
        data = read_json(path)
    except Exception:
        return {}
    return data if isinstance(data, dict) else {}


def _bullet(items):
    return [*(f"- {item}" for item in items), ""]


def _first(items):
    return items[0] if items else None


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
        raise AIMarketsError(f"AI & Markets field {key} must be a string")
    return value
