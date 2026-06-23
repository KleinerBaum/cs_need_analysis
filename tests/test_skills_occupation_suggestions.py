from __future__ import annotations

from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from types import SimpleNamespace

import pytest

from constants import SSKey
from esco_client import (
    ESCO_RELATED_ENDPOINT_UNSUPPORTED_MESSAGE,
    extract_skill_candidates,
    load_related_occupation_skill_suggestions,
)
from schemas import JobAdExtract
from state import EscoAnchorStatus

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


def test_extract_skill_candidates_service_filters_non_skill_entries() -> None:
    payload = {
        "_embedded": {
            "hasEssentialSkill": [
                {
                    "uri": "http://data.europa.eu/esco/skill/a",
                    "preferredLabel": "Python",
                    "type": "skill",
                },
                {
                    "uri": "http://data.europa.eu/esco/occupation/1",
                    "preferredLabel": "Data Engineer",
                    "type": "occupation",
                },
            ]
        }
    }

    assert extract_skill_candidates(payload) == [
        {
            "uri": "http://data.europa.eu/esco/skill/a",
            "title": "Python",
            "type": "skill",
        }
    ]


def test_load_related_occupation_skill_suggestions_service_uses_client_payloads() -> None:
    class DummyClient:
        def get_occupation_detail(self, *, uri: str) -> dict[str, str]:
            assert uri == "uri:occupation:test"
            return {"uri": uri}

        def supports_endpoint(self, endpoint: str) -> bool:
            assert endpoint == "resource/related"
            return True

        def get_occupation_essential_skills(
            self, *, occupation_uri: str
        ) -> dict[str, object]:
            assert occupation_uri == "uri:occupation:test"
            return {
                "_embedded": {
                    "hasEssentialSkill": [
                        {
                            "uri": "uri:skill:python",
                            "preferredLabel": "Python",
                            "type": "skill",
                        }
                    ]
                }
            }

        def get_occupation_optional_skills(
            self, *, occupation_uri: str
        ) -> dict[str, object]:
            assert occupation_uri == "uri:occupation:test"
            return {
                "_embedded": {
                    "hasOptionalSkill": [
                        {
                            "uri": "uri:skill:git",
                            "preferredLabel": "Git",
                            "type": "skill",
                        }
                    ]
                }
            }

    must, nice, error = load_related_occupation_skill_suggestions(
        "uri:occupation:test",
        client=DummyClient(),
    )

    assert error is None
    assert must == [{"uri": "uri:skill:python", "title": "Python", "type": "skill"}]
    assert nice == [{"uri": "uri:skill:git", "title": "Git", "type": "skill"}]


def test_load_related_occupation_skill_suggestions_service_handles_unsupported_endpoint() -> None:
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

    must, nice, error = load_related_occupation_skill_suggestions(
        "uri:occupation:test",
        client=dummy_client,
    )

    assert must == []
    assert nice == []
    assert dummy_client.resource_related_calls == 0
    assert error is not None
    assert error.endpoint == "resource/related"
    assert error.message == ESCO_RELATED_ENDPOINT_UNSUPPORTED_MESSAGE


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


def test_merge_suggested_skills_dedupes_by_normalized_title_when_uri_differs() -> None:
    merged, added_count = SKILLS_MODULE._merge_suggested_skills_by_uri(
        suggested_skills=[
            {"uri": "uri:skill:duplicate", "title": "python", "type": "skill"},
            {"uri": "uri:skill:new", "title": "Data Contracts", "type": "skill"},
        ],
        must_selected=[{"uri": "uri:skill:python", "title": "Python", "type": "skill"}],
        nice_selected=[],
    )

    assert added_count == 1
    assert merged == [
        {"uri": "uri:skill:python", "title": "Python", "type": "skill"},
        {"uri": "uri:skill:new", "title": "Data Contracts", "type": "skill"},
    ]


