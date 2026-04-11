from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

from constants import SSKey
from schemas import VacancyBrief


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
        structured_data={"job_extract": {"job_title": "Engineer"}, "answers": {}},
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


def test_build_structured_export_payload_includes_esco_uri_and_label(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.ESCO_CONFIG.value: {"selected_version": "v1.2.0"},
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
    assert payload["esco_skills_must"] == [{"uri": "uri:skill:must", "label": "Python"}]
    assert payload["esco_skills_nice"] == [{"uri": "uri:skill:nice", "label": "dbt"}]
    assert payload["esco_version"] == "v1.2.0"


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
