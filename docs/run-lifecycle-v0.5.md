# Run Lifecycle v0.5

Kernel v0.5 adds workflow run lifecycle management.

The runtime remains file-based. There is no database and no automatic deletion.

## Commands

Archive a run:

```bash
python -m constellation runs archive run_225a2ecf7cd5477e966c7bf6965eec4c
```

Delete a run:

```bash
python -m constellation runs delete run_225a2ecf7cd5477e966c7bf6965eec4c
```

Prune old runs by archiving them:

```bash
python -m constellation runs prune --older-than 30
```

Prune old runs by deleting them:

```bash
python -m constellation runs prune --older-than 30 --delete
```

## Archive

`runs archive RUN_ID` moves active runtime artifacts into:

```text
archive/runs/<workflow_run_id>/
```

Archived artifacts include:

- Run logs and state
- Working memory
- Related approval records

The archive command emits a `WorkflowArchived` event before moving the run logs.

## Delete

`runs delete RUN_ID` removes active or archived runtime artifacts for a run.

Deletion requires confirmation. The CLI asks the operator to type `DELETE`.

For automation, the command supports:

```bash
python -m constellation runs delete run_225a2ecf7cd5477e966c7bf6965eec4c --yes
```

Delete is never the default prune behavior.

## Prune

`runs prune --older-than DAYS` archives active runs whose `updated_at` timestamp is older than the threshold.

Use `--delete` to explicitly delete instead of archive:

```bash
python -m constellation runs prune --older-than 90 --delete
```

When pruning with `--delete`, the CLI requires confirmation unless `--yes` is supplied.

## Lifecycle Log

Lifecycle actions are recorded in:

```text
logs/lifecycle.jsonl
```

This log records archive and delete operations even when run-specific logs are moved or removed.

## Safety Rules

- Missing run IDs return a safe error.
- Delete requires explicit confirmation.
- Prune archives by default.
- Archive preserves artifacts.
- Delete removes artifacts only when explicitly requested.
