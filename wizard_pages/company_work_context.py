from __future__ import annotations

from collections.abc import Callable

import streamlit as st

from constants import FactKey
from schemas import JobAdExtract
from ui_layout import responsive_three_columns, responsive_two_columns
from wizard_pages.fact_inputs import (
    compact_text,
    fact_value,
    persist_compact_object,
    persist_fact,
    render_multiselect_fact,
    render_number_fact,
    render_select_fact,
    render_text_area_fact,
    render_text_fact,
    section_container,
    split_lines,
)


WORK_ARRANGEMENT_LABELS = {
    "onsite": "Vor Ort",
    "hybrid": "Hybrid",
    "remote_country": "Remote im Land",
    "remote_cross_border": "Remote grenzüberschreitend",
    "unknown": "Noch unklar",
}
CEFR_LEVELS = ("A1", "A2", "B1", "B2", "C1", "C2")
LEADERSHIP_LABELS = {
    "individual_contributor": "Individual Contributor",
    "fachliche_fuehrung": "Fachliche Führung",
    "disziplinarische_fuehrung": "Disziplinarische Führung",
    "beides": "Fachlich und disziplinarisch",
    "unklar": "Noch unklar",
}


def _render_secondary_detail(
    title: str,
    renderer: Callable[[], None],
    *,
    collapsed: bool,
) -> None:
    expander = getattr(st, "expander", None)
    if collapsed and callable(expander):
        with expander(title, expanded=False):
            renderer()
        return
    renderer()


def _render_language_fact(
    *,
    fact_key: FactKey,
    title: str,
    default_context: str,
) -> None:
    current_raw = fact_value(fact_key, {})
    current = current_raw if isinstance(current_raw, dict) else {}
    language = st.text_input(
        f"{title}: Sprache",
        value=compact_text(current.get("language")),
        placeholder="Deutsch, Englisch, ...",
        key=f"fact_input.{fact_key.value}.language",
    )
    current_level = compact_text(current.get("level")) or "B2"
    if current_level not in CEFR_LEVELS:
        current_level = "B2"
    level = st.selectbox(
        f"{title}: Mindestniveau",
        options=CEFR_LEVELS,
        index=CEFR_LEVELS.index(current_level),
        key=f"fact_input.{fact_key.value}.level",
    )
    context = st.text_input(
        f"{title}: Kontext",
        value=compact_text(current.get("context") or default_context),
        key=f"fact_input.{fact_key.value}.context",
    )
    persist_compact_object(
        fact_key,
        {
            "language": language,
            "level": level,
            "context": context,
        },
    )


def render_working_model_location_section(
    job: JobAdExtract,
    *,
    show_heading: bool = True,
    collapse_secondary_details: bool = False,
) -> None:
    with section_container(border=True):
        if show_heading:
            st.markdown("#### Arbeitsmodell & Standort")
        location_col, country_col, arrangement_col = responsive_three_columns(
            gap="large"
        )
        with location_col:
            render_text_fact(
                FactKey.COMPANY_LOCATION_CITY,
                "Arbeitsort / Stadt",
                default=job.location_city or "",
            )
        with country_col:
            render_text_fact(
                FactKey.COMPANY_LOCATION_COUNTRY,
                "Land",
                default=job.location_country or "",
            )
        with arrangement_col:
            render_select_fact(
                FactKey.COMPANY_WORK_ARRANGEMENT,
                "Arbeitsmodell",
                options=tuple(WORK_ARRANGEMENT_LABELS),
                default="unknown",
                labels=WORK_ARRANGEMENT_LABELS,
            )
        days_col, remote_col = responsive_two_columns(gap="large")
        with days_col:
            render_number_fact(
                FactKey.COMPANY_OFFICE_DAYS_PER_WEEK,
                "Tage pro Woche vor Ort",
                min_value=0,
                max_value=5,
                default=0,
            )
        with remote_col:
            render_text_fact(
                FactKey.COMPANY_REMOTE_POLICY,
                "Remote-Regel",
                default=job.remote_policy or "",
            )

        def _render_secondary_work_details() -> None:
            render_text_fact(
                FactKey.COMPANY_PLACE_OF_WORK,
                "Konkreter Arbeitsort",
                default=job.place_of_work or "",
            )
            allowed_regions = st.text_area(
                "Erlaubte Regionen oder Zeitzonen",
                value="\n".join(
                    split_lines(
                        fact_value(FactKey.COMPANY_ALLOWED_REGIONS_TIMEZONES, [])
                    )
                ),
                placeholder="z. B. Deutschland\nDACH\nCET +/- 2h",
                height=90,
                key=f"fact_input.{FactKey.COMPANY_ALLOWED_REGIONS_TIMEZONES.value}",
            )
            persist_fact(
                FactKey.COMPANY_ALLOWED_REGIONS_TIMEZONES,
                split_lines(allowed_regions),
            )
            lang_left, lang_right = responsive_two_columns(gap="large")
            with lang_left:
                _render_language_fact(
                    fact_key=FactKey.COMPANY_LANGUAGE_INTERNAL,
                    title="Interne Arbeitssprache",
                    default_context="interne Zusammenarbeit",
                )
            with lang_right:
                _render_language_fact(
                    fact_key=FactKey.COMPANY_LANGUAGE_EXTERNAL,
                    title="Externe Kommunikationssprache",
                    default_context="Kund:innen / Partner",
                )

        _render_secondary_detail(
            "Sekundäre Standort- und Sprachdetails",
            _render_secondary_work_details,
            collapsed=collapse_secondary_details,
        )


