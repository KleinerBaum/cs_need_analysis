from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path

import ui_components

JOBSPEC_PATH = (
    Path(__file__).resolve().parents[1] / "wizard_pages" / "01a_jobspec_review.py"
)
SPEC = spec_from_file_location("wizard_pages.page_01a_jobspec_review", JOBSPEC_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load jobspec review module")
JOBSPEC_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(JOBSPEC_MODULE)  # type: ignore[attr-defined]


def test_infer_applied_provenance_categories_marks_manual_override_and_synonyms() -> (
    None
):
    categories = ui_components._infer_applied_provenance_categories(
        query_text="Data Engineer",
        selected_payload=[
            {
                "uri": "uri:2",
                "title": "Dateningenieur",
                "type": "occupation",
                "source": "manual",
            }
        ],
        selected_index=2,
        allow_multi=False,
    )

    assert "manually selected by user" in categories
    assert "synonym/hidden-term match" in categories


def test_infer_esco_match_explainability_detects_manual_override() -> None:
    explainability = JOBSPEC_MODULE._infer_esco_match_explainability(
        query_text="Data Engineer (Analytics)",
        selected={"uri": "uri:selected", "title": "Machine Learning Engineer"},
        options=[
            {"uri": "uri:top", "title": "Data Engineer"},
            {"uri": "uri:selected", "title": "Machine Learning Engineer"},
        ],
        applied_meta={"source": "auto"},
    )

    assert explainability["badge_label"] == "Manually Selected by User"
    assert explainability["confidence"] == "high"
    assert "manually selected by user" in explainability["provenance_categories"]


def test_infer_esco_match_explainability_prefers_jobspec_title_match() -> None:
    explainability = JOBSPEC_MODULE._infer_esco_match_explainability(
        query_text="Data Engineer (Berlin)",
        selected={"uri": "uri:selected", "title": "Senior Data Engineer"},
        options=[{"uri": "uri:selected", "title": "Senior Data Engineer"}],
        applied_meta={"source": "auto", "provenance_categories": []},
    )

    assert explainability["badge_label"] == "Exact Label Match"
    assert explainability["confidence"] == "high"
    assert "exact label match" in explainability["provenance_categories"]


def test_render_esco_explainability_renders_collapsed_technical_details(monkeypatch) -> None:
    class _DummyContext:
        def __enter__(self) -> "_DummyContext":
            return self

        def __exit__(self, *_: object) -> bool:
            return False

    class _FakeStreamlit:
        def __init__(self) -> None:
            self.caption_messages: list[str] = []
            self.expander_calls: list[tuple[str, bool | None]] = []
            self.markdown_calls: list[str] = []

        def caption(self, message: str) -> None:
            self.caption_messages.append(message)

        def expander(self, label: str, **kwargs: object) -> _DummyContext:
            self.expander_calls.append((label, kwargs.get("expanded")))
            return _DummyContext()

        def markdown(self, message: str, **_kwargs: object) -> None:
            self.markdown_calls.append(message)

    fake_st = _FakeStreamlit()
    monkeypatch.setattr(ui_components, "st", fake_st)

    ui_components.render_esco_explainability(
        labels=["exact label match", "manually selected by user"],
        confidence="high",
        reason="Top-ranked ESCO occupation aligns with query title.",
        caption_prefix="Occupation Explainability",
    )

    assert "Confidence: High" in fake_st.caption_messages
    assert (
        "Occupation Explainability: Top-ranked ESCO occupation aligns with query title."
        in fake_st.caption_messages
    )
    assert fake_st.expander_calls == [("Technische Details", False)]
    assert any("Exact Label Match" in message for message in fake_st.markdown_calls)
