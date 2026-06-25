# Cognitive Staffing — Recruiting-Briefing

Streamlit app for structured Recruiting-Briefing, jobspec extraction, ESCO/EURES enrichment, salary forecasting, interview-process capture, and generation of recruiting outputs with OpenAI structured outputs.

The current implementation is not a loose demo. It is a stateful workflow application with tight coupling between canonical constants, session state, Pydantic schemas, wizard UI, fact/evidence handling, summary outputs, and exports.

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
11. Summary readiness dashboard, action hub, recruiting output generation, and exports.
12. Privacy-safe usage events for lightweight observability.

Known partials / explicit non-goals in this snapshot:

- Full official ESCO bulk-dataset ingestion is not implemented; the offline index path is lookup-focused.
- ESCO matrix priors are optional and do not include ISCO distribution benchmarking or advanced coherence metrics.
- Repo-local QA config is intentionally scoped in `pyproject.toml`: Ruff, Black, mypy, Pyright, and Bandit run through `requirements-dev.txt`.
- `wizard_pages/01a_jobspec_review.py` and `wizard_pages/03_team.py` are legacy/non-routable modules.

## Wizard flow

The full routable contract is defined by `constants.STEPS` and enforced by `wizard_pages/__init__.py`. The intro route is a short pre-start information page. Sidebar navigation, process progress, and completion/readiness metrics use `constants.OPERATIONAL_WIZARD_STEP_KEYS` / `constants.PROGRESS_STEP_KEYS`.

Pre-start route:

| Step key | UI label | Main module | Purpose |
|---|---|---|---|
| `intro` | Einleitung | `wizard_pages/00_intro.py` | Introductory context before the operational flow starts |

Operational flow:

| Order | Step key | UI label | Main module | Purpose |
|---:|---|---|---|---|
| 1 | `landing` | Start | `wizard_pages/00_landing.py` + `wizard_pages/jobad_intake.py` | Landing page plus jobspec intake phases A/B/C |
| 2 | `company` | Unternehmen | `wizard_pages/02_company.py` | Employer profile, website evidence, ESCO context, company questions, team/reporting |
| 3 | `role_tasks` | Rolle & Aufgaben | `wizard_pages/04_role_tasks.py` | Work model/location, non-negotiables/compliance, role/task curation, ESCO/context/AI suggestions, salary block |
| 4 | `skills` | Skills & Anforderungen | `wizard_pages/05_skills.py` | Jobspec/ESCO/AI skills, normalization, matrix priors, unmapped-term decisions |
| 5 | `benefits` | Benefits & Rahmenbedingungen | `wizard_pages/06_benefits.py` | Benefits and operating conditions from jobspec/context/AI |
| 6 | `interview` | Interviewprozess | `wizard_pages/07_interview.py` | Interview values, candidate communication, internal roles/timing |
| 7 | `summary` | Zusammenfassung | `wizard_pages/08_summary.py` | Readiness, facts, action hub, recruiting outputs, exports |

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
| `quick` | `schnell` | Fast path with compact detail groups, 20% of dependency-visible `core` questions, and strict per-step caps |
| `standard` | `ausführlich` | Lean default using 35% of dependency-visible `core` and `standard` questions with per-step caps |
| `expert` | `vollumfänglich` | Full intake using dependency-visible `core`, `standard`, and conditional `detail` questions |

The mode is controlled through the sidebar preference center and the Start step. It affects the number of visible follow-up inputs through `question_limits.py` and compact/detail behavior through shared UI helpers, but does not reduce extraction, enrichment, output, export, or forecast quality. `quick` keeps the essential app functions visible and asks the highest-ranked 20% of eligible core questions per step, capped at 1-2 questions in operational intake steps. `standard` is the default first-run mode and asks the highest-ranked 35% of eligible `core` + `standard` questions per step, capped at 3-5 questions depending on the step. `expert` adds deep conditional questions that can become relevant in specific cases. Expensive or secondary blocks such as source comparison, extracted snapshots, review panels, live previews, and salary forecast render lazily in lean modes; salary forecast remains on-demand.

Wizard design is a separate preference stored as `wizard_design`. `classic` (`Klassisch`) is the default and preserves the existing page density. `focus` (`Fokus`) keeps the primary decision workspace visible and moves secondary evidence, previews, reviews, and technical detail blocks behind explicit drill-downs. The design choice is available in the sidebar preference center and the Start step, and it does not change routing, schemas, OpenAI calls, ESCO anchoring, salary forecasting, or exports.

