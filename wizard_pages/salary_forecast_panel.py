from __future__ import annotations

from collections.abc import Callable
import hashlib
import json
import logging
from typing import Any

import plotly.graph_objects as go  # type: ignore[import-untyped]
import streamlit as st

from constants import SSKey
from esco_semantics import resolve_esco_semantic_context
from salary.context_defaults import sync_salary_scenario_context_defaults
from salary.engine import compute_salary_forecast
from salary.features_esco import extract_esco_context
from salary.scenario_lab_builders import (
    SENIORITY_SWEEP_VALUES,
    apply_scenario_overrides_to_job,
    build_candidate_skill_pool,
    build_salary_scenario_lab_rows,
    unique_skills,
)
from salary.scenarios import (
    SALARY_SCENARIO_BASE,
    SALARY_SCENARIO_COST_FOCUS,
    SALARY_SCENARIO_MARKET_UPSIDE,
    SALARY_SCENARIO_OPTIONS,
    map_salary_scenario_to_overrides,
)
from salary.types import (
    SalaryEscoContext,
    SalaryScenarioInputs,
    SalaryScenarioOverrides,
)
from safe_html import escape_html_text, render_static_html
from schemas import JobAdExtract
from ui_layout import render_fragment_pilot_panel
from ui_widget_state import ensure_multiselect_widget_state
from i18n import active_language
from ux_copy_contract import salary_ui_copy

LOGGER = logging.getLogger(__name__)


def _salary_copy(key: str, *, language: str | None = None, **params: Any) -> str:
    return salary_ui_copy(key, language=language or active_language(), **params)


def _safe_int(value: Any) -> int:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return 0


def _selected_clean(values: list[str]) -> list[str]:
    return list(
        dict.fromkeys(str(item).strip() for item in values if str(item).strip())
    )