def render_non_negotiables_compliance_section(
    *,
    show_heading: bool = True,
    heading: str = "Fixe Rahmenbedingungen",
    collapse_secondary_details: bool = False,
) -> None:
    with section_container(border=True):
        if show_heading:
            st.markdown(f"#### {heading}")
        render_multiselect_fact(
            FactKey.COMPANY_NON_NEGOTIABLES,
            "Nicht verhandelbar",
            options=[
                "Standort",
                "Arbeitszeit",
                "Gehalt",
                "Vertragsart",
                "Sprache",
                "Zertifikat/Nachweis",
                "Reisebereitschaft",
                "Schicht/Rufbereitschaft",
                "Sonstiges",
            ],
        )

        def _render_secondary_compliance_details() -> None:
            compliance_col, tariff_col = responsive_two_columns(gap="large")
            with compliance_col:
                render_multiselect_fact(
                    FactKey.COMPANY_COMPLIANCE_CONTEXT,
                    "Regulatorische oder betriebliche Besonderheiten",
                    options=[
                        "Regulierte Branche",
                        "Datenschutz",
                        "Arbeitssicherheit",
                        "Zertifizierungen",
                        "Betriebsrat",
                        "Öffentlicher Sektor",
                        "Sonstiges",
                    ],
                )
            with tariff_col:
                render_text_fact(
                    FactKey.COMPANY_TARIFF_CONTEXT,
                    "Tarifbindung / Betriebsvereinbarung / besondere Vorgaben",
                )

        _render_secondary_detail(
            "Sekundäre Compliance-Details",
            _render_secondary_compliance_details,
            collapsed=collapse_secondary_details,
        )


def render_team_reporting_section(
    job: JobAdExtract,
    *,
    show_heading: bool = True,
    collapse_secondary_details: bool = False,
) -> None:
    with section_container(border=True):
        if show_heading:
            st.markdown("#### Team & Berichtslinie")
        team_col, reports_to_col, scope_col = responsive_three_columns(gap="large")
        with team_col:
            render_text_fact(
                FactKey.TEAM_NAME,
                "Welches Team nimmt die Person auf?",
                default=job.department_name or "",
            )
        with reports_to_col:
            render_text_fact(
                FactKey.COMPANY_REPORTS_TO,
                "An wen berichtet die Rolle?",
                default=job.reports_to or "",
            )
        with scope_col:
            render_select_fact(
                FactKey.TEAM_LEADERSHIP_SCOPE,
                "Welche Führungsverantwortung hat die Rolle?",
                options=tuple(LEADERSHIP_LABELS),
                default="individual_contributor",
                labels=LEADERSHIP_LABELS,
            )

        def _render_secondary_team_context() -> None:
            department_col, direct_reports_col, team_size_col = (
                responsive_three_columns(gap="large")
            )
            with department_col:
                render_text_fact(
                    FactKey.COMPANY_DEPARTMENT_NAME,
                    "Abteilung / Fachbereich",
                    default=job.department_name or "",
                )
            with direct_reports_col:
                render_number_fact(
                    FactKey.COMPANY_DIRECT_REPORTS_COUNT,
                    "Wie viele Direct Reports hat die Rolle?",
                    min_value=0,
                    max_value=500,
                    default=job.direct_reports_count or 0,
                )
            with team_size_col:
                render_number_fact(
                    FactKey.TEAM_SIZE_DIRECT,
                    "Wie groß ist das unmittelbare Team?",
                    min_value=0,
                    max_value=500,
                    default=job.direct_reports_count or 0,
                )
            render_multiselect_fact(
                FactKey.TEAM_STAKEHOLDERS_PRIMARY,
                "Mit welchen wichtigsten Stakeholdern arbeitet die Person regelmäßig?",
                options=[
                    "Fachbereich",
                    "Management",
                    "HR/Recruiting",
                    "Sales",
                    "Customer Success",
                    "Operations",
                    "Kund:innen",
                    "Lieferanten/Partner",
                    "Sonstiges",
                ],
            )
            render_text_area_fact(
                FactKey.TEAM_SUCCESS_CONTEXT_90D,
                "Arbeitsweise im Team in den ersten 90 Tagen",
                height=100,
            )

        _render_secondary_detail(
            "Sekundäre Teamdetails",
            _render_secondary_team_context,
            collapsed=collapse_secondary_details,
        )


def append_context_to_team_success_fact(context_line: str) -> bool:
    current = str(fact_value(FactKey.TEAM_SUCCESS_CONTEXT_90D, "") or "").strip()
    addition = context_line.strip()
    if not addition:
        return False
    if addition.casefold() in current.casefold():
        return True
    updated = f"{current}\n- {addition}".strip() if current else f"- {addition}"
    persist_fact(FactKey.TEAM_SUCCESS_CONTEXT_90D, updated)
    return True


def render_work_context_sections(
    job: JobAdExtract,
    *,
    include_non_negotiables_compliance: bool = True,
) -> None:
    render_working_model_location_section(job)
    if include_non_negotiables_compliance:
        render_non_negotiables_compliance_section()
