# Evidence Graph v3.5

Constellation v3.5 adds a deterministic Evidence Graph: a focused analytical view over relationships between evidence records, sources, workflow runs, artifacts, cross-document findings, theses, morning briefs, and institutional memory snapshots.

The Evidence Graph does not replace the Knowledge Graph. The Knowledge Graph models institutional concepts and cross-document structure. The Evidence Graph models traceability: what exact evidence, IDs, and source references support or preserve downstream intelligence.

## Safety Model

The Evidence Graph is local and deterministic.

- It does not call providers.
- It does not use LLM inference.
- It does not use embeddings or semantic similarity.
- It does not use web retrieval.
- It does not infer relationships from similar wording.
- It does not run intake, research, graph, thesis, intelligence, memory, or morning workflows automatically.

Relationships are created only from exact IDs or explicit source references already present in local artifacts.

## Build

```bash
python -m constellation evidence-graph build
```

This reads existing local artifacts and writes:

```text
outputs/evidence-graph/evidence-graph.json
outputs/evidence-graph/evidence-graph.md
```

## Inspect

```bash
python -m constellation evidence-graph nodes
python -m constellation evidence-graph edges
python -m constellation evidence-graph show NODE_OR_EDGE_ID
python -m constellation evidence-graph export
```

`show` accepts either an Evidence Graph node ID, an edge ID, or a direct referenced ID such as an evidence ID.

## Node Types

- `evidence`
- `source`
- `workflow`
- `artifact`
- `finding`
- `thesis`
- `morning_brief`
- `memory_snapshot`

## Edge Types

- `derived_from`
- `referenced_by`
- `supports`
- `contributes_to`
- `appears_in`
- `summarized_by`
- `preserved_in`
- `conflicts_with`
- `repeats`

Every edge includes metadata describing why it exists and which exact field created it.

## Relationship Rules

The builder creates relationships only when proven by stored data:

- Evidence to source from `source_identifier`.
- Evidence to workflow from `workflow_run_id`.
- Evidence to artifact from artifact `evidence_used`.
- Evidence to finding from finding `evidence_ids`.
- Evidence to thesis from thesis `supporting_evidence_ids`.
- Finding to thesis from thesis `supporting_finding_ids`.
- Thesis to morning brief from morning `top_theses`.
- Thesis to memory snapshot from snapshot `top_thesis_ids`.
- Source to memory snapshot from snapshot `source_document_references`.
- Source to morning brief from morning `new_documents_detected.path`.

Conflict and repeat edges are created only from explicit finding types such as `possible_contradiction` and `repeated_*`.

## Markdown Export

The markdown report includes:

- Summary counts.
- Counts by node type.
- Counts by edge type.
- Top evidence-connected theses.
- Evidence-to-thesis paths.
- Orphan evidence records.
- Orphan theses.
- Limitations.

## Limitations

- The graph omits any relationship that cannot be proven from exact IDs or explicit source references.
- Source matching is exact; equivalent names or paths are not merged.
- The graph is a current-state analytical view, not a historical database.
- It depends on upstream artifacts already existing locally.
