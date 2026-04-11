from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from zipfile import ZipFile
import base64
import io
from typing import Any, Literal, cast

from streamlit.errors import StreamlitAPIException

from constants import SSKey
from salary.engine import compute_salary_forecast
from salary.scenarios import (
    SALARY_SCENARIO_BASE,
    SALARY_SCENARIO_COST_FOCUS,
    SALARY_SCENARIO_MARKET_UPSIDE,
    map_salary_scenario_to_overrides,
)
from salary.types import SalaryScenarioOverrides
from schemas import JobAdExtract, MoneyRange, RecruitmentStep


SUMMARY_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "08_summary.py"
SALARY_PANEL_PATH = (
    Path(__file__).resolve().parents[1] / "wizard_pages" / "salary_forecast_panel.py"
)
SPEC = spec_from_file_location("wizard_pages.page_08_summary", SUMMARY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load summary page module")
SUMMARY_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(SUMMARY_MODULE)  # type: ignore[attr-defined]

SALARY_PANEL_SPEC = spec_from_file_location(
    "wizard_pages.salary_forecast_panel", SALARY_PANEL_PATH
)
if SALARY_PANEL_SPEC is None or SALARY_PANEL_SPEC.loader is None:
    raise RuntimeError("Could not load salary forecast panel module")
SALARY_PANEL_MODULE = module_from_spec(SALARY_PANEL_SPEC)
SALARY_PANEL_SPEC.loader.exec_module(SALARY_PANEL_MODULE)  # type: ignore[attr-defined]


def test_salary_forecast_engine_applies_scenario_overrides() -> None:
    job = JobAdExtract(
        job_title="Data Scientist",
        seniority_level="Senior",
        salary_range=MoneyRange(min=70000, max=90000, currency="EUR", period="yearly"),
    )
    answers = {"team_size": 8}

    baseline = compute_salary_forecast(job_extract=job, answers=answers)
    boosted = compute_salary_forecast(
        job_extract=job,
        answers=answers,
        scenario_overrides=SalaryScenarioOverrides(
            seniority_multiplier_delta=0.1,
            title_multiplier_factor=1.1,
            confidence_delta=10,
        ),
    )

    assert boosted.forecast.p50 > baseline.forecast.p50
    assert boosted.quality.value >= baseline.quality.value


def test_map_salary_scenario_to_overrides_uses_expected_presets() -> None:
    base = map_salary_scenario_to_overrides(SALARY_SCENARIO_BASE)
    market = map_salary_scenario_to_overrides(SALARY_SCENARIO_MARKET_UPSIDE)
    cost = map_salary_scenario_to_overrides(SALARY_SCENARIO_COST_FOCUS)
    fallback = map_salary_scenario_to_overrides("unknown")

    assert base == SalaryScenarioOverrides()
    assert market.requirements_multiplier_delta > 0
    assert market.location_multiplier_factor > 1.0
    assert cost.requirements_multiplier_delta < 0
    assert cost.location_multiplier_factor < 1.0
    assert fallback == SalaryScenarioOverrides()


def test_build_salary_forecast_snapshot_uses_job_inputs() -> None:
    job = JobAdExtract(
        job_title="Principal Engineer",
        seniority_level="Principal",
        remote_policy="Remote-first",
        location_country="Deutschland",
        must_have_skills=["Python", "Go", "Kubernetes", "AWS", "Security"],
        recruitment_steps=[
            RecruitmentStep(name="Screen"),
            RecruitmentStep(name="Tech"),
            RecruitmentStep(name="Final"),
        ],
        salary_range=MoneyRange(min=95000, max=125000, currency="EUR", period="yearly"),
    )
    answers = {"team_size": 8, "benefits": "Top", "work_mode": "hybrid"}

    snapshot = SALARY_PANEL_MODULE._build_salary_forecast_snapshot(
        job=job, answers=answers
    )

    assert snapshot["forecast"]["p10"] > 0
    assert snapshot["forecast"]["p50"] >= snapshot["forecast"]["p10"]
    assert snapshot["forecast"]["p90"] >= snapshot["forecast"]["p50"]
    assert snapshot["currency"] == "EUR"
    assert snapshot["period"] == "yearly"
    assert snapshot["location"] == "Deutschland"
    assert snapshot["must_have_count"] == 5
    assert snapshot["answers_count"] == 3
    assert 0.35 <= float(snapshot["quality"]["value"]) <= 1.0


def test_build_salary_forecast_snapshot_uses_compute_salary_forecast_only() -> None:
    job = JobAdExtract(job_title="Data Engineer")
    answers: dict[str, Any] = {"team_size": 4}
    calls: list[dict[str, Any]] = []
    baseline = compute_salary_forecast(job_extract=job, answers=answers)

    def _fake_compute_salary_forecast(
        *,
        job_extract: JobAdExtract,
        answers: dict[str, Any],
        scenario_overrides: SalaryScenarioOverrides | None = None,
        scenario_inputs: Any | None = None,
    ) -> Any:
        calls.append(
            {
                "job_title": job_extract.job_title,
                "answers": answers,
                "scenario_overrides": scenario_overrides,
                "scenario_inputs": scenario_inputs,
            }
        )
        return baseline

    panel_module = cast(Any, SALARY_PANEL_MODULE)
    original_compute_salary_forecast = panel_module.compute_salary_forecast
    panel_module.compute_salary_forecast = _fake_compute_salary_forecast
    overrides = map_salary_scenario_to_overrides(SALARY_SCENARIO_MARKET_UPSIDE)
    try:
        snapshot = SALARY_PANEL_MODULE._build_salary_forecast_snapshot(
            job=job,
            answers=answers,
            scenario_name=SALARY_SCENARIO_MARKET_UPSIDE,
            scenario_overrides=overrides,
        )
    finally:
        panel_module.compute_salary_forecast = original_compute_salary_forecast

    assert len(calls) == 1
    assert calls[0]["scenario_overrides"] == overrides
    assert snapshot["forecast_result"]["forecast"]["p50"] == baseline.forecast.p50


def test_summary_source_hides_engine_internal_delta_widgets() -> None:
    source = SUMMARY_PATH.read_text(encoding="utf-8")

    assert "Requirements Δ" not in source
    assert "Seniority Δ" not in source
    assert "Remote Δ" not in source
    assert "Interview Δ" not in source
    assert "Location-Faktor" not in source
    assert "Titel-Faktor" not in source
    assert "Spread Δ" not in source
    assert "Confidence Δ" not in source
    assert "_render_sidebar_salary_forecast" not in source
    assert "Salary Forecast" not in source


def test_summary_source_uses_city_and_country_salary_overrides() -> None:
    source = SALARY_PANEL_PATH.read_text(encoding="utf-8")

    assert "SALARY_SCENARIO_LOCATION_CITY_OVERRIDE" in source
    assert "SALARY_SCENARIO_LOCATION_COUNTRY_OVERRIDE" in source
    assert "location_city_override" in source
    assert "location_country_override" in source


def test_normalize_logo_payload_rejects_unsupported_type() -> None:
    class FakeUpload:
        name = "logo.svg"
        type = "image/svg+xml"

        def getvalue(self) -> bytes:
            return b"<svg></svg>"

    assert SUMMARY_MODULE._normalize_logo_payload(FakeUpload()) is None


def test_build_selection_rows_formats_language_requirements() -> None:
    job = JobAdExtract(job_title="Data Engineer")
    answers = {
        "sprachen": [
            {"language": "Deutsch", "level": "C1"},
            {"language": "Englisch", "level": "B2"},
        ]
    }

    rows = SUMMARY_MODULE._build_selection_rows(job=job, answers=answers)
    language_rows = [
        row
        for row in rows
        if row["Kategorie"] == "Manager-Input" and row["Feld"] == "sprachen"
    ]

    assert len(language_rows) == 2
    assert language_rows[0]["Wert"] == "Deutsch (C1)"
    assert language_rows[1]["Wert"] == "Englisch (B2)"


def test_job_ad_docx_contains_logo_media_when_logo_present() -> None:
    png_bytes = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO5vS3wAAAAASUVORK5CYII="
    )
    SUMMARY_MODULE.st.session_state[SUMMARY_MODULE.SSKey.SUMMARY_LOGO.value] = {
        "name": "logo.png",
        "mime_type": "image/png",
        "bytes": png_bytes,
    }
    job_ad = SUMMARY_MODULE.JobAdGenerationResult(
        headline="Titel",
        target_group=["Data Scientists"],
        agg_checklist=["neutral wording"],
        job_ad_text="Text",
    )

    docx_bytes = SUMMARY_MODULE._job_ad_to_docx_bytes(job_ad, styleguide="")

    with ZipFile(io.BytesIO(docx_bytes), "r") as archive:
        media_entries = [
            name for name in archive.namelist() if name.startswith("word/media/")
        ]
    assert media_entries


