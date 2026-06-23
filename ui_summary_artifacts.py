# ui_summary_artifacts.py
"""Summary artifact renderers."""

from __future__ import annotations

import json
from collections.abc import Callable, Mapping, Sequence
from typing import Any

import streamlit as st

from i18n import active_language
from schemas import (
    BooleanSearchPack,
    InterviewPrepSheetHiringManager,
    InterviewPrepSheetHR,
    VacancyBrief,
)
from ux_copy_contract import summary_export_copy, summary_ui_copy


def _language(language: str | None = None) -> str:
    return str(language or active_language() or "de").strip().lower()


def _ui(key: str, *, language: str | None = None, **params: Any) -> str:
    return summary_ui_copy(key, language=_language(language), **params)


def _export(key: str, *, language: str | None = None, **params: Any) -> str:
    return summary_export_copy(key, language=_language(language), **params)


def _as_mapping_payload(payload: Any) -> dict[str, Any]:
    if isinstance(payload, dict):
        return payload
    if hasattr(payload, "model_dump"):
        try:
            raw = payload.model_dump(mode="json")
        except Exception:
            return {}
        return raw if isinstance(raw, dict) else {}
    return {}


def _as_text_list(value: Any, *, limit: int = 6) -> list[str]:
    if not isinstance(value, list):
        return []
    items = [str(item).strip() for item in value if str(item).strip()]
    return items[:limit]


def _render_compact_bullets(title: str, values: list[str], *, empty: str) -> None:
    st.markdown(f"**{title}**")
    if not values:
        st.caption(empty)
        return
    for value in values:
        st.write(f"- {value}")


def _render_downstream_impact(
    payload: dict[str, Any],
    *,
    language: str | None = None,
) -> None:
    selected_benefits = _as_text_list(payload.get("selected_benefits"))
    offer_positioning = _as_mapping_payload(payload.get("offer_positioning"))
    interview_process = _as_mapping_payload(payload.get("interview_process"))

    if not selected_benefits and not offer_positioning and not interview_process:
        return

    st.markdown(f"**{_export('candidate_value', language=language)}**")
    col_offer, col_interview = st.columns(2)
    with col_offer:
        candidate_value = _as_text_list(
            offer_positioning.get("candidate_value") or selected_benefits
        )
        _render_compact_bullets(
            "Candidate Value",
            candidate_value,
            empty=_ui("workspace.no_result", language=language),
        )
    with col_interview:
        hiring_plan = _as_text_list(interview_process.get("candidate_stages"))
        if not hiring_plan:
            selected_values = interview_process.get("selected_values")
            if isinstance(selected_values, list):
                hiring_plan = _as_text_list(
                    [
                        item.get("Wert", "")
                        for item in selected_values
                        if isinstance(item, dict)
                    ]
                )
        _render_compact_bullets(
            "Hiring-Plan",
            hiring_plan,
            empty=_ui("workspace.no_result", language=language),
        )


def _preview_fragment_payload(fragment: Any) -> dict[str, Any]:
    return fragment if isinstance(fragment, dict) else {}


def _preview_bullets(fragment: Mapping[str, Any], *, limit: int = 3) -> list[str]:
    raw_bullets = fragment.get("bullets")
    bullets = _as_text_list(raw_bullets, limit=limit)
    if bullets:
        return bullets
    summary = str(fragment.get("summary") or "").strip()
    return [summary] if summary else []


