# Changelog

All notable changes to Constellation will be recorded here.

## 3.7.0 - Daily Intelligence Pipeline

- Added deterministic Daily Intelligence Pipeline orchestration.
- Added `python -m constellation daily`.
- Added `python -m constellation daily --overwrite`.
- Added `python -m constellation daily status`.
- Added `python -m constellation daily history`.
- Added `python -m constellation daily export`.
- Added daily outputs under `outputs/daily/`.
- Added daily run, manifest, report, and history persistence.
- Reused existing intake scan, Google Drive readiness/sync, morning brief, institutional memory, Evidence Graph, and Thesis Intelligence modules.
- Preserved deterministic orchestration-only behavior with no provider calls, no OpenAI calls, no LLM inference, no embeddings, no semantic search, no web retrieval, no Gmail, and no autonomous decisions.

## 3.6.0 - Thesis Intelligence

- Added deterministic Thesis Intelligence records with support, conflict, source, morning brief, and memory snapshot references.
- Added thesis confidence records based on deterministic support/conflict/repeated-confirmation rules.
- Added thesis timeline events for created, updated, strengthened, weakened, and archived states.
- Added `python -m constellation thesis build`.
- Added `python -m constellation thesis timeline THESIS_ID`.
- Extended `thesis list`, `thesis show`, and `thesis export` to use Thesis Intelligence records when present while preserving legacy generated thesis fallback behavior.
- Added Thesis Intelligence outputs under `outputs/thesis/`.
- Preserved local-only behavior with no provider calls, no OpenAI calls, no LLM inference, no embeddings, no semantic similarity, no web retrieval, no Gmail, and no automatic workflow execution.

## 3.5.0 - Evidence Graph

- Added deterministic Evidence Graph nodes and edges across evidence, sources, workflows, artifacts, findings, theses, morning briefs, and institutional memory snapshots.
- Added `python -m constellation evidence-graph build`.
- Added `python -m constellation evidence-graph nodes`.
- Added `python -m constellation evidence-graph edges`.
- Added `python -m constellation evidence-graph show NODE_OR_EDGE_ID`.
- Added `python -m constellation evidence-graph export`.
- Added Evidence Graph outputs under `outputs/evidence-graph/`.
- Preserved exact-reference-only behavior with no provider calls, no LLM inference, no embeddings, no semantic similarity, no web retrieval, and no automatic upstream workflow execution.

## 3.4.0 - Institutional Memory

- Added deterministic institutional memory snapshots and deltas.
- Added `python -m constellation memory snapshot`.
- Added `python -m constellation memory snapshot --label LABEL`.
- Added `python -m constellation memory list`.
- Added `python -m constellation memory show SNAPSHOT_ID`.
- Added `python -m constellation memory diff`.
- Added `python -m constellation memory diff SNAPSHOT_ID_A SNAPSHOT_ID_B`.
- Added `python -m constellation memory export`.
- Added institutional memory outputs under `outputs/memory/`.
- Preserved explicit command-only behavior with no provider calls, no LLM inference, no web retrieval, and no automatic upstream workflow execution.

## 3.3.0 - Morning Executive Intelligence

- Added deterministic morning executive brief model, engine, and store.
- Added `python -m constellation morning`.
- Added `python -m constellation morning --export`.
- Added `python -m constellation morning --overwrite`.
- Added morning brief outputs under `outputs/morning/`.
- Added summaries for intake, Google Drive sync, evidence, graph, findings, theses, and institutional intelligence state.
- Preserved report-only behavior with no provider calls, no LLM inference, no web retrieval, no autonomous decisions, and no automatic upstream workflow execution.

## 3.2.0 - Google Drive Connector

- Added optional Google Drive connector module for staging Drive files into `inbox/google-drive/incoming/`.
- Added disabled-by-default Google Drive source placeholders in `config/sources.yaml`.
- Added `config/google-drive.example.yaml` and ignored `config/secrets/` location for local-only credentials and tokens.
- Added optional `google-drive` dependency extra.
- Added `python -m constellation drive status`.
- Added `python -m constellation drive list`.
- Added `python -m constellation drive sync`.
- Added `python -m constellation drive sync --source SOURCE_ID`.
- Added `python -m constellation drive sync --dry-run`.
- Added Google Drive sync manifests under `outputs/google-drive/`.
- Preserved staging-only behavior with no Drive mutation, no Gmail integration, no provider execution, no automatic intake import, and no downstream workflow execution.

## 3.1.0 - Intake Pipeline

- Added operational intake scaffolding under `inbox/` for future Google Drive, Gmail, and manual intake workflows.
- Added placeholder source registry at `config/sources.yaml` without credentials, Drive IDs, or Gmail tokens.
- Added deterministic local intake pipeline from incoming inbox folders into dated `research_inputs/` folders.
- Added SHA-256 duplicate detection and overwrite refusal for conflicting destination filenames.
- Added intake manifest outputs under `outputs/intake/`.
- Added `python -m constellation intake scan`.
- Added `python -m constellation intake import`.
- Added `python -m constellation intake status`.
- Preserved local-only behavior with no Google Drive, Gmail, OAuth, external API, provider, or workflow integration.

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

## 1.1.0 - Crew Validation And Health Check