def test_sanitize_generated_job_ad_removes_embedded_sections() -> None:
    source = SUMMARY_MODULE.JobAdGenerationResult(
        headline="Baggerfahrer (m/w/d)",
        target_group=["Baggerfahrer/innen"],
        agg_checklist=["Geschlechtsneutrale Ansprache vorhanden."],
        job_ad_text=(
            "Wir suchen Verstärkung für unser Team.\n\n"
            "Hinweis: Startdatum ist nicht angegeben.\n"
            "Zielgruppe\n"
            "- Galabauer/innen\n"
            "AGG-Checkliste\n"
            "- Fehlende Angaben: Bewerbungsschluss nicht angegeben.\n"
        ),
    )

    sanitized, notes = SUMMARY_MODULE._sanitize_generated_job_ad(source)

    assert sanitized.job_ad_text == "Wir suchen Verstärkung für unser Team."
    assert sanitized.target_group == ["Baggerfahrer/innen", "Galabauer/innen"]
    assert (
        "Fehlende Angaben: Bewerbungsschluss nicht angegeben."
        in sanitized.agg_checklist
    )
    assert notes == ["Startdatum ist nicht angegeben."]


def test_estimate_text_area_height_scales_with_job_ad_length() -> None:
    short_height = SUMMARY_MODULE._estimate_text_area_height("Kurz")
    long_height = SUMMARY_MODULE._estimate_text_area_height("\n".join(["Zeile"] * 50))

    assert short_height >= 160
    assert long_height > short_height


