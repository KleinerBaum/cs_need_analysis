# UX Copy Guidance

This document captures stable guidance for German product copy in the
Recruiting-Briefing workflow. It is documentation only; runtime copy remains in
`ux_copy_contract.py`, `locales/*.json`, `i18n.py`, and the wizard pages.

## Principles

- Keep copy short, concrete, and reversible.
- Treat extracted values as suggestions until the user confirms them.
- Prefer visible labels and captions over relying on input placeholders alone.
- Keep German UI copy and English technical terms separated intentionally.
- Update UI, state, exports, and prompt construction together when copy changes
  the meaning of a field or workflow state.

## Step Copy Direction

| Step | Headline direction | User value |
|---|---|---|
| Start | Stellenanzeige einlesen und Intake starten | Source text becomes reviewed facts, evidence, and an ESCO anchor candidate. |
| Unternehmen | Unternehmenskontext klären | Employer story, market context, and team context become reusable downstream input. |
| Rolle & Aufgaben | Rolle und Kernaufgaben festzurren | Responsibilities and outcomes become clearer signals for briefing and salary context. |
| Skills & Anforderungen | Skills präzisieren und priorisieren | Must-haves and nice-to-haves are separated for matching, interview, and exports. |
| Benefits & Rahmenbedingungen | Angebot und Rahmenbedingungen schärfen | Salary, work model, benefits, and constraints become internally consistent. |
| Interviewprozess | Interviewprozess klar und fair gestalten | Candidate communication and internal evaluation become aligned. |
| Zusammenfassung | Alles bereit für Recruiting und Hiring-Team | Readiness, blockers, artifacts, and final export eligibility are visible in one place. |

## Personalization Rules

Use extracted context only when it is source-backed and high confidence.

- Job title, company, location, salary, benefits, and remote-policy hints should
  be shown as `Erkannt` or `Vorschlag`, not as final truth.
- Auto-prefill should require stricter confidence than display-only hints.
- Every personalized value must remain editable or rejectable.
- If extraction fails, the manual workflow must remain complete.

## Placeholder Policy

Input placeholders may show examples such as `z. B. Berlin, NRW, DACH`, but they
must not carry required meaning that is absent from the visible label or help
text. Public/legal pages must not use fake placeholder values for missing
organization data; they should render explicit missing-configuration language
until reviewed final data is available.

## Accessibility And Validation

- Every interactive field needs a visible label.
- Validation messages should be close to the field and state the next action.
- Status must not rely on color alone; pair color with text such as `Erkannt`,
  `Bitte prüfen`, `Bestätigt`, or `Fehlt`.
- Fallback states must explain what still works and what is limited.

## Verification

Relevant checks for copy changes:

```bash
TMPDIR=/tmp TMP=/tmp TEMP=/tmp .venv/bin/python -m pytest -q tests/test_i18n.py tests/test_ux_copy_contract.py tests/test_dynamic_step_copy.py
TMPDIR=/tmp TMP=/tmp TEMP=/tmp .venv/bin/python scripts/check_repo_hygiene.py
```
