# Changelog

All notable changes to Constellation will be recorded here.

## 7.2.1 - Canonical Operations Hardening

- Added Canonical Operations as the Real Estate operator visibility layer.
- Synchronized canonical status, migration plan, dashboard, operations report, and review queue counts around one deterministic migration state.
- Added explicit migration categories: `safe_merge`, `preserve_alias`, `blocked_by_conflict`, `ambiguous`, `orphan`, and `already_migrated`.
- Added review queue and operations outputs under `outputs/real-estate/canonical/`.
- Added `python -m constellation real-estate canonical review`, filtered review views, `operations`, `report`, and improved `conflicts`.
- Updated the Executive Dashboard to report canonical migration, review, blocked, and ambiguous counts from Canonical Operations.
- Preserved deterministic local-only behavior with no providers, OpenAI, LLM inference, embeddings, semantic or fuzzy matching, web retrieval, Gmail, calendar integration, valuation opinions, comparable selection, adjustments, permit interpretation, automatic live migration, or USPAP conclusions.

## 7.2.0 - Canonical Assignment Model

- Added the Canonical Assignment Model as the Real Estate persistence and operational layer.
- Added canonical assignments, aliases, sources, resolution records, snapshots, deltas, and non-destructive migration support.
- Added `python -m constellation real-estate canonical ...` commands for status, assignments, aliases, resolution, migration planning, migration apply, and export.
- Updated Real Estate intake so new artifacts resolve to canonical assignments before writing assignment directories.
- Updated assignment commands to resolve canonical IDs, order IDs, loan numbers, source-generated aliases, address aliases, and previous IDs when unambiguous.
- Updated assignment listing and dashboard summaries to count canonical assignments rather than alias directories.
- Added normalization for HTML-noise addresses, equivalent date formats, unit markers, ZIP/ZIP+4 compatibility, and source paths.
- Suppressed normalized-equivalent assignment conflicts while preserving true conflicts and original provenance.
- Preserved deterministic local-only behavior with no providers, OpenAI, LLM inference, embeddings, semantic similarity, fuzzy matching, web retrieval, Gmail, calendar integration, valuation opinions, comparable selection, adjustments, permit interpretation, destructive migration, or USPAP conclusions.

## 7.1.2 - Assignment Identity Resolution

- Refined Real Estate Assignment Consolidation identity resolution.
- Added HTML entity cleanup, `&nbsp;` handling, and unit-aware address normalization.
- Added source companion pairing for exact JSON/Markdown source stems.
- Added assignment alias preservation and identity-source reporting.
- Added unassigned artifact outputs and identity resolution reports.
- Suppressed false assignment ID conflicts from source-generated aliases while preserving true explicit ID conflicts.
- Updated dashboard and CLI summaries with canonical assignment, alias, source companion, unassigned artifact, and true identity conflict counts.
- Preserved deterministic local-only behavior with no providers, OpenAI, LLM inference, embeddings, semantic similarity, web retrieval, Gmail, calendar integration, valuation opinions, comparable selection, adjustments, or USPAP conclusions.

## 7.1.1 - Real Estate Assignment Consolidation

- Added deterministic Assignment Consolidation for Real Estate Intelligence.
- Added assignment clusters, relationships, conflicts, history, and delta outputs under `outputs/real-estate/consolidation/`.
- Added `python -m constellation real-estate consolidation` with status, clusters, conflicts, relationships, and export commands.
- Integrated consolidated assignment, artifact, knowledge pack, reviewer note, and conflict counts into the Executive Dashboard.
- Extended Assignment Briefs with consolidation artifacts, relationships, and conflicts when consolidation data exists.
- Preserved deterministic local-only behavior with no providers, OpenAI, LLM inference, embeddings, semantic similarity, web retrieval, Gmail, calendar integration, valuation opinions, comparable selection, adjustments, or USPAP conclusions.

## 7.1.0 - Real Estate Assignment Auto-Ingestion

