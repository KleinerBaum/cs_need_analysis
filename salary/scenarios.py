"""Scenario adapter helpers for salary-forecast UI inputs."""

from __future__ import annotations

from salary.types import SalaryScenarioOverrides

SALARY_SCENARIO_BASE = "base"
SALARY_SCENARIO_MARKET_UPSIDE = "market_upside"
SALARY_SCENARIO_COST_FOCUS = "cost_focus"

SALARY_SCENARIO_OPTIONS: tuple[str, str, str] = (
    SALARY_SCENARIO_BASE,
    SALARY_SCENARIO_MARKET_UPSIDE,
    SALARY_SCENARIO_COST_FOCUS,
)


def map_salary_scenario_to_overrides(scenario_name: str) -> SalaryScenarioOverrides:
    """Translate a business scenario key into bounded engine overrides."""

    mapping = {
        SALARY_SCENARIO_BASE: SalaryScenarioOverrides(),
        SALARY_SCENARIO_MARKET_UPSIDE: SalaryScenarioOverrides(
            requirements_multiplier_delta=0.04,
            seniority_multiplier_delta=0.03,
            remote_multiplier_delta=0.02,
            interview_multiplier_delta=0.01,
            location_multiplier_factor=1.05,
            title_multiplier_factor=1.04,
            spread_factor_delta=0.02,
            confidence_delta=5,
        ),
        SALARY_SCENARIO_COST_FOCUS: SalaryScenarioOverrides(
            requirements_multiplier_delta=-0.03,
            seniority_multiplier_delta=-0.02,
            remote_multiplier_delta=-0.01,
            interview_multiplier_delta=-0.01,
            location_multiplier_factor=0.96,
            title_multiplier_factor=0.97,
            spread_factor_delta=-0.01,
            confidence_delta=-4,
        ),
    }
    return mapping.get(scenario_name, mapping[SALARY_SCENARIO_BASE])
