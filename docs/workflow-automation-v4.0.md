# Workflow Automation Engine v4.0

Constellation v4.0 adds a deterministic workflow automation layer for running repeatable recipes made from existing Constellation commands.

This is an orchestration layer only. It does not add new intelligence logic and does not call providers, OpenAI, Gmail, web retrieval, embeddings, semantic search, scheduling, or autonomous execution.

## Commands

```bash
python -m constellation workflow list
python -m constellation workflow run Morning
python -m constellation workflow history
python -m constellation workflow show Morning
python -m constellation workflow export
```

## Built-In Workflows

### Morning

Runs:

- monitor
- drive sync
- intake scan
- morning
- memory snapshot
- evidence-graph build
- thesis build
- daily
- dashboard

### Research Refresh

Runs:

- monitor
- drive sync
- intake scan
- evidence-graph build
- thesis build
- dashboard

### Executive Snapshot

Runs:

- morning
- memory snapshot
- dashboard

## Outputs

Workflow Automation writes:

- `outputs/workflows/workflow-definitions.json`
- `outputs/workflows/workflow-history.json`
- `outputs/workflows/latest-workflow.json`
- `outputs/workflows/workflow-report.md`

## Execution Model

Each workflow step has:

- `name`
- `command`
- `arguments`
- `enabled`
- `continue_on_failure`

The engine executes enabled steps in order. Failed steps stop the workflow unless `continue_on_failure` is enabled for that step.

Google Drive sync is skipped when local configuration is incomplete or optional dependencies are unavailable. No Gmail, provider, web retrieval, embedding, or semantic search behavior is introduced.

## Dashboard Integration

Executive Dashboard reads `outputs/workflows/latest-workflow.json` and displays:

- last workflow run
- workflow status
- workflow duration
- completed steps
- failed steps
