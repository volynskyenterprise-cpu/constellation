# Institutional Memory v3.4

Constellation v3.4.0 adds deterministic Institutional Memory snapshots and diffs.

Institutional Memory records the current local intelligence state only when explicitly commanded. It does not run intake, research, graph, thesis, intelligence, morning, providers, web retrieval, embeddings, or external services.

## CLI

Create a snapshot:

```bash
python -m constellation memory snapshot
python -m constellation memory snapshot --label baseline
```

List snapshots:

```bash
python -m constellation memory list
```

Show one snapshot:

```bash
python -m constellation memory show SNAPSHOT_ID
```

Diff snapshots:

```bash
python -m constellation memory diff
python -m constellation memory diff SNAPSHOT_ID_A SNAPSHOT_ID_B
```

Export the report:

```bash
python -m constellation memory export
```

## Outputs

```text
outputs/memory/snapshots.json
outputs/memory/latest-snapshot.json
outputs/memory/latest-delta.json
outputs/memory/institutional-memory.md
```

## Snapshot Contents

Snapshots include:

- snapshot ID
- label
- created timestamp
- intake counts
- Google Drive sync counts
- evidence count
- graph node count
- graph edge count
- findings count
- thesis count
- intelligence brief ID, when present
- morning brief ID, when present
- top thesis IDs
- top finding IDs
- source document references
- artifact references
- limitations
- provenance references

## Delta Contents

Deltas include:

- prior snapshot ID
- current snapshot ID
- evidence count change
- graph node change
- graph edge change
- findings count change
- thesis count change
- new and removed thesis IDs
- new and removed finding IDs
- new and removed source references
- summary
- limitations

## Safety

- No provider calls.
- No LLM inference.
- No web retrieval.
- No embeddings.
- No external dependencies.
- No Gmail connector.
- No autonomous decisions.
- No automatic upstream workflow execution.

Institutional Memory preserves and compares deterministic local state only.
