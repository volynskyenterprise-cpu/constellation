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

Policy precedence in v7.2.6 is deterministic:

1. secret-risk and unresolved conflict blocking
2. explicit exclude overrides
3. runtime and generated artifact exclusions
4. highest-priority review or stage override
5. built-in path and content rules
6. unknown-file review fallback

More-specific overrides win ties at the same priority. Broad override patterns that affect many files are reported as broad override warnings in the preview diagnostics.

The detailed classification matrix is documented in `pkos-smart-sync-policy-matrix-v7.2.md`.

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
python -m constellation pkos sync preview --explain 07-tools/aoc_email/gmail_client.py
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

The v7.2.7 detector distinguishes secret-field references from secret values. Safe examples include `creds.refresh_token`, `config.get("client_secret")`, `settings["api_key"]`, `Credentials.from_authorized_user_file(...)`, and `InstalledAppFlow.from_client_secrets_file(...)` when no literal credential value is present.

Blocked examples include hardcoded assignments such as `refresh_token = "actual-value"`, mapping values such as `{"client_secret": "actual-value"}`, environment fallbacks with literal values, private key material, credential blobs, known token prefixes, and secret-risk paths. Placeholders such as `REDACTED`, `YOUR_API_KEY`, `CHANGE_ME`, `example`, `dummy`, `test-token`, an empty string, or `None` are not treated as real credentials.

The verified OAuth false positive was an attribute read: `creds.refresh_token`. Smart Sync now reports that as `secret-reference:attribute-read` rather than blocking it.

`preview --explain PATH` reports the path, classification, action, matched rules, safe-reference rules, blocked secret rules if present, precedence order, reason, override source, and final decision without exposing file contents. Blocked diagnostics redact values and report only rule IDs such as `secret-literal:assignment:line-12` or `secret-content:private-key:line-1`.

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
