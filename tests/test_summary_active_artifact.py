from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any, Literal

from constants import SSKey


SUMMARY_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "08_summary.py"
SPEC = spec_from_file_location("wizard_pages.page_08_summary_active", SUMMARY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load summary page module")
SUMMARY_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(SUMMARY_MODULE)  # type: ignore[attr-defined]


class _NoopContext:
    def __enter__(self) -> "_NoopContext":
        return self

    def __exit__(self, *_: object) -> Literal[False]:
        return False


class _FakeStreamlit:
    def __init__(self, session_state: dict[str, Any], button_results: list[bool]):
        self.session_state = session_state
        self._button_results = button_results
        self.rerun_called = False
        self.button_labels: list[str] = []
        self.subheader_calls: list[str] = []
        self.text_area_calls: list[dict[str, Any]] = []
        self.download_button_labels: list[str] = []
        self.markdown_calls: list[str] = []

    def container(self, **_: Any) -> _NoopContext:
        return _NoopContext()

    def markdown(self, body: Any, **__: Any) -> None:
        self.markdown_calls.append(str(body))
        return None

    def subheader(self, body: str, **__: Any) -> None:
        self.subheader_calls.append(body)
        return None

    def caption(self, *_: Any, **__: Any) -> None:
        return None

    def write(self, *_: Any, **__: Any) -> None:
        return None

    def info(self, *_: Any, **__: Any) -> None:
        return None

    def button(self, label: str, **__: Any) -> bool:
        self.button_labels.append(label)
        return self._button_results.pop(0) if self._button_results else False

    def columns(self, count: int) -> list[_NoopContext]:
        return [_NoopContext() for _ in range(count)]

    def download_button(self, *_: Any, **__: Any) -> None:
        if _:
            self.download_button_labels.append(str(_[0]))
        return None

    def text_area(self, label: str, **kwargs: Any) -> str:
        self.text_area_calls.append({"label": label, **kwargs})
        return str(kwargs.get("value", ""))

    def rerun(self) -> None:
        self.rerun_called = True


def _build_action(action_id: str, result_key: SSKey) -> dict[str, Any]:
    return {
        "id": action_id,
        "title": "Action",
        "benefit": "desc",
        "cta_label": "Run",
        "blocked_cta_label": None,
        "requires": (SSKey.JOB_EXTRACT,),
        "requirement_text": "Jobspec vorhanden",
        "requirement_check_fn": None,
        "generator_fn": lambda: None,
        "result_key": result_key,
        "input_hints": (),
        "input_renderer": None,
    }


def test_button_action_sets_canonical_active_artifact_id(monkeypatch) -> None:
    fake_st = _FakeStreamlit(
        session_state={SSKey.JOB_EXTRACT.value: {"job_title": "Engineer"}},
        button_results=[True],
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    triggered = SUMMARY_MODULE._render_action_card(
        _build_action("job_ad", SSKey.JOB_AD_DRAFT_CUSTOM)
    )

    assert triggered is True
    assert fake_st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] == "job_ad"


def test_resolve_active_artifact_falls_back_from_legacy_value(monkeypatch) -> None:
    fake_st = _FakeStreamlit(
        session_state={SSKey.SUMMARY_ACTIVE_ARTIFACT.value: "job_ad_generator"},
        button_results=[],
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    active_id = SUMMARY_MODULE._resolve_active_artifact_id(
        available_artifact_ids=["brief", "job_ad"]
    )

    assert active_id == "job_ad"
    assert fake_st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] == "job_ad"


def test_resolve_active_artifact_normalizes_case_and_whitespace(monkeypatch) -> None:
    fake_st = _FakeStreamlit(
        session_state={SSKey.SUMMARY_ACTIVE_ARTIFACT.value: " JOB_AD_GENERATOR "},
        button_results=[],
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    active_id = SUMMARY_MODULE._resolve_active_artifact_id(
        available_artifact_ids=["brief", "job_ad"]
    )

    assert active_id == "job_ad"
    assert fake_st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] == "job_ad"


def test_resolve_active_artifact_falls_back_when_selected_artifact_is_missing(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlit(
        session_state={SSKey.SUMMARY_ACTIVE_ARTIFACT.value: "employment_contract"},
        button_results=[],
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    active_id = SUMMARY_MODULE._resolve_active_artifact_id(
        available_artifact_ids=["brief", "job_ad"]
    )

    assert active_id == "brief"
    assert fake_st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] == "brief"


def test_active_artifact_renderer_uses_expected_payload(monkeypatch) -> None:
    calls: dict[str, Any] = {}

    def _capture(payload: Any) -> None:
        calls["payload"] = payload

    fake_st = _FakeStreamlit(
        session_state={
            SSKey.BOOLEAN_SEARCH_STRING.value: {
                "channel_queries": [{"channel": "linkedin", "query": "x"}]
            }
        },
        button_results=[],
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)
    monkeypatch.setattr(SUMMARY_MODULE, "render_boolean_search_pack", _capture)
    monkeypatch.setattr(
        SUMMARY_MODULE, "_boolean_search_pack_to_markdown", lambda _pack: "x"
    )
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "BooleanSearchPack",
        type(
            "_FakePack",
            (),
            {
                "model_validate": staticmethod(
                    lambda value: type(
                        "_Payload",
                        (),
                        {"model_dump": lambda self, mode="json": value},
                    )()
                )
            },
        ),
    )

    SUMMARY_MODULE._render_active_artifact(
        artifact_id="boolean_search",
        brief=None,  # type: ignore[arg-type]
    )

    dumped = calls["payload"].model_dump(mode="json")
    assert dumped["channel_queries"][0]["channel"] == "linkedin"


def test_secondary_artifact_switching_updates_active_artifact(monkeypatch) -> None:
    fake_st = _FakeStreamlit(
        session_state={SSKey.SUMMARY_ACTIVE_ARTIFACT.value: "brief"},
        button_results=[True],
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    SUMMARY_MODULE._render_secondary_artifacts(
        active_artifact_id="brief",
        available_artifact_ids=["brief", "job_ad"],
    )

    assert fake_st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] == "job_ad"
    assert fake_st.rerun_called is True


def test_render_active_artifact_job_ad_calls_helper(monkeypatch) -> None:
    helper_calls: list[dict[str, Any]] = []

    def _capture(payload: dict[str, Any]) -> None:
        helper_calls.append(payload)

    fake_st = _FakeStreamlit(
        session_state={
            SSKey.JOB_AD_DRAFT_CUSTOM.value: {
                "headline": "Senior Engineer",
                "job_ad_text": "Hallo Welt",
            }
        },
        button_results=[],
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)
    monkeypatch.setattr(SUMMARY_MODULE, "_render_job_ad_artifact", _capture)

    SUMMARY_MODULE._render_active_artifact(
        artifact_id="job_ad",
        brief=None,  # type: ignore[arg-type]
    )

    assert helper_calls == [
        {
            "headline": "Senior Engineer",
            "job_ad_text": "Hallo Welt",
        }
    ]


def test_render_job_ad_artifact_renders_cards_in_expected_order(monkeypatch) -> None:
    fake_st = _FakeStreamlit(session_state={}, button_results=[])
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)
    monkeypatch.setattr(SUMMARY_MODULE, "render_output_header", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(SUMMARY_MODULE, "_job_ad_to_docx_bytes", lambda *_args, **_kwargs: b"docx")
    monkeypatch.setattr(SUMMARY_MODULE, "_job_ad_to_pdf_bytes", lambda *_args, **_kwargs: b"pdf")
    monkeypatch.setattr(SUMMARY_MODULE, "_estimate_text_area_height", lambda _text: 120)

    card_markers: list[str] = []

    def _capture_card_start(css_class: str) -> None:
        card_markers.append(f"start:{css_class}")

    monkeypatch.setattr(SUMMARY_MODULE, "render_card_start", _capture_card_start)

    SUMMARY_MODULE._render_job_ad_artifact(
        {
            "headline": "Senior Engineer",
            "target_group": ["A"],
            "agg_checklist": ["OK"],
            "job_ad_text": "Line 1\nLine 2",
        }
    )

    section_markers = [
        marker
        for marker in fake_st.markdown_calls
        if marker in {"### Primary Output", "### Review", "### Export"}
    ]
    assert card_markers == [
        "start:cs-card cs-result-card",
        "start:cs-card cs-result-card",
        "start:cs-card cs-result-card",
    ]
    assert section_markers == ["### Primary Output", "### Review", "### Export"]


def test_render_job_ad_artifact_has_markdown_download_button(monkeypatch) -> None:
    fake_st = _FakeStreamlit(session_state={}, button_results=[])
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)
    monkeypatch.setattr(SUMMARY_MODULE, "render_output_header", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(SUMMARY_MODULE, "_job_ad_to_docx_bytes", lambda *_args, **_kwargs: b"docx")
    monkeypatch.setattr(SUMMARY_MODULE, "_job_ad_to_pdf_bytes", lambda *_args, **_kwargs: b"pdf")

    SUMMARY_MODULE._render_job_ad_artifact(
        {"headline": "Senior Engineer", "job_ad_text": "Text"}
    )

    assert "Download Stellenanzeige (Markdown)" in fake_st.download_button_labels


def test_artifact_display_label_maps_expected_labels_and_fallbacks() -> None:
    assert SUMMARY_MODULE._artifact_display_label("job_ad") == "Stellenanzeige"
    assert SUMMARY_MODULE._artifact_display_label("interview_hr") == "HR-Sheet"
    assert SUMMARY_MODULE._artifact_display_label("interview_fach") == "Fachbereich-Sheet"
    assert SUMMARY_MODULE._artifact_display_label("boolean_search") == "Boolean Search"
    assert SUMMARY_MODULE._artifact_display_label("employment_contract") == "Arbeitsvertrag"
    assert SUMMARY_MODULE._artifact_display_label("brief") == "Recruiting Brief"
    assert SUMMARY_MODULE._artifact_display_label("custom_artifact") == "custom_artifact"
    assert SUMMARY_MODULE._artifact_display_label("  custom_artifact  ") == "custom_artifact"
    assert SUMMARY_MODULE._artifact_display_label("") == ""
    assert SUMMARY_MODULE._artifact_display_label(123) == ""


def test_render_secondary_artifacts_uses_human_label_but_sets_canonical_id(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlit(
        session_state={SSKey.SUMMARY_ACTIVE_ARTIFACT.value: "brief"},
        button_results=[True],
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    SUMMARY_MODULE._render_secondary_artifacts(
        active_artifact_id="brief",
        available_artifact_ids=["brief", "job_ad"],
    )

    assert fake_st.button_labels == ["Als Fokus öffnen: Stellenanzeige"]
    assert fake_st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] == "job_ad"
