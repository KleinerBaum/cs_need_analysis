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
    WIZARD_STEP_QUERY_PARAM,
)
from i18n import (
    patch_streamlit_text,
    sync_language_from_known_widgets,
)
from llm_client import (
    TASK_EXTRACT_JOB_AD,
    TASK_GENERATE_QUESTION_PLAN,
    TASK_GENERATE_VACANCY_BRIEF,
    resolve_model_for_task,
)
from settings_openai import load_openai_settings
from state import init_session_state, normalize_ui_preferences, reset_vacancy
from ui_layout import render_intake_process_progress
from wizard_pages import load_pages
from wizard_pages.base import (
    WizardContext,
    map_ui_mode_to_information_depth,
    map_ui_mode_to_answer_mode,
    normalize_ui_mode,
    sidebar_navigation,
)

SIDEBAR_PAGE_LINKS: tuple[tuple[str, str], ...] = (
    ("pages/01_Unsere_Kompetenzen.py", "Unsere Kompetenzen"),
    ("pages/02_Über_Cognitive_Staffing.py", "Über Cognitive Staffing"),
    ("pages/03_Impressum.py", "Impressum"),
    ("pages/13_Cookie_Policy_Settings.py", "Cookie Policy/Settings"),
)
SIDEBAR_PRIMARY_PAGE_LINKS: tuple[tuple[str, str], ...] = SIDEBAR_PAGE_LINKS[:2]
SIDEBAR_FOOTER_PAGE_LINKS: tuple[tuple[str, str], ...] = (
    SIDEBAR_PAGE_LINKS[3],
    SIDEBAR_PAGE_LINKS[2],
)
ROOT_DIR = Path(__file__).resolve().parent
WIZARD_DARK_BACKGROUND_PATH = ROOT_DIR / "images" / "dark2.png"
WIZARD_LIGHT_BACKGROUND_PATH = ROOT_DIR / "images" / "light.png"


def _first_query_param_value(value: object) -> str | None:
    if isinstance(value, list):
        value = value[0] if value else None
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _drop_query_param(name: str) -> None:
    try:
        del st.query_params[name]
    except KeyError:
        return


def _consume_wizard_step_query_param(ctx: WizardContext) -> None:
    target_step = _first_query_param_value(
        st.query_params.get(WIZARD_STEP_QUERY_PARAM)
    )
    if target_step is None:
        return

    valid_step_keys = {page.key for page in ctx.pages}
    if target_step in valid_step_keys:
        ctx.goto(target_step)
    _drop_query_param(WIZARD_STEP_QUERY_PARAM)


def _image_data_uri(path: Path) -> str:
    encoded = base64.b64encode(path.read_bytes()).decode("ascii")
    return f"data:image/png;base64,{encoded}"


