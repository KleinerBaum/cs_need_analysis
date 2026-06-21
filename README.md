# Cognitive Staffing — Vacancy Intake Wizard

Streamlit app for structured vacancy intake, jobspec extraction, ESCO/EURES enrichment, salary forecasting, interview-process capture, and generation of recruiting artifacts with OpenAI structured outputs.

The current implementation is not a loose demo. It is a stateful workflow application with tight coupling between canonical constants, session state, Pydantic schemas, wizard UI, fact/evidence handling, summary artifacts, and exports.

## Current implementation status

Implemented core flow:

1. Source intake from PDF, DOCX, TXT, or pasted text.
2. Privacy-first source handling with PII reduction enabled by default.
3. Structured jobspec extraction through OpenAI structured outputs.
4. Reviewable identified-information block with fact/evidence promotion.
5. Deterministic occupation-aware question-flow overlay.
6. ESCO occupation anchoring with degraded fallback mode.
7. Company/team context, including optional public homepage enrichment.
8. Role/task, skill, and benefit curation through comparable source-pill blocks.
9. Deterministic salary forecast and scenario state.
10. Interview-process workspace.
11. Summary readiness dashboard, action hub, artifact generation, and exports.
12. Privacy-safe usage events for lightweight observability.

Known partials / explicit non-goals in this snapshot:

- Full official ESCO bulk-dataset ingestion is not implemented; the offline index path is lookup-focused.
- ESCO matrix priors are optional and do not include ISCO distribution benchmarking or advanced coherence metrics.
- Repo-local QA config is intentionally scoped in `pyproject.toml`: Ruff, Black, mypy, and Bandit run through `requirements-dev.txt`; Pyright is not configured.
- `wizard_pages/01a_jobspec_review.py` and `wizard_pages/03_team.py` are legacy/non-routable modules.

## Wizard flow

The active visible route is defined by `constants.STEPS` and enforced by `wizard_pages/__init__.py`.

| Order | Step key | UI label | Main module | Purpose |
|---:|---|---|---|---|
| 1 | `intro` | Einleitung | `wizard_pages/00_intro.py` | Introductory context before the operational intake starts |
| 2 | `landing` | Start | `wizard_pages/00_landing.py` + `wizard_pages/jobad_intake.py` | Landing page plus jobspec intake phases A/B/C |
| 3 | `company` | Unternehmen | `wizard_pages/02_company.py` | Employer profile, website evidence, ESCO context, company questions, team/reporting |
| 4 | `role_tasks` | Rolle & Aufgaben | `wizard_pages/04_role_tasks.py` | Work model/location, non-negotiables/compliance, role/task curation, ESCO/context/AI suggestions, salary block |
| 5 | `skills` | Skills & Anforderungen | `wizard_pages/05_skills.py` | Jobspec/ESCO/AI skills, normalization, matrix priors, unmapped-term decisions |
| 6 | `benefits` | Benefits & Rahmenbedingungen | `wizard_pages/06_benefits.py` | Benefits and operating conditions from jobspec/context/AI |
| 7 | `interview` | Interviewprozess | `wizard_pages/07_interview.py` | Interview values, candidate communication, internal roles/timing |
| 8 | `summary` | Zusammenfassung | `wizard_pages/08_summary.py` | Readiness, facts, action hub, artifacts, exports |

### Start step phases

The Start step contains the former review flow directly:

- **Phase A — Quelle & Datenschutz:** upload/manual text, active source handling, consent, PII reduction, UI mode, ESCO operating settings, and routing metadata for hiring reason, urgency, volume, confidentiality, and role-definition maturity.
- **Phase B — Extraktion prüfen:** editable identified-information block with confidence/evidence where available.
- **Phase C — ESCO-Suche:** primary occupation anchor, optional secondary context anchors, degraded fallback when no anchor is confirmed.

There is no separate visible `jobspec_review` step.

## UI modes

The app supports three global UI modes:

| Stored value | German label | Intended behavior |
|---|---|---|
| `quick` | `schnell` | Curated core flow with compact detail groups and per-step question caps |
| `standard` | `ausführlich` | Complete essential intake using all dependency-visible `core` and `standard` questions |
| `expert` | `vollumfänglich` | Full intake using dependency-visible `core`, `standard`, and conditional `detail` questions |

