# Message Schema

This document defines the universal agent message format.

Every message exchanged between workflow participants should be structured, inspectable, and suitable for audit. Provider-specific prompts may be generated from messages, but the message itself remains provider-agnostic.

## Universal Agent Message

Every agent-facing message must include:

```text
Message
  id
  timestamp
  workflow_id
  sender
  receiver
  task
  context
  assumptions
  reasoning_summary
  evidence
  confidence
  requested_action
  status
```

## Field Definitions

`id`: Unique message identifier.

`timestamp`: ISO 8601 timestamp with timezone.

`workflow_id`: Identifier of the workflow definition associated with this message.

`sender`: Entity sending the message. May be a human, agent, workflow, tool, provider, or system.

`receiver`: Entity expected to process the message.

`task`: Specific assignment or communication purpose.

`context`: Relevant background, constraints, prior outputs, memory references, and workflow state.

`assumptions`: Assumptions the sender believes are relevant. Receivers may accept, challenge, or add assumptions.

`reasoning_summary`: Concise explanation of the reasoning behind the message. This should summarize judgment without exposing unnecessary hidden chain-of-thought.

`evidence`: Sources, artifacts, memory entries, logs, or references supporting the task or claim.

`confidence`: Sender's confidence in the message content. Use `low`, `medium`, `high`, or `unknown`.

`requested_action`: What the receiver should do next.

`status`: Current state of the message. Recommended values: `draft`, `sent`, `received`, `accepted`, `rejected`, `blocked`, `completed`, `superseded`.

## Optional Extension Fields

Implementations may add:

- `workflow_run_id`
- `thread_id`
- `priority`
- `deadline`
- `schema_version`
- `approval_id`
- `correlation_id`
- `causation_id`
- `artifacts`
- `metadata`

Extensions must not change the meaning of required fields.

## Sender And Receiver Format

Sender and receiver should include:

```text
Party
  type
  id
  name
```

Allowed party types:

- `human`
- `agent`
- `workflow`
- `tool`
- `provider`
- `system`

## Task Format

Tasks should be concise but complete:

```text
Task
  objective
  instructions
  expected_output
  quality_criteria
  constraints
```

## Context Format

Context should include only what is relevant to the requested action:

```text
Context
  summary
  workflow_state
  prior_messages
  memory_references
  artifacts
  constraints
  open_questions
```

## Evidence Format

Evidence entries should include:

```text
Evidence
  id
  type
  location
  summary
  provenance
  confidence
  checked_at
```

Evidence types may include:

- `file`
- `url`
- `memory`
- `log`
- `artifact`
- `human_statement`
- `tool_result`
- `provider_output`

## Requested Action Values

Recommended values:

- `frame_objective`
- `retrieve_context`
- `produce_artifact`
- `review_artifact`
- `validate_output`
- `request_approval`
- `revise_output`
- `update_memory`
- `escalate`
- `complete_step`

New requested actions may be added when they describe reusable workflow behavior.

## Message Status Rules

- A `draft` message has not been sent.
- A `sent` message has been emitted by the sender.
- A `received` message has been acknowledged by the receiver.
- An `accepted` message is valid for processing.
- A `rejected` message violates schema, policy, or authority.
- A `blocked` message cannot be completed without more context or approval.
- A `completed` message has been processed.
- A `superseded` message has been replaced by a newer message.

## Reasoning Summary Rule

`reasoning_summary` should explain the basis of a recommendation or request in a concise, auditable way.

It should include:

- Relevant criteria considered
- Key tradeoffs
- Important uncertainty
- Why the requested action is appropriate

It should not require preserving private model reasoning traces.

## Compatibility Rule

Provider prompts, UI messages, logs, and API requests may adapt this schema for their medium, but must preserve the required fields and semantics.
