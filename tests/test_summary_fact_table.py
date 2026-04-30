from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

from constants import AnswerType, SSKey
from schemas import JobAdExtract, Question, QuestionPlan, QuestionStep


SUMMARY_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "08_summary.py"
SPEC = spec_from_file_location("wizard_pages.page_08_summary_facts", SUMMARY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load summary page module")
SUMMARY_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(SUMMARY_MODULE)  # type: ignore[attr-defined]


def _meta(*, selected_occupation_title: str | None) -> object:
    return SUMMARY_MODULE.SummaryMeta(
        role_label="Data Engineer",
        company_label="Acme",
        country_label="DE",
        selected_occupation_title=selected_occupation_title or "",
        nace_code="62.01",
        nace_mapped_esco_uri="http://data.europa.eu/esco/occupation/123",
        readiness_items=[],
    )


def _artifacts(*, with_brief: bool = False) -> object:
    brief = None
    if with_brief:
        brief = SimpleNamespace()
    return SUMMARY_MODULE.SummaryArtifactState(
        brief=brief,
        selected_role_tasks=[],
        selected_skills=[],
        input_fingerprint="in",
        last_brief_fingerprint="out",
        is_dirty=True,
    )


def test_build_summary_fact_rows_include_jobspec_core_facts() -> None:
    job = JobAdExtract(
        job_title="Data Engineer",
        company_name="Acme",
        location_country="DE",
        location_city="Berlin",
    )

    rows = SUMMARY_MODULE._build_summary_fact_rows(
        job=job,
        answers={},
        plan=None,
        artifacts=_artifacts(),
        meta=_meta(selected_occupation_title="Dateningenieur/in"),
    )

    role_row = next(row.to_dict() for row in rows if row.feld == "Rolle")
    assert role_row == {
        "Bereich": "Kernprofil",
        "Feld": "Rolle",
        "Wert": "Data Engineer",
        "Quelle": "Jobspec",
        "Status": "Vollständig",
    }


def test_build_summary_fact_rows_include_answer_rows() -> None:
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="team",
                title_de="Team",
                questions=[
                    Question(
                        id="team_size",
                        label="Teamgröße",
                        answer_type=AnswerType.NUMBER,
                    ),
                ],
            )
        ]
    )

    rows = SUMMARY_MODULE._build_summary_fact_rows(
        job=JobAdExtract(job_title="Data Engineer"),
        answers={"team_size": 7},
        plan=plan,
        artifacts=_artifacts(),
        meta=_meta(selected_occupation_title=None),
    )

    team_row = next(row.to_dict() for row in rows if row.feld == "Teamgröße")
    assert team_row["Bereich"] == "Team"
    assert team_row["Wert"] == "7"
    assert team_row["Quelle"] == "Intake-Antwort"
    assert team_row["Status"] == "Vollständig"


def test_build_summary_fact_rows_marks_missing_values_as_fehlend() -> None:
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="skills",
                title_de="Skills",
                questions=[
                    Question(
                        id="must_have",
                        label="Must-Haves",
                        answer_type=AnswerType.MULTI_SELECT,
                    )
                ],
            )
        ]
    )

    rows = SUMMARY_MODULE._build_summary_fact_rows(
        job=JobAdExtract(job_title="Data Engineer"),
        answers={},
        plan=plan,
        artifacts=_artifacts(),
        meta=_meta(selected_occupation_title=None),
    )

    skill_row = next(row.to_dict() for row in rows if row.feld == "Must-Haves")
    assert skill_row["Wert"] == "Nicht beantwortet"
    assert skill_row["Status"] == "Fehlend"


def test_build_summary_fact_rows_include_esco_and_nace_rows_when_anchor_confirmed(
    monkeypatch,
) -> None:
    monkeypatch.setattr(SUMMARY_MODULE, "has_confirmed_esco_anchor", lambda: True)
    rows = SUMMARY_MODULE._build_summary_fact_rows(
        job=JobAdExtract(job_title="Data Engineer"),
        answers={},
        plan=None,
        artifacts=_artifacts(),
        meta=_meta(selected_occupation_title="Dateningenieur/in"),
    )

    fields = {row.feld: row.to_dict() for row in rows}
    assert fields["ESCO Occupation"]["Status"] == "Automatisch erkannt"
    assert fields["NACE-Code"]["Wert"] == "62.01"
    assert fields["NACE-Code"]["Status"] == "Automatisch erkannt"
    assert fields["NACE → ESCO Mapping"]["Wert"].startswith("http://data.europa.eu")