The mode is controlled through the sidebar preference center and the Start step. It affects visible question depth through `question_limits.py` and compact/detail behavior through shared UI helpers. `quick` keeps the essential app functions visible but caps the curated core questions per step. `standard` is the default first-run mode and collects all essential information (`core` + `standard`). `expert` adds deep conditional questions that can become relevant in specific cases. Expensive secondary blocks such as source comparison and salary forecast render lazily; source comparison follows the detail-expanded preference, while salary forecast remains on-demand.

Adaptive question ranking can use optional question metadata: `impact_targets`, `acquisition_cost`, and `info_gain_score`. These fields let high-impact unanswered questions rise above lower-value detail questions without changing the visible step contract or existing UI modes.

To compare UI mode, ESCO, RAG, model-routing, and enrichment combinations, use the evaluation runbook in `docs/feature_combination_evaluation.md` and the offline scoring helper:

```bash
python scripts/evaluate_feature_combinations.py --json-only
```

## Information acquisition model

The intake process combines several evidence streams:

| Source | Main modules | Stored/used as |
|---|---|---|
| Jobspec extraction | `llm_client.py`, `schemas.py`, `wizard_pages/jobad_intake.py` | `JobAdExtract`, intake facts, evidence, base question plan |
| Manual review/input | `job_extract_review_helpers.py`, wizard pages, `state.py` | confirmed answers/facts with manual precedence |
| ESCO/EURES context | `esco_client.py`, `esco_semantics.py`, `eures_mapping.py` | occupation anchors, skill suggestions, task context, export metadata |
| Homepage enrichment | `homepage_research.py`, `wizard_pages/02_company.py` | company/team facts and open-question matches |
| AI suggestions | `llm_client.py`, role/skills/benefits pages | source-pill suggestions and optional artifact inputs |
| Salary engine | `salary/`, salary forecast panels | deterministic forecast result and scenario state |

Manual corrections remain authoritative over extracted values. Jobspec assumptions/gaps are not collected as a single Start-step backlog; they are routed to the best matching downstream step.

Canonical intake fact evidence also carries a resolution status (`confirmed`, `inferred`, `assumed`, `conflicted`, or `missing`). Structured Summary exports include `intake_fact_resolution` so downstream consumers can distinguish confirmed facts from inferred, assumed, conflicted, or still-missing information without changing the legacy fact values.

Fact definitions in `constants.INTAKE_FACTS` also carry steering metadata: `salary_impact` separates direct Salary drivers from quality/uncertainty inputs, `requirement_stage` distinguishes facts required before Summary from facts required before artifact generation, and `website_enrichable` marks fields that can be reviewed against homepage evidence.

The canonical fact registry also covers downstream decision points from the improvement report: company and team context, role outcomes and travel profile, typed skill requirements, variable pay and offer constraints, work authorization, start-date flexibility, and interview assessment/scorecard fields.

## Architecture map

### Canonical contracts

- `constants.py` — session keys, step IDs, UI modes, ESCO modes, fact registry, artifact IDs.
- `state_store.py` — typed facade over canonical `SSKey` session-state storage; new code should prefer it for high-value state domains.
- `state.py` — session defaults, vacancy reset behavior, answer/fact adapters.
- `schemas.py` — Pydantic contracts for jobspec extraction, question plans, briefs, and generated artifacts.
- `intake_facts.py` — canonical fact/evidence storage and legacy field compatibility.
- `question_*`, `question_plan_compiler.py`, `question_packs/` — dynamic question flow and occupation-aware overlays.

### Runtime shell and UI

- `app.py` — Streamlit entrypoint, preferences query-param view, navigation and rendering.
- `wizard_pages/base.py` — shared wizard context, navigation, progress, UI-mode helpers, ESCO sidebar/status.
- `components/`, `ui_components.py`, `ui_layout.py`, `site_ui.py`, `styles/theme.css` — shared UI/layout/design system.

### AI and enrichment

- `settings_openai.py` — OpenAI settings, model defaults, task limits, ESCO RAG flags.
- `model_capabilities.py` — model-family compatibility gates for request kwargs.
- `llm_client.py` — OpenAI task routing, prompts, structured parsing, retries, fallbacks, response caching, error mapping.
- `esco_client.py`, `esco_semantics.py`, `esco_offline_index.py`, `esco_matrix.py`, `esco_rag.py` — ESCO runtime layers.
- `homepage_research.py` — public website enrichment.
- `salary/` — salary forecast engine and scenario helpers.