def _unique_texts(values: list[Any]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        text = str(value or "").strip()
        if not text:
            continue
        key = text.casefold()
        if key in seen:
            continue
        seen.add(key)
        result.append(text)
    return result


def _merge_answers(
    base_answers: dict[str, Any], additions: dict[str, Any]
) -> dict[str, Any]:
    return {**base_answers, **additions}


def _factor_widget_key(*, step_key: str, factor_key: str) -> str:
    return f"{SSKey.SALARY_FORECAST_FACTOR_SELECTIONS.value}.{step_key}.{factor_key}"


def _select_salary_factors(
    *,
    step_key: str,
    factor_key: str,
    label: str,
    options: list[str],
    default: list[str] | None = None,
) -> list[str]:
    candidates = _unique_texts(options)
    raw_store = st.session_state.get(SSKey.SALARY_FORECAST_FACTOR_SELECTIONS.value, {})
    store = dict(raw_store) if isinstance(raw_store, dict) else {}
    step_store_raw = store.get(step_key, {})
    step_store = dict(step_store_raw) if isinstance(step_store_raw, dict) else {}
    factor_store_raw = step_store.get(factor_key, {})
    factor_store = dict(factor_store_raw) if isinstance(factor_store_raw, dict) else {}

    previous_candidates = _unique_texts(factor_store.get("candidates", []))
    previous_selected = _unique_texts(factor_store.get("selected", []))
    if previous_candidates:
        previous_candidate_keys = {item.casefold() for item in previous_candidates}
        selected_default = [
            item
            for item in previous_selected
            if item.casefold() in {candidate.casefold() for candidate in candidates}
        ]
        selected_keys = {item.casefold() for item in selected_default}
        selected_default.extend(
            item
            for item in candidates
            if item.casefold() not in previous_candidate_keys
            and item.casefold() not in selected_keys
        )
    else:
        selected_default = _unique_texts(default or candidates)

    widget_key = _factor_widget_key(step_key=step_key, factor_key=factor_key)
    ensure_multiselect_widget_state(
        widget_key,
        options=candidates,
        default=selected_default,
        session_state=st.session_state,
    )
    selected = st.multiselect(label, options=candidates, key=widget_key)
    selected = _unique_texts(selected)

    step_store[factor_key] = {"candidates": candidates, "selected": selected}
    store[step_key] = step_store
    st.session_state[SSKey.SALARY_FORECAST_FACTOR_SELECTIONS.value] = store
    return selected


def _current_step_forecast_fingerprint(
    *,
    step_key: str,
    job: JobAdExtract,
    selected_inputs: list[str],
    model: str,
    language: str,
    store: bool,
) -> str:
    payload = {
        "step_key": step_key,
        "selected_inputs": _selected_clean(selected_inputs),
        "job_title": str(job.job_title or "").strip(),
        "location_city": str(job.location_city or "").strip(),
        "location_country": str(job.location_country or "").strip(),
        "job_seniority": str(job.seniority_level or "").strip(),
        "esco_context": _session_esco_context().model_dump(mode="json"),
        "radius_km": _safe_int(
            st.session_state.get(SSKey.SALARY_SCENARIO_RADIUS_KM.value, 50)
        ),
        "remote_share_percent": _safe_int(
            st.session_state.get(SSKey.SALARY_SCENARIO_REMOTE_SHARE_PERCENT.value, 0)
        ),
        "seniority_override": str(
            st.session_state.get(SSKey.SALARY_SCENARIO_SENIORITY_OVERRIDE.value, "")
        ).strip(),
        "model": model,
        "language": language,
        "store": bool(store),
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _should_refresh_step_forecast(*, step_key: str, fingerprint: str) -> bool:
    raw_fingerprints = st.session_state.get(
        SSKey.SALARY_FORECAST_INPUT_FINGERPRINT.value, {}
    )
    fingerprints = raw_fingerprints if isinstance(raw_fingerprints, dict) else {}
    last_result = st.session_state.get(SSKey.SALARY_FORECAST_LAST_RESULT.value, {})
    last_step_key = (
        str(last_result.get("step_key") or "").strip()
        if isinstance(last_result, dict)
        else ""
    )
    return fingerprints.get(step_key) != fingerprint or last_step_key != step_key


def _remember_step_forecast_fingerprint(*, step_key: str, fingerprint: str) -> None:
    raw_fingerprints = st.session_state.get(
        SSKey.SALARY_FORECAST_INPUT_FINGERPRINT.value, {}
    )
    fingerprints = dict(raw_fingerprints) if isinstance(raw_fingerprints, dict) else {}
    fingerprints[step_key] = fingerprint
    st.session_state[SSKey.SALARY_FORECAST_INPUT_FINGERPRINT.value] = fingerprints


def _render_source_mix_pie(
    *, source_counts: dict[str, int] | None, chart_key: str
) -> None:
    counts = {
        str(label).strip(): _safe_int(count)
        for label, count in (source_counts or {}).items()
        if str(label).strip() and _safe_int(count) > 0
    }
    if not counts:
        st.caption("Quellenmix erscheint, sobald Elemente ausgewählt sind.")
        return
    fig = go.Figure(
        go.Bar(
            x=list(counts.values()),
            y=list(counts.keys()),
            orientation="h",
            marker_color="#5EA2FF",
            hovertemplate="%{y}: %{x} ausgewählt<extra></extra>",
        )
    )
    fig.update_layout(
        height=max(180, 44 * len(counts) + 80),
        margin=dict(l=8, r=8, t=12, b=8),
        showlegend=False,
        xaxis_title="Ausgewählte Elemente",
        yaxis_title="",
    )
    st.plotly_chart(fig, width="stretch", key=chart_key)
    st.caption("Die Übersicht zeigt, aus welchen Quellen die aktiven Elemente stammen.")


def _driver_chart_rows(salary_result: dict[str, Any] | None) -> list[dict[str, Any]]:
    payload = salary_result if isinstance(salary_result, dict) else {}
    raw_drivers = payload.get("drivers", [])
    if not isinstance(raw_drivers, list):
        return []
    rows: list[dict[str, Any]] = []
    for driver in raw_drivers:
        if not isinstance(driver, dict):
            continue
        impact = _safe_int(driver.get("impact_eur") or driver.get("impact"))
        direction = str(driver.get("direction") or "").strip()
        signed = -impact if direction == "down" else impact
        if signed == 0:
            continue
        rows.append(
            {
                "label": str(driver.get("label") or driver.get("key") or "").strip(),
                "value": signed,
                "detail": str(driver.get("detail") or "").strip(),
            }
        )
    return sorted(rows, key=lambda row: abs(row["value"]), reverse=True)[:8]


def _render_driver_impact_chart(
    *, salary_result: dict[str, Any] | None, chart_key: str
) -> None:
    rows = _driver_chart_rows(salary_result)
    if not rows:
        st.caption("Treiberdiagramm erscheint nach der nächsten Prognose.")
        return
    fig = go.Figure(
        go.Bar(
            x=[row["value"] for row in rows],
            y=[row["label"] for row in rows],
            orientation="h",
            marker_color=[
                "#44B678" if row["value"] >= 0 else "#D66A6A" for row in rows
            ],
            customdata=[row["detail"] for row in rows],
            hovertemplate="%{y}: %{x:,.0f} EUR<br>%{customdata}<extra></extra>",
        )
    )
    fig.update_layout(
        height=max(260, 36 * len(rows) + 100),
        margin=dict(l=8, r=8, t=24, b=8),
        title="Einfluss auf p50",
        xaxis_title="EUR",
        yaxis_title="",
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch", key=chart_key)


def _render_factor_delta_chart(
    *,
    rows: list[dict[str, Any]],
    chart_key: str,
    empty_caption: str,
) -> None:
    if not rows:
        st.caption(empty_caption)
        return
    visible_rows = sorted(rows, key=lambda row: abs(row["delta"]), reverse=True)[:12]
    fig = go.Figure(
        go.Bar(
            x=[row["delta"] for row in visible_rows],
            y=[row["label"] for row in visible_rows],
            orientation="h",
            marker_color="#44B678",
            hovertemplate="%{y}: %{x:,.0f} EUR p50-Effekt<extra></extra>",
        )
    )
    fig.update_layout(
        height=max(260, 34 * len(visible_rows) + 90),
        margin=dict(l=8, r=8, t=24, b=8),
        title="Einzeleffekt bei Abwahl",
        xaxis_title="EUR",
        yaxis_title="",
        showlegend=False,
    )
    st.plotly_chart(fig, width="stretch", key=chart_key)


def _build_quality_note(quality_payload: Any) -> str:
    fallback_note = "Heuristische Prognose ohne zusätzliche Qualitätssignale"
    if not hasattr(quality_payload, "signals") and not isinstance(
        quality_payload, dict
    ):
        return fallback_note

    if isinstance(quality_payload, dict):
        signals_raw = quality_payload.get("signals", [])
        kind_raw = quality_payload.get("kind")
        value_raw = quality_payload.get("value")
    else:
        signals_raw = getattr(quality_payload, "signals", [])
        kind_raw = getattr(quality_payload, "kind", "")
        value_raw = getattr(quality_payload, "value", None)

    signals = [str(item).strip() for item in signals_raw if str(item).strip()]
    if signals:
        return "; ".join(signals)

    kind = str(kind_raw or "").strip()
    try:
        value = float(value_raw)
    except (TypeError, ValueError):
        value = 0.0

    if kind:
        return f"{kind}: {int(round(value * 100, 0))}%"
    return fallback_note


def _extract_esco_skill_titles(raw_items: Any) -> list[str]:
    if not isinstance(raw_items, list):
        return []
    labels: list[str] = []
    for item in raw_items:
        if not isinstance(item, dict):
            continue
        label = str(item.get("title") or "").strip()
        if label:
            labels.append(label)
    return labels


def _get_selected_plotly_point(selection: Any) -> dict[str, Any] | None:
    if not isinstance(selection, dict):
        return None
    payload = selection.get("selection")
    if not isinstance(payload, dict):
        return None
    points = payload.get("points")
    if not isinstance(points, list) or not points:
        return None
    first = points[0]
    return first if isinstance(first, dict) else None


def _salary_scenario_table_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    group_labels = {
        "baseline": "Basis",
        "skill_delta": "Skill",
        "location_compare": "Standort",
        "radius_sweep": "Suchradius",
        "remote_share_sweep": "Remote-Anteil",
        "seniority_sweep": "Seniority",
    }
    table_rows: list[dict[str, Any]] = []
    for row in rows:
        details: list[str] = []
        city = str(row.get("city") or "").strip()
        country = str(row.get("country") or "").strip()
        if city or country:
            details.append(", ".join(part for part in (city, country) if part))
        if row.get("radius_km") not in (None, ""):
            details.append(f"{row['radius_km']} km Suchradius")
        if row.get("remote_share_percent") not in (None, ""):
            details.append(f"{row['remote_share_percent']}% remote")
        seniority = str(row.get("seniority_override") or "").strip()
        if seniority:
            details.append(f"Seniority: {seniority}")
        skills = [
            str(skill).strip()
            for skill in row.get("skills_add", [])
            if str(skill).strip()
        ]
        if skills:
            details.append("Skills: " + ", ".join(skills))
        table_rows.append(
            {
                "Typ": group_labels.get(
                    str(row.get("group") or ""), str(row.get("group") or "")
                ),
                "Szenario": str(row.get("label") or ""),
                "Unteres Gehalt": row.get("p10"),
                "Mittleres Gehalt": row.get("p50"),
                "Oberes Gehalt": row.get("p90"),
                "Unterschied": row.get("delta_p50"),
                "Details": " | ".join(details),
            }
        )
    return table_rows


def _session_esco_context() -> SalaryEscoContext:
    return extract_esco_context(
        occupation_selected=st.session_state.get(SSKey.ESCO_OCCUPATION_SELECTED.value),
        skills_must=st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_MUST.value, []),
        skills_nice=st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_NICE.value, []),
        esco_config=st.session_state.get(SSKey.ESCO_CONFIG.value, {}),
    )


def _current_salary_scenario_inputs() -> SalaryScenarioInputs:
    return SalaryScenarioInputs(
        location_city_override=str(
            st.session_state.get(SSKey.SALARY_SCENARIO_LOCATION_CITY_OVERRIDE.value, "")
        ).strip()
        or None,
        location_country_override=str(
            st.session_state.get(
                SSKey.SALARY_SCENARIO_LOCATION_COUNTRY_OVERRIDE.value, ""
            )
        ).strip()
        or None,
        search_radius_km=_safe_int(
            st.session_state.get(SSKey.SALARY_SCENARIO_RADIUS_KM.value, 50)
        ),
        remote_share_percent=_safe_int(
            st.session_state.get(SSKey.SALARY_SCENARIO_REMOTE_SHARE_PERCENT.value, 0)
        ),
    )


def _step_job_with_seniority_override(job: JobAdExtract) -> JobAdExtract:
    seniority_override = str(
        st.session_state.get(SSKey.SALARY_SCENARIO_SENIORITY_OVERRIDE.value, "")
    ).strip()
    if not seniority_override:
        return job
    return job.model_copy(update={"seniority_level": seniority_override})


def _build_step_salary_result(
    *,
    step_key: str,
    job: JobAdExtract,
    answers: dict[str, Any],
    inputs: dict[str, Any],
    input_fingerprint: str | None = None,
) -> dict[str, Any]:
    forecast = compute_salary_forecast(
        job_extract=_step_job_with_seniority_override(job),
        answers=answers,
        esco_context=_session_esco_context(),
        scenario_inputs=_current_salary_scenario_inputs(),
    )
    result = forecast.model_dump(mode="json")
    result["step_key"] = step_key
    if input_fingerprint:
        result["input_fingerprint"] = input_fingerprint
    result["confidence_note"] = _build_quality_note(result.get("quality", {}))
    result["inputs"] = {
        **inputs,
        "answers_count": len(answers),
        "radius_km": _safe_int(
            st.session_state.get(SSKey.SALARY_SCENARIO_RADIUS_KM.value, 50)
        ),
        "remote_share_percent": _safe_int(
            st.session_state.get(SSKey.SALARY_SCENARIO_REMOTE_SHARE_PERCENT.value, 0)
        ),
        "seniority_override": str(
            st.session_state.get(SSKey.SALARY_SCENARIO_SENIORITY_OVERRIDE.value, "")
        ).strip(),
    }
    return result


def _build_factor_delta_rows(
    *,
    job: JobAdExtract,
    answers: dict[str, Any],
    selected_items: list[str],
    field_name: str,
) -> list[dict[str, Any]]:
    selected = _unique_texts(selected_items)
    if len(selected) <= 1:
        return []
    forecast_job = _step_job_with_seniority_override(job)
    baseline = compute_salary_forecast(
        job_extract=forecast_job,
        answers=answers,
        esco_context=_session_esco_context(),
        scenario_inputs=_current_salary_scenario_inputs(),
    )
    baseline_p50 = float(baseline.forecast.p50)
    rows: list[dict[str, Any]] = []
    for item in selected:
        remaining = [value for value in selected if value.casefold() != item.casefold()]
        scenario_job = forecast_job.model_copy(update={field_name: remaining})
        forecast = compute_salary_forecast(
            job_extract=scenario_job,
            answers=answers,
            esco_context=_session_esco_context(),
            scenario_inputs=_current_salary_scenario_inputs(),
        )
        rows.append(
            {
                "label": item,
                "delta": round(baseline_p50 - float(forecast.forecast.p50), 0),
            }
        )
    return rows


def _build_skill_factor_delta_rows(
    *,
    job: JobAdExtract,
    answers: dict[str, Any],
    must_have_skills: list[str],
    nice_to_have_skills: list[str],
) -> list[dict[str, Any]]:
    selected = _unique_texts([*must_have_skills, *nice_to_have_skills])
    if len(selected) <= 1:
        return []
    forecast_job = _step_job_with_seniority_override(job)
    baseline = compute_salary_forecast(
        job_extract=forecast_job,
        answers=answers,
        esco_context=_session_esco_context(),
        scenario_inputs=_current_salary_scenario_inputs(),
    )
    baseline_p50 = float(baseline.forecast.p50)
    rows: list[dict[str, Any]] = []
    for item in selected:
        item_key = item.casefold()
        scenario_job = forecast_job.model_copy(
            update={
                "must_have_skills": [
                    skill for skill in must_have_skills if skill.casefold() != item_key
                ],
                "nice_to_have_skills": [
                    skill
                    for skill in nice_to_have_skills
                    if skill.casefold() != item_key
                ],
            }
        )
        forecast = compute_salary_forecast(
            job_extract=scenario_job,
            answers=answers,
            esco_context=_session_esco_context(),
            scenario_inputs=_current_salary_scenario_inputs(),
        )
        rows.append(
            {
                "label": item,
                "delta": round(baseline_p50 - float(forecast.forecast.p50), 0),
            }
        )
    return rows


def _build_salary_forecast_snapshot(
    job: JobAdExtract,
    answers: dict[str, Any],
    *,
    scenario_name: str = "base",
    scenario_overrides: SalaryScenarioOverrides | None = None,
    esco_context: SalaryEscoContext | None = None,
) -> dict[str, Any]:
    overrides = scenario_overrides or SalaryScenarioOverrides()
    forecast = compute_salary_forecast(
        job_extract=job,
        answers=answers,
        scenario_overrides=overrides,
        esco_context=esco_context or _session_esco_context(),
        scenario_inputs=_current_salary_scenario_inputs(),
    )
    full_result = forecast.model_dump(mode="json")
    return {
        **full_result,
        "scenario": scenario_name,
        "inputs": {
            "skills_add": st.session_state.get(
                SSKey.SALARY_SCENARIO_SKILLS_ADD.value, []
            ),
            "skills_remove": st.session_state.get(
                SSKey.SALARY_SCENARIO_SKILLS_REMOVE.value, []
            ),
            "location_city_override": st.session_state.get(
                SSKey.SALARY_SCENARIO_LOCATION_CITY_OVERRIDE.value, ""
            ),
            "location_country_override": st.session_state.get(
                SSKey.SALARY_SCENARIO_LOCATION_COUNTRY_OVERRIDE.value, ""
            ),
            "radius_km": _safe_int(
                st.session_state.get(SSKey.SALARY_SCENARIO_RADIUS_KM.value, 50)
            ),
            "remote_share_percent": _safe_int(
                st.session_state.get(
                    SSKey.SALARY_SCENARIO_REMOTE_SHARE_PERCENT.value, 0
                )
            ),
            "seniority_override": str(
                st.session_state.get(SSKey.SALARY_SCENARIO_SENIORITY_OVERRIDE.value, "")
            ).strip(),
        },
        "forecast": forecast.forecast.model_dump(mode="json"),
        "forecast_result": full_result,
    }


def _salary_debug_enabled() -> bool:
    return str(
        st.session_state.get(SSKey.UI_MODE.value, "standard")
    ).strip().lower() == "expert" or bool(
        st.session_state.get(SSKey.DEBUG.value, False)
    )


def _render_salary_forecast_recovery(
    *,
    step_key: str,
    language: str,
    exc: Exception | None = None,
) -> None:
    st.warning(_salary_copy("unavailable", language=language))
    existing_result = st.session_state.get(SSKey.SALARY_FORECAST_LAST_RESULT.value, {})
    if isinstance(existing_result, dict) and existing_result:
        st.caption(
            "Vorherige Prognose bleibt sichtbar. Nächste Aktion: Eingaben prüfen "
            "oder die Gehaltsprognose später erneut öffnen."
        )
    else:
        st.caption(
            "Nächste Aktion: Eingaben prüfen oder die Gehaltsprognose später erneut öffnen; "
            "Rolle, Skills und Benefits bleiben weiter bearbeitbar."
        )
    if exc is not None and _salary_debug_enabled():
        with st.expander("Technische Prognose-Diagnose", expanded=False):
            st.caption(f"step={step_key}")
            st.caption(f"type={type(exc).__name__}")


def _queue_pending_salary_scenario_update(
    *,
    skills_add: list[str] | None = None,
    skills_remove: list[str] | None = None,
    location_city_override: str | None = None,
    radius_km: int | None = None,
    remote_share_percent: int | None = None,
    seniority_override: str | None = None,
    selected_row_id: str | None = None,
) -> None:
    if skills_add is not None:
        st.session_state[SSKey.SALARY_SCENARIO_PENDING_SKILLS_ADD.value] = skills_add
    if skills_remove is not None:
        st.session_state[SSKey.SALARY_SCENARIO_PENDING_SKILLS_REMOVE.value] = (
            skills_remove
        )
    if location_city_override is not None:
        st.session_state[SSKey.SALARY_SCENARIO_PENDING_LOCATION_CITY_OVERRIDE.value] = (
            location_city_override
        )
    if radius_km is not None:
        st.session_state[SSKey.SALARY_SCENARIO_PENDING_RADIUS_KM.value] = radius_km
    if remote_share_percent is not None:
        st.session_state[SSKey.SALARY_SCENARIO_PENDING_REMOTE_SHARE_PERCENT.value] = (
            remote_share_percent
        )
    if seniority_override is not None:
        st.session_state[SSKey.SALARY_SCENARIO_PENDING_SENIORITY_OVERRIDE.value] = (
            seniority_override
        )
    if selected_row_id is not None:
        st.session_state[SSKey.SALARY_SCENARIO_PENDING_SELECTED_ROW_ID.value] = (
            selected_row_id
        )
    st.session_state[SSKey.SALARY_SCENARIO_APPLY_PENDING_UPDATE.value] = True


def _apply_pending_salary_scenario_update() -> None:
    if not bool(
        st.session_state.get(SSKey.SALARY_SCENARIO_APPLY_PENDING_UPDATE.value, False)
    ):
        return

    pending_skills_add = st.session_state.get(
        SSKey.SALARY_SCENARIO_PENDING_SKILLS_ADD.value
    )
    if isinstance(pending_skills_add, list):
        st.session_state[SSKey.SALARY_SCENARIO_SKILLS_ADD.value] = unique_skills(
            [str(skill) for skill in pending_skills_add if str(skill).strip()]
        )

    pending_skills_remove = st.session_state.get(
        SSKey.SALARY_SCENARIO_PENDING_SKILLS_REMOVE.value
    )
    if isinstance(pending_skills_remove, list):
        st.session_state[SSKey.SALARY_SCENARIO_SKILLS_REMOVE.value] = unique_skills(
            [str(skill) for skill in pending_skills_remove if str(skill).strip()]
        )

    pending_city = st.session_state.get(
        SSKey.SALARY_SCENARIO_PENDING_LOCATION_CITY_OVERRIDE.value
    )
    if isinstance(pending_city, str):
        st.session_state[SSKey.SALARY_SCENARIO_LOCATION_CITY_OVERRIDE.value] = (
            pending_city
        )

    pending_radius = st.session_state.get(SSKey.SALARY_SCENARIO_PENDING_RADIUS_KM.value)
    if pending_radius is not None:
        st.session_state[SSKey.SALARY_SCENARIO_RADIUS_KM.value] = _safe_int(
            pending_radius
        )

    pending_remote = st.session_state.get(
        SSKey.SALARY_SCENARIO_PENDING_REMOTE_SHARE_PERCENT.value
    )
    if pending_remote is not None:
        st.session_state[SSKey.SALARY_SCENARIO_REMOTE_SHARE_PERCENT.value] = _safe_int(
            pending_remote
        )

    pending_seniority = st.session_state.get(
        SSKey.SALARY_SCENARIO_PENDING_SENIORITY_OVERRIDE.value
    )
    if isinstance(pending_seniority, str):
        st.session_state[SSKey.SALARY_SCENARIO_SENIORITY_OVERRIDE.value] = (
            pending_seniority
        )

    pending_row_id = st.session_state.get(
        SSKey.SALARY_SCENARIO_PENDING_SELECTED_ROW_ID.value
    )
    if isinstance(pending_row_id, str):
        st.session_state[SSKey.SALARY_SCENARIO_SELECTED_ROW_ID.value] = pending_row_id

    st.session_state[SSKey.SALARY_SCENARIO_PENDING_SKILLS_ADD.value] = None
    st.session_state[SSKey.SALARY_SCENARIO_PENDING_SKILLS_REMOVE.value] = None
    st.session_state[SSKey.SALARY_SCENARIO_PENDING_LOCATION_CITY_OVERRIDE.value] = None
    st.session_state[SSKey.SALARY_SCENARIO_PENDING_RADIUS_KM.value] = None
    st.session_state[SSKey.SALARY_SCENARIO_PENDING_REMOTE_SHARE_PERCENT.value] = None
    st.session_state[SSKey.SALARY_SCENARIO_PENDING_SENIORITY_OVERRIDE.value] = None
    st.session_state[SSKey.SALARY_SCENARIO_PENDING_SELECTED_ROW_ID.value] = None
    st.session_state[SSKey.SALARY_SCENARIO_APPLY_PENDING_UPDATE.value] = False


def _apply_salary_scenario_inputs(job: JobAdExtract) -> tuple[JobAdExtract, list[str]]:
    semantic_context = resolve_esco_semantic_context(st.session_state)
    esco_titles = (
        unique_skills(
            [
                *_extract_esco_skill_titles(
                    st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_MUST.value, [])
                ),
                *_extract_esco_skill_titles(
                    st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_NICE.value, [])
                ),
            ]
        )
        if semantic_context.can_use_esco_normalization
        else []
    )
    candidate_skills = build_candidate_skill_pool(
        job=job, esco_skill_titles=esco_titles
    )
    current_skills_add_raw = st.session_state.get(
        SSKey.SALARY_SCENARIO_SKILLS_ADD.value, []
    )
    current_skills_add = _selected_clean(
        current_skills_add_raw if isinstance(current_skills_add_raw, list) else []
    )
    current_skills_remove_raw = st.session_state.get(
        SSKey.SALARY_SCENARIO_SKILLS_REMOVE.value, []
    )
    current_skills_remove = _selected_clean(
        current_skills_remove_raw if isinstance(current_skills_remove_raw, list) else []
    )
    skill_options = unique_skills(
        [*candidate_skills, *current_skills_add, *current_skills_remove]
    )
    ensure_multiselect_widget_state(
        SSKey.SALARY_SCENARIO_SKILLS_ADD.value,
        options=skill_options,
        default=current_skills_add,
        session_state=st.session_state,
    )
    ensure_multiselect_widget_state(
        SSKey.SALARY_SCENARIO_SKILLS_REMOVE.value,
        options=skill_options,
        default=current_skills_remove,
        session_state=st.session_state,
    )

    skills_add = st.multiselect(
        "Skills hinzufügen",
        options=skill_options,
        key=SSKey.SALARY_SCENARIO_SKILLS_ADD.value,
    )
    skills_remove = st.multiselect(
        "Skills entfernen",
        options=skill_options,
        key=SSKey.SALARY_SCENARIO_SKILLS_REMOVE.value,
    )
    city = st.text_input(
        "Stadt-Override",
        key=SSKey.SALARY_SCENARIO_LOCATION_CITY_OVERRIDE.value,
    ).strip()
    country = st.text_input(
        "Land-Override",
        key=SSKey.SALARY_SCENARIO_LOCATION_COUNTRY_OVERRIDE.value,
    ).strip()
    st.slider(
        "Suchradius (km)",
        min_value=0,
        max_value=500,
        step=5,
        key=SSKey.SALARY_SCENARIO_RADIUS_KM.value,
    )
    st.slider(
        "Remote Share (%)",
        min_value=0,
        max_value=100,
        step=5,
        key=SSKey.SALARY_SCENARIO_REMOTE_SHARE_PERCENT.value,
    )
    st.selectbox(
        "Seniority Override",
        options=["", *SENIORITY_SWEEP_VALUES],
        format_func=lambda value: "(keine)" if not value else value,
        key=SSKey.SALARY_SCENARIO_SENIORITY_OVERRIDE.value,
    )

    forecast_job = apply_scenario_overrides_to_job(
        job=job,
        skills_add=skills_add,
        skills_remove=skills_remove,
        location_city_override=city,
        location_country_override=country,
        remote_share_percent=_safe_int(
            st.session_state.get(SSKey.SALARY_SCENARIO_REMOTE_SHARE_PERCENT.value, 0)
        ),
        seniority_override=str(
            st.session_state.get(SSKey.SALARY_SCENARIO_SENIORITY_OVERRIDE.value, "")
        ).strip(),
    )
    return forecast_job, unique_skills([*candidate_skills, *skills_add, *skills_remove])


