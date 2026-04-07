# app.py

from __future__ import annotations

import base64
from pathlib import Path

import streamlit as st

from constants import APP_TITLE, SSKey
from settings_openai import load_openai_settings
from state import init_session_state, reset_vacancy
from wizard_pages import load_pages
from wizard_pages.base import WizardContext, sidebar_navigation


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
        </style>
        """,
        unsafe_allow_html=True,
    )


def _render_openai_debug_panel() -> None:
    """Render a compact, safe OpenAI resolution debug panel."""

    settings = load_openai_settings()
    session_model = st.session_state.get(SSKey.MODEL.value)
    resolved_model = settings.openai_model
    if isinstance(session_model, str) and session_model.strip():
        resolved_model = session_model.strip()

    with st.expander(
        "Debug (DE/EN): OpenAI-Auflösung / OpenAI resolution", expanded=False
    ):
        st.caption("Nur aufgelöste Laufzeitwerte, keine Secrets.")
        st.caption("Resolved runtime values only, no secrets.")
        st.json(
            {
                "resolved_model": resolved_model,
                "resolved_default_model": settings.default_model,
                "resolved_reasoning_effort": settings.reasoning_effort,
                "resolved_verbosity": settings.verbosity,
                "resolved_timeout": settings.openai_request_timeout,
            },
            expanded=False,
        )


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")
    _inject_theme_styles()

    init_session_state()

    pages = load_pages()
    ctx = WizardContext(pages=pages)

    with st.sidebar:
        st.markdown("### Aktionen")
        st.button("Reset Vacancy", on_click=reset_vacancy)
        st.divider()
        st.caption("Tipp: Du kannst jederzeit im Wizard springen.")
        if st.session_state.get(SSKey.DEBUG.value):
            _render_openai_debug_panel()

    current = sidebar_navigation(ctx)

    # Guard: if page requires jobspec but it's missing, redirect to jobad
    if current.requires_jobspec and not st.session_state.get(SSKey.JOB_EXTRACT.value):
        st.warning("Bitte zuerst ein Jobspec analysieren.")
        st.session_state[SSKey.CURRENT_STEP.value] = "jobad"
        st.rerun()

    current.render(ctx)


if __name__ == "__main__":
    main()
