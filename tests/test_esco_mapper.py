from __future__ import annotations

from typing import Any

from esco_mapper import expand_esco_query, map_esco_concept, map_esco_concepts


class _FakeEscoClient:
    def __init__(self) -> None:
        self.search_calls: list[dict[str, Any]] = []
        self.occupation_calls: list[dict[str, Any]] = []
        self.skill_calls: list[dict[str, Any]] = []

    def search(self, **query: Any) -> dict[str, Any]:
        self.search_calls.append(query)
        text = str(query.get("text") or "")
        kind = str(query.get("type") or "")
        if kind == "occupation" and text == "Softwareentwickler":
            return {
                "_embedded": {
                    "results": [
                        {
                            "uri": "https://data.europa.eu/esco/occupation/1",
                            "preferredLabel": "Softwareentwickler/in",
                            "type": "occupation",
                            "score": 0.92,
                        }
                    ]
                }
            }
        if kind == "skill" and text == "active sourcing":
            return {
                "_embedded": {
                    "results": [
                        {
                            "uri": "https://data.europa.eu/esco/skill/1",
                            "preferredLabel": "active sourcing",
                            "type": "skill",
                            "score": 0.9,
                        }
                    ]
                }
            }
        return {"_embedded": {"results": []}}

    def resource_occupation(self, **query: Any) -> dict[str, Any]:
        self.occupation_calls.append(query)
        return {
            "uri": query["uri"],
            "preferredLabel": "Softwareentwickler/in",
            "type": "occupation",
        }

    def resource_skill(self, **query: Any) -> dict[str, Any]:
        self.skill_calls.append(query)
        return {
            "uri": query["uri"],
            "preferredLabel": "active sourcing",
            "type": "skill",
        }


def test_expand_esco_query_adds_german_to_english_variant() -> None:
    assert expand_esco_query("Softwareentwickler", language="de") == (
        "Softwareentwickler",
        "software developer",
    )


def test_expand_esco_query_adds_english_to_german_variant() -> None:
    assert expand_esco_query("Data Engineer", language="en") == (
        "Data Engineer",
        "Dateningenieur",
    )


def test_map_esco_concept_uses_search_then_canonical_occupation_hydration() -> None:
    client = _FakeEscoClient()

    mapped = map_esco_concept(
        "Softwareentwickler",
        kind="occupation",
        language="de",
        selected_version="v1.2.1",
        client=client,  # type: ignore[arg-type]
    )

    assert mapped is not None
    assert client.search_calls[0] == {
        "text": "Softwareentwickler",
        "type": "occupation",
        "limit": 10,
        "language": "de",
        "selectedVersion": "v1.2.1",
    }
    assert client.occupation_calls == [
        {
            "uri": "https://data.europa.eu/esco/occupation/1",
            "language": "de",
            "selectedVersion": "v1.2.1",
        }
    ]
    assert mapped.uri == "https://data.europa.eu/esco/occupation/1"
    assert mapped.preferred_label == "Softwareentwickler/in"
    assert mapped.confidence > 0.7
    assert mapped.to_persistence_dict() == {
        "uri": "https://data.europa.eu/esco/occupation/1",
        "preferred_label": "Softwareentwickler/in",
        "preferredLabel": "Softwareentwickler/in",
        "title": "Softwareentwickler/in",
        "type": "occupation",
        "language": "de",
        "selectedVersion": "v1.2.1",
        "confidence": mapped.confidence,
        "source": "search+resource",
        "raw_score": 0.92,
    }


def test_map_esco_concepts_hydrates_skill_resource() -> None:
    client = _FakeEscoClient()

    mapped = map_esco_concepts(
        "active sourcing",
        kind="skill",
        language="en",
        selected_version="v1.2.1",
        client=client,  # type: ignore[arg-type]
    )

    assert [item.uri for item in mapped] == ["https://data.europa.eu/esco/skill/1"]
    assert client.skill_calls == [
        {
            "uri": "https://data.europa.eu/esco/skill/1",
            "language": "en",
            "selectedVersion": "v1.2.1",
        }
    ]
