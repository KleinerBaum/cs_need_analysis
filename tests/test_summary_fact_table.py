from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal

from constants import AnswerType, FactKey, SSKey
from schemas import JobAdExtract, Question, QuestionPlan, QuestionStep, RecruitmentStep


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
        selected_benefits=[],
        input_fingerprint="in",
        last_brief_fingerprint="out",
        is_dirty=True,
    )


class _NoopContext:
    def __enter__(self) -> "_NoopContext":
        return self

    def __exit__(self, *_: object) -> Literal[False]:
        return False


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


def test_build_summary_fact_rows_prefer_canonical_core_facts(monkeypatch) -> None:
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.INTAKE_FACTS.value: {
                    FactKey.ROLE_JOB_TITLE.value: "Analytics Engineer",
                    FactKey.COMPANY_COMPANY_NAME.value: "Manual GmbH",
                },
                SSKey.INTAKE_FACT_EVIDENCE.value: {
                    FactKey.ROLE_JOB_TITLE.value: {"source_label": "Manual input"},
                    FactKey.COMPANY_COMPANY_NAME.value: {"source_label": "Manual input"},
                },
            }
        ),
    )
    job = JobAdExtract(job_title="Data Engineer", company_name="Jobspec GmbH")

    rows = SUMMARY_MODULE._build_summary_fact_rows(
        job=job,
        answers={},
        plan=None,
        artifacts=_artifacts(),
        meta=_meta(selected_occupation_title=None),
    )

    fields = {row.feld: row.to_dict() for row in rows}
    assert [row.feld for row in rows[:5]] == [
        "Rolle",
        "Unternehmen",
        "Land",
        "Stadt",
        "Recruiting Brief",
    ]
    assert fields["Rolle"]["Wert"] == "Analytics Engineer"
    assert fields["Rolle"]["Quelle"] == "Manual input"
    assert fields["Unternehmen"]["Wert"] == "Manual GmbH"
    assert fields["Unternehmen"]["Quelle"] == "Manual input"


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


def test_build_summary_fact_rows_include_selected_benefits() -> None:
    rows = SUMMARY_MODULE._build_summary_fact_rows(
        job=JobAdExtract(job_title="Data Engineer"),
        answers={},
        plan=None,
        artifacts=SUMMARY_MODULE.SummaryArtifactState(
            brief=None,
            selected_role_tasks=[],
            selected_skills=[],
            selected_benefits=["Mentoring", "Flexible Arbeitsmodelle"],
            input_fingerprint="in",
            last_brief_fingerprint="out",
            is_dirty=True,
        ),
        meta=_meta(selected_occupation_title=None),
    )

    benefit_row = next(row.to_dict() for row in rows if row.feld == "Ausgewählte Benefits")
    assert benefit_row["Bereich"] == "Benefits"
    assert benefit_row["Wert"] == "Mentoring | Flexible Arbeitsmodelle"
    assert benefit_row["Quelle"] == "Auswahl"


def test_build_summary_fact_rows_include_interview_phases_from_jobspec(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "st",
        SimpleNamespace(session_state={SSKey.INTERVIEW_INTERNAL_FLOW.value: {}}),
    )
    job = JobAdExtract(
        job_title="Data Engineer",
        recruitment_steps=[
            RecruitmentStep(name="HR Screen", details="30 Minuten"),
            RecruitmentStep(name="Fachinterview"),
        ],
    )

    rows = SUMMARY_MODULE._build_summary_fact_rows(
        job=job,
        answers={},
        plan=None,
        artifacts=_artifacts(),
        meta=_meta(selected_occupation_title=None),
    )

    interview_row = next(row.to_dict() for row in rows if row.feld == "Interviewphasen")
    assert interview_row["Bereich"] == "Interview"
    assert interview_row["Wert"] == "HR Screen: 30 Minuten | Fachinterview"
    assert interview_row["Status"] == "Vollständig"


