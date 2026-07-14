# Constellation v5.0 — AI & Markets Intelligence

## Product Vision

Constellation v5.0 marks the transition from a deterministic intelligence platform into an Institutional Investment Operating System.

Constellation AI is not an AI investing tool. It is designed to improve investment judgment over time by converting research into intelligence, intelligence into understanding, understanding into decisions, and decisions into learning.

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

The goal is not to predict markets automatically. The goal is to build durable institutional capability around market awareness, contextual understanding, decision support, and learning.

## Capability Roadmap

Constellation AI follows a capability-centric roadmap:

| Phase | Versions | Capability | Primary Question |
| --- | --- | --- | --- |
| Observe | v5.0.x | Intelligence | What is happening? |
| Understand | v5.1.x - v5.3.x | Contextual Understanding | Why does it matter? |
| Decide | v5.4.x - v5.5.x | Judgment Support | What should I do today from a research and decision-support standpoint? |
| Improve | v6.0.x | Performance Intelligence | How can I become a better investor? |

Each release adds a durable institutional capability rather than a standalone feature.

## v5.0.1 Signal Refinement

v5.0.1 refines the MVP output into a more executive-useful signal layer.

Open questions are now normalized and deduplicated deterministically. The full archive remains in `outputs/ai-markets/open-questions.json`, while the top prioritized executive questions are written to:

- `outputs/ai-markets/executive-questions.json`
- `outputs/ai-markets/executive-questions.md`

Question priority is deterministic. High-priority questions are those linked to multiple themes, multiple evidence records, high-priority entities, or explicit terms such as risk, bottleneck, catalyst, liquidity, capex, power, margin, regulation, adoption, acceleration, slowdown, contradiction, or weakening.

Entity detection now recognizes a broader fixed set of tickers, assets, and company-name aliases including NVDA, AMD, AVGO, MSFT, GOOGL, GOOG, AMZN, META, TSLA, PLTR, ORCL, CRWV, IREN, COIN, MSTR, IBM, NOW, INTC, MRVL, GFS, AMKR, BTC, ETH, GLD, SLV, URA, XME, and COPX. Matching remains token/regex based only; no semantic similarity, embeddings, providers, or web retrieval are used.

## v5.1.0 Theme Lifecycle

v5.1.0 turns AI & Markets Intelligence from a point-in-time snapshot into a deterministic longitudinal research layer.

Each theme receives a lifecycle status:

- `emerging`
- `active`
- `strengthening`
- `high_conviction`
- `weakening`
- `contradicted`
- `archived`

Lifecycle status is derived from deterministic counts only: evidence count, source count, entity count, risk count, prior status, prior confidence, and explicit contradiction or conflict language. It does not infer investment conclusions and does not use AI, providers, embeddings, semantic similarity, web retrieval, or trading systems.

Lifecycle outputs:

- `outputs/ai-markets/theme-lifecycle.json`
- `outputs/ai-markets/theme-lifecycle.md`
- `outputs/ai-markets/theme-history.json`
- `outputs/ai-markets/theme-transitions.json`
- `outputs/ai-markets/theme-timeline.md`

Lifecycle commands:

```bash
python -m constellation ai-markets lifecycle
python -m constellation ai-markets lifecycle --export
python -m constellation ai-markets lifecycle --history
python -m constellation ai-markets lifecycle --transitions
python -m constellation ai-markets theme THEME_ID
```

The AI & Markets report includes a Theme Lifecycle section, and the Executive Dashboard includes lifecycle counts, high-conviction themes, strengthening themes, weakening themes, and the lifecycle report path.

## v5.2.0 Portfolio Intelligence

v5.2.0 adds deterministic Portfolio Intelligence for AI & Markets research organization.

This is not trading software and is not financial advice. It does not generate buy, sell, or allocation recommendations. It maps optional local portfolio/watchlist config and detected entities to themes, lifecycle status, risks, open questions, and research priority.

