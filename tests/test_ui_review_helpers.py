from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
from typing import Any
from typing import Literal

import ui_components
from constants import (
    FactKey,
    QUESTION_IMPACT_TARGET_EXPORT,
    QUESTION_IMPACT_TARGET_SKILLS,
    SSKey,
    UI_PREFERENCE_CONFIDENCE_THRESHOLD,
)
from schemas import AnswerType, JobAdExtract, Question, QuestionStep


INTERVIEW_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "07_interview.py"
INTERVIEW_SPEC = spec_from_file_location("wizard_pages.page_07_interview_ui", INTERVIEW_PATH)
if INTERVIEW_SPEC is None or INTERVIEW_SPEC.loader is None:
    raise RuntimeError("Could not load interview page module")
INTERVIEW_MODULE = module_from_spec(INTERVIEW_SPEC)
INTERVIEW_SPEC.loader.exec_module(INTERVIEW_MODULE)  # type: ignore[attr-defined]


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
        render_mode=ui_components.ReviewRenderMode.FULL,
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
        render_mode=ui_components.ReviewRenderMode.FULL,
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
        render_mode=ui_components.ReviewRenderMode.FULL,
        step_status=None,
    )

    expected = ui_components._truncate_for_review(long_text, limit=140)
    assert any(
        caption.startswith(f"Lange Antwort: {expected}")
        and "Eingabe" in caption
        for caption in fake_st.captions
    )


def test_render_step_review_card_displays_jobspec_covered_answer(monkeypatch) -> None:
    fake_st = _FakeStreamlitRecorder()
    monkeypatch.setattr(ui_components, "st", fake_st)

    company_question = _question(
        question_id="company_context_name",
        label="Wie heißt das Unternehmen?",
        group_key="company_info",
    )
    step = _step_with_questions([company_question])

    ui_components.render_step_review_card(
        step=step,
        visible_questions=step.questions,
        answers={},
        answer_meta={},
        answered_lookup={"company_context_name": True},
        render_mode=ui_components.ReviewRenderMode.FULL,
        step_status={
            "answered": 1,
            "total": 1,
            "completion_state": "complete",
            "essentials_answered": 1,
            "essentials_total": 1,
            "missing_essentials": [],
            "missing_essential_ids": [],
        },
        job_extract=JobAdExtract(company_name="Rheinbahn"),
    )

    assert any(
        "Wie heißt das Unternehmen? (Jobspec): Rheinbahn" in caption
        for caption in fake_st.captions
    )


