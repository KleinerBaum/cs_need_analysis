"""Helpers for Streamlit widgets backed by session state."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from typing import Any, TypeVar

import streamlit as st

T = TypeVar("T")


def ensure_option_widget_state(
    key: str,
    *,
    options: Sequence[T],
    default: T,
    session_state: Any | None = None,
) -> T:
    """Initialize a single-choice widget key without passing a widget default."""
    state = st.session_state if session_state is None else session_state
    option_values = list(options)
    current = state.get(key)
    if current not in option_values:
        state[key] = default
        return default
    return current


def ensure_multiselect_widget_state(
    key: str,
    *,
    options: Sequence[str],
    default: Iterable[str] | None = None,
    session_state: Any | None = None,
) -> list[str]:
    """Keep multiselect/pills widget state valid without duplicating defaults."""
    state = st.session_state if session_state is None else session_state
    option_values = [str(option).strip() for option in options if str(option).strip()]
    option_set = set(option_values)
    default_values = [
        str(item).strip()
        for item in (default or [])
        if str(item).strip() in option_set
    ]
    current_raw = state.get(key, default_values)
    if isinstance(current_raw, (list, tuple, set)):
        current_values = [str(item).strip() for item in current_raw]
        current_snapshot = [str(item).strip() for item in current_raw]
        current_is_sequence = True
    else:
        current_values = default_values
        current_snapshot = []
        current_is_sequence = False

    filtered_values: list[str] = []
    seen: set[str] = set()
    for value in current_values:
        if not value or value not in option_set or value in seen:
            continue
        filtered_values.append(value)
        seen.add(value)

    if (
        key not in state
        or not current_is_sequence
        or filtered_values != current_snapshot
    ):
        state[key] = filtered_values
    return filtered_values