Optional local config:

- `config/portfolio.yaml`
- `config/portfolio.local.yaml`

These files are gitignored. Use `config/portfolio.example.yaml` as a non-private template.

Portfolio Intelligence commands:

```bash
python -m constellation ai-markets portfolio
python -m constellation ai-markets portfolio --export
python -m constellation ai-markets portfolio --exposures
python -m constellation ai-markets portfolio --risks
python -m constellation ai-markets portfolio --watchlist
python -m constellation ai-markets portfolio --questions
python -m constellation ai-markets portfolio --history
python -m constellation ai-markets portfolio --delta
```

Outputs:

- `outputs/ai-markets/portfolio/portfolio-intelligence.json`
- `outputs/ai-markets/portfolio/portfolio-intelligence.md`
- `outputs/ai-markets/portfolio/portfolio-exposures.json`
- `outputs/ai-markets/portfolio/portfolio-exposures.md`
- `outputs/ai-markets/portfolio/portfolio-risks.json`
- `outputs/ai-markets/portfolio/portfolio-risks.md`
- `outputs/ai-markets/portfolio/portfolio-watchlist.json`
- `outputs/ai-markets/portfolio/portfolio-watchlist.md`
- `outputs/ai-markets/portfolio/portfolio-questions.json`
- `outputs/ai-markets/portfolio/portfolio-questions.md`
- `outputs/ai-markets/portfolio/portfolio-history.json`
- `outputs/ai-markets/portfolio/portfolio-delta.json`

If no local config exists, Portfolio Intelligence runs in `detected_entities_only` mode using the entities already detected by AI & Markets Intelligence.

## v5.3.0 Catalyst Monitoring

v5.3.0 adds deterministic Catalyst Monitoring for AI & Markets research organization.

Catalyst Monitoring identifies explicit catalyst language already present in local Constellation artifacts. It does not retrieve new market data, monitor markets autonomously, predict outcomes, or provide financial advice.

Initial catalyst categories include:

- `earnings`
- `fed_policy`
- `inflation`
- `employment`
- `liquidity`
- `credit`
- `capex`
- `product_launch`
- `regulation`
- `energy_power`
- `supply_chain`
- `geopolitical`
- `crypto_etf_flows`
- `bitcoin_halving_cycle`
- `commodity_supply`
- `ai_infrastructure`
- `semiconductor_cycle`
- `enterprise_ai_adoption`
- `defense_policy`
- `nuclear_policy`
- `robotics_adoption`
- `technical_breakout`
- `technical_breakdown`
- `risk_event`
- `unknown`

Commands:

```bash
python -m constellation ai-markets catalysts
python -m constellation ai-markets catalysts --monitor
python -m constellation ai-markets catalysts --priorities
python -m constellation ai-markets catalysts --calendar
python -m constellation ai-markets catalysts --history
python -m constellation ai-markets catalysts --delta
python -m constellation ai-markets catalysts --transitions
python -m constellation ai-markets catalysts --export
```

Outputs:

- `outputs/ai-markets/catalysts/catalyst-monitor.json`
- `outputs/ai-markets/catalysts/catalyst-monitor.md`
- `outputs/ai-markets/catalysts/catalyst-priorities.json`
- `outputs/ai-markets/catalysts/catalyst-priorities.md`
- `outputs/ai-markets/catalysts/catalyst-history.json`
- `outputs/ai-markets/catalysts/catalyst-delta.json`
- `outputs/ai-markets/catalysts/catalyst-transitions.json`
- `outputs/ai-markets/catalysts/catalyst-calendar.md`

Priority is deterministic and based on explicit links to themes, risks, lifecycle status, portfolio/watchlist exposure, evidence counts, source counts, and high-impact catalyst terms such as FOMC, CPI, PCE, earnings, guidance, capex, liquidity, credit, breakout, breakdown, regulation, power bottleneck, and export controls.

## v5.4.0 Decision Journal

