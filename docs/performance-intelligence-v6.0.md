# Constellation AI v6.0 — Performance Intelligence

## 1. Product Vision

Performance Intelligence closes the loop between research, decisions, outcomes, and learning.

Constellation AI is an Institutional Investment Operating System. v5 built the capability stack for observing markets, understanding context, supporting judgment, and prioritizing daily research. v6.0 adds the deterministic feedback layer that helps the operator evaluate whether the research process is improving over time.

Performance Intelligence should help answer:

- How well am I doing?
- How can I become a better investor?
- Which decisions were well-supported by evidence?
- Which theses strengthened, weakened, or failed to develop?
- Which signals were useful, stale, noisy, or misleading?
- Which catalysts mattered?
- Which recurring mistakes should be corrected?
- Which repeatable strengths should be reinforced?

This is not financial advice. It is not performance reporting for clients. It is not a trading system. It is not an autonomous investment system.

It is a deterministic learning and feedback layer.

## v6.0.0 MVP Implementation

The v6.0.0 MVP implements the first deterministic feedback loop with a narrow focus on Decision Outcome Tracking and Process Lessons.

Implemented capabilities:

- Parse generated AI & Markets Decision Journal outputs
- Classify decision outcomes as pending, due, overdue, user-confirmed, user-challenged, user-contradicted, lesson-recorded, or reviewed without outcome
- Link decisions to deterministic theme lifecycle, catalyst, portfolio/watchlist, and risk records when exact references exist
- Generate Performance Signal records for review discipline, missing review inputs, catalyst follow-up, risk follow-up, and available lessons
- Generate Process Lesson records only from explicit user-recorded lessons or repeated deterministic process gaps
- Persist Learning Loop snapshots, history, and deltas
- Integrate Performance Intelligence into the Executive Dashboard and Morning workflow

Deferred capabilities:

- Attribution analysis
- Win/loss analysis
- Full thesis accuracy scoring
- Full signal quality scoring
- Full catalyst accuracy scoring
- Forecast calibration
- Human-reviewed learning-loop promotion
- Any user-supplied performance data ingestion

## 2. Why Performance Intelligence Matters

Most investment systems emphasize discovery: more sources, more signals, more alerts, more charts.

Constellation AI should emphasize improvement: better judgment, better process discipline, better evidence review, better decision records, and better learning from outcomes.

Performance Intelligence matters because investment judgment compounds only when decisions are reviewed honestly. Without a structured feedback loop, research can become accumulation rather than learning.

The purpose of v6.0 is to make the investment process inspectable:

- What did the system believe?
- What evidence supported that belief?
- What decision or review action followed?
- What happened afterward?
- What should be learned?
- What should change in the process?

## 3. Relationship to v5 AI & Markets Intelligence

The v5 capability stack is complete:

- v5.0.0 — AI & Markets Intelligence
- v5.0.1 — Signal Refinement
- v5.1.0 — Theme Lifecycle
- v5.2.0 — Portfolio Intelligence
- v5.3.0 — Catalyst Monitoring
- v5.4.0 — Decision Journal
- v5.5.0 — Executive Morning Brief

v5 answers:

- What is happening?
- Why does it matter?
- What should I do today from a research and decision-support standpoint?

v6 answers:

- How well am I doing?
- How can I become a better investor?

Performance Intelligence should consume v5 outputs rather than replace them. It should especially consume:

- Decision Journal outputs from v5.4
- Executive Morning Brief outputs from v5.5
- Theme Lifecycle records from v5.1
- Portfolio Intelligence review queues from v5.2
- Catalyst Monitoring records from v5.3
- Evidence, thesis, graph, dashboard, and workflow outputs from the deterministic Constellation core

The result is a closed loop:

```text
Research
↓
Evidence
↓
Signals
↓
Themes
↓
Decisions
↓
Outcomes
↓
Lessons
↓
Improved process
```

## 4. Core Question: How can I become a better investor?

Performance Intelligence should not ask, "What should I buy?"

It should ask:

- Did I make decisions with enough evidence?
- Did I distinguish signal from noise?
- Did I update theses when facts changed?
- Did I follow up on catalysts?
- Did I review portfolio/watchlist exposures at the right time?
- Did I ignore contradictions?
- Did I overreact to weak signals?
- Did I underreact to repeated confirmations?
- Did I write down the reason for important decisions?
- Did later evidence confirm, weaken, or complicate the original reasoning?

