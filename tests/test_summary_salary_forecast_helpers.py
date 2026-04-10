from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from zipfile import ZipFile
import base64
import io

from schemas import JobAdExtract, MoneyRange, RecruitmentStep


SUMMARY_PATH = Path(__file__).resolve().parents[1] / "wizard_pages" / "08_summary.py"
SPEC = spec_from_file_location("wizard_pages.page_08_summary", SUMMARY_PATH)
if SPEC is None or SPEC.loader is None:
    raise RuntimeError("Could not load summary page module")
SUMMARY_MODULE = module_from_spec(SPEC)
SPEC.loader.exec_module(SUMMARY_MODULE)  # type: ignore[attr-defined]


def test_estimate_salary_baseline_uses_range_average() -> None:
    job = JobAdExtract(
        job_title="Data Scientist",
        salary_range=MoneyRange(min=70000, max=90000, currency="EUR", period="yearly"),
    )

    assert SUMMARY_MODULE._estimate_salary_baseline(job) == 80000


def test_estimate_salary_baseline_uses_seniority_fallback() -> None:
    job = JobAdExtract(job_title="Engineer", seniority_level="Senior")

    assert SUMMARY_MODULE._estimate_salary_baseline(job) == 90000


def test_estimate_candidate_baseline_has_floor() -> None:
    job = JobAdExtract(
        must_have_skills=["Python", "SQL", "ML", "Spark", "Kubernetes", "Terraform"],
        certifications=["AWS", "GCP", "Azure"],
        languages=["Deutsch", "Englisch", "Französisch"],
    )

    baseline = SUMMARY_MODULE._estimate_candidate_baseline(job)

    assert baseline >= 8.0
    assert baseline == 55.0


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

    snapshot = SUMMARY_MODULE._build_salary_forecast_snapshot(job=job, answers=answers)

    assert snapshot["forecast"]["p10"] > 0
    assert snapshot["forecast"]["p50"] >= snapshot["forecast"]["p10"]
    assert snapshot["forecast"]["p90"] >= snapshot["forecast"]["p50"]
    assert snapshot["currency"] == "EUR"
    assert snapshot["period"] == "yearly"
    assert snapshot["location"] == "Deutschland"
    assert snapshot["must_have_count"] == 5
    assert snapshot["answers_count"] == 3
    assert 0.35 <= float(snapshot["quality"]["value"]) <= 1.0


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
    assert long_height <= 520