## OpenAI configuration

Configuration can be supplied through Streamlit secrets or environment variables.

Resolution order in `settings_openai.py`:

1. nested Streamlit secret: `[openai] KEY = ...`
2. root Streamlit secret: `KEY = ...`
3. environment variable
4. hard default

Primary keys:

| Key | Purpose |
|---|---|
| `OPENAI_API_KEY` | API key; never commit this value |
| `OPENAI_MODEL` | global model override |
| `DEFAULT_MODEL` | default model when no override is set |
| `LIGHTWEIGHT_MODEL` | extraction-oriented tasks |
| `MEDIUM_REASONING_MODEL` | question plan, brief, boolean/gap/benefit style tasks |
| `HIGH_REASONING_MODEL` | job ad, interview sheet, employment contract tasks |
| `REASONING_EFFORT` | optional reasoning effort after capability gating |
| `VERBOSITY` | optional `text.verbosity` after capability gating |
| `OPENAI_REQUEST_TIMEOUT` | request timeout in seconds; default is 120 |
| `ESCO_VECTOR_STORE_ID` | optional ESCO vector store for RAG |
| `ESCO_RAG_ENABLED` | enables ESCO RAG only when true and vector store ID exists |
| `ESCO_RAG_MAX_RESULTS` | max ESCO RAG hits; default is 8 |

Task-specific output limits follow this pattern for task kinds registered in `settings_openai._TASK_KINDS`:

```text
<TASK_KIND_UPPER>_MAX_OUTPUT_TOKENS
<TASK_KIND_UPPER>_MAX_BULLETS_PER_FIELD
<TASK_KIND_UPPER>_MAX_SENTENCES_PER_FIELD
```

Example:

```toml
# .streamlit/secrets.toml
[openai]
OPENAI_API_KEY = "sk-..."
LIGHTWEIGHT_MODEL = "gpt-4o-mini"
MEDIUM_REASONING_MODEL = "gpt-4o-mini"
HIGH_REASONING_MODEL = "o3-mini"
OPENAI_REQUEST_TIMEOUT = "120"
ESCO_RAG_ENABLED = "false"
```

### Model capability gating

`model_capabilities.py` centralizes model-specific request behavior:

- GPT-5 legacy family (`gpt-5`, `gpt-5-mini`, `gpt-5-nano`, including dated snapshots) does not receive `temperature`.
- GPT-5.4 family receives `temperature` only when `reasoning_effort="none"` is normalized as compatible.
- `reasoning` and `text.verbosity` are only sent to compatible GPT-5 families.
- Valid `reasoning_effort` values are `none`, `minimal`, `low`, `medium`, `high`, `xhigh`; `none` is GPT-5.4-only.
- Fallback families such as `gpt-4o-mini` do not receive GPT-5-specific request fields.

## ESCO configuration

Default ESCO API base URL: `https://ec.europa.eu/esco/api/`.

| Key | Values / default | Purpose |
|---|---|---|
| `ESCO_API_BASE_URL` | default hosted API | API base URL or local mirror/proxy |
| `ESCO_RELEASE_LANE` | `stable` default, `preview` | maps to selected ESCO version |
| `ESCO_SELECTED_VERSION` | optional override | explicit ESCO version |
| `ESCO_API_MODE` | `hosted`, `local` | capability profile |
| `ESCO_DATA_SOURCE_MODE` | `live_api`, `offline_index`, `hybrid` | runtime lookup lane |
| `ESCO_FALLBACK_LANGUAGE` | derived from app language | fallback language for ESCO calls |
| `ESCO_INDEX_STORAGE_PATH` | `data/esco_index` | local index root |
| `ESCO_INDEX_VERSION` | selected ESCO version | local index version |

On Streamlit Cloud, the same ESCO settings can be provided in `.streamlit/secrets.toml`
under `[esco]` with lowercase keys: `api_base_url`, `release_lane`,
`selected_version`, `api_mode`, `data_source_mode`, `fallback_language`,
`index_storage_path`, and `index_version`. Runtime precedence is session state,
then `[esco]` secrets, then environment variables, then defaults.
Normal users cannot edit these technical ESCO runtime settings through the
detail-grade selector. Debug mode may expose sanitized diagnostics and operator
controls for local troubleshooting.

