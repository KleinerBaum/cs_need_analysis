from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any, Literal

from constants import SSKey


SUMMARY_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "08_summary.py"
SPEC = spec_from_file_location("wizard_pages.page_08_summary_job_ad_panel", SUMMARY_PATH)
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
    def __init__(
        self,
        session_state: dict[str, Any],
        *,
        button_results: dict[str, bool] | None = None,
        toggle_value: bool | None = None,
    ):
        self.session_state = session_state
        self.button_results = button_results or {}
        self.toggle_value = toggle_value

    def container(self, **_: Any) -> _NoopContext:
        return _NoopContext()

    def markdown(self, *_: Any, **__: Any) -> None:
        return None

    def caption(self, *_: Any, **__: Any) -> None:
        return None

    def write(self, *_: Any, **__: Any) -> None:
        return None

    def button(self, _: str, **kwargs: Any) -> bool:
        key = str(kwargs.get("key", ""))
        return self.button_results.get(key, False)

    def toggle(self, _: str, **kwargs: Any) -> bool:
        key = kwargs.get("key")
        if isinstance(key, str):
            if self.toggle_value is not None:
                self.session_state[key] = self.toggle_value
            return bool(self.session_state.get(key, False))
        return False


class _UploadedLogo:
    def __init__(self, *, name: str, mime_type: str, payload: bytes):
        self.name = name
        self.type = mime_type
        self._payload = payload

    def getvalue(self) -> bytes:
        return self._payload


def _job_ad_action_with_inputs(renderer) -> dict[str, Any]:
    return {
        "id": "job_ad",
        "title": "Job Ad",
        "benefit": "desc",
        "cta_label": "Generate",
        "blocked_cta_label": None,
        "requires": (SSKey.JOB_EXTRACT,),
        "requirement_text": "Jobspec vorhanden",
        "requirement_check_fn": None,
        "generator_fn": lambda: None,
        "result_key": SSKey.JOB_AD_DRAFT_CUSTOM,
        "input_hints": (),
        "input_renderer": renderer,
    }


def test_job_ad_card_open_config_button_sets_panel_state(monkeypatch) -> None:
    open_key = (
        f"{SSKey.SUMMARY_ACTION_WIDGET_PREFIX.value}.job_ad.open_config"
    )
    fake_st = _FakeStreamlit(
        session_state={SSKey.JOB_EXTRACT.value: {"job_title": "Engineer"}},
        button_results={open_key: True},
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    action = _job_ad_action_with_inputs(lambda: None)

    SUMMARY_MODULE._render_action_card(action)

    assert fake_st.session_state[SSKey.SUMMARY_SHOW_JOB_AD_CONFIG.value] is True


def test_job_ad_configuration_panel_calls_renderer_when_open(monkeypatch) -> None:
    calls = {"count": 0}

    def _renderer() -> None:
        calls["count"] += 1

    fake_st = _FakeStreamlit(
        session_state={SSKey.SUMMARY_SHOW_JOB_AD_CONFIG.value: True},
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    SUMMARY_MODULE._render_job_ad_configuration_panel(
        action_registry=[_job_ad_action_with_inputs(_renderer)]
    )

    assert calls["count"] == 1


def test_job_ad_configuration_panel_preserves_existing_inputs(monkeypatch) -> None:
    fake_st = _FakeStreamlit(
        session_state={
            SSKey.SUMMARY_SHOW_JOB_AD_CONFIG.value: False,
            SSKey.SUMMARY_SELECTIONS.value: {"seniority": "senior"},
            SSKey.SUMMARY_STYLEGUIDE_TEXT.value: "Be concise",
            SSKey.SUMMARY_CHANGE_REQUEST_TEXT.value: "Shorten CTA",
        },
        toggle_value=False,
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    SUMMARY_MODULE._render_job_ad_configuration_panel(
        action_registry=[_job_ad_action_with_inputs(lambda: None)]
    )

    assert fake_st.session_state[SSKey.SUMMARY_SELECTIONS.value] == {
        "seniority": "senior"
    }
    assert fake_st.session_state[SSKey.SUMMARY_STYLEGUIDE_TEXT.value] == "Be concise"
    assert (
        fake_st.session_state[SSKey.SUMMARY_CHANGE_REQUEST_TEXT.value] == "Shorten CTA"
    )


def test_normalize_logo_payload_supports_png_and_jpeg_only() -> None:
    png_logo = _UploadedLogo(name="brand.png", mime_type="image/png", payload=b"png")
    jpg_logo = _UploadedLogo(
        name="brand.jpg", mime_type="image/jpeg", payload=b"jpeg"
    )
    svg_logo = _UploadedLogo(name="brand.svg", mime_type="image/svg+xml", payload=b"svg")

    normalized_png = SUMMARY_MODULE._normalize_logo_payload(png_logo)
    normalized_jpg = SUMMARY_MODULE._normalize_logo_payload(jpg_logo)
    normalized_svg = SUMMARY_MODULE._normalize_logo_payload(svg_logo)

    assert normalized_png == {
        "name": "brand.png",
        "mime_type": "image/png",
        "bytes": b"png",
    }
    assert normalized_jpg == {
        "name": "brand.jpg",
        "mime_type": "image/jpeg",
        "bytes": b"jpeg",
    }
    assert normalized_svg is None
