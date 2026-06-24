# Persistence Strategy

This product snapshot uses explicit draft files, not backend persistence.

## Current Strategy

The current persistence contract is manual JSON draft/resume:

- Users save progress from the sidebar with `Entwurf speichern`.
- The app downloads a schema-versioned JSON payload with schema ID `cs_need_analysis.vacancy_draft`.
- Users resume with `Entwurf laden`.
- Loading resets vacancy state first, restores only allowlisted canonical `SSKey` vacancy domains, normalizes loaded values through `state_store.py`, and then resumes at the restored wizard step.

The implementation boundary is:

- `state.VACANCY_DRAFT_SESSION_KEYS` defines the allowlist.
- `state.build_vacancy_draft_json()` creates draft JSON.
- `state.load_vacancy_draft_json()` validates, resets, restores, and normalizes draft state.
- `summary_exports.build_vacancy_draft_payload()` serializes only JSON-safe allowlisted values.

The app also retains the existing browser-safe recovery bridge for reload resilience:

- UI language is mirrored through query parameters and origin-local browser storage.
- The app shell contains a safe-recovery storage key for vacancy draft recovery behavior.
- Browser recovery must remain opportunistic and local to the browser; JSON draft/resume remains the durable product contract.

There is no backend user store, account-bound draft store, or server-side autosave in this release.

## Persisted State Categories

Draft JSON may persist vacancy domains required to continue the Recruiting-Briefing:

- current wizard step and navigation selection
- UI language, UI mode, UI preferences, and expanded UI groups
- source text and source selection
- reviewed jobspec extract, intake facts, fact evidence, question plan, question limits, and answers
- occupation profile, ESCO anchor state, selected anchors, selected skills, unmapped-term decisions, matrix coverage, and question-flow provenance
- company website review outputs selected by the user
- role tasks, skills, benefits, salary scenario state, salary forecast state, and interview process state
- generated Summary artifacts that remain part of the active or compatibility draft contract

## Excluded State Categories

Draft JSON must not persist runtime-only, sensitive, or cache state:

- OpenAI settings, model override state, API keys, secrets, tokens, OAuth material, or credentials
- LLM response cache, OpenAI debug payloads, raw request/response objects, and transient error state
- privacy or content-sharing consent flags
- usage events and telemetry
- uploaded file metadata, upload signatures, file handles, and binary upload widgets
- logo binary payloads and other non-JSON-safe binary values
- external fetch caches, ESCO negative caches, and homepage fetch caches
- transient Streamlit widget-only state unless it has an intentional canonical `SSKey`

If a new state key is needed for resume, add it to `SSKey`, initialize/reset it in `state.py`, and decide explicitly whether it belongs in `VACANCY_DRAFT_SESSION_KEYS`.

## Future Adapter Boundary

Future persistence should be added behind a browser/backend adapter, not by spreading storage calls through wizard pages.

The adapter should expose a small contract:

- `save_draft(payload, metadata) -> draft_ref`
- `load_draft(draft_ref) -> payload`
- `list_drafts(scope) -> metadata[]`
- `delete_draft(draft_ref) -> result`

The payload format should continue to be the existing schema-versioned draft JSON, so manual JSON drafts, browser-local drafts, and backend drafts share one normalization path. The adapter may store browser-local drafts or backend drafts later, but the restore path must still call `load_vacancy_draft_json()` or an equivalent allowlist-and-normalize function.

## Product Contract

Persistence is beta-ready when:

- a user can save and resume the core vacancy workflow with manual JSON draft/resume
- excluded state stays excluded in tests
- old draft payloads with retained compatibility keys do not crash the app
- no backend is required for the core regression suite
- adding backend persistence is possible without changing page-level workflow logic
