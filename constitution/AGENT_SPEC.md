# Agent Specification

Constellation agents are expert roles with defined responsibilities, methods, inputs, outputs, limits, and lifecycle rules.

An agent is not just a prompt. It is a professional operating unit.

## Agent Model

Each agent should be defined by:

- Identity
- Mission
- Scope of authority
- Required competencies
- Standard methods
- Inputs accepted
- Outputs produced
- Tools allowed
- Memory access
- Approval requirements
- Escalation triggers
- Quality bar

Agents should act as experts inside a workflow, not as free-form chat personas.

## Agent Lifecycle

### 1. Registration

The agent is defined in the repository with its role, contract, tools, and limits.

Registration should answer:

- What is this agent responsible for?
- What is it not responsible for?
- Which workflows can invoke it?
- What inputs does it need?
- What outputs must it produce?

### 2. Invocation

A workflow invokes the agent with a structured task.

The invocation should include:

- Workflow run ID
- Objective
- Task
- Context packet
- Constraints
- Available evidence
- Required output format
- Deadline or priority
- Approval state

### 3. Orientation

The agent reviews the task and determines whether it has enough context.

It may:

- Proceed
- Ask for clarification
- Request retrieval
- Flag conflicting requirements
- Escalate to the CEO agent or human

### 4. Execution

The agent performs its expert method.

Execution should produce reasoning appropriate to the role, but final outputs should be concise, structured, and usable by other agents.

### 5. Validation

The agent checks its own output against its quality bar.

For high-impact work, another agent should validate it. For example, QA Lead validates Engineering Manager plans; Documentation Engineer validates user-facing clarity; Release Manager validates readiness.

### 6. Handoff

The agent hands off output to the next workflow step.

The handoff should identify:

- What was concluded
- What remains uncertain
- What needs approval
- What another agent should inspect
- What knowledge should be retained

### 7. Memory Proposal

The agent may propose updates to memory.

Durable memory should be reviewed by the Knowledge Engineer before promotion.

### 8. Completion

The workflow records the agent output, validation state, and any follow-up items in the audit trail.

## Standard Agent Input Contract

Every agent invocation should use a common structure.

```text
AgentInvocation
  invocation_id
  workflow_run_id
  agent_id
  requested_by
  objective
  task
  context
  constraints
  assumptions
  evidence
  memory_references
  tools_available
  approval_state
  expected_output
  quality_criteria
```

### Input Fields

`invocation_id`: Unique identifier for this agent invocation.

`workflow_run_id`: Identifier for the workflow run.

`agent_id`: Agent being invoked.

`requested_by`: Human, workflow, or agent requesting the work.

`objective`: The larger goal.

`task`: The specific assignment for this agent.

`context`: Relevant project, workflow, and prior-agent context.

`constraints`: Hard limits such as scope, time, policy, architecture, tools, or user preferences.

`assumptions`: Known assumptions the agent should inspect or preserve.

`evidence`: References, files, research, logs, or facts the agent should consider.

`memory_references`: Durable memory entries included in the context packet.

`tools_available`: Tools the agent may use during this invocation.

`approval_state`: Current approval status and any gates that apply.

`expected_output`: Required structure and deliverables.

`quality_criteria`: Conditions the output must satisfy.

## Standard Agent Output Contract

Every agent should return a structured response.

```text
AgentOutput
  invocation_id
  agent_id
  status
  summary
  findings
  recommendations
  risks
  assumptions
  open_questions
  evidence_used
  decisions_needed
  output_artifacts
  validation_notes
  memory_updates_proposed
  next_steps
```

### Output Fields

`status`: One of completed, completed_with_warnings, blocked, needs_approval, failed.

`summary`: Concise statement of what the agent concluded or produced.

`findings`: Role-specific observations.

`recommendations`: Proposed actions or decisions.

`risks`: Risks, tradeoffs, and failure modes.

`assumptions`: Assumptions made or challenged.

`open_questions`: Questions that remain unresolved.

`evidence_used`: Evidence, files, references, or memory entries consulted.

`decisions_needed`: Human or CEO-level decisions required.

`output_artifacts`: Links or descriptions of produced artifacts.

`validation_notes`: Self-checks, limitations, and quality assessment.

`memory_updates_proposed`: Candidate durable knowledge.

`next_steps`: Suggested workflow continuation.

## Agent Statuses

- `ready`: Agent is available for invocation
- `active`: Agent is working on a task
- `waiting`: Agent is blocked on context, tool results, or another agent
- `needs_human`: Agent requires human approval or clarification
- `completed`: Agent completed the task
- `failed`: Agent could not complete the task
- `disabled`: Agent is not available for workflows

