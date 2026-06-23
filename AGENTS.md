# AGENTS.md — cs_need_analysis

Working guide for AI/coding agents in `cs_need_analysis`, a Streamlit Recruiting-Briefing workflow with OpenAI structured outputs, ESCO/EURES enrichment, deterministic question-flow overlays, salary forecasting, summary artifacts, and export generation.

This repository is a stateful workflow application. Treat changes as system changes, not isolated edits.

## Current repo contract

### Active product flow

The full routable contract is defined by `constants.STEPS` and enforced by `wizard_pages/__init__.py`. Sidebar navigation, process progress, and completion/readiness metrics use the operational route group constants.

Pre-start route:

| Step key | UI label | Page module |
|---|---|---|
| `intro` | Einleitung | `wizard_pages/00_intro.py` |

Operational flow:

| Order | Step key | UI label | Page module |
|---:|---|---|---|
| 1 | `landing` | Start | `wizard_pages/00_landing.py` |
| 2 | `company` | Unternehmen | `wizard_pages/02_company.py` |
| 3 | `role_tasks` | Rolle & Aufgaben | `wizard_pages/04_role_tasks.py` |
| 4 | `skills` | Skills & Anforderungen | `wizard_pages/05_skills.py` |
| 5 | `benefits` | Benefits & Rahmenbedingungen | `wizard_pages/06_benefits.py` |
| 6 | `interview` | Interviewprozess | `wizard_pages/07_interview.py` |
| 7 | `summary` | Zusammenfassung | `wizard_pages/08_summary.py` |

Legacy/non-routable modules:

- `wizard_pages/01a_jobspec_review.py` — legacy hidden review step; Start phases B/C now own extraction review and ESCO anchoring.
- `wizard_pages/03_team.py` — legacy hidden team step; team context is handled inside `company` through `wizard_pages/team_section.py`.

Do not reintroduce these modules into routing unless the task explicitly redesigns the wizard contract and updates tests/docs.

### Information acquisition pipeline

The current intake process is intentionally staged:

1. **Einleitung** — short product context before the operational flow starts; routable but excluded from sidebar/progress/readiness.
2. **Start / Phase A** — source selection, upload/manual text, consent, PII reduction, UI mode, ESCO operating settings.
3. **Start / Phase B** — structured jobspec extraction review with field-level fact/evidence handling.
4. **Start / Phase C** — ESCO occupation anchoring with primary anchor and up to two secondary context anchors.
5. **Company** — company/team context, optional homepage enrichment, open-question matching.
6. **Role/Skills/Benefits** — unified blocks: extracted jobspec values, source comparison, salary forecast, open questions, review.
7. **Interview** — process board, candidate communication, internal roles/timing, export-marked values.
8. **Summary** — readiness, fact overview, action hub, artifact generation, result workspace, export workspace.

Keep this chain synchronized across `constants.py`, `state.py`, `intake_facts.py`, `job_extract_review_helpers.py`, `question_plan_compiler.py`, `question_*`, wizard pages, summary/export code, tests, and README.

## Core invariants

- `constants.py` is the single source of truth for session-state keys, step IDs, UI modes, ESCO modes, artifact IDs, schema-version-like constants, and canonical IDs.
- Add new session keys to `SSKey`; do not use raw string keys when an enum entry should exist.
- Prefer `state_store.py` for new typed access to existing high-value session-state domains; keep raw storage keys unchanged unless the task explicitly changes the state contract.
- Keep schema, logic, UI, summary artifacts, exports, tests, and README in sync.
- Keep OpenAI settings precedence unchanged unless explicitly redesigned: nested `st.secrets["openai"][KEY]` → root `st.secrets[KEY]` → environment → hard default.
- Keep model-family capability checks centralized in `model_capabilities.py`.
- Keep OpenAI request construction, retries, structured parsing, fallback behavior, response caching, usage metadata, and error mapping centralized in `llm_client.py`.
- Keep privacy-sensitive logging and telemetry restricted to whitelisted, non-sensitive metadata.
- Use minimal diffs. Avoid drive-by refactors.

