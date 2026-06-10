from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

from constants import FactKey, FactSourceType, SSKey
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
            selected_benefits=["Mentoring"],
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

    assert payload["job_extract"] == {"job_title": "Engineer"}
    assert payload["answers"] == {}
    assert payload["interview_process"]["candidate_stages"] == []
    assert payload["interview_process"]["selected_values"] == []


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
                SSKey.BENEFITS_SELECTED.value: [],
            }
        ),
    )
    monkeypatch.setattr(SUMMARY_MODULE, "get_esco_occupation_selected", lambda: None)

    payload = SUMMARY_MODULE._build_structured_export_payload(
        _brief_with_saved_selections()
    )

    assert payload["selected_role_tasks"] == ["Build ETL pipelines"]
    assert payload["selected_skills"] == ["Python", "SQL"]
    assert payload["selected_benefits"] == ["Mentoring"]


def test_build_structured_export_payload_includes_canonical_intake_facts(
    monkeypatch,
) -> None:
    evidence = {
        "source_type": FactSourceType.JOBSPEC.value,
        "source_label": "Jobspec extraction",
        "confidence": 0.75,
        "evidence_snippet": None,
        "updated_at": "2026-06-10T00:00:00+00:00",
    }
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.ESCO_CONFIG.value: {},
                SSKey.ESCO_SKILLS_SELECTED_MUST.value: [],
                SSKey.ESCO_SKILLS_SELECTED_NICE.value: [],
                SSKey.INTAKE_FACTS.value: {
                    FactKey.ROLE_JOB_TITLE.value: "Engineer",
                },
                SSKey.INTAKE_FACT_EVIDENCE.value: {
                    FactKey.ROLE_JOB_TITLE.value: evidence,
                },
            }
        ),
    )
    monkeypatch.setattr(SUMMARY_MODULE, "get_esco_occupation_selected", lambda: None)

    payload = SUMMARY_MODULE._build_structured_export_payload(_brief())

    assert payload["job_extract"] == {"job_title": "Engineer"}
    assert payload["intake_facts"] == {
        FactKey.ROLE_JOB_TITLE.value: "Engineer",
    }
    assert payload["intake_fact_evidence"] == {
        FactKey.ROLE_JOB_TITLE.value: evidence,
    }


def test_build_structured_export_payload_includes_session_selected_benefits(
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
                SSKey.BENEFITS_SELECTED.value: ["Flexible Arbeitsmodelle"],
            }
        ),
    )
    monkeypatch.setattr(SUMMARY_MODULE, "get_esco_occupation_selected", lambda: None)

    payload = SUMMARY_MODULE._build_structured_export_payload(_brief())

    assert payload["selected_benefits"] == ["Flexible Arbeitsmodelle"]


def test_build_structured_export_payload_includes_occupation_context(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.OCCUPATION_PROFILE.value: {
                    "occupation_family": "digital_product",
                    "confidence": 0.72,
                    "authority_source": "deterministic_rules",
                    "pack_keys": ["base.core", "family.digital_product"],
                },
                SSKey.QUESTION_FLOW_PROVENANCE.value: {
                    "base_question_count": 3,
                    "compiled_question_count": 5,
                    "selected_pack_keys": ["base.core", "family.digital_product"],
                    "injected_question_ids": ["ctx_digital_ownership"],
                },
                SSKey.ESCO_CONFIG.value: {},
                SSKey.ESCO_SKILLS_SELECTED_MUST.value: [],
                SSKey.ESCO_SKILLS_SELECTED_NICE.value: [],
            }
        ),
    )
    monkeypatch.setattr(SUMMARY_MODULE, "get_esco_occupation_selected", lambda: None)

    payload = SUMMARY_MODULE._build_structured_export_payload(_brief())

    assert payload["occupation_context_profile"]["occupation_family"] == (
        "digital_product"
    )
    assert payload["occupation_context_profile"]["pack_keys"] == [
        "base.core",
        "family.digital_product",
    ]
    assert payload["question_flow_provenance"]["compiled_question_count"] == 5
    assert payload["question_flow_provenance"]["injected_question_ids"] == [
        "ctx_digital_ownership"
    ]


def test_build_brief_structured_preview_payload_uses_export_subset(monkeypatch) -> None:
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

    brief = _brief_with_saved_selections()
    preview_payload = SUMMARY_MODULE._build_brief_structured_preview_payload(brief)
    export_payload = SUMMARY_MODULE._build_structured_export_payload(brief)

    assert preview_payload == {
        "job_extract": {"job_title": "Engineer"},
        "answers": {},
        "selected_role_tasks": ["Build ETL pipelines"],
        "selected_skills": ["Python", "SQL"],
        "selected_benefits": ["Mentoring"],
    }
    assert export_payload["selected_role_tasks"] == preview_payload["selected_role_tasks"]
    assert export_payload["selected_skills"] == preview_payload["selected_skills"]
    assert export_payload["selected_benefits"] == preview_payload["selected_benefits"]


