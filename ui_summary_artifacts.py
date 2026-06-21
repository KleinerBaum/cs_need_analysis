# ui_summary_artifacts.py
"""Summary artifact renderers."""

from __future__ import annotations

import json
from collections.abc import Sequence
from typing import Any

import streamlit as st

from schemas import (
    BooleanSearchPack,
    EmploymentContractDraft,
    InterviewPrepSheetHiringManager,
    InterviewPrepSheetHR,
    VacancyBrief,
)

def render_brief(
    brief: VacancyBrief,
    *,
    structured_data_payload: Any | None = None,
    show_title: bool = True,
    show_structured_data: bool = True,
) -> None:
    if show_title:
        st.subheader("Recruiting Brief")
    st.markdown(f"**One-liner:** {brief.one_liner}")
    st.markdown("**Hiring Context**")
    st.write(brief.hiring_context)
    st.markdown("**Role Summary**")
    st.write(brief.role_summary)

    st.markdown("**Top Responsibilities**")
    for x in brief.top_responsibilities:
        st.write(f"- {x}")

    st.markdown("**Must-have**")
    for x in brief.must_have:
        st.write(f"- {x}")

    st.markdown("**Nice-to-have**")
    for x in brief.nice_to_have:
        st.write(f"- {x}")

    st.markdown("**Dealbreakers**")
    for x in brief.dealbreakers:
        st.write(f"- {x}")

    st.markdown("**Interview Plan**")
    for x in brief.interview_plan:
        st.write(f"- {x}")

    st.markdown("**Evaluation Rubric**")
    for x in brief.evaluation_rubric:
        st.write(f"- {x}")

    st.markdown("**Risks / Open Questions**")
    for x in brief.risks_open_questions:
        st.write(f"- {x}")

    st.markdown("**Job Ad Draft (DE)**")
    st.write(brief.job_ad_draft)

    if show_structured_data:
        payload = (
            structured_data_payload
            if structured_data_payload is not None
            else brief.structured_data
        )
        structured_data_json = json.dumps(
            payload,
            ensure_ascii=False,
            indent=2,
        )

        st.markdown("**Structured Data**")
        st.caption(
            "Kompakte Preview. Der vollständige Export-JSON steht im Bereich „Export“ bereit."
        )
        show_col, download_col = st.columns([1, 1])
        with show_col:
            st.markdown("**JSON anzeigen**")
            st.json(payload, expanded=False)
        with download_col:
            st.download_button(
                "JSON herunterladen",
                data=structured_data_json.encode("utf-8"),
                file_name="vacancy_brief_structured_data.json",
                mime="application/json",
            )


def render_interview_prep_hr(sheet: InterviewPrepSheetHR) -> None:
    st.markdown(
        f"**Rolle:** {sheet.role_title} · **Stage:** {sheet.interview_stage} · "
        f"**Dauer:** {sheet.duration_minutes} Min."
    )
    st.markdown("**Opening Script**")
    st.write(sheet.opening_script)

    st.markdown("**Frageblöcke**")
    if not sheet.question_blocks:
        st.info("Keine Frageblöcke vorhanden.")
    for index, block in enumerate(sheet.question_blocks, start=1):
        st.markdown(f"**{index}. {block.title}**")
        st.caption(f"Ziel: {block.objective}")
        if block.questions:
            st.write("Fragen:")
            for question in block.questions:
                st.write(f"- {question}")
        if block.follow_up_prompts:
            st.write("Follow-ups:")
            for follow_up in block.follow_up_prompts:
                st.write(f"- {follow_up}")

    st.markdown("**Knockout-Kriterien**")
    if sheet.knockout_criteria:
        for knockout_criterion in sheet.knockout_criteria:
            st.write(f"- {knockout_criterion}")
    else:
        st.info("Keine Knockout-Kriterien hinterlegt.")

    st.markdown("**Bewertungsrubrik**")
    if not sheet.evaluation_rubric:
        st.info("Keine Bewertungsrubrik vorhanden.")
    for rubric_criterion in sheet.evaluation_rubric:
        st.markdown(
            f"- **{rubric_criterion.title}** ({rubric_criterion.weight_percent} %) — "
            f"{rubric_criterion.description}"
        )
        if rubric_criterion.score_scale:
            st.caption(f"Skala: {' | '.join(rubric_criterion.score_scale)}")
        if rubric_criterion.evidence_examples:
            st.caption("Beobachtbare Evidenz:")
            for evidence in rubric_criterion.evidence_examples:
                st.write(f"  - {evidence}")

    st.markdown("**Empfehlungsoptionen**")
    if sheet.final_recommendation_options:
        for option in sheet.final_recommendation_options:
            st.write(f"- {option}")
    else:
        st.info("Keine finalen Empfehlungsoptionen hinterlegt.")


