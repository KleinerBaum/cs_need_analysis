"""Small typed input helpers for canonical intake facts."""

from __future__ import annotations

from typing import Any, Iterable, Mapping

import streamlit as st

from constants import FactKey, SSKey
from intake_facts import get_intake_fact_state
from state import get_answers, mark_answer_touched, set_answer


def compact_text(value: Any) -> str:
    return " ".join(str(value or "").split()).strip()


def split_lines(value: Any) -> list[str]:
    if isinstance(value, list):
        raw_items = value
    else:
        raw_items = str(value or "").replace(";", "\n").replace(",", "\n").splitlines()
    output: list[str] = []
    seen: set[str] = set()
    for item in raw_items:
        text = compact_text(item)
        key = text.casefold()
        if not text or key in seen:
            continue
        output.append(text)
        seen.add(key)
    return output


def fact_value(fact_key: FactKey, default: Any = None) -> Any:
    answers = get_answers()
    if fact_key.value in answers:
        value = answers.get(fact_key.value)
        return default if value is None else value
    facts = get_intake_fact_state(st.session_state)
    if fact_key.value in facts:
        value = facts.get(fact_key.value)
        return default if value is None else value
    return default


def persist_fact(fact_key: FactKey, value: Any) -> Any:
    previous_value = fact_value(fact_key)
    mark_answer_touched(fact_key.value, previous_value, value)
    set_answer(fact_key.value, value, fact_key=fact_key.value)
    return value


def persist_compact_object(fact_key: FactKey, value: Mapping[str, Any]) -> dict[str, Any]:
    cleaned = {
        str(key): item
        for key, item in value.items()
        if compact_text(item) or isinstance(item, (bool, int, float))
    }
    return persist_fact(fact_key, cleaned)


def render_text_fact(
    fact_key: FactKey,
    label: str,
    *,
    default: str = "",
    help_text: str | None = None,
    placeholder: str | None = None,
) -> str:
    current = compact_text(fact_value(fact_key, default))
    value = st.text_input(
        label,
        value=current,
        help=help_text,
        placeholder=placeholder,
        key=f"fact_input.{fact_key.value}",
    )
    return persist_fact(fact_key, compact_text(value))


def render_text_area_fact(
    fact_key: FactKey,
    label: str,
    *,
    default: str = "",
    help_text: str | None = None,
    placeholder: str | None = None,
    height: int | None = None,
) -> str:
    current = str(fact_value(fact_key, default) or "")
    value = st.text_area(
        label,
        value=current,
        help=help_text,
        placeholder=placeholder,
        height=height,
        key=f"fact_input.{fact_key.value}",
    )
    return persist_fact(fact_key, value.strip())


def render_select_fact(
    fact_key: FactKey,
    label: str,
    *,
    options: Iterable[str],
    default: str,
    labels: Mapping[str, str] | None = None,
    help_text: str | None = None,
) -> str:
    option_list = list(options)
    current = compact_text(fact_value(fact_key, default)) or default
    if current not in option_list:
        current = default
    value = st.selectbox(
        label,
        options=option_list,
        index=option_list.index(current),
        format_func=lambda item: labels.get(item, item) if labels else item,
        help=help_text,
        key=f"fact_input.{fact_key.value}",
    )
    return persist_fact(fact_key, value)


def render_multiselect_fact(
    fact_key: FactKey,
    label: str,
    *,
    options: Iterable[str],
    default: Iterable[str] | None = None,
    help_text: str | None = None,
) -> list[str]:
    option_list = list(options)
    current = fact_value(fact_key, list(default or []))
    selected = [item for item in split_lines(current) if item in option_list]
    value = st.multiselect(
        label,
        options=option_list,
        default=selected,
        help=help_text,
        key=f"fact_input.{fact_key.value}",
    )
    return persist_fact(fact_key, list(value))


def render_number_fact(
    fact_key: FactKey,
    label: str,
    *,
    min_value: int,
    max_value: int,
    default: int,
    step: int = 1,
    help_text: str | None = None,
) -> int:
    current = fact_value(fact_key, default)
    try:
        current_int = int(current)
    except (TypeError, ValueError):
        current_int = default
    value = st.number_input(
        label,
        min_value=min_value,
        max_value=max_value,
        value=max(min_value, min(max_value, current_int)),
        step=step,
        help=help_text,
        key=f"fact_input.{fact_key.value}",
    )
    return persist_fact(fact_key, int(value))
