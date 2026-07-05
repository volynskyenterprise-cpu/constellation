# Constellation

Constellation is an AI Operating System for Professional Judgment.

It coordinates specialized AI agents that reason, challenge assumptions, retrieve knowledge, validate outputs, and produce reliable professional work. Its goal is not to make one assistant louder. Its goal is to make expert judgment more deliberate, inspectable, reusable, and trustworthy.

Constellation begins with Codex as the execution environment, but its architecture is model-agnostic. Future runtimes should support GPT, Claude, Gemini, local models, and specialized tools without changing the product philosophy or agent contracts.

## Product Definition

Constellation is a professional work orchestration system built around expert agents, governed workflows, durable knowledge, and human executive control.

The system helps a human operator define objectives, assemble the right expert roles, execute structured reasoning workflows, validate outputs, preserve knowledge, and maintain an audit trail of how conclusions were reached.

Constellation is designed for work where correctness, traceability, and judgment matter more than raw generation speed:

- Software architecture and engineering delivery
- Product strategy and planning
- Research synthesis
- Technical documentation
- Design review
- Quality assurance
- Release readiness
- Decision support

## Core Promise

Constellation turns professional AI work from a chat transcript into an operating system:

- Clear objectives
- Explicit roles
- Structured methods
- Human approval gates
- Persistent knowledge
- Verifiable outputs
- Auditable decisions

## Design Principles

- Experts, not assistants
- Judgment before generation
- Methodology over prompting
- Knowledge compounds
- Human remains CEO
- Model-agnostic architecture
- Start simple, but make it extensible

## Initial V1 Agent Team

- CEO
- Research Lead
- Knowledge Engineer
- Engineering Manager
- Designer
- Documentation Engineer
- QA Lead
- Release Manager

## Constellation Crew

Phase II introduces the [Constellation Crew](crew/README.md): a durable organizational layer that defines agents as professional roles rather than prompt wrappers.

The existing `agents/` YAML files remain the runtime registry. The `crew/` directory defines each role's mission, responsibilities, authority, communication style, methodologies, memory rules, and prompt templates.

Crew doctrine is intentionally broader than runtime configuration. It is the professional standard future workflows and agent implementations should satisfy.

## Research Organization

v2.0 introduces the [Research Organization](docs/research-organization-v2.0.md), the first professional capability built on the Constellation kernel.

It runs an institutional research workflow over markdown or text inputs, coordinates the CEO, Research Lead, Knowledge Engineer, QA Lead, and Documentation Engineer, and exports an evidence-aware executive research report.

```bash
python -m constellation research run research_inputs/sample-brief.md
python -m constellation research export RUN_ID
```

## PKOS Knowledge Organization

v2.1 introduces the [PKOS Knowledge Organization](docs/pkos-knowledge-organization-v2.1.md), a proposal-first workflow for turning markdown or text sources into reviewable PKOS update packages.

It writes proposed files under `outputs/pkos/RUN_ID/` and never mutates an external Obsidian vault by default.

```bash
python -m constellation pkos ingest pkos_inputs/source-note.md
python -m constellation pkos package RUN_ID
```

## Evidence Engine

v2.2 introduces the [Evidence Engine](docs/evidence-engine-v2.2.md), a deterministic evidence layer that records source-backed claims before Research and PKOS workflows execute.

Evidence is stored under `memory/evidence/`, referenced by artifacts through evidence IDs, and can be inspected or exported:

```bash
python -m constellation evidence list
python -m constellation evidence show EVIDENCE_ID
python -m constellation evidence export RUN_ID
```

## Knowledge Graph

v2.3 introduces the [Knowledge Graph](docs/knowledge-graph-v2.3.md), a deterministic file-based graph connecting evidence, sources, workflows, artifacts, and explicit source concepts.

Graph building is opt-in:

```bash
python -m constellation graph build RUN_ID
python -m constellation graph nodes
python -m constellation graph edges
python -m constellation graph export
```

## Cross-Document Reasoning

v2.4 introduces [Cross-Document Reasoning](docs/cross-document-reasoning-v2.4.md), deterministic analysis across the Knowledge Graph.

After building graph entries from multiple runs, Constellation can identify repeated explicit concepts, themes, risks, assumptions, recommendations, source clusters, and explicitly marked possible contradictions:

```bash
python -m constellation graph analyze
python -m constellation graph findings
python -m constellation graph findings show FINDING_ID
```

## Thesis Engine

v2.5 introduces the [Thesis Engine](docs/thesis-engine-v2.5.md), deterministic conversion of cross-document findings into proposed institutional theses.

Thesis generation is opt-in and never accepts a thesis automatically:

```bash
python -m constellation thesis generate
python -m constellation thesis list
python -m constellation thesis show THESIS_ID
python -m constellation thesis export
```

## Institutional Intelligence Platform

v3.0 introduces the [Institutional Intelligence Platform](docs/institutional-intelligence-platform-v3.0.md), an opt-in executive synthesis layer over evidence, graph records, cross-document findings, and proposed theses.

Generate the intelligence brief only after graph analysis and thesis generation:

```bash
python -m constellation intelligence generate
python -m constellation intelligence show
python -m constellation intelligence export
```

## Proposed Documentation Set

- [VISION.md](VISION.md): Product philosophy, strategic intent, and guiding beliefs
- [ARCHITECTURE.md](ARCHITECTURE.md): System architecture, repository structure, workflow engine, memory, configuration, logging, and errors
- [AGENT_SPEC.md](AGENT_SPEC.md): Agent model, lifecycle, standard input/output contract, and V1 agent definitions
- [ROADMAP.md](ROADMAP.md): MVP scope and future roadmap

## V1 Definition

The first version should be deliberately small:

- Markdown-defined agents
- Markdown or YAML-defined workflows
- File-based project memory
- Codex-based execution
- Human approval checkpoints
- Structured logs
- Manual or semi-automated orchestration

The early product should prove the methodology before automating heavily.

## Non-Goals For V1

- Fully autonomous execution
- Complex distributed infrastructure
- Custom model hosting
- Real-time multi-user collaboration
- A large plugin marketplace
- Fine-grained permission systems
- Hidden agent behavior

Constellation should earn complexity only after the core judgment loop works.

## Operating Model

The human remains the final authority. Agents may recommend, critique, retrieve, validate, and produce work, but they do not silently commit irreversible decisions.

The system should make professional reasoning easier to inspect:

- What was asked?
- Which agents participated?
- What assumptions were made?
- What evidence was used?
- What alternatives were considered?
- What was approved by the human?
- What was shipped or recorded?

## North Star

Constellation succeeds when it helps a professional team produce work that is clearer, better reasoned, easier to validate, and easier to build upon than work produced by a single generic assistant.
