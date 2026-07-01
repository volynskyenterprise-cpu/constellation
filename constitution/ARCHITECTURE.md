# Architecture

Constellation is a layered operating system for coordinating expert AI agents, workflows, knowledge, approvals, and audit trails.

The V1 implementation should run inside Codex and use the filesystem as its primary state layer. The architecture should remain portable to other execution environments and model providers.

## System Architecture

### Layers

Constellation should be organized into the following conceptual layers:

1. Human control layer
2. Workflow orchestration layer
3. Agent execution layer
4. Tool and model provider layer
5. Memory and knowledge layer
6. Logging and audit layer
7. Configuration and policy layer

### Human Control Layer

The human control layer is responsible for:

- Defining objectives
- Approving plans
- Resolving tradeoffs
- Granting permission for consequential actions
- Accepting final outputs
- Overriding or stopping workflows

In V1, this can be represented through explicit markdown approval gates and Codex user interactions.

### Workflow Orchestration Layer

The workflow orchestration layer coordinates:

- Which agents participate
- In what order agents act
- What each agent receives
- What each agent must return
- Where human approval is required
- How outputs are validated
- What knowledge should be retained

V1 workflows may be simple markdown or YAML definitions interpreted manually or semi-automatically by Codex.

### Agent Execution Layer

The agent execution layer runs individual expert agents according to the standard agent contract.

Each agent should have:

- Role definition
- Scope of authority
- Required inputs
- Expected outputs
- Methods and checklists
- Tool permissions
- Escalation rules
- Quality standards

Agents should be deterministic in structure, even when model responses are probabilistic.

### Tool And Model Provider Layer

The provider layer abstracts execution away from any one model vendor.

Providers may include:

- Codex execution
- OpenAI models
- Anthropic Claude
- Google Gemini
- Local models
- Search tools
- File tools
- Code execution tools
- Retrieval systems
- Design and document tools

Provider adapters should expose capabilities rather than vendor-specific assumptions.

Example capability categories:

- Reasoning
- Retrieval
- Code editing
- File inspection
- Document generation
- Image understanding
- Web search
- Test execution
- Structured extraction

### Memory And Knowledge Layer

The memory layer stores reusable project knowledge and workflow outputs.

It should distinguish between:

- Raw artifacts
- Curated knowledge
- Decisions
- Assumptions
- Project facts
- External references
- Validation results
- Agent notes

V1 can be file-based. Later versions may add vector indexes, databases, graph stores, and knowledge provenance systems.

### Logging And Audit Layer

The audit layer records what happened.

It should capture:

- Workflow runs
- Agent invocations
- Inputs and outputs
- Approval gates
- Human decisions
- Tool calls
- Evidence references
- Errors and retries
- Final deliverables

The audit trail should support reconstruction of professional reasoning.

### Configuration And Policy Layer

Configuration defines:

- Available agents
- Workflow templates
- Model/provider routing
- Tool permissions
- Approval policies
- Logging policies
- Memory retention policies
- Environment-specific settings

Policies define what the system may do without human approval.

## Recommended Repository Structure

```text
constellation/
  README.md
  VISION.md
  ARCHITECTURE.md
  AGENT_SPEC.md
  ROADMAP.md

  agents/
    ceo.md
    research-lead.md
    knowledge-engineer.md
    engineering-manager.md
    designer.md
    documentation-engineer.md
    qa-lead.md
    release-manager.md

  workflows/
    README.md
    product-definition.md
    architecture-review.md
    implementation-planning.md
    qa-review.md
    release-readiness.md

  memory/
    README.md
    project/
      facts.md
      glossary.md
      constraints.md
      decisions.md
    knowledge/
      patterns.md
      references.md
      lessons-learned.md
    runs/
      .gitkeep

  approvals/
    README.md
    pending/
    accepted/
    rejected/

  logs/
    README.md
    runs/
    agents/
    decisions/

  config/
    constellation.md
    agents.md
    workflows.md
    providers.md
    policies.md

  docs/
    operating-manual.md
    agent-authoring-guide.md
    workflow-authoring-guide.md
    memory-curation-guide.md
```

This structure is intentionally document-first. Implementation directories should be introduced only when the runtime begins.

## Workflow Engine Design

The workflow engine coordinates professional methods.

### Workflow Definition

Each workflow should define:

- Name
- Purpose
- Trigger conditions
- Required human input
- Participating agents
- Ordered steps
- Parallelizable steps
- Required artifacts
- Approval gates
- Validation criteria
- Memory updates
- Completion criteria

### Workflow Run State

Each run should maintain:

- Run ID
- Objective
- Initiating human
- Start time
- Current status
- Active step
- Agent assignments
- Inputs
- Outputs
- Decisions
- Approvals
- Errors
- Final artifacts

### Step Types

Supported step types should include:

- Frame objective
- Retrieve context
- Generate plan
- Critique plan
- Produce artifact
- Validate artifact
- Request human approval
- Revise artifact
- Record knowledge
- Prepare release

### Execution Modes

V1 should support:

- Manual execution: Codex follows workflow files and produces artifacts
- Guided execution: Codex uses structured checklists and logs state
- Semi-automated execution: later V1 can invoke agent specs and workflow steps systematically

