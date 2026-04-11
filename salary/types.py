"""Typed salary forecast input/output models."""

from __future__ import annotations

from typing import Any, Mapping

from pydantic import Field, model_validator

from schemas import StrictSchemaModel


def normalize_salary_quality_kind(kind: str) -> str:
    """Normalize quality-kind semantics while keeping backwards compatibility."""

    if kind == "confidence_score":
        return "data_quality_score"
    return kind


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


class SalaryEscoContext(StrictSchemaModel):
    """Optional ESCO context enrichments for salary forecast calculations."""

    occupation_uri: str | None = None
    skill_uris_must: list[str] = Field(default_factory=list)
    skill_uris_nice: list[str] = Field(default_factory=list)
    esco_version: str | None = None


class SalaryScenarioInputs(StrictSchemaModel):
    """Optional scenario inputs used for salary forecast what-if simulation."""

    location_city_override: str | None = None
    location_country_override: str | None = None
    search_radius_km: int = Field(default=50)
    remote_share_percent: int | None = None


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
    impact_eur: float = Field(default=0.0, description="Absolute impact in EUR.")
    category: str | None = Field(
        default=None, description="Optional category for grouped waterfall charts."
    )
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
    benchmark_year: int | None = None
    benchmark_source_label: str | None = None
    occupation_id: str | None = None
    region_id: str | None = None


class SalaryForecastQuality(StrictSchemaModel):
    """Quality/uncertainty marker for salary forecast outputs."""

    kind: str = Field(description="Quality indicator kind.")
    value: float = Field(description="Numeric quality score/value.")
    signals: list[str] = Field(
        default_factory=list,
        description="Structured signals used to derive the quality indicator.",
    )

    @model_validator(mode="before")
    @classmethod
    def _normalize_kind(cls, data: Any) -> Any:
        if isinstance(data, dict):
            kind = data.get("kind")
            if isinstance(kind, str):
                data = dict(data)
                data["kind"] = normalize_salary_quality_kind(kind)
        return data


def parse_salary_forecast_result(payload: Mapping[str, Any]) -> SalaryForecastResult:
    """Validate a salary-forecast payload against the strict schema contract."""

    return SalaryForecastResult.model_validate(payload, strict=True)
