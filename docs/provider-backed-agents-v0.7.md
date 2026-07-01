# Provider-Backed Agents v0.7

Kernel v0.7 adds optional provider-backed agent step output.

The default kernel behavior remains unchanged. Provider invocation only happens when explicitly enabled in `config/providers.yaml`.

## Routing Configuration

Provider-backed execution is controlled by:

```yaml
routing:
  invoke_provider_during_kernel_run: false
  default_provider: echo
  per_agent_provider:
    qa_lead: "null"
  allow_fallback: false
  fallback_provider: "null"
```

## Default Behavior

When `invoke_provider_during_kernel_run` is `false`, workflow steps keep using placeholder artifacts and no provider is invoked.

## Provider-Backed Behavior

When enabled, each workflow step:

1. Creates the standard agent message.
2. Selects a provider.
3. Calls the provider's deterministic `generate` method.
4. Stores provider output in working memory.
5. Appends provider result metadata to the message log.
6. Emits provider lifecycle events to the event log.

## Provider Selection

Selection order:

1. `per_agent_provider` override for the agent ID
2. `default_provider`

Example:

```yaml
routing:
  invoke_provider_during_kernel_run: true
  default_provider: echo
  per_agent_provider:
    qa_lead: "null"
```

The CEO, Research Lead, and Documentation Engineer use `echo`; QA Lead uses `null`.

## Failure Behavior

If a provider fails:

- The kernel emits `ProviderFailed`.
- Provider failure metadata is written to the message log.
- The failed provider result is stored in working memory.
- The workflow is marked `failed`.

## Fallback Behavior

Fallback only occurs when explicitly enabled:

```yaml
routing:
  invoke_provider_during_kernel_run: true
  default_provider: failure
  allow_fallback: true
  fallback_provider: "null"
```

Fallback metadata includes:

- `fallback: true`
- `fallback_from`
- `agent_id`
- `step_id`

## Determinism

No external APIs are called.

No API keys are used.

`EchoProvider`, `NullProvider`, and `FailureProvider` remain deterministic for tests.
