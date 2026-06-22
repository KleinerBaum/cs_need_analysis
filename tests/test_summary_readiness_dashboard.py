from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from typing import Any, Literal
from types import SimpleNamespace

from constants import (
    AnswerType,
    FactKey,
    FactRequirementStage,
    FactResolutionStatus,
    SSKey,
    STEP_KEY_COMPANY,
    STEP_KEY_ROLE_TASKS,
    STEP_SECTION_OPEN_QUESTIONS,
    UI_PREFERENCE_CONFIDENCE_THRESHOLD,
)
from schemas import JobAdExtract, Question, QuestionPlan, QuestionStep


SUMMARY_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "08_summary.py"
SPEC = spec_from_file_location("wizard_pages.page_08_summary_readiness", SUMMARY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load summary page module")
SUMMARY_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(SUMMARY_MODULE)  # type: ignore[attr-defined]


class _NoopContext:
    def __enter__(self) -> "_NoopContext":
        return self

    def __exit__(self, *_: object) -> Literal[False]:
        return False


def _fact_row(
    bereich: str,
    feld: str,
    status: str,
    *,
    value: str = "Nicht angegeben",
    fact_key: FactKey | None = None,
    requirement_stage: FactRequirementStage = FactRequirementStage.BEFORE_SUMMARY,
    resolution_status: FactResolutionStatus | str = "",
) -> SUMMARY_MODULE.SummaryFactsRow:
    return SUMMARY_MODULE.SummaryFactsRow(
        bereich,
        feld,
        value,
        "Test",
        status,
        (
            resolution_status.value
            if isinstance(resolution_status, FactResolutionStatus)
            else str(resolution_status)
        ),
        fact_key=fact_key.value if fact_key is not None else "",
        requirement_stage=requirement_stage.value,
    )


def test_resolve_next_best_action_prefers_brief_when_not_ready(monkeypatch) -> None:
    monkeypatch.setattr(SUMMARY_MODULE, "st", SimpleNamespace(session_state={}))
    registry = [
        {
            "id": "brief",
            "title": "Brief",
            "benefit": "",
            "cta_label": "gen",
            "blocked_cta_label": None,
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "requirement_text": "",
            "requirement_check_fn": None,
            "generator_fn": lambda: None,
            "result_key": SSKey.BRIEF,
            "input_hints": (),
            "input_renderer": None,
        },
        {
            "id": "job_ad",
            "title": "Job ad",
            "benefit": "",
            "cta_label": "gen",
            "blocked_cta_label": None,
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "requirement_text": "",
            "requirement_check_fn": None,
            "generator_fn": lambda: None,
            "result_key": SSKey.JOB_AD_DRAFT_CUSTOM,
            "input_hints": (),
            "input_renderer": None,
        },
    ]
    vm = SimpleNamespace(fact_rows=[])
    action = SUMMARY_MODULE._resolve_next_best_action(
        registry, resolved_brief_model="gpt-5-mini", vm=vm
    )
    assert action is not None
    assert action["id"] == "brief"


def test_build_summary_tabs_uses_dashboard_workspace_labels(monkeypatch) -> None:
    captured_labels: list[str] = []

    class _FakeStreamlit:
        def tabs(self, labels: list[str]) -> list[_NoopContext]:
            captured_labels.extend(labels)
            return [_NoopContext() for _ in labels]

    monkeypatch.setattr(SUMMARY_MODULE, "st", _FakeStreamlit())

    tabs = SUMMARY_MODULE._build_summary_tabs()

    assert len(tabs) == 4
    assert captured_labels == ["Brief", "Fakten", "Export", "Advanced"]


def test_artifact_pipeline_status_uses_brief_freshness(monkeypatch) -> None:
    action = {
        "id": "brief",
        "title": "Recruiting Brief",
        "benefit": "",
        "cta_label": "Brief erstellen",
        "blocked_cta_label": None,
        "requires": (),
        "requirement_text": "",
        "requirement_check_fn": None,
        "generator_fn": lambda: None,
        "result_key": SSKey.BRIEF,
        "input_hints": (),
        "input_renderer": None,
    }
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "_get_brief_status",
        lambda **_kwargs: ("stale", "Recruiting Brief ist veraltet.", "Aktualisieren"),
    )

    status_key, status_label = SUMMARY_MODULE._artifact_pipeline_status(
        action,
        resolved_brief_model="gpt-5-mini",
    )

    assert (status_key, status_label) == ("stale", "Veraltet")


