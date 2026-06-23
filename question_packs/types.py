"""Types for deterministic question packs."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from pydantic import Field, ValidationError, model_validator

from constants import (
    FactKey,
    QUESTION_IMPACT_TARGETS,
    STEP_KEY_BENEFITS,
    STEP_KEY_COMPANY,
    STEP_KEY_INTERVIEW,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
)
from schemas import OccupationContextProfile, Question, StrictSchemaModel


_QUESTION_PACK_STEP_KEYS = {
    STEP_KEY_COMPANY,
    STEP_KEY_ROLE_TASKS,
    STEP_KEY_SKILLS,
    STEP_KEY_BENEFITS,
    STEP_KEY_INTERVIEW,
}


class QuestionPackDataError(ValueError):
    """Raised when JSON question-pack data is malformed."""


@dataclass(frozen=True)
class QuestionPackEntry:
    step_key: str
    question: Question


@dataclass(frozen=True)
class QuestionPack:
    pack_key: str
    description: str
    entries: tuple[QuestionPackEntry, ...]

    def applies_to(self, profile: OccupationContextProfile) -> bool:
        return self.pack_key in profile.pack_keys

    @property
    def questions(self) -> tuple[Question, ...]:
        return tuple(entry.question for entry in self.entries)


class _QuestionPackEntryPayload(StrictSchemaModel):
    step_key: str
    question: Question


class _QuestionPackPayload(StrictSchemaModel):
    pack_key: str
    description: str
    entries: tuple[_QuestionPackEntryPayload, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _validate_pack(self) -> "_QuestionPackPayload":
        if not self.pack_key.strip():
            raise ValueError("pack_key must not be empty")
        if not self.description.strip():
            raise ValueError("description must not be empty")

        seen_ids: set[str] = set()
        canonical_impact_targets = set(QUESTION_IMPACT_TARGETS)
        for index, entry in enumerate(self.entries):
            step_key = entry.step_key.strip()
            if step_key not in _QUESTION_PACK_STEP_KEYS:
                raise ValueError(f"entries[{index}].step_key is not canonical")

            question = entry.question
            question_id = question.id.strip()
            if not question_id:
                raise ValueError(f"entries[{index}].question.id must not be empty")
            if question_id in seen_ids:
                raise ValueError(
                    f"entries[{index}].question.id duplicates {question_id!r}"
                )
            seen_ids.add(question_id)

            if not question.label.strip():
                raise ValueError(f"entries[{index}].question.label must not be empty")
            if question.fact_key:
                try:
                    FactKey(question.fact_key)
                except ValueError as exc:
                    raise ValueError(
                        f"entries[{index}].question.fact_key is not canonical"
                    ) from exc
            invalid_targets = [
                target
                for target in question.impact_targets
                if target not in canonical_impact_targets
            ]
            if invalid_targets:
                raise ValueError(
                    f"entries[{index}].question.impact_targets contains "
                    f"non-canonical values: {invalid_targets}"
                )
        return self


def _load_json_object(path: Path) -> dict[str, Any]:
    try:
        with path.open("r", encoding="utf-8") as handle:
            raw_data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        raise QuestionPackDataError(
            f"Could not load question pack data from {path}: {exc}"
        ) from exc
    if not isinstance(raw_data, dict):
        raise QuestionPackDataError(
            f"Question pack data in {path} must be a JSON object"
        )
    return raw_data


def load_question_pack_from_json(
    path: Path,
    *,
    expected_pack_key: str | None = None,
) -> QuestionPack:
    """Load a deterministic question pack from a validated JSON object."""

    raw_data = _load_json_object(path)
    try:
        payload = _QuestionPackPayload.model_validate(raw_data)
    except ValidationError as exc:
        raise QuestionPackDataError(
            f"Invalid question pack data in {path}: {exc}"
        ) from exc

    if expected_pack_key is not None and payload.pack_key != expected_pack_key:
        raise QuestionPackDataError(
            f"Question pack data in {path} has pack_key {payload.pack_key!r}; "
            f"expected {expected_pack_key!r}"
        )

    return QuestionPack(
        pack_key=payload.pack_key,
        description=payload.description,
        entries=tuple(
            QuestionPackEntry(step_key=entry.step_key, question=entry.question)
            for entry in payload.entries
        ),
    )
