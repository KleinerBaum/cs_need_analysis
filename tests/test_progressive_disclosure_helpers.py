from __future__ import annotations

from typing import Any

from constants import AnswerType
from question_progress import build_answered_lookup, compute_question_progress
from schemas import Question, QuestionDependency, QuestionStep
from ui_components import (
    _collect_incomplete_group_titles,
    _extract_esco_suggestions,
    _group_questions,
    _split_core_and_detail_questions,
)


class _LazyDisclosureFakeStreamlit:
    def __init__(self, *, clicked_keys: set[str] | None = None) -> None:
        self.session_state: dict[str, Any] = {}
        self.clicked_keys = clicked_keys or set()
        self.buttons: list[tuple[str, str | None]] = []
        self.captions: list[str] = []
        self.markdowns: list[str] = []

    def markdown(self, text: str, *_args: Any, **_kwargs: Any) -> None:
        self.markdowns.append(text)

    def caption(self, text: str) -> None:
        self.captions.append(text)

    def button(self, label: str, *, key: str | None = None, **_kwargs: Any) -> bool:
        self.buttons.append((label, key))
        return bool(key and key in self.clicked_keys)


def test_lazy_section_stays_collapsed_without_rendering_slot(monkeypatch) -> None:
    import ui_layout

    fake_st = _LazyDisclosureFakeStreamlit()
    monkeypatch.setattr(ui_layout, "st", fake_st)
    calls: list[str] = []

    ui_layout.render_lazy_section(
        step_key="skills",
        slot_name="source_comparison_slot",
        config=ui_layout.LazySectionConfig(
            label="Quellenabgleich",
            caption="Wird erst bei Bedarf geladen.",
            button_label="Anzeigen",
        ),
        render_slot=lambda: calls.append("rendered"),
    )

    assert calls == []
    assert fake_st.buttons == [
        (
            "Anzeigen",
            "cs.lazy_section.skills.source_comparison_slot.revealed.button",
        )
    ]
    assert "cs.lazy_section.skills.source_comparison_slot.revealed" not in fake_st.session_state


def test_lazy_section_reveals_and_persists_across_reruns(monkeypatch) -> None:
    import ui_layout

    button_key = "cs.lazy_section.skills.source_comparison_slot.revealed.button"
    fake_st = _LazyDisclosureFakeStreamlit(clicked_keys={button_key})
    monkeypatch.setattr(ui_layout, "st", fake_st)
    calls: list[str] = []
    config = ui_layout.LazySectionConfig(
        label="Quellenabgleich",
        caption="Wird erst bei Bedarf geladen.",
        button_label="Anzeigen",
    )

    ui_layout.render_lazy_section(
        step_key="skills",
        slot_name="source_comparison_slot",
        config=config,
        render_slot=lambda: calls.append("first"),
    )
    fake_st.clicked_keys.clear()
    ui_layout.render_lazy_section(
        step_key="skills",
        slot_name="source_comparison_slot",
        config=config,
        render_slot=lambda: calls.append("second"),
    )

    assert calls == ["first", "second"]
    assert fake_st.session_state[
        "cs.lazy_section.skills.source_comparison_slot.revealed"
    ] is True


def test_lazy_section_default_open_renders_without_button(monkeypatch) -> None:
    import ui_layout

    fake_st = _LazyDisclosureFakeStreamlit()
    monkeypatch.setattr(ui_layout, "st", fake_st)
    calls: list[str] = []

    ui_layout.render_lazy_section(
        step_key="role_tasks",
        slot_name="source_comparison_slot",
        config=ui_layout.LazySectionConfig(
            label="Quellenabgleich",
            caption="Wird erst bei Bedarf geladen.",
            default_open=True,
        ),
        render_slot=lambda: calls.append("rendered"),
    )

    assert calls == ["rendered"]
    assert fake_st.buttons == []
    assert fake_st.session_state[
        "cs.lazy_section.role_tasks.source_comparison_slot.revealed"
    ] is True


def test_salary_lazy_section_remains_on_demand(monkeypatch) -> None:
    import ui_layout

    fake_st = _LazyDisclosureFakeStreamlit()
    monkeypatch.setattr(ui_layout, "st", fake_st)
    calls: list[str] = []

    ui_layout.render_lazy_section(
        step_key="benefits",
        slot_name="salary_forecast_slot",
        config=ui_layout.LazySectionConfig(
            label="Gehaltsprognose",
            caption="Berechnung erst auf Anforderung.",
            button_label="Gehaltsprognose laden",
            default_open=False,
        ),
        render_slot=lambda: calls.append("rendered"),
    )

    assert calls == []
    assert fake_st.buttons == [
        (
            "Gehaltsprognose laden",
            "cs.lazy_section.benefits.salary_forecast_slot.revealed.button",
        )
    ]


def test_split_core_and_detail_questions_falls_back_for_legacy_metadata() -> None:
    questions = [
        Question(
            id="q_required_1",
            label="Pflicht 1",
            answer_type=AnswerType.SHORT_TEXT,
            required=True,
        ),
        Question(
            id="q_optional_1",
            label="Optional 1",
            answer_type=AnswerType.SHORT_TEXT,
            required=False,
        ),
        Question(
            id="q_required_2",
            label="Pflicht 2",
            answer_type=AnswerType.SHORT_TEXT,
            required=True,
        ),
    ]

    core, detail = _split_core_and_detail_questions(questions)

    assert [question.id for question in core] == [
        "q_required_1",
        "q_required_2",
        "q_optional_1",
    ]
    assert detail == []