def test_summary_status_counts_jobspec_evidence_fact_and_missing_fact(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.UI_PREFERENCES.value: {
                    UI_PREFERENCE_CONFIDENCE_THRESHOLD: 0.6
                }
            }
        ),
    )
    job = JobAdExtract()
    intake_facts = {FactKey.ROLE_JOB_TITLE.value: "Data Engineer"}
    intake_fact_evidence = {
        FactKey.ROLE_JOB_TITLE.value: {
            "source_label": "Jobspec extraction",
            "confidence": 0.9,
        }
    }
    plan = QuestionPlan(
        steps=[
            QuestionStep(
                step_key=STEP_KEY_ROLE_TASKS,
                title_de="Role",
                questions=[
                    Question(
                        id="role_title",
                        label="Welche Rolle wird gesucht?",
                        answer_type=AnswerType.SHORT_TEXT,
                        target_path=FactKey.ROLE_JOB_TITLE.value,
                        required=True,
                        priority="core",
                    ),
                    Question(
                        id="location_country",
                        label="Für welches Land gilt die Vakanz?",
                        answer_type=AnswerType.SHORT_TEXT,
                        target_path=FactKey.COMPANY_LOCATION_COUNTRY.value,
                        required=True,
                        priority="core",
                    ),
                ],
            )
        ]
    )

    confidence_threshold = SUMMARY_MODULE._read_summary_confidence_threshold()
    meta = SUMMARY_MODULE._build_summary_meta(
        job,
        intake_facts=intake_facts,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=confidence_threshold,
    )
    status = SUMMARY_MODULE._build_summary_status(
        answers={},
        meta=meta,
        resolved_brief_model="gpt-5-mini",
        plan=plan,
        answer_meta={},
        job_extract=job,
        intake_facts=intake_facts,
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=confidence_threshold,
        fact_rows=[
            _fact_row(
                "Kernprofil",
                "Rolle",
                "Vollständig",
                value="Data Engineer",
                fact_key=FactKey.ROLE_JOB_TITLE,
                resolution_status=FactResolutionStatus.INFERRED,
            ),
            _fact_row(
                "Kernprofil",
                "Land",
                "Fehlend",
                fact_key=FactKey.COMPANY_LOCATION_COUNTRY,
                resolution_status=FactResolutionStatus.MISSING,
            ),
        ],
    )

    assert meta.role_label == "Data Engineer"
    assert meta.country_label == ""
    assert status.completion_text == "1/2 kritische Fakten geklärt"
    assert status.completion_ratio == 0.5
    assert status.readiness_percent == 50
    assert status.ready_for_follow_ups is False