def render_salary_forecast_panel(job: JobAdExtract, answers: dict[str, Any]) -> None:
    _apply_pending_salary_scenario_update()
    sync_salary_scenario_context_defaults(st.session_state, job=job)
    st.subheader(_salary_copy("forecast_heading"))
    controls_col, result_col = st.columns((1, 2))

    with controls_col:
        selected_scenario = st.radio(
            "Szenario",
            options=SALARY_SCENARIO_OPTIONS,
            format_func=lambda value: {
                SALARY_SCENARIO_BASE: "Baseline",
                SALARY_SCENARIO_MARKET_UPSIDE: "Marktaufschwung",
                SALARY_SCENARIO_COST_FOCUS: "Kostenfokus",
            }[value],
            key=SSKey.SALARY_FORECAST_SELECTED_SCENARIO.value,
        )
        forecast_job, candidate_skills = _apply_salary_scenario_inputs(job)

    scenario_overrides = map_salary_scenario_to_overrides(selected_scenario)
    scenario_inputs = _current_salary_scenario_inputs()
    esco_context = _session_esco_context()
    forecast = compute_salary_forecast(
        job_extract=forecast_job,
        answers=answers,
        scenario_overrides=scenario_overrides,
        esco_context=esco_context,
        scenario_inputs=scenario_inputs,
    )

    scenario_rows = build_salary_scenario_lab_rows(
        job=forecast_job,
        answers=answers,
        scenario_overrides=scenario_overrides,
        candidate_skills=candidate_skills,
        location_country_override=str(
            st.session_state.get(
                SSKey.SALARY_SCENARIO_LOCATION_COUNTRY_OVERRIDE.value, ""
            )
        ).strip(),
        radius_km=_safe_int(
            st.session_state.get(SSKey.SALARY_SCENARIO_RADIUS_KM.value, 50)
        ),
        remote_share_percent=_safe_int(
            st.session_state.get(SSKey.SALARY_SCENARIO_REMOTE_SHARE_PERCENT.value, 0)
        ),
        seniority_override=str(
            st.session_state.get(SSKey.SALARY_SCENARIO_SENIORITY_OVERRIDE.value, "")
        ).strip(),
        top_n_skills=12,
        esco_context=esco_context,
    )
    st.session_state[SSKey.SALARY_SCENARIO_LAB_ROWS.value] = scenario_rows

    with result_col:
        p10, p50, p90 = st.columns(3)
        p10.metric(
            f"p10 ({forecast.period})",
            f"{int(forecast.forecast.p10):,} {forecast.currency}".replace(",", "."),
        )
        p50.metric(
            f"p50 ({forecast.period})",
            f"{int(forecast.forecast.p50):,} {forecast.currency}".replace(",", "."),
        )
        p90.metric(
            f"p90 ({forecast.period})",
            f"{int(forecast.forecast.p90):,} {forecast.currency}".replace(",", "."),
        )
        quality_percent = int(round(float(forecast.quality.value) * 100, 0))
        st.caption(_salary_copy("main_caveat"))
        st.caption(_salary_copy("quality_caveat", quality=quality_percent))
        show_debug = str(
            st.session_state.get(SSKey.UI_MODE.value, "standard")
        ).strip().lower() == "expert" or bool(
            st.session_state.get(SSKey.DEBUG.value, False)
        )
        if show_debug:
            with st.expander("Technische Prognose-Diagnose", expanded=False):
                st.caption(f"quality_kind={forecast.quality.kind}")

        skill_rows = [row for row in scenario_rows if row["group"] == "skill_delta"]
        location_rows = [
            row for row in scenario_rows if row["group"] == "location_compare"
        ]
        radius_rows = [row for row in scenario_rows if row["group"] == "radius_sweep"]
        remote_rows = [
            row for row in scenario_rows if row["group"] == "remote_share_sweep"
        ]
        seniority_rows = [
            row for row in scenario_rows if row["group"] == "seniority_sweep"
        ]

        tornado_fig = go.Figure(
            go.Bar(
                x=[row["delta_p50"] for row in skill_rows],
                y=[row["label"] for row in skill_rows],
                orientation="h",
                customdata=[row["row_id"] for row in skill_rows],
            )
        )
        tornado_fig.update_layout(
            height=320, margin=dict(l=8, r=8, t=24, b=8), title="Skill-Tornado (Δ p50)"
        )
        tornado_selection = st.plotly_chart(
            tornado_fig, width="stretch", key="salary_tornado_chart", on_select="rerun"
        )
        selected_tornado = _get_selected_plotly_point(tornado_selection)
        if selected_tornado and isinstance(selected_tornado.get("y"), str):
            selected_skill = str(selected_tornado["y"])
            skills_add = unique_skills(
                [
                    *st.session_state.get(SSKey.SALARY_SCENARIO_SKILLS_ADD.value, []),
                    selected_skill,
                ]
            )
            skills_remove = [
                skill
                for skill in st.session_state.get(
                    SSKey.SALARY_SCENARIO_SKILLS_REMOVE.value, []
                )
                if str(skill).casefold() != selected_skill.casefold()
            ]
            _queue_pending_salary_scenario_update(
                skills_add=skills_add,
                skills_remove=skills_remove,
                selected_row_id=str(selected_tornado.get("customdata") or ""),
            )

        location_fig = go.Figure(
            go.Bar(
                x=[row["label"] for row in location_rows],
                y=[row["p50"] for row in location_rows],
                error_y={
                    "type": "data",
                    "symmetric": False,
                    "array": [row["p90"] - row["p50"] for row in location_rows],
                    "arrayminus": [row["p50"] - row["p10"] for row in location_rows],
                },
                customdata=[row["row_id"] for row in location_rows],
            )
        )
        location_fig.update_layout(
            height=320, margin=dict(l=8, r=8, t=24, b=8), title="Standortvergleich"
        )
        location_selection = st.plotly_chart(
            location_fig,
            width="stretch",
            key="salary_location_chart",
            on_select="rerun",
        )
        selected_location = _get_selected_plotly_point(location_selection)
        if selected_location and isinstance(selected_location.get("x"), str):
            _queue_pending_salary_scenario_update(
                location_city_override=str(selected_location["x"]),
                selected_row_id=str(selected_location.get("customdata") or ""),
            )

        radius_fig = go.Figure(
            go.Scatter(
                x=[row["radius_km"] for row in radius_rows],
                y=[row["p50"] for row in radius_rows],
                mode="lines+markers",
                customdata=[row["row_id"] for row in radius_rows],
            )
        )
        radius_fig.update_layout(
            height=280, margin=dict(l=8, r=8, t=24, b=8), title="Radius-Sweep"
        )
        radius_selection = st.plotly_chart(
            radius_fig, width="stretch", key="salary_radius_chart", on_select="rerun"
        )
        selected_radius = _get_selected_plotly_point(radius_selection)
        if selected_radius and selected_radius.get("x") is not None:
            _queue_pending_salary_scenario_update(
                radius_km=_safe_int(selected_radius["x"]),
                selected_row_id=str(selected_radius.get("customdata") or ""),
            )

        filter_col_a, filter_col_b = st.columns(2)
        with filter_col_a:
            remote_fig = go.Figure(
                go.Scatter(
                    x=[row["remote_share_percent"] for row in remote_rows],
                    y=[row["p50"] for row in remote_rows],
                    mode="lines+markers",
                    customdata=[row["row_id"] for row in remote_rows],
                )
            )
            remote_fig.update_layout(
                height=260,
                margin=dict(l=8, r=8, t=24, b=8),
                title="Remote-Share-Sensitivität",
            )
            remote_selection = st.plotly_chart(
                remote_fig,
                width="stretch",
                key="salary_remote_chart",
                on_select="rerun",
            )
            selected_remote = _get_selected_plotly_point(remote_selection)
            if selected_remote and selected_remote.get("x") is not None:
                _queue_pending_salary_scenario_update(
                    remote_share_percent=_safe_int(selected_remote["x"]),
                    selected_row_id=str(selected_remote.get("customdata") or ""),
                )

        with filter_col_b:
            seniority_fig = go.Figure(
                go.Bar(
                    x=[row["label"] for row in seniority_rows],
                    y=[row["p50"] for row in seniority_rows],
                    customdata=[row["row_id"] for row in seniority_rows],
                )
            )
            seniority_fig.update_layout(
                height=260,
                margin=dict(l=8, r=8, t=24, b=8),
                title="Seniority-Sensitivität",
            )
            seniority_selection = st.plotly_chart(
                seniority_fig,
                width="stretch",
                key="salary_seniority_chart",
                on_select="rerun",
            )
            selected_seniority = _get_selected_plotly_point(seniority_selection)
            if selected_seniority and isinstance(selected_seniority.get("x"), str):
                _queue_pending_salary_scenario_update(
                    seniority_override=str(selected_seniority["x"]),
                    selected_row_id=str(selected_seniority.get("customdata") or ""),
                )

        st.markdown("**Szenario-Tabelle**")
        st.dataframe(
            _salary_scenario_table_rows(scenario_rows),
            hide_index=True,
            width="stretch",
            column_config={
                "Typ": st.column_config.TextColumn("Typ"),
                "Szenario": st.column_config.TextColumn("Szenario"),
                "Unteres Gehalt": st.column_config.NumberColumn("Unteres Gehalt"),
                "Mittleres Gehalt": st.column_config.NumberColumn("Mittleres Gehalt"),
                "Oberes Gehalt": st.column_config.NumberColumn("Oberes Gehalt"),
                "Unterschied": st.column_config.NumberColumn("Unterschied"),
                "Details": st.column_config.TextColumn("Details"),
            },
        )

    st.session_state[SSKey.SALARY_FORECAST_LAST_RESULT.value] = (
        _build_salary_forecast_snapshot(
            forecast_job,
            answers,
            scenario_name=selected_scenario,
            scenario_overrides=scenario_overrides,
            esco_context=esco_context,
        )
    )


