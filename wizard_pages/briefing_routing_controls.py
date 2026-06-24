from __future__ import annotations

from typing import Any, Final

import streamlit as st

from constants import FactKey, SSKey
from i18n import t
from state import set_answer


BRIEFING_ROUTING_LABELS: Final[dict[str, dict[str, str]]] = {
    FactKey.INTAKE_SEARCH_CONFIDENTIALITY.value: {
        "open": "Offen kommunizierbar",
        "limited": "Intern begrenzt",
        "high": "Vertraulich / neutralisieren",
    },
    FactKey.INTAKE_HIRING_REASON.value: {
        "unknown": "Noch unklar",
        "replacement": "Ersatz / Backfill",
        "growth": "Wachstum",
        "new_role": "Neue Rolle / Neuaufbau",
        "internal_move": "Interne Nachfolge",
        "confidential": "Vertrauliche Suche",
    },
    FactKey.INTAKE_URGENCY.value: {
        "unknown": "Noch unklar",
        "low": "Planbar",
        "medium": "Relevant",
        "high": "Dringend",
        "critical": "Kritisch / sofort",
    },
    FactKey.INTAKE_ROLE_DEFINITION_MATURITY.value: {
        "unknown": "Noch unklar",
        "high": "Intern kalibriert",
        "medium": "Teilweise kalibriert",
        "low": "Noch unscharf",
    },
}


def _routing_answer(fact_key: FactKey, default: Any) -> Any:
    answers_raw = st.session_state.get(SSKey.ANSWERS.value, {})
    answers = answers_raw if isinstance(answers_raw, dict) else {}
    value = answers.get(fact_key.value, default)
    return default if value is None else value


def _persist_routing_answer(fact_key: FactKey, value: Any) -> None:
    set_answer(fact_key.value, value, fact_key=fact_key.value)


def _render_routing_select(
    *,
    fact_key: FactKey,
    label: str,
    options: tuple[str, ...],
    default: str,
    key_prefix: str,
) -> None:
    labels = BRIEFING_ROUTING_LABELS[fact_key.value]
    current = str(_routing_answer(fact_key, default) or default)
    if current not in options:
        current = default
    selected = st.selectbox(
        label,
        options=options,
        index=options.index(current),
        format_func=lambda value: labels.get(value, value),
        key=f"{key_prefix}.{fact_key.value}",
    )
    _persist_routing_answer(fact_key, selected)


def render_briefing_routing_controls(*, key_prefix: str) -> None:
    if not all(hasattr(st, name) for name in ("selectbox", "number_input")):
        if hasattr(st, "caption"):
            st.caption(str(t("Briefing-Routing vorab: Standardwerte werden verwendet.")))
        return

    _render_routing_select(
        fact_key=FactKey.INTAKE_SEARCH_CONFIDENTIALITY,
        label="Vertraulichkeit",
        options=("open", "limited", "high"),
        default="open",
        key_prefix=key_prefix,
    )
    _render_routing_select(
        fact_key=FactKey.INTAKE_URGENCY,
        label="Dringlichkeit",
        options=("unknown", "low", "medium", "high", "critical"),
        default="unknown",
        key_prefix=key_prefix,
    )
    _render_routing_select(
        fact_key=FactKey.INTAKE_HIRING_REASON,
        label="Besetzungsgrund",
        options=(
            "unknown",
            "replacement",
            "growth",
            "new_role",
            "internal_move",
            "confidential",
        ),
        default="unknown",
        key_prefix=key_prefix,
    )
    current_volume = _routing_answer(FactKey.INTAKE_HIRING_VOLUME, 1)
    try:
        current_volume_int = int(current_volume)
    except (TypeError, ValueError):
        current_volume_int = 1
    hiring_volume = st.number_input(
        "Anzahl Positionen",
        min_value=1,
        max_value=50,
        value=max(1, min(50, current_volume_int)),
        step=1,
        key=f"{key_prefix}.{FactKey.INTAKE_HIRING_VOLUME.value}",
    )
    _persist_routing_answer(FactKey.INTAKE_HIRING_VOLUME, int(hiring_volume))
    _render_routing_select(
        fact_key=FactKey.INTAKE_ROLE_DEFINITION_MATURITY,
        label="Rollenkalibrierung",
        options=("unknown", "high", "medium", "low"),
        default="unknown",
        key_prefix=key_prefix,
    )
