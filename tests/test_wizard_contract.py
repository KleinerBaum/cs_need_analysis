from __future__ import annotations

from constants import NON_INTAKE_STEP_KEYS, STEPS, STEP_KEY_JOBSPEC_REVIEW
from wizard_pages import load_pages


def test_loaded_wizard_pages_match_canonical_steps() -> None:
    pages = load_pages()
    assert [page.key for page in pages] == [step.key for step in STEPS]


def test_non_intake_step_keys_include_jobspec_review_but_not_rendered_steps() -> None:
    rendered_step_keys = {step.key for step in STEPS}
    assert STEP_KEY_JOBSPEC_REVIEW in NON_INTAKE_STEP_KEYS
    assert STEP_KEY_JOBSPEC_REVIEW not in rendered_step_keys
    assert NON_INTAKE_STEP_KEYS[0] in rendered_step_keys
    assert NON_INTAKE_STEP_KEYS[-1] in rendered_step_keys
