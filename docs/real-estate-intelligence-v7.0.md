# Constellation Real Estate Intelligence v7.0

Institutional Valuation Operating System

Constellation Real Estate Intelligence is a deterministic evidence-first operating system for valuation professionals.

It is not automated appraisal. It is not value prediction. It is not autonomous valuation.

It is designed to improve valuation judgment through deterministic evidence, institutional memory, comparable intelligence, adjustment intelligence, reviewer intelligence, and continuous learning.

## 1. Product Vision

Constellation Real Estate Intelligence extends Constellation into professional valuation work.

The product vision is to help appraisers and valuation teams organize assignments, preserve evidence, understand property context, support conclusions, respond to review pressure, and improve over time.

The system should help answer:

- What property am I working on?
- Why is it worth what it is?
- How should I support this appraisal?
- How can I become a better appraiser?

Real Estate Intelligence is not a replacement for professional judgment. It is a deterministic institutional support system for better judgment.

## 2. Why Real Estate Intelligence

Real estate valuation depends on evidence, comparability, local knowledge, adjustment discipline, narrative support, client requirements, and reviewer expectations.

Much of that knowledge is scattered across MLS exports, public records, permit data, prior reports, photos, sketches, contracts, client instructions, reviewer notes, and personal memory.

Real Estate Intelligence exists to make that knowledge durable.

It should help valuation professionals:

- Understand assignment context quickly.
- Preserve source evidence and provenance.
- Compare properties more consistently.
- Track adjustment rationale.
- Detect missing support before review.
- Learn from reviewer comments and past outcomes.
- Reuse institutional knowledge without fabricating unsupported conclusions.

## 3. Relationship to PKOS

PKOS remains the Executive Operating System.

PKOS coordinates executive execution, knowledge orchestration, priorities, communication, and operating cadence.

Real Estate Intelligence is not PKOS. It is a domain intelligence system that can feed PKOS with valuation-related status, bottlenecks, learning records, and decision-support artifacts.

PKOS may answer:

- What appraisal work needs executive attention?
- Which client or reviewer issues require follow-up?
- Which operational risks are emerging?

Real Estate Intelligence answers:

- What does the valuation evidence show?
- How should this assignment be supported?
- What should the appraiser review before completing or revising the report?

## 4. Relationship to Constellation AI

Constellation AI is becoming a multi-domain institutional decision platform.

AI & Markets Core v1 has completed the first domain stack:

- Observe: AI & Markets Intelligence
- Understand: Theme Lifecycle, Portfolio Intelligence, Catalyst Monitoring
- Decide: Decision Journal, Executive Morning Brief
- Improve: Performance Intelligence, Thesis Accuracy

Real Estate Intelligence applies the same deterministic evidence-first operating model to valuation work.

AI & Markets remains the Institutional Investment Operating System.

Real Estate Intelligence becomes the Institutional Valuation Operating System.

Both domains share architectural primitives:

- Evidence
- Memory
- Knowledge Graph
- Decision Support
- Learning

They remain operationally independent.

## v7.0 Implementation - Assignment Intelligence MVP

The first implemented Real Estate Intelligence capability is Assignment Intelligence.

Assignment Intelligence answers the Phase I Observe question:

> What property am I working on?

It creates deterministic local assignment records from `assignment.yaml`, source-file metadata, and explicitly supplied structured facts. It produces assignment briefs, source manifests, evidence indexes, missing-information reports, risk reports, timeline records, history snapshots, and deltas.

### v7.3.2 Canonical Property-Type Normalization

Assignment Intelligence and Comparable Intelligence share one deterministic property-type alias policy. Explicit single-family labels such as `Single Family`, `single-family`, `SFR`, and `detached single family` normalize to `single_family_residential`, while the raw source value and assignment provenance remain visible.

Blank classifications remain unavailable. Unsupported non-empty classifications remain visible with a `review_required` normalization state and a missing-information review item instead of silently becoming `other`. No property type is inferred from an address, zoning, bedroom count, ADU, proposed configuration, or ARV condition. Directional address discrepancies remain conservative identity review items.

### v7.3.3 Structured Address Equivalence

Comparable Intelligence compares scenario and canonical subject addresses through explicit structured components. Supported suffix, directional, unit-marker, state-name, punctuation, case, whitespace, and ZIP+4 aliases normalize deterministically while raw values and both source paths remain visible. Locality omitted by one source is incomplete rather than contradictory; conflicting populated city, state, or postal-code facts remain review-required.