def test_render_step_review_card_marks_open_low_confidence_fact_without_snippet(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlitRecorder()
    monkeypatch.setattr(ui_components, "st", fake_st)

    company_question = _question(
        question_id="company_name",
        label="Wie heißt das Unternehmen?",
        group_key="company_info",
    )
    company_question.target_path = FactKey.COMPANY_COMPANY_NAME.value
    step = _step_with_questions([company_question])

    ui_components.render_step_review_card(
        step=step,
        visible_questions=step.questions,
        answers={},
        answer_meta={},
        answered_lookup=None,
        render_mode=ui_components.ReviewRenderMode.FULL,
        step_status=None,
        intake_facts={FactKey.COMPANY_COMPANY_NAME.value: "Acme GmbH"},
        intake_fact_evidence={
            FactKey.COMPANY_COMPANY_NAME.value: {
                "confidence": 0.4,
                "resolution_status": "conflicted",
                "evidence_snippet": "Do not leak recruiting@example.test",
            }
        },
        confidence_threshold=0.6,
    )

    joined_captions = " ".join(fake_st.captions)
    assert (
        "Zu prüfen: Wie heißt das Unternehmen?: Konflikt · 40% · prüfen"
        in joined_captions
    )
    assert "Do not leak" not in joined_captions
    assert "recruiting@example.test" not in joined_captions


def test_render_step_review_card_prefers_user_answer_over_jobspec(monkeypatch) -> None:
    fake_st = _FakeStreamlitRecorder()
    monkeypatch.setattr(ui_components, "st", fake_st)

    company_question = _question(
        question_id="company_name",
        label="Wie heißt das Unternehmen?",
        group_key="company_info",
    )
    step = _step_with_questions([company_question])

    ui_components.render_step_review_card(
        step=step,
        visible_questions=step.questions,
        answers={"company_name": "Manuell GmbH"},
        answer_meta={"company_name": {"touched": True}},
        answered_lookup={"company_name": True},
        render_mode=ui_components.ReviewRenderMode.FULL,
        step_status={
            "answered": 1,
            "total": 1,
            "completion_state": "complete",
            "essentials_answered": 1,
            "essentials_total": 1,
            "missing_essentials": [],
            "missing_essential_ids": [],
        },
        job_extract=JobAdExtract(company_name="Rheinbahn"),
    )

    assert any(
        "Wie heißt das Unternehmen?: Manuell GmbH" in caption
        for caption in fake_st.captions
    )
    assert not any("Rheinbahn" in caption for caption in fake_st.captions)


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
        render_mode=ui_components.ReviewRenderMode.FULL,
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


def test_render_step_review_card_mode_compact_hides_direct_answer_block(
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
        render_mode=ui_components.ReviewRenderMode.COMPACT,
        step_status=None,
    )

    assert ("Gruppenstatus", False) not in fake_st.expanders
    assert not any(
        "Offene Fragen direkt beantworten" in markdown for markdown in fake_st.markdowns
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
        render_mode=ui_components.ReviewRenderMode.COMPACT,
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
        lambda _questions, _answers, **_kwargs: [],
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
    assert not any(
        "aktuellen Umfang zurückgestellt" in caption
        for caption in fake_st.captions
    )
    assert not any(
        "vorausgesetzten Antworten" in caption for caption in fake_st.captions
    )


def test_render_question_step_shows_adaptive_hidden_scope_caption(monkeypatch) -> None:
    class _FakeStepStreamlit:
        def __init__(self) -> None:
            self.session_state: dict[str, Any] = {
                SSKey.UI_MODE.value: "standard",
                SSKey.QUESTION_LIMITS.value: {"company": 1},
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
        lambda _questions, _answers, **_kwargs: [],
    )
    step = QuestionStep(
        step_key="company",
        title_de="Company",
        questions=[
            Question(
                id="company_q_core",
                label="Hiring goal",
                answer_type=AnswerType.SHORT_TEXT,
                required=True,
                priority="core",
                group_key="company",
            ),
            Question(
                id="company_q_detail",
                label="Detail",
                answer_type=AnswerType.SHORT_TEXT,
                priority="detail",
                group_key="company",
            ),
        ],
    )

    ui_components.render_question_step(step)

    assert any(
        "1 Detailfrage ist im aktuellen Umfang zurückgestellt" in caption
        for caption in fake_st.captions
    )


def test_render_question_step_hides_group_provenance_counts_and_sensitive_details(
    monkeypatch,
) -> None:
    class _FakeStepStreamlit:
        def __init__(self) -> None:
            self.session_state: dict[str, Any] = {
                SSKey.UI_MODE.value: "standard",
                SSKey.QUESTION_LIMITS.value: {},
                SSKey.UI_PREFERENCES.value: {
                    UI_PREFERENCE_CONFIDENCE_THRESHOLD: 0.6,
                },
                SSKey.INTAKE_FACTS.value: {
                    FactKey.COMPANY_COMPANY_NAME.value: "Rheinbahn",
                    FactKey.ROLE_TECH_STACK.value: ["Python"],
                },
                SSKey.INTAKE_FACT_EVIDENCE.value: {
                    FactKey.COMPANY_COMPANY_NAME.value: {
                        "confidence": 0.9,
                        "evidence_snippet": "Company name from upload",
                    },
                    FactKey.ROLE_TECH_STACK.value: {
                        "confidence": 0.4,
                        "evidence_snippet": "Do not leak this evidence snippet",
                    },
                },
                SSKey.QUESTION_FLOW_PROVENANCE.value: {
                    "injected_question_ids": ["ctx_esco_skill"],
                    "source_uris_by_question_id": {
                        "ctx_esco_skill": ["uri:skill:python"]
                    },
                },
                SSKey.JOB_EXTRACT.value: JobAdExtract(
                    company_name="Rheinbahn"
                ).model_dump(mode="json"),
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
        lambda _questions, _answers, **_kwargs: [],
    )
    step = QuestionStep(
        step_key="company",
        title_de="Company",
        questions=[
            Question(
                id="company_name",
                label="Unternehmen",
                answer_type=AnswerType.SHORT_TEXT,
                group_key="origin",
                target_path=FactKey.COMPANY_COMPANY_NAME.value,
            ),
            Question(
                id="ctx_esco_skill",
                label="ESCO Skill",
                answer_type=AnswerType.SHORT_TEXT,
                group_key="origin",
            ),
            Question(
                id="role_tech_stack",
                label="Tech Stack",
                answer_type=AnswerType.SHORT_TEXT,
                group_key="origin",
                target_path=FactKey.ROLE_TECH_STACK.value,
            ),
            Question(
                id="open_goal",
                label="Offenes Ziel",
                answer_type=AnswerType.SHORT_TEXT,
                group_key="origin",
            ),
        ],
    )

    ui_components.render_question_step(step)

    joined_captions = " ".join(fake_st.captions)
    assert any(
        caption.startswith("Herkunft:")
        and "Warum:" in caption
        and "Für:" in caption
        for caption in fake_st.captions
    )
    assert "ESCO" in joined_captions
    assert "Offen" in joined_captions
    assert not any(caption.startswith("Aus Start:") for caption in fake_st.captions)
    assert "uri:skill:python" not in joined_captions
    assert "Do not leak this evidence snippet" not in joined_captions


def test_render_question_step_compact_context_hides_visible_provenance(
    monkeypatch,
) -> None:
    class _FakeStepStreamlit:
        def __init__(self) -> None:
            self.session_state: dict[str, Any] = {
                SSKey.UI_MODE.value: "standard",
                SSKey.QUESTION_LIMITS.value: {},
                SSKey.QUESTION_FLOW_PROVENANCE.value: {
                    "injected_question_ids": ["ctx_interview"],
                },
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
    captured_context_modes: list[str] = []
    monkeypatch.setattr(ui_components, "st", fake_st)
    monkeypatch.setattr(ui_components, "get_answers", lambda: {})
    monkeypatch.setattr(ui_components, "get_answer_meta", lambda: {})

    def _capture_questions_two_columns(
        _questions: list[Question],
        _answers: dict[str, Any],
        **kwargs: Any,
    ) -> list[tuple[str, Any, Any]]:
        captured_context_modes.append(kwargs.get("context_mode", "default"))
        return []

    monkeypatch.setattr(
        ui_components,
        "_render_questions_two_columns",
        _capture_questions_two_columns,
    )
    step = QuestionStep(
        step_key="interview",
        title_de="Interview",
        questions=[
            Question(
                id="ctx_interview",
                label="Wer informiert Kandidat:innen?",
                answer_type=AnswerType.SHORT_TEXT,
                rationale="Defines candidate communication timing.",
                group_key="candidate_communication",
            )
        ],
    )

    ui_components.render_question_step(step, context_mode="compact")

    assert captured_context_modes == ["compact"]
    assert not any(caption.startswith("Herkunft:") for caption in fake_st.captions)
    assert not any(("Warum:" in caption or "Für:" in caption) for caption in fake_st.captions)


def test_question_provenance_display_uses_safe_labels_and_canonical_impacts() -> None:
    question = Question(
        id="ctx_esco_skill",
        label="ESCO Skill",
        answer_type=AnswerType.SHORT_TEXT,
        rationale=(
            "Confirm uri:skill:python for recruiting@example.test with token=abc123."
        ),
        impact_targets=[QUESTION_IMPACT_TARGET_SKILLS, QUESTION_IMPACT_TARGET_EXPORT],
        acquisition_cost="low",
        info_gain_score=0.74,
    )

    display = ui_components._build_question_provenance_display(
        question,
        {
            "injected_question_ids": ["ctx_esco_skill"],
            "demoted_question_ids": ["ctx_esco_skill"],
            "source_uris_by_question_id": {
                "ctx_esco_skill": ["uri:skill:python"]
            },
        },
    )
    caption = ui_components._format_question_provenance_caption(display)

    assert display["sources"] == ["ESCO context", "Occupation context"]
    assert display["impacts"] == ["Skills", "Export"]
    assert display["effort"] == "geringer Aufwand"
    assert display["info_gain"] == "74% Info-Gain"
    assert display["adjustments"] == [
        "selected by occupation overlay",
        "demoted by relevance filter",
    ]
    assert "Herkunft: ESCO, Kontext" in caption
    assert "Für: Skills, Export" in caption
    assert "uri:skill:python" not in caption
    assert "recruiting@example.test" not in caption
    assert "token=abc123" not in caption


def test_render_section_provenance_expert_adds_collapsed_details(monkeypatch) -> None:
    fake_st = _FakeStreamlitRecorder()
    monkeypatch.setattr(ui_components, "st", fake_st)
    question = Question(
        id="ctx_esco_skill",
        label="ESCO Skill",
        answer_type=AnswerType.SHORT_TEXT,
        rationale="Clarifies the skill requirement before exports.",
        impact_targets=[QUESTION_IMPACT_TARGET_SKILLS],
    )

    ui_components._render_section_provenance(
        section_title="Skill context",
        questions=[question],
        ui_mode="expert",
        provenance={
            "injected_question_ids": ["ctx_esco_skill"],
            "source_uris_by_question_id": {
                "ctx_esco_skill": ["uri:skill:python"]
            },
        },
    )

    assert any(
        caption.startswith("Herkunft:")
        and "Warum:" in caption
        and "Für:" in caption
        for caption in fake_st.captions
    )
    assert ("Provenienz", False) in fake_st.expanders
    assert "**Herkunft**: ESCO, Kontext" in fake_st.markdowns
    assert "**Verwendet für**: Skills" in fake_st.markdowns
    joined_events = " ".join(
        value for _event_type, value in fake_st.events if isinstance(value, str)
    )
    assert "uri:skill:python" not in joined_events


class _QuestionFormFakeStreamlit:
    def __init__(self, *, submitted: bool) -> None:
        self.session_state: dict[str, Any] = {
            "cs.ui_mode": "standard",
            "cs.question_limits": {},
        }
        self.submitted = submitted
        self.rerun_called = False

    def caption(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def markdown(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def info(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def success(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def container(self, *, border: bool = False) -> _NoopContext:
        del border
        return _NoopContext()

    def columns(self, spec: int | list[int], **_: Any) -> list[_NoopContext]:
        count = spec if isinstance(spec, int) else len(spec)
        return [_NoopContext() for _ in range(count)]

    def form(self, *_args: Any, **_kwargs: Any) -> _NoopContext:
        return _NoopContext()

    def form_submit_button(self, *_args: Any, **_kwargs: Any) -> bool:
        return self.submitted

    def text_input(self, *_args: Any, **_kwargs: Any) -> str:
        return "Draft answer"

    def rerun(self) -> None:
        self.rerun_called = True


def test_render_question_step_form_waits_for_submit_before_persisting(
    monkeypatch,
) -> None:
    fake_st = _QuestionFormFakeStreamlit(submitted=False)
    persisted_answers: list[tuple[str, Any]] = []
    touched_answers: list[tuple[str, Any, Any]] = []
    monkeypatch.setattr(ui_components, "st", fake_st)
    monkeypatch.setattr(ui_components, "get_answers", lambda: {})
    monkeypatch.setattr(ui_components, "get_answer_meta", lambda: {})
    monkeypatch.setattr(
        ui_components,
        "set_answer",
        lambda question_id, value: persisted_answers.append((question_id, value)),
    )
    monkeypatch.setattr(
        ui_components,
        "mark_answer_touched",
        lambda question_id, previous, current: touched_answers.append(
            (question_id, previous, current)
        ),
    )
    step = QuestionStep(
        step_key="company",
        title_de="Company",
        questions=[
            Question(
                id="company_context",
                label="Company context",
                answer_type=AnswerType.SHORT_TEXT,
                group_key="company",
            )
        ],
    )

    ui_components.render_question_step(step)

    assert persisted_answers == []
    assert touched_answers == []
    assert fake_st.rerun_called is False


def test_render_question_step_form_persists_answers_on_submit(monkeypatch) -> None:
    fake_st = _QuestionFormFakeStreamlit(submitted=True)
    persisted_answers: list[tuple[str, Any]] = []
    touched_answers: list[tuple[str, Any, Any]] = []
    monkeypatch.setattr(ui_components, "st", fake_st)
    monkeypatch.setattr(ui_components, "get_answers", lambda: {})
    monkeypatch.setattr(ui_components, "get_answer_meta", lambda: {})
    monkeypatch.setattr(
        ui_components,
        "set_answer",
        lambda question_id, value: persisted_answers.append((question_id, value)),
    )
    monkeypatch.setattr(
        ui_components,
        "mark_answer_touched",
        lambda question_id, previous, current: touched_answers.append(
            (question_id, previous, current)
        ),
    )
    step = QuestionStep(
        step_key="company",
        title_de="Company",
        questions=[
            Question(
                id="company_context",
                label="Company context",
                answer_type=AnswerType.SHORT_TEXT,
                group_key="company",
            )
        ],
    )

    ui_components.render_question_step(step)

    assert persisted_answers == [("company_context", "Draft answer")]
    assert touched_answers == [("company_context", None, "Draft answer")]
    assert fake_st.rerun_called is True


def test_question_step_form_is_disabled_for_language_widgets(monkeypatch) -> None:
    fake_st = SimpleNamespace(
        form=lambda *_args, **_kwargs: _NoopContext(),
        form_submit_button=lambda *_args, **_kwargs: False,
    )
    monkeypatch.setattr(ui_components, "st", fake_st)

    normal_question = Question(
        id="company_context",
        label="Company context",
        answer_type=AnswerType.SHORT_TEXT,
    )
    language_question = Question(
        id="language_requirements",
        label="Welche Sprachen sind erforderlich?",
        answer_type=AnswerType.MULTI_SELECT,
    )

    assert ui_components._can_render_question_step_form([normal_question]) is True
    assert ui_components._can_render_question_step_form([language_question]) is False


def test_render_step_review_card_direct_answers_mode_shows_hint_when_inline_disabled(
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
        render_mode=ui_components.ReviewRenderMode.DIRECT_ANSWERS,
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
        render_mode=ui_components.ReviewRenderMode.DIRECT_ANSWERS,
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


def test_render_step_review_card_full_mode_shows_group_level_open_question_counts(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlitRecorder()
    monkeypatch.setattr(ui_components, "st", fake_st)
    monkeypatch.setattr(ui_components, "_can_render_inline_answer_inputs", lambda: False)

    question = _question(question_id="q1", label="Offen", group_key="group_open")
    step = _step_with_questions([question])
    ui_components.render_step_review_card(
        step=step,
        visible_questions=[question],
        answers={},
        answer_meta={},
        answered_lookup={"q1": False},
        render_mode=ui_components.ReviewRenderMode.FULL,
        step_status=None,
    )

    assert ("Gruppenstatus", False) in fake_st.expanders
    assert "1 offene Frage(n) in dieser Gruppe." in fake_st.captions


def test_render_compare_adopt_intro_renders_no_explanatory_copy(monkeypatch) -> None:
    calls: list[str] = []
    captions: list[str] = []

    class _FakeStreamlit:
        def __init__(self) -> None:
            self.session_state: dict[str, Any] = {}

        def markdown(self, *_: Any, **__: Any) -> None:
            raise AssertionError("markdown fallback should not be used when html exists")

        def caption(self, text: str, *_: Any, **__: Any) -> None:
            captions.append(text)

        def expander(self, *_: Any, **__: Any) -> _NoopContext:
            return _NoopContext()

        def html(self, html: str) -> None:
            calls.append(html)

    monkeypatch.setattr(ui_components, "st", _FakeStreamlit())

    ui_components.render_compare_adopt_intro(
        adopt_target="Skills",
        canonical_target="SSKey.SKILLS_SELECTED",
        source_labels=("Jobspec", "ESCO", "AI"),
        render_explanatory_copy=False,
    )

    assert calls == []
    assert captions == []


def test_interview_value_board_includes_compact_provenance_column(monkeypatch) -> None:
    class _FakeInterviewStreamlit:
        def __init__(self) -> None:
            self.session_state: dict[str, Any] = {
                SSKey.INTERVIEW_INTERNAL_FLOW.value: {"selected_value_ids": []}
            }
            self.column_config = SimpleNamespace(TextColumn=lambda *args, **kwargs: None)
            self.dataframe_rows: list[dict[str, str]] = []
            self.column_order: list[str] = []

        def info(self, *_args: Any, **_kwargs: Any) -> None:
            return None

        def dataframe(
            self,
            rows: list[dict[str, str]],
            *,
            column_order: list[str],
            **_: Any,
        ) -> None:
            self.dataframe_rows = rows
            self.column_order = column_order

        def multiselect(
            self,
            *_args: Any,
            default: list[str],
            **_kwargs: Any,
        ) -> list[str]:
            return default

    fake_st = _FakeInterviewStreamlit()
    monkeypatch.setattr(INTERVIEW_MODULE, "st", fake_st)
    monkeypatch.setattr(INTERVIEW_MODULE, "get_answers", lambda: {})
    monkeypatch.setattr(
        INTERVIEW_MODULE,
        "build_interview_value_rows",
        lambda **_kwargs: [
            {
                "id": "jobspec-stage",
                "Bereich": "Interview",
                "Feld": "Interviewphase 1",
                "Wert": "HR Screen",
                "Quelle": "Jobspec",
                "Status": "Vollständig",
            },
            {
                "id": "manual-stage",
                "Bereich": "Timing",
                "Feld": "Start",
                "Wert": "2026-07-01",
                "Quelle": "Interview-Step",
                "Status": "Vollständig",
            },
        ],
    )
    monkeypatch.setattr(
        INTERVIEW_MODULE,
        "default_selected_interview_value_ids",
        lambda rows: [row["id"] for row in rows],
    )

    INTERVIEW_MODULE._render_interview_value_board(job=JobAdExtract(), plan=None)

    assert "Provenienz" in fake_st.column_order
    assert fake_st.dataframe_rows[0]["Provenienz"] == "Jobspec"
    assert fake_st.dataframe_rows[1]["Provenienz"] == "Eingabe"
