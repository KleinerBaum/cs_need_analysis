"""Salary domain package."""

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


def __getattr__(name: str):
    if name in {"compute_salary_forecast", "estimate_salary_baseline"}:
        from salary.engine import compute_salary_forecast, estimate_salary_baseline

        mapping = {
            "compute_salary_forecast": compute_salary_forecast,
            "estimate_salary_baseline": estimate_salary_baseline,
        }
        return mapping[name]

    if name in {
        "normalize_esco_uri",
        "extract_esco_context",
        "compute_esco_skill_coverage_signals",
    }:
        from salary.features_esco import (
            compute_esco_skill_coverage_signals,
            extract_esco_context,
            normalize_esco_uri,
        )

        mapping = {
            "normalize_esco_uri": normalize_esco_uri,
            "extract_esco_context": extract_esco_context,
            "compute_esco_skill_coverage_signals": compute_esco_skill_coverage_signals,
        }
        return mapping[name]

    if name in {
        "SalaryForecastResult",
        "SalaryScenarioOverrides",
        "parse_salary_forecast_result",
    }:
        from salary.types import (
            SalaryForecastResult,
            SalaryScenarioOverrides,
            parse_salary_forecast_result,
        )

        mapping = {
            "SalaryForecastResult": SalaryForecastResult,
            "SalaryScenarioOverrides": SalaryScenarioOverrides,
            "parse_salary_forecast_result": parse_salary_forecast_result,
        }
        return mapping[name]

    raise AttributeError(f"module 'salary' has no attribute {name!r}")
