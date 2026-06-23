from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pytest
from streamlit.testing.v1 import AppTest

from constants import SSKey, STEP_KEY_LANDING, WIZARD_STEP_QUERY_PARAM


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
    )
    for group in element_groups:
        for element in group:
            for attr in ("value", "label"):
                value = getattr(element, attr, "")
                if value:
                    yield str(value)


def _assert_no_streamlit_exceptions(app_test: AppTest) -> None:
    assert not app_test.exception


def test_intro_smoke_renders_start_cta() -> None:
    app_test = _run_app()

    _assert_no_streamlit_exceptions(app_test)
    rendered_text = "\n".join(_element_strings(app_test))
    assert "Vakanzanforderungen präzise erfassen" in rendered_text
    assert "Zum Start" in rendered_text


def test_landing_query_param_smoke_renders_jobspec_intake() -> None:
    app_test = _run_app(query_params={WIZARD_STEP_QUERY_PARAM: STEP_KEY_LANDING})

    _assert_no_streamlit_exceptions(app_test)
    assert app_test.session_state[SSKey.CURRENT_STEP.value] == STEP_KEY_LANDING
    rendered_text = "\n".join(_element_strings(app_test))
    assert "Stellenanzeige oder Jobspec" in rendered_text
    assert "landing-process-step" not in rendered_text
    assert "cs-document-preview-wrap" not in rendered_text
