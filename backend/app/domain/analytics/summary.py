"""Сводка по всем дисциплинам: ``summarize`` (контракт §7, ТЗ §15.2, §15.7, §15.8).

* Индекс учебной устойчивости — среднее баллов уровней риска с равными весами,
  с ограничениями сверху (есть critical → ≤ 59, есть high → ≤ 74), чтобы одна
  проблемная дисциплина не пряталась за благополучными. Это ориентир, а не
  вероятность и не официальная оценка.
* Приоритеты — critical/high/medium/low; score = вес риска + срочность + достижимость.
  Сроки и задания берутся только из ``next_actions`` (учебного плана).
"""

from __future__ import annotations

import math
from datetime import date
from typing import Iterable

from .config import DEFAULT_CONFIG, AnalyticsConfig
from .risk import CONTACT_TEACHER_RULES
from .texts import (
    INSUFFICIENT_INDEX_LABEL,
    RISK_LABELS,
    index_formula,
    points_target_text,
    positive_message,
    summary_explanation,
)
from .types import (
    RISK_ORDER,
    AnalyticsSummary,
    DisciplineAnalytics,
    IndexInfo,
    NextAction,
    PositiveItem,
    PriorityItem,
)

#: Порядок ключей в zone_counts.
ZONE_COUNT_KEYS: tuple[str, ...] = ("critical", "high", "medium", "low", "stable", "insufficient_data")


def _round_half_up(value: float) -> int:
    return math.floor(value + 0.5)


def compute_index(
    items: Iterable[DisciplineAnalytics], cfg: AnalyticsConfig = DEFAULT_CONFIG
) -> IndexInfo:
    params = cfg.index
    formula = index_formula(cfg)
    known = [d for d in items if d.risk.level in params.level_scores]
    if not known:
        return IndexInfo(
            value=None,
            max=params.max_value,
            zone="insufficient_data",
            label=INSUFFICIENT_INDEX_LABEL,
            is_estimate=True,
            formula=formula,
            caps_applied=(),
            uncapped_value=None,
            disciplines_counted=0,
        )
    mean = sum(params.level_scores[d.risk.level] for d in known) / len(known)
    uncapped = _round_half_up(mean)
    present = {d.risk.level for d in known}
    value = uncapped
    caps_applied: list[str] = []
    for level, cap in sorted(params.caps.items(), key=lambda kv: kv[1]):
        if level in present and cap < uncapped:
            caps_applied.append(level)
            value = min(value, cap)
    zone = params.zones[-1]
    for candidate in params.zones:  # по убыванию нижней границы
        if value >= candidate.min_value:
            zone = candidate
            break
    return IndexInfo(
        value=value,
        max=params.max_value,
        zone=zone.key,
        label=zone.label,
        is_estimate=True,
        formula=formula,
        caps_applied=tuple(caps_applied),
        uncapped_value=mean,
        disciplines_counted=len(known),
    )


def _nearest_action(d: DisciplineAnalytics) -> NextAction | None:
    for action in d.next_actions:
        if action.due_date is not None:
            return action
    return None


def urgency(d: DisciplineAnalytics, today: date, cfg: AnalyticsConfig = DEFAULT_CONFIG) -> float:
    """0..urgency_max: чем ближе ближайший срок из next_actions, тем больше."""
    p = cfg.priority
    action = _nearest_action(d)
    if action is None or action.due_date is None:
        return 0.0
    days = (action.due_date - today).days
    if days <= p.urgency_full_days:
        return float(p.urgency_max)
    if days >= p.urgency_horizon_days:
        return 0.0
    span = p.urgency_horizon_days - p.urgency_full_days
    return p.urgency_max * (p.urgency_horizon_days - days) / span


def improvement_achievable(d: DisciplineAnalytics) -> bool:
    """Улучшение возможно в рамках оставшихся работ (порог ещё достижим)."""
    return d.remaining_points_max > 0 and d.pass_status == "achievable"


def priority_score(d: DisciplineAnalytics, today: date, cfg: AnalyticsConfig = DEFAULT_CONFIG) -> float:
    p = cfg.priority
    weight = p.risk_weights.get(d.risk.level, 0.0)
    bonus = p.achievability_bonus if improvement_achievable(d) else 0.0
    return weight + urgency(d, today, cfg) + bonus


def summarize(
    items: list[DisciplineAnalytics],
    today: date,
    cfg: AnalyticsConfig = DEFAULT_CONFIG,
) -> AnalyticsSummary:
    items = list(items)
    zone_counts = {key: 0 for key in ZONE_COUNT_KEYS}
    for d in items:
        zone_counts[d.risk.level] += 1

    index = compute_index(items, cfg)
    scores = {id(d): priority_score(d, today, cfg) for d in items}
    rank = {level: i for i, level in enumerate(RISK_ORDER)}

    # Дисциплины по убыванию риска; внутри уровня — по срочности/достижимости.
    disciplines = tuple(
        sorted(items, key=lambda d: (rank[d.risk.level], -scores[id(d)], d.title, d.discipline_id))
    )

    ranked: list[tuple[PriorityItem, DisciplineAnalytics]] = []
    for d in items:
        if d.risk.level not in cfg.priority.risk_weights:
            continue
        contact = d.risk.rule in CONTACT_TEACHER_RULES
        action = _nearest_action(d)
        item = PriorityItem(
                discipline_id=d.discipline_id,
                title=d.title,
                risk_level=d.risk.level,
                risk_label=d.risk.label,
                reason=d.risk.reasons[0] if d.risk.reasons else RISK_LABELS[d.risk.level],
                action=d.recommendation,
                points_target=points_target_text(d),
                deadline=None if contact or action is None else action.due_date,
                score=scores[id(d)],
        )
        ranked.append((item, d))
    ranked.sort(key=lambda pd: (-pd[0].score, rank[pd[0].risk_level], pd[0].title, pd[0].discipline_id))
    priorities = [p for p, _ in ranked]

    positives: list[PositiveItem] = []
    for d in disciplines:
        is_positive = d.risk.level == "stable" or (
            d.risk.level == "low"
            and d.projected_semester_points is not None
            and d.projected_semester_points >= d.semester_target - cfg.epsilon
        )
        if not is_positive:
            continue
        message = positive_message(d)
        if message:
            positives.append(PositiveItem(discipline_id=d.discipline_id, title=d.title, message=message))

    first_priority = None
    if ranked:
        top, top_d = ranked[0]
        top_action = None if top_d.risk.rule in CONTACT_TEACHER_RULES else _nearest_action(top_d)
        fallback = top.action[:1].lower() + top.action[1:] if top.action else ""
        first_priority = (top.title, top_action, fallback)

    explanation = summary_explanation(
        index_value=index.value,
        index_label=index.label,
        zone_counts=zone_counts,
        caps_applied=index.caps_applied,
        cap_value=index.value if index.caps_applied else None,
        first_priority=first_priority,
        insufficient_titles=[d.title for d in disciplines if d.risk.level == "insufficient_data"],
    )

    return AnalyticsSummary(
        as_of=today,
        index=index,
        zone_counts=zone_counts,
        explanation=explanation,
        priorities=tuple(priorities),
        positives=tuple(positives),
        disciplines=disciplines,
    )
