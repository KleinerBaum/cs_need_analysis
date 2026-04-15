# app.py

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

from constants import (
    APP_TITLE,
    SSKey,
    UI_PREFERENCE_ANSWER_MODE,
    UI_PREFERENCE_CONFIDENCE_THRESHOLD,
    UI_PREFERENCE_ESCO_MATCHING_STRICTNESS,
    UI_PREFERENCE_INFORMATION_DEPTH,
    UI_PREFERENCE_PII_REDUCTION,
    UI_PREFERENCE_REGIONAL_FOCUS,
    UI_PREFERENCE_SHOW_SOURCES_DEFAULT,
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
    set_current_step,
    sidebar_navigation,
)


def _image_as_data_uri(image_path: Path, mime_type: str) -> str:
    image_bytes = image_path.read_bytes()
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def _inject_theme_styles() -> None:
    root_dir = Path(__file__).resolve().parent
    logo_path = root_dir / "images" / "animation_pulse_SingleColorHex1_7kigl22lw.gif"
    bg_path = root_dir / "images" / "AdobeStock_506577005.jpeg"

    logo_uri = _image_as_data_uri(logo_path, "image/gif")
    bg_uri = _image_as_data_uri(bg_path, "image/jpeg")

    st.markdown(
        f"""
        <style>
            .stApp {{
                background: #0A0A0A url("{bg_uri}") center center / cover no-repeat fixed;
                color: #F5F5F5;
            }}

            [data-testid="stHeader"] {{
                background: transparent;
            }}

            [data-testid="stSidebar"] {{
                background: #050505;
                border-right: 1px solid #232323;
            }}

            [data-testid="stSidebarContent"]::before {{
                content: "";
                display: block;
                width: 220px;
                height: 64px;
                margin: 0 auto 0.75rem auto;
                background: url("{logo_uri}") center / contain no-repeat;
            }}

            [data-testid="stMarkdownContainer"] p,
            [data-testid="stMarkdownContainer"] li,
            [data-testid="stMarkdownContainer"] span,
            h1, h2, h3, h4, h5, h6,
            label {{
                color: #F5F5F5 !important;
            }}

            [data-testid="stAlert"] {{
                background: #121212;
                border: 1px solid #232323;
                color: #F5F5F5;
            }}

            [data-testid="stForm"],
            [data-testid="stExpander"] details,
            [data-testid="stVerticalBlockBorderWrapper"] {{
                background: #121212;
                border: 1px solid #232323;
                border-radius: 14px;
            }}
            .block-container {{
                max-width: 960px;
                padding-top: 1rem;
            }}
            [data-testid="stSidebarContent"] [data-testid="stVerticalBlock"] > div {{
                row-gap: 8px;
            }}
            .cs-sidebar-link-list {{
                display: flex;
                flex-direction: column;
                gap: 8px;
                margin: 2px 0 0 0;
            }}
            .cs-sidebar-link-list a {{
                color: #F5F5F5;
                text-decoration: none;
            }}
            .cs-sidebar-link-list a:hover {{
                color: #B8B8B8;
                text-decoration: underline;
            }}
            .cs-sidebar-nav-gap {{
                height: 22px;
            }}

            .stButton > button {{
                background-color: #1565c0;
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }}

            .stButton > button:hover {{
                background-color: #0d47a1;
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.35);
            }}

            .stDownloadButton > button {{
                background-color: #1e7f5e;
                color: #ffffff;
                border: 1px solid rgba(255, 255, 255, 0.2);
            }}

            .stTextInput input,
            .stTextArea textarea,
            .stSelectbox [data-baseweb="select"] > div,
            .stMultiSelect [data-baseweb="select"] > div {{
                background-color: rgba(255, 255, 255, 0.96);
                color: #10213f;
            }}

            /* Improve readability for preview-only textareas (e.g. upload excerpt). */
            .stTextArea textarea:disabled {{
                background:
                    linear-gradient(
                        140deg,
                        rgba(17, 44, 82, 0.88),
                        rgba(12, 32, 64, 0.92)
                    ) !important;
                color: #eaf2ff !important;
                border: 1px solid rgba(126, 173, 255, 0.45) !important;
                box-shadow: inset 0 0 0 1px rgba(255, 255, 255, 0.06);
                -webkit-text-fill-color: #eaf2ff !important;
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


def _get_info_page_key() -> str | None:
    query_params = st.query_params
    info_param = query_params.get("info")
    if isinstance(info_param, list):
        info_param = info_param[0] if info_param else None
    if isinstance(info_param, str) and info_param in {
        "competencies",
        "about",
        "imprint",
        "cookie",
        "accessibility",
        "contact",
    }:
        return info_param
    return None


def _render_info_page_sidebar_navigation(ctx: WizardContext) -> None:
    current_step = st.session_state.get(SSKey.CURRENT_STEP.value, ctx.pages[0].key)
    wizard_keys = [page.key for page in ctx.pages]
    current_index = (
        wizard_keys.index(current_step) if current_step in wizard_keys else 0
    )

    selected_label = st.sidebar.radio(
        "Prozess",
        options=[page.label for page in ctx.pages],
        index=current_index,
        key="info_page.wizard_nav",
    )

    selected_page = next(page for page in ctx.pages if page.label == selected_label)
    if selected_page.key != current_step:
        set_current_step(selected_page.key)
        st.query_params.clear()
        st.rerun()


def _render_info_page(info_page_key: str) -> None:
    if info_page_key == "competencies":
        st.title("Unsere Kompetenzen")
        st.markdown(
            """
            Wir kombinieren strukturierte Intake-Prozesse, ESCO-gestützte Normalisierung,
            modellgestützte Vorschläge und nachvollziehbare Export-Artefakte für Recruiting.
            """
        )
    elif info_page_key == "about":
        st.title("Über Cognitive Staffing")
        st.markdown(
            """
            Diese App führt dich strukturiert durch die Erstellung eines Vacancy Briefs – von
            den Basisdaten bis zur konsistenten Zusammenfassung für Recruiting und Hiring.
            """
        )
        col_expert, col_guided = st.columns(2)
        with col_expert:
            show_expert_view = st.checkbox(
                "Für fachlich-technische Einordnung",
                key="about_view_technical_expert",
            )
        with col_guided:
            show_guided_view = st.checkbox(
                "Für praxisnahe, allgemeinverständliche Einordnung",
                key="about_view_general_user",
            )

        if show_expert_view and show_guided_view:
            st.info(
                "Bitte wähle eine Perspektive aus, damit die Inhalte gezielt angezeigt werden."
            )
        elif show_expert_view:
            st.markdown(
                """
            ### Gehen wir ins Detail
            - **Wizard-Architektur mit Session-State:** Jeder Schritt schreibt in klar benannte
              Session-Keys; so bleiben Eingaben und Ableitungen reproduzierbar.
            - **Validierte Datenmodelle:** Eingaben und LLM-Antworten werden über Schema-/Model-
              Validierung abgesichert, damit Folgeschritte mit stabilen Daten arbeiten.
            - **Strukturierte LLM-Nutzung:** Die App nutzt strukturierte Outputs für Funktionen wie
              Job-Ad-Extraktion, Aufgaben-Planung und Brief-Generierung.
            - **Deterministische Fallbacks:** Bei fehlenden Keys/Antworten bleibt der Flow nutzbar
              und zeigt sichere, nachvollziehbare Hinweise statt „stiller“ Fehler.
            - **API-gestützte Erweiterbarkeit:** Externe Datenquellen (z. B. ESCO) werden als
              Ergänzung in den Wizard eingebunden, um Begriffe zu normalisieren und Vorschläge
              zu verbessern.
                """
            )
        elif show_guided_view:
            st.markdown(
                """
            ### Kurz und klar
            - **Schritt-für-Schritt-Assistent:** Du beantwortest nacheinander verständliche Fragen.
            - **Weniger Tipparbeit:** Die App schlägt Inhalte vor, die du übernehmen oder anpassen kannst.
            - **Mehr Konsistenz:** Angaben aus frühen Schritten werden später wiederverwendet, damit
              am Ende ein stimmiges Gesamtbild entsteht.
            - **Klare Zusammenfassung:** Im letzten Schritt siehst du alle wichtigen Punkte gebündelt
              und kannst sie direkt für weitere Prozesse verwenden.
            - **Sicherer Umgang mit Daten:** Die App ist darauf ausgelegt, sensible Informationen nicht
              unnötig anzuzeigen oder in Debug-Ansichten offenzulegen.
                """
            )
    elif info_page_key == "imprint":
        st.title("Impressum")
        st.info("Inhaltliche Pflege erfolgt organisationseitig.")
    elif info_page_key == "cookie":
        st.title("Cookie Policy/Settings")
        st.info(
            "Vorbereitetes Informationsmodul: Cookie-Präferenzen folgen in einem separaten Release."
        )
    elif info_page_key == "accessibility":
        st.title("Erklärung zur Barrierefreiheit")
        st.info(
            "Vorbereitete Seite: Barrierefreiheits-Statement wird zentral gepflegt."
        )
    elif info_page_key == "contact":
        st.title("Kontakt")
        st.info("Kontaktinformationen werden zentral bereitgestellt.")

    if st.button("← Zurück zum Wizard", key=f"back.info.{info_page_key}"):
        st.query_params.clear()
        st.rerun()


def _get_legal_page_key() -> str | None:
    query_params = st.query_params
    legal_param = query_params.get("legal")
    if isinstance(legal_param, list):
        legal_param = legal_param[0] if legal_param else None
    if isinstance(legal_param, str) and legal_param in {"terms", "privacy"}:
        return legal_param
    return None


def _render_legal_page(legal_page_key: str) -> None:
    if legal_page_key == "terms":
        st.title("Nutzungsbedingungen")
        st.markdown(
            """
            ### EN
            By using this application, you agree to use it only for lawful business purposes.
            You are responsible for all data you provide and for checking generated results
            before operational use. This tool is provided “as is”, without warranties of
            merchantability, fitness for a particular purpose, or uninterrupted availability.

            **Content Sharing Agreement (OpenAI):**
            If your organization enables designated content sharing with OpenAI, designated
            content may be used by OpenAI for service improvement and model development
            (including training, evaluation, and testing). You confirm that your organization
            has all required rights and that End Users were informed and, where required,
            consent was obtained before data is shared for these purposes.

            You and your End Users must not submit:
            - sensitive/confidential/proprietary information that must not be used for development,
            - HIPAA Protected Health Information (PHI),
            - personal data of children under 13 (or below the local digital consent age).

            ### DE
            Mit der Nutzung dieser Anwendung stimmen Sie zu, sie ausschließlich für rechtmäßige
            geschäftliche Zwecke zu verwenden. Sie sind für alle eingegebenen Daten verantwortlich
            und müssen generierte Ergebnisse vor dem produktiven Einsatz prüfen. Das Tool wird
            „wie besehen“ bereitgestellt, ohne Gewähr für Marktgängigkeit, Eignung für einen
            bestimmten Zweck oder unterbrechungsfreie Verfügbarkeit.

            **Content Sharing Agreement (OpenAI):**
            Falls Ihre Organisation die Freigabe von Designated Content an OpenAI aktiviert,
            kann dieser zur Verbesserung der Services und zur Modellentwicklung (u. a. Training,
            Evaluierung und Tests) verwendet werden. Sie bestätigen, dass Ihre Organisation über
            alle erforderlichen Rechte verfügt und Endnutzende informiert wurden und – sofern
            erforderlich – eine Einwilligung eingeholt wurde.

            Sie und Ihre Endnutzenden dürfen insbesondere **nicht** übermitteln:
            - sensible/vertrauliche/proprietäre Informationen, die nicht für Entwicklungszwecke genutzt werden sollen,
            - HIPAA-geschützte Gesundheitsdaten (PHI),
            - personenbezogene Daten von Kindern unter 13 Jahren (bzw. unter dem lokal geltenden Mindestalter).
            """
        )
    elif legal_page_key == "privacy":
        st.title("Datenschutzerklärung")
        st.markdown(
            """
            ### EN
            This app processes user-provided content to generate hiring-related outputs.
            Do not enter sensitive personal data unless you are authorized to process it.
            Access credentials are loaded from secure environment variables or secrets and
            should never be exposed in logs.

            If content sharing for development purposes is enabled by your organization owner,
            designated content may be processed by OpenAI as an independent Data Controller for
            model and service improvement. The organization is responsible for end-user notice
            and consent collection where required.

            ### DE
            Diese App verarbeitet von Nutzenden bereitgestellte Inhalte, um Recruiting-bezogene
            Ausgaben zu erzeugen. Geben Sie keine sensiblen personenbezogenen Daten ein, sofern
            dafür keine Berechtigung vorliegt. Zugangsdaten werden aus sicheren Umgebungsvariablen
            oder Secrets geladen und dürfen niemals in Logs erscheinen.

            Falls Content Sharing für Entwicklungszwecke durch den Organisations-Owner aktiviert
            ist, kann Designated Content durch OpenAI als eigenständiger Data Controller zur
            Modell- und Serviceverbesserung verarbeitet werden. Die Organisation ist für
            Endnutzerhinweise und ggf. erforderliche Einwilligungen verantwortlich.
            """
        )

    if st.button("← Zurück zum Wizard", key=f"back.legal.{legal_page_key}"):
        st.query_params.clear()
        st.rerun()


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
    show_sources_default = st.toggle(
        "Quellen standardmäßig einblenden",
        value=bool(preferences.get(UI_PREFERENCE_SHOW_SOURCES_DEFAULT, True)),
        key=f"{key_prefix}.show_sources_default",
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
            UI_PREFERENCE_SHOW_SOURCES_DEFAULT: show_sources_default,
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
     """Render only the global preference center as last sidebar block."""
     with st.sidebar:
         st.markdown("### Need-Analysis-Tool")
         st.markdown('<div class="cs-sidebar-nav-gap"></div>', unsafe_allow_html=True)
 
         st.markdown("**Über Cognitive Staffing**")
         st.markdown(
             """
             <div class="cs-sidebar-link-list">
               <a href="?info=competencies">Unsere Kompetenzen</a>
               <a href="?info=about">Über Cognitive Staffing</a>
             </div>
             """,
             unsafe_allow_html=True,
         )
         st.markdown('<div class="cs-sidebar-nav-gap"></div>', unsafe_allow_html=True)
 
         st.markdown("**Rechtliches**")
         st.markdown(
             """
             <div class="cs-sidebar-link-list">
               <a href="?info=contact">Kontakt</a>
               <a href="?info=accessibility">Erklärung zur Barrierefreiheit</a>
               <a href="?info=cookie">Cookies</a>
               <a href="?info=terms">Nutzungsbedingungen</a>
               <a href="?info=privacy">Datenschutzrichtlinie</a>
               <a href="?info=imprint">Impressum</a>
             </div>
             """,
             unsafe_allow_html=True,
         )
 
         st.markdown('<div class="cs-sidebar-nav-gap"></div>', unsafe_allow_html=True)
         with st.expander("Präferenz-Center", expanded=False):
             _render_preference_center_sidebar()

def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    _inject_theme_styles()

    init_session_state()
    previous_step = st.session_state.get(SSKey.LAST_RENDERED_STEP.value)

    pages = load_pages()
    ctx = WizardContext(pages=pages)

    info_page_key = _get_info_page_key()
    if info_page_key is not None:
        _render_info_page_sidebar_navigation(ctx)
        _render_info_page(info_page_key)
        _render_sidebar_actions()
        st.session_state[SSKey.LAST_RENDERED_STEP.value] = None
        return

    legal_page_key = _get_legal_page_key()
    if legal_page_key is not None:
        _render_legal_page(legal_page_key)
        _render_sidebar_actions()
        st.session_state[SSKey.LAST_RENDERED_STEP.value] = None
        return
    page_param = st.query_params.get("page")
    if isinstance(page_param, list):
        page_param = page_param[0] if page_param else None
    if page_param == "preferences":
        _render_info_page_sidebar_navigation(ctx)
        _render_preferences_page()
        _render_sidebar_actions()
        st.session_state[SSKey.LAST_RENDERED_STEP.value] = None
        return

    current = sidebar_navigation(ctx)
    step_changed = bool(previous_step and previous_step != current.key)
    if step_changed:
        # Keep inline HTML script until Streamlit offers an equivalent native API
        # for parent-window scroll reset on wizard step changes.
        st.components.v1.html(
            """
            <script>
            const topOptions = { top: 0, behavior: "instant" };
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
            </script>
            """,
            height=0,
        )

    current.render(ctx)
    _render_sidebar_actions()
    st.session_state[SSKey.LAST_RENDERED_STEP.value] = current.key


if __name__ == "__main__":
    main()
