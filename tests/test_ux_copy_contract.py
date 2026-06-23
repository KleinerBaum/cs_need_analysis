from __future__ import annotations

from constants import (
    STEP_KEY_COMPANY,
    STEP_KEY_LANDING,
    STEP_KEY_SUMMARY,
)
from ux_copy_contract import VacancyCopyContext, build_step_copy


def test_landing_copy_defaults_to_clear_german_value_prop() -> None:
    copy = build_step_copy(STEP_KEY_LANDING, language="de")

    assert copy.headline == "Stellenanzeige hochladen. Recruiting-Briefing starten."
    assert "Recruiting, HR und Hiring Teams" in copy.subheadline
    assert "Briefing-Basis" in copy.value_line
    assert copy.primary_cta == "Briefing aus Stellenanzeige erstellen"


def test_landing_copy_uses_role_aware_handoff_after_analysis() -> None:
    copy = build_step_copy(
        STEP_KEY_LANDING,
        language="de",
        context=VacancyCopyContext(role_title="Data Engineer"),
    )

    assert copy.headline == "Wir haben die ersten Informationen zu Data Engineer erkannt."
    assert "Quelle ein Recruiting-Briefing" in copy.subheadline


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
    assert copy.primary_cta == "Recruiting-Unterlagen erstellen"


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
    assert copy.primary_cta == "Generate recruiting outputs"


def test_missing_context_falls_back_to_safe_labels() -> None:
    copy = build_step_copy(
        STEP_KEY_COMPANY,
        language="en",
        context=VacancyCopyContext(),
    )

    assert copy.headline == "Position the company as the employer for this role"
    assert "why this role matters" in copy.subheadline
