from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
from typing import Any

from constants import (
    AnswerType,
    FactKey,
    SSKey,
    STEP_KEY_BENEFITS,
    STEP_KEY_COMPANY,
    STEP_KEY_INTERVIEW,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
    STEP_SECTION_EXTRACTED_FROM_JOBSPEC,
    STEP_SECTION_OPEN_QUESTIONS,
    STEP_SECTION_REVIEW,
    STEP_SECTION_SALARY_FORECAST,
    STEP_SECTION_SOURCE_COMPARISON,
)
from schemas import JobAdExtract, Question, QuestionStep

ROOT = Path(__file__).resolve().parents[1]


class _FakeStreamlit:
    def __init__(self) -> None:
        self.session_state: dict[str, Any] = {}

    def caption(self, _text: str) -> None:
        return None

    def markdown(self, _text: str, *_args: Any, **_kwargs: Any) -> None:
        return None


class _ShellFakeStreamlit:
    def __init__(self, *, selected_label: str | None = None, correction: str = "") -> None:
        self.session_state: dict[str, Any] = {}
        self.selected_label = selected_label
        self.correction = correction
        self.events: list[tuple[str, str]] = []

    def caption(self, text: str) -> None:
        self.events.append(("caption", text))

    def markdown(self, text: str, *_args: Any, **_kwargs: Any) -> None:
        self.events.append(("markdown", text))

    def warning(self, text: str, *_args: Any, **_kwargs: Any) -> None:
        self.events.append(("warning", text))

    def info(self, text: str, *_args: Any, **_kwargs: Any) -> None:
        self.events.append(("info", text))

    def success(self, text: str, *_args: Any, **_kwargs: Any) -> None:
        self.events.append(("success", text))

    def write(self, text: str, *_args: Any, **_kwargs: Any) -> None:
        self.events.append(("write", text))

    def text_input(self, *_args: Any, key: str | None = None, **_kwargs: Any) -> str:
        if key is None:
            return ""
        return str(self.session_state.get(key, ""))

    def number_input(
        self,
        *_args: Any,
        key: str | None = None,
        value: int | None = None,
        **_kwargs: Any,
    ) -> int:
        if key is None:
            return value or 1
        self.session_state.setdefault(key, value or 5)
        return int(self.session_state[key])

    def button(self, *_args: Any, **_kwargs: Any) -> bool:
        return False

    def columns(self, count_or_spec: Any, *_args: Any, **_kwargs: Any) -> list[Any]:
        count = count_or_spec if isinstance(count_or_spec, int) else len(count_or_spec)
        return [_Column() for _index in range(count)]

    def segmented_control(self, *_args: Any, **_kwargs: Any) -> str | None:
        return self.selected_label

    def radio(self, *_args: Any, **_kwargs: Any) -> str | None:
        return self.selected_label

    def text_area(self, *_args: Any, **_kwargs: Any) -> str:
        return self.correction

    def divider(self) -> None:
        self.events.append(("divider", ""))

    def spinner(self, text: str) -> Any:
        self.events.append(("spinner", text))
        return _Column()


class _Column:
    def __enter__(self) -> "_Column":
        return self

    def __exit__(self, *_args: Any) -> None:
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
        key
        for key in render_kwargs
        if key.endswith("_slot") and key not in {"footer_slot", "outcome_slot"}
    ]


def test_role_skills_benefits_use_expected_step_shell_block_order() -> None:
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

    assert role_slots == [
        "source_comparison_slot",
        "extracted_from_jobspec_slot",
        "salary_forecast_slot",
        "open_questions_slot",
        "review_slot",
    ]
    assert skills_slots == [
        "source_comparison_slot",
        "extracted_from_jobspec_slot",
        "salary_forecast_slot",
        "open_questions_slot",
        "review_slot",
    ]
    assert benefits_slots == [
        "source_comparison_slot",
        "extracted_from_jobspec_slot",
        "salary_forecast_slot",
        "open_questions_slot",
        "review_slot",
    ]

    assert callable(role_kwargs["salary_forecast_slot"])
    assert callable(skills_kwargs["salary_forecast_slot"])
    assert callable(benefits_kwargs["salary_forecast_slot"])