## Architecture map

### App shell and navigation

- `app.py` — Streamlit entry point, page config, theme injection, preferences query-param view, current-step rendering, scroll reset.
- `wizard_pages/__init__.py` — explicit page loader and route contract against `constants.STEPS`.
- `wizard_pages/base.py` — page/context dataclasses, sidebar navigation, UI mode helpers, progress/status rendering, ESCO sidebar/migration helpers, shared layout helpers.
- `components/`, `ui_components.py`, `ui_layout.py`, `site_ui.py`, `styles/theme.css` — reusable UI/layout/design primitives.

### Canonical state and contracts

- `constants.py` — canonical state keys, wizard steps, UI modes, ESCO modes, artifact IDs, fact registry, usage event types.
- `state_store.py` — typed facade over canonical `SSKey` session-state storage; new code should prefer it for high-value state domains.
- `state.py` — session defaults, reset behavior, source redaction preference sync, ESCO semantic state sync, answer/fact adapters.
- `schemas.py` — Pydantic contracts for structured OpenAI outputs and exports.
- `intake_facts.py` — canonical intake fact/evidence helpers and legacy field adapters.
- `job_extract_evidence.py`, `job_extract_review_helpers.py` — jobspec review/evidence utilities.
- `question_dependencies.py`, `question_limits.py`, `question_progress.py`, `question_plan_compiler.py`, `step_status.py` — dynamic question rendering, overlays, limits, completion/readiness behavior.

### LLM integration

- `settings_openai.py` — settings/secrets/env/default resolution, task output limits, ESCO RAG settings, non-sensitive `resolved_from` provenance.
- `model_capabilities.py` — GPT-5/GPT-5.4 compatibility rules for `reasoning`, `text.verbosity`, `temperature`, and valid `reasoning_effort` values.
- `llm_client.py` — task routing, prompts, request kwargs, structured parse, fallback model path, response cache, retry/error handling.
- `scripts/openai_smoke_test.py` — preferred verification path for OpenAI request-building and capability changes.

Current LLM task functions in `llm_client.py`:

- `extract_job_ad`
- `generate_question_plan`
- `generate_vacancy_brief`
- `generate_custom_job_ad`
- `generate_interview_sheet_hr`
- `generate_interview_sheet_hm`
- `generate_boolean_search_pack`
- `generate_employment_contract_draft`
- `generate_requirement_gap_suggestions`
- `generate_benefit_suggestions`
- `generate_role_tasks_salary_forecast`

### Domain modules

- `esco_client.py`, `esco_semantics.py`, `eures_mapping.py` — ESCO/EURES/NACE lookup, anchor semantics, degraded/anchored modes.
- `esco_offline_index.py`, `scripts/build_esco_index.py` — local ESCO lookup index build/runtime path.
- `esco_matrix.py`, `scripts/build_esco_matrix.py` — optional ESCO matrix priors and coverage inputs.
- `esco_rag.py`, `scripts/prepare_esco_for_vectorstore.py` — optional vector-store retrieval for ESCO context.
- `occupation_context.py`, `question_packs/` — deterministic occupation-aware question-flow overlays.
- `homepage_research.py` — public website fetch/extraction/matching with safety constraints.
- `salary/` — deterministic salary forecast engine, benchmark/mapping data, feature extraction, scenario lab builders.
- `parsing.py` — PDF/DOCX/TXT upload and text extraction pipeline.

### Workflow hotspots

- `wizard_pages/jobad_intake.py` — Start phase A/B/C, source handling, PII controls, jobspec extraction, deterministic question-flow sync, review promotion, ESCO operating block.
- `wizard_pages/02_company.py` and `wizard_pages/team_section.py` — company and team context, homepage enrichment, role-context suggestions.
- `wizard_pages/04_role_tasks.py` — role/task source pills, ESCO/context suggestions, AI suggestions, salary block.
- `wizard_pages/05_skills.py` — jobspec/ESCO/AI skill comparison, ESCO normalization, unmapped-term workflow, ESCO matrix priors, coverage.
- `wizard_pages/06_benefits.py` — jobspec/context/AI benefit comparison and salary-relevant benefit state.
- `wizard_pages/07_interview.py` — interview process board and export-marked interview values.
- `wizard_pages/08_summary.py` — readiness dashboard, fact table, action registry, artifact generation, result/export workspaces, DOCX/PDF/JSON/Markdown exports.

