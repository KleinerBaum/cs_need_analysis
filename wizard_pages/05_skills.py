# wizard_pages/05_skills.py
from __future__ import annotations

import os
from html import escape
from typing import Any

import streamlit as st
from pydantic import ValidationError

from constants import SSKey
from esco_client import (
    EscoClient,
    EscoClientError,
)
from esco_matrix import load_esco_matrix
from esco_rag import extract_skill_suggestions, retrieve_esco_context
from llm_client import (
    generate_requirement_gap_suggestions,
)
from components.design_system import render_output_header
from schemas import EscoMappingReport
from schemas import EscoSkillDetail, JobAdExtract, QuestionStep
from state import (
    EscoAnchorStatus,
    EscoCoverageSnapshot,
    get_active_model,
    get_answers,
    get_esco_anchor_status,
    sync_esco_shared_state,
)
from ui_layout import render_step_shell, responsive_three_columns
from ui_components import (
    has_meaningful_value,
    render_esco_picker_card,
    render_error_banner,
    render_question_step,
    ReviewRenderContext,
    resolve_standard_review_mode,
    render_standard_step_review,
)
from wizard_pages.base import (
    WizardContext,
    WizardPage,
    get_current_ui_mode,
    guard_job_and_plan,
    nav_buttons,
)
from wizard_pages.salary_forecast_panel import render_skills_salary_forecast_panel

ESCO_RELATED_ENDPOINT_UNSUPPORTED_MESSAGE = (
    "Dieser ESCO-Endpunkt wird in der aktuell gewählten API-Variante "
    "nicht unterstützt. Occupation-Skill-Vorschläge sind daher hier nicht verfügbar."
)


def _normalize_term(term: str) -> str:
    return " ".join(term.strip().casefold().split())


def _dedupe_terms(values: list[str]) -> list[str]:
    unique_terms: list[str] = []
    seen: set[str] = set()
    for value in values:
        if not has_meaningful_value(value):
            continue
        normalized = _normalize_term(value)
        if not normalized or normalized in seen:
            continue
        unique_terms.append(value.strip())
        seen.add(normalized)
    return unique_terms


