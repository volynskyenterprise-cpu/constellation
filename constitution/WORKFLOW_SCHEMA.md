# Workflow Schema

This document defines the workflow state machine and workflow definition requirements.

Workflows are explicit professional processes. They coordinate agents, tools, approvals, memory, and artifacts.

## Workflow State Machine

Constellation workflows use these states:

1. `Draft`
2. `Planning`
3. `Research`
4. `Execution`
5. `Review`
6. `Approval`
7. `Complete`
8. `Archived`

## State Definitions

### Draft

The workflow exists as an idea or initial request. Objective, scope, agents, and steps may be incomplete.

### Planning

The workflow is being framed. The CEO agent or human clarifies objectives, assigns agents, identifies constraints, and defines completion criteria.

### Research

The workflow gathers evidence, memory, context, and external references needed for judgment.

### Execution

Agents produce the primary work artifacts.

### Review

Agents validate, critique, test, or inspect produced artifacts.

### Approval

The workflow waits for a human approval decision or records the result of that decision.

### Complete

The workflow has met completion criteria, produced required artifacts, resolved required approvals, and proposed memory updates.

### Archived

The workflow is closed for active work and retained for audit, retrieval, and long-term reference.

## Valid Transitions

```text
Draft -> Planning
Draft -> Archived

Planning -> Research
Planning -> Execution
Planning -> Approval
Planning -> Archived

Research -> Planning
Research -> Execution
Research -> Review
Research -> Approval

Execution -> Review
Execution -> Research
Execution -> Approval

Review -> Execution
Review -> Approval
Review -> Complete

Approval -> Planning
Approval -> Research
Approval -> Execution
Approval -> Review
Approval -> Complete
Approval -> Archived

Complete -> Archived
```

No other transitions are valid unless a future spec version adds them.

## Blocked Workflows

`blocked` is a status, not a primary lifecycle state.

A workflow may be blocked while in:

- `Planning`
- `Research`
- `Execution`
- `Review`
- `Approval`

Blocked workflows must record:

- Blocking reason
- Responsible party
- Needed action
- Timestamp
- Next review condition

## Workflow Definition

Every workflow definition should include:

```text
Workflow
  id
  name
  version
  purpose
  states_supported
  agents
  steps
  approval_gates
  validation
  memory_updates
  completion_criteria
```

## Step Definition

Every step should include:

```text
Step
  id
  name
  type
  agent
  inputs
  outputs
  required
  approval_required
  completion_criteria
```

## Standard Step Types

- `frame_objective`
- `retrieve_context`
- `produce_artifact`
- `review_artifact`
- `validate_artifact`
- `request_human_approval`
- `revise_artifact`
- `record_memory`
- `prepare_release`
- `archive_run`

New step types must be reusable and documented.

## Workflow Run State

Every workflow run should track:

```text
WorkflowRun
  workflow_run_id
  workflow_id
  state
  status
  objective
  current_step
  assigned_agents
  artifacts
  approvals
  memory_updates
  events
  started_at
  updated_at
  completed_at
```

## Approval Gates

Approval gates should include:

```text
ApprovalGate
  id
  name
  required_by
  after_step
  question
  options
  recommendation_required
  blocking
```

Approval gates that are marked `blocking` must halt state progression until resolved.

## Completion Criteria

A workflow may enter `Complete` only when:

- Required steps are complete.
- Required artifacts exist.
- Required validation is complete.
- Blocking approvals are resolved.
- Open blockers are either resolved or explicitly accepted by the human.
- Memory updates have been proposed or intentionally skipped.
- A completion event has been emitted.

## Archive Criteria

A workflow may enter `Archived` when:

- It is complete, rejected, abandoned, or superseded.
- Required logs are preserved.
- Final artifacts are linked.
- Approval decisions are recorded.
- Memory promotion status is recorded.

## Extension Rules

New workflows should:

- Use the standard state machine.
- Reference registered agents.
- Use standard step types when possible.
- Emit canonical events.
- Declare approval gates explicitly.
- Declare memory effects explicitly.

New workflow states require a Core Specification version change.
