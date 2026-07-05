# Evidence Engine v2.2

Constellation v2.2.0 adds the foundational evidence layer for Research and PKOS workflows.

The Evidence Engine is deterministic, file-based, and local. It does not perform web retrieval, vector search, embeddings, or external service calls.

## EvidenceItem

Each evidence record includes:

- `evidence_id`
- `workflow_run_id`
- `claim`
- `supporting_quote`
- `source_identifier`
- `source_location`
- `confidence`
- `provenance`
- `created_at`
- `updated_at`

Evidence IDs are stable hash IDs derived from the workflow run, source identifier, source line number, and quote.

## Evidence Store

Evidence is stored under:

```text
memory/evidence/
```

The store supports:

- save
- load
- list
- query by run or source
- markdown export

## CLI

List evidence:

```bash
python -m constellation evidence list
```

Show one record:

```bash
python -m constellation evidence show EVIDENCE_ID
```

Export a run-level evidence report:

```bash
python -m constellation evidence export RUN_ID
```

The generic export writes:

```text
outputs/evidence/RUN_ID-evidence.md
```

Research export also writes:

```text
outputs/research/RUN_ID-evidence.md
```

PKOS packaging also writes:

```text
outputs/pkos/RUN_ID/evidence-report.md
```

## Research And PKOS Integration

When Research or PKOS workflows ingest `.md` or `.txt` inputs, Constellation creates evidence records before the first workflow step executes.

Each non-empty source line becomes one deterministic evidence record with:

- the raw line as `supporting_quote`
- a normalized line claim
- source file path as `source_identifier`
- line number as `source_location`
- source-provided confidence
- provenance describing the organization and deterministic extraction method

Provider-backed artifacts reference evidence IDs in `evidence_used` instead of embedding unsupported source claims.

## Limitations

- No PDF parsing yet.
- No web retrieval yet.
- No embeddings or vector database.
- No automatic citation span extraction beyond deterministic line locations.
- No external services.
- Provider execution remains disabled by default.
