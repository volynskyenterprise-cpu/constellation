# Research Organization v2.0

Constellation v2.0.0 introduces the first professional capability built on the kernel: the Research Organization.

It converts a markdown or text source document into a structured, evidence-aware executive research report through the existing crew doctrine, prompt assembly engine, provider abstraction, structured artifacts, and human approval gates.

## What It Does

The institutional research workflow coordinates:

- CEO
- Research Lead
- Knowledge Engineer
- QA Lead
- Documentation Engineer

The workflow produces:

- `research_objective_brief`
- `evidence_table`
- `knowledge_implications`
- `validation_challenge`
- `executive_research_report`

The workflow pauses at a human approval gate after the executive research report is produced.

## Add A Research Input

Place `.md` or `.txt` files in:

```text
research_inputs/
```

Example:

```bash
mkdir -p research_inputs
printf "# Market Brief\n\nObserved fact: customer teams need faster evidence review.\n" > research_inputs/sample-brief.md
```

## Run The Research Workflow

```bash
python -m constellation research run research_inputs/sample-brief.md
```

Provider execution follows the existing provider configuration:

- Disabled providers produce placeholder workflow artifacts.
- EchoProvider produces deterministic structured artifacts when enabled.
- OpenAI remains disabled unless explicitly configured.

## Enable EchoProvider For Deterministic Execution

In `config/providers.yaml`:

```yaml
routing:
  invoke_provider_during_kernel_run: true
  default_provider: echo
  allow_fallback: false
```

Then run:

```bash
python -m constellation research run research_inputs/sample-brief.md
python -m constellation artifacts list RUN_ID
```

## Export The Report

```bash
python -m constellation research export RUN_ID
```

The report is written to:

```text
outputs/research/RUN_ID-report.md
```

The export includes:

- Title
- Executive summary
- Source document reference
- Evidence table
- Knowledge implications
- QA challenge
- Final recommendations
- Risks and uncertainty
- Open questions
- Next steps
- Approval status

## Approval

Research workflows still require explicit human approval:

```bash
python -m constellation approvals list
python -m constellation approvals approve APPROVAL_ID
python -m constellation resume RUN_ID
```

## Limitations

- No PDF parsing yet.
- No web retrieval yet.
- No real citation extraction yet.
- Provider execution is disabled by default.
- EchoProvider is deterministic and does not perform real research reasoning.
- OpenAI can be enabled manually, but live API calls may cost money.