- Added deterministic Real Estate Assignment Auto-Ingestion for structured local intake files.
- Added `python -m constellation real-estate intake ...` commands for status, scan, import, history, and record inspection.
- Added optional local intake configuration with gitignored `config/real-estate-intake.yaml` and `config/real-estate-intake.local.yaml`.
- Added reference and copy source modes with checksum and source-path provenance.
- Added deterministic assignment ID normalization, alias-based field mapping, duplicate detection, non-overwriting merge behavior, and conflict fact creation.
- Automatic intake import now creates/updates private assignment case files, builds Assignment Intelligence, writes intake manifests, and refreshes the dashboard.
- Preserved no-provider, no-OpenAI, no-LLM, no-embedding, no-web, no-Gmail, no-calendar, no-autonomous-valuation behavior.

## 7.0.1 - Assignment Template and Empty-Fact Handling

- Fixed Real Estate Assignment Intelligence so empty structured fact values are omitted instead of becoming populated facts.
- Preserved valid zero and boolean false fact values.
- Kept `unit` as structured fact provenance metadata and prevented it from being substituted as the fact value.
- Updated the generated assignment template and public example to use `facts: []` instead of active empty placeholder facts.
- Preserved deterministic local-only Real Estate behavior with no providers, OpenAI, LLM inference, embeddings, web retrieval, Gmail, calendar integration, or valuation conclusions.

## 7.0.0 - Real Estate Assignment Intelligence MVP

- Added deterministic Real Estate Assignment Intelligence as the first Real Estate Intelligence capability.
- Added private local assignment conventions under gitignored `real-estate/assignments/`.
- Added `python -m constellation real-estate assignment ...` commands for templates, builds, status, source manifests, missing information, risks, timelines, and exports.
- Added Assignment Intelligence outputs under `outputs/real-estate/assignments/`.
- Integrated Real Estate Assignment Intelligence summary fields into the Executive Dashboard.
- Added public sanitized examples and documentation for the v7.0 Assignment Intelligence MVP.
- Preserved no-provider, no-OpenAI, no-LLM, no-embedding, no-web, no-Gmail, no-calendar, no-autonomous-execution behavior.
- Preserved professional valuation boundaries: no generated value opinions, comparable selections, adjustments, USPAP opinions, or appraisal conclusions.

## 6.1.1 - Executive Brief Refinement and Automated Daily Review Launch

- Refined the AI & Markets Executive Morning Brief into a concise top-five CIO-style daily brief.
- Moved supporting research agenda detail, IDs, source paths, unavailable artifacts, and limitations into appendix/provenance sections.
- Added deterministic agenda, catalyst, and risk deduplication and cleaner structured catalyst/risk titles.
- Calibrated configured watchlist items without current evidence to medium priority unless another high-priority rule applies.
- Updated the Windows Morning launcher to open the Morning Brief and Performance Learning Loop in Visual Studio Code after successful workflow runs.
- Preserved deterministic local-only behavior with no providers, OpenAI, LLM inference, embeddings, web retrieval, Gmail, calendar integration, trading execution, financial advice, or autonomous investment decisions.

## 6.1.0 - Thesis Accuracy

- Added deterministic Thesis Accuracy as a Performance Intelligence layer.
- Added `outputs/performance/thesis-accuracy.json`, `thesis-accuracy.md`, `thesis-scoreboard.md`, `thesis-history.json`, and `thesis-delta.json`.
- Added `python -m constellation performance thesis` with history, delta, scoreboard, and export options.
- Integrated Thesis Accuracy into the Executive Dashboard and the built-in Morning workflow.
- Updated Morning workflow to complete 19 deterministic steps with Thesis Accuracy after Performance Intelligence.
- Preserved no-provider, no-OpenAI, no-LLM, no-embedding, no-web, no-Gmail, no-calendar, no-trading, no-financial-advice behavior.

## 6.0.1 - Connector Failure Resilience

