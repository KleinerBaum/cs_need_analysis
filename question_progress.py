"""Helpers for question-level UX progress state."""

from __future__ import annotations

import hashlib
import json
from typing import Any, Literal, TypedDict

from constants import AnswerType
from schemas import Question

WizardUIMode = Literal["quick", "standard", "expert"]

SINGLE_SELECT_PLACEHOLDERS = frozenset({"", "— Bitte wählen —"})


class AnswerMeta(TypedDict, total=False):
    touched: bool
    confirmed: bool
    last_value_hash: str


AnswerMetaMap = dict[str, AnswerMeta]


def value_hash(value: Any) -> str:
    """Return a deterministic hash for arbitrary JSON-like values."""

    payload = json.dumps(value, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def is_answered(question: Question, value: Any, meta: AnswerMeta | None) -> bool:
    """Type-aware answered evaluation with meta-aware handling for defaults."""

    metadata = meta or {}
    touched = bool(metadata.get("touched", False))
    confirmed = bool(metadata.get("confirmed", False))

    if question.answer_type in (AnswerType.SHORT_TEXT, AnswerType.LONG_TEXT):
        return isinstance(value, str) and bool(value.strip())

    if question.answer_type == AnswerType.MULTI_SELECT:
        return isinstance(value, list) and len(value) > 0

    if question.answer_type == AnswerType.SINGLE_SELECT:
        if value is None:
            return False
        normalized = str(value).strip()
        return normalized not in SINGLE_SELECT_PLACEHOLDERS

    if question.answer_type in (AnswerType.BOOLEAN, AnswerType.NUMBER):
        return touched or confirmed

    if question.answer_type == AnswerType.DATE:
        if value is None:
            return False
        return bool(str(value).strip())

    return value is not None