def test_build_structured_export_payload_keeps_rag_provenance_for_suggestions(
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
                SSKey.ROLE_TASKS_LLM_SUGGESTED.value: [
                    {
                        "label": "Run incident postmortems",
                        "source": "AI",
                        "source_hint": "esco_rag",
                        "source_file": "rag/tasks.json",
                        "concept_uri": "uri:task:incident-postmortem",
                        "rationale": "Derived from similar ESCO occupation tasks.",
                        "evidence": "RAG snippet on incident-response workflows.",
                    }
                ],
                SSKey.SKILLS_LLM_SUGGESTED.value: [
                    {
                        "label": "Data Governance",
                        "source": "AI suggestion",
                        "source_hint": "esco_rag",
                        "source_file": "rag/skills.json",
                        "concept_uri": "uri:skill:data-governance",
                        "rationale": "Recurring in adjacent occupation profiles.",
                        "evidence": "RAG snippet referencing governance standards.",
                    }
                ],
            }
        ),
    )
    monkeypatch.setattr(SUMMARY_MODULE, "get_esco_occupation_selected", lambda: None)

    payload = SUMMARY_MODULE._build_structured_export_payload(_brief())

    assert payload["role_task_suggestions"] == [
        {
            "label": "Run incident postmortems",
            "source_hint": "esco_rag",
            "source_file": "rag/tasks.json",
            "concept_uri": "uri:task:incident-postmortem",
            "rationale": "Derived from similar ESCO occupation tasks.",
            "evidence": "RAG snippet on incident-response workflows.",
        }
    ]
    assert payload["skill_suggestions"] == [
        {
            "label": "Data Governance",
            "source_hint": "esco_rag",
            "source_file": "rag/skills.json",
            "concept_uri": "uri:skill:data-governance",
            "rationale": "Recurring in adjacent occupation profiles.",
            "evidence": "RAG snippet referencing governance standards.",
        }
    ]


