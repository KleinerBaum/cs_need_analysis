# Product Definition of Done

This Definition of Done describes beta readiness for the active Recruiting-Briefing flow.

## Core Flow

The core flow is done when a user can move from upload or pasted jobspec text to usable Summary outputs without a dead end:

1. Start accepts upload or pasted text and records privacy/source choices.
2. Extracted jobspec information can be reviewed and promoted into facts.
3. ESCO occupation anchoring can be confirmed or safely degraded.
4. Company and team context can be completed or marked open.
5. Role/tasks, skills, and benefits can reconcile jobspec, ESCO/context, and user selections.
6. Salary forecast remains deterministic and never invents numeric salary from qualitative wording.
7. Interview process values can be captured for HR and hiring-manager outputs.
8. Summary shows readiness, blockers, stale state, and export eligibility.
9. Focused outputs can be previewed or generated without exposing archived outputs.

Core regression tests must not require live OpenAI, live ESCO, website fetches, or browser E2E.

## Per-Page Value Line

Every active page must explain product value, not just collect fields.

For active steps, DE and EN copy must both provide:

- headline
- subheadline
- value line
- primary CTA where relevant

The required active steps are:

- `landing`
- `company`
- `role_tasks`
- `skills`
- `benefits`
- `interview`
- `summary`

The intro route can remain product-context oriented and excluded from readiness/progress.

## Summary Release Credibility

Summary is release-credible when it states the status of every active output in concrete terms:

- ready: current result can be exported
- open: needed input or generation is still missing
- risky: non-critical warnings exist; expert override may be possible
- stale: result no longer matches current inputs and must be regenerated
- exportable: final export is available, or clearly blocked with next action

The UI can use localized labels such as `Bereit`, `Offen`, `Warnung`, `Veraltet`, and `Aktuell und exportierbar`, but the product behavior must keep these states distinct.

## Language Parity

Active flows are beta-ready only when German and English stay separated and equivalent:

- active step copy has matching key shapes
- active artifact labels have matching key sets
- deterministic previews and exports use the selected language
- German text does not leak into English output labels
- English text does not replace German source copy unless explicitly requested

## Focused Output Set

The active Summary output set is intentionally focused:

- `brief`
- `job_ad`
- `interview_hr`
- `interview_fach`
- `boolean_search`

`employment_contract` is archived. It may remain in compatibility constants and old draft loading, but it must not appear in active output cards, artifact labels, result switchers, release gates, previews, or focused exports.

## No-Live-API Beta Smoke

The beta smoke test must be deterministic and offline:

- no live OpenAI calls
- no live ESCO calls
- no homepage fetch
- no Streamlit browser E2E requirement
- synthetic or paraphrased fixture data only

The smoke should protect the product promises that matter most:

- focused outputs only
- archived employment contract stays inactive
- qualitative salary wording such as "competitive" does not become a numeric range
- hybrid/remote wording does not become remote-only or work-from-anywhere
- language separation is visible in DE and EN previews
- benefits remain candidate value, not hard requirements

## Verification

Minimum product-readiness verification for this contract:

```bash
.venv/bin/python -m pytest -q tests/test_product_readiness_contract.py
```

The broader repo verification remains the targeted compileall and pytest set documented in README and AGENTS.md.
