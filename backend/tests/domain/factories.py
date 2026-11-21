"""Фабрики входных данных для тестов аналитики (без БД)."""

from __future__ import annotations

from datetime import date, timedelta
from itertools import count
from typing import Iterable, Sequence

from app.domain.analytics import (
    DisciplineInput,
    ItemInput,
    ModuleInput,
    default_assessment_config,
)

TODAY = date(2026, 11, 23)

_ids = count(1)


def item(
    max_points: float,
    points: float | None = None,
    *,
    due: date | int | None = None,
    title: str | None = None,
    kind: str = "homework",
) -> ItemInput:
    """Работа. ``due`` — дата или число дней от TODAY."""
    item_id = next(_ids)
    if isinstance(due, int):
        due = TODAY + timedelta(days=due)
    return ItemInput(
        id=item_id,
        title=title or f"Работа {item_id}",
        kind=kind,
        max_points=max_points,
        due_date=due,
        points=points,
    )


def module(
    status: str,
    *items: ItemInput,
    ordinal: int | None = None,
    title: str | None = None,
    topic_ids: Sequence[int] = (),
) -> ModuleInput:
    module_id = next(_ids)
    return ModuleInput(
        id=module_id,
        ordinal=ordinal if ordinal is not None else module_id,
        title=title or f"Модуль {module_id}",
        status=status,  # type: ignore[arg-type]
        ends_on=None,
        items=tuple(items),
        topic_ids=tuple(topic_ids),
    )


def discipline(
    assessment_type: str,
    modules: Iterable[ModuleInput],
    *,
    exam_points: float | None = None,
    today: date = TODAY,
    semester_progress: float | None = 0.7,
    title: str = "Тестовая дисциплина",
    discipline_id: int | None = None,
) -> DisciplineInput:
    return DisciplineInput(
        discipline_id=discipline_id if discipline_id is not None else next(_ids),
        title=title,
        config=default_assessment_config(assessment_type),
        modules=tuple(modules),
        exam_points=exam_points,
        today=today,
        semester_progress=semester_progress,
    )


def simple(
    assessment_type: str,
    *,
    current: float,
    graded_max: float,
    remaining: float,
    exam_points: float | None = None,
    semester_progress: float | None = 0.7,
    remaining_due: int | None = 10,
    title: str = "Тестовая дисциплина",
) -> DisciplineInput:
    """Дисциплина из двух модулей: завершённый (graded_max, current) и текущий (remaining).

    Сумма максимумов равна semester_points_max, если graded_max + remaining = максимум.
    """
    modules = [module("completed", item(graded_max, current, due=-20, title="Рубежный контроль 1"))]
    if remaining > 0:
        modules.append(
            module("in_progress", item(remaining, None, due=remaining_due, title="Рубежный контроль 2"))
        )
    return discipline(
        assessment_type,
        modules,
        exam_points=exam_points,
        semester_progress=semester_progress,
        title=title,
    )