def render_live_artifact_previews(
    preview_payload: Mapping[str, Any],
    *,
    show_title: bool = True,
    max_items_per_fragment: int = 3,
    streamlit_module: Any | None = None,
    language: str | None = None,
) -> None:
    """Render concise deterministic previews for downstream artifacts."""

    st_module = streamlit_module or st
    if not all(
        callable(getattr(st_module, name, None))
        for name in ("markdown", "caption", "columns", "container", "write")
    ):
        return

    if show_title:
        st_module.markdown(f"#### {_ui('live_preview.title', language=language)}")
    notice = str(preview_payload.get("notice") or "").strip()
    if notice:
        st_module.caption(
            _ui("live_preview.notice_with_detail", language=language, notice=notice)
        )
    else:
        st_module.caption(_ui("live_preview.notice_default", language=language))

    fragments_raw = preview_payload.get("fragments")
    fragments = fragments_raw if isinstance(fragments_raw, Mapping) else {}
    ordered_ids = (
        "brief",
        "job_ad",
        "interview_hr",
        "interview_fach",
        "boolean_search",
    )
    cols = st_module.columns(2, gap="large")
    for index, fragment_id in enumerate(ordered_ids):
        fragment = _preview_fragment_payload(fragments.get(fragment_id))
        title = str(fragment.get("title") or fragment_id).strip()
        summary = str(fragment.get("summary") or "").strip()
        bullets = _preview_bullets(fragment, limit=max_items_per_fragment)
        with cols[index % len(cols)]:
            with st_module.container(border=True):
                st_module.markdown(f"**{title}**")
                if summary:
                    st_module.caption(summary)
                if bullets:
                    for bullet in bullets[:max_items_per_fragment]:
                        st_module.write(f"- {bullet}")
                else:
                    st_module.caption(_ui("live_preview.empty", language=language))


def render_live_artifact_preview_panel(
    *,
    preview_builder: Callable[[], Mapping[str, Any]],
    key: str,
    default_open: bool = False,
    title: str | None = None,
    caption: str | None = None,
    streamlit_module: Any | None = None,
    language: str | None = None,
) -> None:
    st_module = streamlit_module or st
    if not callable(getattr(st_module, "markdown", None)) or not callable(
        getattr(st_module, "caption", None)
    ):
        return

    state_key = f"cs.live_artifact_preview.{key}.revealed"
    session_state = getattr(st_module, "session_state", {})
    if state_key not in session_state and default_open:
        session_state[state_key] = True

    resolved_title = title or _ui("live_preview.panel_title", language=language)
    resolved_caption = caption or _ui("live_preview.panel_caption", language=language)
    st_module.markdown(f"#### {resolved_title}")
    st_module.caption(resolved_caption)
    revealed = bool(session_state.get(state_key, False))
    if not revealed:
        button = getattr(st_module, "button", None)
        if callable(button) and button(
            _ui("live_preview.show_preview", language=language),
            key=f"{state_key}.button",
            width="stretch",
        ):
            session_state[state_key] = True
            revealed = True
        if not revealed:
            return

    render_live_artifact_previews(
        preview_builder(),
        show_title=False,
        streamlit_module=st_module,
        language=language,
    )


