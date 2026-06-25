"""Audience-mode helpers for role-specific UI and prompt style."""

from __future__ import annotations

from constants import (
    AUDIENCE_MODE_CANDIDATE,
    AUDIENCE_MODE_DEFAULT,
    AUDIENCE_MODE_RECRUITER,
    AUDIENCE_MODE_VALUES,
)


def normalize_audience_mode(raw_mode: object) -> str:
    """Normalize any raw mode value to the canonical audience-mode domain."""

    mode = str(raw_mode or "").strip().lower()
    if mode not in set(AUDIENCE_MODE_VALUES):
        return AUDIENCE_MODE_DEFAULT
    return mode


def build_audience_instructions(mode: str) -> str:
    """Return prompt style instructions for the active audience mode."""

    normalized = normalize_audience_mode(mode)
    return (
        f"Audience mode: {normalized}. Answer as a recruiter copilot: highlight gaps, "
        "risks, evidence conflicts, verification questions, and next-best actions."
    )


def is_candidate_audience(mode: object) -> bool:
    return normalize_audience_mode(mode) == AUDIENCE_MODE_CANDIDATE


def is_recruiter_audience(mode: object) -> bool:
    return normalize_audience_mode(mode) == AUDIENCE_MODE_RECRUITER