def test_build_summary_fact_rows_include_selected_interview_flow_values(
    monkeypatch,
) -> None:
    flow = {
        "contacts": [
            {
                "role": "Money",
                "name": "M. Example",
                "phone": "01234",
                "email": "m.example@example.com",
                "participates_in_interview": True,
                "interview_datetime": "2026-06-05T09:00:00",
            }
        ],
        "info_loop_items": ["Interviewtag abstimmen"],
        "earliest_start_date": "2026-07-01",
        "latest_start_date": "2026-08-01",
        "selected_value_ids": [],
    }
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "st",
        SimpleNamespace(session_state={SSKey.INTERVIEW_INTERNAL_FLOW.value: flow}),
    )

    rows = SUMMARY_MODULE._build_summary_fact_rows(
        job=JobAdExtract(job_title="Data Engineer"),
        answers={},
        plan=None,
        artifacts=_artifacts(),
        meta=_meta(selected_occupation_title=None),
    )

    fields = {row.feld: row.to_dict() for row in rows}
    assert fields["Recruiting-Infoloop"]["Bereich"] == "Candidate Communication"
    assert fields["Money Ansprechpartner"]["Wert"] == "M. Example"
    assert fields["Frühestmöglicher Startzeitpunkt"]["Wert"] == "2026-07-01"


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