def render_brief(
    brief: VacancyBrief,
    *,
    structured_data_payload: Any | None = None,
    show_title: bool = True,
    show_structured_data: bool = True,
    language: str | None = None,
) -> None:
    if show_title:
        st.subheader(_export("brief_title", language=language, role_title="").strip(" -"))
    st.markdown(f"**{_export('one_liner', language=language)}:** {brief.one_liner}")
    st.markdown(f"**{_export('hiring_context', language=language)}**")
    st.write(brief.hiring_context)
    st.markdown(f"**{_export('role_summary', language=language)}**")
    st.write(brief.role_summary)

    payload_for_preview = _as_mapping_payload(
        structured_data_payload
        if structured_data_payload is not None
        else brief.structured_data
    )
    _render_downstream_impact(payload_for_preview, language=language)

    st.markdown(f"**{_export('top_responsibilities', language=language)}**")
    for x in brief.top_responsibilities:
        st.write(f"- {x}")

    st.markdown(f"**{_export('must_have', language=language)}**")
    for x in brief.must_have:
        st.write(f"- {x}")

    st.markdown(f"**{_export('nice_to_have', language=language)}**")
    for x in brief.nice_to_have:
        st.write(f"- {x}")

    st.markdown(f"**{_export('dealbreakers', language=language)}**")
    for x in brief.dealbreakers:
        st.write(f"- {x}")

    st.markdown(f"**{_export('interview_plan', language=language)}**")
    for x in brief.interview_plan:
        st.write(f"- {x}")

    st.markdown(f"**{_export('evaluation_rubric', language=language)}**")
    for x in brief.evaluation_rubric:
        st.write(f"- {x}")

    st.markdown(f"**{_export('risks_open_questions', language=language)}**")
    for x in brief.risks_open_questions:
        st.write(f"- {x}")

    st.markdown(f"**{_export('job_ad_draft', language=language)}**")
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

        st.markdown("**Structured data**" if _language(language) == "en" else "**Strukturierte Daten**")
        st.caption(
            "Compact preview. The full export JSON is available in Export."
            if _language(language) == "en"
            else "Kompakte Vorschau. Der vollständige Export-JSON steht im Bereich „Export“ bereit."
        )
        show_col, download_col = st.columns([1, 1])
        with show_col:
            st.markdown("**Show JSON**" if _language(language) == "en" else "**JSON anzeigen**")
            st.json(payload, expanded=False)
        with download_col:
            st.download_button(
                _ui("final_export.download_json", language=language),
                data=structured_data_json.encode("utf-8"),
                file_name="vacancy_brief_structured_data.json",
                mime="application/json",
            )


def render_interview_prep_hr(
    sheet: InterviewPrepSheetHR,
    *,
    language: str | None = None,
) -> None:
    is_en = _language(language) == "en"
    st.markdown(
        (
            f"**Role:** {sheet.role_title} · **Stage:** {sheet.interview_stage} · "
            f"**Duration:** {sheet.duration_minutes} min."
        )
        if is_en
        else (
            f"**Rolle:** {sheet.role_title} · **Phase:** {sheet.interview_stage} · "
            f"**Dauer:** {sheet.duration_minutes} Min."
        )
    )
    st.markdown("**Opening script**" if is_en else "**Einstiegsskript**")
    st.write(sheet.opening_script)

    st.markdown("**Question blocks**" if is_en else "**Frageblöcke**")
    if not sheet.question_blocks:
        st.info("No question blocks available." if is_en else "Keine Frageblöcke vorhanden.")
    for index, block in enumerate(sheet.question_blocks, start=1):
        st.markdown(f"**{index}. {block.title}**")
        st.caption(f"Objective: {block.objective}" if is_en else f"Ziel: {block.objective}")
        if block.questions:
            st.write("Questions:" if is_en else "Fragen:")
            for question in block.questions:
                st.write(f"- {question}")
        if block.follow_up_prompts:
            st.write("Follow-ups:" if is_en else "Nachfragen:")
            for follow_up in block.follow_up_prompts:
                st.write(f"- {follow_up}")

    st.markdown("**Knockout criteria**" if is_en else "**Knockout-Kriterien**")
    if sheet.knockout_criteria:
        for knockout_criterion in sheet.knockout_criteria:
            st.write(f"- {knockout_criterion}")
    else:
        st.info("No knockout criteria provided." if is_en else "Keine Knockout-Kriterien hinterlegt.")

    st.markdown("**Scorecard / evaluation evidence**" if is_en else "**Scorecard / Bewertungsevidenz**")
    st.caption(
        "Criterion, weighting, and observable evidence for consistent decisions."
        if is_en
        else "Kriterium, Gewichtung und beobachtbare Evidenz für konsistente Entscheidungen."
    )
    if not sheet.evaluation_rubric:
        st.info("No evaluation rubric available." if is_en else "Keine Bewertungsrubrik vorhanden.")
    for rubric_criterion in sheet.evaluation_rubric:
        st.markdown(
            f"- **{rubric_criterion.title}** ({rubric_criterion.weight_percent} %) — "
            f"{rubric_criterion.description}"
        )
        if rubric_criterion.score_scale:
            st.caption(
                f"Scale: {' | '.join(rubric_criterion.score_scale)}"
                if is_en
                else f"Skala: {' | '.join(rubric_criterion.score_scale)}"
            )
        if rubric_criterion.evidence_examples:
            st.caption("Evidence:" if is_en else "Evidenz:")
            for evidence in rubric_criterion.evidence_examples:
                st.write(f"  - {evidence}")

    st.markdown("**Recommendation options**" if is_en else "**Empfehlungsoptionen**")
    if sheet.final_recommendation_options:
        for option in sheet.final_recommendation_options:
            st.write(f"- {option}")
    else:
        st.info("No final recommendation options provided." if is_en else "Keine finalen Empfehlungsoptionen hinterlegt.")


