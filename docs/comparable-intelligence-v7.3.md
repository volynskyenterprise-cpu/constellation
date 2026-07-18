# Comparable Intelligence v7.3

Comparable Intelligence is the deterministic comparable-sale evidence layer for Constellation Real Estate Intelligence.

It answers:

> What market evidence should the appraiser evaluate, and how well does that evidence cover the subject?

It does not select final comparables, generate value opinions, develop adjustments, reconcile indicators, interpret permits, or create USPAP conclusions.

## Architecture

Comparable Intelligence sits downstream of canonical assignment infrastructure:

```text
PKOS/AOC Intake
  -> Assignment Consolidation
  -> Canonical Assignment
  -> Assignment Intelligence
  -> Comparable Intelligence
  -> Appraiser Review and Selection
```

Inputs are private local files under:

```text
real-estate/assignments/<CANONICAL_ASSIGNMENT_ID>/comparables/
```

Outputs are generated under:

```text
outputs/real-estate/assignments/<CANONICAL_ASSIGNMENT_ID>/comparables/
```

## Schemas

Supported local input formats:

- structured YAML
- structured JSON
- CSV
- appraiser-entered comparable records
- locally supplied MLS or public-record exports

Core comparable fields include identity, transaction, property, geography, evidence/provenance, and appraiser review state.

Unknown CSV or JSON columns are retained in `source_fields`. Malformed files are reported as source errors without rewriting the source.

## Normalization

Normalization is deterministic:

- HTML entities and non-breaking spaces in addresses
- street abbreviations and unit markers
- currency and comma-formatted numeric values
- dates in explicit U.S. and ISO formats
- status synonyms such as `sold` -> `closed_sale`
- boolean values
- square-foot and distance units
- condition and quality codes such as `C3` and `Q4`

Original source values remain in source metadata.

## Duplicate Rules

Potential duplicates are identified by deterministic keys:

1. listing ID
2. parcel number plus sale date
3. normalized address plus sale date
4. normalized address plus transaction price
5. exact source-record ID

Duplicates are flagged for review. Records are never deleted.

## Assessments

Comparable assessment is component based:

- property type
- geography
- recency
- gross living area
- lot size
- bed/bath count
- age
- quality
- condition
- amenities
- data completeness

Assessment values are:

- `strong_match`
- `acceptable_match`
- `meaningful_difference`
- `major_difference`
- `unavailable`
- `review_required`

These classify differences only. They do not imply adjustments.

## Candidate Tiers

Candidate tiers are evidence-navigation categories:

- `primary_candidate`
- `secondary_candidate`
- `contextual_candidate`
- `insufficient_data`
- `potential_duplicate`
- `review_required`
- `appraiser_selected`
- `appraiser_excluded`

The engine never assigns `appraiser_selected` or `appraiser_excluded` automatically.

## Coverage and Bracketing

Coverage is reported for property type, location, sale date, GLA, lot size, bed/bath, age, quality, condition, amenities, and special features.

Coverage levels:

- `excellent`
- `adequate`
- `limited`
- `absent`
- `unavailable`

Bracketing is factual only: below, above, matching, fully bracketed, partially bracketed, not bracketed, or unavailable.

## Conflicts

Comparable conflicts preserve all source values. Conflicts include sale price, sale date, GLA, lot size, status, listing ID, APN, condition, and quality.

Configured source priority may influence presentation but does not silently resolve conflicts.

## CLI

```bash
python -m constellation real-estate comparables build ASSIGNMENT_ID --overwrite
python -m constellation real-estate comparables status ASSIGNMENT_ID
python -m constellation real-estate comparables list ASSIGNMENT_ID
python -m constellation real-estate comparables show ASSIGNMENT_ID COMPARABLE_ID
python -m constellation real-estate comparables coverage ASSIGNMENT_ID
python -m constellation real-estate comparables conflicts ASSIGNMENT_ID
python -m constellation real-estate comparables review-queue ASSIGNMENT_ID
python -m constellation real-estate comparables export ASSIGNMENT_ID
python -m constellation real-estate comparables create-template ASSIGNMENT_ID
python -m constellation real-estate comparables select ASSIGNMENT_ID COMPARABLE_ID --confirm
python -m constellation real-estate comparables exclude ASSIGNMENT_ID COMPARABLE_ID --reason "Appraiser reviewed." --confirm
python -m constellation real-estate comparables reset-review ASSIGNMENT_ID COMPARABLE_ID
```

Selection and exclusion commands update local private appraiser review state only.

## Outputs

- `comparable-universe.json`
- `comparable-universe.md`
- `comparable-coverage.json`
- `comparable-coverage.md`
- `comparable-conflicts.json`
- `comparable-history.json`
- `comparable-delta.json`
- `comparable-review-queue.md`

## Integration

Assignment briefs include a compact Comparable Intelligence summary when outputs exist.

The dashboard includes aggregate Real Estate Comparable Intelligence counts without embedding private property details.

Real Estate Daily Automation detects changed comparable inputs and rebuilds only affected assignments.

## Privacy

Comparable inputs, source exports, private review state, and generated comparable outputs are local and ignored by Git.

Public examples are fictional.

## Safety

Comparable Intelligence must never:

- generate a value opinion
- select final comparables automatically
- exclude a sale as an appraisal judgment
- generate adjustments
- claim market support not present in source data
- use LLMs, embeddings, semantic similarity, providers, web retrieval, Gmail, or calendar integrations

It may:

- organize comparable evidence
- classify factual similarities and differences
- report coverage and bracketing
- preserve conflicts
- generate review questions
- record appraiser-controlled review state

## Limitations

This release is local-file based. Live MLS, public-record, and connector-based imports are future optional adapters, not core requirements.
