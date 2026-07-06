# Knowledge Evolution Engine v4.1

Constellation v4.1 adds a deterministic longitudinal intelligence layer.

Knowledge Evolution answers:

- What changed?
- Why did it change?
- Which theses strengthened or weakened?
- Which evidence appeared or disappeared?
- Which sources are becoming more active?
- Which research workflows are accelerating?

No AI inference is used. The engine consumes existing local outputs only.

## Commands

```bash
python -m constellation evolution
python -m constellation evolution status
python -m constellation evolution history
python -m constellation evolution export
python -m constellation evolution compare SNAPSHOT_A SNAPSHOT_B
```

## Inputs

Knowledge Evolution reads:

- `outputs/memory/snapshots.json`
- `memory/evidence/`
- `memory/graph/graph.json`
- `outputs/thesis/theses.json`
- `outputs/source-monitor/source-history.json`
- `outputs/daily/daily-history.json`
- `outputs/workflows/workflow-history.json`

Missing artifacts are treated as empty local state. Values are never fabricated.

## Outputs

The engine writes:

- `outputs/evolution/evolution.json`
- `outputs/evolution/evolution.md`
- `outputs/evolution/trend-report.md`
- `outputs/evolution/trend-history.json`

## Metrics

The deterministic delta includes:

- evidence gained
- evidence removed
- graph node growth
- graph edge growth
- thesis confidence changes
- thesis status changes
- source activity trends
- research volume trends
- workflow execution trends
- longitudinal health score

## Daily Pipeline

Daily Pipeline now runs Knowledge Evolution after Institutional Memory and before downstream graph/thesis refresh.

## Dashboard

Executive Dashboard now includes a Knowledge Evolution Summary with:

- Evidence Growth
- Graph Growth
- Thesis Changes
- Fastest Growing Sources
- Most Active Research Areas
- Recent Trend Changes
- Longitudinal Health Score

## Safety

Knowledge Evolution does not call providers, OpenAI, Gmail, web retrieval, embeddings, semantic search, or LLM inference. It does not schedule or autonomously execute workflows.
