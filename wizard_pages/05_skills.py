# wizard_pages/05_skills.py
from __future__ import annotations

from typing import Any

import streamlit as st

from constants import SSKey
from esco_client import EscoClient, EscoClientError
from schemas import EscoConceptRef, EscoMappingReport, EscoSuggestionItem
from schemas import JobAdExtract, QuestionPlan
from state import get_esco_occupation_selected
from ui_components import (
    has_meaningful_value,
    render_error_banner,
    render_question_step,
)
from wizard_pages.base import WizardContext, WizardPage, nav_buttons

_NO_SKILL_MAPPING_OPTION = "Kein passendes ESCO-Skill"
_AUTO_PICK_SCORE_THRESHOLD = 0.94
_AUTO_PICK_GAP_THRESHOLD = 0.1


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


def _extract_skill_candidates(payload: dict[str, Any]) -> list[dict[str, Any]]:
    candidates: list[dict[str, Any]] = []
    seen_uris: set[str] = set()

    def _walk(node: Any) -> None:
        if isinstance(node, dict):
            uri_raw = node.get("uri")
            title_raw = (
                node.get("title")
                or node.get("preferredLabel")
                or node.get("label")
                or node.get("name")
            )
            type_raw = str(node.get("type") or "skill").strip().lower()
            score_raw = node.get("score")
            if isinstance(uri_raw, str) and isinstance(title_raw, str):
                uri = uri_raw.strip()
                title = title_raw.strip()
                if uri and title and type_raw == "skill" and uri not in seen_uris:
                    score: float | None = None
                    if isinstance(score_raw, (int, float)):
                        score = float(score_raw)
                    candidates.append(
                        {
                            "uri": uri,
                            "title": title,
                            "type": "skill",
                            "score": score,
                        }
                    )
                    seen_uris.add(uri)
            for value in node.values():
                _walk(value)
        elif isinstance(node, list):
            for item in node:
                _walk(item)

    _walk(payload)
    validated: list[dict[str, Any]] = []
    for item in candidates:
        try:
            validated.append(EscoSuggestionItem.model_validate(item).model_dump())
        except Exception:
            continue
    return validated


def _auto_pick_skill(
    term: str, candidates: list[dict[str, Any]]
) -> dict[str, Any] | None:
    if not candidates:
        return None
    normalized_term = _normalize_term(term)
    if not normalized_term:
        return None
    for candidate in candidates:
        title = str(candidate.get("title") or "")
        if normalized_term == _normalize_term(title):
            return candidate

    top_candidate = candidates[0]
    top_score = top_candidate.get("score")
    second_score = candidates[1].get("score") if len(candidates) > 1 else None
    if not isinstance(top_score, (int, float)):
        return None
    numeric_top_score = float(top_score)
    if numeric_top_score < _AUTO_PICK_SCORE_THRESHOLD:
        return None
    if isinstance(second_score, (int, float)):
        score_gap = numeric_top_score - float(second_score)
        if score_gap < _AUTO_PICK_GAP_THRESHOLD:
            return None
    return top_candidate


def _validate_skill_ref(candidate: dict[str, Any]) -> dict[str, Any] | None:
    try:
        return EscoConceptRef.model_validate(
            {
                "uri": candidate["uri"],
                "title": candidate["title"],
                "type": "skill",
            }
        ).model_dump()
    except Exception:
        return None


def _map_terms_to_esco_skills(
    terms: list[str],
) -> tuple[dict[str, list[dict[str, Any]]], dict[str, dict[str, Any]]]:
    client = EscoClient()
    candidates_by_term: dict[str, list[dict[str, Any]]] = {}
    auto_picks: dict[str, dict[str, Any]] = {}
    for term in terms:
        try:
            payload = client.suggest2(text=term, type="skill", limit=8)
        except EscoClientError:
            candidates_by_term[term] = []
            continue
        candidates = _extract_skill_candidates(payload)
        candidates_by_term[term] = candidates
        auto = _auto_pick_skill(term, candidates)
        if auto is None:
            continue
        validated = _validate_skill_ref(auto)
        if validated is not None:
            auto_picks[term] = validated
    return candidates_by_term, auto_picks


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


def _render_skill_picker(
    *,
    bucket_label: str,
    term: str,
    candidates: list[dict[str, Any]],
    auto_picks: dict[str, dict[str, Any]],
) -> dict[str, Any] | None:
    auto_pick = auto_picks.get(term)
    if auto_pick:
        st.caption(f"✅ Auto-Mapping: {auto_pick['title']}")
        return auto_pick

    if not candidates:
        st.caption("⚠️ Keine ESCO-Skill-Vorschläge gefunden.")
        return None

    options = [_NO_SKILL_MAPPING_OPTION] + [
        str(item.get("title") or "—") for item in candidates
    ]
    selected_label = st.selectbox(
        f"{bucket_label}: {term}",
        options=options,
        key=f"cs.skills.mapping.{bucket_label}.{_normalize_term(term)}",
    )
    if selected_label == _NO_SKILL_MAPPING_OPTION:
        return None
    selected_candidate = next(
        (
            candidate
            for candidate in candidates
            if str(candidate.get("title") or "") == selected_label
        ),
        None,
    )
    if selected_candidate is None:
        return None
    return _validate_skill_ref(selected_candidate)


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

    must_candidates_by_term, must_auto_picks = _map_terms_to_esco_skills(
        normalized_must_terms
    )
    nice_candidates_by_term, nice_auto_picks = _map_terms_to_esco_skills(
        normalized_nice_terms
    )

    selected_must: list[dict[str, Any]] = []
    selected_nice: list[dict[str, Any]] = []
    collisions: list[str] = []
    notes: list[str] = []
    follow_up_terms: list[str] = []

    with st.expander("Must-have Mapping", expanded=True):
        for term in normalized_must_terms:
            candidates = must_candidates_by_term.get(term, [])
            if len(candidates) > 1 and term not in must_auto_picks:
                collisions.append(term)
            picked = _render_skill_picker(
                bucket_label="must",
                term=term,
                candidates=candidates,
                auto_picks=must_auto_picks,
            )
            if picked is None:
                follow_up_terms.append(term)
                continue
            selected_must.append(picked)

    with st.expander("Nice-to-have Mapping", expanded=True):
        for term in normalized_nice_terms:
            candidates = nice_candidates_by_term.get(term, [])
            if len(candidates) > 1 and term not in nice_auto_picks:
                collisions.append(term)
            picked = _render_skill_picker(
                bucket_label="nice",
                term=term,
                candidates=candidates,
                auto_picks=nice_auto_picks,
            )
            if picked is None:
                follow_up_terms.append(term)
                continue
            selected_nice.append(picked)

    deduped_must, deduped_nice = _dedupe_selected_skills_across_buckets(
        selected_must, selected_nice
    )
    duplicate_count = (len(selected_must) + len(selected_nice)) - (
        len(deduped_must) + len(deduped_nice)
    )
    if duplicate_count > 0:
        notes.append(
            f"{duplicate_count} Duplikat(e) über Must/Nice anhand URI entfernt."
        )

    st.session_state[SSKey.ESCO_SKILLS_SELECTED_MUST.value] = deduped_must
    st.session_state[SSKey.ESCO_SKILLS_SELECTED_NICE.value] = deduped_nice
    mapping_report = EscoMappingReport.model_validate(
        {
            "mapped_count": len(deduped_must) + len(deduped_nice),
            "unmapped_terms": _dedupe_terms(follow_up_terms),
            "collisions": _dedupe_terms(collisions),
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
