from __future__ import annotations

import math
from contextlib import nullcontext
from typing import Any, Final

import streamlit as st

from constants import (
    AnswerType,
    DEFAULT_ESCO_DATA_SOURCE_MODE,
    ESCO_API_MODES,
    ESCO_DATA_SOURCE_MODES,
    ESCO_RELEASE_LANE_PREVIEW,
    ESCO_RELEASE_LANE_SELECTED_VERSION,
    ESCO_RELEASE_LANE_STABLE,
    SSKey,
)
from llm_client import (
    OpenAICallError,
    TASK_EXTRACT_JOB_AD,
    TASK_GENERATE_QUESTION_PLAN,
    extract_job_ad,
    generate_question_plan,
    resolve_model_for_task,
)
from occupation_context import classify_occupation_context
from parsing import extract_text_from_uploaded_file, redact_pii
from question_progress import (
    is_answered,
    resolve_question_job_extract_value,
    value_hash,
)
from question_plan_compiler import compile_question_plan
from schemas import JobAdExtract, Question, QuestionPlan
from settings_openai import load_openai_settings
from state import (
    clear_error,
    get_esco_occupation_selected,
    get_esco_semantic_context,
    has_confirmed_esco_anchor,
    get_model_override,
    handle_unexpected_exception,
    set_error,
)
from ui_components import (
    render_error_banner,
    render_intake_process_animation,
    render_job_extract_overview,
    render_openai_error,
)
from usage_utils import usage_has_cache_hit
from wizard_pages.base import (
    WizardContext,
    _get_esco_config,
    _set_esco_config,
    render_ui_mode_selector,
)
from wizard_pages.esco_occupation_ui import render_esco_occupation_confirmation


SOURCE_TEXT_INPUT_KEY: Final[str] = "cs.source_text_input"
SOURCE_UPLOAD_SIG_KEY: Final[str] = "cs.source_upload_signature"
SOURCE_UPLOAD_TEXT_KEY: Final[str] = "cs.source_uploaded_text"
SOURCE_ACTIVE_KEY: Final[str] = "cs.source_active"


def _model_dump_json_compatible(model: Any) -> dict[str, Any]:
    model_dump = getattr(model, "model_dump")
    try:
        return model_dump(mode="json")
    except TypeError:
        return model_dump()


def _sync_deterministic_question_flow(job: JobAdExtract, base_plan: QuestionPlan) -> None:
    semantic_context = get_esco_semantic_context()
    answers_raw = st.session_state.get(SSKey.ANSWERS.value, {})
    answers = answers_raw if isinstance(answers_raw, dict) else {}
    primary_anchor = (
        semantic_context.primary_anchor.model_dump(mode="json")
        if semantic_context.primary_anchor is not None
        else None
    )
    capability_snapshot = semantic_context.capability_snapshot
    profile = classify_occupation_context(
        job=job,
        esco_selected=primary_anchor,
        esco_payload=st.session_state.get(SSKey.ESCO_OCCUPATION_PAYLOAD.value),
        esco_version=(
            capability_snapshot.selected_version if capability_snapshot else None
        ),
        answers=answers,
    )
    compiled = compile_question_plan(base_plan=base_plan, profile=profile)
    st.session_state[SSKey.OCCUPATION_PROFILE.value] = profile.model_dump(mode="json")
    st.session_state[SSKey.OCCUPATION_CLASSIFICATION_TRACE.value] = [
        item.model_dump(mode="json") for item in profile.evidence
    ]
    st.session_state[SSKey.OCCUPATION_PACK_KEYS.value] = list(profile.pack_keys)
    st.session_state[SSKey.QUESTION_FLOW_PROVENANCE.value] = (
        compiled.provenance.model_dump(mode="json")
    )
    st.session_state[SSKey.QUESTION_FLOW_FINGERPRINT.value] = (
        compiled.provenance.profile_fingerprint
    )
    st.session_state[SSKey.QUESTION_PLAN.value] = compiled.plan.model_dump(mode="json")