- Added deterministic connector failure classification for Google Drive auth failures.
- Classified Google Drive OAuth expiration and revoked-token errors as `needs_reauth`.
- Hardened Morning workflow so Google Drive re-authentication failures are recorded as degraded connector warnings while downstream deterministic local outputs continue where possible.
- Hardened Daily Pipeline so Google Drive re-authentication failures produce connector warnings instead of failing the entire daily package when local artifacts can still be used.
- Added Connector Warnings sections to workflow and daily reports.
- Added connector warning summary fields to Executive Dashboard.
- Added AI & Markets Executive Morning Brief limitation text when latest daily artifacts report Google Drive re-authentication needs.
- Preserved no-provider, no-web, no-Gmail, no-calendar, no-trading, no-financial-advice behavior.

## 6.0.0 - Performance Intelligence MVP

- Added deterministic Performance Intelligence as the first v6 feedback layer.
- Added Decision Outcome Tracking, Performance Signals, Process Lessons, Learning Loop snapshots, history, and delta outputs under `outputs/performance/`.
- Added `python -m constellation performance` with review, decisions, signals, lessons, export, history, and delta commands.
- Integrated Performance Intelligence into the Executive Dashboard and Morning workflow.
- Updated Morning workflow to include an explicit `Performance Intelligence` final step.
- Preserved deterministic learning-only behavior with no financial advice, client performance reporting, trading system behavior, provider calls, OpenAI, LLM inference, embeddings, semantic search, web retrieval, Gmail, calendar integration, autonomous scheduling, or autonomous decisions.

## 5.5.0 - AI & Markets Executive Morning Brief

- Added deterministic AI & Markets Executive Morning Brief.
- Added executive brief, research agenda, brief history, and brief delta outputs under `outputs/ai-markets/briefings/`.
- Added research agenda generation from decisions, catalysts, portfolio reviews, lifecycle status, open questions, and missing artifacts.
- Added `python -m constellation ai-markets brief` with agenda, history, delta, and export flags.
- Integrated Executive Morning Brief into AI & Markets reports, Executive Dashboard, and Morning workflow.
- Preserved deterministic briefing-only behavior with no market prediction, trading recommendations, financial advice, providers, OpenAI, LLM inference, embeddings, semantic search, web retrieval, Gmail, calendar integration, or autonomous decisions.

## 5.4.0 - AI & Markets Decision Journal

- Added deterministic AI & Markets Decision Journal.
- Added private local journal conventions under gitignored `journal/ai-markets/`.
- Added example decision journal config and example Markdown entry.
- Added decision entry parsing, exact artifact linking, review queue, outcome tracking, history, and delta outputs.
- Added `python -m constellation ai-markets decisions` with entries, queue, timeline, outcomes, history, delta, export, and template creation flags.
- Integrated Decision Journal into AI & Markets reports, Executive Dashboard, and Morning workflow.
- Preserved research-memory-only behavior with no trading recommendations, financial advice, providers, OpenAI, LLM inference, embeddings, semantic search, web retrieval, Gmail, calendar integration, or autonomous decisions.

## 5.3.0 - AI & Markets Catalyst Monitoring

- Added deterministic AI & Markets Catalyst Monitoring.
- Added catalyst category, time horizon, priority, status, history, delta, and transition tracking.
- Added catalyst monitor, priorities, history, delta, transitions, and calendar outputs under `outputs/ai-markets/catalysts/`.
- Added `python -m constellation ai-markets catalysts` with monitor, priorities, calendar, history, delta, transitions, and export flags.
- Integrated Catalyst Monitoring into AI & Markets reports, watchlists, Executive Dashboard, and Morning workflow.
- Preserved research-only behavior with no trading recommendations, financial advice, providers, OpenAI, LLM inference, embeddings, semantic search, web retrieval, Gmail, calendar integration, or autonomous decisions.

## 5.2.0 - AI & Markets Portfolio Intelligence

