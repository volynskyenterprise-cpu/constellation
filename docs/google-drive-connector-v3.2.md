# Google Drive Connector v3.2

Constellation v3.2.0 adds an explicit Google Drive connector that stages files into the existing local intake system.

The connector downloads configured Drive files into:

```text
inbox/google-drive/incoming/
```

It does not run intake import, research, graph, thesis, intelligence, providers, or any downstream workflow automatically.

## Purpose

The connector is a source staging layer. It makes Google Drive files available to the deterministic Intake Pipeline while preserving source metadata and avoiding Drive mutation.

## Optional Dependency Installation

Google Drive support is optional:

```bash
pip install -e .[google-drive]
```

Without the optional dependencies, base Constellation behavior continues to work. Drive commands that require API access return:

```text
Google Drive dependencies are not installed. Run: pip install -e .[google-drive]
```

## Google Cloud Setup

At a high level:

1. Create or select a Google Cloud project.
2. Enable the Google Drive API.
3. Create OAuth client credentials for a local/desktop app.
4. Download the credentials JSON locally.
5. Store credentials outside source control, for example:

```text
config/secrets/google-drive-credentials.json
```

Do not commit credentials or OAuth tokens.

## Config Files

Template:

```text
config/google-drive.example.yaml
```

Local config may be copied to:

```text
config/google-drive.yaml
```

Example fields:

```yaml
credentials_path: config/secrets/google-drive-credentials.json
token_path: config/secrets/google-drive-token.json
scopes:
  - https://www.googleapis.com/auth/drive.readonly
download_folder: inbox/google-drive/incoming
allowed_extensions:
  - .md
  - .txt
  - .pdf
```

Source placeholders live in:

```text
config/sources.yaml
```

Drive source entries are disabled by default and use `folder_id: null` until configured locally.

## CLI Usage

Check status without authenticating:

```bash
python -m constellation drive status
```

List files from enabled Drive sources:

```bash
python -m constellation drive list
```

Dry run sync:

```bash
python -m constellation drive sync --dry-run
```

Sync all enabled sources:

```bash
python -m constellation drive sync
```

Sync one source:

```bash
python -m constellation drive sync --source moonshots
```

Then run the local intake pipeline explicitly:

```bash
python -m constellation intake scan
python -m constellation intake import
```

## Supported File Handling

Supported extensions:

- `.md`
- `.txt`
- `.pdf`

Google Docs are exported as Markdown when possible. If Markdown export is unavailable, the connector falls back to plain text export.

Unsupported file types are skipped with a clear manifest reason.

## Manifest

Sync manifests are written to:

```text
outputs/google-drive/google-drive-sync-manifest.json
outputs/google-drive/google-drive-sync-manifest.md
```

The manifest includes:

- sync ID
- created timestamp
- source folder ID or selected source
- downloaded files
- skipped files
- duplicates
- errors
- destination paths
- file metadata

Manifests never include credentials, tokens, or secrets.

## Safety Rules

- No hard-coded credentials.
- No committed credentials or tokens.
- No Google Drive mutation by default.
- No Gmail integration.
- No provider execution.
- No automatic intake import.
- No automatic research, graph, thesis, or intelligence workflow execution.
- All behavior is user-triggered through CLI commands.

## Limitations

- No Gmail connector yet.
- No scheduled sync.
- No folder traversal beyond configured source folders.
- No automatic source registry validation.
- No automatic import into dated research inputs.
- No downstream workflow execution.

## Roadmap

- Gmail Connector.
- Source registry validation.
- Morning Brief orchestration.
- Sync scheduling with explicit user approval.
- Intake review queue.
- Drive file change detection with non-mutating local state.
