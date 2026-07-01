# Changelog

All notable changes to Constellation will be recorded here.

## 0.0.0 - Scaffold

- Added founding blueprint documents.
- Added initial repository folder structure.
- Added V1 agent definition files.
- Added initial workflow definitions and one example workflow.
- Added model-agnostic configuration files.
- Added memory, approval, log, and test placeholder structures.
- Added developer documentation for agents, workflows, and operations.

## 0.1.0 - Kernel

- Added minimal Python package under `src/constellation/`.
- Added agent registry with required-field validation.
- Added workflow loader with agent and approval-gate validation.
- Added standardized message creation and JSONL persistence.
- Added event emission and JSONL persistence.
- Added basic Working Memory and Project Memory with Knowledge and Long-Term stubs.
- Added approval gate detection with pending approval records and no automatic bypass.
- Added YAML configuration loader.
- Added CLI command: `python -m constellation run workflows/examples/ceo-research-qa-docs.yaml`.
- Added unit tests for registry, workflow loading, messages, events, memory, and kernel execution.
- Added Kernel v0.1 developer documentation.

## 0.3.0 - Approval Continuation

- Added persisted workflow run state under `logs/runs/<workflow_run_id>/state.json`.
- Added `python -m constellation approvals list`.
- Added `python -m constellation approvals approve APPROVAL_ID`.
- Added `python -m constellation resume WORKFLOW_RUN_ID`.
- Added explicit approval continuation with no automatic bypass.
- Added `ApprovalGranted` and `WorkflowResumed` event logging.
- Added approval continuation tests.
- Added approval continuation developer documentation.

## 0.4.0 - Workflow State Inspection

- Added `python -m constellation runs list`.
- Added `python -m constellation runs show RUN_ID`.
- Added run inspection from persisted file-based workflow state.
- Added current step, created timestamp, updated timestamp, approval status, recent events, and recent messages display.
- Added graceful handling for missing and corrupt state files.
- Added workflow state inspection tests.
- Added workflow state inspection documentation.

## 0.5.0 - Run Cleanup And Lifecycle Management

- Added `python -m constellation runs archive RUN_ID`.
- Added `python -m constellation runs delete RUN_ID`.
- Added `python -m constellation runs prune --older-than DAYS`.
- Added explicit prune deletion via `--delete`.
- Added confirmation prompts for delete operations, with `--yes` for automation.
- Added file-based archive storage under `archive/runs/`.
- Added lifecycle event logging under `logs/lifecycle.jsonl`.
- Added run lifecycle tests.
- Added run lifecycle documentation.

## 0.6.0 - Provider Interface Stub

- Added provider protocol and deterministic provider result schema.
- Added provider registry loading from `config/providers.yaml`.
- Added `EchoProvider`, `NullProvider`, and `FailureProvider`.
- Added provider CLI commands: `providers list`, `providers show PROVIDER_NAME`, and `providers health`.
- Added optional provider invocation hook behind a disabled-by-default config flag.
- Added provider tests and documentation.

## 0.7.0 - Provider-Backed Agent Outputs

- Added opt-in provider-backed workflow step output.
- Added provider routing through `default_provider` and `per_agent_provider`.
- Added provider result metadata persistence in message logs, event logs, and working memory.
- Added provider failure handling with `ProviderFailed` events and failed workflow status.
- Added explicit fallback behavior controlled by `allow_fallback` and `fallback_provider`.
- Added provider-backed agent tests and documentation.

## Phase II Foundation - The Organization

- Added the `crew/` organizational layer.
- Added complete professional doctrine folders for all founding crew members.
- Added organization-wide collaboration, escalation, org chart, and hiring standard documents.
- Updated project documentation to distinguish runtime agent YAML from durable professional role doctrine.

## 0.8.0 - Context Engine

- Added Crew Loader for professional role doctrine in `crew/<role>/`.
- Added immutable `ExecutionContext` assembly for workflow runs.
- Added context assembly from workflow state, workflow definition, crew doctrine, messages, events, memory, provider routing, and approval state.
- Added `python -m constellation context show RUN_ID`.
- Added Context Engine tests and documentation.

## 0.9.0 - Prompt Assembly Engine

- Added deterministic `PromptPackage` schema.
- Added Prompt Assembler from crew doctrine, workflow step, messages, memory, and provider routing.
- Added `python -m constellation prompt show RUN_ID`.
- Added optional `--step STEP_ID` prompt inspection.
- Added prompt package persistence under `logs/runs/<run_id>/prompts/`.
- Added provider integration so enabled providers receive prompt packages.
- Added prompt package metadata to message/event logs and working memory when provider-backed execution is enabled.
- Added Prompt Assembly tests and documentation.

## 1.0.0 - First Executable AI Organization Workflow

- Added `AgentArtifact` schema for structured provider-backed crew outputs.
- Added deterministic provider-result parsing into structured artifacts.
- Added artifact persistence under `logs/runs/<run_id>/artifacts/`.
- Added artifact references to Working Memory for provider-backed workflow steps.
- Added artifact metadata records to message logs and artifact lifecycle events to event logs.
- Added `python -m constellation artifacts list RUN_ID`.
- Added `python -m constellation artifacts show RUN_ID ARTIFACT_ID`.
- Preserved disabled-by-default provider invocation and placeholder behavior.
- Added Executable Organization v1.0 documentation and tests.