def _inject_theme_styles() -> None:
    """Inject global design-system styles plus minimal app-shell overrides."""

    render_ui_styles()
    wizard_dark_background_uri = _image_data_uri(WIZARD_DARK_BACKGROUND_PATH)
    wizard_light_background_uri = _image_data_uri(WIZARD_LIGHT_BACKGROUND_PATH)

    # App-shell specific styles (header/sidebar spacing/layout quirks).
    st.markdown(
        f"""
        <style>
            [data-testid="stHeader"] {{
                background: transparent;
            }}

            .stApp {{
                --cs-app-bg: var(--background-color, #F6F8FB);
                --cs-step-background-image: url("{wizard_light_background_uri}");
                --cs-app-text: var(--text-color, #142033);
                --cs-app-surface: var(
                    --secondary-background-color,
                    #FFFFFF
                );
                --cs-app-border: var(
                    --border-color,
                    #CAD6E2
                );
                --cs-bg: var(--cs-app-bg);
                --cs-surface: var(--cs-app-surface);
                --cs-surface-raised: color-mix(
                    in srgb,
                    var(--cs-app-surface) 94%,
                    #ffffff 6%
                );
                --cs-surface-muted: color-mix(
                    in srgb,
                    var(--cs-app-surface) 82%,
                    var(--cs-app-bg) 18%
                );
                --cs-border: var(--cs-app-border);
                --cs-border-soft: color-mix(in srgb, var(--cs-app-border) 72%, transparent);
                --cs-text: var(--cs-app-text);
                --cs-text-muted: color-mix(in srgb, var(--cs-app-text) 76%, var(--cs-app-bg));
                --cs-text-subtle: color-mix(in srgb, var(--cs-app-text) 60%, var(--cs-app-bg));
                background: var(--cs-app-bg) !important;
                background-image: var(--cs-step-background-image) !important;
                background-position: center top !important;
                background-repeat: no-repeat !important;
                background-size: cover !important;
                background-attachment: fixed !important;
                color: var(--cs-app-text);
            }}

            .stApp[data-theme="dark"],
            :root[data-theme="dark"] .stApp,
            html[data-theme="dark"] .stApp,
            body[data-theme="dark"] .stApp,
            [data-theme="dark"] .stApp {{
                --cs-app-bg: var(--background-color, #0B111B);
                --cs-step-background-image: url("{wizard_dark_background_uri}");
                --cs-app-text: var(--text-color, #F1F5F9);
                --cs-app-surface: var(
                    --secondary-background-color,
                    #111827
                );
                --cs-app-border: var(
                    --border-color,
                    #334155
                );
            }}

            [data-testid="stAppViewContainer"],
            .stMain {{
                background: transparent !important;
                color: var(--cs-text);
            }}

            .stMainBlockContainer,
            .block-container {{
                background: transparent !important;
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

                [data-testid="stHorizontalBlock"] {{
                    flex-wrap: wrap;
                    gap: 0.75rem;
                }}

                [data-testid="stHorizontalBlock"] > div[data-testid="column"] {{
                    flex: 1 1 100% !important;
                    min-width: min(100%, 18rem) !important;
                }}

                [data-testid="stTabs"] [role="tablist"] {{
                    overflow-x: auto;
                    justify-content: flex-start;
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


def _sync_language_before_render() -> None:
    """Apply language widget changes before any routed page renders."""

    sync_language_from_known_widgets(session_state=st.session_state)


def _render_preference_center_sidebar(
    *, key_prefix: str = "sidebar", show_reset_button: bool = True
) -> None:
    raw_preferences = st.session_state.get(SSKey.UI_PREFERENCES.value)
    preferences = normalize_ui_preferences(raw_preferences)
    st.session_state[SSKey.UI_PREFERENCES.value] = preferences

    current_ui_mode = normalize_ui_mode(st.session_state.get(SSKey.UI_MODE.value))
    answer_mode = map_ui_mode_to_answer_mode(current_ui_mode)
    information_depth = map_ui_mode_to_information_depth(current_ui_mode)
    preferences.update(
        {
            UI_PREFERENCE_ANSWER_MODE: answer_mode,
            UI_PREFERENCE_INFORMATION_DEPTH: information_depth,
        }
    )
    st.session_state[SSKey.UI_PREFERENCES.value] = normalize_ui_preferences(preferences)
    st.markdown(
        "Detailgrad, Antwortmodus und Informationstiefe werden im Start-Schritt "
        "über eine gemeinsame Auswahl gesteuert."
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
        value=bool(preferences.get(UI_PREFERENCE_PII_REDUCTION, True)),
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


def _render_sidebar_primary_links() -> None:
    """Render prominent sidebar links above the wizard navigation."""
    with st.sidebar:
        for page_path, label in SIDEBAR_PRIMARY_PAGE_LINKS:
            st.page_link(page_path, label=label)
        st.markdown('<div class="cs-sidebar-nav-gap"></div>', unsafe_allow_html=True)


def _render_sidebar_footer_links() -> None:
    """Render non-wizard legal sidebar links below contextual controls."""
    with st.sidebar:
        st.markdown('<div class="cs-sidebar-nav-gap"></div>', unsafe_allow_html=True)
        for page_path, label in SIDEBAR_FOOTER_PAGE_LINKS:
            st.page_link(page_path, label=label)


def _reset_scroll_on_step_change() -> None:
    """Reset scroll position on step changes."""
    scroll_reset_html = """
        <script>
        const topOptions = { top: 0, left: 0, behavior: "auto" };
        const scrollElement = (element) => {
            if (!element) {
                return;
            }
            if (typeof element.scrollTo === "function") {
                element.scrollTo(topOptions);
            }
            element.scrollTop = 0;
        };
        const scrollTop = () => {
            const targetWindow = window.parent || window;
            try {
                if (typeof targetWindow.scrollTo === "function") {
                    targetWindow.scrollTo(topOptions);
                }
            } catch (error) {
                if (typeof window.scrollTo === "function") {
                    window.scrollTo(topOptions);
                }
            }
            try {
                const doc = targetWindow.document || document;
                scrollElement(doc.scrollingElement);
                scrollElement(doc.documentElement);
                scrollElement(doc.body);
                doc
                    .querySelectorAll(
                        '[data-testid="stAppViewContainer"], [data-testid="stMain"], section.main'
                    )
                    .forEach(scrollElement);
            } catch (error) {
                scrollElement(document.scrollingElement);
                scrollElement(document.documentElement);
                scrollElement(document.body);
            }
        };
        scrollTop();
        if (typeof window.requestAnimationFrame === "function") {
            window.requestAnimationFrame(scrollTop);
        }
        window.setTimeout(scrollTop, 0);
        window.setTimeout(scrollTop, 50);
        window.setTimeout(scrollTop, 150);
        window.setTimeout(scrollTop, 300);
        window.setTimeout(scrollTop, 600);
        </script>
    """
    encoded_html = base64.b64encode(scroll_reset_html.encode("utf-8")).decode("ascii")
    st.iframe(
        f"data:text/html;base64,{encoded_html}",
        height=1,
    )


def main() -> None:
    st.set_page_config(
        page_title=APP_TITLE,
        layout="wide",
        initial_sidebar_state="auto",
    )
    _inject_theme_styles()

    init_session_state()
    patch_streamlit_text()
    _sync_language_before_render()
    previous_step = st.session_state.get(SSKey.LAST_RENDERED_STEP.value)

    pages = load_pages()
    ctx = WizardContext(pages=pages)

    page_param = st.query_params.get("page")
    if isinstance(page_param, list):
        page_param = page_param[0] if page_param else None
    if page_param == "preferences":
        _render_sidebar_primary_links()
        sidebar_navigation(ctx)
        _render_preferences_page()
        _render_sidebar_footer_links()
        st.session_state[SSKey.LAST_RENDERED_STEP.value] = None
        return

    _consume_wizard_step_query_param(ctx)
    _render_sidebar_primary_links()
    current = sidebar_navigation(ctx)
    step_changed = bool(previous_step and previous_step != current.key)

    if step_changed:
        _reset_scroll_on_step_change()
    render_intake_process_progress(current.key)
    current.render(ctx)
    _render_sidebar_footer_links()
    st.session_state[SSKey.LAST_RENDERED_STEP.value] = current.key


if __name__ == "__main__":
    main()