def test_group_incomplete_titles_uses_answered_lookup() -> None:
    core_question = Question(
        id="core_1",
        label="Minimalprofil",
        answer_type=AnswerType.SHORT_TEXT,
        required=True,
        priority="core",
    )
    detail_open = Question(
        id="detail_1",
        label="Detail optional",
        answer_type=AnswerType.SHORT_TEXT,
        required=False,
        priority="detail",
    )
    detail_required = Question(
        id="detail_2",
        label="Detail Pflicht",
        answer_type=AnswerType.SHORT_TEXT,
        required=True,
        priority="detail",
    )
    answers = {"core_1": "Ja", "detail_1": "Done", "detail_2": ""}
    answered_lookup = build_answered_lookup(
        [core_question, detail_open, detail_required],
        answers,
        answer_meta={},
    )

    incomplete = _collect_incomplete_group_titles(
        [("Details", [detail_open, detail_required])],
        answers,
        answer_meta={},
        answered_lookup=answered_lookup,
    )

    assert incomplete == ["Details"]
    detail_progress = compute_question_progress(
        [detail_open, detail_required],
        answers,
        answer_meta={},
        answered_lookup=answered_lookup,
    )
    assert detail_progress["required_unanswered"] == 1


def test_declared_dependency_is_answered_handles_placeholder_like_values() -> None:
    dependent_question = Question(
        id="detail_dep",
        label="Follow-up",
        answer_type=AnswerType.SHORT_TEXT,
        depends_on=[QuestionDependency(question_id="work_mode", is_answered=True)],
    )

    from question_dependencies import should_show_question

    assert (
        should_show_question(
            dependent_question,
            answers={"work_mode": "— Bitte wählen —"},
            answer_meta={},
            step_key="company",
        )
        is False
    )
    assert (
        should_show_question(
            dependent_question,
            answers={"work_mode": "Hybrid"},
            answer_meta={},
            step_key="company",
        )
        is True
    )


def test_extract_esco_suggestions_accepts_alternate_type_fields() -> None:
    payload = {
        "_embedded": {
            "results": [
                {
                    "uri": "http://data.europa.eu/esco/occupation/123",
                    "preferredLabel": "Data Analyst",
                    "conceptType": "occupation",
                }
            ]
        }
    }

    suggestions = _extract_esco_suggestions(
        payload,
        concept_type="occupation",
        source="auto",
    )

    assert suggestions == [
        {
            "uri": "http://data.europa.eu/esco/occupation/123",
            "title": "Data Analyst",
            "type": "occupation",
            "source": "auto",
        }
    ]


def test_extract_esco_suggestions_keeps_unknown_type_with_matching_uri_hint() -> None:
    payload = {
        "results": [
            {
                "uri": "http://data.europa.eu/esco/skill/abc",
                "title": "Python programming",
                "type": "",
            },
            {
                "uri": "http://data.europa.eu/esco/occupation/xyz",
                "title": "Should not be a skill",
                "type": "occupation",
            },
        ]
    }

    suggestions = _extract_esco_suggestions(
        payload,
        concept_type="skill",
        source="manual",
    )

    assert suggestions == [
        {
            "uri": "http://data.europa.eu/esco/skill/abc",
            "title": "Python programming",
            "type": "skill",
            "source": "manual",
        }
    ]


def test_group_questions_uses_new_role_step_section_labels() -> None:
    step = QuestionStep(
        step_key="role_tasks",
        title_de="Rolle & Aufgaben",
        questions=[
            Question(
                id="role_scope",
                label="Rollenfokus",
                answer_type=AnswerType.SHORT_TEXT,
            ),
            Question(
                id="deliverables",
                label="Aufgabenbeschreibung",
                answer_type=AnswerType.SHORT_TEXT,
            ),
            Question(
                id="kpi_outcome",
                label="Erfolgskriterien",
                answer_type=AnswerType.SHORT_TEXT,
            ),
            Question(
                id="stakeholder_sync",
                label="Zusammenarbeit mit Stakeholdern",
                answer_type=AnswerType.SHORT_TEXT,
            ),
        ],
    )

    grouped = _group_questions(step, step.questions)
    group_titles = [title for title, _ in grouped]

    assert group_titles == [
        "Rollen-Detailfragen",
        "Verantwortung & Scope",
        "Erfolgskriterien",
        "Zusammenarbeit",
    ]


def test_extract_esco_suggestions_falls_back_for_unresolved_unknown_type() -> None:
    payload = {
        "results": [
            {
                "uri": "http://data.europa.eu/esco/resource/misc",
                "label": "Generic ESCO node",
                "className": None,
            }
        ]
    }

    suggestions = _extract_esco_suggestions(
        payload,
        concept_type="occupation",
        source="auto",
    )

    assert suggestions == [
        {
            "uri": "http://data.europa.eu/esco/resource/misc",
            "title": "Generic ESCO node",
            "type": "occupation",
            "source": "auto",
        }
    ]
