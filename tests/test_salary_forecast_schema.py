from __future__ import annotations

import pytest
from pydantic import ValidationError

from salary.engine import compute_salary_forecast
from salary.types import parse_salary_forecast_result
from schemas import JobAdExtract


def _valid_payload() -> dict[str, object]:
    job = JobAdExtract(job_title="Engineer", location_country="Deutschland")
    return compute_salary_forecast(
        job_extract=job, answers={"team_size": 4}
    ).model_dump()


def test_parse_salary_forecast_result_accepts_valid_payload() -> None:
    payload = _valid_payload()

    parsed = parse_salary_forecast_result(payload)

    assert parsed.forecast.p10 > 0
    assert parsed.forecast.p50 >= parsed.forecast.p10
    assert parsed.forecast.p90 >= parsed.forecast.p50


def test_parse_salary_forecast_result_rejects_missing_required_field() -> None:
    payload = _valid_payload()
    payload.pop("currency")

    with pytest.raises(ValidationError, match="currency"):
        parse_salary_forecast_result(payload)


def test_parse_salary_forecast_result_rejects_wrong_type_in_strict_mode() -> None:
    payload = _valid_payload()
    payload["answers_count"] = "3"

    with pytest.raises(ValidationError, match="answers_count"):
        parse_salary_forecast_result(payload)


def test_parse_salary_forecast_result_rejects_extra_fields() -> None:
    payload = _valid_payload()
    payload["forecast_min"] = 12345

    with pytest.raises(ValidationError, match="forecast_min"):
        parse_salary_forecast_result(payload)


def test_parse_salary_forecast_result_normalizes_legacy_confidence_kind() -> None:
    payload = _valid_payload()
    quality = payload.get("quality")
    assert isinstance(quality, dict)
    quality["kind"] = "confidence_score"

    parsed = parse_salary_forecast_result(payload)

    assert parsed.quality.kind == "data_quality_score"
