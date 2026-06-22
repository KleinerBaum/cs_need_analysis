"""Wizard base utilities (page model + navigation helpers)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import json
from typing import (
    Any,
    TYPE_CHECKING,
    Callable,
    List,
    Literal,
    Mapping,
    NotRequired,
    Sequence,
    TypedDict,
    cast,
)

import streamlit as st

from constants import (
    COMPLETION_STATE_NOT_STARTED,
    COMPLETION_STATE_PREFIX_TOKENS,
    DEFAULT_ESCO_DATA_SOURCE_MODE,
    DEFAULT_ESCO_RELEASE_LANE,
    DEFAULT_ESCO_SELECTED_VERSION,
    ESCO_API_MODES,
    ESCO_DATA_SOURCE_MODES,
    ESCO_RELEASE_LANE_PREVIEW,
    ESCO_RELEASE_LANE_SELECTED_VERSION,
    ESCO_RELEASE_LANE_STABLE,
    FactKey,
    SSKey,
    STEPS,
    STEP_KEY_INTRO,
    UI_PREFERENCE_ANSWER_MODE,
    UI_PREFERENCE_CONFIDENCE_THRESHOLD,
    UI_PREFERENCE_INFORMATION_DEPTH,
    UI_MODE_DEFAULT,
    UI_MODE_DISPLAY_LABELS,
    UI_MODE_VALUES,
)
from esco_client import EscoClient, EscoClientError, clear_esco_cache
from esco_semantics import (
    normalize_release_lane,
    resolve_fallback_language,
    selected_version_for_release_lane,
    sync_esco_semantic_state,
)
from intake_facts import collect_legacy_facts
from i18n import sync_language_state, sync_streamlit_language_widget, t
from question_dependencies import should_show_question
from question_limits import (
    StepQuestionScope,
    build_step_question_scope_from_plan,
    sync_adaptive_question_limits,
)
from question_progress import AnswerMetaMap
from question_progress import (
    build_answered_lookup,
    build_step_scope_progress_labels,
    compute_question_progress,
)
from schemas import JobAdExtract, Question, QuestionPlan, QuestionStep
from safe_html import escape_html_text, render_static_html
from step_sections import build_section_status_payloads, section_status_summary
from step_status import StepStatusPayload, build_step_status_payload
from state import normalize_ui_preferences
from usage_events import record_step_entered, record_step_submitted
from wizard_pages.salary_forecast import render_sidebar_salary_forecast

if TYPE_CHECKING:
    from salary.types import SalaryEscoContext, SalaryForecastResult, SalaryScenarioInputs


@dataclass(frozen=True)
class SalarySidebarInputRow:
    id: str
    group: str
    label: str
    value: Any
    target: str
    source_label: str
    default_enabled: bool = True
    label_prefix: str = ""
    display_value: str = ""


def _has_meaningful_value(value: object) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, (list, tuple, set, dict)):
        return len(value) > 0
    return True


def _fallback_job_from_session(
    *, answers: Mapping[str, object], source_text: str
) -> JobAdExtract | None:
    seniority_hint = ""
    location_hint = ""
    job_title_hint = ""
    for key, value in answers.items():
        if not _has_meaningful_value(value):
            continue
        normalized_key = str(key).lower()
        value_text = str(value).strip()
        if not seniority_hint and "senior" in normalized_key:
            seniority_hint = value_text
        if not location_hint and (
            "location" in normalized_key or "standort" in normalized_key
        ):
            location_hint = value_text
        if not job_title_hint and (
            "job_title" in normalized_key or "rolle" in normalized_key
        ):
            job_title_hint = value_text

    source_lower = source_text.lower()
    if not seniority_hint:
        for marker in ("principal", "lead", "senior", "junior"):
            if marker in source_lower:
                seniority_hint = marker
                break
    if not job_title_hint and source_text.strip():
        first_line = source_text.strip().splitlines()[0]
        job_title_hint = first_line[:90]

    if not any((seniority_hint, location_hint, job_title_hint, source_text.strip())):
        return None

    return JobAdExtract(
        job_title=job_title_hint or None,
        location_country=location_hint or None,
        seniority_level=seniority_hint or None,
    )


_SALARY_SIDEBAR_FACT_TARGETS: dict[FactKey, tuple[str, str, str]] = {
    FactKey.ROLE_JOB_TITLE: ("Rolle & Standort", "Jobtitel", "job_title"),
    FactKey.COMPANY_LOCATION_CITY: ("Rolle & Standort", "Stadt", "location_city"),
    FactKey.COMPANY_LOCATION_COUNTRY: ("Rolle & Standort", "Land", "location_country"),
    FactKey.COMPANY_REMOTE_POLICY: ("Rolle & Standort", "Remote-Regel", "remote_policy"),
    FactKey.ROLE_SENIORITY_LEVEL: ("Rolle & Standort", "Seniority", "seniority_level"),
    FactKey.ROLE_RESPONSIBILITIES: ("Aufgaben", "Aufgabe", "responsibilities"),
    FactKey.SKILLS_MUST_HAVE_SKILLS: ("Skills", "Must-have", "must_have_skills"),
    FactKey.SKILLS_NICE_TO_HAVE_SKILLS: ("Skills", "Nice-to-have", "nice_to_have_skills"),
    FactKey.SKILLS_CERTIFICATIONS: ("Skills", "Zertifikat", "certifications"),
    FactKey.SKILLS_LANGUAGES: ("Skills", "Sprache", "languages"),
    FactKey.BENEFITS_SALARY_RANGE: ("Benefits", "Gehaltsrahmen", "salary_range"),
    FactKey.BENEFITS_BENEFITS: ("Benefits", "Benefit", "benefits"),
    FactKey.INTERVIEW_RECRUITMENT_STEPS: (
        "Interview",
        "Interview-Schritt",
        "recruitment_steps",
    ),
}
_SALARY_SIDEBAR_LIST_TARGETS = {
    "responsibilities",
    "must_have_skills",
    "nice_to_have_skills",
    "certifications",
    "languages",
    "benefits",
    "recruitment_steps",
}
_SALARY_SIDEBAR_STEP_KEY = "sidebar"


def _json_safe(value: Any) -> Any:
    if hasattr(value, "model_dump"):
        try:
            return value.model_dump(mode="json")
        except Exception:
            return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe(item) for item in value]
    return value


def _stable_sidebar_input_id(*, target: str, source_label: str, value: Any) -> str:
    payload = {
        "target": target,
        "source_label": source_label,
        "value": _json_safe(value),
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]


def _stringify_salary_sidebar_value(value: Any) -> str:
    if isinstance(value, Mapping):
        if {"min", "max", "currency", "period"} & set(value):
            salary_min = value.get("min")
            salary_max = value.get("max")
            currency = str(value.get("currency") or "EUR").strip()
            period = str(value.get("period") or "").strip()
            return f"{salary_min or '—'} bis {salary_max or '—'} {currency} {period}".strip()
        if "name" in value:
            return str(value.get("name") or "").strip()
        if "title" in value:
            return str(value.get("title") or "").strip()
    return str(value).strip()


def _append_salary_sidebar_row(
    rows: list[SalarySidebarInputRow],
    *,
    group: str,
    label_prefix: str,
    value: Any,
    target: str,
    source_label: str,
) -> None:
    if not _has_meaningful_value(value):
        return
    if target in _SALARY_SIDEBAR_LIST_TARGETS and isinstance(value, list):
        for item in value:
            _append_salary_sidebar_row(
                rows,
                group=group,
                label_prefix=label_prefix,
                value=item,
                target=target,
                source_label=source_label,
            )
        return
    value_label = _stringify_salary_sidebar_value(value)
    if not value_label:
        return
    row_id = _stable_sidebar_input_id(
        target=target, source_label=source_label, value=value
    )
    if any(row.id == row_id for row in rows):
        return
    rows.append(
        SalarySidebarInputRow(
            id=row_id,
            group=group,
            label=f"{label_prefix}: {value_label}",
            value=_json_safe(value),
            target=target,
            source_label=source_label,
            label_prefix=label_prefix,
            display_value=value_label,
        )
    )


def _append_sidebar_selected_state_rows(rows: list[SalarySidebarInputRow]) -> None:
    selected_sources = (
        (
            SSKey.ROLE_TASKS_SELECTED,
            "Aufgaben",
            "Ausgewählte Aufgabe",
            "responsibilities",
            "Manual task selection",
        ),
        (
            SSKey.SKILLS_SELECTED,
            "Skills",
            "Ausgewählter Skill",
            "must_have_skills",
            "Manual skill selection",
        ),
        (
            SSKey.BENEFITS_SELECTED,
            "Benefits",
            "Ausgewählter Benefit",
            "benefits",
            "Manual benefit selection",
        ),
    )
    for state_key, group, label_prefix, target, source_label in selected_sources:
        raw_values = st.session_state.get(state_key.value, [])
        if not isinstance(raw_values, list):
            continue
        for value in raw_values:
            _append_salary_sidebar_row(
                rows,
                group=group,
                label_prefix=label_prefix,
                value=value,
                target=target,
                source_label=source_label,
            )


def _append_sidebar_esco_rows(rows: list[SalarySidebarInputRow]) -> None:
    occupation = st.session_state.get(SSKey.ESCO_OCCUPATION_SELECTED.value)
    if isinstance(occupation, Mapping):
        uri = str(occupation.get("uri") or "").strip()
        title = str(occupation.get("title") or occupation.get("preferredLabel") or "").strip()
        if uri:
            _append_salary_sidebar_row(
                rows,
                group="ESCO",
                label_prefix="Occupation",
                value={"uri": uri, "title": title or uri},
                target="esco_occupation_uri",
                source_label="ESCO occupation anchor",
            )

    for state_key, target, label_prefix in (
        (SSKey.ESCO_SKILLS_SELECTED_MUST, "esco_skill_uri_must", "ESCO Must-have"),
        (SSKey.ESCO_SKILLS_SELECTED_NICE, "esco_skill_uri_nice", "ESCO Nice-to-have"),
    ):
        raw_items = st.session_state.get(state_key.value, [])
        if not isinstance(raw_items, list):
            continue
        for item in raw_items:
            if not isinstance(item, Mapping):
                continue
            uri = str(item.get("uri") or "").strip()
            title = str(item.get("title") or item.get("preferredLabel") or "").strip()
            if uri:
                _append_salary_sidebar_row(
                    rows,
                    group="ESCO",
                    label_prefix=label_prefix,
                    value={"uri": uri, "title": title or uri},
                    target=target,
                    source_label="ESCO skill selection",
                )


def _append_sidebar_scenario_rows(rows: list[SalarySidebarInputRow]) -> None:
    scenario_values = (
        (
            SSKey.SALARY_SCENARIO_LOCATION_CITY_OVERRIDE,
            "Stadt-Override",
            "scenario.location_city_override",
        ),
        (
            SSKey.SALARY_SCENARIO_LOCATION_COUNTRY_OVERRIDE,
            "Land-Override",
            "scenario.location_country_override",
        ),
        (
            SSKey.SALARY_SCENARIO_RADIUS_KM,
            "Suchradius",
            "scenario.search_radius_km",
        ),
        (
            SSKey.SALARY_SCENARIO_REMOTE_SHARE_PERCENT,
            "Remote Share",
            "scenario.remote_share_percent",
        ),
        (
            SSKey.SALARY_SCENARIO_SENIORITY_OVERRIDE,
            "Seniority-Override",
            "scenario.seniority_override",
        ),
    )
    for state_key, label_prefix, target in scenario_values:
        value = st.session_state.get(state_key.value)
        if state_key == SSKey.SALARY_SCENARIO_RADIUS_KM:
            value = value if value is not None else 50
        if state_key == SSKey.SALARY_SCENARIO_REMOTE_SHARE_PERCENT:
            value = value if value is not None else 0
        _append_salary_sidebar_row(
            rows,
            group="Szenario",
            label_prefix=label_prefix,
            value=value,
            target=target,
            source_label="Salary scenario controls",
        )


def _build_sidebar_salary_input_rows() -> list[SalarySidebarInputRow]:
    rows: list[SalarySidebarInputRow] = []
    for fact_key, value in collect_legacy_facts(st.session_state).items():
        target_config = _SALARY_SIDEBAR_FACT_TARGETS.get(fact_key)
        if target_config is None:
            continue
        group, label_prefix, target = target_config
        _append_salary_sidebar_row(
            rows,
            group=group,
            label_prefix=label_prefix,
            value=value,
            target=target,
            source_label="Stored vacancy fact",
        )
    _append_sidebar_selected_state_rows(rows)
    _append_sidebar_esco_rows(rows)
    if rows:
        _append_sidebar_scenario_rows(rows)
    return rows


def _sync_sidebar_salary_input_selections(
    rows: Sequence[SalarySidebarInputRow],
) -> dict[str, bool]:
    raw_selections = st.session_state.get(SSKey.SALARY_FORECAST_INPUT_SELECTIONS.value)
    existing = raw_selections if isinstance(raw_selections, dict) else {}
    valid_ids = {row.id for row in rows}
    selections = {
        row.id: bool(existing.get(row.id, row.default_enabled))
        for row in rows
        if row.id in valid_ids
    }
    st.session_state[SSKey.SALARY_FORECAST_INPUT_SELECTIONS.value] = selections
    return selections


def _sidebar_salary_fingerprint(
    *,
    rows: Sequence[SalarySidebarInputRow],
    selections: Mapping[str, bool],
) -> str:
    payload = {
        "rows": [
            {
                "id": row.id,
                "target": row.target,
                "value": _json_safe(row.value),
                "enabled": bool(selections.get(row.id, row.default_enabled)),
            }
            for row in rows
        ]
    }
    serialized = json.dumps(payload, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _selected_sidebar_rows(
    rows: Sequence[SalarySidebarInputRow],
    selections: Mapping[str, bool],
) -> list[SalarySidebarInputRow]:
    return [row for row in rows if bool(selections.get(row.id, row.default_enabled))]


def _active_sidebar_esco_context(
    rows: Sequence[SalarySidebarInputRow],
    selections: Mapping[str, bool],
) -> "SalaryEscoContext":
    from salary.types import SalaryEscoContext

    active_rows = _selected_sidebar_rows(rows, selections)
    occupation_uri = next(
        (
            str(row.value.get("uri") or "").strip()
            for row in active_rows
            if row.target == "esco_occupation_uri" and isinstance(row.value, Mapping)
        ),
        "",
    )
    skill_uris_must = [
        str(row.value.get("uri") or "").strip()
        for row in active_rows
        if row.target == "esco_skill_uri_must" and isinstance(row.value, Mapping)
    ]
    skill_uris_nice = [
        str(row.value.get("uri") or "").strip()
        for row in active_rows
        if row.target == "esco_skill_uri_nice" and isinstance(row.value, Mapping)
    ]
    esco_config = st.session_state.get(SSKey.ESCO_CONFIG.value, {})
    esco_version = (
        str(esco_config.get("selected_version") or "").strip()
        if isinstance(esco_config, Mapping)
        else ""
    )
    return SalaryEscoContext(
        occupation_uri=occupation_uri or None,
        skill_uris_must=list(dict.fromkeys(uri for uri in skill_uris_must if uri)),
        skill_uris_nice=list(dict.fromkeys(uri for uri in skill_uris_nice if uri)),
        esco_version=esco_version or None,
    )


def _active_sidebar_scenario_inputs(
    rows: Sequence[SalarySidebarInputRow],
    selections: Mapping[str, bool],
) -> "SalaryScenarioInputs":
    from salary.types import SalaryScenarioInputs

    active_by_target = {
        row.target: row.value
        for row in _selected_sidebar_rows(rows, selections)
        if row.target.startswith("scenario.")
    }
    return SalaryScenarioInputs(
        location_city_override=str(
            active_by_target.get("scenario.location_city_override") or ""
        ).strip()
        or None,
        location_country_override=str(
            active_by_target.get("scenario.location_country_override") or ""
        ).strip()
        or None,
        search_radius_km=_safe_sidebar_int(
            active_by_target.get("scenario.search_radius_km"), default=50
        ),
        remote_share_percent=(
            _safe_sidebar_int(active_by_target.get("scenario.remote_share_percent"))
            if "scenario.remote_share_percent" in active_by_target
            else None
        ),
    )


def _safe_sidebar_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(round(float(value)))
    except (TypeError, ValueError):
        return default


def _sidebar_job_and_answers(
    *,
    base_job: JobAdExtract | None,
    rows: Sequence[SalarySidebarInputRow],
    selections: Mapping[str, bool],
    source_text: str,
) -> tuple[JobAdExtract | None, dict[str, Any]]:
    active_rows = _selected_sidebar_rows(rows, selections)
    answers = {
        row.id: row.value
        for row in active_rows
        if not row.target.startswith(("esco_", "scenario."))
    }
    fallback_job = base_job or _fallback_job_from_session(
        answers=answers, source_text=source_text
    )
    has_forecast_signal = any(
        not row.target.startswith("scenario.") for row in active_rows
    )
    if fallback_job is None and not has_forecast_signal:
        return None, answers
    updates: dict[str, Any] = {}
    list_updates: dict[str, list[Any]] = {}
    for row in active_rows:
        target = row.target
        if target.startswith(("esco_", "scenario.")):
            continue
        if target in _SALARY_SIDEBAR_LIST_TARGETS:
            list_updates.setdefault(target, []).append(row.value)
        elif target == "salary_range":
            updates[target] = row.value
        else:
            updates[target] = row.value

    for target, values in list_updates.items():
        if target == "recruitment_steps":
            normalized_steps = []
            for value in values:
                if isinstance(value, Mapping):
                    name = str(value.get("name") or "").strip()
                    if name:
                        details = str(value.get("details") or "").strip() or None
                        normalized_steps.append({"name": name, "details": details})
                else:
                    name = str(value or "").strip()
                    if name:
                        normalized_steps.append({"name": name})
            updates[target] = normalized_steps
            continue
        deduped = list(dict.fromkeys(str(value).strip() for value in values if str(value).strip()))
        updates[target] = deduped

    seniority_override = next(
        (
            str(row.value or "").strip()
            for row in active_rows
            if row.target == "scenario.seniority_override"
        ),
        "",
    )
    if seniority_override:
        updates["seniority_level"] = seniority_override

    try:
        base_values = (fallback_job or JobAdExtract()).model_dump(mode="json")
        merged_job = JobAdExtract.model_validate({**base_values, **updates})
        return merged_job, answers
    except Exception:
        return fallback_job, answers


def _coerce_sidebar_salary_forecast(payload: Any) -> "SalaryForecastResult | None":
    from salary.types import SalaryForecastResult

    if isinstance(payload, SalaryForecastResult):
        return payload
    if not isinstance(payload, Mapping):
        return None
    model_fields = set(SalaryForecastResult.model_fields)
    try:
        return SalaryForecastResult.model_validate(
            {key: value for key, value in payload.items() if key in model_fields}
        )
    except Exception:
        return None


def _compute_sidebar_salary_forecast(
    *,
    job: JobAdExtract | None,
    answers: dict[str, object],
    source_text: str,
    esco_context: "SalaryEscoContext | None" = None,
    scenario_inputs: "SalaryScenarioInputs | None" = None,
) -> "SalaryForecastResult | None":
    forecast_job = job or _fallback_job_from_session(
        answers=answers, source_text=source_text
    )
    if forecast_job is None:
        return None
    try:
        from salary.engine import compute_salary_forecast

        return compute_salary_forecast(
            job_extract=forecast_job,
            answers=answers,
            esco_context=esco_context,
            scenario_inputs=scenario_inputs,
        )
    except Exception:
        return None


@dataclass(frozen=True)
class WizardPage:
    key: str
    title_de: str
    icon: str
    render: Callable[["WizardContext"], None]
    requires_jobspec: bool = False

    @property
    def label(self) -> str:
        title = str(t(self.title_de))
        return f"{self.icon} {title}" if self.icon else title


@dataclass
class WizardContext:
    pages: List[WizardPage]

    def get_current_page_key(self) -> str:
        return st.session_state.get(SSKey.CURRENT_STEP.value, STEPS[0].key)

    def goto(self, key: str) -> None:
        set_current_step(key)

    def next(self) -> None:
        cur = self.get_current_page_key()
        keys = [p.key for p in self.pages]
        if cur in keys:
            i = keys.index(cur)
            if i < len(keys) - 1:
                self.goto(keys[i + 1])

    def prev(self) -> None:
        cur = self.get_current_page_key()
        keys = [p.key for p in self.pages]
        if cur in keys:
            i = keys.index(cur)
            if i > 0:
                self.goto(keys[i - 1])


StepStatus = Literal["complete", "partial", "not_started"]


class SidebarStepProgress(TypedDict):
    key: str
    status: StepStatus
    answered: int
    total: int
    payload: "SidebarStepDetailStatus"


class SidebarStepDetailStatus(TypedDict):
    answered: int
    total: int
    visible_answered: int
    visible_total: int
    overall_answered: int
    overall_total: int
    completion_state: StepStatus
    essentials_answered: int
    essentials_total: int
    missing_essentials: list[str]
    missing_essential_ids: list[str]
    missing_essential_targets: list[dict[str, str]]
    section_answered: NotRequired[int]
    section_total: NotRequired[int]


class EscoMigrationPendingPayload(TypedDict):
    target: str
    uri: str
    concept_type: str
    index: NotRequired[str]
    candidates: NotRequired[list[dict[str, str]]]


def _status_prefix(status: StepStatus) -> str:
    return COMPLETION_STATE_PREFIX_TOKENS.get(
        status, COMPLETION_STATE_PREFIX_TOKENS[COMPLETION_STATE_NOT_STARTED]
    )


def _ensure_salary_forecast_state_defaults() -> None:
    st.session_state.setdefault(SSKey.SALARY_SCENARIO_SKILLS_ADD.value, [])
    st.session_state.setdefault(SSKey.SALARY_SCENARIO_SKILLS_REMOVE.value, [])
    st.session_state.setdefault(SSKey.SALARY_SCENARIO_LOCATION_OVERRIDE.value, "")
    st.session_state.setdefault(SSKey.SALARY_SCENARIO_LOCATION_CITY_OVERRIDE.value, "")
    st.session_state.setdefault(
        SSKey.SALARY_SCENARIO_LOCATION_COUNTRY_OVERRIDE.value, ""
    )
    st.session_state.setdefault(SSKey.SALARY_SCENARIO_RADIUS_KM.value, 50)
    st.session_state.setdefault(SSKey.SALARY_SCENARIO_REMOTE_SHARE_PERCENT.value, 0)
    st.session_state.setdefault(SSKey.SALARY_SCENARIO_SENIORITY_OVERRIDE.value, "")
    st.session_state.setdefault(SSKey.SALARY_SCENARIO_LAB_ROWS.value, [])
    st.session_state.setdefault(SSKey.SALARY_SCENARIO_SELECTED_ROW_ID.value, "")
    st.session_state.setdefault(SSKey.SALARY_SCENARIO_PENDING_SKILLS_ADD.value, None)
    st.session_state.setdefault(SSKey.SALARY_SCENARIO_PENDING_SKILLS_REMOVE.value, None)
    st.session_state.setdefault(
        SSKey.SALARY_SCENARIO_PENDING_LOCATION_CITY_OVERRIDE.value, None
    )
    st.session_state.setdefault(SSKey.SALARY_SCENARIO_PENDING_RADIUS_KM.value, None)
    st.session_state.setdefault(
        SSKey.SALARY_SCENARIO_PENDING_REMOTE_SHARE_PERCENT.value, None
    )
    st.session_state.setdefault(
        SSKey.SALARY_SCENARIO_PENDING_SENIORITY_OVERRIDE.value, None
    )
    st.session_state.setdefault(SSKey.SALARY_SCENARIO_APPLY_PENDING_UPDATE.value, False)
    st.session_state.setdefault(
        SSKey.SALARY_SCENARIO_PENDING_SELECTED_ROW_ID.value, None
    )
    st.session_state.setdefault(SSKey.SALARY_FORECAST_SELECTED_SCENARIO.value, "base")
    st.session_state.setdefault(SSKey.SALARY_FORECAST_LAST_RESULT.value, {})
    st.session_state.setdefault(SSKey.SALARY_FORECAST_INPUT_FINGERPRINT.value, {})
    st.session_state.setdefault(SSKey.SALARY_FORECAST_INPUT_SELECTIONS.value, {})


def set_current_step(key: str, *, sync_navigation: bool = True) -> None:
    previous_key = st.session_state.get(SSKey.CURRENT_STEP.value)
    st.session_state[SSKey.CURRENT_STEP.value] = key
    if previous_key != key:
        record_step_entered(st.session_state, step_key=key)
    if sync_navigation:
        st.session_state[SSKey.NAV_SYNC_PENDING.value] = True


def _get_step_questions(
    plan: QuestionPlan | None,
    step_key: str,
    *,
    answers: dict[str, object] | None = None,
    answer_meta: AnswerMetaMap | None = None,
    job_extract: JobAdExtract | None = None,
    intake_facts: Mapping[str, object] | None = None,
    intake_fact_evidence: Mapping[str, object] | None = None,
    confidence_threshold: float | None = None,
) -> list[Question]:
    return _get_step_question_scope(
        plan,
        step_key,
        answers=answers,
        answer_meta=answer_meta,
        job_extract=job_extract,
        intake_facts=intake_facts,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=confidence_threshold,
    ).selected_questions


def _get_step_question_scope(
    plan: QuestionPlan | None,
    step_key: str,
    *,
    answers: dict[str, object] | None = None,
    answer_meta: AnswerMetaMap | None = None,
    job_extract: JobAdExtract | None = None,
    intake_facts: Mapping[str, object] | None = None,
    intake_fact_evidence: Mapping[str, object] | None = None,
    confidence_threshold: float | None = None,
) -> StepQuestionScope:
    limits_raw = st.session_state.get(SSKey.QUESTION_LIMITS.value, {})
    return build_step_question_scope_from_plan(
        plan,
        step_key,
        question_limits=limits_raw if isinstance(limits_raw, Mapping) else None,
        answers=answers or {},
        answer_meta=answer_meta or {},
        job_extract=job_extract,
        intake_facts=intake_facts,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=confidence_threshold,
    )


def _read_sidebar_confidence_threshold() -> float | None:
    preferences_raw = st.session_state.get(SSKey.UI_PREFERENCES.value, {})
    if not isinstance(preferences_raw, Mapping):
        return None
    try:
        return max(
            0.0,
            min(1.0, float(preferences_raw.get(UI_PREFERENCE_CONFIDENCE_THRESHOLD))),
        )
    except (TypeError, ValueError):
        return None


def _compute_step_statuses(pages: Sequence[WizardPage]) -> list[SidebarStepProgress]:
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN.value)
    plan: QuestionPlan | None = None
    if isinstance(plan_dict, dict):
        try:
            plan = QuestionPlan.model_validate(plan_dict)
        except Exception:
            plan = None

    answers_raw = st.session_state.get(SSKey.ANSWERS.value, {})
    answers = answers_raw if isinstance(answers_raw, dict) else {}
    answer_meta_raw = st.session_state.get(SSKey.ANSWER_META.value, {})
    answer_meta = answer_meta_raw if isinstance(answer_meta_raw, dict) else {}
    intake_facts_raw = st.session_state.get(SSKey.INTAKE_FACTS.value)
    intake_facts = intake_facts_raw if isinstance(intake_facts_raw, dict) else {}
    intake_fact_evidence_raw = st.session_state.get(SSKey.INTAKE_FACT_EVIDENCE.value)
    intake_fact_evidence = (
        intake_fact_evidence_raw if isinstance(intake_fact_evidence_raw, dict) else {}
    )
    confidence_threshold = _read_sidebar_confidence_threshold()
    job_extract_raw = st.session_state.get(SSKey.JOB_EXTRACT.value)
    has_job_extract = bool(job_extract_raw)
    job_extract: JobAdExtract | None = None
    if isinstance(job_extract_raw, JobAdExtract):
        job_extract = job_extract_raw
    elif isinstance(job_extract_raw, dict):
        try:
            job_extract = JobAdExtract.model_validate(job_extract_raw)
        except Exception:
            job_extract = None
    has_brief = bool(st.session_state.get(SSKey.BRIEF.value))

    statuses: list[SidebarStepProgress] = []
    for page in pages:
        question_scope = _get_step_question_scope(
            plan,
            page.key,
            answers=answers,
            answer_meta=cast(AnswerMetaMap, answer_meta),
            job_extract=job_extract,
            intake_facts=intake_facts,
            intake_fact_evidence=intake_fact_evidence,
            confidence_threshold=confidence_threshold,
        )
        questions = question_scope.selected_questions
        step_status = _build_step_status_payload_for_page(
            page_key=page.key,
            questions=questions,
            answers=answers,
            answer_meta=answer_meta,
            job_extract=job_extract,
            intake_facts=intake_facts,
            intake_fact_evidence=intake_fact_evidence,
            confidence_threshold=confidence_threshold,
            visible_questions=question_scope.visible_questions,
        )
        section_answered, section_total = section_status_summary(
            build_section_status_payloads(
                step_key=page.key,
                intake_facts=intake_facts,
                intake_fact_evidence=intake_fact_evidence,
                confidence_threshold=confidence_threshold,
            )
        )
        payload: SidebarStepDetailStatus = {
            "answered": int(step_status["answered"]),
            "total": int(step_status["total"]),
            "visible_answered": int(step_status["answered"]),
            "visible_total": int(step_status["total"]),
            "overall_answered": 0,
            "overall_total": len(questions),
            "completion_state": cast(StepStatus, step_status["completion_state"]),
            "essentials_answered": int(step_status["essentials_answered"]),
            "essentials_total": int(step_status["essentials_total"]),
            "missing_essentials": cast(list[str], step_status["missing_essentials"]),
            "missing_essential_ids": cast(
                list[str], step_status.get("missing_essential_ids", [])
            ),
            "missing_essential_targets": cast(
                list[dict[str, str]],
                step_status.get("missing_essential_targets", []),
            ),
            "section_answered": section_answered,
            "section_total": section_total,
        }
        overall_lookup = build_answered_lookup(
            questions,
            answers,
            cast(AnswerMetaMap, answer_meta),
            job_extract=job_extract,
            intake_facts=intake_facts,
            intake_fact_evidence=intake_fact_evidence,
            confidence_threshold=confidence_threshold,
        )
        overall_progress = compute_question_progress(
            questions,
            answers,
            cast(AnswerMetaMap, answer_meta),
            answered_lookup=overall_lookup,
        )
        payload["overall_answered"] = int(overall_progress["answered"])

        answered = payload["answered"]
        total = payload["total"]

        status: StepStatus = payload["completion_state"]
        if total > 0:
            status = cast(StepStatus, step_status["completion_state"])
        elif page.key == STEP_KEY_INTRO:
            status = "complete"
        elif page.key == "landing":
            source_text = st.session_state.get(SSKey.SOURCE_TEXT.value, "")
            has_source = isinstance(source_text, str) and bool(source_text.strip())
            if has_job_extract and plan is not None:
                status = "complete"
            elif has_source:
                status = "partial"
        elif page.key == "summary":
            if has_brief:
                status = "complete"
            elif any(value for value in answers.values()):
                status = "partial"

        statuses.append(
            {
                "key": page.key,
                "status": status,
                "answered": answered,
                "total": total,
                "payload": payload,
            }
        )
    return statuses


def _build_step_status_payload_for_page(
    *,
    page_key: str,
    questions: list[Question],
    answers: dict[str, object],
    answer_meta: dict[str, object],
    job_extract: JobAdExtract | None = None,
    intake_facts: Mapping[str, object] | None = None,
    intake_fact_evidence: Mapping[str, object] | None = None,
    confidence_threshold: float | None = None,
    visible_questions: list[Question] | None = None,
) -> StepStatusPayload:
    step = QuestionStep(step_key=page_key, title_de=page_key, questions=questions)
    return build_step_status_payload(
        step=step,
        answers=answers,
        answer_meta=cast(AnswerMetaMap, answer_meta),
        should_show_question=should_show_question,
        step_key=page_key,
        job_extract=job_extract,
        intake_facts=intake_facts,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=confidence_threshold,
        visible_questions=visible_questions,
    )


def _render_sidebar_step_status_card(
    *, page: WizardPage, status: SidebarStepDetailStatus
) -> None:
    state = status["completion_state"]
    indicator = _status_prefix(state)
    missing = status["missing_essentials"][:3]
    with st.sidebar.container(border=True):
        st.caption(
            f"{indicator} {page.title_de} · {status['answered']}/{status['total']}"
        )
        scope_labels = build_step_scope_progress_labels(
            visible_answered=status["visible_answered"],
            visible_total=status["visible_total"],
            overall_answered=status["overall_answered"],
            overall_total=status["overall_total"],
        )
        st.caption(scope_labels["visible_label"])
        if scope_labels["has_different_denominator"]:
            st.caption(scope_labels["overall_label"])
        if status.get("section_total", 0):
            st.caption(
                f"Abschnitte: {status.get('section_answered', 0)}/{status['section_total']} geklärt"
            )
        if missing:
            st.caption(f"Missing: {', '.join(missing)}")


def _get_esco_config() -> dict[str, object]:
    raw = st.session_state.get(SSKey.ESCO_CONFIG.value, {})
    config = raw if isinstance(raw, dict) else {}
    raw_view_obsolete = config.get("view_obsolete", False)
    if isinstance(raw_view_obsolete, str):
        normalized = raw_view_obsolete.strip().lower()
        view_obsolete = normalized in {"true", "1", "yes", "on"}
    else:
        view_obsolete = bool(raw_view_obsolete)
    release_lane = normalize_release_lane(
        st.session_state.get(SSKey.ESCO_RELEASE_LANE.value)
        or config.get("release_lane")
        or DEFAULT_ESCO_RELEASE_LANE
    )
    selected_version = str(
        config.get("selected_version") or selected_version_for_release_lane(release_lane)
    ).strip() or DEFAULT_ESCO_SELECTED_VERSION
    language = str(config.get("language") or "de").strip().lower() or "de"
    fallback_language = resolve_fallback_language(
        language,
        config.get("fallback_language"),
    )
    api_mode = str(config.get("api_mode") or "hosted").strip().lower()
    if api_mode not in ESCO_API_MODES:
        api_mode = "hosted"
    data_source_mode = str(
        config.get("data_source_mode") or DEFAULT_ESCO_DATA_SOURCE_MODE
    ).strip().lower()
    if data_source_mode not in ESCO_DATA_SOURCE_MODES:
        data_source_mode = DEFAULT_ESCO_DATA_SOURCE_MODE
    return {
        "base_url": str(config.get("base_url") or "https://ec.europa.eu/esco/api/"),
        "release_lane": release_lane,
        "selected_version": selected_version,
        "language": language,
        "fallback_language": fallback_language,
        "view_obsolete": view_obsolete,
        "api_mode": api_mode,
        "data_source_mode": data_source_mode,
        "index_storage_path": str(config.get("index_storage_path") or "data/esco_index"),
        "index_version": str(config.get("index_version") or selected_version),
    }


def _set_esco_config(
    *,
    release_lane: str,
    selected_version: str,
    view_obsolete: bool,
    language: str,
    fallback_language: str | None = None,
    api_mode: str | None = None,
    data_source_mode: str | None = None,
) -> bool:
    current_config = _get_esco_config()
    normalized_release_lane = normalize_release_lane(release_lane)
    normalized_version = (
        selected_version.strip()
        or selected_version_for_release_lane(normalized_release_lane)
    )
    normalized_language = language.strip().lower() or "de"
    normalized_fallback_language = resolve_fallback_language(
        normalized_language,
        fallback_language or current_config.get("fallback_language"),
    )
    normalized_api_mode = (api_mode or str(current_config.get("api_mode") or "hosted")).strip().lower()
    if normalized_api_mode not in ESCO_API_MODES:
        normalized_api_mode = "hosted"
    normalized_data_source_mode = (
        data_source_mode or str(current_config.get("data_source_mode") or DEFAULT_ESCO_DATA_SOURCE_MODE)
    ).strip().lower()
    if normalized_data_source_mode not in ESCO_DATA_SOURCE_MODES:
        normalized_data_source_mode = DEFAULT_ESCO_DATA_SOURCE_MODE
    changed = (
        current_config["release_lane"] != normalized_release_lane
        or current_config["selected_version"] != normalized_version
        or current_config["language"] != normalized_language
        or current_config["fallback_language"] != normalized_fallback_language
        or bool(current_config["view_obsolete"]) != view_obsolete
        or current_config["api_mode"] != normalized_api_mode
        or current_config["data_source_mode"] != normalized_data_source_mode
    )
    if not changed:
        return False

    st.session_state[SSKey.ESCO_CONFIG.value] = {
        **current_config,
        "release_lane": normalized_release_lane,
        "selected_version": normalized_version,
        "language": normalized_language,
        "fallback_language": normalized_fallback_language,
        "view_obsolete": view_obsolete,
        "api_mode": normalized_api_mode,
        "data_source_mode": normalized_data_source_mode,
    }
    st.session_state[SSKey.ESCO_RELEASE_LANE.value] = normalized_release_lane
    sync_esco_semantic_state(st.session_state)
    clear_esco_cache()
    return True


def _is_legacy_esco_uri(uri: object) -> bool:
    if not isinstance(uri, str):
        return False
    normalized = uri.strip().lower()
    if not normalized:
        return False
    return "data.europa.eu/esco/" not in normalized


def _normalize_esco_migration_pending_payload(
    payload: object,
) -> EscoMigrationPendingPayload | None:
    if not isinstance(payload, Mapping):
        return None
    target = str(payload.get("target") or "").strip()
    uri = str(payload.get("uri") or "").strip()
    concept_type = str(payload.get("concept_type") or "").strip()
    if not target or not uri or not concept_type:
        return None

    normalized: EscoMigrationPendingPayload = {
        "target": target,
        "uri": uri,
        "concept_type": concept_type,
    }

    index = payload.get("index")
    if index is not None:
        normalized_index = str(index).strip()
        if normalized_index:
            normalized["index"] = normalized_index

    raw_candidates = payload.get("candidates")
    if isinstance(raw_candidates, list):
        candidates = [
            {
                "uri": str(candidate.get("uri") or "").strip(),
                "label": str(candidate.get("label") or "").strip(),
            }
            for candidate in raw_candidates
            if isinstance(candidate, Mapping)
            and str(candidate.get("uri") or "").strip()
        ]
        if candidates:
            normalized["candidates"] = candidates
    return normalized


def _find_legacy_uri_payload() -> EscoMigrationPendingPayload | None:
    selected = st.session_state.get(SSKey.ESCO_OCCUPATION_SELECTED.value)
    if isinstance(selected, dict):
        uri = selected.get("uri")
        if _is_legacy_esco_uri(uri):
            return {
                "target": SSKey.ESCO_OCCUPATION_SELECTED.value,
                "uri": str(uri),
                "concept_type": "occupation",
            }
    for bucket_key in (
        SSKey.ESCO_SKILLS_SELECTED_MUST.value,
        SSKey.ESCO_SKILLS_SELECTED_NICE.value,
    ):
        bucket = st.session_state.get(bucket_key)
        if not isinstance(bucket, list):
            continue
        for index, item in enumerate(bucket):
            if not isinstance(item, dict):
                continue
            uri = item.get("uri")
            if _is_legacy_esco_uri(uri):
                return {
                    "target": bucket_key,
                    "uri": str(uri),
                    "concept_type": "skill",
                    "index": str(index),
                }
    return None


def _extract_conversion_candidates(
    payload: object, *, concept_type: str
) -> list[dict[str, str]]:
    candidates: list[dict[str, str]] = []
    seen_uris: set[str] = set()

    def _matches_type(concept_uri: str, value_type: str) -> bool:
        normalized_type = value_type.strip().lower()
        if normalized_type == concept_type:
            return True
        return f"/{concept_type}/" in concept_uri.strip().lower()

    def _walk(node: object) -> None:
        if isinstance(node, dict):
            uri_value = node.get("uri")
            if isinstance(uri_value, str) and not _is_legacy_esco_uri(uri_value):
                node_type = str(node.get("type") or "")
                if _matches_type(uri_value, node_type) and uri_value not in seen_uris:
                    label = str(
                        node.get("title")
                        or node.get("preferredLabel")
                        or node.get("label")
                        or uri_value
                    ).strip()
                    candidates.append({"uri": uri_value, "label": label})
                    seen_uris.add(uri_value)
            for nested in node.values():
                _walk(nested)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(payload)
    return candidates


def _append_esco_migration_log(
    *,
    concept_type: str,
    old_uri: str,
    new_uri: str,
    decision: str,
) -> None:
    raw_log = st.session_state.get(SSKey.ESCO_MIGRATION_LOG.value, [])
    migration_log = list(raw_log) if isinstance(raw_log, list) else []
    migration_log.append(
        {
            "concept_type": concept_type,
            "old_uri": old_uri,
            "new_uri": new_uri,
            "decision": decision,
            "migrated_at": datetime.now(timezone.utc).isoformat(),
        }
    )
    st.session_state[SSKey.ESCO_MIGRATION_LOG.value] = migration_log


def _apply_canonical_uri(
    *,
    migration_payload: EscoMigrationPendingPayload,
    canonical_uri: str,
    decision: str,
) -> bool:
    target = str(migration_payload.get("target") or "").strip()
    legacy_uri = str(migration_payload.get("uri") or "").strip()
    concept_type = str(migration_payload.get("concept_type") or "").strip()
    if not target or not legacy_uri or not concept_type:
        return False

    if target == SSKey.ESCO_OCCUPATION_SELECTED.value:
        selected = st.session_state.get(target)
        if not isinstance(selected, dict):
            return False
        migrated = dict(selected)
        migrated["uri"] = canonical_uri
        st.session_state[target] = migrated
        st.session_state[SSKey.ESCO_SELECTED_OCCUPATION_URI.value] = canonical_uri
    elif target in (
        SSKey.ESCO_SKILLS_SELECTED_MUST.value,
        SSKey.ESCO_SKILLS_SELECTED_NICE.value,
    ):
        raw_bucket = st.session_state.get(target)
        if not isinstance(raw_bucket, list):
            return False
        try:
            index = int(str(migration_payload.get("index") or "").strip())
        except ValueError:
            return False
        if index < 0 or index >= len(raw_bucket):
            return False
        entry = raw_bucket[index]
        if not isinstance(entry, dict):
            return False
        bucket = list(raw_bucket)
        migrated = dict(entry)
        migrated["uri"] = canonical_uri
        bucket[index] = migrated
        st.session_state[target] = bucket
    else:
        return False

    _append_esco_migration_log(
        concept_type=concept_type,
        old_uri=legacy_uri,
        new_uri=canonical_uri,
        decision=decision,
    )
    st.session_state[SSKey.ESCO_MIGRATION_PENDING.value] = None
    return True


def _render_pending_esco_migration_choice() -> None:
    pending = _normalize_esco_migration_pending_payload(
        st.session_state.get(SSKey.ESCO_MIGRATION_PENDING.value)
    )
    if pending is None:
        st.session_state[SSKey.ESCO_MIGRATION_PENDING.value] = None
        return
    candidates = pending.get("candidates", [])
    if len(candidates) <= 1:
        return

    st.info("Mehrere mögliche Zielkonzepte gefunden. Bitte explizit auswählen.")
    options = [
        str(candidate.get("uri") or "").strip()
        for candidate in candidates
        if isinstance(candidate, dict) and str(candidate.get("uri") or "").strip()
    ]
    if not options:
        st.session_state[SSKey.ESCO_MIGRATION_PENDING.value] = None
        return

    labels_by_uri = {
        str(candidate.get("uri") or "").strip(): str(
            candidate.get("label") or candidate.get("uri") or "Unbenannt"
        ).strip()
        for candidate in candidates
        if isinstance(candidate, dict)
    }
    selected_uri = st.selectbox(
        "Migrationsziel auswählen",
        options=options,
        format_func=lambda uri: f"{labels_by_uri.get(uri, uri)} — {uri}",
        key="esco.legacy_uri.candidate_select",
    )
    c_apply, c_cancel = st.columns([1, 1])
    with c_apply:
        if st.button("Auswahl übernehmen", key="esco.legacy_uri.apply_selection"):
            applied = _apply_canonical_uri(
                migration_payload=pending,
                canonical_uri=selected_uri,
                decision="selected_from_multiple",
            )
            if applied:
                st.success("Legacy-URI wurde auf eine kanonische ESCO-URI migriert.")
            else:
                st.warning("Die Auswahl konnte nicht übernommen werden.")
    with c_cancel:
        if st.button("Auswahl verwerfen", key="esco.legacy_uri.cancel_selection"):
            st.session_state[SSKey.ESCO_MIGRATION_PENDING.value] = None
            st.info("Migrationsauswahl wurde verworfen.")


def _conversion_endpoint_for_concept(concept_type: str) -> str:
    return "occupation" if concept_type == "occupation" else "skill"


def _render_esco_migration_trigger(legacy_payload: EscoMigrationPendingPayload) -> None:
    concept_type = str(legacy_payload.get("concept_type") or "").strip()
    conversion_endpoint = _conversion_endpoint_for_concept(concept_type)
    if st.button("Legacy-URI migrieren", key="esco.legacy_uri.migrate"):
        try:
            conversion_payload = EscoClient().conversion(
                conversion_endpoint,
                uri=legacy_payload["uri"],
            )
        except EscoClientError as exc:
            st.warning(f"Migration aktuell nicht möglich: {exc}")
            return

        candidates = _extract_conversion_candidates(
            conversion_payload,
            concept_type=concept_type,
        )
        if not candidates:
            st.info("Keine kanonische URI im Conversion-Resultat gefunden.")
            return
        if len(candidates) == 1:
            applied = _apply_canonical_uri(
                migration_payload=legacy_payload,
                canonical_uri=candidates[0]["uri"],
                decision="single_candidate",
            )
            if applied:
                st.success("Legacy-URI wurde auf eine kanonische ESCO-URI migriert.")
            else:
                st.info("Keine aktualisierbare ESCO-Auswahl gefunden.")
            return

        pending = cast(EscoMigrationPendingPayload, dict(legacy_payload))
        pending["candidates"] = candidates
        st.session_state[SSKey.ESCO_MIGRATION_PENDING.value] = pending
        st.info("Bitte wählen Sie ein Zielkonzept für die Migration aus.")


def _render_esco_sidebar_status_block(ui_mode: str) -> None:
    del ui_mode
    config = _get_esco_config()
    release_lane = str(config["release_lane"])
    selected_version = str(config["selected_version"])
    view_obsolete = bool(config["view_obsolete"])
    selected_language = str(config["language"]).strip().lower() or "de"
    fallback_language = str(config["fallback_language"]).strip().lower() or "en"
    if selected_language not in {"de", "en"}:
        selected_language = "de"

    if bool(st.session_state.get(SSKey.DEBUG.value, False)):
        lane_options = (ESCO_RELEASE_LANE_STABLE, ESCO_RELEASE_LANE_PREVIEW)
        release_lane = st.sidebar.selectbox(
            "ESCO Release Lane",
            options=lane_options,
            index=lane_options.index(release_lane) if release_lane in lane_options else 0,
            format_func=lambda lane: (
                f"Stable ({ESCO_RELEASE_LANE_SELECTED_VERSION[ESCO_RELEASE_LANE_STABLE]})"
                if lane == ESCO_RELEASE_LANE_STABLE
                else f"Preview ({ESCO_RELEASE_LANE_SELECTED_VERSION[ESCO_RELEASE_LANE_PREVIEW]})"
            ),
            key=f"{SSKey.ESCO_CONFIG.value}.release_lane_select",
        )
        selected_version = selected_version_for_release_lane(release_lane)
        view_obsolete = st.sidebar.toggle(
            "Obsolete anzeigen (Debug only)",
            value=view_obsolete,
            key=f"{SSKey.ESCO_CONFIG.value}.view_obsolete_toggle",
        )
        config_changed = _set_esco_config(
            release_lane=release_lane,
            selected_version=selected_version,
            view_obsolete=view_obsolete,
            language=selected_language,
            fallback_language=fallback_language,
        )
        if config_changed:
            st.sidebar.success("ESCO-Konfiguration aktualisiert. Cache wurde invalidiert.")


def render_esco_language_toggle() -> None:
    if not bool(st.session_state.get(SSKey.DEBUG.value, False)):
        return
    config = _get_esco_config()
    release_lane = str(config["release_lane"])
    selected_version = str(config["selected_version"])
    view_obsolete = bool(config["view_obsolete"])
    language = str(config["language"]).strip().lower() or "de"
    if language not in {"de", "en"}:
        language = "de"

    language_options = ("de", "en")
    selected_language = st.radio(
        "Sprache",
        options=language_options,
        index=language_options.index(language),
        format_func=lambda value: "🇩🇪 Deutsch" if value == "de" else "🇬🇧 English",
        horizontal=True,
        key=f"{SSKey.ESCO_CONFIG.value}.language_choice",
        label_visibility="collapsed",
        on_change=sync_streamlit_language_widget,
        args=(f"{SSKey.ESCO_CONFIG.value}.language_choice",),
    )
    selected_language = str(selected_language).strip().lower()
    selected_fallback_language = "en" if selected_language == "de" else "de"
    _set_esco_config(
        release_lane=release_lane,
        selected_version=selected_version,
        view_obsolete=view_obsolete,
        language=selected_language,
        fallback_language=selected_fallback_language,
    )
    sync_language_state(selected_language)


def _render_esco_warnings_and_migration_cta() -> None:
    _render_pending_esco_migration_choice()
    config = _get_esco_config()
    if bool(config["view_obsolete"]):
        st.warning(
            "ESCO Obsolete-Modus ist aktiv. Ergebnisse können veraltete Konzepte enthalten."
        )

    legacy_payload = _find_legacy_uri_payload()
    if legacy_payload is None:
        return
    legacy_uri = legacy_payload["uri"]
    st.warning(
        "Legacy-URI erkannt. Bitte migrieren, damit aktuelle ESCO-Daten "
        "konsistent geladen werden."
    )
    with st.expander("Legacy-URI Details", expanded=False):
        st.code(legacy_uri)
    _render_esco_migration_trigger(legacy_payload)


def get_current_ui_mode() -> str:
    """Return normalized UI mode from session state."""
    ui_mode_raw = st.session_state.get(SSKey.UI_MODE.value, UI_MODE_DEFAULT)
    return normalize_ui_mode(ui_mode_raw)


def normalize_ui_mode(raw_mode: object) -> str:
    """Normalize any raw mode value to the canonical UI mode domain."""
    ui_mode = str(raw_mode).strip().lower()
    if ui_mode not in set(UI_MODE_VALUES):
        return "standard"
    return ui_mode


def map_answer_mode_to_ui_mode(raw_answer_mode: object) -> str:
    """Map preference-center answer modes to canonical UI modes."""
    normalized_answer_mode = str(raw_answer_mode).strip().lower()
    answer_to_ui_mode = {
        "compact": "quick",
        "balanced": "standard",
        "advisory": "expert",
    }
    return normalize_ui_mode(answer_to_ui_mode.get(normalized_answer_mode, "standard"))


def map_ui_mode_to_answer_mode(raw_ui_mode: object) -> str:
    """Map canonical UI mode to persisted answer-mode preference metadata."""
    normalized_ui_mode = normalize_ui_mode(raw_ui_mode)
    ui_to_answer_mode = {
        "quick": "compact",
        "standard": "balanced",
        "expert": "advisory",
    }
    return str(ui_to_answer_mode.get(normalized_ui_mode, "balanced"))


def map_ui_mode_to_information_depth(raw_ui_mode: object) -> str:
    """Map canonical UI mode to persisted information-depth preference metadata."""
    normalized_ui_mode = normalize_ui_mode(raw_ui_mode)
    ui_to_information_depth = {
        "quick": "niedrig",
        "standard": "standard",
        "expert": "hoch",
    }
    return str(ui_to_information_depth.get(normalized_ui_mode, "standard"))


def sync_ui_mode_preference_metadata() -> None:
    """Persist derived preference metadata from canonical runtime UI mode."""
    ui_mode = get_current_ui_mode()
    preferences = normalize_ui_preferences(
        st.session_state.get(SSKey.UI_PREFERENCES.value)
    )
    preferences[UI_PREFERENCE_ANSWER_MODE] = map_ui_mode_to_answer_mode(ui_mode)
    preferences[UI_PREFERENCE_INFORMATION_DEPTH] = map_ui_mode_to_information_depth(
        ui_mode
    )
    st.session_state[SSKey.UI_PREFERENCES.value] = preferences


def _sync_mode_change() -> None:
    sync_ui_mode_preference_metadata()
    sync_adaptive_question_limits()


def get_ui_mode_badge_text(ui_mode: str | None = None) -> str:
    normalized_mode = (ui_mode or get_current_ui_mode()).strip().lower()
    display_label = UI_MODE_DISPLAY_LABELS.get(normalized_mode, normalized_mode)
    display_label = str(t(display_label.capitalize()))
    return str(t(f"Detailgrad aktiv: **{display_label}** (`{normalized_mode}`)"))


def render_active_ui_mode_caption(*, ui_mode: str | None = None) -> None:
    st.caption(
        f"{get_ui_mode_badge_text(ui_mode)} · "
        f"{t('Der Modus steuert die Anzahl der Rückfragen; die Analysequalität bleibt gleich.')}"
    )


def render_ui_mode_selector(
    *,
    sidebar: bool = False,
    widget_key: str | None = None,
    show_label: bool = True,
) -> str:
    ui_mode_key = widget_key or SSKey.UI_MODE.value
    selectbox = st.sidebar.selectbox if sidebar else st.selectbox
    normalized_mode = normalize_ui_mode(
        st.session_state.get(ui_mode_key, get_current_ui_mode())
    )
    st.session_state[ui_mode_key] = normalized_mode
    selected_mode = selectbox(
        "Detailgrad",
        options=list(UI_MODE_VALUES),
        key=ui_mode_key,
        format_func=lambda mode: str(
            t(UI_MODE_DISPLAY_LABELS.get(mode, str(mode).capitalize()))
        ),
        help=(
            "Steuert, wie viele Rückfragen pro Schritt gestellt werden. "
            "Analyse, Extraktion und Ergebnisqualität bleiben unverändert."
        ),
        on_change=_sync_mode_change,
        label_visibility="visible" if show_label else "collapsed",
    )
    sync_ui_mode_preference_metadata()
    return normalize_ui_mode(selected_mode)


def sidebar_navigation(ctx: WizardContext) -> WizardPage:
    _ensure_salary_forecast_state_defaults()
    sync_adaptive_question_limits()
    pages = ctx.pages
    options = [p.key for p in pages]
    cur_key = ctx.get_current_page_key()
    if cur_key not in options:
        cur_key = options[0]
        set_current_step(cur_key)

    nav_key = SSKey.NAV_SELECTED.value
    nav_sync_pending = bool(st.session_state.get(SSKey.NAV_SYNC_PENDING.value, False))
    nav_selected = st.session_state.get(nav_key)
    if nav_sync_pending or nav_selected not in options:
        st.session_state[nav_key] = cur_key
        st.session_state[SSKey.NAV_SYNC_PENDING.value] = False

    ui_preferences_key = SSKey.UI_PREFERENCES.value
    get_current_ui_mode()
    st.session_state[ui_preferences_key] = normalize_ui_preferences(
        st.session_state.get(ui_preferences_key)
    )
    format_map: dict[str, str] = {}
    for page in pages:
        format_map[page.key] = page.label

    def _format(k: str) -> str:
        return format_map.get(k, k)

    selected = st.sidebar.radio(
        "Prozess",
        options=options,
        key=nav_key,
        format_func=_format,
    )
    if selected != cur_key:
        set_current_step(selected, sync_navigation=False)
        st.rerun()

    current_page = next(p for p in pages if p.key == selected)

    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    answers_raw = st.session_state.get(SSKey.ANSWERS.value, {})
    answers = answers_raw if isinstance(answers_raw, dict) else {}
    source_text_raw = st.session_state.get(SSKey.SOURCE_TEXT.value, "")
    source_text = source_text_raw if isinstance(source_text_raw, str) else ""
    job: JobAdExtract | None = None
    if isinstance(job_dict, dict):
        try:
            job = JobAdExtract.model_validate(job_dict)
        except Exception:
            job = None
    sidebar_input_rows = _build_sidebar_salary_input_rows()
    sidebar_input_selections = _sync_sidebar_salary_input_selections(
        sidebar_input_rows
    )
    sidebar_fingerprint = _sidebar_salary_fingerprint(
        rows=sidebar_input_rows,
        selections=sidebar_input_selections,
    )
    raw_fingerprints = st.session_state.get(
        SSKey.SALARY_FORECAST_INPUT_FINGERPRINT.value, {}
    )
    fingerprints = raw_fingerprints if isinstance(raw_fingerprints, dict) else {}
    last_sidebar_fingerprint = str(
        fingerprints.get(_SALARY_SIDEBAR_STEP_KEY) or ""
    ).strip()
    forecast = _coerce_sidebar_salary_forecast(
        st.session_state.get(SSKey.SALARY_FORECAST_LAST_RESULT.value)
    )
    update_requested = render_sidebar_salary_forecast(
        forecast=forecast,
        input_rows=sidebar_input_rows,
        input_selections=sidebar_input_selections,
        is_stale=last_sidebar_fingerprint != sidebar_fingerprint,
    )
    if update_requested:
        updated_selections_raw = st.session_state.get(
            SSKey.SALARY_FORECAST_INPUT_SELECTIONS.value, {}
        )
        updated_selections = (
            updated_selections_raw if isinstance(updated_selections_raw, dict) else {}
        )
        forecast_job, forecast_answers = _sidebar_job_and_answers(
            base_job=job,
            rows=sidebar_input_rows,
            selections=updated_selections,
            source_text=source_text,
        )
        forecast = _compute_sidebar_salary_forecast(
            job=forecast_job,
            answers=forecast_answers,
            source_text=source_text,
            esco_context=_active_sidebar_esco_context(
                sidebar_input_rows, updated_selections
            ),
            scenario_inputs=_active_sidebar_scenario_inputs(
                sidebar_input_rows, updated_selections
            ),
        )
        if forecast is not None:
            st.session_state[SSKey.SALARY_FORECAST_LAST_RESULT.value] = {
                **forecast.model_dump(mode="json"),
                "step_key": _SALARY_SIDEBAR_STEP_KEY,
            }
            fingerprints = dict(fingerprints)
            fingerprints[_SALARY_SIDEBAR_STEP_KEY] = _sidebar_salary_fingerprint(
                rows=sidebar_input_rows,
                selections=updated_selections,
            )
            st.session_state[SSKey.SALARY_FORECAST_INPUT_FINGERPRINT.value] = (
                fingerprints
            )
            st.rerun()
    _render_esco_warnings_and_migration_cta()
    return current_page


def nav_buttons(
    ctx: WizardContext, *, disable_next: bool = False, disable_prev: bool = False
) -> None:
    c1, c2 = st.columns([1, 1])
    with c1:
        back_clicked = st.button("← Zurück", disabled=disable_prev)
    with c2:
        next_clicked = st.button("Weiter →", disabled=disable_next)
    # rerun only in normal render flow; callbacks may be within disallowed rerun contexts
    if back_clicked:
        ctx.prev()
        st.rerun()
    if next_clicked:
        record_step_submitted(
            st.session_state,
            step_key=ctx.get_current_page_key(),
            action="next",
        )
        ctx.next()
        st.rerun()


def guard_job_and_plan(
    ctx: WizardContext,
) -> tuple[JobAdExtract, QuestionPlan] | None:
    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN.value)

    if not job_dict or not plan_dict:
        st.warning("Bitte zuerst im Start-Schritt eine Analyse durchführen.")
        st.button("Zur Startseite", on_click=lambda: ctx.goto("landing"))
        nav_buttons(ctx, disable_next=True)
        return None

    job = JobAdExtract.model_validate(job_dict)
    plan = QuestionPlan.model_validate(plan_dict)
    return job, plan


LANDING_STYLE_TOKENS: dict[str, str] = {
    "card_radius": "8px",
    "section_spacing": "0.85rem 0 1rem 0",
    "muted_text_color": "var(--cs-text-muted)",
    "emphasis_border": "3px solid var(--cs-success)",
    "emphasis_background": "var(--cs-success-soft)",
}


LANDING_SECTION_IDS: dict[str, str] = {
    "hero": "LANDING_HERO",
    "value_cards": "LANDING_VALUE_CARDS",
    "importance": "LANDING_IMPORTANCE",
    "flow": "LANDING_FLOW",
    "output": "LANDING_OUTPUT",
    "security": "LANDING_SECURITY",
}


LANDING_CTA_KEYS: dict[str, str] = {
    "start": "landing.start_intake",
    "consent": SSKey.CONTENT_SHARING_CONSENT.value,
    "debug": SSKey.DEBUG.value,
}


def render_landing_css(style_tokens: Mapping[str, str]) -> None:
    card_radius = escape_html_text(style_tokens["card_radius"])
    section_spacing = escape_html_text(style_tokens["section_spacing"])
    muted_text_color = escape_html_text(style_tokens["muted_text_color"])
    emphasis_background = escape_html_text(style_tokens["emphasis_background"])
    emphasis_border = escape_html_text(style_tokens["emphasis_border"])
    render_static_html(
        f"""
        <style>
            .landing-section {{
                margin: {section_spacing};
            }}

            .landing-hero {{
                background: var(--cs-surface);
                border: 1px solid var(--cs-border);
                border-radius: {card_radius};
                padding: 1.15rem 1.1rem;
                box-shadow: var(--cs-shadow-sm);
            }}

            .landing-hero h1 {{
                margin: 0;
                font-size: clamp(1.55rem, 2vw, 2.15rem);
                line-height: 1.18;
                letter-spacing: 0;
                color: var(--cs-text);
            }}

            .landing-hero-copy {{
                max-width: 72ch;
            }}

            .landing-subhead {{
                margin-top: 0.6rem;
                color: var(--cs-text-muted);
                line-height: 1.5;
                font-size: 1rem;
            }}

            .landing-card {{
                background: var(--cs-surface);
                border: 1px solid var(--cs-border);
                border-radius: {card_radius};
                padding: 0.95rem;
                height: 100%;
                box-shadow: var(--cs-shadow-sm);
            }}

            .landing-card h4 {{
                margin: 0 0 0.45rem 0;
                font-size: 1rem;
                color: var(--cs-text);
            }}

            .landing-card p {{
                margin: 0;
                color: var(--cs-text-muted);
                line-height: 1.5;
            }}

            .landing-emphasis {{
                background: {emphasis_background};
                border-left: {emphasis_border};
                border-radius: {card_radius};
                padding: 0.72rem 0.8rem;
                margin-bottom: 0.75rem;
            }}

            .landing-emphasis p {{
                margin: 0;
                color: var(--cs-text);
                line-height: 1.5;
                font-size: 1.02rem;
                font-weight: 650;
            }}

            .landing-emphasis--subtle {{
                background: var(--cs-surface-muted);
                border-left: 3px solid var(--cs-border);
                padding-bottom: 0.65rem;
                margin-bottom: 0.65rem;
            }}

            .landing-problem-panel {{
                background: var(--cs-surface-muted);
                border: 1px solid var(--cs-border);
                border-radius: {card_radius};
                padding: 0.65rem 0.85rem;
                margin-top: 0.65rem;
            }}

            .landing-problem-list {{
                margin: 0.1rem 0 0 0;
                padding-left: 1rem;
                color: var(--cs-text-muted);
            }}

            .landing-problem-list li {{
                margin-bottom: 0.42rem;
                line-height: 1.35;
            }}

            .landing-problem-list strong {{
                color: var(--cs-text);
            }}

            .landing-problem-heading {{
                margin: 0 0 0.5rem 0;
                font-size: 0.9rem;
                letter-spacing: 0.01em;
                color: var(--cs-text);
            }}

            .landing-section-stack {{
                display: grid;
                gap: 0.65rem;
            }}

            .landing-outcome-callout {{
                margin-top: 0.75rem;
                border-radius: {card_radius};
                border: 1px solid var(--cs-success);
                background: var(--cs-success-soft);
                padding: 0.68rem 0.78rem;
            }}

            .landing-outcome-badge {{
                display: inline-flex;
                align-items: center;
                gap: 0.35rem;
                border: 1px solid var(--cs-success);
                border-radius: 999px;
                padding: 0.13rem 0.48rem;
                font-size: 0.76rem;
                font-weight: 650;
                text-transform: uppercase;
                letter-spacing: 0.02em;
                color: var(--cs-text);
                background: var(--cs-surface);
            }}

            .landing-outcome-text {{
                margin: 0.5rem 0 0 0;
                color: var(--cs-text);
                line-height: 1.42;
                font-size: 0.95rem;
            }}

            .landing-flow-step {{
                background: var(--cs-surface);
                border: 1px solid var(--cs-border);
                border-radius: {card_radius};
                padding: 0.68rem;
                min-height: 108px;
            }}

            .landing-list {{
                margin: 0.5rem 0 0 0;
                padding-left: 1.1rem;
            }}

            .landing-list li {{
                margin-bottom: 0.5rem;
                line-height: 1.45;
            }}

            .landing-output-panel {{
                background: var(--cs-surface);
                border: 1px solid var(--cs-border);
                border-radius: {card_radius};
                padding: 0.65rem 0.85rem;
                min-height: 100%;
            }}

            .landing-caption {{
                color: {muted_text_color};
                font-size: 0.9rem;
                margin-top: 0.35rem;
            }}

            .landing-app-title-row {{
                display: flex;
                justify-content: space-between;
                align-items: center;
                gap: 0.8rem;
                margin-bottom: 0.45rem;
                flex-wrap: wrap;
            }}

            .landing-app-title {{
                color: var(--cs-text);
                font-size: 0.84rem;
                letter-spacing: 0.02em;
                text-transform: uppercase;
                font-weight: 650;
            }}

            .landing-app-links {{
                display: inline-flex;
                justify-content: flex-end;
                align-items: center;
                gap: 0.45rem;
                flex-wrap: wrap;
            }}

            .landing-app-link-pill {{
                display: inline-flex;
                align-items: center;
                gap: 0.35rem;
                padding: 0.34rem 0.75rem;
                border-radius: 999px;
                border: 1px solid var(--cs-primary);
                background: var(--cs-primary);
                text-decoration: none !important;
                color: var(--cs-on-primary, #FFFFFF) !important;
                font-size: 0.82rem;
                font-weight: 620;
                transition: transform 130ms ease, box-shadow 130ms ease, border-color 130ms ease;
            }}

            .landing-app-link-pill:hover {{
                transform: translateY(-1px);
                box-shadow: 0 8px 20px color-mix(in srgb, var(--cs-primary) 22%, transparent);
                border-color: color-mix(in srgb, var(--cs-primary) 88%, #000000);
                color: var(--cs-on-primary, #FFFFFF) !important;
            }}

            .landing-app-link-pill:visited,
            .landing-app-link-pill:focus,
            .landing-app-link-pill:active {{
                text-decoration: none !important;
                color: var(--cs-on-primary, #FFFFFF) !important;
            }}

            .landing-security-note {{
                background: var(--cs-warning-soft);
                border: 1px solid var(--cs-warning);
                border-radius: {card_radius};
                padding: 0.8rem 0.95rem;
                color: var(--cs-text);
                font-size: 0.9rem;
            }}

            @media (max-width: 900px) {{
                .landing-hero {{
                    padding: 1rem;
                }}

                .landing-hero-copy {{
                    max-width: 100%;
                }}

                .landing-flow-step {{
                    min-height: 0;
                }}
            }}
        </style>
        """,
        streamlit_module=st,
    )


def render_hero_section(
    ctx: WizardContext,
    *,
    section_id: str,
    headline: str,
    subhead: str,
    primary_cta: str,
    secondary_cta_hint: str,
    before_start_title: str = "",
    before_start_bullets: Sequence[str] = (),
    reassurance_line: str = "",
    extraction_helper_copy: str = "",
    next_step_line: str = "",
    post_cta_microcopy: str = "",
    value_cards: Sequence[tuple[str, str]],
    show_value_cards: bool = True,
    consent_given: bool,
    start_button_key: str,
    on_start: Callable[[], None],
    start_target: str,
) -> None:
    safe_section_id = escape_html_text(section_id, quote=True)
    render_static_html(
        f'<section id="{safe_section_id}" class="landing-section landing-hero">',
        streamlit_module=st,
    )
    render_static_html('<div class="landing-hero-copy">', streamlit_module=st)
    render_static_html(f"<h1>{escape_html_text(headline)}</h1>", streamlit_module=st)
    if subhead:
        render_static_html(
            f'<p class="landing-subhead">{escape_html_text(subhead)}</p>',
            streamlit_module=st,
        )
    if primary_cta and st.button(
        primary_cta,
        key=start_button_key,
        type="primary",
        width="stretch",
        disabled=not consent_given,
    ):
        on_start()
        ctx.goto(start_target)
        st.rerun()
    if secondary_cta_hint:
        render_static_html(
            f'<p class="landing-caption">{escape_html_text(secondary_cta_hint)}</p>',
            streamlit_module=st,
        )
    if next_step_line:
        st.caption(next_step_line)
    has_more_details = any(
        [
            bool(before_start_title and before_start_bullets),
            bool(reassurance_line),
            bool(extraction_helper_copy),
            bool(post_cta_microcopy),
        ]
    )
    if has_more_details:
        with st.expander("Mehr erfahren", expanded=False):
            if before_start_title and before_start_bullets:
                st.markdown(f"#### {before_start_title}")
                render_static_html(
                    '<ul class="landing-list">'
                    + "".join(
                        f"<li>{escape_html_text(bullet)}</li>"
                        for bullet in before_start_bullets
                    )
                    + "</ul>",
                    streamlit_module=st,
                )
            if reassurance_line:
                st.caption(reassurance_line)
            if extraction_helper_copy:
                st.info(extraction_helper_copy, icon="ℹ️")
            if post_cta_microcopy:
                st.caption(post_cta_microcopy)
    render_static_html("</div>", streamlit_module=st)

    render_static_html("</section>", streamlit_module=st)

    if show_value_cards and value_cards:
        render_static_html(
            f'<section id="{LANDING_SECTION_IDS["value_cards"]}" class="landing-section">',
            streamlit_module=st,
        )
        st.markdown("### Wertbeitrag auf einen Blick")
        render_value_cards(value_cards=value_cards)
        render_static_html("</section>", streamlit_module=st)


def render_value_cards(*, value_cards: Sequence[tuple[str, str]]) -> None:
    # Keep predictable 2-column rhythm to avoid narrow, uneven cards.
    for row_start in range(0, len(value_cards), 2):
        row_cols = st.columns(2, gap="small")
        for col, (title, body) in zip(row_cols, value_cards[row_start : row_start + 2]):
            with col:
                render_static_html(
                    (
                        '<div class="landing-card">'
                        f"<h4>{escape_html_text(title)}</h4>"
                        f"<p>{escape_html_text(body)}</p>"
                        "</div>"
                    ),
                    streamlit_module=st,
                )


def render_importance_section(
    *,
    section_id: str,
    title: str,
    intro: str,
    risk_points: Sequence[tuple[str, str]],
    leverage_points: Sequence[tuple[str, str]],
    closer: str,
) -> None:
    safe_section_id = escape_html_text(section_id, quote=True)
    render_static_html(
        f'<section id="{safe_section_id}" class="landing-section">',
        streamlit_module=st,
    )
    st.subheader(title)
    render_static_html(
        f'<div class="landing-emphasis"><p>{escape_html_text(intro)}</p></div>',
        streamlit_module=st,
    )
    risk_items = "".join(
        f"<li><strong>{escape_html_text(point_title)}:</strong> {escape_html_text(body)}</li>"
        for point_title, body in risk_points
    )
    leverage_items = "".join(
        f"<li><strong>{escape_html_text(point_title)}:</strong> {escape_html_text(body)}</li>"
        for point_title, body in leverage_points
    )
    if risk_items or leverage_items:
        render_static_html('<div class="landing-section-stack">', streamlit_module=st)
    if risk_items:
        render_static_html(
            (
                '<div class="landing-problem-panel">'
                '<h4 class="landing-problem-heading">Ohne sauberen Intake</h4>'
                f'<ul class="landing-problem-list">{risk_items}</ul>'
                "</div>"
            ),
            streamlit_module=st,
        )

    if leverage_items:
        render_static_html(
            (
                '<div class="landing-problem-panel">'
                '<h4 class="landing-problem-heading">Mit präzisem Intake</h4>'
                f'<ul class="landing-problem-list">{leverage_items}</ul>'
                "</div>"
            ),
            streamlit_module=st,
        )
    if risk_items or leverage_items:
        render_static_html("</div>", streamlit_module=st)

    render_static_html(
        (
            '<div class="landing-outcome-callout">'
            '<span class="landing-outcome-badge">🏁 Ergebnis</span>'
            f'<p class="landing-outcome-text">{escape_html_text(closer)}</p>'
            "</div>"
        ),
        streamlit_module=st,
    )
    render_static_html("</section>", streamlit_module=st)


def render_flow_steps(
    *, section_id: str, title: str, steps: Sequence[tuple[str, str]]
) -> None:
    safe_section_id = escape_html_text(section_id, quote=True)
    render_static_html(
        f'<section id="{safe_section_id}" class="landing-section">',
        streamlit_module=st,
    )
    st.subheader(title)
    for row_start in range(0, len(steps), 2):
        flow_cols = st.columns(2, gap="small")
        for col, (step_title, body) in zip(flow_cols, steps[row_start : row_start + 2]):
            with col:
                render_static_html(
                    (
                        '<div class="landing-flow-step">'
                        f"<h4>{escape_html_text(step_title)}</h4>"
                        f"<p>{escape_html_text(body)}</p>"
                        "</div>"
                    ),
                    streamlit_module=st,
                )
    render_static_html("</section>", streamlit_module=st)


def render_output_section(
    *, section_id: str, title: str, bullets: Sequence[str]
) -> None:
    safe_section_id = escape_html_text(section_id, quote=True)
    render_static_html(
        f'<section id="{safe_section_id}" class="landing-section">',
        streamlit_module=st,
    )
    st.subheader(title)
    render_static_html(
        '<div class="landing-output-panel"><ul class="landing-list">'
        + "".join(f"<li>{escape_html_text(bullet)}</li>" for bullet in bullets)
        + "</ul></div>",
        streamlit_module=st,
    )
    render_static_html("</section>", streamlit_module=st)


def render_security_note(*, section_id: str, title: str, body: str) -> None:
    safe_section_id = escape_html_text(section_id, quote=True)
    render_static_html(
        f'<section id="{safe_section_id}" class="landing-section">',
        streamlit_module=st,
    )
    st.subheader(title)
    render_static_html(
        f'<div class="landing-security-note">{escape_html_text(body)}</div>',
        streamlit_module=st,
    )
    render_static_html("</section>", streamlit_module=st)
