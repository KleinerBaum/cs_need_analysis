from __future__ import annotations

from typing import Any

from constants import AnswerType, FactKey, FactSourceType, SSKey
import document_preview
from schemas import JobAdExtract, Question, QuestionPlan, QuestionStep
import wizard_pages.jobad_intake as jobad_intake


class _FakeStreamlit:
    def __init__(self) -> None:
        self.session_state: dict[str, object] = {
            jobad_intake.SOURCE_UPLOAD_TEXT_KEY: "bestehender upload-text"
        }


class _FakeUploadBytes:
    def __init__(self, payload: bytes, *, name: str) -> None:
        self.name = name
        self.size = len(payload)
        self._payload = payload
        self._pos = 0

    def seek(self, pos: int) -> int:
        self._pos = pos
        return pos

    def read(self) -> bytes:
        payload = self._payload[self._pos :]
        self._pos = len(self._payload)
        return payload


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


def test_extract_upload_to_state_keeps_previous_text_on_signature_error(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlit()
    set_error_messages: list[str] = []

    monkeypatch.setattr(jobad_intake, "st", fake_st)
    monkeypatch.setattr(
        jobad_intake, "set_error", lambda msg: set_error_messages.append(msg)
    )

    result = jobad_intake._extract_upload_to_state(
        _FakeUploadBytes(b"%PDF-1.4\n%%EOF\n", name="jobspec.docx"),
        step="test.extract_upload_to_state.signature_guard",
    )

    assert result is None
    assert set_error_messages == ["Dateisignatur passt nicht zur Dateiendung."]
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
        self.text_area_labels: list[str] = []
        self.warnings: list[str] = []

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

    def text_area(self, label: str, *_args: Any, **_kwargs: Any) -> None:
        self.text_area_labels.append(label)
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

    def warning(self, text: str, *_args: Any, **_kwargs: Any) -> None:
        self.warnings.append(text)


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

    assert "Datei bereit: scan.pdf" in fake_st.infos
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


def test_phase_a_keeps_editable_extracted_text_after_upload(monkeypatch) -> None:
    upload = type("Upload", (), {"name": "jobspec.txt", "size": 12})()
    fake_st = _FakeStreamlitPhaseA(
        {
            "cs.source_upload_file": upload,
            jobad_intake.SOURCE_UPLOAD_TEXT_KEY: "Extrahierter Inhalt",
            jobad_intake.SOURCE_UPLOAD_SIG_KEY: ("jobspec.txt", 12),
            SSKey.LAST_ERROR.value: "",
            SSKey.SOURCE_TEXT.value: "Extrahierter Inhalt",
            jobad_intake.SOURCE_TEXT_INPUT_KEY: "Extrahierter Inhalt",
            SSKey.SOURCE_FILE_META.value: {"name": "jobspec.txt"},
        }
    )

    monkeypatch.setattr(jobad_intake, "st", fake_st)
    monkeypatch.setattr(jobad_intake, "render_ui_mode_selector", lambda **_kwargs: None)

    jobad_intake._render_phase_a_source_and_privacy_controls()

    assert "Extrahierter Text für die Analyse" in fake_st.text_area_labels


class _FakeUploadPreview:
    def __init__(self, payload: bytes, *, name: str) -> None:
        self.name = name
        self.size = len(payload)
        self._payload = payload
        self._pos = 0

    def seek(self, pos: int) -> int:
        self._pos = pos
        return pos

    def read(self) -> bytes:
        if self._pos:
            payload = self._payload[self._pos :]
        else:
            payload = self._payload
        self._pos = len(self._payload)
        return payload


class _PreviewStreamlit:
    def __init__(self) -> None:
        self.markdowns: list[str] = []

    def markdown(self, text: str, *_args: Any, **_kwargs: Any) -> None:
        self.markdowns.append(text)


def test_render_uploaded_document_preview_embeds_pdf_bytes(monkeypatch) -> None:
    fake_st = _PreviewStreamlit()
    monkeypatch.setattr(jobad_intake, "st", fake_st)
    upload = _FakeUploadPreview(b"%PDF-1.4\nbody\n%%EOF\n", name="jobspec.pdf")

    rendered = jobad_intake._render_uploaded_document_preview(upload, "")

    assert rendered is True
    assert "data:application/pdf;base64," in fake_st.markdowns[0]


def test_uploaded_document_preview_skips_invalid_pdf_bytes() -> None:
    upload = _FakeUploadPreview(b"%PDF-1.4\nbody", name="jobspec.pdf")

    html = document_preview.uploaded_document_preview_html(upload, "")

    assert html is not None
    assert "data:application/pdf;base64," not in html


def test_text_preview_html_escapes_fallback_text() -> None:
    html = jobad_intake._text_preview_html("<script>alert(1)</script>")

    assert "<script>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html


def test_docx_preview_html_escapes_blocks(monkeypatch) -> None:
    monkeypatch.setattr(
        document_preview,
        "extract_docx_preview_blocks",
        lambda _raw: [{"type": "paragraph", "text": "<b>unsafe</b>", "level": 0}],
    )

    html = document_preview.docx_preview_html(b"docx")

    assert "<b>unsafe</b>" not in html
    assert "&lt;b&gt;unsafe&lt;/b&gt;" in html


class _FakeStreamlitSourceSection:
    def __init__(self, session_state: dict[str, object]) -> None:
        self.session_state = session_state
        self.markdowns: list[str] = []
        self.expanders: list[tuple[str, bool]] = []

    def container(self, **_kwargs: Any) -> _DummyContext:
        return _DummyContext()

    def markdown(self, text: str, *_args: Any, **_kwargs: Any) -> None:
        self.markdowns.append(text)

    def expander(self, label: str, *, expanded: bool = False) -> _DummyContext:
        self.expanders.append((label, expanded))
        return _DummyContext()

    def caption(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def columns(self, spec, **_kwargs: Any):
        count = spec if isinstance(spec, int) else len(spec)
        return tuple(_DummyContext() for _ in range(count))

    def file_uploader(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def text_area(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def metric(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def button(self, *_args: Any, **_kwargs: Any) -> bool:
        return False

    def info(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def success(self, *_args: Any, **_kwargs: Any) -> None:
        return None

    def error(self, *_args: Any, **_kwargs: Any) -> None:
        return None


def test_source_input_section_stays_visible_after_analysis(monkeypatch) -> None:
    fake_st = _FakeStreamlitSourceSection(
        {
            SSKey.JOB_EXTRACT.value: {"job_title": "Data Engineer"},
            SSKey.QUESTION_PLAN.value: {"steps": []},
            SSKey.SOURCE_TEXT.value: "Initial text",
        }
    )
    monkeypatch.setattr(jobad_intake, "st", fake_st)
    monkeypatch.setattr(
        jobad_intake, "_render_phase_a_source_and_privacy_controls", lambda: False
    )

    result = jobad_intake._render_source_input_section(object())

    assert result is False
    assert "#### Quelle bearbeiten" not in fake_st.markdowns
    assert fake_st.expanders == []


def test_extraction_result_section_opens_by_default(monkeypatch) -> None:
    fake_st = _FakeStreamlitSourceSection(
        {
            SSKey.JOB_EXTRACT.value: {"job_title": "Data Engineer"},
            SSKey.QUESTION_PLAN.value: {"steps": []},
        }
    )
    monkeypatch.setattr(jobad_intake, "st", fake_st)
    monkeypatch.setattr(jobad_intake, "_has_completed_intake_analysis", lambda: True)
    monkeypatch.setattr(
        jobad_intake,
        "_render_phase_b_extraction_review",
        lambda _ctx: fake_st.markdowns.append("rendered-review"),
    )

    jobad_intake._render_extraction_result_section(object())

    assert fake_st.expanders == []
    assert "rendered-review" in fake_st.markdowns


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
    monkeypatch.setattr(jobad_intake, "_render_phase_c_esco_anchor", lambda _ctx: None)
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


def test_render_jobad_intake_redacts_by_default_when_privacy_key_missing(
    monkeypatch,
) -> None:
    manual_text = "Kontakt: max@example.com"
    redacted_text = "Kontakt: [redacted]"
    fake_st = _FakeStreamlitRender(
        {
            SSKey.SOURCE_TEXT.value: manual_text,
            jobad_intake.SOURCE_UPLOAD_TEXT_KEY: "",
            jobad_intake.SOURCE_TEXT_INPUT_KEY: manual_text,
            SSKey.STORE_API_OUTPUT.value: False,
            "cs.source_upload_file": object(),
        }
    )
    captured: dict[str, object] = {}
    redaction_calls: list[str] = []

    monkeypatch.setattr(jobad_intake, "st", fake_st)
    monkeypatch.setattr(
        jobad_intake, "_render_phase_a_source_and_privacy_controls", lambda: True
    )
    monkeypatch.setattr(
        jobad_intake, "_render_phase_b_extraction_review", lambda _ctx: None
    )
    monkeypatch.setattr(jobad_intake, "_render_phase_c_esco_anchor", lambda _ctx: None)
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

    def _fake_redact_pii(text: str) -> str:
        redaction_calls.append(text)
        return redacted_text

    def _fake_extract_job_ad(
        text: str, **_kwargs: Any
    ) -> tuple[_DummyModel, dict[str, bool]]:
        captured["submitted"] = text
        return _DummyModel(), {"cached": False}

    monkeypatch.setattr(jobad_intake, "redact_pii", _fake_redact_pii)
    monkeypatch.setattr(jobad_intake, "extract_job_ad", _fake_extract_job_ad)
    monkeypatch.setattr(
        jobad_intake,
        "generate_question_plan",
        lambda _job, **_kwargs: (_DummyModel(), {"cached": False}),
    )

    ctx = type("Ctx", (), {})()
    jobad_intake.render_jobad_intake(ctx)

    assert redaction_calls == [manual_text]
    assert captured["submitted"] == redacted_text


def test_promote_reviewed_job_extract_fills_confirmed_state_without_overwriting_touched(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlitRender(
        {
            SSKey.ANSWERS.value: {"company_name": "Manual GmbH"},
            SSKey.ANSWER_META.value: {"company_name": {"touched": True}},
            SSKey.ROLE_TASKS_SELECTED.value: [],
            SSKey.SKILLS_SELECTED.value: [],
        }
    )
    monkeypatch.setattr(jobad_intake, "st", fake_st)
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="company",
                title_de="Unternehmen",
                questions=[
                    Question(
                        id="job_title",
                        label="Jobtitel",
                        answer_type=AnswerType.SHORT_TEXT,
                        target_path="job_title",
                    ),
                    Question(
                        id="company_name",
                        label="Unternehmen",
                        answer_type=AnswerType.SHORT_TEXT,
                        target_path="company_name",
                    ),
                ],
            ),
            QuestionStep(
                step_key="skills",
                title_de="Skills",
                questions=[
                    Question(
                        id="must_have_skills",
                        label="Must-have Skills",
                        answer_type=AnswerType.MULTI_SELECT,
                        target_path="must_have_skills",
                    )
                ],
            ),
        ]
    )
    job = JobAdExtract(
        job_title="AI Transformation Consultant",
        company_name="Acme",
        responsibilities=["Service Cluster vorbereiten"],
        deliverables=["Mini-Pitch-Deck vorbereiten"],
        must_have_skills=["AI-Kompetenzen"],
        tech_stack=["myConcerto"],
    )

    jobad_intake._promote_reviewed_job_extract(job, plan)

    answers = fake_st.session_state[SSKey.ANSWERS.value]
    meta = fake_st.session_state[SSKey.ANSWER_META.value]
    assert answers["job_title"] == "AI Transformation Consultant"
    assert answers["company_name"] == "Manual GmbH"
    assert answers["must_have_skills"] == ["AI-Kompetenzen"]
    assert meta["job_title"]["confirmed"] is True
    assert meta["company_name"]["touched"] is True
    assert fake_st.session_state[SSKey.ROLE_TASKS_SELECTED.value] == [
        "Service Cluster vorbereiten",
        "Mini-Pitch-Deck vorbereiten",
    ]
    assert fake_st.session_state[SSKey.SKILLS_SELECTED.value] == [
        "AI-Kompetenzen",
        "myConcerto",
    ]
    intake_facts = fake_st.session_state[SSKey.INTAKE_FACTS.value]
    assert intake_facts[FactKey.COMPANY_COMPANY_NAME.value] == "Manual GmbH"
    assert (
        intake_facts[FactKey.ROLE_JOB_TITLE.value] == "AI Transformation Consultant"
    )
    assert intake_facts[FactKey.SKILLS_MUST_HAVE_SKILLS.value] == ["AI-Kompetenzen"]
    evidence = fake_st.session_state[SSKey.INTAKE_FACT_EVIDENCE.value]
    assert evidence[FactKey.COMPANY_COMPANY_NAME.value]["source_type"] == (
        FactSourceType.MANUAL.value
    )
    assert evidence[FactKey.COMPANY_COMPANY_NAME.value]["confidence"] == 1.0
    assert evidence[FactKey.ROLE_JOB_TITLE.value]["source_type"] == (
        FactSourceType.JOBSPEC.value
    )
    assert evidence[FactKey.ROLE_JOB_TITLE.value]["confidence"] == 0.75
