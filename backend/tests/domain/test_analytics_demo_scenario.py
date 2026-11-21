"""Сценарий на демо-данных: curriculum.json + demo_results.json, today = 2026-11-23.

Проверяем ожидаемый уровень риска по каждой дисциплине и сводный индекс
(зона и значение ±1) для двух демо-студентов (ТЗ §19).
"""

from __future__ import annotations

from dataclasses import replace

import pytest

from app.domain.analytics import analyze_discipline, summarize
from tests.domain.demo_data import (
    DEMO_TODAY,
    build_inputs,
    load_demo_results,
    semester_progress,
)

STUDENTS = ("student1", "student2")


def _cases():
    results = load_demo_results()
    for student in STUDENTS:
        for key, value in results[student].items():
            yield pytest.param(student, key, value["expected_risk"], id=f"{student}-{key}")


def test_semester_progress_is_share_of_days():
    # 2026-09-01 → 2026-12-27: 117 дней; к 2026-11-23 прошло 83.
    assert semester_progress(DEMO_TODAY) == pytest.approx(83 / 117)


@pytest.mark.parametrize("student, key, expected", list(_cases()))
def test_demo_expected_risk_per_discipline(student, key, expected):
    inputs = dict(build_inputs(student))
    analytics = analyze_discipline(inputs[key])
    assert analytics.risk.level == expected, analytics.risk.reasons


@pytest.mark.parametrize("student", STUDENTS)
def test_demo_expected_index(student):
    expected = load_demo_results()["expected_index"][student]
    items = [analyze_discipline(inp) for _, inp in build_inputs(student)]
    summary = summarize(items, DEMO_TODAY)
    assert summary.index.zone == expected["zone"]
    assert abs(summary.index.value - expected["value"]) <= 1
    assert sum(summary.zone_counts.values()) == len(items)


def test_demo_student1_is_mostly_stable():
    items = [analyze_discipline(inp) for _, inp in build_inputs("student1")]
    s = summarize(items, DEMO_TODAY)
    assert s.index.value == 90
    assert s.zone_counts["stable"] == 4
    assert len(s.positives) >= 4
    assert s.priorities[0].title == "Дискретная математика"
    assert s.priorities[0].deadline.isoformat() == "2026-11-26"  # «Домашнее задание 3» из плана


def test_demo_student2_has_several_high_risk_disciplines():
    items = [analyze_discipline(inp) for _, inp in build_inputs("student2")]
    s = summarize(items, DEMO_TODAY)
    assert s.index.value == 51
    assert s.zone_counts["high"] == 3 and s.zone_counts["critical"] == 1
    assert s.priorities[0].risk_level == "critical"
    assert s.priorities[0].title == "Теория механизмов и машин"
    assert s.disciplines[0].risk.level == "critical"


def test_demo_three_assessment_types_are_calculated_differently():
    by_key = {key: analyze_discipline(inp) for key, inp in build_inputs("student1")}
    calc = by_key["calculus3"]  # C
    oop = by_key["oop-cpp"]  # B
    graphics = by_key["eng-graphics"]  # A
    assert calc.semester_target == 42 and calc.exam is not None
    assert calc.exam.total_at_exam_min == 60 and calc.exam.total_at_exam_max == 72
    assert [t.threshold for t in oop.targets] == [60, 71, 85] and oop.exam is None
    assert [t.grade_key for t in graphics.targets] == ["credit"] and graphics.exam is None


def test_demo_recalculation_when_scores_change():
    """Изменение баллов автоматически меняет уровень, рекомендацию и индекс (ТЗ §19)."""
    inputs = build_inputs("student1")
    before = [analyze_discipline(inp) for _, inp in inputs]

    def grade_discrete_math(inp):
        modules = []
        for m in inp.modules:
            items = tuple(
                replace(it, points={"Домашнее задание 3": 9, "Рубежный контроль 2": 13}.get(it.title, it.points))
                if m.ordinal == 2
                else it
                for it in m.items
            )
            modules.append(replace(m, items=items))
        return replace(inp, modules=tuple(modules))

    after_inputs = [(k, grade_discrete_math(i) if k == "discrete-math" else i) for k, i in inputs]
    after = [analyze_discipline(inp) for _, inp in after_inputs]

    dm_before = next(a for a in before if a.title == "Дискретная математика")
    dm_after = next(a for a in after if a.title == "Дискретная математика")
    assert dm_before.risk.level == "medium"
    assert dm_after.current_semester_points == 42
    assert dm_after.risk.level in ("low", "stable")
    assert dm_after.recommendation != dm_before.recommendation

    idx_before = summarize(before, DEMO_TODAY).index.value
    idx_after = summarize(after, DEMO_TODAY).index.value
    assert idx_after > idx_before
