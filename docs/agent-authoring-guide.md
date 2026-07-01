# Agent Authoring Guide

Agents should represent durable professional responsibilities.

## Required Sections

Every agent file should define:

- `id`
- `name`
- `version`
- `status`
- `mission`
- `authority`
- `methods`
- `inputs`
- `outputs`
- `escalation_triggers`
- `quality_bar`

## Guidance

- Keep agents model-agnostic.
- Define what the agent cannot do.
- Make escalation triggers concrete.
- Prefer role methods over prompt style.
- Add new agents only when they add a distinct judgment lens.
