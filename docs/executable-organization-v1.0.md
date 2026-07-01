# Executable Organization v1.0

Constellation v1.0.0 connects the organization layer to the runtime path:

`Crew doctrine -> Prompt package -> Provider -> Structured artifact -> Working memory -> Approval gate -> Resume/completion`

Provider execution remains opt-in. The default kernel path still records placeholder workflow outputs and does not call providers or create structured artifacts.

## Enabling EchoProvider Execution

Set provider invocation in `config/providers.yaml`:

```yaml
routing:
  invoke_provider_during_kernel_run: true
  default_provider: echo
```

The `echo` provider is deterministic and makes no external API calls. It is intended for verifying end-to-end runtime behavior before real provider adapters exist.

## AgentArtifact

Provider-backed workflow steps now produce an `AgentArtifact` persisted under:

```text
logs/runs/RUN_ID/artifacts/
```

Each artifact includes:

- `artifact_id`
- `workflow_run_id`
- `workflow_id`
- `step_id`
- `agent_id`
- `crew_role`
- `artifact_type`
- `title`
- `summary`
- `findings`
- `recommendations`
- `risks`
- `assumptions`
- `evidence_used`
- `next_steps`
- `confidence`
- `status`
- `provider_result_id`
- `prompt_package_id`
- `created_at`

The artifact parser currently supports deterministic stub parsing for provider results. EchoProvider output is transformed into a structured artifact using the prompt package as the authoritative context.

## Runtime Behavior

When provider invocation is enabled, the kernel:

1. Builds the prompt package for the current workflow step.
2. Sends the prompt package to the selected provider.
3. Parses the provider result into an `AgentArtifact`.
4. Persists the artifact JSON file.
5. Stores an artifact reference in Working Memory.
6. Records artifact metadata in the message log.
7. Emits an artifact lifecycle event.

If provider parsing fails, the kernel persists a failed artifact with the parse error recorded in `summary` and `risks`.

Human approval gates remain mandatory. The example workflow still pauses after `produce_documentation` and requires explicit approval before resume can complete the run.

## CLI

List artifacts for a run:

```bash
python -m constellation artifacts list RUN_ID
```

Show one artifact:

```bash
python -m constellation artifacts show RUN_ID ARTIFACT_ID
```

Example:

```bash
python -m constellation run workflows/examples/ceo-research-qa-docs.yaml
python -m constellation artifacts list run_2f4a7d8c3b1e4f6a9c0d123456789abc
python -m constellation artifacts show run_2f4a7d8c3b1e4f6a9c0d123456789abc artifact_run_2f4a7d8c3b1e4f6a9c0d123456789abc_frame_request
python -m constellation approvals list
python -m constellation approvals approve approval_93b2f0c1a4d54e0e8a11f23456789abc
python -m constellation resume run_2f4a7d8c3b1e4f6a9c0d123456789abc
```

## Notes

- No real AI provider is connected in v1.0.0.
- No external tools or databases are required.
- Runtime artifacts remain file-based.
- Provider invocation remains disabled by default.
