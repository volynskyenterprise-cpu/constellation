# Constellation Real Estate Intelligence v7.1.1 - Assignment Consolidation

Assignment Consolidation groups multiple local intake artifacts that belong to the same real-world appraisal or valuation assignment into one canonical assignment view.

This is deterministic assignment consolidation, not document deduplication.

## Purpose

A single assignment may appear as:

- Gmail intake JSON
- Axis intake JSON
- Assignment markdown
- Knowledge Pack
- Review markdown
- Intake review JSON
- Supporting automation artifacts

Consolidation turns those source artifacts into:

```text
Canonical Assignment
  -> Assignment Timeline
  -> Assignment Sources
  -> Assignment Facts
  -> Knowledge Pack
  -> Evidence
  -> Reviewer Notes
  -> Assignment Intelligence
```

## Rules

Artifacts are grouped using deterministic rules only:

1. Explicit `assignment_id`
2. Explicit `order_id`
3. Loan number
4. Exact normalized property address
5. Subject address plus effective date
6. Structured field overlap

No fuzzy semantic matching, embeddings, LLM inference, or external address services are used.

## Address Normalization

Addresses are normalized by:

- lowercasing
- removing punctuation
- normalizing abbreviations such as `street` to `st`, `avenue` to `ave`, and `road` to `rd`
- collapsing whitespace

## Outputs

```text
outputs/real-estate/consolidation/
  assignment-clusters.json
  assignment-clusters.md
  assignment-relationships.json
  assignment-conflicts.json
  assignment-consolidation-history.json
  assignment-consolidation-delta.json
```

## CLI

```bash
python -m constellation real-estate consolidation
python -m constellation real-estate consolidation status
python -m constellation real-estate consolidation clusters
python -m constellation real-estate consolidation conflicts
python -m constellation real-estate consolidation relationships
python -m constellation real-estate consolidation export
```

## Dashboard

The dashboard reports consolidated Real Estate state:

- Assignments
- Artifacts
- Knowledge Packs
- Assignments with reviewer notes
- Assignments with conflicts
- Top active assignments

## Assignment Briefs

When consolidation data exists, Assignment Briefs include:

- Artifacts
- Relationships
- Conflicts
- Knowledge Pack availability
- Reviewer note availability

## Safety

Assignment Consolidation does not:

- generate valuation opinions
- select comparables
- generate adjustments
- interpret permits
- make USPAP conclusions
- call providers
- call external services
- use semantic similarity

It only groups explicit local artifacts and preserves conflicts for human review.