def test_salary_panel_chart_selection_uses_pending_keys_on_rerun(monkeypatch) -> None:
    panel_module = cast(Any, SALARY_PANEL_MODULE)

    class _LockedSessionState(dict[str, Any]):
        def __init__(self) -> None:
            super().__init__()
            self.locked_keys: set[str] = set()

        def __setitem__(self, key: str, value: Any) -> None:
            if key in self.locked_keys:
                raise StreamlitAPIException(
                    f"Widget key '{key}' cannot be mutated post-render."
                )
            super().__setitem__(key, value)

    class _FakeColumn:
        def __enter__(self) -> "_FakeColumn":
            return self

        def __exit__(self, exc_type: Any, exc: Any, tb: Any) -> Literal[False]:
            return False

        def metric(self, *_args: Any, **_kwargs: Any) -> None:
            return None

    class _FakeStreamlit:
        def __init__(self) -> None:
            self.session_state = _LockedSessionState()
            self._selections_by_run = [
                {
                    "salary_tornado_chart": {
                        "selection": {
                            "points": [{"y": "Python", "customdata": "skill_python"}]
                        }
                    }
                },
                {},
            ]
            self._run_index = 0

        def begin_run(self) -> None:
            self.session_state.locked_keys.clear()

        def _register_widget(self, key: str, default: Any) -> Any:
            if key not in self.session_state:
                self.session_state[key] = default
            self.session_state.locked_keys.add(key)
            return self.session_state[key]

        def subheader(self, *_args: Any, **_kwargs: Any) -> None:
            return None

        def columns(self, spec: Any) -> tuple[Any, ...]:
            count = spec if isinstance(spec, int) else len(spec)
            return tuple(_FakeColumn() for _ in range(count))

        def radio(
            self, _label: str, *, options: list[str], key: str, **_kwargs: Any
        ) -> Any:
            return self._register_widget(key, options[0])

        def multiselect(
            self, _label: str, *, default: list[str], key: str, **_kwargs: Any
        ) -> Any:
            return self._register_widget(key, list(default))

        def text_input(self, _label: str, *, key: str, **_kwargs: Any) -> str:
            return str(self._register_widget(key, ""))

        def slider(
            self, _label: str, *, key: str, min_value: int, **_kwargs: Any
        ) -> int:
            return int(self._register_widget(key, min_value))

        def selectbox(
            self, _label: str, *, options: list[str], key: str, **_kwargs: Any
        ) -> str:
            return str(self._register_widget(key, options[0]))

        def plotly_chart(self, _fig: Any, *, key: str, **_kwargs: Any) -> Any:
            selections = self._selections_by_run[
                min(self._run_index, len(self._selections_by_run) - 1)
            ]
            return selections.get(key)

        def metric(self, *_args: Any, **_kwargs: Any) -> None:
            return None

        def caption(self, *_args: Any, **_kwargs: Any) -> None:
            return None

        def markdown(self, *_args: Any, **_kwargs: Any) -> None:
            return None

        def dataframe(self, *_args: Any, **_kwargs: Any) -> None:
            return None

    class _ForecastValue:
        p10 = 90_000
        p50 = 100_000
        p90 = 120_000

        def model_dump(self, mode: str = "json") -> dict[str, int]:
            return {"p10": self.p10, "p50": self.p50, "p90": self.p90}

    class _QualityValue:
        value = 0.8
        kind = "medium"

    class _ForecastResult:
        period = "yearly"
        currency = "EUR"
        forecast = _ForecastValue()
        quality = _QualityValue()

        def model_dump(self, mode: str = "json") -> dict[str, Any]:
            return {
                "period": self.period,
                "currency": self.currency,
                "forecast": self.forecast.model_dump(mode=mode),
                "quality": {"value": self.quality.value, "kind": self.quality.kind},
            }

    fake_rows = [
        {
            "group": "skill_delta",
            "delta_p50": 2000,
            "label": "Python",
            "row_id": "skill_python",
        },
        {
            "group": "location_compare",
            "label": "Berlin",
            "p10": 90000,
            "p50": 100000,
            "p90": 120000,
            "row_id": "loc_berlin",
        },
        {
            "group": "radius_sweep",
            "radius_km": 50,
            "p50": 100000,
            "row_id": "radius_50",
        },
        {
            "group": "remote_share_sweep",
            "remote_share_percent": 0,
            "p50": 100000,
            "row_id": "remote_0",
        },
        {
            "group": "seniority_sweep",
            "label": "Senior",
            "p50": 100000,
            "row_id": "senior",
        },
    ]

    fake_st = _FakeStreamlit()
    monkeypatch.setattr(panel_module, "st", fake_st)
    monkeypatch.setattr(
        panel_module, "compute_salary_forecast", lambda **_kwargs: _ForecastResult()
    )
    monkeypatch.setattr(
        panel_module,
        "build_salary_scenario_lab_rows",
        lambda **_kwargs: list(fake_rows),
    )

    job = JobAdExtract(job_title="Data Engineer")
    answers: dict[str, Any] = {}

    fake_st.begin_run()
    panel_module.render_salary_forecast_panel(job, answers)
    assert (
        fake_st.session_state[SSKey.SALARY_SCENARIO_APPLY_PENDING_UPDATE.value] is True
    )
    assert fake_st.session_state[SSKey.SALARY_SCENARIO_SKILLS_ADD.value] == []

    fake_st._run_index = 1
    fake_st.begin_run()
    panel_module.render_salary_forecast_panel(job, answers)
    assert (
        fake_st.session_state[SSKey.SALARY_SCENARIO_APPLY_PENDING_UPDATE.value] is False
    )
    assert fake_st.session_state[SSKey.SALARY_SCENARIO_PENDING_SKILLS_ADD.value] is None
    assert fake_st.session_state[SSKey.SALARY_SCENARIO_SKILLS_ADD.value] == ["Python"]
