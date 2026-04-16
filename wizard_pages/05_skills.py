# wizard_pages/05_skills.py
from __future__ import annotations

from typing import Any

import streamlit as st
from pydantic import ValidationError

from constants import SSKey
from esco_client import (
    EscoClient,
    EscoClientError,
)
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
    render_compare_adopt_intro,
    render_compact_requirement_board,
    render_error_banner,
    render_question_step,
    render_standard_step_review,
)
from wizard_pages.base import WizardContext, WizardPage, guard_job_and_plan, nav_buttons
from wizard_pages.salary_forecast_panel import render_skills_salary_forecast_panel


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


def _render_skills_source_columns(
    *,
    jobspec_suggested: list[dict[str, Any]],
    esco_suggested: list[dict[str, Any]],
    llm_suggested: list[dict[str, Any]],
) -> None:
    selected_labels_raw = st.session_state.get(SSKey.SKILLS_SELECTED.value, [])
    selected_labels = (
        [str(item).strip() for item in selected_labels_raw if has_meaningful_value(item)]
        if isinstance(selected_labels_raw, list)
        else []
    )

    bulk_buffer = render_compact_requirement_board(
        title_jobspec="Aus Jobspec extrahiert",
        jobspec_items=jobspec_suggested,
        title_esco="ESCO-Skills",
        esco_items=esco_suggested,
        title_llm="AI-Skills",
        llm_items=llm_suggested,
        selected_labels=selected_labels,
        selection_state_key=f"{SSKey.SKILLS_SELECTED.value}.bulk_buffer",
        key_prefix="skills.board",
    )
    if st.button("Ausgewählte Skills übernehmen", width="stretch"):
        added_count = _save_selected_skill_suggestions(bulk_buffer)
        if added_count > 0:
            st.success(f"{added_count} Skill(s) übernommen.")
        else:
            st.info("Keine neuen Skills übernommen.")


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
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], str | None]:
    client = EscoClient()
    try:
        client.get_occupation_detail(uri=occupation_uri)
        must_payload = client.get_occupation_essential_skills(
            occupation_uri=occupation_uri
        )
        nice_payload = client.get_occupation_optional_skills(
            occupation_uri=occupation_uri
        )
    except EscoClientError as exc:
        return [], [], str(exc)

    must_suggestions = _extract_skill_candidates(must_payload)
    nice_suggestions = _extract_skill_candidates(nice_payload)
    return must_suggestions, nice_suggestions, None


def _render_unmapped_term_workflow(flagged_terms: list[str]) -> None:
    st.markdown("#### Offene Begriffe")
    st.caption("Offene Begriffe aus dem Jobspec, verteilt auf drei Spalten.")
    columns = st.columns(3, gap="large")
    for idx, term in enumerate(flagged_terms):
        with columns[idx % 3]:
            st.write(f"- {term}")


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
    nice_to_have_skills = [
        x for x in job.nice_to_have_skills if has_meaningful_value(x)
    ]
    tech_stack = [x for x in job.tech_stack if has_meaningful_value(x)]
    jobspec_suggestions = [
        {"label": term, "source": "Jobspec"}
        for term in _dedupe_terms(
            [*must_have_skills, *nice_to_have_skills, *tech_stack]
        )
    ]
    st.session_state[SSKey.SKILLS_JOBSPEC_SUGGESTED.value] = jobspec_suggestions
    llm_suggested_raw = st.session_state.get(SSKey.SKILLS_LLM_SUGGESTED.value, [])
    llm_suggested = llm_suggested_raw if isinstance(llm_suggested_raw, list) else []

    selected_must_raw = st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_MUST.value, [])
    selected_nice_raw = st.session_state.get(SSKey.ESCO_SKILLS_SELECTED_NICE.value, [])
    selected_must = selected_must_raw if isinstance(selected_must_raw, list) else []
    selected_nice = selected_nice_raw if isinstance(selected_nice_raw, list) else []
    deduped_must, deduped_nice = _dedupe_selected_skills_across_buckets(
        selected_must, selected_nice
    )
    esco_suggestions = (
        [
            {
                "label": str(item.get("title") or "").strip(),
                "source": "ESCO essential",
                "rationale": "manually selected by user",
                "importance": "high",
            }
            for item in deduped_must
            if has_meaningful_value(str(item.get("title") or ""))
        ]
        + [
            {
                "label": str(item.get("title") or "").strip(),
                "source": "ESCO optional",
                "rationale": "manually selected by user",
                "importance": "high",
            }
            for item in deduped_nice
            if has_meaningful_value(str(item.get("title") or ""))
        ]
        if show_esco_sections
        else []
    )

    render_compare_adopt_intro(
        adopt_target="Skills",
        canonical_target="SSKey.SKILLS_SELECTED",
        source_labels=("Jobspec", "AI")
        if not show_esco_sections
        else ("Jobspec", "ESCO", "AI"),
    )
    _render_skills_source_columns(
        jobspec_suggested=jobspec_suggestions,
        esco_suggested=esco_suggestions,
        llm_suggested=llm_suggested,
    )
    st.markdown("#### Skill-Generierung")
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
    col_esco_generate, col_ai_generate = st.columns(2, gap="large")
    with col_esco_generate:
        st.markdown("### ESCO-Skills")
        st.caption(
            "Lädt ESCO Occupation-Details und relationale Skills "
            "(hasEssentialSkill/hasOptionalSkill)."
        )
        load_esco_clicked = st.button(
            "Occupation-Skill-Vorschläge laden", key="skills.esco.load"
        )

    with col_ai_generate:
        st.markdown("### AI Skill-Vorschläge")
        st.number_input(
            "Anzahl AI-Skill-Vorschläge",
            key=SSKey.SKILLS_SUGGEST_COUNT.value,
            min_value=1,
            max_value=12,
            step=1,
        )
        generate_ai_clicked = st.button(
            "Skills-Vorschläge generieren", key="skills.ai.generate"
        )

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

        if load_error:
            st.warning(
                "ESCO-Vorschläge sind aktuell nicht verfügbar. "
                "Du kannst mit manueller Auswahl weiterarbeiten oder später erneut versuchen."
            )
        else:
            st.success(
                f"ESCO-Vorschläge für {occupation_title}: "
                f"{len(suggested_must)} essential, {len(suggested_nice)} optional."
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
                    for item in suggested_must
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
                    for item in suggested_nice
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
        source_comparison_slot=lambda: _render_skills_source_comparison_block(
            job=job,
            selected_occupation=selected_occupation,
            coverage_snapshot=coverage_snapshot,
            show_esco_sections=show_esco_sections,
        ),
        salary_forecast_slot=lambda: _render_salary_forecast_slot(job),
        open_questions_slot=lambda: _render_open_questions_slot(step),
        review_slot=lambda: render_standard_step_review(step),
        footer_slot=lambda: nav_buttons(ctx),
    )


PAGE = WizardPage(
    key="skills",
    title_de="Skills & Anforderungen",
    icon="🧠",
    render=render,
    requires_jobspec=True,
)