def render_interview_prep_fach(sheet: InterviewPrepSheetHiringManager) -> None:
    st.markdown(
        f"**Rolle:** {sheet.role_title} · **Stage:** {sheet.interview_stage} · "
        f"**Dauer:** {sheet.duration_minutes} Min."
    )

    st.markdown("**Kompetenzen validieren**")
    if sheet.competencies_to_validate:
        for competency in sheet.competencies_to_validate:
            st.write(f"- {competency}")
    else:
        st.info("Keine zu validierenden Kompetenzen hinterlegt.")

    st.markdown("**Frageblöcke**")
    if not sheet.question_blocks:
        st.info("Keine Frageblöcke vorhanden.")
    for index, block in enumerate(sheet.question_blocks, start=1):
        st.markdown(f"**{index}. {block.title}**")
        st.caption(f"Ziel: {block.objective}")
        if block.questions:
            st.write("Fragen:")
            for question in block.questions:
                st.write(f"- {question}")
        if block.follow_up_prompts:
            st.write("Follow-ups:")
            for follow_up in block.follow_up_prompts:
                st.write(f"- {follow_up}")

    st.markdown("**Technical Deep Dive Topics**")
    if sheet.technical_deep_dive_topics:
        for topic in sheet.technical_deep_dive_topics:
            st.write(f"- {topic}")
    else:
        st.info("Keine Deep-Dive-Themen hinterlegt.")

    st.markdown("**Case / Task Prompt**")
    if sheet.case_or_task_prompt:
        st.write(sheet.case_or_task_prompt)
    else:
        st.info("Kein Case/Task Prompt hinterlegt.")

    st.markdown("**Bewertungsrubrik**")
    if not sheet.evaluation_rubric:
        st.info("Keine Bewertungsrubrik vorhanden.")
    for criterion in sheet.evaluation_rubric:
        st.markdown(
            f"- **{criterion.title}** ({criterion.weight_percent} %) — "
            f"{criterion.description}"
        )
        if criterion.score_scale:
            st.caption(f"Skala: {' | '.join(criterion.score_scale)}")
        if criterion.evidence_examples:
            st.caption("Beobachtbare Evidenz:")
            for evidence in criterion.evidence_examples:
                st.write(f"  - {evidence}")

    st.markdown("**Debrief-Fragen**")
    if sheet.debrief_questions:
        for question in sheet.debrief_questions:
            st.write(f"- {question}")
    else:
        st.info("Keine Debrief-Fragen hinterlegt.")


def _first_boolean_query(pack: BooleanSearchPack) -> tuple[str, str, str] | None:
    prioritized_queries = (
        ("Google", "Focused", pack.google.focused),
        ("LinkedIn", "Focused", pack.linkedin.focused),
        ("XING", "Focused", pack.xing.focused),
        ("Google", "Broad", pack.google.broad),
        ("LinkedIn", "Broad", pack.linkedin.broad),
        ("XING", "Broad", pack.xing.broad),
    )
    for channel, variant, entries in prioritized_queries:
        for entry in entries:
            query = entry.strip()
            if query:
                return channel, variant, query
    return None


def _render_boolean_code_card(
    channel: str,
    variant: str,
    queries: Sequence[str],
    *,
    key_prefix: str,
) -> None:
    del key_prefix
    del channel
    st.markdown(f"**{variant}**")
    normalized_queries = [query.strip() for query in queries if query.strip()]
    if not normalized_queries:
        st.caption("Keine Queries vorhanden.")
        return

    for index, query in enumerate(normalized_queries, start=1):
        if len(normalized_queries) > 1:
            st.caption(f"Query {index}")
        st.code(query, language="text")


def render_boolean_supporting_terms(pack: BooleanSearchPack) -> None:
    st.markdown("### Supporting Terms")
    metadata_fields = (
        ("Must-have Terms", pack.must_have_terms),
        ("Seniority Terms", pack.seniority_terms),
        ("Exclusion Terms", pack.exclusion_terms),
        ("Target Locations", pack.target_locations),
    )
    for label, values in metadata_fields:
        st.markdown(f"**{label}**")
        if values:
            for value in values:
                st.write(f"- {value}")
        else:
            st.caption("—")


def render_boolean_usage_notes(pack: BooleanSearchPack) -> None:
    st.markdown("### Usage Notes")
    if pack.usage_notes:
        for note in pack.usage_notes:
            st.write(f"- {note}")
    else:
        st.info("Keine Usage Notes hinterlegt.")


