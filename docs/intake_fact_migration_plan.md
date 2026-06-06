# Intake Fact Migration Plan

## Summary

This plan defines a staged migration from scattered intake answers and summary-only derived rows toward a canonical intake Fact Registry. It is documentation only; do not implement PR 1-5 from this document until a follow-up task explicitly asks for one phase.

The migration goal is to make intake facts addressable, traceable, and reusable across UI state, summary artifacts, exports, prompt construction, and readiness checks without changing user-visible behavior during the initial compatibility phases.

## Current Baseline

- Canonical session keys, step IDs, and labels live in `constants.py`.
- Session defaults and reset behavior live in `state.py`.
- Wizard pages collect answers through Streamlit session state and page-local helpers.
- Summary facts are currently assembled in `wizard_pages/08_summary.py` from available state, generated artifacts, and derived values.
- There is no canonical Fact Registry, no canonical `fact_key` contract, and no Evidence Store yet.

## Migration Principles

- Keep each PR small and reviewable.
- Preserve existing UI behavior, session-state behavior, exports, and prompt output unless a PR explicitly changes them.
- Introduce canonical constants before using new identifiers in UI, exports, prompts, or tests.
- Prefer adapters and compatibility wrappers before removing legacy state reads.
- Keep Fact Registry, Evidence Store, readiness, and export behavior separable so failures are easy to isolate.
- Do not mix salary, ESCO, Summary Readiness, or design-system changes into foundational fact migration PRs unless they are direct consumers of a completed fact contract.

## Proposed PR Sequence

### PR 1: Fact Contract Skeleton

Add the canonical fact vocabulary without changing runtime behavior.

- Define the minimum fact identity model: canonical `fact_key`, label, step ownership, value type, and persistence intent.
- Add constants/enums for fact IDs in `constants.py`.
- Add typed helper structures where needed, but avoid wiring them into wizard pages yet.
- Add contract tests for uniqueness, naming stability, and step ownership.
- Keep existing session-state keys and summary generation untouched.

### PR 2: Registry Initialization and Legacy Read Adapters

Introduce a read-only registry layer that can mirror existing session state.

- Initialize an empty or mirrored registry in `state.py` without replacing existing session-state values.
- Add adapter helpers that read legacy values and expose canonical fact entries.
- Ensure reset paths clear or rebuild registry state consistently.
- Add tests for default state, reset behavior, and partial legacy-state compatibility.
- Do not migrate wizard writes yet.

### PR 3: Wizard Write-Through

Update wizard pages to write canonical facts while preserving legacy session-state keys.

- For each migrated field, write through to the Fact Registry and keep the existing session-state key updated.
- Start with low-risk fields from one wizard step before expanding to the rest.
- Keep UI labels, validation, progress, and completion behavior unchanged.
- Add tests proving legacy state and canonical facts remain synchronized.
- Do not change exports or prompt construction in this PR.

### PR 4: Summary, Export, and Prompt Consumers

Move downstream consumers to read canonical facts through adapters.

- Update summary fact table assembly to prefer canonical facts while retaining legacy fallbacks.
- Update export payload construction to use canonical fact identities.
- Update prompt construction only where existing behavior can be preserved exactly.
- Add tests for summary facts, export payloads, and prompt payload compatibility.
- Keep Salary, ESCO, and Summary Readiness domain behavior unchanged unless they only consume the new adapter output.

### PR 5: Evidence Store and Legacy Cleanup

Add evidence tracking and remove only proven-dead legacy paths.

- Define Evidence Store entries for source type, source label, confidence, timestamps, and optional raw excerpts.
- Link evidence to canonical facts without storing secrets, credentials, or personal data in logs.
- Remove legacy-only duplicate reads after tests prove canonical paths cover them.
- Add regression tests for evidence linkage, privacy-safe redaction, and reset behavior.
- Update README and docs to reflect the new canonical fact lifecycle.

## Verification Strategy

Use the smallest relevant verification set per PR, then broaden when contracts cross module boundaries.

- Contract and state work: `python -m pytest -q tests/test_state_reset.py tests/test_wizard_contract.py`
- Summary and export consumers: `python -m pytest -q tests/test_summary_*.py tests/test_additional_task_generators.py`
- Prompt and OpenAI routing consumers: `python -m pytest -q tests/test_openai_smoke_modes.py tests/test_generate_vacancy_brief.py`
- Baseline syntax and regression pass: `python -m compileall app.py components config pages salary scripts tests wizard_pages` and `python -m pytest -q`

