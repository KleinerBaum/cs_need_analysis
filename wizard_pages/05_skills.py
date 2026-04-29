# wizard_pages/05_skills.py
from __future__ import annotations

import os
from typing import Any

import streamlit as st
from pydantic import ValidationError

from constants import SSKey
from esco_client import (
    EscoClient,
    EscoClientError,
)
from esco_matrix import load_esco_matrix
from llm_client import (
    generate_requirement_gap_suggestions,
)
from schemas import EscoMappingReport
from schemas import EscoSkillDetail, JobAdExtract, QuestionStep
from state import (
    EscoCoverageSnapshot,
    get_active_model,
    get_answers,
    get_esco_occupation_selected,
    has_confirmed_esco_anchor,
    sync_esco_shared_state,
)
from ui_layout import render_step_shell
from ui_components import (
    has_meaningful_value,
    render_esco_picker_card,
    render_compare_adopt_intro,
    render_error_banner,
    render_multi_select_pills,
    render_question_step,
    render_standard_step_review,
)
from wizard_pages.base import WizardContext, WizardPage, guard_job_and_plan, nav_buttons
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
    seen = {
        _normalize_term(label)
        for label in blocked_labels
        if has_meaningful_value(label)
    }
    for item in llm_skills:
        label = str(item.get("label") or "").strip()
        normalized = _normalize_term(label)
        if not normalized or normalized in seen:
            continue
        accepted.append(
            {
                "label": label,
                "source": "AI suggestion",
                "importance": str(item.get("importance") or "").strip(),
                "rationale": str(item.get("rationale") or "").strip(),
                "evidence": str(item.get("evidence") or "").strip(),
            }
        )
        seen.add(normalized)
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


def _render_skills_source_columns(
    *,
    jobspec_labels: list[str],
    llm_labels: list[str],
    esco_labels: list[str],
) -> tuple[bool, bool]:
    selected_labels_raw = st.session_state.get(SSKey.SKILLS_SELECTED.value, [])
    selected_labels = _dedupe_terms([str(item) for item in selected_labels_raw]) if isinstance(selected_labels_raw, list) else []
    selected_normalized = {_normalize_term(item) for item in selected_labels}

    col_jobspec, col_ai, col_esco = st.columns(3, gap="large")
    with col_jobspec:
        st.markdown("#### Aus der Anzeige extrahiert")
        render_multi_select_pills(
            " ",
            options=jobspec_labels,
            key="skills.jobspec.pills",
            default=[item for item in selected_labels if _normalize_term(item) in {_normalize_term(v) for v in jobspec_labels}],
        )
    with col_ai:
        st.markdown("#### AI-Vorschläge")
        st.number_input(
            "Anzahl AI-Skill-Vorschläge",
            key=SSKey.SKILLS_SUGGEST_COUNT.value,
            min_value=1,
            max_value=12,
            step=1,
        )
        generate_ai_clicked = st.button(
            "AI-Skill-Vorschläge generieren", key="skills.ai.generate"
        )
        render_multi_select_pills(
            "  ",
            options=llm_labels,
            key="skills.ai.pills",
            default=[item for item in selected_labels if _normalize_term(item) in {_normalize_term(v) for v in llm_labels}],
        )
    with col_esco:
        st.markdown("#### ESCO")
        load_esco_clicked = st.button("ESCO-Skills laden", key="skills.esco.load")
        for label in esco_labels:
            normalized = _normalize_term(label)
            relation = "optional"
            source_badge = "ESCO"
            if normalized in {_normalize_term(str(v.get("title") or "")) for v in st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_MUST.value, []) if isinstance(v, dict)}:
                relation = "essential"
            for item in (
                st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_MUST.value, [])
                + st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_NICE.value, [])
            ):
                if isinstance(item, dict) and _normalize_term(str(item.get("title") or "")) == normalized:
                    if str(item.get("source") or "").strip() == "ESCO matrix prior":
                        source_badge = "ESCO matrix prior"
                    break
            st.caption(f"{label} · {relation} · {source_badge}")
        render_multi_select_pills(
            "   ",
            options=esco_labels,
            key="skills.esco.pills",
            default=[item for item in selected_labels if _normalize_term(item) in {_normalize_term(v) for v in esco_labels}],
        )

    selected_jobspec = st.session_state.get("skills.jobspec.pills", []) or []
    selected_ai = st.session_state.get("skills.ai.pills", []) or []
    selected_esco = st.session_state.get("skills.esco.pills", []) or []
    buffer = _dedupe_terms([*selected_jobspec, *selected_ai, *selected_esco, *selected_labels])
    st.session_state[f"{SSKey.SKILLS_SELECTED.value}.bulk_buffer"] = buffer
    if st.button("Ausgewählte Skills übernehmen", width="stretch"):
        _save_selected_skill_suggestions(buffer)
    current_selected = st.session_state.get(SSKey.SKILLS_SELECTED.value, [])
    current_count = len(_dedupe_terms([str(item) for item in current_selected])) if isinstance(current_selected, list) else 0
    st.caption(f"Übernommen: {current_count} Skills")
    return load_esco_clicked, generate_ai_clicked


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


