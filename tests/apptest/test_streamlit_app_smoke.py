from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pytest
from streamlit.testing.v1 import AppTest

from constants import (
    OPERATIONAL_WIZARD_STEP_KEYS,
    SSKey,
    STEP_KEY_LANDING,
    STEP_KEY_SUMMARY,
    WIZARD_STEP_QUERY_PARAM,
)
from tests.synthetic_smoke_state import (
    SYNTHETIC_JOB_TITLE,
    seed_summary_artifact_smoke_state,
)


pytestmark = pytest.mark.apptest

ROOT = Path(__file__).resolve().parents[2]
APP_PATH = ROOT / "app.py"


def _run_app(*, query_params: dict[str, str] | None = None) -> AppTest:
    app_test = AppTest.from_file(str(APP_PATH), default_timeout=45)
    for key, value in (query_params or {}).items():
        app_test.query_params[key] = value
    app_test.run(timeout=45)
    return app_test


def _element_strings(app_test: AppTest) -> Iterable[str]:
    element_groups = (
        app_test.title,
        app_test.header,
        app_test.subheader,
        app_test.markdown,
        app_test.caption,
        app_test.text,
        app_test.button,
        app_test.radio,
        app_test.text_area,
        app_test.warning,
    )
    for group in element_groups:
        for element in group:
            for attr in ("value", "label"):
                value = getattr(element, attr, "")
                if value:
                    yield str(value)
    for element in app_test.main:
        if getattr(element, "type", None) != "html":
            continue
        proto = getattr(element, "proto", None)
        body = str(getattr(proto, "body", "") or "")
        if body:
            yield body


def _assert_no_streamlit_exceptions(app_test: AppTest) -> None:
    assert not app_test.exception


def _rendered_text(app_test: AppTest) -> str:
    return "\n".join(_element_strings(app_test))


def _process_progress_html(app_test: AppTest) -> str:
    for element in app_test.main:
        if getattr(element, "type", None) != "html":
            continue
        proto = getattr(element, "proto", None)
        body = str(getattr(proto, "body", "") or "")
        if "cs-process-progress" in body:
            return body
    return ""


def _button_by_label(app_test: AppTest, label: str):
    for button in app_test.button:
        if getattr(button, "label", None) == label:
            return button
    raise AssertionError(f"Button not found: {label}")


def _radio_by_label(app_test: AppTest, label: str):
    for radio in reversed(app_test.radio):
        if getattr(radio, "label", None) == label:
            return radio
    raise AssertionError(f"Radio not found: {label}")


def test_intro_smoke_renders_start_cta() -> None:
    app_test = _run_app()

    _assert_no_streamlit_exceptions(app_test)
    rendered_text = _rendered_text(app_test)
    assert "Erst klären. Dann suchen." in rendered_text
    assert "Briefing-Cockpit öffnen" in rendered_text


def test_landing_query_param_smoke_renders_jobspec_intake() -> None:
    app_test = _run_app(query_params={WIZARD_STEP_QUERY_PARAM: STEP_KEY_LANDING})

    _assert_no_streamlit_exceptions(app_test)
    assert app_test.session_state[SSKey.CURRENT_STEP.value] == STEP_KEY_LANDING
    rendered_text = _rendered_text(app_test)
    assert "Jobspec oder Rohtext für das Briefing einfügen" in rendered_text
    assert "landing-process-step" not in rendered_text
    assert "cs-document-preview-wrap" not in rendered_text


def test_recruiter_audience_mode_is_default_on_landing() -> None:
    app_test = _run_app(query_params={WIZARD_STEP_QUERY_PARAM: STEP_KEY_LANDING})

    _assert_no_streamlit_exceptions(app_test)
    assert app_test.session_state[SSKey.AUDIENCE_MODE.value] == "recruiter"
    rendered_text = _rendered_text(app_test)
    assert "Ansichtsmodus" not in rendered_text
    assert "Kandidatenansicht: erklärt Erwartungen transparent" not in rendered_text


def test_candidate_audience_mode_is_not_selectable_on_landing() -> None:
    app_test = _run_app(query_params={WIZARD_STEP_QUERY_PARAM: STEP_KEY_LANDING})
    _assert_no_streamlit_exceptions(app_test)

    assert app_test.session_state[SSKey.AUDIENCE_MODE.value] == "recruiter"
    rendered_text = _rendered_text(app_test)
    assert "Ansichtsmodus" not in rendered_text
    assert "Kandidat:in" not in rendered_text


def test_operational_wizard_path_reaches_seeded_summary_via_sidebar() -> None:
    app_test = _run_app()
    _assert_no_streamlit_exceptions(app_test)

    _button_by_label(app_test, "Briefing-Cockpit öffnen").click().run(timeout=45)
    _assert_no_streamlit_exceptions(app_test)
    assert app_test.session_state[SSKey.CURRENT_STEP.value] == STEP_KEY_LANDING

    rendered_text = _rendered_text(app_test)
    assert "Jobspec oder Rohtext für das Briefing einfügen" in rendered_text
    progress_html = _process_progress_html(app_test)
    assert "Fortschritt des Informationsgewinnungsprozesses" in progress_html
    for label in ("Start", "Unternehmen", "Zusammenfassung"):
        assert label in progress_html

    process_radio = _radio_by_label(app_test, "Prozess")
    assert process_radio.value == STEP_KEY_LANDING
    assert len(process_radio.options) == len(OPERATIONAL_WIZARD_STEP_KEYS)
    assert process_radio.options[0].endswith("Start")
    assert process_radio.options[-1].endswith("Zusammenfassung")

    seed_summary_artifact_smoke_state(
        app_test.session_state,
        last_mode="apptest_seed",
    )
    process_radio.set_value(STEP_KEY_SUMMARY).run(timeout=45)
    _assert_no_streamlit_exceptions(app_test)
    assert app_test.session_state[SSKey.CURRENT_STEP.value] == STEP_KEY_SUMMARY

    rendered_text = _rendered_text(app_test)
    assert "Bitte zuerst im Start-Schritt eine Analyse durchführen" not in rendered_text
    assert "Recruiting-Unterlagen" in rendered_text
    assert "Stellenanzeige" in rendered_text
    assert "Ergebnis" in rendered_text
    assert SYNTHETIC_JOB_TITLE in rendered_text
