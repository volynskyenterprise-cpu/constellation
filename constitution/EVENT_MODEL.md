# Event Model

Constellation is event-driven.

Every meaningful state change should emit an event. Events create the audit trail, enable workflow orchestration, support replay, and make future automation possible without hiding system behavior.

## Event Principles

- Events are immutable.
- Events are append-only.
- Events describe what happened, not what should happen.
- Events should be structured and machine-readable.
- Events should include enough context for audit and replay.
- Events should not contain unnecessary private reasoning or sensitive data.
- Events may reference artifacts rather than duplicate large content.

## Standard Event Envelope

Every event should use this envelope:

```text
Event
  id
  type
  timestamp
  workflow_id
  workflow_run_id
  actor
  subject
  summary
  data
  references
  correlation_id
  causation_id
  severity
```

## Event Fields

`id`: Unique event identifier.

`type`: Event type, such as `WorkflowStarted`.

`timestamp`: ISO 8601 timestamp with timezone.

`workflow_id`: Workflow definition identifier, if applicable.

`workflow_run_id`: Specific workflow run identifier, if applicable.

`actor`: Human, agent, tool, provider, or system that caused the event.

`subject`: Entity affected by the event.

`summary`: Short human-readable description.

`data`: Structured event-specific payload.

`references`: Links or IDs for related messages, artifacts, memory entries, approvals, or logs.

`correlation_id`: Shared ID connecting related events in a workflow or request.

`causation_id`: Event ID or message ID that directly caused this event.

`severity`: One of `debug`, `info`, `warning`, `error`, `critical`.

## Canonical Event Types

### Workflow Events

- `WorkflowDrafted`
- `WorkflowStarted`
- `WorkflowStateChanged`
- `WorkflowPaused`
- `WorkflowResumed`
- `WorkflowBlocked`
- `WorkflowCompleted`
- `WorkflowArchived`

### Agent Events

- `AgentAssigned`
- `AgentInvoked`
- `AgentResponded`
- `AgentBlocked`
- `AgentEscalated`
- `AgentCompleted`

### Message Events

- `MessageCreated`
- `MessageDelivered`
- `MessageRejected`
- `MessageSuperseded`

### Memory Events

- `MemoryCaptured`
- `MemoryProposed`
- `MemoryReviewed`
- `MemoryUpdated`
- `MemoryPromoted`
- `MemoryDeprecated`
- `MemoryConflictDetected`

### Approval Events

- `ApprovalRequested`
- `ApprovalGranted`
- `ApprovalGrantedWithConditions`
- `ApprovalRejected`
- `ApprovalDeferred`
- `ApprovalSuperseded`

### Tool Events

- `ToolRequested`
- `ToolStarted`
- `ToolCompleted`
- `ToolFailed`
- `ToolDenied`

### Provider Events

- `ProviderSelected`
- `ProviderRequestStarted`
- `ProviderRequestCompleted`
- `ProviderRequestFailed`
- `ProviderFallbackRequested`

### Artifact Events

- `ArtifactCreated`
- `ArtifactUpdated`
- `ArtifactReviewed`
- `ArtifactAccepted`
- `ArtifactRejected`

### Error Events

- `ValidationFailed`
- `PolicyViolationDetected`
- `SchemaViolationDetected`
- `ExecutionFailed`
- `RecoveryAttempted`

## Required Events By Workflow Lifecycle

Every workflow run should emit at least:

1. `WorkflowStarted`
2. `AgentAssigned` for each assigned agent
3. `AgentInvoked` for each agent invocation
4. `AgentResponded` for each agent response
5. `ApprovalRequested` for each required gate
6. One approval resolution event for each approval request
7. `MemoryProposed` when durable memory is suggested
8. `WorkflowCompleted` or `WorkflowBlocked`

`WorkflowArchived` should be emitted when the run is closed for long-term retention.

## Event Ordering

Events should be recorded in append order.

Implementations should not assume perfect clock ordering across distributed systems. If distributed execution is introduced, use both timestamps and event sequence numbers.

## Event References

Events should reference related entities by ID:

- Messages
- Agent invocations
- Tool calls
- Provider requests
- Approval records
- Memory entries
- Artifacts
- Logs

Large artifacts should be stored separately and referenced.

## Event-Driven Extension Rule

New system behavior should be observable through events.

If a future feature changes workflow state, memory, approvals, artifacts, tools, providers, or agent assignments, it must define which events it emits.
