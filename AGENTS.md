# AGENTS.md — cs_need_analysis

Contributor guide for `cs_need_analysis`, a Streamlit-based vacancy intake wizard with
OpenAI structured outputs, ESCO/EURES integrations, and follow-up hiring artifacts.

## Scope

This repository is not a generic demo app. It is a stateful wizard with strong coupling
between:

- canonical constants and session keys
- Streamlit session-state initialization and reset behavior
- structured LLM generation and model-routing rules
- ESCO / EURES / NACE-derived enrichment
- Summary action hub artifacts and exports
- documentation (README) that must reflect actual runtime behavior

Treat changes as system changes, not isolated edits.

---

## Non-negotiables

- Keep canonical session keys in `constants.py` (`SSKey`) as the single source of truth.
- Keep wizard step identifiers in `constants.py` aligned with rendered pages.
- OpenAI config precedence must remain:
  `nested secrets > root secrets > env > defaults`.
- Structured outputs only:
  validate through Pydantic models and fail with safe UI messages.
- No secrets or PII in logs, prompts, debug panels, exports, or test fixtures.
- Do not add UI capabilities that are not supported by downstream export or processing paths.
- Do not let README drift away from actual code behavior.

---

## Canonical source files

Use these files as the authoritative sources before changing behavior:

- `constants.py`
  - session-state keys
  - wizard step definitions
  - schema versions
- `state.py`
  - session-state defaults
  - reset behavior
  - safe error/debug persistence
- `llm_client.py`
  - task kinds
  - model routing
  - OpenAI request building
  - structured parsing
  - fallback behavior
  - session response caching
- `settings_openai.py`
  - config loading
  - precedence rules
  - timeout parsing
  - resolved provenance
- `model_capabilities.py`
  - reasoning / verbosity / temperature compatibility rules
- `wizard_pages/08_summary.py`
  - action hub
  - follow-up artifact generation
  - export matrix
  - salary forecast integration
- `wizard_pages/01a_jobspec_review.py`
  - ESCO occupation workflow
- `wizard_pages/02_company.py`
  - optional NACE / EURES mapping usage
- `wizard_pages/04_role_tasks.py`
  - jobspec / ESCO / AI task suggestion flow
- `wizard_pages/05_skills.py`
  - ESCO skill mapping
  - occupation-related skill suggestions
  - AI skill suggestions
- `scripts/openai_smoke_test.py`
  - preferred verification path for OpenAI request-building and capability gating

---

## Required synchronization rules

### 1) New session-state keys
Whenever adding, renaming, or removing any `SSKey`:

- update `constants.py`
- update `state.init_session_state()`
- update `state.reset_vacancy()`
- update affected UI and exports
- update or add tests, especially reset/default tests

Do not leave dead keys, duplicate semantic keys, or implicit string keys in UI code.

### 2) New Summary artifact or follow-up generator
Whenever adding a new action-hub artifact:

- define canonical state keys in `constants.py`
- initialize and reset them in `state.py`
- register the action in `wizard_pages/08_summary.py`
- implement rendering and export paths in `wizard_pages/08_summary.py`
- expose cache/mode/model metadata consistently where applicable
- add or update tests for reset behavior and artifact state handling
- update README feature and export documentation

For this repo, artifact work is incomplete unless state, UI, export, and docs move together.

### 3) OpenAI routing / capability changes
Whenever changing model routing or request kwargs:

- update `llm_client.resolve_model_for_task()`
- keep `settings_openai.py` precedence unchanged unless intentionally redesigned
- keep `model_capabilities.py` as the only place for model-family capability rules
- verify behavior with `scripts/openai_smoke_test.py`
- update README wherever routing or compatibility is described

Never hardcode duplicated capability logic in multiple files.

### 4) ESCO / EURES / NACE changes
Any ESCO-related change must be checked across the full path:

- jobspec review occupation selection
- skills mapping
- occupation title variants
- NACE / EURES lookup usage
- summary readiness block
- structured export payload
- ESCO mapping report export

Do not treat ESCO UI changes as isolated cosmetic changes.

### 5) Documentation sync
Any change affecting one of the following requires README review in the same PR:

- wizard flow or step semantics
- Action Hub / Advanced Studio structure
- model routing
- exports
- ESCO / EURES / NACE behavior
- required install / verification commands

README must describe actual current behavior, not intended behavior.

---

## LLM rules

- Prefer Responses API structured outputs via SDK helpers.
- Use Pydantic models as the contract boundary for generated outputs.
- Keep capability-gating centralized in `model_capabilities.py`.
- Keep request-building centralized in `llm_client.py`.
- Preserve deterministic fallback behavior for supported tasks.
- Preserve safe error mapping for:
  - missing API key
  - timeout
  - connection errors
  - bad request / unsupported parameters
  - structured parse failures
- Preserve retry behavior for transient OpenAI failures.
- Never expose raw secrets or full sensitive request payloads in logs or UI.

---

## Caching rules

This repo uses session-based response caching. When touching LLM tasks:

- keep cache keys tied to model-relevant inputs
- keep schema-version awareness intact
- invalidate cached entries when validation fails
- preserve explicit cache-hit signals shown in UI
- avoid silent behavioral changes that make old cache entries semantically wrong

If task semantics materially change, also review schema version constants in `constants.py`.

---

## UI and export compatibility rules

- Only offer upload / input options that downstream processing and exports can safely support.
- If the UI accepts a format, verify the export/render path can handle it.
- Do not add “preview-only” or “temporary” UI affordances without deciding whether they belong in:
  - persisted session state
  - structured exports
  - README documentation

Example principle:
If logo uploads are accepted in the UI, their supported MIME types must be consistent with export handling.

---

## Install / run

Prefer the reproducible dependency path used by the repo documentation:

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt -c constraints.txt
streamlit run app.py