Directionals and unit identifiers are identity-bearing. A populated directional or unit does not equal a blank or different value, malformed and unsupported addresses remain reviewable, and no input or canonical output is rewritten automatically. The policy uses no fuzzy matching, geocoding, parcel lookup, provider calls, or external address validation.

### v7.3.4 Expanded Scenario Subject Provenance

Comparable Intelligence resolves explicit scenario facts for unit and accessory-unit configuration, garage and parking counts, pool and spa, view, design/style, effective age, year built, and location features. Deterministic aliases produce canonical internal field names while retaining raw field names, source paths, alternate values, and verification status.

Private `subject_alternates` assertions are compared without changing the governing scenario fact. Material differences open scenario-specific conflicts and review items, and coverage is labeled when its subject baseline is conflicted. Assignment briefs and aggregate dashboards expose only administrative conflict counts and review indicators; private subject detail remains in assignment-specific reports.

Unit/accessory-unit evidence remains descriptive. Constellation does not determine legality, permits, completion, zoning compliance, highest and best use, GLA treatment, feasibility, adjustments, or value.

### v7.3.5 Nested Subject Evidence Compatibility

Comparable Intelligence reads preferred `subject_alternates` documents and the historical `subject_evidence.alternates`, direct-field, and nested `subject_evidence.fields.<field>.alternate_values` layouts through one deterministic assertion adapter. Alternate, field, and document provenance is inherited only when explicitly supplied; schema origin/path and raw field names remain visible in assignment-specific reports.

Scalar, structured mapping, and documented field-keyed alternates are supported. Exact duplicate assertions are consolidated without merging different sources or materially different metadata. Malformed nested evidence remains review-required, and descriptive text is never converted into structured unit, accessory-unit, bedroom, bathroom, legal, completion, GLA, adjustment, or valuation facts.

### v7.3.6 Alternate Evidence Integrity Hardening

Valid empty alternate lists—including an exact scalar `"[]"` emitted by the local YAML reader—are treated as empty evidence without false parsing limitations or review items. Non-empty malformed or descriptive values remain reviewable and never produce cross-field facts.

Alternate assertions inherit explicit provenance from alternate, field, then enclosing-document scope. One parent path can populate the compatible singular path, while multiple parent paths remain preserved together without an arbitrary choice. Usable parent provenance prevents false missing-source reviews. Assignment-specific Markdown reports show source, verification, schema origin, schema path, and inheritance details.

Byte-aware appraiser review-state persistence skips writes when deterministic serialized bytes are unchanged, preserving modification timestamps on no-op builds. Meaningful state changes and history snapshots retain their existing governed behavior.

Private assignment files use:

```text
real-estate/assignments/<ASSIGNMENT_ID>/
  assignment.yaml
  sources/
  notes/
  evidence/
```

This private assignment tree is ignored by Git. Public examples remain under `real-estate/examples/`.

The MVP does not parse PDFs, OCR images, retrieve permits, analyze MLS files, select comparables, generate adjustments, produce value opinions, or make USPAP conclusions.

## v7.1 Implementation - Assignment Auto-Ingestion

The second implemented Real Estate Intelligence capability removes manual assignment setup friction.

Assignment Auto-Ingestion reads structured local intake artifacts, detects assignment candidates, creates or merges private assignment folders, writes `assignment.yaml`, references or copies source files, builds Assignment Intelligence automatically, writes intake manifests, and refreshes the dashboard.

It supports optional local PKOS/AOC integration through gitignored config files. It does not hardcode external vault paths and does not create a dependency on PKOS.

The v7.1 implementation still does not parse arbitrary narrative content, select comparables, generate adjustments, interpret permits, produce value opinions, or make USPAP conclusions.

## v7.1.1 Implementation - Assignment Consolidation

Assignment Consolidation groups multiple intake artifacts that represent the same real-world assignment into one canonical assignment view.

It creates deterministic clusters, relationships, conflicts, history, and deltas from existing local Real Estate intake and assignment artifacts.

Consolidation is based only on explicit IDs, normalized addresses, dates, and structured field overlap. It does not use semantic similarity, provider calls, external address services, or valuation inference.

## v7.1.2 Implementation - Assignment Identity Resolution

Assignment Identity Resolution refines consolidation by cleaning HTML entities, pairing source companion artifacts, preserving source-generated aliases, separating unassigned artifacts, and reporting true identity conflicts.

It keeps exact deterministic rules: no fuzzy matching, semantic similarity, provider calls, external address services, or valuation inference.

