from __future__ import annotations

from typing import Any
from typing import Literal

import ui_components
from schemas import AnswerType, Question, QuestionStep


class _NoopContext:
    def __enter__(self) -> "_NoopContext":
        return self

    def __exit__(self, *_: object) -> Literal[False]:
        return False


class _FakeStreamlitRecorder:
    def __init__(self) -> None:
        self.session_state: dict[str, Any] = {}
        self.container_calls: list[bool] = []
        self.markdowns: list[str] = []
        self.captions: list[str] = []
        self.warnings: list[str] = []
        self.events: list[tuple[str, str]] = []
        self.expanders: list[tuple[str, bool]] = []

    def container(self, *, border: bool = False) -> _NoopContext:
        self.container_calls.append(border)
        return _NoopContext()

    def markdown(self, message: str, *_: Any, **__: Any) -> None:
        self.markdowns.append(message)
        self.events.append(("markdown", message))

    def caption(self, message: str, *_: Any, **__: Any) -> None:
        self.captions.append(message)
        self.events.append(("caption", message))

    def warning(self, message: str, *_: Any, **__: Any) -> None:
        self.warnings.append(message)
        self.events.append(("warning", message))

    def columns(self, spec: int | list[int], **_: Any) -> list[_NoopContext]:
        count = spec if isinstance(spec, int) else len(spec)
        return [_NoopContext() for _ in range(count)]

    def expander(self, label: str, *, expanded: bool = False) -> _NoopContext:
        self.expanders.append((label, expanded))
        self.events.append(("expander", label))
        return _NoopContext()


def _question(
    *,
    question_id: str,
    label: str,
    required: bool = True,
    group_key: str,
    answer_type: AnswerType = AnswerType.SHORT_TEXT,
) -> Question:
    return Question(
        id=question_id,
        label=label,
        answer_type=answer_type,
        required=required,
        group_key=group_key,
    )


def _step_with_questions(questions: list[Question]) -> QuestionStep:
    return QuestionStep(step_key="tasks", title_de="Tasks", questions=questions)


