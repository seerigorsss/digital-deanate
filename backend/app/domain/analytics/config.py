"""Конфигурация модуля академической аналитики.

ВСЕ числовые параметры алгоритма собраны здесь: шкала оценок, параметры типов
аттестации, коэффициенты классификации риска, веса и зоны индекса, веса
приоритизации. Код ``engine.py`` / ``risk.py`` / ``summary.py`` не содержит
«магических» порогов — только ссылки на поля ``AnalyticsConfig``.

Чтобы изменить правило (например, официальную трактовку границы 60), создайте
свой экземпляр ``AnalyticsConfig`` (``dataclasses.replace(DEFAULT_CONFIG, ...)``)
и передайте его в ``analyze_discipline(..., cfg=...)`` / ``summarize(..., cfg=...)``.
"""

from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType
from typing import Mapping

from .types import AssessmentConfig, GradeBand

# --------------------------------------------------------------------------- #
# Шкала итоговой оценки (ТЗ §14.1)
# --------------------------------------------------------------------------- #

#: ДОПУЩЕНИЕ: в исходной формулировке границы пересекаются на 60
#: («0–60 неуд» и «60–70 удовл»). Для прототипа принято однозначное правило
#: ТЗ §14.1: 0–59 — неудовлетворительно, 60–70 — удовлетворительно.
#: Оценка определяется по НИЖНЕЙ границе диапазона: балл ≥ min_points.
#: Поэтому дробные значения между диапазонами (например, 59,5 или 70,5)
#: относятся к нижнему диапазону. Чтобы принять другую трактовку,
#: достаточно поменять min_points здесь (или передать grade_bands в
#: AssessmentConfig конкретной дисциплины).
DEFAULT_GRADE_BANDS: tuple[GradeBand, ...] = (
    GradeBand(key="unsatisfactory", label="Неудовлетворительно", min_points=0, max_points=59),
    GradeBand(key="satisfactory", label="Удовлетворительно", min_points=60, max_points=70),
    GradeBand(key="good", label="Хорошо", min_points=71, max_points=84),
    GradeBand(key="excellent", label="Отлично", min_points=85, max_points=100),
)


# --------------------------------------------------------------------------- #
# Типы аттестации (ТЗ §14.2)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class AssessmentTypeDefaults:
    """Стандартные параметры типа аттестации (может быть переопределено в дисциплине)."""

    semester_points_max: float  # максимум семестровой части
    passing_threshold: float  # итоговый порог сдачи
    exam_points_min: float | None  # обязательный минимум на экзамене (только C)
    exam_points_max: float | None  # максимум экзаменационной части (только C)
    grade_targets: bool  # True — цели 60/71/85 по шкале; False — одна цель «Зачёт»


ASSESSMENT_TYPE_DEFAULTS: Mapping[str, AssessmentTypeDefaults] = MappingProxyType(
    {
        # A — зачёт: не менее 60 семестровых баллов, оценки по шкале нет.
        "credit": AssessmentTypeDefaults(
            semester_points_max=100, passing_threshold=60,
            exam_points_min=None, exam_points_max=None, grade_targets=False,
        ),
        # B — распределённый экзамен: все 0–100 набираются в семестре.
        "distributed_exam": AssessmentTypeDefaults(
            semester_points_max=100, passing_threshold=60,
            exam_points_min=None, exam_points_max=None, grade_targets=True,
        ),
        # C — экзамен: до 70 в семестре + 18–30 на экзамене, минимум 18 обязателен.
        "exam": AssessmentTypeDefaults(
            semester_points_max=70, passing_threshold=60,
            exam_points_min=18, exam_points_max=30, grade_targets=True,
        ),
    }
)


# --------------------------------------------------------------------------- #
# Классификация риска (контракт §4)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class RiskParams:
    #: Темп (current / graded_max) считается надёжным, если оценено не меньше
    #: этой доли семестрового максимума. 0.25 → 25 из 100 (A, B) или 17,5 из 70 (C).
    #: В контракте значение не задано; взято стартовое значение из docs/assumptions.md (A4):
    #: после одной-двух работ (< 25 %) о темпе судить рано, после первого модуля — можно.
    #: Демо-данные дают ожидаемые уровни при любом значении в диапазоне (0; 0.4].
    min_evidence_share: float = 0.25
    #: insufficient_data, если баллы не внесены за работы завершённых модулей
    #: на сумму больше этой доли их максимума.
    insufficient_missing_share: float = 0.5
    #: high, если нужно набрать не меньше этой доли оставшегося максимума.
    high_share: float = 0.9
    #: high, если (требуемая доля остатка − текущий темп) не меньше этого значения
    #: (только при надёжном темпе): «темп нужно резко повысить».
    pace_gap_high: float = 0.25
    #: medium, если нужно набрать не меньше этой доли остатка («запас ограничен»).
    medium_share: float = 0.7
    #: medium, если требуемая доля остатка выше текущего темпа на это значение и больше.
    pace_gap_medium: float = 0.1
    #: stable, если ориентир по темпу ≥ S + stable_margin · semester_points_max
    #: (запас 10 баллов из 100 или 7 из 70) ...
    stable_margin: float = 0.1
    #: ... и требуемая доля остатка не больше этого значения.
    stable_max_share: float = 0.5