def _dedupe_selected_skills_across_buckets(
    must_selected: list[dict[str, Any]],
    nice_selected: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    seen_uris: set[str] = set()
    deduped_must: list[dict[str, Any]] = []
    deduped_nice: list[dict[str, Any]] = []
    for item in must_selected:
        uri = str(item.get("uri") or "").strip()
        if not uri or uri in seen_uris:
            continue
        deduped_must.append(item)
        seen_uris.add(uri)
    for item in nice_selected:
        uri = str(item.get("uri") or "").strip()
        if not uri or uri in seen_uris:
            continue
        deduped_nice.append(item)
        seen_uris.add(uri)
    return deduped_must, deduped_nice


def _extract_skill_candidates(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen: set[str] = set()

    def _walk(value: Any) -> None:
        if isinstance(value, dict):
            uri = str(value.get("uri") or "").strip()
            concept_type = str(value.get("type") or "").strip().lower()
            title = str(
                value.get("title")
                or value.get("preferredLabel")
                or value.get("label")
                or value.get("name")
                or ""
            ).strip()
            is_skill_like = concept_type == "skill" or "/skill/" in uri.casefold()
            if uri and is_skill_like and uri not in seen:
                candidates.append(
                    {
                        "uri": uri,
                        "title": title or uri,
                        "type": concept_type or "skill",
                    }
                )
                seen.add(uri)
            for nested in value.values():
                _walk(nested)
        elif isinstance(value, list):
            for nested in value:
                _walk(nested)

    _walk(payload)
    return candidates


def _merge_suggested_skills_by_uri(
    *,
    suggested_skills: list[dict[str, Any]],
    must_selected: list[dict[str, Any]],
    nice_selected: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], int]:
    existing_uris = {
        str(item.get("uri") or "").strip()
        for item in (must_selected + nice_selected)
        if str(item.get("uri") or "").strip()
    }
    merged: list[dict[str, Any]] = list(must_selected)
    added_count = 0
    for item in suggested_skills:
        uri = str(item.get("uri") or "").strip()
        if not uri or uri in existing_uris:
            continue
        merged.append(item)
        existing_uris.add(uri)
        added_count += 1
    return merged, added_count


def _build_skill_suggestion_context(
    *,
    job: JobAdExtract,
    esco_must_selected: list[dict[str, Any]],
    esco_nice_selected: list[dict[str, Any]],
) -> dict[str, list[str]]:
    jobspec_terms = _dedupe_terms(
        [
            *job.must_have_skills,
            *job.nice_to_have_skills,
            *job.tech_stack,
        ]
    )
    esco_titles = _dedupe_terms(
        [
            str(item.get("title") or "").strip()
            for item in (esco_must_selected + esco_nice_selected)
        ]
    )
    selected_labels_raw = st.session_state.get(SSKey.SKILLS_SELECTED.value, [])
    selected_labels = (
        _dedupe_terms([str(item) for item in selected_labels_raw])
        if isinstance(selected_labels_raw, list)
        else []
    )
    return {
        "jobspec_terms": jobspec_terms,
        "esco_titles": esco_titles,
        "selected_labels": selected_labels,
    }


def _merge_llm_skill_suggestions(
    *,
    llm_skills: list[dict[str, Any]],
    blocked_labels: list[str],
) -> list[dict[str, Any]]:
    accepted: list[dict[str, Any]] = []
    seen_uris: set[str] = set()
    seen = {
        _normalize_term(label)
        for label in blocked_labels
        if has_meaningful_value(label)
    }
    for item in llm_skills:
        label = str(item.get("label") or "").strip()
        uri = str(item.get("uri") or "").strip()
        normalized = _normalize_term(label)
        if (uri and uri in seen_uris) or not normalized or normalized in seen:
            continue
        accepted.append(
            {
                "label": label,
                "uri": uri,
                "source": str(item.get("source") or "AI suggestion").strip(),
                "source_hint": str(item.get("source_hint") or "llm").strip() or "llm",
                "source_file": str(item.get("source_file") or "").strip(),
                "concept_uri": str(item.get("concept_uri") or uri).strip(),
                "importance": str(item.get("importance") or "").strip(),
                "rationale": str(item.get("rationale") or "").strip(),
                "evidence": str(item.get("evidence") or "").strip(),
            }
        )
        seen.add(normalized)
        if uri:
            seen_uris.add(uri)
    return accepted


def _save_selected_skill_suggestions(labels: list[str]) -> int:
    existing_raw = st.session_state.get(SSKey.SKILLS_SELECTED.value, [])
    existing = (
        [str(item) for item in existing_raw if has_meaningful_value(str(item))]
        if isinstance(existing_raw, list)
        else []
    )
    merged = list(existing)
    seen = {_normalize_term(item) for item in existing}
    added_count = 0
    for label in labels:
        normalized = _normalize_term(label)
        if not normalized or normalized in seen:
            continue
        merged.append(label.strip())
        seen.add(normalized)
        added_count += 1
    st.session_state[SSKey.SKILLS_SELECTED.value] = merged
    return added_count


def _get_selected_skill_labels() -> list[str]:
    selected_raw = st.session_state.get(SSKey.SKILLS_SELECTED.value, [])
    if not isinstance(selected_raw, list):
        return []
    return _dedupe_terms([str(item) for item in selected_raw])


def _free_skill_status_key(label: str, uri: str = "") -> str:
    normalized_uri = str(uri or "").strip()
    if normalized_uri:
        return f"uri:{normalized_uri}"
    return f"label:{_normalize_term(label)}"


def _get_free_skill_statuses() -> dict[str, dict[str, str]]:
    raw_statuses = st.session_state.get(SSKey.SKILLS_SELECTED_STATUS.value, {})
    statuses = raw_statuses if isinstance(raw_statuses, dict) else {}
    normalized_statuses: dict[str, dict[str, str]] = {}
    for key, value in statuses.items():
        key_text = str(key or "").strip()
        if not key_text or not isinstance(value, dict):
            continue
        label = str(value.get("label") or "").strip()
        status = str(value.get("status") or "").strip().lower()
        if status not in {"nice", "must"} or not label:
            continue
        normalized_statuses[key_text] = {
            "label": label,
            "status": status,
            "source": str(value.get("source") or "").strip(),
            "group_hint": str(value.get("group_hint") or "").strip(),
            "uri": str(value.get("uri") or "").strip(),
        }
    st.session_state[SSKey.SKILLS_SELECTED_STATUS.value] = normalized_statuses
    return normalized_statuses


def _set_free_skill_status(
    *,
    label: str,
    uri: str,
    source: str,
    group_hint: str,
    status: str | None,
) -> None:
    normalized_label = _normalize_term(label)
    if not normalized_label:
        return
    statuses = _get_free_skill_statuses()
    status_key = _free_skill_status_key(label, uri)
    if status is None:
        statuses.pop(status_key, None)
        _remove_selected_skill_label(label)
    else:
        _save_selected_skill_suggestions([label])
        statuses[status_key] = {
            "label": label.strip(),
            "status": status,
            "source": source.strip(),
            "group_hint": group_hint.strip(),
            "uri": uri.strip(),
        }
    st.session_state[SSKey.SKILLS_SELECTED_STATUS.value] = statuses


def _remove_selected_skill_label(label: str) -> None:
    normalized_label = _normalize_term(label)
    if not normalized_label:
        return
    st.session_state[SSKey.SKILLS_SELECTED.value] = [
        item
        for item in _get_selected_skill_labels()
        if _normalize_term(item) != normalized_label
    ]
    statuses = _get_free_skill_statuses()
    for key, value in list(statuses.items()):
        if _normalize_term(str(value.get("label") or "")) == normalized_label:
            statuses.pop(key, None)
    st.session_state[SSKey.SKILLS_SELECTED_STATUS.value] = statuses


def _skill_title(item: dict[str, Any]) -> str:
    return (
        str(item.get("title") or item.get("label") or "Unbenannter Skill").strip()
        or "Unbenannter Skill"
    )


def _skill_uri(item: dict[str, Any]) -> str:
    return str(item.get("uri") or item.get("concept_uri") or "").strip()


def _find_esco_skill(uri: str, label: str) -> tuple[str | None, dict[str, Any] | None]:
    normalized_label = _normalize_term(label)
    for status, state_key in (
        ("must", SSKey.ESCO_SKILLS_SELECTED_MUST.value),
        ("nice", SSKey.ESCO_SKILLS_SELECTED_NICE.value),
    ):
        existing_raw = st.session_state.get(state_key, [])
        existing = existing_raw if isinstance(existing_raw, list) else []
        for item in existing:
            if not isinstance(item, dict):
                continue
            item_uri = _skill_uri(item)
            if (uri and item_uri == uri) or (
                normalized_label and _normalize_term(_skill_title(item)) == normalized_label
            ):
                return status, item
    return None, None



def _esco_skill_removed_key(uri: str, label: str) -> str:
    uri = str(uri or "").strip()
    if uri:
        return uri
    return f"label:{_normalize_term(label)}"


def _get_removed_esco_skill_keys() -> list[str]:
    raw_removed = st.session_state.get(SSKey.ESCO_SKILLS_REMOVED.value, [])
    removed = raw_removed if isinstance(raw_removed, list) else []
    deduped: list[str] = []
    seen: set[str] = set()
    for item in removed:
        key = str(item or "").strip()
        if not key or key in seen:
            continue
        deduped.append(key)
        seen.add(key)
    st.session_state[SSKey.ESCO_SKILLS_REMOVED.value] = deduped
    return deduped


def _remember_removed_esco_skill(uri: str, label: str) -> None:
    key = _esco_skill_removed_key(uri, label)
    if not key.endswith(":") and key not in _get_removed_esco_skill_keys():
        st.session_state[SSKey.ESCO_SKILLS_REMOVED.value] = [
            *_get_removed_esco_skill_keys(),
            key,
        ]


def _restore_removed_esco_skill(uri: str, label: str) -> None:
    keys_to_restore = {
        _esco_skill_removed_key(uri, label),
        _esco_skill_removed_key("", label),
    }
    st.session_state[SSKey.ESCO_SKILLS_REMOVED.value] = [
        key for key in _get_removed_esco_skill_keys() if key not in keys_to_restore
    ]


def _is_removed_esco_skill(item: dict[str, Any]) -> bool:
    removed = set(_get_removed_esco_skill_keys())
    uri = _skill_uri(item)
    title = _skill_title(item)
    return (
        _esco_skill_removed_key(uri, title) in removed
        or _esco_skill_removed_key("", title) in removed
    )


def _build_skill_item(
    *,
    label: str,
    uri: str,
    source: str,
    group_hint: str,
    status: str,
    existing_item: dict[str, Any] | None = None,
) -> dict[str, Any]:
    relation = "hasEssentialSkill" if status == "must" else "hasOptionalSkill"
    base = dict(existing_item or {})
    base.update(
        {
            "uri": uri.strip(),
            "title": label.strip(),
            "type": str(base.get("type") or "skill").strip() or "skill",
            "relation": relation,
        }
    )
    if source.strip() and not str(base.get("source") or "").strip():
        base["source"] = source.strip()
    if group_hint.strip() and not str(base.get("group_hint") or "").strip():
        base["group_hint"] = group_hint.strip()
    return base


def _remove_esco_skill(uri: str, label: str) -> None:
    normalized_label = _normalize_term(label)
    for state_key in (
        SSKey.ESCO_SKILLS_SELECTED_MUST.value,
        SSKey.ESCO_SKILLS_SELECTED_NICE.value,
    ):
        existing_raw = st.session_state.get(state_key, [])
        existing = existing_raw if isinstance(existing_raw, list) else []
        st.session_state[state_key] = [
            item
            for item in existing
            if not (
                isinstance(item, dict)
                and (
                    (_skill_uri(item) and _skill_uri(item) == uri)
                    or (
                        normalized_label
                        and _normalize_term(_skill_title(item)) == normalized_label
                    )
                )
            )
        ]
    _remove_selected_skill_label(label)
    _remember_removed_esco_skill(uri, label)
    sync_esco_shared_state()


def _set_esco_skill_status(
    *,
    label: str,
    uri: str,
    source: str,
    group_hint: str,
    status: str | None,
) -> None:
    current_status, existing_item = _find_esco_skill(uri, label)
    _remove_esco_skill(uri, label)
    if status is None:
        return
    _restore_removed_esco_skill(uri, label)
    target_key = (
        SSKey.ESCO_SKILLS_SELECTED_MUST.value
        if status == "must"
        else SSKey.ESCO_SKILLS_SELECTED_NICE.value
    )
    existing_raw = st.session_state.get(target_key, [])
    existing = existing_raw if isinstance(existing_raw, list) else []
    item = _build_skill_item(
        label=label,
        uri=uri,
        source=source,
        group_hint=group_hint,
        status=status,
        existing_item=existing_item if current_status else None,
    )
    item_key = uri or _normalize_term(label)
    if item_key and not any(
        isinstance(existing_item, dict)
        and (
            (_skill_uri(existing_item) or _normalize_term(_skill_title(existing_item)))
            == item_key
        )
        for existing_item in existing
    ):
        existing = [*existing, item]
    st.session_state[target_key] = existing
    sync_esco_shared_state()


def _selection_status(label: str, uri: str = "") -> str | None:
    if uri:
        status, _item = _find_esco_skill(uri, label)
        return status
    statuses = _get_free_skill_statuses()
    status_key = _free_skill_status_key(label, uri)
    if status_key in statuses:
        return statuses[status_key]["status"]
    normalized_label = _normalize_term(label)
    if normalized_label in {
        _normalize_term(item) for item in _get_selected_skill_labels()
    }:
        return "nice"
    return None


def _selection_status_label(status: str | None) -> str:
    if status == "must":
        return "Must-have"
    if status == "nice":
        return "Nice-to-have"
    return "Nicht übernommen"


def _cycle_skill_selection(label: str, uri: str, source: str, group_hint: str) -> None:
    """Cycle one skill through: absent → nice-to-have → must-have → removed."""

    label = str(label or "").strip()
    uri = str(uri or "").strip()
    if not label:
        return
    current_status = _selection_status(label, uri)
    next_status = (
        "nice"
        if current_status is None
        else "must"
        if current_status == "nice"
        else None
    )
    if uri:
        _set_esco_skill_status(
            label=label,
            uri=uri,
            source=source,
            group_hint=group_hint,
            status=next_status,
        )
    else:
        _set_free_skill_status(
            label=label,
            uri=uri,
            source=source,
            group_hint=group_hint,
            status=next_status,
        )


def _render_skill_status_surface(
    *,
    jobspec_count: int,
    esco_count: int,
    selected_count: int,
) -> bool:
    render_output_header(
        "Skills & Anforderungen schärfen",
        "Aus Stellenanzeige, ESCO und AI-Vorschlägen entsteht eine prüfbare "
        "Skill-Liste für Brief, Matching und Interview.",
    )
    st.caption(
        f"{jobspec_count} aus der Anzeige erkannt · "
        f"{esco_count} durch ESCO/AI ergänzt · {selected_count} übernommen"
    )
    with st.expander("Weitere AI-Vorschläge", expanded=False):
        st.caption(
            "Die ersten 5 AI-Vorschläge werden automatisch einmalig erzeugt. "
            "Diese Steuerung ergänzt bei zusätzlichem Bedarf weitere Vorschläge."
        )
        count_col, action_col = st.columns([1, 2], gap="small")
        with count_col:
            st.number_input(
                "Anzahl",
                key=SSKey.SKILLS_SUGGEST_COUNT.value,
                min_value=1,
                max_value=12,
                step=1,
                label_visibility="collapsed",
            )
        with action_col:
            return st.button(
                "+ AI-Vorschläge",
                key=SSKey.SKILLS_AI_GENERATE_CLICKED.value,
                width="stretch",
            )


def _render_term_group(title: str, values: list[str], *, limit: int = 10) -> None:
    st.markdown(f"**{title}** · {len(values)}")
    if not values:
        st.caption("Keine Begriffe erkannt.")
        return
    visible_values = values[:limit]
    for value in visible_values:
        st.caption(f"- {value}")
    if len(values) > limit:
        with st.expander(f"Mehr anzeigen ({len(values) - limit})", expanded=False):
            for value in values[limit:]:
                st.caption(f"- {value}")


def _build_jobspec_skill_groups(job: JobAdExtract) -> dict[str, list[str]]:
    return {
        "Must-have": _dedupe_terms(
            [x for x in job.must_have_skills if has_meaningful_value(x)]
        ),
        "Nice-to-have": _dedupe_terms(
            [x for x in job.nice_to_have_skills if has_meaningful_value(x)]
        ),
        "Tech Stack": _dedupe_terms(
            [x for x in job.tech_stack if has_meaningful_value(x)]
        ),
    }


def _render_skill_action_row(
    *,
    label: str,
    source: str,
    key_prefix: str,
    uri: str = "",
    can_mark_optional: bool = True,
    show_status_caption: bool = True,
    group_hint: str = "",
) -> None:
    status = _selection_status(label, uri)
    status_label = _selection_status_label(status)
    compact_label = f"{label} · {status_label}"
    if st.button(compact_label, key=f"{key_prefix}.cycle", width="stretch"):
        _cycle_skill_selection(label, uri, source, group_hint)
    if show_status_caption:
        st.caption(f"{source} · Status: {status_label}")


def _build_skills_source_view_data(
    *,
    job: JobAdExtract,
    show_esco_sections: bool,
) -> tuple[list[str], list[str], list[str], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    jobspec_terms = _dedupe_terms(
        [
            *[x for x in job.must_have_skills if has_meaningful_value(x)],
            *[x for x in job.nice_to_have_skills if has_meaningful_value(x)],
            *[x for x in job.tech_stack if has_meaningful_value(x)],
        ]
    )
    jobspec_suggestions = [{"label": term, "source": "Jobspec"} for term in jobspec_terms]
    st.session_state[SSKey.SKILLS_JOBSPEC_SUGGESTED.value] = jobspec_suggestions

    llm_raw = st.session_state.get(SSKey.SKILLS_LLM_SUGGESTED.value, [])
    llm_suggested = llm_raw if isinstance(llm_raw, list) else []
    llm_labels = _dedupe_terms(
        [str(item.get("label") or "").strip() for item in llm_suggested if isinstance(item, dict)]
    )

    selected_must_raw = st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_MUST.value, [])
    selected_nice_raw = st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_NICE.value, [])
    selected_must = selected_must_raw if isinstance(selected_must_raw, list) else []
    selected_nice = selected_nice_raw if isinstance(selected_nice_raw, list) else []
    deduped_must, deduped_nice = _dedupe_selected_skills_across_buckets(selected_must, selected_nice)
    esco_labels = _dedupe_terms(
        [str(item.get("title") or "").strip() for item in (deduped_must + deduped_nice)]
    ) if show_esco_sections else []
    return jobspec_terms, llm_labels, esco_labels, deduped_must, deduped_nice, llm_suggested


