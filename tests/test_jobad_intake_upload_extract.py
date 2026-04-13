from __future__ import annotations

from typing import Any

from constants import SSKey
import wizard_pages.jobad_intake as jobad_intake


class _FakeStreamlit:
    def __init__(self) -> None:
        self.session_state: dict[str, object] = {
            jobad_intake.SOURCE_UPLOAD_TEXT_KEY: "bestehender upload-text"
        }


def test_extract_upload_to_state_sets_text_input_key_when_successful(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(jobad_intake, "st", fake_st)
    monkeypatch.setattr(
        jobad_intake,
        "extract_text_from_uploaded_file",
        lambda _upload: ("Extrahierter Inhalt", {"name": "jobspec.docx", "size": 10}),
    )

    result = jobad_intake._extract_upload_to_state(
        object(),
        step="test.extract_upload_to_state.success",
        update_text_widget=False,
    )

    assert result == "Extrahierter Inhalt"
    assert (
        fake_st.session_state[jobad_intake.SOURCE_TEXT_INPUT_KEY]
        == "Extrahierter Inhalt"
    )


def test_extract_upload_to_state_does_not_overwrite_with_empty_text(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlit()
    set_error_messages: list[str] = []

    monkeypatch.setattr(jobad_intake, "st", fake_st)
    monkeypatch.setattr(
        jobad_intake,
        "extract_text_from_uploaded_file",
        lambda _upload: ("", {"name": "empty.txt", "size": 0}),
    )
    monkeypatch.setattr(
        jobad_intake, "set_error", lambda msg: set_error_messages.append(msg)
    )

    result = jobad_intake._extract_upload_to_state(
        object(), step="test.extract_upload_to_state"
    )

    assert result is None
    assert set_error_messages == ["Datei enthält keinen auslesbaren Inhalt."]
    assert (
        fake_st.session_state[jobad_intake.SOURCE_UPLOAD_TEXT_KEY]
        == "bestehender upload-text"
    )


class _DummyContext:
    def __enter__(self) -> "_DummyContext":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class _FakeStreamlitPhaseA:
    def __init__(self, session_state: dict[str, object]) -> None:
        self.session_state = session_state
        self.captions: list[str] = []
        self.errors: list[str] = []
        self.successes: list[str] = []
        self.infos: list[str] = []

    def container(self, **_kwargs: Any) -> _DummyContext:
        return _DummyContext()

    def markdown(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def columns(self, spec, **_kwargs: Any):
        count = spec if isinstance(spec, int) else len(spec)
        return tuple(_DummyContext() for _ in range(count))

    def file_uploader(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def caption(self, text: str, *_args: Any, **_kwargs: Any) -> None:
        self.captions.append(text)

    def text_area(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def metric(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def button(self, *_args: Any, **_kwargs: Any) -> bool:
        return False

    def info(self, text: str, *_args: Any, **_kwargs: Any) -> None:
        self.infos.append(text)

    def success(self, text: str, *_args: Any, **_kwargs: Any) -> None:
        self.successes.append(text)

    def error(self, text: str, *_args: Any, **_kwargs: Any) -> None:
        self.errors.append(text)


def test_phase_a_shows_failed_extraction_status_without_no_file_caption(
    monkeypatch,
) -> None:
    upload = type("Upload", (), {"name": "scan.pdf", "size": 128})()
    fake_st = _FakeStreamlitPhaseA(
        {
            "cs.source_upload_file": upload,
            jobad_intake.SOURCE_UPLOAD_TEXT_KEY: "",
            jobad_intake.SOURCE_UPLOAD_SIG_KEY: ("scan.pdf", 128),
            SSKey.LAST_ERROR.value: "Datei enthält keinen auslesbaren Inhalt.",
            SSKey.SOURCE_TEXT.value: "",
            jobad_intake.SOURCE_TEXT_INPUT_KEY: "",
            SSKey.SOURCE_FILE_META.value: {"name": "scan.pdf"},
        }
    )

    monkeypatch.setattr(jobad_intake, "st", fake_st)
    monkeypatch.setattr(jobad_intake, "render_ui_mode_selector", lambda **_kwargs: None)

    jobad_intake._render_phase_a_source_and_privacy_controls()

    assert "Datei ausgewählt: scan.pdf" in fake_st.infos
    assert (
        "Extraktion fehlgeschlagen: Datei enthält keinen auslesbaren Inhalt."
        in fake_st.errors
    )
    assert "Noch keine Datei hochgeladen." not in fake_st.captions


def test_phase_a_shows_pdf_ocr_error_message(monkeypatch) -> None:
    upload = type("Upload", (), {"name": "scan.pdf", "size": 128})()
    fake_st = _FakeStreamlitPhaseA(
        {
            "cs.source_upload_file": upload,
            jobad_intake.SOURCE_UPLOAD_TEXT_KEY: "",
            jobad_intake.SOURCE_UPLOAD_SIG_KEY: ("scan.pdf", 128),
            SSKey.LAST_ERROR.value: "PDF enthält keinen Textlayer (OCR fehlt).",
            SSKey.SOURCE_TEXT.value: "",
            jobad_intake.SOURCE_TEXT_INPUT_KEY: "",
            SSKey.SOURCE_FILE_META.value: {"name": "scan.pdf"},
        }
    )

    monkeypatch.setattr(jobad_intake, "st", fake_st)
    monkeypatch.setattr(jobad_intake, "render_ui_mode_selector", lambda **_kwargs: None)

    jobad_intake._render_phase_a_source_and_privacy_controls()

    assert (
        "Extraktion fehlgeschlagen: PDF enthält keinen Textlayer (OCR fehlt)."
        in fake_st.errors
    )


class _DummySpinner:
    def __enter__(self) -> "_DummySpinner":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        return None


class _FakeStreamlitRender:
    def __init__(self, session_state: dict[str, object]) -> None:
        self.session_state = session_state

    def header(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def caption(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def success(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def info(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def write(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def expander(self, *_args: Any, **_kwargs: Any) -> _DummyContext:
        return _DummyContext()

    def spinner(self, *_args: Any, **_kwargs: Any) -> _DummySpinner:
        return _DummySpinner()

    def rerun(self) -> None:
        return None


class _DummyModel:
    def model_dump(self) -> dict[str, object]:
        return {"ok": True}


def test_render_jobad_intake_uses_manual_text_when_upload_empty(monkeypatch) -> None:
    manual_text = "Manueller Jobspec"
    fake_st = _FakeStreamlitRender(
        {
            SSKey.SOURCE_TEXT.value: manual_text,
            jobad_intake.SOURCE_UPLOAD_TEXT_KEY: "",
            jobad_intake.SOURCE_TEXT_INPUT_KEY: manual_text,
            SSKey.SOURCE_REDACT_PII.value: False,
            SSKey.STORE_API_OUTPUT.value: False,
            "cs.source_upload_file": object(),
        }
    )
    captured: dict[str, object] = {}

    monkeypatch.setattr(jobad_intake, "st", fake_st)
    monkeypatch.setattr(
        jobad_intake, "_render_phase_a_source_and_privacy_controls", lambda: True
    )
    monkeypatch.setattr(
        jobad_intake, "_render_phase_b_extraction_review", lambda _ctx: None
    )
    monkeypatch.setattr(jobad_intake, "_render_phase_c_esco_anchor", lambda: None)
    monkeypatch.setattr(jobad_intake, "render_error_banner", lambda: None)
    monkeypatch.setattr(jobad_intake, "clear_error", lambda: None)
    monkeypatch.setattr(jobad_intake, "load_openai_settings", lambda: object())
    monkeypatch.setattr(jobad_intake, "get_model_override", lambda: None)
    monkeypatch.setattr(
        jobad_intake,
        "resolve_model_for_task",
        lambda **_kwargs: "gpt-test",
    )
    monkeypatch.setattr(jobad_intake, "usage_has_cache_hit", lambda _usage: False)

    def _fake_extract_job_ad(
        text: str, **_kwargs: Any
    ) -> tuple[_DummyModel, dict[str, bool]]:
        captured["submitted"] = text
        return _DummyModel(), {"cached": False}

    monkeypatch.setattr(jobad_intake, "extract_job_ad", _fake_extract_job_ad)
    monkeypatch.setattr(
        jobad_intake,
        "generate_question_plan",
        lambda _job, **_kwargs: (_DummyModel(), {"cached": False}),
    )

    ctx = type("Ctx", (), {})()
    jobad_intake.render_jobad_intake(ctx)

    assert captured["submitted"] == manual_text
