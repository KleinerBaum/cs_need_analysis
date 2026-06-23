# Legacy Summary outputs

## Archived employment contract draft

`employment_contract` is archived because the active Summary product now focuses
on recruiting and hiring-team outputs:

- `brief`
- `job_ad`
- `interview_hr`
- `interview_fach`
- `boolean_search`

The archived output is hidden from normal UI, release gates, live previews,
action recommendations, result switchers, and export workspaces. This keeps the
visible product focused while old saved drafts continue to load safely.

Legacy support remains in:

- `SSKey.EMPLOYMENT_CONTRACT_*` state keys for old draft JSON payloads.
- `VACANCY_DRAFT_SESSION_KEYS` so old saved draft state is accepted.
- `llm_client.generate_employment_contract_draft` and its tests until downstream
  imports are removed deliberately.
- `settings_openai._TASK_KINDS` while the legacy generator remains test-covered.

Future deletion prerequisites:

- Confirm no saved-draft migration path needs `SSKey.EMPLOYMENT_CONTRACT_*`.
- Remove or migrate tests and imports for `generate_employment_contract_draft`.
- Remove the `generate_employment_contract` task settings key only in the same
  change that deletes the generator.
- Bump or document any draft schema behavior change if old payloads stop being
  accepted.
