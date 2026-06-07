"""Heuristic dependency rules for conditional question visibility."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any, Callable

from constants import FactKey
from schemas import Question

TriggerEvaluator = Callable[
    [dict[str, Any], dict[str, dict[str, Any]], Mapping[str, Any] | None],
    bool,
]
QuestionMatcher = Callable[[str], bool]


@dataclass(frozen=True)
class DependencyRule:
    """Maps a trigger condition to dependent question matching."""

    name: str
    dependent_matcher: QuestionMatcher
    trigger_evaluator: TriggerEvaluator
    notes: str


def _question_blob(question: Question) -> str:
    parts = [
        question.id,
        question.label,
        question.target_path or "",
        question.help or "",
        question.rationale or "",
    ]
    return " ".join(parts).lower()


def _contains_all(text: str, terms: tuple[str, ...]) -> bool:
    return all(term in text for term in terms)


def _contains_any(text: str, terms: tuple[str, ...]) -> bool:
    return any(term in text for term in terms)


def _normalize_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, list):
        return " ".join(_normalize_text(item) for item in value)
    return str(value).strip().lower()


def _is_yes_like(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    text = _normalize_text(value)
    if not text:
        return False

    yes_tokens = (
        "yes",
        "ja",
        "true",
        "required",
        "erforderlich",
        "regelmäßig",
        "regelmaessig",
        "often",
        "häufig",
        "haeufig",
    )
    no_tokens = ("no", "nein", "false", "none", "kein", "keine")
    if _contains_any(text, no_tokens):
        return False
    return _contains_any(text, yes_tokens)


def _has_non_empty_answer(value: Any) -> bool:
    text = _normalize_text(value)
    return bool(text and text not in {"— bitte wählen —", "-"})


def _values_equal(left: Any, right: Any) -> bool:
    if isinstance(left, str) or isinstance(right, str):
        return _normalize_text(left) == _normalize_text(right)
    return left == right


def _matches_declared_dependencies(
    question: Question, answers: dict[str, Any]
) -> bool | None:
    dependencies = question.depends_on
    if not dependencies:
        return None

    for dependency in dependencies:
        source_id = dependency.question_id
        if source_id not in answers:
            return False

        source_value = answers.get(source_id)
        if dependency.equals is not None and not _values_equal(
            source_value, dependency.equals
        ):
            return False
        if dependency.any_of is not None and not any(
            _values_equal(source_value, candidate) for candidate in dependency.any_of
        ):
            return False
        if dependency.is_answered is True and not _has_non_empty_answer(source_value):
            return False
        if dependency.is_answered is False and _has_non_empty_answer(source_value):
            return False
    return True


def _answer_matches(
    answers: dict[str, Any],
    *,
    id_keywords: tuple[str, ...],
    predicate: Callable[[Any], bool],
) -> bool:
    for answer_id, answer_value in answers.items():
        answer_id_text = str(answer_id).lower()
        if not _contains_any(answer_id_text, id_keywords):
            continue
        if predicate(answer_value):
            return True
    return False


def _has_meaningful_fact_value(value: Any) -> bool:
    if value is None:
        return False
    if isinstance(value, str):
        return bool(value.strip())
    if isinstance(value, Mapping):
        return any(_has_meaningful_fact_value(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_has_meaningful_fact_value(item) for item in value)
    return True


def _fact_matches(
    intake_facts: Mapping[str, Any] | None,
    fact_keys: tuple[FactKey, ...],
    *,
    predicate: Callable[[Any], bool],
) -> bool:
    if not isinstance(intake_facts, Mapping):
        return False
    for fact_key in fact_keys:
        value = intake_facts.get(fact_key.value)
        if _has_meaningful_fact_value(value) and predicate(value):
            return True
    return False


def _is_positive_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return value > 0
    if isinstance(value, str):
        try:
            return float(value.strip()) > 0
        except ValueError:
            return False
    return False


def _depends_on_leadership_detail(question: Question) -> bool:
    blob = _question_blob(question)
    return _depends_on_leadership_detail_blob(blob)


def _depends_on_leadership_detail_blob(blob: str) -> bool:
    return _contains_any(
        blob,
        (
            "team size",
            "teamgröße",
            "teamgroesse",
            "direct report",
            "disziplinar",
            "führungsspanne",
            "fuehrungsspanne",
            "stakeholder management",
            "führung",
            "fuehrung",
        ),
    )


def _depends_on_remote_hybrid(question: Question) -> bool:
    blob = _question_blob(question)
    return _depends_on_remote_hybrid_blob(blob)


def _depends_on_remote_hybrid_blob(blob: str) -> bool:
    return _contains_any(
        blob,
        (
            "remote policy",
            "hybrid",
            "onsite",
            "on-site",
            "vor ort",
            "office days",
            "travel",
            "reisen",
            "pendel",
        ),
    )


def _depends_on_salary_budget(question: Question) -> bool:
    blob = _question_blob(question)
    return _depends_on_salary_budget_blob(blob)


def _depends_on_salary_budget_blob(blob: str) -> bool:
    return _contains_any(
        blob,
        (
            "bonus",
            "variable",
            "gehaltsspanne",
            "compensation range",
            "flexibilität",
            "verhandlung",
            "sign-on",
            "equity",
            "aktien",
        ),
    )


def _depends_on_travel(question: Question) -> bool:
    blob = _question_blob(question)
    return _depends_on_travel_blob(blob)


def _depends_on_travel_blob(blob: str) -> bool:
    return _contains_any(
        blob,
        (
            "reisefrequenz",
            "travel frequency",
            "travel percentage",
            "reiseanteil",
            "region",
            "travel region",
            "kundenbesuche",
        ),
    )


def _depends_on_oncall(question: Question) -> bool:
    blob = _question_blob(question)
    return _depends_on_oncall_blob(blob)


def _depends_on_oncall_blob(blob: str) -> bool:
    return _contains_any(
        blob,
        (
            "on-call rotation",
            "rufbereitschaft rotation",
            "rotation",
            "vergütung",
            "zulage",
            "frequency",
            "häufigkeit",
            "haeufigkeit",
        ),
    ) and _contains_any(blob, ("on-call", "rufbereitschaft"))


def _leadership_trigger(
    answers: dict[str, Any],
    answer_meta: dict[str, dict[str, Any]],
    intake_facts: Mapping[str, Any] | None,
) -> bool:
    del answer_meta
    return _answer_matches(
        answers,
        id_keywords=("lead", "manage", "führung", "fuehrung", "reports_to"),
        predicate=_is_yes_like,
    ) or _fact_matches(
        intake_facts,
        (FactKey.COMPANY_REPORTS_TO,),
        predicate=_has_non_empty_answer,
    ) or _fact_matches(
        intake_facts,
        (FactKey.COMPANY_DIRECT_REPORTS_COUNT,),
        predicate=_is_positive_number,
    )


def _remote_trigger(
    answers: dict[str, Any],
    answer_meta: dict[str, dict[str, Any]],
    intake_facts: Mapping[str, Any] | None,
) -> bool:
    del answer_meta
    return _answer_matches(
        answers,
        id_keywords=("remote", "hybrid", "place_of_work", "arbeitsort"),
        predicate=lambda value: _contains_any(
            _normalize_text(value), ("remote", "hybrid")
        ),
    ) or _fact_matches(
        intake_facts,
        (
            FactKey.COMPANY_REMOTE_POLICY,
            FactKey.COMPANY_PLACE_OF_WORK,
        ),
        predicate=lambda value: _contains_any(
            _normalize_text(value), ("remote", "hybrid")
        ),
    )


def _salary_trigger(
    answers: dict[str, Any],
    answer_meta: dict[str, dict[str, Any]],
    intake_facts: Mapping[str, Any] | None,
) -> bool:
    del answer_meta
    return _answer_matches(
        answers,
        id_keywords=(
            "salary",
            "gehalt",
            "budget",
            "compensation",
            "vergütung",
            "verguetung",
        ),
        predicate=_has_non_empty_answer,
    ) or _fact_matches(
        intake_facts,
        (FactKey.BENEFITS_SALARY_RANGE,),
        predicate=_has_meaningful_fact_value,
    )


def _travel_trigger(
    answers: dict[str, Any],
    answer_meta: dict[str, dict[str, Any]],
    intake_facts: Mapping[str, Any] | None,
) -> bool:
    del answer_meta
    return _answer_matches(
        answers,
        id_keywords=("travel", "reise"),
        predicate=_is_yes_like,
    ) or _fact_matches(
        intake_facts,
        (FactKey.ROLE_TRAVEL_REQUIRED,),
        predicate=_is_yes_like,
    )


def _oncall_trigger(
    answers: dict[str, Any],
    answer_meta: dict[str, dict[str, Any]],
    intake_facts: Mapping[str, Any] | None,
) -> bool:
    del answer_meta
    return _answer_matches(
        answers,
        id_keywords=("on_call", "oncall", "rufbereitschaft"),
        predicate=_is_yes_like,
    ) or _fact_matches(
        intake_facts,
        (FactKey.ROLE_ON_CALL,),
        predicate=_is_yes_like,
    )


DEPENDENCY_RULES: tuple[DependencyRule, ...] = (
    DependencyRule(
        name="leadership-detail",
        dependent_matcher=_depends_on_leadership_detail_blob,
        trigger_evaluator=_leadership_trigger,
        notes="Heuristic matching on leadership/team-detail terms.",
    ),
    DependencyRule(
        name="remote-hybrid-detail",
        dependent_matcher=_depends_on_remote_hybrid_blob,
        trigger_evaluator=_remote_trigger,
        notes="Heuristic matching on remote/hybrid detail wording.",
    ),
    DependencyRule(
        name="salary-budget-detail",
        dependent_matcher=_depends_on_salary_budget_blob,
        trigger_evaluator=_salary_trigger,
        notes="Heuristic matching on compensation detail wording.",
    ),
    DependencyRule(
        name="travel-detail",
        dependent_matcher=_depends_on_travel_blob,
        trigger_evaluator=_travel_trigger,
        notes="Heuristic matching on travel frequency/region details.",
    ),
    DependencyRule(
        name="oncall-detail",
        dependent_matcher=_depends_on_oncall_blob,
        trigger_evaluator=_oncall_trigger,
        notes="Heuristic matching on on-call detail wording.",
    ),
)


def should_show_question(
    question: Question,
    answers: dict[str, Any],
    answer_meta: dict[str, Any],
    step_key: str,
    *,
    intake_facts: Mapping[str, Any] | None = None,
) -> bool:
    """Return question visibility based on deterministic dependency rules.

    If declarative `depends_on` metadata exists, it is evaluated first.
    Otherwise, local heuristics (id/label/path/help text) are used as fallback.
    """

    del step_key
    declared_dependency_match = _matches_declared_dependencies(question, answers)
    if declared_dependency_match is not None:
        return declared_dependency_match

    question_blob = _question_blob(question)
    matching_rules = [
        rule for rule in DEPENDENCY_RULES if rule.dependent_matcher(question_blob)
    ]
    if not matching_rules:
        return True

    return any(
        rule.trigger_evaluator(answers, answer_meta, intake_facts)
        for rule in matching_rules
    )