- Added deterministic AI & Markets Portfolio Intelligence.
- Added optional local portfolio/watchlist config convention with `config/portfolio.example.yaml`.
- Added gitignore protection for local/private portfolio config files.
- Added portfolio exposures, risks, watchlist, questions, history, and delta outputs under `outputs/ai-markets/portfolio/`.
- Added `python -m constellation ai-markets portfolio` and inspection flags for exposures, risks, watchlist, questions, history, and delta.
- Integrated Portfolio Intelligence into AI & Markets reports, watchlists, Executive Dashboard, and Morning workflow.
- Preserved research-only behavior with no trading recommendations, financial advice, providers, OpenAI, LLM inference, embeddings, semantic search, web retrieval, Gmail, or autonomous decisions.

## 5.1.0 - AI & Markets Theme Lifecycle

- Added deterministic AI & Markets theme lifecycle tracking.
- Added lifecycle statuses: emerging, active, strengthening, high_conviction, weakening, contradicted, and archived.
- Added lifecycle snapshots, history, transitions, and timeline outputs under `outputs/ai-markets/`.
- Added `python -m constellation ai-markets lifecycle`.
- Added `python -m constellation ai-markets lifecycle --export`.
- Added `python -m constellation ai-markets lifecycle --history`.
- Added `python -m constellation ai-markets lifecycle --transitions`.
- Added `python -m constellation ai-markets theme THEME_ID`.
- Updated AI & Markets reports with a Theme Lifecycle section.
- Integrated lifecycle counts into the Executive Dashboard and Workflow Automation report.
- Preserved deterministic local-only behavior with no providers, OpenAI, LLM inference, embeddings, semantic search, web retrieval, Gmail, trading execution, financial advice, scheduling, or autonomous decisions.

## 5.0.1 - AI & Markets Signal Refinement

- Added deterministic open-question normalization and deduplication.
- Added prioritized executive questions with `executive-questions.json` and `executive-questions.md`.
- Updated `python -m constellation ai-markets questions` to show total, deduplicated, and executive question counts, with optional `--executive` output.
- Expanded deterministic ticker, asset, and company-name matching for AI & Markets entities.
- Updated the AI & Markets report to show top executive questions and link to full question archives.
- Added AI & Markets executive question and high-confidence entity fields to the Executive Dashboard.
- Added AI & Markets question counts to Workflow Automation reports.
- Preserved deterministic local-only behavior with no providers, OpenAI, LLM inference, embeddings, semantic search, web retrieval, Gmail, trading execution, financial advice, scheduling, or autonomous decisions.

## 5.0.0 - AI & Markets Intelligence MVP

- Added deterministic AI & Markets Intelligence domain layer.
- Added fixed AI & Markets theme taxonomy and ticker/entity detection.
- Added `python -m constellation ai-markets build`.
- Added `python -m constellation ai-markets status`.
- Added `python -m constellation ai-markets themes`.
- Added `python -m constellation ai-markets entities`.
- Added `python -m constellation ai-markets risks`.
- Added `python -m constellation ai-markets questions`.
- Added `python -m constellation ai-markets report`.
- Added `python -m constellation ai-markets export`.
- Added AI & Markets outputs under `outputs/ai-markets/`.
- Integrated AI & Markets Summary into Executive Dashboard.
- Added AI & Markets generation to Morning workflow after Institutional Research Reports.
- Preserved deterministic local-only behavior with no providers, OpenAI, LLM inference, embeddings, semantic search, web retrieval, Gmail, trading execution, financial advice, scheduling, or autonomous decisions.

## 4.2.0 - Institutional Research Reports

- Added deterministic Institutional Research Report engine.
- Added `python -m constellation report latest`.
- Added `python -m constellation report latest --export`.
- Added `python -m constellation report status`.
- Added `python -m constellation report history`.
- Added `python -m constellation report show REPORT_ID`.
- Added report outputs under `outputs/reports/`.
- Added report sections for executive summary, changes, evidence, thesis intelligence, evolution, source activity, risks, open questions, actions, references, source documents, limitations, and provenance.
- Integrated report summary into Executive Dashboard.
- Added Morning workflow report generation after dashboard refresh.
- Preserved deterministic local-only behavior with no providers, OpenAI, LLM inference, embeddings, semantic search, web retrieval, Gmail, scheduling, or autonomous decisions.