def _has_promotable_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, dict):
        return any(_has_promotable_value(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_has_promotable_value(item) for item in value)
    return True


def _dedupe_strings(values: list[Any]) -> list[str]:
    deduped: list[str] = []
    seen: set[str] = set()
    for value in values:
        text = str(value or "").strip()
        key = text.casefold()
        if not text or key in seen:
            continue
        deduped.append(text)
        seen.add(key)
    return deduped


def _coerce_extract_value_for_question(question: Question, value: Any) -> Any:
    if not _has_promotable_value(value):
        return None
    if question.answer_type == AnswerType.MULTI_SELECT:
        if isinstance(value, list):
            return _dedupe_strings(value)
        return [str(value).strip()]
    if question.answer_type in (AnswerType.SHORT_TEXT, AnswerType.LONG_TEXT):
        if isinstance(value, list):
            return "\n".join(_dedupe_strings(value))
        if isinstance(value, dict):
            return None
        return str(value).strip()
    if question.answer_type == AnswerType.SINGLE_SELECT:
        text = str(value).strip()
        option_values = {
            str(getattr(option, "value", option)).strip()
            for option in question.options or []
            if str(getattr(option, "value", option)).strip()
        }
        if option_values and text not in option_values:
            return None
        return text
    if question.answer_type == AnswerType.NUMBER:
        if isinstance(value, (int, float)):
            return value
        try:
            return float(str(value).strip())
        except ValueError:
            return None
    if question.answer_type == AnswerType.BOOLEAN:
        return value if isinstance(value, bool) else None
    if question.answer_type == AnswerType.DATE:
        return str(value).strip()
    return value


def _seed_list_state_from_jobspec(state_key: SSKey, values: list[Any]) -> None:
    current = st.session_state.get(state_key.value, [])
    if isinstance(current, list) and current:
        return
    deduped = _dedupe_strings(values)
    if deduped:
        st.session_state[state_key.value] = deduped


def _promote_reviewed_job_extract(job: JobAdExtract, plan: QuestionPlan) -> None:
    answers_raw = st.session_state.get(SSKey.ANSWERS.value, {})
    answers = dict(answers_raw) if isinstance(answers_raw, dict) else {}
    meta_raw = st.session_state.get(SSKey.ANSWER_META.value, {})
    meta = dict(meta_raw) if isinstance(meta_raw, dict) else {}

    for step in plan.steps:
        for question in step.questions:
            question_meta = meta.get(question.id, {})
            if isinstance(question_meta, dict) and question_meta.get("touched"):
                continue
            if is_answered(
                question,
                answers.get(question.id),
                question_meta if isinstance(question_meta, dict) else {},
            ):
                continue
            extracted_value = resolve_question_job_extract_value(question, job)
            answer_value = _coerce_extract_value_for_question(question, extracted_value)
            if not _has_promotable_value(answer_value):
                continue
            answers[question.id] = answer_value
            meta[question.id] = {
                **(question_meta if isinstance(question_meta, dict) else {}),
                "confirmed": True,
                "touched": False,
                "last_value_hash": value_hash(answer_value),
            }

    st.session_state[SSKey.ANSWERS.value] = answers
    st.session_state[SSKey.ANSWER_META.value] = meta
    _seed_list_state_from_jobspec(
        SSKey.ROLE_TASKS_SELECTED,
        [*job.responsibilities, *job.deliverables, *job.success_metrics],
    )
    _seed_list_state_from_jobspec(
        SSKey.SKILLS_SELECTED,
        [
            *job.must_have_skills,
            *job.nice_to_have_skills,
            *job.tech_stack,
            *job.domain_expertise,
        ],
    )


def _preview_height_for_text(text: str) -> int:
    """Return a dynamic textarea height so the preview does not need scrolling."""
    chars_per_line = 95
    line_height_px = 28
    padding_px = 28
    total_lines = sum(
        max(1, math.ceil(len(line) / chars_per_line))
        for line in text.splitlines() or [""]
    )
    return (total_lines * line_height_px) + padding_px


def _manual_input_height_for_text(text: str) -> int:
    """Return a compact default height for short text and grow moderately for longer text."""
    min_height_px = 200
    max_height_px = 380
    return max(min_height_px, min(_preview_height_for_text(text), max_height_px))


def _render_identified_information_block(ctx: WizardContext) -> None:
    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN.value)
    if not isinstance(job_dict, dict) or not isinstance(plan_dict, dict):
        return

    job = JobAdExtract.model_validate(job_dict)
    plan = QuestionPlan.model_validate(plan_dict)

    selected_occupation = get_esco_occupation_selected() or {}
    has_confirmed_anchor = has_confirmed_esco_anchor()
    selected_occupation_title = str(selected_occupation.get("title") or "").strip()

    st.caption(
        "Die wichtigsten Angaben sind vorbereitet. Prüfen Sie kurz die Basisdaten "
        "und bestätigen Sie anschließend den passenden ESCO-Beruf."
    )
    render_job_extract_overview(
        job,
        plan=plan,
        show_question_limits=False,
        show_heading=False,
        mode="compact",
        show_notes=False,
    )

    nav_col_back, nav_col_anchor = st.columns([1, 2], gap="small")
    with nav_col_back:
        if st.button("← Zurück", key="cs.jobspec.ident_info.back"):
            ctx.prev()
            st.rerun()
    with nav_col_anchor:
        if has_confirmed_anchor:
            title = selected_occupation_title or "ESCO-Beruf"
            st.success(f"ESCO-Anker bestätigt: {title}")
        else:
            st.caption(
                "Optional: In Phase C können Sie einen semantischen ESCO-Anker bestätigen."
            )