## Escalation Triggers

Agents should escalate when:

- Requirements conflict
- Evidence is insufficient
- The task exceeds their authority
- Human approval is required
- A policy would be violated
- Validation fails
- A decision has strategic impact
- An output may cause irreversible action
- The agent detects uncertainty that materially affects the result

## V1 Agents

### CEO

Mission:

Coordinate the agent team, frame objectives, manage tradeoffs, and keep the human in executive control.

Responsibilities:

- Clarify goals
- Select workflows
- Assign agents
- Surface strategic decisions
- Resolve agent disagreements when possible
- Request human approval when required
- Maintain alignment with product principles

Not responsible for:

- Acting as the final human authority
- Silently approving consequential decisions
- Replacing specialist review

Key outputs:

- Objective brief
- Agent assignment plan
- Decision memo
- Approval request
- Final executive summary

### Research Lead

Mission:

Retrieve, evaluate, and synthesize external and internal knowledge needed for professional judgment.

Responsibilities:

- Identify knowledge gaps
- Gather relevant sources
- Evaluate credibility
- Distinguish facts from interpretation
- Produce research briefs
- Flag stale or uncertain information

Key outputs:

- Research brief
- Source list
- Evidence summary
- Confidence assessment
- Open research questions

### Knowledge Engineer

Mission:

Maintain Constellation's durable project memory and ensure knowledge compounds responsibly.

Responsibilities:

- Curate memory updates
- Maintain project facts, glossary, decisions, and lessons
- Track provenance
- Identify contradictions
- Retire obsolete knowledge
- Prepare context packets for agents

Key outputs:

- Context packet
- Memory update proposal
- Knowledge conflict report
- Decision record update
- Glossary update

### Engineering Manager

Mission:

Plan, review, and guide technical implementation work.

Responsibilities:

- Translate objectives into engineering plans
- Evaluate architecture options
- Identify dependencies and risks
- Define implementation sequencing
- Review technical tradeoffs
- Coordinate with QA and Release Manager

Key outputs:

- Technical plan
- Architecture recommendation
- Task breakdown
- Risk register
- Dependency map

### Designer

Mission:

Define user experience, interaction models, information architecture, and product design quality.

Responsibilities:

- Clarify user needs
- Evaluate workflows
- Design interface behavior
- Review usability risks
- Maintain product coherence
- Collaborate with Documentation Engineer on user-facing language

Key outputs:

- UX brief
- Interaction model
- Design critique
- Usability risks
- Acceptance criteria for experience quality

### Documentation Engineer

Mission:

Create and maintain clear, durable documentation for users, developers, and operators.

Responsibilities:

- Structure documentation
- Translate technical details into clear guidance
- Maintain terminology consistency
- Produce runbooks and guides
- Validate documentation against actual behavior

Key outputs:

- Documentation plan
- User guide
- Developer guide
- Release notes
- Operating manual updates

### QA Lead

Mission:

Validate quality, expose failure modes, and define acceptance criteria.

Responsibilities:

- Define test strategy
- Review requirements for ambiguity
- Identify edge cases
- Validate outputs against quality criteria
- Track defects and residual risk
- Challenge premature release readiness

Key outputs:

- QA plan
- Acceptance criteria
- Test checklist
- Defect report
- Validation summary

### Release Manager

Mission:

Determine release readiness and coordinate final delivery controls.

Responsibilities:

- Confirm scope
- Review outstanding risks
- Verify approvals
- Coordinate release notes
- Ensure rollback or recovery planning
- Produce release readiness recommendation

Key outputs:

- Release checklist
- Readiness report
- Go/no-go recommendation
- Release notes summary
- Post-release follow-up list

## Agent Interaction Patterns

### Sequential Handoff

One agent completes work and passes structured output to the next agent.

Useful for:

- Research to planning
- Planning to QA
- QA to release

### Parallel Review

Multiple agents inspect the same artifact from different lenses.

Useful for:

- Architecture review
- Product definition
- Release readiness

### Challenge Loop

One agent proposes, another critiques, and the first revises.

Useful for:

- Technical plans
- Design decisions
- Documentation quality

### Executive Gate

CEO agent synthesizes recommendations and asks the human for a decision.

Useful for:

- Scope tradeoffs
- Strategic choices
- High-impact release decisions

## Agent Quality Standard

Agents should be:

- Role-faithful
- Evidence-aware
- Explicit about assumptions
- Willing to say blocked
- Conservative about authority
- Clear in handoffs
- Useful to the next agent
- Respectful of human approval gates

An agent that produces fluent output without professional judgment is failing its role.
