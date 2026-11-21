"""Граничные случаи и ветки правил риска (контракт §3–§5)."""

from __future__ import annotations

import pytest

from app.domain.analytics import DEFAULT_CONFIG, analyze_discipline
from tests.domain.factories import discipline, item, module, simple


def _target(analytics, threshold):
    return next(t for t in analytics.targets if t.threshold == threshold)


# --------------------------------------------------------------------------- #
# Зачёт 59/60
# --------------------------------------------------------------------------- #


def test_credit_59_with_zero_remaining_is_critical():
    a = analyze_discipline(simple("credit", current=59, graded_max=100, remaining=0))
    assert a.risk.level == "critical"
    assert a.pass_status == "unreachable"
    assert _target(a, 60).status == "unreachable"
    assert a.required_share_of_remaining is None


def test_credit_60_with_zero_remaining_is_stable():
    a = analyze_discipline(simple("credit", current=60, graded_max=100, remaining=0))
    assert a.risk.level == "stable"
    assert a.pass_status == "secured"
    assert _target(a, 60).status == "reached"
    assert a.current_grade is None  # у зачёта нет оценки по шкале
    assert [t.grade_key for t in a.targets] == ["credit"]


# --------------------------------------------------------------------------- #
# Распределённый экзамен 60/71/85 и шкала оценок
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "current, reached",
    [
        (59, []),
        (60, [60]),
        (70, [60]),
        (71, [60, 71]),
        (84.5, [60, 71]),
        (85, [60, 71, 85]),
    ],
)
def test_distributed_exam_thresholds_reached_exactly_at_boundaries(current, reached):
    a = analyze_discipline(simple("distributed_exam", current=current, graded_max=90, remaining=10))
    assert [int(t.threshold) for t in a.targets if t.status == "reached"] == reached


@pytest.mark.parametrize(
    "current, grade",
    [(59, "unsatisfactory"), (59.5, "unsatisfactory"), (60, "satisfactory"), (70, "satisfactory"),
     (70.5, "satisfactory"), (71, "good"), (84, "good"), (85, "excellent"), (100, "excellent")],
)
def test_grade_scale_boundaries_use_lower_bound(current, grade):
    a = analyze_discipline(simple("distributed_exam", current=current, graded_max=100, remaining=0))
    assert a.current_grade.key == grade


def test_distributed_exam_targets_with_different_remaining_share():
    a = analyze_discipline(simple("distributed_exam", current=57, graded_max=65, remaining=35))
    t60, t71, t85 = (_target(a, x) for x in (60, 71, 85))
    assert (t60.points_needed_semester, t71.points_needed_semester, t85.points_needed_semester) == (3, 14, 28)
    assert t85.required_share_of_remaining == pytest.approx(0.8)
    assert all(t.status == "achievable" for t in (t60, t71, t85))


# --------------------------------------------------------------------------- #
# Экзамен: 70 + 18, минимум 18, максимум 30
# --------------------------------------------------------------------------- #


def test_exam_17_is_critical_even_if_total_reaches_threshold():
    a = analyze_discipline(simple("exam", current=70, graded_max=70, remaining=0, exam_points=17))
    assert a.exam.final_total == 87  # формально ≥ 60
    assert a.exam.passed is False
    assert a.risk.level == "critical"
    assert a.risk.rule == "exam_below_minimum"
    assert a.pass_status == "failed"
    assert all(t.status == "unreachable" for t in a.targets)
    assert a.current_grade.key == "unsatisfactory"
    assert "ниже обязательного минимума 18" in a.risk.reasons[0]
    assert "преподавател" in a.recommendation


def test_exam_18_is_admitted_as_passed():
    a = analyze_discipline(simple("exam", current=42, graded_max=70, remaining=0, exam_points=18))
    assert a.exam.passed is True
    assert a.exam.final_total == 60
    assert a.pass_status == "passed"
    assert a.risk.level == "stable"
    assert a.current_grade.key == "satisfactory"
    assert [t.status for t in a.targets] == ["reached", "unreachable", "unreachable"]


def test_exam_18_but_total_below_60_is_critical():
    a = analyze_discipline(simple("exam", current=41, graded_max=70, remaining=0, exam_points=18))
    assert a.exam.passed is True  # минимум на экзамене выполнен
    assert a.pass_status == "failed"
    assert a.risk.level == "critical"
    assert a.risk.rule == "exam_total_below_threshold"


