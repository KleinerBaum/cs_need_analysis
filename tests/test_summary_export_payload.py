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
