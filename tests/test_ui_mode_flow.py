from __future__ import annotations

from typing import Any

from streamlit.errors import StreamlitAPIException

import wizard_pages.base as base
import wizard_pages.salary_forecast as salary_forecast
from constants import (
    SSKey,
    STEPS,
    STEP_KEY_TEAM,
    UI_PREFERENCE_ANSWER_MODE,
    UI_PREFERENCE_DETAILS_EXPANDED_DEFAULT,
    UI_PREFERENCE_INFORMATION_DEPTH,
    UI_PREFERENCE_WIZARD_DESIGN,
)
from schemas import JobAdExtract, RecruitmentStep


class _LockedSessionState(dict[str, Any]):
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.locked_keys: set[str] = set()

    def __setitem__(self, key: str, value: Any) -> None:
        if key in self.locked_keys:
            raise StreamlitAPIException(
                f"Widget key '{key}' cannot be mutated post-render."
            )
        super().__setitem__(key, value)


class _FakeStreamlit:
    def __init__(self, session_state: _LockedSessionState) -> None:
        self.session_state = session_state
        self.sidebar = self
        self.checkbox_labels: list[str] = []
        self.markdown_calls: list[str] = []
        self.caption_calls: list[str] = []
        self.expander_labels: list[str] = []

    def markdown(self, body: str, **_kwargs: Any) -> None:
        self.markdown_calls.append(body)

    def caption(self, body: str, **_kwargs: Any) -> None:
        self.caption_calls.append(body)

    class _Expander:
        def __init__(self, owner: "_FakeStreamlit", label: str) -> None:
            self.owner = owner
            self.label = label

        def __enter__(self) -> "_FakeStreamlit":
            return self.owner

        def __exit__(self, *_args: Any) -> None:
            return None

    def expander(self, label: str, **_kwargs: Any) -> "_FakeStreamlit._Expander":
        self.expander_labels.append(label)
        return _FakeStreamlit._Expander(self, label)

    def checkbox(
        self,
        label: str,
        *,
        value: bool = False,
        key: str | None = None,
        **_kwargs: Any,
    ) -> bool:
        self.checkbox_labels.append(label)
        if key is not None:
            self.session_state.locked_keys.add(key)
        return bool(value)

    def selectbox(
        self,
        _label: str,
        *,
        options: list[str],
        key: str,
        index: int | None = None,
        on_change: Any | None = None,
        **_kwargs: Any,
    ) -> str:
        if key not in self.session_state:
            fallback_index = index if index is not None else 0
            self.session_state[key] = options[fallback_index]
        self.session_state.locked_keys.add(key)
        if on_change is not None:
            on_change()
        return str(self.session_state[key])

    def radio(
        self,
        _label: str,
        *,
        options: list[str],
        key: str,
        **_kwargs: Any,
    ) -> str:
        if key not in self.session_state:
            self.session_state[key] = options[0]
        return str(self.session_state[key])


def test_render_ui_mode_selector_does_not_mutate_widget_bound_mode_key(
    monkeypatch,
) -> None:
    session_state = _LockedSessionState(
        {
            SSKey.UI_MODE.value: "standard",
            SSKey.UI_PREFERENCES.value: {UI_PREFERENCE_ANSWER_MODE: "balanced"},
        }
    )
    fake_st = _FakeStreamlit(session_state)
    monkeypatch.setattr(base, "st", fake_st)
    monkeypatch.setattr(base, "sync_adaptive_question_limits", lambda: None)

    selected_mode = base.render_ui_mode_selector(widget_key=SSKey.UI_MODE.value)

    assert selected_mode == "standard"
    assert session_state[SSKey.UI_MODE.value] == "standard"
    assert (
        session_state[SSKey.UI_PREFERENCES.value][UI_PREFERENCE_ANSWER_MODE]
        == "balanced"
    )
    assert (
        session_state[SSKey.UI_PREFERENCES.value][UI_PREFERENCE_INFORMATION_DEPTH]
        == "standard"
    )