## Modes and runtime switches

### UI modes

Canonical values: `quick`, `standard`, `expert`.

Display labels: `schnell`, `ausführlich`, `vollumfänglich`.

Update all of these together when mode behavior changes:

- `constants.UI_MODE_VALUES`, `UI_MODE_DISPLAY_LABELS`, preference constants
- `config/preferences.py`
- `wizard_pages/base.py` mode helpers and captions
- `question_limits.py`
- step pages using compact/detail behavior
- `tests/test_ui_mode_flow.py`, `tests/test_question_limits.py`, `tests/test_progressive_disclosure_helpers.py`
- README mode documentation

### ESCO modes

Canonical modes are defined in `constants.py` and interpreted through `esco_client.py` / `esco_semantics.py`.

- Release lanes: `stable -> v1.2.0`, `preview -> v1.2.1`.
- API modes: `hosted`, `local`.
- Data-source modes: `live_api`, `offline_index`, `hybrid`.
- Anchor states: `degraded_unconfirmed`, `anchored`, `anchored_with_context`.
- Semantic export modes: `degraded`, `anchored`.

Downstream behavior must respect anchor state. URI-based exports, ESCO skill normalization, matrix coverage, ESCO-based interview prioritization, and ESCO task suggestions require an anchored state.

### Summary artifact modes

Active Summary artifact IDs are in `constants.SUMMARY_ACTIVE_ARTIFACT_IDS`.
Known legacy/current IDs remain in `constants.SUMMARY_ARTIFACT_IDS` for draft
loading and compatibility; labels/aliases are in `summary_artifacts.py`.

Current active IDs:

- `brief`
- `job_ad`
- `interview_hr`
- `interview_fach`
- `boolean_search`

When adding or renaming artifacts, update constants, aliases, state initialization/reset, `wizard_pages/08_summary.py`, export functions, tests under `tests/test_summary_*`, and README export documentation in one change.

Archived legacy ID:

- `employment_contract` — hidden from active Summary UI, release gates,
  previews, result switchers, and exports; preserved only for old draft state
  loading until its generator/schema/state keys can be removed safely.

## OpenAI configuration contract

Settings are resolved in `settings_openai.py` with this precedence:

1. nested Streamlit secret: `[openai] KEY = ...`
2. root Streamlit secret: `KEY = ...`
3. environment variable
4. hard default

Main keys:

- `OPENAI_API_KEY`
- `OPENAI_MODEL`
- `DEFAULT_MODEL`
- `LIGHTWEIGHT_MODEL`
- `MEDIUM_REASONING_MODEL`
- `HIGH_REASONING_MODEL`
- `REASONING_EFFORT`
- `VERBOSITY`
- `OPENAI_REQUEST_TIMEOUT`
- `ESCO_VECTOR_STORE_ID`
- `ESCO_RAG_ENABLED`
- `ESCO_RAG_MAX_RESULTS`

Task limit keys follow the pattern:

- `<TASK_KIND_UPPER>_MAX_OUTPUT_TOKENS`
- `<TASK_KIND_UPPER>_MAX_BULLETS_PER_FIELD`
- `<TASK_KIND_UPPER>_MAX_SENTENCES_PER_FIELD`

for task kinds listed in `settings_openai._TASK_KINDS`.

Important implementation detail: `llm_client.py` currently has a `generate_role_tasks_salary_forecast` task route; if task-specific limit configuration is required for it, align `settings_openai._TASK_KINDS` and tests in the same PR.

## Synchronization rules

### 1) Session-state changes

When adding, renaming, or removing an `SSKey` or canonical state concept:

