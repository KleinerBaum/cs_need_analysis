from __future__ import annotations

from types import SimpleNamespace
from typing import cast

from constants import SSKey
from esco_client import EscoClient, EscoClientError
from wizard_pages import esco_occupation_ui


def test_extract_first_text_supports_plain_string() -> None:
    payload = {"description": "  Plain occupation description.  "}

    extracted = esco_occupation_ui._extract_first_text(payload, "description")

    assert extracted == "Plain occupation description."


def test_extract_first_text_prefers_configured_language_with_fallback() -> None:
    payload = {
        "description": {"de": "Deutsche Beschreibung", "en": "English description"}
    }

    extracted_de = esco_occupation_ui._extract_first_text(
        payload,
        "description",
        preferred_language="de",
        fallback_language="en",
    )
    extracted_en = esco_occupation_ui._extract_first_text(
        payload,
        "description",
        preferred_language="en",
        fallback_language="de",
    )

    assert extracted_de == "Deutsche Beschreibung"
    assert extracted_en == "English description"


def test_extract_first_text_handles_empty_and_mixed_structures() -> None:
    empty_payload = {"scopeNote": {"de": " ", "en": ""}}
    mixed_payload = {
        "scopeNote": [
            None,
            {"misc": ["", {"de": "Deutscher Hinweis", "en": "English hint"}]},
            {"en": "English fallback"},
        ]
    }

    empty_extracted = esco_occupation_ui._extract_first_text(
        empty_payload,
        "scopeNote",
        preferred_language="de",
        fallback_language="en",
    )
    mixed_extracted = esco_occupation_ui._extract_first_text(
        mixed_payload,
        "scopeNote",
        preferred_language="de",
        fallback_language="en",
    )

    assert empty_extracted == ""
    assert mixed_extracted == "Deutscher Hinweis"


def test_load_occupation_related_counts_uses_related_endpoint_payloads() -> None:
    class _FakeClient:
        def resource_related(self, *, uri: str, relation: str) -> dict[str, object]:
            assert uri == "http://data.europa.eu/esco/occupation/123"
            payloads = {
                "hasEssentialSkill": {
                    "_embedded": {"hasEssentialSkill": [{"uri": "skill:1"}]}
                },
                "hasOptionalSkill": {
                    "_embedded": {
                        "hasOptionalSkill": [{"uri": "skill:2"}, {"uri": "skill:3"}]
                    }
                },
                "hasEssentialKnowledge": {
                    "_embedded": {"hasEssentialKnowledge": [{"uri": "knowledge:1"}]}
                },
                "hasOptionalKnowledge": {
                    "_embedded": {
                        "hasOptionalKnowledge": [
                            {"uri": "knowledge:2"},
                            {"uri": "knowledge:3"},
                            {"uri": "knowledge:4"},
                        ]
                    }
                },
            }
            return payloads[relation]

    counts = esco_occupation_ui._load_occupation_related_counts(
        client=cast(EscoClient, _FakeClient()),
        occupation_uri="http://data.europa.eu/esco/occupation/123",
    )

    assert counts == {
        "hasEssentialSkill": 1,
        "hasOptionalSkill": 2,
        "hasEssentialKnowledge": 1,
        "hasOptionalKnowledge": 3,
    }


def test_resolve_related_counts_prefers_related_counts_over_payload_defaults() -> None:
    payload_without_relations = {"uri": "http://data.europa.eu/esco/occupation/123"}

    counts = esco_occupation_ui._resolve_related_counts(
        payload_without_relations,
        {
            "hasEssentialSkill": 4,
            "hasOptionalSkill": 5,
            "hasEssentialKnowledge": 2,
            "hasOptionalKnowledge": 1,
        },
    )

    assert counts["hasEssentialSkill"] == 4
    assert counts["hasOptionalSkill"] == 5
    assert counts["hasEssentialKnowledge"] == 2
    assert counts["hasOptionalKnowledge"] == 1