def _render_matrix_coverage_section(snapshot: dict[str, Any]) -> None:
    st.markdown("#### ESCO Matrix Coverage")
    reason = str(snapshot.get("reason") or "").strip()
    rows = snapshot.get("rows", [])
    if not isinstance(rows, list) or not rows:
        if reason == "no_matrix_loaded":
            st.caption("Keine Matrix-Coverage verfügbar (Matrix nicht geladen).")
        elif reason == "occupation_group_missing":
            st.caption("Keine Matrix-Coverage verfügbar (ISCO Occupation Group fehlt).")
        elif reason == "missing_expected_group":
            st.caption("Keine Matrix-Coverage verfügbar (für diese ISCO Group keine Matrix-Zeilen).")
        else:
            st.caption("Keine Matrix-Coverage verfügbar.")
        return

    status_counts: dict[str, int] = {"covered": 0, "missing": 0, "partial": 0, "overrepresented": 0}
    for row in rows:
        status = str(row.get("coverage_status") or "").strip().lower()
        if status in status_counts:
            status_counts[status] += 1
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
    st.dataframe(compact_rows, use_container_width=True, hide_index=True)


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
    col_must, col_nice, col_stack = st.columns(3, gap="large")
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
) -> None:
    st.markdown("#### Bestätigte Auswahl")
    cc1, cc2, cc3 = st.columns(3, gap="large")
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


