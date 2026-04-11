"""Configurable ESCO skill premium helpers (domain-only)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from schemas import JobAdExtract

from salary.features_esco import normalize_esco_uri
from salary.mapping import normalize_token
from salary.types import SalaryEscoContext


def load_skill_premiums(path: Path) -> dict[str, Any]:
    """Load skill premium config from local JSON file."""

    if not path.exists():
        raise FileNotFoundError(f"Skill premium config does not exist: {path}")

    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("Skill premium config must be a JSON object")

    skills = payload.get("skills")
    if not isinstance(skills, dict):
        raise ValueError("Skill premium config requires a top-level 'skills' object")
    return payload


def resolve_skill_premium_path() -> Path:
    return (
        Path(__file__).resolve().parent.parent
        / "data"
        / "salary_skill_premiums"
        / "demo_skill_premiums.json"
    )


def compute_skill_premium_delta(
    esco_context: SalaryEscoContext | None,
    job_extract: JobAdExtract,
    *,
    premium_config: dict[str, Any] | None = None,
    baseline_p50: float | None = None,
    max_matches: int = 5,
) -> tuple[float, list[str]]:
    """Compute total EUR delta from configured ESCO and label-based skill premiums."""

    config = premium_config or load_skill_premiums(resolve_skill_premium_path())
    skills_map = config.get("skills") if isinstance(config, dict) else None
    if not isinstance(skills_map, dict):
        return 0.0, []

    default_nice_weight = 0.4
    meta = config.get("meta") if isinstance(config, dict) else None
    if isinstance(meta, dict):
        parsed_weight = meta.get("default_pct_for_nice_to_have")
        if isinstance(parsed_weight, (int, float)):
            default_nice_weight = min(1.0, max(0.0, float(parsed_weight)))

    matched_deltas: list[tuple[str, float]] = []

    must_uris = esco_context.skill_uris_must if esco_context else []
    nice_uris = esco_context.skill_uris_nice if esco_context else []

    for uri in must_uris:
        normalized_uri = normalize_esco_uri(uri)
        if not normalized_uri:
            continue
        delta = _entry_to_eur_delta(skills_map.get(normalized_uri), baseline_p50)
        if delta == 0.0:
            continue
        matched_deltas.append((normalized_uri, delta))

    for uri in nice_uris:
        normalized_uri = normalize_esco_uri(uri)
        if not normalized_uri:
            continue
        delta = _entry_to_eur_delta(skills_map.get(normalized_uri), baseline_p50)
        if delta == 0.0:
            continue
        matched_deltas.append((normalized_uri, delta * default_nice_weight))

    normalized_labels = {
        normalize_token(skill)
        for skill in [*job_extract.must_have_skills, *job_extract.nice_to_have_skills]
        if isinstance(skill, str) and skill.strip()
    }
    for label in sorted(normalized_labels):
        if not label:
            continue
        delta = _entry_to_eur_delta(skills_map.get(label), baseline_p50)
        if delta == 0.0:
            continue
        matched_deltas.append((label, delta))

    if not matched_deltas:
        return 0.0, []

    matched_deltas.sort(key=lambda item: abs(item[1]), reverse=True)
    top_premium_skills = [
        f"{skill} ({round(delta, 0):.0f} EUR)"
        for skill, delta in matched_deltas[:max_matches]
    ]
    total_delta = sum(delta for _, delta in matched_deltas)
    return total_delta, top_premium_skills


def _entry_to_eur_delta(entry: Any, baseline_p50: float | None) -> float:
    if not isinstance(entry, dict):
        return 0.0

    eur_delta = entry.get("eur_delta")
    if isinstance(eur_delta, (int, float)):
        return float(eur_delta)

    pct_delta = entry.get("pct_delta")
    if (
        isinstance(pct_delta, (int, float))
        and baseline_p50 is not None
        and baseline_p50 > 0
    ):
        return float(pct_delta) * baseline_p50

    return 0.0
