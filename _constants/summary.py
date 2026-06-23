"""Summary artifact and legacy session-key constants."""

from __future__ import annotations

from typing import Final

from _constants.state_keys import SSKey


SUMMARY_ARTIFACT_IDS: Final[tuple[str, ...]] = (
    "brief",
    "job_ad",
    "interview_hr",
    "interview_fach",
    "boolean_search",
    "employment_contract",
)
SUMMARY_ACTIVE_ARTIFACT_IDS: Final[tuple[str, ...]] = (
    "brief",
    "job_ad",
    "interview_hr",
    "interview_fach",
    "boolean_search",
)
SUMMARY_ARTIFACT_LEGACY_ALIASES: Final[dict[str, str]] = {
    "recruiting_brief": "brief",
    "job_ad_generator": "job_ad",
    "interview_hr_sheet": "interview_hr",
    "interview_fach_sheet": "interview_fach",
}
SUMMARY_SESSION_KEY_LEGACY_ALIASES: Final[dict[SSKey, tuple[str, ...]]] = {
    SSKey.SUMMARY_ACTIVE_ARTIFACT: (
        "cs.summary.active_artifact",
        "cs.summary.active_action",
    ),
    SSKey.SUMMARY_SELECTIONS: ("cs.summary.selections",),
    SSKey.SUMMARY_STYLEGUIDE_TEXT: ("cs.summary.style_guide",),
    SSKey.SUMMARY_CHANGE_REQUEST_TEXT: ("cs.summary.change_requests",),
}