def test_exam_semester_target_boundary_41_vs_42():
    a41 = analyze_discipline(simple("exam", current=41, graded_max=60, remaining=10))
    a42 = analyze_discipline(simple("exam", current=42, graded_max=60, remaining=10))
    assert a42.risk.rule == "semester_secured" and a42.pass_status == "secured"
    assert a41.risk.rule != "semester_secured"
    assert a41.exam.required_for_pass == 19
    assert a42.exam.required_for_pass == 18
    # Для C даже «обеспечено» означает: на экзамене всё равно нужно ≥ 18.
    assert any("не меньше 18" in r for r in a42.risk.reasons)


@pytest.mark.parametrize(
    "current, remaining, need, with_current, extra",
    [
        (30, 20, 30, True, 0),  # ровно 30 — достижимо одним экзаменом
        (29, 20, None, False, 1),  # нужно 31 → добрать 1 в семестре
    ],
)
def test_exam_need_exactly_30_vs_31(current, remaining, need, with_current, extra):
    a = analyze_discipline(simple("exam", current=current, graded_max=70 - remaining, remaining=remaining))
    t60 = _target(a, 60)
    assert t60.reachable_with_current_points is with_current
    assert t60.extra_semester_points_needed == extra
    assert t60.exam_points_needed == 30
    assert a.exam.required_for_pass == need


def test_exam_unreachable_floor_29_is_critical_30_is_high():
    a29 = analyze_discipline(simple("exam", current=19, graded_max=60, remaining=10))  # максимум 29
    a30 = analyze_discipline(simple("exam", current=20, graded_max=60, remaining=10))  # максимум 30
    assert a29.risk.level == "critical" and a29.pass_status == "unreachable"
    assert a29.exam.total_max_possible == 59
    assert a30.risk.level == "high" and a30.risk.rule == "exam_above_minimum_required"
    assert a30.exam.total_max_possible == 60
    assert "не меньше 30 баллов" in a30.risk.reasons[0]


def test_exam_target_85_unreachable_when_remaining_too_small():
    a = analyze_discipline(simple("exam", current=45, graded_max=65, remaining=5))
    t85 = _target(a, 85)
    assert t85.status == "unreachable"
    assert t85.extra_semester_points_needed == 10
    assert t85.exam_points_needed is None
    assert "не хватает" in t85.explanation


def test_exam_totals_at_18_and_30_always_shown():
    a = analyze_discipline(simple("exam", current=33, graded_max=50, remaining=20))
    assert (a.exam.total_at_exam_min, a.exam.total_at_exam_max) == (51, 63)
    assert "Итог при 18 на экзамене — 51, при 30 — 63" in a.explanation


# --------------------------------------------------------------------------- #
# Ветки правил шага 6 (доля остатка r и темп)
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "current, graded_max, remaining, level, rule",
    [
        # r = 18/20 = 0.9 → high (почти весь остаток)
        (42, 80, 20, "high", "almost_all_remaining"),
        # r = 0.8, темп 0.55 → разрыв 0.25 → high
        (44, 80, 20, "high", "pace_gap_high"),
        # r = 0.7, темп ненадёжен (оценено 20 из 100) → medium
        (4, 20, 80, "medium", "limited_margin"),
        # r = 40/60 ≈ 0.67, темп 0.5 → разрыв 0.17 ≥ 0.1 → medium
        (20, 40, 60, "medium", "pace_gap_medium"),
        # r = 0.3, темп 0.9, ориентир 90 ≥ 70 → stable
        (45, 50, 50, "stable", "projection_margin"),
        # r = 0.6, темп 0.6 → разрыва нет, но ориентир 60 < 70 → low
        (30, 50, 50, "low", "realistic"),
        # ранний семестр: r = 0.6, темп ненадёжен → low (только доля остатка)
        (12, 20, 80, "low", "realistic"),
    ],
)
def test_share_rules(current, graded_max, remaining, level, rule):
    a = analyze_discipline(
        simple("distributed_exam", current=current, graded_max=graded_max, remaining=remaining)
    )
    assert (a.risk.level, a.risk.rule) == (level, rule)
    assert 1 <= len(a.risk.reasons) <= 3


