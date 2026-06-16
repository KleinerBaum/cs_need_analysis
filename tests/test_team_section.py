from __future__ import annotations

from types import SimpleNamespace

from constants import AnswerType
from schemas import Question, QuestionStep
from wizard_pages import team_section


def test_build_role_context_themes_deduplicates_labels_and_groups() -> None:
    payload = {
        "description": (
            "Cross-functional team collaboration and stakeholder communication. "
            "Lead and coordinate remote digital work with clients."
        )
    }

    themes = team_section._build_role_context_themes(payload)

    labels = [str(theme.get("label") or "") for theme in themes]
    groups = [str(theme.get("group") or "") for theme in themes]
    assert len(labels) == len(set(labels))
    assert set(groups).issubset(
        {
            "Zusammenarbeit & Kommunikation",
            "Führung & Koordination",
            "Arbeitsumfeld & Rahmenbedingungen",
        }
    )


def test_append_context_to_team_notes_uses_clean_user_facing_line(monkeypatch) -> None:
    step = QuestionStep(
        step_key="team",
        title_de="Team",
        questions=[
            Question(
                id="team_notes",
                label="Team-Notiz",
                answer_type=AnswerType.LONG_TEXT,
            )
        ],
    )
    answers = {"team_notes": ""}
    captured: dict[str, str] = {}

    monkeypatch.setattr(team_section, "get_answers", lambda: answers)
    monkeypatch.setattr(
        team_section,
        "set_answer",
        lambda question_id, value: captured.update(
            {"question_id": str(question_id), "value": str(value)}
        ),
    )
    monkeypatch.setattr(team_section, "mark_answer_touched", lambda *_args: None)

    result = team_section._append_context_to_team_notes(
        step=step,
        context_line="ESCO-Hinweis: Zusammenarbeit / Kommunikation",
    )

    assert result is True
    assert captured["question_id"] == "team_notes"
    assert "Confirmed selection" not in captured["value"]
    assert "ESCO-Hinweis: Zusammenarbeit / Kommunikation" in captured["value"]


def test_role_context_ui_texts_do_not_contain_forbidden_terms() -> None:
    forbidden_terms = (
        "zone 1",
        "zone 2",
        "pillen",
        "inferred",
        "confirmed selection",
        "confidence",
        "synonym/hidden-term match",
    )
    all_ui_text = " ".join(team_section.ROLE_CONTEXT_UI_TEXTS).casefold()
    for term in forbidden_terms:
        assert term not in all_ui_text


def test_role_context_enrichment_uses_optional_adoption_callback(monkeypatch) -> None:
    adopted_lines: list[str] = []

    class _FakeStreamlit:
        session_state: dict[str, object] = {}

        def markdown(self, *_args, **_kwargs) -> None:
            return None

        def caption(self, *_args, **_kwargs) -> None:
            return None

        def pills(self, *_args, options, **_kwargs):
            return list(options)

        def button(self, *_args, **_kwargs) -> bool:
            return True

        def success(self, *_args, **_kwargs) -> None:
            return None

        def info(self, *_args, **_kwargs) -> None:
            return None

    class _FakeEscoClient:
        def resource_occupation(self, *, uri: str):
            assert uri == "uri:occupation"
            return {
                "description": (
                    "Cross-functional team collaboration and stakeholder communication."
                )
            }

    monkeypatch.setattr(team_section, "st", _FakeStreamlit())
    monkeypatch.setattr(team_section, "EscoClient", _FakeEscoClient)
    monkeypatch.setattr(
        team_section,
        "get_esco_semantic_context",
        lambda: SimpleNamespace(
            primary_anchor=SimpleNamespace(uri="uri:occupation"),
        ),
    )
    monkeypatch.setattr(
        team_section,
        "_append_context_to_team_notes",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("legacy Team answer path should not be used")
        ),
    )

    team_section.render_role_context_enrichment(
        step=None,
        ctx=SimpleNamespace(),
        adopt_context_callback=lambda line: not adopted_lines.append(line),
    )

    assert adopted_lines
    assert all(line.startswith("ESCO-Hinweis: ") for line in adopted_lines)
