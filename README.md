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
- There is no repo-local Ruff/Black/Mypy/Pyright configuration; CI relies on install checks, compilation, pytest, and OpenAI smoke dry-run.
- `wizard_pages/01a_jobspec_review.py` and `wizard_pages/03_team.py` are legacy/non-routable modules.

## Wizard flow

The active visible route is defined by `constants.STEPS` and enforced by `wizard_pages/__init__.py`.

| Order | Step key | UI label | Main module | Purpose |
|---:|---|---|---|---|
| 1 | `landing` | Start | `wizard_pages/00_landing.py` + `wizard_pages/jobad_intake.py` | Landing page plus jobspec intake phases A/B/C |
| 2 | `company` | Unternehmen | `wizard_pages/02_company.py` | Company context, team context, homepage enrichment |
| 3 | `role_tasks` | Rolle & Aufgaben | `wizard_pages/04_role_tasks.py` | Role/task curation, ESCO/context/AI suggestions, salary block |
| 4 | `skills` | Skills & Anforderungen | `wizard_pages/05_skills.py` | Jobspec/ESCO/AI skills, normalization, matrix priors, unmapped-term decisions |
| 5 | `benefits` | Benefits & Rahmenbedingungen | `wizard_pages/06_benefits.py` | Benefits and operating conditions from jobspec/context/AI |
| 6 | `interview` | Interviewprozess | `wizard_pages/07_interview.py` | Interview values, candidate communication, internal roles/timing |
| 7 | `summary` | Zusammenfassung | `wizard_pages/08_summary.py` | Readiness, facts, action hub, artifacts, exports |

### Start step phases

The Start step contains the former review flow directly:

- **Phase A — Quelle & Datenschutz:** upload/manual text, active source handling, consent, PII reduction, UI mode, ESCO operating settings.
- **Phase B — Extraktion prüfen:** editable identified-information block with confidence/evidence where available.
- **Phase C — ESCO-Suche:** primary occupation anchor, optional secondary context anchors, degraded fallback when no anchor is confirmed.

There is no separate visible `jobspec_review` step.

## UI modes

The app supports three global UI modes:

| Stored value | German label | Intended behavior |
|---|---|---|
| `quick` | `schnell` | Reduced question depth, compact detail groups |
| `standard` | `ausführlich` | Default balanced depth, compact detail groups |
| `expert` | `vollumfänglich` | Full depth, detail groups open by default, extended expert controls |

The mode is controlled through the sidebar preference center and the Start step. It affects visible question depth through `question_limits.py` and compact/detail behavior through shared UI helpers.

Adaptive question ranking can use optional question metadata: `impact_targets`, `acquisition_cost`, and `info_gain_score`. These fields let high-impact unanswered questions rise above lower-value detail questions without changing the visible step contract or existing UI modes.

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

## Architecture map

### Canonical contracts

- `constants.py` — session keys, step IDs, UI modes, ESCO modes, fact registry, artifact IDs.
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

Safety constraints in `homepage_research.py`:

- public HTTP(S) only
- content-type and size checks
- in-process cache
- no sensitive URL/payload logging through usage events
- normalized facts and open-question matches stored in session state

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

Canonical summary artifact IDs:

| ID | Label | Main export formats |
|---|---|---|
| `brief` | Recruiting Brief | JSON, Markdown, DOCX |
| `job_ad` | Stellenanzeige | DOCX, PDF when `reportlab` is available |
| `interview_hr` | HR Interview Sheet | JSON, DOCX |
| `interview_fach` | Fachbereich Interview Sheet | JSON, DOCX |
| `boolean_search` | Boolean Search Pack | JSON, Markdown |
| `employment_contract` | Arbeitsvertrag Draft | JSON, DOCX |

Additional structured exports include ESCO mapping CSV/JSON and Summary payload fields for intake facts/evidence/resolution, interview process data, ESCO anchor metadata, ESCO skills, unmapped terms, occupation context, and question-flow provenance.

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

## Verification

### Baseline / CI-equivalent

```bash
pip check
python -m compileall app.py homepage_research.py job_extract_evidence.py job_extract_review_helpers.py summary_artifacts.py summary_esco.py summary_exports.py summary_facts.py summary_job_ad.py usage_events.py components config pages salary scripts tests wizard_pages
python -m pytest -q
python scripts/openai_smoke_test.py --mode all --ci-dry-run-if-no-key --json-only
```

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

## GitHub Actions CI

`.github/workflows/ci.yml` runs on pull requests and pushes to `main`:

1. Python 3.11 setup
2. dependency install with `requirements.txt` and `constraints.txt`
3. `pip check`
4. `compileall`
5. `pytest -q`
6. OpenAI smoke dry-run without requiring an API key

No separate lint/type job is configured in this snapshot.

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
