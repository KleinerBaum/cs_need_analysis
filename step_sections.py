"""Central registry for ordered wizard step sections."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from constants import (
    STEP_KEY_COMPANY,
    STEP_KEY_BENEFITS,
    STEP_KEY_INTERVIEW,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
    STEP_SECTION_EXTRACTED_FROM_JOBSPEC,
    STEP_SECTION_LABELS_DE,
    STEP_SECTION_OPEN_QUESTIONS,
    STEP_SECTION_REVIEW,
    STEP_SECTION_SALARY_FORECAST,
    STEP_SECTION_SLOT_NAMES,
    STEP_SECTION_SOURCE_COMPARISON,
)

StepSectionRenderer = Callable[[], None]


@dataclass(frozen=True)
class StepSectionDef:
    section_id: str
    slot_name: str
    title_de: str
    shell_heading_de: str | None = None


def _section(
    section_id: str,
    *,
    shell_heading_de: str | None = None,
) -> StepSectionDef:
    return StepSectionDef(
        section_id=section_id,
        slot_name=STEP_SECTION_SLOT_NAMES[section_id],
        title_de=STEP_SECTION_LABELS_DE[section_id],
        shell_heading_de=shell_heading_de,
    )


_COMPANY_STEP_SECTIONS: tuple[StepSectionDef, ...] = (
    _section(STEP_SECTION_EXTRACTED_FROM_JOBSPEC, shell_heading_de=""),
    _section(STEP_SECTION_SOURCE_COMPARISON),
    _section(STEP_SECTION_OPEN_QUESTIONS),
    _section(STEP_SECTION_REVIEW),
)

_INTERVIEW_STEP_SECTIONS: tuple[StepSectionDef, ...] = (
    _section(
        STEP_SECTION_EXTRACTED_FROM_JOBSPEC,
        shell_heading_de="Identifizierte Interview-Werte",
    ),
    _section(STEP_SECTION_SOURCE_COMPARISON),
    _section(STEP_SECTION_OPEN_QUESTIONS),
    _section(STEP_SECTION_REVIEW),
)

_ROLE_TASKS_STEP_SECTIONS: tuple[StepSectionDef, ...] = (
    _section(STEP_SECTION_EXTRACTED_FROM_JOBSPEC),
    _section(STEP_SECTION_SOURCE_COMPARISON),
    _section(STEP_SECTION_SALARY_FORECAST),
    _section(STEP_SECTION_OPEN_QUESTIONS),
    _section(STEP_SECTION_REVIEW),
)

_SKILLS_STEP_SECTIONS: tuple[StepSectionDef, ...] = (
    _section(STEP_SECTION_EXTRACTED_FROM_JOBSPEC),
    _section(STEP_SECTION_SOURCE_COMPARISON),
    _section(STEP_SECTION_SALARY_FORECAST),
    _section(STEP_SECTION_OPEN_QUESTIONS),
    _section(STEP_SECTION_REVIEW),
)

_BENEFITS_STEP_SECTIONS: tuple[StepSectionDef, ...] = (
    _section(STEP_SECTION_EXTRACTED_FROM_JOBSPEC),
    _section(STEP_SECTION_SOURCE_COMPARISON),
    _section(STEP_SECTION_SALARY_FORECAST),
    _section(STEP_SECTION_OPEN_QUESTIONS),
    _section(STEP_SECTION_REVIEW),
)

_STEP_SECTION_REGISTRY: dict[str, tuple[StepSectionDef, ...]] = {
    STEP_KEY_COMPANY: _COMPANY_STEP_SECTIONS,
    STEP_KEY_ROLE_TASKS: _ROLE_TASKS_STEP_SECTIONS,
    STEP_KEY_SKILLS: _SKILLS_STEP_SECTIONS,
    STEP_KEY_BENEFITS: _BENEFITS_STEP_SECTIONS,
    STEP_KEY_INTERVIEW: _INTERVIEW_STEP_SECTIONS,
}


def get_step_sections(step_key: str) -> tuple[StepSectionDef, ...]:
    """Return the ordered section definitions for a wizard step."""
    return _STEP_SECTION_REGISTRY.get(step_key, ())


def build_step_shell_section_kwargs(
    *,
    step_key: str,
    renderers: Mapping[str, StepSectionRenderer],
) -> dict[str, Any]:
    """Build ordered ``render_step_shell`` kwargs from registered sections."""
    shell_kwargs: dict[str, Any] = {}
    for section in get_step_sections(step_key):
        renderer = renderers.get(section.section_id)
        if renderer is None:
            continue
        shell_kwargs[section.slot_name] = renderer
        if section.section_id == STEP_SECTION_EXTRACTED_FROM_JOBSPEC:
            shell_kwargs["extracted_from_jobspec_label"] = (
                section.shell_heading_de
                if section.shell_heading_de is not None
                else section.title_de
            )
    return shell_kwargs
