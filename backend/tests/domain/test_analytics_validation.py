"""Валидация диапазонов входных данных."""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.domain.analytics import (
    AnalyticsInputError,
    AssessmentConfig,
    GradeBand,
    analyze_discipline,
    default_assessment_config,
    validate_discipline_input,
)
from tests.domain.factories import discipline, item, module, simple


@pytest.mark.parametrize("points", [-1, 10.5, float("nan"), float("inf")])
def test_item_points_out_of_range_raise(points):
    inp = discipline("credit", [module("completed", item(10, points), item(90, 50))])
    with pytest.raises(AnalyticsInputError) as exc:
        analyze_discipline(inp)
    assert exc.value.errors
    assert isinstance(exc.value, ValueError)


@pytest.mark.parametrize("max_points", [0, -5])
def test_item_max_points_must_be_positive(max_points):
    inp = discipline("credit", [module("completed", item(max_points, None))])
    assert validate_discipline_input(inp)
    with pytest.raises(AnalyticsInputError):
        analyze_discipline(inp)


@pytest.mark.parametrize("exam_points", [-1, 30.5, 31])
def test_exam_points_out_of_range_raise(exam_points):
    with pytest.raises(AnalyticsInputError, match="вне диапазона"):
        analyze_discipline(simple("exam", current=50, graded_max=70, remaining=0, exam_points=exam_points))


@pytest.mark.parametrize("exam_points", [0, 17, 18, 30])
def test_exam_points_in_range_accepted(exam_points):
    a = analyze_discipline(simple("exam", current=50, graded_max=70, remaining=0, exam_points=exam_points))
    assert a.exam.result == exam_points


def test_exam_points_not_allowed_for_credit_and_distributed_exam():
    for kind in ("credit", "distributed_exam"):
        with pytest.raises(AnalyticsInputError, match="только для типа C"):
            analyze_discipline(simple(kind, current=50, graded_max=100, remaining=0, exam_points=20))


@pytest.mark.parametrize("progress", [-0.1, 1.01])
def test_semester_progress_out_of_range(progress):
    with pytest.raises(AnalyticsInputError, match="semester_progress"):
        analyze_discipline(simple("credit", current=50, graded_max=80, remaining=20, semester_progress=progress))


def test_exam_type_requires_exam_bounds():
    inp = simple("exam", current=40, graded_max=50, remaining=20)
    broken = replace(inp, config=AssessmentConfig("exam", 70, 60))
    with pytest.raises(AnalyticsInputError, match="exam_points_min"):
        analyze_discipline(broken)


def test_unknown_assessment_type_rejected():
    inp = simple("credit", current=40, graded_max=50, remaining=50)
    with pytest.raises(AnalyticsInputError, match="тип аттестации"):
        analyze_discipline(replace(inp, config=replace(inp.config, assessment_type="oral")))
    with pytest.raises(ValueError):
        default_assessment_config("oral")


def test_duplicate_item_ids_rejected():
    first = item(50, 40)
    inp = discipline("credit", [module("completed", first), module("in_progress", replace(first, points=None))])
    with pytest.raises(AnalyticsInputError, match="Повторяется id работы"):
        analyze_discipline(inp)


def test_overlapping_grade_bands_rejected():
    bands = (
        GradeBand("unsatisfactory", "Неуд.", 0, 60),
        GradeBand("satisfactory", "Удовл.", 60, 70),
    )
    inp = simple("distributed_exam", current=40, graded_max=50, remaining=50)
    with pytest.raises(AnalyticsInputError, match="пересекаются"):
        analyze_discipline(replace(inp, config=replace(inp.config, grade_bands=bands)))


def test_all_errors_reported_together():
    inp = discipline(
        "credit",
        [module("completed", item(10, 11), item(10, -1))],
        semester_progress=2,
    )
    errors = validate_discipline_input(inp)
    assert len(errors) == 3


def test_boundary_values_are_valid():
    inp = discipline("credit", [module("completed", item(50, 0), item(50, 50))], semester_progress=1.0)
    assert validate_discipline_input(inp) == []
    a = analyze_discipline(inp)
    assert a.current_semester_points == 50


def test_custom_grade_bands_change_targets():
    """Официальная трактовка границы 60 меняется в конфигурации, а не в коде."""
    bands = (
        GradeBand("unsatisfactory", "Неудовлетворительно", 0, 60),
        GradeBand("satisfactory", "Удовлетворительно", 61, 70),
        GradeBand("good", "Хорошо", 71, 84),
        GradeBand("excellent", "Отлично", 85, 100),
    )
    inp = simple("distributed_exam", current=60, graded_max=90, remaining=10)
    cfg = replace(inp.config, grade_bands=bands, passing_threshold=61)
    a = analyze_discipline(replace(inp, config=cfg))
    assert [t.threshold for t in a.targets] == [61, 71, 85]
    assert a.current_grade.key == "unsatisfactory"
    assert a.targets[0].status == "achievable"