def test_load_occupation_related_counts_skips_unsupported_relations_with_400() -> None:
    class _FakeClient:
        def resource_related(self, *, uri: str, relation: str) -> dict[str, object]:
            assert uri == "http://data.europa.eu/esco/occupation/123"
            if relation == "hasOptionalKnowledge":
                raise EscoClientError(
                    400,
                    f"/resource/{relation}",
                    "unsupported relation",
                )
            payloads = {
                "hasEssentialSkill": {
                    "_embedded": {"hasEssentialSkill": [{"uri": "skill:1"}]}
                },
                "hasOptionalSkill": {
                    "_embedded": {
                        "hasOptionalSkill": [{"uri": "skill:2"}, {"uri": "skill:3"}]
                    }
                },
                "hasEssentialKnowledge": {
                    "_embedded": {"hasEssentialKnowledge": [{"uri": "knowledge:1"}]}
                },
            }
            return payloads[relation]

    counts = esco_occupation_ui._load_occupation_related_counts(
        client=cast(EscoClient, _FakeClient()),
        occupation_uri="http://data.europa.eu/esco/occupation/123",
    )

    assert counts == {
        "hasEssentialSkill": 1,
        "hasOptionalSkill": 2,
        "hasEssentialKnowledge": 1,
    }


def test_load_occupation_related_data_skips_policy_blocked_relations_without_calls(
    monkeypatch,
) -> None:
    call_relations: list[str] = []

    class _FakeClient:
        def supports_endpoint(self, endpoint: str) -> bool:
            return endpoint == "resource/related"

        def resource_related(self, *, uri: str, relation: str) -> dict[str, object]:
            assert uri == "http://data.europa.eu/esco/occupation/123"
            call_relations.append(relation)
            return {"_embedded": {relation: [{"uri": f"{relation}:1"}]}}

    monkeypatch.setattr(
        esco_occupation_ui,
        "st",
        SimpleNamespace(
            session_state={
                SSKey.ESCO_CONFIG.value: {
                    "selected_version": "v-test",
                    "api_mode": "hosted",
                }
            }
        ),
    )
    monkeypatch.setattr(
        esco_occupation_ui,
        "_OCCUPATION_RELATED_RELATION_SKIPLIST",
        {("v-test", "hosted"): ("hasOptionalKnowledge",)},
    )

    counts, labels, availability = esco_occupation_ui._load_occupation_related_data(
        client=cast(EscoClient, _FakeClient()),
        occupation_uri="http://data.europa.eu/esco/occupation/123",
    )

    assert call_relations == [
        "hasEssentialSkill",
        "hasOptionalSkill",
        "hasEssentialKnowledge",
    ]
    assert counts == {
        "hasEssentialSkill": 1,
        "hasOptionalSkill": 1,
        "hasEssentialKnowledge": 1,
    }
    assert "hasOptionalKnowledge" not in labels
    assert availability["hasOptionalKnowledge"] == "not_available"


def test_extract_skill_group_share_rows_normalizes_common_payload_shapes() -> None:
    payload = {
        "_embedded": {
            "results": [
                {"skillGroupLabel": "Group A", "share": 0.2},
                {"label": "Group B", "percentage": 40},
                {"name": "Group C", "value": "15.5"},
            ]
        }
    }

    rows = esco_occupation_ui._extract_skill_group_share_rows(payload)

    assert rows == [
        {"label": "Group B", "share_percent": 40.0},
        {"label": "Group A", "share_percent": 20.0},
        {"label": "Group C", "share_percent": 15.5},
    ]