## v7.2.0 Implementation - Canonical Assignment Model

The Canonical Assignment Model makes one canonical assignment object the operational center of Real Estate Intelligence.

Target flow:

```text
Intake Artifacts
  -> Identity Resolution
  -> Canonical Assignment
  -> Assignment Intelligence
  -> Comparable Intelligence
  -> Adjustment Intelligence
```

Assignment Consolidation decides which artifacts belong together. The Canonical Assignment Model persists one assignment directory, alias index, source index, assignment brief, timeline, fact set, missing-information set, and risk set for each real-world assignment.

New intake writes to canonical assignment directories instead of creating separate directories for Gmail aliases, Axis aliases, or address-derived aliases. Assignment CLI commands resolve aliases before operating when resolution is unambiguous.

Migration support is non-destructive. It can identify existing alias directories, write migration plans, mark alias directories as migrated, and preserve rollback metadata. It does not delete source artifacts or private assignment directories.

## v7.2.1 Implementation - Canonical Operations Hardening

Canonical Operations Hardening makes the canonical assignment layer easier to operate safely.

It synchronizes canonical status, migration plan, dashboard counts, review queue, and operations reports around one deterministic migration state.

It adds explicit migration categories:

- `safe_merge`
- `preserve_alias`
- `blocked_by_conflict`
- `ambiguous`
- `orphan`
- `already_migrated`

It also adds operator review outputs under:

```text
outputs/real-estate/canonical/
```

The key new output is:

```text
review-queue.md
```

This is a visibility layer only. It does not automatically migrate live assignment directories, resolve conflicts, infer identity semantically, or generate valuation conclusions.

## v7.2.2 Implementation - Scoped Canonical Migration

Scoped Canonical Migration completes the core v7.2 operational safety model.

Operators can now scope migration by:

- ready-only entries
- migration category
- canonical assignment
- source assignment directory

The recommended apply path is:

```bash
python -m constellation real-estate canonical migrate --apply --ready-only
```

This applies only `safe_merge` and `preserve_alias` entries.

It never applies:

- `blocked_by_conflict`
- `ambiguous`
- `orphan`
- `already_migrated`

Unsafe unscoped apply is refused when the plan contains mixed categories. Alias directories are preserved, source files are not deleted, and conflicts remain for human review.

## v7.2.3 Implementation - Post-Migration Canonical Count Integrity

Post-Migration Canonical Count Integrity ensures non-destructive migration markers do not change assignment identity.

A migrated alias directory is classified as `migrated_alias`. It remains on disk and remains visible in migration audit outputs as `already_migrated`, but canonical assignment refresh excludes it from canonical assignment discovery and source-artifact discovery. Dashboard and operations counts should remain stable across repeated refreshes after scoped migration.

This patch does not delete alias directories, remove markers, roll back migrations, resolve conflicts, or alter valuation logic.

## v7.2.4 Implementation - Real Estate Daily Automation

Real Estate Daily Automation adds the Real Estate operating loop to the scheduled Morning workflow.

The daily loop runs deterministic Real Estate intake, Assignment Consolidation refresh, Canonical Assignment refresh, Assignment Intelligence builds for affected canonical assignments, Canonical Operations refresh, and dashboard refresh.

It writes:

```text
outputs/real-estate/daily/latest-real-estate-daily-run.json
outputs/real-estate/daily/real-estate-daily-report.md
outputs/real-estate/daily/real-estate-daily-history.json
outputs/real-estate/daily/real-estate-daily-delta.json
```

It does not apply migration, resolve conflicts automatically, delete alias directories, generate valuation opinions, select comparables, create adjustments, interpret permits, or make USPAP conclusions.

## v7.3.0 Implementation - Comparable Intelligence

Comparable Intelligence marks the transition from assignment infrastructure to valuation evidence intelligence.

It organizes locally supplied comparable-sale evidence for a canonical assignment, normalizes structured YAML, JSON, and CSV records, detects deterministic duplicates and conflicts, classifies factual similarity components, reports coverage and bracketing, and preserves appraiser-controlled review state.

It does not select final comparables, generate appraisal adjustments, reconcile value indicators, produce value conclusions, retrieve live MLS data, use semantic matching, or replace professional judgment.

## v7.3.1 Implementation - Comparable Scenario and Subject Resolution

Two-value assignments now use isolated comparable scenarios, including `as_is` and `arv`. Each scenario owns its subject facts, comparable universe, coverage, conflicts, review state, history, and outputs. Scenario facts take precedence over blank or conflicting generic canonical facts for that scenario only; conflicts remain visible and neither source is overwritten.

