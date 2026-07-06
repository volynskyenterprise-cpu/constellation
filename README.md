# Constellation

> **Deterministic Institutional Intelligence Platform**

Constellation transforms research into explainable institutional intelligence through deterministic evidence extraction, knowledge graphs, cross-document reasoning, thesis generation, executive intelligence briefs, and operational intake pipelines.

Unlike black-box AI systems, every conclusion produced by Constellation is fully traceable back to explicit evidence with complete provenance.

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

## Current

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
- ✅ Institutional Intelligence
- ✅ Intake Pipeline
- ✅ Google Drive Connector
- ✅ Morning Executive Intelligence
- ✅ Institutional Memory

## Coming Next

- Gmail Connector
- Folder Watchers
- Executive Dashboard

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
