from __future__ import annotations

from llm_client import JobAdGenerationResult
from summary_job_ad import (
    dedupe_preserve_order,
    estimate_text_area_height,
    normalize_list_item,
    sanitize_generated_job_ad,
)


def test_normalize_list_item_removes_common_bullet_prefixes() -> None:
    assert normalize_list_item("- Data Engineer") == "Data Engineer"
    assert normalize_list_item("1. Python") == "Python"
    assert normalize_list_item("• SQL") == "SQL"


def test_dedupe_preserve_order_strips_empty_and_case_duplicates() -> None:
    assert dedupe_preserve_order([" Python ", "", "python", "SQL"]) == [
        "Python",
        "SQL",
    ]


def test_sanitize_generated_job_ad_removes_embedded_sections() -> None:
    source = JobAdGenerationResult(
        headline=" Baggerfahrer (m/w/d) ",
        target_group=["Baggerfahrer/innen"],
        agg_checklist=["Geschlechtsneutrale Ansprache vorhanden."],
        job_ad_text=(
            "Wir suchen Verstärkung für unser Team.\n\n"
            "Hinweis: Startdatum ist nicht angegeben.\n"
            "Zielgruppe\n"
            "- Galabauer/innen\n"
            "AGG-Checkliste\n"
            "- Fehlende Angaben: Bewerbungsschluss nicht angegeben.\n"
        ),
    )

    sanitized, notes = sanitize_generated_job_ad(source)

    assert sanitized.headline == "Baggerfahrer (m/w/d)"
    assert sanitized.job_ad_text == "Wir suchen Verstärkung für unser Team."
    assert sanitized.target_group == ["Baggerfahrer/innen", "Galabauer/innen"]
    assert (
        "Fehlende Angaben: Bewerbungsschluss nicht angegeben."
        in sanitized.agg_checklist
    )
    assert notes == ["Startdatum ist nicht angegeben."]


def test_estimate_text_area_height_has_minimum_and_cap() -> None:
    assert estimate_text_area_height("Kurz") == 160
    assert estimate_text_area_height("\n".join(["Zeile"] * 50)) == 520
