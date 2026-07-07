# Constellation v5.0 — AI & Markets Intelligence

## Product Vision

Constellation v5.0 marks the transition from a deterministic intelligence platform into a domain-specific institutional research system.

Phase I built the core infrastructure:

- Research intake
- Evidence generation
- Knowledge graphs
- Institutional memory
- Source monitoring
- Workflow automation
- Knowledge evolution
- Executive dashboards
- Institutional research reports

Phase II teaches Constellation how to reason within a domain.

The first domain is **AI & Markets**.

AI & Markets Intelligence is designed to help track, organize, and evolve institutional-grade research across artificial intelligence, capital markets, infrastructure, commodities, digital assets, and macroeconomic regime change.

The goal is not to predict markets automatically.

The goal is to create a durable research operating system that helps the user understand:

- What changed
- Why it matters
- Which themes are strengthening
- Which theses are weakening
- What evidence supports each view
- What risks or contradictions are emerging
- What deserves attention next

## MVP Implementation

The v5.0 MVP implements deterministic AI & Markets classification from existing local Constellation artifacts only.

Commands:

```bash
python -m constellation ai-markets build
python -m constellation ai-markets status
python -m constellation ai-markets themes
python -m constellation ai-markets entities
python -m constellation ai-markets risks
python -m constellation ai-markets questions
python -m constellation ai-markets report
python -m constellation ai-markets export
```

Outputs:

- `outputs/ai-markets/ai-markets.json`
- `outputs/ai-markets/themes.json`
- `outputs/ai-markets/entities.json`
- `outputs/ai-markets/catalysts.json`
- `outputs/ai-markets/risks.json`
- `outputs/ai-markets/open-questions.json`
- `outputs/ai-markets/ai-markets-report.md`
- `outputs/ai-markets/watchlist.md`
- `outputs/ai-markets/content-ideas.md`

The MVP uses fixed keyword and ticker matching only. It does not call providers, OpenAI, web retrieval, embeddings, semantic search, Gmail, or trading systems. It does not provide financial advice.

---

## Core Thesis

AI & Markets is not a single topic.

It is the convergence of several long-duration investment regimes:

- Artificial intelligence
- Compute infrastructure
- Semiconductors
- Power and grid infrastructure
- Robotics
- Automation
- Space infrastructure
- Digital assets
- Monetary debasement
- Commodities
- Defense technology
- Enterprise software transformation
- Capital allocation

The opportunity is not merely collecting more information.

The opportunity is building a system that continuously converts research into institutional memory, evidence, evolving theses, and decision-ready intelligence.

---

## Strategic Objective

v5.0 should make Constellation useful as an AI & Markets research analyst.

After every Morning workflow, the system should be able to produce an AI & Markets view that answers:

1. What themes are currently active?
2. Which themes are strengthening?
3. Which themes are weakening?
4. What new evidence entered the system?
5. Which companies, sectors, and assets are implicated?
6. Which catalysts are approaching?
7. Which risks are rising?
8. Which theses need review?
9. What should be read next?
10. What should be watched this week?

---

## User

Primary user:

- Stan Volynsky

Primary workflows:

- Daily AI & Markets research
- Investment thesis tracking
- Content creation for AI & Markets
- Portfolio and watchlist intelligence
- Market narrative development
- Executive briefing preparation

Secondary future users:

- Investors
- Research analysts
- Operators
- Advisors
- Family offices
- Institutional allocators

---

## Product Positioning

Constellation v5.0 is not a trading bot.

It is not a financial advisor.

It is not an autonomous investment system.

It is an institutional research operating system.

It helps convert fragmented research into:

- Structured themes
- Evidence-backed theses
- Risk registers
- Catalyst calendars
- Source maps
- Watchlists
- Decision briefs
- Executive summaries

---

## Domain Model

AI & Markets Intelligence should introduce a domain layer on top of the existing deterministic core.

### Core Objects

#### Theme

A theme is a persistent research area.

Examples:

- AI Infrastructure
- Robotics
- Power Grid
- Semiconductors
- Enterprise AI
- Bitcoin
- Gold
- Nuclear Energy
- Defense Technology
- Space Infrastructure
- Software Disruption
- Digital Credit
- Monetary Debasement

