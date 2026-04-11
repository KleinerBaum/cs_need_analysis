from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

from constants import SSKey
from schemas import VacancyBrief, VacancyStructuredData


SUMMARY_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "08_summary.py"
SPEC = spec_from_file_location("wizard_pages.page_08_summary_export", SUMMARY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load summary page module")
SUMMARY_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(SUMMARY_MODULE)  # type: ignore[attr-defined]


def _brief() -> VacancyBrief:
    return VacancyBrief(
        one_liner="One line",
        hiring_context="Context",
        role_summary="Summary",
        top_responsibilities=[],
        must_have=[],
        nice_to_have=[],
        dealbreakers=[],
        interview_plan=[],
        evaluation_rubric=[],
        sourcing_channels=[],
        risks_open_questions=[],
        job_ad_draft="Draft",
        structured_data=VacancyStructuredData(
            job_extract={"job_title": "Engineer"},
            answers={},
        ),
    )


def _brief_with_saved_selections() -> VacancyBrief:
    return VacancyBrief(
        one_liner="One line",
        hiring_context="Context",
        role_summary="Summary",
        top_responsibilities=[],
        must_have=[],
        nice_to_have=[],
        dealbreakers=[],
        interview_plan=[],
        evaluation_rubric=[],
        sourcing_channels=[],
        risks_open_questions=[],
        job_ad_draft="Draft",
        structured_data=VacancyStructuredData(
            job_extract={"job_title": "Engineer"},
            answers={},
            selected_role_tasks=["Build ETL pipelines"],
            selected_skills=["Python", "SQL"],
        ),
    )


def test_build_structured_export_payload_keeps_legacy_export_without_esco(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.ESCO_CONFIG.value: {},
                SSKey.ESCO_SKILLS_SELECTED_MUST.value: [],
                SSKey.ESCO_SKILLS_SELECTED_NICE.value: [],
            }
        ),
    )
    monkeypatch.setattr(SUMMARY_MODULE, "get_esco_occupation_selected", lambda: None)

    payload = SUMMARY_MODULE._build_structured_export_payload(_brief())

    assert payload == {"job_extract": {"job_title": "Engineer"}, "answers": {}}


def test_build_structured_export_payload_preserves_saved_tasks_and_skills(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.ESCO_CONFIG.value: {},
                SSKey.ESCO_SKILLS_SELECTED_MUST.value: [],
                SSKey.ESCO_SKILLS_SELECTED_NICE.value: [],
                SSKey.ROLE_TASKS_SELECTED.value: [],
                SSKey.SKILLS_SELECTED.value: [],
            }
        ),
    )
    monkeypatch.setattr(SUMMARY_MODULE, "get_esco_occupation_selected", lambda: None)

    payload = SUMMARY_MODULE._build_structured_export_payload(
        _brief_with_saved_selections()
    )

    assert payload["selected_role_tasks"] == ["Build ETL pipelines"]
    assert payload["selected_skills"] == ["Python", "SQL"]


def test_build_structured_export_payload_includes_esco_uri_and_label(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.ESCO_CONFIG.value: {"selected_version": "v1.2.0"},
                SSKey.ESCO_MATCH_REASON.value: "Manuell als semantischer Anker bestätigt.",
                SSKey.ESCO_MATCH_CONFIDENCE.value: "high",
                SSKey.ESCO_MATCH_PROVENANCE.value: ["manual override"],
                SSKey.ESCO_SKILLS_SELECTED_MUST.value: [
                    {"uri": "uri:skill:must", "title": "Python", "type": "skill"}
                ],
                SSKey.ESCO_SKILLS_SELECTED_NICE.value: [
                    {"uri": "uri:skill:nice", "title": "dbt", "type": "skill"}
                ],
            }
        ),
    )
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "get_esco_occupation_selected",
        lambda: {"uri": "uri:occ:1", "title": "Data Engineer", "type": "occupation"},
    )

    payload = SUMMARY_MODULE._build_structured_export_payload(_brief())

    assert payload["esco_occupations"] == [
        {"uri": "uri:occ:1", "label": "Data Engineer"}
    ]
    assert payload["esco_occupation_provenance"] == {
        "reason": "Manuell als semantischer Anker bestätigt.",
        "confidence": "high",
        "provenance_categories": ["manual override"],
    }
    assert payload["esco_skills_must"] == [{"uri": "uri:skill:must", "label": "Python"}]
    assert payload["esco_skills_nice"] == [{"uri": "uri:skill:nice", "label": "dbt"}]
    assert payload["esco_version"] == "v1.2.0"


def test_build_structured_export_payload_includes_recommended_titles_by_language(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.ESCO_CONFIG.value: {"selected_version": "latest"},
                SSKey.ESCO_SKILLS_SELECTED_MUST.value: [],
                SSKey.ESCO_SKILLS_SELECTED_NICE.value: [],
                SSKey.ESCO_OCCUPATION_TITLE_VARIANTS.value: {
                    "uri": "uri:occ:1",
                    "recommended_titles": {
                        "de": ["Data Engineer", "Dateningenieur/in"],
                        "en": ["Data Engineer"],
                    },
                },
            }
        ),
    )
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "get_esco_occupation_selected",
        lambda: {"uri": "uri:occ:1", "title": "Data Engineer", "type": "occupation"},
    )

    payload = SUMMARY_MODULE._build_structured_export_payload(_brief())

    assert payload["recommended_titles"] == {
        "de": ["Data Engineer", "Dateningenieur/in"],
        "en": ["Data Engineer"],
    }