def test_render_esco_occupation_confirmation_keeps_chart_before_title_variants(
    monkeypatch,
) -> None:
    class _DummyContext:
        def __enter__(self) -> "_DummyContext":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            del exc_type, exc, tb
            return False

    class _FakeStreamlit:
        def __init__(self) -> None:
            self.events: list[str] = []
            self.session_state = {
                f"{SSKey.ESCO_OCCUPATION_SELECTED.value}.esco_picker.options": [],
                SSKey.ESCO_OCCUPATION_SELECTED.value: {
                    "uri": "http://data.europa.eu/esco/occupation/123",
                    "title": "Data Engineer",
                },
                SSKey.ESCO_CONFIG.value: {"language": "de"},
            }

        def caption(self, _message: str) -> None:
            return None

        def info(self, _message: str) -> None:
            return None

        def warning(self, _message: str) -> None:
            return None

        def write(self, _message: object) -> None:
            return None

        def code(self, _value: str, *, language: str) -> None:
            del language
            return None

        def markdown(self, message: str, **_kwargs: object) -> None:
            self.events.append(f"markdown::{message}")

        def button(self, label: str, **_kwargs: object) -> bool:
            self.events.append(f"button::{label}")
            return False

        def toggle(self, _label: str, *, value: bool = False, **_kwargs: object) -> bool:
            return value

        def columns(self, _spec: list[int] | tuple[int, ...]) -> list[_DummyContext]:
            return [_DummyContext(), _DummyContext(), _DummyContext()]

        def container(self) -> _DummyContext:
            return _DummyContext()

        def expander(self, _label: str, **_kwargs: object) -> _DummyContext:
            return _DummyContext()

        def multiselect(self, _label: str, **_kwargs: object) -> list[str]:
            return ["de"]

        def vega_lite_chart(self, _spec: object, **_kwargs: object) -> None:
            self.events.append("chart::vega_lite")

    class _FakeClient:
        def supports_endpoint(self, endpoint: str) -> bool:
            return endpoint == "resource/occupationSkillsGroupShare"

        def get_occupation_detail(self, *, uri: str) -> dict[str, object]:
            del uri
            return {"description": {"de": "Beschreibung"}, "uri": "uri:occ:1"}

        def resource_related(self, *, uri: str, relation: str) -> dict[str, object]:
            del uri, relation
            return {"_embedded": {}}

        def get_occupation_skill_group_share(
            self, *, occupation_uri: str
        ) -> dict[str, object]:
            del occupation_uri
            return {
                "results": [
                    {"label": "Core Skills", "sharePercent": 60},
                    {"label": "Domain Skills", "sharePercent": 40},
                ]
            }

    fake_st = _FakeStreamlit()
    monkeypatch.setattr(esco_occupation_ui, "st", fake_st)
    monkeypatch.setattr(esco_occupation_ui, "EscoClient", _FakeClient)
    monkeypatch.setattr(esco_occupation_ui, "render_esco_picker_card", lambda **_kwargs: None)
    monkeypatch.setattr(esco_occupation_ui, "render_esco_explainability", lambda **_kwargs: None)

    job = SimpleNamespace(
        job_title="Data Engineer",
        seniority_level="Senior",
        department_name="Data",
        location_city="Berlin",
    )
    esco_occupation_ui.render_esco_occupation_confirmation(
        cast(object, job),
        show_start_context_panels=True,
    )

    skills_index = fake_st.events.index("markdown::#### Skills & Competences")
    chart_index = fake_st.events.index("chart::vega_lite")
    title_variant_index = fake_st.events.index("button::Titel-Varianten laden")

    assert skills_index < chart_index < title_variant_index


