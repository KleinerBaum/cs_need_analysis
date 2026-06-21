"""Typed access facade for Streamlit session state.

The facade keeps the existing ``SSKey`` storage contract intact. Read methods
normalize invalid or missing values without creating session-state keys; write
methods only assign canonical ``SSKey.value`` keys.
"""

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from dataclasses import dataclass
from typing import Any

import streamlit as st

from constants import (
    ESCO_ANCHOR_STATE_DEGRADED,
    ESCO_SEMANTIC_EXPORT_MODE_DEGRADED,
    JOBSPEC_SOURCE_LEGACY_TEXT,
    JOBSPEC_SOURCE_MANUAL,
    JOBSPEC_SOURCE_VALUES,
    SSKey,
    UI_PREFERENCE_CONFIDENCE_THRESHOLD,
)
from schemas import JobAdExtract


@dataclass(frozen=True)
class JobspecSourceState:
    active: str = JOBSPEC_SOURCE_MANUAL
    active_fingerprint: str = ""
    source_text: str = ""
    file_meta: dict[str, Any] | None = None
    manual_text: str = ""
    uploaded_text: str = ""
    upload_text_input: str = ""
    upload_signature: Any = None
    redact_pii: bool = True


@dataclass(frozen=True)
class JobExtractionState:
    extract: JobAdExtract | None = None


@dataclass(frozen=True)
class EscoState:
    anchor_state: str = ESCO_ANCHOR_STATE_DEGRADED
    primary_anchor: dict[str, Any] | None = None
    secondary_anchors: list[Any] | None = None
    semantic_export_mode: str = ESCO_SEMANTIC_EXPORT_MODE_DEGRADED
    occupation_selected: dict[str, Any] | None = None
    selected_occupation_uri: str = ""
    occupation_payload: dict[str, Any] | None = None
    occupation_candidates: list[Any] | None = None
    match_reason: str | None = None
    match_confidence: Any = None
    match_provenance: list[Any] | None = None


@dataclass(frozen=True)
class QuestionAnswerState:
    answers: dict[str, Any] | None = None
    answer_meta: dict[str, Any] | None = None


@dataclass(frozen=True)
class SummaryDirtyState:
    is_dirty: bool = False
    input_fingerprint: str = ""
    last_brief_fingerprint: str = ""
    active_artifact: str = "brief"


def _normalize_jobspec_source(source: Any) -> str:
    normalized = str(source or "").strip().lower()
    if normalized == JOBSPEC_SOURCE_LEGACY_TEXT:
        return JOBSPEC_SOURCE_MANUAL
    if normalized in JOBSPEC_SOURCE_VALUES:
        return normalized
    return JOBSPEC_SOURCE_MANUAL


def _dict_or_empty(raw: Any) -> dict[str, Any]:
    return raw if isinstance(raw, dict) else {}


def _dict_or_none(raw: Any) -> dict[str, Any] | None:
    return raw if isinstance(raw, dict) else None


def _list_or_empty(raw: Any) -> list[Any]:
    return raw if isinstance(raw, list) else []


def _string(raw: Any) -> str:
    return str(raw or "").strip()


