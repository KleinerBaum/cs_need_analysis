from __future__ import annotations

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
