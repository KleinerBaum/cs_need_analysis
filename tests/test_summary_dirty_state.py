from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

from constants import SSKey
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
    occupation_title: str = "Data Engineer",
    nace_mapping: dict[str, str] | None = None,
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
                    else ["matched from jobspec title"]
                ),
                SSKey.ESCO_SKILLS_SELECTED_MUST.value: [
                    {"uri": "uri:skill:python", "title": "Python"}
                ],
                SSKey.ESCO_SKILLS_SELECTED_NICE.value: [],
                SSKey.COMPANY_NACE_CODE.value: "62.01",
                SSKey.EURES_NACE_TO_ESCO.value: nace_mapping
                if nace_mapping is not None
                else {"62.01": "uri:occ:data-engineer"},
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
        selected_role_tasks=["Build data products"],
        selected_skills=["Python", "SQL"],
        esco_occupation_selected=SUMMARY_MODULE._read_selected_esco_occupation(),
        esco_match_explainability=SUMMARY_MODULE._read_esco_match_explainability(),
        esco_selected_skills_must=SUMMARY_MODULE._read_esco_skill_refs(
            SSKey.ESCO_SKILLS_SELECTED_MUST
        ),
        esco_selected_skills_nice=SUMMARY_MODULE._read_esco_skill_refs(
            SSKey.ESCO_SKILLS_SELECTED_NICE
        ),
        nace_code="62.01",
        nace_to_esco_mapping=SUMMARY_MODULE._read_nace_to_esco_mapping(),
    )


def test_summary_dirty_fingerprint_changes_when_answers_change(monkeypatch) -> None:
    baseline = _fingerprint(monkeypatch, answers={"team_size": 5})
    changed = _fingerprint(monkeypatch, answers={"team_size": 10})

    assert baseline != changed


def test_summary_dirty_fingerprint_changes_when_esco_occupation_changes(
    monkeypatch,
) -> None:
    baseline = _fingerprint(monkeypatch, occupation_title="Data Engineer")
    changed = _fingerprint(monkeypatch, occupation_title="Analytics Engineer")

    assert baseline != changed


def test_summary_dirty_fingerprint_changes_when_nace_mapping_changes(
    monkeypatch,
) -> None:
    baseline = _fingerprint(
        monkeypatch, nace_mapping={"62.01": "uri:occ:data-engineer"}
    )
    changed = _fingerprint(
        monkeypatch, nace_mapping={"62.01": "uri:occ:software-developer"}
    )

    assert baseline != changed


def test_summary_dirty_fingerprint_changes_when_esco_provenance_changes(
    monkeypatch,
) -> None:
    baseline = _fingerprint(monkeypatch, esco_provenance=["matched from jobspec title"])
    changed = _fingerprint(monkeypatch, esco_provenance=["manual override"])

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
        input_fingerprint=current_fingerprint,
    )

    assert artifacts.is_dirty is False
