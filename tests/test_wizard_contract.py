from __future__ import annotations

from constants import NON_INTAKE_STEP_KEYS, STEPS, STEP_KEY_JOBSPEC_REVIEW
from wizard_pages import load_pages


def test_loaded_wizard_pages_match_canonical_steps() -> None:
    pages = load_pages()
    visible_page_keys = [page.key for page in pages]
    assert visible_page_keys == [step.key for step in STEPS]
    assert STEP_KEY_JOBSPEC_REVIEW not in visible_page_keys


def test_non_intake_step_keys_follow_active_step_contract() -> None:
    rendered_step_keys = {step.key for step in STEPS}
    assert NON_INTAKE_STEP_KEYS
    assert STEP_KEY_JOBSPEC_REVIEW not in rendered_step_keys
    assert all(step_key in rendered_step_keys for step_key in NON_INTAKE_STEP_KEYS)
