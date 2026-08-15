# Adjustment Intelligence v7.4

Adjustment Intelligence is the scenario-specific evidence layer between Comparable Intelligence and an appraiser's adjustment decision. It answers what explicit market evidence supports possible adjustments; it never decides what adjustment must be used.

## Architecture

Canonical Assignment → Scenario Subject Resolution → Comparable Intelligence → Adjustment Intelligence → Appraiser Decision → Deterministic Grid Application → Appraiser Reconciliation.

The first four stages organize facts and evidence. Selection of a rate, comparable weighting, and reconciliation remain professional judgments.

## Scenario model and privacy

Each `as_is`, `arv`, or safe custom scenario has independent evidence, decisions, calculations, conflicts, history, fingerprints, and reports.

Private input:

`real-estate/assignments/<ID>/adjustments/scenarios/<SCENARIO>/adjustment-evidence.yaml`

Private decision state:

`real-estate/assignments/<ID>/adjustments/scenarios/<SCENARIO>/adjustment-decisions.json`

Generated reports are written beneath:

`outputs/real-estate/assignments/<ID>/adjustments/scenarios/<SCENARIO>/`

The engine does not merge as-is and ARV evidence or decisions. Public examples are fictional. No web, MLS, provider, geocoding, or LLM access occurs.

## Factors and factual differences

The initial factors are market conditions, GLA, lot size, bedrooms, bathrooms, condition, quality, garage, parking, pool, spa, view, location, design/style, effective age, accessory units, unit count, and concessions. Supported bases are `per_unit`, `lump_sum`, `percentage`, `ordinal_step`, `time_percentage`, and `informational_only`.

Quantitative grid differences follow one convention:

`difference_for_adjustment = subject_value - comparable_value`

- Comparable inferior to subject: positive difference and positive application.
- Comparable superior to subject: negative difference and negative application.

A difference is a factual comparison, not an adjustment.

## Evidence schema and methods

Evidence is grouped by factor under `adjustment_evidence`. Every record retains its ID, method, classification, verification status, source paths, arithmetic, limitations, and unresolved differences.

Supported methods:

- `matched_pair`
- `grouped_comparison`
- `repeat_sale`
- `sensitivity_analysis`
- `market_extraction`
- `appraiser_entered_support`
- `external_study`
- `informational_reference`

Evidence classifications are `independent_market_evidence`, `appraiser_decision_reference`, `derived_appraiser_decision_reference`, `contextual_reference`, and `unsupported`.

An optional `evidence_sources` list may name local CSV, YAML, or JSON files relative to the private scenario directory. Only explicitly named structured files are read. Imported rows retain their configured path, checksum, record ID, classification, and verification status. The adapter does not scan workfiles, parse PDFs, use OCR, or access external systems. Appraisal-grid source types remain decision references and cannot become independent support through import.

### Structured source-grid metadata

An appraisal decision reference may include structured facts describing the source grid itself:

```yaml
source_rate_consistency:
  absolute_tolerance: 1.0
  relative_tolerance_percent: 1.0

adjustment_evidence:
  gross_living_area:
    evidence:
      - evidence_id: fictional-grid-reference
        method: informational_reference
        source_type: appraisal_grid_export
        source_path: sources/fictional-grid.pdf
        source_page: 18
        source_location: Supplemental grid, living area row
        source_checksum: fictional-checksum
        verification_status: source_reported
        evidence_classification: appraiser_decision_reference
        valuation_scenario: as_is
        source_grid:
          valuation_scenario: as_is
          subject:
            gross_living_area: 2100
          comparables:
            - source_comparable_id: fictional-supplemental-comp-1
              gross_living_area: 1700
              displayed_adjustment_amount: 130000
          displayed_adjustment:
            factor: gross_living_area
            explicit_rate: 150
            unit: dollars_per_square_foot
```

Source-grid subject fields are optional. Supported deterministic comparisons include GLA, property type, lot size, bedrooms, bathrooms, condition, quality, garage, parking, pool, accessory-unit presence, and unit count. Missing facts are incomplete rather than contradictory. Raw source fields, normalized values, page/grid location, checksum, and verification provenance remain visible.

The v7.4.0 top-level grid fields (`grid_subject_gross_living_area`, `grid_entries`, and `explicit_displayed_rate`) remain readable through a compatibility adapter. Inputs are not rewritten.

### Decision-reference scenario consistency

Explicit source-grid subject facts are compared with the resolved subject for the requested Adjustment Intelligence scenario. A material normalized difference creates one high-severity `scenario_mismatch` conflict and review item. The conflict preserves both values and source provenance.

The evidence remains attached to its declared scenario. Constellation does not decide that the source was intended for ARV, move evidence automatically, correct appraisal data, or import supplemental comparables. A source comparable set is reported as `aligned`, `partial_overlap`, `distinct_source_set`, or `unavailable`. A distinct supplemental set is administrative information, not automatically a conflict. Only an explicit claimed link to a governed comparable that fails to resolve creates a review item.

### Source-grid arithmetic diagnostics

When the source supplies a subject value, comparable values, displayed adjustment amounts, and an explicit rate, each row receives deterministic arithmetic:

`difference = source-grid subject value - source-grid comparable value`

`derived diagnostic rate = displayed adjustment amount / difference`

Row calculations retain signs, raw values, amount variance from the explicit rate, and zero-denominator limitations. Multiple derived rates receive count, minimum, maximum, median, and mutual-consistency status. Derived rates are classified only as `derived_appraiser_decision_reference_diagnostic`; they never enter market indications or evidence ranges.