The product should improve the operator's investment process by making judgment visible, reviewable, and historically grounded.

## 5. Inputs

Performance Intelligence should consume existing local artifacts only.

Primary inputs:

- `outputs/ai-markets/decisions/decision-journal.json`
- `outputs/ai-markets/decisions/decision-entries.json`
- `outputs/ai-markets/decisions/decision-review-queue.json`
- `outputs/ai-markets/decisions/decision-outcomes.json`
- `outputs/ai-markets/briefings/morning-brief.json`
- `outputs/ai-markets/briefings/research-agenda.json`
- `outputs/ai-markets/theme-lifecycle.json`
- `outputs/ai-markets/theme-history.json`
- `outputs/ai-markets/theme-transitions.json`
- `outputs/ai-markets/portfolio/portfolio-intelligence.json`
- `outputs/ai-markets/portfolio/portfolio-exposures.json`
- `outputs/ai-markets/portfolio/portfolio-risks.json`
- `outputs/ai-markets/catalysts/catalyst-monitor.json`
- `outputs/ai-markets/catalysts/catalyst-history.json`
- `outputs/ai-markets/catalysts/catalyst-delta.json`
- `outputs/thesis/theses.json`
- `outputs/evidence-graph/evidence-graph.json`
- `outputs/dashboard/dashboard.json`
- `outputs/daily/daily-history.json`
- `outputs/workflows/workflow-history.json`
- `memory/evidence/`

Optional future inputs:

- Human-reviewed decision outcome notes
- Human-reviewed thesis review notes
- Human-reviewed catalyst follow-up notes
- Portfolio review annotations
- External performance data explicitly supplied by the user

Performance Intelligence should not fetch external market data, call providers, retrieve web content, or infer unsupported outcomes.

## 6. Core Objects

### PerformanceReview

A periodic review of the investment process.

Fields should include:

- `review_id`
- `created_at`
- `review_period_start`
- `review_period_end`
- `decision_outcome_ids`
- `thesis_outcome_ids`
- `signal_quality_score_ids`
- `catalyst_outcome_ids`
- `portfolio_review_outcome_ids`
- `process_lesson_ids`
- `summary`
- `strengths`
- `weaknesses`
- `open_questions`
- `provenance`
- `limitations`

### DecisionOutcome

A deterministic review record linking a decision journal entry to later evidence, reviews, or outcomes.

Fields should include:

- `decision_outcome_id`
- `decision_id`
- `decision_title`
- `decision_date`
- `review_status`
- `review_due_at`
- `linked_evidence_ids`
- `later_evidence_ids`
- `linked_theme_ids`
- `linked_entity_ids`
- `linked_catalyst_ids`
- `outcome_status`
- `outcome_summary`
- `lesson_ids`
- `provenance`

Allowed `outcome_status` values:

- `unreviewed`
- `needs_review`
- `supported_by_later_evidence`
- `weakened_by_later_evidence`
- `mixed_or_inconclusive`
- `closed`

### ThesisOutcome

A deterministic review of whether a thesis strengthened, weakened, remained unresolved, or was archived.

Fields should include:

- `thesis_outcome_id`
- `thesis_id`
- `title`
- `prior_status`
- `current_status`
- `status_change`
- `supporting_evidence_count_change`
- `conflicting_evidence_count_change`
- `source_count_change`
- `related_decision_ids`
- `related_signal_ids`
- `review_status`
- `provenance`

### SignalQualityScore

A deterministic observation about whether a signal category has been useful, repeated, stale, noisy, or contradictory.

Fields should include:

- `signal_quality_score_id`
- `signal_type`
- `source_artifact`
- `first_seen_at`
- `last_seen_at`
- `evidence_count`
- `source_count`
- `related_theme_ids`
- `related_decision_ids`
- `related_catalyst_ids`
- `confirmation_count`
- `contradiction_count`
- `quality_status`
- `reason`
- `provenance`

Allowed `quality_status` values:

- `insufficient_history`
- `useful`
- `repeated`
- `stale`
- `noisy`
- `contradicted`

### CatalystOutcome

A deterministic follow-up record for catalysts identified by v5.3.

Fields should include:

- `catalyst_outcome_id`
- `catalyst_id`
- `title`
- `category`
- `time_horizon`
- `priority`
- `related_theme_ids`
- `related_entity_ids`
- `related_decision_ids`
- `follow_up_status`
- `later_evidence_ids`
- `outcome_summary`
- `provenance`