def test_company_team_interview_use_step_shell_with_review_slot_and_canonical_order() -> None:
    company = _load_module("wizard_pages.page_02_company", "wizard_pages/02_company.py")
    team = _load_module("wizard_pages.page_03_team", "wizard_pages/03_team.py")
    interview = _load_module("wizard_pages.page_07_interview", "wizard_pages/07_interview.py")

    company_kwargs = _capture_step_shell_kwargs(company, step_key="company")
    team_kwargs = _capture_step_shell_kwargs(team, step_key="team")
    interview_kwargs = _capture_step_shell_kwargs(interview, step_key="interview")

    assert _slot_order_from_render_kwargs(company_kwargs) == [
        "open_questions_slot",
        "review_slot",
    ]
    assert _slot_order_from_render_kwargs(team_kwargs) == [
        "extracted_from_jobspec_slot",
        "main_content_slot",
        "review_slot",
    ]
    assert _slot_order_from_render_kwargs(interview_kwargs) == [
        "source_comparison_slot",
        "extracted_from_jobspec_slot",
        "open_questions_slot",
        "review_slot",
    ]

    assert callable(company_kwargs["review_slot"])
    assert callable(team_kwargs["review_slot"])
    assert callable(interview_kwargs["review_slot"])


def test_interview_open_questions_use_compact_context_mode() -> None:
    interview = _load_module(
        "wizard_pages.page_07_interview_compact_questions",
        "wizard_pages/07_interview.py",
    )
    fake_st = _FakeStreamlit()
    captured_kwargs: dict[str, Any] = {}
    question_step = QuestionStep(
        step_key=STEP_KEY_INTERVIEW,
        title_de="Interview",
        questions=[
            Question(
                id="interview_update_sla",
                label="Welches Update-SLA gilt?",
                answer_type=AnswerType.LONG_TEXT,
                group_key="candidate_communication",
            )
        ],
    )
    captured_call: dict[str, Any] = {}

    interview.st = fake_st
    interview.render_error_banner = lambda: None
    interview.guard_job_and_plan = lambda _ctx: (
        JobAdExtract(),
        SimpleNamespace(steps=[question_step]),
    )
    interview.nav_buttons = lambda _ctx: None
    interview.render_step_shell = lambda **kwargs: captured_kwargs.update(kwargs)

    def _capture_question_step(step: Any, *, context_mode: str = "default") -> None:
        captured_call["step"] = step
        captured_call["context_mode"] = context_mode

    interview.render_question_step = _capture_question_step

    interview.render(SimpleNamespace())
    captured_kwargs["open_questions_slot"]()

    assert captured_call["step"] is question_step
    assert captured_call["context_mode"] == "compact"


