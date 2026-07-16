# PKOS Smart Sync Policy Matrix v7.2

This matrix documents the deterministic default policy used by PKOS Smart Sync.

Precedence:

1. Secret block
2. Unresolved Git conflict block
3. Explicit local exclude override
4. Runtime/generated exclusion
5. Temporary/private exclusion
6. Explicit local review override
7. Approved production/governed staging rule
8. Unknown to review

More specific runtime exclusions must win over broad include rules.

| Path pattern | Classification | Action | Precedence | Reason |
| --- | --- | --- | --- | --- |
| `00-system/**` | `production_knowledge` | `stage` | 7 | Durable governed system files. |
| `01-system/**` | `production_knowledge` | `stage` | 7 | Durable system architecture and orchestration docs. |
| `02-commands/**` | `production_knowledge` | `stage` | 7 | Governed command documentation. |
| `00-system/Morning Executive Brief.md` | `unknown` | `review` | 8 | Generated daily brief unless explicitly designated durable. |
| `.obsidian/**` | `configuration` | `review` | 6 | Obsidian local/configuration state should not auto-stage. |
| root daily notes | `unknown` | `review` | 8 | Daily notes require operator review. |
| `03-operations/aoc/00-system/**` | `governed_operations` | `stage` | 7 | Durable AOC operating system records. |
| `03-operations/aoc/01-dashboard/**` | `governed_operations` | `stage` | 7 | Current operational dashboards. |
| `03-operations/aoc/02-assignments/**` | `governed_operations` | `stage` | 7 | Assignment records, excluding temp/backup/lock files. |
| `03-operations/aoc/05-knowledge/packs/**` | `governed_operations` | `stage` | 7 | Durable assignment knowledge packs. |
| `03-operations/aoc/07-automation/intake/approved/**` | `governed_operations` | `stage` | 7 | Approved intake records. |
| `03-operations/aoc/07-automation/intake/incoming/**` | `runtime_artifact` | `exclude` | 3/4 | Incoming intake is transient runtime material. |
| `03-operations/aoc/07-automation/intake/review/**` | `runtime_artifact` | `exclude` | 3/4 | Review intake artifacts are transient unless approved. |
| `03-operations/aoc/07-automation/opportunities/review/**` | `unknown` | `review` | 6 | Opportunity review records require operator judgment. |
| `03-operations/aoc/08-analytics/friction/**` | `governed_operations` | `stage` | 7 | Durable learning/friction records. |
| `03-operations/lodestar/eoc/**` | `governed_operations` | `stage` | 7 | Durable Lodestar EOC records. |
| `03-operations/lodestar/growth/content-intelligence/**` | `unknown` | `review` | 8 | Content-intelligence queues and assets require review unless final/approved metadata exists. |
| `04-thought-leadership/**` | `unknown` | `review` | 8 | Publication material requires operator review. |
| `06-templates/**` | `tooling` | `stage` | 7 | Governed templates. |
| `07-tools/**` | `tooling` | `stage` | 7 | Governed scripts, tests, examples, and docs, subject to secret blocking. |
| `08-research/**` | `draft_research` | `review` | 6 | Research remains draft unless explicitly approved. |
| `**/*.log`, `**/*.lock`, `**/*.tmp`, `**/*.bak` | runtime/temp | `exclude` | 4/5 | Runtime or temporary material. |
| Secret-field references without literal values | unchanged | unchanged | diagnostic only | Attribute reads, config lookups, credential-file loader calls, and placeholder fields are reported as safe references. |
| Secret-like literal assignments or mapping values | `private_or_secret` | `block` | 1 | Hardcoded credential material remains blocked even inside governed tooling paths. |
| Secret-risk path/content | `private_or_secret` | `block` | 1 | Secrets can never be staged by policy override. |

Smart Sync reports subtree summaries, top review reasons, and top exclusion reasons so daily previews remain reviewable.