def render_interview_prep_fach(
    sheet: InterviewPrepSheetHiringManager,
    *,
    language: str | None = None,
) -> None:
    is_en = _language(language) == "en"
    st.markdown(
        (
            f"**Role:** {sheet.role_title} · **Stage:** {sheet.interview_stage} · "
            f"**Duration:** {sheet.duration_minutes} min."
        )
        if is_en
        else (
            f"**Rolle:** {sheet.role_title} · **Phase:** {sheet.interview_stage} · "
            f"**Dauer:** {sheet.duration_minutes} Min."
        )
    )

    st.markdown("**Validate competencies**" if is_en else "**Kompetenzen validieren**")
    if sheet.competencies_to_validate:
        for competency in sheet.competencies_to_validate:
            st.write(f"- {competency}")
    else:
        st.info("No competencies to validate provided." if is_en else "Keine zu validierenden Kompetenzen hinterlegt.")

    st.markdown("**Question blocks**" if is_en else "**Frageblöcke**")
    if not sheet.question_blocks:
        st.info("No question blocks available." if is_en else "Keine Frageblöcke vorhanden.")
    for index, block in enumerate(sheet.question_blocks, start=1):
        st.markdown(f"**{index}. {block.title}**")
        st.caption(f"Objective: {block.objective}" if is_en else f"Ziel: {block.objective}")
        if block.questions:
            st.write("Questions:" if is_en else "Fragen:")
            for question in block.questions:
                st.write(f"- {question}")
        if block.follow_up_prompts:
            st.write("Follow-ups:" if is_en else "Nachfragen:")
            for follow_up in block.follow_up_prompts:
                st.write(f"- {follow_up}")

    st.markdown("**Domain deep-dive topics**" if is_en else "**Fachliche Vertiefungsthemen**")
    if sheet.technical_deep_dive_topics:
        for topic in sheet.technical_deep_dive_topics:
            st.write(f"- {topic}")
    else:
        st.info("No deep-dive topics provided." if is_en else "Keine Deep-Dive-Themen hinterlegt.")

    st.markdown("**Case/task briefing**" if is_en else "**Case-/Aufgabenbriefing**")
    if sheet.case_or_task_prompt:
        st.write(sheet.case_or_task_prompt)
    else:
        st.info("No case/task briefing provided." if is_en else "Kein Case-/Aufgabenbriefing hinterlegt.")

    st.markdown("**Scorecard / evaluation evidence**" if is_en else "**Scorecard / Bewertungsevidenz**")
    st.caption(
        "Criterion, weighting, and observable evidence for consistent decisions."
        if is_en
        else "Kriterium, Gewichtung und beobachtbare Evidenz für konsistente Entscheidungen."
    )
    if not sheet.evaluation_rubric:
        st.info("No evaluation rubric available." if is_en else "Keine Bewertungsrubrik vorhanden.")
    for criterion in sheet.evaluation_rubric:
        st.markdown(
            f"- **{criterion.title}** ({criterion.weight_percent} %) — "
            f"{criterion.description}"
        )
        if criterion.score_scale:
            st.caption(
                f"Scale: {' | '.join(criterion.score_scale)}"
                if is_en
                else f"Skala: {' | '.join(criterion.score_scale)}"
            )
        if criterion.evidence_examples:
            st.caption("Evidence:" if is_en else "Evidenz:")
            for evidence in criterion.evidence_examples:
                st.write(f"  - {evidence}")

    st.markdown("**Debrief questions**" if is_en else "**Debrief-Fragen**")
    if sheet.debrief_questions:
        for question in sheet.debrief_questions:
            st.write(f"- {question}")
    else:
        st.info("No debrief questions provided." if is_en else "Keine Debrief-Fragen hinterlegt.")


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
    language: str | None = None,
) -> None:
    del key_prefix
    del channel
    st.markdown(f"**{variant}**")
    normalized_queries = [query.strip() for query in queries if query.strip()]
    if not normalized_queries:
        st.caption(
            "No search strings available."
            if _language(language) == "en"
            else "Keine Suchstrings vorhanden."
        )
        return

    for index, query in enumerate(normalized_queries, start=1):
        if len(normalized_queries) > 1:
            st.caption(f"Suchstring {index}")
        st.code(query, language="text")