def test_canonical_step_section_registry_drives_shell_order() -> None:
    from step_sections import build_step_shell_section_kwargs, get_step_sections

    expected_contracts = {
        STEP_KEY_COMPANY: (
            [
                STEP_SECTION_OPEN_QUESTIONS,
                STEP_SECTION_EXTRACTED_FROM_JOBSPEC,
                STEP_SECTION_SOURCE_COMPARISON,
                STEP_SECTION_REVIEW,
            ],
            [
                "open_questions_slot",
                "extracted_from_jobspec_slot",
                "source_comparison_slot",
                "review_slot",
            ],
            "",
        ),
        STEP_KEY_ROLE_TASKS: (
            [
                STEP_SECTION_SOURCE_COMPARISON,
                STEP_SECTION_EXTRACTED_FROM_JOBSPEC,
                STEP_SECTION_SALARY_FORECAST,
                STEP_SECTION_OPEN_QUESTIONS,
                STEP_SECTION_REVIEW,
            ],
            [
                "source_comparison_slot",
                "extracted_from_jobspec_slot",
                "salary_forecast_slot",
                "open_questions_slot",
                "review_slot",
            ],
            "Aus Jobspec extrahiert",
        ),
        STEP_KEY_SKILLS: (
            [
                STEP_SECTION_SOURCE_COMPARISON,
                STEP_SECTION_EXTRACTED_FROM_JOBSPEC,
                STEP_SECTION_SALARY_FORECAST,
                STEP_SECTION_OPEN_QUESTIONS,
                STEP_SECTION_REVIEW,
            ],
            [
                "source_comparison_slot",
                "extracted_from_jobspec_slot",
                "salary_forecast_slot",
                "open_questions_slot",
                "review_slot",
            ],
            "Aus Jobspec extrahiert",
        ),
        STEP_KEY_BENEFITS: (
            [
                STEP_SECTION_SOURCE_COMPARISON,
                STEP_SECTION_EXTRACTED_FROM_JOBSPEC,
                STEP_SECTION_SALARY_FORECAST,
                STEP_SECTION_OPEN_QUESTIONS,
                STEP_SECTION_REVIEW,
            ],
            [
                "source_comparison_slot",
                "extracted_from_jobspec_slot",
                "salary_forecast_slot",
                "open_questions_slot",
                "review_slot",
            ],
            "Aus Jobspec extrahiert",
        ),
        STEP_KEY_INTERVIEW: (
            [
                STEP_SECTION_SOURCE_COMPARISON,
                STEP_SECTION_EXTRACTED_FROM_JOBSPEC,
                STEP_SECTION_OPEN_QUESTIONS,
                STEP_SECTION_REVIEW,
            ],
            [
                "source_comparison_slot",
                "extracted_from_jobspec_slot",
                "open_questions_slot",
                "review_slot",
            ],
            "Identifizierte Interview-Werte",
        ),
    }

    for step_key, (expected_sections, expected_slots, expected_label) in expected_contracts.items():
        section_ids = [section.section_id for section in get_step_sections(step_key)]
        assert section_ids == expected_sections

        renderers = {section_id: (lambda: None) for section_id in section_ids}
        shell_kwargs = build_step_shell_section_kwargs(
            step_key=step_key,
            renderers=renderers,
        )

        assert _slot_order_from_render_kwargs(shell_kwargs) == expected_slots
        if expected_label is None:
            assert "extracted_from_jobspec_label" not in shell_kwargs
        else:
            assert shell_kwargs["extracted_from_jobspec_label"] == expected_label


def test_salary_forecast_slots_keep_canonical_result_key_wiring() -> None:
    role_tasks = _load_module(
        "wizard_pages.page_04_role_tasks", "wizard_pages/04_role_tasks.py"
    )
    skills = _load_module("wizard_pages.page_05_skills", "wizard_pages/05_skills.py")
    benefits = _load_module(
        "wizard_pages.page_06_benefits", "wizard_pages/06_benefits.py"
    )

    _capture_step_shell_kwargs(role_tasks, step_key="role_tasks")
    _capture_step_shell_kwargs(skills, step_key="skills")
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

    role_tasks._render_role_tasks_salary_block(
        job=JobAdExtract(),
        selected_tasks=[],
    )
    benefits_kwargs["salary_forecast_slot"]()

    assert (
        role_tasks.st.session_state[SSKey.SALARY_FORECAST_LAST_RESULT.value]["source"]
        == "role_tasks"
    )
    assert (
        benefits.st.session_state[SSKey.SALARY_FORECAST_LAST_RESULT.value]["source"]
        == "benefits"
    )


def test_role_tasks_extracted_work_context_skips_duplicate_guardrails(monkeypatch) -> None:
    role_tasks = _load_module(
        "wizard_pages.page_04_role_tasks", "wizard_pages/04_role_tasks.py"
    )
    role_kwargs = _capture_step_shell_kwargs(role_tasks, step_key="role_tasks")
    captured_include_flags: list[bool] = []

    monkeypatch.setattr(role_tasks, "render_output_header", lambda *_, **__: None)
    monkeypatch.setattr(
        role_tasks,
        "responsive_three_columns",
        lambda **_kwargs: [_Column(), _Column(), _Column()],
    )
    monkeypatch.setattr(role_tasks, "_render_compact_signal_list", lambda *_, **__: None)
    monkeypatch.setattr(role_tasks.st, "info", lambda *_, **__: None, raising=False)
    monkeypatch.setattr(
        role_tasks,
        "render_work_context_sections",
        lambda _job, *, include_non_negotiables_compliance=True: (
            captured_include_flags.append(include_non_negotiables_compliance)
        ),
    )

    role_kwargs["extracted_from_jobspec_slot"]()

    assert captured_include_flags == [False]


