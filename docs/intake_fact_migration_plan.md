# Intake Fact Migration Plan

## Summary

This plan defines a staged migration from scattered intake answers and summary-only derived rows toward a canonical intake Fact Registry. The initial fact vocabulary, additive `SSKey.INTAKE_FACTS` state, selected write-through adapters, and the additive `SSKey.INTAKE_FACT_EVIDENCE` store now exist; remaining phases should continue to preserve legacy compatibility.

The migration goal is to make intake facts addressable, traceable, and reusable across UI state, summary artifacts, exports, prompt construction, and readiness checks without changing user-visible behavior during the initial compatibility phases.

## Current Baseline

- Canonical session keys, step IDs, fact IDs, fact source types, and labels live in `constants.py`.
- Session defaults and reset behavior live in `state.py`.
- Wizard pages collect answers through Streamlit session state and page-local helpers.
- `intake_facts.py` exposes legacy-compatible read/write adapters. `SSKey.INTAKE_FACTS` keeps plain values, while `SSKey.INTAKE_FACT_EVIDENCE` stores additive metadata (`source_type`, `source_label`, `confidence`, `confirmed`, `sensitivity`, redacted optional `evidence_snippet`, `used_by_artifacts`, `updated_at`).
- `JobAdExtract.field_evidence` can carry optional field-level extraction confidence and source snippets; jobspec fact write-through uses that metadata when it is present, and Phase B review surfaces available field evidence read-only.
- Manual writes default to confidence `1.0`; jobspec extraction write-through defaults to confidence `0.75`.
- Summary artifact generation appends the generated artifact ID to existing evidence rows via `used_by_artifacts`, without creating new fact values.
- Adaptive question coverage can use `SSKey.INTAKE_FACT_EVIDENCE` plus the UI confidence threshold; facts without evidence keep legacy coverage behavior.
- `Question.fact_key` is an optional canonical pointer used for fact-backed coverage and prefill resolution. Existing QuestionPlans without `fact_key` remain valid.
- Summary facts are currently assembled in `wizard_pages/08_summary.py` from available state, generated artifacts, and derived values.

## Migration Principles

- Keep each PR small and reviewable.
- Preserve existing UI behavior, session-state behavior, exports, and prompt output unless a PR explicitly changes them.
- Introduce canonical constants before using new identifiers in UI, exports, prompts, or tests.
- Prefer adapters and compatibility wrappers before removing legacy state reads.
- Keep Fact Registry, Evidence Store, readiness, and export behavior separable so failures are easy to isolate.
- Do not mix salary, ESCO, Summary Readiness, or design-system changes into foundational fact migration PRs unless they are direct consumers of a completed fact contract.

## Proposed PR Sequence

### PR 1: Fact Contract Skeleton (done)

Add the canonical fact vocabulary without changing runtime behavior.

- Define the minimum fact identity model: canonical `fact_key`, label, step ownership, value type, and persistence intent.
- Add constants/enums for fact IDs in `constants.py`.
- Add typed helper structures where needed, but avoid wiring them into wizard pages yet.
- Add contract tests for uniqueness, naming stability, and step ownership.
- Keep existing session-state keys and summary generation untouched.

### PR 2: Registry Initialization and Legacy Read Adapters (done)

Introduce a read-only registry layer that can mirror existing session state.

- Initialize an empty or mirrored registry in `state.py` without replacing existing session-state values.
- Add adapter helpers that read legacy values and expose canonical fact entries.
- Ensure reset paths clear or rebuild registry state consistently.
- Add tests for default state, reset behavior, and partial legacy-state compatibility.
- Do not migrate wizard writes yet.

### PR 3: Wizard Write-Through (partially done)

Update wizard pages to write canonical facts while preserving legacy session-state keys.

- For each migrated field, write through to the Fact Registry and keep the existing session-state key updated.
- Start with low-risk fields from one wizard step before expanding to the rest.
- Keep UI labels, validation, progress, and completion behavior unchanged.
- Add tests proving legacy state and canonical facts remain synchronized.
- Do not change exports or prompt construction in this PR.

### PR 4: Summary, Export, and Prompt Consumers (partially started)

Move downstream consumers to read canonical facts through adapters.

- Update summary fact table assembly to prefer canonical facts while retaining legacy fallbacks. Core profile rows now read canonical intake facts first and fall back to Jobspec values.
- Update export payload construction to use canonical fact identities. The structured Summary export now includes additive `intake_facts` and `intake_fact_evidence` sections when present, while legacy export keys remain stable.
- Update prompt construction only where existing behavior can be preserved exactly.
- Add tests for summary facts, export payloads, and prompt payload compatibility.
- Keep Salary, ESCO, and Summary Readiness domain behavior unchanged unless they only consume the new adapter output.

### PR 5: Evidence Store and Legacy Cleanup (partially started)

Add evidence tracking and remove only proven-dead legacy paths.

- Extend Evidence Store usage beyond current write-through metadata where source-safe evidence is available. Jobspec field-level evidence is now wired into supported fact write-through.
- Link evidence to canonical facts without storing secrets, credentials, or personal data in logs; snippets are redacted before storage, sensitivity is canonicalized, and artifact usage uses canonical Summary artifact IDs.
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

- How far to expand write-through coverage beyond the current supported fact fields.
- Whether evidence snippets should be populated for all imported facts or only source-safe AI-derived/imported facts beyond jobspec field evidence.
- How much historical legacy state should remain as compatibility surface after PR 5.

## Non-Goals For This Plan

- No replacement of existing legacy session-state values with fact envelopes.
- No migration of all Summary/export/prompt consumers until PR 4 scope is explicitly picked up.
- No required field-level LLM evidence fields; `JobAdExtract.field_evidence` remains optional and additive.
- No ESCO, Salary, Summary Readiness, design-system, or wizard-page behavior changes.
- No lint auto-fixes.

## Proposed Registry / Schema Shape

The first implementation phase introduced the canonical vocabulary before runtime migration. Later phases should continue extending consumers without changing existing `Question.id` or legacy session-key behavior.

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

Implemented:

- `fact_key: str | None`
- `follow_up_prompts: list[str]`

Future schema extensions may add:

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

Disable evidence consumers and keep canonical facts without using evidence metadata until privacy and reset behavior are stable.

## Acceptance Criteria

- `Question.id` remains the stable UI/widget/history identity.
- Existing QuestionPlans without `fact_key` validate and render.
- No existing Session State key is removed during the compatibility phases.
- New registry or evidence payloads are additive.
- Summary and export legacy keys remain stable unless a dedicated PR explicitly changes them.
- Tests prove old and new paths are compatible before any legacy path is removed.
- Each implementation PR is small enough to review independently.
- No production API calls, secrets, or PII are introduced in tests or logs.
