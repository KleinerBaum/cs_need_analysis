from __future__ import annotations

from collections.abc import Callable
from typing import Any

import plotly.graph_objects as go  # type: ignore[import-untyped]
import streamlit as st

from constants import SSKey
from llm_client import generate_role_tasks_salary_forecast
from salary.engine import compute_salary_forecast
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
from salary.types import SalaryScenarioInputs, SalaryScenarioOverrides
from schemas import JobAdExtract


def _safe_int(value: Any) -> int:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return 0


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


def _build_salary_forecast_snapshot(
    job: JobAdExtract,
    answers: dict[str, Any],
    *,
    scenario_name: str = "base",
    scenario_overrides: SalaryScenarioOverrides | None = None,
) -> dict[str, Any]:
    overrides = scenario_overrides or SalaryScenarioOverrides()
    forecast = compute_salary_forecast(
        job_extract=job,
        answers=answers,
        scenario_overrides=overrides,
        scenario_inputs=SalaryScenarioInputs(
            location_city_override=str(
                st.session_state.get(
                    SSKey.SALARY_SCENARIO_LOCATION_CITY_OVERRIDE.value, ""
                )
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
                st.session_state.get(
                    SSKey.SALARY_SCENARIO_REMOTE_SHARE_PERCENT.value, 0
                )
            ),
        ),
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
    esco_titles = unique_skills(
        [
            *_extract_esco_skill_titles(
                st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_MUST.value, [])
            ),
            *_extract_esco_skill_titles(
                st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_NICE.value, [])
            ),
        ]
    )
    candidate_skills = build_candidate_skill_pool(
        job=job, esco_skill_titles=esco_titles
    )

    skills_add = st.multiselect(
        "Skills hinzufügen",
        options=candidate_skills,
        default=st.session_state.get(SSKey.SALARY_SCENARIO_SKILLS_ADD.value, []),
        key=SSKey.SALARY_SCENARIO_SKILLS_ADD.value,
    )
    skills_remove = st.multiselect(
        "Skills entfernen",
        options=candidate_skills,
        default=st.session_state.get(SSKey.SALARY_SCENARIO_SKILLS_REMOVE.value, []),
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
    return forecast_job, candidate_skills


def render_salary_forecast_panel(job: JobAdExtract, answers: dict[str, Any]) -> None:
    _apply_pending_salary_scenario_update()
    st.subheader("Gehaltsprognose (indikativ)")
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
    scenario_inputs = SalaryScenarioInputs(
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
    forecast = compute_salary_forecast(
        job_extract=forecast_job,
        answers=answers,
        scenario_overrides=scenario_overrides,
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
        st.caption("Bandbreite und p50 sind indikative Richtwerte (kein Garantiewert).")
        st.caption(
            f"Datenqualität: {quality_percent}% (`{forecast.quality.kind}`) – signalisiert Datenabdeckung und Mapping-Treffer, nicht Prognosegenauigkeit."
        )

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

        st.markdown("**Scenario Table**")
        st.dataframe(scenario_rows, hide_index=True, width="stretch")

    st.session_state[SSKey.SALARY_FORECAST_LAST_RESULT.value] = (
        _build_salary_forecast_snapshot(
            forecast_job,
            answers,
            scenario_name=selected_scenario,
            scenario_overrides=scenario_overrides,
        )
    )


def _format_eur(value: int) -> str:
    return f"{value:,} €".replace(",", ".")


def render_salary_forecast_step_sections(
    *,
    influence_factors_slot: Callable[[], None],
    scenario_controls_slot: Callable[[], None],
    forecast_result_slot: Callable[[], None],
) -> None:
    """Render the shared three-section salary forecast layout for wizard steps."""

    left_col, right_col = st.columns((3, 2), gap="large")
    with left_col:
        with st.container(border=True):
            st.markdown("#### Einflussfaktoren")
            influence_factors_slot()

    with right_col:
        with st.container(border=True):
            st.markdown("#### Szenario-Steuerung")
            scenario_controls_slot()
        with st.container(border=True):
            st.markdown("#### Prognose-Ergebnis")
            forecast_result_slot()


def render_role_tasks_salary_forecast_panel(
    *,
    job: JobAdExtract,
    selected_tasks: list[str],
    model: str,
    language: str,
    store: bool,
) -> None:
    selected_count = len([item for item in selected_tasks if str(item).strip()])

    def _render_influence_factors() -> None:
        st.caption(f"Ausgewählte Rollen/Aufgaben: {selected_count}")

    def _render_scenario_controls() -> None:
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
        if st.button("Prognose aktualisieren", width="stretch"):
            with st.spinner("Berechne Gehaltsprognose …"):
                forecast, usage = generate_role_tasks_salary_forecast(
                    job_title=str(job.job_title or "").strip(),
                    location_city=str(job.location_city or "").strip(),
                    location_country=str(job.location_country or "").strip(),
                    seniority=str(
                        st.session_state.get(
                            SSKey.SALARY_SCENARIO_SENIORITY_OVERRIDE.value,
                            job.seniority_level or "",
                        )
                    ).strip(),
                    selected_tasks=selected_tasks,
                    search_radius_km=_safe_int(
                        st.session_state.get(SSKey.SALARY_SCENARIO_RADIUS_KM.value, 50)
                    ),
                    remote_share_percent=_safe_int(
                        st.session_state.get(
                            SSKey.SALARY_SCENARIO_REMOTE_SHARE_PERCENT.value, 0
                        )
                    ),
                    model=model,
                    language=language,
                    store=store,
                )
            st.session_state[SSKey.SALARY_FORECAST_LAST_RESULT.value] = {
                "forecast": {"p50": forecast.yearly_salary_eur},
                "currency": "EUR",
                "period": "year",
                "confidence_note": forecast.confidence_note,
                "inputs": {
                    "selected_tasks": selected_tasks,
                    "radius_km": _safe_int(
                        st.session_state.get(SSKey.SALARY_SCENARIO_RADIUS_KM.value, 50)
                    ),
                    "remote_share_percent": _safe_int(
                        st.session_state.get(
                            SSKey.SALARY_SCENARIO_REMOTE_SHARE_PERCENT.value, 0
                        )
                    ),
                    "seniority_override": str(
                        st.session_state.get(
                            SSKey.SALARY_SCENARIO_SENIORITY_OVERRIDE.value, ""
                        )
                    ).strip(),
                },
                "usage": usage or {},
            }

    def _render_forecast_result() -> None:
        last_result = st.session_state.get(SSKey.SALARY_FORECAST_LAST_RESULT.value, {})
        forecast_payload = (
            last_result.get("forecast", {}) if isinstance(last_result, dict) else {}
        )
        p50_value = _safe_int(forecast_payload.get("p50"))
        if p50_value > 0:
            st.metric("Gehaltsprognose (Jahr)", _format_eur(p50_value))
            note = str(last_result.get("confidence_note") or "").strip()
            if note:
                st.caption(note)
        else:
            st.info(
                "Noch keine Gehaltsprognose vorhanden. Bitte Prognose aktualisieren."
            )

    render_salary_forecast_step_sections(
        influence_factors_slot=_render_influence_factors,
        scenario_controls_slot=_render_scenario_controls,
        forecast_result_slot=_render_forecast_result,
    )


def render_benefits_salary_forecast_panel(
    *,
    job: JobAdExtract,
    benefit_candidates: list[str],
    answers: dict[str, Any],
    model: str,
    language: str,
    store: bool,
) -> None:
    """Render salary forecast for the Benefits step using shared section layout."""
    selected_benefits = list(benefit_candidates)

    def _factor_candidates() -> list[str]:
        return [
            str(job.job_title or "").strip(),
            str(job.location_city or "").strip(),
            str(job.location_country or "").strip(),
            str(job.seniority_level or "").strip(),
            *(item for item in selected_benefits if str(item).strip()),
        ]

    def _render_influence_factors() -> None:
        nonlocal selected_benefits
        if benefit_candidates:
            st.caption(
                "Gewählte Benefits als Einflussfaktoren für die Prognose (Review-Ansicht)."
            )
            column_count = min(3, max(2, len(benefit_candidates) // 5 + 1))
            review_columns = st.columns(column_count, gap="small")
            for index, benefit in enumerate(benefit_candidates):
                with review_columns[index % column_count]:
                    st.markdown(f"- {benefit}")
            with st.expander("Auswahl anpassen (optional)"):
                selected_benefits = st.multiselect(
                    "Einflussfaktoren: Benefits",
                    options=benefit_candidates,
                    default=benefit_candidates,
                    help=(
                        "Nur bei Bedarf anpassen. Standardmäßig fließen alle gewählten "
                        "Benefits als Einflussfaktoren ein."
                    ),
                )
        selected_factor_count = len([item for item in _factor_candidates() if item])
        st.caption(f"Einbezogene Faktoren (inkl. Benefits): {selected_factor_count}")

    def _render_scenario_controls() -> None:
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
        if st.button(
            "Prognose aktualisieren", width="stretch", key="benefits.salary.update"
        ):
            with st.spinner("Berechne Gehaltsprognose …"):
                forecast, usage = generate_role_tasks_salary_forecast(
                    job_title=str(job.job_title or "").strip(),
                    location_city=str(job.location_city or "").strip(),
                    location_country=str(job.location_country or "").strip(),
                    seniority=str(
                        st.session_state.get(
                            SSKey.SALARY_SCENARIO_SENIORITY_OVERRIDE.value,
                            job.seniority_level or "",
                        )
                    ).strip(),
                    selected_tasks=[item for item in _factor_candidates() if item],
                    search_radius_km=_safe_int(
                        st.session_state.get(SSKey.SALARY_SCENARIO_RADIUS_KM.value, 50)
                    ),
                    remote_share_percent=_safe_int(
                        st.session_state.get(
                            SSKey.SALARY_SCENARIO_REMOTE_SHARE_PERCENT.value, 0
                        )
                    ),
                    model=model,
                    language=language,
                    store=store,
                )
            st.session_state[SSKey.SALARY_FORECAST_LAST_RESULT.value] = {
                "forecast": {"p50": forecast.yearly_salary_eur},
                "currency": "EUR",
                "period": "year",
                "confidence_note": forecast.confidence_note,
                "inputs": {
                    "benefits_selected": selected_benefits,
                    "factors": [item for item in _factor_candidates() if item],
                    "answers_count": len(answers),
                    "radius_km": _safe_int(
                        st.session_state.get(SSKey.SALARY_SCENARIO_RADIUS_KM.value, 50)
                    ),
                    "remote_share_percent": _safe_int(
                        st.session_state.get(
                            SSKey.SALARY_SCENARIO_REMOTE_SHARE_PERCENT.value, 0
                        )
                    ),
                    "seniority_override": str(
                        st.session_state.get(
                            SSKey.SALARY_SCENARIO_SENIORITY_OVERRIDE.value, ""
                        )
                    ).strip(),
                },
                "usage": usage or {},
            }

    def _render_forecast_result() -> None:
        last_result = st.session_state.get(SSKey.SALARY_FORECAST_LAST_RESULT.value, {})
        forecast_payload = (
            last_result.get("forecast", {}) if isinstance(last_result, dict) else {}
        )
        p50_value = _safe_int(forecast_payload.get("p50"))
        if p50_value > 0:
            st.metric("Erwartetes Jahresgehalt", _format_eur(p50_value))
            note = str(last_result.get("confidence_note") or "").strip()
            if note:
                st.caption(note)
        else:
            st.info(
                "Noch keine Gehaltsprognose vorhanden. Bitte Prognose aktualisieren."
            )

    render_salary_forecast_step_sections(
        influence_factors_slot=_render_influence_factors,
        scenario_controls_slot=_render_scenario_controls,
        forecast_result_slot=_render_forecast_result,
    )


def render_skills_salary_forecast_panel(
    *,
    job: JobAdExtract,
    selected_skills: list[str],
    selected_role_tasks: list[str],
    model: str,
    language: str,
    store: bool,
) -> None:
    """Render salary forecast for Skills step using shared section layout."""

    priority_must_key = f"{SSKey.SKILLS_SELECTED.value}.priority.must"
    priority_nice_key = f"{SSKey.SKILLS_SELECTED.value}.priority.nice"
    unique_selected_skills = [
        str(skill).strip() for skill in selected_skills if str(skill).strip()
    ]
    unique_selected_skills = list(dict.fromkeys(unique_selected_skills))

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
        with st.container(border=True):
            st.caption("Skill-Priorisierung")
            default_must = st.session_state.get(priority_must_key, unique_selected_skills)
            must_default = [
                skill
                for skill in (default_must if isinstance(default_must, list) else [])
                if skill in unique_selected_skills
            ] or unique_selected_skills
            chosen_must = st.multiselect(
                "Must-have",
                options=unique_selected_skills,
                default=must_default,
                key=priority_must_key,
            )
            remaining_options = [
                skill for skill in unique_selected_skills if skill not in chosen_must
            ]
            default_nice = st.session_state.get(priority_nice_key, [])
            nice_default = [
                skill
                for skill in (default_nice if isinstance(default_nice, list) else [])
                if skill in remaining_options
            ]
            chosen_nice = st.multiselect(
                "Nice-to-have",
                options=remaining_options,
                default=nice_default,
                key=priority_nice_key,
            )
            st.caption(f"Must-have: {len(chosen_must)} · Nice-to-have: {len(chosen_nice)}")

    def _render_scenario_controls() -> None:
        with st.container(border=True):
            st.caption("Szenario-Parameter")
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
        if st.button("Gehaltsprognose für Skills berechnen", width="stretch", type="primary"):
            must_priority, nice_priority = _read_priority_selection()
            selected_inputs = [
                *(f"Must-have: {skill}" for skill in must_priority),
                *(f"Nice-to-have: {skill}" for skill in nice_priority),
                *selected_role_tasks,
            ]
            with st.spinner("Berechne Gehaltsprognose …"):
                forecast, usage = generate_role_tasks_salary_forecast(
                    job_title=str(job.job_title or "").strip(),
                    location_city=str(job.location_city or "").strip(),
                    location_country=str(job.location_country or "").strip(),
                    seniority=str(
                        st.session_state.get(
                            SSKey.SALARY_SCENARIO_SENIORITY_OVERRIDE.value,
                            job.seniority_level or "",
                        )
                    ).strip(),
                    selected_tasks=selected_inputs,
                    search_radius_km=_safe_int(
                        st.session_state.get(SSKey.SALARY_SCENARIO_RADIUS_KM.value, 50)
                    ),
                    remote_share_percent=_safe_int(
                        st.session_state.get(
                            SSKey.SALARY_SCENARIO_REMOTE_SHARE_PERCENT.value, 0
                        )
                    ),
                    model=model,
                    language=language,
                    store=store,
                )
            st.session_state[SSKey.SALARY_FORECAST_LAST_RESULT.value] = {
                "forecast": {"p50": forecast.yearly_salary_eur},
                "currency": "EUR",
                "period": "year",
                "confidence_note": forecast.confidence_note,
                "inputs": {
                    "must_have_skills": must_priority,
                    "nice_to_have_skills": nice_priority,
                    "selected_role_tasks": selected_role_tasks,
                },
                "usage": usage or {},
            }

    def _render_forecast_result() -> None:
        salary_result = st.session_state.get(SSKey.SALARY_FORECAST_LAST_RESULT.value, {})
        salary_forecast_payload = (
            salary_result.get("forecast", {}) if isinstance(salary_result, dict) else {}
        )
        p50 = _safe_int(salary_forecast_payload.get("p50"))
        if p50 > 0:
            p10 = _safe_int(salary_forecast_payload.get("p10"))
            p90 = _safe_int(salary_forecast_payload.get("p90"))
            metric_col_main, metric_col_low, metric_col_high = st.columns((2, 1, 1))
            with metric_col_main:
                st.metric("Erwartetes Jahresgehalt (p50)", _format_eur(p50))
            with metric_col_low:
                st.metric("p10", _format_eur(p10) if p10 > 0 else "—")
            with metric_col_high:
                st.metric("p90", _format_eur(p90) if p90 > 0 else "—")
            note = str(salary_result.get("confidence_note") or "").strip()
            if note:
                st.caption(note)
        else:
            st.info("Noch keine Gehaltsprognose vorhanden.")

    render_salary_forecast_step_sections(
        influence_factors_slot=_render_influence_factors,
        scenario_controls_slot=_render_scenario_controls,
        forecast_result_slot=_render_forecast_result,
    )