def _set_active_source(source: str, text: str) -> None:
    st.session_state[SSKey.SOURCE_TEXT.value] = text
    st.session_state[SOURCE_ACTIVE_KEY] = source


def _usage_has_cache_hit(usage: Any) -> bool:
    if isinstance(usage, dict):
        return bool(usage.get("cached"))
    return bool(getattr(usage, "cached", False))


def _on_manual_text_change() -> None:
    manual_text = str(st.session_state.get(SOURCE_TEXT_INPUT_KEY, ""))
    _set_active_source("text", manual_text)


def _extract_upload_to_state(
    upload: object, *, step: str, update_text_widget: bool = True
) -> str | None:
    try:
        uploaded_text, source_meta = extract_text_from_uploaded_file(upload)
        if not uploaded_text.strip():
            raise ValueError("Datei enthält keinen auslesbaren Inhalt.")
    except ValueError as exc:
        set_error(str(exc) or "Datei enthält keinen auslesbaren Inhalt.")
        return None
    except Exception as exc:
        error_type = type(exc).__name__
        handle_unexpected_exception(
            step=step,
            exc=exc,
            error_type=error_type,
            error_code="JOBAD_FILE_READ_UNEXPECTED",
            user_message="Datei konnte nicht gelesen werden.",
        )
        return None

    st.session_state[SOURCE_UPLOAD_TEXT_KEY] = uploaded_text
    st.session_state[SSKey.SOURCE_FILE_META.value] = source_meta
    st.session_state[SOURCE_UPLOAD_SIG_KEY] = (
        source_meta.get("name", ""),
        source_meta.get("size", 0),
    )
    if uploaded_text.strip():
        st.session_state[SOURCE_TEXT_INPUT_KEY] = uploaded_text
    _set_active_source("upload", uploaded_text)
    return uploaded_text


def _on_upload_change() -> None:
    upload = st.session_state.get("cs.source_upload_file")
    if upload is None:
        return

    _extract_upload_to_state(
        upload, step="_on_upload_change.extract_text_from_uploaded_file"
    )


def _has_completed_landing_analysis() -> bool:
    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN.value)
    return isinstance(job_dict, dict) and isinstance(plan_dict, dict)


def _has_completed_intake_analysis() -> bool:
    return _has_completed_landing_analysis()