Adaptive question ranking can use optional question metadata: `impact_targets`, `acquisition_cost`, and `info_gain_score`. These fields let high-impact unanswered questions rise above lower-value detail questions without changing the visible step contract or existing UI modes.

To compare UI mode, ESCO, RAG, model-routing, and enrichment combinations, use the evaluation runbook in `docs/feature_combination_evaluation.md` and the offline scoring helper:

```bash
python scripts/evaluate_feature_combinations.py --json-only
```

Quality eval fixtures for extraction, ESCO mapping, retrieval faithfulness,
latency, and token cost live in `evals/*.jsonl`. The CI threshold gate writes a
CSV summary and fails when configured quality thresholds are missed:

```bash
python scripts/run_quality_evals.py \
  --fixtures evals \
  --output reports/evals/summary.csv \
  --json-output reports/evals/summary.json \
  --enforce-thresholds
```

## UI language

The UI language supports German (`de`) and English (`en`). German remains the
default and fallback. The visible language selector on the intro, Start, and
public pages syncs `SSKey.LANGUAGE` plus `UI_PREFERENCE_UI_LANGUAGE`; the
browser choice is also mirrored through the `lang` query parameter and
origin-local browser storage so it survives reloads and public-page navigation.

## Draft save and resume

The app works without a backend-specific user store. Users can intentionally
save progress from the sidebar via `Entwurf speichern`, which downloads a
schema-versioned JSON draft. The matching `Entwurf laden` action restores only
allowlisted, canonical `SSKey` vacancy domains and then shows a resume banner
with the restored wizard step.

Draft JSON excludes OpenAI settings, secrets, caches, usage events, debug/error
state, uploaded file metadata/signatures, and logo binary payloads. It does
include the vacancy content required to continue later, such as source text,
reviewed facts, answers, ESCO anchors, selected role/tasks/skills/benefits,
salary scenario state, interview process data, and generated summary artifacts.

## Product readiness contracts

Product-readiness contracts are documented in:

- [`docs/persistence_strategy.md`](docs/persistence_strategy.md) - current JSON draft/resume strategy, excluded state, and future adapter boundary.
- [`docs/legacy_wizard_modules.md`](docs/legacy_wizard_modules.md) - archived wizard modules, replacement paths, route guardrails, and removal prerequisites.
- [`docs/definition_of_done.md`](docs/definition_of_done.md) - beta Definition of Done, Summary release credibility, DE/EN parity, focused outputs, and no-live-API smoke expectations.
- [`reports/README.md`](reports/README.md) - historical report archive index and current-source-of-truth warning.

## Information acquisition model

The intake process combines several evidence streams:

| Source | Main modules | Stored/used as |
|---|---|---|
| Jobspec extraction | `llm_client.py`, `schemas.py`, `wizard_pages/jobad_intake.py` | `JobAdExtract`, intake facts, evidence, base question plan |
| Manual review/input | `job_extract_review_helpers.py`, wizard pages, `state.py` | confirmed answers/facts with manual precedence |
| ESCO/EURES context | `esco_client.py`, `esco_semantics.py`, `eures_mapping.py` | occupation anchors, skill suggestions, task context, export metadata |
| Homepage enrichment | `homepage_research.py`, `wizard_pages/02_company.py` | company/team facts and open-question matches |
| AI suggestions | `llm_client.py`, role/skills/benefits pages | source-pill suggestions and optional output inputs |
| Salary engine | `salary/`, salary forecast panels | deterministic forecast result and scenario state |

Manual corrections remain authoritative over extracted values. Jobspec assumptions/gaps are not collected as a single Start-step backlog; they are routed to the best matching downstream step.

Canonical intake fact evidence also carries a resolution status (`confirmed`, `inferred`, `assumed`, `conflicted`, or `missing`). Structured Summary exports include `intake_fact_resolution` so downstream consumers can distinguish confirmed facts from inferred, assumed, conflicted, or still-missing information without changing the legacy fact values.

Fact definitions in `constants.INTAKE_FACTS` also carry steering metadata: `salary_impact` separates direct Salary drivers from quality/uncertainty inputs, `requirement_stage` distinguishes facts required before Summary from facts required before recruiting output generation, and `website_enrichable` marks fields that can be reviewed against homepage evidence.

The canonical fact registry also covers downstream decision points from the improvement report: company and team context, role outcomes and travel profile, typed skill requirements, variable pay and offer constraints, work authorization, start-date flexibility, and interview assessment/scorecard fields.

## Architecture map

### Canonical contracts

