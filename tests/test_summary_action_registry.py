from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Literal

from constants import FactKey, SSKey


SUMMARY_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "08_summary.py"
SPEC = spec_from_file_location("wizard_pages.page_08_summary_actions", SUMMARY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load summary page module")
SUMMARY_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(SUMMARY_MODULE)  # type: ignore[attr-defined]


class _NoopContext:
    def __enter__(self) -> "_NoopContext":
        return self

    def __exit__(self, *_: object) -> Literal[False]:
        return False


class _FakeStreamlit:
    def __init__(self, session_state: dict[str, Any], *, button_result: bool = False):
        self.session_state = session_state
        self.button_result = button_result
        self.last_button_kwargs: dict[str, Any] = {}

    def container(self, **_: Any) -> _NoopContext:
        return _NoopContext()

    def markdown(self, *_: Any, **__: Any) -> None:
        return None

    def caption(self, *_: Any, **__: Any) -> None:
        return None

    def write(self, *_: Any, **__: Any) -> None:
        return None

    def button(self, label: str, **kwargs: Any) -> bool:
        self.last_button_kwargs = {"label": label, **kwargs}
        return self.button_result


class _LauncherFakeStreamlit:
    def __init__(self, session_state: dict[str, Any]):
        self.session_state = session_state
        self.button_labels: list[str] = []

    def container(self, **_: Any) -> _NoopContext:
        return _NoopContext()

    def markdown(self, *_: Any, **__: Any) -> None:
        return None

    def caption(self, *_: Any, **__: Any) -> None:
        return None

    def button(self, label: str, **__: Any) -> bool:
        self.button_labels.append(label)
        return False


class _PipelineFakeStreamlit:
    def __init__(self, session_state: dict[str, Any], *, clicked_label: str):
        self.session_state = session_state
        self.clicked_label = clicked_label
        self.rerun_count = 0

    def columns(self, spec: Any, **_kwargs: Any) -> list[_NoopContext]:
        count = spec if isinstance(spec, int) else len(spec)
        return [_NoopContext() for _ in range(count)]

    def container(self, **_: Any) -> _NoopContext:
        return _NoopContext()

    def markdown(self, *_: Any, **__: Any) -> None:
        return None

    def caption(self, *_: Any, **__: Any) -> None:
        return None

    def button(self, label: str, **__: Any) -> bool:
        return label == self.clicked_label

    def rerun(self) -> None:
        self.rerun_count += 1


def test_build_action_registry_contains_expected_actions_and_requirements() -> None:
    action_registry = SUMMARY_MODULE._build_action_registry(
        resolved_brief_model="gpt-5-mini",
        resolved_job_ad_model="gpt-4o-mini",
        resolved_hr_sheet_model="gpt-5-nano",
        resolved_fach_sheet_model="gpt-5",
        resolved_boolean_search_model="gpt-5-mini",
        resolved_employment_contract_model="o3-mini",
        follow_up_requirement_check=lambda: (
            True,
            "Aktueller Recruiting Brief vorhanden.",
        ),
        generate_recruiting_brief=lambda: None,
        generate_job_ad=lambda: None,
        generate_interview_prep_hr=lambda: None,
        generate_interview_prep_fach=lambda: None,
        generate_boolean_search=lambda: None,
        generate_employment_contract=lambda: None,
    )

    assert [action["id"] for action in action_registry] == [
        "brief",
        "job_ad",
        "interview_hr",
        "interview_fach",
        "boolean_search",
        "employment_contract",
    ]
    assert action_registry[0]["requires"] == (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN)
    assert action_registry[1]["requires"] == (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN)
    assert action_registry[2]["requires"] == (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN)
    assert action_registry[2]["generator_fn"] is not None
    assert action_registry[3]["requires"] == (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN)
    assert action_registry[3]["generator_fn"] is not None
    assert action_registry[4]["requires"] == (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN)
    assert action_registry[4]["generator_fn"] is not None
    assert action_registry[5]["requires"] == (SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN)
    assert action_registry[5]["generator_fn"] is not None


def test_record_artifact_generated_with_fact_usage_marks_evidence() -> None:
    session_state: dict[str, Any] = {
        SSKey.INTAKE_FACT_EVIDENCE.value: {
            FactKey.ROLE_JOB_TITLE.value: {
                "source_type": "manual",
                "used_by_artifacts": [],
                "updated_at": "old",
            }
        }
    }

    SUMMARY_MODULE._record_artifact_generated_with_fact_usage(
        session_state,
        artifact_id="job_ad",
        cache_hit=False,
        mode="test",
    )

    assert session_state[SSKey.USAGE_EVENTS.value][0]["event_type"] == (
        "artifact_generated"
    )
    assert session_state[SSKey.USAGE_EVENTS.value][0]["metadata"] == {
        "artifact_id": "job_ad",
        "cache_hit": False,
        "mode": "test",
    }
    evidence = session_state[SSKey.INTAKE_FACT_EVIDENCE.value][
        FactKey.ROLE_JOB_TITLE.value
    ]
    assert evidence["used_by_artifacts"] == ["job_ad"]
    assert evidence["updated_at"] != "old"


def test_build_enrichment_timing_rows_sorts_by_duration() -> None:
    session_state: dict[str, Any] = {
        SSKey.USAGE_EVENTS.value: [
            {
                "event_type": "enrichment_timed",
                "metadata": {
                    "stage": "extract_job_ad",
                    "path": "landing_phase_a",
                    "status": "success",
                    "duration_ms": 120,
                    "cache_hit": False,
                },
            },
            {
                "event_type": "artifact_generated",
                "metadata": {"artifact_id": "brief"},
            },
            {
                "event_type": "enrichment_timed",
                "metadata": {
                    "stage": "esco_rag",
                    "path": "skills",
                    "status": "success",
                    "duration_ms": 250,
                    "result_count": 4,
                },
            },
        ]
    }

    rows = SUMMARY_MODULE._build_enrichment_timing_rows(session_state)

    assert [row["Stage"] for row in rows] == ["esco_rag", "extract_job_ad"]
    assert rows[0]["Dauer (ms)"] == 250
    assert rows[0]["Cache"] is None
    assert rows[0]["Treffer"] == 4
    assert rows[1]["Cache"] is False
    assert rows[1]["Treffer"] is None


def test_render_action_card_returns_false_when_requirements_missing(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlit(session_state={})
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    action = {
        "id": "brief",
        "title": "Recruiting Brief",
        "benefit": "desc",
        "cta_label": "Generate",
        "blocked_cta_label": None,
        "requires": (SSKey.JOB_EXTRACT,),
        "requirement_text": "Jobspec vorhanden",
        "requirement_check_fn": None,
        "generator_fn": lambda: None,
        "result_key": SSKey.BRIEF,
        "input_hints": ("hint",),
        "input_renderer": None,
    }
    triggered = SUMMARY_MODULE._render_action_card(action)

    assert triggered is False
    assert fake_st.last_button_kwargs["disabled"] is True


def test_render_action_card_renders_available_fach_action(monkeypatch) -> None:
    fake_st = _FakeStreamlit(
        session_state={
            SSKey.BRIEF.value: {"one_liner": "x"},
            SSKey.INTERVIEW_PREP_FACH.value: None,
        }
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    action = {
        "id": "interview_fach",
        "title": "Fachbereich Sheet",
        "benefit": "desc",
        "cta_label": "Generate",
        "blocked_cta_label": None,
        "requires": (SSKey.BRIEF,),
        "requirement_text": "Aktueller Brief erforderlich",
        "requirement_check_fn": None,
        "generator_fn": lambda: None,
        "result_key": SSKey.INTERVIEW_PREP_FACH,
        "input_hints": (),
        "input_renderer": None,
    }
    triggered = SUMMARY_MODULE._render_action_card(action)

    assert triggered is False
    assert fake_st.last_button_kwargs["disabled"] is False


def test_render_action_card_returns_button_state_for_available_action(
    monkeypatch,
) -> None:
    fake_st = _FakeStreamlit(
        session_state={SSKey.JOB_EXTRACT.value: {"job_title": "Engineer"}},
        button_result=True,
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    action = {
        "id": "job_ad",
        "title": "Job Ad",
        "benefit": "desc",
        "cta_label": "Generate",
        "blocked_cta_label": None,
        "requires": (SSKey.JOB_EXTRACT,),
        "requirement_text": "Jobspec vorhanden",
        "requirement_check_fn": None,
        "generator_fn": lambda: None,
        "result_key": SSKey.JOB_AD_DRAFT_CUSTOM,
        "input_hints": (),
        "input_renderer": None,
    }
    triggered = SUMMARY_MODULE._render_action_card(action)

    assert triggered is True
    assert fake_st.last_button_kwargs["type"] == "primary"


def test_has_required_state_requires_all_truthy_values(monkeypatch) -> None:
    fake_st = SimpleNamespace(
        session_state={
            SSKey.JOB_EXTRACT.value: {"job_title": "Engineer"},
            SSKey.QUESTION_PLAN.value: None,
        }
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)

    assert (
        SUMMARY_MODULE._has_required_state((SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN))
        is False
    )
    fake_st.session_state[SSKey.QUESTION_PLAN.value] = {"steps": []}
    assert (
        SUMMARY_MODULE._has_required_state((SSKey.JOB_EXTRACT, SSKey.QUESTION_PLAN))
        is True
    )


def test_follow_up_actions_describe_explicit_brief_dependency() -> None:
    """Expected vs Actual: Follow-up-Eingaben verlangen explizit aktuellen Brief."""
    action_registry = SUMMARY_MODULE._build_action_registry(
        resolved_brief_model="gpt-5-mini",
        resolved_job_ad_model="gpt-4o-mini",
        resolved_hr_sheet_model="gpt-5-nano",
        resolved_fach_sheet_model="gpt-5",
        resolved_boolean_search_model="gpt-5-mini",
        resolved_employment_contract_model="o3-mini",
        follow_up_requirement_check=lambda: (
            True,
            "Aktueller Recruiting Brief vorhanden.",
        ),
        generate_recruiting_brief=lambda: None,
        generate_job_ad=lambda: None,
        generate_interview_prep_hr=lambda: None,
        generate_interview_prep_fach=lambda: None,
        generate_boolean_search=lambda: None,
        generate_employment_contract=lambda: None,
    )

    follow_up_ids = {
        "interview_hr",
        "interview_fach",
        "boolean_search",
        "employment_contract",
    }
    for action in action_registry:
        if action["id"] in follow_up_ids:
            hints = " ".join(action["input_hints"]).lower()
            assert "kein automatischer fallback" in hints
            assert "optional auto brief" not in hints
            assert (
                action["requirement_text"]
                == "Aktueller Recruiting Brief ist erforderlich"
            )
            assert action["blocked_cta_label"]


def test_render_artifact_launcher_cards_uses_artifact_specific_labels(monkeypatch) -> None:
    fake_st = _LauncherFakeStreamlit(
        session_state={
            SSKey.JOB_EXTRACT.value: {"job_title": "Engineer"},
            SSKey.QUESTION_PLAN.value: {"questions": []},
        }
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)
    monkeypatch.setattr(SUMMARY_MODULE, "_has_required_state", lambda _requires: True)
    monkeypatch.setattr(
        SUMMARY_MODULE,
        "_get_brief_status",
        lambda **_: ("dirty", "Eingaben geändert", "Brief aktualisieren"),
    )

    action_registry = [
        {
            "id": "brief",
            "title": "Recruiting Brief",
            "benefit": "desc",
            "cta_label": "Recruiting Brief erstellen",
            "blocked_cta_label": None,
            "requires": (SSKey.JOB_EXTRACT,),
            "requirement_text": "Jobspec vorhanden",
            "requirement_check_fn": None,
            "generator_fn": lambda: None,
            "result_key": SSKey.BRIEF,
            "input_hints": (),
            "input_renderer": None,
        },
        {
            "id": "job_ad",
            "title": "Stellenanzeige",
            "benefit": "desc",
            "cta_label": "Stellenanzeige erstellen",
            "blocked_cta_label": None,
            "requires": (SSKey.JOB_EXTRACT,),
            "requirement_text": "Jobspec vorhanden",
            "requirement_check_fn": None,
            "generator_fn": lambda: None,
            "result_key": SSKey.JOB_AD_DRAFT_CUSTOM,
            "input_hints": (),
            "input_renderer": None,
        },
        {
            "id": "boolean_search",
            "title": "Boolean Search",
            "benefit": "desc",
            "cta_label": "Boolean Search erstellen",
            "blocked_cta_label": "Recruiting Brief erstellen und danach Boolean Search erstellen",
            "requires": (SSKey.JOB_EXTRACT,),
            "requirement_text": "Jobspec vorhanden",
            "requirement_check_fn": None,
            "generator_fn": lambda: None,
            "result_key": SSKey.BOOLEAN_SEARCH_STRING,
            "input_hints": (),
            "input_renderer": None,
        },
    ]

    SUMMARY_MODULE._render_artifact_launcher_cards(
        action_registry=action_registry,
        resolved_brief_model="gpt-5-mini",
    )

    assert fake_st.button_labels[0] == "Brief aktualisieren"
    assert fake_st.button_labels[1] == "Stellenanzeige erstellen"
    assert fake_st.button_labels[2] == "Boolean Search erstellen"


def test_render_artifact_launcher_cards_prefers_blocked_label_when_requirements_fail(
    monkeypatch,
) -> None:
    fake_st = _LauncherFakeStreamlit(session_state={})
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)
    monkeypatch.setattr(SUMMARY_MODULE, "_has_required_state", lambda _requires: False)

    action_registry = [
        {
            "id": "boolean_search",
            "title": "Boolean Search",
            "benefit": "desc",
            "cta_label": "Boolean Search erstellen",
            "blocked_cta_label": "Recruiting Brief erstellen und danach Boolean Search erstellen",
            "requires": (SSKey.BRIEF,),
            "requirement_text": "Aktueller Recruiting Brief ist erforderlich",
            "requirement_check_fn": None,
            "generator_fn": lambda: None,
            "result_key": SSKey.BOOLEAN_SEARCH_STRING,
            "input_hints": (),
            "input_renderer": None,
        }
    ]

    SUMMARY_MODULE._render_artifact_launcher_cards(
        action_registry=action_registry,
        resolved_brief_model="gpt-5-mini",
    )

    assert fake_st.button_labels == [
        "Recruiting Brief erstellen und danach Boolean Search erstellen"
    ]


def test_render_artifact_pipeline_click_generates_selected_artifact(monkeypatch) -> None:
    generator_calls: list[str] = []
    fake_st = _PipelineFakeStreamlit(
        session_state={
            SSKey.JOB_EXTRACT.value: {"job_title": "Engineer"},
            SSKey.QUESTION_PLAN.value: {"questions": []},
        },
        clicked_label="Stellenanzeige erstellen",
    )
    monkeypatch.setattr(SUMMARY_MODULE, "st", fake_st)
    monkeypatch.setattr(SUMMARY_MODULE, "_has_required_state", lambda _requires: True)

    action_registry = [
        {
            "id": "job_ad",
            "title": "Stellenanzeige",
            "benefit": "desc",
            "cta_label": "Stellenanzeige erstellen",
            "blocked_cta_label": None,
            "requires": (SSKey.JOB_EXTRACT,),
            "requirement_text": "Jobspec vorhanden",
            "requirement_check_fn": None,
            "generator_fn": lambda: generator_calls.append("job_ad"),
            "result_key": SSKey.JOB_AD_DRAFT_CUSTOM,
            "input_hints": (),
            "input_renderer": None,
        }
    ]

    SUMMARY_MODULE._render_artifact_pipeline(
        action_registry=action_registry,
        resolved_brief_model="gpt-5-mini",
    )

    assert generator_calls == ["job_ad"]
    assert fake_st.session_state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] == "job_ad"
    assert fake_st.rerun_count == 1
