"""Usage event constants."""

from __future__ import annotations

from enum import Enum


class UsageEventType(str, Enum):
    STEP_ENTERED = "step_entered"
    STEP_SUBMITTED = "step_submitted"
    FACT_CONFIRMED = "fact_confirmed"
    FACT_CORRECTED = "fact_corrected"
    FACT_REJECTED = "fact_rejected"
    FALLBACK_MODEL_USED = "fallback_model_used"
    HOMEPAGE_FETCH_FAILED = "homepage_fetch_failed"
    ENRICHMENT_TIMED = "enrichment_timed"
    ARTIFACT_GENERATED = "artifact_generated"
    EVALUATION_RUN_COMPLETED = "evaluation_run_completed"