def test_summary_status_treats_inferred_as_ready_but_conflicts_and_low_confidence_open(
    monkeypatch,
) -> None:
    monkeypatch.setattr(SUMMARY_MODULE, "st", SimpleNamespace(session_state={}))
    meta = SUMMARY_MODULE.SummaryMeta(
        role_label="Data Engineer",
        company_label="Acme",
        country_label="DE",
        selected_occupation_title="",
        readiness_items=[],
    )
    intake_fact_evidence = {
        FactKey.ROLE_JOB_TITLE.value: {"confidence": 0.9},
        FactKey.COMPANY_COMPANY_NAME.value: {
            "confidence": 0.95,
            "resolution_status": FactResolutionStatus.CONFLICTED.value,
        },
        FactKey.COMPANY_LOCATION_COUNTRY.value: {"confidence": 0.4},
    }

    status = SUMMARY_MODULE._build_summary_status(
        answers={},
        meta=meta,
        resolved_brief_model="gpt-5-mini",
        intake_fact_evidence=intake_fact_evidence,
        confidence_threshold=0.6,
        fact_rows=[
            _fact_row(
                "Kernprofil",
                "Rolle",
                "Vollständig",
                value="Data Engineer",
                fact_key=FactKey.ROLE_JOB_TITLE,
                resolution_status=FactResolutionStatus.INFERRED,
            ),
            _fact_row(
                "Kernprofil",
                "Unternehmen",
                "Vollständig",
                value="Acme",
                fact_key=FactKey.COMPANY_COMPANY_NAME,
                resolution_status=FactResolutionStatus.CONFLICTED,
            ),
            _fact_row(
                "Kernprofil",
                "Land",
                "Vollständig",
                value="DE",
                fact_key=FactKey.COMPANY_LOCATION_COUNTRY,
                resolution_status=FactResolutionStatus.INFERRED,
            ),
        ],
    )

    assert status.completion_text == "1/3 kritische Fakten geklärt"
    assert status.completion_ratio == 1 / 3
    assert status.readiness_percent == 33
    assert status.ready_for_follow_ups is False


def test_readiness_tab_delegates_detail_sections_to_workspaces(monkeypatch) -> None:
    class _MetricColumn:
        def __enter__(self) -> "_MetricColumn":
            return self

        def __exit__(self, *_: object) -> Literal[False]:
            return False

        def metric(self, *_args: Any, **_kwargs: Any) -> None:
            return None

    class _FakeStreamlit:
        def __init__(self) -> None:
            self.session_state: dict[str, object] = {}

        def markdown(self, *_args: Any, **_kwargs: Any) -> None:
            return None

        def container(self, **_kwargs: Any) -> _NoopContext:
            return _NoopContext()

        def columns(self, spec: Any, **_kwargs: Any) -> list[Any]:
            count = spec if isinstance(spec, int) else len(spec)
            return [_MetricColumn() for _ in range(count)]

        def caption(self, *_args: Any, **_kwargs: Any) -> None:
            return None

        def button(self, *_args: Any, **_kwargs: Any) -> bool:
            return False

        def success(self, *_args: Any, **_kwargs: Any) -> None:
            return None

    action = {
        "id": "brief",
        "title": "Recruiting Brief",
        "benefit": "desc",
        "cta_label": "Brief erstellen",
        "blocked_cta_label": None,
        "requires": (),
        "requirement_text": "Jobspec vorhanden",
        "requirement_check_fn": None,
        "generator_fn": lambda: None,
        "result_key": SSKey.BRIEF,
        "input_hints": (),
        "input_renderer": None,
    }
    vm = SimpleNamespace(
        status=SimpleNamespace(
            readiness_percent=80,
            completion_text="4/5 beantwortet",
            esco_ready=True,
            brief_state="current",
            brief_status_label="Aktuell",
        ),
        fact_rows=[],
    )
    workspace_calls: list[dict[str, object]] = []
    render_events: list[str] = []

    monkeypatch.setattr(SUMMARY_MODULE, "st", _FakeStreamlit())
    monkeypatch.setattr(
        SUMMARY_MODULE, "render_output_header", lambda *_args, **_kwargs: None
    )
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "render_next_best_action",
        lambda *_args, **_kwargs: render_events.append("next_action"),
    )
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "_render_summary_facts_column_overview",
        lambda _vm: render_events.append("facts_overview"),
    )
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "_render_readiness_dashboard_header",
        lambda _vm: render_events.append("dashboard"),
    )
    monkeypatch.setattr(SUMMARY_MODULE, "_build_missing_critical_items", lambda _vm: [])
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "_resolve_next_best_action_recommendation",
        lambda *_args, **_kwargs: SimpleNamespace(
            action=action, reason="Sicherer Startpunkt", cta_label="Brief erstellen"
        ),
    )
    monkeypatch.setattr(SUMMARY_MODULE, "_has_required_state", lambda _requires: True)

    def _capture_workspace(**kwargs: object) -> None:
        render_events.append("workspace")
        workspace_calls.append(kwargs)

    monkeypatch.setattr(
        SUMMARY_MODULE, "_render_summary_workspace_tabs", _capture_workspace
    )
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "render_brief",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("brief rendered inline")
        ),
    )
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "_render_artifact_launcher_cards",
        lambda **_kwargs: (_ for _ in ()).throw(
            AssertionError("artifact launcher rendered inline")
        ),
    )
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "_render_summary_facts_section",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            AssertionError("facts rendered inline")
        ),
    )
    results_calls: list[dict[str, object]] = []
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "_render_summary_results_workspace",
        lambda **kwargs: results_calls.append(kwargs),
    )

    SUMMARY_MODULE._render_readiness_tab(
        vm=vm,
        action_registry=[action],
        resolved_brief_model="gpt-5-mini",
        brief=SimpleNamespace(),
    )

    assert len(workspace_calls) == 1
    assert workspace_calls[0]["vm"] is vm
    assert results_calls == []
    assert render_events.index("dashboard") < render_events.index("next_action")
    assert render_events.index("dashboard") < render_events.index("workspace")


