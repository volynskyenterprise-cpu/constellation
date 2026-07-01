# Workflow Authoring Guide

Workflows define how agents collaborate.

## Required Sections

Every workflow should define:

- `id`
- `name`
- `version`
- `purpose`
- `agents`
- `steps`
- `approval_gates`
- `validation`
- `memory_updates`

## Guidance

- Keep steps explicit and inspectable.
- Prefer small workflows over broad ambiguous ones.
- Reference agents by stable `id`.
- Add approval gates where authority matters.
- Define required artifacts before considering a workflow complete.