Version mapping:

- `stable -> v1.2.0`
- `preview -> v1.2.1`

Semantic states:

| State | Meaning |
|---|---|
| `degraded_unconfirmed` | no confirmed ESCO anchor; URI-based flows/exports stay disabled |
| `anchored` | confirmed primary anchor |
| `anchored_with_context` | confirmed primary anchor plus secondary context anchors |

Secondary anchors are context/rationale only; they must not inject skills into core exports unless the semantics are explicitly redesigned.

### ESCO/ISCO question-flow context

Confirmed ESCO context is normalized into an optional question context used by the deterministic question compiler. ESCO supplies occupation, skill, knowledge, ISCO, NACE, and regulation context; it does not provide ready-made interview questions or a canonical benefit taxonomy.

Generated base question plans use only the canonical section groups for the active wizard steps. ESCO/ISCO-specific question IDs, skill-group groups, and concept-confirmation questions are owned by the deterministic overlay compiler so the generated base plan does not duplicate or contradict them.

Question-flow provenance records the ordered module keys when data is available:

- `BASE_RECRUITING`
- `ISCO1:<code>`, `ISCO3:<code>`, `ISCO4:<code>`
- `ESCO_OCCUPATION:<uri>`
- `SKILL_GROUP:<canonical_group>`
- `NACE:<code>`
- `REGULATED_PROFESSION`
- `facet.<routing_context>` modules derived from Start-step routing metadata and answered company/team/role context.

Skill groups are mapped into reusable blocks such as `domain_knowledge`, `tools_methods`, `regulation_safety`, `customer_client_interaction`, `documentation_reporting`, `leadership_coordination`, `physical_manual_context`, `digital_data_ai`, `language_communication`, and `transversal_fit`.

Essential and optional ESCO skills/knowledge are converted into capped confirmation questions in the Skills step. ESCO `essential` is treated as a signal to ask the hiring manager, not as an automatic knockout criterion. If ESCO, NACE, matrix, or knowledge metadata is missing, the wizard degrades to the existing generic/family/facet packs and records skipped module reasons in export provenance.

Structured exports may include `occupation_question_context` and extended `question_flow_provenance` fields (`resolved_module_keys`, `skipped_module_reasons`, `source_uris_by_question_id`). These fields are optional and absent/empty in degraded mode.

### ESCO offline index

The repo can build and use a versioned local ESCO lookup index.

Build:

```bash
python scripts/build_esco_index.py --source-dir /path/to/esco_bulk --version v1.2.0
```

Generated artifacts:

```text
data/esco_index/normalized/<version>/concepts.csv
data/esco_index/normalized/<version>/labels.csv
data/esco_index/normalized/<version>/relations.csv
data/esco_index/indexed/<version>/esco_index.sqlite
data/esco_index/indexed/<version>/manifest.json
```

The manifest records source files, hashes, languages, counts, build time, and the normalized/indexed layout. Runtime loading prefers the `indexed/<version>` layout and still accepts the legacy `<version>/esco_index.sqlite` path.

Runtime modes:

- `live_api` — query hosted/local API only.
- `offline_index` — query local index only.
- `hybrid` — query live API first and fall back to local index if unavailable.

The current offline path is lookup-focused and accepts official-CSV-compatible inputs. Full RDF/TTL/XML/JSON-LD ingestion remains future scope.

### ESCO matrix priors

Optional matrix priors add occupation-specific Must/Nice skill candidates and coverage context in the Skills step.

Enable:

```bash
export ESCO_MATRIX_ENABLED=true
export ESCO_MATRIX_PATH=/path/to/esco_matrix.normalized.json  # or .csv
```

Preprocess XLSX to loader-compatible JSON:

```bash
python scripts/build_esco_matrix.py \
  --xlsx /path/to/esco_matrix.xlsx \
  --out /path/to/esco_matrix.normalized.json \
  --version 2026.05
```

Current behavior:

- Live ESCO skills remain the primary source.
- Matrix priors are additive and marked as matrix-derived candidates.
- Matrix coverage runs only for anchored states.
- Merge/dedupe is deterministic by ESCO URI.
- Structured exports may include `esco_matrix_coverage` and `esco_matrix_coverage_context` when available.

