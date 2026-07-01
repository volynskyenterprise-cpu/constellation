# Core Specification

This document defines the non-negotiable system contracts for Constellation.

No runtime, agent, workflow, provider, tool, or memory implementation should violate these specifications. Implementations may add fields and capabilities, but they must preserve the core contracts.

## Specification Set

- `CORE_SPEC.md`: System-wide principles, ownership, and extension rules
- `EVENT_MODEL.md`: Event-driven architecture and canonical event types
- `MESSAGE_SCHEMA.md`: Universal agent message format
- `WORKFLOW_SCHEMA.md`: Workflow state machine and workflow definition requirements
- `MEMORY_SCHEMA.md`: Memory types, movement rules, and promotion criteria
- `TOOL_INTERFACE.md`: Standard tool interface
- `PROVIDER_INTERFACE.md`: Standard AI provider interface

## Core System Guarantees

Constellation must preserve these guarantees:

- Agents are expert roles with bounded authority.
- Workflows are explicit, inspectable, and stateful.
- Human approval gates cannot be silently bypassed.
- All meaningful state changes emit events.
- Memory promotion is deliberate and provenance-aware.
- Tools expose common capabilities through a standard interface.
- AI providers expose common capabilities through a standard interface.
- Model choice must not change the agent, workflow, memory, or event contracts.
- Auditability is a first-class system property.

## Core Entities

### Agent

An expert role that receives structured messages, applies role-specific judgment, produces structured outputs, and emits events.

Agents must have:

- Stable identifier
- Mission
- Scope of authority
- Input and output expectations
- Escalation triggers
- Quality criteria

### Workflow

A stateful professional process composed of steps, agents, approvals, tools, memory operations, and events.

Workflows must have:

- Stable identifier
- State
- Objective
- Participants
- Steps
- Valid transitions
- Required artifacts
- Approval gates
- Completion criteria

### Message

A structured unit of communication between humans, agents, workflows, tools, and providers.

Every agent-facing message must follow `MESSAGE_SCHEMA.md`.

### Event

An immutable record of something that happened.

Events are the basis for orchestration, logs, audit trails, memory promotion, and future automation.

### Memory

Information retained by Constellation for use during current or future work.

Memory must be categorized, sourced, and promoted according to `MEMORY_SCHEMA.md`.

### Tool

A callable capability that performs bounded work outside the agent's internal reasoning.

Tools include search, read, write, execute, notify, and future extensions.

### Provider

An AI execution backend that can run agent reasoning or generation tasks behind a standard interface.

Providers include Codex, GPT, Claude, Gemini, Ollama, local models, and future systems.

## Required IDs

All durable entities must use stable IDs:

- `workflow_id`
- `workflow_run_id`
- `agent_id`
- `message_id`
- `event_id`
- `memory_id`
- `tool_id`
- `provider_id`
- `approval_id`

IDs should be unique within their entity type. Runtime implementations may use UUIDs, ULIDs, timestamp-prefixed IDs, or another documented scheme.

## Time

All timestamps must be stored in ISO 8601 format with timezone.

Example:

```text
2026-06-30T21:55:00-07:00
```

## Status Language

Where possible, Constellation should use consistent status values:

- `draft`
- `active`
- `waiting`
- `needs_approval`
- `blocked`
- `completed`
- `failed`
- `archived`

Domain-specific statuses may be added, but they should map cleanly to these base concepts.

## Confidence

Confidence should be explicit when agents make claims or recommendations.

Recommended values:

- `low`
- `medium`
- `high`
- `unknown`

Confidence must not be used as a substitute for evidence.

## Human Authority

The human remains the final authority for consequential decisions.

The system must require human approval for:

- Strategic decisions
- Architecture decisions with lasting impact
- Release decisions
- Destructive operations
- External communications
- Policy changes
- Disputed durable memory promotion
- Any action explicitly marked as requiring approval

## Extension Rules

### Adding Agents

New agents may be added without changing core architecture when they:

- Represent a durable professional responsibility
- Use the universal message schema
- Declare authority and limits
- Emit standard events
- Reference existing tools and providers through standard interfaces
- Are registered in configuration

New agents must not require custom workflow semantics unless a new general-purpose step type is justified.

### Adding Tools

New tools may be added when they:

- Implement the standard tool interface
- Declare capabilities
- Declare permissions and approval requirements
- Return structured results
- Emit tool events
- Preserve audit-relevant inputs and outputs

Tool-specific fields are allowed inside extension metadata, but core fields must remain stable.

### Adding Providers

New providers may be added when they:

- Implement the provider interface
- Declare capabilities
- Support structured input and output
- Report limitations
- Preserve provider-agnostic message contracts
- Expose errors in standard form

Provider-specific behavior must be isolated behind configuration or adapter metadata.

### Adding Workflows

New workflows may be added when they:

- Use the workflow state machine
- Define valid steps and participants
- Reference registered agents
- Include approval gates where authority matters
- Define completion criteria
- Emit standard events
- Declare memory update behavior

Workflows should compose existing concepts before introducing new core abstractions.

### Adding Memory Types

New memory categories may be added only when the existing four layers are insufficient:

- Working Memory
- Project Memory
- Knowledge Memory
- Long-Term Memory

Any new memory type must define ownership, promotion rules, retention rules, and provenance requirements.

## Compatibility Rule

Future implementations may become more automated, distributed, or interactive, but they must remain compatible with these documents unless the Core Specification is intentionally versioned.

## Versioning

This specification begins at version `0.1.0`.

Breaking changes require:

- A new spec version
- Migration notes
- A changelog entry
- Review by the human owner
