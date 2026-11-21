"""Типы входа и выхода модуля академической аналитики.

Структуры соответствуют контракту ``docs/analytics-contract.md``.
Входные структуры неизменяемы (``frozen=True``). Выходные структуры тоже
неизменяемы и имеют метод ``to_dict()``, который возвращает JSON-сериализуемый
словарь (числа, строки, bool, None, list, dict; даты — ISO-строки).

Модуль не зависит от БД, FastAPI, ORM и сети.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import date
from typing import Any, Literal, Mapping

# --------------------------------------------------------------------------- #
# Перечисления
# --------------------------------------------------------------------------- #

AssessmentType = Literal["credit", "distributed_exam", "exam"]  # A, B, C из ТЗ §14.2
ModuleStatus = Literal["completed", "in_progress", "upcoming"]
RiskLevel = Literal["critical", "high", "medium", "low", "stable", "insufficient_data"]
PassStatus = Literal["secured", "achievable", "unreachable", "passed", "failed", "unknown"]
TargetStatus = Literal["reached", "achievable", "unreachable", "unknown"]
ItemState = Literal["graded", "pending", "missing"]
DataCompleteness = Literal["full", "partial", "insufficient"]

ASSESSMENT_TYPES: tuple[str, ...] = ("credit", "distributed_exam", "exam")
MODULE_STATUSES: tuple[str, ...] = ("completed", "in_progress", "upcoming")

#: Уровни риска в порядке убывания серьёзности (для сортировки дисциплин).
#: ``insufficient_data`` стоит перед ``stable``: такие дисциплины требуют
#: проверки данных, но не считаются ни рискованными, ни благополучными.
RISK_ORDER: tuple[str, ...] = (
    "critical",
    "high",
    "medium",
    "low",
    "insufficient_data",
    "stable",
)


class AnalyticsInputError(ValueError):
    """Входные данные нарушают допустимые диапазоны (см. ``validation.py``)."""

    def __init__(self, errors: list[str] | tuple[str, ...]):
        self.errors: tuple[str, ...] = tuple(errors)
        super().__init__("; ".join(self.errors))


# --------------------------------------------------------------------------- #
# Вход
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class GradeBand:
    """Диапазон шкалы итоговой оценки. Принадлежность определяется нижней границей."""

    key: str  # unsatisfactory | satisfactory | good | excellent
    label: str  # «Удовлетворительно» и т.п.
    min_points: float
    max_points: float


@dataclass(frozen=True)
class ItemInput:
    """Вид работы внутри модуля (ДЗ, ЛР, РК, тест, проект, активность)."""

    id: int
    title: str
    kind: str  # homework | lab | control | test | project | activity
    max_points: float
    due_date: date | None
    points: float | None  # None = результата в системе нет


@dataclass(frozen=True)
class ModuleInput:
    id: int
    ordinal: int
    title: str
    status: ModuleStatus
    ends_on: date | None  # срок закрытия модуля
    items: tuple[ItemInput, ...]
    topic_ids: tuple[int, ...] = ()


@dataclass(frozen=True)
class AssessmentConfig:
    """Параметры аттестации конкретной дисциплины (ТЗ §14.2, §15.6)."""

    assessment_type: AssessmentType
    semester_points_max: float  # 100 (A, B) или 70 (C)
    passing_threshold: float  # 60
    exam_points_min: float | None = None  # 18 (только C)
    exam_points_max: float | None = None  # 30 (только C)
    grade_bands: tuple[GradeBand, ...] | None = None  # переопределение шкалы для дисциплины


@dataclass(frozen=True)
class DisciplineInput:
    discipline_id: int
    title: str
    config: AssessmentConfig
    modules: tuple[ModuleInput, ...]
    exam_points: float | None  # результат экзамена (C), None — не сдавал
    today: date
    semester_progress: float | None  # 0..1 — доля прошедшего учебного периода; None — неизвестно


# --------------------------------------------------------------------------- #
# Вспомогательные функции сериализации
# --------------------------------------------------------------------------- #


def _num(value: float | None, digits: int = 2) -> float | None:
    """Округляет число для вывода; ``-0.0`` превращает в ``0.0``."""
    if value is None:
        return None
    if isinstance(value, float) and not math.isfinite(value):
        return None
    result = round(float(value), digits)
    return 0.0 if result == 0 else result


def _share(value: float | None) -> float | None:
    return _num(value, 3)


def _iso(value: date | None) -> str | None:
    return value.isoformat() if value is not None else None


# --------------------------------------------------------------------------- #
# Выход: дисциплина
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class ItemAnalytics:
    id: int
    title: str
    kind: str
    max_points: float
    points: float | None
    due_date: date | None
    state: ItemState  # graded | pending | missing

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "kind": self.kind,
            "max_points": _num(self.max_points),
            "points": _num(self.points),
            "due_date": _iso(self.due_date),
            "state": self.state,
        }


@dataclass(frozen=True)
class ModuleAnalytics:
    id: int
    ordinal: int
    title: str
    status: str
    ends_on: date | None
    points: float  # сумма набранных баллов
    max_points: float  # сумма максимумов всех работ модуля
    graded_max: float  # сумма максимумов оценённых работ
    remaining: float  # максимум работ, которые ещё впереди
    missing: float  # максимум работ завершённого модуля без результата
    share: float | None  # points / graded_max
    is_weak: bool  # share < weak_module_share
    topic_ids: tuple[int, ...]
    items: tuple[ItemAnalytics, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "ordinal": self.ordinal,
            "title": self.title,
            "status": self.status,
            "ends_on": _iso(self.ends_on),
            "points": _num(self.points),
            "max_points": _num(self.max_points),
            "graded_max": _num(self.graded_max),
            "remaining": _num(self.remaining),
            "missing": _num(self.missing),
            "share": _share(self.share),
            "is_weak": self.is_weak,
            "topic_ids": list(self.topic_ids),
            "items": [item.to_dict() for item in self.items],
        }


@dataclass(frozen=True)
class RiskAssessment:
    level: RiskLevel
    label: str
    reasons: tuple[str, ...]  # 1–3 фразы с числами
    rule: str  # код сработавшего правила (для прозрачности и отладки)

    def to_dict(self) -> dict[str, Any]:
        return {
            "level": self.level,
            "label": self.label,
            "reasons": list(self.reasons),
            "rule": self.rule,
        }


@dataclass(frozen=True)
class GradeInfo:
    key: str
    label: str

    def to_dict(self) -> dict[str, Any]:
        return {"key": self.key, "label": self.label}


@dataclass(frozen=True)
class ExamInfo:
    """Экзаменационная часть (только тип C)."""

    points_min: float
    points_max: float
    result: float | None  # результат экзамена, None — не сдавал
    passed: bool | None  # выполнен ли обязательный минимум на экзамене
    required_for_pass: float | None  # сколько нужно на экзамене для итоговых 60 (при текущем семестре)
    total_at_exam_min: float  # текущий семестр + минимум экзамена
    total_at_exam_max: float  # текущий семестр + максимум экзамена
    final_total: float | None  # семестр + экзамен (если экзамен сдан)
    total_max_possible: float  # максимум семестра с остатком + максимум экзамена

    def to_dict(self) -> dict[str, Any]:
        return {
            "points_min": _num(self.points_min),
            "points_max": _num(self.points_max),
            "result": _num(self.result),
            "passed": self.passed,
            "required_for_pass": _num(self.required_for_pass),
            "total_at_exam_min": _num(self.total_at_exam_min),
            "total_at_exam_max": _num(self.total_at_exam_max),
            "final_total": _num(self.final_total),
            "total_max_possible": _num(self.total_max_possible),
        }


@dataclass(frozen=True)
class TargetAnalytics:
    threshold: float
    grade_key: str
    label: str
    status: TargetStatus
    points_needed_semester: float | None  # сколько ещё нужно набрать в семестре
    required_share_of_remaining: float | None  # доля оставшегося максимума
    exam_points_needed: float | None  # только C: нужный балл на экзамене
    extra_semester_points_needed: float | None  # только C: добрать в семестре, если на экзамене нужно > 30
    reachable_with_current_points: bool | None  # только C: хватает ли текущих семестровых баллов
    explanation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "threshold": _num(self.threshold),
            "grade_key": self.grade_key,
            "label": self.label,
            "status": self.status,
            "points_needed_semester": _num(self.points_needed_semester),
            "required_share_of_remaining": _share(self.required_share_of_remaining),
            "exam_points_needed": _num(self.exam_points_needed),
            "extra_semester_points_needed": _num(self.extra_semester_points_needed),
            "reachable_with_current_points": self.reachable_with_current_points,
            "explanation": self.explanation,
        }


@dataclass(frozen=True)
class NextAction:
    """Ближайшая работа без результата в незавершённом модуле (из учебного плана)."""

    item_id: int
    title: str
    kind: str
    module_id: int
    module_title: str
    max_points: float
    due_date: date | None
    days_left: int | None
    overdue: bool

    def to_dict(self) -> dict[str, Any]:
        return {
            "item_id": self.item_id,
            "title": self.title,
            "kind": self.kind,
            "module_id": self.module_id,
            "module_title": self.module_title,
            "max_points": _num(self.max_points),
            "due_date": _iso(self.due_date),
            "days_left": self.days_left,
            "overdue": self.overdue,
        }


@dataclass(frozen=True)
class DisciplineAnalytics:
    discipline_id: int
    title: str
    as_of: date
    assessment_type: AssessmentType
    assessment_type_label: str
    current_semester_points: float
    semester_points_max: float
    completed_points_max: float
    graded_points_max: float
    remaining_points_max: float
    missing_points_max: float
    max_achievable_semester: float
    passing_threshold: float
    semester_target: float  # S из контракта: 60 (A, B) или 42 (C)
    semester_points_needed: float | None  # max(0, S − current); None при недостатке данных
    semester_progress: float | None
    data_completeness: DataCompleteness
    data_issues: tuple[str, ...]
    current_pace: float | None
    pace_is_reliable: bool
    projected_semester_points: float | None  # ориентир, не прогноз
    required_share_of_remaining: float | None
    pass_status: PassStatus
    risk: RiskAssessment
    current_grade: GradeInfo | None
    exam: ExamInfo | None
    targets: tuple[TargetAnalytics, ...]
    modules: tuple[ModuleAnalytics, ...]
    next_actions: tuple[NextAction, ...]
    weak_topic_ids: tuple[int, ...]
    explanation: str
    recommendation: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "discipline_id": self.discipline_id,
            "title": self.title,
            "as_of": _iso(self.as_of),
            "assessment_type": self.assessment_type,
            "assessment_type_label": self.assessment_type_label,
            "current_semester_points": _num(self.current_semester_points),
            "semester_points_max": _num(self.semester_points_max),
            "completed_points_max": _num(self.completed_points_max),
            "graded_points_max": _num(self.graded_points_max),
            "remaining_points_max": _num(self.remaining_points_max),
            "missing_points_max": _num(self.missing_points_max),
            "max_achievable_semester": _num(self.max_achievable_semester),
            "passing_threshold": _num(self.passing_threshold),
            "semester_target": _num(self.semester_target),
            "semester_points_needed": _num(self.semester_points_needed),
            "semester_progress": _share(self.semester_progress),
            "data_completeness": self.data_completeness,
            "data_issues": list(self.data_issues),
            "current_pace": _share(self.current_pace),
            "pace_is_reliable": self.pace_is_reliable,
            "projected_semester_points": _num(self.projected_semester_points),
            "required_share_of_remaining": _share(self.required_share_of_remaining),
            "pass_status": self.pass_status,
            "risk": self.risk.to_dict(),
            "current_grade": self.current_grade.to_dict() if self.current_grade else None,
            "exam": self.exam.to_dict() if self.exam else None,
            "targets": [t.to_dict() for t in self.targets],
            "modules": [m.to_dict() for m in self.modules],
            "next_actions": [a.to_dict() for a in self.next_actions],
            "weak_topic_ids": list(self.weak_topic_ids),
            "explanation": self.explanation,
            "recommendation": self.recommendation,
        }


# --------------------------------------------------------------------------- #
# Выход: сводка («Академический радар»)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class IndexInfo:
    value: int | None  # None — нет ни одной дисциплины с известным риском
    max: int
    zone: str  # stable | medium | high | critical | insufficient_data
    label: str
    is_estimate: bool
    formula: str
    caps_applied: tuple[str, ...]  # уровни, ограничение которых снизило значение
    uncapped_value: float | None  # среднее до ограничений (для прозрачности)
    disciplines_counted: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "max": self.max,
            "zone": self.zone,
            "label": self.label,
            "is_estimate": self.is_estimate,
            "formula": self.formula,
            "caps_applied": list(self.caps_applied),
            "uncapped_value": _num(self.uncapped_value, 1),
            "disciplines_counted": self.disciplines_counted,
        }


@dataclass(frozen=True)
class PriorityItem:
    discipline_id: int
    title: str
    risk_level: str
    risk_label: str
    reason: str
    action: str
    points_target: str
    deadline: date | None
    score: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "discipline_id": self.discipline_id,
            "title": self.title,
            "risk_level": self.risk_level,
            "risk_label": self.risk_label,
            "reason": self.reason,
            "action": self.action,
            "points_target": self.points_target,
            "deadline": _iso(self.deadline),
            "score": _num(self.score, 1),
        }


@dataclass(frozen=True)
class PositiveItem:
    discipline_id: int
    title: str
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {"discipline_id": self.discipline_id, "title": self.title, "message": self.message}


@dataclass(frozen=True)
class AnalyticsSummary:
    as_of: date
    index: IndexInfo
    zone_counts: Mapping[str, int]
    explanation: str
    priorities: tuple[PriorityItem, ...]
    positives: tuple[PositiveItem, ...]
    disciplines: tuple[DisciplineAnalytics, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, Any]:
        return {
            "as_of": _iso(self.as_of),
            "index": self.index.to_dict(),
            "zone_counts": dict(self.zone_counts),
            "explanation": self.explanation,
            "priorities": [p.to_dict() for p in self.priorities],
            "positives": [p.to_dict() for p in self.positives],
            "disciplines": [d.to_dict() for d in self.disciplines],
        }