Ruff findings that predate a PR should be reported but not fixed unless the PR scope explicitly includes lint cleanup.

## Open Decisions

- Exact canonical `fact_key` naming format.
- Whether fact values are stored as plain typed values, structured envelopes, or both.
- Whether evidence is mandatory for all facts or only AI-derived/imported facts.
- How much historical legacy state should remain as compatibility surface after PR 5.

## Non-Goals For This Plan

- No implementation of Fact Registry in this documentation-only change.
- No implementation of `fact_key`.
- No Evidence Store implementation.
- No ESCO, Salary, Summary Readiness, design-system, or wizard-page behavior changes.
- No test changes and no lint auto-fixes.

## Proposed Registry / Schema Shape

The first implementation phase should introduce the canonical vocabulary before any runtime migration.

### Fact Identity

A canonical fact should have at least:

- `fact_key`: stable machine-readable identifier
- `label`: human-readable label for debugging and documentation
- `step_key`: owning wizard step
- `target_path`: optional existing `JobAdExtract` or legacy target path
- `value_type`: expected value shape, for example `string`, `list[string]`, `bool`, `date`, `money_range`, or `object`
- `criticality`: `critical`, `important`, or `optional`
- `source_priority`: ordered read preference, for example user answer before extracted value
- `artifact_dependencies`: downstream outputs affected by this fact
- `esco_relevant`: whether this fact affects ESCO occupation or skill workflows
- `legacy_aliases`: old keys, labels, or target paths that still need compatibility support

### Question Schema

`Question.id` must remain the UI/widget/history identity.

A future schema extension may add:

- `fact_key: str | None`
- `prefill_paths: list[str]`
- `criticality: str | None`
- `answer_cost: int | float | None`
- `artifact_dependencies: list[str]`

These fields must be optional and backward-compatible. Existing QuestionPlans without `fact_key` must continue to validate, normalize, render, and export.

## Greppable Anchors

Use sparse comments only where they improve reviewability:

- `FACT_REGISTRY`: canonical intake fact definitions
- `FACT_KEY_NORMALIZATION`: preserve `Question.id` identity
- `FACT_RESOLVER`: read-through compatibility layer
- `EVIDENCE_STORE`: additive mirror, not initial source of truth
- `SUMMARY_FACTS`: registry-backed readiness and export rows
- `LEGACY_FACT_ALIASES`: compatibility for old QuestionPlans and legacy state

## Compatibility Risks

- Old QuestionPlans lack `fact_key`; all new fields must have explicit defaults.
- `Question.id` must not be replaced in `answers`, `answer_meta`, widget keys, or `depends_on`.
- Structured Outputs can break if schema fields are made required too early.
- Summary/export changes can accidentally rename legacy JSON keys.
- Session State migrations can invalidate existing user sessions if old keys are removed.
- ESCO state has legacy aliases and helper logic; registry reads must not bypass canonical ESCO helpers.
- Salary, Summary Readiness, and artifact generation should not become implicit consumers before the fact contract is stable.

## Rollback Strategy

### PR 1 Rollback

Remove the fact contract skeleton and optional schema fields. Existing QuestionPlans remain valid because runtime behavior has not changed.

### PR 2 Rollback

Disable registry initialization and legacy read adapters. Continue reading existing Session State values directly.

### PR 3 Rollback

Stop writing canonical facts and keep legacy wizard writes as the only source of truth.

### PR 4 Rollback

Restore summary, export, and prompt construction to their previous mixed-source builders while keeping the registry unused.

### PR 5 Rollback

Disable evidence writes and keep canonical facts without evidence metadata until privacy and reset behavior are stable.

## Acceptance Criteria

- `Question.id` remains the stable UI/widget/history identity.
- Existing QuestionPlans without `fact_key` validate and render.
- No existing Session State key is removed during the compatibility phases.
- New registry or evidence payloads are additive.
- Summary and export legacy keys remain stable unless a dedicated PR explicitly changes them.
- Tests prove old and new paths are compatible before any legacy path is removed.
- Each implementation PR is small enough to review independently.
- No production API calls, secrets, or PII are introduced in tests or logs.
