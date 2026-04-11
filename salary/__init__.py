"""Salary domain package."""

from salary.engine import compute_salary_forecast, estimate_salary_baseline
from salary.features_esco import (
    compute_esco_skill_coverage_signals,
    extract_esco_context,
    normalize_esco_uri,
)
from salary.types import (
    SalaryForecastResult,
    SalaryScenarioOverrides,
    parse_salary_forecast_result,
)

__all__ = [
    "compute_salary_forecast",
    "estimate_salary_baseline",
    "SalaryForecastResult",
    "SalaryScenarioOverrides",
    "parse_salary_forecast_result",
    "normalize_esco_uri",
    "extract_esco_context",
    "compute_esco_skill_coverage_signals",
]