def _format_eur(value: int) -> str:
    return f"{value:,} €".replace(",", ".")


def _quality_label_from_payload(payload: Any) -> str:
    quality_payload = payload if isinstance(payload, dict) else {}
    try:
        value = float(quality_payload.get("value"))
    except (TypeError, ValueError):
        value = 0.0
    if value >= 0.75:
        return "hoch"
    if value >= 0.5:
        return "mittel"
    if value > 0:
        return "niedrig"
    return "noch nicht bewertet"


def _render_common_scenario_inputs(job: JobAdExtract | None = None) -> None:
    sync_salary_scenario_context_defaults(st.session_state, job=job)
    st.slider(
        "Suchradius (km)",
        min_value=0,
        max_value=500,
        step=5,
        key=SSKey.SALARY_SCENARIO_RADIUS_KM.value,
    )
    st.slider(
        "Remote Share (%)",
        min_value=0,
        max_value=100,
        step=5,
        key=SSKey.SALARY_SCENARIO_REMOTE_SHARE_PERCENT.value,
    )
    st.selectbox(
        "Erfahrung",
        options=["", *SENIORITY_SWEEP_VALUES],
        format_func=lambda value: "(keine)" if not value else value,
        key=SSKey.SALARY_SCENARIO_SENIORITY_OVERRIDE.value,
    )