## Homepage enrichment

The company step can analyze public company pages for:

- `about`
- `imprint`
- `vision_mission`

After analysis, deterministic website findings are matched against the canonical
`FactKey` registry. Matching values are shown as editable website-finding review
rows with a user-facing target field, value, compact source/status text, and
optional evidence details; confirmed rows are stored as homepage-sourced intake
facts and mirrored into wizard answers for downstream questions, summaries, and
exports. Website matches for open questions can be bookmarked, but they do not
answer questions automatically.

Safety constraints in `homepage_research.py`:

- public HTTP(S) only
- content-type and size checks
- in-process cache
- no sensitive URL/payload logging through usage events
- normalized facts, backward-compatible open-question matches, and review
  decisions stored in session state

## Salary forecast

Salary forecasting is deterministic and uses the current wizard state plus configured benchmark data.

Main modules:

- `salary/benchmarks.py`
- `salary/engine.py`
- `salary/features_esco.py`
- `salary/mapping.py`
- `salary/scenario_lab_builders.py`
- `salary/scenarios.py`
- `salary/types.py`
- `wizard_pages/salary_forecast.py`
- `wizard_pages/salary_forecast_panel.py`

Optional benchmark override:

```bash
export SALARY_BENCHMARK_PATH=/path/to/benchmarks.csv
```

Bundled demo data lives under `data/salary_benchmarks/` and `data/salary_skill_premiums/`.

## Summary artifacts and exports

The visible Summary step starts with `Alles bereit für Recruiting und Hiring-Team`.
It shows editable facts by wizard step, a critical-gap table, a compact artifact grid,
and the active output with refinement requests and downloads. The Recruiting Brief
remains a compatible internal context artifact for downstream generation, but it is
not shown as a required user-facing CTA.

The Summary facts table and per-step fact matrix show steering columns for Salary
impact, requirement stage, and website second-source eligibility. Missing
`before_summary` facts remain hidden from the main fact table but are surfaced in
critical gaps.

Canonical summary artifact IDs:

| ID | Label | Main export formats |
|---|---|---|
| `brief` | Recruiting Brief (internal context) | JSON, Markdown, DOCX |
| `job_ad` | Stellenanzeige | Markdown, DOCX, PDF when `reportlab` is available |
| `interview_hr` | HR Interview Sheet | JSON, DOCX |
| `interview_fach` | Fachbereich Interview Sheet | JSON, DOCX |
| `boolean_search` | Boolean Search Pack | JSON, Markdown |
| `employment_contract` | Arbeitsvertrag Draft | JSON, DOCX |

Additional structured exports include ESCO mapping CSV/JSON and Summary payload fields for intake facts/evidence/resolution, supplemental routing/company/team/role/benefit/interview facts, interview process data, ESCO anchor metadata, ESCO skills, unmapped terms, occupation context, and question-flow provenance.

Job ad DOCX/PDF exports use the uploaded PNG/JPG logo when available; Styleguide input controls generation only and is not included in publishable exports.

When `semantic_export_mode="degraded"`, URI-based ESCO core exports are intentionally suppressed.

## Installation

Prerequisites:

- Python 3.11+
- OpenAI API key for live AI calls

