# Thesis Engine v2.5

Constellation v2.5.0 adds a deterministic Thesis Engine on top of Cross-Document Reasoning.

The Thesis Engine converts explicit cross-document findings into proposed institutional theses. It does not use LLM inference, semantic similarity, embeddings, web retrieval, provider calls, vector databases, or external graph databases.

## Purpose

Cross-document findings identify repeated labels, risks, recommendations, source clusters, evidence gaps, and explicit contradiction markers. The Thesis Engine turns those findings into reviewable propositions that an institution can accept, reject, supersede, or keep under watch.

Theses are not beliefs by default. Every generated thesis starts as `proposed` and requires human review before it can be treated as accepted knowledge.

## Model

`Thesis` fields:

- `thesis_id`
- `title`
- `summary`
- `thesis_type`
- `status`
- `confidence`
- `supporting_finding_ids`
- `supporting_evidence_ids`
- `supporting_node_ids`
- `source_ids`
- `workflow_run_ids`
- `counterpoint_finding_ids`
- `risks`
- `assumptions`
- `recommendations`
- `open_questions`
- `rationale`
- `metadata`
- `created_at`
- `updated_at`

Outputs are written to:

```text
outputs/theses/theses.json
outputs/theses/theses.md
```

Existing thesis outputs are not overwritten unless `--overwrite` is supplied.

## Thesis Types

- `strategic_theme`
- `emerging_risk`
- `repeated_recommendation`
- `evidence_gap`
- `source_consensus`
- `contradiction_watch`

## Statuses

- `proposed`
- `accepted`
- `rejected`
- `superseded`

v2.5.0 only generates `proposed` theses. Acceptance remains a future human-reviewed lifecycle action.

## Generation Rules

The engine reads `outputs/analysis/cross-document-analysis.json`.

Rules:

- `repeated_concept` or `repeated_theme` with `high` confidence creates `strategic_theme`.
- `repeated_risk` creates `emerging_risk`.
- `repeated_recommendation` creates `repeated_recommendation`.
- `missing_evidence` creates `evidence_gap`.
- `source_cluster` with `high` confidence creates `source_consensus`.
- `possible_contradiction` creates `contradiction_watch`.

The engine does not infer beyond findings. Every thesis references its supporting finding IDs and evidence IDs when available.

## CLI Usage

Build graph entries from workflow runs:

```bash
python -m constellation graph build RUN_ID_1
python -m constellation graph build RUN_ID_2
```

Run cross-document analysis:

```bash
python -m constellation graph analyze
```

Generate theses:

```bash
python -m constellation thesis generate
```

Overwrite existing thesis outputs intentionally:

```bash
python -m constellation thesis generate --overwrite
```

List theses:

```bash
python -m constellation thesis list
```

Show one thesis:

```bash
python -m constellation thesis show THESIS_ID
```

Export Markdown:

```bash
python -m constellation thesis export
```

## Safety

- No provider calls.
- No LLM inference.
- No semantic similarity.
- No embeddings.
- No web retrieval.
- No external graph database.
- No automatic thesis acceptance.
- No automatic generation during graph analysis.

Provider execution remains disabled by default and is not used by the Thesis Engine.

## Relationship To Existing Layers

Evidence Engine provides source-backed records.

Knowledge Graph connects evidence, sources, workflows, artifacts, and explicit labels.

Cross-Document Reasoning creates deterministic findings from the graph.

Thesis Engine turns selected findings into proposed institutional theses for human review.

## Roadmap

- Human-reviewed thesis acceptance and rejection.
- Thesis supersession and version history.
- Thesis comparison across analysis versions.
- Thesis-driven workflow recommendations.
- Evidence-weighted thesis confidence refinement.
