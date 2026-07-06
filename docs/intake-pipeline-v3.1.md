# Intake Pipeline v3.1

Constellation v3.1.0 adds deterministic local intake orchestration.

This release does not connect to Google Drive, Gmail, OAuth, external APIs, providers, or external services. It only imports files already present in local inbox folders.

## Inbox Structure

Supported incoming folders:

```text
inbox/google-drive/incoming/
inbox/gmail/incoming/
inbox/manual/incoming/
```

Each channel also has `processing`, `processed`, and `failed` folders reserved for future automation. v3.1.0 reads only the `incoming` folders.

## Import Flow

Run a scan:

```bash
python -m constellation intake scan
```

Import available files:

```bash
python -m constellation intake import
```

Check manifest counts:

```bash
python -m constellation intake status
```

Import behavior:

- Creates `research_inputs/YYYY-MM-DD/` if needed.
- Copies files into that dated folder.
- Does not delete originals.
- Preserves filenames.
- Uses SHA-256 hashes for duplicate detection.
- Refuses to overwrite an existing destination filename with different content.
- Records provenance for every imported, duplicate, or failed item.

## Manifest

The intake manifest is written to:

```text
outputs/intake/intake-manifest.json
outputs/intake/intake-manifest.md
```

Each manifest item records:

- source channel
- original path
- destination path
- file hash
- import timestamp
- status
- error, when applicable

Statuses:

- `available`
- `imported`
- `duplicate`
- `error`

## Duplicate Handling

Duplicate detection is hash-based.

If an incoming file has the same SHA-256 hash as an already imported item, the file is recorded as `duplicate` and is not copied again.

If a destination filename already exists with identical content, the item is also recorded as `duplicate`.

If a destination filename already exists with different content, the item is recorded as `error` and the existing destination file is left untouched.

## Roadmap

Future intake work may add:

- Source registry validation for `config/sources.yaml`.
- Google Drive connector support with credentials handled outside the repo.
- Gmail connector support with credentials handled outside the repo.
- Intake manifests with batch IDs and checksums.
- Processing, processed, and failed folder transitions.
- Manual promotion into Research or PKOS workflows.
- Intake retry and failure review workflows.
