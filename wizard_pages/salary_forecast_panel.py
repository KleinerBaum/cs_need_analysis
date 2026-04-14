from __future__ import annotations

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


def render_role_tasks_salary_forecast_panel(
    *,
    job: JobAdExtract,
    selected_tasks: list[str],
    model: str,
    language: str,
    store: bool,
) -> None:
    """Render a compact Role & Tasks salary forecast with explicit update trigger."""

    st.markdown("#### Gehaltsprognose (€)")
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

    selected_count = len([item for item in selected_tasks if str(item).strip()])
    st.caption(f"Ausgewählte Rollen/Aufgaben: {selected_count}")

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
        st.info("Noch keine Gehaltsprognose vorhanden. Bitte Prognose aktualisieren.")
