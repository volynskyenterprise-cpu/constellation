# Daily Intelligence Pipeline v3.7

Constellation v3.7 adds a deterministic Daily Intelligence Pipeline that runs the existing local intelligence modules in the correct order and produces a daily package.

The pipeline is an orchestrator only. It does not add inference, provider execution, web retrieval, Gmail, embeddings, semantic search, or autonomous decisions.

## Command

```bash
python -m constellation daily
python -m constellation daily --overwrite
python -m constellation daily status
python -m constellation daily history
python -m constellation daily export
```

## Stage Order

The pipeline runs:

1. Intake Scan
2. Google Drive Sync, only when connector readiness checks pass
3. Morning Executive Brief
4. Institutional Memory Snapshot
5. Evidence Graph Build
6. Thesis Intelligence Build
7. Daily Summary Manifest

Each stage reuses an existing Constellation module.

## Outputs

```text
outputs/daily/daily-run.json
outputs/daily/daily-report.md
outputs/daily/daily-history.json
outputs/daily/daily-manifest.json
```

## Report Contents

`daily-report.md` includes:

- Intake files processed
- Google Drive sync result
- Morning brief ID
- Memory snapshot ID
- Evidence graph ID
- Thesis count
- Evidence count
- Graph nodes
- Graph edges
- Runtime
- Timestamp
- Version
- Stage status summary
- Limitations

## Overwrite Behavior

Running `python -m constellation daily` creates the current daily run output. If `outputs/daily/daily-run.json` already exists, run:

```bash
python -m constellation daily --overwrite
```

History is appended for auditability. Institutional Memory snapshots are never rewritten.

## Google Drive Behavior

Google Drive sync is skipped unless the connector is ready:

- config exists
- optional dependencies are installed
- credentials and token paths are configured
- enabled Google Drive sources exist

If not ready, the daily pipeline records a skipped stage with a reason.

## Safety

The pipeline never:

- calls providers
- calls OpenAI
- invokes LLM inference
- uses embeddings
- uses semantic search
- uses web retrieval
- uses Gmail
- modifies evidence
- rewrites previous memory snapshots
- makes autonomous decisions

It reports current deterministic local state.
