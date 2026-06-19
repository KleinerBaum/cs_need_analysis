from __future__ import annotations

from document_preview import markdown_article_preview_html
from llm_client import JobAdGenerationResult
from summary_job_ad import (
    build_publishable_job_ad_markdown,
    build_publishable_job_ad_plain_text,
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


def test_job_ad_generation_result_accepts_structured_sections_and_legacy_payload() -> None:
    legacy = JobAdGenerationResult.model_validate(
        {
            "headline": "Titel",
            "target_group": [],
            "agg_checklist": [],
            "job_ad_text": "Legacy text",
        }
    )
    structured = JobAdGenerationResult.model_validate(
        {
            "headline": "Titel",
            "target_group": ["Senior Professionals"],
            "agg_checklist": ["AGG-konform formuliert."],
            "job_ad_text": "Fallback",
            "intro": "Intro",
            "responsibilities": ["Aufgabe"],
            "profile": ["Profil"],
            "offer": ["Benefit"],
            "cta": "Jetzt bewerben.",
            "equal_opportunity_note": "Alle Bewerbungen sind willkommen.",
        }
    )

    assert legacy.intro == ""
    assert structured.responsibilities == ["Aufgabe"]


def test_publishable_job_ad_markdown_uses_structured_sections_without_raw_markdown() -> None:
    source = JobAdGenerationResult(
        headline="**Senior Engineer**",
        target_group=[],
        agg_checklist=[],
        job_ad_text="Fallback",
        intro="Gestalte Plattformen.",
        responsibilities=["**Baue Pipelines**"],
        profile=["Python"],
        offer=["Mentoring"],
        cta="Bewirb dich jetzt.",
        equal_opportunity_note="Alle Menschen sind willkommen.",
    )
    sanitized, _ = sanitize_generated_job_ad(source)

    markdown = build_publishable_job_ad_markdown(sanitized)
    plain_text = build_publishable_job_ad_plain_text(sanitized)

    assert "# Senior Engineer" in markdown
    assert "- Baue Pipelines" in markdown
    assert "**" not in markdown
    assert "# " not in plain_text


def test_markdown_article_preview_html_renders_publishable_job_ad_text() -> None:
    preview_html = markdown_article_preview_html(
        "# Senior Engineer\n\n"
        "Gestalte Plattformen.\n\n"
        "## Deine Aufgaben\n\n"
        "- Baue Pipelines\n"
        "- Sichere Datenqualitaet"
    )

    assert "<h1>Senior Engineer</h1>" in preview_html
    assert "<p>Gestalte Plattformen.</p>" in preview_html
    assert "<h2>Deine Aufgaben</h2>" in preview_html
    assert "<li>Baue Pipelines</li>" in preview_html
    assert "<li>Sichere Datenqualitaet</li>" in preview_html


def test_estimate_text_area_height_has_minimum_and_cap() -> None:
    assert estimate_text_area_height("Kurz") == 160
    assert estimate_text_area_height("\n".join(["Zeile"] * 50)) == 520
