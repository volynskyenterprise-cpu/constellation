# Constellation

> **Current Status - Multi-Domain Intelligence Platform (v7.0)**
>
> Constellation AI is an Institutional Investment Operating System.
>
> It improves investment judgment over time by converting research into intelligence, intelligence into understanding, understanding into decisions, and decisions into learning.
>
> The system is not an AI investing tool. It is a deterministic operating system for institutional research, signal processing, decision support, and learning.

**No hallucinations.**

**No hidden reasoning.**

**No opaque decision making.**

**Everything is explainable.**

---

# Why Constellation Exists

Most AI systems generate answers.

Constellation generates **evidence-backed institutional knowledge**.

Every artifact produced by the platform can be traced back to:

- Original source document
- Evidence record
- Knowledge Graph node
- Cross-document finding
- Institutional thesis
- Executive Intelligence Brief

Nothing is inferred without evidence.

Everything remains deterministic, reproducible, and governed by humans.

---

# PKOS Smart Sync

PKOS Smart Sync replaces broad end-of-day PKOS staging with a governed preview-first workflow:

```powershell
python -m constellation pkos sync preview --export
python -m constellation pkos sync stage --approved-only
python -m constellation pkos sync commit
python -m constellation pkos sync push
```

Preview is read-only. Staging uses explicit approved paths only. Commit verifies the staged manifest against the approval record. Push requires a Smart Sync commit and never force pushes.

Secret-risk files are blocked, generated/runtime files are excluded, and draft or unknown files require review.
Policy refinement in v7.2.6 keeps daily previews smaller by excluding AOC intake runtime noise before broad governed-operation rules can apply. Use `python -m constellation pkos sync preview --explain PATH` to inspect a single classification decision.
Secret false-positive hardening in v7.2.7 distinguishes harmless credential-object references, such as `creds.refresh_token`, from literal secret values. Hardcoded keys, token prefixes, private key material, credential blobs, and secret-risk paths remain blocked.

---

# Core Principles

Constellation is built around six principles:

- Deterministic execution
- Evidence before conclusions
- Complete provenance
- Explainable reasoning
- Human governance
- Provider-agnostic architecture

---

# Capabilities

Current institutional capabilities include:

- PKOS Smart Sync
- ✅ Research Organization
- ✅ PKOS Knowledge Organization
- ✅ Evidence Engine
- ✅ Knowledge Graph
- ✅ Evidence Graph
- ✅ Cross-Document Reasoning
- ✅ Thesis Engine
- ✅ Thesis Intelligence
- ✅ Daily Intelligence Pipeline
- ✅ Executive Dashboard
- ✅ Source Monitoring
- Workflow Automation Engine
- Knowledge Evolution Engine
- Institutional Research Reports
- AI & Markets Intelligence
- Real Estate Assignment Intelligence
- ✅ Institutional Intelligence Platform
- ✅ Operational Intake Pipeline
- ✅ Google Drive Connector
- ✅ Morning Executive Intelligence
- ✅ Institutional Memory
- ✅ Executive Intelligence Brief generation
- ✅ Deterministic provenance tracking
- ✅ Human approval workflow
- ✅ Comprehensive automated testing

---

# Architecture

```text
Research Sources
        │
        ▼
 Intake Pipeline
        │
        ▼
Research Organization
        │
        ▼
Evidence Engine
        │
        ▼
Knowledge Graph
        │
        ▼
Evidence Graph
        │
        ▼
Cross-Document Reasoning
        │
        ▼
Thesis Engine
        │
        ▼
Thesis Intelligence
        │
        ▼
Daily Intelligence Pipeline
        │
        ▼
Executive Dashboard
        │
        ▼
Source Monitoring
        │
        ▼
Institutional Intelligence
        │
        ▼
Executive Intelligence Brief
```

Every stage preserves complete provenance and remains deterministic.

---

# Installation

Clone the repository:

```bash
git clone https://github.com/volynskyenterprise-cpu/constellation.git

cd constellation
```

Install locally:

```bash
pip install -e .
```

Verify installation:

```bash
python -m constellation health
```

---

# Quick Start

### 1. Import research

```bash
python -m constellation intake scan

python -m constellation intake import
```

---

### 2. Run research workflow

```bash
python -m constellation research run research_inputs/document.md
```

---

### 3. Build the Knowledge Graph

```bash
python -m constellation graph build RUN_ID
```

---

### 4. Build the Evidence Graph

```bash
python -m constellation evidence-graph build
```

---

### 5. Analyze cross-document findings

```bash
python -m constellation graph analyze
```

---

### 6. Generate institutional theses

```bash
python -m constellation thesis generate
```

---

### 7. Generate executive intelligence

```bash
python -m constellation intelligence generate
```

---

# Example Workflow

```text
Moonshots Summary
        │
        ▼
Research Input
        │
        ▼
Evidence Records
        │
        ▼
Knowledge Graph
        │
        ▼
Evidence Graph
        │
        ▼
Cross-Document Findings
        │
        ▼
Institutional Theses
        │
        ▼
Executive Intelligence Brief
```

---

# Repository Structure

```text
src/
    constellation/

research_inputs/

pkos_inputs/

memory/

outputs/

docs/

tests/

config/

inbox/

workflows/

real-estate/
```

---

# CLI Overview

### Intake

```bash
python -m constellation intake scan
python -m constellation intake import
python -m constellation intake status
```

### Google Drive

```bash
pip install -e .[google-drive]
python -m constellation drive status
python -m constellation drive sync --dry-run
python -m constellation drive sync
```

Drive sync stages files into `inbox/google-drive/incoming/` only. It does not run intake import or downstream workflows automatically.

### Morning Executive Intelligence

```bash
python -m constellation morning
python -m constellation morning --export
python -m constellation morning --overwrite
```

Morning briefs report current deterministic local state only. They do not run upstream workflows or call providers.

### Institutional Memory

```bash
python -m constellation memory snapshot --label baseline
python -m constellation memory list
python -m constellation memory diff
python -m constellation memory export
```

Institutional Memory preserves historical snapshots of deterministic local state and compares snapshots without LLM inference or provider calls.

### Daily Intelligence Pipeline

```bash
python -m constellation daily
python -m constellation daily --overwrite
python -m constellation daily status
python -m constellation daily history
python -m constellation daily export
```

Daily Pipeline orchestrates intake scan, optional Google Drive sync readiness, morning brief, memory snapshot, Evidence Graph, and Thesis Intelligence into `outputs/daily/`. It does not call providers, run LLM inference, or make autonomous decisions.

If Google Drive requires re-authentication, Daily Pipeline records a connector warning and continues from existing local artifacts where possible.

### Executive Dashboard

```bash
python -m constellation dashboard
python -m constellation dashboard --export
python -m constellation dashboard --overwrite
python -m constellation dashboard status
```

Executive Dashboard presents current local Constellation state from existing outputs only. It reports missing artifacts as unavailable and writes `outputs/dashboard/dashboard.json` and `outputs/dashboard/dashboard.md`. It also summarizes connector warnings such as Google Drive `needs_reauth` events when available.

### Real Estate Assignment Intelligence

```bash
python -m constellation real-estate assignments
python -m constellation real-estate assignment create-template ASSIGNMENT_ID
python -m constellation real-estate assignment build ASSIGNMENT_ID
python -m constellation real-estate assignment status ASSIGNMENT_ID
python -m constellation real-estate assignment sources ASSIGNMENT_ID
python -m constellation real-estate assignment missing ASSIGNMENT_ID
python -m constellation real-estate assignment risks ASSIGNMENT_ID
python -m constellation real-estate assignment export ASSIGNMENT_ID
```

Real Estate Assignment Intelligence is the first Real Estate Intelligence capability. It organizes local assignment metadata, source-file metadata, missing information, exact structured conflicts, assignment risks, and review timelines. It does not generate value opinions, comparable selections, adjustments, USPAP opinions, or appraisal conclusions.