def test_dedupe_selected_skills_across_buckets_uses_uri_and_normalized_label() -> None:
    must, nice = SKILLS_MODULE._dedupe_selected_skills_across_buckets(
        must_selected=[
            {"uri": "uri:skill:python", "title": "Python"},
            {"uri": "uri:skill:sql", "title": "SQL"},
        ],
        nice_selected=[
            {"uri": "uri:skill:python", "title": "Python duplicate URI"},
            {"uri": "uri:skill:other-python", "title": " python "},
            {"uri": "uri:skill:git", "title": "Git"},
        ],
    )

    assert must == [
        {"uri": "uri:skill:python", "title": "Python"},
        {"uri": "uri:skill:sql", "title": "SQL"},
    ]
    assert nice == [{"uri": "uri:skill:git", "title": "Git"}]


def test_render_skill_action_row_does_not_emit_per_row_source_caption() -> None:
    class DummyColumn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummyStreamlit:
        def __init__(self) -> None:
            self.session_state = {SSKey.SKILLS_SELECTED.value: []}
            self.captions: list[str] = []

        def columns(self, spec):
            return [DummyColumn(), DummyColumn(), DummyColumn(), DummyColumn()]

        def markdown(self, *args, **kwargs) -> None:
            return None

        def caption(self, value: str) -> None:
            self.captions.append(value)

        def button(self, *args, **kwargs) -> bool:
            return False

    dummy_st = DummyStreamlit()
    setattr(SKILLS_MODULE, "st", dummy_st)

    SKILLS_MODULE._render_skill_action_row(
        label="Python",
        source="ESCO",
        key_prefix="test.skill",
        show_status_caption=True,
    )

    assert dummy_st.captions == []


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


