from __future__ import annotations

from constants import (
    STEP_KEY_BENEFITS,
    STEP_KEY_COMPANY,
    STEP_KEY_INTERVIEW,
    STEP_KEY_LANDING,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
    STEP_KEY_SUMMARY,
)
from ux_copy_contract import UX_COPY_FIELDS, VacancyCopyContext, build_step_copy


def test_landing_copy_defaults_to_clear_german_value_prop() -> None:
    copy = build_step_copy(STEP_KEY_LANDING, language="de")

    assert copy.headline == "Stellenanzeige hochladen. Recruiting-Briefing starten."
    assert "belastbares Recruiting-Briefing" in copy.subheadline
    assert copy.value_line.startswith("Aus einer unklaren Jobspec")
    assert copy.primary_cta == "Stellenanzeige analysieren"


def test_company_copy_uses_dynamic_context_in_german() -> None:
    copy = build_step_copy(
        STEP_KEY_COMPANY,
        language="de",
        context=VacancyCopyContext(
            company_name="Accenture",
            role_title="Analytics Lead",
        ),
    )

    assert copy.headline == "Accenture als Arbeitgeber für Analytics Lead einordnen"
    assert "warum diese Rolle relevant ist" in copy.subheadline
    assert copy.value_line == "Hilft zu erklären, warum diese Rolle existiert."


def test_summary_copy_uses_gap_state_when_critical_gaps_exist() -> None:
    copy = build_step_copy(
        STEP_KEY_SUMMARY,
        language="de",
        context=VacancyCopyContext(
            role_title="Data Scientist",
            readiness_score=82,
            critical_gaps_count=3,
        ),
    )

    assert copy.headline == "Noch 3 kritische Punkte offen"
    assert "bevor Sie Stellenanzeige" in copy.subheadline
    assert copy.readiness == "3 kritische Lücken"
    assert copy.primary_cta == "Recruiting-Unterlagen erstellen"


def test_summary_copy_uses_location_in_default_state() -> None:
    copy = build_step_copy(
        STEP_KEY_SUMMARY,
        language="en",
        context=VacancyCopyContext(
            role_title="Data Scientist",
            location="Germany",
            readiness_score=82,
            critical_gaps_count=0,
        ),
    )

    assert copy.headline == "Recruiting brief for Data Scientist in Germany: 82% ready"


def test_summary_copy_uses_ready_state_when_fully_ready() -> None:
    copy = build_step_copy(
        STEP_KEY_SUMMARY,
        language="en",
        context=VacancyCopyContext(
            role_title="Data Scientist",
            readiness_score=100,
            critical_gaps_count=0,
        ),
    )

    assert copy.headline == "Ready for recruiting, interviews, and active sourcing"
    assert "All important facts are checked." in copy.subheadline
    assert copy.readiness == "Ready"
    assert copy.primary_cta == "Generate recruiting outputs"


def test_missing_context_falls_back_to_safe_labels() -> None:
    copy = build_step_copy(
        STEP_KEY_COMPANY,
        language="en",
        context=VacancyCopyContext(),
    )

    assert copy.headline == "Position the company as the employer for this role"
    assert "why this role matters" in copy.subheadline


def test_all_contract_steps_resolve_all_fields_in_both_languages() -> None:
    for language in ("de", "en"):
        for step_key in (
            STEP_KEY_LANDING,
            STEP_KEY_COMPANY,
            STEP_KEY_ROLE_TASKS,
            STEP_KEY_SKILLS,
            STEP_KEY_BENEFITS,
            STEP_KEY_INTERVIEW,
            STEP_KEY_SUMMARY,
        ):
            copy = build_step_copy(
                step_key,
                language=language,
                context=VacancyCopyContext(readiness_score=40),
            )

            for field in UX_COPY_FIELDS:
                assert getattr(copy, field)


def test_unknown_step_uses_landing_fallback() -> None:
    copy = build_step_copy("unknown", language="en")

    assert copy.headline == "Upload a job ad. Start the recruiting brief."
