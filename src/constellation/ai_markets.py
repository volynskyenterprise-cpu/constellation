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
        report_data = report.to_dict()
        report_data["theme_lifecycle"] = lifecycle.to_dict()
        report_data["portfolio_intelligence"] = portfolio.to_dict()
        report_data["catalyst_monitor"] = catalyst_monitor.to_dict()
        write_json(self.json_path, report_data)
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(render_report(report, lifecycle, portfolio, catalyst_monitor), encoding="utf-8")
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
        }

    def export(self) -> Path:
        report = self.load()
        lifecycle = AIMarketsThemeLifecycleStore(self.root).build(report)
        portfolio = AIMarketsPortfolioStore(self.root).build(report, lifecycle)
        catalyst_monitor = AIMarketsCatalystStore(self.root).build(report, lifecycle, portfolio)
        self.report_path.write_text(render_report(report, lifecycle, portfolio, catalyst_monitor), encoding="utf-8")
        self.watchlist_path.write_text(render_watchlist(report, portfolio, catalyst_monitor), encoding="utf-8")
        self.content_ideas_path.write_text(render_content_ideas(report), encoding="utf-8")
        self.executive_questions_path.write_text(render_executive_questions(report), encoding="utf-8")
        return self.report_path


def render_report(report: AIMarketsReport, lifecycle: AIMarketsThemeLifecycleSnapshot | None = None, portfolio: AIMarketsPortfolioSnapshot | None = None, catalyst_monitor: AIMarketsCatalystSnapshot | None = None) -> str:
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
        return "high", "Review because configured exposure has no current evidence."
    if configured and any(status == "emerging" for status in statuses):
        return "high", "Review because configured exposure is tied to an emerging theme."
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


def _priority_rank(priority: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(priority, 3)


def _severity_rank(severity: str) -> int:
    return {"high": 0, "medium": 1, "low": 2}.get(severity, 3)


def _short(text: str) -> str:
    clean = " ".join(text.split())
    return clean[:220] if len(clean) > 220 else clean


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
