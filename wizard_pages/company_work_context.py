from __future__ import annotations

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
) -> None:
    with section_container(border=True):
        if show_heading:
            st.markdown("#### Arbeitsmodell & Standort")
        location_col, country_col, place_col = responsive_three_columns(gap="large")
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
        with place_col:
            render_text_fact(
                FactKey.COMPANY_PLACE_OF_WORK,
                "Konkreter Arbeitsort",
                default=job.place_of_work or "",
            )

        arrangement_col, days_col, remote_col = responsive_three_columns(gap="large")
        with arrangement_col:
            render_select_fact(
                FactKey.COMPANY_WORK_ARRANGEMENT,
                "Arbeitsmodell",
                options=tuple(WORK_ARRANGEMENT_LABELS),
                default="unknown",
                labels=WORK_ARRANGEMENT_LABELS,
            )
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
        allowed_regions = st.text_area(
            "Erlaubte Regionen oder Zeitzonen",
            value="\n".join(
                split_lines(fact_value(FactKey.COMPANY_ALLOWED_REGIONS_TIMEZONES, []))
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


def render_non_negotiables_compliance_section(
    *,
    show_heading: bool = True,
    heading: str = "Fixe Rahmenbedingungen",
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


def render_work_context_sections(job: JobAdExtract) -> None:
    render_working_model_location_section(job)
    render_non_negotiables_compliance_section()
