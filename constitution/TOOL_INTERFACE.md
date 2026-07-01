# Tool Interface

This document defines the standard interface every future Constellation tool must implement.

Tools are bounded capabilities used by agents and workflows. They must be inspectable, permission-aware, and auditable.

## Tool Principles

- Tools perform bounded actions.
- Tools declare capabilities and permissions.
- Tools accept structured input.
- Tools return structured output.
- Tools emit events.
- Tools report errors in a standard format.
- Tools must not bypass human approval gates.

## Standard Tool Interface

Every tool should expose:

```text
Tool
  id
  name
  version
  capabilities
  permissions
  input_schema
  output_schema
  approval_requirements
  execute(input, context)
  validate_input(input)
  describe()
```

This is a specification, not an implementation requirement for a specific programming language.

## Required Metadata

`id`: Stable tool identifier.

`name`: Human-readable name.

`version`: Tool interface version.

`capabilities`: Capability categories the tool provides.

`permissions`: Actions or resources the tool may access.

`input_schema`: Required input shape.

`output_schema`: Returned output shape.

`approval_requirements`: Conditions requiring human approval.

## Standard Capabilities

### Search

Find relevant information.

Examples:

- Web search
- Repository search
- Memory search
- Document search

Required behavior:

- Return sources or result references.
- Include query used.
- Include confidence or relevance where available.
- Identify freshness risk when applicable.

### Read

Retrieve content from a known location.

Examples:

- Read file
- Read document
- Read memory entry
- Read log

Required behavior:

- Return content or structured extract.
- Return location and metadata.
- Preserve provenance.

### Write

Create or update content.

Examples:

- Write file
- Update memory
- Create approval record
- Save artifact

Required behavior:

- Identify target.
- Describe change.
- Preserve previous state when appropriate.
- Require approval for destructive or consequential writes.

### Execute

Run a bounded operation.

Examples:

- Run tests
- Execute shell command
- Render document
- Validate schema

Required behavior:

- Record command or operation.
- Return exit status.
- Return output summary.
- Capture errors.
- Respect approval policy.

### Notify

Send a message or alert.

Examples:

- Request approval
- Notify human
- Notify agent
- Send external communication

Required behavior:

- Identify recipient.
- Identify message content.
- Record delivery status.
- Require approval for external communications when policy requires it.

## Standard Tool Request

```text
ToolRequest
  id
  tool_id
  workflow_id
  workflow_run_id
  requested_by
  capability
  input
  context
  approval_state
  timestamp
```

## Standard Tool Result

```text
ToolResult
  id
  request_id
  tool_id
  status
  output
  summary
  evidence
  errors
  artifacts
  started_at
  completed_at
```

## Tool Status Values

- `accepted`
- `rejected`
- `running`
- `completed`
- `failed`
- `denied`
- `needs_approval`

## Error Format

Tool errors should include:

```text
ToolError
  code
  message
  category
  retryable
  details
```

Error categories:

- `invalid_input`
- `permission_denied`
- `approval_required`
- `resource_unavailable`
- `execution_failed`
- `timeout`
- `unknown`

## Events

Tools should emit:

- `ToolRequested`
- `ToolStarted`
- `ToolCompleted`
- `ToolFailed`
- `ToolDenied`

## Approval Rules

Tools must request approval when:

- A write is destructive.
- An action affects external systems.
- A notification leaves the workspace.
- A policy marks the action as approval-required.
- A tool cannot determine whether the action is safe.

## Extension Rules

New tools may add specialized capabilities if they:

- Preserve the standard request and result shape.
- Declare permissions.
- Emit standard tool events.
- Return standard errors.
- Document any approval requirements.