def test_render_ui_mode_selector_derives_legacy_preference_metadata(monkeypatch) -> None:
    session_state = _LockedSessionState(
        {
            SSKey.UI_MODE.value: "expert",
            SSKey.UI_PREFERENCES.value: {
                UI_PREFERENCE_ANSWER_MODE: "balanced",
                UI_PREFERENCE_INFORMATION_DEPTH: "standard",
            },
        }
    )
    fake_st = _FakeStreamlit(session_state)
    monkeypatch.setattr(base, "st", fake_st)
    monkeypatch.setattr(base, "sync_adaptive_question_limits", lambda: None)

    selected_mode = base.render_ui_mode_selector(widget_key=SSKey.UI_MODE.value)

    assert selected_mode == "expert"
    assert (
        session_state[SSKey.UI_PREFERENCES.value][UI_PREFERENCE_ANSWER_MODE]
        == "advisory"
    )
    assert (
        session_state[SSKey.UI_PREFERENCES.value][UI_PREFERENCE_INFORMATION_DEPTH]
        == "hoch"
    )


def test_render_wizard_design_selector_preserves_widget_selection(monkeypatch) -> None:
    widget_key = "test.wizard_design"
    session_state = _LockedSessionState(
        {
            widget_key: "focus",
            SSKey.UI_PREFERENCES.value: {UI_PREFERENCE_WIZARD_DESIGN: "classic"},
        }
    )
    fake_st = _FakeStreamlit(session_state)
    monkeypatch.setattr(base, "st", fake_st)

    selected_design = base.render_wizard_design_selector(widget_key=widget_key)

    assert selected_design == "focus"
    assert session_state[widget_key] == "focus"
    assert (
        session_state[SSKey.UI_PREFERENCES.value][UI_PREFERENCE_WIZARD_DESIGN]
        == "focus"
    )


def test_visible_step_set_for_ui_mode_navigation_excludes_team_step() -> None:
    visible_step_keys = [step.key for step in STEPS]

    assert STEP_KEY_TEAM not in visible_step_keys
    assert visible_step_keys == [
        "intro",
        "landing",
        "company",
        "role_tasks",
        "skills",
        "benefits",
        "interview",
        "summary",
    ]


def test_lazy_source_section_default_follows_mode_and_details_preference(
    monkeypatch,
) -> None:
    import ui_layout

    cases = [
        ("quick", {}, False),
        ("standard", {}, False),
        ("expert", {}, True),
        ("quick", {UI_PREFERENCE_DETAILS_EXPANDED_DEFAULT: True}, True),
        ("expert", {UI_PREFERENCE_DETAILS_EXPANDED_DEFAULT: False}, False),
        (
            "expert",
            {UI_PREFERENCE_WIZARD_DESIGN: "focus"},
            False,
        ),
        (
            "standard",
            {
                UI_PREFERENCE_WIZARD_DESIGN: "focus",
                UI_PREFERENCE_DETAILS_EXPANDED_DEFAULT: True,
            },
            True,
        ),
    ]
    for ui_mode, preferences, expected in cases:
        session_state = _LockedSessionState(
            {
                SSKey.UI_MODE.value: ui_mode,
                SSKey.UI_PREFERENCES.value: preferences,
            }
        )
        monkeypatch.setattr(ui_layout, "st", _FakeStreamlit(session_state))

        assert ui_layout.default_lazy_source_section_open() is expected


def test_set_current_step_records_step_entered_once(monkeypatch) -> None:
    session_state = _LockedSessionState({SSKey.CURRENT_STEP.value: "landing"})
    fake_st = _FakeStreamlit(session_state)
    monkeypatch.setattr(base, "st", fake_st)

    base.set_current_step("company")
    base.set_current_step("company")

    assert session_state[SSKey.USAGE_EVENTS.value] == [
        {
            "event_type": "step_entered",
            "occurred_at": session_state[SSKey.USAGE_EVENTS.value][0]["occurred_at"],
            "metadata": {"step_key": "company"},
        }
    ]