def _render_skills_source_comparison_block(
    *,
    job: JobAdExtract,
    selected_occupation: dict[str, Any] | None,
    coverage_snapshot: EscoCoverageSnapshot,
    show_esco_sections: bool,
) -> None:
    must_have_skills = [x for x in job.must_have_skills if has_meaningful_value(x)]
    nice_to_have_skills = [x for x in job.nice_to_have_skills if has_meaningful_value(x)]
    jobspec_labels, llm_labels, esco_labels, deduped_must, deduped_nice, llm_suggested = _build_skills_source_view_data(
        job=job,
        show_esco_sections=show_esco_sections,
    )

    render_compare_adopt_intro(
        adopt_target="Skills",
        canonical_target="SSKey.SKILLS_SELECTED",
        source_labels=("Jobspec", "AI")
        if not show_esco_sections
        else ("Jobspec", "ESCO", "AI"),
    )
    load_esco_clicked, generate_ai_clicked = _render_skills_source_columns(
        jobspec_labels=jobspec_labels,
        esco_labels=esco_labels,
        llm_labels=llm_labels,
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
    matrix_expected_must: list[dict[str, Any]] = []
    matrix_expected_nice: list[dict[str, Any]] = []
    if show_esco_sections and occupation_uri and load_esco_clicked:
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
            elif (
                load_error.endpoint == "resource/related"
                and load_error.status_code is None
            ):
                st.info(load_error.message)
            else:
                st.warning(
                    "ESCO-Vorschläge sind aktuell nicht verfügbar. "
                    "Du kannst mit manueller Auswahl weiterarbeiten oder später erneut versuchen."
                )
        else:
            st.success(
                f"ESCO-Vorschläge für {occupation_title}: "
                f"{len(suggested_must)} essential, {len(suggested_nice)} optional."
            )
            if matrix_must or matrix_nice:
                st.caption(
                    "Zusätzliche Matrix-Priors: "
                    f"{len(matrix_must)} essential, {len(matrix_nice)} optional "
                    "(Quelle: ESCO matrix prior)."
                )
            selected_must_raw = st.session_state.get(
                SSKey.ESCO_SKILLS_SELECTED_MUST.value, []
            )
            selected_nice_raw = st.session_state.get(
                SSKey.ESCO_SKILLS_SELECTED_NICE.value, []
            )
            selected_must = (
                selected_must_raw if isinstance(selected_must_raw, list) else []
            )
            selected_nice = (
                selected_nice_raw if isinstance(selected_nice_raw, list) else []
            )

            merged_must, added_must = _merge_suggested_skills_by_uri(
                suggested_skills=[
                    {
                        **item,
                        "relation": "hasEssentialSkill",
                        "related_occupation_uri": occupation_uri,
                    }
                    for item in [*suggested_must, *matrix_must]
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
                ],
                must_selected=merged_must,
                nice_selected=selected_nice,
            )
            st.session_state[SSKey.ESCO_SKILLS_SELECTED_MUST.value] = merged_must
            st.session_state[SSKey.ESCO_SKILLS_SELECTED_NICE.value] = merged_nice
            st.info(
                f"Übernommen: {added_must} Must, {added_nice} Nice "
                "(dedupliziert anhand ESCO-URI)."
            )
    elif show_esco_sections:
        st.info("Keine ESCO Occupation ausgewählt.")

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
    ui_mode = str(st.session_state.get(SSKey.UI_MODE.value, "standard")).strip().lower()
    is_expert_mode = ui_mode == "expert"

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
    if show_esco_sections:
        _render_matrix_coverage_section(matrix_snapshot)

    suggestion_context = _build_skill_suggestion_context(
        job=job,
        esco_must_selected=deduped_must,
        esco_nice_selected=deduped_nice,
    )
    if generate_ai_clicked:
        with st.spinner("Generiere Skill-Vorschläge …"):
            try:
                suggestion_pack, _usage = generate_requirement_gap_suggestions(
                    job=job,
                    answers=get_answers(),
                    existing_skills=[
                        *suggestion_context["jobspec_terms"],
                        *suggestion_context["esco_titles"],
                        *suggestion_context["selected_labels"],
                    ],
                    existing_tasks=[],
                    esco_skill_titles=suggestion_context["esco_titles"],
                    target_skill_count=int(
                        st.session_state.get(SSKey.SKILLS_SUGGEST_COUNT.value, 5)
                    ),
                    target_task_count=0,
                    model=get_active_model(),
                )
            except Exception:
                st.warning("AI-Vorschläge konnten nicht erzeugt werden.")
            else:
                llm_skill_payload = [
                    item.model_dump(mode="json")
                    for item in suggestion_pack.skills
                    if str(item.type) == "skill"
                ]
                merged_llm = _merge_llm_skill_suggestions(
                    llm_skills=llm_skill_payload,
                    blocked_labels=[
                        *suggestion_context["jobspec_terms"],
                        *suggestion_context["esco_titles"],
                        *suggestion_context["selected_labels"],
                    ],
                )
                st.session_state[SSKey.SKILLS_LLM_SUGGESTED.value] = merged_llm
                llm_suggested = merged_llm
                if merged_llm:
                    st.success(f"{len(merged_llm)} AI-Skill(s) übernommen.")
                else:
                    st.info("Keine zusätzlichen AI-Skills gefunden.")

    _render_confirmed_selection_block(
        deduped_must=deduped_must,
        deduped_nice=deduped_nice,
        detail_cache=detail_cache,
        llm_suggested=llm_suggested,
        is_expert_mode=is_expert_mode,
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
    selected_occupation = get_esco_occupation_selected()
    show_esco_sections = has_confirmed_esco_anchor()
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
            "Ziel: Rohbegriffe aus dem Jobspec zuerst sichtbar machen, dann mit ESCO "
            "vereinheitlichen und abschließend als essential oder optional bestätigen."
        ),
        outcome_text=(
            "Eine bestätigte Skill-Liste (essential/optional) mit nachvollziehbarer Herkunft "
            "aus Jobspec, ESCO und AI-Vorschlägen."
        ),
        step=step,
        extracted_from_jobspec_slot=lambda: _render_extracted_slot(job),
        extracted_from_jobspec_label="Aus der Anzeige extrahierte Skills",
        extracted_from_jobspec_use_expander=False,
        open_questions_slot=lambda: _render_open_questions_slot(step),
        review_slot=lambda: render_standard_step_review(step),
        after_review_slot=lambda: (
            _render_skills_source_comparison_block(
                job=job,
                selected_occupation=selected_occupation,
                coverage_snapshot=coverage_snapshot,
                show_esco_sections=show_esco_sections,
            ),
            _render_salary_forecast_slot(job),
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