def test_min_evidence_share_controls_pace_reliability():
    reliable = analyze_discipline(simple("credit", current=15, graded_max=25, remaining=75))
    unreliable = analyze_discipline(simple("credit", current=14.5, graded_max=24, remaining=76))
    assert DEFAULT_CONFIG.risk.min_evidence_share == 0.25
    assert reliable.pace_is_reliable is True
    assert unreliable.pace_is_reliable is False
    # Для C порог — 25 % от 70 = 17,5.
    c_reliable = analyze_discipline(simple("exam", current=10, graded_max=17.5, remaining=52.5))
    c_unreliable = analyze_discipline(simple("exam", current=10, graded_max=17, remaining=53))
    assert c_reliable.pace_is_reliable is True and c_unreliable.pace_is_reliable is False


# --------------------------------------------------------------------------- #
# Нулевой остаток, нет данных, частичные данные
# --------------------------------------------------------------------------- #


def test_zero_remaining_distributed_exam_below_threshold():
    a = analyze_discipline(simple("distributed_exam", current=55, graded_max=100, remaining=0))
    assert a.remaining_points_max == 0
    assert a.risk.level == "critical"
    assert any("оставшегося потенциала нет" in r for r in a.risk.reasons)
    assert a.next_actions == ()


def test_no_modules_is_insufficient_data():
    a = analyze_discipline(discipline("credit", []))
    assert a.risk.level == "insufficient_data"
    assert a.risk.rule == "no_items"
    assert a.data_completeness == "insufficient"
    assert a.pass_status == "unknown"


def test_many_missing_results_in_completed_modules_is_insufficient_data():
    inp = discipline(
        "credit",
        [
            module("completed", item(20, 15), item(15, None, title="Эссе"), item(15, None, title="Тест")),
            module("in_progress", item(50, None, due=5)),
        ],
    )
    a = analyze_discipline(inp)
    assert a.missing_points_max == 30
    assert a.risk.level == "insufficient_data" and a.risk.rule == "missing_data"
    assert "«Эссе»" in a.recommendation
    assert [i.state for i in a.modules[0].items] == ["graded", "missing", "missing"]


def test_few_missing_results_gives_partial_completeness_but_risk_is_computed():
    inp = discipline(
        "credit",
        [
            module("completed", item(40, 36), item(10, None, title="Опрос")),
            module("in_progress", item(50, None, due=5)),
        ],
    )
    a = analyze_discipline(inp)
    assert a.risk.level != "insufficient_data"
    assert a.data_completeness == "partial"
    assert a.missing_points_max == 10
    # Пропуск не считается ни нулём, ни потенциалом.
    assert a.remaining_points_max == 50
    assert a.max_achievable_semester == 86


def test_sum_of_items_not_equal_semester_max_is_data_issue_not_error():
    a = analyze_discipline(simple("credit", current=40, graded_max=50, remaining=40))  # сумма 90
    assert a.data_completeness == "partial"
    assert any("не совпадает" in i for i in a.data_issues)


# --------------------------------------------------------------------------- #
# Слабые темы и ближайшие действия
# --------------------------------------------------------------------------- #


def test_weak_topics_are_from_modules_below_weak_share():
    inp = discipline(
        "distributed_exam",
        [
            module("completed", item(50, 30), topic_ids=[1, 2]),  # 0.6 — не слабый
            module("completed", item(20, 11.9), topic_ids=[3]),  # 0.595 — слабый
            module("in_progress", item(30, None, due=3), topic_ids=[4]),  # не оценён
        ],
    )
    a = analyze_discipline(inp)
    assert a.weak_topic_ids == (3,)
    assert [m.is_weak for m in a.modules] == [False, True, False]


def test_next_actions_sorted_by_due_date_limited_and_flag_overdue():
    inp = discipline(
        "credit",
        [
            module("completed", item(30, 25)),
            module(
                "in_progress",
                item(10, None, due=None, title="Без срока"),
                item(10, None, due=12, title="Позже"),
                item(10, None, due=-2, title="Просрочено"),
                item(10, None, due=0, title="Сегодня"),
            ),
            module("upcoming", item(30, None, due=40, title="Следующий модуль")),
        ],
    )
    a = analyze_discipline(inp)
    assert [x.title for x in a.next_actions] == ["Просрочено", "Сегодня", "Позже"]
    assert a.next_actions[0].overdue is True and a.next_actions[0].days_left == -2
    assert a.next_actions[1].days_left == 0 and not a.next_actions[1].overdue
    assert "уточните у преподавателя" in a.recommendation