def test_sidebar_salary_forecast_is_rendered_for_all_ui_modes(monkeypatch) -> None:
    rendered_modes: list[str] = []
    computed_modes: list[str] = []

    def _fake_compute_sidebar_salary_forecast(**_kwargs: Any) -> object:
        computed_modes.append(str(base.st.session_state[SSKey.UI_MODE.value]))
        return object()

    def _fake_render_sidebar_salary_forecast(**_kwargs: Any) -> bool:
        rendered_modes.append(str(base.st.session_state[SSKey.UI_MODE.value]))
        return False

    monkeypatch.setattr(base, "sync_adaptive_question_limits", lambda: None)
    monkeypatch.setattr(
        base,
        "_compute_step_statuses",
        lambda _pages: [
            {
                "key": "landing",
                "status": "not_started",
                "answered": 0,
                "total": 0,
                "payload": {},
            }
        ],
    )
    monkeypatch.setattr(base, "_render_esco_warnings_and_migration_cta", lambda: None)
    monkeypatch.setattr(
        base, "_compute_sidebar_salary_forecast", _fake_compute_sidebar_salary_forecast
    )
    monkeypatch.setattr(
        base, "render_sidebar_salary_forecast", _fake_render_sidebar_salary_forecast
    )

    ctx = base.WizardContext(
        pages=[
            base.WizardPage(
                key="landing",
                title_de="Start",
                icon="",
                render=lambda _ctx: None,
            )
        ]
    )

    for mode in ("quick", "standard", "expert"):
        session_state = _LockedSessionState(
            {
                SSKey.CURRENT_STEP.value: "landing",
                SSKey.NAV_SELECTED.value: "landing",
                SSKey.NAV_SYNC_PENDING.value: False,
                SSKey.UI_MODE.value: mode,
                SSKey.JOB_EXTRACT.value: {"job_title": "Friseurmeisterin"},
                SSKey.ANSWERS.value: {"job_title": "Friseurmeisterin"},
                SSKey.SOURCE_TEXT.value: "",
            }
        )
        monkeypatch.setattr(base, "st", _FakeStreamlit(session_state))

        current_page = base.sidebar_navigation(ctx)

        assert current_page.key == "landing"

    assert computed_modes == []
    assert rendered_modes == ["quick", "standard", "expert"]


def test_sidebar_salary_input_selections_default_active_and_persist(
    monkeypatch,
) -> None:
    session_state = _LockedSessionState(
        {
            SSKey.JOB_EXTRACT.value: {"job_title": "Engineer"},
            SSKey.ROLE_TASKS_SELECTED.value: ["Build APIs"],
            SSKey.SALARY_FORECAST_INPUT_SELECTIONS.value: {},
        }
    )
    monkeypatch.setattr(base, "st", _FakeStreamlit(session_state))

    rows = base._build_sidebar_salary_input_rows()
    selections = base._sync_sidebar_salary_input_selections(rows)

    assert rows
    assert all(selections[row.id] is True for row in rows)

    first_row_id = rows[0].id
    session_state[SSKey.SALARY_FORECAST_INPUT_SELECTIONS.value][first_row_id] = False
    persisted = base._sync_sidebar_salary_input_selections(rows)

    assert persisted[first_row_id] is False


def test_sidebar_salary_input_selection_groups_repeated_prefix_labels(
    monkeypatch,
) -> None:
    session_state = _LockedSessionState(
        {SSKey.SALARY_FORECAST_INPUT_SELECTIONS.value: {}}
    )
    fake_st = _FakeStreamlit(session_state)
    monkeypatch.setattr(salary_forecast, "st", fake_st)
    rows = [
        base.SalarySidebarInputRow(
            id="city",
            group="Rolle & Standort",
            label="Stadt: Berlin",
            value="Berlin",
            target="location_city",
            source_label="Stored vacancy fact",
            label_prefix="Stadt",
            display_value="Berlin",
        ),
        base.SalarySidebarInputRow(
            id="task-1",
            group="Aufgaben",
            label="Aufgabe: Kunden beraten",
            value="Kunden beraten",
            target="responsibilities",
            source_label="Stored vacancy fact",
            label_prefix="Aufgabe",
            display_value="Kunden beraten",
        ),
        base.SalarySidebarInputRow(
            id="task-2",
            group="Aufgaben",
            label="Aufgabe: Lösungen konzipieren",
            value="Lösungen konzipieren",
            target="responsibilities",
            source_label="Stored vacancy fact",
            label_prefix="Aufgabe",
            display_value="Lösungen konzipieren",
        ),
        base.SalarySidebarInputRow(
            id="selected-task-1",
            group="Aufgaben",
            label="Ausgewählte Aufgabe: Workshop moderieren",
            value="Workshop moderieren",
            target="responsibilities",
            source_label="Manual task selection",
            label_prefix="Ausgewählte Aufgabe",
            display_value="Workshop moderieren",
        ),
        base.SalarySidebarInputRow(
            id="selected-task-2",
            group="Aufgaben",
            label="Ausgewählte Aufgabe: Roadmap priorisieren",
            value="Roadmap priorisieren",
            target="responsibilities",
            source_label="Manual task selection",
            label_prefix="Ausgewählte Aufgabe",
            display_value="Roadmap priorisieren",
        ),
    ]

    selections = salary_forecast._render_sidebar_input_selection(
        input_rows=rows,
        input_selections={"selected-task-2": False},
    )

    assert "**Aufgabe (2)**" in fake_st.markdown_calls
    assert "**Ausgewählte Aufgabe (2)**" in fake_st.markdown_calls
    assert "Stadt: Berlin" in fake_st.checkbox_labels
    assert "Aufgabe: Kunden beraten" not in fake_st.checkbox_labels
    assert "Ausgewählte Aufgabe: Workshop moderieren" not in fake_st.checkbox_labels
    assert {
        "Kunden beraten",
        "Lösungen konzipieren",
        "Workshop moderieren",
        "Roadmap priorisieren",
    }.issubset(set(fake_st.checkbox_labels))
    assert selections["selected-task-2"] is False
    assert session_state[SSKey.SALARY_FORECAST_INPUT_SELECTIONS.value] == selections