def test_build_structured_export_payload_includes_salary_artifacts_when_available(
    monkeypatch,
) -> None:
    salary_forecast = {
        "scenario": "market_upside",
        "forecast": {"p10": 85000, "p50": 98000, "p90": 112000},
        "provenance": {"engine": "benchmark_salary_engine_v1"},
    }
    scenario_rows = [
        {
            "row_id": f"row::{index}",
            "group": "skill_delta",
            "label": f"Scenario {index}",
            "p10": 80000.0,
            "p50": 90000.0 + index,
            "p90": 105000.0,
            "delta_p50": float(index),
            "city": "",
            "country": "DE",
            "radius_km": 50,
            "remote_share_percent": 25,
            "seniority_override": "mid",
            "skills_add": ["Python"],
        }
        for index in range(150)
    ]
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.ESCO_CONFIG.value: {},
                SSKey.ESCO_SKILLS_SELECTED_MUST.value: [],
                SSKey.ESCO_SKILLS_SELECTED_NICE.value: [],
                SSKey.SALARY_FORECAST_LAST_RESULT.value: salary_forecast,
                SSKey.SALARY_SCENARIO_LAB_ROWS.value: scenario_rows,
            }
        ),
    )
    monkeypatch.setattr(SUMMARY_MODULE, "get_esco_occupation_selected", lambda: None)

    payload = SUMMARY_MODULE._build_structured_export_payload(_brief())

    assert payload["salary_forecast"] == salary_forecast
    assert payload["salary_scenarios"] == scenario_rows[:100]
    assert len(payload["salary_scenarios"]) == 100


def test_build_esco_mapping_report_rows_uses_expected_fields_and_sorting(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.JOB_EXTRACT.value: {
                    "must_have_skills": ["Python", "SQL"],
                    "nice_to_have_skills": ["Docker"],
                },
                SSKey.ESCO_SKILLS_SELECTED_MUST.value: [
                    {"uri": "uri:skill:python", "title": "Python", "type": "skill"}
                ],
                SSKey.ESCO_SKILLS_SELECTED_NICE.value: [
                    {"uri": "uri:skill:k8s", "title": "Kubernetes", "type": "skill"}
                ],
                SSKey.ESCO_SKILLS_MAPPING_REPORT.value: {
                    "mapped_count": 2,
                    "unmapped_terms": ["SQL"],
                    "collisions": ["Docker"],
                    "notes": ["1 Duplikat entfernt"],
                },
            }
        ),
    )

    rows = SUMMARY_MODULE._build_esco_mapping_report_rows()

    assert rows
    assert all(
        set(row.keys())
        == {"raw_term", "chosen_uri", "chosen_label", "match_method", "notes"}
        for row in rows
    )
    assert rows == sorted(
        rows,
        key=lambda row: (
            row["raw_term"].casefold(),
            row["chosen_uri"].casefold(),
            row["chosen_label"].casefold(),
            row["match_method"].casefold(),
            row["notes"].casefold(),
        ),
    )
    assert any(
        row["raw_term"] == "Python"
        and row["chosen_uri"] == "uri:skill:python"
        and row["match_method"] == "label_exact"
        for row in rows
    )
    assert any(
        row["raw_term"] == "SQL"
        and row["chosen_uri"] == ""
        and row["match_method"] == "unmapped"
        for row in rows
    )
    assert any(
        row["raw_term"] == ""
        and row["chosen_uri"] == "uri:skill:k8s"
        and row["match_method"] == "manual_selection"
        for row in rows
    )


def test_build_esco_mapping_report_csv_has_expected_columns(monkeypatch) -> None:
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.JOB_EXTRACT.value: {"must_have_skills": ["Python"]},
                SSKey.ESCO_SKILLS_SELECTED_MUST.value: [
                    {"uri": "uri:skill:python", "title": "Python", "type": "skill"}
                ],
                SSKey.ESCO_SKILLS_SELECTED_NICE.value: [],
                SSKey.ESCO_SKILLS_MAPPING_REPORT.value: {
                    "mapped_count": 1,
                    "unmapped_terms": [],
                    "collisions": [],
                    "notes": [],
                },
            }
        ),
    )

    rows = SUMMARY_MODULE._build_esco_mapping_report_rows()
    csv_text = SUMMARY_MODULE._build_esco_mapping_report_csv(rows).decode("utf-8")

    assert (
        csv_text.splitlines()[0]
        == "raw_term,chosen_uri,chosen_label,match_method,notes"
    )


def test_build_country_readiness_items_reports_optional_nace_context(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.EURES_NACE_TO_ESCO.value: {"62.01": "uri:occ:software"},
                SSKey.COMPANY_NACE_CODE.value: "62.01",
            }
        ),
    )
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "get_esco_occupation_selected",
        lambda: {"uri": "uri:occ:1", "title": "Software Developer"},
    )

    rows = SUMMARY_MODULE._build_country_readiness_items(
        SimpleNamespace(location_country="Germany")
    )

    assert ("Land vorhanden", "Germany", True) in rows
    assert ("Semantischer Anker bestätigt", "Ja", True) in rows
    assert ("NACE-Code gesetzt", "62.01", True) in rows
    assert ("NACE → ESCO gemappt", "uri:occ:software", True) in rows
