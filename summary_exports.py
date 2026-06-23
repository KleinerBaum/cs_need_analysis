"""Pure helpers for Summary export formatting and input fingerprints."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timezone
from typing import Any

from constants import APP_NAME, SSKey, VACANCY_DRAFT_SCHEMA_VERSION
from schemas import BooleanSearchPack, JobAdExtract, VacancyBrief

VACANCY_DRAFT_SCHEMA_ID = "cs_need_analysis.vacancy_draft"


def build_summary_input_fingerprint(
    *,
    job: JobAdExtract,
    answers: dict[str, Any],
    selected_role_tasks: list[str],
    selected_skills: list[str],
    selected_benefits: list[str],
    esco_occupation_selected: dict[str, str],
    esco_match_explainability: dict[str, Any],
    esco_selected_skills_must: list[dict[str, str]],
    esco_selected_skills_nice: list[dict[str, str]],
    intake_facts: dict[str, Any] | None = None,
    intake_fact_resolution: dict[str, Any] | None = None,
    confidence_threshold: float | None = None,
) -> str:
    non_sensitive_payload = {
        "job": job.model_dump(mode="json", exclude_none=True),
        "answers": answers,
        "intake_facts": intake_facts or {},
        "intake_fact_resolution": intake_fact_resolution or {},
        "confidence_threshold": confidence_threshold,
        "selected_role_tasks": selected_role_tasks,
        "selected_skills": selected_skills,
        "selected_benefits": selected_benefits,
        "esco_occupation_selected": esco_occupation_selected,
        "esco_match_explainability": esco_match_explainability,
        "esco_selected_skills_must": esco_selected_skills_must,
        "esco_selected_skills_nice": esco_selected_skills_nice,
    }
    serialized = json.dumps(
        non_sensitive_payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        default=str,
    )
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def _json_safe_draft_value(value: Any) -> Any:
    if value is None or isinstance(value, str | int | float | bool):
        return value
    if isinstance(value, datetime):
        return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")
    if isinstance(value, bytes | bytearray | memoryview):
        return None
    if hasattr(value, "model_dump"):
        try:
            return _json_safe_draft_value(value.model_dump(mode="json"))
        except Exception:
            return str(value)
    if isinstance(value, Mapping):
        return {str(key): _json_safe_draft_value(item) for key, item in value.items()}
    if isinstance(value, Sequence) and not isinstance(value, str):
        return [_json_safe_draft_value(item) for item in value]
    if isinstance(value, set):
        return [_json_safe_draft_value(item) for item in value]
    return str(value)


def build_vacancy_draft_payload(
    session_state: Mapping[str, Any],
    *,
    allowed_keys: Sequence[SSKey],
    saved_at: datetime | None = None,
) -> dict[str, Any]:
    """Build a schema-versioned JSON-safe draft from allowlisted session keys."""

    saved_at_utc = (saved_at or datetime.now(timezone.utc)).astimezone(timezone.utc)
    state_payload: dict[str, Any] = {}
    for key in allowed_keys:
        if key.value not in session_state:
            continue
        state_payload[key.value] = _json_safe_draft_value(session_state[key.value])

    return {
        "schema": VACANCY_DRAFT_SCHEMA_ID,
        "schema_version": VACANCY_DRAFT_SCHEMA_VERSION,
        "application": APP_NAME,
        "saved_at": saved_at_utc.isoformat().replace("+00:00", "Z"),
        "state": state_payload,
    }


def vacancy_draft_payload_to_json(payload: Mapping[str, Any]) -> str:
    return json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        indent=2,
        default=str,
    )


def vacancy_draft_to_json(
    session_state: Mapping[str, Any],
    *,
    allowed_keys: Sequence[SSKey],
    saved_at: datetime | None = None,
) -> str:
    return vacancy_draft_payload_to_json(
        build_vacancy_draft_payload(
            session_state,
            allowed_keys=allowed_keys,
            saved_at=saved_at,
        )
    )


def parse_vacancy_draft_json(raw_json: str | bytes) -> dict[str, Any]:
    if isinstance(raw_json, bytes):
        raw_json = raw_json.decode("utf-8")
    payload = json.loads(raw_json)
    if not isinstance(payload, dict):
        raise ValueError("Draft JSON must contain an object payload.")
    return payload


def brief_to_markdown(brief: VacancyBrief) -> str:
    structured_data = brief.structured_data.model_dump(mode="json")
    lines = []
    lines.append(
        f"# Recruiting Brief – {structured_data.get('job_extract', {}).get('job_title', '')}".strip()
    )
    lines.append("")
    lines.append(f"**One-liner:** {brief.one_liner}")
    lines.append("")
    lines.append("## Hiring Context")
    lines.append(brief.hiring_context)
    lines.append("")
    lines.append("## Role Summary")
    lines.append(brief.role_summary)
    lines.append("")
    lines.append("## Top Responsibilities")
    lines.extend([f"- {x}" for x in brief.top_responsibilities])
    lines.append("")
    lines.append("## Must-have")
    lines.extend([f"- {x}" for x in brief.must_have])
    lines.append("")
    lines.append("## Nice-to-have")
    lines.extend([f"- {x}" for x in brief.nice_to_have])
    lines.append("")
    lines.append("## Dealbreakers")
    lines.extend([f"- {x}" for x in brief.dealbreakers])
    lines.append("")
    lines.append("## Interview Plan")
    lines.extend([f"- {x}" for x in brief.interview_plan])
    lines.append("")
    lines.append("## Evaluation Rubric")
    lines.extend([f"- {x}" for x in brief.evaluation_rubric])
    lines.append("")
    lines.append("## Risks / Open Questions")
    lines.extend([f"- {x}" for x in brief.risks_open_questions])
    lines.append("")
    lines.append("## Stellenanzeigenentwurf (DE)")
    lines.append(brief.job_ad_draft)
    lines.append("")
    return "\n".join(lines)


def boolean_search_pack_to_markdown(pack: BooleanSearchPack) -> str:
    def _as_bullets(values: list[str], *, code: bool = False) -> list[str]:
        if not values:
            return ["- —"]
        if code:
            return [f"- `{value}`" for value in values]
        return [f"- {value}" for value in values]

    lines = [
        "# Suchstrings",
        "",
        f"**Role Title:** {pack.role_title}",
        "",
        "## Must-have Terms",
        *_as_bullets(pack.must_have_terms),
        "",
        "## Seniority Terms",
        *_as_bullets(pack.seniority_terms),
        "",
        "## Exclusion Terms",
        *_as_bullets(pack.exclusion_terms),
        "",
        "## Target Locations",
        *_as_bullets(pack.target_locations),
        "",
    ]
    for channel_label, channel in (
        ("Google", pack.google),
        ("LinkedIn", pack.linkedin),
        ("XING", pack.xing),
    ):
        lines.extend(
            [
                f"## {channel_label}",
                "",
                "### Broad",
                *_as_bullets(channel.broad, code=True),
                "",
                "### Focused",
                *_as_bullets(channel.focused, code=True),
                "",
                "### Fallback",
                *_as_bullets(channel.fallback, code=True),
                "",
            ]
        )
    lines.extend(
        [
            "## Channel Limitations",
            *_as_bullets(pack.channel_limitations),
            "",
            "## Usage Notes",
            *_as_bullets(pack.usage_notes),
            "",
        ]
    )
    return "\n".join(lines)