def _render_phase_a_source_and_privacy_controls() -> bool:
    do_extract = False

    st.markdown(
        """
        <style>
        .st-key-cs_ui_mode [data-baseweb="select"] > div,
        .st-key-cs-ui_mode [data-baseweb="select"] > div {
            background: rgba(255, 255, 255, 0.10) !important;
            color: #eaf2ff !important;
            border: 1px solid rgba(255, 255, 255, 0.25) !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )
    upload_col, text_col = st.columns([1, 1.4], gap="large")
    with upload_col:
        st.file_uploader(
            "Datei hochladen",
            type=["pdf", "docx", "txt"],
            accept_multiple_files=False,
            key="cs.source_upload_file",
            on_change=_on_upload_change,
        )
        upload = st.session_state.get("cs.source_upload_file")
        if upload is not None:
            current_sig = (
                str(getattr(upload, "name", "") or ""),
                int(getattr(upload, "size", 0) or 0),
            )
            if st.session_state.get(SOURCE_UPLOAD_SIG_KEY) != current_sig:
                _extract_upload_to_state(
                    upload,
                    step="_render_phase_a_source_and_privacy_controls.sync_upload",
                    update_text_widget=True,
                )
        render_ui_mode_selector(show_label=False)
        _render_esco_operating_block()
    with text_col:
        manual_text = str(st.session_state.get(SOURCE_TEXT_INPUT_KEY, ""))
        st.text_area(
            "Text einfügen oder Datei hochladen (PDF/DOCX/TXT)",
            key=SOURCE_TEXT_INPUT_KEY,
            height=min(420, max(280, _manual_input_height_for_text(manual_text))),
            on_change=_on_manual_text_change,
            placeholder="Füge hier die Stellenanzeige oder Jobspec ein …",
        )

    uploaded_text = str(st.session_state.get(SOURCE_UPLOAD_TEXT_KEY, ""))
    upload_meta = st.session_state.get(SSKey.SOURCE_FILE_META.value, {})
    upload = st.session_state.get("cs.source_upload_file")
    last_error = str(st.session_state.get(SSKey.LAST_ERROR.value, "") or "")

    st.markdown("---")
    status_col, chars_col, action_col = st.columns([1.6, 1, 1], gap="small")
    with status_col:
        file_name = str(upload_meta.get("name") or getattr(upload, "name", "") or "")
        if upload is not None:
            st.info(f"Datei bereit: {file_name or 'Unbekannt'}")

        if upload is not None and not uploaded_text and last_error:
            st.error(f"Extraktion fehlgeschlagen: {last_error}")
    with chars_col:
        active_source_text = str(st.session_state.get(SSKey.SOURCE_TEXT.value, ""))
        char_count = len(active_source_text.strip()) if active_source_text else 0
        st.metric("Zeichen", f"{char_count:,}".replace(",", "."))
    with action_col:
        do_extract = st.button(
            "Jetzt analysieren",
            width="stretch",
            help="Analysieren und identifizierte Informationen direkt im Start anzeigen",
        )

    return do_extract


def _render_esco_operating_block() -> None:
    if not all(hasattr(st, name) for name in ("radio", "selectbox", "caption")):
        if hasattr(st, "caption"):
            st.caption("ESCO-Betrieb: Stable · hosted/live_api · Sprache DE/EN")
        return

    config = _get_esco_config()
    ui_mode = str(st.session_state.get(SSKey.UI_MODE.value, "standard")).strip().lower()
    is_expert = ui_mode == "expert"
    language_options = ("de", "en")
    selected_language = str(config.get("language") or "de").strip().lower()
    if selected_language not in language_options:
        selected_language = "de"
    fallback_language = str(config.get("fallback_language") or "en").strip().lower()
    if fallback_language not in language_options or fallback_language == selected_language:
        fallback_language = "en" if selected_language == "de" else "de"

    with st.container(border=True):
        st.markdown("#### ESCO-Betrieb")
        lang_col, fallback_col = st.columns([1, 1], gap="small")
        with lang_col:
            selected_language = st.radio(
                "Arbeitssprache",
                options=language_options,
                index=language_options.index(selected_language),
                horizontal=True,
                key=f"{SSKey.ESCO_CONFIG.value}.phase_a.language",
            )
        with fallback_col:
            fallback_language = st.selectbox(
                "Fallback-Sprache",
                options=[value for value in language_options if value != selected_language],
                index=0,
                key=f"{SSKey.ESCO_CONFIG.value}.phase_a.fallback_language",
            )

        release_lane = str(config.get("release_lane") or ESCO_RELEASE_LANE_STABLE)
        selected_version = str(config.get("selected_version") or "").strip()
        api_mode = str(config.get("api_mode") or "hosted").strip().lower()
        data_source_mode = str(
            config.get("data_source_mode") or DEFAULT_ESCO_DATA_SOURCE_MODE
        ).strip().lower()
        view_obsolete = bool(config.get("view_obsolete", False))
        if is_expert:
            release_lane_options = (ESCO_RELEASE_LANE_STABLE, ESCO_RELEASE_LANE_PREVIEW)
            release_lane = st.selectbox(
                "Semantik-Lane",
                options=release_lane_options,
                index=(
                    release_lane_options.index(release_lane)
                    if release_lane in release_lane_options
                    else 0
                ),
                format_func=lambda lane: (
                    f"Stable ({ESCO_RELEASE_LANE_SELECTED_VERSION[ESCO_RELEASE_LANE_STABLE]})"
                    if lane == ESCO_RELEASE_LANE_STABLE
                    else f"Preview ({ESCO_RELEASE_LANE_SELECTED_VERSION[ESCO_RELEASE_LANE_PREVIEW]})"
                ),
                key=f"{SSKey.ESCO_CONFIG.value}.phase_a.release_lane",
            )
            selected_version = ESCO_RELEASE_LANE_SELECTED_VERSION[release_lane]
            api_mode = st.selectbox(
                "API-Modus",
                options=ESCO_API_MODES,
                index=ESCO_API_MODES.index(api_mode) if api_mode in ESCO_API_MODES else 0,
                key=f"{SSKey.ESCO_CONFIG.value}.phase_a.api_mode",
            )
            data_source_mode = st.selectbox(
                "Runtime-Lane",
                options=ESCO_DATA_SOURCE_MODES,
                index=(
                    ESCO_DATA_SOURCE_MODES.index(data_source_mode)
                    if data_source_mode in ESCO_DATA_SOURCE_MODES
                    else 0
                ),
                key=f"{SSKey.ESCO_CONFIG.value}.phase_a.data_source_mode",
            )
            if hasattr(st, "toggle"):
                view_obsolete = st.toggle(
                    "Obsolete anzeigen",
                    value=view_obsolete,
                    key=f"{SSKey.ESCO_CONFIG.value}.phase_a.view_obsolete",
                )
        else:
            release_lane = ESCO_RELEASE_LANE_STABLE
            selected_version = (
                selected_version
                or ESCO_RELEASE_LANE_SELECTED_VERSION[ESCO_RELEASE_LANE_STABLE]
            )

        _set_esco_config(
            release_lane=release_lane,
            selected_version=selected_version,
            view_obsolete=view_obsolete,
            language=selected_language,
            fallback_language=fallback_language,
            api_mode=api_mode,
            data_source_mode=data_source_mode,
        )
        st.caption(
            "Diagnose: "
            f"lane={release_lane} · version={selected_version} · "
            f"api={api_mode} · runtime={data_source_mode} · "
            f"language={selected_language}/{fallback_language}"
        )




def _render_source_summary() -> None:
    active_source = str(st.session_state.get(SOURCE_ACTIVE_KEY, "") or "")
    source_label = "Upload" if active_source == "upload" else "Text"
    source_text = str(st.session_state.get(SSKey.SOURCE_TEXT.value, "") or "")
    char_count = len(source_text.strip())

    job_title = ""
    company_name = ""
    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    if isinstance(job_dict, dict):
        job_title = str(job_dict.get("job_title") or "").strip()
        company_name = str(job_dict.get("company_name") or "").strip()

    summary_parts = [
        f"Quelle: **{source_label}**",
        f"Zeichen: **{char_count:,}**".replace(",", "."),
    ]
    if job_title:
        summary_parts.append(f"Rolle: **{job_title}**")
    if company_name:
        summary_parts.append(f"Unternehmen: **{company_name}**")
    st.caption(" · ".join(summary_parts))


def _render_source_input_section(ctx: WizardContext) -> bool:
    del ctx
    if _has_completed_intake_analysis():
        _render_source_summary()
        container_ctx = (
            st.container(border=True) if hasattr(st, "container") else nullcontext()
        )
        with container_ctx:
            if hasattr(st, "markdown"):
                st.markdown("#### Jobspec-Quelle bearbeiten")
            return _render_phase_a_source_and_privacy_controls()
    container_ctx = (
        st.container(border=True) if hasattr(st, "container") else nullcontext()
    )
    with container_ctx:
        return _render_phase_a_source_and_privacy_controls()


def _render_extraction_result_section(ctx: WizardContext) -> None:
    if not _has_completed_intake_analysis():
        return
    container_ctx = (
        st.container(border=True) if hasattr(st, "container") else nullcontext()
    )
    with container_ctx:
        if hasattr(st, "markdown"):
            st.markdown("### Analyseergebnis")
        _render_phase_b_extraction_review(ctx)


def _render_esco_anchor_section(ctx: WizardContext) -> None:
    if not _has_completed_intake_analysis():
        return
    container_ctx = (
        st.container(border=True) if hasattr(st, "container") else nullcontext()
    )
    with container_ctx:
        if hasattr(st, "markdown"):
            st.markdown("### ESCO-Anker bestätigen")
        _render_phase_c_esco_anchor(ctx)

def _render_phase_b_extraction_review(ctx: WizardContext) -> None:
    _render_identified_information_block(ctx)


def _render_phase_c_esco_anchor(ctx: WizardContext) -> None:
    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN_BASE.value) or st.session_state.get(
        SSKey.QUESTION_PLAN.value
    )
    if not isinstance(job_dict, dict) or not isinstance(plan_dict, dict):
        return
    job = JobAdExtract.model_validate(job_dict)
    base_plan = QuestionPlan.model_validate(plan_dict)
    render_esco_occupation_confirmation(
        job,
        compact=True,
        show_start_context_panels=True,
        show_detail_panels=False,
    )
    _sync_deterministic_question_flow(job, base_plan)

    _, _, next_col = st.columns([1, 1, 1], gap="small")
    with next_col:
        if st.button("Weiter →", key="cs.start.next_step", width="stretch"):
            active_plan_raw = st.session_state.get(SSKey.QUESTION_PLAN.value, {})
            active_plan = (
                QuestionPlan.model_validate(active_plan_raw)
                if isinstance(active_plan_raw, dict)
                else base_plan
            )
            _promote_reviewed_job_extract(job, active_plan)
            ctx.next()
            st.rerun()


def render_jobad_intake(
    ctx: WizardContext, *, title: str = "Jobspezifikation einlesen"
) -> None:
    st.header(title)
    render_error_banner()

    if SOURCE_TEXT_INPUT_KEY not in st.session_state:
        st.session_state[SOURCE_TEXT_INPUT_KEY] = st.session_state.get(
            SSKey.SOURCE_TEXT.value, ""
        )

    do_extract = _render_source_input_section(ctx)

    if _has_completed_intake_analysis():
        render_intake_process_animation(state="done")

    if do_extract:
        clear_error()
        effective_source_text = str(
            st.session_state.get(SSKey.SOURCE_TEXT.value, "") or ""
        )
        raw = effective_source_text
        if not raw.strip():
            uploaded_text = str(st.session_state.get(SOURCE_UPLOAD_TEXT_KEY, "") or "")
            if uploaded_text.strip():
                _set_active_source("upload", uploaded_text)
                raw = uploaded_text

        if not raw.strip():
            upload = st.session_state.get("cs.source_upload_file")
            if upload is not None:
                extracted_upload_text = _extract_upload_to_state(
                    upload,
                    step="jobad.extract_and_plan.extract_text_from_uploaded_file",
                    update_text_widget=False,
                )
                if extracted_upload_text is not None:
                    raw = extracted_upload_text

        if not raw.strip():
            set_error("Bitte zuerst ein Jobspec hochladen oder Text einfügen.")
            st.rerun()

        redact = bool(st.session_state.get(SSKey.SOURCE_REDACT_PII.value, False))        
        submitted = redact_pii(raw) if redact else raw
        session_override = get_model_override()
        store = bool(st.session_state.get(SSKey.STORE_API_OUTPUT.value, False))
        settings = load_openai_settings()
        resolved_extract_model = resolve_model_for_task(
            task_kind=TASK_EXTRACT_JOB_AD,
            session_override=session_override,
            settings=settings,
        )
        resolved_plan_model = resolve_model_for_task(
            task_kind=TASK_GENERATE_QUESTION_PLAN,
            session_override=session_override,
            settings=settings,
        )

        try:
            with st.spinner("Extrahiere Jobspec…"):
                job, usage1 = extract_job_ad(
                    submitted,
                    model=resolved_extract_model,
                    store=store,
                )

            with st.spinner("Erzeuge dynamischen Fragebogen…"):
                plan, usage2 = generate_question_plan(
                    job,
                    model=resolved_plan_model,
                    store=store,
                )

            st.session_state[SSKey.JOB_EXTRACT.value] = _model_dump_json_compatible(
                job
            )
            st.session_state[SSKey.QUESTION_PLAN_BASE.value] = (
                _model_dump_json_compatible(plan)
            )
            if isinstance(job, JobAdExtract) and isinstance(plan, QuestionPlan):
                _sync_deterministic_question_flow(job, plan)
            else:
                st.session_state[SSKey.QUESTION_PLAN.value] = (
                    _model_dump_json_compatible(plan)
                )

            extract_cached = usage_has_cache_hit(usage1)
            plan_cached = usage_has_cache_hit(usage2)
            st.session_state[SSKey.JOBAD_CACHE_HIT.value] = {
                "extract_job_ad": extract_cached,
                "generate_question_plan": plan_cached,
            }
            st.success("Fertig: Jobspec extrahiert und Fragebogen erzeugt.")
            if extract_cached or plan_cached:
                st.info("Mindestens ein Ergebnis wurde aus dem Cache geladen.")        
        except OpenAICallError as e:
            render_openai_error(e)
        except Exception as exc:
            error_type = type(exc).__name__
            handle_unexpected_exception(
                step="jobad.extract_and_plan",
                exc=exc,
                error_type=error_type,
                error_code="JOBAD_ANALYZE_UNEXPECTED",
            )

        st.rerun()

    _render_extraction_result_section(ctx)
    _render_esco_anchor_section(ctx)
