from __future__ import annotations

import math

from job_extract_review_helpers import (
    format_recruitment_steps_value,
    format_salary_range_value,
    group_extract_notes_by_tab,
    has_meaningful_value,
    normalize_optional_string,
    parse_optional_int,
    sanitize_display_value,
)
from schemas import MoneyRange, RecruitmentStep


def test_format_salary_range_value_handles_model_and_partial_ranges() -> None:
    salary = MoneyRange(min=60000, max=80000, currency="EUR", period="year")

    assert format_salary_range_value(salary) == "60000.0 – 80000.0 EUR / year"
    assert format_salary_range_value({"min": 50000, "currency": "EUR"}) == "50000 – — EUR"
    assert format_salary_range_value({}) == "—"


def test_format_recruitment_steps_value_limits_preview_and_details() -> None:
    steps = [
        RecruitmentStep(name="Screening", details="30 min"),
        {"name": "Case", "details": ""},
        "Final",
        {"name": "Offer"},
    ]

    assert (
        format_recruitment_steps_value(steps)
        == "Screening (30 min) · Case · Final +1 weitere"
    )


def test_group_extract_notes_by_tab_deduplicates_and_classifies_notes() -> None:
    grouped = group_extract_notes_by_tab(
        [
            "Remote policy is unclear",
            "remote policy is unclear",
            "Salary not stated",
            "Interview process missing",
            "",
        ]
    )

    assert grouped["Benefits & Rahmenbedingungen"] == [
        "Remote policy is unclear",
        "Salary not stated",
    ]
    assert grouped["Interviewprozess"] == ["Interview process missing"]


def test_value_helpers_normalize_empty_sentinels_and_parse_numbers() -> None:
    assert has_meaningful_value("n/a") is False
    assert has_meaningful_value(math.nan) is False
    assert has_meaningful_value([]) is False
    assert has_meaningful_value({}) is False
    assert has_meaningful_value(["Skill", ""]) is True
    assert normalize_optional_string("  Berlin ") == "Berlin"
    assert normalize_optional_string("—") is None
    assert parse_optional_int("3.0") == 3
    assert parse_optional_int("not numeric") is None
    assert sanitize_display_value(
        {"name": "Rolle", "items": ["Skill", "n/a", None], "empty": "-"}
    ) == {"name": "Rolle", "items": ["Skill"], "empty": None}
