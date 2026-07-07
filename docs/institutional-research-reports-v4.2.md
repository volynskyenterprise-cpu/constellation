# Institutional Research Reports v4.2

Constellation v4.2 adds deterministic Institutional Research Reports.

Reports answer:

- What changed?
- What matters?
- What evidence supports it?
- Which theses are strengthening or weakening?
- What risks or gaps exist?
- What should be reviewed next?
- What are the open questions?
- Which source documents support the report?

## Commands

```bash
python -m constellation report latest
python -m constellation report latest --export
python -m constellation report status
python -m constellation report history
python -m constellation report show REPORT_ID
```

## Inputs

Reports consume existing local artifacts:

- `outputs/dashboard/dashboard.json`
- `outputs/daily/daily-run.json`
- `outputs/morning/morning-brief.json`
- `outputs/evolution/evolution.json`
- `outputs/evolution/trend-report.md`
- `outputs/thesis/theses.json`
- `outputs/thesis/thesis-report.md`
- `outputs/evidence-graph/evidence-graph.json`
- `outputs/memory/latest-snapshot.json`
- `outputs/source-monitor/latest-monitor.json`
- `outputs/workflows/latest-workflow.json`
- `outputs/intake/intake-manifest.json`
- `outputs/google-drive/google-drive-sync-manifest.json`

Missing artifacts are reported as unavailable. Values are not fabricated.

## Outputs

Reports write:

- `outputs/reports/latest-report.json`
- `outputs/reports/latest-report.md`
- `outputs/reports/report-history.json`

## Markdown Sections

1. Executive Summary
2. What Changed
3. Key Evidence
4. Thesis Intelligence
5. Knowledge Evolution
6. Source Activity
7. Risks and Gaps
8. Open Questions
9. Recommended Next Actions
10. Evidence References
11. Source Documents
12. Limitations
13. Provenance

## Dashboard And Workflow Integration

Executive Dashboard includes the latest report ID, created time, available sections, risk count, open question count, evidence reference count, and report path.

The built-in Morning workflow generates the latest institutional research report after dashboard refresh.

## Safety

Reports are deterministic presentation artifacts generated only from existing local Constellation outputs. They do not call providers, OpenAI, LLM inference, embeddings, semantic search, web retrieval, Gmail, scheduling, or autonomous execution.
