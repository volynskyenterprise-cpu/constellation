# Memory Schema

This document defines Constellation's memory model.

Memory exists to improve future professional judgment. It should be curated, sourced, and organized by lifecycle.

## Memory Layers

Constellation has four memory layers:

1. Working Memory
2. Project Memory
3. Knowledge Memory
4. Long-Term Memory

## Working Memory

Working Memory contains temporary context used during an active workflow.

Examples:

- Current objective
- Active assumptions
- Intermediate agent outputs
- Retrieved context
- Open questions
- Temporary notes
- In-progress artifacts

Properties:

- Short-lived
- Workflow-scoped
- May be noisy
- Not automatically trusted
- Cleared, summarized, or promoted at workflow completion

## Project Memory

Project Memory contains durable knowledge about the current project.

Examples:

- Project facts
- Product constraints
- Architecture decisions
- Glossary terms
- Stakeholder preferences
- Accepted risks
- Current roadmap decisions

Properties:

- Project-scoped
- Curated
- Provenance-required
- Used frequently in future workflows
- Owned by the project and maintained by the Knowledge Engineer

## Knowledge Memory

Knowledge Memory contains reusable domain and methodology knowledge.

Examples:

- Reusable patterns
- Research references
- Methods
- Lessons learned
- Evaluation criteria
- Common failure modes

Properties:

- Cross-workflow
- May be cross-project in future versions
- Curated
- Provenance-required
- Should include freshness or review expectations when facts may change

## Long-Term Memory

Long-Term Memory contains retained historical records that support audit, continuity, and organizational learning.

Examples:

- Archived workflow summaries
- Final decisions
- Release records
- Approval history
- Deprecated knowledge
- Postmortems
- Major artifact versions

Properties:

- Retention-oriented
- Audit-friendly
- Usually not loaded directly into active context
- Retrieved selectively
- May include obsolete information if clearly marked

## Memory Entry Format

Every durable memory entry should include:

```text
MemoryEntry
  id
  type
  layer
  title
  summary
  content
  provenance
  confidence
  status
  owner
  created_at
  updated_at
  review_after
  related_entities
```

## Memory Fields

`id`: Unique memory identifier.

`type`: Fact, decision, constraint, reference, lesson, pattern, glossary term, artifact summary, or other documented type.

`layer`: One of `working`, `project`, `knowledge`, `long_term`.

`title`: Short name.

`summary`: Concise human-readable summary.

`content`: Full memory content.

`provenance`: Source of the memory entry.

`confidence`: `low`, `medium`, `high`, or `unknown`.

`status`: `candidate`, `accepted`, `accepted_with_caveats`, `rejected`, `obsolete`, or `deprecated`.

`owner`: Responsible human or agent role.

`created_at`: ISO 8601 timestamp.

`updated_at`: ISO 8601 timestamp.

`review_after`: Optional date or condition for review.

`related_entities`: Related workflows, messages, events, approvals, artifacts, or memory entries.

## Information Movement

### Working Memory To Project Memory

Information may move from Working Memory to Project Memory when:

- It describes this project.
- It is likely to matter again.
- It has provenance.
- It has been reviewed by the Knowledge Engineer.
- It is not merely an intermediate note.

Examples:

- Accepted product constraint
- Approved architecture decision
- Stable glossary term

### Working Memory To Knowledge Memory

Information may move from Working Memory to Knowledge Memory when:

- It is reusable beyond the current workflow.
- It captures a method, pattern, reference, or lesson.
- It has provenance and enough context to be useful later.

Examples:

- QA pattern
- Research method
- Design review heuristic

### Project Memory To Long-Term Memory

Project Memory may move or copy into Long-Term Memory when:

- It is superseded but still relevant for audit.
- It belongs to a completed phase.
- It records a major decision or release.

### Knowledge Memory To Long-Term Memory

Knowledge Memory may move into Long-Term Memory when:

- It is obsolete.
- It is retained for historical reasons.
- It has been replaced by a better pattern or reference.

### Long-Term Memory To Working Memory

Long-Term Memory may be retrieved into Working Memory when:

- A current workflow needs historical context.
- A prior decision explains a constraint.
- A previous failure mode may recur.

Retrieved long-term entries should be clearly marked as historical.

## Promotion Workflow

1. Capture candidate information in Working Memory.
2. Emit `MemoryProposed`.
3. Knowledge Engineer reviews provenance and relevance.
4. Resolve conflicts with existing memory.
5. Human approval is requested if the memory is disputed or consequential.
6. Accepted memory is written to the appropriate layer.
7. Emit `MemoryUpdated` or `MemoryPromoted`.

## Memory Conflict Rules

When memory entries conflict:

- Do not silently overwrite.
- Emit `MemoryConflictDetected`.
- Preserve both entries until resolved.
- Mark confidence and status clearly.
- Escalate disputed durable knowledge to human approval.

## Retention Rules

- Working Memory may be summarized or discarded after workflow completion.
- Project Memory should remain current.
- Knowledge Memory should be reviewed for freshness.
- Long-Term Memory should preserve audit value even when obsolete.

## Extension Rules

New memory stores may be introduced if they preserve:

- Layer classification
- Provenance
- Status
- Reviewability
- Event emission
- Human approval for disputed durable knowledge
