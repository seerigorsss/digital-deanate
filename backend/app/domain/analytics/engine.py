"""Анализ одной дисциплины: ``analyze_discipline``.

Порядок: валидация → базовые величины (``metrics``) → уровень риска (``risk``)
→ цели и экзамен (``targets``) → тексты (``texts``). Функция чистая и
детерминированная: не читает текущую дату (она приходит в ``inp.today``),
не обращается к БД/сети и не использует случайность.
"""

from __future__ import annotations

from .config import DEFAULT_CONFIG, AnalyticsConfig
from .metrics import compute_facts
from .risk import classify_risk
from .targets import compute_current_grade, compute_exam, compute_targets
from .texts import (
    ASSESSMENT_TYPE_LABELS,
    RISK_LABELS,
    data_issues,
    discipline_explanation,
    discipline_recommendation,
    risk_reasons,
)
from .types import AnalyticsInputError, DisciplineAnalytics, DisciplineInput, RiskAssessment
from .validation import validate_discipline_input


def analyze_discipline(
    inp: DisciplineInput, cfg: AnalyticsConfig = DEFAULT_CONFIG
) -> DisciplineAnalytics:
    """Рассчитывает аналитику по дисциплине.

    Raises:
        AnalyticsInputError: если входные данные нарушают допустимые диапазоны.
    """
    errors = validate_discipline_input(inp, cfg)
    if errors:
        raise AnalyticsInputError(errors)

    f = compute_facts(inp, cfg)
    decision = classify_risk(f, cfg)
    insufficient = decision.level == "insufficient_data"
    # После экзамена (тип C) семестровая «потребность» уже не имеет смысла.
    no_semester_need = insufficient or f.exam_taken

    reasons = risk_reasons(f, decision)
    targets = compute_targets(f, decision, cfg)
    next_actions = f.pending[: cfg.next_actions_limit]
    issues = tuple(data_issues(f))

    if insufficient:
        completeness = "insufficient"
    elif issues:
        completeness = "partial"
    else:
        completeness = "full"

    return DisciplineAnalytics(
        discipline_id=inp.discipline_id,
        title=inp.title,
        as_of=inp.today,
        assessment_type=f.assessment_type,  # type: ignore[arg-type]
        assessment_type_label=ASSESSMENT_TYPE_LABELS[f.assessment_type],
        current_semester_points=f.current,
        semester_points_max=f.semester_max,
        completed_points_max=f.completed_max,
        graded_points_max=f.graded_max,
        remaining_points_max=f.remaining,
        missing_points_max=f.missing,
        max_achievable_semester=f.max_achievable,
        passing_threshold=f.passing,
        semester_target=f.semester_target,
        semester_points_needed=None if no_semester_need else f.deficit,
        semester_progress=inp.semester_progress,
        data_completeness=completeness,  # type: ignore[arg-type]
        data_issues=issues,
        current_pace=f.pace,
        pace_is_reliable=f.pace_reliable,
        projected_semester_points=None if insufficient else f.projection,
        required_share_of_remaining=None if no_semester_need else f.required_share,
        pass_status=decision.pass_status,  # type: ignore[arg-type]
        risk=RiskAssessment(
            level=decision.level,  # type: ignore[arg-type]
            label=RISK_LABELS[decision.level],
            reasons=reasons,
            rule=decision.rule,
        ),
        current_grade=compute_current_grade(f, cfg),
        exam=compute_exam(f, cfg),
        targets=targets,
        modules=f.modules,
        next_actions=next_actions,
        weak_topic_ids=f.weak_topic_ids,
        explanation=discipline_explanation(f, decision, reasons),
        recommendation=discipline_recommendation(f, decision, targets, next_actions),
    )
