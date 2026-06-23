from __future__ import annotations

from constants import SUMMARY_ACTIVE_ARTIFACT_IDS
from summary_artifacts import (
    artifact_display_label,
    brief_pipeline_status_for_state,
    to_canonical_artifact_id,
)


def test_active_summary_artifacts_are_focused_product_outputs() -> None:
    assert SUMMARY_ACTIVE_ARTIFACT_IDS == (
        "brief",
        "job_ad",
        "interview_hr",
        "interview_fach",
        "boolean_search",
    )


def test_to_canonical_artifact_id_accepts_current_and_legacy_ids() -> None:
    assert to_canonical_artifact_id("job_ad") == "job_ad"
    assert to_canonical_artifact_id("job_ad_generator") == "job_ad"
    assert to_canonical_artifact_id(" JOB_AD_GENERATOR ") == "job_ad"
    assert to_canonical_artifact_id("unknown") == ""
    assert to_canonical_artifact_id(None) == ""


def test_artifact_display_label_maps_known_ids_and_preserves_unknown_labels() -> None:
    assert artifact_display_label("job_ad") == "Stellenanzeige"
    assert artifact_display_label("interview_hr") == "HR-Sheet"
    assert artifact_display_label("interview_fach") == "Fachbereich-Sheet"
    assert artifact_display_label("boolean_search") == "Suchstrings"
    assert artifact_display_label("employment_contract") == "employment_contract"
    assert artifact_display_label("brief") == "Recruiting Brief"
    assert artifact_display_label("  custom_artifact  ") == "custom_artifact"
    assert artifact_display_label("") == ""
    assert artifact_display_label(123) == ""


def test_brief_pipeline_status_for_state_maps_known_states() -> None:
    assert brief_pipeline_status_for_state("current") == ("current", "Aktuell")
    assert brief_pipeline_status_for_state("stale") == ("stale", "Veraltet")
    assert brief_pipeline_status_for_state("missing") == ("open", "Fehlt")
    assert brief_pipeline_status_for_state("invalid") == ("blocked", "Ungültig")
    assert brief_pipeline_status_for_state("blocked") == ("blocked", "Wartet")
    assert brief_pipeline_status_for_state("unknown") == ("open", "Offen")
