# OpenAI Provider Adapter v1.2

Constellation v1.2.0 adds an OpenAI provider adapter behind the existing provider interface.

OpenAI remains disabled by default. Constellation will not call OpenAI unless both provider invocation and OpenAI routing are explicitly enabled.

## Install Optional Dependency

The OpenAI SDK is optional:

```bash
pip install -e ".[openai]"
```

or:

```bash
pip install openai
```

## Set API Key

Set the API key through the environment only. Do not write API keys into repository files.

PowerShell:

```powershell
$env:OPENAI_API_KEY="sk-your-key"
```

macOS/Linux:

```bash
export OPENAI_API_KEY="sk-your-key"
```

## Provider Configuration

`config/providers.yaml` includes OpenAI disabled by default:

```yaml
  - id: openai
    enabled: false
    role: future_model_provider
    provider_type: openai
    model: gpt-4.1-mini
    capabilities:
      - reasoning
      - structured_output
      - multimodal_understanding
    config:
      api_key_env: OPENAI_API_KEY
      timeout_seconds: 30
      max_output_tokens: 2000
      health_check_mode: config_only
```

To enable OpenAI manually:

```yaml
  - id: openai
    enabled: true
    role: future_model_provider
    provider_type: openai
    model: gpt-4.1-mini
    capabilities:
      - reasoning
      - structured_output
      - multimodal_understanding
    config:
      api_key_env: OPENAI_API_KEY
      timeout_seconds: 30
      max_output_tokens: 2000
      health_check_mode: config_only
```

Then route workflow execution to OpenAI:

```yaml
routing:
  invoke_provider_during_kernel_run: true
  default_provider: openai
  allow_fallback: false
```

## Health Checks

Show OpenAI configuration:

```bash
python -m constellation providers show openai
```

Check provider health:

```bash
python -m constellation providers health
```

Expected disabled output:

```text
openai status=disabled enabled=False
```

If OpenAI is enabled but `OPENAI_API_KEY` is missing, health reports:

```text
openai status=missing_api_key enabled=True
```

If OpenAI is enabled and the SDK is missing, health reports:

```text
openai status=missing_sdk enabled=True
```

By default, health does not perform an external API probe. Set `health_check_mode: api` only when you explicitly want a lightweight model probe.

## Provider Request Shape

When provider execution is enabled, the OpenAI adapter sends the assembled prompt package through the existing provider interface. The request includes:

- `system_prompt`
- `task_prompt`
- `output_contract`
- `evidence_requirements`
- `uncertainty_requirements`
- `context_sections`

The adapter asks for JSON-like output matching the `AgentArtifact` fields. The artifact parser remains responsible for converting provider responses into structured artifacts and must not assume perfect model compliance.

## Cost Warning

Real OpenAI calls may cost money. Keep `enabled: false` and `invoke_provider_during_kernel_run: false` unless you intentionally want live provider execution.
