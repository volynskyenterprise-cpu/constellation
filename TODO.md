# TODO

## Next Engineering Milestones

- Formalize the canonical schema for agent definition YAML from the Kernel v0.1 validator.
- Formalize the canonical schema for workflow definition YAML from the Kernel v0.1 validator.
- Add stricter validation for config registries and provider capability declarations.
- Add approval rejection commands.
- Add richer approval metadata, including approver identity and notes.
- Add run summary generation from message and event logs.
- Add machine-readable output mode for `runs list` and `runs show`.
- Add filters for run status and workflow ID.
- Add `runs list --archived` and `runs restore RUN_ID`.
- Add retention policy configuration for prune defaults.
- Add sample memory curation after an example workflow.
- Decide whether Phase 2 should keep the current standard-library YAML subset parser or adopt a full YAML dependency.
- Add real provider adapters for Codex, GPT, Claude, Gemini, and local models.
- Add provider selection policies based on workflow capabilities.
- Add provider result logs when provider invocation is enabled.
- Write acceptance criteria for the first end-to-end guided workflow.

## Deferred

- Full orchestration engine.
- Provider adapters.
- Database-backed memory.
- Vector retrieval.
- Web interface.
- Role-based access control.
