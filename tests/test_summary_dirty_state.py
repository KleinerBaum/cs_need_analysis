from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

from constants import FactKey, FactResolutionStatus, FactSourceType, SSKey
from schemas import JobAdExtract


SUMMARY_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "08_summary.py"
SPEC = spec_from_file_location("wizard_pages.page_08_summary_dirty", SUMMARY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load summary page module")
SUMMARY_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(SUMMARY_MODULE)  # type: ignore[attr-defined]


def _fingerprint(
    monkeypatch,
    *,
    answers: dict[str, object] | None = None,
    intake_facts: dict[str, object] | None = None,
    intake_fact_resolution: dict[str, object] | None = None,
    occupation_title: str = "Data Engineer",
    esco_provenance: list[str] | None = None,
) -> str:
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.ESCO_MATCH_REASON.value: "Anker bestätigt",
                SSKey.ESCO_MATCH_CONFIDENCE.value: "high",
                SSKey.ESCO_MATCH_PROVENANCE.value: (
                    esco_provenance
                    if esco_provenance is not None
                    else ["exact label match"]
                ),
                SSKey.ESCO_SKILLS_SELECTED_MUST.value: [
                    {"uri": "uri:skill:python", "title": "Python"}
                ],
                SSKey.ESCO_SKILLS_SELECTED_NICE.value: [],
            }
        ),
    )
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "get_esco_occupation_selected",
        lambda: {"uri": "uri:occ:1", "title": occupation_title},
    )

    job = JobAdExtract(job_title="Engineer", company_name="ACME", location_country="DE")
    return SUMMARY_MODULE._build_summary_input_fingerprint(
        job=job,
        answers=answers or {"team_size": 5},
        intake_facts=intake_facts or {},
        intake_fact_resolution=intake_fact_resolution or {},
        selected_role_tasks=["Build data products"],
        selected_skills=["Python", "SQL"],
        selected_benefits=["Mentoring"],
        esco_occupation_selected=SUMMARY_MODULE._read_selected_esco_occupation(),
        esco_match_explainability=SUMMARY_MODULE._read_esco_match_explainability(),
        esco_selected_skills_must=SUMMARY_MODULE._read_esco_skill_refs(
            SSKey.ESCO_SKILLS_SELECTED_MUST
        ),
        esco_selected_skills_nice=SUMMARY_MODULE._read_esco_skill_refs(
            SSKey.ESCO_SKILLS_SELECTED_NICE
        ),
    )


def test_summary_dirty_fingerprint_changes_when_answers_change(monkeypatch) -> None:
    baseline = _fingerprint(monkeypatch, answers={"team_size": 5})
    changed = _fingerprint(monkeypatch, answers={"team_size": 10})

    assert baseline != changed


def test_summary_dirty_fingerprint_changes_when_canonical_fact_changes(
    monkeypatch,
) -> None:
    fact_key = FactKey.COMPANY_COMPANY_NAME.value
    baseline = _fingerprint(
        monkeypatch,
        intake_facts={fact_key: "ACME GmbH"},
        intake_fact_resolution={
            fact_key: {
                "status": FactResolutionStatus.CONFIRMED.value,
                "value": "ACME GmbH",
                "source_type": FactSourceType.MANUAL.value,
                "confirmed": True,
            }
        },
    )
    changed = _fingerprint(
        monkeypatch,
        intake_facts={fact_key: "Example GmbH"},
        intake_fact_resolution={
            fact_key: {
                "status": FactResolutionStatus.CONFIRMED.value,
                "value": "Example GmbH",
                "source_type": FactSourceType.MANUAL.value,
                "confirmed": True,
            }
        },
    )

    assert baseline != changed


def test_summary_dirty_fingerprint_changes_when_esco_occupation_changes(
    monkeypatch,
) -> None:
    baseline = _fingerprint(monkeypatch, occupation_title="Data Engineer")
    changed = _fingerprint(monkeypatch, occupation_title="Analytics Engineer")

    assert baseline != changed


def test_summary_dirty_fingerprint_changes_when_esco_provenance_changes(
    monkeypatch,
) -> None:
    baseline = _fingerprint(monkeypatch, esco_provenance=["exact label match"])
    changed = _fingerprint(monkeypatch, esco_provenance=["manually selected by user"])

    assert baseline != changed


def test_summary_dirty_false_after_explicit_brief_regeneration(monkeypatch) -> None:
    current_fingerprint = _fingerprint(monkeypatch)

    monkeypatch.setattr(
        SUMMARY_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.BRIEF.value: None,
                SSKey.SUMMARY_LAST_BRIEF_FINGERPRINT.value: current_fingerprint,
            }
        ),
    )

    artifacts = SUMMARY_MODULE._build_summary_artifact_state(
        selected_role_tasks=["Build data products"],
        selected_skills=["Python", "SQL"],
        selected_benefits=["Mentoring"],
        input_fingerprint=current_fingerprint,
    )

    assert artifacts.is_dirty is False


def test_artifact_with_result_but_missing_fingerprint_is_stale(monkeypatch) -> None:
    fake_st = SimpleNamespace(
        session_state={
            SSKey.JOB_AD_DRAFT_CUSTOM.value: {"headline": "Engineer"},
            SSKey.SUMMARY_ARTIFACT_FINGERPRINTS.value: {},
        }
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)
    artifacts = SUMMARY_MODULE.SummaryArtifactState(
        brief=None,
        selected_role_tasks=[],
        selected_skills=[],
        selected_benefits=[],
        input_fingerprint="current",
        last_brief_fingerprint="current",
        is_dirty=False,
    )
    vm = SUMMARY_MODULE.SummaryViewModel(
        job=JobAdExtract(job_title="Engineer"),
        answers={},
        plan=None,
        meta=SUMMARY_MODULE.SummaryMeta(
            role_label="Engineer",
            company_label="",
            country_label="",
            selected_occupation_title="",
            readiness_items=[],
        ),
        status=SUMMARY_MODULE.SummaryStatus(
            completion_ratio=1.0,
            completion_text="ok",
            brief_state="current",
            brief_status_label="ok",
            next_step="next",
            readiness_percent=100,
            ready_for_follow_ups=True,
            esco_ready=False,
        ),
        fact_rows=[],
        artifacts=artifacts,
    )

    assert SUMMARY_MODULE._artifact_status_label(vm, "job_ad") == ("stale", "Veraltet")
