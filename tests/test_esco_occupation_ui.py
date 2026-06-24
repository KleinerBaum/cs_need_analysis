from __future__ import annotations

from types import SimpleNamespace
from typing import cast

from constants import SSKey
from esco_client import EscoApiCapabilities, EscoClient, EscoClientError
from schemas import JobAdExtract
from wizard_pages import esco_occupation_ui


def test_build_esco_query_falls_back_to_role_context_without_job_title() -> None:
    query = esco_occupation_ui._build_esco_query(
        JobAdExtract(
            role_overview="HR Transformation Consultant for AI adoption",
            department_name="Talent",
            location_city="Kronberg",
        )
    )

    assert query == "HR Transformation Consultant for AI adoption"


def test_build_esco_occupation_query_keeps_context_separate() -> None:
    query = esco_occupation_ui._build_esco_occupation_query(
        JobAdExtract(
            job_title="Data Engineer",
            seniority_level="Senior",
            department_name="Analytics",
            location_city="Berlin",
        )
    )

    assert query.search_query == "Data Engineer"
    assert query.context_label == "Senior, Analytics, Berlin"


def test_build_esco_occupation_query_truncates_long_fallback_title() -> None:
    query = esco_occupation_ui._build_esco_occupation_query(
        JobAdExtract(
            role_overview=(
                "Lead HR Transformation Consultant for AI adoption across global "
                "people operations, workforce planning, process automation, "
                "change management, and executive stakeholder enablement"
            ),
            department_name="Talent",
        )
    )

    assert len(query.search_query) <= 140
    assert "(" not in query.search_query
    assert query.context_label == "Talent"


def test_render_esco_occupation_confirmation_allows_manual_query_without_title(
    monkeypatch,
) -> None:
    class _FakeStreamlit:
        def __init__(self) -> None:
            self.session_state: dict[str, object] = {
                f"{SSKey.ESCO_OCCUPATION_SELECTED.value}.esco_picker.options": [],
                SSKey.ESCO_OCCUPATION_SELECTED.value: None,
            }
            self.infos: list[str] = []

        def info(self, message: str) -> None:
            self.infos.append(message)

        def button(self, *_args: object, **_kwargs: object) -> bool:
            return False

    fake_st = _FakeStreamlit()
    picker_calls: list[dict[str, object]] = []
    monkeypatch.setattr(esco_occupation_ui, "st", fake_st)
    monkeypatch.setattr(
        esco_occupation_ui,
        "render_esco_picker_card",
        lambda **kwargs: picker_calls.append(kwargs),
    )

    esco_occupation_ui.render_esco_occupation_confirmation(
        JobAdExtract(),
        compact=True,
        show_start_context_panels=True,
        show_detail_panels=False,
    )

    assert picker_calls
    assert fake_st.infos == [
        "Kein Jobtitel vorhanden. Gib einen Rollenbegriff ein, um die "
        "Berufsabgleich manuell zu starten."
    ]
    assert fake_st.session_state[SSKey.ESCO_UNMAPPED_ROLE_TERMS.value] == []