def render_salary_forecast_result_card(
    *,
    salary_result: dict[str, Any] | None,
    empty_message: str,
    headline: str = "Gehaltsprognose (Jahr)",
    use_main_card_layout: bool = False,
    language: str | None = None,
) -> None:
    payload = salary_result if isinstance(salary_result, dict) else {}
    forecast_payload = payload.get("forecast", {}) if isinstance(payload, dict) else {}
    p50 = _safe_int(forecast_payload.get("p50"))
    if p50 <= 0:
        st.info(empty_message)
        return

    p10 = _safe_int(forecast_payload.get("p10"))
    p90 = _safe_int(forecast_payload.get("p90"))
    confidence_note = str(
        payload.get("quality_note") or payload.get("confidence_note") or ""
    ).strip()
    if not confidence_note and isinstance(payload.get("quality"), dict):
        confidence_note = _build_quality_note(payload["quality"])
    quality_label = _quality_label_from_payload(payload.get("quality"))
    inputs = payload.get("inputs", {})
    answers_count = 0
    if isinstance(inputs, dict):
        answers_count = _safe_int(inputs.get("answers_count"))

    with st.container(border=True):
        st.markdown(f"**{headline}**")
        if not use_main_card_layout:
            metric_col_main, metric_col_low, metric_col_high = st.columns(
                (2, 1, 1), gap="small"
            )
            with metric_col_main:
                st.metric("p50 (Median)", _format_eur(p50))
            with metric_col_low:
                st.metric(
                    "p10 (niedrig)", _format_eur(p10) if p10 > 0 else "nicht verfügbar"
                )
            with metric_col_high:
                st.metric(
                    "p90 (hoch)", _format_eur(p90) if p90 > 0 else "nicht verfügbar"
                )
        else:
            render_static_html(
                """
                <style>
                .salary-main-cards-grid {
                    display: grid;
                    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
                    gap: 0.5rem;
                    margin-top: 0.35rem;
                }
                .salary-main-card {
                    border: 1px solid rgba(49, 51, 63, 0.2);
                    border-radius: 0.5rem;
                    padding: 0.55rem 0.65rem;
                    min-width: 0;
                    background: rgba(255, 255, 255, 0.02);
                }
                .salary-main-card-label {
                    font-size: 0.78rem;
                    opacity: 0.85;
                    margin-bottom: 0.15rem;
                }
                .salary-main-card-value {
                    font-size: 1.08rem;
                    font-weight: 700;
                    line-height: 1.2;
                    overflow-wrap: anywhere;
                }
                </style>
                """,
                streamlit_module=st,
            )
            p50_label = escape_html_text(_format_eur(p50))
            p10_label = escape_html_text(
                _format_eur(p10) if p10 > 0 else "nicht verfügbar"
            )
            p90_label = escape_html_text(
                _format_eur(p90) if p90 > 0 else "nicht verfügbar"
            )
            render_static_html(
                (
                    "<div class='salary-main-cards-grid'>"
                    f"<div class='salary-main-card'><div class='salary-main-card-label'>p50</div><div class='salary-main-card-value'>{p50_label}</div></div>"
                    f"<div class='salary-main-card'><div class='salary-main-card-label'>p10</div><div class='salary-main-card-value'>{p10_label}</div></div>"
                    f"<div class='salary-main-card'><div class='salary-main-card-label'>p90</div><div class='salary-main-card-value'>{p90_label}</div></div>"
                    "</div>"
                ),
                streamlit_module=st,
            )
        st.caption(
            _salary_copy("quality_caveat", language=language, quality=quality_label)
        )
        if answers_count > 0:
            st.caption(f"Berücksichtigte Antworten: {answers_count}.")
        with st.expander("Einordnung", expanded=False):
            st.caption(_salary_copy("context_caveat", language=language))
        show_debug = str(
            st.session_state.get(SSKey.UI_MODE.value, "standard")
        ).strip().lower() == "expert" or bool(
            st.session_state.get(SSKey.DEBUG.value, False)
        )
        if show_debug and confidence_note:
            with st.expander("Technische Prognose-Diagnose", expanded=False):
                st.caption(confidence_note)