Private assignment files belong under `real-estate/assignments/<ASSIGNMENT_ID>/` and are ignored by Git. Public examples live in `real-estate/examples/`.

Structured facts are optional. Empty fact values are omitted; `unit`, `notes`, and other metadata fields are never substituted as values.

Assignment Auto-Ingestion reduces setup friction by creating private assignment files directly from structured local intake artifacts:

```bash
python -m constellation real-estate intake status
python -m constellation real-estate intake scan
python -m constellation real-estate intake import
python -m constellation real-estate intake import --file PATH
```

Target flow:

```text
Structured assignment intake artifact
    -> assignment detected
    -> canonical assignment resolved
    -> private canonical case folder created or merged
    -> assignment.yaml populated from explicit fields
    -> sources referenced or copied
    -> Assignment Intelligence built
    -> assignment brief generated
    -> dashboard refreshed
```

Use `config/real-estate-intake.example.yaml` as a placeholder template for optional PKOS/AOC or other local structured intake sources. Real paths belong only in gitignored local config. `source_mode: reference` preserves original paths without copying files; `source_mode: copy` copies files from configured roots into the private assignment `sources/` directory.

Assignment Consolidation groups multiple artifacts for the same real-world assignment into one canonical assignment view:

```bash
python -m constellation real-estate consolidation
python -m constellation real-estate consolidation status
python -m constellation real-estate consolidation clusters
python -m constellation real-estate consolidation conflicts
python -m constellation real-estate consolidation relationships
```

It reports Assignments, Artifacts, Knowledge Packs, assignments with reviewer notes, assignments with conflicts, and top active assignments. Consolidation uses exact IDs, normalized addresses, dates, and structured field overlap only. It does not use semantic similarity or valuation inference.

v7.1.2 adds Identity Resolution refinements: HTML entity cleanup, source companion pairing for matching JSON/Markdown stems, assignment aliases, unassigned artifacts, true identity conflict reporting, and unit-aware address normalization.

v7.2.0 adds the Canonical Assignment Model. Assignment Consolidation remains the identity-resolution layer; the Canonical Assignment Model is now the persistence and operational layer. New intake writes to one canonical directory per real-world assignment, preserves aliases, and stops creating separate Gmail/Axis/address-derived assignment directories for the same assignment.

v7.2.1 hardens Canonical Operations. Canonical status, migration plan, review queue, operations report, and dashboard summaries now use the same migration state. Migration items are categorized as `safe_merge`, `preserve_alias`, `blocked_by_conflict`, `ambiguous`, `orphan`, or `already_migrated`, and review queues are written for human operator review.

v7.2.2 adds scoped canonical migration controls. Use `--ready-only` to apply only migration-ready alias entries. Blocked, ambiguous, orphan, and already-migrated entries are never applied by `--ready-only`, and unsafe unscoped apply is refused when a plan contains mixed categories.

v7.2.3 fixes post-migration count integrity. A directory with a valid `canonical-migration.json` marker is treated as `migrated_alias`: preserved on disk and counted in migration audit state, but excluded from normal canonical assignment and source-artifact discovery. Repeated canonical refreshes must not inflate assignment, artifact, or alias counts.

v7.2.4 adds Real Estate Daily Automation to the Morning workflow. The daily loop runs deterministic Real Estate intake, Assignment Consolidation, Canonical Assignment refresh, affected Assignment Intelligence builds, Canonical Operations, and dashboard refresh. It writes `outputs/real-estate/daily/latest-real-estate-daily-run.json` and `outputs/real-estate/daily/real-estate-daily-report.md`, and it does not apply migration, resolve conflicts, generate valuation opinions, select comparables, create adjustments, interpret permits, or make USPAP conclusions.

```bash
python -m constellation real-estate daily
python -m constellation real-estate daily status
python -m constellation real-estate daily history
python -m constellation real-estate daily export
```

