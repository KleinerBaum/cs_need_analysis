"""Pure helpers for Summary ESCO export and coverage formatting."""

from __future__ import annotations

import csv
import io
from typing import Any

from pydantic import ValidationError

from schemas import EscoConceptRef


def to_esco_export_concepts(raw_items: Any) -> list[dict[str, str]]:
    if not isinstance(raw_items, list):
        return []
    concepts: list[dict[str, str]] = []
    for item in raw_items:
        try:
            parsed = EscoConceptRef.model_validate(item)
        except ValidationError:
            continue
        concepts.append({"uri": parsed.uri, "label": parsed.title})
    return concepts


def normalize_skill_term(value: str) -> str:
    return " ".join(str(value or "").strip().casefold().split())


def extract_skills_step_raw_terms(job_extract_payload: Any) -> list[str]:
    if not isinstance(job_extract_payload, dict):
        return []

    raw_terms: list[str] = []
    for key in ("must_have_skills", "nice_to_have_skills"):
        values = job_extract_payload.get(key, [])
        if not isinstance(values, list):
            continue
        for value in values:
            term = str(value or "").strip()
            if term:
                raw_terms.append(term)

    deduped_terms: list[str] = []
    seen: set[str] = set()
    for term in raw_terms:
        normalized = normalize_skill_term(term)
        if not normalized or normalized in seen:
            continue
        deduped_terms.append(term)
        seen.add(normalized)
    return deduped_terms


def build_esco_coverage_metrics(
    *,
    job_extract_payload: Any,
    essential_skills: list[dict[str, Any]],
    optional_skills: list[dict[str, Any]],
) -> dict[str, int]:
    must_terms = (
        extract_skills_step_raw_terms(
            {"must_have_skills": job_extract_payload.get("must_have_skills", [])}
        )
        if isinstance(job_extract_payload, dict)
        else []
    )
    nice_terms = (
        extract_skills_step_raw_terms(
            {"nice_to_have_skills": job_extract_payload.get("nice_to_have_skills", [])}
        )
        if isinstance(job_extract_payload, dict)
        else []
    )

    essential_titles = {
        normalize_skill_term(str(item.get("title") or ""))
        for item in essential_skills
        if isinstance(item, dict)
    }
    optional_titles = {
        normalize_skill_term(str(item.get("title") or ""))
        for item in optional_skills
        if isinstance(item, dict)
    }

    essential_covered = sum(
        1 for term in must_terms if normalize_skill_term(term) in essential_titles
    )
    optional_covered = sum(
        1 for term in nice_terms if normalize_skill_term(term) in optional_titles
    )
    essential_total = len(must_terms)
    optional_total = len(nice_terms)
    essential_pct = (
        round((essential_covered / essential_total) * 100) if essential_total else 0
    )
    optional_pct = (
        round((optional_covered / optional_total) * 100) if optional_total else 0
    )
    return {
        "essential_covered": essential_covered,
        "essential_total": essential_total,
        "essential_pct": essential_pct,
        "optional_covered": optional_covered,
        "optional_total": optional_total,
        "optional_pct": optional_pct,
    }


def build_esco_coverage_chart_spec(
    *, metrics: dict[str, int], unmapped_requirements_count: int
) -> dict[str, Any]:
    essential_total = int(metrics.get("essential_total", 0) or 0)
    optional_total = int(metrics.get("optional_total", 0) or 0)
    covered_total = int(metrics.get("essential_covered", 0) or 0) + int(
        metrics.get("optional_covered", 0) or 0
    )
    requirements_total = essential_total + optional_total
    unmapped_total = max(int(unmapped_requirements_count or 0), 0)

    return {
        "data": {
            "values": [
                {
                    "group": "Quelle",
                    "category": "Must-have (Jobspec)",
                    "value": essential_total,
                },
                {
                    "group": "Quelle",
                    "category": "Nice-to-have (Jobspec)",
                    "value": optional_total,
                },
                {
                    "group": "Abdeckung",
                    "category": "ESCO-unterstützt",
                    "value": covered_total,
                },
                {
                    "group": "Abdeckung",
                    "category": "Nicht gemappt",
                    "value": unmapped_total,
                },
                {
                    "group": "Abdeckung",
                    "category": "Gesamtanforderungen",
                    "value": requirements_total,
                },
            ]
        },
        "mark": {"type": "bar", "cornerRadiusTopLeft": 3, "cornerRadiusTopRight": 3},
        "encoding": {
            "x": {"field": "category", "type": "nominal", "title": ""},
            "y": {"field": "value", "type": "quantitative", "title": "Anzahl"},
            "color": {"field": "group", "type": "nominal", "title": "Sicht"},
            "tooltip": [
                {"field": "group", "type": "nominal", "title": "Sicht"},
                {"field": "category", "type": "nominal", "title": "Kategorie"},
                {"field": "value", "type": "quantitative", "title": "Anzahl"},
            ],
        },
    }


def build_esco_coverage_kpis(
    *, metrics: dict[str, int], unmapped_requirements_count: int
) -> list[tuple[str, int]]:
    essential_total = int(metrics.get("essential_total", 0) or 0)
    optional_total = int(metrics.get("optional_total", 0) or 0)
    covered_total = int(metrics.get("essential_covered", 0) or 0) + int(
        metrics.get("optional_covered", 0) or 0
    )
    requirements_total = essential_total + optional_total
    unmapped_total = max(int(unmapped_requirements_count or 0), 0)
    return [
        ("Anforderungen", requirements_total),
        ("ESCO unterstützt", covered_total),
        ("Nicht gemappt", unmapped_total),
        ("Quelle vorhanden", requirements_total),
    ]


def build_esco_mapping_report_csv(rows: list[dict[str, str]]) -> bytes:
    fieldnames = ["raw_term", "chosen_uri", "chosen_label", "match_method", "notes"]
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=fieldnames)
    writer.writeheader()
    for row in rows:
        writer.writerow({name: row.get(name, "") for name in fieldnames})
    return buffer.getvalue().encode("utf-8")