Distance aliases normalize deterministically to `distance_from_subject_miles`. Missing geography limits tier eligibility but no longer makes an otherwise usable closed sale insufficient. Older sales remain available as contextual evidence. Comparable Intelligence remains a pre-adjustment evidence-organization layer: it does not calculate values, adjustments, feasibility, legality, hypothetical conditions, or final comparable selection.

## 5. Institutional Valuation Operating System

Real Estate Intelligence should operate as an institutional layer around the appraisal workflow.

It should not complete appraisals automatically. It should structure valuation work so evidence, reasoning, adjustments, and review responses become auditable and reusable.

The operating loop is:

Observe

↓

Understand

↓

Decide

↓

Improve

The system should make every valuation assignment more organized than the last.

## 6. Capability Roadmap

Real Estate Intelligence follows the same capability progression as AI & Markets:

| Phase | Capability | Primary Question |
| --- | --- | --- |
| Phase I — Observe | Assignment Intelligence | What property am I working on? |
| Phase II — Understand | Comparable, Adjustment, Neighborhood, Market, Permit, MLS, and Knowledge Pack Intelligence | Why is this property worth what it is? |
| Phase III — Decide | Reviewer, Narrative, Certification, Evidence Pack, and Report Intelligence | How should I support this appraisal? |
| Phase IV — Improve | Adjustment Accuracy, Reviewer Trend Analysis, Litigation Intelligence, Quality Scoring, Valuation Learning Loop, and Institutional Memory | How can I become a better appraiser? |

Each capability should be deterministic, evidence-backed, and provenance-preserving.

## 7. Phase I — Observe

### Assignment Intelligence

Assignment Intelligence is the v7.0 foundation.

Primary question:

> What property am I working on?

Assignment Intelligence should organize the basic facts of a valuation assignment:

- Subject property identity
- Assignment type
- Client and intended use
- Effective date
- Report due date
- Property rights
- Scope of work
- Source documents received
- Known constraints
- Missing information
- Required follow-up

It should generate an assignment brief that helps the appraiser start with a clear factual picture.

Assignment Intelligence must not infer unsupported property facts. If a fact is missing, conflicting, or unclear, it should be reported as missing, conflicting, or unclear.

## 8. Phase II — Understand

### Comparable Intelligence

Comparable Intelligence should organize comparable sales, listings, rentals, pending sales, and relevant market evidence.

It should help identify:

- Which comparables are available.
- Which comparables are most similar by explicit attributes.
- Which comparables require explanation.
- Which comparables may be weak or unsupported.
- Which data fields conflict across sources.

It should not select comps autonomously or claim a comp is superior without deterministic evidence.

### Adjustment Intelligence

Adjustment Intelligence should preserve adjustment rationale and evidence.

It should track:

- Adjustment type
- Direction
- Source evidence
- Paired-sales support where available
- Market-extracted support where available
- Prior institutional support
- Reviewer challenges
- Known weaknesses

It must never invent adjustments.

### Neighborhood Intelligence

Neighborhood Intelligence should organize location context.

It may consume:

- Neighborhood descriptions
- Market area boundaries
- School district references
- Proximity factors
- External obsolescence indicators
- Local land use context
- Prior neighborhood narratives

It should support consistency without copying stale unsupported language.

### Market Condition Intelligence

Market Condition Intelligence should track deterministic market indicators.

Potential inputs include:

- MLS export statistics
- Sale/list ratios
- Days on market
- Inventory
- Price trends
- Concessions
- Contract activity
- Prior market condition summaries

It should identify available evidence and open questions, not predict value.

### Permit Intelligence

Permit Intelligence should organize permit records.

It should track:

- Permit number
- Permit type
- Status
- Issued date
- Finaled date
- Scope
- Contractor
- Source path
- Relevance to subject or comparable

It must never invent permits or assume permit completion without evidence.

### MLS Intelligence

MLS Intelligence should normalize MLS data exports and preserve field-level provenance.

It should support:

- Property attribute comparison
- Sale and listing chronology
- Concessions and financing terms
- Agent remarks review
- Data conflict detection
- Comparable table preparation

It should not rely on MLS remarks as fact without source qualification.

### Knowledge Pack Intelligence

Knowledge Pack Intelligence should preserve reusable domain knowledge.

Knowledge packs may include:

- Local market area notes
- Builder/subdivision knowledge
- Property type considerations
- Adjustment studies
- Review response templates
- Client-specific requirements
- Agency guideline summaries