- Added deterministic crew validation for founding folders, required doctrine files, agent mappings, and orphan crew folders.
- Added `python -m constellation validate crew`.
- Added optional `--allow-orphans` validation mode for planned future roles.
- Added system health checks for constitution, config, agents, workflows, crew, providers, runtime directories, and provider invocation defaults.
- Added `python -m constellation health`.
- Added validation and health tests and documentation.

## 1.2.0 - OpenAI Provider Adapter

- Added `OpenAIProvider` behind the existing provider interface.
- Added OpenAI prompt-package request conversion with system prompt, task prompt, output contract, evidence requirements, uncertainty requirements, and context sections.
- Added disabled-by-default OpenAI config with `api_key_env`, timeout, output token limit, and config-only health mode.
- Added optional `openai` package extra.
- Added OpenAI provider health behavior for disabled, missing API key, missing SDK, configured, and optional API probe states.
- Preserved disabled-by-default provider execution and EchoProvider default routing.
- Added mocked OpenAI provider tests and documentation.

## 2.0.0 - Research Organization

- Added institutional research workflow under `workflows/research/institutional-research.yaml`.
- Added `research_inputs/` for markdown and text source documents.
- Added `python -m constellation research run PATH_TO_MD_OR_TXT`.
- Added research source ingestion into Working Memory before workflow execution.
- Added research artifact support fields for key findings, contradictions, open questions, and implications.
- Added `python -m constellation research export RUN_ID`.
- Added markdown report export under `outputs/research/`.
- Preserved disabled-by-default provider execution and human approval gates.
- Added Research Organization tests and documentation.

## 2.1.0 - PKOS Knowledge Organization

- Added PKOS ingestion workflow under `workflows/pkos/pkos-ingestion.yaml`.
- Added `pkos_inputs/` for markdown and text source documents.
- Added `python -m constellation pkos ingest PATH_TO_MD_OR_TXT`.
- Added PKOS source ingestion into Working Memory before workflow execution.
- Extended artifacts with `proposed_files` and `knowledge_actions`.
- Added `python -m constellation pkos package RUN_ID`.
- Added PKOS proposal package export under `outputs/pkos/RUN_ID/`.
- Added overwrite protection with optional `--overwrite`.
- Preserved disabled-by-default provider execution and human approval gates.
- Added PKOS Knowledge Organization tests and documentation.

## 2.2.0 - Evidence Engine

- Added deterministic `EvidenceItem` model.
- Added file-based evidence store under `memory/evidence/`.
- Added evidence save, list, show, query, and markdown export support.
- Added `python -m constellation evidence list`.
- Added `python -m constellation evidence show EVIDENCE_ID`.
- Added `python -m constellation evidence export RUN_ID`.
- Integrated evidence generation into Research and PKOS workflow ingestion before execution.
- Updated provider-backed artifacts to reference evidence IDs in `evidence_used`.
- Added evidence reports alongside Research exports and PKOS packages.
- Preserved disabled-by-default provider execution and deterministic tests.

## 2.3.0 - Knowledge Graph

- Added deterministic `GraphNode`, `GraphEdge`, and `KnowledgeGraph` models.
- Added file-based graph persistence under `memory/graph/graph.json`.
- Added deterministic graph builder from workflow runs, evidence records, source files, and artifacts.
- Added conservative topic, concept, theme, risk, assumption, and recommendation extraction from explicit source text.
- Added `python -m constellation graph build RUN_ID`.
- Added `python -m constellation graph nodes`.
- Added `python -m constellation graph edges`.
- Added `python -m constellation graph show NODE_OR_EDGE_ID`.
- Added `python -m constellation graph export`.
- Added graph health directory checks, tests, and documentation.

## 2.4.0 - Cross-Document Reasoning

- Added deterministic `CrossDocumentFinding` and `CrossDocumentAnalysis` models.
- Added cross-document analysis store under `outputs/analysis/`.
- Added repeated concept, theme, risk, assumption, and recommendation detection.
- Added source cluster detection.
- Added explicit-marker-only possible contradiction detection.
- Added missing evidence and confidence signal findings.
- Added `python -m constellation graph analyze`.
- Added `python -m constellation graph findings`.
- Added `python -m constellation graph findings show FINDING_ID`.
- Added `python -m constellation graph findings export`.
- Preserved opt-in graph analysis and disabled-by-default provider execution.

## 2.5.0 - Thesis Engine

- Added deterministic `Thesis` model and Thesis Engine.
- Added thesis generation from cross-document findings without provider calls.
- Added thesis store under `outputs/theses/`.
- Added overwrite protection for thesis generation.
- Added `python -m constellation thesis generate`.
- Added `python -m constellation thesis list`.
- Added `python -m constellation thesis show THESIS_ID`.
- Added `python -m constellation thesis export`.
- Added documentation for the Evidence, Knowledge Graph, Cross-Document, and Thesis relationship.
- Preserved proposed-by-default thesis status and human authority over acceptance.

## 3.0.0 - Institutional Intelligence Platform

- Added deterministic `IntelligenceBrief` model and Intelligence Engine.
- Added executive synthesis from theses, cross-document analysis, graph records, and evidence records.
- Added intelligence store under `outputs/intelligence/`.
- Added overwrite protection for intelligence brief generation.
- Added `python -m constellation intelligence generate`.
- Added `python -m constellation intelligence show`.
- Added `python -m constellation intelligence export`.
- Added Markdown executive intelligence report export.
- Preserved disabled-by-default provider execution and proposed-by-default brief status.
