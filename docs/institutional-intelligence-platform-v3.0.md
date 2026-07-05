# Institutional Intelligence Platform v3.0

Constellation v3.0.0 introduces the first end-to-end Institutional Intelligence layer.

It synthesizes existing deterministic outputs into an executive intelligence package:

```text
Research -> Evidence -> Knowledge Graph -> Cross-Document Findings -> Theses -> Executive Intelligence Brief
```

No LLM inference, semantic similarity, embeddings, web retrieval, provider calls, vector database, or external graph database is used.

## Purpose

The Institutional Intelligence Platform turns traceable work products into a proposed executive brief. It is designed to help a human decision maker inspect what the institution appears to know, what risks are recurring, where sources converge, where contradictions or evidence gaps remain, and what next actions deserve review.

The brief is not an institutional position by default. It is generated with status `proposed` and requires human review before adoption.

## Required Upstream Sequence

The intelligence command does not run upstream steps automatically.

Run the pipeline explicitly:

```bash
python -m constellation graph build RUN_ID_1
python -m constellation graph build RUN_ID_2
python -m constellation graph analyze
python -m constellation thesis generate
python -m constellation intelligence generate
```

If upstream outputs are missing, the CLI returns a clear error with the required sequence:

1. Build graph
2. Run graph analyze
3. Generate theses
4. Generate intelligence

## CLI Usage

Generate the brief:

```bash
python -m constellation intelligence generate
```

Overwrite an existing brief intentionally:

```bash
python -m constellation intelligence generate --overwrite
```

Show the current brief as JSON:

```bash
python -m constellation intelligence show
```

Export the Markdown report:

```bash
python -m constellation intelligence export
```

Outputs are written to:

```text
outputs/intelligence/institutional-intelligence.json
outputs/intelligence/institutional-intelligence.md
```

## Model

`IntelligenceBrief` fields:

- `brief_id`
- `title`
- `summary`
- `status`
- `generated_from`
- `thesis_ids`
- `finding_ids`
- `evidence_ids`
- `node_ids`
- `source_ids`
- `workflow_run_ids`
- `strategic_themes`
- `emerging_risks`
- `repeated_recommendations`
- `consensus_signals`
- `contradiction_watches`
- `evidence_gaps`
- `confidence_assessment`
- `executive_recommendations`
- `open_questions`
- `limitations`
- `approval_note`
- `metadata`
- `created_at`
- `updated_at`

Statuses:

- `draft`
- `proposed`
- `approved`
- `rejected`

v3.0.0 generation always defaults to `proposed`.

## Deterministic Rules

- Strategic themes come from `strategic_theme` theses.
- Emerging risks come from `emerging_risk` theses.
- Repeated recommendations come from `repeated_recommendation` theses.
- Consensus signals come from `source_consensus` theses.
- Contradiction watches come from `contradiction_watch` theses.
- Evidence gaps come from `evidence_gap` theses.
- Confidence assessment counts high, medium, and low thesis confidence labels.
- The overall confidence label is derived only from those counts.

The engine does not infer beyond existing theses, findings, graph nodes, and evidence records.

## Report Structure

The Markdown report includes:

- Executive Summary
- Strategic Themes
- Emerging Risks
- Consensus Signals
- Repeated Recommendations
- Contradiction Watches
- Evidence Gaps
- Confidence Assessment
- Supporting Evidence IDs
- Source References
- Open Questions
- Limitations
- Recommended Next Actions
- Human Review Note

## Safety Limitations

- No LLM inference.
- No semantic similarity.
- No embeddings.
- No web retrieval.
- No external database.
- No provider calls.
- Provider execution remains disabled by default.
- No automatic intelligence generation from graph, analysis, or thesis commands.
- Human review is required before treating the brief as institutional position.

## Relationship To Research Organization

Research workflows create source-backed artifacts and evidence. The intelligence layer does not run research workflows; it consumes outputs after graph, analysis, and thesis steps are explicitly run.

## Relationship To Evidence Engine

Evidence records provide the source-backed basis for traceability. Intelligence briefs preserve evidence IDs and source references rather than embedding unsupported conclusions.

## Relationship To Knowledge Graph

The Knowledge Graph connects evidence, sources, workflows, artifacts, and explicit source concepts. The intelligence layer reads the graph but does not mutate it.

## Relationship To Cross-Document Reasoning

Cross-Document Reasoning identifies deterministic findings across graph records. Intelligence briefs preserve finding IDs through the generated theses.

## Relationship To Thesis Engine

The Thesis Engine creates proposed institutional theses. The intelligence layer groups those theses into executive categories and summarizes confidence counts.

## v3.x Roadmap

- Human approval lifecycle for intelligence briefs.
- Intelligence comparison across brief versions.
- Brief diffing by thesis and evidence changes.
- Executive report variants by audience.
- Intelligence package review workflow using the existing approval system.
- Optional provider-assisted narrative drafting after deterministic controls are mature.
