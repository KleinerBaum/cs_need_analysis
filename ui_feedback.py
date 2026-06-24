# ui_feedback.py
"""Feedback banners and lightweight process feedback UI."""

from __future__ import annotations

import textwrap
from typing import Literal

import streamlit as st

from constants import SSKey
from llm_client import OpenAICallError
from state import set_error
from ui_inputs import _render_html_block

def render_error_banner() -> None:
    err = st.session_state.get(SSKey.LAST_ERROR.value)
    if err:
        st.error(err)
    debug_err = st.session_state.get(SSKey.LAST_ERROR_DEBUG.value)
    if debug_err and bool(st.session_state.get(SSKey.OPENAI_DEBUG_ERRORS.value, False)):
        with st.expander("Debug (non-sensitive)", expanded=False):
            st.caption("Nur technische Metadaten, keine Inhalte (kein Prompt/PII).")
            st.code(str(debug_err))


def render_openai_error(error: OpenAICallError) -> None:
    """Persist concise user message and optional non-sensitive debug details."""

    set_error(error.ui_message)
    st.session_state[SSKey.LAST_ERROR_DEBUG.value] = None
    if bool(st.session_state.get(SSKey.OPENAI_DEBUG_ERRORS.value, False)):
        details: list[str] = ["type=OpenAICallError", "step=llm_call"]
        if error.error_code:
            details.insert(0, f"code={error.error_code}")
        st.session_state[SSKey.LAST_ERROR_DEBUG.value] = " | ".join(details)
def render_intake_process_animation(*, state: Literal["idle", "running", "done"]) -> None:
    state = state if state in {"idle", "running", "done"} else "idle"
    state_class = f"cs-process-{state}"
    title = {
        "idle": "So entsteht dein Fragenplan",
        "running": "Analyse läuft",
        "done": "Intelligenter Vacancy-Intake",
    }[state]
    subtitle = {
        "idle": "Der Wizard reduziert manuelle Eingaben, erkennt offene Punkte und bereitet verwertbare Recruitment-Ergebnisse vor.",
        "running": "Die App liest den Text, setzt Kontext und bereitet dynamische Rückfragen sowie Folgeartefakte vor.",
        "done": "Rollenprofil, ESCO-Kontext und offene Fragen sind bereit für einen passgenauen Wizard.",
    }[state]
    steps = (
        (
            "Weniger manuell eingeben",
            "Jobspec, Kontext und vorhandene Fakten werden vorbefüllt; bei lokaler LLM-Konfiguration bleiben sensible Daten besonders geschützt.",
        ),
        (
            "Dynamisch nachfragen",
            "Der Fragebogen passt sich an die Vakanz an und schärft Must-have- und Nice-to-have-Skills mit Gehaltsprognose und Kandidatenverfügbarkeit.",
        ),
        (
            "Folgeschritte optimieren",
            "Job Ad, Vertrag, Suchstrings, Interviewleitfäden und interne oder externe Kommunikation bauen auf derselben Datenbasis auf.",
        ),
    )
    step_items = []
    for idx, (label, detail) in enumerate(steps):
        step_items.append(
            textwrap.dedent(
                f"""
                <div class="cs-process-step cs-process-step-{idx + 1}">
                    <span class="cs-process-dot"></span>
                    <div class="cs-process-copy">
                        <div class="cs-process-label">{label}</div>
                        <div class="cs-process-detail">{detail}</div>
                    </div>
                </div>
                """
            ).strip()
        )
    _render_html_block(
        textwrap.dedent(
            f"""
            <style>
            .cs-process-banner {{
                border: 1px solid var(--cs-border);
                background: var(--cs-surface);
                border-radius: 0.5rem;
                padding: 0.9rem;
                margin: 0.45rem 0 0.8rem 0;
                box-shadow: 0 10px 28px rgba(22, 50, 79, 0.07);
            }}
            .cs-process-title {{
                font-weight: 700;
                font-size: 0.98rem;
                margin-bottom: 0.15rem;
            }}
            .cs-process-subtitle {{
                color: var(--cs-text-muted);
                font-size: 0.88rem;
                margin-bottom: 0.8rem;
            }}
            .cs-process-track {{
                display: grid;
                grid-template-columns: repeat(3, minmax(0, 1fr));
                gap: 0.65rem;
            }}
            .cs-process-step {{
                display: flex;
                align-items: flex-start;
                gap: 0.65rem;
                padding: 0.7rem 0.75rem;
                border-radius: 0.5rem;
                border: 1px solid var(--cs-border);
                background: var(--cs-surface-muted);
                min-height: 3.2rem;
            }}
            .cs-process-banner.cs-process-running .cs-process-step {{
                box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.18);
            }}
            .cs-process-banner.cs-process-done .cs-process-step {{
                box-shadow: inset 0 0 0 1px rgba(15, 118, 110, 0.18);
            }}
            .cs-process-dot {{
                width: 0.7rem;
                height: 0.7rem;
                margin-top: 0.3rem;
                border-radius: 999px;
                background: #0F766E;
                box-shadow: 0 0 0 0 rgba(15, 118, 110, 0.28);
                animation: csProcessPulse 1.8s ease-in-out infinite;
            }}
            .cs-process-banner.cs-process-done .cs-process-dot {{
                background: #0F766E;
                box-shadow: 0 0 0 0 rgba(15, 118, 110, 0.28);
            }}
            .cs-process-step-1 .cs-process-dot {{ animation-delay: 0s; }}
            .cs-process-step-2 .cs-process-dot {{ animation-delay: 0.2s; }}
            .cs-process-step-3 .cs-process-dot {{ animation-delay: 0.4s; }}
            .cs-process-label {{
                font-weight: 650;
                font-size: 0.9rem;
                line-height: 1.2;
            }}
            .cs-process-detail {{
                color: var(--cs-text-subtle);
                font-size: 0.82rem;
                line-height: 1.25;
                margin-top: 0.18rem;
            }}
            @keyframes csProcessPulse {{
                0%, 100% {{
                    transform: scale(0.92);
                    opacity: 0.68;
                }}
                50% {{
                    transform: scale(1);
                    opacity: 1;
                }}
            }}
            @media (max-width: 820px) {{
                .cs-process-track {{
                    grid-template-columns: minmax(0, 1fr);
                }}
            }}
            </style>
            <div class="cs-process-banner {state_class}">
                <div class="cs-process-title">{title}</div>
                <div class="cs-process-subtitle">{subtitle}</div>
                <div class="cs-process-track">
                    {''.join(step_items)}
                </div>
            </div>
            """
        ).strip()
    )
