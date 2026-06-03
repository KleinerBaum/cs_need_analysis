"""Types for deterministic question packs."""

from __future__ import annotations

from dataclasses import dataclass

from schemas import OccupationContextProfile, Question


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
