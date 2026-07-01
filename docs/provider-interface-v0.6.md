# Provider Interface v0.6

Kernel v0.6 adds a model-provider abstraction without connecting to external APIs.

The provider layer is dormant by default. The kernel still uses placeholder agent behavior unless provider invocation is explicitly enabled in configuration.

## Provider Interface

Each provider exposes:

- `name`
- `capabilities`
- `validate_config`
- `generate`
- `stream`
- `health_check`

`stream` is stubbed through the deterministic `generate` response.

## Provider Result

Every provider response includes:

- `provider_name`
- `model`
- `input_message_id`
- `output_text`
- `status`
- `error`
- `metadata`
- `created_at`

## Stub Providers

### EchoProvider

Returns deterministic text:

```text
echo:<message_id>:<requested_action>
```

### NullProvider

Returns a controlled no-op response with empty output text.

### FailureProvider

Raises a controlled `ProviderError` for testing error handling.

## Configuration

Providers are loaded from:

```text
config/providers.yaml
```

Provider entries include:

- `id`
- `enabled`
- `role`
- `provider_type`
- `model`
- `capabilities`

## Kernel Integration

Provider invocation during normal workflow runs is disabled by default:

```yaml
routing:
  invoke_provider_during_kernel_run: false
  default_provider: null
```

When disabled, Kernel v0.6 behaves like previous versions and records placeholder artifacts without provider output.

## CLI

List providers:

```bash
python -m constellation providers list
```

Show one provider:

```bash
python -m constellation providers show echo
```

Check health:

```bash
python -m constellation providers health
```

## Safety

No API keys are read.

No network calls are made.

All provider outputs are deterministic for testing.
