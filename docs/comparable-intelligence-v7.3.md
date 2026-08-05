# Comparable Intelligence v7.3.1

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

Scenario-specific inputs are private local files under:

```text
real-estate/assignments/<CANONICAL_ASSIGNMENT_ID>/comparables/scenarios/<SCENARIO_ID>/comparables.yaml
```

Scenario-specific outputs are generated under:

```text
outputs/real-estate/assignments/<CANONICAL_ASSIGNMENT_ID>/comparables/scenarios/<SCENARIO_ID>/
```

`as_is` and `arv` are first-class scenarios. Additional lowercase path-safe identifiers may be supplied explicitly. Subject facts, records, coverage, conflicts, review state, history, deltas, checksums, and reports never cross scenario boundaries.

## Subject Resolution

Each field resolves independently:

1. non-empty private scenario subject value
2. verified canonical assignment value
3. unavailable

Equivalent formatting such as `1452`, `1,452 sqft.`, and `1452 square feet` does not create a conflict. A material difference preserves both values and source paths as a `subject_fact_conflict`; the private value governs only that scenario and the canonical assignment remains unchanged. Effective dates use the same scenario-first rule.

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

Distance aliases `distance_miles`, `distance_from_subject`, and `distance_from_subject_miles` normalize to `distance_from_subject_miles`. Miles, explicit kilometers, and explicit feet are supported. An ambiguous unit remains unavailable; conflicting aliases create a geography review item. No geocoding or provider lookup occurs.

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

`insufficient_data` is reserved for unusable transaction evidence, such as a closed sale without price/date or a record without meaningful property facts. Missing geography, condition, quality, concessions, financing, or listing history remains a transparent limitation. Missing geography caps an otherwise useful sale at `secondary_candidate`. Old sales are retained as `contextual_candidate`; age never causes automatic exclusion.

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
python -m constellation real-estate comparables build ASSIGNMENT_ID --scenario as_is --overwrite
python -m constellation real-estate comparables status ASSIGNMENT_ID --scenario as_is
python -m constellation real-estate comparables list ASSIGNMENT_ID --scenario as_is
python -m constellation real-estate comparables show ASSIGNMENT_ID COMPARABLE_ID --scenario as_is
python -m constellation real-estate comparables coverage ASSIGNMENT_ID --scenario as_is
python -m constellation real-estate comparables conflicts ASSIGNMENT_ID --scenario as_is
python -m constellation real-estate comparables review-queue ASSIGNMENT_ID --scenario as_is
python -m constellation real-estate comparables export ASSIGNMENT_ID --scenario as_is
python -m constellation real-estate comparables select ASSIGNMENT_ID COMPARABLE_ID --scenario as_is --confirm
python -m constellation real-estate comparables exclude ASSIGNMENT_ID COMPARABLE_ID --scenario as_is --reason "Appraiser reviewed." --confirm
python -m constellation real-estate comparables reset-review ASSIGNMENT_ID COMPARABLE_ID --scenario as_is --confirm
python -m constellation real-estate comparables scenarios list ASSIGNMENT_ID
python -m constellation real-estate comparables scenarios show ASSIGNMENT_ID --scenario as_is
python -m constellation real-estate comparables scenarios initialize ASSIGNMENT_ID --scenario as_is --from-legacy --confirm
```

Selection and exclusion commands update local private appraiser review state only.

## Legacy Compatibility

A legacy `comparables/comparables.yaml` remains the `default` scenario when no scenario is supplied. An explicit scenario may use it only as a recorded fallback when no scenario file exists. Commands without `--scenario` fail when multiple scenarios exist and safely resolve when exactly one exists. Initialization copies the legacy source, adds the requested scenario identifier, preserves the original, and writes a checksum receipt; migration is never automatic.

## Outputs

- `comparable-universe.json`
- `comparable-universe.md`
- `comparable-coverage.json`
- `comparable-coverage.md`
- `comparable-conflicts.json`
- `comparable-history.json`
- `comparable-delta.json`
- `comparable-review-queue.md`
- `appraiser-review-state.json`

## Integration

Assignment briefs include a compact Comparable Intelligence summary when outputs exist.

The dashboard includes aggregate Real Estate Comparable Intelligence counts without embedding private property details.

Real Estate Daily Automation fingerprints each scenario independently and rebuilds only changed scenarios while preserving unaffected outputs and appraiser review state.

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
