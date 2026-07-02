# Validation And Health Checks v1.1

Constellation v1.1.0 adds deterministic preflight checks for the organization layer and runtime scaffold.

## Crew Validation

Run:

```bash
python -m constellation validate crew
```

The crew validator checks:

- Every founding crew folder exists.
- Every crew folder contains:
  - `profile.md`
  - `responsibilities.md`
  - `authority.md`
  - `communication.md`
  - `methodologies.md`
  - `memory.md`
  - `prompts.md`
- Every `agents/*.yaml` agent maps to a crew folder using the standard `agent_id -> crew-role` conversion.
- No orphan crew folders exist unless explicitly allowed.

Allow orphan folders for planned future roles:

```bash
python -m constellation validate crew --allow-orphans
```

Successful output:

```text
crew: ok
checked: 73
```

Failure output:

```text
crew: failed
error: crew_file_missing: Crew role ceo missing required file: profile.md path=C:\path\to\constellation\crew\ceo\profile.md
```

Validation failure exits with a non-zero status code.

## System Health

Run:

```bash
python -m constellation health
```

The health checker verifies:

- `constitution/` exists.
- Required config files exist.
- Agents load.
- Workflows load.
- Crew validation passes.
- Providers load.
- Runtime directories exist or can be created.
- Provider execution remains disabled by default, unless explicitly enabled.

Successful output:

```text
health: ok
ok: constitution: Constitution folder exists.
ok: config: Required config files exist.
ok: agents: Loaded 8 agents.
ok: workflows: Loaded 8 workflows.
ok: crew: Crew validation passed.
ok: providers: Loaded 8 providers.
ok: runtime_directories: Runtime directories exist or were created.
ok: provider_execution_default: Provider execution is disabled by default.
```

If provider execution is explicitly enabled, health reports a warning but does not fail:

```text
warn: provider_execution_default: Provider execution is explicitly enabled.
```

Any failed check makes the command exit non-zero.
