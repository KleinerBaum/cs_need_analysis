# app.py

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

from components.design_system import render_ui_styles
from constants import (
    APP_TITLE,
    SSKey,
    UI_PREFERENCE_ANSWER_MODE,
    UI_PREFERENCE_CONFIDENCE_THRESHOLD,
    UI_PREFERENCE_ESCO_MATCHING_STRICTNESS,
    UI_PREFERENCE_INFORMATION_DEPTH,
    UI_PREFERENCE_PII_REDUCTION,
    UI_PREFERENCE_REGIONAL_FOCUS,
)
from llm_client import (
    TASK_EXTRACT_JOB_AD,
    TASK_GENERATE_QUESTION_PLAN,
    TASK_GENERATE_VACANCY_BRIEF,
    resolve_model_for_task,
)
from settings_openai import load_openai_settings
from state import init_session_state, normalize_ui_preferences, reset_vacancy
from wizard_pages import load_pages
from wizard_pages.base import (
    WizardContext,
    map_ui_mode_to_answer_mode,
    normalize_ui_mode,
    sidebar_navigation,
)


def _public_sidebar_links() -> tuple[tuple[str, str], ...]:
    return (
        ("app.py", "Recruitment Need Analysis"),
        ("pages/01_Unsere_Kompetenzen.py", "Unsere Kompetenzen"),
        ("pages/02_Über_Cognitive_Staffing.py", "Ueber Cognitive Staffing"),
        ("pages/15_Kontakt.py", "Kontakt"),
    )


def _render_public_page_links_sidebar() -> None:
    for page_path, label in _public_sidebar_links():
        st.sidebar.page_link(page_path, label=label)
    st.sidebar.markdown('<div class="cs-sidebar-nav-gap"></div>', unsafe_allow_html=True)