The scheduled Morning launcher opens Real Estate daily review files only when Real Estate activity, warnings, errors, or review queue items exist. VS Code launch failures are logged without failing the Morning workflow.

```bash
python -m constellation real-estate canonical status
python -m constellation real-estate canonical assignments
python -m constellation real-estate canonical aliases
python -m constellation real-estate canonical resolve ALIAS
python -m constellation real-estate canonical migration-plan
python -m constellation real-estate canonical review
python -m constellation real-estate canonical review --blocked
python -m constellation real-estate canonical review --safe
python -m constellation real-estate canonical review --ambiguous
python -m constellation real-estate canonical operations
python -m constellation real-estate canonical report
python -m constellation real-estate canonical conflicts
python -m constellation real-estate canonical migrate --dry-run
python -m constellation real-estate canonical migrate --ready-only --list-selected
python -m constellation real-estate canonical migrate --dry-run --ready-only
python -m constellation real-estate canonical migrate --apply --ready-only
python -m constellation real-estate canonical migrate --dry-run --category preserve_alias
python -m constellation real-estate canonical migrate --apply --assignment CANONICAL_ASSIGNMENT_ID --ready-only
python -m constellation real-estate canonical migrate --apply --source-assignment SOURCE_ASSIGNMENT_ID
python -m constellation real-estate canonical migrate --apply
python -m constellation real-estate canonical export
python -m constellation real-estate assignments --include-aliases
python -m constellation real-estate assignment show ALIAS
```

Canonical migration is non-destructive. Dry-run inspects existing alias directories and writes a plan; apply marks alias directories as migrated and preserves rollback metadata, but does not delete source artifacts or assignment directories. Assignment commands accept canonical IDs, order IDs, loan numbers, source-generated aliases, address aliases, and previous canonical IDs when they resolve unambiguously.

Scoped migration is the recommended operator path:

1. Review canonical state with `python -m constellation real-estate canonical review`.
2. Inspect ready entries with `python -m constellation real-estate canonical migrate --ready-only --list-selected`.
3. Dry-run with `python -m constellation real-estate canonical migrate --dry-run --ready-only`.
4. Apply only ready entries with `python -m constellation real-estate canonical migrate --apply --ready-only`.

Blocked, ambiguous, and orphan entries remain in the review queue for human review.

### Source Monitoring

```bash
python -m constellation monitor
python -m constellation monitor --overwrite
python -m constellation monitor status
python -m constellation monitor history
python -m constellation monitor export
```

Source Monitoring tracks configured and local intelligence sources over time, reports new/removed/updated/failed sources, and recommends deterministic downstream refreshes. It does not call remote APIs or modify source data.

### Workflow Automation

```bash
python -m constellation workflow list
python -m constellation workflow run Morning
python -m constellation workflow history
python -m constellation workflow show Morning
python -m constellation workflow export
```

Workflow Automation runs named deterministic recipes made from existing Constellation commands. Built-in workflows include `Morning`, `Research Refresh`, and `Executive Snapshot`. The `Morning` workflow imports intake files, processes newly imported markdown/text research inputs, builds graph records for the generated research runs, and refreshes downstream deterministic intelligence outputs. Workflow execution occurs only when explicitly invoked and does not add provider calls, LLM inference, Gmail, web retrieval, embeddings, semantic search, scheduling, or autonomous decisions.

If Google Drive OAuth has expired or been revoked, the Google Drive step is marked degraded with a `needs_reauth` connector warning. Morning continues using existing local artifacts where possible. Refresh the local token with:

```bash
python -m constellation drive sync --dry-run
```

### Automated Daily Routine

The Windows Morning launcher is `tools/run_constellation_morning.bat`. The local Task Scheduler task runs it daily at 6:45 AM.

After a successful Morning workflow, the launcher opens the concise AI & Markets Executive Morning Brief and Performance Learning Loop in Visual Studio Code:

- `outputs/ai-markets/briefings/morning-brief.md`
- `outputs/performance/learning-loop.md`