- update `constants.py`
- update `state.init_session_state()`
- update `state.reset_vacancy()` or other reset paths
- update any legacy alias migration if needed
- update affected wizard pages, summary/export builders, and tests
- update README if runtime behavior or configuration changes

Do not leave dead keys, shadow keys, or implicit widget-only state without an intentional persistence decision.

### 2) Wizard-step changes

When changing visible step flow, step semantics, or completion logic:

- update `constants.STEPS`
- update `wizard_pages/__init__.py` only if routing rules intentionally change
- verify `question_progress.py`, `step_status.py`, `question_limits.py`, and `wizard_pages/base.py`
- update tests: `tests/test_wizard_contract.py`, `tests/test_ui_mode_flow.py`, `tests/test_ui_step_shell_order.py`, progress/status tests
- update README wizard-flow documentation

### 3) Jobspec/intake/fact changes

When changing extraction, identified-information review, fact promotion, or evidence behavior:

- update `schemas.JobAdExtract` or related schemas if the structured output changes
- update `llm_client.build_extract_job_ad_messages()` and prompt limits only if needed
- update `intake_facts.py`, `job_extract_evidence.py`, `job_extract_review_helpers.py`, and `wizard_pages/jobad_intake.py`
- update `question_plan_compiler.py`, `occupation_context.py`, and `question_packs/` if follow-up question selection changes
- update summary/export payloads if facts/evidence become externally visible
- run intake/fact/question tests

### 4) OpenAI routing or request changes

When changing model routing, kwargs, timeouts, capability gating, parsing, retry, fallback, cache, or error behavior:

- update `settings_openai.py`, `model_capabilities.py`, and `llm_client.py` consistently
- keep logs and debug output non-sensitive
- update smoke-test modes in `scripts/openai_smoke_test.py` if request semantics change
- run OpenAI tests and dry-run smoke test
- update README configuration/smoke-test sections when behavior changes

### 5) Summary artifact/export changes

When adding or changing summary artifacts, generation buttons, config panels, readiness logic, exports, or structured export fields:

- update canonical artifact IDs and state keys in `constants.py`
- initialize/reset state in `state.py`
- update action registry, active artifact handling, result rendering, and export workspace in `wizard_pages/08_summary.py`
- update `summary_artifacts.py`, `summary_exports.py`, `summary_esco.py`, `summary_facts.py`, or `summary_job_ad.py` as needed
- update tests under `tests/test_summary_*`
- update README export/summary documentation

Artifact work is incomplete unless state, UI, export, and docs stay aligned.

### 6) ESCO/EURES/NACE changes

When changing occupation matching, anchor semantics, skill normalization, code lookups, local index behavior, RAG, or readiness behavior:

- review `esco_client.py`, `esco_semantics.py`, `eures_mapping.py`, `esco_offline_index.py`, `esco_rag.py`, `wizard_pages/jobad_intake.py`, `wizard_pages/04_role_tasks.py`, `wizard_pages/05_skills.py`, and summary export code
- preserve degraded-mode behavior when no anchor exists or ESCO is unavailable
- keep secondary anchors context-only unless explicitly redesigned
- update structured export payloads and tests covering ESCO, mapping, title variants, offline contracts, RAG, matrix, and readiness impacts

### 7) Salary forecast changes

When changing salary feature extraction, benchmark loading, scenario behavior, UI presentation, or exports:

- review `salary/types.py`, `salary/engine.py`, `salary/benchmarks.py`, `salary/features_esco.py`, `salary/mapping.py`, `salary/scenario_lab_builders.py`, `salary/scenarios.py`, `wizard_pages/salary_forecast.py`, and `wizard_pages/salary_forecast_panel.py`
- keep role/skills/benefits salary blocks and sidebar behavior consistent
- update `state.py` salary scenario defaults/resets if state changes
- run salary tests and affected summary tests

### 8) Homepage research changes

When changing homepage enrichment:

