# app.py

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

from constants import APP_TITLE, SSKey
from llm_client import (
    TASK_EXTRACT_JOB_AD,
    TASK_GENERATE_QUESTION_PLAN,
    TASK_GENERATE_VACANCY_BRIEF,
    resolve_model_for_task,
)
from settings_openai import load_openai_settings
from state import init_session_state, reset_vacancy
from wizard_pages import load_pages
from wizard_pages.base import WizardContext, set_current_step, sidebar_navigation


def _image_as_data_uri(image_path: Path, mime_type: str) -> str:
    image_bytes = image_path.read_bytes()
    encoded = base64.b64encode(image_bytes).decode("utf-8")
    return f"data:{mime_type};base64,{encoded}"


def _inject_theme_styles() -> None:
    root_dir = Path(__file__).resolve().parent
    logo_path = root_dir / "images" / "color1_logo_transparent_background.png"
    bg_path = root_dir / "images" / "AdobeStock_506577005.jpeg"

    logo_uri = _image_as_data_uri(logo_path, "image/png")
    bg_uri = _image_as_data_uri(bg_path, "image/jpeg")

    st.markdown(
        f"""
        <style>
            .stApp {{
                background:
                    linear-gradient(
                        rgba(8, 18, 39, 0.82),
                        rgba(12, 27, 54, 0.72)
                    ),
                    url("{bg_uri}") center center / cover no-repeat fixed;
                color: #f5f7fb;
            }}

            [data-testid="stHeader"] {{
                background: transparent;
            }}

            [data-testid="stSidebar"] {{
                background: rgba(10, 24, 48, 0.85);
                border-right: 1px solid rgba(255, 255, 255, 0.1);
            }}

            [data-testid="stSidebarContent"]::before {{
                content: "";
                display: block;
                width: 220px;
                height: 64px;
                margin: 0 auto 1rem auto;
                background: url("{logo_uri}") center / contain no-repeat;
            }}

            [data-testid="stMarkdownContainer"] p,
            [data-testid="stMarkdownContainer"] li,
            [data-testid="stMarkdownContainer"] span,
            h1, h2, h3, h4, h5, h6,
            label {{
                color: #f5f7fb !important;
            }}

            [data-testid="stAlert"] {{
                background: rgba(0, 0, 0, 0.35);
                border: 1px solid rgba(255, 255, 255, 0.15);
                color: #f5f7fb;
            }}

            [data-testid="stForm"],
            [data-testid="stExpander"] details,
            [data-testid="stVerticalBlockBorderWrapper"] {{
                background: rgba(8, 18, 39, 0.52);
                border: 1px solid rgba(255, 255, 255, 0.12);
                border-radius: 12px;
                backdrop-filter: blur(4px);
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

    with st.expander(
        "Debug (DE/EN): OpenAI-Auflösung / OpenAI resolution", expanded=False
    ):
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
        st.title("Terms of Service / Nutzungsbedingungen")
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
        st.title("Privacy Policy / Datenschutzerklärung")
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

    if st.button("← Back to Wizard / Zurück zum Wizard"):
        st.query_params.clear()
        st.rerun()


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    _inject_theme_styles()

    init_session_state()

    pages = load_pages()
    ctx = WizardContext(pages=pages)

    with st.sidebar:
        st.markdown("### Aktionen")
        st.button("Reset Vacancy", on_click=reset_vacancy)

    legal_page_key = _get_legal_page_key()
    if legal_page_key is not None:
        _render_legal_page(legal_page_key)
        return

    current = sidebar_navigation(ctx)

    # Guard: if page requires jobspec but it's missing, redirect to landing
    if current.requires_jobspec and not st.session_state.get(SSKey.JOB_EXTRACT.value):
        st.warning("Bitte zuerst ein Jobspec analysieren.")
        set_current_step("landing")
        st.rerun()

    current.render(ctx)


if __name__ == "__main__":
    main()
