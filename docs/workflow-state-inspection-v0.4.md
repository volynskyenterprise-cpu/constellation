# Workflow State Inspection v0.4

Kernel v0.4 adds read-only workflow run inspection.

The runtime remains file-based. Run inspection reads existing state, message logs, event logs, memory paths, and approval records. It does not create a database.

## Commands

List known workflow runs:

```bash
python -m constellation runs list
```

Show one workflow run:

```bash
python -m constellation runs show run_bbe65d3ff4c54baa87022f343eac0ef9
```

## runs list

`runs list` displays:

- Workflow run ID
- Workflow ID
- Status
- Current step
- Created timestamp
- Updated timestamp

Runs are sorted newest first when timestamps are available.

Invalid or corrupt state files are listed as `invalid_state` rather than crashing the command.

## runs show

`runs show RUN_ID` displays:

- Workflow run ID
- Workflow ID
- Status
- Current step
- Approval status
- Message log path
- Event log path
- Working memory path
- Recent events
- Recent messages

If the run ID does not exist, the command reports an error.

## State Source

The inspector reads:

```text
logs/runs/<workflow_run_id>/state.json
logs/runs/<workflow_run_id>/events.jsonl
logs/runs/<workflow_run_id>/messages.jsonl
memory/runs/<workflow_run_id>-working.json
approvals/pending/
approvals/accepted/
```

## Status Notes

- `needs_approval` indicates a paused run waiting for explicit approval.
- `completed` indicates all workflow steps have finished.
- `invalid_state` indicates a missing or corrupt state file was found during listing.