def test_render_esco_occupation_confirmation_skips_skill_group_request_when_unsupported(
    monkeypatch,
) -> None:
    class _DummyContext:
        def __enter__(self) -> "_DummyContext":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            del exc_type, exc, tb
            return False

    class _FakeStreamlit:
        def __init__(self) -> None:
            self.warning_messages: list[str] = []
            self.caption_messages: list[str] = []
            self.session_state = {
                f"{SSKey.ESCO_OCCUPATION_SELECTED.value}.esco_picker.options": [],
                SSKey.ESCO_OCCUPATION_SELECTED.value: {
                    "uri": "http://data.europa.eu/esco/occupation/123",
                    "title": "Data Engineer",
                },
                SSKey.ESCO_CONFIG.value: {"language": "de"},
            }

        def caption(self, message: str) -> None:
            self.caption_messages.append(message)

        def info(self, _message: str) -> None:
            return None

        def warning(self, message: str) -> None:
            self.warning_messages.append(message)

        def write(self, _message: object) -> None:
            return None

        def code(self, _value: str, *, language: str) -> None:
            del language
            return None

        def markdown(self, _message: str, **_kwargs: object) -> None:
            return None

        def button(self, _label: str, **_kwargs: object) -> bool:
            return False

        def toggle(self, _label: str, *, value: bool = False, **_kwargs: object) -> bool:
            return value

        def columns(self, _spec: list[int] | tuple[int, ...]) -> list[_DummyContext]:
            return [_DummyContext(), _DummyContext(), _DummyContext()]

        def container(self) -> _DummyContext:
            return _DummyContext()

        def expander(self, _label: str, **_kwargs: object) -> _DummyContext:
            return _DummyContext()

        def multiselect(self, _label: str, **_kwargs: object) -> list[str]:
            return ["de"]

        def vega_lite_chart(self, _spec: object, **_kwargs: object) -> None:
            return None

    class _FakeClient:
        def supports_endpoint(self, endpoint: str) -> bool:
            return endpoint != "resource/occupationSkillsGroupShare"

        def get_occupation_detail(self, *, uri: str) -> dict[str, object]:
            del uri
            return {"description": {"de": "Beschreibung"}, "uri": "uri:occ:1"}

        def resource_related(self, *, uri: str, relation: str) -> dict[str, object]:
            del uri, relation
            return {"_embedded": {}}

        def get_occupation_skill_group_share(
            self, *, occupation_uri: str
        ) -> dict[str, object]:
            raise AssertionError(f"unexpected call for {occupation_uri}")

    fake_st = _FakeStreamlit()
    monkeypatch.setattr(esco_occupation_ui, "st", fake_st)
    monkeypatch.setattr(esco_occupation_ui, "EscoClient", _FakeClient)
    monkeypatch.setattr(esco_occupation_ui, "render_esco_picker_card", lambda **_kwargs: None)
    monkeypatch.setattr(esco_occupation_ui, "render_esco_explainability", lambda **_kwargs: None)

    job = SimpleNamespace(
        job_title="Data Engineer",
        seniority_level="Senior",
        department_name="Data",
        location_city="Berlin",
    )
    esco_occupation_ui.render_esco_occupation_confirmation(
        cast(object, job),
        show_start_context_panels=True,
    )

    assert fake_st.session_state[SSKey.ESCO_OCCUPATION_SKILL_GROUP_SHARE.value] == []
    assert fake_st.warning_messages == []
    assert any(
        "Skillgruppen-Anteil ist für die aktuelle ESCO-Version/den Modus nicht verfügbar."
        in message
        for message in fake_st.caption_messages
    )


def test_render_esco_occupation_confirmation_tolerates_single_relation_400_without_repeat_calls(
    monkeypatch,
) -> None:
    class _DummyContext:
        def __enter__(self) -> "_DummyContext":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            del exc_type, exc, tb
            return False

    class _FakeStreamlit:
        def __init__(self) -> None:
            self.warning_messages: list[str] = []
            self.session_state = {
                f"{SSKey.ESCO_OCCUPATION_SELECTED.value}.esco_picker.options": [],
                SSKey.ESCO_OCCUPATION_SELECTED.value: {
                    "uri": "http://data.europa.eu/esco/occupation/123",
                    "title": "Data Engineer",
                },
                SSKey.ESCO_CONFIG.value: {"language": "de"},
            }

        def caption(self, _message: str) -> None:
            return None

        def info(self, _message: str) -> None:
            return None

        def warning(self, message: str) -> None:
            self.warning_messages.append(message)

        def write(self, _message: object) -> None:
            return None

        def code(self, _value: str, *, language: str) -> None:
            del language
            return None

        def markdown(self, _message: str, **_kwargs: object) -> None:
            return None

        def button(self, _label: str, **_kwargs: object) -> bool:
            return False

        def toggle(self, _label: str, *, value: bool = False, **_kwargs: object) -> bool:
            return value

        def columns(self, _spec: list[int] | tuple[int, ...]) -> list[_DummyContext]:
            return [_DummyContext(), _DummyContext(), _DummyContext()]

        def container(self) -> _DummyContext:
            return _DummyContext()

        def expander(self, _label: str, **_kwargs: object) -> _DummyContext:
            return _DummyContext()

        def multiselect(self, _label: str, **_kwargs: object) -> list[str]:
            return ["de"]

        def vega_lite_chart(self, _spec: object, **_kwargs: object) -> None:
            return None

    class _FakeClient:
        def __init__(self) -> None:
            self.related_calls = 0

        def supports_endpoint(self, endpoint: str) -> bool:
            return endpoint == "resource/related"

        def get_occupation_detail(self, *, uri: str) -> dict[str, object]:
            del uri
            return {"description": {"de": "Beschreibung"}, "uri": "uri:occ:1"}

        def resource_related(self, *, uri: str, relation: str) -> dict[str, object]:
            del uri
            self.related_calls += 1
            if relation == "hasOptionalKnowledge":
                raise EscoClientError(400, f"resource/related?relation={relation}", "unsupported")
            return {"_embedded": {relation: [{"uri": f"{relation}:1"}]}}

    fake_st = _FakeStreamlit()
    fake_client = _FakeClient()
    monkeypatch.setattr(esco_occupation_ui, "st", fake_st)
    monkeypatch.setattr(esco_occupation_ui, "EscoClient", lambda: fake_client)
    monkeypatch.setattr(esco_occupation_ui, "render_esco_picker_card", lambda **_kwargs: None)
    monkeypatch.setattr(esco_occupation_ui, "render_esco_explainability", lambda **_kwargs: None)

    job = SimpleNamespace(
        job_title="Data Engineer",
        seniority_level="Senior",
        department_name="Data",
        location_city="Berlin",
    )
    esco_occupation_ui.render_esco_occupation_confirmation(
        cast(object, job),
        show_start_context_panels=True,
    )

    assert fake_st.warning_messages == []
    assert fake_client.related_calls == 4
    assert fake_st.session_state[SSKey.ESCO_OCCUPATION_RELATED_COUNTS.value] == {
        "hasEssentialSkill": 1,
        "hasOptionalSkill": 1,
        "hasEssentialKnowledge": 1,
    }


