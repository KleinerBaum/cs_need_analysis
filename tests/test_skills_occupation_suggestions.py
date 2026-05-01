from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

import pytest

from constants import SSKey
from schemas import JobAdExtract
from state import EscoAnchorStatus, EscoCoverageSnapshot

SKILLS_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "05_skills.py"
SPEC = spec_from_file_location("wizard_pages.page_05_skills", SKILLS_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load skills page module")
SKILLS_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(SKILLS_MODULE)  # type: ignore[attr-defined]


def test_extract_skill_candidates_filters_non_skill_entries() -> None:
    payload = {
        "uri": "http://data.europa.eu/esco/occupation/123",
        "type": "occupation",
        "title": "Data Engineer",
        "_embedded": {
            "hasEssentialSkill": [
                {
                    "uri": "http://data.europa.eu/esco/skill/a",
                    "preferredLabel": "Python",
                    "type": "skill",
                },
                {
                    "uri": "http://data.europa.eu/esco/skill/a",
                    "preferredLabel": "Python duplicate",
                    "type": "skill",
                },
            ]
        },
    }

    extracted = SKILLS_MODULE._extract_skill_candidates(payload)

    assert extracted == [
        {
            "uri": "http://data.europa.eu/esco/skill/a",
            "title": "Python",
            "type": "skill",
        }
    ]


def test_merge_suggested_skills_dedupes_against_existing_must_and_nice() -> None:
    merged, added_count = SKILLS_MODULE._merge_suggested_skills_by_uri(
        suggested_skills=[
            {"uri": "uri:skill:must", "title": "Existing Must", "type": "skill"},
            {"uri": "uri:skill:nice", "title": "Existing Nice", "type": "skill"},
            {"uri": "uri:skill:new", "title": "Brand New", "type": "skill"},
        ],
        must_selected=[
            {"uri": "uri:skill:must", "title": "Existing Must", "type": "skill"}
        ],
        nice_selected=[
            {"uri": "uri:skill:nice", "title": "Existing Nice", "type": "skill"}
        ],
    )

    assert added_count == 1
    assert merged == [
        {"uri": "uri:skill:must", "title": "Existing Must", "type": "skill"},
        {"uri": "uri:skill:new", "title": "Brand New", "type": "skill"},
    ]


def test_build_skill_suggestion_context_normalizes_jobspec_and_esco_titles() -> None:
    setattr(
        SKILLS_MODULE,
        "st",
        SimpleNamespace(session_state={"cs.skills.selected": ["Python"]}),
    )
    job = JobAdExtract(
        must_have_skills=[" Python ", "SQL"],
        nice_to_have_skills=["sql", "Kommunikation"],
        tech_stack=[" Airflow ", "python"],
    )

    context = SKILLS_MODULE._build_skill_suggestion_context(
        job=job,
        esco_must_selected=[{"title": "Data Modeling"}],
        esco_nice_selected=[{"title": "data modeling"}, {"title": "Stakeholder Mgmt"}],
    )

    assert context["jobspec_terms"] == ["Python", "SQL", "Kommunikation", "Airflow"]
    assert context["esco_titles"] == ["Data Modeling", "Stakeholder Mgmt"]
    assert context["selected_labels"] == ["Python"]


def test_load_related_skills_returns_friendly_error_when_related_endpoint_unsupported(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyClient:
        def __init__(self) -> None:
            self.resource_related_calls = 0

        def get_occupation_detail(self, *, uri: str) -> dict[str, str]:
            return {"uri": uri}

        def supports_endpoint(self, endpoint: str) -> bool:
            assert endpoint == "resource/related"
            return False

        def get_occupation_essential_skills(
            self, *, occupation_uri: str
        ) -> dict[str, str]:
            self.resource_related_calls += 1
            return {"uri": occupation_uri}

        def get_occupation_optional_skills(
            self, *, occupation_uri: str
        ) -> dict[str, str]:
            self.resource_related_calls += 1
            return {"uri": occupation_uri}

    dummy_client = DummyClient()
    monkeypatch.setattr(SKILLS_MODULE, "EscoClient", lambda: dummy_client)

    must, nice, error = SKILLS_MODULE._load_related_skills_from_selected_occupation(
        "uri:occupation:test"
    )

    assert must == []
    assert nice == []
    assert dummy_client.resource_related_calls == 0
    assert error is not None
    assert error.endpoint == "resource/related"
    assert error.message == SKILLS_MODULE.ESCO_RELATED_ENDPOINT_UNSUPPORTED_MESSAGE


def test_load_matrix_priors_returns_empty_when_disabled(monkeypatch) -> None:
    setattr(
        SKILLS_MODULE,
        "st",
        SimpleNamespace(session_state={"cs.esco_matrix_enabled": False}),
    )
    must, nice = SKILLS_MODULE._load_matrix_priors("uri:occ:1")
    assert must == []
    assert nice == []


def test_load_matrix_priors_updates_metadata_when_loaded(monkeypatch) -> None:
    class DummyLookup:
        metadata = SimpleNamespace(
            loaded=True, source="offline_build", version="2026.04", records=3
        )

        def candidates_for(
            self, *, occupation_uri: str, occupation_group: str | None = None
        ) -> tuple[list[dict], list[dict]]:
            assert occupation_uri == "uri:occ:1"
            assert occupation_group is None
            return ([{"uri": "uri:skill:1", "title": "Python"}], [])

    monkeypatch.setenv("ESCO_MATRIX_PATH", "/tmp/matrix.json")
    monkeypatch.setattr(SKILLS_MODULE, "load_esco_matrix", lambda _: DummyLookup())
    state = {
        "cs.esco_matrix_enabled": True,
        "cs.esco_matrix_metadata": {},
        "cs.esco_matrix_loaded": False,
    }
    setattr(SKILLS_MODULE, "st", SimpleNamespace(session_state=state))
    must, nice = SKILLS_MODULE._load_matrix_priors("uri:occ:1")
    assert len(must) == 1 and nice == []
    assert state["cs.esco_matrix_loaded"] is True
    assert state["cs.esco_matrix_metadata"]["version"] == "2026.04"


def test_load_matrix_priors_passes_occupation_group_when_provided(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class DummyLookup:
        metadata = SimpleNamespace(
            loaded=True, source="offline_build", version="2026.04", records=2
        )

        def candidates_for(
            self, *, occupation_uri: str, occupation_group: str | None = None
        ) -> tuple[list[dict], list[dict]]:
            assert occupation_uri == "uri:occ:1"
            assert occupation_group == "251"
            return (
                [{"uri": "uri:skill:must", "title": "Python", "type": "skill"}],
                [{"uri": "uri:skill:nice", "title": "Git", "type": "skill"}],
            )

    monkeypatch.setenv("ESCO_MATRIX_PATH", "/tmp/matrix.json")
    monkeypatch.setattr(SKILLS_MODULE, "load_esco_matrix", lambda _: DummyLookup())
    state = {
        "cs.esco_matrix_enabled": True,
        "cs.esco_matrix_metadata": {},
        "cs.esco_matrix_loaded": False,
    }
    setattr(SKILLS_MODULE, "st", SimpleNamespace(session_state=state))

    must, nice = SKILLS_MODULE._load_matrix_priors(
        "uri:occ:1", occupation_group="251"
    )

    assert len(must) == 1
    assert len(nice) == 1
    assert must[0]["uri"] == "uri:skill:must"
    assert nice[0]["uri"] == "uri:skill:nice"


def test_resolve_matrix_occupation_group_ignores_generic_selected_code() -> None:
    state = {
        "cs.esco_occupation_payload": {"iscoGroup": "351"},
    }
    setattr(SKILLS_MODULE, "st", SimpleNamespace(session_state=state))

    selected_group = SKILLS_MODULE._resolve_matrix_occupation_group(
        {"uri": "uri:occ:1", "code": "some-esco-code"}
    )
    payload_group = SKILLS_MODULE._resolve_matrix_occupation_group({"uri": "uri:occ:1"})

    assert selected_group == "351"
    assert payload_group == "351"


def test_resolve_matrix_occupation_group_prefers_selected_explicit_group() -> None:
    state = {
        "cs.esco_occupation_payload": {"iscoGroup": "351"},
    }
    setattr(SKILLS_MODULE, "st", SimpleNamespace(session_state=state))

    selected_group = SKILLS_MODULE._resolve_matrix_occupation_group(
        {"uri": "uri:occ:1", "occupation_group": "251"}
    )

    assert selected_group == "251"


def test_compute_matrix_coverage_snapshot_no_matrix_loaded() -> None:
    snapshot = SKILLS_MODULE._compute_matrix_coverage_snapshot(
        matrix_loaded=False,
        occupation_group="251",
        expected_must=[],
        expected_nice=[],
        confirmed_must=[],
        confirmed_nice=[],
    )

    assert snapshot["reason"] == "no_matrix_loaded"
    assert snapshot["rows"] == []


def test_compute_matrix_coverage_snapshot_missing_occupation_group() -> None:
    snapshot = SKILLS_MODULE._compute_matrix_coverage_snapshot(
        matrix_loaded=True,
        occupation_group="",
        expected_must=[],
        expected_nice=[],
        confirmed_must=[],
        confirmed_nice=[],
    )

    assert snapshot["reason"] == "occupation_group_missing"
    assert snapshot["rows"] == []


def test_compute_matrix_coverage_snapshot_missing_expected_group() -> None:
    snapshot = SKILLS_MODULE._compute_matrix_coverage_snapshot(
        matrix_loaded=True,
        occupation_group="251",
        expected_must=[],
        expected_nice=[],
        confirmed_must=[],
        confirmed_nice=[],
    )

    assert snapshot["reason"] == "missing_expected_group"
    assert snapshot["rows"] == []


def test_compute_matrix_coverage_rows_marks_covered_and_partial() -> None:
    rows = SKILLS_MODULE._compute_matrix_coverage_rows(
        occupation_group="251",
        expected_must=[
            {
                "uri": "uri:skill:a",
                "title": "Python",
                "skill_group_uri": "uri:group:core",
                "skill_group_id": "group-core",
                "skill_group_label": "Core",
                "share_percent": 60.0,
            },
            {
                "uri": "uri:skill:b",
                "title": "SQL",
                "skill_group_uri": "uri:group:core",
                "skill_group_id": "group-core",
                "skill_group_label": "Core",
                "share_percent": 60.0,
            },
        ],
        expected_nice=[
            {
                "uri": "uri:skill:c",
                "title": "Git",
                "skill_group_uri": "uri:group:collab",
                "skill_group_id": "group-collab",
                "skill_group_label": "Collaboration",
                "share_percent": 25.0,
            }
        ],
        confirmed_must=[{"uri": "uri:skill:a", "title": "Python"}],
        confirmed_nice=[{"uri": "uri:skill:c", "title": "Git"}],
    )

    core_row = next(row for row in rows if row["skill_group_id"] == "group-core")
    collab_row = next(row for row in rows if row["skill_group_id"] == "group-collab")
    assert core_row["coverage_status"] == "partial"
    assert core_row["expected_share_percent"] == 60.0
    assert core_row["matched_skill_uris"] == ["uri:skill:a"]
    assert collab_row["coverage_status"] == "covered"




def test_compute_matrix_coverage_rows_matches_group_when_uri_misses() -> None:
    rows = SKILLS_MODULE._compute_matrix_coverage_rows(
        occupation_group="251",
        expected_must=[
            {
                "uri": "uri:skill:expected-only",
                "title": "Expected only",
                "skill_group_id": "group-core",
                "skill_group_label": "Core",
                "share_percent": 60.0,
            }
        ],
        expected_nice=[],
        confirmed_must=[
            {
                "uri": "uri:skill:confirmed-other",
                "title": "Confirmed other",
                "skill_group_id": "group-core",
            }
        ],
        confirmed_nice=[],
    )

    assert rows[0]["coverage_status"] == "covered"
    assert rows[0]["match_basis"] == "group"
    assert rows[0]["matched_skill_uris"] == ["uri:skill:confirmed-other"]


def test_compute_matrix_coverage_rows_group_match_avoids_false_missing() -> None:
    rows = SKILLS_MODULE._compute_matrix_coverage_rows(
        occupation_group="251",
        expected_must=[
            {
                "uri": "uri:skill:a",
                "title": "Python",
                "skill_group_uri": "uri:group:core",
                "skill_group_id": "group-core",
                "skill_group_label": "Core",
                "share_percent": 60.0,
            },
            {
                "uri": "uri:skill:b",
                "title": "SQL",
                "skill_group_uri": "uri:group:core",
                "skill_group_id": "group-core",
                "skill_group_label": "Core",
                "share_percent": 60.0,
            },
        ],
        expected_nice=[],
        confirmed_must=[
            {
                "uri": "uri:skill:other",
                "title": "Other",
                "skill_group_uri": "uri:group:core",
                "skill_group_id": "group-core",
            }
        ],
        confirmed_nice=[],
    )

    assert rows[0]["coverage_status"] == "partial"
    assert rows[0]["coverage_status"] != "missing"
    assert rows[0]["match_basis"] == "group"

def test_compute_matrix_coverage_rows_marks_overrepresented_custom_group() -> None:
    rows = SKILLS_MODULE._compute_matrix_coverage_rows(
        occupation_group="251",
        expected_must=[],
        expected_nice=[],
        confirmed_must=[
            {
                "uri": "uri:skill:x",
                "title": "Custom X",
                "skill_group_id": "group-custom",
                "skill_group_label": "Custom Group",
                "matrix_bucket": "must",
            }
        ],
        confirmed_nice=[],
    )

    assert len(rows) == 1
    assert rows[0]["coverage_status"] == "overrepresented"
    assert rows[0]["matrix_bucket"] == "must"
    assert rows[0]["skill_group_id"] == "group-custom"
    assert rows[0]["matched_skill_uris"] == ["uri:skill:x"]


def test_render_unmapped_term_workflow_serializes_canonical_retry_and_bucket() -> None:
    state = {
        SSKey.ESCO_UNMAPPED_TERM_ACTIONS.value: {},
        SSKey.ESCO_UNMAPPED_REQUIREMENT_TERMS.value: ["PySpark"],
        SSKey.ESCO_CONFIG.value: {"data_source_mode": "api_live"},
        "skills.unresolved.pyspark.retry_map": {
            "uri": "uri:skill:pyspark",
            "title": "Apache Spark",
        },
    }

    class DummySt:
        session_state = state

        @staticmethod
        def markdown(*args, **kwargs):
            return None

        @staticmethod
        def caption(*args, **kwargs):
            return None

        @staticmethod
        def selectbox(*args, **kwargs):
            return "retry_search"

        @staticmethod
        def radio(*args, **kwargs):
            return "de"

    setattr(SKILLS_MODULE, "st", DummySt)
    setattr(SKILLS_MODULE, "render_esco_picker_card", lambda *args, **kwargs: None)

    SKILLS_MODULE._render_unmapped_term_workflow(["PySpark"])

    decisions = state[SSKey.ESCO_UNRESOLVED_TERM_DECISIONS.value]
    assert decisions == [
        {
            "raw_term": "PySpark",
            "action": "retry_search",
            "mapped_uri": "uri:skill:pyspark",
            "mapped_title": "Apache Spark",
            "bucket": "must",
            "source_mode": "api_live",
        }
    ]


def test_skills_source_block_warns_when_anchor_confirmed_but_payload_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(SKILLS_MODULE, "render_output_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(SKILLS_MODULE, "_build_skills_source_view_data", lambda **kwargs: ([], [], [], [], [], []))
    monkeypatch.setattr(SKILLS_MODULE, "render_compare_adopt_intro", lambda *args, **kwargs: None)
    monkeypatch.setattr(SKILLS_MODULE, "_render_skills_source_columns", lambda **kwargs: (False, False))
    monkeypatch.setattr(SKILLS_MODULE, "_resolve_matrix_occupation_group", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(SKILLS_MODULE, "_render_matrix_coverage_section", lambda *args, **kwargs: None)
    monkeypatch.setattr(SKILLS_MODULE, "_render_confirmed_selection_block", lambda *args, **kwargs: None)
    monkeypatch.setattr(SKILLS_MODULE, "get_current_ui_mode", lambda: "standard")
    monkeypatch.setattr(
        SKILLS_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.ESCO_SKILLS_SELECTED_MUST.value: [],
                SSKey.ESCO_SKILLS_SELECTED_NICE.value: [],
            },
            warning=lambda message: calls.append(("warning", message)),
            info=lambda message: calls.append(("info", message)),
            caption=lambda *_args, **_kwargs: None,
        ),
    )

    SKILLS_MODULE._render_skills_source_comparison_block(
        job=JobAdExtract(),
        selected_occupation=None,
        coverage_snapshot=EscoCoverageSnapshot("", [], [], [], 0, 0, 0, 0),
        show_esco_sections=True,
        esco_anchor_status=EscoAnchorStatus(True, None, "anchor_confirmed_missing_payload"),
    )

    assert any(kind == "warning" and "erneut synchronisieren" in msg for kind, msg in calls)
    assert not any("Keine ESCO Occupation ausgewählt." in msg for _, msg in calls)


def test_skills_source_block_does_not_show_missing_occupation_message_when_payload_present(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(SKILLS_MODULE, "render_output_header", lambda *args, **kwargs: None)
    monkeypatch.setattr(SKILLS_MODULE, "_build_skills_source_view_data", lambda **kwargs: ([], [], [], [], [], []))
    monkeypatch.setattr(SKILLS_MODULE, "render_compare_adopt_intro", lambda *args, **kwargs: None)
    monkeypatch.setattr(SKILLS_MODULE, "_render_skills_source_columns", lambda **kwargs: (False, False))
    monkeypatch.setattr(SKILLS_MODULE, "_resolve_matrix_occupation_group", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(SKILLS_MODULE, "_render_matrix_coverage_section", lambda *args, **kwargs: None)
    monkeypatch.setattr(SKILLS_MODULE, "_render_confirmed_selection_block", lambda *args, **kwargs: None)
    monkeypatch.setattr(SKILLS_MODULE, "get_current_ui_mode", lambda: "standard")
    monkeypatch.setattr(
        SKILLS_MODULE,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.ESCO_SKILLS_SELECTED_MUST.value: [],
                SSKey.ESCO_SKILLS_SELECTED_NICE.value: [],
            },
            warning=lambda message: calls.append(("warning", message)),
            info=lambda message: calls.append(("info", message)),
            caption=lambda *_args, **_kwargs: None,
        ),
    )

    SKILLS_MODULE._render_skills_source_comparison_block(
        job=JobAdExtract(),
        selected_occupation={"uri": "uri:occ:1", "title": "Data Engineer", "type": "occupation"},
        coverage_snapshot=EscoCoverageSnapshot("uri:occ:1", [], [], [], 0, 0, 0, 0),
        show_esco_sections=True,
        esco_anchor_status=EscoAnchorStatus(True, {"uri": "uri:occ:1", "title": "Data Engineer", "type": "occupation"}, "anchor_confirmed_with_payload"),
    )

    assert not any("Keine ESCO Occupation ausgewählt." in msg for _, msg in calls)
