from __future__ import annotations

from summary_esco import (
    build_esco_coverage_chart_spec,
    build_esco_coverage_kpis,
    build_esco_coverage_metrics,
    build_esco_mapping_report_csv,
    extract_skills_step_raw_terms,
    normalize_skill_term,
    to_esco_export_concepts,
)


def test_to_esco_export_concepts_keeps_schema_valid_concepts_only() -> None:
    concepts = to_esco_export_concepts(
        [
            {"uri": "uri:skill:python", "title": "Python", "type": "skill"},
            {"uri": "", "title": "Broken", "type": "skill"},
            {"title": "Missing URI", "type": "skill"},
            "not a concept",
        ]
    )

    assert concepts == [
        {"uri": "uri:skill:python", "label": "Python"},
        {"uri": "", "label": "Broken"},
    ]


def test_extract_skills_step_raw_terms_dedupes_across_skill_buckets() -> None:
    terms = extract_skills_step_raw_terms(
        {
            "must_have_skills": [" Python ", "SQL", ""],
            "nice_to_have_skills": ["python", "Docker"],
        }
    )

    assert terms == ["Python", "SQL", "Docker"]
    assert normalize_skill_term("  PYTHON   scripting ") == "python scripting"


def test_build_esco_coverage_metrics_matches_must_and_nice_titles() -> None:
    metrics = build_esco_coverage_metrics(
        job_extract_payload={
            "must_have_skills": ["Python", "SQL"],
            "nice_to_have_skills": ["Docker"],
        },
        essential_skills=[{"title": "python"}],
        optional_skills=[{"title": "Docker"}],
    )

    assert metrics == {
        "essential_covered": 1,
        "essential_total": 2,
        "essential_pct": 50,
        "optional_covered": 1,
        "optional_total": 1,
        "optional_pct": 100,
    }


def test_build_esco_coverage_chart_and_kpis_use_consistent_totals() -> None:
    metrics = {
        "essential_total": 3,
        "optional_total": 2,
        "essential_covered": 2,
        "optional_covered": 1,
    }

    spec = build_esco_coverage_chart_spec(
        metrics=metrics,
        unmapped_requirements_count=2,
    )
    kpis = build_esco_coverage_kpis(
        metrics=metrics,
        unmapped_requirements_count=2,
    )

    values = spec["data"]["values"]
    assert {"group": "Abdeckung", "category": "ESCO-unterstützt", "value": 3} in values
    assert {
        "group": "Abdeckung",
        "category": "Gesamtanforderungen",
        "value": 5,
    } in values
    assert kpis == [
        ("Anforderungen", 5),
        ("ESCO unterstützt", 3),
        ("Nicht gemappt", 2),
        ("Quelle vorhanden", 5),
    ]


def test_build_esco_mapping_report_csv_has_stable_columns() -> None:
    csv_text = build_esco_mapping_report_csv(
        [
            {
                "raw_term": "Python",
                "chosen_uri": "uri:skill:python",
                "chosen_label": "Python",
                "match_method": "label_exact",
                "notes": "",
            }
        ]
    ).decode("utf-8")

    assert (
        csv_text.splitlines()[0]
        == "raw_term,chosen_uri,chosen_label,match_method,notes"
    )
    assert "Python,uri:skill:python,Python,label_exact," in csv_text
