# AGENTS.md — cs_need_analysis

Contributor guide for `cs_need_analysis`, a Streamlit-based vacancy intake wizard with OpenAI structured outputs, ESCO/EURES integrations, salary forecasting, and summary-stage hiring artifacts.

## What this repo is

This is not a loose Streamlit demo. It is a stateful workflow application with tight coupling between:

- canonical constants and session-state keys
- Pydantic schemas and structured LLM outputs
- wizard navigation, progress, limits, and completion logic
- summary artifacts and export paths
- ESCO / EURES / NACE enrichment
- salary forecast logic and scenario lab state
- README documentation that is expected to match runtime behavior

Treat changes as system changes, not isolated edits.

## Core working rules

- Keep `constants.py` as the single source of truth for session keys, wizard step keys, schema-version-like constants, and canonical IDs.
- Never introduce raw session-state string keys when an `SSKey` enum entry should exist.
- Keep schema, logic, UI, summary artifacts, and exports in sync.
- Keep OpenAI config precedence unchanged unless the task explicitly redesigns it: `nested secrets > root secrets > env > defaults`.
- Keep model-family capability gating centralized in `model_capabilities.py`.
- Keep OpenAI request-building, retries, parsing, and error mapping centralized in `llm_client.py`.
- Keep README aligned with current behavior whenever workflow, routing, exports, install steps, or feature flags change.
- Use minimal diffs. Avoid drive-by refactors.

## Architecture map

### App shell and navigation
- `app.py` — Streamlit entrypoint
- `wizard_pages/base.py` — wizard page contracts and shared helpers
- `components/`, `ui_components.py`, `ui_layout.py`, `site_ui.py` — reusable UI/layout building blocks

### Canonical state and contracts
- `constants.py` — authoritative keys, step IDs, canonical labels/IDs
- `state.py` — default session state, reset behavior, loaders, derived getters
- `schemas.py` — Pydantic contracts and question/schema helpers
- `question_dependencies.py`, `question_limits.py`, `question_progress.py`, `step_status.py` — dynamic wizard behavior

### LLM integration
- `llm_client.py` — task kinds, routing, request construction, structured parse, retry/error mapping, cache integration
- `settings_openai.py` — secrets/env/default resolution and task-level settings
- `model_capabilities.py` — model-family compatibility rules
- `scripts/openai_smoke_test.py` — preferred verification path for routing/capability changes

### Domain modules
- `esco_client.py`, `eures_mapping.py` — ESCO/EURES/NACE integration
- `salary/` — salary forecast engine, mapping, benchmarks, skill premiums, scenario builders
- `parsing.py` — upload/text extraction pipeline

### Workflow hotspots
- `wizard_pages/01a_jobspec_review.py` — integrated jobspec extraction review / ESCO flow
- `wizard_pages/04_role_tasks.py` — role tasks and salary forecast interactions
- `wizard_pages/05_skills.py` — ESCO skill mapping and AI skill suggestions
- `wizard_pages/08_summary.py` — summary action hub, artifact generation, exports, salary forecast integration

## Naming and coding conventions

- Python names: `snake_case` for functions/variables, `PascalCase` for classes, `UPPER_CASE` for module constants.
- Use English technical naming in code. Preserve existing German product/UI copy unless the task explicitly changes wording.
- New session-state keys must be added to `SSKey` in `constants.py`.
- New artifact IDs must be canonicalized in `constants.py` before use in UI or exports.
- Prefer typed boundaries:
  - `dataclass` / `TypedDict` for internal structured helpers
  - Pydantic models in `schemas.py` for LLM and export contracts
- Reuse existing helper functions before adding parallel logic.
- Do not duplicate model capability checks outside `model_capabilities.py`.
- Do not duplicate config precedence logic outside `settings_openai.py`.

## Synchronization rules

### 1) Session-state changes
Whenever adding, renaming, or removing any `SSKey` or canonical state concept:

- update `constants.py`
- update `state.init_session_state()`
- update reset paths in `state.py`
- update affected wizard pages and exports
- update tests, especially reset/default/contract tests

Do not leave dead keys, shadow keys, or implicit UI-only keys without an intentional persistence decision.

### 2) Wizard-step changes
Whenever changing visible step flow, step semantics, or completion logic:

- update step definitions in `constants.py`
- verify `question_progress.py`, `step_status.py`, and `question_limits.py`
- verify navigation and mode behavior in `wizard_pages/base.py`
- update README wizard-flow documentation
- run wizard contract and UI flow tests

### 3) OpenAI routing or request changes
Whenever changing task routing, kwargs, timeouts, capability gating, or structured output parsing:

- update `llm_client.py`
- keep precedence logic in `settings_openai.py`
- keep compatibility logic in `model_capabilities.py`
- verify with `tests/test_openai_smoke_modes.py`, `tests/test_openai_error_mapping.py`, and `scripts/openai_smoke_test.py`
- update README when runtime behavior changes

### 4) Summary artifact changes
Whenever adding or changing summary artifacts, generation buttons, config panels, or export behavior:

- update canonical IDs / state keys in `constants.py`
- initialize/reset state in `state.py`
- update action registry and render/export flow in `wizard_pages/08_summary.py`
- update related tests under `tests/test_summary_*`
- update README export / summary behavior

Artifact work is incomplete unless state, UI, export, and docs stay aligned.

### 5) ESCO / EURES / NACE changes
Whenever changing occupation matching, skills mapping, code lookups, or readiness behavior:

- review `esco_client.py`, `eures_mapping.py`, `wizard_pages/01a_jobspec_review.py`, `wizard_pages/05_skills.py`, and summary usage
- keep structured export payloads consistent
- verify tests covering ESCO, mapping, title variants, and readiness impacts

### 6) Salary forecast changes
Whenever changing salary types, feature extraction, scenario behavior, or UI presentation:

- review `salary/types.py`, `salary/engine.py`, `salary/features_esco.py`, `salary/scenario_lab_builders.py`, `wizard_pages/salary_forecast.py`, and `wizard_pages/salary_forecast_panel.py`
- verify schema/output compatibility and scenario selection state
- run the salary-focused tests

## Verification commands

Use the smallest relevant verification set first, then broaden if the change crosses module boundaries.

### Environment / install
```bash
python -m pip install --upgrade pip
pip install -r requirements.txt -c constraints.txt
```

### Run app
```bash
streamlit run app.py
```

### Baseline checks
```bash
pip check
python -m compileall app.py components config pages salary scripts tests wizard_pages
python -m pytest -q
```

### Targeted checks by area

#### State / constants / wizard contracts
```bash
python -m pytest -q \
  tests/test_state_reset.py \
  tests/test_wizard_contract.py \
  tests/test_ui_mode_flow.py \
  tests/test_question_limits.py \
  tests/test_question_progress.py
```

#### Summary / artifacts / exports
```bash
python -m pytest -q tests/test_summary_*.py tests/test_additional_task_generators.py
```

#### OpenAI routing / capability gating
```bash
python -m pytest -q \
  tests/test_openai_smoke_modes.py \
  tests/test_openai_error_mapping.py \
  tests/test_generate_vacancy_brief.py \
  tests/test_additional_task_generators.py
python scripts/openai_smoke_test.py --mode all --ci-dry-run-if-no-key --json-only
```

#### ESCO / EURES / parsing
```bash
python -m pytest -q \
  tests/test_esco_client.py \
  tests/test_eures_mapping.py \
  tests/test_jobspec_title_variants.py \
  tests/test_parsing_upload_stream.py \
  tests/test_skills_occupation_suggestions.py
```

#### Salary forecast
```bash
python -m pytest -q tests/test_salary_*.py tests/tests_test_salary_benchmarks.py
```

## Linting policy

There is currently no dedicated repo-local Ruff/Mypy/Black configuration checked in.

- Do **not** silently introduce a new lint/type toolchain in routine implementation tasks.
- For this repo, the practical quality gate is: targeted pytest + syntax compilation + smoke tests where relevant.
- If the task explicitly asks for lint/type tooling, propose it as a separate, small change set.

## Do-not-touch areas without explicit request

- `images/` — brand and static assets
- `data/salary_benchmarks/` and `data/salary_skill_premiums/` — curated data inputs
- `pages/03_Impressum.py`, `pages/11_Datenschutzrichtlinie.py`, `pages/12_Nutzungsbedingungen.py`, `pages/13_Cookie_Policy_Settings.py`, `pages/14_Erklaerung_zur_Barrierefreiheit.py` — legal/compliance pages
- `.streamlit/config.toml` — theme/branding defaults
- `constraints.txt` — pinned dependency constraint; change only when dependency work is part of the task
- `constants.cpython-313.pyc` — generated artifact; do not edit, and do not rely on it as source

## Security and privacy rules

- Never commit secrets, API keys, OAuth tokens, or copied secret values.
- Never print raw secrets or full credential-bearing env dumps in logs, tests, or docs.
- Keep Google and other OAuth scopes least-privilege.
- Do not place PII into prompts, fixtures, exported examples, or debug output unless the task explicitly requires redaction-safe handling.
- Keep OpenAI/UI debug output non-sensitive.
- Preserve safe error mapping and user-facing fallbacks.
- For examples and fixtures, use synthetic placeholder data.

## Diff style

- Prefer the smallest working change.
- Preserve existing file organization and naming style.
- Avoid unrelated renames, formatting churn, and broad import reshuffles.
- Keep comments purposeful; do not narrate obvious code.
- Preserve existing UX/copy tone unless content work is requested.
- When changing labels or canonical IDs, update tests/docs in the same change.

## PR and commit conventions

### Commit style
Use focused commits with a clear scope, for example:

- `fix(state): keep summary artifact reset aligned with SSKey changes`
- `feat(summary): add canonical export metadata for job ad drafts`
- `refactor(openai): centralize GPT-5.4 temperature gating`
- `test(esco): cover occupation fallback title variants`
- `docs(readme): sync summary export behavior`

### PR structure
Every PR should include:

1. **What changed** — concise summary
2. **Why** — problem or requirement
3. **Files / modules touched** — especially canonical source files
4. **Verification** — exact commands run
5. **Risk / regression notes** — state, export, routing, or schema impacts
6. **Follow-ups** — only if intentionally deferred

## Prompting Codex inside this repo

When asking Codex to change this repo, provide:

- the exact goal
- the affected files or likely hotspots
- constraints (no new deps, preserve schema, keep docs in sync, etc.)
- the definition of done
- the verification commands to run

Good prompt shape:

```text
Goal: Fix duplicate summary artifact state after vacancy reset.
Context: constants.py, state.py, wizard_pages/08_summary.py, tests/test_state_reset.py.
Constraints: no new dependencies; keep canonical SSKey usage only; update README only if runtime behavior changes.
Done when: state resets cleanly, targeted tests pass, diff stays minimal.
```
