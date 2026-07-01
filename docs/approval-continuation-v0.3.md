# Approval Continuation v0.3

Kernel v0.3 adds explicit approval continuation.

The kernel can now:

- List pending approvals.
- Explicitly approve a pending approval record.
- Resume a workflow run after approval.
- Persist workflow run state in `logs/runs/<workflow_run_id>/state.json`.
- Emit `ApprovalGranted` and `WorkflowResumed` events.

## Commands

List pending approvals:

```bash
python -m constellation approvals list
```

Approve a pending approval:

```bash
python -m constellation approvals approve appr_6216d525db0d499cab196cb2894b4d01
```

Resume a workflow run:

```bash
python -m constellation resume run_17d3f0fea9994657b8e765195e0937e1
```

## Approval Rules

Approval is explicit. A workflow run that is blocked at an approval gate will not resume unless its pending approval record has been approved.

The approve command moves the approval record from:

```text
approvals/pending/<approval_id>.json
```

to:

```text
approvals/accepted/<approval_id>.json
```

The accepted record includes:

- `status: approved`
- `approved_at`
- `explicit_human_approval: true`

## State Persistence

Each workflow run persists state at:

```text
logs/runs/<workflow_run_id>/state.json
```

The state file records:

- Workflow run ID
- Workflow ID
- Workflow path
- Current status
- Next step index
- Pending approval ID
- Last update timestamp

## Event Logging

When approval is granted, the kernel appends an `ApprovalGranted` event to the run event log.

When a run resumes, the kernel appends a `WorkflowResumed` event.

The workflow can then continue until the next approval gate or completion.
