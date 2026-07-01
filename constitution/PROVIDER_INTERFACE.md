# Provider Interface

This document defines the standard interface every AI provider must expose.

Providers execute agent reasoning, generation, analysis, or multimodal tasks. Constellation must remain model-agnostic, so providers are selected by capability rather than by hardcoded vendor behavior.

## Provider Principles

- Providers are replaceable.
- Agents should not depend on provider-specific behavior.
- Workflows request capabilities, not vendors.
- Provider output must conform to Constellation schemas.
- Provider limitations must be visible.
- Provider failures must be reported in standard form.

## Standard Provider Interface

Every provider should expose:

```text
Provider
  id
  name
  version
  models
  capabilities
  limits
  input_modes
  output_modes
  invoke(request)
  validate_request(request)
  describe()
  health_check()
```

This is a specification, not an implementation requirement for a specific programming language.

## Required Provider Metadata

`id`: Stable provider identifier.

`name`: Human-readable provider name.

`version`: Provider adapter version.

`models`: Available model identifiers or runtime targets.

`capabilities`: Supported capability categories.

`limits`: Context limits, rate limits, file limits, modality limits, or cost constraints.

`input_modes`: Supported input types.

`output_modes`: Supported output types.

## Required Capabilities

Every provider used for agent execution must support:

- Structured input
- Structured output
- Instruction following
- Reasoning summary generation
- Evidence-aware response formatting
- Status reporting
- Error reporting

Providers may additionally support:

- Tool use
- Code editing
- Shell execution
- File inspection
- Multimodal input
- Long context
- Local execution
- Streaming output
- Function calling

## Standard Provider Request

```text
ProviderRequest
  id
  provider_id
  model
  workflow_id
  workflow_run_id
  agent_id
  message
  capabilities_requested
  tools_available
  constraints
  output_schema
  approval_state
  timestamp
```

## Standard Provider Response

```text
ProviderResponse
  id
  request_id
  provider_id
  model
  status
  message
  structured_output
  reasoning_summary
  evidence
  confidence
  usage
  errors
  started_at
  completed_at
```

## Provider Status Values

- `accepted`
- `rejected`
- `running`
- `completed`
- `failed`
- `rate_limited`
- `unavailable`
- `needs_fallback`

## Provider Error Format

```text
ProviderError
  code
  message
  category
  retryable
  provider_details
```

Error categories:

- `invalid_request`
- `schema_violation`
- `context_limit_exceeded`
- `rate_limited`
- `provider_unavailable`
- `model_unavailable`
- `tool_use_failed`
- `safety_refusal`
- `timeout`
- `unknown`

## Provider Capability Categories

### Reasoning

Can analyze a structured task and produce a useful judgment summary.

### Structured Output

Can produce output that conforms to requested schemas.

### Retrieval-Aware Reasoning

Can use supplied evidence and memory references without inventing unsupported claims.

### Tool-Aware Execution

Can request or coordinate tool calls through Constellation's tool interface.

### Code And File Work

Can inspect, edit, or reason about files when granted tool access.

### Multimodal Understanding

Can process images, audio, video, or documents when provided.

### Local Execution

Can run in an environment controlled by the user or organization.

## Provider Selection

Provider selection should consider:

- Required capabilities
- Agent role
- Workflow state
- Data sensitivity
- Cost limits
- Context size
- Latency requirements
- Availability
- Human or policy preference

Provider selection must emit `ProviderSelected`.

## Fallback Rules

Fallback to another provider may occur when:

- The selected provider is unavailable.
- The selected provider lacks required capability.
- The provider fails with a retryable error.
- A policy allows fallback.

Fallback must not occur silently. It should emit `ProviderFallbackRequested` and record why the fallback happened.

Human confirmation is required when fallback changes data handling, privacy posture, or authority assumptions.

## Compatibility With Named Providers

### Codex

Codex may serve as the V1 execution environment and provider for file-aware engineering workflows.

### GPT

GPT providers may support general reasoning, structured output, multimodal tasks, and tool-aware workflows.

### Claude

Claude providers may support long-context reasoning, structured outputs, and document-heavy workflows.

### Gemini

Gemini providers may support multimodal reasoning and structured outputs.

### Ollama And Local Models

Local providers may support private, offline, or cost-controlled execution, subject to capability limits.

## Events

Providers should emit:

- `ProviderSelected`
- `ProviderRequestStarted`
- `ProviderRequestCompleted`
- `ProviderRequestFailed`
- `ProviderFallbackRequested`

## Extension Rules

New providers may be added without changing core architecture when they:

- Implement the standard request and response shape.
- Declare capabilities and limits.
- Return standard errors.
- Preserve message schema semantics.
- Emit provider events.
- Keep provider-specific behavior behind configuration or adapter metadata.