def test_render_step_review_card_shows_missing_essentials_before_group_cards(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlitRecorder()
    monkeypatch.setattr(ui_components, "st", fake_st)

    q_essential = _question(
        question_id="q_essential",
        label="Essenzielle Frage",
        group_key="group_a",
    )
    q_answered_a = _question(
        question_id="q_a",
        label="Antwort Gruppe A",
        required=False,
        group_key="group_a",
    )
    q_answered_b = _question(
        question_id="q_b",
        label="Antwort Gruppe B",
        required=False,
        group_key="group_b",
    )
    step = _step_with_questions([q_essential, q_answered_a, q_answered_b])

    ui_components.render_step_review_card(
        step=step,
        visible_questions=step.questions,
        answers={"q_a": "Erledigt", "q_b": "Done"},
        answer_meta={},
        answered_lookup={"q_essential": False, "q_a": True, "q_b": True},
        step_status={
            "answered": 2,
            "total": 3,
            "completion_state": "partial",
            "essentials_answered": 0,
            "essentials_total": 1,
            "missing_essentials": ["Essenzielle Frage"],
            "missing_essential_ids": ["q_essential"],
        },
    )

    essentials_idx = fake_st.markdowns.index("##### ⚠️ Essentials offen")
    first_group_idx = fake_st.markdowns.index("**Group A**")
    assert essentials_idx < first_group_idx


def test_render_step_review_card_renders_group_status_indicators(monkeypatch) -> None:
    fake_st = _FakeStreamlitRecorder()
    monkeypatch.setattr(ui_components, "st", fake_st)

    full_q1 = _question(question_id="g1_q1", label="G1 Frage 1", group_key="group_full")
    full_q2 = _question(question_id="g1_q2", label="G1 Frage 2", group_key="group_full")
    partial_q1 = _question(question_id="g2_q1", label="G2 Frage 1", group_key="group_partial")
    partial_q2 = _question(question_id="g2_q2", label="G2 Frage 2", group_key="group_partial")
    step = _step_with_questions([full_q1, full_q2, partial_q1, partial_q2])

    ui_components.render_step_review_card(
        step=step,
        visible_questions=step.questions,
        answers={
            "g1_q1": "x",
            "g1_q2": "y",
            "g2_q1": "z",
        },
        answer_meta={},
        answered_lookup={
            "g1_q1": True,
            "g1_q2": True,
            "g2_q1": True,
            "g2_q2": False,
        },
        step_status=None,
    )

    assert "**Group Full**" in fake_st.markdowns
    assert "**Group Partial**" in fake_st.markdowns
    assert "✅ vollständig" in fake_st.captions
    assert "⚠️ offen" in fake_st.captions
    assert ("Gruppenstatus", False) in fake_st.expanders


def test_render_step_review_card_truncates_long_answer_previews(monkeypatch) -> None:
    fake_st = _FakeStreamlitRecorder()
    monkeypatch.setattr(ui_components, "st", fake_st)

    long_question = _question(
        question_id="long_text",
        label="Lange Antwort",
        group_key="group_preview",
        answer_type=AnswerType.LONG_TEXT,
    )
    step = _step_with_questions([long_question])
    long_text = "x" * 200

    ui_components.render_step_review_card(
        step=step,
        visible_questions=step.questions,
        answers={"long_text": long_text},
        answer_meta={},
        answered_lookup={"long_text": True},
        step_status=None,
    )

    expected = ui_components._truncate_for_review(long_text, limit=140)
    assert f"Lange Antwort: {expected}" in fake_st.captions


def test_render_step_review_card_maps_missing_essentials_by_id_with_duplicate_labels(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlitRecorder()
    monkeypatch.setattr(ui_components, "st", fake_st)

    q_dup_a = _question(
        question_id="dup_a",
        label="Doppelte Frage",
        group_key="group_a",
    )
    q_dup_b = _question(
        question_id="dup_b",
        label="Doppelte Frage",
        group_key="group_b",
    )
    q_answered = _question(
        question_id="group_b_answered",
        label="Antwort B",
        required=False,
        group_key="group_b",
    )
    step = _step_with_questions([q_dup_a, q_dup_b, q_answered])

    ui_components.render_step_review_card(
        step=step,
        visible_questions=step.questions,
        answers={"dup_a": "gesetzt", "group_b_answered": "ok"},
        answer_meta={},
        answered_lookup={"dup_a": True, "dup_b": False, "group_b_answered": True},
        step_status={
            "answered": 1,
            "total": 3,
            "completion_state": "partial",
            "essentials_answered": 0,
            "essentials_total": 2,
            "missing_essentials": ["Doppelte Frage"],
            "missing_essential_ids": ["dup_b"],
        },
    )

    affected_group_caption = next(
        caption
        for caption in fake_st.captions
        if caption.startswith("Betroffene Gruppen:")
    )
    assert "Group B" in affected_group_caption
    assert "Group A" not in affected_group_caption


def test_render_step_review_card_shows_open_question_count_without_input_widgets(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlitRecorder()
    monkeypatch.setattr(ui_components, "st", fake_st)

    unanswered_question = _question(
        question_id="group_open_q1",
        label="Noch offen",
        group_key="group_open",
    )
    step = _step_with_questions([unanswered_question])

    ui_components.render_step_review_card(
        step=step,
        visible_questions=step.questions,
        answers={},
        answer_meta={},
        answered_lookup={"group_open_q1": False},
        step_status=None,
    )

    assert (
        "1 offene Frage(n) – Details und direkte Eingabe im Bereich „Gruppenstatus“."
        in fake_st.captions
    )


def test_render_step_review_card_compact_summary_with_group_counts(monkeypatch) -> None:
    fake_st = _FakeStreamlitRecorder()
    monkeypatch.setattr(ui_components, "st", fake_st)

    questions = [
        _question(question_id="q1", label="Frage 1", group_key="group_a"),
        _question(question_id="q2", label="Frage 2", group_key="group_a"),
        _question(question_id="q3", label="Frage 3", required=False, group_key="group_b"),
    ]
    step = _step_with_questions(questions)
    ui_components.render_step_review_card(
        step=step,
        visible_questions=questions,
        answers={"q1": "ok", "q3": "ok"},
        answer_meta={},
        answered_lookup={"q1": True, "q2": False, "q3": True},
        step_status={
            "answered": 2,
            "total": 3,
            "completion_state": "partial",
            "essentials_answered": 1,
            "essentials_total": 2,
            "missing_essentials": ["Frage 2"],
            "missing_essential_ids": ["q2"],
        },
    )

    assert "• Beantwortet 2/3" in fake_st.captions
    assert "⚠️ Essentials 1/2" in fake_st.captions
    assert "⚠️ Gruppen 1 vollständig · 1 offen" in fake_st.captions


def test_render_question_step_hides_verbose_progress_captions(monkeypatch) -> None:
    class _FakeStepStreamlit:
        def __init__(self) -> None:
            self.session_state: dict[str, Any] = {
                "cs.ui_mode": "standard",
                "cs.question_limits": {},
            }
            self.captions: list[str] = []
            self.markdowns: list[str] = []

        def caption(self, message: str, *_: Any, **__: Any) -> None:
            self.captions.append(message)

        def markdown(self, message: str, *_: Any, **__: Any) -> None:
            self.markdowns.append(message)

        def info(self, *_: Any, **__: Any) -> None:
            return None

        def container(self, *, border: bool = False) -> _NoopContext:
            del border
            return _NoopContext()

        def columns(self, spec: int | list[int], **_: Any) -> list[_NoopContext]:
            count = spec if isinstance(spec, int) else len(spec)
            return [_NoopContext() for _ in range(count)]

    fake_st = _FakeStepStreamlit()
    monkeypatch.setattr(ui_components, "st", fake_st)
    monkeypatch.setattr(ui_components, "get_answers", lambda: {})
    monkeypatch.setattr(ui_components, "get_answer_meta", lambda: {})
    monkeypatch.setattr(
        ui_components,
        "_render_questions_two_columns",
        lambda _questions, _answers: None,
    )
    step = QuestionStep(
        step_key="company",
        title_de="Company",
        questions=[
            Question(
                id="company_q_1",
                label="Unternehmensgröße",
                answer_type=AnswerType.SHORT_TEXT,
                required=True,
                group_key="company",
            )
        ],
    )

    ui_components.render_question_step(step)

    assert not any(caption.startswith("Beantwortet:") for caption in fake_st.captions)
    assert not any(
        caption.startswith("Sichtbar im aktuellen Umfang:")
        for caption in fake_st.captions
    )
    assert not any(
        caption.startswith("Gesamt im Step (inkl. derzeit ausgeblendeter Details):")
        for caption in fake_st.captions
    )
    assert not any(
        caption.startswith("Pflichtfragen offen in:") for caption in fake_st.captions
    )


def test_render_step_review_card_shows_compact_essentials_and_direct_answer_hint_when_inline_disabled(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlitRecorder()
    monkeypatch.setattr(ui_components, "st", fake_st)
    monkeypatch.setattr(ui_components, "_can_render_inline_answer_inputs", lambda: False)

    questions = [
        _question(question_id="q1", label="Essentiell 1", group_key="group_a"),
        _question(question_id="q2", label="Essentiell 2", group_key="group_b"),
        _question(question_id="q3", label="Optional", required=False, group_key="group_b"),
    ]
    step = _step_with_questions(questions)

    ui_components.render_step_review_card(
        step=step,
        visible_questions=questions,
        answers={"q3": "ok"},
        answer_meta={},
        answered_lookup={"q1": False, "q2": False, "q3": True},
        step_status={
            "answered": 1,
            "total": 3,
            "completion_state": "partial",
            "essentials_answered": 0,
            "essentials_total": 2,
            "missing_essentials": ["Essentiell 1", "Essentiell 2"],
            "missing_essential_ids": ["q1", "q2"],
        },
    )

    assert "• Beantwortet 1/3" in fake_st.captions
    assert "⚠️ Essentials 0/2" in fake_st.captions
    assert "⚠️ Gruppen 0 vollständig · 2 offen" in fake_st.captions
    assert "##### ⚠️ Essentials offen" in fake_st.markdowns
    assert any(
        "offene Frage(n) – Details und direkte Eingabe im Bereich „Gruppenstatus“."
        in caption
        for caption in fake_st.captions
    )


def test_render_step_review_card_hides_direct_answer_hint_when_no_open_questions(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlitRecorder()
    monkeypatch.setattr(ui_components, "st", fake_st)
    monkeypatch.setattr(ui_components, "_can_render_inline_answer_inputs", lambda: False)

    questions = [
        _question(question_id="q1", label="Essentiell 1", group_key="group_a"),
        _question(question_id="q2", label="Optional", required=False, group_key="group_a"),
    ]
    step = _step_with_questions(questions)

    ui_components.render_step_review_card(
        step=step,
        visible_questions=questions,
        answers={"q1": "ok", "q2": "ok"},
        answer_meta={},
        answered_lookup={"q1": True, "q2": True},
        step_status={
            "answered": 2,
            "total": 2,
            "completion_state": "complete",
            "essentials_answered": 1,
            "essentials_total": 1,
            "missing_essentials": [],
            "missing_essential_ids": [],
        },
    )

    assert not any("offene Frage(n)" in caption for caption in fake_st.captions)
