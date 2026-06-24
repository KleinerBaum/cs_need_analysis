# app.py

from __future__ import annotations

import base64
import json
from collections.abc import Mapping
from datetime import datetime, timezone
from pathlib import Path

import streamlit as st

from components.design_system import render_ui_styles
from config.preferences import (
    PREFERENCE_CENTER_QUERY_PARAM,
    PREFERENCE_CENTER_QUERY_VALUE,
)
from constants import (
    APP_TITLE,
    SSKey,
    UI_PREFERENCE_ANSWER_MODE,
    UI_PREFERENCE_CONFIDENCE_THRESHOLD,
    UI_PREFERENCE_ESCO_MATCHING_STRICTNESS,
    UI_PREFERENCE_INFORMATION_DEPTH,
    UI_PREFERENCE_PII_REDUCTION,
    UI_PREFERENCE_REGIONAL_FOCUS,
    UI_PREFERENCE_WIZARD_DESIGN,
    UI_WIZARD_DESIGN_DEFAULT,
    UI_WIZARD_DESIGN_DISPLAY_LABELS,
    UI_WIZARD_DESIGN_VALUES,
    WIZARD_STEP_QUERY_PARAM,
)
from i18n import (
    patch_streamlit_text,
    render_language_persistence_bridge,
    sync_language_from_known_widgets,
    sync_language_state_from_request,
)
from llm_client import (
    TASK_EXTRACT_JOB_AD,
    TASK_GENERATE_QUESTION_PLAN,
    TASK_GENERATE_VACANCY_BRIEF,
    resolve_model_for_task,
)
from safe_html import render_static_html
from settings_openai import load_openai_settings
from state import (
    build_vacancy_draft_fingerprint,
    build_vacancy_draft_json,
    init_session_state,
    load_vacancy_draft_json,
    normalize_ui_preferences,
    reset_vacancy,
)
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
DRAFT_BROWSER_RECOVERY_STORAGE_KEY = "cs.vacancyDraft.safeRecovery.v1"


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
    render_static_html(
        f"""
        <style>
            [data-testid="stHeader"] {{
                background: transparent;
            }}

            .stApp {{
                --cs-app-bg: var(--background-color, #F6F8FB);
                --cs-step-background-image: url("{wizard_light_background_uri}");
                --cs-step-background-blend: soft-light;
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
                background-color: var(--cs-app-bg) !important;
                background-image:
                    linear-gradient(
                        180deg,
                        color-mix(in srgb, var(--cs-app-bg) 96%, transparent),
                        color-mix(in srgb, var(--cs-app-bg) 88%, transparent)
                    ),
                    var(--cs-step-background-image) !important;
                background-position: center top !important;
                background-repeat: no-repeat !important;
                background-size: auto, cover !important;
                background-attachment: fixed !important;
                background-blend-mode: normal, var(--cs-step-background-blend);
                color: var(--cs-app-text);
            }}

            .stApp[data-cs-theme="dark"],
            :root[data-cs-theme="dark"] .stApp,
            html[data-cs-theme="dark"] .stApp,
            body[data-cs-theme="dark"] .stApp,
            [data-cs-theme="dark"] .stApp,
            .stApp[data-theme="dark"],
            :root[data-theme="dark"] .stApp,
            html[data-theme="dark"] .stApp,
            body[data-theme="dark"] .stApp,
            [data-theme="dark"] .stApp {{
                --cs-app-bg: var(--background-color, #0B111B);
                --cs-step-background-image: url("{wizard_dark_background_uri}");
                --cs-step-background-blend: screen;
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
                max-width: min(100%, 1180px);
                padding-top: 0.8rem;
                padding-left: clamp(0.9rem, 1.8vw, 1.5rem);
                padding-right: clamp(0.9rem, 1.8vw, 1.5rem);
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
        streamlit_module=st,
    )


def _build_runtime_theme_bridge_html() -> str:
    """Build the iframe script that mirrors Streamlit's runtime theme into DOM."""

    return """
        <script>
        (() => {
            const THEME_ATTR = "data-cs-theme";
            const DARK = "dark";
            const LIGHT = "light";
            const targetWindow = window.parent || window;

            const normalizeTheme = (value) => {
                const normalized = String(value || "").trim().toLowerCase();
                if (normalized === DARK || normalized.includes('"base":"dark"') || normalized.includes('"base": "dark"')) {
                    return DARK;
                }
                if (normalized === LIGHT || normalized.includes('"base":"light"') || normalized.includes('"base": "light"')) {
                    return LIGHT;
                }
                return null;
            };

            const parseColor = (value) => {
                const normalized = String(value || "").trim();
                if (!normalized || normalized === "transparent") {
                    return null;
                }
                const rgbMatch = normalized.match(/rgba?\\(([^)]+)\\)/i);
                if (rgbMatch) {
                    const channels = rgbMatch[1]
                        .split(",")
                        .slice(0, 3)
                        .map((channel) => Number.parseFloat(channel.trim()));
                    if (channels.length === 3 && channels.every(Number.isFinite)) {
                        return channels.map((channel) => Math.max(0, Math.min(255, channel)));
                    }
                }
                const hexMatch = normalized.match(/^#([0-9a-f]{3}|[0-9a-f]{6})$/i);
                if (!hexMatch) {
                    return null;
                }
                let hex = hexMatch[1];
                if (hex.length === 3) {
                    hex = hex.split("").map((char) => char + char).join("");
                }
                return [0, 2, 4].map((offset) => Number.parseInt(hex.slice(offset, offset + 2), 16));
            };

            const luminance = (color) => {
                const channels = parseColor(color);
                if (!channels) {
                    return null;
                }
                const linear = channels.map((channel) => {
                    const value = channel / 255;
                    return value <= 0.03928
                        ? value / 12.92
                        : Math.pow((value + 0.055) / 1.055, 2.4);
                });
                return (0.2126 * linear[0]) + (0.7152 * linear[1]) + (0.0722 * linear[2]);
            };

            const themeFromStorage = () => {
                try {
                    const storage = targetWindow.localStorage;
                    for (let index = 0; index < storage.length; index += 1) {
                        const key = storage.key(index) || "";
                        const value = storage.getItem(key) || "";
                        const keyTheme = normalizeTheme(key);
                        const valueTheme = normalizeTheme(value);
                        const haystack = `${key} ${value}`.toLowerCase();
                        if (!haystack.includes("theme")) {
                            continue;
                        }
                        if (valueTheme) {
                            return valueTheme;
                        }
                        if (keyTheme) {
                            return keyTheme;
                        }
                        const hasDark = haystack.includes("dark");
                        const hasLight = haystack.includes("light");
                        if (hasDark !== hasLight) {
                            return hasDark ? DARK : LIGHT;
                        }
                    }
                } catch (error) {
                    return null;
                }
                return null;
            };

            const themeFromDom = (doc) => {
                const nodes = [
                    doc.documentElement,
                    doc.body,
                    doc.querySelector(".stApp"),
                    doc.querySelector("[data-testid='stAppViewContainer']"),
                ].filter(Boolean);
                for (const node of nodes) {
                    const explicitTheme = normalizeTheme(node.getAttribute("data-theme"));
                    if (explicitTheme) {
                        return explicitTheme;
                    }
                }
                return null;
            };

            const themeFromToolbar = (doc) => {
                const selectedControls = Array.from(
                    doc.querySelectorAll(
                        '[aria-checked="true"], [aria-selected="true"], [data-selected="true"]'
                    )
                );
                for (const control of selectedControls) {
                    const label = `${control.textContent || ""} ${control.getAttribute("aria-label") || ""}`.toLowerCase();
                    if (label.includes("dark")) {
                        return DARK;
                    }
                    if (label.includes("light")) {
                        return LIGHT;
                    }
                }
                return null;
            };

            const themeFromComputedStyle = (doc) => {
                const nodes = [
                    doc.documentElement,
                    doc.body,
                    doc.querySelector("[data-testid='stAppViewContainer']"),
                    doc.querySelector(".stApp"),
                ].filter(Boolean);
                for (const node of nodes) {
                    const style = targetWindow.getComputedStyle(node);
                    const colorScheme = String(style.colorScheme || "").toLowerCase();
                    if (colorScheme.split(" ").includes(DARK)) {
                        return DARK;
                    }
                    const bg = style.getPropertyValue("--background-color") || style.backgroundColor;
                    const text = style.getPropertyValue("--text-color") || style.color;
                    const bgLuminance = luminance(bg);
                    const textLuminance = luminance(text);
                    if (bgLuminance === null || textLuminance === null) {
                        continue;
                    }
                    if (bgLuminance < 0.35 && textLuminance > 0.55) {
                        return DARK;
                    }
                    if (bgLuminance > 0.55 && textLuminance < 0.45) {
                        return LIGHT;
                    }
                }
                return null;
            };

            const resolveTheme = (doc) => (
                themeFromDom(doc)
                || themeFromToolbar(doc)
                || themeFromStorage()
                || themeFromComputedStyle(doc)
                || LIGHT
            );

            const applyTheme = () => {
                try {
                    const doc = targetWindow.document || document;
                    const theme = resolveTheme(doc);
                    doc.documentElement.setAttribute(THEME_ATTR, theme);
                    if (doc.body) {
                        doc.body.setAttribute(THEME_ATTR, theme);
                    }
                    doc.querySelectorAll(".stApp").forEach((node) => {
                        node.setAttribute(THEME_ATTR, theme);
                    });
                } catch (error) {
                    return;
                }
            };

            applyTheme();
            try {
                const doc = targetWindow.document || document;
                const observer = new MutationObserver(applyTheme);
                observer.observe(doc.documentElement, {
                    attributes: true,
                    attributeFilter: ["data-theme", "aria-checked", "aria-selected", "data-selected", "class", "style"],
                    childList: true,
                    subtree: true,
                });
                targetWindow.addEventListener("storage", applyTheme);
                targetWindow.setTimeout(applyTheme, 50);
                targetWindow.setTimeout(applyTheme, 250);
                targetWindow.setTimeout(applyTheme, 1000);
            } catch (error) {
                return;
            }
        })();
        </script>
    """


def _inject_runtime_theme_bridge() -> None:
    """Mirror Streamlit's runtime theme into a stable app-shell DOM attribute."""

    st.iframe(
        _build_runtime_theme_bridge_html(),
        height=1,
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

    sync_language_state_from_request(session_state=st.session_state)
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
    wizard_design_value = str(
        preferences.get(UI_PREFERENCE_WIZARD_DESIGN, UI_WIZARD_DESIGN_DEFAULT)
    )
    if wizard_design_value not in UI_WIZARD_DESIGN_VALUES:
        wizard_design_value = UI_WIZARD_DESIGN_DEFAULT
    wizard_design = st.selectbox(
        "Wizard-Design",
        options=list(UI_WIZARD_DESIGN_VALUES),
        index=list(UI_WIZARD_DESIGN_VALUES).index(wizard_design_value),
        format_func=lambda value: UI_WIZARD_DESIGN_DISPLAY_LABELS.get(value, value),
        key=f"{key_prefix}.wizard_design",
        help=(
            "Klassisch behält die bisherige Detaildarstellung. Fokus hält "
            "sekundäre Details geschlossen, bis sie aktiv geöffnet werden."
        ),
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
            UI_PREFERENCE_WIZARD_DESIGN: wizard_design,
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
        render_static_html(
            '<div class="cs-sidebar-nav-gap"></div>',
            streamlit_module=st,
        )


def _vacancy_draft_filename() -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"cognitive-staffing-entwurf-{timestamp}.json"


def _draft_has_meaningful_progress(session_state: Mapping[str, object]) -> bool:
    if str(session_state.get(SSKey.SOURCE_TEXT.value) or "").strip():
        return True
    if str(session_state.get(SSKey.SOURCE_MANUAL_TEXT.value) or "").strip():
        return True
    if str(session_state.get(SSKey.SOURCE_UPLOADED_TEXT.value) or "").strip():
        return True
    if session_state.get(SSKey.JOB_EXTRACT.value):
        return True
    for key in (
        SSKey.ANSWERS,
        SSKey.INTAKE_FACTS,
        SSKey.COMPANY_WEBSITE_RESEARCH,
        SSKey.ROLE_TASKS_SELECTED,
        SSKey.SKILLS_SELECTED,
        SSKey.BENEFITS_SELECTED,
    ):
        if bool(session_state.get(key.value)):
            return True
    for key in (
        SSKey.BRIEF,
        SSKey.JOB_AD_DRAFT_CUSTOM,
        SSKey.INTERVIEW_PREP_HR,
        SSKey.INTERVIEW_PREP_FACH,
        SSKey.BOOLEAN_SEARCH_STRING,
        SSKey.EMPLOYMENT_CONTRACT_DRAFT,
    ):
        if session_state.get(key.value) is not None:
            return True
    return False


def _generated_draft_artifact_count(session_state: Mapping[str, object]) -> int:
    return sum(
        1
        for key in (
            SSKey.BRIEF,
            SSKey.JOB_AD_DRAFT_CUSTOM,
            SSKey.INTERVIEW_PREP_HR,
            SSKey.INTERVIEW_PREP_FACH,
            SSKey.BOOLEAN_SEARCH_STRING,
            SSKey.EMPLOYMENT_CONTRACT_DRAFT,
        )
        if session_state.get(key.value) is not None
    )


def _answer_count(session_state: Mapping[str, object]) -> int:
    answers = session_state.get(SSKey.ANSWERS.value)
    return len(answers) if isinstance(answers, Mapping) else 0


def _mark_current_draft_saved(fingerprint: str) -> None:
    st.session_state[SSKey.DRAFT_LAST_SAVED_FINGERPRINT.value] = str(fingerprint or "")


def _render_draft_controls() -> None:
    current_fingerprint = build_vacancy_draft_fingerprint()
    last_saved_fingerprint = str(
        st.session_state.get(SSKey.DRAFT_LAST_SAVED_FINGERPRINT.value) or ""
    )
    has_progress = _draft_has_meaningful_progress(st.session_state)
    is_saved_current = bool(
        has_progress
        and last_saved_fingerprint
        and last_saved_fingerprint == current_fingerprint
    )
    draft_json = build_vacancy_draft_json()

    with st.sidebar.expander("Entwurf", expanded=False):
        st.caption(
            "Speichert die aktuelle Vacancy als JSON. Enthalten sind nur "
            "notwendige Wizard-Daten; Secrets, Caches, Logs, Debug-Daten und "
            "Logo-Dateien werden nicht exportiert."
        )
        if has_progress and is_saved_current:
            st.success(
                "Der zuletzt gespeicherte Entwurf passt zum aktuellen Stand. "
                "Nach weiteren Änderungen erneut als JSON speichern."
            )
        elif has_progress:
            st.warning(
                "Aktive Änderungen erkannt. `session_state` ist nur Laufzeitstatus; "
                "speichere ein Entwurf-JSON, wenn du nach Unterbrechungen fortsetzen willst."
            )
        else:
            st.caption("Noch kein speicherbarer Vacancy-Stand erkannt.")
        st.download_button(
            "Entwurf speichern",
            data=draft_json,
            file_name=_vacancy_draft_filename(),
            mime="application/json",
            key=SSKey.DRAFT_SAVE_DOWNLOAD_WIDGET.value,
            on_click=_mark_current_draft_saved,
            args=(current_fingerprint,),
        )
        uploaded_draft = st.file_uploader(
            "Entwurf-JSON auswählen",
            type=["json"],
            key=SSKey.DRAFT_LOAD_UPLOAD_WIDGET.value,
        )
        load_clicked = st.button(
            "Entwurf laden",
            disabled=uploaded_draft is None,
            key=SSKey.DRAFT_LOAD_BUTTON_WIDGET.value,
        )
        if load_clicked:
            if uploaded_draft is None:
                st.error(
                    "Bitte im Feld „Entwurf-JSON auswählen“ eine JSON-Datei auswählen."
                )
                return
            result = load_vacancy_draft_json(uploaded_draft.getvalue())
            if not result.success:
                st.error(result.message)
                return
            st.query_params.clear()
            st.rerun()


def _build_draft_recovery_bridge_html(metadata: Mapping[str, object]) -> str:
    encoded_metadata = base64.b64encode(
        json.dumps(metadata, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    ).decode("ascii")
    return f"""
        <script>
        (() => {{
            const STORAGE_KEY = "{DRAFT_BROWSER_RECOVERY_STORAGE_KEY}";
            const metadata = JSON.parse(atob("{encoded_metadata}"));
            const targetWindow = window.parent || window;
            try {{
                if (metadata.hasProgress) {{
                    targetWindow.localStorage.setItem(
                        STORAGE_KEY,
                        JSON.stringify({{
                            schema: "safe-recovery-metadata-v1",
                            storedAt: new Date().toISOString(),
                            ...metadata
                        }})
                    );
                }} else {{
                    targetWindow.localStorage.removeItem(STORAGE_KEY);
                }}
                if (metadata.hasProgress && !metadata.saved) {{
                    targetWindow.addEventListener("beforeunload", (event) => {{
                        event.preventDefault();
                        event.returnValue = "Entwurf zuerst als JSON speichern.";
                        return event.returnValue;
                    }});
                }}
            }} catch (error) {{
                return;
            }}
        }})();
        </script>
    """


def _inject_draft_recovery_bridge(ctx: WizardContext) -> None:
    step_key = str(st.session_state.get(SSKey.CURRENT_STEP.value) or "")
    step_label_by_key = {page.key: page.title_de for page in ctx.pages}
    has_progress = _draft_has_meaningful_progress(st.session_state)
    current_fingerprint = build_vacancy_draft_fingerprint()
    saved_fingerprint = str(
        st.session_state.get(SSKey.DRAFT_LAST_SAVED_FINGERPRINT.value) or ""
    )
    metadata = {
        "hasProgress": has_progress,
        "saved": bool(has_progress and saved_fingerprint == current_fingerprint),
        "stepKey": step_key,
        "stepLabel": step_label_by_key.get(step_key, ""),
        "hasAnalysis": bool(st.session_state.get(SSKey.JOB_EXTRACT.value)),
        "answerCount": _answer_count(st.session_state),
        "artifactCount": _generated_draft_artifact_count(st.session_state),
    }
    st.iframe(_build_draft_recovery_bridge_html(metadata), height=1)


def _dismiss_resume_notice() -> None:
    st.session_state[SSKey.DRAFT_RESUME_NOTICE.value] = None


def _render_resume_banner(ctx: WizardContext) -> None:
    notice = st.session_state.get(SSKey.DRAFT_RESUME_NOTICE.value)
    if not isinstance(notice, Mapping):
        return
    restored_step = str(notice.get("restored_step") or "").strip()
    step_label_by_key = {page.key: page.title_de for page in ctx.pages}
    step_label = step_label_by_key.get(restored_step, restored_step or "Wizard")
    saved_at = str(notice.get("saved_at") or "").strip()
    schema_version = str(notice.get("schema_version") or "").strip()
    restored_key_count = notice.get("restored_key_count")

    with st.container(border=True):
        st.success(f"Entwurf geladen. Fortsetzung bei „{step_label}“.")
        details = []
        if saved_at:
            details.append(f"gespeichert: {saved_at}")
        if schema_version:
            details.append(f"Schema: {schema_version}")
        if isinstance(restored_key_count, int):
            details.append(f"{restored_key_count} State-Felder wiederhergestellt")
        if details:
            st.caption(" · ".join(details))
        st.button(
            "Banner ausblenden",
            key=SSKey.DRAFT_RESUME_DISMISS_WIDGET.value,
            on_click=_dismiss_resume_notice,
        )


def _render_sidebar_footer_links() -> None:
    """Render non-wizard legal sidebar links below contextual controls."""
    with st.sidebar:
        render_static_html(
            '<div class="cs-sidebar-nav-gap"></div>',
            streamlit_module=st,
        )
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
    _inject_runtime_theme_bridge()

    init_session_state()
    patch_streamlit_text()
    _sync_language_before_render()
    render_language_persistence_bridge()
    previous_step = st.session_state.get(SSKey.LAST_RENDERED_STEP.value)

    pages = load_pages()
    ctx = WizardContext(pages=pages)

    page_param = st.query_params.get(PREFERENCE_CENTER_QUERY_PARAM)
    if isinstance(page_param, list):
        page_param = page_param[0] if page_param else None
    if page_param == PREFERENCE_CENTER_QUERY_VALUE:
        _render_sidebar_primary_links()
        _render_draft_controls()
        sidebar_navigation(ctx)
        _render_preferences_page()
        _render_sidebar_footer_links()
        st.session_state[SSKey.LAST_RENDERED_STEP.value] = None
        return

    _consume_wizard_step_query_param(ctx)
    _render_sidebar_primary_links()
    _render_draft_controls()
    current = sidebar_navigation(ctx)
    _inject_draft_recovery_bridge(ctx)
    step_changed = bool(previous_step and previous_step != current.key)

    if step_changed:
        _reset_scroll_on_step_change()
    render_intake_process_progress(current.key)
    _render_resume_banner(ctx)
    current.render(ctx)
    _render_sidebar_footer_links()
    st.session_state[SSKey.LAST_RENDERED_STEP.value] = current.key


if __name__ == "__main__":
    main()
