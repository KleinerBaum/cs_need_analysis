"""Central OpenAI model capability helpers.

Rules are intentionally concentrated here so request-building code does not
duplicate model-family checks.
"""

from __future__ import annotations

import re

_GPT5_LEGACY_SNAPSHOT_RE = re.compile(r"^gpt-5(?:-mini|-nano)?(?:-\d{4}-\d{2}-\d{2})?$")


def _normalize_model(model: str) -> str:
    return model.strip().lower()


def is_gpt5_legacy_model(model: str) -> bool:
    """Return ``True`` for GPT-5 legacy variants, incl. dated snapshots."""

    return bool(_GPT5_LEGACY_SNAPSHOT_RE.match(_normalize_model(model)))


def is_gpt54_family(model: str) -> bool:
    """Return ``True`` for the GPT-5.4 family (including dated variants)."""

    return _normalize_model(model).startswith("gpt-5.4")


def is_nano_model(model: str) -> bool:
    """Return ``True`` for GPT-5 nano models, incl. snapshots."""

    normalized = _normalize_model(model)
    return normalized.startswith("gpt-5-nano") or normalized.startswith("gpt-5.4-nano")


def supports_reasoning(model: str) -> bool:
    """Reasoning payload is currently only supported by GPT-5 families."""

    return is_gpt5_legacy_model(model) or is_gpt54_family(model)


def supports_verbosity(model: str) -> bool:
    """`text.verbosity` is only sent to GPT-5 families."""

    return is_gpt5_legacy_model(model) or is_gpt54_family(model)


def normalize_reasoning_effort(model: str, effort: str | None) -> str | None:
    """Normalize reasoning effort by model compatibility.

    Valid values are: ``none``, ``minimal``, ``low``, ``medium``, ``high``,
    and ``xhigh``.
    """

    if effort is None or not supports_reasoning(model):
        return None

    normalized_effort = effort.strip().lower()
    if not normalized_effort:
        return None

    if normalized_effort == "none":
        return "none" if is_gpt54_family(model) else None

    if normalized_effort in {"minimal", "low", "medium", "high", "xhigh"}:
        return normalized_effort

    return None


def supports_temperature(model: str, reasoning_effort: str | None) -> bool:
    """Return whether ``temperature`` should be forwarded.

    - GPT-5 legacy: never.
    - GPT-5.4: only when reasoning is explicitly disabled via ``none``.
    - all other families: keep ``temperature`` behavior unchanged.
    """

    if is_gpt5_legacy_model(model):
        return False

    normalized_effort = normalize_reasoning_effort(model, reasoning_effort)
    if is_gpt54_family(model):
        return normalized_effort == "none"

    return True