def _image_as_data_uri(image_path: Path, mime_type: str) -> str:
    image_bytes = image_path.read_bytes()
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def _inject_theme_styles() -> None:
    """Inject global design-system styles plus minimal app-shell overrides."""

    render_ui_styles()

    root_dir = Path(__file__).resolve().parent
    logo_path = root_dir / "images" / "animation_pulse_SingleColorHex1_7kigl22lw.gif"
    logo_uri = _image_as_data_uri(logo_path, "image/gif")

    # App-shell specific styles (logo/header/sidebar spacing/layout quirks).
    st.markdown(
        f"""
        <style>
            [data-testid="stHeader"] {{
                background: transparent;
            }}

            [data-testid="stSidebarContent"]::before {{
                content: "";
                display: block;
                width: 220px;
                height: 64px;
                margin: 0 auto 0.75rem auto;
                background: url("{logo_uri}") center / contain no-repeat;
            }}

            .block-container {{
                max-width: none;
                padding-top: 1rem;
                padding-left: clamp(1rem, 2vw, 2rem);
                padding-right: clamp(1rem, 2vw, 2rem);
            }}

            [data-testid="stSidebarContent"] [data-testid="stVerticalBlock"] > div {{
                row-gap: 8px;
            }}

            .cs-sidebar-nav-gap {{
                height: 22px;
            }}

            @media (max-width: 900px) {{
                .block-container {{
                    padding-left: 0.9rem;
                    padding-right: 0.9rem;
                }}

                h1 {{
                    line-height: 1.2;
                }}

                h2 {{
                    line-height: 1.25;
                }}

                [data-testid="stButton"] button {{
                    min-height: 44px;
                }}
            }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_openai_debug_panel() -> None:
    """Render a compact, safe OpenAI resolution debug panel."""

    settings = load_openai_settings()
    session_model = st.session_state.get(SSKey.MODEL.value)
    session_model_override: str | None = None
    if isinstance(session_model, str):
        cleaned_session_model = session_model.strip()
        if cleaned_session_model and cleaned_session_model != settings.openai_model:
            session_model_override = cleaned_session_model

    session_model_override_active = session_model_override is not None
    resolved_model = session_model_override or settings.openai_model
    resolved_model_source = (
        "session_state_ui"
        if session_model_override_active
        else settings.resolved_from.get("OPENAI_MODEL", "unknown")
    )
    resolved_task_models = {
        "extract_job_ad": resolve_model_for_task(
            task_kind=TASK_EXTRACT_JOB_AD,
            session_override=session_model_override,
            settings=settings,
        ),
        "generate_question_plan": resolve_model_for_task(
            task_kind=TASK_GENERATE_QUESTION_PLAN,
            session_override=session_model_override,
            settings=settings,
        ),
        "generate_vacancy_brief": resolve_model_for_task(
            task_kind=TASK_GENERATE_VACANCY_BRIEF,
            session_override=session_model_override,
            settings=settings,
        ),
    }

    with st.expander("Debug: OpenAI-Auflösung", expanded=False):
        st.caption("Nur aufgelöste Laufzeitwerte, keine Secrets.")
        st.caption("Resolved runtime values only, no secrets.")
        debug_payload: dict[str, object] = {
            "resolved_model": resolved_model,
            "resolved_model_source": resolved_model_source,
            "resolved_default_model": settings.default_model,
            "resolved_default_model_source": settings.resolved_from.get(
                "DEFAULT_MODEL", "unknown"
            ),
            "resolved_reasoning_effort": settings.reasoning_effort,
            "resolved_reasoning_effort_source": settings.resolved_from.get(
                "REASONING_EFFORT", "unknown"
            ),
            "resolved_verbosity": settings.verbosity,
            "resolved_verbosity_source": settings.resolved_from.get(
                "VERBOSITY", "unknown"
            ),
            "resolved_timeout": settings.openai_request_timeout,
            "resolved_timeout_source": settings.resolved_from.get(
                "OPENAI_REQUEST_TIMEOUT", "unknown"
            ),
            "session_model_override_active": session_model_override_active,
            "resolved_task_models": resolved_task_models,
        }
        if session_model_override_active and session_model_override is not None:
            debug_payload["session_model_override_value"] = session_model_override
        structured_output_path = st.session_state.get(
            SSKey.OPENAI_LAST_STRUCTURED_OUTPUT_PATH.value
        )
        if isinstance(structured_output_path, dict):
            debug_payload["structured_output_final_path"] = structured_output_path
        st.json(debug_payload, expanded=False)


def _render_preference_center_sidebar(
    *, key_prefix: str = "sidebar", show_reset_button: bool = True
) -> None:
    raw_preferences = st.session_state.get(SSKey.UI_PREFERENCES.value)
    preferences = normalize_ui_preferences(raw_preferences)
    st.session_state[SSKey.UI_PREFERENCES.value] = preferences

    answer_mode_options = ["compact", "balanced", "advisory"]
    current_ui_mode = normalize_ui_mode(st.session_state.get(SSKey.UI_MODE.value))
    answer_mode = map_ui_mode_to_answer_mode(current_ui_mode)
    st.selectbox(
        "Antwortmodus",
        options=answer_mode_options,
        index=answer_mode_options.index(answer_mode),
        key=f"{key_prefix}.answer_mode",
        disabled=True,
        help=(
            "Wird aus dem kanonischen Laufzeitmodus synchronisiert "
            "(Detailgrad-Auswahl im Wizard)."
        ),
    )
    information_depth_options = ["niedrig", "standard", "hoch"]
    information_depth_value = str(
        preferences.get(UI_PREFERENCE_INFORMATION_DEPTH, "standard")
    )
    if information_depth_value not in information_depth_options:
        information_depth_value = "standard"
    information_depth = st.selectbox(
        "Informationstiefe",
        options=information_depth_options,
        index=information_depth_options.index(information_depth_value),
        key=f"{key_prefix}.information_depth",
    )
    strictness_options = ["locker", "ausgewogen", "streng"]
    strictness_value = str(
        preferences.get(UI_PREFERENCE_ESCO_MATCHING_STRICTNESS, "ausgewogen")
    )
    if strictness_value not in strictness_options:
        strictness_value = "ausgewogen"
    esco_matching_strictness = st.selectbox(
        "ESCO-Matching-Strenge",
        options=strictness_options,
        index=strictness_options.index(strictness_value),
        key=f"{key_prefix}.esco_matching_strictness",
        help="Vorbereitetes Steuerfeld: End-to-end verdrahtet, finale Wirkung wird schrittweise ausgebaut.",
    )
    regional_focus = st.text_input(
        "Regionaler Fokus",
        value=str(preferences.get(UI_PREFERENCE_REGIONAL_FOCUS, "DACH")),
        key=f"{key_prefix}.regional_focus",
    )
    confidence_threshold = st.slider(
        "Confidence-Schwelle für Treffer",
        min_value=0.05,
        max_value=0.95,
        value=float(preferences.get(UI_PREFERENCE_CONFIDENCE_THRESHOLD, 0.6)),
        step=0.05,
        help="Vorbereitete globale Schwelle für Match-/Trefferdarstellung.",
        key=f"{key_prefix}.confidence_threshold",
    )
    pii_reduction = st.toggle(
        "PII-Reduktion",
        value=bool(preferences.get(UI_PREFERENCE_PII_REDUCTION, False)),
        help="Reduziert sensible personenbezogene Angaben in der Verarbeitung, wo möglich.",
        key=f"{key_prefix}.pii_reduction",
    )

    preferences.update(
        {
            UI_PREFERENCE_ANSWER_MODE: answer_mode,
            UI_PREFERENCE_INFORMATION_DEPTH: information_depth,
            UI_PREFERENCE_ESCO_MATCHING_STRICTNESS: esco_matching_strictness,
            UI_PREFERENCE_REGIONAL_FOCUS: regional_focus.strip() or "DACH",
            UI_PREFERENCE_CONFIDENCE_THRESHOLD: confidence_threshold,
            UI_PREFERENCE_PII_REDUCTION: pii_reduction,
        }
    )
    st.session_state[SSKey.UI_PREFERENCES.value] = normalize_ui_preferences(preferences)
    st.session_state[SSKey.SOURCE_REDACT_PII.value] = pii_reduction
    st.markdown("[⚙️ Präferenz-Center (volle Ansicht)](?page=preferences)")
    if show_reset_button:
        st.button("Reset Vacancy", on_click=reset_vacancy, key=f"{key_prefix}.reset")


def _render_preferences_page() -> None:
    st.title("Präferenz-Center")
    st.caption("Globale Einstellungen gelten wizard-weit.")
    _render_preference_center_sidebar(key_prefix="page", show_reset_button=False)
    with st.expander("Advanced / Bestehende Detail-Einstellungen", expanded=False):
        raw_preferences = st.session_state.get(SSKey.UI_PREFERENCES.value)
        preferences = normalize_ui_preferences(raw_preferences)
        preferences["details_expanded_default"] = st.toggle(
            "Details standardmäßig öffnen",
            value=bool(preferences.get("details_expanded_default", False)),
        )
        st.session_state[SSKey.UI_PREFERENCES.value] = normalize_ui_preferences(
            preferences
        )
    if st.button("← Zurück zum Wizard", key="back.preferences"):
        st.query_params.clear()
        st.rerun()


def _render_sidebar_actions() -> None:
    """Render non-wizard global sidebar controls."""
    with st.sidebar:
        st.caption("Globale Steuerung für den aktuellen Wizard-Kontext.")
        with st.expander("Präferenz-Center", expanded=False):
            _render_preference_center_sidebar()


def _reset_scroll_on_step_change() -> None:
    """Reset scroll position on step changes using native Streamlit HTML rendering."""
    if not hasattr(st, "html"):
        return
    st.html(
        """
        <script>
        const topOptions = { top: 0, behavior: "auto" };
        const scrollTop = () => {
            try {
                if (window.parent && typeof window.parent.scrollTo === "function") {
                    window.parent.scrollTo(topOptions);
                } else if (typeof window.scrollTo === "function") {
                    window.scrollTo(topOptions);
                }
            } catch (error) {
                if (typeof window.scrollTo === "function") {
                    window.scrollTo(topOptions);
                }
            }
        };
        scrollTop();
        if (typeof window.requestAnimationFrame === "function") {
            window.requestAnimationFrame(scrollTop);
        }
        window.setTimeout(scrollTop, 0);
        </script>
        """
    )


def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        layout="wide",
        initial_sidebar_state="auto",
    )
    _inject_theme_styles()

    init_session_state()
    previous_step = st.session_state.get(SSKey.LAST_RENDERED_STEP.value)

    pages = load_pages()
    ctx = WizardContext(pages=pages)
    _render_public_page_links_sidebar()

    page_param = st.query_params.get("page")
    if isinstance(page_param, list):
        page_param = page_param[0] if page_param else None
    if page_param == "preferences":
        sidebar_navigation(ctx)
        _render_preferences_page()
        _render_sidebar_actions()
        st.session_state[SSKey.LAST_RENDERED_STEP.value] = None
        return

    current = sidebar_navigation(ctx)
    step_changed = bool(previous_step and previous_step != current.key)
    if step_changed:
        _reset_scroll_on_step_change()

    current.render(ctx)
    _render_sidebar_actions()
    st.session_state[SSKey.LAST_RENDERED_STEP.value] = current.key


if __name__ == "__main__":
    main()