def test_benefits_step_shell_includes_jobspec_context_before_source_comparison() -> None:
    benefits = _load_module(
        "wizard_pages.page_06_benefits_extract", "wizard_pages/06_benefits.py"
    )
    captured_kwargs: dict[str, Any] = {}
    fake_st = _FakeStreamlit()

    benefits.st = fake_st
    benefits.render_error_banner = lambda: None
    benefits.guard_job_and_plan = lambda _ctx: (
        JobAdExtract(
            benefits=[
                "State-of-the-art Trainings und Tools",
                "Flexible Arbeitsmodelle",
            ]
        ),
        SimpleNamespace(steps=[SimpleNamespace(step_key="benefits")]),
    )
    benefits.nav_buttons = lambda _ctx: None
    benefits.render_step_shell = lambda **kwargs: captured_kwargs.update(kwargs)

    benefits.render(SimpleNamespace())

    assert captured_kwargs["extracted_from_jobspec_slot"] is not None
    assert captured_kwargs["source_comparison_slot"] is not None
    assert captured_kwargs["salary_forecast_slot"] is not None


def test_benefits_source_comparison_auto_generates_ai_and_renders_ai_controls() -> None:
    benefits = _load_module(
        "wizard_pages.page_06_benefits_ai", "wizard_pages/06_benefits.py"
    )
    fake_st = _ShellFakeStreamlit()
    fake_st.session_state = {
        SSKey.BENEFITS_SUGGEST_COUNT.value: 3,
        SSKey.BENEFITS_REGION_CONTEXT.value: "Berlin",
    }
    captured_columns: list[dict[str, Any]] = []
    calls: list[dict[str, Any]] = []

    class _Suggestion:
        label = "Deutschlandticket"

        def model_dump(self, **_kwargs: Any) -> dict[str, str]:
            return {
                "label": self.label,
                "source_hint": "llm",
                "importance": "medium",
            }

    benefits.st = fake_st
    benefits.render_error_banner = lambda: None
    benefits.guard_job_and_plan = lambda _ctx: (
        JobAdExtract(benefits=["Flexible Arbeitsmodelle"]),
        SimpleNamespace(steps=[SimpleNamespace(step_key="benefits", questions=[])]),
    )
    benefits.nav_buttons = lambda _ctx: None
    benefits.render_step_shell = lambda **kwargs: captured_columns.append(kwargs)
    benefits.build_step_review_payload = lambda _step: {
        "visible_questions": [],
        "answers": {},
        "answered_lookup": {},
        "step_status": {"essentials_total": 0, "essentials_answered": 0},
    }
    benefits.render_compare_adopt_intro = lambda **_kwargs: None
    benefits.get_esco_semantic_context = lambda: SimpleNamespace(
        can_use_semantic_exports=False,
        primary_anchor=None,
    )
    benefits.load_openai_settings = lambda: object()
    benefits.resolve_model_for_task = lambda **_kwargs: "test-model"
    benefits.get_answers = lambda: {"existing": "answer"}

    def _generate(**kwargs: Any) -> tuple[Any, dict[str, Any]]:
        calls.append(kwargs)
        return SimpleNamespace(benefits=[_Suggestion()]), {}

    def _capture_pills(**kwargs: Any) -> dict[str, Any]:
        captured_columns.clear()
        captured_columns.extend(kwargs["columns"])
        ai_column = kwargs["columns"][2]
        ai_column["footer"]()
        return {
            "selected_labels": [],
            "selected_by_source": {},
            "source_counts": {"Jobspec": 0, "ESCO / Kontext": 0, "AI": 0},
        }

    benefits.generate_benefit_suggestions = _generate
    benefits.render_source_pill_selection = _capture_pills

    benefits.render(SimpleNamespace())
    captured_kwargs = captured_columns[0]
    captured_kwargs["source_comparison_slot"]()

    assert fake_st.session_state[SSKey.BENEFITS_AI_INITIAL_GENERATED.value] is True
    assert fake_st.session_state[SSKey.BENEFITS_LLM_SUGGESTED.value] == [
        {
            "label": "Deutschlandticket",
            "source_hint": "llm",
            "importance": "medium",
        }
    ]
    assert calls[0]["target_benefit_count"] == 3
    assert calls[0]["answers"]["benefit_generation_context"]["region"] == "Berlin"
    assert callable(captured_columns[2]["footer"])