def render_boolean_supporting_terms(
    pack: BooleanSearchPack,
    *,
    language: str | None = None,
) -> None:
    st.markdown("### Search terms" if _language(language) == "en" else "### Suchbegriffe")
    metadata_fields = (
        (_export("must_have_terms", language=language), pack.must_have_terms),
        (_export("seniority_terms", language=language), pack.seniority_terms),
        (_export("exclusion_terms", language=language), pack.exclusion_terms),
        (_export("target_locations", language=language), pack.target_locations),
    )
    for label, values in metadata_fields:
        st.markdown(f"**{label}**")
        if values:
            for value in values:
                st.write(f"- {value}")
        else:
            st.caption("—")


def render_boolean_usage_notes(
    pack: BooleanSearchPack,
    *,
    language: str | None = None,
) -> None:
    st.markdown(f"### {_export('usage_notes', language=language)}")
    if pack.usage_notes:
        for note in pack.usage_notes:
            st.write(f"- {note}")
    else:
        st.info("No usage notes provided." if _language(language) == "en" else "Keine Nutzungshinweise hinterlegt.")


def render_boolean_risks(
    pack: BooleanSearchPack,
    *,
    language: str | None = None,
) -> None:
    st.markdown("### Risks" if _language(language) == "en" else "### Risiken")
    if pack.channel_limitations:
        for limitation in pack.channel_limitations:
            st.write(f"- {limitation}")
    else:
        st.info(
            "No channel-specific limitations provided."
            if _language(language) == "en"
            else "Keine kanalbezogenen Einschränkungen hinterlegt."
        )


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


def render_boolean_search_pack(
    pack: BooleanSearchPack,
    *,
    language: str | None = None,
) -> None:
    is_en = _language(language) == "en"
    st.markdown(f"## {_export('boolean_title', language=language)}")
    locations = ", ".join(pack.target_locations) if pack.target_locations else "—"
    st.caption(
        f"{_export('role_title', language=language)}: {pack.role_title} · "
        f"{_export('target_locations', language=language)}: {locations}"
    )

    if not _has_visible_boolean_queries(pack):
        st.info("No search strings available." if is_en else "Keine Suchstrings vorhanden.")
        return

    st.markdown("### Channel variants" if is_en else "### Kanalvarianten")
    visible_channels = _visible_boolean_channels(pack)
    columns = st.columns(min(len(visible_channels), 5))
    for column, (channel_name, channel_queries) in zip(columns, visible_channels):
        with column:
            st.markdown(f"#### {channel_name}")
            _render_boolean_code_card(
                channel_name,
                _export("broad", language=language),
                channel_queries.broad,
                key_prefix=f"{channel_name.lower()}.broad",
                language=language,
            )
            with st.expander(_export("focused", language=language), expanded=False):
                _render_boolean_code_card(
                    channel_name,
                    _export("focused", language=language),
                    channel_queries.focused,
                    key_prefix=f"{channel_name.lower()}.focused",
                    language=language,
                )