- `constants.py` — session keys, step IDs, UI modes, ESCO modes, fact registry, artifact IDs.
- `state_store.py` — typed facade over canonical `SSKey` session-state storage; new code should prefer it for high-value state domains.
- `state.py` — session defaults, vacancy reset behavior, answer/fact adapters.
- `schemas.py` — Pydantic contracts for jobspec extraction, question plans, briefs, and generated outputs.
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
| `HIGH_REASONING_MODEL` | job ad and interview sheet tasks |
| `REASONING_EFFORT` | optional reasoning effort after capability gating |
| `VERBOSITY` | optional `text.verbosity` after capability gating |
| `OPENAI_REQUEST_TIMEOUT` | request timeout in seconds; default is 120 |
| `ESCO_VECTOR_STORE_ID` | optional ESCO vector store for RAG |
| `ESCO_RAG_ENABLED` | enables ESCO RAG only when true and vector store ID exists |
| `ESCO_RAG_MAX_RESULTS` | max ESCO RAG hits, capped at 50; default is 8 |
| `ESCO_RAG_REWRITE_QUERY` | toggles vector search query rewriting; default is true |
| `ESCO_RAG_RANKER` | vector search ranker; default is `auto` |
| `ESCO_RAG_SCORE_THRESHOLD` | optional vector search score threshold; default is 0.35 |
| `ESCO_RAG_CHUNK_SIZE_TOKENS` | indexing chunk profile size hint; default is 800 |
| `ESCO_RAG_CHUNK_OVERLAP_TOKENS` | indexing chunk profile overlap hint; default is 400 |

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
ESCO_RAG_REWRITE_QUERY = "true"
ESCO_RAG_SCORE_THRESHOLD = "0.35"
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
- DNS validation for public IP targets only
- redirect limits with target and final-URL revalidation
- content-type and size checks before payload processing
- positive in-process cache plus TTL-based negative cache for repeated failures
- optional deployment allowlist via `HOMEPAGE_FETCH_ALLOWED_DOMAINS`
- no sensitive URL/payload logging through usage events
- normalized facts, backward-compatible open-question matches, and review
  decisions stored in session state

`HOMEPAGE_FETCH_ALLOWED_DOMAINS` is disabled by default. When set, use comma-
or whitespace-separated domains such as `example.com intranet.example`; each
entry allows the exact domain and its subdomains by dot-boundary matching.

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

## Summary recruiting outputs and exports

The visible Summary step starts with `Alles bereit für Recruiting und Hiring-Team`.
It shows editable facts by wizard step, a critical-gap table, a compact output grid,
and the active output with refinement requests and downloads. The Recruiting Brief
remains a compatible internal context output for downstream generation, but it is
not shown as a required user-facing CTA.

The Summary facts table and per-step fact matrix show steering columns for Salary
impact, requirement stage, and website second-source eligibility. Missing
`before_summary` facts remain hidden from the main fact table but are surfaced in
critical gaps.

Active Summary artifact IDs are governed by
`constants.SUMMARY_ACTIVE_ARTIFACT_IDS`; known compatibility IDs remain in
`constants.SUMMARY_ARTIFACT_IDS` only for draft loading and migration safety.
Current active IDs and user-facing labels:

| ID | Label | Main export formats |
|---|---|---|
| `brief` | Recruiting Brief (internal context) | JSON, Markdown, DOCX |
| `job_ad` | Stellenanzeige | Markdown, DOCX, PDF when `reportlab` is available |
| `interview_hr` | HR-Sheet | JSON, DOCX |
| `interview_fach` | Fachbereich-Sheet | JSON, DOCX |
| `boolean_search` | Suchstrings | JSON, Markdown |

Additional structured exports include ESCO mapping CSV/JSON and Summary payload fields for intake facts/evidence/resolution, supplemental routing/company/team/role/benefit/interview facts, interview process data, ESCO anchor metadata, ESCO skills, unmapped terms, occupation context, and question-flow provenance.

Job ad DOCX/PDF exports use the uploaded PNG/JPG logo when available; Styleguide input controls generation only and is not included in publishable exports.

When `semantic_export_mode="degraded"`, URI-based ESCO core exports are intentionally suppressed.

The former `employment_contract` output is archived and hidden from the active
Summary product flow. Legacy draft JSON may still contain its state key so older
saved drafts can load without crashing.

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

Development and test-only QA tools are installed separately from runtime dependencies:

```bash
pip install -r requirements-dev.txt -c constraints.txt
```

## Verification

### Baseline / CI-equivalent