def test_build_summary_fact_rows_have_deterministic_ordering() -> None:
    rows = SUMMARY_MODULE._build_summary_fact_rows(
        job=JobAdExtract(job_title="Data Engineer"),
        answers={},
        plan=None,
        artifacts=_artifacts(),
        meta=_meta(selected_occupation_title=None),
    )

    ordered_fields = [row.feld for row in rows[:6]]
    assert ordered_fields == [
        "Rolle",
        "Unternehmen",
        "Land",
        "Stadt",
        "NACE-Code",
        "Recruiting Brief",
    ]


def test_build_summary_fact_rows_marks_partial_multiselect_as_teilweise() -> None:
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key="skills",
                title_de="Skills",
                questions=[
                    Question(
                        id="must_have",
                        label="Must-Haves",
                        answer_type=AnswerType.MULTI_SELECT,
                    )
                ],
            )
        ]
    )

    rows = SUMMARY_MODULE._build_summary_fact_rows(
        job=JobAdExtract(job_title="Data Engineer"),
        answers={"must_have": ["Python", ""]},
        plan=plan,
        artifacts=_artifacts(),
        meta=_meta(selected_occupation_title=None),
    )

    skill_row = next(row.to_dict() for row in rows if row.feld == "Must-Haves")
    assert skill_row["Wert"] == "Python"
    assert skill_row["Status"] == "Teilweise"


def test_build_esco_coverage_chart_spec_contains_expected_bars() -> None:
    spec = SUMMARY_MODULE._build_esco_coverage_chart_spec(
        metrics={
            "essential_total": 3,
            "optional_total": 2,
            "essential_covered": 2,
            "optional_covered": 1,
        },
        unmapped_requirements_count=2,
    )

    assert spec["mark"]["type"] == "bar"
    values = spec["data"]["values"]
    assert {"group": "Quelle", "category": "Must-have (Jobspec)", "value": 3} in values
    assert {
        "group": "Quelle",
        "category": "Nice-to-have (Jobspec)",
        "value": 2,
    } in values
    assert {"group": "Abdeckung", "category": "ESCO-unterstützt", "value": 3} in values
    assert {"group": "Abdeckung", "category": "Nicht gemappt", "value": 2} in values


def test_render_summary_facts_section_uses_esco_shared_fields_for_coverage(
    monkeypatch,
) -> None:
    class _FakeStreamlit:
        def __init__(self, session_state: dict[str, object]):
            self.session_state = session_state
            self.info_calls: list[str] = []
            self.caption_calls: list[str] = []
            self.vega_specs: list[dict[str, object]] = []
            self.markdown_calls: list[str] = []

        def markdown(self, text: str, **_: object) -> None:
            self.markdown_calls.append(text)

        def info(self, text: str, **_: object) -> None:
            self.info_calls.append(text)

        def caption(self, text: str, **_: object) -> None:
            self.caption_calls.append(text)

        def vega_lite_chart(self, spec: dict[str, object], **_: object) -> None:
            self.vega_specs.append(spec)

    fake_st = _FakeStreamlit(
        {
            SSKey.JOB_EXTRACT.value: {
                "job_title": "Data Engineer",
                "must_have_skills": ["Python", "SQL"],
                "nice_to_have_skills": ["Airflow"],
            },
            SSKey.ESCO_CONFIRMED_ESSENTIAL_SKILLS.value: [
                {"title": "Python"},
                {"title": "Databricks"},
            ],
            SSKey.ESCO_CONFIRMED_OPTIONAL_SKILLS.value: [{"title": "Airflow"}],
            SSKey.ESCO_UNMAPPED_REQUIREMENT_TERMS.value: ["Kafka"],
        }
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)
    monkeypatch.setattr(SUMMARY_MODULE, "_render_summary_facts_table", lambda *_: None)

    vm = SUMMARY_MODULE.SummaryViewModel(
        job=JobAdExtract(job_title="Data Engineer"),
        answers={},
        plan=None,
        meta=_meta(selected_occupation_title="Dateningenieur/in"),
        status=SUMMARY_MODULE.SummaryStatus(
            completion_ratio=1.0,
            completion_text="100%",
            brief_state="missing",
            brief_status_label="",
            next_step="",
            readiness_percent=0,
            ready_for_follow_ups=False,
            esco_ready=False,
            nace_ready=False,
        ),
        fact_rows=[],
        artifacts=_artifacts(),
    )

    SUMMARY_MODULE._render_summary_facts_section(vm)

    assert fake_st.info_calls == []
    assert len(fake_st.vega_specs) == 1
    values = fake_st.vega_specs[0]["data"]["values"]  # type: ignore[index]
    assert {"group": "Quelle", "category": "Must-have (Jobspec)", "value": 2} in values
    assert {"group": "Quelle", "category": "Nice-to-have (Jobspec)", "value": 1} in values
    assert {"group": "Abdeckung", "category": "ESCO-unterstützt", "value": 2} in values
    assert {"group": "Abdeckung", "category": "Nicht gemappt", "value": 1} in values