- keep public HTTP(S)-only behavior, content-type/size checks, and fetch-cache behavior in `homepage_research.py`
- do not log raw URLs, page text, contact data, prompts, or extracted payloads in usage events
- keep selected matches compatible with intake facts and summary brief generation
- update `tests/test_company_homepage_research.py` and company/team regression tests

### 9) Usage/telemetry changes

When changing usage events:

- update `constants.UsageEventType`
- keep metadata sanitization in `usage_events.py` restrictive
- never store prompts, full URLs, credentials, raw response payloads, contact data, or answer values
- update `tests/test_usage_events.py`

## Verification commands

Use the smallest relevant verification set first, then broaden when the change crosses module boundaries.

### Environment / install

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt -c constraints.txt
```

### Run app

```bash
streamlit run app.py
```

### CI-equivalent baseline

```bash
pip check
python scripts/check_repo_hygiene.py
python -m compileall app.py homepage_research.py job_extract_evidence.py job_extract_review_helpers.py summary_artifacts.py summary_esco.py summary_exports.py summary_facts.py summary_job_ad.py usage_events.py components config pages salary scripts tests wizard_pages
python -m pytest -q tests/test_repo_contract_drift.py tests/test_wizard_contract.py tests/test_quality_gate_config.py tests/test_public_page_links.py tests/test_constants_import_contract.py tests/test_schema_contracts.py --junitxml=reports/junit/contract.xml
python -m pytest -q tests --ignore=tests/e2e --ignore=tests/apptest --junitxml=reports/junit/unit.xml
python -m pytest -q tests/apptest --junitxml=reports/junit/apptest.xml
python scripts/openai_smoke_test.py --mode all --ci-dry-run-if-no-key --json-only > reports/openai-smoke.json
```

### Docs and wizard contract

Use this smaller set for documentation or routed-step contract changes:

```bash
python -m compileall README.md AGENTS.md CHANGELOG.md
python -m pytest -q tests/test_repo_contract_drift.py tests/test_wizard_contract.py tests/test_quality_gate_config.py tests/test_public_page_links.py
rg -n '01[_]jobad|wizard_pages/01[_]jobad' README.md AGENTS.md CHANGELOG.md
```

The grep command should return no matches after stale Start-step references are removed.

### Targeted checks by area

State, constants, wizard contracts:

```bash
python -m pytest -q \
  tests/test_state_reset.py \
  tests/test_wizard_contract.py \
  tests/test_ui_mode_flow.py \
  tests/test_question_limits.py \
  tests/test_question_progress.py \
  tests/test_step_status_payload.py
```

Intake, facts, jobspec extraction, question flow:

```bash
python -m pytest -q \
  tests/test_fact_contract.py \
  tests/test_intake_facts.py \
  tests/test_job_extract_evidence.py \
  tests/test_job_extract_review_helpers.py \
  tests/test_jobad_intake_cache_usage.py \
  tests/test_jobad_intake_identified_info_block.py \
  tests/test_jobad_intake_upload_extract.py \
  tests/test_question_pack_compiler.py \
  tests/test_question_plan_normalization.py
```

Summary, artifacts, exports:

```bash
python -m pytest -q tests/test_summary_*.py tests/test_additional_task_generators.py
```

OpenAI routing/capability/error handling:

```bash
python -m pytest -q \
  tests/test_openai_settings.py \
  tests/test_openai_smoke_modes.py \
  tests/test_openai_error_mapping.py \
  tests/test_generate_vacancy_brief.py \
  tests/test_additional_task_generators.py
python scripts/openai_smoke_test.py --mode all --ci-dry-run-if-no-key --json-only
```

ESCO/EURES/RAG/matrix/offline index:

```bash
python -m pytest -q \
  tests/test_esco_client.py \
  tests/test_esco_metadata.py \
  tests/test_esco_occupation_ui.py \
  tests/test_esco_offline_contract.py \
  tests/test_esco_rag.py \
  tests/test_esco_matrix_loader.py \
  tests/test_eures_mapping.py \
  tests/test_jobspec_title_variants.py \
  tests/test_skills_occupation_suggestions.py \
  tests/test_state_esco_loaders.py
