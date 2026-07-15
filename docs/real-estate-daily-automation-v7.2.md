# Real Estate Daily Automation v7.2.4

Real Estate Daily Automation adds the Real Estate operating loop to Constellation's scheduled Morning workflow.

It is deterministic orchestration only. It does not generate value opinions, select comparables, create adjustments, interpret permits, resolve identity conflicts, apply migrations, call providers, use OpenAI, use LLM inference, use embeddings, use web retrieval, add Gmail, or add calendar integration.

## Purpose

The daily loop keeps Real Estate Assignment Intelligence current after local intake artifacts arrive.

It answers:

- Were new assignment artifacts detected?
- Were artifacts imported or skipped as duplicates?
- Which canonical assignments were created or updated?
- Which assignment briefs were rebuilt?
- Are there canonical review items, blocked migrations, or orphan artifacts?
- Should the operator inspect the Real Estate review queue today?

## Daily Flow

`python -m constellation real-estate daily` runs these deterministic stages:

1. Real Estate intake status
2. Real Estate intake import
3. Assignment Consolidation refresh
4. Canonical Assignment refresh
5. Assignment Intelligence build for affected canonical assignments
6. Canonical Operations refresh
7. Executive Dashboard refresh

Morning workflow invokes the same engine through the `Real Estate Daily Automation` workflow step.

## Outputs

Real Estate daily outputs are written under:

```text
outputs/real-estate/daily/
```

Files:

- `latest-real-estate-daily-run.json`
- `real-estate-daily-report.md`
- `real-estate-daily-history.json`
- `real-estate-daily-delta.json`

The JSON run records stage status, counts, warnings, errors, key output paths, and provenance.

The Markdown report summarizes intake activity, canonical assignment activity, assignment builds, review queue status, warnings, errors, limitations, and output references.

## CLI

Run the daily loop:

```bash
python -m constellation real-estate daily
```

Overwrite latest outputs:

```bash
python -m constellation real-estate daily --overwrite
```

Rebuild Assignment Intelligence for all canonical assignments:

```bash
python -m constellation real-estate daily --full-refresh
```

Inspect latest status:

```bash
python -m constellation real-estate daily status
```

List history:

```bash
python -m constellation real-estate daily history
```

Print output paths:

```bash
python -m constellation real-estate daily export
```

Open review files when activity or review items exist:

```bash
python -m constellation real-estate daily --open
```

## Morning Workflow Integration

The Morning workflow now includes:

```text
Real Estate Daily Automation
```

The step runs after research auto-processing and before the rest of the executive intelligence package.

The workflow report includes a Real Estate Daily Automation section with:

- Real Estate daily run ID
- status
- intake candidates
- imported and updated artifacts
- canonical assignments created and updated
- assignment briefs built
- migrated aliases detected
- blocked migrations
- orphan artifacts
- true conflicts
- review item count
- warning count
- error count
- report path
- review queue path

## Batch Launcher

`tools/run_constellation_morning.bat` still runs:

```bash
python -m constellation workflow run Morning
```

On success, it opens the existing AI & Markets and Performance review files as before.

It also opens the Real Estate daily report and canonical review queue only when Real Estate activity, warnings, errors, or review items exist. VS Code launch failures are logged as warnings and do not fail the Morning workflow.

## Dashboard Integration

The Executive Dashboard reads:

```text
outputs/real-estate/daily/latest-real-estate-daily-run.json
```

It reports Real Estate daily availability, run status, activity counts, assignment build counts, review item counts, warning counts, error counts, and the daily report path.

If the daily artifact is missing, dashboard output degrades gracefully and reports the daily run as unavailable.

## Safety Boundaries

Real Estate Daily Automation never:

- applies canonical migration
- deletes alias directories
- deletes source artifacts
- resolves assignment conflicts automatically
- changes valuation conclusions
- selects comparables
- generates adjustments
- interprets permits
- generates USPAP conclusions
- exposes private assignment data in logs

It only refreshes deterministic local state and makes review work visible.

## Limitations

- Review queue items remain operator-reviewed.
- Blocked, orphan, and conflicting assignments remain unresolved.
- Assignment Intelligence is rebuilt only for affected canonical assignments unless `--full-refresh` is used.
- The launcher uses file existence and count summaries to decide whether Real Estate review files should open.