def test_build_structured_export_payload_includes_esco_uri_and_label(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.ESCO_CONFIG.value: {"selected_version": "v1.2.0", "data_source_mode": "api_live"},
                SSKey.ESCO_MATCH_REASON.value: "Manuell als semantischer Anker bestätigt.",
                SSKey.ESCO_MATCH_CONFIDENCE.value: "high",
                SSKey.ESCO_MATCH_PROVENANCE.value: ["manually selected by user"],
                SSKey.ESCO_MATRIX_ENABLED.value: True,
                SSKey.ESCO_MATRIX_LOADED.value: True,
                SSKey.ESCO_MATRIX_METADATA.value: {
                    "source": "offline_build",
                    "version": "2026.04",
                    "records": 12,
                },
                SSKey.ESCO_MATRIX_COVERAGE_ROWS.value: [
                    {
                        "occupation_group": "251",
                        "skill_group_uri": "uri:group:core",
                        "skill_group_id": "group-core",
                        "skill_group_label": "Core",
                        "expected_share_percent": 60.0,
                        "matched_skill_uris": ["uri:skill:must"],
                        "matched_skill_titles": ["Python"],
                        "coverage_status": "covered",
                        "match_basis": "uri",
                        "matrix_bucket": "must",
                    }
                ],
                SSKey.ESCO_MATRIX_COVERAGE_CONTEXT.value: {
                    "reason": "ok",
                    "occupation_group": "251",
                    "rows": 1,
                },
                SSKey.ESCO_SKILLS_SELECTED_MUST.value: [
                    {"uri": "uri:skill:must", "title": "Python", "type": "skill"}
                ],
                SSKey.ESCO_SKILLS_SELECTED_NICE.value: [
                    {"uri": "uri:skill:nice", "title": "dbt", "type": "skill"}
                ],
                SSKey.ESCO_UNRESOLVED_TERM_DECISIONS.value: [
                    {
                        "raw_term": "PySpark",
                        "action": "map_to_esco_skill",
                        "mapped_uri": "uri:skill:pyspark",
                        "mapped_title": "Apache Spark",
                        "bucket": "must",
                        "source_mode": "api_live",
                    }
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
        "provenance_categories": ["manually selected by user"],
    }
    assert payload["esco_skills_must"] == [{"uri": "uri:skill:must", "label": "Python"}]
    assert payload["esco_skills_nice"] == [{"uri": "uri:skill:nice", "label": "dbt"}]
    decision = payload["esco_unresolved_term_decisions"][0]
    assert decision["raw_term"] == "PySpark"
    assert decision["action"] == "map_to_esco_skill"
    assert decision["mapped_uri"] == "uri:skill:pyspark"
    assert decision["mapped_title"] == "Apache Spark"
    assert decision["bucket"] == "must"
    assert decision["source_mode"] == "api_live"
    assert payload["esco_version"] == "v1.2.0"
    assert payload["esco_matrix"]["source"] == "offline_build"
    assert payload["esco_matrix"]["version"] == "2026.04"
    assert payload["esco_matrix"]["coverage_rows"] == 1
    assert payload["esco_matrix_coverage"][0]["coverage_status"] == "covered"
    assert payload["esco_matrix_coverage"][0]["match_basis"] == "uri"
    assert payload["esco_matrix_coverage_context"]["occupation_group"] == "251"


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


def test_build_structured_export_payload_skips_invalid_or_unmatched_recommended_titles(
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
                    "uri": "uri:occ:other",
                    "recommended_titles": {
                        "de": ["Data Engineer", "   ", 123],
                        "en": "Data Engineer",
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

    assert "recommended_titles" not in payload


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


def test_build_structured_export_payload_includes_interview_process(
    monkeypatch,
) -> None:
    flow = {
        "contacts": [
            {
                "role": "Authority",
                "name": "A. Example",
                "phone": "",
                "email": "a.example@example.com",
                "participates_in_interview": True,
                "interview_datetime": "2026-06-05T09:00:00",
            }
        ],
        "info_loop_items": ["Interview-Feedback bündeln"],
        "earliest_start_date": "2026-07-01",
        "latest_start_date": "2026-08-01",
        "selected_value_ids": [],
    }
    brief = VacancyBrief(
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
            job_extract={
                "job_title": "Engineer",
                "recruitment_steps": [
                    {"name": "HR Screen", "details": "30 Minuten"},
                    {"name": "Fachinterview"},
                ],
            },
            answers={},
        ),
    )
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.ESCO_CONFIG.value: {},
                SSKey.ESCO_SKILLS_SELECTED_MUST.value: [],
                SSKey.ESCO_SKILLS_SELECTED_NICE.value: [],
                SSKey.INTERVIEW_INTERNAL_FLOW.value: flow,
            }
        ),
    )
    monkeypatch.setattr(SUMMARY_MODULE, "get_esco_occupation_selected", lambda: None)

    payload = SUMMARY_MODULE._build_structured_export_payload(brief)

    interview_process = payload["interview_process"]
    assert interview_process["candidate_stages"] == [
        "HR Screen: 30 Minuten",
        "Fachinterview",
    ]
    assert interview_process["internal_flow"]["info_loop_items"] == [
        "Interview-Feedback bündeln"
    ]
    assert any(
        row["Feld"] == "Authority Ansprechpartner"
        and row["Wert"] == "A. Example"
        for row in interview_process["selected_values"]
    )


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



def test_build_structured_export_payload_normalizes_legacy_unresolved_action_fields(
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
                SSKey.ESCO_UNRESOLVED_TERM_DECISIONS.value: [
                    {
                        "raw_term": "PySpark",
                        "esco_uri": "uri:skill:pyspark",
                        "matched_label": "Apache Spark",
                        "match_method": "retry_query",
                        "status": "retried",
                    }
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

    assert payload["semantic_export_mode"] == "anchored"
    assert payload["esco_unresolved_term_decisions"] == [
        {
            "raw_term": "PySpark",
            "action": "retry_search",
            "mapped_uri": "uri:skill:pyspark",
            "mapped_title": "Apache Spark",
        }
    ]


def test_build_structured_export_payload_omits_esco_uri_exports_when_degraded(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.ESCO_CONFIG.value: {},
                SSKey.ESCO_SKILLS_SELECTED_MUST.value: [
                    {"uri": "uri:skill:python", "title": "Python", "type": "skill"}
                ],
                SSKey.ESCO_SKILLS_SELECTED_NICE.value: [
                    {"uri": "uri:skill:dbt", "title": "dbt", "type": "skill"}
                ],
                SSKey.ESCO_UNRESOLVED_TERM_DECISIONS.value: [
                    {
                        "raw_term": "PySpark",
                        "esco_uri": "uri:skill:pyspark",
                        "matched_label": "Apache Spark",
                        "match_method": "retry_query",
                        "status": "retried",
                    }
                ],
            }
        ),
    )
    monkeypatch.setattr(SUMMARY_MODULE, "get_esco_occupation_selected", lambda: None)

    payload = SUMMARY_MODULE._build_structured_export_payload(_brief())

    assert payload["semantic_export_mode"] == "degraded"
    assert payload["esco_anchor_state"] == "degraded_unconfirmed"
    assert "esco_occupations" not in payload
    assert "esco_primary_anchor" not in payload
    assert "esco_skills_must" not in payload
    assert "esco_skills_nice" not in payload
    assert "esco_unresolved_term_decisions" not in payload
