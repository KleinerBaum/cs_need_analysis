"""Wizard base utilities (page model + navigation helpers)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import (
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

from constants import SSKey, STEPS
from esco_client import EscoClient, EscoClientError, clear_esco_cache
from question_dependencies import should_show_question
from question_limits import sync_adaptive_question_limits
from question_progress import build_answered_lookup, compute_question_progress
from salary.engine import compute_salary_forecast
from salary.types import SalaryForecastResult
from schemas import JobAdExtract, Question, QuestionPlan
from wizard_pages.salary_forecast import render_sidebar_salary_forecast


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


def _compute_sidebar_salary_forecast(
    *,
    job: JobAdExtract | None,
    answers: dict[str, object],
    source_text: str,
) -> SalaryForecastResult | None:
    forecast_job = job or _fallback_job_from_session(
        answers=answers, source_text=source_text
    )
    if forecast_job is None:
        return None
    return compute_salary_forecast(job_extract=forecast_job, answers=answers)


@dataclass(frozen=True)
class WizardPage:
    key: str
    title_de: str
    icon: str
    render: Callable[["WizardContext"], None]
    requires_jobspec: bool = False

    @property
    def label(self) -> str:
        return f"{self.icon} {self.title_de}" if self.icon else self.title_de


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


class SidebarStepDetailStatus(TypedDict):
    essentials_answered: int
    essentials_total: int
    details_answered: int
    details_total: int
    missing_essentials: list[str]


class EscoMigrationPendingPayload(TypedDict):
    target: str
    uri: str
    concept_type: str
    index: NotRequired[str]
    candidates: NotRequired[list[dict[str, str]]]


def _status_prefix(status: StepStatus) -> str:
    if status == "complete":
        return "✅"
    if status == "partial":
        return "🟡"
    return "⬜"


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


def set_current_step(key: str, *, sync_navigation: bool = True) -> None:
    st.session_state[SSKey.CURRENT_STEP.value] = key
    if sync_navigation:
        st.session_state[SSKey.NAV_SYNC_PENDING.value] = True


def _get_step_questions(plan: QuestionPlan | None, step_key: str) -> list[Question]:
    if plan is None:
        return []
    step = next((entry for entry in plan.steps if entry.step_key == step_key), None)
    if step is None:
        return []

    limits_raw = st.session_state.get(SSKey.QUESTION_LIMITS.value, {})
    step_limit: int | None = None
    if isinstance(limits_raw, dict):
        raw_limit = limits_raw.get(step_key)
        if isinstance(raw_limit, (int, float, str)):
            try:
                step_limit = int(raw_limit)
            except ValueError:
                step_limit = None

    questions = step.questions
    if step_limit is not None and step_limit > 0:
        questions = step.questions[:step_limit]
    return questions


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
    has_job_extract = bool(st.session_state.get(SSKey.JOB_EXTRACT.value))
    has_brief = bool(st.session_state.get(SSKey.BRIEF.value))

    statuses: list[SidebarStepProgress] = []
    for page in pages:
        questions = _get_step_questions(plan, page.key)
        visible_questions = [
            question
            for question in questions
            if should_show_question(question, answers, answer_meta, page.key)
        ]
        progress = compute_question_progress(visible_questions, answers, answer_meta)
        answered = progress["answered"]
        total = progress["total"]

        status: StepStatus = "not_started"
        if total > 0:
            if answered == 0:
                status = "not_started"
            elif answered < total:
                status = "partial"
            else:
                status = "complete"
        elif page.key == "landing":
            source_text = st.session_state.get(SSKey.SOURCE_TEXT.value, "")
            has_source = isinstance(source_text, str) and bool(source_text.strip())
            if has_job_extract and plan is not None:
                status = "complete"
            elif has_source:
                status = "partial"
        elif page.key == "jobspec_review":
            if plan is not None:
                status = "complete"
            elif has_job_extract:
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
            }
        )
    return statuses


def _compute_sidebar_step_detail_status(page: WizardPage) -> SidebarStepDetailStatus:
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

    visible_questions = [
        question
        for question in _get_step_questions(plan, page.key)
        if should_show_question(question, answers, answer_meta, page.key)
    ]
    answered_lookup = build_answered_lookup(visible_questions, answers, answer_meta)

    essential_questions = [
        question
        for question in visible_questions
        if (question.priority or "") == "core"
    ]
    detail_questions = [
        question
        for question in visible_questions
        if (question.priority or "") != "core"
    ]
    essentials_progress = compute_question_progress(
        essential_questions,
        answers,
        answer_meta,
        answered_lookup=answered_lookup,
    )
    details_progress = compute_question_progress(
        detail_questions,
        answers,
        answer_meta,
        answered_lookup=answered_lookup,
    )

    missing_essentials = [
        question.label
        for question in essential_questions
        if not answered_lookup.get(question.id, False)
    ][:5]

    return {
        "essentials_answered": essentials_progress["answered"],
        "essentials_total": essentials_progress["total"],
        "details_answered": details_progress["answered"],
        "details_total": details_progress["total"],
        "missing_essentials": missing_essentials,
    }


def _render_sidebar_step_status_card(page: WizardPage) -> None:
    status = _compute_sidebar_step_detail_status(page)
    with st.sidebar.container(border=True):
        st.caption(f"Step: {page.title_de}")
        st.caption(
            f"Essentials {status['essentials_answered']}/{status['essentials_total']} · "
            f"Details {status['details_answered']}/{status['details_total']}"
        )
        if status["missing_essentials"]:
            st.caption("Missing")
            for label in status["missing_essentials"]:
                st.markdown(f"- {label}")


def _get_esco_config() -> dict[str, object]:
    raw = st.session_state.get(SSKey.ESCO_CONFIG.value, {})
    config = raw if isinstance(raw, dict) else {}
    raw_view_obsolete = config.get("view_obsolete", False)
    if isinstance(raw_view_obsolete, str):
        normalized = raw_view_obsolete.strip().lower()
        view_obsolete = normalized in {"true", "1", "yes", "on"}
    else:
        view_obsolete = bool(raw_view_obsolete)
    return {
        "base_url": str(config.get("base_url") or "https://ec.europa.eu/esco/api/"),
        "selected_version": str(config.get("selected_version") or "latest"),
        "language": str(config.get("language") or "de"),
        "view_obsolete": view_obsolete,
    }


def _set_esco_config(
    *,
    selected_version: str,
    view_obsolete: bool,
    language: str,
) -> bool:
    current_config = _get_esco_config()
    normalized_version = selected_version.strip() or "latest"
    normalized_language = language.strip().lower() or "de"
    changed = (
        current_config["selected_version"] != normalized_version
        or current_config["language"] != normalized_language
        or bool(current_config["view_obsolete"]) != view_obsolete
    )
    if not changed:
        return False

    st.session_state[SSKey.ESCO_CONFIG.value] = {
        **current_config,
        "selected_version": normalized_version,
        "language": normalized_language,
        "view_obsolete": view_obsolete,
    }
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
    config = _get_esco_config()
    selected_version = str(config["selected_version"])
    view_obsolete = bool(config["view_obsolete"])
    selected_language = str(config["language"]).strip().lower() or "de"
    if selected_language not in {"de", "en"}:
        selected_language = "de"

    if ui_mode == "expert":
        view_obsolete = st.sidebar.toggle(
            "Obsolete anzeigen (Expert only)",
            value=view_obsolete,
            key=f"{SSKey.ESCO_CONFIG.value}.view_obsolete_toggle",
        )

    config_changed = _set_esco_config(
        selected_version=selected_version,
        view_obsolete=view_obsolete,
        language=selected_language,
    )
    if config_changed:
        st.sidebar.success("ESCO-Konfiguration aktualisiert. Cache wurde invalidiert.")


def render_esco_language_toggle() -> None:
    config = _get_esco_config()
    selected_version = str(config["selected_version"])
    view_obsolete = bool(config["view_obsolete"])
    language = str(config["language"]).strip().lower() or "de"
    if language not in {"de", "en"}:
        language = "de"

    left_flag_col, toggle_col, right_flag_col = st.columns((0.55, 0.9, 0.55))
    with left_flag_col:
        st.markdown("<div style='text-align: right;'>🇩🇪</div>", unsafe_allow_html=True)
    with toggle_col:
        english_selected = st.toggle(
            "Sprache",
            value=language == "en",
            key=f"{SSKey.ESCO_CONFIG.value}.language_toggle",
            label_visibility="collapsed",
        )
    with right_flag_col:
        st.markdown("<div>🇬🇧</div>", unsafe_allow_html=True)

    selected_language = "en" if english_selected else "de"
    _set_esco_config(
        selected_version=selected_version,
        view_obsolete=view_obsolete,
        language=selected_language,
    )


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
    allowed_ui_modes = {"quick", "standard", "expert"}
    ui_mode_raw = st.session_state.get(SSKey.UI_MODE.value, "standard")
    ui_mode = str(ui_mode_raw).strip().lower()
    if ui_mode not in allowed_ui_modes:
        return "standard"
    return ui_mode


def render_ui_mode_selector(*, sidebar: bool = False) -> str:
    ui_mode_key = SSKey.UI_MODE.value
    mode_labels = {
        "quick": "schnell",
        "standard": "ausführlich",
        "expert": "vollumfänglich",
    }
    selectbox = st.sidebar.selectbox if sidebar else st.selectbox
    selected_mode = selectbox(
        "Wie weit möchten Sie ins Detail gehen?",
        options=["quick", "standard", "expert"],
        key=ui_mode_key,
        format_func=lambda mode: mode_labels.get(mode, str(mode).capitalize()),
        help=(
            "schnell/ausführlich: Detailgruppen standardmäßig kompakt. "
            "vollumfänglich: Detailgruppen standardmäßig geöffnet."
        ),
    )
    return str(selected_mode).strip().lower()


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

    step_statuses = _compute_step_statuses(pages)
    status_by_key = {entry["key"]: entry for entry in step_statuses}
    ui_preferences_key = SSKey.UI_PREFERENCES.value
    ui_mode = get_current_ui_mode()
    raw_ui_preferences = st.session_state.get(ui_preferences_key, {})
    ui_preferences = raw_ui_preferences if isinstance(raw_ui_preferences, dict) else {}
    details_expanded_default = ui_preferences.get("details_expanded_default")
    if not isinstance(details_expanded_default, bool):
        details_expanded_default = ui_mode == "expert"
    details_expanded_default = st.sidebar.toggle(
        "Details standardmäßig öffnen",
        value=details_expanded_default,
        help=(
            "Globale Voreinstellung für Detailgruppen in allen Wizard-Schritten. "
            "vollumfänglich setzt standardmäßig auf geöffnet, ausführlich/Quick auf kompakt."
        ),
    )
    normalized_preferences = dict(ui_preferences)
    normalized_preferences["details_expanded_default"] = details_expanded_default
    if not isinstance(normalized_preferences.get("step_compact"), dict):
        normalized_preferences["step_compact"] = {}
    st.session_state[ui_preferences_key] = normalized_preferences
    _render_esco_sidebar_status_block(ui_mode=ui_mode)
    format_map: dict[str, str] = {}
    for page in pages:
        step_status = status_by_key.get(page.key)
        prefix = _status_prefix(step_status["status"]) if step_status else "⬜"
        progress_suffix = ""
        if step_status and step_status["total"] > 0:
            progress_suffix = f" · {step_status['answered']}/{step_status['total']}"
        format_map[page.key] = f"{prefix} {page.title_de}{progress_suffix}"

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
    if ui_mode == "expert":
        forecast = _compute_sidebar_salary_forecast(
            job=job,
            answers=answers,
            source_text=source_text,
        )
        if forecast is not None:
            render_sidebar_salary_forecast(forecast=forecast)
    _render_esco_warnings_and_migration_cta()
    return current_page


def nav_buttons(
    ctx: WizardContext, *, disable_next: bool = False, disable_prev: bool = False
) -> None:
    c1, c2, c3 = st.columns([1, 1, 3])
    with c1:
        back_clicked = st.button("← Zurück", disabled=disable_prev)
    with c2:
        next_clicked = st.button("Weiter →", disabled=disable_next)
    with c3:
        st.caption("Fortschritt wird automatisch in dieser Session gespeichert.")
    # rerun only in normal render flow; callbacks may be within disallowed rerun contexts
    if back_clicked:
        ctx.prev()
        st.rerun()
    if next_clicked:
        ctx.next()
        st.rerun()


LANDING_STYLE_TOKENS: dict[str, str] = {
    "card_radius": "14px",
    "section_spacing": "1.2rem 0 1.4rem 0",
    "muted_text_color": "rgba(220, 233, 255, 0.9)",
    "emphasis_border": "4px solid rgba(138, 184, 255, 0.95)",
    "emphasis_background": "linear-gradient(135deg, rgba(22, 58, 112, 0.56), rgba(14, 34, 67, 0.4))",
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
    st.markdown(
        f"""
        <style>
            .landing-section {{
                margin: {style_tokens["section_spacing"]};
            }}

            .landing-hero {{
                background: linear-gradient(145deg, rgba(10, 27, 52, 0.9), rgba(8, 20, 40, 0.85));
                border: 1px solid rgba(167, 201, 255, 0.34);
                border-radius: 18px;
                padding: 1.6rem 1.45rem;
                box-shadow: 0 10px 30px rgba(0, 0, 0, 0.25);
            }}

            .landing-hero h1 {{
                margin: 0;
                font-size: clamp(1.6rem, 2.3vw, 2.45rem);
                line-height: 1.18;
                letter-spacing: 0.01em;
            }}

            .landing-hero-copy {{
                max-width: 66ch;
            }}

            .landing-subhead {{
                margin-top: 0.9rem;
                color: rgba(247, 249, 253, 0.95);
                line-height: 1.58;
                font-size: 1.05rem;
            }}

            .landing-card {{
                background: rgba(12, 27, 52, 0.78);
                border: 1px solid rgba(228, 236, 252, 0.2);
                border-radius: {style_tokens["card_radius"]};
                padding: 0.8rem 0.75rem;
                height: 100%;
            }}

            .landing-card h4 {{
                margin: 0 0 0.45rem 0;
                font-size: 1rem;
            }}

            .landing-card p {{
                margin: 0;
                color: rgba(245, 247, 251, 0.92);
                line-height: 1.5;
            }}

            .landing-emphasis {{
                background: {style_tokens["emphasis_background"]};
                border-left: {style_tokens["emphasis_border"]};
                border-radius: {style_tokens["card_radius"]};
                padding: 0.8rem 0.85rem 0.2rem 0.85rem;
                margin-bottom: 0.85rem;
            }}

            .landing-emphasis p {{
                margin: 0;
                color: rgba(247, 251, 255, 0.97);
                line-height: 1.5;
                font-size: 1.02rem;
                font-weight: 650;
            }}

            .landing-emphasis--subtle {{
                background: rgba(11, 26, 50, 0.42);
                border-left: 3px solid rgba(158, 189, 240, 0.45);
                padding-bottom: 0.65rem;
                margin-bottom: 0.65rem;
            }}

            .landing-problem-panel {{
                background: rgba(8, 19, 38, 0.28);
                border: 1px solid rgba(202, 219, 247, 0.16);
                border-radius: {style_tokens["card_radius"]};
                padding: 0.65rem 0.85rem;
                margin-top: 0.65rem;
            }}

            .landing-problem-list {{
                margin: 0.1rem 0 0 0;
                padding-left: 1rem;
                color: rgba(236, 243, 255, 0.88);
            }}

            .landing-problem-list li {{
                margin-bottom: 0.42rem;
                line-height: 1.35;
            }}

            .landing-problem-list strong {{
                color: rgba(244, 249, 255, 0.94);
            }}

            .landing-problem-heading {{
                margin: 0 0 0.5rem 0;
                font-size: 0.9rem;
                letter-spacing: 0.01em;
                color: rgba(226, 239, 255, 0.92);
            }}

            .landing-section-stack {{
                display: grid;
                gap: 0.65rem;
            }}

            .landing-outcome-callout {{
                margin-top: 0.9rem;
                border-radius: {style_tokens["card_radius"]};
                border: 1px solid rgba(154, 197, 255, 0.38);
                background: linear-gradient(145deg, rgba(16, 40, 77, 0.8), rgba(12, 30, 56, 0.72));
                padding: 0.75rem 0.85rem;
            }}

            .landing-outcome-badge {{
                display: inline-flex;
                align-items: center;
                gap: 0.35rem;
                border: 1px solid rgba(180, 212, 255, 0.45);
                border-radius: 999px;
                padding: 0.13rem 0.48rem;
                font-size: 0.76rem;
                font-weight: 650;
                text-transform: uppercase;
                letter-spacing: 0.02em;
                color: rgba(232, 244, 255, 0.96);
                background: rgba(10, 25, 48, 0.56);
            }}

            .landing-outcome-text {{
                margin: 0.5rem 0 0 0;
                color: rgba(241, 248, 255, 0.95);
                line-height: 1.42;
                font-size: 0.95rem;
            }}

            .landing-flow-step {{
                background: rgba(9, 20, 42, 0.66);
                border: 1px solid rgba(227, 235, 251, 0.18);
                border-radius: 12px;
                padding: 0.75rem;
                min-height: 124px;
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
                background: rgba(8, 19, 38, 0.28);
                border: 1px solid rgba(202, 219, 247, 0.16);
                border-radius: {style_tokens["card_radius"]};
                padding: 0.65rem 0.85rem;
                min-height: 100%;
            }}

            .landing-caption {{
                color: {style_tokens["muted_text_color"]};
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
                color: rgba(226, 239, 255, 0.82);
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
                border: 1px solid rgba(174, 211, 255, 0.55);
                background: linear-gradient(135deg, rgba(20, 74, 142, 0.68), rgba(16, 49, 95, 0.76));
                text-decoration: none !important;
                color: #edf5ff !important;
                font-size: 0.82rem;
                font-weight: 620;
                transition: transform 130ms ease, box-shadow 130ms ease, border-color 130ms ease;
            }}

            .landing-app-link-pill:hover {{
                transform: translateY(-1px);
                box-shadow: 0 8px 20px rgba(3, 11, 24, 0.35);
                border-color: rgba(216, 236, 255, 0.9);
                color: #ffffff !important;
            }}

            .landing-app-link-pill:visited,
            .landing-app-link-pill:focus,
            .landing-app-link-pill:active {{
                text-decoration: none !important;
                color: #edf5ff !important;
            }}

            .landing-security-note {{
                background: rgba(8, 19, 40, 0.5);
                border: 1px solid rgba(225, 235, 252, 0.14);
                border-radius: {style_tokens["card_radius"]};
                padding: 0.8rem 0.95rem;
                color: rgba(229, 239, 255, 0.82);
                font-size: 0.9rem;
            }}

            @media (max-width: 900px) {{
                .landing-hero {{
                    padding: 1.2rem;
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
        unsafe_allow_html=True,
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
    st.markdown(
        f'<section id="{section_id}" class="landing-section landing-hero">',
        unsafe_allow_html=True,
    )
    st.markdown('<div class="landing-hero-copy">', unsafe_allow_html=True)
    st.markdown(f"<h1>{headline}</h1>", unsafe_allow_html=True)
    if subhead:
        st.markdown(f'<p class="landing-subhead">{subhead}</p>', unsafe_allow_html=True)
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
        st.markdown(
            f'<p class="landing-caption">{secondary_cta_hint}</p>',
            unsafe_allow_html=True,
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
                st.markdown(
                    '<ul class="landing-list">'
                    + "".join(f"<li>{bullet}</li>" for bullet in before_start_bullets)
                    + "</ul>",
                    unsafe_allow_html=True,
                )
            if reassurance_line:
                st.caption(reassurance_line)
            if extraction_helper_copy:
                st.info(extraction_helper_copy, icon="ℹ️")
            if post_cta_microcopy:
                st.caption(post_cta_microcopy)
    st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("</section>", unsafe_allow_html=True)

    if show_value_cards and value_cards:
        st.markdown(
            f'<section id="{LANDING_SECTION_IDS["value_cards"]}" class="landing-section">',
            unsafe_allow_html=True,
        )
        st.markdown("### Wertbeitrag auf einen Blick")
        render_value_cards(value_cards=value_cards)
        st.markdown("</section>", unsafe_allow_html=True)


def render_value_cards(*, value_cards: Sequence[tuple[str, str]]) -> None:
    # Keep predictable 2-column rhythm to avoid narrow, uneven cards.
    for row_start in range(0, len(value_cards), 2):
        row_cols = st.columns(2, gap="small")
        for col, (title, body) in zip(row_cols, value_cards[row_start : row_start + 2]):
            with col:
                st.markdown(
                    f'<div class="landing-card"><h4>{title}</h4><p>{body}</p></div>',
                    unsafe_allow_html=True,
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
    st.markdown(
        f'<section id="{section_id}" class="landing-section">',
        unsafe_allow_html=True,
    )
    st.subheader(title)
    st.markdown(
        f'<div class="landing-emphasis"><p>{intro}</p></div>',
        unsafe_allow_html=True,
    )
    risk_items = "".join(
        f"<li><strong>{point_title}:</strong> {body}</li>"
        for point_title, body in risk_points
    )
    leverage_items = "".join(
        f"<li><strong>{point_title}:</strong> {body}</li>"
        for point_title, body in leverage_points
    )
    if risk_items or leverage_items:
        st.markdown('<div class="landing-section-stack">', unsafe_allow_html=True)
    if risk_items:
        st.markdown(
            (
                '<div class="landing-problem-panel">'
                '<h4 class="landing-problem-heading">Ohne sauberen Intake</h4>'
                f'<ul class="landing-problem-list">{risk_items}</ul>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )

    if leverage_items:
        st.markdown(
            (
                '<div class="landing-problem-panel">'
                '<h4 class="landing-problem-heading">Mit präzisem Intake</h4>'
                f'<ul class="landing-problem-list">{leverage_items}</ul>'
                "</div>"
            ),
            unsafe_allow_html=True,
        )
    if risk_items or leverage_items:
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown(
        (
            '<div class="landing-outcome-callout">'
            '<span class="landing-outcome-badge">🏁 Ergebnis</span>'
            f'<p class="landing-outcome-text">{closer}</p>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )
    st.markdown("</section>", unsafe_allow_html=True)


def render_flow_steps(
    *, section_id: str, title: str, steps: Sequence[tuple[str, str]]
) -> None:
    st.markdown(
        f'<section id="{section_id}" class="landing-section">',
        unsafe_allow_html=True,
    )
    st.subheader(title)
    for row_start in range(0, len(steps), 2):
        flow_cols = st.columns(2, gap="small")
        for col, (step_title, body) in zip(flow_cols, steps[row_start : row_start + 2]):
            with col:
                st.markdown(
                    f'<div class="landing-flow-step"><h4>{step_title}</h4><p>{body}</p></div>',
                    unsafe_allow_html=True,
                )
    st.markdown("</section>", unsafe_allow_html=True)


def render_output_section(
    *, section_id: str, title: str, bullets: Sequence[str]
) -> None:
    st.markdown(
        f'<section id="{section_id}" class="landing-section">',
        unsafe_allow_html=True,
    )
    st.subheader(title)
    st.markdown(
        '<div class="landing-output-panel"><ul class="landing-list">'
        + "".join(f"<li>{bullet}</li>" for bullet in bullets)
        + "</ul></div>",
        unsafe_allow_html=True,
    )
    st.markdown("</section>", unsafe_allow_html=True)


def render_security_note(*, section_id: str, title: str, body: str) -> None:
    st.markdown(
        f'<section id="{section_id}" class="landing-section">',
        unsafe_allow_html=True,
    )
    st.subheader(title)
    st.markdown(
        f'<div class="landing-security-note">{body}</div>', unsafe_allow_html=True
    )
    st.markdown("</section>", unsafe_allow_html=True)