v5.4.0 adds a deterministic Decision Journal for AI & Markets research memory.

This layer parses optional private Markdown entries from gitignored local folders, links them to existing AI & Markets artifacts by exact matches, and produces review queues, timelines, outcomes, links, history, and deltas.

Private local entries:

- `journal/ai-markets/*.md`
- `journal/ai-markets/*.yaml`
- `journal/ai-markets/*.json`

These paths are gitignored. Use `journal/examples/ai-markets-decision.example.md` as a non-private example.

Commands:

```bash
python -m constellation ai-markets decisions
python -m constellation ai-markets decisions --entries
python -m constellation ai-markets decisions --queue
python -m constellation ai-markets decisions --timeline
python -m constellation ai-markets decisions --outcomes
python -m constellation ai-markets decisions --history
python -m constellation ai-markets decisions --delta
python -m constellation ai-markets decisions --create-template
```

Outputs:

- `outputs/ai-markets/decisions/decision-journal.json`
- `outputs/ai-markets/decisions/decision-journal.md`
- `outputs/ai-markets/decisions/decision-entries.json`
- `outputs/ai-markets/decisions/decision-timeline.md`
- `outputs/ai-markets/decisions/decision-review-queue.json`
- `outputs/ai-markets/decisions/decision-review-queue.md`
- `outputs/ai-markets/decisions/decision-links.json`
- `outputs/ai-markets/decisions/decision-outcomes.json`
- `outputs/ai-markets/decisions/decision-history.json`
- `outputs/ai-markets/decisions/decision-delta.json`

Decision Journal is research memory only. It is not financial advice, trading software, or an autonomous decision maker.

## v5.5.0 Executive Morning Brief

v5.5.0 adds the AI & Markets Executive Morning Brief, the primary daily user-facing artifact for the AI & Markets domain.

The brief consolidates deterministic local outputs from:

- AI & Markets Intelligence
- Theme Lifecycle
- Portfolio Intelligence
- Catalyst Monitoring
- Decision Journal
- Institutional Research Reports
- Executive Dashboard
- Daily and morning platform outputs

Commands:

```bash
python -m constellation ai-markets brief
python -m constellation ai-markets brief --export
python -m constellation ai-markets brief --agenda
python -m constellation ai-markets brief --history
python -m constellation ai-markets brief --delta
```

Outputs:

- `outputs/ai-markets/briefings/morning-brief.json`
- `outputs/ai-markets/briefings/morning-brief.md`
- `outputs/ai-markets/briefings/research-agenda.json`
- `outputs/ai-markets/briefings/research-agenda.md`
- `outputs/ai-markets/briefings/brief-history.json`
- `outputs/ai-markets/briefings/brief-delta.json`

The brief includes a header, executive summary, top five priorities, what changed, theme lifecycle snapshot, portfolio/watchlist review, catalyst monitor, decision and performance review, risks, recommended reading, limitations, provenance, and appendix.

v6.1.1 refines the Executive Morning Brief for daily executive use:

- The main brief shows no more than five top priorities.
- Raw evidence fragments, URLs, timestamp links, `None` placeholders, and Markdown remnants are excluded from the main executive sections.
- Catalyst, risk, and agenda items are deduplicated through deterministic normalization only.
- Catalyst titles prefer structured category/theme/entity fields over raw source excerpts.
- The full research agenda remains available in `outputs/ai-markets/briefings/research-agenda.md`.
- Supporting IDs, source paths, unavailable artifacts, and deterministic limitations move to the appendix and provenance sections.

Research agenda structure:

- Top 5 Executive Priorities
- Remaining High Priority
- Medium Priority
- Low Priority
- Appendix / Provenance

It is deterministic only. It does not perform market prediction, retrieve web data, call providers, provide financial advice, or make autonomous decisions.

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
- `outputs/ai-markets/executive-questions.json`
- `outputs/ai-markets/executive-questions.md`
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