The Task Scheduler task must use **Run only when user is logged on** because Visual Studio Code is opened interactively. If the `code` command is unavailable, the launcher logs a warning and preserves the Morning workflow exit code.

Manual fallback:

```bash
python -m constellation workflow run Morning
python -m constellation ai-markets brief
python -m constellation performance
code -r outputs/ai-markets/briefings/morning-brief.md outputs/performance/learning-loop.md
```

### Knowledge Evolution

```bash
python -m constellation evolution
python -m constellation evolution status
python -m constellation evolution history
python -m constellation evolution export
python -m constellation evolution compare SNAPSHOT_A SNAPSHOT_B
```

Knowledge Evolution compares longitudinal institutional state from existing local artifacts. It reports evidence gained/removed, graph growth, thesis changes, source activity trends, research volume trends, workflow execution trends, and a deterministic longitudinal health score.

### Institutional Research Reports

```bash
python -m constellation report latest
python -m constellation report latest --export
python -m constellation report status
python -m constellation report history
python -m constellation report show REPORT_ID
```

Institutional Research Reports turn existing dashboard, daily, morning, evolution, thesis, evidence graph, memory, source monitor, workflow, intake, and Google Drive artifacts into polished Markdown research reports. Reports are deterministic presentation artifacts and do not call providers or infer unsupported claims.

### AI & Markets Intelligence

```bash
python -m constellation ai-markets build
python -m constellation ai-markets status
python -m constellation ai-markets themes
python -m constellation ai-markets entities
python -m constellation ai-markets risks
python -m constellation ai-markets questions
python -m constellation ai-markets questions --executive
python -m constellation ai-markets lifecycle
python -m constellation ai-markets lifecycle --history
python -m constellation ai-markets lifecycle --transitions
python -m constellation ai-markets theme THEME_ID
python -m constellation ai-markets portfolio
python -m constellation ai-markets portfolio --exposures
python -m constellation ai-markets portfolio --risks
python -m constellation ai-markets portfolio --watchlist
python -m constellation ai-markets portfolio --questions
python -m constellation ai-markets catalysts
python -m constellation ai-markets catalysts --priorities
python -m constellation ai-markets catalysts --calendar
python -m constellation ai-markets decisions
python -m constellation ai-markets decisions --queue
python -m constellation ai-markets decisions --create-template
python -m constellation ai-markets brief
python -m constellation ai-markets brief --agenda
python -m constellation ai-markets report
python -m constellation ai-markets export
```

AI & Markets Intelligence classifies existing local Constellation artifacts into deterministic themes, entities, catalysts, risks, prioritized executive questions, watchlists, and content ideas. Theme Lifecycle tracks whether each theme is emerging, active, strengthening, high conviction, weakening, contradicted, or archived. Portfolio Intelligence maps optional local portfolio/watchlist config and detected entities to themes, lifecycle statuses, risks, and review priorities. Catalyst Monitoring organizes catalyst categories, time horizons, priorities, risks, and changes. Decision Journal preserves private local research memory. v5.5.0 adds the Executive Morning Brief, the primary daily AI & Markets briefing artifact. v6.1.1 refines it into a concise top-five executive brief with supporting details moved to the appendix and full research agenda. It uses fixed keyword and exact matching only and does not provide financial advice or trading recommendations.

Local portfolio config is optional. Use `config/portfolio.example.yaml` as a template, and keep real local configs in `config/portfolio.yaml` or `config/portfolio.local.yaml`, which are gitignored.

Key outputs:

- `outputs/ai-markets/ai-markets-report.md`
- `outputs/ai-markets/open-questions.json`
- `outputs/ai-markets/executive-questions.json`
- `outputs/ai-markets/executive-questions.md`
- `outputs/ai-markets/theme-lifecycle.json`
- `outputs/ai-markets/theme-lifecycle.md`
- `outputs/ai-markets/theme-history.json`
- `outputs/ai-markets/theme-transitions.json`
- `outputs/ai-markets/theme-timeline.md`
- `outputs/ai-markets/portfolio/portfolio-intelligence.md`
- `outputs/ai-markets/portfolio/portfolio-exposures.json`
- `outputs/ai-markets/portfolio/portfolio-risks.json`
- `outputs/ai-markets/portfolio/portfolio-watchlist.json`
- `outputs/ai-markets/catalysts/catalyst-monitor.md`
- `outputs/ai-markets/catalysts/catalyst-priorities.json`
- `outputs/ai-markets/catalysts/catalyst-calendar.md`
- `outputs/ai-markets/decisions/decision-journal.md`
- `outputs/ai-markets/decisions/decision-review-queue.md`
- `outputs/ai-markets/decisions/decision-timeline.md`
- `outputs/ai-markets/briefings/morning-brief.md`
- `outputs/ai-markets/briefings/research-agenda.md`
- `outputs/ai-markets/watchlist.md`

### Performance Intelligence

```bash
python -m constellation performance
python -m constellation performance review
python -m constellation performance decisions
python -m constellation performance thesis
python -m constellation performance thesis --scoreboard
python -m constellation performance thesis --delta
python -m constellation performance signals
python -m constellation performance lessons
python -m constellation performance export
python -m constellation performance history
python -m constellation performance delta
```

Performance Intelligence closes the loop between AI & Markets decisions, later evidence, theme lifecycle changes, catalyst follow-ups, portfolio/watchlist reviews, thesis accuracy, and process lessons. The v6.1.0 layer adds deterministic Thesis Accuracy scoring from existing thesis, evidence, decision, catalyst, memory, evolution, and performance artifacts.

This is not financial advice, client performance reporting, a trading system, or an autonomous investment system. It does not produce investment instructions, expected return estimates, price targets, autonomous allocation changes, or trading actions.

Key outputs:

- `outputs/performance/performance-intelligence.md`
- `outputs/performance/performance-intelligence.json`
- `outputs/performance/decision-outcomes.md`
- `outputs/performance/performance-signals.md`
- `outputs/performance/process-lessons.md`
- `outputs/performance/learning-loop.md`
- `outputs/performance/thesis-accuracy.md`
- `outputs/performance/thesis-accuracy.json`
- `outputs/performance/thesis-scoreboard.md`
- `outputs/performance/thesis-history.json`
- `outputs/performance/thesis-delta.json`
- `outputs/performance/performance-history.json`
- `outputs/performance/performance-delta.json`

### Research

```bash
python -m constellation research run
```

### Knowledge Graph

```bash
python -m constellation graph build
python -m constellation graph analyze
python -m constellation graph findings
```

### Evidence Graph

```bash
python -m constellation evidence-graph build
python -m constellation evidence-graph nodes
python -m constellation evidence-graph edges
python -m constellation evidence-graph show NODE_OR_EDGE_ID
python -m constellation evidence-graph export
```

Evidence Graph shows exact-ID relationships between evidence, sources, artifacts, findings, theses, morning briefs, and institutional memory snapshots. It does not infer semantic relationships or call providers.

### Thesis Engine

```bash
python -m constellation thesis build
python -m constellation thesis generate
python -m constellation thesis list
python -m constellation thesis show THESIS_ID
python -m constellation thesis timeline THESIS_ID
python -m constellation thesis export
```

`thesis build` maintains deterministic Thesis Intelligence records under `outputs/thesis/`, including support, conflicts, confidence, timeline events, morning brief references, and memory snapshot references.

### Intelligence Platform

```bash
python -m constellation intelligence generate
python -m constellation intelligence show
python -m constellation intelligence export
```

---

# Design Philosophy

Constellation intentionally avoids black-box AI.

The platform emphasizes:

- deterministic execution
- evidence-first reasoning
- explainability
- provenance preservation
- reproducibility
- institutional governance
- provider independence

Professional judgment should become **more transparent**, not less.

---

# What Constellation Is NOT

Constellation is intentionally **not**:

- an autonomous AI agent
- an auto-trading system
- a black-box reasoning engine
- an LLM wrapper
- a vector database
- an embedding platform
- a semantic search engine

