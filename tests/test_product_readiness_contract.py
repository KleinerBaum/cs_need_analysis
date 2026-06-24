from __future__ import annotations

from pathlib import Path

import esco_client
import homepage_research
import llm_client
from constants import (
    SUMMARY_ACTIVE_ARTIFACT_IDS,
    STEP_KEY_BENEFITS,
    STEP_KEY_COMPANY,
    STEP_KEY_INTERVIEW,
    STEP_KEY_LANDING,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
    STEP_KEY_SUMMARY,
)
from offer_decision import build_offer_decision_context
from occupation_context import classify_occupation_context
from schemas import JobAdExtract, MoneyRange, WorkArrangement
from summary_artifacts import artifact_display_label
from summary_exports import build_live_artifact_preview_payload
from ux_copy_contract import ARTIFACT_LABELS, VacancyCopyContext, build_step_copy
from wizard_pages.summary_readiness import (
    SummaryArtifactGate,
    SummaryReleaseBlocker,
    can_export_final,
    summarize_artifact_release_state,
)


ROOT = Path(__file__).resolve().parents[1]
PRODUCT_READINESS_DOCS = (
    ROOT / "docs" / "persistence_strategy.md",
    ROOT / "docs" / "legacy_wizard_modules.md",
    ROOT / "docs" / "definition_of_done.md",
)
FOCUSED_OUTPUT_IDS = {
    "brief",
    "job_ad",
    "interview_hr",
    "interview_fach",
    "boolean_search",
}


def _fail_if_live_api_is_touched(*_args: object, **_kwargs: object) -> None:
    raise AssertionError("Product readiness smoke must not call live APIs.")


def _synthetic_consulting_strategy_fixture() -> JobAdExtract:
    return JobAdExtract(
        job_title="AI Strategy and Analytics Manager",
        company_name="Synthetic Consulting AG",
        location_city="Berlin",
        location_country="DE",
        remote_policy=(
            "Hybrid work with optional remote days; recurring client-site workshops "
            "in DACH are expected."
        ),
        travel_required="Recurring client workshops in DACH.",
        salary_range=MoneyRange(notes="Competitive package based on experience."),
        languages=["German C1", "English B2"],
        responsibilities=[
            "Develop enterprise AI strategy and analytics roadmaps",
            "Structure data-governance target pictures",
            "Assess digital business models and operating models",
            "Prepare business cases for transformation programs",
        ],
        must_have_skills=[
            "AI strategy",
            "Analytics",
            "Data governance",
            "Operating model design",
            "Digital business models",
            "Consulting",
            "Business case development",
        ],
        benefits=["Learning budget", "Training academy", "Corporate discounts"],
        gaps=["Confirm numeric compensation range before publication"],
    )


def test_product_readiness_docs_exist_and_are_linked_from_readme() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8")

    for doc_path in PRODUCT_READINESS_DOCS:
        assert doc_path.exists()
        assert f"docs/{doc_path.name}" in readme

    persistence_doc = PRODUCT_READINESS_DOCS[0].read_text(encoding="utf-8")
    legacy_doc = PRODUCT_READINESS_DOCS[1].read_text(encoding="utf-8")
    dod_doc = PRODUCT_READINESS_DOCS[2].read_text(encoding="utf-8")

    assert "manual JSON draft/resume" in persistence_doc
    assert "Future Adapter Boundary" in persistence_doc
    assert "wizard_pages/01a_jobspec_review.py" in legacy_doc
    assert "wizard_pages/03_team.py" in legacy_doc
    assert "No-Live-API Beta Smoke" in dod_doc


