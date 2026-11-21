"""Цели по оценкам и экзаменационная часть (контракт §5, ТЗ §15.5).

* A (зачёт): одна цель — порог сдачи («Зачёт»).
* B (распределённый экзамен): 60, 71, 85 — нижние границы диапазонов шкалы.
* C (экзамен): 60, 71, 85 по итогу = семестр + экзамен. Для цели T:
  need = T − семестр; если need ≤ 30 — на экзамене нужно max(18, need);
  если need > 30 — при текущих семестровых баллах цель недостижима, нужно добрать
  extra = T − 30 − семестр в оставшихся работах (если остаток позволяет).
"""

from __future__ import annotations

from .config import AnalyticsConfig
from .metrics import DisciplineFacts, grade_for
from .risk import RiskDecision
from .texts import CREDIT_TARGET_KEY, CREDIT_TARGET_LABEL, target_explanation
from .types import ExamInfo, GradeInfo, TargetAnalytics


def _target_definitions(f: DisciplineFacts, cfg: AnalyticsConfig) -> list[tuple[float, str, str]]:
    defaults = cfg.assessment_types[f.assessment_type]
    if not defaults.grade_targets:
        return [(f.passing, CREDIT_TARGET_KEY, CREDIT_TARGET_LABEL)]
    eps = cfg.epsilon
    defs = [
        (float(b.min_points), b.key, b.label)
        for b in f.bands
        if b.min_points >= f.passing - eps
    ]
    if not defs or abs(defs[0][0] - f.passing) > eps:
        band = grade_for(f.passing, f.bands, eps)
        defs.insert(0, (f.passing, band.key, band.label))
    return defs


def _target(
    f: DisciplineFacts,
    cfg: AnalyticsConfig,
    decision: RiskDecision,
    threshold: float,
    key: str,
    label: str,
) -> TargetAnalytics:
    eps = cfg.epsilon

    def make(status: str, **kw: float | bool | None) -> TargetAnalytics:
        return TargetAnalytics(
            threshold=threshold,
            grade_key=key,
            label=label,
            status=status,  # type: ignore[arg-type]
            points_needed_semester=kw.get("need"),  # type: ignore[arg-type]
            required_share_of_remaining=kw.get("share"),  # type: ignore[arg-type]
            exam_points_needed=kw.get("exam_needed"),  # type: ignore[arg-type]
            extra_semester_points_needed=kw.get("extra"),  # type: ignore[arg-type]
            reachable_with_current_points=kw.get("with_current"),  # type: ignore[arg-type]
            explanation=target_explanation(
                f,
                threshold,
                label,
                status,
                need=kw.get("need"),  # type: ignore[arg-type]
                share=kw.get("share"),  # type: ignore[arg-type]
                exam_needed=kw.get("exam_needed"),  # type: ignore[arg-type]
                extra=kw.get("extra"),  # type: ignore[arg-type]
            ),
        )

    insufficient = decision.level == "insufficient_data"

    # ---- A, B: всё набирается в семестре ----
    if not f.is_exam:
        need = threshold - f.current
        if need <= eps:
            return make("reached", need=0.0)
        if insufficient:
            return make("unknown")
        if need <= f.remaining + eps:
            return make("achievable", need=need, share=need / f.remaining)
        return make("unreachable", need=need)

    # ---- C: семестр + экзамен ----
    assert f.exam_min is not None and f.exam_max is not None
    if insufficient:
        return make("unknown")
    if f.exam_taken:
        exam = f.exam_points or 0.0
        ok = exam >= f.exam_min - eps and f.current + exam >= threshold - eps
        return make("reached" if ok else "unreachable")

    need = threshold - f.current
    if need <= f.exam_max + eps:
        # Хватает экзамена; даже если по сумме нужно меньше 18, требуется минимум 18.
        return make(
            "achievable",
            need=0.0,
            exam_needed=max(f.exam_min, need),
            extra=0.0,
            with_current=True,
        )
    extra = threshold - f.exam_max - f.current
    if extra <= f.remaining + eps:
        return make(
            "achievable",
            need=extra,
            share=extra / f.remaining if f.remaining > 0 else None,
            exam_needed=f.exam_max,
            extra=extra,
            with_current=False,
        )
    return make("unreachable", need=extra, extra=extra, with_current=False)


def compute_targets(
    f: DisciplineFacts, decision: RiskDecision, cfg: AnalyticsConfig
) -> tuple[TargetAnalytics, ...]:
    return tuple(
        _target(f, cfg, decision, threshold, key, label)
        for threshold, key, label in _target_definitions(f, cfg)
    )


def compute_exam(f: DisciplineFacts, cfg: AnalyticsConfig) -> ExamInfo | None:
    if not f.is_exam:
        return None
    assert f.exam_min is not None and f.exam_max is not None
    eps = cfg.epsilon
    if f.exam_taken:
        exam = f.exam_points or 0.0
        return ExamInfo(
            points_min=f.exam_min,
            points_max=f.exam_max,
            result=exam,
            passed=exam >= f.exam_min - eps,
            required_for_pass=None,
            total_at_exam_min=f.current + f.exam_min,
            total_at_exam_max=f.current + f.exam_max,
            final_total=f.current + exam,
            total_max_possible=f.current + exam,
        )
    need = f.passing - f.current
    required = max(f.exam_min, need) if need <= f.exam_max + eps else None
    return ExamInfo(
        points_min=f.exam_min,
        points_max=f.exam_max,
        result=None,
        passed=None,
        required_for_pass=required,
        total_at_exam_min=f.current + f.exam_min,
        total_at_exam_max=f.current + f.exam_max,
        final_total=None,
        total_max_possible=f.max_achievable + f.exam_max,
    )


def compute_current_grade(f: DisciplineFacts, cfg: AnalyticsConfig) -> GradeInfo | None:
    """B — оценка по текущей сумме; C со сданным экзаменом — по итогу; иначе None."""
    eps = cfg.epsilon
    if f.assessment_type == "distributed_exam" and f.graded_max > 0:
        band = grade_for(f.current, f.bands, eps)
        return GradeInfo(key=band.key, label=band.label)
    if f.exam_taken:
        exam = f.exam_points or 0.0
        assert f.exam_min is not None
        band = (
            grade_for(f.current + exam, f.bands, eps)
            if exam >= f.exam_min - eps
            else f.bands[0]
        )
        return GradeInfo(key=band.key, label=band.label)
    return None
