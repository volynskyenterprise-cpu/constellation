# Constellation Crew

The Constellation Crew is the durable organizational layer above agent YAML definitions.

Agents are professionals, not chatbots. YAML files can register an agent with the kernel, but the crew files define the role's professional identity: mission, responsibilities, authority, communication style, methodology, memory obligations, and prompt templates.

## Purpose

The crew layer exists so Constellation can grow from prompt execution into an inspectable professional organization.

Runtime agents may eventually load these files, but the files are useful before automation because they define:

- What each role is accountable for
- What each role may decide
- What each role must escalate
- How roles challenge each other
- What evidence standards apply
- What memory each role should preserve
- How prompts should be derived from methodology

## Founding Crew

- [CEO](ceo/profile.md)
- [Research Lead](research-lead/profile.md)
- [Knowledge Engineer](knowledge-engineer/profile.md)
- [Engineering Manager](engineering-manager/profile.md)
- [Designer](designer/profile.md)
- [QA Lead](qa-lead/profile.md)
- [Documentation Engineer](documentation-engineer/profile.md)
- [Release Manager](release-manager/profile.md)

## Relationship To Existing Agents

The existing `agents/` YAML files remain the runtime registry layer.

The `crew/` directory is the professional doctrine layer. Future runtime work may connect crew documents to agent loading, prompt assembly, workflow planning, review checklists, and memory policy.

## Extension

Future crew members should be added only when they represent a durable professional responsibility.

Candidate future roles:

- Investment Strategist
- Market Analyst
- Appraisal Expert
- Real Estate Analyst
- CAIO Advisor
- Content Strategist

New roles must meet the [Hiring Standard](HIRING_STANDARD.md).