Knowledge packs must be dated, sourced, and subject to review.

## 9. Phase III — Decide

### Reviewer Intelligence

Reviewer Intelligence should organize reviewer comments, conditions, patterns, and response history.

It should help answer:

- What is the reviewer asking?
- Has this issue appeared before?
- Which evidence supports the response?
- Which report section needs revision?
- Which response language worked previously?

It should not obscure legitimate reviewer concerns.

### Narrative Intelligence

Narrative Intelligence should help assemble evidence-backed narrative components.

It may support:

- Neighborhood narrative
- Market conditions narrative
- Comparable selection rationale
- Adjustment rationale
- Reconciliation support
- Extraordinary assumption and hypothetical condition checks

It must not generate unsupported appraisal conclusions.

### Certification Intelligence

Certification Intelligence should help verify required certifications and limiting conditions.

It should check:

- Assignment type requirements
- Client requirements
- Intended use language
- Property rights appraised
- Effective date consistency
- Report form requirements
- Required disclosures

It should flag issues for professional review.

### Evidence Packs

Evidence Packs should bundle supporting records for a valuation conclusion or report section.

They may include:

- MLS sheets
- Public record excerpts
- Permit records
- Photos
- Maps
- Market statistics
- Adjustment support
- Prior report references
- Reviewer response evidence

Each evidence pack must preserve provenance.

### Report Intelligence

Report Intelligence should help review report completeness and internal consistency.

It may check:

- Subject facts consistency
- Comparable data consistency
- Date consistency
- Narrative alignment
- Adjustment support references
- Missing exhibits
- Reviewer-risk flags

It must not automatically complete appraisal reports.

## 10. Phase IV — Improve

### Adjustment Accuracy

Adjustment Accuracy should compare prior adjustment rationale against later evidence and review outcomes.

It should track where adjustments were:

- Supported
- Challenged
- Revised
- Repeated
- Inconsistent
- Unresolved

It should not claim market accuracy unless supported by explicit outcome evidence.

### Reviewer Trend Analysis

Reviewer Trend Analysis should track recurring reviewer concerns.

It should help identify:

- Repeated condition types
- Client-specific review patterns
- Narrative weaknesses
- Evidence gaps
- Formatting or compliance issues

### Litigation Intelligence

Litigation Intelligence should preserve high-risk case memory and dispute lessons.

It may track:

- Dispute type
- Challenged conclusion
- Evidence cited
- Outcome
- Lessons learned
- Preventive process changes

### Quality Scoring

Quality Scoring should evaluate process quality, not property value.

Potential factors:

- Evidence completeness
- Source provenance
- Comparable support
- Adjustment support
- Narrative consistency
- Reviewer issue count
- Revision count
- Missing document count

Scores must be deterministic and explainable.

### Valuation Learning Loop

The Valuation Learning Loop should connect assignments, reviewer comments, revisions, outcomes, and lessons.

It should answer:

- What caused rework?
- Which evidence was missing?
- Which narrative was weak?
- Which adjustment was challenged?
- Which process improvement should be retained?

### Institutional Memory

Institutional Memory should preserve lessons across assignments.

It should store:

- Reusable evidence patterns
- Market area notes
- Adjustment support references
- Reviewer response history
- Client requirements
- Quality lessons

It should never store private or sensitive data beyond the authorized local operating scope.

## 11. Core Objects

Suggested core objects:

- Assignment
- Property
- Comparable
- KnowledgePack
- PermitRecord
- Adjustment
- NeighborhoodProfile
- MarketCondition
- ReviewerComment
- EvidencePack
- Narrative
- Certification
- LearningRecord
- ValuationOutcome
- AdjustmentOutcome
- QualityScore
- CaseMemory

Each object should include:

- Stable ID
- Source references
- Created and updated timestamps
- Provenance
- Status
- Limitations
- Human review state where appropriate

## 12. Inputs

Potential deterministic inputs:

- MLS exports
- Property records
- Permit records
- Floor plans
- Sketches
- Photos
- Comparable spreadsheets
- Prior reports
- Reviewer conditions
- AMC messages
- Client instructions
- Contracts
- Escrow documents
- Market studies
- Knowledge packs
- Private institutional memory

Inputs should be local-first and provenance-preserving.

No source should be treated as authoritative without source identification.

## 13. Outputs

Potential outputs:

