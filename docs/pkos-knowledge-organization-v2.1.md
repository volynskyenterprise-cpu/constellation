# PKOS Knowledge Organization v2.1

Constellation v2.1.0 introduces the PKOS Knowledge Organization: a proposal-first capability for turning raw markdown or text sources into reviewable PKOS update packages.

It does not mutate an external PKOS or Obsidian vault. It creates proposed files under Constellation's own output directory for human review.

## Purpose

The PKOS Knowledge Organization ingests a raw source document and produces a proposed knowledge update package:

- Source summary
- Evidence table
- Proposed concepts
- Proposed synthesis
- Proposed map
- Proposed source record
- Validation review
- Release notes
- Review package
- Manifest

## Workflow

The workflow is defined at:

```text
workflows/pkos/pkos-ingestion.yaml
```

Crew sequence:

- CEO
- Research Lead
- Knowledge Engineer
- QA Lead
- Documentation Engineer
- Release Manager

Steps:

1. `classify_source`
2. `extract_core_claims`
3. `map_existing_knowledge`
4. `propose_knowledge_updates`
5. `challenge_update_quality`
6. `produce_pkos_package`
7. `prepare_release_notes`

The workflow pauses after `prepare_release_notes` for explicit human approval.

## Input Folder

Place source files in:

```text
pkos_inputs/
```

Supported in v2.1.0:

- `.md`
- `.txt`

PDF parsing is not implemented yet.

## CLI Usage

Create a sample input:

```bash
mkdir -p pkos_inputs
printf "# Source Note\n\nSource claim: durable knowledge should be proposed before application.\n" > pkos_inputs/source-note.md
```

Run ingestion:

```bash
python -m constellation pkos ingest pkos_inputs/source-note.md
```

Package a run:

```bash
python -m constellation pkos package RUN_ID
```

Overwrite an existing package intentionally:

```bash
python -m constellation pkos package RUN_ID --overwrite
```

## Output Package

Packages are written under:

```text
outputs/pkos/RUN_ID/
```

Generated files:

- `source-summary.md`
- `evidence-table.md`
- `proposed-concepts.md`
- `proposed-synthesis.md`
- `proposed-map.md`
- `proposed-source-record.md`
- `validation-review.md`
- `release-notes.md`
- `review-package.md`
- `manifest.json`

The manifest includes:

- `workflow_run_id`
- `source_path`
- `source_type`
- `generated_files`
- `approval_status`
- `created_at`
- `warnings`
- `limitations`

## Safety Rules

- Do not mutate a real PKOS vault.
- Do not write outside `outputs/pkos/` except normal runtime logs and memory.
- Do not auto-approve.
- Do not auto-commit.
- Do not assume source truth.
- Treat generated packages as proposals only.
- Existing package files are not overwritten unless `--overwrite` is supplied.

## Provider Behavior

Provider execution remains disabled by default.

With providers disabled, PKOS ingestion records placeholder artifacts and still requires human approval.

With EchoProvider explicitly enabled, Constellation produces deterministic structured artifacts and package content suitable for testing the workflow.

## Manual Obsidian PKOS Connection

To use the package with an external Obsidian PKOS:

1. Run `python -m constellation pkos package RUN_ID`.
2. Review every generated file in `outputs/pkos/RUN_ID/`.
3. Compare proposed concepts, synthesis, maps, and source records against your vault.
4. Manually copy approved content into the vault.
5. Keep rejected or uncertain updates out of the vault.

Constellation v2.1.0 does not connect to Obsidian directly.

## Limitations

- No PDF parsing yet.
- No web retrieval yet.
- No direct Obsidian integration yet.
- No automatic citation extraction yet.
- No source truth assumption.
- Provider execution is disabled by default.