def test_sidebar_salary_fingerprint_changes_with_selection(monkeypatch) -> None:
    session_state = _LockedSessionState(
        {
            SSKey.JOB_EXTRACT.value: {"job_title": "Engineer"},
            SSKey.ROLE_TASKS_SELECTED.value: ["Build APIs"],
            SSKey.SALARY_FORECAST_INPUT_SELECTIONS.value: {},
        }
    )
    monkeypatch.setattr(base, "st", _FakeStreamlit(session_state))

    rows = base._build_sidebar_salary_input_rows()
    selections = base._sync_sidebar_salary_input_selections(rows)
    first = base._sidebar_salary_fingerprint(rows=rows, selections=selections)
    selections[rows[0].id] = False
    second = base._sidebar_salary_fingerprint(rows=rows, selections=selections)

    assert second != first


def test_sidebar_salary_job_excludes_disabled_inputs(monkeypatch) -> None:
    session_state = _LockedSessionState({})
    monkeypatch.setattr(base, "st", _FakeStreamlit(session_state))
    disabled = base.SalarySidebarInputRow(
        id="python",
        group="Skills",
        label="Must-have: Python",
        value="Python",
        target="must_have_skills",
        source_label="test",
    )
    enabled = base.SalarySidebarInputRow(
        id="go",
        group="Skills",
        label="Must-have: Go",
        value="Go",
        target="must_have_skills",
        source_label="test",
    )

    job, answers = base._sidebar_job_and_answers(
        base_job=JobAdExtract(job_title="Engineer", must_have_skills=["Legacy"]),
        rows=[disabled, enabled],
        selections={"python": False, "go": True},
        source_text="",
    )

    assert job is not None
    assert job.must_have_skills == ["Go"]
    assert "python" not in answers
    assert answers["go"] == "Go"


def test_sidebar_salary_job_validates_recruitment_step_updates(monkeypatch) -> None:
    session_state = _LockedSessionState({})
    monkeypatch.setattr(base, "st", _FakeStreamlit(session_state))
    row = base.SalarySidebarInputRow(
        id="hr-screen",
        group="Interview",
        label="Schritt: HR Screen",
        value={"name": "HR Screen", "duration_minutes": 45},
        target="recruitment_steps",
        source_label="test",
    )

    job, answers = base._sidebar_job_and_answers(
        base_job=JobAdExtract(job_title="Engineer"),
        rows=[row],
        selections={"hr-screen": True},
        source_text="",
    )

    assert job is not None
    assert job.recruitment_steps == [RecruitmentStep(name="HR Screen")]
    assert answers["hr-screen"] == {"name": "HR Screen", "duration_minutes": 45}


def test_compute_sidebar_salary_forecast_passes_esco_and_scenario(
    monkeypatch,
) -> None:
    from salary.types import SalaryEscoContext, SalaryScenarioInputs

    captured: dict[str, Any] = {}

    def _fake_compute_salary_forecast(**kwargs: Any) -> object:
        captured.update(kwargs)
        return object()

    monkeypatch.setattr(
        "salary.engine.compute_salary_forecast", _fake_compute_salary_forecast
    )
    esco_context = SalaryEscoContext(occupation_uri="https://example.test/occ")
    scenario_inputs = SalaryScenarioInputs(remote_share_percent=75)

    result = base._compute_sidebar_salary_forecast(
        job=JobAdExtract(job_title="Engineer"),
        answers={"skill": "Python"},
        source_text="",
        esco_context=esco_context,
        scenario_inputs=scenario_inputs,
    )

    assert result is not None
    assert captured["esco_context"] == esco_context
    assert captured["scenario_inputs"] == scenario_inputs
