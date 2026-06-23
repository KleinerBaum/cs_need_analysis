from __future__ import annotations

from constants import (
    SUMMARY_ACTIVE_ARTIFACT_IDS,
    STEP_KEY_COMPANY,
    STEP_KEY_LANDING,
    STEP_KEY_SUMMARY,
)
from ux_copy_contract import (
    ARTIFACT_LABELS,
    ESCO_UI_COPY,
    SALARY_UI_COPY,
    SUMMARY_EXPORT_COPY,
    SUMMARY_PREVIEW_COPY,
    SUMMARY_UI_COPY,
    VacancyCopyContext,
    artifact_label,
    build_step_copy,
    summary_ui_copy,
)


def _leaf_keys(payload: dict[str, object], prefix: str = "") -> set[str]:
    keys: set[str] = set()
    for key, value in payload.items():
        dotted_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            keys.update(_leaf_keys(value, dotted_key))
        else:
            keys.add(dotted_key)
    return keys


def test_landing_copy_defaults_to_clear_german_value_prop() -> None:
    copy = build_step_copy(STEP_KEY_LANDING, language="de")

    assert copy.headline == "Vom Rollenbedarf zum Recruiting-Briefing."
    assert "Recruiting, HR und Hiring Teams" in copy.subheadline
    assert "Briefing-Cockpit" in copy.value_line
    assert copy.primary_cta == "Quelle in Briefing verwandeln"


def test_landing_copy_uses_role_aware_handoff_after_analysis() -> None:
    copy = build_step_copy(
        STEP_KEY_LANDING,
        language="de",
        context=VacancyCopyContext(role_title="Data Engineer"),
    )

    assert copy.headline == "Briefing-Cockpit für Data Engineer ist vorbereitet."
    assert "Nächste Aktion" in copy.subheadline


def test_company_copy_uses_dynamic_context_in_german() -> None:
    copy = build_step_copy(
        STEP_KEY_COMPANY,
        language="de",
        context=VacancyCopyContext(
            company_name="Accenture",
            role_title="Analytics Lead",
        ),
    )

    assert copy.headline == "Accenture als Arbeitgeber für Analytics Lead einordnen"
    assert "warum diese Rolle relevant ist" in copy.subheadline
    assert copy.value_line == "Hilft zu erklären, warum diese Rolle existiert."


def test_summary_copy_uses_gap_state_when_critical_gaps_exist() -> None:
    copy = build_step_copy(
        STEP_KEY_SUMMARY,
        language="de",
        context=VacancyCopyContext(
            role_title="Data Scientist",
            readiness_score=82,
            critical_gaps_count=3,
        ),
    )

    assert copy.headline == "Noch 3 Release-Blocker offen"
    assert "blockierenden Punkte" in copy.subheadline
    assert copy.primary_cta == "Recruiting-Unterlagen erstellen"


def test_summary_copy_uses_ready_state_when_fully_ready() -> None:
    copy = build_step_copy(
        STEP_KEY_SUMMARY,
        language="en",
        context=VacancyCopyContext(
            role_title="Data Scientist",
            readiness_score=100,
            critical_gaps_count=0,
        ),
    )

    assert copy.headline == "Ready for recruiting, interviews, and active sourcing"
    assert "All important facts are checked." in copy.subheadline
    assert copy.primary_cta == "Generate recruiting outputs"


def test_missing_context_falls_back_to_safe_labels() -> None:
    copy = build_step_copy(
        STEP_KEY_COMPANY,
        language="en",
        context=VacancyCopyContext(),
    )

    assert copy.headline == "Position the company as the employer for this role"
    assert "why this role matters" in copy.subheadline


def test_active_copy_contracts_have_de_en_shape_parity() -> None:
    for contract in (
        ARTIFACT_LABELS,
        SUMMARY_UI_COPY,
        SUMMARY_EXPORT_COPY,
        SUMMARY_PREVIEW_COPY,
        ESCO_UI_COPY,
        SALARY_UI_COPY,
    ):
        assert _leaf_keys(contract["de"]) == _leaf_keys(contract["en"])


def test_active_artifact_labels_exclude_archived_outputs() -> None:
    assert set(ARTIFACT_LABELS["de"]) == set(SUMMARY_ACTIVE_ARTIFACT_IDS)
    assert set(ARTIFACT_LABELS["en"]) == set(SUMMARY_ACTIVE_ARTIFACT_IDS)
    assert "employment_contract" not in ARTIFACT_LABELS["de"]
    assert artifact_label("job_ad", language="en") == "Job ad"


def test_release_gate_and_draft_copy_has_english_parity() -> None:
    assert (
        summary_ui_copy("release_gate.brief_missing_or_not_ready", language="en")
        == "Recruiting brief is missing or not ready yet."
    )
    assert summary_ui_copy("final_export.draft", language="en") == "Save draft"
    assert summary_ui_copy("live_preview.panel_title", language="en") == (
        "Live preview: recruiting outputs"
    )