def test_render_esco_occupation_confirmation_tolerates_missing_detail_payload(
    monkeypatch,
) -> None:
    class _DummyContext:
        def __enter__(self) -> "_DummyContext":
            return self

        def __exit__(self, exc_type, exc, tb) -> bool:
            del exc_type, exc, tb
            return False

    class _FakeStreamlit:
        def __init__(self) -> None:
            self.caption_messages: list[str] = []
            self.session_state = {
                f"{SSKey.ESCO_OCCUPATION_SELECTED.value}.esco_picker.options": [],
                SSKey.ESCO_OCCUPATION_SELECTED.value: {
                    "uri": "http://data.europa.eu/esco/occupation/123",
                    "title": "Data Engineer",
                },
                SSKey.ESCO_CONFIG.value: {"language": "de"},
            }

        def caption(self, message: str) -> None:
            self.caption_messages.append(message)

        def info(self, _message: str) -> None:
            return None

        def warning(self, _message: str) -> None:
            return None

        def write(self, _message: object) -> None:
            return None

        def code(self, _value: str, *, language: str) -> None:
            del language
            return None

        def markdown(self, _message: str, **_kwargs: object) -> None:
            return None

        def button(self, _label: str, **_kwargs: object) -> bool:
            return False

        def toggle(self, _label: str, *, value: bool = False, **_kwargs: object) -> bool:
            return value

        def columns(self, _spec: list[int] | tuple[int, ...]) -> list[_DummyContext]:
            return [_DummyContext(), _DummyContext(), _DummyContext()]

        def container(self) -> _DummyContext:
            return _DummyContext()

        def expander(self, _label: str, **_kwargs: object) -> _DummyContext:
            return _DummyContext()

        def multiselect(self, _label: str, **_kwargs: object) -> list[str]:
            return ["de"]

        def vega_lite_chart(self, _spec: object, **_kwargs: object) -> None:
            return None

    class _FakeClient:
        def supports_endpoint(self, endpoint: str) -> bool:
            return endpoint != "resource/occupationSkillsGroupShare"

        def get_occupation_detail(self, *, uri: str) -> None:
            del uri
            return None

        def resource_related(self, *, uri: str, relation: str) -> dict[str, object]:
            del uri, relation
            return {"_embedded": {}}

    fake_st = _FakeStreamlit()
    monkeypatch.setattr(esco_occupation_ui, "st", fake_st)
    monkeypatch.setattr(esco_occupation_ui, "EscoClient", _FakeClient)
    monkeypatch.setattr(esco_occupation_ui, "render_esco_picker_card", lambda **_kwargs: None)
    monkeypatch.setattr(esco_occupation_ui, "render_esco_explainability", lambda **_kwargs: None)

    job = SimpleNamespace(
        job_title="Data Engineer",
        seniority_level="Senior",
        department_name="Data",
        location_city="Berlin",
    )
    esco_occupation_ui.render_esco_occupation_confirmation(
        cast(object, job),
        show_start_context_panels=True,
    )

    assert "Noch nicht geladen" in fake_st.caption_messages