def test_benefits_render_migrates_legacy_selected_state() -> None:
    benefits = _load_module(
        "wizard_pages.page_06_benefits_legacy", "wizard_pages/06_benefits.py"
    )
    fake_st = _FakeStreamlit()
    fake_st.session_state["benefits.compare.selected"] = ["Mentoring", "Mentoring"]

    benefits.st = fake_st
    benefits.render_error_banner = lambda: None
    benefits.guard_job_and_plan = lambda _ctx: (
        JobAdExtract(),
        SimpleNamespace(steps=[SimpleNamespace(step_key="benefits")]),
    )
    benefits.nav_buttons = lambda _ctx: None
    benefits.render_step_shell = lambda **_kwargs: None

    benefits.render(SimpleNamespace())

    assert fake_st.session_state[SSKey.BENEFITS_SELECTED.value] == ["Mentoring"]
    assert "benefits.compare.selected" not in fake_st.session_state


def test_benefits_selected_state_syncs_intake_fact() -> None:
    benefits = _load_module(
        "wizard_pages.page_06_benefits_fact_sync", "wizard_pages/06_benefits.py"
    )
    fake_st = _FakeStreamlit()
    fake_st.session_state = {
        SSKey.BENEFITS_SELECTED.value: [" Mentoring ", " ", "Mentoring"],
        SSKey.INTAKE_FACTS.value: {},
    }
    benefits.st = fake_st

    benefits._sync_selected_benefit_intake_facts()

    assert fake_st.session_state[SSKey.INTAKE_FACTS.value] == {
        FactKey.BENEFITS_BENEFITS.value: ["Mentoring"]
    }


def test_benefits_esco_skill_dicts_do_not_become_benefit_labels() -> None:
    benefits = _load_module(
        "wizard_pages.page_06_benefits_esco_guard", "wizard_pages/06_benefits.py"
    )

    labels = benefits._benefit_labels_from_suggestions(
        [
            {"uri": "uri:skill:python", "title": "Python", "source": "ESCO"},
            {"label": "Weiterbildung", "source": "AI"},
        ]
    )

    assert labels == ["Weiterbildung"]


def test_interview_contact_state_syncs_intake_fact() -> None:
    interview = _load_module(
        "wizard_pages.page_07_interview_fact_sync", "wizard_pages/07_interview.py"
    )
    fake_st = _FakeStreamlit()
    fake_st.session_state = {
        SSKey.INTERVIEW_INTERNAL_FLOW.value: {
            "contacts": [
                {
                    "name": " Hiring Team ",
                    "role": "Recruiting",
                    "email": "",
                    "phone": None,
                }
            ],
            "info_loop_items": [],
            "earliest_start_date": None,
            "latest_start_date": None,
            "selected_value_ids": [],
        },
        SSKey.INTAKE_FACTS.value: {},
    }
    interview.st = fake_st

    interview._sync_interview_contact_intake_facts()

    assert fake_st.session_state[SSKey.INTAKE_FACTS.value] == {
        FactKey.INTERVIEW_CONTACTS.value: [
            {"name": "Hiring Team", "role": "Recruiting"}
        ]
    }