def test_render_secondary_anchor_controls_uses_friendly_expander_and_labels(
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
            self.session_state: dict[str, object] = {
                SSKey.UI_MODE.value: "standard",
                SSKey.ESCO_SECONDARY_ANCHORS.value: [
                    {
                        "uri": "uri:occ:secondary",
                        "title": "Product Analyst",
                        "reason": "benachbarte Rolle",
                    }
                ],
            }
            self.caption_messages: list[str] = []
            self.expander_calls: list[tuple[str, bool | None]] = []
            self.markdown_messages: list[str] = []
            self.selectbox_labels: list[str] = []
            self.button_labels: list[str] = []
            self.column_calls: list[tuple[list[float], str | None]] = []

        def expander(self, label: str, **kwargs: object) -> _DummyContext:
            self.expander_calls.append((label, kwargs.get("expanded")))
            return _DummyContext()

        def columns(self, spec: list[float], **kwargs: object) -> list[_DummyContext]:
            self.column_calls.append((spec, kwargs.get("gap")))
            return [_DummyContext() for _ in spec]

        def caption(self, message: str) -> None:
            self.caption_messages.append(message)

        def markdown(self, message: str, **_kwargs: object) -> None:
            self.markdown_messages.append(message)

        def selectbox(self, label: str, **kwargs: object) -> str:
            self.selectbox_labels.append(label)
            options = kwargs.get("options")
            return list(options)[0] if options else ""

        def button(self, label: str, **_kwargs: object) -> bool:
            self.button_labels.append(label)
            return False

        def info(self, _message: str) -> None:
            return None

    picker_calls: list[dict[str, object]] = []

    fake_st = _FakeStreamlit()
    monkeypatch.setattr(esco_occupation_ui, "st", fake_st)
    monkeypatch.setattr(
        esco_occupation_ui,
        "render_esco_picker_card",
        lambda **kwargs: picker_calls.append(kwargs),
    )

    esco_occupation_ui._render_secondary_anchor_controls(primary_uri="uri:occ:primary")

    assert ("Optionale Kontextanker", False) in fake_st.expander_calls
    assert fake_st.column_calls == [([1, 1.4], "large")]
    assert any(
        "Grenzrollen oder Mischprofile" in message
        and "bestätigte Referenzberuf" in message
        for message in fake_st.caption_messages
    )
    assert any(
        "Product Analyst" in message and "Grund: benachbarte Rolle" in message
        for message in fake_st.markdown_messages
    )
    assert picker_calls == [
        {
            "concept_type": "occupation",
            "target_state_key": "cs.esco_secondary_anchor_picker",
            "enable_preview": False,
            "apply_label": "Kontextrolle bestätigen",
            "selection_label": "Kontextrolle auswählen",
            "query_label": "Suchbegriff für Kontextrolle",
            "query_placeholder": "Benachbarte Rolle oder Alternativtitel eingeben",
            "confirmed_summary_label": "Ausgewählte Kontextrolle",
            "show_results_overview": False,
            "show_confirmed_summary": False,
            "taxonomy_auto_load": False,
            "layout_variant": "secondary_anchor",
        }
    ]
    assert "Grund" in fake_st.selectbox_labels
    assert "Als Kontextanker hinzufügen" not in fake_st.button_labels


def test_render_secondary_anchor_controls_persists_confirmed_picker_selection(
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
            self.session_state: dict[str, object] = {
                SSKey.UI_MODE.value: "standard",
                SSKey.ESCO_PRIMARY_ANCHOR.value: {
                    "uri": "uri:occ:primary",
                    "title": "Data Engineer",
                    "type": "occupation",
                    "selected_as": "primary",
                },
                SSKey.ESCO_SECONDARY_ANCHORS.value: [
                    {
                        "uri": "uri:occ:existing",
                        "title": "Product Analyst",
                        "reason": "benachbarte Rolle",
                        "selected_as": "secondary",
                    }
                ],
                "cs.esco_secondary_anchor_picker": {
                    "uri": "uri:occ:secondary",
                    "title": "Analytics Engineer",
                    "type": "occupation",
                },
            }

        def expander(self, _label: str, **_kwargs: object) -> _DummyContext:
            return _DummyContext()

        def columns(self, spec: list[float], **_kwargs: object) -> list[_DummyContext]:
            return [_DummyContext() for _ in spec]

        def caption(self, _message: str) -> None:
            return None

        def markdown(self, _message: str, **_kwargs: object) -> None:
            return None

        def selectbox(self, _label: str, **kwargs: object) -> str:
            options = kwargs.get("options")
            return list(options)[1] if options else ""

        def info(self, _message: str) -> None:
            return None

        def warning(self, _message: str) -> None:
            return None

    fake_st = _FakeStreamlit()
    monkeypatch.setattr(esco_occupation_ui, "st", fake_st)
    monkeypatch.setattr(
        esco_occupation_ui,
        "render_esco_picker_card",
        lambda **_kwargs: None,
    )

    esco_occupation_ui._render_secondary_anchor_controls(primary_uri="uri:occ:primary")

    assert fake_st.session_state[SSKey.ESCO_SECONDARY_ANCHORS.value] == [
        {
            "uri": "uri:occ:existing",
            "title": "Product Analyst",
            "type": "occupation",
            "reason": "benachbarte Rolle",
            "selected_as": "secondary",
        },
        {
            "uri": "uri:occ:secondary",
            "title": "Analytics Engineer",
            "type": "occupation",
            "reason": "spezialisierende Variante",
            "selected_as": "secondary",
        },
    ]
    assert fake_st.session_state[SSKey.ESCO_ANCHOR_STATE.value] == "anchored_with_context"


def test_render_secondary_anchor_controls_keeps_expander_when_anchor_limit_reached(
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
            self.session_state: dict[str, object] = {
                SSKey.UI_MODE.value: "expert",
                SSKey.ESCO_SECONDARY_ANCHORS.value: [
                    {"uri": "uri:1", "title": "Rolle 1", "reason": "benachbarte Rolle"},
                    {"uri": "uri:2", "title": "Rolle 2", "reason": "Alternativtitel"},
                ],
            }
            self.expander_labels: list[str] = []
            self.markdown_messages: list[str] = []
            self.info_messages: list[str] = []
            self.column_calls: list[tuple[list[float], str | None]] = []

        def expander(self, label: str, **_kwargs: object) -> _DummyContext:
            self.expander_labels.append(label)
            return _DummyContext()

        def columns(self, spec: list[float], **kwargs: object) -> list[_DummyContext]:
            self.column_calls.append((spec, kwargs.get("gap")))
            return [_DummyContext() for _ in spec]

        def caption(self, _message: str) -> None:
            return None

        def markdown(self, message: str, **_kwargs: object) -> None:
            self.markdown_messages.append(message)

        def selectbox(self, _label: str, **_kwargs: object) -> str:
            raise AssertionError("selectbox should not render after anchor limit")

        def button(self, _label: str, **_kwargs: object) -> bool:
            raise AssertionError("button should not render after anchor limit")

        def info(self, message: str) -> None:
            self.info_messages.append(message)

    picker_calls: list[dict[str, object]] = []
    fake_st = _FakeStreamlit()
    monkeypatch.setattr(esco_occupation_ui, "st", fake_st)
    monkeypatch.setattr(
        esco_occupation_ui,
        "render_esco_picker_card",
        lambda **kwargs: picker_calls.append(kwargs),
    )

    esco_occupation_ui._render_secondary_anchor_controls(primary_uri="uri:primary")

    assert "Optionale Kontextanker" in fake_st.expander_labels
    assert fake_st.column_calls == [([1, 1.4], "large")]
    assert any("Rolle 1" in message for message in fake_st.markdown_messages)
    assert any("Rolle 2" in message for message in fake_st.markdown_messages)
    assert fake_st.info_messages == [
        "Maximal zwei sekundäre Kontextanker sind hinterlegt."
    ]
    assert picker_calls == []


def test_build_capability_status_rows_with_capabilities() -> None:
    capabilities = EscoApiCapabilities(
        supported_occupation_relations=("hasEssentialSkill", "hasOptionalSkill"),
        unsupported_occupation_relations=("hasEssentialKnowledge", "hasOptionalKnowledge"),
        unsupported_endpoints=frozenset({"resource/occupationSkillsGroupShare"}),
        supports_occupation_knowledge_relations=False,
        supports_occupation_skill_group_share=False,
    )

    rows = esco_occupation_ui._build_capability_status_rows(
        source_mode="live_api",
        api_mode="hosted",
        selected_version="v1.2.0",
        capabilities=capabilities,
        matrix_loaded=False,
        matrix_coverage_available=False,
    )

    assert rows[0] == {
        "label": "Quelle",
        "state": "supported",
        "value": "live_api",
    }
    assert rows[1] == {
        "label": "API-Modus",
        "state": "supported",
        "value": "hosted",
    }
    assert rows[2] == {
        "label": "ESCO-Version",
        "state": "supported",
        "value": "v1.2.0",
    }
    assert rows[3] == {
        "label": "Occupation-Skill API-Relation",
        "state": "supported",
        "value": "verfügbar",
    }
    assert rows[4] == {
        "label": "Knowledge-Relation",
        "state": "unsupported",
        "value": "nicht unterstützt",
    }
    assert rows[5] == {
        "label": "API Skill-Group-Share",
        "state": "unsupported",
        "value": "nicht unterstützt",
    }
    assert rows[6] == {
        "label": "Offline-Matrix geladen",
        "state": "unsupported",
        "value": "nicht geladen",
    }
    assert rows[7] == {
        "label": "Matrix-Coverage",
        "state": "unsupported",
        "value": "nicht verfügbar",
    }


def test_build_capability_status_rows_not_loaded_without_capabilities() -> None:
    rows = esco_occupation_ui._build_capability_status_rows(
        source_mode="",
        api_mode="",
        selected_version="",
        capabilities=None,
        matrix_loaded=None,
        matrix_coverage_available=None,
    )

    assert rows[0]["state"] == "not loaded"
    assert rows[1]["state"] == "not loaded"
    assert rows[2]["state"] == "not loaded"
    assert rows[3]["state"] == "not loaded"
    assert rows[4]["state"] == "not loaded"
    assert rows[5]["state"] == "not loaded"
    assert rows[6]["state"] == "not loaded"
    assert rows[7]["state"] == "not loaded"


def test_build_capability_status_rows_offline_index_matrix_available() -> None:
    rows = esco_occupation_ui._build_capability_status_rows(
        source_mode="offline_index",
        api_mode="hosted",
        selected_version="v1.2.0",
        capabilities=None,
        matrix_loaded=True,
        matrix_coverage_available=True,
    )

    assert rows[0]["value"] == "offline_index"
    assert rows[6] == {
        "label": "Offline-Matrix geladen",
        "state": "supported",
        "value": "geladen",
    }
    assert rows[7] == {
        "label": "Matrix-Coverage",
        "state": "supported",
        "value": "verfügbar",
    }


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




def test_extract_text_field_with_state_fallback_order_de_en_then_other_language() -> None:
    payload = {
        "description": {
            "no": "Norsk beskrivelse",
            "en": "English description",
            "de": "Deutsche Beschreibung",
        }
    }
    text, state = esco_occupation_ui._extract_text_field_with_state(
        payload,
        keys=("description",),
        preferred_language="de",
        fallback_language="en",
    )
    assert text == "Deutsche Beschreibung"
    assert state == "verfügbar"

    payload_no_de = {"description": {"no": "Norsk beskrivelse", "en": "English description"}}
    text_no_de, state_no_de = esco_occupation_ui._extract_text_field_with_state(
        payload_no_de,
        keys=("description",),
        preferred_language="de",
        fallback_language="en",
    )
    assert text_no_de == "English description"
    assert state_no_de == "In gewählter Sprache nicht verfügbar (Fallback EN genutzt)"

    payload_only_no = {"description": {"no": "Norsk beskrivelse"}}
    text_only_no, state_only_no = esco_occupation_ui._extract_text_field_with_state(
        payload_only_no,
        keys=("description",),
        preferred_language="de",
        fallback_language="en",
    )
    assert text_only_no == "Norsk beskrivelse"
    assert state_only_no == "In gewählter Sprache nicht verfügbar (Fallback NO genutzt)"

def test_load_occupation_related_counts_uses_related_endpoint_payloads() -> None:
    call_relations: list[str] = []

    class _FakeClient:
        def resource_related(self, *, uri: str, relation: str) -> dict[str, object]:
            assert uri == "http://data.europa.eu/esco/occupation/123"
            call_relations.append(relation)
            payloads = {
                "hasEssentialSkill": {
                    "_embedded": {"hasEssentialSkill": [{"uri": "skill:1"}]}
                },
                "hasOptionalSkill": {
                    "_embedded": {
                        "hasOptionalSkill": [{"uri": "skill:2"}, {"uri": "skill:3"}]
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
    }
    assert sorted(call_relations) == ["hasEssentialSkill", "hasOptionalSkill"]


def test_resolve_related_counts_prefers_related_counts_over_payload_defaults() -> None:
    payload_without_relations = {"uri": "http://data.europa.eu/esco/occupation/123"}

    counts = esco_occupation_ui._resolve_related_counts(
        payload_without_relations,
        {
            "hasEssentialSkill": 4,
            "hasOptionalSkill": 5,
        },
    )

    assert counts["hasEssentialSkill"] == 4
    assert counts["hasOptionalSkill"] == 5


def test_load_occupation_related_counts_requests_only_the_two_skill_relations() -> None:
    call_relations: list[str] = []

    class _FakeClient:
        def resource_related(self, *, uri: str, relation: str) -> dict[str, object]:
            assert uri == "http://data.europa.eu/esco/occupation/123"
            call_relations.append(relation)
            payloads = {
                "hasEssentialSkill": {
                    "_embedded": {"hasEssentialSkill": [{"uri": "skill:1"}]}
                },
                "hasOptionalSkill": {
                    "_embedded": {
                        "hasOptionalSkill": [{"uri": "skill:2"}, {"uri": "skill:3"}]
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
    }
    assert call_relations == ["hasEssentialSkill", "hasOptionalSkill"]


def test_load_occupation_related_data_respects_client_supported_relations() -> None:
    call_relations: list[str] = []

    class _FakeClient:
        supported_occupation_relations = [
            "hasEssentialSkill",
            "hasEssentialKnowledge",
        ]

        def resource_related(self, *, uri: str, relation: str) -> dict[str, object]:
            assert uri == "http://data.europa.eu/esco/occupation/123"
            call_relations.append(relation)
            return {"_embedded": {relation: [{"uri": f"{relation}:1"}]}}

    counts, labels = esco_occupation_ui._load_occupation_related_data(
        client=cast(EscoClient, _FakeClient()),
        occupation_uri="http://data.europa.eu/esco/occupation/123",
    )

    assert call_relations == [
        "hasEssentialSkill",
        "hasEssentialKnowledge",
    ]
    assert counts == {
        "hasEssentialSkill": 1,
        "hasEssentialKnowledge": 1,
    }
    assert "hasOptionalSkill" not in labels
    assert "hasOptionalKnowledge" not in labels


def test_load_occupation_related_data_skips_unsupported_relation_status_400() -> None:
    class _FakeClient:
        supported_occupation_relations = ["hasEssentialSkill", "hasOptionalSkill"]

        def resource_related(self, *, uri: str, relation: str) -> dict[str, object]:
            assert uri == "http://data.europa.eu/esco/occupation/123"
            if relation == "hasOptionalSkill":
                raise EscoClientError(
                    status_code=400,
                    endpoint="/resource/related",
                    message="bad relation",
                )
            return {"_embedded": {relation: [{"uri": "skill:1"}]}}

    counts, labels = esco_occupation_ui._load_occupation_related_data(
        client=cast(EscoClient, _FakeClient()),
        occupation_uri="http://data.europa.eu/esco/occupation/123",
    )

    assert counts == {"hasEssentialSkill": 1}
    assert "hasEssentialSkill" not in labels


def test_load_occupation_related_data_uses_client_supported_relations_callable() -> None:
    call_relations: list[str] = []

    class _FakeClient:
        def supported_occupation_relations(self) -> tuple[str, ...]:
            return ("hasEssentialSkill", "hasOptionalSkill")

        def resource_related(self, *, uri: str, relation: str) -> dict[str, object]:
            assert uri == "http://data.europa.eu/esco/occupation/123"
            call_relations.append(relation)
            return {"_embedded": {relation: [{"uri": f"{relation}:1"}]}}

    counts, _ = esco_occupation_ui._load_occupation_related_data(
        client=cast(EscoClient, _FakeClient()),
        occupation_uri="http://data.europa.eu/esco/occupation/123",
    )

    assert call_relations == ["hasEssentialSkill", "hasOptionalSkill"]
    assert counts == {
        "hasEssentialSkill": 1,
        "hasOptionalSkill": 1,
    }


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
            self.caption_messages: list[str] = []
            self.write_messages: list[object] = []
            self.expander_calls: list[tuple[str, bool | None]] = []
            self.session_state = {
                f"{SSKey.ESCO_OCCUPATION_SELECTED.value}.esco_picker.options": [],
                SSKey.ESCO_OCCUPATION_SELECTED.value: {
                    "uri": "http://data.europa.eu/esco/occupation/123",
                    "title": "Data Engineer",
                },
                SSKey.UI_MODE.value: "expert",
                SSKey.ESCO_CONFIG.value: {"language": "de"},
            }

        def caption(self, message: str) -> None:
            self.caption_messages.append(message)

        def info(self, _message: str) -> None:
            return None

        def warning(self, _message: str) -> None:
            return None

        def write(self, message: object) -> None:
            self.write_messages.append(message)

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

        def expander(self, label: str, **kwargs: object) -> _DummyContext:
            self.expander_calls.append((label, kwargs.get("expanded")))
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
    assert any("Sicherheit: hoch" in event for event in fake_st.events)
    assert any("passt direkt zur Rolle" in event for event in fake_st.events)
    assert fake_st.expander_calls[:5] == [
        ("Warum Berufsabgleich?", False),
        ("Warum dieser Vorschlag?", False),
        ("Technische Details", True),
        ("ESCO Capability Status", False),
        ("ESCO Debug", True),
    ]
    assert ("Beruf im Detail", True) in fake_st.expander_calls
    assert any("Essential Knowledge" in event for event in fake_st.events)
    assert any("Optional Knowledge" in event for event in fake_st.events)


def test_render_esco_occupation_confirmation_compact_mode_keeps_decision_first(
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
            self.session_state = {
                f"{SSKey.ESCO_OCCUPATION_SELECTED.value}.esco_picker.options": [],
                SSKey.ESCO_OCCUPATION_SELECTED.value: {
                    "uri": "http://data.europa.eu/esco/occupation/123",
                    "title": "Data Engineer",
                },
                SSKey.UI_MODE.value: "expert",
                SSKey.ESCO_CONFIG.value: {"language": "de"},
            }
            self.caption_messages: list[str] = []
            self.markdown_messages: list[str] = []
            self.info_messages: list[str] = []
            self.expander_calls: list[tuple[str, bool | None]] = []

        def caption(self, message: str) -> None:
            self.caption_messages.append(message)

        def info(self, message: str) -> None:
            self.info_messages.append(message)
        def warning(self, _message: str) -> None: return None
        def write(self, _message: object) -> None: return None
        def code(self, _value: str, *, language: str) -> None:
            del language
            return None
        def markdown(self, message: str, **_kwargs: object) -> None:
            self.markdown_messages.append(message)
        def button(self, _label: str, **_kwargs: object) -> bool: return False
        def toggle(self, _label: str, *, value: bool = False, **_kwargs: object) -> bool:
            return value
        def columns(self, _spec: list[int] | tuple[int, ...]) -> list[_DummyContext]:
            return [_DummyContext(), _DummyContext(), _DummyContext()]
        def container(self) -> _DummyContext: return _DummyContext()
        def expander(self, label: str, **kwargs: object) -> _DummyContext:
            self.expander_calls.append((label, kwargs.get("expanded")))
            return _DummyContext()
        def multiselect(self, _label: str, **_kwargs: object) -> list[str]: return ["de"]
        def vega_lite_chart(self, _spec: object, **_kwargs: object) -> None: return None

    class _FakeClient:
        def supports_endpoint(self, _endpoint: str) -> bool:
            return True
        def get_occupation_detail(self, *, uri: str) -> dict[str, object]:
            del uri
            return {"description": {"de": "Beschreibung"}, "uri": "uri:occ:1"}
        def resource_related(self, *, uri: str, relation: str) -> dict[str, object]:
            del uri, relation
            return {"_embedded": {}}
        def get_occupation_skill_group_share(self, *, occupation_uri: str) -> dict[str, object]:
            del occupation_uri
            return {"results": []}

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
        compact=True,
        show_start_context_panels=True,
    )

    assert any(
        "Der Referenzberuf ist der gemeinsame Bezugspunkt" in message
        for message in fake_st.info_messages
    )
    assert any("Portal öffnen" in message for message in fake_st.markdown_messages)
    assert ("Mehr Details", False) in fake_st.expander_calls
    assert ("Beruf im Detail", False) not in fake_st.expander_calls


def test_render_esco_occupation_confirmation_can_hide_start_detail_panels(
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
            self.session_state = {
                f"{SSKey.ESCO_OCCUPATION_SELECTED.value}.esco_picker.options": [],
                SSKey.ESCO_OCCUPATION_SELECTED.value: {
                    "uri": "http://data.europa.eu/esco/occupation/123",
                    "title": "Data Engineer",
                },
                SSKey.UI_MODE.value: "expert",
                SSKey.ESCO_CONFIG.value: {"language": "de"},
            }
            self.button_labels: list[str] = []
            self.caption_messages: list[str] = []
            self.expander_labels: list[str] = []
            self.info_messages: list[str] = []
            self.markdown_messages: list[str] = []
            self.multiselect_labels: list[str] = []
            self.write_messages: list[object] = []

        def caption(self, message: str) -> None:
            self.caption_messages.append(message)

        def info(self, message: str) -> None:
            self.info_messages.append(message)

        def warning(self, _message: str) -> None:
            return None

        def write(self, message: object) -> None:
            self.write_messages.append(message)

        def code(self, _value: str, *, language: str) -> None:
            del language
            return None

        def markdown(self, message: str, **_kwargs: object) -> None:
            self.markdown_messages.append(message)

        def button(self, label: str, **_kwargs: object) -> bool:
            self.button_labels.append(label)
            return False

        def toggle(self, _label: str, *, value: bool = False, **_kwargs: object) -> bool:
            return value

        def columns(self, _spec: list[int] | tuple[int, ...]) -> list[_DummyContext]:
            return [_DummyContext(), _DummyContext(), _DummyContext()]

        def container(self) -> _DummyContext:
            return _DummyContext()

        def expander(self, label: str, **_kwargs: object) -> _DummyContext:
            self.expander_labels.append(label)
            return _DummyContext()

        def multiselect(self, label: str, **_kwargs: object) -> list[str]:
            self.multiselect_labels.append(label)
            return ["de"]

        def vega_lite_chart(self, _spec: object, **_kwargs: object) -> None:
            return None

    class _FakeClient:
        def supports_endpoint(self, _endpoint: str) -> bool:
            return True

        def get_occupation_detail(self, *, uri: str) -> dict[str, object]:
            del uri
            return {
                "description": {"de": "Beschreibung"},
                "code": "2512.1",
                "uri": "uri:occ:1",
            }

        def resource_related(self, *, uri: str, relation: str) -> dict[str, object]:
            del uri, relation
            return {"_embedded": {}}

        def get_occupation_skill_group_share(self, *, occupation_uri: str) -> dict[str, object]:
            del occupation_uri
            return {"results": []}

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
        compact=True,
        show_start_context_panels=True,
        show_detail_panels=False,
    )

    rendered_text = "\n".join(
        [
            *fake_st.button_labels,
            *fake_st.caption_messages,
            *fake_st.expander_labels,
            *fake_st.info_messages,
            *fake_st.markdown_messages,
            *fake_st.multiselect_labels,
            *(str(message) for message in fake_st.write_messages),
        ]
    )
    assert "Titel-Varianten laden" not in rendered_text
    assert "Sprachen für Berufstitel" not in rendered_text
    assert "Concept overview" not in rendered_text
    assert "Capabilities:" not in rendered_text
    assert "URI kopieren" not in rendered_text
    assert "Taxonomie/Breadcrumb" not in rendered_text
    assert "Portal öffnen" not in rendered_text
    assert "Warum Berufsabgleich" not in rendered_text
    assert any("Sicherheit: hoch" in message for message in fake_st.markdown_messages)
    assert fake_st.session_state[SSKey.ESCO_SELECTED_OCCUPATION_URI.value] == (
        "http://data.europa.eu/esco/occupation/123"
    )
    assert fake_st.session_state[SSKey.ESCO_OCCUPATION_PAYLOAD.value] == {
        "description": {"de": "Beschreibung"},
        "code": "2512.1",
        "uri": "uri:occ:1",
    }
    assert fake_st.session_state[SSKey.ESCO_OCCUPATION_RELATED_COUNTS.value] == {
        "hasEssentialSkill": 0,
        "hasOptionalSkill": 0,
    }
    assert fake_st.session_state[SSKey.ESCO_MATCH_CONFIDENCE.value] == "high"
    assert fake_st.session_state[SSKey.ESCO_MATCH_REASON.value]


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
            self.markdown_messages: list[str] = []
            self.session_state = {
                f"{SSKey.ESCO_OCCUPATION_SELECTED.value}.esco_picker.options": [],
                SSKey.ESCO_OCCUPATION_SELECTED.value: {
                    "uri": "http://data.europa.eu/esco/occupation/123",
                    "title": "Data Engineer",
                },
                SSKey.UI_MODE.value: "expert",
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
            self.markdown_messages.append(_message)
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
        "Das ESCO-Portal zeigt diesen Anteil, der aktuell über den genutzten ESCO-Webservice nicht abrufbar ist."
        in message
        for message in fake_st.caption_messages
    )
    assert any("Portal öffnen" in message for message in fake_st.markdown_messages)
    assert any(
        "Capabilities: Skills ✅ · Knowledge 🚫 · Skill Groups 🚫" in message
        for message in fake_st.caption_messages
    )
    assert any("Skills: ✅ verfügbar" in message for message in fake_st.caption_messages)
    assert any(
        "Knowledge: 🚫 nicht unterstützt" in message
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
    assert fake_client.related_calls == 2
    assert fake_st.session_state[SSKey.ESCO_OCCUPATION_RELATED_COUNTS.value] == {
        "hasEssentialSkill": 1,
        "hasOptionalSkill": 1,
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

    assert "noch nicht geladen" in fake_st.caption_messages
