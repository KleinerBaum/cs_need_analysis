"""Typed salary forecast input/output models."""

from __future__ import annotations

from pydantic import Field

from schemas import StrictSchemaModel


class SalaryScenarioOverrides(StrictSchemaModel):
    """Optional, bounded tweaks for scenario-based salary simulations."""

    requirements_multiplier_delta: float = Field(
        default=0.0,
        ge=-0.3,
        le=0.3,
        description="Absolute delta added to the requirements-based multiplier.",
    )
    seniority_multiplier_delta: float = Field(
        default=0.0,
        ge=-0.3,
        le=0.3,
        description="Absolute delta added to the seniority-based multiplier.",
    )
    remote_multiplier_delta: float = Field(
        default=0.0,
        ge=-0.2,
        le=0.2,
        description="Absolute delta added to the remote-policy multiplier.",
    )
    interview_multiplier_delta: float = Field(
        default=0.0,
        ge=-0.2,
        le=0.2,
        description="Absolute delta added to the interview-process multiplier.",
    )
    location_multiplier_factor: float = Field(
        default=1.0,
        ge=0.6,
        le=1.6,
        description="Factor multiplied with the location multiplier.",
    )
    title_multiplier_factor: float = Field(
        default=1.0,
        ge=0.6,
        le=1.6,
        description="Factor multiplied with the title multiplier.",
    )
    spread_factor_delta: float = Field(
        default=0.0,
        ge=-0.08,
        le=0.08,
        description="Absolute delta applied to the band spread factor.",
    )
    confidence_delta: int = Field(
        default=0,
        ge=-30,
        le=30,
        description="Absolute delta applied after confidence base scoring.",
    )


class SalaryForecastResult(StrictSchemaModel):
    """Structured output for salary forecast calculations."""

    forecast_min: float
    forecast_central: float
    forecast_max: float
    confidence: int

    answers_count: int
    must_have_count: int
    interview_steps: int
    location: str
    seniority: str
    job_title: str
    currency: str

    base_salary: float
    salary_multiplier: float
    spread_factor: float