- `assignment-brief.md`
- `knowledge-pack.md`
- `comparable-intelligence.md`
- `adjustment-intelligence.md`
- `reviewer-intelligence.md`
- `evidence-pack.md`
- `narrative.md`
- `quality-review.md`
- `valuation-learning-loop.md`

Outputs should support professional review, not replace it.

## 14. Morning Workflow

A future Real Estate Morning Brief should summarize the current valuation operating state.

Potential sections:

- Assignments due soon
- Missing documents
- Reviewer conditions requiring response
- Open evidence gaps
- Comparable research needs
- Permit questions
- Narrative sections needing review
- Quality risks
- Learning loop updates

The brief should be deterministic and local-only.

It should not make value predictions or complete reports.

## 15. Relationship to AI & Markets

Constellation AI is becoming multi-domain.

AI & Markets remains:

Institutional Investment Operating System

Real Estate Intelligence becomes:

Institutional Valuation Operating System

Both share:

- Evidence
- Memory
- Knowledge Graph
- Decision Support
- Learning

The systems should integrate at the platform layer while preserving separate domain objects, workflows, and responsibilities.

## 16. Relationship to PKOS

PKOS remains:

Executive Operating System

Constellation becomes:

Domain Intelligence Platform

PKOS may coordinate work across domains, while Constellation domain systems preserve the specialized evidence, methodology, and learning loops required for each professional field.

## 17. Safety

Real Estate Intelligence must never:

- Generate unsupported values
- Invent comparable adjustments
- Invent permits
- Invent market evidence
- Replace professional judgment
- Automatically complete appraisal reports
- Provide USPAP opinions without evidence

Real Estate Intelligence must always:

- Preserve provenance
- Show evidence
- Support, not replace, professional judgment
- Flag missing evidence clearly
- Preserve uncertainty
- Escalate conflicts for human review

## 18. Capability Roadmap

### Phase I — Observe

v7.0 — Assignment Intelligence

Question:

> What property am I working on?

### Phase II — Understand

v7.1–v7.3 — Comparable Intelligence, Adjustment Intelligence, Neighborhood Intelligence, Permit Intelligence

Question:

> Why is this property worth what it is?

### Phase III — Decide

v7.4–v7.5 — Reviewer Intelligence, Narrative Intelligence, Evidence Packs

Question:

> How should I support this appraisal?

### Phase IV — Improve

v8.0 — Adjustment Accuracy, Reviewer Trend Analysis, Valuation Learning Loop

Question:

> How can I become a better appraiser?

## 19. Future Extensions

Future Real Estate Intelligence extensions may include:

- Commercial
- Industrial
- Land
- Hospitality
- Litigation
- Expert Witness
- Portfolio Valuation
- Institutional Lending
- Fannie
- Freddie
- FHA
- VA
- USDA

Each extension should maintain deterministic evidence-first behavior and clear professional boundaries.

## 20. Operating Philosophy

Data

↓

Information

↓

Evidence

↓

Intelligence

↓

Understanding

↓

Judgment

↓

Decision

↓

Learning

Constellation AI is evolving into a multi-domain institutional decision platform.

Each domain follows the same deterministic evidence-first operating philosophy while remaining independent.

AI & Markets

Institutional Investment Operating System

Real Estate Intelligence

Institutional Valuation Operating System

Future domains may reuse the same architecture while preserving clear operational boundaries.

### v7.4.0 Adjustment Intelligence

Adjustment Intelligence implements the governed transition from comparable facts to adjustment support:

`Assignment Intelligence → Comparable Intelligence → Adjustment Intelligence → Appraiser Decision → Deterministic Application → Appraiser Reconciliation`

Each valuation scenario retains independent evidence, decisions, conflicts, history, fingerprints, and reports. The engine calculates factual subject-minus-comparable differences, transparent governed-pair and grouped indications, descriptive aggregation, coverage, sensitivity, and gross/net mathematical diagnostics. Appraisal-grid adjustment references are blocked from circularly serving as independent support.

Only an explicitly confirmed appraiser decision may select a rate or record no adjustment. Deterministic application follows the appraisal-grid convention: an inferior comparable receives a positive adjustment and a superior comparable receives a negative adjustment. Raw arithmetic remains visible separately from presentation rounding.

Adjustment Intelligence does not select rates, final comparables, weights, reconciliation, ARV, or market value. It makes no legality, permitting, completion, feasibility, GLA-treatment, highest-and-best-use, or USPAP determination. Full architecture, schema, CLI, outputs, privacy controls, and limitations are documented in `adjustment-intelligence-v7.4.md`.