Future versions may support a service-based engine with queues, state machines, retries, and provider routing.

### Workflow Control Rules

Workflows should be explicit about:

- What can proceed without approval
- What must pause for approval
- What evidence is required
- What validation must pass
- What gets stored in memory
- What counts as completion

## Memory And Knowledge Architecture

Constellation should treat memory as a professional asset.

### Memory Types

Project memory:

- Current goals
- Product decisions
- Constraints
- Architecture choices
- Glossary
- Stakeholders
- Open questions

Knowledge memory:

- Reusable methods
- Domain references
- Patterns
- Lessons learned
- Validated approaches

Run memory:

- Workflow transcript summaries
- Agent outputs
- Approval decisions
- Validation results
- Final artifacts

### Memory Lifecycle

1. Capture raw output during workflows
2. Review relevance and quality
3. Curate durable knowledge
4. Store with provenance
5. Retrieve during future work
6. Update or retire obsolete knowledge

The Knowledge Engineer owns curation. Other agents may propose memory updates, but durable knowledge should be reviewed before being promoted.

### Retrieval Principles

Retrieval should be:

- Purpose-driven
- Scoped to the task
- Provenance-aware
- Recent when needed
- Conservative when facts may be stale
- Explicit about uncertainty

### Future Memory Capabilities

Future versions may add:

- Embedding indexes
- Knowledge graphs
- Semantic search
- Source freshness checks
- Confidence scoring
- Contradiction detection
- Automatic memory decay
- Organization-wide shared knowledge

## Human Approval Gates

Human approval gates protect authority and accountability.

Approval should be required for:

- Project scope changes
- Strategic decisions
- Architecture decisions with long-term impact
- External communications
- Production release decisions
- Destructive operations
- Budget or vendor commitments
- Policy changes
- Promotion of durable knowledge when disputed

### Approval Record

Each approval record should include:

- Approval ID
- Workflow run ID
- Decision requested
- Options considered
- Agent recommendation
- Risks and tradeoffs
- Human decision
- Timestamp
- Conditions or caveats

### Approval Statuses

- Pending
- Approved
- Approved with conditions
- Rejected
- Deferred
- Superseded

## Logging And Audit Trail Design

Logs should be structured enough to reconstruct the work.

### Required Log Events

- Workflow started
- Workflow step started
- Agent invoked
- Tool used
- Evidence retrieved
- Output produced
- Critique raised
- Human approval requested
- Human decision recorded
- Error encountered
- Retry attempted
- Workflow completed
- Memory updated

### Audit Principles

- Prefer structured summaries over full noisy transcripts
- Preserve exact final outputs
- Link claims to evidence where possible
- Record human decisions explicitly
- Record uncertainty and unresolved questions
- Avoid hidden state that affects future work without explanation

### V1 Log Format

V1 can use markdown logs with predictable sections:

- Metadata
- Objective
- Participants
- Timeline
- Inputs
- Agent outputs
- Decisions
- Approvals
- Validation
- Memory updates
- Final artifacts

Later versions can add JSONL events for machine processing.

## Configuration Strategy

Configuration should be declarative and environment-aware.

### Configuration Domains

System configuration:

- Project name
- Default execution environment
- Default model/provider preferences
- Logging location
- Memory location

Agent configuration:

- Enabled agents
- Default model/provider
- Tool permissions
- Escalation rules
- Output schemas

Workflow configuration:

- Available workflows
- Required agents
- Approval gates
- Validation rules

Policy configuration:

- Human approval requirements
- Destructive action rules
- External communication rules
- Memory retention rules
- Data sensitivity rules

Provider configuration:

- Provider name
- Capability map
- Authentication method
- Cost or usage limits
- Fallback provider

### Configuration Principles

- Keep defaults simple
- Make policy visible
- Separate provider details from agent identity
- Avoid hardcoding model names into workflows
- Allow local overrides without changing shared project definitions

## Error Handling Principles

Constellation should treat errors as part of professional work, not just runtime failures.

### Error Categories

- Missing context
- Conflicting requirements
- Insufficient evidence
- Tool failure
- Model failure
- Validation failure
- Approval rejection
- Policy violation
- Memory conflict
- Provider unavailability

### Handling Rules

- Surface uncertainty early
- Escalate when authority is required
- Retry only when the failure mode is transient
- Do not hide failed validation
- Preserve partial work when useful
- Record errors in the audit trail
- Prefer graceful degradation over silent substitution
- Require human approval before bypassing a required gate

### Recovery Patterns

- Ask for clarification
- Retrieve additional knowledge
- Re-run with a different agent
- Route to a different provider
- Reduce workflow scope
- Return a blocked state with reasons
- Create a follow-up task

## Extensibility Principles

Constellation should make future growth straightforward:

- New agents should be added by authoring agent specs
- New workflows should compose existing step types
- New providers should map into common capabilities
- New memory systems should preserve provenance
- New tools should declare permissions and audit requirements
- New approval policies should be explicit and testable

The architecture should grow from stable contracts, not from hidden conventions.
