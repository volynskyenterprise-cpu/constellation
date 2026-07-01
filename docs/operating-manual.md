# Operating Manual

Constellation V1 is document-first and manually operated.

## Running A Workflow Manually

1. Select a workflow from `workflows/`.
2. Confirm the objective with the human.
3. Load relevant memory from `memory/`.
4. Invoke each listed agent in order.
5. Capture agent outputs in a run log under `logs/runs/`.
6. Pause at human approval gates.
7. Record approval decisions under `approvals/`.
8. Propose memory updates.
9. Ask the Knowledge Engineer to curate durable updates.
10. Record final artifacts and residual risk.

## Operating Rules

- Keep the human in control of consequential decisions.
- Preserve uncertainty instead of smoothing it away.
- Record why decisions were made.
- Do not promote memory without provenance.
- Do not bypass approval gates.
