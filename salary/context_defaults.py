"""Context-derived salary scenario defaults."""

from __future__ import annotations

from collections.abc import MutableMapping
from typing import Any

from constants import SSKey
from salary.engine import infer_remote_share_percent, normalize_seniority_level
from schemas import JobAdExtract


def _default_entry(value: Any, source: str) -> dict[str, Any]:
    return {"value": value, "source": source}


def _sync_context_default(
    session_state: MutableMapping[str, Any],
    *,
    state_key: SSKey,
    value: Any,
    source: str,
    empty_values: tuple[Any, ...],
) -> Any:
    raw_defaults = session_state.get(SSKey.SALARY_SCENARIO_CONTEXT_DEFAULTS.value, {})
    defaults = dict(raw_defaults) if isinstance(raw_defaults, dict) else {}
    entry_raw = defaults.get(state_key.value)
    entry = entry_raw if isinstance(entry_raw, dict) else {}
    previous_value = entry.get("value")
    current_value = session_state.get(state_key.value)

    has_previous_default = "value" in entry
    if (not has_previous_default and current_value in empty_values) or (
        has_previous_default and current_value == previous_value
    ):
        session_state[state_key.value] = value
        defaults[state_key.value] = _default_entry(value, source)
        session_state[SSKey.SALARY_SCENARIO_CONTEXT_DEFAULTS.value] = defaults
        return value
    return current_value


def sync_salary_scenario_context_defaults(
    session_state: MutableMapping[str, Any],
    *,
    job: JobAdExtract | None,
) -> None:
    """Seed scenario controls from extracted context without overwriting user edits."""

    if job is None:
        return

    remote_source = str(job.remote_policy or "").strip()
    remote_share = infer_remote_share_percent(remote_source)
    if remote_share is not None:
        _sync_context_default(
            session_state,
            state_key=SSKey.SALARY_SCENARIO_REMOTE_SHARE_PERCENT,
            value=remote_share,
            source=remote_source,
            empty_values=(None, 0),
        )

    seniority_source = str(job.seniority_level or "").strip()
    seniority = normalize_seniority_level(seniority_source)
    if seniority:
        _sync_context_default(
            session_state,
            state_key=SSKey.SALARY_SCENARIO_SENIORITY_OVERRIDE,
            value=seniority,
            source=seniority_source,
            empty_values=(None, ""),
        )