# --------------------------------------------------------------------------- #
# Индекс учебной устойчивости (контракт §7, ТЗ §15.7)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class IndexZone:
    key: str  # stable | medium | high | critical
    label: str
    min_value: int  # нижняя граница зоны (включительно)


@dataclass(frozen=True)
class IndexParams:
    #: Максимум шкалы индекса.
    max_value: int = 100
    #: Баллы зон дисциплин; индекс — их среднее с равными весами.
    #: insufficient_data в среднем не участвует.
    level_scores: Mapping[str, float] = MappingProxyType(
        {"stable": 100, "low": 80, "medium": 60, "high": 35, "critical": 10}
    )
    #: Ограничения сверху: если есть хотя бы одна дисциплина уровня, индекс
    #: не выше значения. Так одна критическая дисциплина не прячется за зелёными.
    caps: Mapping[str, int] = MappingProxyType({"critical": 59, "high": 74})
    #: Зоны индекса — по убыванию нижней границы.
    zones: tuple[IndexZone, ...] = (
        IndexZone(key="stable", label="Стабильно", min_value=80),
        IndexZone(key="medium", label="Требует внимания", min_value=65),
        IndexZone(key="high", label="Высокий риск", min_value=50),
        IndexZone(key="critical", label="Критично", min_value=0),
    )


# --------------------------------------------------------------------------- #
# Приоритизация «Что подтянуть в первую очередь» (контракт §7, ТЗ §15.8)
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class PriorityParams:
    #: Базовый вес по уровню риска. stable и insufficient_data в приоритеты не попадают.
    risk_weights: Mapping[str, float] = MappingProxyType(
        {"critical": 1000, "high": 700, "medium": 400, "low": 100}
    )
    #: Максимум добавки за срочность.
    urgency_max: float = 100
    #: Если до ближайшего срока не больше стольких дней (или срок прошёл) — максимум срочности.
    urgency_full_days: int = 3
    #: Если до ближайшего срока столько дней и больше — срочность 0. Между — линейно.
    urgency_horizon_days: int = 30
    #: Добавка, если улучшение возможно в рамках оставшихся работ.
    achievability_bonus: float = 50


# --------------------------------------------------------------------------- #
# Общая конфигурация
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class AnalyticsConfig:
    grade_bands: tuple[GradeBand, ...] = DEFAULT_GRADE_BANDS
    assessment_types: Mapping[str, AssessmentTypeDefaults] = ASSESSMENT_TYPE_DEFAULTS
    risk: RiskParams = RiskParams()
    index: IndexParams = IndexParams()
    priority: PriorityParams = PriorityParams()
    #: Модуль считается «слабым», если доля набранного по оценённым работам ниже этого
    #: значения; его темы попадают в weak_topic_ids (для подбора материалов).
    weak_module_share: float = 0.6
    #: Сколько ближайших работ возвращать в next_actions.
    next_actions_limit: int = 3
    #: Допуск сравнения дробных баллов (защита от ошибок округления float).
    epsilon: float = 1e-9


DEFAULT_CONFIG = AnalyticsConfig()


def default_assessment_config(
    assessment_type: str, cfg: AnalyticsConfig = DEFAULT_CONFIG
) -> AssessmentConfig:
    """Стандартная ``AssessmentConfig`` для типа аттестации (A/B/C) из конфигурации."""
    try:
        defaults = cfg.assessment_types[assessment_type]
    except KeyError as exc:
        raise ValueError(f"Неизвестный тип аттестации: {assessment_type!r}") from exc
    return AssessmentConfig(
        assessment_type=assessment_type,  # type: ignore[arg-type]
        semester_points_max=defaults.semester_points_max,
        passing_threshold=defaults.passing_threshold,
        exam_points_min=defaults.exam_points_min,
        exam_points_max=defaults.exam_points_max,
    )
