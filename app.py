# app.py

from __future__ import annotations

import streamlit as st

from constants import APP_TITLE, SSKey, STEPS
from state import init_session_state, reset_vacancy
from wizard_pages import load_pages
from wizard_pages.base import WizardContext, sidebar_navigation


def main() -> None:
    st.set_page_config(page_title=APP_TITLE, layout="wide")

    init_session_state()

    pages = load_pages()
    ctx = WizardContext(pages=pages)

    with st.sidebar:
        st.markdown("### Aktionen")
        st.button("Reset Vacancy", on_click=reset_vacancy)
        st.divider()
        st.caption("Tipp: Du kannst jederzeit im Wizard springen.")

    current = sidebar_navigation(ctx)

    # Guard: if page requires jobspec but it's missing, redirect to jobad
    if current.requires_jobspec and not st.session_state.get(SSKey.JOB_EXTRACT.value):
        st.warning("Bitte zuerst ein Jobspec analysieren.")
        st.session_state[SSKey.CURRENT_STEP.value] = "jobad"
        st.rerun()

    current.render(ctx)

    # Optional debug panel
    if st.session_state.get(SSKey.DEBUG.value):
        with st.expander("Debug: session_state", expanded=False):
            # Avoid showing secrets; show only known keys
            safe = {k: st.session_state.get(k) for k in [x.value for x in SSKey]}
            st.json(safe, expanded=False)


if __name__ == "__main__":
    main()
