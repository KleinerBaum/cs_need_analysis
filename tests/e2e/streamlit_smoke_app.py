from __future__ import annotations

import os
import sys
from pathlib import Path

import streamlit as st

ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

import app as real_app  # noqa: E402
from tests.synthetic_smoke_state import (  # noqa: E402
    SYNTHETIC_SUMMARY_SEED_QUERY_VALUE,
    seed_summary_artifact_smoke_state,
)

_ORIGINAL_INIT_SESSION_STATE = real_app.init_session_state


def _first_query_param_value(name: str) -> str | None:
    value = st.query_params.get(name)
    if isinstance(value, list):
        value = value[0] if value else None
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _should_seed_summary_artifact() -> bool:
    return (
        os.getenv("CS_E2E_TEST_MODE") == "1"
        and _first_query_param_value("e2e_seed") == SYNTHETIC_SUMMARY_SEED_QUERY_VALUE
    )


def _init_session_state_for_e2e() -> None:
    _ORIGINAL_INIT_SESSION_STATE()
    if _should_seed_summary_artifact():
        seed_summary_artifact_smoke_state(st.session_state, last_mode="e2e_seed")


real_app.init_session_state = _init_session_state_for_e2e
real_app.main()
