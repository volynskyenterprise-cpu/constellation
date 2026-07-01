# Vision

Constellation is built on a simple belief: professional AI systems should improve judgment, not merely accelerate text generation.

Most AI tools treat work as a conversation with one assistant. Constellation treats work as a governed process involving expert roles, explicit methods, shared memory, validation, and human executive control.

## Core Philosophy

### Experts, Not Assistants

Constellation agents are not generic helpers with different names. Each agent represents a professional responsibility, a decision lens, and a set of methods.

An Engineering Manager should think in delivery risk, architecture boundaries, sequencing, and maintainability. A QA Lead should think in failure modes, acceptance criteria, regression risk, and verification. A Documentation Engineer should think in audience, structure, precision, and long-term usability.

The system should make these responsibilities real through contracts, checklists, evaluation criteria, and lifecycle rules.

### Judgment Before Generation

The system should resist producing polished output before it has clarified the problem.

Before generation, agents should ask:

- What decision is being made?
- What facts are known?
- What assumptions are being made?
- What standards apply?
- What would make this output wrong?
- What does the human need in order to approve it?

Generation is only one phase of professional work. Constellation gives equal importance to framing, research, critique, validation, approval, and retention.

### Methodology Over Prompting

Prompts are not enough. A reliable professional system needs methods.

Constellation should encode repeatable ways of working:

- Research protocols
- Design review methods
- Engineering planning methods
- QA acceptance methods
- Release readiness methods
- Documentation methods
- Decision review methods

Prompts can express a method, but they should not be the only place where the method lives.

### Knowledge Compounds

Every completed workflow should make the next workflow smarter.

Constellation should capture durable knowledge:

- Decisions
- Assumptions
- Constraints
- Lessons learned
- Reusable patterns
- Project vocabulary
- Domain references
- Validated outputs
- Known risks

Memory should not be a dumping ground. It should be curated by the Knowledge Engineer and organized so that agents can retrieve the right context at the right time.

### Human Remains CEO

Constellation can coordinate expert agents, but it does not replace the accountable human.

The human sets priorities, approves direction, resolves tradeoffs, grants authority, and accepts final responsibility. The CEO agent may help frame decisions, coordinate work, and surface recommendations, but the human remains the actual CEO.

### Model-Agnostic Architecture

Constellation should treat models as replaceable execution providers.

Agent behavior should be defined through role specifications, tools, contracts, workflows, and policies rather than hardcoded assumptions about one model vendor.

The same agent should eventually be runnable through:

- Codex
- GPT
- Claude
- Gemini
- Local models
- Specialized task models

Different models may have different strengths, but the system should preserve the same professional contract.

### Start Simple, But Make It Extensible

The first version should be understandable, inspectable, and easy to modify.

Prefer:

- Files over databases
- Markdown over custom UIs
- Explicit workflows over hidden orchestration
- Manual approvals over implied autonomy
- Small contracts over large frameworks

The architecture should still leave clean paths toward richer orchestration, persistent services, model routing, advanced retrieval, and enterprise governance.

## Product Thesis

AI professional work improves when the system separates responsibilities:

- One role frames the objective
- One role retrieves knowledge
- One role critiques assumptions
- One role designs the solution
- One role validates the output
- One role documents the result
- One role prepares release
- The human approves the consequential decisions

This separation creates productive friction. Constellation should use that friction to prevent shallow answers and premature certainty.

## Experience Goals

Constellation should feel like working with a compact expert organization:

- Calm, deliberate, and transparent
- Opinionated about process
- Flexible about tools and models
- Serious about evidence
- Respectful of human authority
- Comfortable with ambiguity
- Relentless about preserving useful knowledge

## Success Criteria

Constellation is succeeding when:

- Work products are more reliable than single-agent outputs
- The human can inspect how conclusions were reached
- Agents catch each other's weak assumptions
- Repeated work gets faster because knowledge compounds
- Approval gates prevent uncontrolled action
- Outputs are traceable to evidence, decisions, and responsible roles
- New agents can be added without redesigning the system

## Cultural Standard

Constellation should produce work that a professional would be willing to stand behind.

Not just plausible work.

Not just fluent work.

Work with reasons.