Each theme should include:

- theme_id
- name
- description
- status
- confidence
- related theses
- related evidence
- related companies
- related assets
- catalysts
- risks
- open questions
- latest update
- provenance

---

#### Company / Asset

A company or asset is an entity connected to themes and theses.

Examples:

- NVDA
- AMD
- AVGO
- MSFT
- GOOGL
- AMZN
- TSLA
- PLTR
- CRWV
- IREN
- BTC
- GLD
- SLV
- URA
- XME
- COPX

Each entity should include:

- entity_id
- ticker or symbol
- name
- entity_type
- related themes
- supporting evidence
- risks
- catalysts
- current relevance
- latest mention date
- provenance

---

#### Catalyst

A catalyst is a future or current event that may affect a thesis.

Examples:

- Earnings
- Fed meeting
- CPI / PCE release
- Product launch
- Policy change
- Capex announcement
- ETF flows
- Regulatory development
- Credit stress
- Breakout / breakdown
- Supply chain event

Each catalyst should include:

- catalyst_id
- title
- date or time window
- related themes
- related entities
- expected impact
- evidence references
- status
- provenance

---

#### Risk

A risk is a challenge, contradiction, or uncertainty attached to a thesis or theme.

Examples:

- Overvaluation
- Capex slowdown
- Power bottlenecks
- Margin compression
- Regulatory pressure
- Liquidity deterioration
- Concentration risk
- Narrative exhaustion
- Weak breadth
- Source disagreement

Each risk should include:

- risk_id
- description
- severity
- related themes
- related entities
- related evidence
- status
- mitigation notes
- provenance

---

#### Open Question

An open question captures what the system does not yet know.

Examples:

- Is AI infrastructure spending accelerating or plateauing?
- Are robotics adoption curves becoming investable now?
- Is Bitcoin acting as liquidity beta or monetary insurance?
- Is power infrastructure the real bottleneck in AI?
- Is enterprise AI monetization improving?
- Are semiconductors rotating or deteriorating?

Each open question should include:

- question_id
- question
- related themes
- priority
- evidence needed
- partially answered by
- status
- provenance

---

## Theme Status Model

Themes should evolve through deterministic states:

- emerging
- active
- strengthening
- high_conviction
- weakening
- contradicted
- archived

Status should not be inferred by an LLM.

Status should be determined by deterministic rules using:

- Evidence count
- New evidence velocity
- Supporting thesis count
- Conflict count
- Source diversity
- Recency
- Knowledge evolution trends
- Explicit contradiction records

---

## Confidence Model

Confidence should be deterministic and explainable.

Allowed values:

- low
- medium
- high

Potential deterministic rules:

- Low confidence: limited evidence, single source, no repeated support
- Medium confidence: multiple evidence records or repeated mentions
- High confidence: repeated support across multiple sources, themes, or time periods

Confidence should always include:

- confidence level
- reason
- evidence count
- conflict count
- source count
- last updated

---

## New CLI Commands

v5.0 should introduce:

```bash
python -m constellation ai-markets build
python -m constellation ai-markets status
python -m constellation ai-markets themes
python -m constellation ai-markets theme THEME_ID
python -m constellation ai-markets entities
python -m constellation ai-markets catalysts
python -m constellation ai-markets risks
python -m constellation ai-markets questions
python -m constellation ai-markets report
python -m constellation ai-markets export
```

---

## Outputs

v5.0 should create:

```text
outputs/ai-markets/

ai-markets.json
themes.json
entities.json
catalysts.json
risks.json
open-questions.json
ai-markets-report.md
theme-map.md
watchlist.md
```

---

## AI & Markets Report

The primary user-facing artifact should be:

```text
outputs/ai-markets/ai-markets-report.md
```

The report should include:

1. Executive Summary
2. What Changed
3. Strongest Themes
4. Weakening Themes
5. New Evidence
6. Key Companies / Assets
7. Catalysts
8. Risks
9. Open Questions
10. Watchlist
11. Portfolio / Allocation Implications
12. Content Ideas
13. Evidence References
14. Provenance
15. Limitations