def _llm_skill_label(item: dict[str, Any]) -> str:
    return str(item.get("label") or item.get("title") or "").strip()


def _build_llm_skill_groups(
    *,
    llm_suggested: list[dict[str, Any]],
    tech_stack_terms: list[str],
    blocked_labels: set[str],
) -> dict[str, list[str]]:
    tech_stack_normalized = {_normalize_term(term) for term in tech_stack_terms}
    groups: dict[str, list[str]] = {
        "Must-have": [],
        "Nice-to-have": [],
        "Tech Stack": [],
    }
    for item in llm_suggested:
        if not isinstance(item, dict):
            continue
        label = _llm_skill_label(item)
        normalized = _normalize_term(label)
        if not normalized or normalized in blocked_labels:
            continue
        if normalized in tech_stack_normalized:
            groups["Tech Stack"].append(label)
            continue
        importance = str(item.get("importance") or "").strip().casefold()
        target_group = "Must-have" if importance == "high" else "Nice-to-have"
        groups[target_group].append(label)
    return {title: _dedupe_terms(values) for title, values in groups.items()}


def _render_suggestion_group(
    *,
    title: str,
    esco_items: list[dict[str, Any]],
    ai_labels: list[str],
    key_prefix: str,
    can_mark_optional: bool,
) -> None:
    total_count = len(esco_items) + len(ai_labels)
    st.markdown(f"**{title}** · {total_count}")
    if total_count == 0:
        st.caption("Keine Vorschläge.")
        return
    for index, item in enumerate(esco_items):
        label = _skill_title(item)
        uri = _skill_uri(item)
        source = str(item.get("source") or "ESCO").strip() or "ESCO"
        _render_skill_action_row(
            label=label,
            source=source,
            uri=uri,
            key_prefix=f"{key_prefix}.esco.{index}.{_normalize_term(label)}",
            can_mark_optional=can_mark_optional,
            group_hint=title,
        )
    for index, label in enumerate(ai_labels):
        _render_skill_action_row(
            label=label,
            source="AI",
            key_prefix=f"{key_prefix}.ai.{index}.{_normalize_term(label)}",
            can_mark_optional=can_mark_optional,
            show_status_caption=True,
            group_hint=title,
        )


def _render_selected_group(
    *,
    title: str,
    labels: list[str],
    esco_items: list[dict[str, Any]],
    key_prefix: str,
    can_mark_optional: bool,
) -> None:
    st.markdown(f"**{title}** · {len(labels)}")
    if not labels:
        st.caption("Keine Einträge.")
        return
    for index, label in enumerate(labels):
        matching_item = next(
            (
                item
                for item in esco_items
                if _normalize_term(_skill_title(item)) == _normalize_term(label)
            ),
            {},
        )
        _render_skill_action_row(
            label=label,
            source="Übernommen",
            uri=_skill_uri(matching_item) if isinstance(matching_item, dict) else "",
            key_prefix=f"{key_prefix}.{index}.{_normalize_term(label)}",
            can_mark_optional=can_mark_optional,
            show_status_caption=True,
            group_hint=title,
        )


def _render_skills_source_columns(
    *,
    job: JobAdExtract,
    jobspec_labels: list[str],
    llm_labels: list[str],
    deduped_must: list[dict[str, Any]],
    deduped_nice: list[dict[str, Any]],
    show_esco_sections: bool,
) -> None:
    jobspec_groups = _build_jobspec_skill_groups(job)
    jobspec_count = len(
        _dedupe_terms([term for terms in jobspec_groups.values() for term in terms])
    )

    llm_raw = st.session_state.get(SSKey.SKILLS_LLM_SUGGESTED.value, [])
    llm_suggested = llm_raw if isinstance(llm_raw, list) else []
    selected_labels = _get_selected_skill_labels()
    selected_normalized = {_normalize_term(item) for item in selected_labels}
    esco_titles = _dedupe_terms(
        [_skill_title(item) for item in [*deduped_must, *deduped_nice]]
    )
    esco_normalized = {_normalize_term(title) for title in esco_titles}
    llm_label_set = _dedupe_terms(
        [
            label
            for label in llm_labels
            if _normalize_term(label) not in esco_normalized
        ]
    )
    esco_count = len(_dedupe_terms([*esco_titles, *llm_label_set]))

    llm_groups = _build_llm_skill_groups(
        llm_suggested=llm_suggested,
        tech_stack_terms=jobspec_groups["Tech Stack"],
        blocked_labels=selected_normalized | esco_normalized,
    )

    must_titles = _dedupe_terms([_skill_title(item) for item in deduped_must])
    nice_titles = _dedupe_terms([_skill_title(item) for item in deduped_nice])
    esco_selected_normalized = {
        _normalize_term(item) for item in [*must_titles, *nice_titles]
    }
    selected_tech_stack = _dedupe_terms(
        [
            label
            for label in selected_labels
            if _normalize_term(label) not in esco_selected_normalized
        ]
    )
    selected_count = len(
        _dedupe_terms([*must_titles, *nice_titles, *selected_tech_stack])
    )

    col_jobspec, col_esco, col_selected = st.columns(3, gap="medium")
    with col_jobspec:
        st.metric("Aus Anzeige erkannt", jobspec_count)
        for title, values in jobspec_groups.items():
            _render_term_group(title, values)

    with col_esco:
        st.metric("ESCO ergänzt", esco_count)
        if show_esco_sections:
            st.caption("ESCO + AI als gemeinsame Empfehlungsliste.")
        else:
            st.caption("ESCO-Vorschläge erscheinen nach bestätigtem ESCO-Anker.")
        _render_suggestion_group(
            title="Must-have",
            esco_items=deduped_must if show_esco_sections else [],
            ai_labels=llm_groups["Must-have"],
            key_prefix="skills.recommend.must",
            can_mark_optional=True,
        )
        _render_suggestion_group(
            title="Nice-to-have",
            esco_items=deduped_nice if show_esco_sections else [],
            ai_labels=llm_groups["Nice-to-have"],
            key_prefix="skills.recommend.nice",
            can_mark_optional=False,
        )
        _render_suggestion_group(
            title="Tech Stack",
            esco_items=[],
            ai_labels=llm_groups["Tech Stack"],
            key_prefix="skills.recommend.tech_stack",
            can_mark_optional=True,
        )
    with col_selected:
        st.metric("Übernommen", selected_count)
        st.caption("Finaler Warenkorb für Brief, Matching und Interview.")
        _render_selected_group(
            title="Must-have",
            labels=must_titles,
            esco_items=deduped_must,
            key_prefix="skills.selection.must",
            can_mark_optional=True,
        )
        _render_selected_group(
            title="Nice-to-have",
            labels=nice_titles,
            esco_items=deduped_nice,
            key_prefix="skills.selection.nice",
            can_mark_optional=False,
        )
        _render_selected_group(
            title="Tech Stack",
            labels=selected_tech_stack,
            esco_items=[],
            key_prefix="skills.selection.tech_stack",
            can_mark_optional=True,
        )

    st.session_state[SSKey.SKILLS_SELECTED_BULK_BUFFER.value] = selected_labels


