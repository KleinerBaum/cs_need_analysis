from __future__ import annotations

from typing import cast

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