---

## Morning Workflow Integration

The Morning workflow should eventually produce:

```text
outputs/reports/latest-report.md
outputs/dashboard/dashboard.md
outputs/ai-markets/ai-markets-report.md
```

Updated Morning workflow:

```text
Source Monitoring
        ↓
Google Drive Sync
        ↓
Intake Import
        ↓
Research Processing
        ↓
Knowledge Graph
        ↓
Institutional Memory
        ↓
Knowledge Evolution
        ↓
Evidence Graph
        ↓
Thesis Intelligence
        ↓
Institutional Research Report
        ↓
AI & Markets Intelligence
        ↓
Executive Dashboard
```

---

## Dashboard Integration

The Executive Dashboard should include an AI & Markets Summary:

- Active themes
- Strengthening themes
- Weakening themes
- High-conviction themes
- New evidence count
- Key companies / assets mentioned
- Upcoming catalysts
- Top risks
- Open questions
- Latest AI & Markets report path

---

## Example Dashboard Output

```text
AI & Markets Summary

Active Themes: 9
Strengthening Themes: 4
Weakening Themes: 1
High Conviction Themes: 3

Strengthening:
- AI Infrastructure
- Power Grid
- Robotics
- Bitcoin

Weakening:
- Unprofitable AI Software

Top Risks:
- AI capex slowdown
- Power bottlenecks
- Valuation compression

Open Questions:
- Is enterprise AI monetization accelerating?
- Is Bitcoin becoming institutional collateral?
- Are robotics entering commercial adoption?
```

---

## Content Creation Use Case

AI & Markets Intelligence should support social content creation.

Potential outputs:

```text
outputs/ai-markets/content-ideas.md
```

Sections:

- X post ideas
- LinkedIn post ideas
- Instagram carousel ideas
- Long-form article ideas
- Charts or visuals to create
- Themes worth revisiting

The system should not generate final posts autonomously in v5.0.

It should identify evidence-backed content opportunities.

---

## Investment Research Use Case

AI & Markets Intelligence should support investment research.

Potential outputs:

```text
outputs/ai-markets/watchlist.md
```

Sections:

- Companies mentioned
- Assets mentioned
- Related themes
- Supporting evidence
- Risks
- Catalysts
- Confidence
- Recent changes

This is not investment advice.

It is a research organization layer.

---

## Real Estate Separation

AI & Markets Intelligence should remain separate from future Real Estate Intelligence.

Shared foundation:

- Evidence
- Memory
- Graph
- Workflow
- Dashboard
- Reports

Separate domain layers:

- AI & Markets
- Real Estate / Appraisal
- Capital Allocation
- Personal Operating System

---

## Safety Principles

v5.0 must preserve the deterministic core.

Do not add:

- OpenAI calls
- Provider execution
- LLM inference
- Embeddings
- Semantic search
- Web retrieval
- Gmail
- Autonomous decisions
- Trading execution
- Financial advice

All domain intelligence must be derived from local artifacts, explicit evidence, deterministic rules, and complete provenance.

---

## Success Criteria

v5.0 is successful if, after running:

```bash
python -m constellation workflow run Morning
python -m constellation ai-markets report
```

the user receives a useful AI & Markets research report that clearly shows:

- What changed
- Which themes matter
- Which evidence supports them
- Which risks are rising
- Which companies or assets are implicated
- What questions remain open
- What should be reviewed next

The report should be good enough to guide the user’s daily research process.

---

## Strategic Importance

v5.0 is the first domain-intelligence release.

It proves that Constellation is not merely a platform for organizing information.

It is a platform for building specialized institutional intelligence systems.

AI & Markets is the first domain.

Future domains can include:

- Portfolio Intelligence
- Capital Allocation Intelligence
- Real Estate Intelligence
- Appraisal Review Intelligence
- Executive Operating Intelligence

The long-term vision is a multi-domain institutional operating system built on deterministic evidence, persistent memory, workflow orchestration, and optional AI-assisted reasoning layered only after the deterministic foundation is complete.
