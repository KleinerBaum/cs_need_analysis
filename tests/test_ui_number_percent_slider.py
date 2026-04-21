from __future__ import annotations

from typing import Any

import ui_components
from schemas import AnswerType, Question


class _FakeStreamlit:
    def __init__(self) -> None:
        self.slider_calls: list[dict[str, Any]] = []
        self.number_input_calls: list[dict[str, Any]] = []

    def slider(self, label: str, **kwargs: Any) -> int:
        self.slider_calls.append({"label": label, **kwargs})
        return int(kwargs["value"])

    def number_input(self, label: str, **kwargs: Any) -> int:
        self.number_input_calls.append({"label": label, **kwargs})
        return int(kwargs["value"])


def test_render_number_question_uses_percent_slider_bounds(monkeypatch) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(ui_components, "st", fake_st)
    question = Question(
        id="team_role_distribution_percent",
        label="Wie stark ist der Anteil ... in typischen Einsätzen?",
        help="Bitte grobe Aufteilung in Prozent pro Woche/Monat.",
        answer_type=AnswerType.NUMBER,
        min_value=0,
        max_value=300,
        step_value=1,
    )

    value, validation_error = ui_components._render_number_question(
        question=question,
        key="q_team_role_distribution_percent",
        label=question.label,
        help_text=question.help,
        current_value=250,
    )

    assert value == 100
    assert validation_error is not None
    assert len(fake_st.slider_calls) == 1
    assert fake_st.number_input_calls == []
    assert fake_st.slider_calls[0]["min_value"] == 0
    assert fake_st.slider_calls[0]["max_value"] == 100
    assert fake_st.slider_calls[0]["step"] == 5
    assert fake_st.slider_calls[0]["value"] == 100


def test_is_percentage_number_question_detects_percentage_hints() -> None:
    question = Question(
        id="q_remote_share",
        label="Remote Share",
        help="Anteil in % angeben.",
        answer_type=AnswerType.NUMBER,
    )
    assert ui_components._is_percentage_number_question(question) is True
