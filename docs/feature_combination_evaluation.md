# Feature Combination Evaluation

Use this runbook to compare app configurations by user value instead of raw feature count. The evaluation must use synthetic vacancy cases only. Do not store raw personal data, credential values, full homepage content, prompts, or generated artifacts in the scoring CSV.

## Goal

Pick the configuration with the best balance of intake quality, hiring value, runtime, cost, robustness, privacy, and export readiness.

The expected default candidate is:

```text
standard UI + confirmed ESCO anchor where available + selective ESCO RAG for gap/skill suggestions + high model only for final artifacts
```

## Evaluation Matrix

Score each criterion from 1 to 5:

| Criterion | What to score |
|---|---|
| `intake_quality` | Role profile, skills, benefits, interview process, and open questions are captured correctly. |
| `hiring_value` | Summary and recruiting outputs help with job ads, interview prep, search strings, and briefing. |
| `user_effort` | The flow avoids unnecessary questions, clicks, and manual repairs. |
| `speed` | Time to a usable Summary and at least one generated artifact. |
| `cost` | OpenAI calls, RAG calls, ESCO lookups, and artifact-generation cost stay proportionate. |
| `robustness` | The flow works with missing ESCO anchors, missing homepage data, weak jobspecs, and no API key dry-runs. |
| `privacy` | PII reduction, consent, degraded fallbacks, and sensitive logging constraints remain intact. |
| `export_readiness` | Summary, ESCO exports, Markdown/JSON/DOCX/PDF output remain consistent. |

## Combinations

| ID | Configuration |
|---|---|
| `baseline` | `standard` UI, ESCO `live_api`, RAG off, default model routing, homepage optional. |
| `fast` | `quick` UI, ESCO degraded/optional, RAG off, lightweight extraction and question plan, external enrichment off. |
| `quality` | `expert` UI, ESCO anchor required when available, optional ESCO RAG, stronger models for artifacts. |
| `balanced` | `standard` UI, ESCO anchor required when available, RAG only for gap/skill suggestions, high model only for final artifacts. |
| `offline_resilience` | `standard` UI, ESCO `offline_index` or `hybrid`, RAG off, no external enrichment except OpenAI. |

## Synthetic Cases

Run at least these five cases:

| Case ID | Coverage |
|---|---|
| `tech_senior_good_salary_homepage` | Technical senior role, good jobspec, salary present, homepage available. |
| `tech_junior_sparse_no_salary` | Technical junior role, sparse jobspec, no salary. |
| `commercial_medior_good_homepage` | Commercial medior role, good jobspec, homepage available. |
| `regulated_senior_sparse_salary` | Regulated senior role, weak input, salary present. |
| `operations_medior_bullets_only` | Operations role with bullet-only source text. |

## Workflow

1. Run the technical baseline:

   ```bash
   python -m pytest -q
   python scripts/openai_smoke_test.py --mode all --ci-dry-run-if-no-key --json-only
   ```

2. Run the deterministic offline evaluation:

   ```bash
   python scripts/evaluate_feature_combinations.py --json-only
   ```

3. For the top-ranked combination and at least one fallback combination, complete the app flow through Summary with the synthetic cases.

4. Record only non-sensitive manual observations in a local note or issue:

   - `usable_summary`: `true` when Summary can be used without manual repair.
   - `high_quality_artifacts`: count of generated artifacts that are ready or nearly ready.
   - `open_questions_count`, `completion_minutes`, `manual_corrections_count`, `degraded_state_count`, `error_count`.
   - 1-5 scores for all criteria.

5. Run targeted checks after any code/config change made because of the evaluation:

   ```bash
   python -m pytest -q tests/test_ui_mode_flow.py tests/test_question_limits.py tests/test_question_progress.py
   python -m pytest -q tests/test_esco_client.py tests/test_esco_rag.py tests/test_esco_offline_contract.py
   python -m pytest -q tests/test_salary_*.py tests/tests_test_salary_benchmarks.py
   python -m pytest -q tests/test_summary_*.py tests/test_additional_task_generators.py
   ```

## Decision Rule

A combination is eligible when it passes all of these checks:

- At least 80% of cases have `usable_summary=true` and `high_quality_artifacts >= 2`.
- Mean score is at least as high as `balanced`.
- `error_count` totals zero across the evaluated cases.
- Costs, user effort, and completion time are not materially worse than `balanced`.

Choose the highest-ranked eligible combination from the script output. If no combination is eligible, keep the current default and treat the weakest criteria as product backlog items.