Allowed `follow_up_status` values:

- `pending`
- `needs_follow_up`
- `supported_by_later_evidence`
- `weakened_by_later_evidence`
- `mixed_or_inconclusive`
- `expired_without_review`

### PortfolioReviewOutcome

A deterministic review of whether portfolio/watchlist review prompts were handled, repeated, stale, or unresolved.

Fields should include:

- `portfolio_review_outcome_id`
- `symbol`
- `entity_id`
- `review_reason`
- `first_reviewed_at`
- `last_reviewed_at`
- `review_count`
- `related_theme_ids`
- `related_risk_ids`
- `related_catalyst_ids`
- `related_decision_ids`
- `review_status`
- `process_lesson_ids`
- `provenance`

### ProcessLesson

A durable lesson about the investment process.

Fields should include:

- `lesson_id`
- `created_at`
- `lesson_type`
- `title`
- `summary`
- `supporting_decision_outcome_ids`
- `supporting_thesis_outcome_ids`
- `supporting_signal_quality_score_ids`
- `supporting_catalyst_outcome_ids`
- `recommended_process_change`
- `status`
- `provenance`

Allowed `lesson_type` values:

- `recurring_mistake`
- `repeatable_strength`
- `process_gap`
- `review_discipline`
- `evidence_quality`
- `signal_quality`
- `thesis_management`

### LearningLoopSnapshot

A point-in-time snapshot of the learning layer.

Fields should include:

- `snapshot_id`
- `created_at`
- `review_period_start`
- `review_period_end`
- `decision_outcome_count`
- `thesis_outcome_count`
- `signal_quality_score_count`
- `catalyst_outcome_count`
- `portfolio_review_outcome_count`
- `process_lesson_count`
- `open_review_count`
- `closed_review_count`
- `unresolved_count`
- `provenance`

### PerformanceIntelligenceReport

The primary v6.0 user-facing artifact.

Fields should include:

- `report_id`
- `created_at`
- `snapshot_id`
- `summary`
- `decision_quality_summary`
- `thesis_accuracy_summary`
- `signal_quality_summary`
- `catalyst_accuracy_summary`
- `portfolio_review_summary`
- `lessons`
- `improvement_opportunities`
- `recommended_review_prompts`
- `limitations`
- `provenance`

## 7. Performance Review Model

Performance reviews should be deterministic, evidence-backed, and scoped to a review period.

The review model should:

- Count decisions with complete versus incomplete records
- Identify decisions due for review
- Link decisions to later evidence by exact IDs, exact theme references, exact entity references, or explicit decision links
- Compare thesis status changes across snapshots
- Identify catalysts that need follow-up
- Count repeated review prompts
- Surface recurring process lessons

The review model should not:

- Infer profitability without explicit user-supplied data
- Estimate returns
- Rank investments
- Recommend trades
- Generate allocation changes
- Treat missing data as failure

If data is incomplete, the report should say so plainly.

## 8. Decision Outcome Model

Decision outcomes should be grounded in v5.4 Decision Journal records.

v6.0 should consume:

- Decision entries
- Decision review queue
- Decision links
- Decision timeline
- Decision outcomes if already present
- Later evidence and thesis changes

Decision outcomes should be assigned using deterministic rules:

- `unreviewed`: no review evidence is available
- `needs_review`: review date is due or overdue
- `supported_by_later_evidence`: later evidence explicitly supports the same theme, catalyst, entity, or thesis
- `weakened_by_later_evidence`: later evidence explicitly contradicts or weakens the linked theme, catalyst, entity, or thesis
- `mixed_or_inconclusive`: both support and contradiction exist, or evidence is insufficient
- `closed`: a human-authored decision record marks the decision closed

Decision outcomes should preserve the distinction between:

- Process quality
- Evidence quality
- Financial outcome

v6.0 may evaluate process quality from local records. It should not claim financial performance unless explicit performance data is supplied by the user.

## 9. Thesis Accuracy Model

Thesis accuracy should measure whether the institutional thesis record improved, weakened, or remained unresolved over time.

Inputs:

- Thesis Intelligence records
- Theme Lifecycle history
- Evidence Graph relationships
- Contradiction records
- Decision links
- Morning brief and research agenda references

Deterministic review dimensions:

- Evidence count change
- Source diversity change
- Conflict count change
- Thesis status change
- Repeated confirmation count
- Explicit contradiction count
- Review recency

Allowed thesis review statuses:

- `strengthened`
- `weakened`
- `unchanged`
- `contradicted`
- `insufficient_history`
- `archived`

Thesis Accuracy should not mean price accuracy unless explicit price or performance outcome data is supplied and mapped by the user.

## 10. Signal Quality Model

Signal Quality should evaluate whether recurring signals helped the research process.

Signal categories may include:

- Evidence velocity
- Theme lifecycle transitions
- Catalyst priority
- Portfolio/watchlist review prompts
- Executive morning priorities
- Repeated source mentions
- Contradiction frequency
- Decision review prompts

Quality should be deterministic and based on observable local records:

- Frequency
- Recency
- Repetition
- Later confirmation
- Later contradiction
- Decision linkage
- Review linkage

Signal Quality may generate observations such as:

- "This signal repeats often but rarely links to decisions."
- "This catalyst category regularly creates follow-up notes."
- "This theme is frequently mentioned but has unresolved contradictions."
- "This review prompt recurs without closure."

Signal Quality must not generate trading recommendations.

## 11. Catalyst Accuracy Model

Catalyst Accuracy should review whether catalysts identified by v5.3 received follow-up evidence or remained unresolved.

Inputs:

- Catalyst Monitor
- Catalyst history
- Catalyst transitions
- Evidence records
- Theme lifecycle transitions
- Decision Journal links
- Morning Brief references

Deterministic statuses:

- `pending`
- `needs_follow_up`
- `supported_by_later_evidence`
- `weakened_by_later_evidence`
- `mixed_or_inconclusive`
- `expired_without_review`

The model should focus on research follow-through:

- Was the catalyst revisited?
- Did later evidence appear?
- Did related themes strengthen or weaken?
- Was a decision linked to the catalyst?
- Did the catalyst remain unresolved?

It should not decide whether the catalyst was "profitable" unless the user supplies explicit outcome data.

## 12. Portfolio Review Effectiveness

Portfolio Review Effectiveness should evaluate whether portfolio/watchlist review prompts are being handled thoughtfully.

Inputs:

- Portfolio Intelligence
- Portfolio exposures
- Portfolio risks
- Portfolio watchlist
- Decision Journal
- Catalyst Monitor
- Executive Morning Brief

Deterministic observations:

- High-priority reviews generated
- Repeated reviews for the same symbol/entity
- Reviews linked to decisions
- Reviews linked to risks
- Reviews linked to catalysts
- Reviews still unresolved

This is not allocation advice.

It may say:

- "This exposure has repeated high-priority review prompts."
- "This watchlist item has many catalysts but no linked decision record."
- "This risk has appeared repeatedly without a process note."

It must not say:

- "Increase exposure"
- "Reduce exposure"
- "Buy"
- "Sell"
- "Hold"
- "Target price"

## 13. Learning Loop

The Learning Loop converts reviewed outcomes into process lessons.

Learning should be promoted only when:

- Multiple records support the lesson, or
- A human-authored review explicitly marks the lesson as important, or
- A repeated unresolved issue appears across decisions, theses, catalysts, or portfolio reviews

Learning loop stages:

1. Observe decision and research records
2. Link later evidence
3. Classify outcome status deterministically
4. Identify process lesson candidates
5. Preserve provenance
6. Present lessons for human review
7. Promote accepted lessons into future process documentation

The system should distinguish:

- A lesson candidate generated by deterministic review
- A lesson accepted by the human operator
- A process change implemented in future workflows

## 14. Reports and Outputs

Potential outputs:

- `outputs/performance/performance-intelligence.md`
- `outputs/performance/performance-intelligence.json`
- `outputs/performance/decision-outcomes.md`
- `outputs/performance/decision-outcomes.json`
- `outputs/performance/thesis-accuracy.md`
- `outputs/performance/thesis-accuracy.json`
- `outputs/performance/signal-quality.md`
- `outputs/performance/signal-quality.json`
- `outputs/performance/catalyst-accuracy.md`
- `outputs/performance/catalyst-accuracy.json`
- `outputs/performance/portfolio-review-effectiveness.md`
- `outputs/performance/portfolio-review-effectiveness.json`
- `outputs/performance/lessons.md`
- `outputs/performance/lessons.json`
- `outputs/performance/performance-history.json`

The primary report should include:

1. Executive Summary
2. Review Period
3. Decision Quality
4. Thesis Accuracy
5. Signal Quality
6. Catalyst Follow-Through
7. Portfolio Review Effectiveness
8. Process Lessons
9. Recurring Mistakes
10. Repeatable Strengths
11. Open Reviews
12. Improvement Opportunities
13. Provenance
14. Limitations

## 15. CLI Concepts

Potential CLI:

```bash
python -m constellation performance
python -m constellation performance review
python -m constellation performance decisions
python -m constellation performance theses
python -m constellation performance signals
python -m constellation performance catalysts
python -m constellation performance lessons
python -m constellation performance export
```

Command concepts:

- `performance`: build the complete Performance Intelligence package
- `performance review`: generate a review snapshot for the current period
- `performance decisions`: show decision outcomes and review prompts
- `performance theses`: show thesis accuracy and status changes
- `performance signals`: show signal quality observations
- `performance catalysts`: show catalyst follow-up and unresolved catalysts
- `performance lessons`: show process lessons and improvement opportunities
- `performance export`: write Markdown reports

All commands should be deterministic and should consume existing local outputs only.

## 16. Dashboard Integration

The Executive Dashboard should gain a Performance Intelligence section.

Dashboard fields may include:

- Performance report available
- Latest performance review ID
- Review period
- Decision outcomes count
- Decisions needing review
- Thesis outcomes count
- Strengthened theses
- Weakened theses
- Signal quality observations
- Catalyst follow-up items
- Portfolio review prompts unresolved
- Process lessons count
- Top improvement opportunities
- Performance report path

The dashboard should summarize the learning loop without making investment recommendations.

## 17. Workflow Integration

Performance Intelligence should integrate with explicit workflows only.

Potential workflow placement:

```text
Morning Workflow
↓
AI & Markets Executive Morning Brief
↓
Performance Intelligence
↓
Dashboard
```

Potential review workflows:

- Weekly Performance Review
- Monthly Thesis Accuracy Review
- Catalyst Follow-Up Review
- Decision Journal Review
- Portfolio Review Discipline Audit

Workflow execution must remain explicit. v6.0 should not introduce scheduling, autonomous execution, outbound delivery, provider execution, or trading behavior.

## 18. Safety Boundaries

Performance Intelligence must not generate:

- Buy recommendations
- Sell recommendations
- Hold recommendations
- Expected return estimates
- Price targets
- Trade recommendations
- Autonomous allocation changes
- Financial advice
- Client performance reporting
- Unsupported claims about profitability

Performance Intelligence may generate:

- Decision review prompts
- Evidence-backed outcome summaries
- Process lessons
- Signal quality observations
- Thesis review status
- Catalyst follow-up notes
- Portfolio/watchlist review discipline observations
- Improvement opportunities

Safety principles:

- Preserve deterministic behavior
- Preserve complete provenance
- Treat missing data as unknown, not failure
- Separate process review from financial outcome
- Require explicit human review for lessons that change future process
- Never infer market performance without user-supplied data
- Never recommend trades or allocation changes

## 19. Success Criteria

v6.0 is successful if it helps the operator answer:

- Which decisions need review?
- Which decisions were supported, weakened, or inconclusive based on later evidence?
- Which theses strengthened or weakened over the review period?
- Which signals were useful, stale, noisy, or contradictory?
- Which catalysts were followed up versus left unresolved?
- Which portfolio/watchlist reviews are recurring without closure?
- What process lessons are emerging?
- What should change about the research and decision process?

The release should be considered successful when:

- Reports are deterministic and reproducible
- Every observation links back to source artifacts
- Decision Journal and Executive Morning Brief outputs are consumed cleanly
- Later evidence is linked to prior decision records
- Missing information is reported as a limitation
- No financial advice or trading recommendations are generated
- The dashboard can show the current learning state

## 20. Future Extensions

Potential future extensions:

- Human acceptance/rejection workflow for process lessons
- Review-period configuration
- User-supplied performance data ingestion
- Benchmark-aware attribution, only with explicit data
- Forecast calibration for explicitly recorded forecasts
- Decision quality scoring with human-reviewed weights
- Thesis accuracy history across quarters
- Signal quality trend charts
- Catalyst follow-up calendar
- Portfolio review discipline reports by symbol, theme, or risk
- Learning loop promotion into future Morning Brief and Decision Journal templates
- Red-team review of repeated process mistakes
- Optional provider-assisted narrative drafting after deterministic records are complete

Future extensions should preserve the core boundary: Performance Intelligence is a deterministic learning layer, not a trading system or financial advisor.