class StateStore:
    """Thin typed facade over the canonical Streamlit session-state keys."""

    def __init__(self, session_state: MutableMapping[str, Any] | None = None) -> None:
        self._state = session_state if session_state is not None else st.session_state

    def jobspec_source(self) -> JobspecSourceState:
        return JobspecSourceState(
            active=_normalize_jobspec_source(
                self._state.get(SSKey.SOURCE_ACTIVE.value, JOBSPEC_SOURCE_MANUAL)
            ),
            active_fingerprint=_string(
                self._state.get(SSKey.SOURCE_ACTIVE_FINGERPRINT.value)
            ),
            source_text=str(self._state.get(SSKey.SOURCE_TEXT.value) or ""),
            file_meta=_dict_or_empty(self._state.get(SSKey.SOURCE_FILE_META.value)),
            manual_text=str(self._state.get(SSKey.SOURCE_MANUAL_TEXT.value) or ""),
            uploaded_text=str(self._state.get(SSKey.SOURCE_UPLOADED_TEXT.value) or ""),
            upload_text_input=str(
                self._state.get(SSKey.SOURCE_UPLOAD_TEXT_INPUT.value) or ""
            ),
            upload_signature=self._state.get(SSKey.SOURCE_UPLOAD_SIGNATURE.value),
            redact_pii=bool(self._state.get(SSKey.SOURCE_REDACT_PII.value, True)),
        )

    def set_jobspec_source(self, value: JobspecSourceState) -> None:
        self._state[SSKey.SOURCE_ACTIVE.value] = _normalize_jobspec_source(value.active)
        self._state[SSKey.SOURCE_ACTIVE_FINGERPRINT.value] = value.active_fingerprint
        self._state[SSKey.SOURCE_TEXT.value] = value.source_text
        self._state[SSKey.SOURCE_FILE_META.value] = dict(value.file_meta or {})
        self._state[SSKey.SOURCE_MANUAL_TEXT.value] = value.manual_text
        self._state[SSKey.SOURCE_UPLOADED_TEXT.value] = value.uploaded_text
        self._state[SSKey.SOURCE_UPLOAD_TEXT_INPUT.value] = value.upload_text_input
        self._state[SSKey.SOURCE_UPLOAD_SIGNATURE.value] = value.upload_signature
        self._state[SSKey.SOURCE_REDACT_PII.value] = bool(value.redact_pii)

    def job_extraction(self) -> JobExtractionState:
        return JobExtractionState(extract=self.job_extract())

    def job_extract(self) -> JobAdExtract | None:
        raw = self._state.get(SSKey.JOB_EXTRACT.value)
        if isinstance(raw, JobAdExtract):
            return raw
        if not isinstance(raw, Mapping):
            return None
        try:
            return JobAdExtract.model_validate(raw)
        except Exception:
            return None

    def set_job_extract(self, value: JobAdExtract | Mapping[str, Any] | None) -> None:
        if isinstance(value, JobAdExtract):
            self._state[SSKey.JOB_EXTRACT.value] = value.model_dump(mode="json")
        elif isinstance(value, Mapping):
            self._state[SSKey.JOB_EXTRACT.value] = dict(value)
        else:
            self._state[SSKey.JOB_EXTRACT.value] = None

    def esco(self) -> EscoState:
        return EscoState(
            anchor_state=_string(self._state.get(SSKey.ESCO_ANCHOR_STATE.value))
            or ESCO_ANCHOR_STATE_DEGRADED,
            primary_anchor=_dict_or_none(self._state.get(SSKey.ESCO_PRIMARY_ANCHOR.value)),
            secondary_anchors=_list_or_empty(
                self._state.get(SSKey.ESCO_SECONDARY_ANCHORS.value)
            ),
            semantic_export_mode=_string(
                self._state.get(SSKey.ESCO_SEMANTIC_EXPORT_MODE.value)
            )
            or ESCO_SEMANTIC_EXPORT_MODE_DEGRADED,
            occupation_selected=_dict_or_none(
                self._state.get(SSKey.ESCO_OCCUPATION_SELECTED.value)
            ),
            selected_occupation_uri=_string(
                self._state.get(SSKey.ESCO_SELECTED_OCCUPATION_URI.value)
            ),
            occupation_payload=_dict_or_none(
                self._state.get(SSKey.ESCO_OCCUPATION_PAYLOAD.value)
            ),
            occupation_candidates=_list_or_empty(
                self._state.get(SSKey.ESCO_OCCUPATION_CANDIDATES.value)
            ),
            match_reason=(
                _string(self._state.get(SSKey.ESCO_MATCH_REASON.value)) or None
            ),
            match_confidence=self._state.get(SSKey.ESCO_MATCH_CONFIDENCE.value),
            match_provenance=_list_or_empty(
                self._state.get(SSKey.ESCO_MATCH_PROVENANCE.value)
            ),
        )

    def set_esco(self, value: EscoState) -> None:
        self._state[SSKey.ESCO_ANCHOR_STATE.value] = value.anchor_state
        self._state[SSKey.ESCO_PRIMARY_ANCHOR.value] = value.primary_anchor
        self._state[SSKey.ESCO_SECONDARY_ANCHORS.value] = list(
            value.secondary_anchors or []
        )
        self._state[SSKey.ESCO_SEMANTIC_EXPORT_MODE.value] = (
            value.semantic_export_mode
        )
        self._state[SSKey.ESCO_OCCUPATION_SELECTED.value] = value.occupation_selected
        self._state[SSKey.ESCO_SELECTED_OCCUPATION_URI.value] = (
            value.selected_occupation_uri
        )
        self._state[SSKey.ESCO_OCCUPATION_PAYLOAD.value] = value.occupation_payload
        self._state[SSKey.ESCO_OCCUPATION_CANDIDATES.value] = list(
            value.occupation_candidates or []
        )
        self._state[SSKey.ESCO_MATCH_REASON.value] = value.match_reason
        self._state[SSKey.ESCO_MATCH_CONFIDENCE.value] = value.match_confidence
        self._state[SSKey.ESCO_MATCH_PROVENANCE.value] = list(
            value.match_provenance or []
        )

    def question_answers(self) -> QuestionAnswerState:
        return QuestionAnswerState(
            answers=self.answers(),
            answer_meta=self.answer_meta(),
        )

    def answers(self) -> dict[str, Any]:
        return _dict_or_empty(self._state.get(SSKey.ANSWERS.value))

    def answer_meta(self) -> dict[str, Any]:
        return _dict_or_empty(self._state.get(SSKey.ANSWER_META.value))

    def set_question_answers(
        self,
        answers: Mapping[str, Any],
        answer_meta: Mapping[str, Any] | None = None,
    ) -> None:
        self._state[SSKey.ANSWERS.value] = dict(answers)
        if answer_meta is not None:
            self._state[SSKey.ANSWER_META.value] = dict(answer_meta)

    def set_answer_meta(self, answer_meta: Mapping[str, Any]) -> None:
        self._state[SSKey.ANSWER_META.value] = dict(answer_meta)

    def intake_facts(self) -> dict[str, Any]:
        return _dict_or_empty(self._state.get(SSKey.INTAKE_FACTS.value))

    def intake_fact_evidence(self) -> dict[str, Any]:
        return _dict_or_empty(self._state.get(SSKey.INTAKE_FACT_EVIDENCE.value))

    def set_intake_facts(self, values: Mapping[str, Any]) -> None:
        self._state[SSKey.INTAKE_FACTS.value] = dict(values)

    def set_intake_fact_evidence(self, values: Mapping[str, Any]) -> None:
        self._state[SSKey.INTAKE_FACT_EVIDENCE.value] = dict(values)

    def question_limits(self) -> Mapping[str, Any] | None:
        raw = self._state.get(SSKey.QUESTION_LIMITS.value, {})
        return raw if isinstance(raw, Mapping) else None

    def confidence_threshold(self) -> float | None:
        preferences = self._state.get(SSKey.UI_PREFERENCES.value, {})
        if not isinstance(preferences, Mapping):
            return None
        try:
            return max(
                0.0,
                min(1.0, float(preferences.get(UI_PREFERENCE_CONFIDENCE_THRESHOLD))),
            )
        except (TypeError, ValueError):
            return None

    def summary_dirty(self) -> SummaryDirtyState:
        return SummaryDirtyState(
            is_dirty=bool(self._state.get(SSKey.SUMMARY_DIRTY.value, False)),
            input_fingerprint=_string(
                self._state.get(SSKey.SUMMARY_INPUT_FINGERPRINT.value)
            ),
            last_brief_fingerprint=_string(
                self._state.get(SSKey.SUMMARY_LAST_BRIEF_FINGERPRINT.value)
            ),
            active_artifact=_string(
                self._state.get(SSKey.SUMMARY_ACTIVE_ARTIFACT.value)
            )
            or "brief",
        )

    def set_summary_dirty_state(self, value: SummaryDirtyState) -> None:
        self._state[SSKey.SUMMARY_DIRTY.value] = bool(value.is_dirty)
        self._state[SSKey.SUMMARY_INPUT_FINGERPRINT.value] = value.input_fingerprint
        self._state[SSKey.SUMMARY_LAST_BRIEF_FINGERPRINT.value] = (
            value.last_brief_fingerprint
        )
        self._state[SSKey.SUMMARY_ACTIVE_ARTIFACT.value] = value.active_artifact

    def set_summary_dirty(self, value: bool = True) -> None:
        self._state[SSKey.SUMMARY_DIRTY.value] = bool(value)
