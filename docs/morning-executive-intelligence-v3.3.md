# Morning Executive Intelligence v3.3

Constellation v3.3.0 adds a one-command morning operating-state brief.

The command reads existing deterministic local artifacts and reports current state. It does not run intake, research, graph, thesis, intelligence, providers, web retrieval, or external services.

## CLI

Generate a morning brief:

```bash
python -m constellation morning
```

Export the current Markdown brief:

```bash
python -m constellation morning --export
```

Overwrite an existing brief:

```bash
python -m constellation morning --overwrite
```

Outputs:

```text
outputs/morning/morning-brief.json
outputs/morning/morning-brief.md
```

## Inputs

The morning brief reads these local artifacts when present:

- `outputs/intake/intake-manifest.json`
- `outputs/google-drive/google-drive-sync-manifest.json`
- `memory/evidence/`
- `memory/graph/graph.json`
- `outputs/analysis/cross-document-analysis.json`
- `outputs/theses/theses.json`
- `outputs/intelligence/institutional-intelligence.json`

Missing artifacts are reported as limitations and recommended next actions.

## Brief Contents

The brief includes:

- date/time created
- intake summary
- Google Drive sync summary
- new documents detected
- evidence count
- graph node and edge counts
- top findings
- top theses
- intelligence summary
- risks or gaps
- recommended next actions
- provenance references
- limitations

## Safety

- No provider calls.
- No LLM inference.
- No web retrieval.
- No autonomous decisions.
- No external dependencies.
- No Gmail connector.
- No automatic downstream workflow execution.

The morning command reports current state only.