The default consistency tolerance is the greater of $1.00 in rate units or 1.0 percent of the explicit/reference rate. Exact matches and harmless rounding remain conflict-free. A material explicit-versus-derived disagreement, or materially inconsistent derived rows, creates one high-severity `source_internal_inconsistency` conflict with all calculations attached. No rate is corrected or selected.

Decision-reference usability is administrative: `clean_reference`, `review_required`, `scenario_inconsistent`, `internally_inconsistent`, or `scenario_and_source_inconsistent`. It is not an appraiser adjustment decision.

## Matched-pair methodology

A possible pair is never promoted automatically. A paired-sale indication enters the governed evidence set only when the private input marks it governed or appraiser verified. The engine divides the explicit price difference by the explicit focal-property difference, retains raw arithmetic, and reports unresolved secondary differences. A zero denominator is rejected. The result is a raw indication and does not establish causality.

## Grouped comparisons

Governed groups retain their definitions, counts, source provenance, descriptive statistics, observed median difference, and uncontrolled differences. An observed group difference is not automatically an adjustment.

## Indications and aggregation

Compatible indications are summarized without selection using count, minimum, maximum, median, mean, explicitly weighted mean when weights exist, population standard deviation, and interquartile range. Outliers remain visible. Mixed units, conflicting directions, high dispersion, thin samples, and scenario mismatches remain reviewable.

## Appraiser decisions

Decision statuses are `unreviewed`, `selected`, `deferred`, `no_adjustment`, and `rejected`. Only an explicit confirmed command may set `selected` or `no_adjustment`. A rationale is required and decision history is preserved independently by scenario.

Selected rates outside the evidence range remain permitted after explicit confirmation but create an open review item.

## Deterministic application and rounding

Only an appraiser-selected rate can be applied. Reports use “Calculated application using appraiser-selected rate,” never “recommended adjustment.” Raw arithmetic is preserved and a separately rounded display amount is generated. Default display rounding is the nearest $100; configuration may change the increment.

Percentage calculations use the explicit selected percentage and comparable sale price. Market-condition calculations use simple, non-compounded elapsed months based on actual days divided by a 365.2425-day year. The system never chooses the percentage.

## Sensitivity and gross/net diagnostics

Candidate sensitivity rates are evaluated side by side. Effects, adjusted-price spread, gross adjustment percentage, and net adjustment percentage are mathematical diagnostics only. The engine identifies no winner and does not reject a comparable based on a threshold.

## Circular-evidence safety

An adjustment copied from the subject appraisal grid is classified as `appraiser_decision_reference`. It cannot serve as independent evidence supporting itself. Independent paired-sale or market evidence remains separate and traceable.

Scenario or arithmetic inconsistency never changes that classification, increases the independent indication count, establishes a support range, approves a matched pair, selects a decision, or applies an adjustment.

## Conflicts, coverage, and review queue

Conflicts include incompatible units, conflicting direction, textual or structured source-grid scenario mismatch, source internal inconsistency, unsupported pair designation, unresolved differences, missing sources, and a selected rate outside the evidence range.

Coverage per factor is `strong`, `adequate`, `limited`, `absent`, `conflicted`, or `unavailable`. Coverage reports factual differences, evidence count, usable indications, decision status, application status, and limitations; it never selects a rate.

Review items cover differences without evidence, missing provenance, unresolved pairs, thin samples, high dispersion, decision-reference scenario mismatch, source internal inconsistency, zero source-grid denominators, unresolved claimed comparable links, unreviewed decisions, missing rationale, circular references, and application anomalies. Ordinary missing optional source-grid facts are not critical.

## CLI

```text
python -m constellation real-estate adjustments create-template ASSIGNMENT_ID --scenario as_is
python -m constellation real-estate adjustments build ASSIGNMENT_ID --scenario as_is --overwrite
python -m constellation real-estate adjustments status ASSIGNMENT_ID --scenario as_is
python -m constellation real-estate adjustments factors ASSIGNMENT_ID --scenario as_is
python -m constellation real-estate adjustments evidence ASSIGNMENT_ID --scenario as_is
python -m constellation real-estate adjustments indications ASSIGNMENT_ID --scenario as_is
python -m constellation real-estate adjustments conflicts ASSIGNMENT_ID --scenario as_is
python -m constellation real-estate adjustments review-queue ASSIGNMENT_ID --scenario as_is
python -m constellation real-estate adjustments export ASSIGNMENT_ID --scenario as_is
```

Appraiser-controlled decisions require confirmation:

```text
python -m constellation real-estate adjustments select ASSIGNMENT_ID gross_living_area --scenario as_is --value 300 --unit dollars_per_square_foot --reason "Evidence reviewed." --confirm
python -m constellation real-estate adjustments no-adjustment ASSIGNMENT_ID pool --scenario as_is --reason "Evidence reviewed." --confirm
python -m constellation real-estate adjustments reset-decision ASSIGNMENT_ID pool --scenario as_is --confirm
```

## Outputs

The scenario output contains `adjustment-analysis`, `adjustment-support`, conflicts, review queue, decisions, history, and delta records. Assignment Intelligence summarizes scenarios separately. Dashboard output exposes administrative counts only. Real Estate Daily fingerprints private evidence and decision state, rebuilds only changed scenarios, preserves decisions, and reports changed indications and opened/resolved conflicts.

## Professional boundaries and limitations

Adjustment Intelligence does not determine legal unit count, ADU legality, permitting, zoning compliance, construction feasibility, completion, GLA inclusion, highest and best use, USPAP compliance, final adjustment rates, final comparable selection, reconciliation, ARV, or market value. It calculates evidence, exposes assumptions, preserves provenance, shows sensitivity, and requires appraiser judgment.
