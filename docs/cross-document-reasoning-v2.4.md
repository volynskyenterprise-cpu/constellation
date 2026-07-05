# Cross-Document Reasoning v2.4

Constellation v2.4.0 adds deterministic cross-document reasoning on top of the file-based Knowledge Graph.

The analysis is conservative and explainable. It does not use LLM inference, semantic similarity, embeddings, web retrieval, vector databases, or external graph databases.

## Purpose

Cross-document reasoning helps identify patterns across multiple sources and workflow runs:

- repeated concepts
- repeated themes
- repeated risks
- repeated assumptions
- repeated recommendations
- source clusters
- explicitly marked possible contradictions
- nodes missing evidence
- confidence signals from repeated labels across independent sources

## Model

`CrossDocumentFinding` fields:

- `finding_id`
- `finding_type`
- `title`
- `summary`
- `node_ids`
- `evidence_ids`
- `source_ids`
- `workflow_run_ids`
- `confidence`
- `rationale`
- `metadata`
- `created_at`

`CrossDocumentAnalysis` fields:

- `analysis_id`
- `graph_version`
- `findings`
- `created_at`
- `metadata`

Analysis outputs are written to:

```text
outputs/analysis/cross-document-analysis.json
outputs/analysis/cross-document-analysis.md
```

Existing analysis files are not overwritten unless `--overwrite` is supplied.

## Deterministic Rules

Repeated labels:

- Same concept label in more than one source or workflow run creates `repeated_concept`.
- Same theme label creates `repeated_theme`.
- Same risk label creates `repeated_risk`.
- Same assumption label creates `repeated_assumption`.
- Same recommendation label creates `repeated_recommendation`.

Source clusters:

- Sources sharing at least one concept, theme, risk, or recommendation label create `source_cluster`.

Possible contradictions:

- Only explicit markers create contradiction findings:
  - `Contradiction:`
  - `Conflicts with:`
  - `Opposes:`
  - `Disputes:`

Missing evidence:

- Concept, theme, risk, and recommendation nodes with no evidence IDs create `missing_evidence`.

Confidence signals:

- Labels repeated across two independent source files receive `medium`.
- Labels repeated across three or more independent source files receive `high`.
- Otherwise confidence is `low`.

No semantic contradiction or similarity is inferred.

## CLI Usage

Build graph from multiple runs first:

```bash
python -m constellation graph build RUN_ID_1
python -m constellation graph build RUN_ID_2
```

Run analysis:

```bash
python -m constellation graph analyze
```

Overwrite existing analysis intentionally:

```bash
python -m constellation graph analyze --overwrite
```

List findings:

```bash
python -m constellation graph findings
```

Show one finding:

```bash
python -m constellation graph findings show FINDING_ID
```

Export findings:

```bash
python -m constellation graph findings export
```

## Example

Two source documents that both contain:

```text
Concept: Evidence Engine
Theme: Traceability
Risk: unsupported inference
```

will produce repeated concept, theme, risk, source cluster, and confidence signal findings after graph analysis.

## Relationship To Evidence Engine

Evidence records provide the source-backed basis for findings. Findings reference graph nodes and evidence IDs where available.

## Relationship To Knowledge Graph

Cross-document analysis reads `memory/graph/graph.json`. It does not build the graph automatically and does not mutate workflow memory.

## Relationship To Research And PKOS

Research and PKOS workflows create evidence and artifacts. After building graph entries from multiple runs, cross-document analysis can identify repeated explicit labels and source clusters across those runs.

## Why No LLM Inference Yet

This release prioritizes traceability over recall. Every finding must be explainable by a deterministic rule and traceable to graph nodes and evidence IDs.

## Future Roadmap

- Human-reviewed finding acceptance and rejection.
- Cross-run contradiction review workflows.
- Evidence-weighted confidence upgrades.
- Graph diffing between analysis versions.
- A future Institutional Reasoning Engine that can use models only after deterministic evidence controls are mature.
