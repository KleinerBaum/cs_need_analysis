from __future__ import annotations

from constants import SSKey, UI_PREFERENCE_UI_LANGUAGE
from i18n import (
    LAST_LANGUAGE_WIDGET_KEY,
    sync_language_from_known_widgets,
    sync_language_state,
    t,
)
import wizard_pages.base as wizard_base
import i18n
from wizard_pages.base import WizardPage


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
    assert t("Einleitung") == "Introduction"
    assert t("Weiter →") == "Next"
    assert t("Zum Start") == "Go to Start"
    assert (
        t("Vakanzanforderungen präzise erfassen")
        == "Capture vacancy requirements precisely"
    )
    assert t("Anzeige hochladen oder einfügen") == "Upload or paste job ad"
    assert t('Nach dem Klick auf "Analyse starten"') == 'After clicking "Start analysis"'
    assert t("Text verstehen") == "Understand text"
    assert t("Was bedeutet RAG?") == "What does RAG mean?"


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


def test_known_widget_sync_updates_language_before_render() -> None:
    session_state = {
        "sidebar.ui_language": "en",
        SSKey.LANGUAGE.value: "de",
        SSKey.UI_PREFERENCES.value: {UI_PREFERENCE_UI_LANGUAGE: "de"},
        SSKey.ESCO_CONFIG.value: {"language": "de", "fallback_language": "en"},
    }

    synced = sync_language_from_known_widgets(session_state=session_state)

    assert synced == "en"
    assert session_state[SSKey.LANGUAGE.value] == "en"
    assert session_state[SSKey.UI_PREFERENCES.value][UI_PREFERENCE_UI_LANGUAGE] == "en"
    assert session_state[SSKey.ESCO_CONFIG.value]["language"] == "en"
    assert session_state[SSKey.ESCO_CONFIG.value]["fallback_language"] == "de"


def test_known_widget_sync_prefers_last_changed_language_widget() -> None:
    esco_widget_key = f"{SSKey.ESCO_CONFIG.value}.language_choice"
    session_state = {
        "sidebar.ui_language": "de",
        esco_widget_key: "en",
        LAST_LANGUAGE_WIDGET_KEY: esco_widget_key,
        SSKey.LANGUAGE.value: "en",
        SSKey.UI_PREFERENCES.value: {UI_PREFERENCE_UI_LANGUAGE: "en"},
        SSKey.ESCO_CONFIG.value: {"language": "en", "fallback_language": "de"},
    }

    synced = sync_language_from_known_widgets(session_state=session_state)

    assert synced == "en"
    assert session_state[SSKey.LANGUAGE.value] == "en"
    assert session_state[SSKey.UI_PREFERENCES.value][UI_PREFERENCE_UI_LANGUAGE] == "en"


def test_wizard_page_label_uses_active_ui_language(monkeypatch) -> None:
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
    page = WizardPage(
        key="company",
        title_de="Unternehmen",
        icon="",
        render=lambda _ctx: None,
    )

    assert page.label == "Company"


class _FakeLanguageToggleStreamlit:
    def __init__(self) -> None:
        self.session_state = {
            SSKey.UI_PREFERENCES.value: {UI_PREFERENCE_UI_LANGUAGE: "de"},
            SSKey.ESCO_CONFIG.value: {
                "release_lane": "stable",
                "selected_version": "v1.2.0",
                "language": "de",
                "fallback_language": "en",
                "view_obsolete": False,
                "api_mode": "hosted",
                "data_source_mode": "live_api",
            },
            SSKey.ESCO_RELEASE_LANE.value: "stable",
        }

    def radio(self, _label: str, **kwargs: object) -> str:
        key = str(kwargs["key"])
        self.session_state[key] = "en"
        on_change = kwargs.get("on_change")
        if callable(on_change):
            args = kwargs.get("args", ())
            on_change(*args)
        return "en"


def test_esco_language_toggle_syncs_canonical_language(monkeypatch) -> None:
    fake_st = _FakeLanguageToggleStreamlit()
    monkeypatch.setattr(wizard_base, "st", fake_st)
    monkeypatch.setattr(i18n, "st", fake_st)

    wizard_base.render_esco_language_toggle()

    assert fake_st.session_state[SSKey.LANGUAGE.value] == "en"
    assert (
        fake_st.session_state[SSKey.UI_PREFERENCES.value][UI_PREFERENCE_UI_LANGUAGE]
        == "en"
    )
    assert fake_st.session_state[SSKey.ESCO_CONFIG.value]["language"] == "en"
    assert fake_st.session_state[SSKey.ESCO_CONFIG.value]["fallback_language"] == "de"
