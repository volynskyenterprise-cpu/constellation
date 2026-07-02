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
