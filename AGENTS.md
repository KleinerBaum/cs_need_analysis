# AGENTS.md — cs_need_analysis

Codex + contributor guide for a Streamlit vacancy intake wizard.

## Non-negotiables
- Keep canonical session keys in constants.py (SSKey) as the single source of truth.
- OpenAI config precedence must remain: nested secrets > root secrets > env > defaults.
- Structured outputs only: validate Pydantic models; handle failures with safe UI messages.
- No secrets/PII in logs, prompts, or debug panels.

## Install / run
- python -m pip install --upgrade pip
- pip install -r requirements.txt
- streamlit run app.py

## Dev checks (recommended)
If dev tools are not pinned, install ad-hoc:
- pip install ruff pytest mypy
Then:
- ruff format --check .
- ruff check .
- mypy
- pytest -q (if tests exist)

## LLM rules
- Prefer Responses API structured outputs (json schema via SDK helpers).
- Capability-gate reasoning/verbosity/temperature parameters per model.
- Always provide deterministic fallback behavior when keys are missing.

## Definition of Done
- Wizard flow works end-to-end.
- Config resolution remains transparent and safe (no secret exposure).
- No drift in SSKey usage / widget key generation.