def test_build_summary_fact_rows_include_esco_row_when_anchor_confirmed(
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


def test_build_summary_fact_rows_have_deterministic_ordering() -> None:
    rows = SUMMARY_MODULE._build_summary_fact_rows(
        job=JobAdExtract(job_title="Data Engineer"),
        answers={},
        plan=None,
        artifacts=_artifacts(),
        meta=_meta(selected_occupation_title=None),
    )

    ordered_fields = [row.feld for row in rows[:5]]
    assert ordered_fields == [
        "Rolle",
        "Unternehmen",
        "Land",
        "Stadt",
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


def test_group_summary_fact_rows_by_area_preserves_area_order_and_statuses() -> None:
    rows = [
        SUMMARY_MODULE.SummaryFactsRow(
            "Kernprofil", "Rolle", "Data Engineer", "Jobspec", "Vollständig"
        ),
        SUMMARY_MODULE.SummaryFactsRow(
            "Interview", "Interviewphasen", "Nicht beantwortet", "Intake", "Fehlend"
        ),
        SUMMARY_MODULE.SummaryFactsRow(
            "Kernprofil", "Stadt", "Berlin", "Jobspec", "Teilweise"
        ),
    ]

    grouped = SUMMARY_MODULE._group_summary_fact_rows_by_area(rows)

    assert [(area, [row.feld for row in area_rows]) for area, area_rows in grouped] == [
        ("Kernprofil", ["Rolle", "Stadt"]),
        ("Interview", ["Interviewphasen"]),
    ]
    assert [row.status for _, area_rows in grouped for row in area_rows] == [
        "Vollständig",
        "Teilweise",
        "Fehlend",
    ]


def test_render_summary_facts_column_overview_groups_multiple_area_columns(
    monkeypatch,
) -> None:
    class _FakeColumn:
        def __enter__(self) -> "_FakeColumn":
            return self

        def __exit__(self, *_: object) -> Literal[False]:
            return False

    class _FakeStreamlit:
        def __init__(self) -> None:
            self.columns_calls: list[int] = []
            self.markdown_calls: list[str] = []
            self.write_calls: list[str] = []
            self.caption_calls: list[str] = []
            self.info_calls: list[str] = []

        def markdown(self, text: str, **_: Any) -> None:
            self.markdown_calls.append(text)

        def columns(self, count: int, **_: Any) -> list[_FakeColumn]:
            self.columns_calls.append(count)
            return [_FakeColumn() for _ in range(count)]

        def container(self, **_: Any) -> _NoopContext:
            return _NoopContext()

        def write(self, text: str, **_: Any) -> None:
            self.write_calls.append(text)

        def caption(self, text: str, **_: Any) -> None:
            self.caption_calls.append(text)

        def info(self, text: str, **_: Any) -> None:
            self.info_calls.append(text)

    fake_st = _FakeStreamlit()
    vm = SimpleNamespace(
        fact_rows=[
            SUMMARY_MODULE.SummaryFactsRow(
                "Kernprofil", "Rolle", "Data Engineer", "Jobspec", "Vollständig"
            ),
            SUMMARY_MODULE.SummaryFactsRow(
                "Interview",
                "Interviewphasen",
                "Nicht beantwortet",
                "Intake-Antwort",
                "Fehlend",
            ),
            SUMMARY_MODULE.SummaryFactsRow(
                "Benefits", "Benefits", "Mentoring", "Auswahl", "Teilweise"
            ),
            SUMMARY_MODULE.SummaryFactsRow(
                "Unternehmen", "Firma", "", "Intake-Antwort", "Fehlend"
            ),
        ]
    )

    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)
    monkeypatch.setattr(SUMMARY_MODULE, "_render_esco_coverage_kpis", lambda: None)

    SUMMARY_MODULE._render_summary_facts_column_overview(vm)

    assert fake_st.columns_calls == [3, 1]
    assert "**Kernprofil**" in fake_st.markdown_calls
    assert "**Interview**" in fake_st.markdown_calls
    assert "**Benefits**" in fake_st.markdown_calls
    assert "**Unternehmen**" in fake_st.markdown_calls
    assert "Nicht beantwortet" in fake_st.write_calls
    assert fake_st.caption_calls == [
        "Vollständig · Quelle: Jobspec",
        "Fehlend · Quelle: Intake-Antwort",
        "Teilweise · Quelle: Auswahl",
        "Fehlend · Quelle: Intake-Antwort",
    ]


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


def test_build_esco_coverage_kpis_contains_expected_values() -> None:
    kpis = SUMMARY_MODULE._build_esco_coverage_kpis(
        metrics={
            "essential_total": 3,
            "optional_total": 2,
            "essential_covered": 2,
            "optional_covered": 1,
        },
        unmapped_requirements_count=2,
    )

    assert kpis == [
        ("Anforderungen", 5),
        ("ESCO unterstützt", 3),
        ("Nicht gemappt", 2),
        ("Quelle vorhanden", 5),
    ]


def test_render_summary_facts_section_uses_esco_shared_fields_for_coverage(
    monkeypatch,
) -> None:
    class _FakeColumn:
        def __init__(self, metrics_calls: list[tuple[str, str]]):
            self.metrics_calls = metrics_calls

        def metric(self, label: str, value: str, **_: object) -> None:
            self.metrics_calls.append((label, value))

    class _FakeStreamlit:
        def __init__(self, session_state: dict[str, object]):
            self.session_state = session_state
            self.info_calls: list[str] = []
            self.caption_calls: list[str] = []
            self.markdown_calls: list[str] = []
            self.metric_calls: list[tuple[str, str]] = []

        def markdown(self, text: str, **_: object) -> None:
            self.markdown_calls.append(text)

        def info(self, text: str, **_: object) -> None:
            self.info_calls.append(text)

        def caption(self, text: str, **_: object) -> None:
            self.caption_calls.append(text)

        def columns(self, count: int, **_: object) -> list[_FakeColumn]:
            return [_FakeColumn(self.metric_calls) for _ in range(count)]

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
        ),
        fact_rows=[],
        artifacts=_artifacts(),
    )

    SUMMARY_MODULE._render_summary_facts_section(vm)

    assert fake_st.info_calls == []
    assert fake_st.metric_calls == [
        ("Anforderungen", "3"),
        ("ESCO unterstützt", "2"),
        ("Nicht gemappt", "1"),
        ("Quelle vorhanden", "3"),
    ]