## 4.1.0 - Knowledge Evolution Engine

- Added deterministic Knowledge Evolution Engine.
- Added `python -m constellation evolution`.
- Added `python -m constellation evolution status`.
- Added `python -m constellation evolution history`.
- Added `python -m constellation evolution export`.
- Added `python -m constellation evolution compare SNAPSHOT_A SNAPSHOT_B`.
- Added evolution outputs under `outputs/evolution/`.
- Added evidence gained/removed, graph growth, thesis confidence/status changes, source activity trends, research volume trends, workflow execution trends, and longitudinal health score.
- Integrated Knowledge Evolution into Daily Pipeline after Institutional Memory.
- Added Knowledge Evolution Summary to Executive Dashboard.
- Preserved deterministic local-only behavior with no providers, no OpenAI, no LLM inference, no embeddings, no semantic search, no Gmail, no web retrieval, and no autonomous execution.

## 4.0.1 - Research Auto-Processing For Morning Workflow

- Updated the built-in `Morning` workflow to import intake files and auto-process newly imported local research inputs.
- Added deterministic research input detection from the latest intake manifest.
- Added research processing metadata to workflow outputs and reports.
- Added per-file research workflow execution through the existing Research Organization.
- Added per-run Knowledge Graph builds for generated research workflow run IDs.
- Added deterministic refresh steps for cross-document analysis, thesis generation, Thesis Intelligence, Evidence Graph, Daily Pipeline, and Executive Dashboard.
- Added duplicate protection through `outputs/workflows/research-processing.json`.
- Preserved approval behavior, provider-disabled defaults, explicit workflow invocation, and no external services.

## 4.0.0 - Workflow Automation Engine

- Added deterministic Workflow Automation Engine.
- Added built-in workflows: `Morning`, `Research Refresh`, and `Executive Snapshot`.
- Added `python -m constellation workflow list`.
- Added `python -m constellation workflow run NAME`.
- Added `python -m constellation workflow history`.
- Added `python -m constellation workflow show NAME`.
- Added `python -m constellation workflow export`.
- Added workflow definitions, latest run, history, and report outputs under `outputs/workflows/`.
- Integrated latest workflow status, duration, completed steps, and failed steps into Executive Dashboard.
- Preserved explicit invocation only with no providers, no OpenAI, no Gmail, no web retrieval, no embeddings, no semantic search, no scheduling, and no autonomous execution.

## 3.9.0 - Source Monitoring

- Added deterministic Source Monitoring subsystem.
- Added `python -m constellation monitor`.
- Added `python -m constellation monitor --overwrite`.
- Added `python -m constellation monitor status`.
- Added `python -m constellation monitor history`.
- Added `python -m constellation monitor export`.
- Added source monitor outputs under `outputs/source-monitor/`.
- Added source monitoring history and latest monitor snapshots.
- Integrated Source Monitoring as the first Daily Pipeline stage.
- Added Source Monitoring Summary to Executive Dashboard.
- Preserved read-only deterministic behavior with no provider calls, no OpenAI calls, no LLM inference, no embeddings, no semantic search, no web retrieval, no Gmail, no scheduling, and no autonomous workflow execution.

## 3.8.0 - Executive Dashboard

- Added deterministic Executive Dashboard presentation layer.
- Added `python -m constellation dashboard`.
- Added `python -m constellation dashboard --export`.
- Added `python -m constellation dashboard --overwrite`.
- Added `python -m constellation dashboard status`.
- Added dashboard outputs under `outputs/dashboard/`.
- Added dashboard sections for daily status, intake, Google Drive, evidence, Evidence Graph, Thesis Intelligence, Institutional Memory, Morning Brief, risks/gaps, recommended next actions, key output files, limitations, and provenance.
- Preserved read-only presentation behavior with no provider calls, no OpenAI calls, no LLM inference, no embeddings, no semantic similarity, no web retrieval, no Gmail, no workflow execution, and no autonomous decisions.

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
