from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
from typing import Any

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


def _capture_step_shell_slot_order(page_module: Any, *, step_key: str) -> list[str]:
    captured_slots: list[str] = []

    def _record_step_shell(**kwargs: Any) -> None:
        nonlocal captured_slots
        captured_slots = [
            key
            for key in kwargs
            if key.endswith("_slot")
            and key
            != "footer_slot"
        ]

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
    return captured_slots


def test_role_skills_benefits_use_identical_step_shell_block_order() -> None:
    role_tasks = _load_module("wizard_pages.page_04_role_tasks", "wizard_pages/04_role_tasks.py")
    skills = _load_module("wizard_pages.page_05_skills", "wizard_pages/05_skills.py")
    benefits = _load_module("wizard_pages.page_06_benefits", "wizard_pages/06_benefits.py")

    role_slots = _capture_step_shell_slot_order(role_tasks, step_key="role_tasks")
    skills_slots = _capture_step_shell_slot_order(skills, step_key="skills")
    benefits_slots = _capture_step_shell_slot_order(benefits, step_key="benefits")

    expected_order = [
        "extracted_from_jobspec_slot",
        "source_comparison_slot",
        "salary_forecast_slot",
        "open_questions_slot",
        "review_slot",
    ]

    assert role_slots == expected_order
    assert skills_slots == expected_order
    assert benefits_slots == expected_order
