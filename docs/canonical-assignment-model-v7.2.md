# Constellation Real Estate Intelligence v7.2 - Canonical Assignment Model

The Canonical Assignment Model unifies Real Estate Intelligence around one operational assignment object per real-world appraisal assignment.

This is a deterministic persistence and operations layer. It does not generate valuation opinions, select comparables, create adjustments, interpret permits, or produce USPAP conclusions.

## Purpose

Before v7.2, Assignment Consolidation could correctly recognize that many artifacts belonged to the same assignment, but Assignment Auto-Ingestion still wrote some artifacts into separate assignment directories.

v7.2 changes the operating model:

```text
Intake Artifacts
  -> Identity Resolution
  -> Canonical Assignment
  -> Assignment Intelligence
  -> Comparable Intelligence
  -> Adjustment Intelligence
```

One real-world assignment should have:

- one canonical assignment ID
- one canonical assignment directory
- many aliases
- many source artifacts
- one assignment brief
- one source manifest
- one timeline
- one fact set
- one risk set

## Architecture

Assignment Consolidation remains the identity-resolution layer.

It decides which local intake artifacts belong together using deterministic relationships.

The Canonical Assignment Model is the persistence and operational layer.

It writes one canonical assignment record and alias index from consolidation output, then routes intake and assignment commands to the canonical assignment.

Assignment Intelligence remains the analysis layer.

It builds facts, missing information, risks, source manifests, and timelines from the canonical assignment directory.

## Canonical ID Rules

Canonical assignment IDs use the v7.1.2 deterministic identity hierarchy:

1. explicit `assignment_id`
2. explicit `order_id`
3. explicit `loan_number`
4. normalized address plus effective date
5. normalized address
6. earliest stable source-generated alias
7. deterministic hash fallback

Existing strong canonical IDs are kept stable. Adding a stronger identifier later should create a migration recommendation rather than silently renaming directories.

## Alias Types

The alias index supports:

- canonical assignment ID
- explicit assignment ID
- order ID
- loan number
- source-generated alias
- address-derived alias
- normalized property address
- previous canonical ID
- hash fallback alias

If an alias resolves to multiple canonical assignments, Constellation reports ambiguity and requires the operator to use an explicit canonical ID.

## Normalization

The shared deterministic normalization layer handles:

- HTML cleanup including `&nbsp;`, `&#160;`, and non-breaking spaces
- U.S. date formats such as `YYYY-MM-DD`, `MM/DD/YYYY`, `M/D/YYYY`, `MM-DD-YYYY`, and explicit ISO timestamps
- address abbreviation normalization for street suffixes
- unit normalization for `Unit 312`, `#312`, `Apt 312`, and `Suite 312`
- ZIP and ZIP+4 compatibility
- path normalization to avoid repeated Windows path escaping

Normalized-equivalent values do not create conflicts. Original source values remain preserved in provenance.

## Intake Integration

Real Estate intake now routes each artifact through canonical assignment resolution before writing assignment files.

New behavior:

1. scan/import artifact
2. resolve canonical assignment ID
3. create or update only the canonical assignment directory
4. attach source artifacts and provenance
5. merge explicit structured fields conservatively
6. build Assignment Intelligence once per affected canonical assignment
7. refresh canonical outputs and dashboard

Alias-only directories are not created during clean import.

## Canonical Directory Model

Canonical private assignment files live under:

```text
real-estate/assignments/<CANONICAL_ASSIGNMENT_ID>/
  assignment.yaml
  aliases.json
  source-index.json
  sources/
  notes/
  evidence/
```

Generated outputs live under:

```text
outputs/real-estate/assignments/<CANONICAL_ASSIGNMENT_ID>/
  assignment.json
  assignment-brief.md
  source-manifest.json
  source-manifest.md
  evidence-index.json
  evidence-index.md
  missing-information.json
  missing-information.md
  assignment-risks.json
  assignment-risks.md
  assignment-timeline.json
  assignment-timeline.md
  assignment-history.json
  assignment-delta.json
  aliases.json
  canonical-resolution.json
```

Canonical model outputs live under:

```text
outputs/real-estate/canonical/
  canonical-assignments.json
  canonical-assignments.md
  assignment-alias-index.json
  assignment-alias-index.md
  canonical-migration-plan.json
  canonical-migration-plan.md
  canonical-migration-history.json
  canonical-migration-backup-manifest.json
  canonical-assignment-delta.json
  canonical-assignment-report.md
```

## CLI

```bash
python -m constellation real-estate canonical status
python -m constellation real-estate canonical assignments
python -m constellation real-estate canonical aliases
python -m constellation real-estate canonical resolve ALIAS
python -m constellation real-estate canonical migration-plan
python -m constellation real-estate canonical migrate --dry-run
python -m constellation real-estate canonical migrate --apply
python -m constellation real-estate canonical export
```

Assignment commands resolve aliases before operating:

```bash
python -m constellation real-estate assignments
python -m constellation real-estate assignments --include-aliases
python -m constellation real-estate assignment show ALIAS
python -m constellation real-estate assignment show ALIAS --open
python -m constellation real-estate assignment build ALIAS
python -m constellation real-estate assignment status ALIAS
python -m constellation real-estate assignment sources ALIAS
python -m constellation real-estate assignment missing ALIAS
python -m constellation real-estate assignment risks ALIAS
python -m constellation real-estate assignment timeline ALIAS
python -m constellation real-estate assignment export ALIAS
```

Commands print the requested alias, resolved canonical assignment ID, alias type, and resolution status when resolution succeeds.

## Migration Safety

Migration support is non-destructive.

Dry-run:

- inspects existing assignment directories
- compares directory IDs to canonical aliases
- identifies alias directories
- identifies target canonical directories
- writes a migration plan
- does not modify files

Apply:

- requires explicit `--apply`
- writes a backup manifest
- marks alias directories as migrated
- preserves alias directories
- does not delete source artifacts
- does not silently overwrite stronger non-empty fields

Deletion is intentionally unsupported in v7.2.

## Dashboard

The dashboard now reports canonical assignment state:

- canonical assignment count
- artifact count
- alias count
- unassigned artifact count
- migrated alias directory count
- pending migration count
- ambiguous alias count
- true assignment conflict count
- active assignment count
- overdue assignment count
- total missing item count
- total risk count
- top active assignments
- latest assignment brief paths

Alias directories are not counted as independent assignments.

## Limitations

- No fuzzy matching.
- No semantic similarity.
- No external address service.
- No provider calls.
- No Gmail integration.
- No web retrieval.
- No comparable selection.
- No adjustment generation.
- No permit interpretation.
- No USPAP conclusions.
- No destructive live-data migration.

## Safety Boundaries

The Canonical Assignment Model supports professional valuation workflow organization. It does not replace professional judgment.

It must never:

- expose private assignment data
- delete source artifacts
- infer unsupported property facts
- generate valuation opinions
- select comparables
- calculate adjustments
- interpret permits
- complete appraisal reports

It must always:

- preserve provenance
- preserve aliases
- report ambiguity
- report conflicts explicitly
- keep migration non-destructive
- support, not replace, valuation professionals