```bash
pip check
python scripts/check_repo_hygiene.py
python -m compileall app.py homepage_research.py job_extract_evidence.py job_extract_review_helpers.py summary_artifacts.py summary_esco.py summary_exports.py summary_facts.py summary_job_ad.py usage_events.py components config pages salary scripts tests wizard_pages
python -m pytest -q tests/test_repo_contract_drift.py tests/test_wizard_contract.py tests/test_quality_gate_config.py tests/test_public_page_links.py tests/test_constants_import_contract.py tests/test_schema_contracts.py --junitxml=reports/junit/contract.xml
python -m pytest -q tests --ignore=tests/e2e --ignore=tests/apptest --junitxml=reports/junit/unit.xml
python -m pytest -q tests/apptest --junitxml=reports/junit/apptest.xml
python scripts/openai_smoke_test.py --mode all --ci-dry-run-if-no-key --json-only > reports/openai-smoke.json
python scripts/run_quality_evals.py --fixtures evals --output reports/evals/summary.csv --json-output reports/evals/summary.json --enforce-thresholds
```

CI uploads JUnit reports from `reports/junit/*.xml`. Historical analysis files
under `reports/` are archived through [`reports/README.md`](reports/README.md)
and are not source-of-truth runtime docs.

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
selected pure helper modules in permissive baseline mode, Pyright checks the
same selected helper-module allowlist in basic mode, and the path-only repo
hygiene guard blocks committed local secrets, credentials, caches, and generated
exports without reading file contents. Bandit, Gitleaks content scanning, and
tracked-artifact drift scanning remain advisory in CI so existing baselines can
be triaged without blocking the fast local/unit path. Tool configuration lives
in `pyproject.toml`; the development dependency surface lives in
`requirements-dev.txt`.

```bash
python scripts/check_repo_hygiene.py
python -m ruff check .
python -m black --check .
python -m mypy
python -m pyright
python -m bandit -c pyproject.toml -r .
gitleaks git --redact .
python scripts/check_tracked_artifacts.py
```

The repo hygiene guard scans tracked file paths only and reports only paths and
rule names. Gitleaks is installed separately for local use; CI uses the official
Gitleaks Action. Gitleaks, Bandit, and the artifact drift scan are non-blocking
in CI and may report existing findings until the security/artifact baselines are
triaged. The artifact drift scan reports only paths and reasons, not file
contents.

Follow-up hardening should expand Ruff rules, expand Black coverage after an
approved formatting-only change, grow the mypy module allowlist, then make
the Pyright and mypy module allowlists together, then make Bandit blocking or
add Semgrep once findings are triaged.

### Optional Playwright smoke tests

Browser-near Streamlit smoke tests are opt-in and use only synthetic fixture data.
Normal `pytest -q` runs skip them unless `CS_RUN_E2E=1` is set. The marker is
registered in `pytest.ini`, and Playwright dependencies live in
`requirements-e2e.txt`.

```bash
pip install -r requirements-e2e.txt -c constraints.txt
python -m playwright install --with-deps chromium
CS_RUN_E2E=1 python -m pytest -q tests/e2e --junitxml=reports/junit/browser-smoke.xml
```

Useful environment overrides:

- `CS_E2E_PORT=8765`
- `CS_E2E_STARTUP_TIMEOUT=60`
- `CS_DEPLOYED_BASE_URL=https://example.streamlit.app` also enables the
  deployed landing-page smoke test inside `tests/e2e`.

## GitHub Actions CI

`.github/workflows/ci.yml` runs on pull requests and pushes to `main`:

Current job IDs are `qa`, `contract`, `unit`, `apptest`, `browser_smoke`, and
`security`.

1. `qa`: blocking repo hygiene, Ruff, scoped Black, scoped mypy, and scoped Pyright gates with `requirements-dev.txt`
2. `contract`: blocking fast repo/wizard/config contract tests with JUnit upload
3. `unit`: blocking Python unit suite excluding AppTest and E2E tests, plus `pip check`, `compileall`, and OpenAI smoke dry-run report upload
4. `apptest`: blocking Streamlit AppTest smoke tests through `streamlit.testing.v1`
5. `browser_smoke`: advisory Playwright Streamlit smoke tests with JUnit upload
6. `security`: advisory Gitleaks, Bandit, and tracked-artifact drift scans with `continue-on-error`

The Playwright smoke job runs advisory on pull requests and pushes. It is also
available through manual workflow dispatch with `run_e2e=true` as job ID
`browser_smoke`. It installs `requirements-e2e.txt`, installs Chromium, and runs
`CS_RUN_E2E=1 python -m pytest -q tests/e2e --junitxml=reports/junit/browser-smoke.xml`.

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
