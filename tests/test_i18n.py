from __future__ import annotations

import ast
import json
import re
import sys
from collections.abc import Mapping
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import check_repo_hygiene
import config.preferences as preferences_config
from constants import (
    SSKey,
    STEP_KEY_BENEFITS,
    STEP_KEY_COMPANY,
    STEP_KEY_INTERVIEW,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
    STEP_KEY_SUMMARY,
    UI_LANGUAGE_QUERY_PARAM,
    UI_PREFERENCE_UI_LANGUAGE,
)
from i18n import (
    LANGUAGE_WIDGET_KEY_PAGE,
    LANGUAGE_WIDGET_KEY_SIDEBAR,
    LAST_LANGUAGE_WIDGET_KEY,
    sync_language_from_known_widgets,
    sync_language_state_from_request,
    sync_language_state,
    t,
    tr,
    tr_safe,
)
import wizard_pages.base as wizard_base


def _leaf_count(value: object) -> int:
    if isinstance(value, Mapping):
        return sum(_leaf_count(item) for item in value.values())
    return 1


def _i18n_dict_literal_count(name: str) -> int:
    module = ast.parse((ROOT / "i18n.py").read_text(encoding="utf-8"))
    for node in module.body:
        if isinstance(node, ast.AnnAssign) and getattr(node.target, "id", "") == name:
            if not isinstance(node.value, ast.Dict):
                raise AssertionError(f"{name} is not a literal dict")
            return len(node.value.keys)
    raise AssertionError(f"{name} not found")


def _inventory_summary_count(label: str) -> int:
    text = (ROOT / "docs/i18n_key_list.md").read_text(encoding="utf-8")
    match = re.search(rf"\| {re.escape(label)} \| (?P<count>\d+) \|", text)
    if match is None:
        raise AssertionError(f"Missing inventory row for {label}")
    return int(match.group("count"))


import i18n
from site_ui import PROFILE, PROFILE_VALUE_NOT_CONFIGURED, PROFILE_VALUE_NOT_PUBLISHED
from site_ui import localized_profile_value
from wizard_pages.base import WizardPage


