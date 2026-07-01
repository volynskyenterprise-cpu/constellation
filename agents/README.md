# Agents

This folder contains Constellation agent definitions.

Agents are expert roles, not generic assistants. Each file defines one role's mission, authority, inputs, outputs, methods, and escalation triggers.

To add an agent:

1. Copy an existing agent YAML file.
2. Give it a stable `id`.
3. Define its mission, authority, methods, and outputs.
4. Add it to `../config/agents.yaml`.
5. Reference it from workflows as needed.

Agent definitions should stay model-agnostic. Provider preferences belong in configuration, not in the agent identity.