def render_salary_forecast_step_sections(
    *,
    influence_factors_slot: Callable[[], None],
    scenario_controls_slot: Callable[[], None],
    forecast_result_slot: Callable[[], None],
    salary_result: dict[str, Any] | None = None,
    source_counts: dict[str, int] | None = None,
    source_mix_chart_key: str = "salary_source_mix_chart",
) -> None:
    """Render the shared three-section salary forecast layout for wizard steps."""

    with st.expander("Eingaben und Szenario anpassen", expanded=False):
        factors_col, scenario_col = st.columns((5, 7), gap="large")
        with factors_col:
            st.markdown("##### Einflussfaktoren")
            influence_factors_slot()
        with scenario_col:
            st.markdown("##### Szenario-Steuerung")
            with st.form(
                f"salary.forecast.controls.{source_mix_chart_key}",
                clear_on_submit=False,
            ):
                scenario_controls_slot()
                st.form_submit_button(
                    "Prognose aktualisieren",
                    type="primary",
                    width="stretch",
                )

    with st.expander("Quellenmix und Wirkungstreiber", expanded=False):
        mix_col, driver_col = st.columns(2, gap="large")
        with mix_col:
            st.markdown("##### Quellenmix")
            _render_source_mix_pie(
                source_counts=source_counts,
                chart_key=source_mix_chart_key,
            )
        with driver_col:
            st.markdown("##### Wirkungstreiber")
            latest_result = st.session_state.get(
                SSKey.SALARY_FORECAST_LAST_RESULT.value, salary_result or {}
            )
            _render_driver_impact_chart(
                salary_result=latest_result if isinstance(latest_result, dict) else {},
                chart_key=f"{source_mix_chart_key}.drivers",
            )

    forecast_result_slot()