def _safe_text(value: str | None) -> str:
    text = str(value or "").strip()
    return text if text else "Keine Details verfügbar."


def _load_skill_detail_on_demand(
    *,
    uri: str,
    cache: dict[str, dict[str, Any]],
) -> tuple[EscoSkillDetail | None, str | None]:
    cached_payload = cache.get(uri)
    if isinstance(cached_payload, dict):
        try:
            return EscoSkillDetail.model_validate(cached_payload), None
        except ValidationError:
            cache.pop(uri, None)

    client = EscoClient()
    try:
        payload = client.resource_skill(uri=uri)
    except EscoClientError as exc:
        return None, f"Details konnten nicht geladen werden ({exc})."

    raw_label = (
        payload.get("preferredLabel")
        or payload.get("title")
        or payload.get("label")
        or uri
    )
    detail_payload = {
        "label": str(raw_label).strip() or uri,
        "description": payload.get("description"),
        "scopeNote": payload.get("scopeNote"),
    }
    try:
        detail = EscoSkillDetail.model_validate(detail_payload)
    except ValidationError:
        return None, "Details konnten nicht sicher verarbeitet werden."

    cache[uri] = detail.model_dump(by_alias=True)
    return detail, None


def _render_selected_skill_details(
    *,
    title: str,
    selected_skills: list[dict[str, Any]],
    detail_cache: dict[str, dict[str, Any]],
    is_expert_mode: bool,
    key_prefix: str,
) -> None:
    st.markdown(f"#### {title}")
    if not selected_skills:
        st.caption("Noch keine Skills ausgewählt.")
        return

    for index, skill in enumerate(selected_skills):
        uri = str(skill.get("uri") or "").strip()
        label = (
            str(skill.get("title") or "Unbenannter Skill").strip()
            or "Unbenannter Skill"
        )
        if not uri:
            st.caption(f"- {label}")
            continue

        with st.expander(label, expanded=False):
            st.caption("Skill-Details werden nur bei Bedarf geladen.")
            load_key = f"{key_prefix}.detail.load.{index}"
            should_load = st.button("Details laden", key=load_key)
            if should_load:
                loaded_detail, error = _load_skill_detail_on_demand(
                    uri=uri, cache=detail_cache
                )
                if error:
                    st.warning(error)
                elif loaded_detail is not None:
                    st.success("Details geladen.")

            cached_detail_payload = detail_cache.get(uri)
            detail: EscoSkillDetail | None = None
            if isinstance(cached_detail_payload, dict):
                try:
                    detail = EscoSkillDetail.model_validate(cached_detail_payload)
                except ValidationError:
                    detail_cache.pop(uri, None)
            if detail is not None:
                st.write(f"**Bezeichnung:** {_safe_text(detail.label)}")
                st.write(f"**Beschreibung:** {_safe_text(detail.description)}")
                st.write(f"**Hinweis:** {_safe_text(detail.scope_note)}")
            elif should_load:
                st.caption(
                    "Für diesen Skill sind aktuell keine sicheren Details verfügbar."
                )
            else:
                st.caption("Noch keine Details geladen.")

            if is_expert_mode:
                st.caption("URI (optional kopieren):")
                st.code(uri, language=None)


def _load_related_skills_from_selected_occupation(
    occupation_uri: str,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], EscoClientError | None]:
    client = EscoClient()
    try:
        client.get_occupation_detail(uri=occupation_uri)
        if not client.supports_endpoint("resource/related"):
            return (
                [],
                [],
                EscoClientError(
                    status_code=None,
                    endpoint="resource/related",
                    message=ESCO_RELATED_ENDPOINT_UNSUPPORTED_MESSAGE,
                ),
            )
        must_payload = client.get_occupation_essential_skills(
            occupation_uri=occupation_uri
        )
        nice_payload = client.get_occupation_optional_skills(
            occupation_uri=occupation_uri
        )
    except EscoClientError as exc:
        return [], [], exc

    must_suggestions = _extract_skill_candidates(must_payload)
    nice_suggestions = _extract_skill_candidates(nice_payload)
    return must_suggestions, nice_suggestions, None


def _load_matrix_priors(
    occupation_uri: str,
    occupation_group: str | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    if not bool(st.session_state.get(SSKey.ESCO_MATRIX_ENABLED.value, False)):
        return [], []
    matrix_path = os.getenv("ESCO_MATRIX_PATH", "").strip()
    if not matrix_path:
        st.session_state[SSKey.ESCO_MATRIX_LOADED.value] = False
        return [], []
    lookup = load_esco_matrix(matrix_path)
    st.session_state[SSKey.ESCO_MATRIX_LOADED.value] = lookup.metadata.loaded
    st.session_state[SSKey.ESCO_MATRIX_METADATA.value] = {
        "source": lookup.metadata.source,
        "version": lookup.metadata.version,
        "records": lookup.metadata.records,
    }
    return lookup.candidates_for(
        occupation_uri=occupation_uri,
        occupation_group=occupation_group,
    )


def _resolve_matrix_occupation_group(
    selected_occupation: dict[str, Any] | None,
) -> str:
    def _coerce_group_value(value: Any) -> str:
        if isinstance(value, str):
            return value.strip()
        if isinstance(value, (int, float)):
            return str(value).strip()
        if isinstance(value, dict):
            for candidate in value.values():
                resolved = _coerce_group_value(candidate)
                if resolved:
                    return resolved
        if isinstance(value, list):
            for candidate in value:
                resolved = _coerce_group_value(candidate)
                if resolved:
                    return resolved
        return ""

    payload_raw = st.session_state.get(SSKey.ESCO_OCCUPATION_PAYLOAD.value)
    payload = payload_raw if isinstance(payload_raw, dict) else {}
    sources: tuple[dict[str, Any], ...] = (
        selected_occupation if isinstance(selected_occupation, dict) else {},
        payload,
    )
    group_keys = (
        "occupation_group",
        "occupationGroup",
        "iscoGroup",
        "isco08",
        "isco08Code",
        "isco_code",
    )
    for source in sources:
        for key in group_keys:
            value = _coerce_group_value(source.get(key))
            if value:
                return value
    return ""


def _normalize_matrix_group_key(item: dict[str, Any]) -> str:
    uri = str(item.get("skill_group_uri") or "").strip()
    group_id = str(item.get("skill_group_id") or "").strip()
    return uri or group_id


def _coerce_share_percent(value: Any) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value or "").strip().replace(",", ".").replace("%", "")
    if not text:
        return 0.0
    try:
        return float(text)
    except ValueError:
        return 0.0