def _locale_leaf_keys(payload: dict[str, object], prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for key, value in payload.items():
        dotted_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys.update(_locale_leaf_keys(value, dotted_key))
        else:
            keys.add(dotted_key)
    return keys


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
    assert t("Briefing-Cockpit öffnen") == "Open briefing cockpit"
    assert t("Recruiting-Briefing vor Workflow") == "Recruiting brief before workflow"
    assert t("Anzeige hochladen oder einfügen") == "Upload or paste job ad"
    assert (
        t("Was der Start vor dem Upload verspricht")
        == "What Start promises before upload"
    )
    assert (
        t(
            "Das Briefing-Cockpit ist vorbereitet. Prüfen Sie erkannte Angaben, "
            "bereinigen Sie Unsicherheiten und bestätigen Sie den Referenzberuf."
        )
        == "The briefing cockpit is prepared. Review detected facts, clean up uncertainty, "
        "and confirm the reference occupation."
    )
    assert t("Quelle in Briefing verwandeln") == "Turn source into brief"
    assert (
        t("Mit Unternehmenskontext weiterarbeiten") == "Continue with company context"
    )
    assert t("Was bedeutet RAG?") == "What does RAG mean?"
    assert t("Datenschutzrichtlinie") == "Privacy policy"


def test_tr_reads_locale_files(monkeypatch) -> None:
    monkeypatch.setattr(i18n, "active_language", lambda: "en")

    assert tr("common.language") == "Language"
    assert tr("common.last_updated", date="14.04.2026") == "Last updated: 14.04.2026"
    assert tr("public_pages.privacy.title") == "Privacy policy"
    assert (
        tr("public_pages.accessibility.enforcement.heading")
        == "## Enforcement or mediation information"
    )


def test_tr_safe_formats_missing_params_without_error(monkeypatch) -> None:
    monkeypatch.setattr(i18n, "active_language", lambda: "en")

    assert tr_safe("common.last_updated") == "Last updated:"
    assert tr_safe("common.last_updated", date="23.06.2026") == (
        "Last updated: 23.06.2026"
    )


def test_locale_files_have_matching_key_shapes() -> None:
    locales_dir = Path(__file__).resolve().parents[1] / "locales"
    de_locale = json.loads((locales_dir / "de.json").read_text(encoding="utf-8"))
    en_locale = json.loads((locales_dir / "en.json").read_text(encoding="utf-8"))

    assert _locale_leaf_keys(de_locale) == _locale_leaf_keys(en_locale)


def test_i18n_inventory_summary_counts_match_sources() -> None:
    locales_dir = ROOT / "locales"
    de_locale = json.loads((locales_dir / "de.json").read_text(encoding="utf-8"))
    en_locale = json.loads((locales_dir / "en.json").read_text(encoding="utf-8"))
    inventory_text = (ROOT / "docs/i18n_key_list.md").read_text(encoding="utf-8")

    assert _inventory_summary_count("`locales/de.json` leaf keys") == _leaf_count(
        de_locale
    )
    assert _inventory_summary_count("`locales/en.json` leaf keys") == _leaf_count(
        en_locale
    )
    assert _inventory_summary_count("`_TRANSLATIONS_EN`") == _i18n_dict_literal_count(
        "_TRANSLATIONS_EN"
    )
    assert _inventory_summary_count(
        "`_PHRASE_TRANSLATIONS_EN`"
    ) == _i18n_dict_literal_count("_PHRASE_TRANSLATIONS_EN")
    assert _inventory_summary_count(
        "High-confidence unkeyed UI-copy candidates"
    ) == sum(1 for line in inventory_text.splitlines() if line.startswith("| P"))


def test_public_legal_copy_uses_missing_configuration_language(monkeypatch) -> None:
    locales_dir = Path(__file__).resolve().parents[1] / "locales"
    locale_text = "\n".join(
        [
            (locales_dir / "de.json").read_text(encoding="utf-8"),
            (locales_dir / "en.json").read_text(encoding="utf-8"),
        ]
    )

    assert "Bitte ergänzen" not in locale_text
    assert "+49 ..." not in locale_text
    assert "legal_placeholder_title" not in locale_text
    assert "legal_template_notice" not in locale_text
    assert "Placeholder - subject-matter" not in locale_text
    assert "This page is a template" not in locale_text
    assert "Legal page · template" not in locale_text
    assert "Rechtliche Seite · Template" not in locale_text
    assert "Before publication, this page should be adapted" not in locale_text
    assert "Diese Seite sollte vor Veröffentlichung" not in locale_text
    assert "Before publication, please align this page" not in locale_text
    assert "Bitte gleichen Sie diese Seite vor Veröffentlichung" not in locale_text
    assert "Before publication, please check" not in locale_text
    assert "Bitte prüfen Sie vor Veröffentlichung" not in locale_text
    assert "must be reviewed before publication" not in locale_text
    assert "muss vor Veröffentlichung geprüft werden" not in locale_text
    assert "Example information that should be added" not in locale_text
    assert "Beispielhafte Angaben, die ergänzt werden sollten" not in locale_text
    assert "cookies.examples" not in locale_text
    assert "Consent-Management-System" not in locale_text
    assert "Vorbereitetes Steuerfeld" not in locale_text
    assert "Vorbereitete globale Schwelle" not in locale_text

    assert PROFILE.phone == PROFILE_VALUE_NOT_PUBLISHED
    monkeypatch.setattr(i18n, "active_language", lambda: "en")
    assert localized_profile_value(PROFILE_VALUE_NOT_PUBLISHED) == "Not published"
    assert localized_profile_value(PROFILE_VALUE_NOT_CONFIGURED) == "Not configured"
    assert (
        t("Rechtliche Seite · Prüfung erforderlich") == "Legal page · review required"
    )


def test_runtime_context_describes_actual_storage_instead_of_cookie_consent(
    monkeypatch,
) -> None:
    fake_st = type("FakeStreamlit", (), {"session_state": {}})()
    monkeypatch.setattr(preferences_config, "st", fake_st)

    context = preferences_config.build_runtime_context()

    assert "consent" not in context
    assert "cs_cookie_consent" not in fake_st.session_state
    assert "regional_focus" not in context["retrieval"]
    assert "esco_match_strictness" not in context["retrieval"]
    assert context["storage"] == {
        "language_preference": True,
        "session_preferences": True,
        "draft_recovery_metadata": True,
        "analytics": False,
        "marketing": False,
    }


def test_i18n_hygiene_contract_guard_passes_current_repo() -> None:
    assert check_repo_hygiene.find_i18n_contract_findings() == []


def test_raw_wizard_ui_guard_flags_changed_literal_without_translation() -> None:
    source = 'import streamlit as st\nst.button("Neue Rohkopie")\n'

    findings = check_repo_hygiene.find_raw_ui_string_findings_in_source(
        "wizard_pages/demo.py",
        source,
        changed_lines={2},
        documented_allowlist=set(),
    )

    assert findings == [
        check_repo_hygiene.RawUiStringFinding(
            path="wizard_pages/demo.py",
            line=2,
            method="button",
            text="Neue Rohkopie",
        )
    ]


def test_raw_wizard_ui_guard_allows_translated_or_explicitly_documented_copy() -> None:
    translated_source = (
        "import streamlit as st\n"
        "from i18n import t\n"
        'st.button(t("Analyse starten"))\n'
    )
    assert (
        check_repo_hygiene.find_raw_ui_string_findings_in_source(
            "wizard_pages/demo.py",
            translated_source,
            changed_lines={3},
            documented_allowlist=set(),
        )
        == []
    )

    commented_source = (
        "import streamlit as st\n"
        'st.button("HR")  # i18n: allow-raw-ui language-neutral abbreviation\n'
    )
    assert (
        check_repo_hygiene.find_raw_ui_string_findings_in_source(
            "wizard_pages/demo.py",
            commented_source,
            changed_lines={2},
            documented_allowlist=set(),
        )
        == []
    )


def test_raw_wizard_ui_guard_uses_i18n_backlog_as_explicit_allowlist() -> None:
    allowlist = check_repo_hygiene.load_i18n_raw_ui_allowlist()

    assert ("wizard_pages/base.py", "Mehr erfahren") in allowlist
    assert (
        check_repo_hygiene.find_raw_ui_string_findings_in_source(
            "wizard_pages/base.py",
            'st.button("Mehr erfahren")\n',
            changed_lines={1},
            documented_allowlist=allowlist,
        )
        == []
    )


def test_active_step_copy_locale_contract_has_de_en_parity() -> None:
    locales_dir = Path(__file__).resolve().parents[1] / "locales"
    de_steps = json.loads((locales_dir / "de.json").read_text(encoding="utf-8"))[
        "ux_copy"
    ]["steps"]
    en_steps = json.loads((locales_dir / "en.json").read_text(encoding="utf-8"))[
        "ux_copy"
    ]["steps"]

    for step_key in (
        STEP_KEY_COMPANY,
        STEP_KEY_ROLE_TASKS,
        STEP_KEY_SKILLS,
        STEP_KEY_BENEFITS,
        STEP_KEY_INTERVIEW,
    ):
        assert set(de_steps[step_key]) == set(en_steps[step_key])
        assert de_steps[step_key]["headline"]
        assert de_steps[step_key]["subheadline"]
        assert de_steps[step_key]["value_line"]
        assert en_steps[step_key]["headline"]
        assert en_steps[step_key]["subheadline"]
        assert en_steps[step_key]["value_line"]

    assert set(de_steps[STEP_KEY_SUMMARY]["headline"]) == set(
        en_steps[STEP_KEY_SUMMARY]["headline"]
    )
    assert set(de_steps[STEP_KEY_SUMMARY]["subheadline"]) == set(
        en_steps[STEP_KEY_SUMMARY]["subheadline"]
    )
    assert de_steps[STEP_KEY_SUMMARY]["value_line"]
    assert en_steps[STEP_KEY_SUMMARY]["value_line"]


def test_sync_language_state_from_request_uses_query_param(monkeypatch) -> None:
    session_state = {
        SSKey.LANGUAGE.value: "de",
        SSKey.UI_PREFERENCES.value: {UI_PREFERENCE_UI_LANGUAGE: "de"},
    }
    fake_st = type(
        "FakeStreamlit",
        (),
        {
            "session_state": session_state,
            "query_params": {UI_LANGUAGE_QUERY_PARAM: "en"},
        },
    )()
    monkeypatch.setattr(i18n, "st", fake_st)

    synced = sync_language_state_from_request(session_state=session_state)

    assert synced == "en"
    assert session_state[SSKey.LANGUAGE.value] == "en"
    assert session_state[SSKey.UI_PREFERENCES.value][UI_PREFERENCE_UI_LANGUAGE] == "en"


def test_sync_language_state_updates_preferences_without_esco_config() -> None:
    session_state = {
        SSKey.UI_PREFERENCES.value: {},
        SSKey.ESCO_CONFIG.value: {"language": "de", "fallback_language": "en"},
    }

    sync_language_state("en", session_state=session_state)

    assert session_state[SSKey.LANGUAGE.value] == "en"
    assert session_state[SSKey.UI_PREFERENCES.value][UI_PREFERENCE_UI_LANGUAGE] == "en"
    assert session_state[SSKey.ESCO_CONFIG.value]["language"] == "de"
    assert session_state[SSKey.ESCO_CONFIG.value]["fallback_language"] == "en"


def test_known_widget_sync_updates_language_before_render() -> None:
    session_state = {
        LANGUAGE_WIDGET_KEY_SIDEBAR: "en",
        SSKey.LANGUAGE.value: "de",
        SSKey.UI_PREFERENCES.value: {UI_PREFERENCE_UI_LANGUAGE: "de"},
        SSKey.ESCO_CONFIG.value: {"language": "de", "fallback_language": "en"},
    }

    synced = sync_language_from_known_widgets(session_state=session_state)

    assert synced == "en"
    assert session_state[SSKey.LANGUAGE.value] == "en"
    assert session_state[SSKey.UI_PREFERENCES.value][UI_PREFERENCE_UI_LANGUAGE] == "en"
    assert session_state[SSKey.ESCO_CONFIG.value]["language"] == "de"
    assert session_state[SSKey.ESCO_CONFIG.value]["fallback_language"] == "en"


def test_known_widget_sync_prefers_last_changed_language_widget() -> None:
    page_widget_key = LANGUAGE_WIDGET_KEY_PAGE
    session_state = {
        LANGUAGE_WIDGET_KEY_SIDEBAR: "de",
        page_widget_key: "en",
        LAST_LANGUAGE_WIDGET_KEY: page_widget_key,
        SSKey.LANGUAGE.value: "en",
        SSKey.UI_PREFERENCES.value: {UI_PREFERENCE_UI_LANGUAGE: "en"},
        SSKey.ESCO_CONFIG.value: {"language": "en", "fallback_language": "de"},
    }

    synced = sync_language_from_known_widgets(session_state=session_state)

    assert synced == "en"
    assert session_state[SSKey.LANGUAGE.value] == "en"
    assert session_state[SSKey.UI_PREFERENCES.value][UI_PREFERENCE_UI_LANGUAGE] == "en"


def test_language_toggle_uses_widget_state_without_index(monkeypatch) -> None:
    session_state = {
        SSKey.LANGUAGE.value: "en",
        SSKey.UI_PREFERENCES.value: {UI_PREFERENCE_UI_LANGUAGE: "en"},
        LANGUAGE_WIDGET_KEY_PAGE: "en",
    }
    radio_kwargs: dict[str, object] = {}

    class FakeStreamlit:
        def __init__(self) -> None:
            self.query_params: dict[str, str] = {}
            self.session_state = session_state

        def radio(self, _label: str, **kwargs: object) -> str:
            radio_kwargs.update(kwargs)
            return str(self.session_state[str(kwargs["key"])])

    fake_st = FakeStreamlit()
    monkeypatch.setattr(i18n, "st", fake_st)
    monkeypatch.setattr(i18n, "render_language_persistence_bridge", lambda **_: None)

    selected = i18n.render_language_toggle(
        location="main", key=LANGUAGE_WIDGET_KEY_PAGE
    )

    assert selected == "en"
    assert "index" not in radio_kwargs
    assert session_state[SSKey.LANGUAGE.value] == "en"


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
            SSKey.DEBUG.value: True,
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
