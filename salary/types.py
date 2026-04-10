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

    forecast: SalaryForecastBand
    currency: str
    period: str
    quality: SalaryForecastQuality
    drivers: list[SalaryForecastDriver]
    provenance: SalaryForecastProvenance

    answers_count: int
    must_have_count: int
    interview_steps: int
    location: str
    seniority: str
    job_title: str

    base_salary: float
    salary_multiplier: float
    spread_factor: float


class SalaryForecastBand(StrictSchemaModel):
    """Percentile band for salary forecast outputs."""

    p10: float = Field(description="10th percentile salary estimate.")
    p50: float = Field(description="50th percentile (median) salary estimate.")
    p90: float = Field(description="90th percentile salary estimate.")


class SalaryForecastDriver(StrictSchemaModel):
    """Structured explanation entry for one forecast driver."""

    key: str = Field(description="Stable machine-readable driver key.")
    label: str = Field(description="Human-readable driver label.")
    direction: str = Field(
        description="Direction of impact, e.g. 'up', 'down', or 'neutral'."
    )
    impact: float = Field(description="Relative driver impact score.")
    detail: str = Field(description="Short explanation of the driver effect.")


class SalaryForecastProvenance(StrictSchemaModel):
    """Provenance metadata for salary forecast generation."""

    engine: str = Field(description="Forecast engine identifier.")
    benchmark_version: str = Field(description="Benchmark dataset version identifier.")
    occupation_mapping: str = Field(
        description="Occupation mapping key or strategy identifier."
    )
    region_mapping: str = Field(
        description="Region mapping key or strategy identifier."
    )


class SalaryForecastQuality(StrictSchemaModel):
    """Quality/uncertainty marker for salary forecast outputs."""

    kind: str = Field(description="Quality indicator kind.")
    value: float = Field(description="Numeric quality score/value.")
    signals: list[str] = Field(
        default_factory=list,
        description="Structured signals used to derive the quality indicator.",
    )