Instead, it provides deterministic infrastructure for institutional research and executive decision support.

---

# Safety

Constellation maintains strict governance principles.

Current guarantees include:

- No hidden reasoning
- No automatic decision making
- No autonomous execution
- No provider execution by default
- No web retrieval
- No embeddings
- No vector databases
- Human approval remains available where configured
- Every output maintains complete provenance

---

# Constellation AI Capability Roadmap

Constellation AI is an Institutional Investment Operating System.

It is designed to improve investment judgment over time by converting research into intelligence, intelligence into understanding, understanding into decisions, and decisions into learning.

## Phase I - Observe

### v5.0.x - Intelligence

Build market awareness and signal structure.

- v5.0.0 - AI & Markets Intelligence
- v5.0.1 - Signal Refinement

Primary question answered:

> What is happening?

## Phase II - Understand

### v5.1.x - v5.3.x - Contextual Understanding

Build context around themes, exposures, catalysts, and risks.

- v5.1.0 - Theme Lifecycle
- v5.2.0 - Portfolio Intelligence
- v5.3.0 - Catalyst Monitoring

Primary question answered:

> Why does it matter?

## Phase III - Decide

### v5.4.x - v5.5.x - Judgment Support

Improve research discipline, decision quality, and daily prioritization.

- v5.4.0 - Decision Journal
- v5.5.0 - Executive Morning Brief

Primary question answered:

> What should I do today from a research and decision-support standpoint?

## Phase IV - Improve

### v6.0.x - Performance Intelligence

Close the loop between decisions and outcomes.

Current capability:

- v6.0.0 - Performance Intelligence MVP
- v6.1.0 - Thesis Accuracy

Future capabilities:

- Attribution analysis
- Win/loss analysis
- Signal quality scoring
- Forecast calibration
- Portfolio decision review
- Process improvement recommendations

Primary question answered:

> How can I become a better investor?

## Phase V - Expand Domains

### v7.0.x - Real Estate Intelligence

Extend Constellation's deterministic evidence-first operating model into valuation work while preserving a separate professional domain boundary.

- v7.0.0 - Real Estate Assignment Intelligence
- v7.1.0 - Assignment Auto-Ingestion
- v7.1.1 - Assignment Consolidation
- v7.1.2 - Assignment Identity Resolution
- v7.2.0 - Canonical Assignment Model

Primary question answered:

> What property am I working on?

## Operating Philosophy

Most investment platforms optimize for finding more signals.

Constellation AI optimizes for making better decisions.

The system is designed to progress through the institutional decision loop:

```text
Data
↓
Information
↓
Intelligence
↓
Understanding
↓
Judgment
↓
Decision
↓
Learning
```

Each release adds a durable institutional capability rather than a standalone feature.

## Ecosystem Positioning

Constellation AI is one operating system inside a broader ecosystem.

- PKOS: Executive Operating System
- Constellation AI: Investment Operating System
- Lodestar OS: Business Operating System
- AI & Markets: Public-facing communication and audience building
- Lodestar AI Store: Commercialization and product distribution

Responsibility boundaries:

| Platform | Responsibility |
| --- | --- |
| PKOS | Executive execution and knowledge orchestration |
| Constellation AI | Investment research, signal processing, and decision support |
| Lodestar OS | Business operations and coordination across business engines |
| AI & Markets | Public-facing communication and audience building |
| Lodestar AI Store | Commercialization and product distribution |

These systems should integrate at the ecosystem level while preserving distinct responsibilities. They should not be merged conceptually.

---

# Contributing

Contributions are welcome.

Please ensure all contributions preserve Constellation's core principles:

- deterministic execution
- explainable outputs
- evidence-backed reasoning
- provenance preservation
- human governance

---

# License

See the LICENSE file for details.

---

# Mission

> **Professional judgment should become more transparent—not less.**

Constellation exists to transform evidence into explainable institutional intelligence while preserving provenance, reproducibility, and human responsibility for every important decision.
