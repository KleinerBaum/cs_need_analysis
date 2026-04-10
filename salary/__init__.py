"""Salary domain package."""

from salary.engine import compute_salary_forecast, estimate_salary_baseline
from salary.types import SalaryForecastResult, SalaryScenarioOverrides

__all__ = [
    "compute_salary_forecast",
    "estimate_salary_baseline",
    "SalaryForecastResult",
    "SalaryScenarioOverrides",
]
