# Workflow Auto-Processing v4.0.1

Constellation v4.0.1 patches the built-in `Morning` workflow so newly imported research files can move through the deterministic research pipeline without requiring manual follow-up commands.

## Behavior

When explicitly invoked:

```bash
python -m constellation workflow run Morning
```

Morning now runs:

- source monitoring
- Google Drive sync when configured
- intake import
- research auto-processing for newly imported markdown/text files
- Knowledge Graph build for each generated research run
- cross-document analysis with overwrite
- thesis generation with overwrite
- Thesis Intelligence build
- Evidence Graph build
- Daily Pipeline with overwrite
- Executive Dashboard with overwrite

## Research Input Detection

Research auto-processing reads the latest intake manifest at:

```text
outputs/intake/intake-manifest.json
```

It processes only `imported` files under:

```text
research_inputs/YYYY-MM-DD/
```

Supported formats remain:

- `.md`
- `.txt`

## Duplicate Protection

Processed research files are tracked by file hash in:

```text
outputs/workflows/research-processing.json
```

Repeated Morning runs skip already processed files and report them in workflow metadata.

## Workflow Metadata

`outputs/workflows/latest-workflow.json` and `outputs/workflows/workflow-report.md` include:

- new research files detected
- research runs created
- graph builds completed
- graph builds failed
- skipped files
- errors

## Governance

Research workflows preserve existing approval behavior. If a research run pauses at an approval gate, the workflow run ID is still captured, and the graph build is attempted only through the existing graph builder.

No provider calls, OpenAI calls, Gmail, web retrieval, embeddings, semantic search, scheduling, or autonomous execution are added.
