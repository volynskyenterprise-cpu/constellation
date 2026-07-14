# Constellation Real Estate Intelligence v7.1 - Assignment Auto-Ingestion

Assignment Auto-Ingestion removes manual setup friction from Assignment Intelligence.

It converts structured local intake artifacts into private assignment case files, builds Assignment Intelligence automatically, and refreshes the dashboard. It organizes intake and evidence. It does not automate valuation judgment.

## Configuration

Committed example:

```text
config/real-estate-intake.example.yaml
```

Local private configs:

```text
config/real-estate-intake.yaml
config/real-estate-intake.local.yaml
```

Local configs are ignored by Git.

Example:

```yaml
real_estate_intake:
  enabled: true
  assignment_root: real-estate/assignments
  source_mode: reference
  sources:
    - id: pkos_aoc_intake
      enabled: true
      source_type: local_directory
      root_path: C:/LOCAL/PATH/TO/PKOS
      include_patterns:
        - 03-operations/aoc/07-automation/intake/incoming/*.json
        - 03-operations/aoc/07-automation/intake/review/*.json
        - 03-operations/aoc/07-automation/intake/review/*.md
        - 03-operations/aoc/02-assignments/*.md
      archive_processed: false
```

Use placeholder paths in committed files. Put real vault paths only in local ignored config.

## Supported Sources

Supported file types:

- `.json`
- `.yaml`
- `.yml`
- `.md`
- `.txt`

JSON and YAML are the primary supported modes. Markdown and text support deterministic front matter or exact labeled fields only.

## Field Mappings

Common aliases include:

- Subject address: `subject_address`, `property_address`, `address`
- Postal code: `postal_code`, `zip`, `zipcode`
- Client: `client_name`, `client`
- Due date: `due_date`, `delivery_date`, `report_due`
- Assignment type: `assignment_type`, `order_type`, `service_type`
- Attachments: `source_files`, `attachments`, `attachment_paths`

Lender and AMC fields are preserved as role notes instead of being silently collapsed into client name.

## Assignment ID Rules

Assignment IDs are deterministic.

Priority:

1. `assignment_id`
2. `order_id`
3. `loan_number`
4. Sanitized subject address plus date
5. Stable hash of source path and structured subject fields

IDs are lowercased, hyphen-separated, and stripped of unsafe filename characters.

## Source Modes

`source_mode: reference`

- Stores absolute local source paths in the private assignment file.
- Does not copy source documents.
- Default mode.

`source_mode: copy`

- Copies intake/source files into the private assignment `sources/` directory.
- Preserves original path and checksum in intake provenance.
- Refuses to copy files outside configured source roots.

## Merge Behavior

If an assignment already exists:

- Existing non-empty fields are preserved.
- Matching incoming values are treated as consistent.
- Different incoming values create structured conflict facts.
- New source paths are merged.
- No unrestricted overwrite is performed in this MVP.

## Duplicate Behavior

Duplicate protection uses:

- Source path
- Source checksum
- Detected assignment ID

Repeated imports of the same unchanged intake record are skipped.

## CLI

```bash
python -m constellation real-estate intake status
python -m constellation real-estate intake scan
python -m constellation real-estate intake import
python -m constellation real-estate intake import --source SOURCE_ID
python -m constellation real-estate intake import --file PATH
python -m constellation real-estate intake import --file PATH --open
python -m constellation real-estate intake history
python -m constellation real-estate intake show INTAKE_ID
```

`--open` attempts to open the generated assignment brief in VS Code. Failure to open VS Code does not fail intake.

## Outputs

```text
outputs/real-estate/intake/
  intake-manifest.json
  intake-manifest.md
  intake-history.json
  latest-intake.json
  intake-errors.json
```

Each record includes intake ID, source ID, source path, checksum, detected assignment ID, import status, assignment path, assignment brief path, mapped fields, unmapped fields, conflicts, linked sources, import timestamp, and provenance.

## Zero-Friction Flow

```text
Structured local intake artifact
  -> Assignment candidate detected
  -> Private assignment directory created or merged
  -> assignment.yaml populated from explicit fields
  -> Sources referenced or copied
  -> Assignment Intelligence built automatically
  -> Assignment brief generated
  -> Dashboard refreshed
```

## Safety

Assignment Auto-Ingestion must never:

- Generate value opinions.
- Select comparables.
- Generate adjustments.
- Interpret permits.
- Make USPAP conclusions.
- Expose private client data in committed files.

It only organizes explicit local structured intake and preserves provenance for human review.