```

Salary forecast:

```bash
python -m pytest -q tests/test_salary_*.py tests/tests_test_salary_benchmarks.py
```

Company/team/homepage:

```bash
python -m pytest -q \
  tests/test_company_homepage_research.py \
  tests/test_company_team_scope_regression.py \
  tests/test_team_section.py
```

## Linting policy

Repo-local QA config is intentionally scoped in `pyproject.toml`: Ruff, Black, mypy, Pyright, and Bandit run through `requirements-dev.txt`.

- Do not silently broaden or replace the existing lint/type toolchain in routine implementation tasks.
- For this repo, the practical quality gate is targeted pytest, syntax compilation, scoped QA checks, and smoke tests where relevant.
- AppTest smoke tests use the `apptest` marker in `pytest.ini` and the Streamlit runtime dependency.
- Optional/advisory browser smoke tests use the `e2e` marker in `pytest.ini` and Playwright dependencies from `requirements-e2e.txt`.
- Current CI job IDs in `.github/workflows/ci.yml` are `qa`, `contract`, `unit`, `apptest`, `browser_smoke`, and `security`.
- If the task explicitly asks for lint/type tooling, propose it as a separate small PR.

## Do-not-touch areas without explicit request

- `images/` — brand/static assets
- `data/salary_benchmarks/` and `data/salary_skill_premiums/` — curated data inputs
- `pages/03_Impressum.py`, `pages/11_Datenschutzrichtlinie.py`, `pages/12_Nutzungsbedingungen.py`, `pages/13_Cookie_Policy_Settings.py`, `pages/14_Erklaerung_zur_Barrierefreiheit.py` — legal/compliance pages
- `.streamlit/config.toml` — theme defaults
- `constraints.txt` — pinned SDK constraint; change only as dependency work
- `constants.cpython-313.pyc` — generated artifact; do not edit or use as source

## Security and privacy rules

- Never commit secrets, API keys, OAuth tokens, credential files, or copied secret values.
- Never print raw secrets or full credential-bearing env dumps in logs, tests, screenshots, or docs.
- Keep OAuth scopes least-privilege.
- Keep PII out of prompts, fixtures, exported examples, usage events, and debug output unless the task explicitly requires redaction-safe handling.
- Preserve safe OpenAI error mapping and user-facing fallbacks.
- For examples and fixtures, use synthetic placeholder data.

## Diff style

- Prefer the smallest working change.
- Preserve file organization and naming style.
- Avoid unrelated renames, formatting churn, and broad import reshuffles.
- Use English technical names in code. Preserve existing German product/UI copy unless the task explicitly changes wording.
- Keep comments purposeful; do not narrate obvious code.
- When changing labels, schema fields, modes, or canonical IDs, update tests/docs in the same change.

## PR and commit conventions

### Commit style

Use focused commits with clear scope, for example:

- `fix(state): reset summary artifacts with canonical SSKey defaults`
- `feat(intake): persist reviewed jobspec facts with evidence metadata`
- `refactor(openai): centralize GPT-5.4 temperature gating`
- `test(esco): cover hybrid offline fallback`
- `docs(readme): sync wizard flow and export modes`

### PR structure

Every PR should include:

1. What changed
2. Why
3. Files/modules touched
4. Verification commands run
5. Risk/regression notes for state, exports, routing, schema, privacy, or OpenAI behavior
6. Follow-ups only if intentionally deferred

## Prompting Codex inside this repo

Use prompts with exact scope, constraints, definition of done, and verification commands.

Good prompt shape:

```text
Goal: Fix stale summary artifact state after vacancy reset.
Context: constants.py, state.py, summary_artifacts.py, wizard_pages/08_summary.py, tests/test_state_reset.py.
Constraints: no new dependencies; canonical SSKey usage only; preserve existing German UI copy; update README only if runtime behavior changes.
Done when: state resets cleanly, targeted tests pass, diff is minimal.
Verification: python -m pytest -q tests/test_state_reset.py tests/test_summary_active_artifact.py
```
