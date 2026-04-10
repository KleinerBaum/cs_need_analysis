# wizard_pages/05_skills.py
from __future__ import annotations

from typing import Any

import streamlit as st

from constants import SSKey
from schemas import EscoMappingReport
from schemas import JobAdExtract, QuestionPlan
from state import get_esco_occupation_selected
from ui_components import (
    has_meaningful_value,
    render_error_banner,
    render_esco_picker_card,
    render_question_step,
)
from wizard_pages.base import WizardContext, WizardPage, nav_buttons


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


def render(ctx: WizardContext) -> None:
    st.header("Skills & Anforderungen")
    render_error_banner()

    job_dict = st.session_state.get(SSKey.JOB_EXTRACT.value)
    plan_dict = st.session_state.get(SSKey.QUESTION_PLAN.value)

    if not job_dict or not plan_dict:
        st.warning("Bitte zuerst im Start-Schritt eine Analyse durchführen.")
        st.button("Zur Startseite", on_click=lambda: ctx.goto("landing"))
        nav_buttons(ctx, disable_next=True)
        return

    job = JobAdExtract.model_validate(job_dict)
    plan = QuestionPlan.model_validate(plan_dict)

    st.write(
        "Ziel: Must-have vs Nice-to-have klar trennen, Level definieren, "
        "und daraus eine Interview- & Assessment-Logik ableiten."
    )
    selected_occupation = get_esco_occupation_selected()
    if selected_occupation:
        st.caption(
            f"ESCO Occupation aus Jobspec-Review: {selected_occupation.get('title', '—')}"
        )
    else:
        st.caption("ESCO Occupation: Keine passende Occupation ausgewählt.")

    with st.expander("Aus Jobspec extrahiert (Skills)", expanded=True):
        must_have_skills = [x for x in job.must_have_skills if has_meaningful_value(x)]
        nice_to_have_skills = [
            x for x in job.nice_to_have_skills if has_meaningful_value(x)
        ]
        tech_stack = [x for x in job.tech_stack if has_meaningful_value(x)]
        if must_have_skills:
            st.write("**Must-have (Auszug):**")
            for x in must_have_skills[:12]:
                st.write(f"- {x}")

        if nice_to_have_skills:
            st.write("**Nice-to-have (Auszug):**")
            for x in nice_to_have_skills[:12]:
                st.write(f"- {x}")

        if tech_stack:
            st.write("**Tech Stack (Auszug):**")
            for x in tech_stack[:15]:
                st.write(f"- {x}")
        if not must_have_skills and not nice_to_have_skills and not tech_stack:
            st.info(
                "Keine verlässlichen Werte erkannt. Details siehe Gaps/Assumptions."
            )

    st.markdown("### ESCO Skill-Mapping")
    normalized_must_terms = _dedupe_terms(must_have_skills)
    normalized_nice_terms = _dedupe_terms(nice_to_have_skills)

    with st.expander("Must-have Mapping", expanded=True):
        st.caption(
            "Suche relevante Must-have Skills, prüfe sie im Preview und bestätige mit Apply."
        )
        render_esco_picker_card(
            concept_type="skill",
            target_state_key=SSKey.ESCO_SKILLS_SELECTED_MUST,
            allow_multi=True,
            enable_preview=True,
        )

    with st.expander("Nice-to-have Mapping", expanded=True):
        st.caption(
            "Suche ergänzende Nice-to-have Skills, prüfe sie im Preview und bestätige mit Apply."
        )
        render_esco_picker_card(
            concept_type="skill",
            target_state_key=SSKey.ESCO_SKILLS_SELECTED_NICE,
            allow_multi=True,
            enable_preview=True,
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

    if deduped_must:
        st.caption(f"Mapped Must-Skills: {len(deduped_must)}")
    if deduped_nice:
        st.caption(f"Mapped Nice-Skills: {len(deduped_nice)}")

    if mapping_report["unmapped_terms"]:
        st.markdown("#### Follow-up: Unmapped Skills")
        for term in mapping_report["unmapped_terms"]:
            st.write(f"- {term}")
    else:
        st.caption(
            "Alle relevanten Skill-Begriffe wurden gemappt oder bewusst übersprungen."
        )

    step = next((s for s in plan.steps if s.step_key == "skills"), None)
    if step is None or not step.questions:
        st.info(
            "Für diesen Abschnitt wurden keine spezifischen Fragen erzeugt. Du kannst trotzdem weitergehen."
        )
        nav_buttons(ctx)
        return

    render_question_step(step)
    nav_buttons(ctx)


PAGE = WizardPage(
    key="skills",
    title_de="Skills & Anforderungen",
    icon="🧠",
    render=render,
    requires_jobspec=True,
)