def _compute_matrix_coverage_rows(
    *,
    occupation_group: str,
    expected_must: list[dict[str, Any]],
    expected_nice: list[dict[str, Any]],
    confirmed_must: list[dict[str, Any]],
    confirmed_nice: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    expected_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    for bucket, rows in (("must", expected_must), ("nice", expected_nice)):
        for row in rows:
            if not isinstance(row, dict):
                continue
            group_key = _normalize_matrix_group_key(row)
            if not group_key:
                continue
            key = (bucket, group_key)
            target = expected_by_key.setdefault(
                key,
                {
                    "occupation_group": occupation_group,
                    "skill_group_uri": str(row.get("skill_group_uri") or "").strip(),
                    "skill_group_id": str(row.get("skill_group_id") or "").strip(),
                    "skill_group_label": str(row.get("skill_group_label") or "").strip()
                    or str(row.get("title") or "").strip()
                    or group_key,
                    "expected_share_percent": _coerce_share_percent(
                        row.get("share_percent")
                    ),
                    "matrix_bucket": bucket,
                    "expected_skill_uris": set(),
                },
            )
            target["expected_share_percent"] = max(
                float(target.get("expected_share_percent") or 0.0),
                _coerce_share_percent(row.get("share_percent")),
            )
            uri = str(row.get("uri") or "").strip()
            if uri:
                target["expected_skill_uris"].add(uri)

    selected_by_uri: dict[str, str] = {}
    selected_group_rows: dict[tuple[str, str], dict[str, Any]] = {}
    for default_bucket, selected_rows in (("must", confirmed_must), ("nice", confirmed_nice)):
        for item in selected_rows:
            if not isinstance(item, dict):
                continue
            uri = str(item.get("uri") or "").strip()
            title = str(item.get("title") or "").strip()
            if uri and uri not in selected_by_uri:
                selected_by_uri[uri] = title or uri
            group_key = _normalize_matrix_group_key(item)
            if not group_key:
                continue
            bucket = str(item.get("matrix_bucket") or "").strip().lower()
            if bucket not in {"must", "nice"}:
                bucket = default_bucket
            key = (bucket, group_key)
            row_target = selected_group_rows.setdefault(
                key,
                {
                    "occupation_group": occupation_group,
                    "skill_group_uri": str(item.get("skill_group_uri") or "").strip(),
                    "skill_group_id": str(item.get("skill_group_id") or "").strip(),
                    "skill_group_label": str(item.get("skill_group_label") or "").strip()
                    or title
                    or group_key,
                    "matrix_bucket": bucket,
                    "matched_skill_uris": set(),
                    "matched_skill_titles": set(),
                },
            )
            if uri:
                row_target["matched_skill_uris"].add(uri)
                row_target["matched_skill_titles"].add(title or uri)

    output_rows: list[dict[str, Any]] = []
    for key, expected in expected_by_key.items():
        bucket, group_key = key
        expected_uris = set(expected.get("expected_skill_uris", set()))
        matched_uris = sorted(uri for uri in expected_uris if uri in selected_by_uri)
        matched_titles = sorted(selected_by_uri[uri] for uri in matched_uris if uri in selected_by_uri)
        match_basis = "uri"

        if not matched_uris:
            selected_group = selected_group_rows.get(key)
            if selected_group is not None:
                matched_uris = sorted(selected_group.get("matched_skill_uris", set()))
                matched_titles = sorted(selected_group.get("matched_skill_titles", set()))
                match_basis = "group"

        expected_count = len(expected_uris)
        matched_count = len(matched_uris)
        if matched_count == 0:
            status = "missing"
        elif expected_count > 0 and matched_count < expected_count:
            status = "partial"
        else:
            status = "covered"

        output_rows.append(
            {
                "occupation_group": occupation_group,
                "skill_group_uri": str(expected.get("skill_group_uri") or ""),
                "skill_group_id": str(expected.get("skill_group_id") or ""),
                "skill_group_label": str(expected.get("skill_group_label") or group_key),
                "expected_share_percent": float(expected.get("expected_share_percent") or 0.0),
                "matched_skill_uris": matched_uris,
                "matched_skill_titles": matched_titles,
                "coverage_status": status,
                "match_basis": match_basis if matched_count > 0 else "none",
                "matrix_bucket": bucket,
            }
        )

    for key, selected_group in selected_group_rows.items():
        if key in expected_by_key:
            continue
        output_rows.append(
            {
                "occupation_group": occupation_group,
                "skill_group_uri": str(selected_group.get("skill_group_uri") or ""),
                "skill_group_id": str(selected_group.get("skill_group_id") or ""),
                "skill_group_label": str(selected_group.get("skill_group_label") or key[1]),
                "expected_share_percent": 0.0,
                "matched_skill_uris": sorted(selected_group.get("matched_skill_uris", set())),
                "matched_skill_titles": sorted(selected_group.get("matched_skill_titles", set())),
                "coverage_status": "overrepresented",
                "match_basis": "group",
                "matrix_bucket": str(selected_group.get("matrix_bucket") or key[0]),
            }
        )

    return sorted(
        output_rows,
        key=lambda row: (
            str(row.get("matrix_bucket") or ""),
            str(row.get("skill_group_label") or "").casefold(),
            str(row.get("skill_group_uri") or ""),
            str(row.get("skill_group_id") or ""),
        ),
    )


def _compute_matrix_coverage_snapshot(
    *,
    matrix_loaded: bool,
    occupation_group: str,
    expected_must: list[dict[str, Any]],
    expected_nice: list[dict[str, Any]],
    confirmed_must: list[dict[str, Any]],
    confirmed_nice: list[dict[str, Any]],
) -> dict[str, Any]:
    if not matrix_loaded:
        return {"rows": [], "reason": "no_matrix_loaded", "occupation_group": "", "rows_count": 0}
    if not occupation_group:
        return {"rows": [], "reason": "occupation_group_missing", "occupation_group": "", "rows_count": 0}
    if not expected_must and not expected_nice:
        return {
            "rows": [],
            "reason": "missing_expected_group",
            "occupation_group": occupation_group,
            "rows_count": 0,
        }
    rows = _compute_matrix_coverage_rows(
        occupation_group=occupation_group,
        expected_must=expected_must,
        expected_nice=expected_nice,
        confirmed_must=confirmed_must,
        confirmed_nice=confirmed_nice,
    )
    return {
        "rows": rows,
        "reason": "ok",
        "occupation_group": occupation_group,
        "rows_count": len(rows),
    }


def _render_matrix_coverage_section(snapshot: dict[str, Any], *, ui_mode: str) -> None:
    st.markdown("#### ESCO Matrix Coverage")
    reason = str(snapshot.get("reason") or "").strip()
    rows = snapshot.get("rows", [])

    reason_messages = {
        "no_matrix_loaded": "Keine Matrix-Coverage verfügbar (Matrix nicht geladen).",
        "occupation_group_missing": "Keine Matrix-Coverage verfügbar (ISCO Occupation Group fehlt).",
        "missing_expected_group": "Keine Matrix-Coverage verfügbar (für diese ISCO Group keine Matrix-Zeilen).",
    }
    if not isinstance(rows, list) or not rows:
        st.warning(reason_messages.get(reason, "Keine Matrix-Coverage verfügbar."))
        technical_expanded = ui_mode == "expert"
        with st.expander("Technische Details", expanded=technical_expanded):
            st.caption(f"reason={reason or 'unknown'}")
            st.caption("covered=0 · partial=0 · missing=0 · overrepresented=0")
        return

    status_counts: dict[str, int] = {"covered": 0, "missing": 0, "partial": 0, "overrepresented": 0}
    for row in rows:
        status = str(row.get("coverage_status") or "").strip().lower()
        if status in status_counts:
            status_counts[status] += 1

    if status_counts["missing"] > 0 or status_counts["partial"] > 0:
        st.warning("Matrix-Coverage hat Lücken: bitte fehlende oder teilweise abgedeckte Skill-Gruppen prüfen.")
    else:
        st.caption("Matrix-Coverage ist vollständig oder überrepräsentiert.")

    technical_expanded = ui_mode == "expert"
    with st.expander("Technische Details", expanded=technical_expanded):
        st.caption(f"reason={reason or 'ok'}")
        st.caption(
            " · ".join(
                [
                    f"covered={status_counts['covered']}",
                    f"partial={status_counts['partial']}",
                    f"missing={status_counts['missing']}",
                    f"overrepresented={status_counts['overrepresented']}",
                ]
            )
        )
        compact_rows = [
            {
                "Bucket": row.get("matrix_bucket"),
                "Skill Group": row.get("skill_group_label"),
                "Expected %": row.get("expected_share_percent"),
                "Matched Skills": len(row.get("matched_skill_uris", [])),
                "Status": row.get("coverage_status"),
            }
            for row in rows
        ]
        st.dataframe(compact_rows, width="stretch", hide_index=True)


def _generate_ai_skill_suggestions(
    *,
    job: JobAdExtract,
    suggestion_context: dict[str, list[str]],
    target_skill_count: int,
) -> list[dict[str, Any]] | None:
    existing_llm_raw = st.session_state.get(SSKey.SKILLS_LLM_SUGGESTED.value, [])
    existing_llm = existing_llm_raw if isinstance(existing_llm_raw, list) else []
    existing_llm_labels = _dedupe_terms(
        [
            _llm_skill_label(item)
            for item in existing_llm
            if isinstance(item, dict)
        ]
    )
    blocked_labels = [
        *suggestion_context["jobspec_terms"],
        *suggestion_context["esco_titles"],
        *suggestion_context["selected_labels"],
        *existing_llm_labels,
    ]
    try:
        suggestion_pack, _usage = generate_requirement_gap_suggestions(
            job=job,
            answers=get_answers(),
            existing_skills=blocked_labels,
            existing_tasks=[],
            esco_skill_titles=suggestion_context["esco_titles"],
            target_skill_count=target_skill_count,
            target_task_count=0,
            model=get_active_model(),
        )
    except Exception:
        st.warning("AI-Vorschläge konnten nicht erzeugt werden.")
        return None

    llm_skill_payload = [
        item.model_dump(mode="json")
        for item in suggestion_pack.skills
        if str(item.type) == "skill"
    ]
    rag_query = " | ".join(
        [
            job.job_title,
            ", ".join(suggestion_context["jobspec_terms"]),
        ]
    ).strip(" |")
    rag_payload: list[dict[str, Any]] = []
    if rag_query:
        rag_result = retrieve_esco_context(
            rag_query,
            purpose="skills",
        )
        if rag_result.reason is None:
            rag_payload = extract_skill_suggestions(rag_result)
    merged_llm = _merge_llm_skill_suggestions(
        llm_skills=[*llm_skill_payload, *rag_payload],
        blocked_labels=blocked_labels,
    )
    combined_llm = [*existing_llm, *merged_llm]
    st.session_state[SSKey.SKILLS_LLM_SUGGESTED.value] = combined_llm
    if merged_llm:
        st.success(f"{len(merged_llm)} AI-Skill(s) übernommen.")
    else:
        st.info("Keine zusätzlichen AI-Skills gefunden.")
    return combined_llm


def _render_unmapped_term_workflow(flagged_terms: list[str]) -> None:
    st.markdown("#### Offene Begriffe")
    st.caption("Für jeden Begriff: ESCO mappen, Freitext behalten, ignorieren oder erneut suchen.")
    actions_raw = st.session_state.get(SSKey.ESCO_UNMAPPED_TERM_ACTIONS.value, {})
    actions = actions_raw if isinstance(actions_raw, dict) else {}
    unresolved_requirement_terms_raw = st.session_state.get(
        SSKey.ESCO_UNMAPPED_REQUIREMENT_TERMS.value, []
    )
    unresolved_requirement_terms = {
        _normalize_term(str(term))
        for term in (unresolved_requirement_terms_raw if isinstance(unresolved_requirement_terms_raw, list) else [])
        if has_meaningful_value(str(term))
    }
    esco_config_raw = st.session_state.get(SSKey.ESCO_CONFIG.value, {})
    esco_config = esco_config_raw if isinstance(esco_config_raw, dict) else {}
    source_mode = str(esco_config.get("data_source_mode") or "").strip() or None

    for term in flagged_terms:
        normalized_term = _normalize_term(term)
        term_key = f"skills.unresolved.{normalized_term}"
        existing = actions.get(term, {}) if isinstance(actions.get(term, {}), dict) else {}
        bucket = "must" if normalized_term in unresolved_requirement_terms else "unknown"
        st.markdown(f"**{term}**")
        action = st.selectbox(
            "Aktion",
            options=["map_to_esco_skill", "keep_free_text", "ignore", "retry_search"],
            index=0,
            key=f"{term_key}.action",
        )
        if action == "map_to_esco_skill":
            render_esco_picker_card(
                concept_type="skill",
                target_state_key=f"{term_key}.map",
                apply_label="ESCO-Mapping übernehmen",
                selection_label="ESCO-Skill auswählen",
                auto_apply_single_select=False,
            )
            picked = st.session_state.get(f"{term_key}.map")
            mapped_uri = str((picked or {}).get("uri") or "").strip() if isinstance(picked, dict) else ""
            mapped_title = str((picked or {}).get("title") or "").strip() if isinstance(picked, dict) else ""
            if mapped_uri:
                actions[term] = {
                    "raw_term": term,
                    "action": action,
                    "mapped_uri": mapped_uri,
                    "mapped_title": mapped_title or None,
                    "bucket": bucket,
                    "source_mode": source_mode,
                }
        elif action == "keep_free_text":
            actions[term] = {
                "raw_term": term,
                "action": action,
                "mapped_uri": None,
                "mapped_title": None,
                "bucket": bucket,
                "source_mode": source_mode,
            }
        elif action == "ignore":
            actions[term] = {
                "raw_term": term,
                "action": action,
                "mapped_uri": None,
                "mapped_title": None,
                "bucket": bucket,
                "source_mode": source_mode,
            }
        else:
            retry_language = st.radio(
                "Retry Sprache",
                options=["de", "en"],
                horizontal=True,
                key=f"{term_key}.retry_lang",
            )
            st.session_state[SSKey.LANGUAGE.value] = retry_language
            render_esco_picker_card(
                concept_type="skill",
                target_state_key=f"{term_key}.retry_map",
                apply_label=f"Retry ({retry_language.upper()}) übernehmen",
                selection_label="Erneute ESCO-Suche",
            )
            picked_retry = st.session_state.get(f"{term_key}.retry_map")
            actions[term] = {
                "raw_term": term,
                "action": action,
                "mapped_uri": str((picked_retry or {}).get("uri") or "").strip() if isinstance(picked_retry, dict) else None,
                "mapped_title": str((picked_retry or {}).get("title") or "").strip() if isinstance(picked_retry, dict) else None,
                "bucket": bucket,
                "source_mode": source_mode,
            }
        if existing and term not in actions:
            actions[term] = existing
    st.session_state[SSKey.ESCO_UNMAPPED_TERM_ACTIONS.value] = actions
    st.session_state[SSKey.ESCO_UNRESOLVED_TERM_DECISIONS.value] = [
        value for value in actions.values() if isinstance(value, dict)
    ]


def _render_extracted_slot(job: JobAdExtract) -> None:
    must_have_skills = [x for x in job.must_have_skills if has_meaningful_value(x)]
    nice_to_have_skills = [
        x for x in job.nice_to_have_skills if has_meaningful_value(x)
    ]
    tech_stack = [x for x in job.tech_stack if has_meaningful_value(x)]
    col_must, col_nice, col_stack = responsive_three_columns(gap="large")
    with col_must:
        st.write("**Must-have (Auszug):**")
        for value in must_have_skills[:12]:
            st.write(f"- {value}")
    with col_nice:
        st.write("**Nice-to-have (Auszug):**")
        for value in nice_to_have_skills[:12]:
            st.write(f"- {value}")
    with col_stack:
        st.write("**Tech Stack (Auszug):**")
        for value in tech_stack[:15]:
            st.write(f"- {value}")
    if not must_have_skills and not nice_to_have_skills and not tech_stack:
        st.info("Keine verlässlichen Werte erkannt. Details siehe Gaps/Assumptions.")


def _render_confirmed_selection_block(
    *,
    deduped_must: list[dict[str, Any]],
    deduped_nice: list[dict[str, Any]],
    detail_cache: dict[str, dict[str, Any]],
    llm_suggested: list[dict[str, Any]],
    is_expert_mode: bool,
    include_details: bool = True,
) -> None:
    st.markdown("#### Auswahl")
    st.caption("Finaler Warenkorb für Brief, Matching und Interview.")
    selected_labels_raw = st.session_state.get(SSKey.SKILLS_SELECTED.value, [])
    selected_labels = (
        _dedupe_terms([str(item) for item in selected_labels_raw])
        if isinstance(selected_labels_raw, list)
        else []
    )
    must_titles = _dedupe_terms(
        [str(item.get("title") or "").strip() for item in deduped_must]
    )
    nice_titles = _dedupe_terms(
        [str(item.get("title") or "").strip() for item in deduped_nice]
    )
    esco_selected_normalized = {
        _normalize_term(item) for item in [*must_titles, *nice_titles]
    }
    company_specific_labels = [
        label
        for label in selected_labels
        if _normalize_term(label) not in esco_selected_normalized
    ]

    st.markdown(
        """
        <style>
        div[data-testid="stVerticalBlock"] div[data-testid="stVerticalBlockBorderWrapper"]:has(.skills-selection-sticky) {
            position: sticky;
            top: 0.85rem;
            z-index: 20;
            background: color-mix(in srgb, var(--background-color) 95%, transparent);
            border-radius: 0.5rem;
            backdrop-filter: blur(2px);
        }
        .skills-chip-row {
            display: flex;
            flex-wrap: wrap;
            gap: 0.35rem;
            margin-top: 0.25rem;
            margin-bottom: 0.3rem;
        }
        .skills-chip {
            display: inline-block;
            max-width: 18rem;
            padding: 0.2rem 0.55rem;
            border-radius: 0.9rem;
            background: color-mix(in srgb, var(--secondary-background-color) 90%, transparent);
            border: 1px solid color-mix(in srgb, var(--text-color) 14%, transparent);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            font-size: 0.82rem;
            line-height: 1.3;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    if include_details:
        basket_col, details_col = st.columns([1.35, 1.65], gap="large")
    else:
        basket_col = st.container()
        details_col = None
    with basket_col:
        sticky = st.container(border=True)
        with sticky:
            st.markdown('<span class="skills-selection-sticky"></span>', unsafe_allow_html=True)
            st.markdown("##### Kategorien")

            def _render_compact_group(title: str, labels: list[str]) -> None:
                st.markdown(f"**{title}** · {len(labels)}")
                if not labels:
                    st.caption("Keine Einträge.")
                    return
                chip_html = "".join(
                    (
                        '<span class="skills-chip" '
                        f'title="{escape(label, quote=True)}">{escape(label)}</span>'
                    )
                    for label in labels
                )
                st.markdown(
                    f'<div class="skills-chip-row">{chip_html}</div>',
                    unsafe_allow_html=True,
                )
                with st.expander("Details anzeigen", expanded=False):
                    for idx, label in enumerate(labels):
                        matching_item = next(
                            (
                                item
                                for item in [*deduped_must, *deduped_nice]
                                if _normalize_term(_skill_title(item))
                                == _normalize_term(label)
                            ),
                            {},
                        )
                        _render_skill_action_row(
                            label=label,
                            source="Auswahl",
                            uri=_skill_uri(matching_item)
                            if isinstance(matching_item, dict)
                            else "",
                            key_prefix=f"skills.selection.{title}.{idx}.{_normalize_term(label)}",
                            can_mark_optional=title != "Nice-to-have",
                        )

            _render_compact_group("Must-have", must_titles)
            _render_compact_group("Nice-to-have", nice_titles)
            _render_compact_group(
                "Unternehmensspezifisch",
                _dedupe_terms(company_specific_labels),
            )

    if not include_details:
        return

    cc1, cc2, cc3 = responsive_three_columns(gap="large")
    if details_col is None:
        return
    with details_col:
        with st.expander("Vertiefung (optional)", expanded=False):
            with cc1:
                _render_selected_skill_details(
                    title="ESCO · Essential",
                    selected_skills=deduped_must,
                    detail_cache=detail_cache,
                    is_expert_mode=is_expert_mode,
                    key_prefix="skills.must",
                )
            with cc2:
                _render_selected_skill_details(
                    title="ESCO · Optional",
                    selected_skills=deduped_nice,
                    detail_cache=detail_cache,
                    is_expert_mode=is_expert_mode,
                    key_prefix="skills.nice",
                )
            with cc3:
                st.markdown("#### AI · Vorschläge")
                if llm_suggested:
                    for item in llm_suggested:
                        label = str(item.get("label") or "").strip()
                        if label:
                            st.write(f"- {label}")
                else:
                    st.caption("Noch keine AI-Skills vorhanden.")


def _maybe_autoload_esco_skill_suggestions(
    *,
    show_esco_sections: bool,
    occupation_uri: str,
    occupation_group: str,
    selected_occupation: dict[str, Any] | None,
    esco_anchor_status: EscoAnchorStatus,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    matrix_expected_must: list[dict[str, Any]] = []
    matrix_expected_nice: list[dict[str, Any]] = []
    if not show_esco_sections:
        return matrix_expected_must, matrix_expected_nice

    if not occupation_uri:
        if esco_anchor_status.status_reason == "anchor_confirmed_invalid_payload":
            st.warning(
                "ESCO-Anker ist bestätigt, aber die Occupation-Payload ist unvollständig oder veraltet. "
                "Bitte ESCO-Auswahl erneut synchronisieren (Start → Phase C)."
            )
        else:
            st.info("ESCO-Sektion wird nach bestätigtem ESCO-Anker eingeblendet.")
        return matrix_expected_must, matrix_expected_nice

    selected_must_raw = st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_MUST.value, [])
    selected_nice_raw = st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_NICE.value, [])
    selected_must = selected_must_raw if isinstance(selected_must_raw, list) else []
    selected_nice = selected_nice_raw if isinstance(selected_nice_raw, list) else []
    if selected_must or selected_nice:
        return matrix_expected_must, matrix_expected_nice

    occupation_title = (
        str(selected_occupation.get("title") or "—").strip()
        if isinstance(selected_occupation, dict)
        else "—"
    )
    with st.spinner("Lade relationale Skills aus ESCO …"):
        suggested_must, suggested_nice, load_error = (
            _load_related_skills_from_selected_occupation(occupation_uri)
        )
    matrix_must: list[dict[str, Any]] = []
    matrix_nice: list[dict[str, Any]] = []
    try:
        matrix_must, matrix_nice = _load_matrix_priors(
            occupation_uri,
            occupation_group=occupation_group,
        )
        matrix_expected_must = list(matrix_must)
        matrix_expected_nice = list(matrix_nice)
    except Exception as exc:
        st.session_state[SSKey.ESCO_MATRIX_LOADED.value] = False
        st.caption(f"Matrix-Prior nicht geladen: {exc}")

    if load_error:
        if load_error.from_negative_cache:
            st.caption(
                "ESCO-Anfragen kurzzeitig gedrosselt (wiederholter 4xx-Fehler). "
                f"Unterdrückte Wiederholungen: {load_error.suppressed_repeat_count}."
            )
        elif load_error.endpoint == "resource/related" and load_error.status_code is None:
            st.info(load_error.message)
        else:
            st.warning(
                "ESCO-Vorschläge sind aktuell nicht verfügbar. "
                "Du kannst mit manueller Auswahl weiterarbeiten oder später erneut versuchen."
            )
        return matrix_expected_must, matrix_expected_nice

    merged_must, added_must = _merge_suggested_skills_by_uri(
        suggested_skills=[
            {
                **item,
                "relation": "hasEssentialSkill",
                "related_occupation_uri": occupation_uri,
            }
            for item in [*suggested_must, *matrix_must]
            if not _is_removed_esco_skill(item)
        ],
        must_selected=selected_must,
        nice_selected=selected_nice,
    )
    merged_nice, added_nice = _merge_suggested_skills_by_uri(
        suggested_skills=[
            {
                **item,
                "relation": "hasOptionalSkill",
                "related_occupation_uri": occupation_uri,
            }
            for item in [*suggested_nice, *matrix_nice]
            if not _is_removed_esco_skill(item)
        ],
        must_selected=selected_nice,
        nice_selected=merged_must,
    )
    st.session_state[SSKey.ESCO_SKILLS_SELECTED_MUST.value] = merged_must
    st.session_state[SSKey.ESCO_SKILLS_SELECTED_NICE.value] = merged_nice
    st.caption(
        f"ESCO ergänzt {added_must + added_nice} Skills für {occupation_title}."
    )
    return matrix_expected_must, matrix_expected_nice


def _render_skills_source_comparison_block(
    *,
    job: JobAdExtract,
    selected_occupation: dict[str, Any] | None,
    coverage_snapshot: EscoCoverageSnapshot,
    show_esco_sections: bool,
    esco_anchor_status: EscoAnchorStatus,
) -> None:
    must_have_skills = [x for x in job.must_have_skills if has_meaningful_value(x)]
    nice_to_have_skills = [x for x in job.nice_to_have_skills if has_meaningful_value(x)]
    jobspec_labels, llm_labels, _esco_labels, deduped_must, deduped_nice, llm_suggested = _build_skills_source_view_data(
        job=job,
        show_esco_sections=show_esco_sections,
    )
    normalized_must_terms = _dedupe_terms(must_have_skills)
    normalized_nice_terms = _dedupe_terms(nice_to_have_skills)

    occupation_uri = (
        (
            coverage_snapshot.selected_occupation_uri
            or (
                str(selected_occupation.get("uri") or "").strip()
                if selected_occupation
                else ""
            )
        )
        if show_esco_sections
        else ""
    )
    occupation_group = _resolve_matrix_occupation_group(selected_occupation) if show_esco_sections else ""
    matrix_expected_must, matrix_expected_nice = _maybe_autoload_esco_skill_suggestions(
        show_esco_sections=show_esco_sections,
        occupation_uri=occupation_uri,
        occupation_group=occupation_group,
        selected_occupation=selected_occupation,
        esco_anchor_status=esco_anchor_status,
    )

    selected_must_raw = st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_MUST.value, [])
    selected_nice_raw = st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_NICE.value, [])
    selected_must = selected_must_raw if isinstance(selected_must_raw, list) else []
    selected_nice = selected_nice_raw if isinstance(selected_nice_raw, list) else []

    deduped_must, deduped_nice = _dedupe_selected_skills_across_buckets(
        selected_must, selected_nice
    )
    duplicate_count = (len(selected_must) + len(selected_nice)) - (
        len(deduped_must) + len(deduped_nice)
    )
    if duplicate_count > 0:
        notes = [f"{duplicate_count} Duplikat(e) über Must/Nice anhand URI entfernt."]
    else:
        notes = []

    st.session_state[SSKey.ESCO_SKILLS_SELECTED_MUST.value] = deduped_must
    st.session_state[SSKey.ESCO_SKILLS_SELECTED_NICE.value] = deduped_nice
    st.session_state[SSKey.ESCO_CONFIRMED_ESSENTIAL_SKILLS.value] = deduped_must
    st.session_state[SSKey.ESCO_CONFIRMED_OPTIONAL_SKILLS.value] = deduped_nice
    raw_detail_cache = st.session_state.get(SSKey.ESCO_SKILL_DETAIL_CACHE.value, {})
    detail_cache = raw_detail_cache if isinstance(raw_detail_cache, dict) else {}
    st.session_state[SSKey.ESCO_SKILL_DETAIL_CACHE.value] = detail_cache
    ui_mode = get_current_ui_mode()

    llm_count_labels = _dedupe_terms(
        [
            label
            for label in llm_labels
            if _normalize_term(label)
            not in {
                _normalize_term(_skill_title(item))
                for item in [*deduped_must, *deduped_nice]
            }
        ]
    )
    selected_status_labels = _dedupe_terms(
        [
            *[_skill_title(item) for item in [*deduped_must, *deduped_nice]],
            *_get_selected_skill_labels(),
        ]
    )
    generate_ai_clicked = _render_skill_status_surface(
        jobspec_count=len(_dedupe_terms(jobspec_labels)),
        esco_count=len(
            _dedupe_terms(
                [
                    *[_skill_title(item) for item in [*deduped_must, *deduped_nice]],
                    *llm_count_labels,
                ]
            )
        ),
        selected_count=len(selected_status_labels),
    )

    mapped_titles = {
        _normalize_term(str(item.get("title") or ""))
        for item in (deduped_must + deduped_nice)
    }
    follow_up_terms = [
        term
        for term in _dedupe_terms(normalized_must_terms + normalized_nice_terms)
        if _normalize_term(term) not in mapped_titles
    ]
    mapping_report = EscoMappingReport.model_validate(
        {
            "mapped_count": len(deduped_must) + len(deduped_nice),
            "unmapped_terms": _dedupe_terms(follow_up_terms),
            "collisions": [],
            "notes": notes,
        }
    ).model_dump()
    st.session_state[SSKey.ESCO_SKILLS_MAPPING_REPORT.value] = mapping_report
    st.session_state[SSKey.ESCO_UNMAPPED_REQUIREMENT_TERMS.value] = list(
        mapping_report["unmapped_terms"]
    )
    coverage_snapshot = sync_esco_shared_state()

    if show_esco_sections and occupation_uri:
        if not matrix_expected_must and not matrix_expected_nice:
            try:
                matrix_expected_must, matrix_expected_nice = _load_matrix_priors(
                    occupation_uri,
                    occupation_group=occupation_group,
                )
            except Exception:
                matrix_expected_must, matrix_expected_nice = [], []
        matrix_snapshot = _compute_matrix_coverage_snapshot(
            matrix_loaded=bool(
                st.session_state.get(SSKey.ESCO_MATRIX_LOADED.value, False)
            ),
            occupation_group=occupation_group,
            expected_must=matrix_expected_must,
            expected_nice=matrix_expected_nice,
            confirmed_must=deduped_must,
            confirmed_nice=deduped_nice,
        )
    else:
        matrix_snapshot = {
            "rows": [],
            "reason": "occupation_group_missing",
            "occupation_group": "",
            "rows_count": 0,
        }
    st.session_state[SSKey.ESCO_MATRIX_COVERAGE_ROWS.value] = list(
        matrix_snapshot.get("rows", [])
    ) if isinstance(matrix_snapshot.get("rows", []), list) else []
    st.session_state[SSKey.ESCO_MATRIX_COVERAGE_CONTEXT.value] = {
        "reason": str(matrix_snapshot.get("reason") or ""),
        "occupation_group": str(matrix_snapshot.get("occupation_group") or ""),
        "rows": int(matrix_snapshot.get("rows_count") or 0),
    }
    suggestion_context = _build_skill_suggestion_context(
        job=job,
        esco_must_selected=deduped_must,
        esco_nice_selected=deduped_nice,
    )
    initial_ai_generated = bool(
        st.session_state.get(SSKey.SKILLS_AI_INITIAL_GENERATED.value, False)
    )
    existing_llm_raw = st.session_state.get(SSKey.SKILLS_LLM_SUGGESTED.value, [])
    existing_llm = existing_llm_raw if isinstance(existing_llm_raw, list) else []
    should_auto_generate_ai = not initial_ai_generated and not existing_llm
    if not initial_ai_generated and existing_llm:
        st.session_state[SSKey.SKILLS_AI_INITIAL_GENERATED.value] = True
    if should_auto_generate_ai or generate_ai_clicked:
        st.session_state[SSKey.SKILLS_AI_INITIAL_GENERATED.value] = True
        target_skill_count = 5 if should_auto_generate_ai else int(
            st.session_state.get(SSKey.SKILLS_SUGGEST_COUNT.value, 5)
        )
        with st.spinner("Generiere Skill-Vorschläge …"):
            _generate_ai_skill_suggestions(
                job=job,
                suggestion_context=suggestion_context,
                target_skill_count=target_skill_count,
            )

    jobspec_labels, llm_labels, _esco_labels, deduped_must, deduped_nice, llm_suggested = _build_skills_source_view_data(
        job=job,
        show_esco_sections=show_esco_sections,
    )
    _render_skills_source_columns(
        job=job,
        jobspec_labels=jobspec_labels,
        llm_labels=llm_labels,
        deduped_must=deduped_must,
        deduped_nice=deduped_nice,
        show_esco_sections=show_esco_sections,
    )

    ambiguous_terms = sorted(
        {
            term
            for term in normalized_must_terms
            if _normalize_term(term)
            in {_normalize_term(value) for value in normalized_nice_terms}
        }
    )
    unmapped_terms = list(coverage_snapshot.unmapped_requirement_terms)
    flagged_terms = _dedupe_terms([*ambiguous_terms, *unmapped_terms])
    selected_count = len(_get_selected_skill_labels())
    open_count = len(flagged_terms)
    status_label = (
        "Bereit für Recruiting Brief und Interviewfragen"
        if open_count == 0
        else "Bitte offene Begriffe technisch prüfen"
    )
    st.info(
        f"{selected_count} Skills übernommen · "
        f"{open_count} offene Begriffe · {status_label}"
    )
    with st.expander("Advanced / Technische Prüfung", expanded=False):
        st.caption("Status: inferred context")
        st.caption("SSKey.SKILLS_SELECTED")
        st.caption("contains/filter")
        st.caption("map_to_esco_skill · keep_free_text · retry_search")
        if show_esco_sections:
            _render_matrix_coverage_section(matrix_snapshot, ui_mode=ui_mode)
        if show_esco_sections and flagged_terms:
            _render_unmapped_term_workflow(flagged_terms)
        else:
            st.caption(
                "Keine offenen oder mehrdeutigen Skill-Begriffe vorhanden."
                if show_esco_sections
                else "ESCO-spezifische Normalisierung ist ohne bestätigten ESCO-Anker ausgeblendet."
            )


def _render_salary_forecast_slot(job: JobAdExtract) -> None:
    selected_skills_raw = st.session_state.get(SSKey.SKILLS_SELECTED.value, [])
    selected_skills = (
        _dedupe_terms([str(item) for item in selected_skills_raw])
        if isinstance(selected_skills_raw, list)
        else []
    )
    role_tasks_raw = st.session_state.get(SSKey.ROLE_TASKS_SELECTED.value, [])
    role_tasks = (
        _dedupe_terms([str(item) for item in role_tasks_raw])
        if isinstance(role_tasks_raw, list)
        else []
    )
    render_skills_salary_forecast_panel(
        job=job,
        selected_skills=selected_skills,
        selected_role_tasks=role_tasks,
        model=get_active_model(),
        language=str(st.session_state.get(SSKey.LANGUAGE.value, "de")),
        store=bool(st.session_state.get(SSKey.STORE_API_OUTPUT.value, False)),
    )


def _render_open_questions_slot(step: QuestionStep | None) -> None:
    if step is not None and step.questions:
        render_question_step(step)


def render(ctx: WizardContext) -> None:
    render_error_banner()

    preflight = guard_job_and_plan(ctx)
    if preflight is None:
        return

    job, plan = preflight
    esco_anchor_status = get_esco_anchor_status()
    selected_occupation = esco_anchor_status.selected_occupation
    show_esco_sections = esco_anchor_status.anchor_confirmed
    coverage_snapshot = sync_esco_shared_state()
    step = next((value for value in plan.steps if value.step_key == "skills"), None)

    if show_esco_sections and selected_occupation:
        st.caption(
            "ESCO Occupation aus Start → Phase C: Semantischen Anker bestätigen: "
            f"{selected_occupation.get('title', '—')}"
        )

    render_step_shell(
        title="Skills & Anforderungen",
        subtitle=(
            "Skills aus Anzeige, ESCO und AI kuratieren und als belastbare "
            "Anforderungsliste bestätigen."
        ),
        outcome_text=(
            "Eine prüfbare Skill-Liste für Recruiting Brief, Matching und Interviewfragen."
        ),
        step=step,
        source_comparison_slot=lambda: _render_skills_source_comparison_block(
            job=job,
            selected_occupation=selected_occupation,
            coverage_snapshot=coverage_snapshot,
            show_esco_sections=show_esco_sections,
            esco_anchor_status=esco_anchor_status,
        ),
        salary_forecast_slot=lambda: _render_salary_forecast_slot(job),
        open_questions_slot=lambda: _render_open_questions_slot(step),
        review_slot=lambda: render_standard_step_review(
            step,
            render_mode=resolve_standard_review_mode(context=ReviewRenderContext.STEP_FORM),
        ),
        footer_slot=lambda: nav_buttons(ctx),
    )


PAGE = WizardPage(
    key="skills",
    title_de="Skills & Anforderungen",
    icon="🧠",
    render=render,
    requires_jobspec=True,
)
