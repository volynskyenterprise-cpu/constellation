# Constellation

> **Current Status — Phase I Complete (v4.2)**
>
> Constellation is a deterministic institutional intelligence platform that transforms research into evidence, knowledge graphs, evolving theses, executive dashboards, and institutional research reports.
>
> The core intelligence platform is complete. Future development is focused on domain-specific intelligence for AI & Markets, capital allocation, and real estate while preserving deterministic, evidence-first reasoning with complete provenance.

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

# Core Principles

Constellation is built around six principles:

- Deterministic execution
- Evidence before conclusions
- Complete provenance
- Explainable reasoning
- Human governance
- Provider-agnostic architecture

---

# Features

Current capabilities include:

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

### Executive Dashboard

```bash
python -m constellation dashboard
python -m constellation dashboard --export
python -m constellation dashboard --overwrite
python -m constellation dashboard status
```

Executive Dashboard presents current local Constellation state from existing outputs only. It reports missing artifacts as unavailable and writes `outputs/dashboard/dashboard.json` and `outputs/dashboard/dashboard.md`.

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

# Roadmap

## Phase I — Core Intelligence Platform ✅ *(Completed)*

The deterministic intelligence foundation is complete.

### Intelligence Core

- ✅ Research Intake Pipeline
- ✅ Google Drive Connector
- ✅ Research Organization
- ✅ Evidence Engine
- ✅ Institutional Memory
- ✅ Knowledge Graph
- ✅ Evidence Graph

### Intelligence Layer

- ✅ Cross-Document Analysis
- ✅ Thesis Engine
- ✅ Thesis Intelligence
- ✅ Knowledge Evolution

### Executive Layer

- ✅ Daily Intelligence Pipeline
- ✅ Morning Executive Intelligence
- ✅ Executive Dashboard
- ✅ Institutional Research Reports

### Automation Layer

- ✅ Source Monitoring
- ✅ Workflow Automation
- ✅ End-to-End Morning Research Processing

---

## Phase II — Domain Intelligence *(In Progress)*

Teach Constellation how to think like an institutional research organization.

### Planned Capabilities

- AI & Markets Intelligence
- Portfolio Intelligence
- Capital Allocation Intelligence
- Decision Journal
- Executive Morning Brief
- Research Question Tracking
- Thesis Lifecycle Management
- Catalyst & Risk Monitoring

---

## Phase III — Enterprise Intelligence

Expand Constellation beyond research into a complete institutional operating system.

### Planned Capabilities

- Multi-domain Intelligence
- Real Estate Intelligence
- Executive Workbench
- CRM Intelligence
- Event-driven Connectors
- Gmail Connector
- Calendar Connector
- Folder Watchers
- Human Approval Workflows
- Optional AI-assisted reasoning layered on deterministic evidence

---

## Platform Principles

Constellation remains intentionally deterministic.

Every capability is built upon:

- Complete provenance
- Deterministic processing
- Human oversight
- Evidence-first reasoning
- Local-first architecture
- No hidden inference
- Reproducible outputs
  
## Future Vision

- Multi-provider intelligence
- Institutional knowledge evolution
- Executive workbench
- Constellation Operating System

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