Setup:

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt -c constraints.txt
streamlit run app.py
```

Without constraints, `pip install -r requirements.txt` remains possible, but CI uses `constraints.txt`.

Optional browser smoke dependencies are kept separate:

```bash
pip install -r requirements-e2e.txt -c constraints.txt
python -m playwright install --with-deps chromium
```

Development-only QA tools are installed separately from runtime dependencies:

```bash
pip install -r requirements-dev.txt -c constraints.txt
```

## Verification

### Baseline / CI-equivalent

```bash
pip check
python -m compileall app.py homepage_research.py job_extract_evidence.py job_extract_review_helpers.py summary_artifacts.py summary_esco.py summary_exports.py summary_facts.py summary_job_ad.py usage_events.py components config pages salary scripts tests wizard_pages
python -m pytest -q
python scripts/openai_smoke_test.py --mode all --ci-dry-run-if-no-key --json-only
```

### Docs and wizard contract

Use this smaller set for documentation or routed-step contract changes:

```bash
python -m compileall README.md AGENTS.md CHANGELOG.md
python -m pytest -q tests/test_repo_contract_drift.py tests/test_wizard_contract.py tests/test_quality_gate_config.py tests/test_public_page_links.py
rg -n '01[_]jobad|wizard_pages/01[_]jobad' README.md AGENTS.md CHANGELOG.md
```

The grep command should return no matches after stale Start-step references are removed.

### OpenAI smoke test

Live run:

```bash
export OPENAI_API_KEY="sk-..."  # local only; never commit
python scripts/openai_smoke_test.py --mode all
```

CI/dry run without key:

```bash
python scripts/openai_smoke_test.py --mode all --ci-dry-run-if-no-key --json-only
```

Useful variants:

```bash
python scripts/openai_smoke_test.py --mode all --fail-fast
python scripts/openai_smoke_test.py --mode all --simulate-error timeout --json-only
python scripts/openai_smoke_test.py --mode all --simulate-error connection --json-only
```

The smoke test reports configured mode, effective request kwargs after capability gating, and response metadata when live calls are used. It does not print secrets.

### ESCO smoke test

```bash
python scripts/esco_smoke_test.py --mode all --ci-dry-run-if-unavailable --json-only
```

### Incremental QA gates

The first local quality gate is intentionally low-noise. Ruff runs critical
syntax/name checks only with an explicit baseline for existing Summary-page
noise, Black checks a small allowlist of stable helper modules, mypy checks
selected pure helper modules in permissive baseline mode, and Bandit starts as
an advisory security scan. Tool configuration lives in `pyproject.toml`; the
development dependency surface lives in `requirements-dev.txt`.

```bash
python -m ruff check .
python -m black --check .
python -m mypy
python -m bandit -c pyproject.toml -r .
```

Bandit is non-blocking in CI and may report existing findings until the
security baseline is triaged.

Follow-up hardening should expand Ruff rules, expand Black coverage after an
approved formatting-only change, grow the mypy module allowlist, then make
Bandit blocking or add Semgrep once findings are triaged.

### Optional Playwright smoke tests

Browser-near Streamlit smoke tests are opt-in and use only synthetic fixture data.
Normal `pytest -q` runs skip them unless `CS_RUN_E2E=1` is set. The marker is
registered in `pytest.ini`, and Playwright dependencies live in
`requirements-e2e.txt`.

```bash
pip install -r requirements-e2e.txt -c constraints.txt
python -m playwright install --with-deps chromium
CS_RUN_E2E=1 python -m pytest -q tests/e2e
```

Useful environment overrides:

- `CS_E2E_PORT=8765`
- `CS_E2E_STARTUP_TIMEOUT=60`

## GitHub Actions CI

`.github/workflows/ci.yml` runs on pull requests and pushes to `main`:

Current job IDs are `qa`, `security`, `test`, and optional `e2e`.

1. `qa`: blocking Ruff, scoped Black, and scoped mypy gates with `requirements-dev.txt`
2. `security`: advisory Bandit security scan with `continue-on-error`
3. `test`: Python 3.11 setup, dependency install with `requirements.txt` and `constraints.txt`, `pip check`, `compileall`, `pytest -q`, and OpenAI smoke dry-run without requiring an API key

The optional Playwright smoke job is available through manual workflow dispatch
with `run_e2e=true` as job ID `e2e`. It installs `requirements-e2e.txt`,
installs Chromium, and runs `CS_RUN_E2E=1 python -m pytest -q tests/e2e`.

## Debugging and incident reports

Use:

- `docs/debugging_incident_template.md`
- `docs/team_runbook_debugging.md`

A useful incident report must include:

- exact repro steps
- expected vs. actual behavior
- full traceback including final `ExceptionType: message` line
- commit/branch/deploy timestamp
- relevant non-sensitive config source information

Do not include API keys, OAuth tokens, raw prompts, full uploaded documents, PII, or credential-bearing logs.

## Developer notes

- Keep `README.md` and `AGENTS.md` synchronized with runtime behavior when step flow, modes, exports, configuration, or verification commands change.
- Prefer canonical constants/enums over ad-hoc strings.
- Update state init, reset logic, UI, exports, and tests together.
- Preserve degraded behavior for optional external systems such as ESCO, OpenAI, RAG, PDF export, and homepage fetches.
