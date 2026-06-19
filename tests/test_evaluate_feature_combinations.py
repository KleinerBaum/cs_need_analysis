from __future__ import annotations

from constants import ESCO_DATA_SOURCE_MODES, SUMMARY_ARTIFACT_IDS, UI_MODE_VALUES
from scripts.evaluate_feature_combinations import (
    COMBINATIONS,
    SCENARIOS,
    build_report,
    validate_matrix,
)


def test_feature_combination_matrix_uses_canonical_values() -> None:
    validate_matrix()

    assert {combination.ui_mode for combination in COMBINATIONS} <= set(UI_MODE_VALUES)
    assert {combination.esco_data_source_mode for combination in COMBINATIONS} <= set(
        ESCO_DATA_SOURCE_MODES
    )
    assert {
        artifact_id
        for combination in COMBINATIONS
        for artifact_id in combination.artifacts_enabled
    } <= set(SUMMARY_ARTIFACT_IDS)


def test_feature_combination_report_covers_planned_matrix() -> None:
    report = build_report()

    assert report["evaluation_mode"] == "offline_deterministic"
    assert len(report["scenarios"]) == 5
    assert len(report["combinations"]) == 5
    assert len(report["scores"]) == len(SCENARIOS) * len(COMBINATIONS)
    assert report["best_combination"]["combination_id"] in {
        combination.id for combination in COMBINATIONS
    }


def test_balanced_or_quality_stack_passes_success_criteria() -> None:
    report = build_report()
    passing_ids = {
        row["combination_id"]
        for row in report["ranking"]
        if row["passed_success_criteria"]
    }

    assert {"balanced", "quality"} <= passing_ids
    assert report["best_combination"]["usable_summary_count"] >= 4
