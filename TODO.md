# TODO

## Next Engineering Milestones

- Add explicit token/context budgeting for prompt packages.
- Add context redaction policy before real provider calls.
- Add prompt package validation and schema version migration.
- Add structured artifact schema validation and schema version migration.
- Add artifact diffing between runs.
- Add artifact promotion rules from Working Memory to Project Memory.
- Add research report templates for different audiences.
- Add citation extraction and source-span tracking for research artifacts.
- Add richer evidence extraction strategies beyond deterministic line records.
- Add evidence-to-artifact validation that blocks unsupported recommendations.
- Add evidence confidence review and downgrade workflows.
- Add cross-run evidence deduplication.
- Add graph diffing across workflow runs.
- Add graph validation for unsupported artifact claims.
- Add human-reviewed graph promotion and rejection workflows.
- Add graph-backed PKOS package previews.
- Add accepted/rejected state for cross-document findings.
- Add cross-document finding comparison across analysis versions.
- Add deterministic contradiction review workflows.
- Add Institutional Reasoning Engine design over accepted evidence and graph findings.
- Add PDF parsing for research inputs.
- Add web retrieval for research workflows.
- Add research export variants for brief, memo, and appendix formats.
- Add PKOS package preview summaries and diff views.
- Add PKOS proposed-file schema validation.
- Add manual acceptance tracking for PKOS package files.
- Add future guarded Obsidian connector that requires explicit user approval before writing.
- Add prompt preview summaries for large crew doctrine sections.
- Add future expert role template generation based on `crew/HIRING_STANDARD.md`.
- Formalize the canonical schema for agent definition YAML from the Kernel v0.1 validator.
- Formalize the canonical schema for workflow definition YAML from the Kernel v0.1 validator.
- Add stricter schema validation for config registries and provider capability declarations.
- Add workflow-to-crew capability validation before execution.
- Add `validate workflows`, `validate config`, and `validate providers` commands.
- Add machine-readable JSON output for validation and health commands.
- Add CI-friendly preflight command that runs validation, health, and tests.
- Add approval rejection commands.
- Add richer approval metadata, including approver identity and notes.
- Add run summary generation from message and event logs.
- Add machine-readable output mode for `runs list` and `runs show`.
- Add filters for run status and workflow ID.
- Add `runs list --archived` and `runs restore RUN_ID`.
- Add retention policy configuration for prune defaults.
- Add sample memory curation after an example workflow.
- Decide whether Phase 2 should keep the current standard-library YAML subset parser or adopt a full YAML dependency.
- Add integration-test harness for live OpenAI calls gated behind explicit environment flags.
- Add real provider adapters for Codex, Claude, Gemini, and local models.
- Add provider selection policies based on workflow capabilities.
- Add provider result schema validation for logs, memory records, and artifacts.
- Add provider retry policy separate from fallback policy.
- Add machine-readable output mode for artifact list/show commands.
- Add approval notes and artifact review metadata.
- Write acceptance criteria for the first real non-stub research workflow.

## Deferred

- Full orchestration engine.
- Provider adapters.
- Database-backed memory.
- Vector retrieval.
- Web interface.
- Role-based access control.
