# Constellation Real Estate Intelligence v7.0 - Assignment Intelligence MVP

Assignment Intelligence is the first deterministic Real Estate Intelligence capability in Constellation.

It answers:

- What assignment am I working on?
- What source documents are available?
- What required information is missing?
- Which structured facts conflict exactly?
- What review risks should be resolved before professional analysis continues?

## Scope

This MVP is a local, file-based assignment intake and review layer. It creates assignment briefs, source manifests, evidence indexes, missing-information lists, risk reports, timeline records, history snapshots, and deterministic deltas.

It does not parse PDFs, images, sketches, MLS exports, or appraisal reports. It records source-file metadata and checksums only.

## Private Assignment Convention

Private assignment data belongs under:

```text
real-estate/assignments/<ASSIGNMENT_ID>/
  assignment.yaml
  sources/
  notes/
  evidence/
```

The assignment directory is ignored by Git. Keep client data, property records, reviewer conditions, source files, photos, reports, and private notes out of commits.

## Commands

```bash
python -m constellation real-estate assignments
python -m constellation real-estate assignment create-template ASSIGNMENT_ID
python -m constellation real-estate assignment build ASSIGNMENT_ID
python -m constellation real-estate assignment status ASSIGNMENT_ID
python -m constellation real-estate assignment show ASSIGNMENT_ID
python -m constellation real-estate assignment sources ASSIGNMENT_ID
python -m constellation real-estate assignment missing ASSIGNMENT_ID
python -m constellation real-estate assignment risks ASSIGNMENT_ID
python -m constellation real-estate assignment timeline ASSIGNMENT_ID
python -m constellation real-estate assignment export ASSIGNMENT_ID
```

## Outputs

Assignment outputs are written to:

```text
outputs/real-estate/assignments/<ASSIGNMENT_ID>/
```

Generated files include:

- `assignment.json`
- `assignment-brief.md`
- `source-manifest.json`
- `source-manifest.md`
- `evidence-index.json`
- `evidence-index.md`
- `missing-information.json`
- `missing-information.md`
- `assignment-risks.json`
- `assignment-risks.md`
- `assignment-timeline.json`
- `assignment-timeline.md`
- `assignment-history.json`
- `assignment-delta.json`

## Structured Facts

Structured facts are optional. The default template uses `facts: []`.

When facts are provided, `value` must be explicit. Empty, missing, null, or whitespace-only values are omitted from the fact list. `unit`, `notes`, `verification_status`, and `source_paths` are metadata fields and are never substituted as the fact value.

Valid zero and boolean false values are preserved.

## Dashboard Integration

The Executive Dashboard includes a Real Estate Assignment Intelligence section when local assignments exist. It reports active, waiting, review, and overdue assignment counts, missing-item counts, risk counts, highest-priority assignments, and latest assignment brief paths.

## Safety Boundaries

Assignment Intelligence must never:

- Generate unsupported values.
- Invent comparable sales.
- Invent adjustments.
- Invent permits.
- Invent market evidence.
- Replace professional valuation judgment.
- Automatically complete appraisal reports.
- Provide USPAP opinions without evidence.

Assignment Intelligence may:

- Preserve assignment provenance.
- Index local source metadata.
- Identify missing assignment information.
- Identify exact structured conflicts.
- Produce deterministic review checklists.
- Support professional judgment without replacing it.

## Limitations

- No PDF parsing.
- No OCR.
- No image analysis.
- No MLS parsing.
- No permit retrieval.
- No web retrieval.
- No provider calls.
- No valuation conclusions.
