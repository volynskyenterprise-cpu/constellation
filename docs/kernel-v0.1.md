# Kernel v0.1

Constellation Kernel v0.1 is the smallest file-based runtime that can exercise the scaffold without calling AI providers or external tools.

## What It Does

- Loads YAML configuration from `config/`
- Loads and validates agent definitions from `agents/`
- Loads and validates workflow definitions from `workflows/`
- Supports the example workflow at `workflows/examples/ceo-research-qa-docs.yaml`
- Creates standardized agent messages
- Persists message logs as JSONL
- Emits lifecycle events
- Persists event logs as JSONL
- Initializes Working Memory and Project Memory
- Creates stubs for Knowledge Memory and Long-Term Memory
- Detects approval gates
- Stops execution when human approval is required

## What It Does Not Do

- No AI provider calls
- No external tools
- No database
- No web UI
- No automatic approval bypass
- No full orchestration engine

## Run The Example

From the repository root:

```bash
python -m constellation run workflows/examples/ceo-research-qa-docs.yaml
```

The run will stop at the approval gate and print:

- Workflow run ID
- Workflow ID
- Status
- Message log path
- Event log path
- Working memory path
- Pending approval path

## Persistence

For each run, logs are written under:

```text
logs/runs/<workflow_run_id>/
  messages.jsonl
  events.jsonl
```

Working memory is written to:

```text
memory/runs/<workflow_run_id>-working.json
```

Pending approvals are written to:

```text
approvals/pending/<approval_id>.json
```

## Development Notes

The kernel intentionally uses only the Python standard library. YAML loading is handled by a small subset parser that supports the simple YAML structures used by the scaffold.

The parser is not intended to be a general YAML implementation. If Constellation later needs full YAML support, replace it behind the loader interfaces rather than changing agent or workflow contracts.
