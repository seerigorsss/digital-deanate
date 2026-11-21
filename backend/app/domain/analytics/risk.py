"""Классификация уровня риска дисциплины (контракт §4, ТЗ §15.4).

Правила проверяются по порядку, срабатывает первое совпадение. Каждое правило
имеет код (``rule``), по которому ``texts.py`` строит объяснение с числами.

Уровень риска — объяснимая эвристика, а НЕ статистическая вероятность сдачи.
"""

from __future__ import annotations

from dataclasses import dataclass

from .config import AnalyticsConfig
from .metrics import DisciplineFacts


@dataclass(frozen=True)
class RiskDecision:
    level: str  # critical | high | medium | low | stable | insufficient_data
    pass_status: str  # secured | achievable | unreachable | passed | failed | unknown
    rule: str  # код сработавшего правила
    share: float | None = None  # r = D / R, если правило его использует


#: Коды правил, при которых нужен разговор с преподавателем / деканатом.
CONTACT_TEACHER_RULES = frozenset(
    {"unreachable", "no_remaining", "exam_below_minimum", "exam_total_below_threshold"}
)

#: Правила шага 6 контракта (оценка по доле остатка и темпу).
SHARE_RULES = frozenset(
    {
        "almost_all_remaining",
        "pace_gap_high",
        "limited_margin",
        "pace_gap_medium",
        "projection_margin",
        "realistic",
    }
)


def classify_risk(f: DisciplineFacts, cfg: AnalyticsConfig) -> RiskDecision:
    p = cfg.risk
    eps = cfg.epsilon

    # 1. Недостаточно данных: нет плана, ничего не оценено или много пропусков
    #    в уже завершённых модулях. Ложной точности не показываем (ТЗ §15.4, §18 п.9).
    if not f.has_items:
        return RiskDecision("insufficient_data", "unknown", "no_items")
    if f.graded_max <= eps:
        return RiskDecision("insufficient_data", "unknown", "no_graded")
    if f.missing > p.insufficient_missing_share * f.completed_max + eps:
        return RiskDecision("insufficient_data", "unknown", "missing_data")

    # 2. Тип C, экзамен уже сдан: минимум 18 обязателен независимо от суммы (ТЗ §15.5).
    if f.exam_taken:
        assert f.exam_points is not None and f.exam_min is not None
        if f.exam_points < f.exam_min - eps:
            return RiskDecision("critical", "failed", "exam_below_minimum")
        if f.current + f.exam_points >= f.passing - eps:
            return RiskDecision("stable", "passed", "exam_passed")
        return RiskDecision("critical", "failed", "exam_total_below_threshold")

    # 3. Семестровый уровень S уже обеспечен (для C — при минимальных 18 на экзамене).
    if f.current >= f.semester_target - eps:
        return RiskDecision("stable", "secured", "semester_secured", 0.0)

    # 4. Порог математически недостижим даже при всём остатке (и 30 на экзамене для C).
    if f.max_achievable < f.floor - eps:
        return RiskDecision("critical", "unreachable", "unreachable")

    # 5. Тип C: даже весь остаток не даёт S → сдать можно только с экзаменом выше минимума.
    if f.is_exam and f.max_achievable < f.semester_target - eps:
        return RiskDecision("high", "achievable", "exam_above_minimum_required")

    # 6. Порог достижим: оцениваем, какую долю остатка нужно набрать и как это
    #    соотносится с текущим темпом.
    if f.remaining <= eps:  # защитная ветка: фактически покрыта пунктами 4–5
        return RiskDecision("critical", "unreachable", "no_remaining")
    r = f.deficit / f.remaining
    pace = f.pace if f.pace is not None else 0.0

    if r >= p.high_share - eps:
        return RiskDecision("high", "achievable", "almost_all_remaining", r)
    if f.pace_reliable and r - pace >= p.pace_gap_high - eps:
        return RiskDecision("high", "achievable", "pace_gap_high", r)
    if r >= p.medium_share - eps:
        return RiskDecision("medium", "achievable", "limited_margin", r)
    if f.pace_reliable and r - pace >= p.pace_gap_medium - eps:
        return RiskDecision("medium", "achievable", "pace_gap_medium", r)
    if (
        f.pace_reliable
        and f.projection is not None
        and f.projection >= f.semester_target + p.stable_margin * f.semester_max - eps
        and r <= p.stable_max_share + eps
    ):
        return RiskDecision("stable", "achievable", "projection_margin", r)
    # Ранний семестр с ненадёжным темпом сюда попадает при r < medium_share:
    # низкий балл при большом остатке не даёт critical (ТЗ §18 п.6).
    return RiskDecision("low", "achievable", "realistic", r)