def render_boolean_risks(pack: BooleanSearchPack) -> None:
    st.markdown("### Risks")
    if pack.channel_limitations:
        for limitation in pack.channel_limitations:
            st.write(f"- {limitation}")
    else:
        st.info("Keine kanalbezogenen Einschränkungen hinterlegt.")


def _visible_boolean_channels(pack: BooleanSearchPack) -> tuple[tuple[str, Any], ...]:
    return (
        ("Google", pack.google),
        ("LinkedIn", pack.linkedin),
        ("XING", pack.xing),
    )


def _has_visible_boolean_queries(pack: BooleanSearchPack) -> bool:
    for _, channel_queries in _visible_boolean_channels(pack):
        if any(query.strip() for query in channel_queries.broad):
            return True
        if any(query.strip() for query in channel_queries.focused):
            return True
    return False


def render_boolean_search_pack(pack: BooleanSearchPack) -> None:
    st.markdown("## Boolean Search")
    locations = ", ".join(pack.target_locations) if pack.target_locations else "—"
    st.caption(f"Rolle: {pack.role_title} · Zielregionen: {locations}")

    if not _has_visible_boolean_queries(pack):
        st.info("Keine Boolean Queries vorhanden.")
        return

    st.markdown("### Channel Variants")
    visible_channels = _visible_boolean_channels(pack)
    columns = st.columns(min(len(visible_channels), 5))
    for column, (channel_name, channel_queries) in zip(columns, visible_channels):
        with column:
            st.markdown(f"#### {channel_name}")
            _render_boolean_code_card(
                channel_name,
                "Broad",
                channel_queries.broad,
                key_prefix=f"{channel_name.lower()}.broad",
            )
            with st.expander("Focused", expanded=False):
                _render_boolean_code_card(
                    channel_name,
                    "Focused",
                    channel_queries.focused,
                    key_prefix=f"{channel_name.lower()}.focused",
                )


def render_employment_contract_draft(draft: EmploymentContractDraft) -> None:
    st.info(
        "Template-Draft zur Prüfung. Kein finaler Vertrag und keine Rechtsberatung."
    )
    st.markdown(
        f"**Jurisdiction:** {draft.jurisdiction} · "
        f"**Rolle:** {draft.role_title} · "
        f"**Employment Type:** {draft.employment_type} · "
        f"**Contract Type:** {draft.contract_type}"
    )

    details = [
        ("Start Date", draft.start_date),
        (
            "Probation (Monate)",
            (
                str(draft.probation_period_months)
                if draft.probation_period_months is not None
                else None
            ),
        ),
        (
            "Salary",
            (
                f"{draft.salary.min if draft.salary.min is not None else '—'} - "
                f"{draft.salary.max if draft.salary.max is not None else '—'} "
                f"{draft.salary.currency or ''} / {draft.salary.period or ''}".strip()
            ),
        ),
        ("Salary Notes", draft.salary.notes),
        (
            "Hours / Week",
            (
                str(draft.working_hours_per_week)
                if draft.working_hours_per_week is not None
                else None
            ),
        ),
        (
            "Vacation Days / Year",
            (
                str(draft.vacation_days_per_year)
                if draft.vacation_days_per_year is not None
                else None
            ),
        ),
        ("Place of Work", draft.place_of_work),
        ("Notice Period", draft.notice_period),
    ]
    meta_col_left, meta_col_right = st.columns(2)
    for index, (label, value) in enumerate(details):
        col = meta_col_left if index % 2 == 0 else meta_col_right
        with col:
            st.markdown(f"**{label}**")
            st.write(value or "—")

    st.markdown("**Missing Inputs (Pflicht-Checkliste vor Finalisierung)**")
    if draft.missing_inputs:
        st.warning(
            "Folgende Inputs fehlen noch. Bitte vor rechtlicher Finalisierung ergänzen."
        )
        for missing_input in draft.missing_inputs:
            st.write(f"- [ ] {missing_input}")
    else:
        st.success("Keine fehlenden Inputs markiert.")

    st.markdown("**Klauseln**")
    if draft.clauses:
        for clause in draft.clauses:
            required_tag = "Pflicht" if clause.required else "Optional"
            st.markdown(f"**{clause.title}** · `{required_tag}`")
            st.write(clause.clause_text)
            if clause.legal_note:
                st.caption(f"Legal note: {clause.legal_note}")
    else:
        st.info("Keine Klauseln vorhanden.")

    st.markdown("**Signature Requirements**")
    signature_requirements = list(draft.signature_requirements)
    legal_review_note = "Legal review required"
    if all(
        legal_review_note.lower() not in requirement.lower()
        for requirement in signature_requirements
    ):
        signature_requirements.append(legal_review_note)
    for requirement in signature_requirements:
        st.write(f"- {requirement}")
