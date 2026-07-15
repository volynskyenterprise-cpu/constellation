# Constellation Real Estate Intelligence v7.2.1 - Canonical Operations Hardening

Canonical Operations Hardening makes the Canonical Assignment Model operationally consistent.

The goal is simple: every operator-facing surface should report the same canonical migration state.

- `real-estate canonical status`
- `real-estate canonical migration-plan`
- `real-estate canonical review`
- `real-estate canonical operations`
- Executive Dashboard
- Canonical reports

All of those views now consume the same deterministic operations state.

## Purpose

v7.2.0 introduced canonical assignments, aliases, and non-destructive migration planning.

v7.2.1 hardens daily operations by adding:

- synchronized migration counts
- explicit migration categories
- review queue outputs
- blocked, safe, and ambiguous assignment views
- dashboard consistency
- operator-facing reports

This release does not migrate live assignment directories automatically.

## Migration State Synchronization

Canonical status, migration plan, operations report, review queue, and dashboard summaries are generated from one refreshed canonical operations state.

The canonical assignment build now saves the current alias index before calculating migration plans. This prevents stale status counts when the migration plan sees newer aliases than the status report.

## Migration Categories

Every migration item is classified as exactly one category:

| Category | Meaning |
| --- | --- |
| `safe_merge` | Alias directory resolves deterministically to one canonical assignment and has source files to preserve. |
| `preserve_alias` | Alias directory resolves deterministically and should be preserved as an alias. |
| `blocked_by_conflict` | Canonical target has explicit conflicts that require human review. |
| `ambiguous` | Alias matches multiple canonical assignments. |
| `orphan` | Directory does not match a canonical assignment or known alias. |
| `already_migrated` | Alias directory already has a migration marker. |

No category is inferred from fuzzy matching, semantic similarity, embeddings, providers, or external systems.

## Review Queue

Canonical Operations writes:

```text
outputs/real-estate/canonical/review-queue.md
```

Review queue categories include:

- identity conflicts
- migration blocked
- ambiguous aliases
- unassigned artifacts
- missing critical fields
- repeated merge failures

Each review item includes:

- canonical assignment ID where available
- reason
- recommended review action
- supporting artifacts
- provenance

## Operations Outputs

Canonical Operations writes:

```text
outputs/real-estate/canonical/canonical-operations-report.md
outputs/real-estate/canonical/review-queue.md
outputs/real-estate/canonical/migration-summary.json
outputs/real-estate/canonical/migration-summary.md
outputs/real-estate/canonical/blocked-assignments.md
outputs/real-estate/canonical/safe-migrations.md
outputs/real-estate/canonical/ambiguous-assignments.md
```

These are generated from local deterministic artifacts only.

## CLI

```bash
python -m constellation real-estate canonical status
python -m constellation real-estate canonical review
python -m constellation real-estate canonical review --blocked
python -m constellation real-estate canonical review --safe
python -m constellation real-estate canonical review --ambiguous
python -m constellation real-estate canonical operations
python -m constellation real-estate canonical report
python -m constellation real-estate canonical conflicts
python -m constellation real-estate canonical migration-plan
```

`review --safe` shows deterministic migration items that are ready for human review before applying.

`review --blocked` shows items requiring manual review before migration.

`review --ambiguous` shows aliases that must not be resolved automatically.

## Scoped Migration Workflow

v7.2.2 adds scoped canonical migration so operators can apply only migration-ready entries.

Recommended workflow:

1. Review the queue.

```bash
python -m constellation real-estate canonical review
```

2. List ready entries.

```bash
python -m constellation real-estate canonical migrate --ready-only --list-selected
```

3. Dry-run ready entries.

```bash
python -m constellation real-estate canonical migrate --dry-run --ready-only
```

4. Apply ready entries.

```bash
python -m constellation real-estate canonical migrate --apply --ready-only
```

5. Verify state.

```bash
python -m constellation real-estate canonical status
python -m constellation dashboard --overwrite
```

Apply-eligible categories:

- `safe_merge`
- `preserve_alias`

Never applied:

- `blocked_by_conflict`
- `ambiguous`
- `orphan`
- `already_migrated`

If an unscoped `--apply` sees a mixed-category plan, it is refused with guidance to use `--ready-only`, `--category`, `--assignment`, or `--source-assignment`.

Scoped migration writes:

```text
outputs/real-estate/canonical/scoped-migration-selection.json
outputs/real-estate/canonical/scoped-migration-selection.md
outputs/real-estate/canonical/scoped-migration-result.json
outputs/real-estate/canonical/scoped-migration-result.md
```

## Dashboard Integration

The Executive Dashboard now uses Canonical Operations state for:

- canonical assignment count
- artifact count
- alias count
- pending migration count
- migration-ready count
- blocked count
- ambiguous count
- pending review count
- true assignment conflict count

Dashboard counts should match canonical status and migration plan counts.

## Safety Boundaries

Canonical Operations must never:

- modify constitution documents
- call providers
- call OpenAI
- use LLM inference
- use embeddings
- use semantic or fuzzy matching
- use web retrieval
- connect to Gmail or calendar
- generate valuation opinions
- select comparables
- generate adjustments
- interpret permits
- generate USPAP conclusions
- automatically migrate live assignment directories
- automatically resolve conflicts

Canonical Operations may:

- classify deterministic migration state
- surface review queues
- write local reports
- mark alias directories migrated only when explicitly commanded with `migrate --apply`

## Limitations

Canonical Operations is an operator visibility layer.

It does not decide whether a migration should be accepted. It identifies deterministic relationships, blocked states, ambiguous aliases, and review needs so a human can act with better visibility.
