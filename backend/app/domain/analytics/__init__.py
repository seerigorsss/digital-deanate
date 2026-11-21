"""Доменный модуль академической аналитики «Цифрового деканата».

Чистый, детерминированный и объяснимый расчёт по ТЗ §14–§18 и контракту
``docs/analytics-contract.md``. Описание модели — ``docs/analytics-model.md``.

Публичный API::

    from app.domain.analytics import analyze_discipline, summarize, DEFAULT_CONFIG

    item = analyze_discipline(discipline_input)          # DisciplineAnalytics
    radar = summarize([item, ...], today=date(2026, 11, 23))  # AnalyticsSummary
    radar.to_dict()                                       # JSON для API
"""

from .config import (
    DEFAULT_CONFIG,
    DEFAULT_GRADE_BANDS,
    AnalyticsConfig,
    AssessmentTypeDefaults,
    IndexParams,
    IndexZone,
    PriorityParams,
    RiskParams,
    default_assessment_config,
)
from .engine import analyze_discipline
from .materials import MaterialRef, TopicMaterials, materials_for_weak_topics, select_materials_for_topic
from .summary import compute_index, summarize
from .types import (
    AnalyticsInputError,
    AnalyticsSummary,
    AssessmentConfig,
    AssessmentType,
    DisciplineAnalytics,
    DisciplineInput,
    ExamInfo,
    GradeBand,
    GradeInfo,
    IndexInfo,
    ItemAnalytics,
    ItemInput,
    ModuleAnalytics,
    ModuleInput,
    ModuleStatus,
    NextAction,
    PositiveItem,
    PriorityItem,
    RiskAssessment,
    RiskLevel,
    TargetAnalytics,
)
from .validation import validate_discipline_input

__all__ = [
    # функции
    "analyze_discipline",
    "summarize",
    "compute_index",
    "validate_discipline_input",
    "default_assessment_config",
    "select_materials_for_topic",
    "materials_for_weak_topics",
    # конфигурация
    "DEFAULT_CONFIG",
    "DEFAULT_GRADE_BANDS",
    "AnalyticsConfig",
    "AssessmentTypeDefaults",
    "RiskParams",
    "IndexParams",
    "IndexZone",
    "PriorityParams",
    # вход
    "AssessmentType",
    "ModuleStatus",
    "GradeBand",
    "ItemInput",
    "ModuleInput",
    "AssessmentConfig",
    "DisciplineInput",
    # выход
    "RiskLevel",
    "ItemAnalytics",
    "ModuleAnalytics",
    "RiskAssessment",
    "GradeInfo",
    "ExamInfo",
    "TargetAnalytics",
    "NextAction",
    "DisciplineAnalytics",
    "IndexInfo",
    "PriorityItem",
    "PositiveItem",
    "AnalyticsSummary",
    "AnalyticsInputError",
    # материалы
    "MaterialRef",
    "TopicMaterials",
]
