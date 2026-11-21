"""Базовые величины по дисциплине (контракт §2–§3).

Здесь только арифметика над входом: суммы по работам, остаток, темп,
целевой семестровый уровень S и порог невозможности F. Никаких оценок риска
и текстов — они в ``risk.py`` / ``targets.py`` / ``texts.py``.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import AnalyticsConfig
from .types import (
    DisciplineInput,
    GradeBand,
    ItemAnalytics,
    ModuleAnalytics,
    NextAction,
)


@dataclass(frozen=True)
class DisciplineFacts:
    """Все вычисленные числа по дисциплине; вход для правил риска, целей и текстов."""

    inp: DisciplineInput
    assessment_type: str
    semester_max: float
    passing: float
    exam_min: float | None
    exam_max: float | None
    exam_points: float | None
    bands: tuple[GradeBand, ...]

    has_items: bool
    items_total_max: float  # Σ max_points всех работ (должна равняться semester_max)
    current: float  # Σ points по работам с результатом
    graded_max: float  # Σ max_points работ с результатом
    completed_max: float  # Σ max_points работ завершённых модулей
    remaining: float  # Σ max_points работ без результата в незавершённых модулях
    missing: float  # Σ max_points работ без результата в завершённых модулях
    missing_titles: tuple[str, ...]
    max_achievable: float  # current + remaining

    semester_target: float  # S: 60 (A, B) или passing − exam_min = 42 (C)
    floor: float  # F: 60 (A, B) или passing − exam_max = 30 (C)
    deficit: float  # D = max(0, S − current)

    pace: float | None  # current / graded_max
    pace_reliable: bool  # graded_max ≥ min_evidence_share · semester_max
    progress_known: bool  # semester_progress задан
    projection: float | None  # current + pace · remaining (если темп надёжен и этап известен)

    modules: tuple[ModuleAnalytics, ...]
    pending: tuple[NextAction, ...]  # все работы без результата в незавершённых модулях, по сроку
    weak_topic_ids: tuple[int, ...]

    # --- производные удобства ---
    @property
    def is_exam(self) -> bool:
        return self.assessment_type == "exam"

    @property
    def exam_taken(self) -> bool:
        return self.is_exam and self.exam_points is not None

    @property
    def sum_mismatch(self) -> bool:
        return self.has_items and abs(self.items_total_max - self.semester_max) > 1e-6

    @property
    def required_share(self) -> float | None:
        """r = D / R; None, если остатка нет или дефицит больше остатка."""
        if self.deficit <= 0:
            return 0.0
        if self.remaining <= 0 or self.deficit > self.remaining:
            return None
        return self.deficit / self.remaining

    @property
    def raw_required_share(self) -> float | None:
        """r без ограничения сверху (может быть > 1); None при нулевом остатке."""
        if self.remaining <= 0:
            return None if self.deficit > 0 else 0.0
        return self.deficit / self.remaining


def grade_for(points: float, bands: tuple[GradeBand, ...], eps: float) -> GradeBand:
    """Диапазон шкалы по нижней границе: последний диапазон с min_points ≤ points."""
    chosen = bands[0]
    for band in bands:
        if points >= band.min_points - eps:
            chosen = band
    return chosen


def compute_facts(inp: DisciplineInput, cfg: AnalyticsConfig) -> DisciplineFacts:
    ac = inp.config
    eps = cfg.epsilon
    bands = ac.grade_bands or cfg.grade_bands
    is_exam = ac.assessment_type == "exam"

    current = graded_max = completed_max = remaining = missing = items_total = 0.0
    missing_titles: list[str] = []
    modules_out: list[ModuleAnalytics] = []
    pending: list[NextAction] = []
    weak_topics: list[int] = []
    has_items = False

    for module in sorted(inp.modules, key=lambda m: (m.ordinal, m.id)):
        m_points = m_graded = m_remaining = m_missing = m_total = 0.0
        items_out: list[ItemAnalytics] = []
        for item in module.items:
            has_items = True
            m_total += item.max_points
            if item.points is not None:
                state = "graded"
                m_points += item.points
                m_graded += item.max_points
            elif module.status == "completed":
                state = "missing"
                m_missing += item.max_points
                missing_titles.append(item.title)
            else:
                state = "pending"
                m_remaining += item.max_points
                days_left = (item.due_date - inp.today).days if item.due_date else None
                pending.append(
                    NextAction(
                        item_id=item.id,
                        title=item.title,
                        kind=item.kind,
                        module_id=module.id,
                        module_title=module.title,
                        max_points=item.max_points,
                        due_date=item.due_date,
                        days_left=days_left,
                        overdue=days_left is not None and days_left < 0,
                    )
                )
            items_out.append(
                ItemAnalytics(
                    id=item.id,
                    title=item.title,
                    kind=item.kind,
                    max_points=item.max_points,
                    points=item.points,
                    due_date=item.due_date,
                    state=state,  # type: ignore[arg-type]
                )
            )
        share = m_points / m_graded if m_graded > 0 else None
        is_weak = share is not None and share < cfg.weak_module_share - eps
        if is_weak:
            weak_topics.extend(t for t in module.topic_ids if t not in weak_topics)
        modules_out.append(
            ModuleAnalytics(
                id=module.id,
                ordinal=module.ordinal,
                title=module.title,
                status=module.status,
                ends_on=module.ends_on,
                points=m_points,
                max_points=m_total,
                graded_max=m_graded,
                remaining=m_remaining,
                missing=m_missing,
                share=share,
                is_weak=is_weak,
                topic_ids=tuple(module.topic_ids),
                items=tuple(items_out),
            )
        )
        current += m_points
        graded_max += m_graded
        remaining += m_remaining
        missing += m_missing
        items_total += m_total
        if module.status == "completed":
            completed_max += m_total

    # Работы без срока — в конце; при равных сроках — по порядку модулей и работ.
    module_order = {m.id: idx for idx, m in enumerate(modules_out)}
    pending.sort(
        key=lambda a: (
            a.due_date is None,
            a.due_date.toordinal() if a.due_date else 0,
            module_order[a.module_id],
            a.item_id,
        )
    )

    passing = float(ac.passing_threshold)
    if is_exam:
        exam_min = float(ac.exam_points_min)  # type: ignore[arg-type]
        exam_max = float(ac.exam_points_max)  # type: ignore[arg-type]
        semester_target = passing - exam_min
        floor = passing - exam_max
    else:
        exam_min = exam_max = None
        semester_target = floor = passing

    deficit = semester_target - current
    if deficit <= eps:  # защита от ошибок округления дробных баллов
        deficit = 0.0

    pace = current / graded_max if graded_max > 0 else None
    pace_reliable = graded_max >= cfg.risk.min_evidence_share * ac.semester_points_max - eps
    progress_known = inp.semester_progress is not None
    projection = (
        current + pace * remaining
        if pace is not None and pace_reliable and progress_known
        else None
    )

    return DisciplineFacts(
        inp=inp,
        assessment_type=ac.assessment_type,
        semester_max=float(ac.semester_points_max),
        passing=passing,
        exam_min=exam_min,
        exam_max=exam_max,
        exam_points=inp.exam_points if is_exam else None,
        bands=bands,
        has_items=has_items,
        items_total_max=items_total,
        current=current,
        graded_max=graded_max,
        completed_max=completed_max,
        remaining=remaining,
        missing=missing,
        missing_titles=tuple(missing_titles),
        max_achievable=current + remaining,
        semester_target=semester_target,
        floor=floor,
        deficit=deficit,
        pace=pace,
        pace_reliable=pace_reliable,
        progress_known=progress_known,
        projection=projection,
        modules=tuple(modules_out),
        pending=tuple(pending),
        weak_topic_ids=tuple(weak_topics),
    )