def render_role_tasks_salary_forecast_panel(
    *,
    job: JobAdExtract,
    selected_tasks: list[str],
    answers: dict[str, Any],
    model: str,
    language: str,
    store: bool,
    source_counts: dict[str, int] | None = None,
) -> None:
    task_candidates = _unique_texts([*selected_tasks, *job.responsibilities])
    active_tasks = task_candidates

    def _render_influence_factors() -> None:
        nonlocal active_tasks
        active_tasks = _select_salary_factors(
            step_key="role_tasks",
            factor_key="tasks",
            label="Aufgaben für die Prognose",
            options=task_candidates,
            default=task_candidates,
        )
        st.caption(f"Aktive Rollen/Aufgaben: {len(active_tasks)}")
        delta_rows = _build_factor_delta_rows(
            job=job.model_copy(update={"responsibilities": active_tasks}),
            answers=_merge_answers(answers, {"selected_tasks": active_tasks}),
            selected_items=active_tasks,
            field_name="responsibilities",
        )
        _render_factor_delta_chart(
            rows=delta_rows,
            chart_key="role_tasks.salary.factor_delta",
            empty_caption="Einzeleffekte erscheinen, sobald mindestens zwei Aufgaben aktiv sind.",
        )

    def _render_scenario_controls() -> None:
        _render_common_scenario_inputs(job)
        fingerprint = _current_step_forecast_fingerprint(
            step_key="role_tasks",
            job=job,
            selected_inputs=active_tasks,
            model=model,
            language=language,
            store=store,
        )
        if _should_refresh_step_forecast(
            step_key="role_tasks", fingerprint=fingerprint
        ):
            try:
                with st.spinner("Berechne Gehaltsprognose …"):
                    forecast_job = job.model_copy(
                        update={
                            "responsibilities": active_tasks or job.responsibilities,
                        }
                    )
                    st.session_state[SSKey.SALARY_FORECAST_LAST_RESULT.value] = (
                        _build_step_salary_result(
                            step_key="role_tasks",
                            job=forecast_job,
                            answers=_merge_answers(
                                answers, {"selected_tasks": active_tasks}
                            ),
                            inputs={"selected_tasks": active_tasks},
                            input_fingerprint=fingerprint,
                        )
                    )
                _remember_step_forecast_fingerprint(
                    step_key="role_tasks", fingerprint=fingerprint
                )
                st.caption("Prognose automatisch aktualisiert.")
            except Exception as exc:
                LOGGER.warning(
                    "Salary forecast refresh failed for role_tasks: %s",
                    type(exc).__name__,
                )
                _render_salary_forecast_recovery(
                    step_key="role_tasks",
                    language=language,
                    exc=exc,
                )
        else:
            st.caption("Prognose ist für die aktuellen Eingaben aktuell.")

    def _render_forecast_result() -> None:
        render_salary_forecast_result_card(
            salary_result=st.session_state.get(
                SSKey.SALARY_FORECAST_LAST_RESULT.value, {}
            ),
            empty_message=_salary_copy("empty", language=language),
            headline=_salary_copy("forecast_year", language=language),
            language=language,
        )

    render_fragment_pilot_panel(
        step_key="role_tasks",
        panel_id="salary_forecast",
        render_slot=lambda: render_salary_forecast_step_sections(
            influence_factors_slot=_render_influence_factors,
            scenario_controls_slot=_render_scenario_controls,
            forecast_result_slot=_render_forecast_result,
            salary_result=st.session_state.get(
                SSKey.SALARY_FORECAST_LAST_RESULT.value, {}
            ),
            source_counts=source_counts,
            source_mix_chart_key="role_tasks.salary.source_mix",
        ),
    )


def render_benefits_salary_forecast_panel(
    *,
    job: JobAdExtract,
    benefit_candidates: list[str],
    answers: dict[str, Any],
    model: str,
    language: str,
    store: bool,
    source_counts: dict[str, int] | None = None,
) -> None:
    """Render salary forecast for the Benefits step using shared section layout."""
    benefit_options = _unique_texts([*benefit_candidates, *job.benefits])
    active_benefits = benefit_options

    def _factor_candidates() -> list[str]:
        return [
            str(job.job_title or "").strip(),
            str(job.location_city or "").strip(),
            str(job.location_country or "").strip(),
            str(job.seniority_level or "").strip(),
            *(item for item in active_benefits if str(item).strip()),
        ]

    def _render_influence_factors() -> None:
        nonlocal active_benefits
        active_benefits = _select_salary_factors(
            step_key="benefits",
            factor_key="benefits",
            label="Benefits für die Prognose",
            options=benefit_options,
            default=benefit_options,
        )
        selected_count = len([item for item in active_benefits if str(item).strip()])
        st.caption("Diese Faktoren werden in der Prognose berücksichtigt.")
        st.caption(f"Gewählte Benefits: {selected_count}")
        delta_rows = _build_factor_delta_rows(
            job=job.model_copy(update={"benefits": active_benefits}),
            answers=_merge_answers(answers, {"benefits_selected": active_benefits}),
            selected_items=active_benefits,
            field_name="benefits",
        )
        _render_factor_delta_chart(
            rows=delta_rows,
            chart_key="benefits.salary.factor_delta",
            empty_caption="Einzeleffekte erscheinen, sobald mindestens zwei Benefits aktiv sind.",
        )
        if not benefit_options:
            st.caption(
                "Keine Benefits ausgewählt – Prognose wird ohne Benefit-Einflussfaktoren berechnet."
            )

    def _render_scenario_controls() -> None:
        _render_common_scenario_inputs(job)
        fingerprint = _current_step_forecast_fingerprint(
            step_key="benefits",
            job=job,
            selected_inputs=active_benefits,
            model=model,
            language=language,
            store=store,
        )
        if _should_refresh_step_forecast(step_key="benefits", fingerprint=fingerprint):
            try:
                with st.spinner("Berechne Gehaltsprognose …"):
                    forecast_payload = _build_step_salary_result(
                        step_key="benefits",
                        job=job.model_copy(update={"benefits": active_benefits}),
                        answers=_merge_answers(
                            answers, {"benefits_selected": active_benefits}
                        ),
                        inputs={
                            "benefits_selected": active_benefits,
                            "factors": [item for item in _factor_candidates() if item],
                        },
                        input_fingerprint=fingerprint,
                    )
                st.session_state[SSKey.SALARY_FORECAST_LAST_RESULT.value] = (
                    forecast_payload
                )
                _remember_step_forecast_fingerprint(
                    step_key="benefits", fingerprint=fingerprint
                )
                st.caption("Prognose automatisch aktualisiert.")
            except Exception as exc:
                LOGGER.warning(
                    "Salary forecast refresh failed for benefits: %s",
                    type(exc).__name__,
                )
                _render_salary_forecast_recovery(
                    step_key="benefits",
                    language=language,
                    exc=exc,
                )
        else:
            st.caption("Prognose ist für die aktuellen Eingaben aktuell.")

    def _render_forecast_result() -> None:
        render_salary_forecast_result_card(
            salary_result=st.session_state.get(
                SSKey.SALARY_FORECAST_LAST_RESULT.value, {}
            ),
            empty_message=_salary_copy("empty", language=language),
            headline=_salary_copy("forecast_year", language=language),
            use_main_card_layout=True,
            language=language,
        )

    render_fragment_pilot_panel(
        step_key="benefits",
        panel_id="salary_forecast",
        render_slot=lambda: render_salary_forecast_step_sections(
            influence_factors_slot=_render_influence_factors,
            scenario_controls_slot=_render_scenario_controls,
            forecast_result_slot=_render_forecast_result,
            salary_result=st.session_state.get(
                SSKey.SALARY_FORECAST_LAST_RESULT.value, {}
            ),
            source_counts=source_counts,
            source_mix_chart_key="benefits.salary.source_mix",
        ),
    )


