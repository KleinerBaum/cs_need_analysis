# Dependency Upgrade Lane

This lane keeps OpenAI and Streamlit dependency freshness deliberate. Do not
upgrade runtime dependencies as part of unrelated product or behavior changes.

## Current Dependency Contract

Runtime ranges and constraints:

| Package | Runtime range | CI constraint | Notes |
|---|---|---|---|
| `openai` | `>=2.30.0,<3.0.0` | `==2.30.0` | OpenAI request compatibility is guarded by `model_capabilities.py`, `llm_client.py`, `settings_openai.py`, and `scripts/openai_smoke_test.py`. |
| `streamlit` | `>=1.56` | none | Streamlit compatibility is guarded by AppTest smoke tests in `tests/apptest/`. |

CI installs runtime dependencies with `pip install -r requirements.txt -c
constraints.txt`. The constraint file is the tested lane for critical SDK
dependencies; do not change it without running the checks below.

## Monthly Check

1. Inspect candidate versions without editing pins:

   ```bash
   python -m pip install --upgrade pip
   python -m pip index versions openai
   python -m pip index versions streamlit
   ```

2. Read OpenAI SDK and Streamlit release notes for breaking changes affecting:
   structured outputs, `responses.parse`, `chat.completions.parse`, request
   kwargs, timeout/client construction, Streamlit session state, query params,
   and `streamlit.testing.v1.AppTest`.

3. If an OpenAI SDK upgrade is proposed, update only dependency metadata first,
   then verify that task routing, capability gates, smoke modes, fallback
   behavior, response caching, retries, error mapping, usage metadata, and
   settings precedence stay unchanged.

4. If a Streamlit upgrade is proposed, verify app shell behavior through
   AppTest before any UI changes. Keep UI, session state, exports, and prompt
   construction unchanged in the dependency PR.

5. Keep the PR small:
   dependency metadata, this runbook if needed, and contract tests only. Product
   migrations, model-name changes, schema changes, or UI changes belong in a
   separate PR.

## Verification

Run the focused dependency lane checks:

```bash
python -m compileall model_capabilities.py llm_client.py settings_openai.py
python -m pytest -q tests -k "openai or model_capabilities or settings or apptest"
python scripts/openai_smoke_test.py --mode all --ci-dry-run-if-no-key --json-only > reports/openai-smoke.json
python -m pytest -q tests/apptest
```

For a live OpenAI smoke test, set `OPENAI_API_KEY` locally only and run:

```bash
python scripts/openai_smoke_test.py --mode all --fail-fast
```

Never commit secrets, raw responses, uploaded documents, or personally
identifying data from local verification.
