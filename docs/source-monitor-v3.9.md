# Source Monitor v3.9

Constellation v3.9 adds deterministic Source Monitoring.

Source Monitoring tracks configured and local intelligence sources over time and reports what changed between monitoring runs. It is local, explicit, and read-only.

## Commands

```bash
python -m constellation monitor
python -m constellation monitor --overwrite
python -m constellation monitor status
python -m constellation monitor history
python -m constellation monitor export
```

## Outputs

```text
outputs/source-monitor/source-monitor.json
outputs/source-monitor/source-monitor.md
outputs/source-monitor/source-history.json
outputs/source-monitor/latest-monitor.json
```

## Sources Monitored

Initial support includes:

- Google Drive source definitions from `config/sources.yaml`
- Local intake folders
- Local evidence files
- Local thesis files
- Local configuration files

Google Drive monitoring is configuration-only in v3.9. It does not call Google APIs or download remote content.

## Change Detection

Each source snapshot records:

- source ID
- source type
- timestamp
- item count
- newest modified timestamp
- deterministic fingerprint
- previous fingerprint
- status

Statuses are:

- `UNCHANGED`
- `NEW ITEMS`
- `REMOVED ITEMS`
- `UPDATED ITEMS`
- `FAILED`
- `UNKNOWN`

## Integrations

Daily Pipeline now runs Source Monitoring first.

Executive Dashboard now includes a Source Monitoring Summary with:

- sources checked
- sources changed
- new items
- removed items
- updated items
- failures
- recommended refreshes

## Safety

Source Monitoring never:

- calls providers
- invokes LLMs
- downloads web pages
- performs semantic comparisons
- modifies source data
- deletes files
- schedules itself
- executes workflows automatically
