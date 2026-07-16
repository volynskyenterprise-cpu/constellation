# PKOS Smart Sync v7.2

PKOS Smart Sync replaces broad end-of-day `git add .` synchronization with a governed, preview-first workflow.

The operating rule is:

```text
Preview first
Stage selectively
Commit only governed knowledge
Never publish uncertainty automatically
```

## Architecture

Constellation owns the Smart Sync policy, deterministic classification, preview reports, approval records, staged manifests, and audit history.

The PKOS vault owns the local launcher and repository-specific configuration.

Smart Sync does not own PKOS content. It only decides whether changed files are safe to stage, require review, should be excluded, or must be blocked.

## Classification Policy

Allowed classifications:

- `production_knowledge`
- `governed_operations`
- `approved_research`
- `draft_research`
- `generated_output`
- `runtime_artifact`
- `temporary_file`
- `private_or_secret`
- `configuration`
- `tooling`
- `unknown`

Allowed actions:

- `stage`
- `exclude`
- `review`
- `block`

Default behavior:

- Production knowledge, governed operations, and tooling are stage candidates.
- Draft research, approved research, configuration, and unknown files require review.
- Generated output, runtime artifacts, and temporary files are excluded.
- Private or secret-risk files are blocked and can never be staged by overrides.

## Approval Workflow

1. Run preview.
2. Review `outputs/pkos-smart-sync/latest-preview.md`.
3. Stage approved files.
4. Commit only if the staged manifest matches the approved preview.
5. Push only after a Smart Sync commit exists.

`--yes` cannot bypass lint failures, secret detection, blocked files, repository safety failures, or staged-manifest mismatch.

## CLI

```powershell
python -m constellation pkos sync status
python -m constellation pkos sync preview --export
python -m constellation pkos sync stage --approved-only
python -m constellation pkos sync commit
python -m constellation pkos sync push
python -m constellation pkos sync run --yes --no-push
python -m constellation pkos sync history
python -m constellation pkos sync show RUN_ID
```

Preview is read-only. Stage does not commit. Commit does not push. Push never force pushes.

## Launcher

The PKOS vault launcher remains:

```powershell
.\07-tools\sync-pkos.ps1
```

The launcher invokes Constellation Smart Sync preview, opens the preview Markdown in VS Code when available, asks before staging, asks before committing, and asks before pushing.

Non-interactive mode previews only by default.

## Outputs

Smart Sync writes local Constellation audit artifacts under:

```text
outputs/pkos-smart-sync/
  latest-preview.json
  latest-preview.md
  latest-run.json
  smart-sync-history.json
  smart-sync-report.md
  staged-manifest.json
  excluded-manifest.json
  review-manifest.json
  blocked-manifest.json
```

These outputs are local runtime artifacts and are ignored by Git.

## Secret Handling

Smart Sync uses deterministic local checks for secret-risk paths and content patterns. It reports only the path, risk category, blocked status, and triggered rule. It does not print secret values and never stages secret-risk files.

## Staging Safety

Smart Sync stages explicit approved paths only. It never uses `git add .` or `git add -A`.

Deleted files require manual review by default.

Pre-existing staged changes are reported separately and block automatic staging until the operator reviews the index.

## Commit And Push Safety

Commit requires:

- an approval record
- a staged manifest matching the approved preview
- a valid commit policy

Push requires:

- an existing Smart Sync commit
- the configured branch and remote
- no force push

## No-Change Behavior

If no files are approved for staging, Smart Sync records a no-change run and does not create a duplicate commit.

## Limitations

Smart Sync does not decide whether research is substantively true. It classifies file paths and local safety signals deterministically. Unknown and draft material requires operator review.

## Future Scheduling

A future scheduled workflow may generate the evening preview automatically. Commit and push remain approval-gated.
