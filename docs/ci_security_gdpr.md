# CI, Security, Monitoring, and GDPR Operations

This repository keeps runtime secrets out of source control and uses GitHub Actions
for deterministic quality gates. Configure deploy credentials as GitHub
repository, environment, or organization secrets only. Prefer cloud-provider OIDC
trust over long-lived cloud access keys when a deployment target is added.

## Required GitHub Settings

- Enable Secret Scanning and Push Protection for the repository or organization.
- Keep `OPENAI_API_KEY` and provider credentials in GitHub Secrets or deployment
  environment secrets; never commit `.streamlit/secrets.toml`.
- Use protected environments for production deployments and require review before
  deployment jobs can access production secrets.
- Keep Dependabot enabled for `pip` and `github-actions` ecosystems.

## Monitoring Signals

CI emits `deployment_event` and `alert_condition` JSON lines in
`reports/observability/deployment-events.jsonl`.

Alert conditions are controlled by environment variables:

- `CS_ALERT_P95_LATENCY_MS`
- `CS_ALERT_AVG_COST_USD`
- `CS_ALERT_FAILURE_RATE`

Application model-call logs use the `need_analysis` logger and include only
aggregate metadata: task kind, model, latency, token counts, cache status,
endpoint, optional estimated cost, and status.

## GDPR Controls

- Keep PII reduction enabled before LLM calls for recruiting source material.
- Keep OpenAI `store=false` as the default unless a task explicitly needs
  provider-side persistence.
- Store usage telemetry as aggregates only. Do not log prompts, uploaded content,
  full URLs, candidate names, contact details, raw model responses, credentials,
  tokens, or API keys.
- Review high-risk profiling, automated decisioning, and retention changes before
  release; use a DPIA when processing risk requires it.
