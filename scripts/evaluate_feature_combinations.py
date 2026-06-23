"""Evaluate app feature-stack combinations against synthetic vacancy scenarios.

The script is deterministic and offline-only. It does not call OpenAI, ESCO, RAG,
homepage research, or export generation services. Its output is intended as a
repeatable decision aid before running manual or instrumented app sessions.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
import json
from pathlib import Path
import sys
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from constants import (  # noqa: E402
    ESCO_ANCHOR_STATE_ANCHORED,
    ESCO_ANCHOR_STATE_DEGRADED,
    ESCO_DATA_SOURCE_MODES,
    SUMMARY_ACTIVE_ARTIFACT_IDS,
    UI_MODE_VALUES,
)


@dataclass(frozen=True)
class VacancyScenario:
    id: str
    label: str
    complexity: int
    structured_input_quality: int
    requires_regulatory_context: bool
    requires_salary_context: bool
    sparse_salary_data: bool
    homepage_evidence_value: int


@dataclass(frozen=True)
class FeatureCombination:
    id: str
    label: str
    ui_mode: str
    esco_data_source_mode: str
    esco_anchor_state: str
    openai_mode: str
    esco_rag_enabled: bool
    esco_matrix_enabled: bool
    salary_forecast_enabled: bool
    homepage_enrichment_enabled: bool
    artifacts_enabled: tuple[str, ...]


@dataclass(frozen=True)
class ScenarioScore:
    scenario_id: str
    combination_id: str
    total_score: float
    fact_quality: float
    user_effort: float
    recruiting_value: float
    robustness: float
    cost_latency: float
    export_readiness: float
    critical_gaps: int


WEIGHTS: dict[str, float] = {
    "fact_quality": 0.24,
    "user_effort": 0.14,
    "recruiting_value": 0.24,
    "robustness": 0.14,
    "cost_latency": 0.10,
    "export_readiness": 0.14,
}


SCENARIOS: tuple[VacancyScenario, ...] = (
    VacancyScenario(
        id="standard_role",
        label="Standard commercial role with structured jobspec",
        complexity=2,
        structured_input_quality=4,
        requires_regulatory_context=False,
        requires_salary_context=True,
        sparse_salary_data=False,
        homepage_evidence_value=2,
    ),
    VacancyScenario(
        id="expert_role",
        label="Complex expert role with broad stakeholder context",
        complexity=5,
        structured_input_quality=3,
        requires_regulatory_context=False,
        requires_salary_context=True,
        sparse_salary_data=False,
        homepage_evidence_value=3,
    ),
    VacancyScenario(
        id="unstructured_jobspec",
        label="Sparse and unstructured job ad input",
        complexity=4,
        structured_input_quality=1,
        requires_regulatory_context=False,
        requires_salary_context=True,
        sparse_salary_data=True,
        homepage_evidence_value=4,
    ),
    VacancyScenario(
        id="regulated_role",
        label="Regulated profession with compliance-sensitive requirements",
        complexity=5,
        structured_input_quality=3,
        requires_regulatory_context=True,
        requires_salary_context=True,
        sparse_salary_data=False,
        homepage_evidence_value=3,
    ),
    VacancyScenario(
        id="salary_sparse_role",
        label="Role with limited salary benchmark coverage",
        complexity=3,
        structured_input_quality=2,
        requires_regulatory_context=False,
        requires_salary_context=True,
        sparse_salary_data=True,
        homepage_evidence_value=2,
    ),
)


COMBINATIONS: tuple[FeatureCombination, ...] = (
    FeatureCombination(
        id="baseline",
        label="Baseline",
        ui_mode="standard",
        esco_data_source_mode="live_api",
        esco_anchor_state=ESCO_ANCHOR_STATE_DEGRADED,
        openai_mode="extract_and_question_plan",
        esco_rag_enabled=False,
        esco_matrix_enabled=False,
        salary_forecast_enabled=True,
        homepage_enrichment_enabled=False,
        artifacts_enabled=("brief", "job_ad"),
    ),
    FeatureCombination(
        id="balanced",
        label="Balanced",
        ui_mode="standard",
        esco_data_source_mode="hybrid",
        esco_anchor_state=ESCO_ANCHOR_STATE_ANCHORED,
        openai_mode="extract_and_question_plan",
        esco_rag_enabled=False,
        esco_matrix_enabled=False,
        salary_forecast_enabled=True,
        homepage_enrichment_enabled=True,
        artifacts_enabled=SUMMARY_ACTIVE_ARTIFACT_IDS,
    ),
    FeatureCombination(
        id="quality",
        label="Quality",
        ui_mode="expert",
        esco_data_source_mode="hybrid",
        esco_anchor_state=ESCO_ANCHOR_STATE_ANCHORED,
        openai_mode="extract_and_question_plan",
        esco_rag_enabled=True,
        esco_matrix_enabled=True,
        salary_forecast_enabled=True,
        homepage_enrichment_enabled=True,
        artifacts_enabled=SUMMARY_ACTIVE_ARTIFACT_IDS,
    ),
    FeatureCombination(
        id="fast",
        label="Fast",
        ui_mode="quick",
        esco_data_source_mode="live_api",
        esco_anchor_state=ESCO_ANCHOR_STATE_DEGRADED,
        openai_mode="extract_and_question_plan",
        esco_rag_enabled=False,
        esco_matrix_enabled=False,
        salary_forecast_enabled=False,
        homepage_enrichment_enabled=False,
        artifacts_enabled=("brief", "job_ad"),
    ),
    FeatureCombination(
        id="offline_resilience",
        label="Offline/resilience",
        ui_mode="standard",
        esco_data_source_mode="offline_index",
        esco_anchor_state=ESCO_ANCHOR_STATE_ANCHORED,
        openai_mode="dry_run_or_cached",
        esco_rag_enabled=False,
        esco_matrix_enabled=False,
        salary_forecast_enabled=True,
        homepage_enrichment_enabled=False,
        artifacts_enabled=("brief", "job_ad", "boolean_search"),
    ),
)


def _clamp_score(value: float) -> float:
    return round(max(0.0, min(5.0, value)), 2)


def validate_matrix() -> None:
    invalid_ui_modes = {combo.ui_mode for combo in COMBINATIONS} - set(UI_MODE_VALUES)
    if invalid_ui_modes:
        raise ValueError(f"Invalid UI modes: {sorted(invalid_ui_modes)}")

    invalid_esco_modes = {
        combo.esco_data_source_mode for combo in COMBINATIONS
    } - set(ESCO_DATA_SOURCE_MODES)
    if invalid_esco_modes:
        raise ValueError(f"Invalid ESCO data source modes: {sorted(invalid_esco_modes)}")

    invalid_artifacts = {
        artifact_id
        for combo in COMBINATIONS
        for artifact_id in combo.artifacts_enabled
        if artifact_id not in SUMMARY_ACTIVE_ARTIFACT_IDS
    }
    if invalid_artifacts:
        raise ValueError(f"Invalid artifact IDs: {sorted(invalid_artifacts)}")


def score_scenario(
    scenario: VacancyScenario, combination: FeatureCombination
) -> ScenarioScore:
    anchored = combination.esco_anchor_state == ESCO_ANCHOR_STATE_ANCHORED
    full_artifacts = set(combination.artifacts_enabled) == set(
        SUMMARY_ACTIVE_ARTIFACT_IDS
    )
    artifact_depth = len(combination.artifacts_enabled) / len(
        SUMMARY_ACTIVE_ARTIFACT_IDS
    )

    fact_quality = 2.2 + scenario.structured_input_quality * 0.35
    if anchored:
        fact_quality += 0.75
    if combination.homepage_enrichment_enabled:
        fact_quality += scenario.homepage_evidence_value * 0.18
    if combination.esco_rag_enabled and scenario.complexity >= 4:
        fact_quality += 0.25

    user_effort = {
        "quick": 4.6,
        "standard": 3.8,
        "expert": 2.6,
    }[combination.ui_mode]
    user_effort -= max(0, scenario.complexity - 3) * 0.25
    if combination.homepage_enrichment_enabled:
        user_effort += 0.25
    if combination.esco_rag_enabled or combination.esco_matrix_enabled:
        user_effort -= 0.15

    recruiting_value = 2.0 + artifact_depth * 1.3
    if anchored:
        recruiting_value += 0.65
    if combination.salary_forecast_enabled and scenario.requires_salary_context:
        recruiting_value += 0.45
    if combination.homepage_enrichment_enabled:
        recruiting_value += 0.35
    if combination.esco_rag_enabled and scenario.complexity >= 4:
        recruiting_value += 0.25
    if combination.esco_matrix_enabled and scenario.sparse_salary_data:
        recruiting_value += 0.20

    robustness = 3.2
    if combination.esco_data_source_mode in {"hybrid", "offline_index"}:
        robustness += 0.75
    if combination.openai_mode == "dry_run_or_cached":
        robustness += 0.45
    if combination.esco_rag_enabled:
        robustness -= 0.25
    if combination.homepage_enrichment_enabled:
        robustness -= 0.15

    cost_latency = {
        "quick": 4.4,
        "standard": 3.7,
        "expert": 2.7,
    }[combination.ui_mode]
    if combination.esco_rag_enabled:
        cost_latency -= 0.35
    if combination.homepage_enrichment_enabled:
        cost_latency -= 0.25
    if full_artifacts:
        cost_latency -= 0.45
    if combination.openai_mode == "dry_run_or_cached":
        cost_latency += 0.50

    export_readiness = 2.4 + artifact_depth * 1.4
    if anchored:
        export_readiness += 0.65
    if full_artifacts:
        export_readiness += 0.35

    critical_gaps = 0
    if scenario.requires_regulatory_context and not anchored:
        critical_gaps += 1
    if scenario.requires_salary_context and not combination.salary_forecast_enabled:
        critical_gaps += 1
    if scenario.complexity >= 4 and combination.ui_mode == "quick":
        critical_gaps += 1
    if scenario.structured_input_quality <= 2 and not combination.homepage_enrichment_enabled:
        critical_gaps += 1
    if not full_artifacts and scenario.complexity >= 4:
        critical_gaps += 1

    scores = {
        "fact_quality": _clamp_score(fact_quality),
        "user_effort": _clamp_score(user_effort),
        "recruiting_value": _clamp_score(recruiting_value),
        "robustness": _clamp_score(robustness),
        "cost_latency": _clamp_score(cost_latency),
        "export_readiness": _clamp_score(export_readiness),
    }
    total = round(
        sum(scores[key] * weight for key, weight in WEIGHTS.items())
        - critical_gaps * 0.25,
        3,
    )

    return ScenarioScore(
        scenario_id=scenario.id,
        combination_id=combination.id,
        total_score=total,
        critical_gaps=critical_gaps,
        **scores,
    )


def build_report() -> dict[str, Any]:
    validate_matrix()
    scenario_scores = [
        score_scenario(scenario, combination)
        for combination in COMBINATIONS
        for scenario in SCENARIOS
    ]
    ranking = []
    for combination in COMBINATIONS:
        scores = [
            score
            for score in scenario_scores
            if score.combination_id == combination.id
        ]
        usable_summary_count = sum(1 for score in scores if score.critical_gaps == 0)
        average_score = round(
            sum(score.total_score for score in scores) / len(scores),
            3,
        )
        ranking.append(
            {
                "combination_id": combination.id,
                "label": combination.label,
                "average_score": average_score,
                "usable_summary_count": usable_summary_count,
                "passed_success_criteria": usable_summary_count >= 4,
            }
        )
    ranking.sort(
        key=lambda row: (
            row["passed_success_criteria"],
            row["average_score"],
            row["usable_summary_count"],
        ),
        reverse=True,
    )

    return {
        "schema_version": "2026-06-19",
        "evaluation_mode": "offline_deterministic",
        "weights": WEIGHTS,
        "success_criteria": {
            "minimum_usable_summaries": 4,
            "scenario_count": len(SCENARIOS),
            "critical_gap_threshold": 0,
        },
        "scenarios": [asdict(scenario) for scenario in SCENARIOS],
        "combinations": [asdict(combination) for combination in COMBINATIONS],
        "scores": [asdict(score) for score in scenario_scores],
        "ranking": ranking,
        "best_combination": ranking[0],
        "privacy_notes": [
            "Scenarios are synthetic and contain no personal data.",
            "The report contains only aggregate scores, canonical IDs, and feature flags.",
            "No prompts, raw vacancy text, URLs, credentials, or API responses are emitted.",
        ],
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Evaluate feature-stack combinations for the vacancy intake app."
    )
    parser.add_argument(
        "--json-only",
        action="store_true",
        help="Print only JSON output.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    report = build_report()
    if args.json_only:
        print(json.dumps(report, ensure_ascii=False))
        return

    best = report["best_combination"]
    print(
        "Feature-combination evaluation completed: "
        f"best={best['combination_id']}, "
        f"score={best['average_score']}, "
        f"usable_summaries={best['usable_summary_count']}/{len(SCENARIOS)}"
    )
    print(json.dumps(report, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