def test_primary_step_pages_use_compact_review_render_mode() -> None:
    page_specs = [
        ("wizard_pages.page_02_company", "wizard_pages/02_company.py", "company"),
        ("wizard_pages.page_04_role_tasks", "wizard_pages/04_role_tasks.py", "role_tasks"),
        ("wizard_pages.page_06_benefits", "wizard_pages/06_benefits.py", "benefits"),
        ("wizard_pages.page_07_interview", "wizard_pages/07_interview.py", "interview"),
        ("wizard_pages.page_03_team", "wizard_pages/03_team.py", "team"),
        ("wizard_pages.page_05_skills", "wizard_pages/05_skills.py", "skills"),
    ]

    for alias, rel_path, step_key in page_specs:
        page_module = _load_module(alias, rel_path)
        kwargs = _capture_step_shell_kwargs(page_module, step_key=step_key)
        called: dict[str, Any] = {}

        def _capture_review(step: Any, render_mode: Any = None) -> None:
            called["step"] = step
            called["render_mode"] = render_mode

        page_module.render_standard_step_review = _capture_review
        if hasattr(page_module, "_render_benefits_consistency_checklist"):
            page_module._render_benefits_consistency_checklist = lambda **_kwargs: None
        if hasattr(page_module, "_render_interview_consistency_checklist"):
            page_module._render_interview_consistency_checklist = lambda **_kwargs: None
        kwargs["review_slot"]()

        assert getattr(called["render_mode"], "value", called["render_mode"]) == "compact"


def test_company_team_esco_hint_persists_to_canonical_team_success_fact(
    monkeypatch,
) -> None:
    company = _load_module("wizard_pages.page_02_company_fact", "wizard_pages/02_company.py")
    persisted: dict[str, Any] = {}

    monkeypatch.setattr(company, "fact_value", lambda *_args, **_kwargs: "Vorhanden")

    def _persist_fact(fact_key: FactKey, value: str) -> None:
        persisted["fact_key"] = fact_key
        persisted["value"] = value

    monkeypatch.setattr(company, "persist_fact", _persist_fact)

    adopted = company._append_context_to_team_success_fact(
        "ESCO-Hinweis: Zusammenarbeit / Kommunikation"
    )

    assert adopted is True
    assert persisted["fact_key"] is FactKey.TEAM_SUCCESS_CONTEXT_90D
    assert persisted["value"] == (
        "Vorhanden\n- ESCO-Hinweis: Zusammenarbeit / Kommunikation"
    )


def test_review_mode_resolution_prefers_full_for_expert_or_debug() -> None:
    from ui_components import ReviewRenderContext, ReviewRenderMode, resolve_standard_review_mode

    assert resolve_standard_review_mode(
        context=ReviewRenderContext.STEP_FORM,
        ui_mode="expert",
        debug_enabled=False,
    ) is ReviewRenderMode.FULL
    assert resolve_standard_review_mode(
        context=ReviewRenderContext.SUMMARY_READINESS,
        ui_mode="standard",
        debug_enabled=True,
    ) is ReviewRenderMode.FULL
    assert resolve_standard_review_mode(
        context=ReviewRenderContext.SUMMARY_READINESS,
        ui_mode="standard",
        debug_enabled=False,
    ) is ReviewRenderMode.DIRECT_ANSWERS


def test_jobspec_note_routing_uses_best_fit_once() -> None:
    import ui_layout

    assert (
        ui_layout.resolve_jobspec_note_step(
            "Konkrete Informationen zum Gehalt und zu den Arbeitsstandorten fehlen."
        )
        == "benefits"
    )
    assert ui_layout.resolve_jobspec_note_step("Python skill assumptions") == "skills"
    assert ui_layout.resolve_jobspec_note_step("Interview steps missing") == "interview"
    assert ui_layout.resolve_jobspec_note_step("company_website fehlt") == "company"


def test_step_shell_renders_jobspec_notes_after_extracted_slot(monkeypatch) -> None:
    import ui_layout

    fake_st = _ShellFakeStreamlit()
    fake_st.session_state = {
        SSKey.JOB_EXTRACT.value: JobAdExtract(
            gaps=["salary_range fehlt"],
            assumptions=["Gehalt wird als marktüblich angenommen."],
        ).model_dump(mode="json"),
        SSKey.ANSWERS.value: {},
        SSKey.ANSWER_META.value: {},
    }
    monkeypatch.setattr(ui_layout, "st", fake_st)
    monkeypatch.setattr(ui_layout, "render_step_header", lambda *_args, **_kwargs: None)

    step = QuestionStep(
        step_key="benefits",
        title_de="Benefits",
        questions=[
            Question(
                id="q_salary",
                label="Gehalt?",
                answer_type=AnswerType.SHORT_TEXT,
            )
        ],
    )

    def _render_extracted() -> None:
        fake_st.events.append(("slot", "extracted"))

    ui_layout.render_step_shell(
        title="Benefits",
        subtitle="Rahmenbedingungen",
        step=step,
        extracted_from_jobspec_slot=_render_extracted,
    )

    event_names = [name for name, _value in fake_st.events]
    assert event_names.index("slot") < event_names.index("warning")
    assert any(
        name == "warning" and "salary_range fehlt" in value
        for name, value in fake_st.events
    )
    assert any(
        name == "info" and "Gehalt wird als marktüblich angenommen." in value
        for name, value in fake_st.events
    )


