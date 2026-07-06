# Executive Dashboard v3.8

Constellation v3.8 adds a deterministic Executive Dashboard that presents the current operating state in one concise view.

The dashboard consumes existing outputs only. It does not create new intelligence logic, run upstream workflows, call providers, use LLM inference, use embeddings, use semantic similarity, use web retrieval, add Gmail, or make autonomous decisions.

## Commands

```bash
python -m constellation dashboard
python -m constellation dashboard --export
python -m constellation dashboard --overwrite
python -m constellation dashboard status
```

## Outputs

```text
outputs/dashboard/dashboard.json
outputs/dashboard/dashboard.md
```

## Inputs

The dashboard reads:

- `outputs/daily/daily-run.json`
- `outputs/daily/daily-report.md`
- `outputs/morning/morning-brief.json`
- `outputs/memory/latest-snapshot.json`
- `outputs/memory/latest-delta.json`
- `outputs/evidence-graph/evidence-graph.json`
- `outputs/thesis/theses.json`
- `outputs/thesis/thesis-report.md`
- `outputs/google-drive/google-drive-sync-manifest.json`
- `outputs/intake/intake-manifest.json`

Missing inputs are reported as unavailable. Missing values are not fabricated.

## Sections

The Markdown dashboard includes:

1. Executive Summary
2. Daily Pipeline Status
3. Intake / Google Drive Summary
4. Evidence Summary
5. Evidence Graph Summary
6. Thesis Intelligence Summary
7. Institutional Memory Summary
8. Morning Brief Summary
9. Current Risks / Gaps
10. Recommended Next Actions
11. Key Output Files
12. Limitations
13. Provenance

## Status

```bash
python -m constellation dashboard status
```

This reports which expected input artifacts exist. It does not generate a dashboard or run upstream modules.

## Safety

The dashboard is read-only with respect to upstream intelligence artifacts. It writes only dashboard outputs.

It never:

- calls providers
- invokes LLM inference
- uses embeddings
- uses semantic similarity
- uses web retrieval
- uses Gmail
- runs workflows automatically
- makes autonomous decisions