def test_cycle_free_skill_selection_tracks_status_and_legacy_labels(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = {
        SSKey.SKILLS_SELECTED.value: [],
        SSKey.SKILLS_SELECTED_STATUS.value: {},
    }
    monkeypatch.setattr(SKILLS_MODULE, "st", SimpleNamespace(session_state=state))

    SKILLS_MODULE._cycle_skill_selection("Python", "", "AI", "Must-have")
    assert state[SSKey.SKILLS_SELECTED.value] == ["Python"]
    assert state[SSKey.SKILLS_SELECTED_STATUS.value]["label:python"]["status"] == "nice"

    SKILLS_MODULE._cycle_skill_selection("Python", "", "AI", "Must-have")
    assert state[SSKey.SKILLS_SELECTED.value] == ["Python"]
    assert state[SSKey.SKILLS_SELECTED_STATUS.value]["label:python"]["status"] == "must"

    SKILLS_MODULE._cycle_skill_selection("Python", "", "AI", "Must-have")
    assert state[SSKey.SKILLS_SELECTED.value] == []
    assert state[SSKey.SKILLS_SELECTED_STATUS.value] == {}


def test_cycle_esco_skill_selection_moves_between_nice_must_and_removed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = {
        SSKey.SKILLS_SELECTED.value: [],
        SSKey.SKILLS_SELECTED_STATUS.value: {},
        SSKey.ESCO_SKILLS_SELECTED_MUST.value: [],
        SSKey.ESCO_SKILLS_SELECTED_NICE.value: [],
        SSKey.ESCO_SKILLS_REMOVED.value: [],
        SSKey.ESCO_CONFIRMED_ESSENTIAL_SKILLS.value: [],
        SSKey.ESCO_CONFIRMED_OPTIONAL_SKILLS.value: [],
    }
    monkeypatch.setattr(SKILLS_MODULE, "st", SimpleNamespace(session_state=state))
    monkeypatch.setattr(SKILLS_MODULE, "sync_esco_shared_state", lambda: None)

    SKILLS_MODULE._cycle_skill_selection(
        "Datenmodellierung", "uri:skill:1", "ESCO", "Must-have"
    )
    assert state[SSKey.ESCO_SKILLS_SELECTED_NICE.value] == [
        {
            "uri": "uri:skill:1",
            "title": "Datenmodellierung",
            "type": "skill",
            "relation": "hasOptionalSkill",
            "source": "ESCO",
            "group_hint": "Must-have",
        }
    ]
    assert state[SSKey.ESCO_SKILLS_SELECTED_MUST.value] == []

    SKILLS_MODULE._cycle_skill_selection(
        "Datenmodellierung", "uri:skill:1", "ESCO", "Must-have"
    )
    assert (
        state[SSKey.ESCO_SKILLS_SELECTED_MUST.value][0]["relation"]
        == "hasEssentialSkill"
    )
    assert state[SSKey.ESCO_SKILLS_SELECTED_NICE.value] == []

    SKILLS_MODULE._cycle_skill_selection(
        "Datenmodellierung", "uri:skill:1", "ESCO", "Must-have"
    )
    assert state[SSKey.ESCO_SKILLS_SELECTED_MUST.value] == []
    assert state[SSKey.ESCO_SKILLS_SELECTED_NICE.value] == []
    assert state[SSKey.ESCO_SKILLS_REMOVED.value] == ["uri:skill:1"]

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


def test_bulk_unmapped_term_action_only_fills_undecided_terms() -> None:
    actions = {
        "Kafka": {
            "raw_term": "Kafka",
            "action": "map_to_esco_skill",
            "mapped_uri": "uri:skill:kafka",
            "mapped_title": "Apache Kafka",
            "bucket": "must",
            "source_mode": "hybrid",
        }
    }

    applied = SKILLS_MODULE._apply_bulk_unmapped_term_action(
        flagged_terms=["Kafka", "PySpark"],
        actions=actions,
        unresolved_requirement_terms={"kafka", "pyspark"},
        source_mode="hybrid",
        action="keep_free_text",
    )

    assert applied == 1
    assert actions["Kafka"]["mapped_uri"] == "uri:skill:kafka"
    assert actions["PySpark"] == {
        "raw_term": "PySpark",
        "action": "keep_free_text",
        "mapped_uri": None,
        "mapped_title": None,
        "bucket": "must",
        "source_mode": "hybrid",
    }


def test_apply_unmapped_term_mapping_updates_selection_and_keeps_raw_provenance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = {
        SSKey.SKILLS_SELECTED.value: ["PySpark"],
        SSKey.SKILLS_SELECTED_STATUS.value: {
            "label:pyspark": {
                "label": "PySpark",
                "status": "must",
                "source": "Jobspec",
                "group_hint": "Must-have",
                "uri": "",
            }
        },
        SSKey.ESCO_SKILLS_SELECTED_MUST.value: [],
        SSKey.ESCO_SKILLS_SELECTED_NICE.value: [],
        SSKey.ESCO_SKILLS_REMOVED.value: [],
        SSKey.ESCO_UNMAPPED_TERM_ACTIONS.value: {
            "PySpark": {
                "raw_term": "PySpark",
                "action": "map_to_esco_skill",
                "mapped_uri": "uri:skill:pyspark",
                "mapped_title": "Apache Spark",
                "bucket": "must",
                "source_mode": "hybrid",
            }
        },
    }
    monkeypatch.setattr(SKILLS_MODULE, "st", SimpleNamespace(session_state=state))
    monkeypatch.setattr(SKILLS_MODULE, "sync_esco_shared_state", lambda: None)
    monkeypatch.setattr(
        SKILLS_MODULE,
        "_sync_question_context_from_esco_skills",
        lambda: None,
    )

    applied = SKILLS_MODULE._apply_unmapped_term_decisions_to_selection(
        flagged_terms=["PySpark"],
    )

    assert applied >= 1
    assert state[SSKey.SKILLS_SELECTED.value] == []
    assert state[SSKey.SKILLS_SELECTED_STATUS.value] == {}
    assert state[SSKey.ESCO_SKILLS_SELECTED_MUST.value] == [
        {
            "uri": "uri:skill:pyspark",
            "title": "Apache Spark",
            "type": "skill",
            "relation": "hasEssentialSkill",
            "source": "ESCO remap",
            "group_hint": "Open term: PySpark",
            "mapped_from_terms": ["PySpark"],
            "mapped_from_term": "PySpark",
            "mapping_action": "map_to_esco_skill",
            "mapping_source_mode": "hybrid",
        }
    ]


def test_apply_keep_free_text_preserves_existing_source(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = {
        SSKey.SKILLS_SELECTED.value: ["Kafka"],
        SSKey.SKILLS_SELECTED_STATUS.value: {
            "label:kafka": {
                "label": "Kafka",
                "status": "must",
                "source": "Jobspec",
                "group_hint": "Must-have",
                "uri": "",
            }
        },
        SSKey.ESCO_UNMAPPED_TERM_ACTIONS.value: {
            "Kafka": {
                "raw_term": "Kafka",
                "action": "keep_free_text",
                "mapped_uri": None,
                "mapped_title": None,
                "bucket": "unknown",
                "source_mode": "hybrid",
            }
        },
    }
    monkeypatch.setattr(SKILLS_MODULE, "st", SimpleNamespace(session_state=state))
    monkeypatch.setattr(SKILLS_MODULE, "sync_esco_shared_state", lambda: None)
    monkeypatch.setattr(
        SKILLS_MODULE,
        "_sync_question_context_from_esco_skills",
        lambda: None,
    )

    applied = SKILLS_MODULE._apply_unmapped_term_decisions_to_selection(
        flagged_terms=["Kafka"],
    )

    assert applied == 1
    assert state[SSKey.SKILLS_SELECTED_STATUS.value]["label:kafka"] == {
        "label": "Kafka",
        "status": "nice",
        "source": "Jobspec",
        "group_hint": "Must-have",
        "uri": "",
    }


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

    class DummyColumn:
        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

    class DummySt:
        session_state = state

        @staticmethod
        def markdown(*args, **kwargs):
            return None

        @staticmethod
        def caption(*args, **kwargs):
            return None

        @staticmethod
        def columns(*args, **kwargs):
            return [DummyColumn(), DummyColumn()]

        @staticmethod
        def selectbox(label, *args, **kwargs):
            if "Bulk action" in str(label):
                return ""
            return "retry_search"

        @staticmethod
        def button(*args, **kwargs):
            return False

        @staticmethod
        def success(*args, **kwargs):
            return None

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


class _DummySpinner:
    def __enter__(self):
        return None

    def __exit__(self, exc_type, exc, traceback):
        return False


def test_maybe_autoload_esco_skills_loads_once_when_anchor_confirmed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = {
        SSKey.ESCO_SKILLS_SELECTED_MUST.value: [],
        SSKey.ESCO_SKILLS_SELECTED_NICE.value: [],
        SSKey.ESCO_MATRIX_ENABLED.value: False,
    }
    calls: list[str] = []
    monkeypatch.setattr(SKILLS_MODULE, "st", SimpleNamespace(
        session_state=state,
        spinner=lambda *_args, **_kwargs: _DummySpinner(),
        caption=lambda message, *args, **kwargs: calls.append(message),
        info=lambda *_args, **_kwargs: None,
        warning=lambda *_args, **_kwargs: None,
    ))
    monkeypatch.setattr(
        SKILLS_MODULE,
        "_load_related_skills_from_selected_occupation",
        lambda occupation_uri: (
            [{"uri": "uri:skill:python", "title": "Python", "type": "skill"}],
            [{"uri": "uri:skill:git", "title": "Git", "type": "skill"}],
            None,
        ),
    )
    monkeypatch.setattr(SKILLS_MODULE, "_load_matrix_priors", lambda *args, **kwargs: ([], []))

    matrix_must, matrix_nice, recommended_must, recommended_nice = (
        SKILLS_MODULE._maybe_autoload_esco_skill_suggestions(
            show_esco_sections=True,
            occupation_uri="uri:occ:1",
            occupation_group="251",
            selected_occupation={"uri": "uri:occ:1", "title": "Data Engineer"},
            esco_anchor_status=EscoAnchorStatus(
                True,
                {"uri": "uri:occ:1", "title": "Data Engineer"},
                "anchor_confirmed_with_payload",
            ),
        )
    )

    assert matrix_must == []
    assert matrix_nice == []
    assert state[SSKey.ESCO_SKILLS_SELECTED_MUST.value] == []
    assert state[SSKey.ESCO_SKILLS_SELECTED_NICE.value] == []
    assert recommended_must == [
        {
            "uri": "uri:skill:python",
            "title": "Python",
            "type": "skill",
            "relation": "hasEssentialSkill",
            "related_occupation_uri": "uri:occ:1",
        }
    ]
    assert recommended_nice == [
        {
            "uri": "uri:skill:git",
            "title": "Git",
            "type": "skill",
            "relation": "hasOptionalSkill",
            "related_occupation_uri": "uri:occ:1",
        }
    ]
    assert any("ESCO empfiehlt 2 Skills" in message for message in calls)


def test_maybe_autoload_esco_skills_keeps_existing_buckets_as_confirmed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = {
        SSKey.ESCO_SKILLS_SELECTED_MUST.value: [
            {"uri": "uri:skill:existing", "title": "Existing"}
        ],
        SSKey.ESCO_SKILLS_SELECTED_NICE.value: [],
        SSKey.ESCO_MATRIX_ENABLED.value: False,
    }
    load_calls = 0

    def _load(*args, **kwargs):
        nonlocal load_calls
        load_calls += 1
        return (
            [
                {"uri": "uri:skill:existing", "title": "Existing"},
                {"uri": "uri:skill:new", "title": "New"},
            ],
            [],
            None,
        )

    monkeypatch.setattr(SKILLS_MODULE, "st", SimpleNamespace(
        session_state=state,
        spinner=lambda *_args, **_kwargs: _DummySpinner(),
        caption=lambda *_args, **_kwargs: None,
        info=lambda *_args, **_kwargs: None,
        warning=lambda *_args, **_kwargs: None,
    ))
    monkeypatch.setattr(SKILLS_MODULE, "_load_related_skills_from_selected_occupation", _load)
    monkeypatch.setattr(SKILLS_MODULE, "_load_matrix_priors", lambda *args, **kwargs: ([], []))

    _matrix_must, _matrix_nice, recommended_must, recommended_nice = (
        SKILLS_MODULE._maybe_autoload_esco_skill_suggestions(
            show_esco_sections=True,
            occupation_uri="uri:occ:1",
            occupation_group="251",
            selected_occupation={"uri": "uri:occ:1", "title": "Data Engineer"},
            esco_anchor_status=EscoAnchorStatus(
                True,
                {"uri": "uri:occ:1", "title": "Data Engineer"},
                "anchor_confirmed_with_payload",
            ),
        )
    )

    assert load_calls == 1
    assert state[SSKey.ESCO_SKILLS_SELECTED_MUST.value] == [
        {"uri": "uri:skill:existing", "title": "Existing"}
    ]
    assert recommended_must == [
        {
            "uri": "uri:skill:new",
            "title": "New",
            "relation": "hasEssentialSkill",
            "related_occupation_uri": "uri:occ:1",
        }
    ]
    assert recommended_nice == []


def test_maybe_autoload_esco_skills_warns_when_anchor_payload_invalid(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, str]] = []
    monkeypatch.setattr(SKILLS_MODULE, "st", SimpleNamespace(
        session_state={},
        warning=lambda message: calls.append(("warning", message)),
        info=lambda message: calls.append(("info", message)),
    ))

    SKILLS_MODULE._maybe_autoload_esco_skill_suggestions(
        show_esco_sections=True,
        occupation_uri="",
        occupation_group="",
        selected_occupation=None,
        esco_anchor_status=EscoAnchorStatus(
            True,
            None,
            "anchor_confirmed_invalid_payload",
        ),
    )

    assert any(kind == "warning" and "erneut synchronisieren" in msg for kind, msg in calls)
    assert not any("Keine ESCO Occupation ausgewählt." in msg for _, msg in calls)