def test_resolve_next_best_action_keeps_brief_for_missing_core_context(monkeypatch) -> None:
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.JOB_EXTRACT.value: {"job_title": "Engineer"},
                SSKey.QUESTION_PLAN.value: {"steps": []},
            }
        ),
    )
    registry = [
        {
            "id": "brief",
            "title": "Recruiting Brief erstellen",
            "benefit": "",
            "cta_label": "gen",
            "blocked_cta_label": None,
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "requirement_text": "",
            "requirement_check_fn": None,
            "generator_fn": lambda: None,
            "result_key": SSKey.BRIEF,
            "input_hints": (),
            "input_renderer": None,
        },
        {
            "id": "employment_contract",
            "title": "Arbeitsvertrag erstellen",
            "benefit": "",
            "cta_label": "gen",
            "blocked_cta_label": None,
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "requirement_text": "",
            "requirement_check_fn": lambda: (True, ""),
            "generator_fn": lambda: None,
            "result_key": SSKey.EMPLOYMENT_CONTRACT_DRAFT,
            "input_hints": (),
            "input_renderer": None,
        },
    ]
    vm = SimpleNamespace(
        fact_rows=[
            _fact_row("Kernprofil", "Land", "Fehlend"),
            _fact_row("Kernprofil", "Stadt", "Fehlend"),
            _fact_row("Kernprofil", "Unternehmen", "Fehlend"),
        ]
    )
    action = SUMMARY_MODULE._resolve_next_best_action(
        registry, resolved_brief_model="gpt-5-mini", vm=vm
    )
    assert action is not None
    assert action["id"] == "brief"


def test_build_artifact_status_rows_uses_requirement_checks(monkeypatch) -> None:
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "st",
        SimpleNamespace(session_state={SSKey.JOB_EXTRACT.value: {"job_title": "x"}}),
    )
    rows = SUMMARY_MODULE._build_artifact_status_rows(
        action_registry=[
            {
                "id": "job_ad",
                "title": "Job ad",
                "benefit": "",
                "cta_label": "gen",
                "blocked_cta_label": None,
                "requires": (SSKey.JOB_EXTRACT,),
                "requirement_text": "",
                "requirement_check_fn": lambda: (False, "blocked"),
                "generator_fn": lambda: None,
                "result_key": SSKey.JOB_AD_DRAFT_CUSTOM,
                "input_hints": (),
                "input_renderer": None,
            }
        ]
    )
    assert rows[0]["Voraussetzungen"] == "Offen"


def test_build_missing_critical_items_uses_fact_rows_status_order() -> None:
    vm = SimpleNamespace(
        fact_rows=[
            _fact_row(
                "Optional",
                "optional",
                "Fehlend",
                requirement_stage=FactRequirementStage.OPTIONAL,
            ),
            _fact_row("A", "f1", "Teilweise", value="—"),
            _fact_row("B", "f2", "Fehlend", value="—"),
        ]
    )
    items = SUMMARY_MODULE._build_missing_critical_items(vm)
    assert items == ["B · f2", "A · f1"]