def render_skills_salary_forecast_panel(
    *,
    job: JobAdExtract,
    selected_skills: list[str],
    selected_role_tasks: list[str],
    answers: dict[str, Any],
    model: str,
    language: str,
    store: bool,
    source_counts: dict[str, int] | None = None,
) -> None:
    """Render salary forecast for Skills step using shared section layout."""

    priority_must_key = f"{SSKey.SKILLS_SELECTED.value}.priority.must"
    priority_nice_key = f"{SSKey.SKILLS_SELECTED.value}.priority.nice"
    semantic_context = resolve_esco_semantic_context(st.session_state)
    esco_titles = (
        _unique_texts(
            [
                *_extract_esco_skill_titles(
                    st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_MUST.value, [])
                ),
                *_extract_esco_skill_titles(
                    st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_NICE.value, [])
                ),
            ]
        )
        if semantic_context.can_use_esco_normalization
        else []
    )
    unique_selected_skills = _unique_texts(
        [
            *selected_skills,
            *job.must_have_skills,
            *job.nice_to_have_skills,
            *job.tech_stack,
            *esco_titles,
        ]
    )
    active_role_tasks = _unique_texts([*selected_role_tasks, *job.responsibilities])

    def _read_priority_selection() -> tuple[list[str], list[str]]:
        must_payload = st.session_state.get(priority_must_key, unique_selected_skills)
        nice_payload = st.session_state.get(priority_nice_key, [])
        must_priority = [
            str(skill).strip()
            for skill in (must_payload if isinstance(must_payload, list) else [])
            if str(skill).strip() in unique_selected_skills
        ]
        nice_priority = [
            str(skill).strip()
            for skill in (nice_payload if isinstance(nice_payload, list) else [])
            if str(skill).strip() in unique_selected_skills
        ]
        nice_set = set(nice_priority)
        must_priority = [skill for skill in must_priority if skill not in nice_set]
        return must_priority, nice_priority

    def _render_influence_factors() -> None:
        default_must = st.session_state.get(priority_must_key, unique_selected_skills)
        must_default = [
            skill
            for skill in (default_must if isinstance(default_must, list) else [])
            if skill in unique_selected_skills
        ]
        default_nice = st.session_state.get(priority_nice_key, [])
        nice_existing = [
            skill
            for skill in (default_nice if isinstance(default_nice, list) else [])
            if skill in unique_selected_skills
        ]
        if (
            priority_must_key not in st.session_state
            and priority_nice_key not in st.session_state
        ):
            must_default = unique_selected_skills
        else:
            existing_keys = {
                *(skill.casefold() for skill in must_default),
                *(skill.casefold() for skill in nice_existing),
            }
            must_default.extend(
                skill
                for skill in unique_selected_skills
                if skill.casefold() not in existing_keys
            )
        chosen_must = st.multiselect(
            "Must-have",
            options=unique_selected_skills,
            default=must_default,
            key=priority_must_key,
        )
        remaining_options = [
            skill for skill in unique_selected_skills if skill not in chosen_must
        ]
        nice_default = [skill for skill in nice_existing if skill in remaining_options]
        chosen_nice = st.multiselect(
            "Nice-to-have",
            options=remaining_options,
            default=nice_default,
            key=priority_nice_key,
        )
        st.caption(f"Must-have: {len(chosen_must)} · Nice-to-have: {len(chosen_nice)}")
        forecast_job = job.model_copy(
            update={
                "must_have_skills": _unique_texts(chosen_must),
                "nice_to_have_skills": _unique_texts(chosen_nice),
                "responsibilities": active_role_tasks or job.responsibilities,
            }
        )
        delta_rows = _build_skill_factor_delta_rows(
            job=forecast_job,
            answers=_merge_answers(
                answers,
                {
                    "must_have_skills": _unique_texts(chosen_must),
                    "nice_to_have_skills": _unique_texts(chosen_nice),
                    "selected_role_tasks": active_role_tasks,
                },
            ),
            must_have_skills=_unique_texts(chosen_must),
            nice_to_have_skills=_unique_texts(chosen_nice),
        )
        _render_factor_delta_chart(
            rows=delta_rows,
            chart_key="skills.salary.factor_delta",
            empty_caption="Einzeleffekte erscheinen, sobald mindestens zwei Skills aktiv sind.",
        )

    def _render_scenario_controls() -> None:
        st.caption("Szenario-Parameter")
        _render_common_scenario_inputs(job)
        must_priority, nice_priority = _read_priority_selection()
        selected_inputs = [
            *(f"Must-have: {skill}" for skill in must_priority),
            *(f"Nice-to-have: {skill}" for skill in nice_priority),
            *active_role_tasks,
        ]
        fingerprint = _current_step_forecast_fingerprint(
            step_key="skills",
            job=job,
            selected_inputs=selected_inputs,
            model=model,
            language=language,
            store=store,
        )
        if _should_refresh_step_forecast(step_key="skills", fingerprint=fingerprint):
            try:
                with st.spinner("Berechne Gehaltsprognose …"):
                    forecast_job = job.model_copy(
                        update={
                            "must_have_skills": must_priority,
                            "nice_to_have_skills": nice_priority,
                            "responsibilities": active_role_tasks
                            or job.responsibilities,
                        }
                    )
                    st.session_state[SSKey.SALARY_FORECAST_LAST_RESULT.value] = (
                        _build_step_salary_result(
                            step_key="skills",
                            job=forecast_job,
                            answers=_merge_answers(
                                answers,
                                {
                                    "must_have_skills": must_priority,
                                    "nice_to_have_skills": nice_priority,
                                    "selected_role_tasks": active_role_tasks,
                                },
                            ),
                            inputs={
                                "must_have_skills": must_priority,
                                "nice_to_have_skills": nice_priority,
                                "selected_role_tasks": active_role_tasks,
                            },
                            input_fingerprint=fingerprint,
                        )
                    )
                _remember_step_forecast_fingerprint(
                    step_key="skills", fingerprint=fingerprint
                )
                st.caption("Prognose automatisch aktualisiert.")
            except Exception as exc:
                LOGGER.warning(
                    "Salary forecast refresh failed for skills: %s",
                    type(exc).__name__,
                )
                _render_salary_forecast_recovery(
                    step_key="skills",
                    language=language,
                    exc=exc,
                )
        else:
            st.caption("Prognose ist für die aktuellen Eingaben aktuell.")

    def _render_forecast_result() -> None:
        render_salary_forecast_result_card(
            salary_result=st.session_state.get(
                SSKey.SALARY_FORECAST_LAST_RESULT.value, {}
            ),
            empty_message=_salary_copy("empty", language=language),
            headline=_salary_copy("forecast_year", language=language),
            language=language,
        )

    render_fragment_pilot_panel(
        step_key="skills",
        panel_id="salary_forecast",
        render_slot=lambda: render_salary_forecast_step_sections(
            influence_factors_slot=_render_influence_factors,
            scenario_controls_slot=_render_scenario_controls,
            forecast_result_slot=_render_forecast_result,
            salary_result=st.session_state.get(
                SSKey.SALARY_FORECAST_LAST_RESULT.value, {}
            ),
            source_counts=source_counts,
            source_mix_chart_key="skills.salary.source_mix",
        ),
    )