def test_step_shell_header_status_does_not_render_duplicate_status_captions(
    monkeypatch,
) -> None:
    import ui_layout

    fake_st = _ShellFakeStreamlit()
    fake_st.session_state = {
        SSKey.JOB_EXTRACT.value: None,
        SSKey.ANSWERS.value: {},
        SSKey.ANSWER_META.value: {},
    }
    header_meta: list[tuple[str, str, str]] = []
    monkeypatch.setattr(ui_layout, "st", fake_st)
    monkeypatch.setattr(
        ui_layout,
        "render_step_header",
        lambda *_args, meta_items=None, **_kwargs: header_meta.extend(
            list(meta_items or [])
        ),
    )

    ui_layout.render_step_shell(
        title="Company",
        subtitle="Kontext",
        step=QuestionStep(
            step_key="company",
            title_de="Company",
            questions=[
                Question(
                    id="company_name",
                    label="Wie heißt das Unternehmen?",
                    answer_type=AnswerType.SHORT_TEXT,
                    required=True,
                )
            ],
        ),
    )

    assert ("📊", "Fortschritt", "0/1 beantwortet") in header_meta
    assert not any(name == "caption" for name, _value in fake_st.events)


def test_landing_and_summary_do_not_render_jobspec_step_notes(monkeypatch) -> None:
    import ui_layout

    fake_st = _ShellFakeStreamlit()
    fake_st.session_state = {
        SSKey.JOB_EXTRACT.value: JobAdExtract(
            gaps=["company_website fehlt"],
            assumptions=["Remote Policy wird angenommen."],
        ).model_dump(mode="json"),
    }
    monkeypatch.setattr(ui_layout, "st", fake_st)

    ui_layout.render_jobspec_step_notes("landing")
    ui_layout.render_jobspec_step_notes("summary")

    assert not any(name in {"warning", "info"} for name, _value in fake_st.events)


def test_assumption_rejection_persists_as_wizard_answer(monkeypatch) -> None:
    import ui_layout

    fake_st = _ShellFakeStreamlit(
        selected_label="Ablehnen & korrigieren",
        correction="Gehalt ist tariflich festgelegt.",
    )
    fake_st.session_state = {
        SSKey.JOB_EXTRACT.value: JobAdExtract(
            assumptions=["Gehalt wird als marktüblich angenommen."],
        ).model_dump(mode="json"),
        SSKey.ANSWERS.value: {},
        SSKey.ANSWER_META.value: {},
    }
    monkeypatch.setattr(ui_layout, "st", fake_st)
    monkeypatch.setattr(
        ui_layout,
        "get_answers",
        lambda: fake_st.session_state[SSKey.ANSWERS.value],
    )

    def _set_answer(question_id: str, value: Any) -> None:
        fake_st.session_state[SSKey.ANSWERS.value][question_id] = value

    def _mark_answer_touched(question_id: str, _previous: Any, _current: Any) -> None:
        fake_st.session_state[SSKey.ANSWER_META.value][question_id] = {
            "touched": True
        }

    monkeypatch.setattr(ui_layout, "set_answer", _set_answer)
    monkeypatch.setattr(ui_layout, "mark_answer_touched", _mark_answer_touched)

    ui_layout.render_jobspec_step_notes("benefits")

    answers = fake_st.session_state[SSKey.ANSWERS.value]
    answer_id = next(
        key for key in answers if key.startswith("jobspec_assumption.benefits.")
    )
    assert answers[answer_id] == {
        "status": "rejected",
        "correction": "Gehalt ist tariflich festgelegt.",
    }
    assert fake_st.session_state[SSKey.ANSWER_META.value][answer_id]["touched"] is True