def test_build_summary_critical_gap_rows_ignores_optional_rows() -> None:
    vm = SimpleNamespace(
        fact_rows=[
            _fact_row(
                "Benefits",
                "Nice detail",
                "Fehlend",
                requirement_stage=FactRequirementStage.OPTIONAL,
            ),
            _fact_row("Kernprofil", "Land", "Fehlend"),
        ]
    )

    rows = SUMMARY_MODULE._build_summary_critical_gap_rows(vm)

    assert [row["Feld"] for row in rows] == ["Land"]
    assert rows[0]["Pflichtigkeit"] == "Pflicht vor Summary"


def test_build_summary_critical_gap_rows_include_deep_link_targets() -> None:
    vm = SimpleNamespace(
        fact_rows=[
            _fact_row(
                "Kernprofil",
                "Land",
                "Fehlend",
                fact_key=FactKey.COMPANY_LOCATION_COUNTRY,
            ),
        ]
    )

    rows = SUMMARY_MODULE._build_summary_critical_gap_rows(vm)

    assert rows[0]["target_step"] == STEP_KEY_COMPANY
    assert rows[0]["target_section"] == STEP_SECTION_OPEN_QUESTIONS
    assert rows[0]["target_fact_key"] == FactKey.COMPANY_LOCATION_COUNTRY.value


def test_resolve_next_best_action_recommendation_priority_order(monkeypatch) -> None:
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.JOB_EXTRACT.value: {"job_title": "Engineer", "company_name": "Acme"},
                SSKey.QUESTION_PLAN.value: {"steps": []},
                SSKey.BRIEF.value: {"role": "Engineer"},
            }
        ),
    )
    registry = [
        {
            "id": "brief",
            "title": "Recruiting Brief erstellen",
            "benefit": "",
            "cta_label": "Brief erstellen",
            "blocked_cta_label": None,
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "requirement_text": "",
            "requirement_check_fn": None,
            "generator_fn": lambda: None,
            "result_key": SSKey.BRIEF,
            "input_hints": (),
            "input_renderer": None,
        },
        {
            "id": "job_ad",
            "title": "Stellenanzeige erstellen",
            "benefit": "",
            "cta_label": "Stellenanzeige erstellen",
            "blocked_cta_label": None,
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "requirement_text": "",
            "requirement_check_fn": None,
            "generator_fn": lambda: None,
            "result_key": SSKey.JOB_AD_DRAFT_CUSTOM,
            "input_hints": (),
            "input_renderer": None,
        },
        {
            "id": "employment_contract",
            "title": "Arbeitsvertrag erstellen",
            "benefit": "",
            "cta_label": "Arbeitsvertrag erstellen",
            "blocked_cta_label": None,
            "requires": (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN),
            "requirement_text": "",
            "requirement_check_fn": lambda: (True, ""),
            "generator_fn": lambda: None,
            "result_key": SSKey.EMPLOYMENT_CONTRACT_DRAFT,
            "input_hints": (),
            "input_renderer": None,
        },
    ]

    vm_missing_core = SimpleNamespace(
        fact_rows=[_fact_row("Kernprofil", "Land", "Fehlend")]
    )
    recommendation = SUMMARY_MODULE._resolve_next_best_action_recommendation(
        registry, resolved_brief_model="gpt-5-mini", vm=vm_missing_core
    )
    assert recommendation is not None
    assert recommendation.action["id"] == "brief"
    assert recommendation.cta_label == "Unternehmenskontext vervollständigen"

    monkeypatch.setattr(
        SUMMARY_MODULE,
        "_resolve_canonical_brief_status",
        lambda resolved_brief_model: SimpleNamespace(ready_for_follow_ups=True),
    )
    vm_ready = SimpleNamespace(fact_rows=[])
    recommendation_ready = SUMMARY_MODULE._resolve_next_best_action_recommendation(
        registry, resolved_brief_model="gpt-5-mini", vm=vm_ready
    )
    assert recommendation_ready is not None
    assert recommendation_ready.action["id"] == "job_ad"
