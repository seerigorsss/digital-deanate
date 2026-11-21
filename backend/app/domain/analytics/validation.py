"""Проверка входных данных аналитики.

Нарушение диапазонов (баллы вне [0, max], экзамен вне [0, exam_points_max],
отрицательные максимумы, NaN, неизвестный тип аттестации и т.п.) — это ошибка
входа: ``analyze_discipline`` бросает ``AnalyticsInputError`` со списком всех
нарушений. Считать риск по заведомо некорректным баллам нельзя — получится
ложный результат.

Несовпадение суммы максимумов работ с ``semester_points_max`` ошибкой НЕ
является (контракт §2): это попадает в ``data_issues``, полнота — ``partial``.
"""

from __future__ import annotations

import math
from datetime import date

from .config import DEFAULT_CONFIG, AnalyticsConfig
from .types import ASSESSMENT_TYPES, MODULE_STATUSES, DisciplineInput, GradeBand


def _is_number(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _validate_bands(bands: tuple[GradeBand, ...], errors: list[str]) -> None:
    if not bands:
        errors.append("Шкала оценок пуста.")
        return
    previous: GradeBand | None = None
    for band in bands:
        if not (_is_number(band.min_points) and _is_number(band.max_points)):
            errors.append(f"Диапазон оценки «{band.label}»: границы должны быть числами.")
            continue
        if band.min_points > band.max_points:
            errors.append(f"Диапазон оценки «{band.label}»: нижняя граница больше верхней.")
        if previous is not None and band.min_points <= previous.max_points:
            errors.append(
                f"Диапазоны оценок «{previous.label}» и «{band.label}» пересекаются "
                "или идут не по возрастанию."
            )
        previous = band


def validate_discipline_input(
    inp: DisciplineInput, cfg: AnalyticsConfig = DEFAULT_CONFIG
) -> list[str]:
    """Возвращает список нарушений (пустой — вход корректен)."""
    errors: list[str] = []
    ac = inp.config

    if not isinstance(inp.today, date):
        errors.append("today должен быть датой (datetime.date).")

    if ac.assessment_type not in ASSESSMENT_TYPES:
        errors.append(f"Неизвестный тип аттестации: {ac.assessment_type!r}.")

    if not _is_number(ac.semester_points_max) or ac.semester_points_max <= 0:
        errors.append("semester_points_max должен быть положительным числом.")
    if not _is_number(ac.passing_threshold) or ac.passing_threshold <= 0:
        errors.append("passing_threshold должен быть положительным числом.")

    if ac.assessment_type == "exam":
        if not _is_number(ac.exam_points_min) or not _is_number(ac.exam_points_max):
            errors.append("Для экзамена (тип C) нужны exam_points_min и exam_points_max.")
        elif not (0 <= ac.exam_points_min <= ac.exam_points_max):  # type: ignore[operator]
            errors.append("Должно выполняться 0 ≤ exam_points_min ≤ exam_points_max.")
        elif _is_number(ac.passing_threshold) and _is_number(ac.semester_points_max):
            if ac.semester_points_max + ac.exam_points_max < ac.passing_threshold:  # type: ignore[operator]
                errors.append("Порог сдачи больше суммы максимумов семестра и экзамена.")
    else:
        if inp.exam_points is not None:
            errors.append("Результат экзамена задаётся только для типа C (exam).")
        if _is_number(ac.passing_threshold) and _is_number(ac.semester_points_max):
            if ac.passing_threshold > ac.semester_points_max:
                errors.append("Порог сдачи больше максимума семестровой части.")

    if inp.exam_points is not None:
        if not _is_number(inp.exam_points):
            errors.append("exam_points должен быть числом.")
        elif _is_number(ac.exam_points_max) and not (0 <= inp.exam_points <= ac.exam_points_max):  # type: ignore[operator]
            errors.append(
                f"Результат экзамена {inp.exam_points} вне диапазона [0, {ac.exam_points_max}]."
            )

    if inp.semester_progress is not None:
        if not _is_number(inp.semester_progress) or not (0 <= inp.semester_progress <= 1):
            errors.append("semester_progress должен быть в диапазоне [0, 1] или None.")

    _validate_bands(ac.grade_bands or cfg.grade_bands, errors)

    module_ids: set[int] = set()
    item_ids: set[int] = set()
    for module in inp.modules:
        if module.id in module_ids:
            errors.append(f"Повторяется id модуля {module.id}.")
        module_ids.add(module.id)
        if module.status not in MODULE_STATUSES:
            errors.append(f"Модуль «{module.title}»: неизвестный статус {module.status!r}.")
        for item in module.items:
            label = f"Работа «{item.title}» (модуль «{module.title}»)"
            if item.id in item_ids:
                errors.append(f"Повторяется id работы {item.id}.")
            item_ids.add(item.id)
            if not _is_number(item.max_points) or item.max_points <= 0:
                errors.append(f"{label}: max_points должен быть положительным числом.")
                continue
            if item.points is not None:
                if not _is_number(item.points):
                    errors.append(f"{label}: баллы должны быть числом.")
                elif not (0 <= item.points <= item.max_points):
                    errors.append(
                        f"{label}: баллы {item.points} вне диапазона [0, {item.max_points}]."
                    )
    return errors
