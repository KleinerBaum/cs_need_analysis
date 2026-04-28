from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from constants import SSKey
from schemas import JobAdExtract

ROOT = Path(__file__).resolve().parents[1]


class _FakeStreamlit:
    def __init__(self) -> None:
        self.session_state: dict[str, Any] = {}

    def caption(self, _text: str) -> None:
        return None


def _load_module(alias: str, relative_path: str):
    module_path = ROOT / relative_path
    spec = spec_from_file_location(alias, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Could not load module from {relative_path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[attr-defined]
    return module


def _capture_step_shell_kwargs(page_module: Any, *, step_key: str) -> dict[str, Any]:
    captured_kwargs: dict[str, Any] = {}

    def _record_step_shell(**kwargs: Any) -> None:
        nonlocal captured_kwargs
        captured_kwargs = kwargs

    page_module.st = _FakeStreamlit()
    page_module.render_error_banner = lambda: None
    page_module.guard_job_and_plan = lambda _ctx: (
        JobAdExtract(),
        SimpleNamespace(steps=[SimpleNamespace(step_key=step_key)]),
    )
    page_module.nav_buttons = lambda _ctx: None
    page_module.render_step_shell = _record_step_shell

    if hasattr(page_module, "get_esco_occupation_selected"):
        page_module.get_esco_occupation_selected = lambda: None
    if hasattr(page_module, "has_confirmed_esco_anchor"):
        page_module.has_confirmed_esco_anchor = lambda: False
    if hasattr(page_module, "sync_esco_shared_state"):
        page_module.sync_esco_shared_state = lambda: SimpleNamespace(
            selected_occupation_uri="",
            confirmed_essential_skills=[],
            confirmed_optional_skills=[],
        )

    page_module.render(SimpleNamespace())
    return captured_kwargs


def _slot_order_from_render_kwargs(render_kwargs: dict[str, Any]) -> list[str]:
    return [
        key for key in render_kwargs if key.endswith("_slot") and key != "footer_slot"
    ]


def test_role_skills_benefits_use_identical_step_shell_block_order() -> None:
    role_tasks = _load_module(
        "wizard_pages.page_04_role_tasks", "wizard_pages/04_role_tasks.py"
    )
    skills = _load_module("wizard_pages.page_05_skills", "wizard_pages/05_skills.py")
    benefits = _load_module(
        "wizard_pages.page_06_benefits", "wizard_pages/06_benefits.py"
    )

    role_kwargs = _capture_step_shell_kwargs(role_tasks, step_key="role_tasks")
    skills_kwargs = _capture_step_shell_kwargs(skills, step_key="skills")
    benefits_kwargs = _capture_step_shell_kwargs(benefits, step_key="benefits")

    role_slots = _slot_order_from_render_kwargs(role_kwargs)
    skills_slots = _slot_order_from_render_kwargs(skills_kwargs)
    benefits_slots = _slot_order_from_render_kwargs(benefits_kwargs)

    expected_order = [
        "extracted_from_jobspec_slot",
        "open_questions_slot",
        "review_slot",
        "post_review_slot",
    ]

    assert role_slots == expected_order
    assert skills_slots == expected_order
    assert benefits_slots == expected_order

    assert callable(role_kwargs["post_review_slot"])
    assert callable(skills_kwargs["salary_forecast_slot"])
    assert callable(benefits_kwargs["salary_forecast_slot"])


def test_salary_forecast_slots_keep_canonical_result_key_wiring() -> None:
    role_tasks = _load_module(
        "wizard_pages.page_04_role_tasks", "wizard_pages/04_role_tasks.py"
    )
    skills = _load_module("wizard_pages.page_05_skills", "wizard_pages/05_skills.py")
    benefits = _load_module(
        "wizard_pages.page_06_benefits", "wizard_pages/06_benefits.py"
    )

    role_kwargs = _capture_step_shell_kwargs(role_tasks, step_key="role_tasks")
    skills_kwargs = _capture_step_shell_kwargs(skills, step_key="skills")
    benefits_kwargs = _capture_step_shell_kwargs(benefits, step_key="benefits")

    role_tasks.st.session_state[SSKey.SALARY_FORECAST_LAST_RESULT.value] = {}
    skills.st.session_state[SSKey.SALARY_FORECAST_LAST_RESULT.value] = {}
    benefits.st.session_state[SSKey.SALARY_FORECAST_LAST_RESULT.value] = {}

    role_tasks._render_role_tasks_salary_block = (
        lambda **_kwargs: role_tasks.st.session_state.__setitem__(
            SSKey.SALARY_FORECAST_LAST_RESULT.value,
            {"source": "role_tasks"},
        )
    )
    skills.render_skills_salary_forecast_panel = (
        lambda **_kwargs: skills.st.session_state.__setitem__(
            SSKey.SALARY_FORECAST_LAST_RESULT.value,
            {"source": "skills"},
        )
    )
    benefits.render_benefits_salary_forecast_panel = (
        lambda **_kwargs: benefits.st.session_state.__setitem__(
            SSKey.SALARY_FORECAST_LAST_RESULT.value,
            {"source": "benefits"},
        )
    )
    benefits._render_benefits_influence_overview = lambda _benefits: None
    benefits.load_openai_settings = lambda: object()
    benefits.resolve_model_for_task = lambda **_kwargs: "test-model"

    role_kwargs["post_review_slot"]()
    skills_kwargs["salary_forecast_slot"]()
    benefits_kwargs["salary_forecast_slot"]()

    assert (
        role_tasks.st.session_state[SSKey.SALARY_FORECAST_LAST_RESULT.value]["source"]
        == "role_tasks"
    )
    assert (
        skills.st.session_state[SSKey.SALARY_FORECAST_LAST_RESULT.value]["source"]
        == "skills"
    )
    assert (
        benefits.st.session_state[SSKey.SALARY_FORECAST_LAST_RESULT.value]["source"]
        == "benefits"
    )
