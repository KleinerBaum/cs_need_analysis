from __future__ import annotations

from constants import SSKey, UI_PREFERENCE_UI_LANGUAGE
from i18n import sync_language_state, t


def test_translation_uses_german_as_source_copy(monkeypatch) -> None:
    monkeypatch.setattr(
        "i18n.st",
        type(
            "FakeStreamlit",
            (),
            {
                "session_state": {
                    SSKey.LANGUAGE.value: "en",
                    SSKey.UI_PREFERENCES.value: {UI_PREFERENCE_UI_LANGUAGE: "en"},
                }
            },
        )(),
    )

    assert t("Unternehmen") == "Company"
    assert t("Weiter →") == "Next"


def test_sync_language_state_updates_preferences_and_esco_config() -> None:
    session_state = {
        SSKey.UI_PREFERENCES.value: {},
        SSKey.ESCO_CONFIG.value: {"language": "de", "fallback_language": "en"},
    }

    sync_language_state("en", session_state=session_state)

    assert session_state[SSKey.LANGUAGE.value] == "en"
    assert session_state[SSKey.UI_PREFERENCES.value][UI_PREFERENCE_UI_LANGUAGE] == "en"
    assert session_state[SSKey.ESCO_CONFIG.value]["language"] == "en"
    assert session_state[SSKey.ESCO_CONFIG.value]["fallback_language"] == "de"