def test_no_live_api_beta_smoke_preserves_focused_output_contracts(
    monkeypatch,
) -> None:
    monkeypatch.setattr(llm_client, "get_openai_client", _fail_if_live_api_is_touched)
    monkeypatch.setattr(
        esco_client.EscoClient,
        "_get",
        _fail_if_live_api_is_touched,
    )
    monkeypatch.setattr(homepage_research, "_open_url", _fail_if_live_api_is_touched)

    job = _synthetic_consulting_strategy_fixture()
    offer = build_offer_decision_context(
        job=job,
        selected_benefits=job.benefits,
        intake_facts={},
        intake_fact_evidence={},
        salary_forecast={},
        salary_fingerprints={},
    )
    preview_de = build_live_artifact_preview_payload(
        job=job,
        selected_role_tasks=job.responsibilities,
        selected_skills=job.must_have_skills,
        selected_benefits=job.benefits,
        offer_positioning=offer,
        language="de",
    )
    preview_en = build_live_artifact_preview_payload(
        job=job,
        selected_role_tasks=job.responsibilities,
        selected_skills=job.must_have_skills,
        selected_benefits=job.benefits,
        offer_positioning=offer,
        language="en",
    )
    occupation_profile = classify_occupation_context(job=job)

    assert set(SUMMARY_ACTIVE_ARTIFACT_IDS) == FOCUSED_OUTPUT_IDS
    assert set(preview_de["fragments"]) == FOCUSED_OUTPUT_IDS
    assert set(preview_en["fragments"]) == FOCUSED_OUTPUT_IDS
    assert "employment_contract" not in SUMMARY_ACTIVE_ARTIFACT_IDS
    assert artifact_display_label("employment_contract") == "employment_contract"

    salary_decision = offer["salary_decision"]
    assert salary_decision["salary_claim_status"] == "notes_only"
    assert salary_decision["has_numeric_salary_claim"] is False
    assert "salary_text" not in salary_decision
    assert salary_decision["salary_notes"] == "Competitive package based on experience."

    assert occupation_profile.work_arrangement != WorkArrangement.REMOTE_GLOBAL_POSSIBLE
    assert "work from anywhere" not in preview_en["fragments"]["boolean_search"][
        "bullets"
    ][2].casefold()

    assert preview_de["fragments"]["brief"]["summary"] == (
        "AI Strategy and Analytics Manager bei Synthetic Consulting AG"
    )
    assert preview_en["fragments"]["brief"]["summary"] == (
        "AI Strategy and Analytics Manager at Synthetic Consulting AG"
    )
    assert " bei Synthetic Consulting AG" not in preview_en["fragments"]["brief"][
        "summary"
    ]
    assert " at Synthetic Consulting AG" not in preview_de["fragments"]["brief"][
        "summary"
    ]
    assert preview_de["notice"].startswith("Live-Vorschau")
    assert preview_en["notice"].startswith("Live preview")

    candidate_value = "\n".join(offer["candidate_value"])
    fixed_terms = "\n".join(offer.get("fixed_terms", []))
    for benefit in job.benefits:
        assert benefit in candidate_value
        assert benefit not in fixed_terms
        assert benefit not in job.must_have_skills


def test_summary_release_state_contract_covers_beta_statuses() -> None:
    def gate(**overrides: object) -> SummaryArtifactGate:
        defaults = {
            "artifact_id": "job_ad",
            "artifact_label": "Job ad",
            "state": "open",
            "state_label": "Open",
            "blockers": [],
            "next_step": "Create job ad.",
            "preview_available": True,
            "draft_available": False,
            "final_export_ready": False,
            "final_export_blocked": False,
            "stale_regeneration_required": False,
            "blocker_severity": "none",
            "override_allowed": False,
        }
        defaults.update(overrides)
        return SummaryArtifactGate(**defaults)

    risky_blocker = SummaryReleaseBlocker(
        artifact_id="job_ad",
        artifact_label="Job ad",
        reason="Forecast assumptions remain open.",
        next_step="Review warnings.",
        blocker_type="forecast_assumptions",
        severity="warning",
    )
    ready_gate = gate(state="current", final_export_ready=True)
    open_gate = gate(state="open", preview_available=True)
    risky_gate = gate(
        state="current",
        blockers=[risky_blocker],
        draft_available=True,
        final_export_blocked=True,
        blocker_severity="warning",
        override_allowed=True,
    )
    stale_gate = gate(
        state="stale",
        final_export_blocked=True,
        stale_regeneration_required=True,
        blocker_severity="critical",
    )

    assert summarize_artifact_release_state(ready_gate, language="en") == (
        "Final export ready."
    )
    assert summarize_artifact_release_state(open_gate, language="en") == (
        "Preview remains available; draft generation needs more base context."
    )
    assert summarize_artifact_release_state(risky_gate, language="en") == (
        "Final export paused: review warnings; expert override is possible."
    )
    assert summarize_artifact_release_state(stale_gate, language="en") == (
        "Final export paused: regenerate the result first."
    )
    assert can_export_final("job_ad", ready_gate, "standard") is True
    assert can_export_final("job_ad", risky_gate, "standard") is False
    assert can_export_final("job_ad", risky_gate, "expert") is True
    assert can_export_final("job_ad", stale_gate, "expert") is False


def test_active_flow_copy_and_artifact_labels_have_de_en_parity() -> None:
    active_steps = (
        STEP_KEY_LANDING,
        STEP_KEY_COMPANY,
        STEP_KEY_ROLE_TASKS,
        STEP_KEY_SKILLS,
        STEP_KEY_BENEFITS,
        STEP_KEY_INTERVIEW,
        STEP_KEY_SUMMARY,
    )
    context = VacancyCopyContext(
        role_title="AI Strategy and Analytics Manager",
        company_name="Synthetic Consulting AG",
        readiness_score=100,
        critical_gaps_count=0,
    )

    for step_key in active_steps:
        de_copy = build_step_copy(step_key, language="de", context=context)
        en_copy = build_step_copy(step_key, language="en", context=context)
        assert de_copy.headline
        assert en_copy.headline
        assert de_copy.subheadline
        assert en_copy.subheadline
        assert de_copy.value_line
        assert en_copy.value_line

    assert set(ARTIFACT_LABELS["de"]) == FOCUSED_OUTPUT_IDS
    assert set(ARTIFACT_LABELS["en"]) == FOCUSED_OUTPUT_IDS
    assert "employment_contract" not in ARTIFACT_LABELS["de"]
    assert "employment_contract" not in ARTIFACT_LABELS["en"]
