# Legacy Wizard Modules

Two wizard modules are archived in place and intentionally non-routable.

## Archived Modules

- `wizard_pages/01a_jobspec_review.py`
- `wizard_pages/03_team.py`

These files remain in the repository for compatibility and focused helper tests. They are not part of the active route contract and must not return to sidebar navigation by filename discovery.

## Current Replacement Paths

`wizard_pages/01a_jobspec_review.py` is replaced by the integrated Start step:

- Phase A: source selection, upload/paste/manual text, privacy controls, UI mode, ESCO operating settings
- Phase B: structured jobspec extraction review with fact and evidence handling
- Phase C: ESCO occupation anchoring with primary and secondary context anchors

`wizard_pages/03_team.py` is replaced by company-step team handling:

- `wizard_pages/02_company.py`
- `wizard_pages/team_section.py`

Team context remains a valid domain in question plans, facts, answers, and Summary exports. It is no longer a standalone routed wizard page.

## Route Guardrails

The active route contract is:

- source of truth: `constants.STEPS`
- route loading: `wizard_pages/__init__.py`
- route group constants: `PRE_WIZARD_STEP_KEYS`, `OPERATIONAL_WIZARD_STEP_KEYS`, and `PROGRESS_STEP_KEYS`

The route loader keeps an explicit ignore list so detached modules cannot become routable by matching the `NN_name.py` filename pattern. Contract tests must continue to assert:

- loaded pages exactly match `constants.STEPS`
- `jobspec_review` is not active
- `team` is not active
- documented active page modules do not include archived modules
- archived modules may exist but must not define an active `PAGE` key

## Removal Prerequisites

Remove these files only after all compatibility paths are deliberately closed:

- no test imports helper behavior from either module
- no historical draft, question-plan, answer, or Summary payload migration depends on legacy step IDs beyond canonical constants
- company-step team rendering covers every still-supported team question/fact/export path
- Start Phase B/C coverage replaces any remaining jobspec review helper expectations
- README, AGENTS.md, this document, and route-contract tests are updated in the same change

Until those prerequisites are met, archive in place is safer than deletion.

## Product Contract

Legacy modules are beta-ready when:

- active users cannot navigate to them
- route tests fail if they are silently reintroduced
- current replacement paths are documented
- later removal has explicit prerequisites
