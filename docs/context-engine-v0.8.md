# Context Engine v0.8

Kernel v0.8 adds the Context Engine.

The Context Engine assembles a read-only execution context for a workflow run. It does not call providers, generate prompts, or change workflow execution behavior.

## Purpose

The Context Engine gives future runtime components one deterministic place to retrieve:

- Workflow run state
- Current step
- Agent and crew role
- Crew doctrine
- Workflow definition
- Previous messages
- Recent events
- Working memory
- Project memory
- Provider routing configuration
- Approval state

## Crew Loader

Crew doctrine is loaded from:

```text
crew/<role>/
  profile.md
  responsibilities.md
  authority.md
  communication.md
  methodologies.md
  memory.md
  prompts.md
```

Agent IDs map to crew roles by replacing underscores with hyphens.

Example:

```text
research_lead -> research-lead
documentation_engineer -> documentation-engineer
```

## Execution Context

The assembled context includes:

- `workflow_run_id`
- `workflow_id`
- `current_step`
- `agent_id`
- `crew_role`
- `crew_doctrine`
- `workflow_definition`
- `previous_messages`
- `recent_events`
- `working_memory`
- `project_memory`
- `provider_routing_config`
- `approval_state`

## CLI

Show assembled context for a workflow run:

```bash
python -m constellation context show run_225a2ecf7cd5477e966c7bf6965eec4c
```

The command prints deterministic JSON.

## Behavior Notes

- Paused runs show the current step as `approval:<approval_id>`.
- Completed runs show the current step as `Complete`.
- Active runs include the current agent ID, crew role, and crew doctrine.
- Provider behavior is unchanged.
- Prompt generation is not implemented in v0.8.

## Future Use

The next natural step is a crew-aware prompt assembly layer that consumes `ExecutionContext` while preserving the distinction between professional doctrine and implementation prompts.
