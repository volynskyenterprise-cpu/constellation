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
