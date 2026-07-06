# Thesis Intelligence v3.6

Constellation v3.6 adds a deterministic Thesis Intelligence layer for maintaining institutional theses over time.

This layer does not create conclusions from model inference. It consumes existing local artifacts and records the explicit evidence, conflicts, findings, source references, memory snapshots, and morning brief references already attached to thesis records.

## Safety Model

Thesis Intelligence does not:

- call providers
- call OpenAI
- use LLM inference
- use embeddings
- use semantic similarity
- use web retrieval
- use Gmail
- execute workflows automatically

It uses only deterministic relationships already present in local evidence records, findings, the Evidence Graph, the Knowledge Graph, institutional memory snapshots, and morning briefs.

## Commands

```bash
python -m constellation thesis build
python -m constellation thesis list
python -m constellation thesis show THESIS_ID
python -m constellation thesis timeline THESIS_ID
python -m constellation thesis export
```

The older generated thesis command remains available:

```bash
python -m constellation thesis generate
```

`thesis build` writes the Thesis Intelligence store under `outputs/thesis/`. When that store exists, `thesis list`, `thesis show`, and `thesis export` inspect Thesis Intelligence records. If it does not exist, those commands continue to fall back to the older generated thesis store under `outputs/theses/`.

## Outputs

```text
outputs/thesis/theses.json
outputs/thesis/thesis-history.json
outputs/thesis/thesis-report.md
```

## Thesis Status

Statuses are deterministic:

- `active`: thesis has support and no new strengthening or weakening condition.
- `strengthening`: supporting evidence increased, or support/repeated confirmations meet the high-confidence rule.
- `weakening`: conflicts or explicit contradiction records are present or increased.
- `archived`: thesis no longer appears in local thesis or evidence graph outputs, or has no supporting/conflicting evidence.

## Confidence

Confidence is rule-based, not probabilistic:

- `high`: three or more supporting evidence IDs, or repeated confirmation findings.
- `medium`: at least one supporting evidence ID and no dominant conflict.
- `low`: no support, explicit contradiction, or conflict count greater than/equal to support count.

The report records the rule used for every thesis.

## Timeline

Each thesis has timeline events:

- `created`
- `updated`
- `strengthened`
- `weakened`
- `archived`

Timeline records include the timestamp, reason, and affected evidence IDs.

## Report

`thesis-report.md` includes:

- Summary
- Active theses
- Strengthening theses
- Weakening theses
- Archived theses
- Supporting evidence counts
- Conflict counts
- Recent timeline events
- Morning brief references
- Memory snapshot references
- Limitations

## Limitations

- Thesis Intelligence does not determine truth.
- It only tracks explicit local relationships.
- Missing IDs mean missing relationships.
- Equivalent source names are not merged unless prior deterministic artifacts already connected them.
