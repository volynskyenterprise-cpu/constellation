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
    "AMZN": ("Amazon", "equity"),
    "META": ("Meta", "equity"),
    "TSLA": ("Tesla", "equity"),
    "PLTR": ("Palantir", "equity"),
    "ORCL": ("Oracle", "equity"),
    "CRWV": ("CoreWeave", "equity"),
    "IREN": ("IREN", "equity"),
    "BTC": ("Bitcoin", "asset"),
    "GLD": ("Gold ETF", "fund"),
    "SLV": ("Silver ETF", "fund"),
    "URA": ("Uranium ETF", "fund"),
    "XME": ("Metals and Mining ETF", "fund"),
    "COPX": ("Copper Miners ETF", "fund"),
}

CATALYST_WORDS = ["catalyst", "launch", "approval", "earnings", "deadline", "buildout", "deployment", "release"]
RISK_WORDS = ["risk", "gap", "constraint", "shortage", "concern", "weakening", "contradiction", "delay"]
QUESTION_WORDS = ["?", "open question", "needs review", "what evidence", "unclear"]

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
            evidence_references=_string_list(data.get("evidence_references", [])),
            provenance=_map(data.get("provenance")),
            limitations=_string_list(data.get("limitations", [])),
        )


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
        self.report_path.parent.mkdir(parents=True, exist_ok=True)
        self.report_path.write_text(render_report(report), encoding="utf-8")
        self.watchlist_path.write_text(render_watchlist(report), encoding="utf-8")
        self.content_ideas_path.write_text(render_content_ideas(report), encoding="utf-8")

    def load(self) -> AIMarketsReport:
        if not self.json_path.exists():
            raise AIMarketsError("No AI & Markets report found. Run `python -m constellation ai-markets build` first.")
        return AIMarketsReport.from_dict(read_json(self.json_path))

    def status(self) -> JsonMap:
        exists = self.json_path.exists()
        report = self.load() if exists else None
        return {
            "available": exists,
            "report_id": report.report_id if report else None,
            "theme_count": len(report.themes) if report else 0,
            "entity_count": len(report.entities) if report else 0,
            "risk_count": len(report.risks) if report else 0,
            "open_question_count": len(report.open_questions) if report else 0,
            "report_path": str(self.report_path),
        }

    def export(self) -> Path:
        report = self.load()
        self.report_path.write_text(render_report(report), encoding="utf-8")
        self.watchlist_path.write_text(render_watchlist(report), encoding="utf-8")
        self.content_ideas_path.write_text(render_content_ideas(report), encoding="utf-8")
        return self.report_path


def render_report(report: AIMarketsReport) -> str:
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
        f"- Open questions: {len(report.open_questions)}",
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
        "## Open Questions",
        "",
        *_bullet([item.question for item in report.open_questions]),
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


def render_watchlist(report: AIMarketsReport) -> str:
    lines = ["# AI & Markets Watchlist", ""]
    lines.extend(_bullet([f"{entity.symbol} - {entity.name}: {', '.join(entity.related_themes) or 'No related theme'}" for entity in report.entities]))
    return "\n".join(lines)


def render_content_ideas(report: AIMarketsReport) -> str:
    lines = ["# AI & Markets Content Ideas", ""]
    lines.extend(_bullet(_content_ideas(report)))
    return "\n".join(lines)


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
    for item in _map_list(_map(artifacts.get("dashboard")).get("current_risks_gaps", [])):
        records.append({"evidence_id": "", "source": "dashboard", "text": str(item), "provenance": "outputs/dashboard/dashboard.json"})
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
        matched = [record for record in records if _symbol_match(str(record.get("text", "")), symbol) or name.lower() in str(record.get("text", "")).lower()]
        if not matched:
            continue
        evidence_ids = sorted({str(record.get("evidence_id")) for record in matched if record.get("evidence_id")})
        related_themes = sorted(theme.name for theme in themes if set(theme.related_evidence_ids).intersection(evidence_ids) or _contains_any(" ".join(str(record.get("text", "")) for record in matched), THEME_KEYWORDS[theme.name]))
        entities.append(AIMarketsEntity(f"entity_{symbol.lower()}", symbol, name, entity_type, related_themes, len(evidence_ids), _now_iso(), {"matched_symbol": symbol}))
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
    results = []
    for record in records:
        text = str(record.get("text", ""))
        if _contains_any(text, QUESTION_WORDS):
            question = _short(text)
            results.append(AIMarketsOpenQuestion(f"question_{_digest(question)}", question, _matched_themes(text), "medium", "Additional explicit evidence record or source document.", "open", {"provenance": record.get("provenance")}))
    return _unique(results, "question_id")


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
    return sorted(symbol for symbol, (name, _) in ENTITY_MAP.items() if _symbol_match(text, symbol) or name.lower() in text.lower())


def _content_ideas(report: AIMarketsReport) -> list[str]:
    return [f"Review evidence behind {theme.name} ({theme.confidence} confidence)." for theme in report.themes[:10]]


def _contains_any(text: str, needles: list[str]) -> bool:
    lower = text.lower()
    return any(needle.lower() in lower for needle in needles)


def _symbol_match(text: str, symbol: str) -> bool:
    return re.search(rf"(?<![A-Z0-9]){re.escape(symbol)}(?![A-Z0-9])", text.upper()) is not None


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
    return AIMarketsOpenQuestion(_require_str(data, "question_id"), _require_str(data, "question"), _string_list(data.get("related_themes", [])), _require_str(data, "priority"), _require_str(data, "evidence_needed"), _require_str(data, "status"), _map(data.get("provenance")))


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
