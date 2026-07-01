# Prompt Assembly v0.9

Kernel v0.9 adds deterministic prompt package assembly.

Prompt assembly converts `ExecutionContext` and crew doctrine into a provider-ready package. It does not call real APIs and does not enable provider execution by default.

## Prompt Package

Each package includes:

- `prompt_id`
- `workflow_run_id`
- `workflow_id`
- `step_id`
- `agent_id`
- `crew_role`
- `system_prompt`
- `task_prompt`
- `context_sections`
- `output_contract`
- `constraints`
- `evidence_requirements`
- `uncertainty_requirements`
- `approval_requirements`
- `metadata`
- `created_at`

## Inputs

Prompt packages are assembled from:

- Crew profile
- Responsibilities
- Authority
- Communication style
- Methodologies
- Memory rules
- `prompts.md` templates
- Workflow step instructions
- Previous messages
- Working memory
- Project memory
- Provider routing config

## CLI

Show the prompt package for the current executable step:

```bash
python -m constellation prompt show run_225a2ecf7cd5477e966c7bf6965eec4c
```

Show a specific step:

```bash
python -m constellation prompt show run_225a2ecf7cd5477e966c7bf6965eec4c --step frame_request
```

If a run is paused at approval, the command prints:

```text
No agent prompt is available until approval is resolved.
```

## Persistence

Prompt packages are persisted under:

```text
logs/runs/<run_id>/prompts/<prompt_package_id>.json
```

When provider-backed execution is enabled, prompt package metadata is also recorded in:

- Message log
- Event log
- Working memory artifact metadata

## Provider Integration

Provider invocation remains opt-in.

When enabled, the kernel passes the prompt package to the selected provider. `EchoProvider` includes prompt package markers in its deterministic output so tests can verify the package was received.

Example echo output:

```text
echo:<message_id>:<requested_action>:prompt=<prompt_id>:role=<crew_role>:step=<step_id>
```

## Non-Goals

- No real model calls
- No API keys
- No prompt optimization
- No token budgeting yet
- No context redaction yet
