# Knowledge Graph v2.3

Constellation v2.3.0 adds a deterministic, file-based Knowledge Graph that connects evidence, sources, workflows, artifacts, and conservatively extracted knowledge nodes.

The graph is built only when explicitly requested. It does not use LLM inference, web retrieval, embeddings, vector databases, or an external graph database.

## Purpose

The Knowledge Graph transforms stored evidence into connected institutional knowledge:

- Which source produced this evidence?
- Which workflow referenced it?
- Which artifacts were produced?
- Which explicit concepts, topics, themes, risks, assumptions, and recommendations appeared in the source?

## Model

`GraphNode` fields:

- `node_id`
- `node_type`
- `label`
- `description`
- `source_ids`
- `evidence_ids`
- `artifact_ids`
- `workflow_run_ids`
- `confidence`
- `metadata`
- `created_at`
- `updated_at`

`GraphEdge` fields:

- `edge_id`
- `source_node_id`
- `target_node_id`
- `relationship_type`
- `evidence_ids`
- `confidence`
- `metadata`
- `created_at`
- `updated_at`

The graph is stored at:

```text
memory/graph/graph.json
```

## Node Types

- `evidence`
- `concept`
- `topic`
- `theme`
- `workflow`
- `artifact`
- `source`
- `assumption`
- `risk`
- `recommendation`

## Edge Types

- `supports`
- `contradicts`
- `relates_to`
- `derived_from`
- `references`
- `strengthens`
- `weakens`
- `updates`
- `supersedes`
- `depends_on`
- `produces`
- `belongs_to`

## Deterministic Extraction Rules

The graph builder uses existing evidence and artifacts.

Rules:

- Every `EvidenceItem` becomes an `evidence` node.
- Every workflow run becomes a `workflow` node.
- Every artifact becomes an `artifact` node.
- Source files become `source` nodes.
- Evidence nodes connect to source nodes with `derived_from`.
- Artifact nodes connect to evidence nodes with `references` when artifacts cite evidence IDs.
- Workflow nodes connect to artifacts with `produces`.
- Workflow nodes connect to evidence with `references`.

Conservative source text extraction:

- Markdown headings beginning with `#`, `##`, or `###` create `topic` nodes.
- Lines beginning with `Concept:` create `concept` nodes.
- Lines beginning with `Theme:` create `theme` nodes.
- Lines beginning with `Risk:` create `risk` nodes.
- Lines beginning with `Assumption:` create `assumption` nodes.
- Lines beginning with `Recommendation:` create `recommendation` nodes.

No unstated concept is inferred.

## CLI Usage

Build or update the graph from one run:

```bash
python -m constellation graph build RUN_ID
```

List nodes:

```bash
python -m constellation graph nodes
```

List edges:

```bash
python -m constellation graph edges
```

Show a node or edge:

```bash
python -m constellation graph show NODE_OR_EDGE_ID
```

Export markdown:

```bash
python -m constellation graph export
```

The export is written to:

```text
outputs/graph/knowledge-graph.md
```

## Relationship To Evidence Engine

The Knowledge Graph depends on evidence records under `memory/evidence/`. Evidence remains the source-backed layer; graph nodes and edges organize those records into navigable institutional structure.

## Relationship To Research Organization

Research workflows produce deterministic evidence records from source text. Running `graph build RUN_ID` after a research run connects the source, evidence, workflow, and research artifacts.

## Relationship To PKOS Knowledge Organization

PKOS ingestion workflows produce proposed knowledge packages. Running `graph build RUN_ID` after a PKOS run connects source evidence, proposed artifacts, explicit concepts, and PKOS workflow output without mutating any external vault.

## Limitations

- No automatic graph build.
- No LLM inference for graph construction.
- No PDF parsing.
- No web retrieval.
- No embeddings or vector database.
- No external graph database.
- No direct Obsidian mutation.

## Future Roadmap

- Graph diffing across workflow runs.
- Evidence support and contradiction analysis.
- Human-reviewed graph promotion.
- Graph-backed PKOS package previews.
- Optional guarded export into external knowledge systems.
