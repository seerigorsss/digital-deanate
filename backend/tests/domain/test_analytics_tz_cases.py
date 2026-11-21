"""Обязательные случаи ТЗ §18 «Тестирование аналитики» — по одному тесту на пункт."""

from __future__ import annotations

from datetime import date

import pytest

from app.domain.analytics import (
    MaterialRef,
    analyze_discipline,
    materials_for_weak_topics,
    select_materials_for_topic,
    summarize,
)
from tests.domain.factories import TODAY, discipline, item, module, simple


def _target(analytics, threshold):
    return next(t for t in analytics.targets if t.threshold == threshold)


# 1. Зачёт: 59 баллов — порог не достигнут; 60 — достигнут.
def test_tz18_01_credit_59_not_reached_60_reached():
    a59 = analyze_discipline(simple("credit", current=59, graded_max=80, remaining=20))
    a60 = analyze_discipline(simple("credit", current=60, graded_max=80, remaining=20))

    assert _target(a59, 60).status == "achievable"
    assert _target(a59, 60).points_needed_semester == 1
    assert a59.pass_status == "achievable"
    assert a59.risk.rule != "semester_secured"

    assert _target(a60, 60).status == "reached"
    assert a60.pass_status == "secured"
    assert a60.risk.level == "stable"
    assert "Зачётный минимум" in a60.risk.reasons[0]


# 2. Распределённый экзамен: достижимость 60, 71 и 85 при разном остатке.
@pytest.mark.parametrize(
    "remaining, expected",
    [
        # current = 50 во всех вариантах; меняется только оставшийся максимум
        (40, {60: "achievable", 71: "achievable", 85: "achievable"}),
        (25, {60: "achievable", 71: "achievable", 85: "unreachable"}),
        (15, {60: "achievable", 71: "unreachable", 85: "unreachable"}),
        (5, {60: "unreachable", 71: "unreachable", 85: "unreachable"}),
    ],
)
def test_tz18_02_distributed_exam_60_71_85_depend_on_remaining(remaining, expected):
    a = analyze_discipline(
        simple("distributed_exam", current=50, graded_max=100 - remaining, remaining=remaining)
    )
    assert [t.threshold for t in a.targets] == [60, 71, 85]
    assert {int(t.threshold): t.status for t in a.targets} == expected
    for t in a.targets:
        assert t.points_needed_semester == t.threshold - 50
        if t.status == "achievable":
            assert t.required_share_of_remaining == pytest.approx((t.threshold - 50) / remaining)


# 3. Экзамен с отдельной частью: 70 семестровых + 18 экзаменационных.
def test_tz18_03_exam_70_semester_plus_18_exam():
    before = analyze_discipline(simple("exam", current=70, graded_max=70, remaining=0))
    assert before.exam.total_at_exam_min == 88
    assert before.exam.total_at_exam_max == 100
    assert before.exam.required_for_pass == 18
    assert before.risk.level == "stable" and before.pass_status == "secured"
    # До экзамена цель не считается «достигнутой»: экзамен ещё нужно сдать минимум на 18.
    assert all(t.status == "achievable" and t.exam_points_needed == 18 for t in before.targets)

    after = analyze_discipline(simple("exam", current=70, graded_max=70, remaining=0, exam_points=18))
    assert after.exam.final_total == 88
    assert after.exam.passed is True
    assert after.pass_status == "passed"
    assert after.risk.level == "stable"
    assert after.current_grade.key == "excellent"
    assert [t.status for t in after.targets] == ["reached", "reached", "reached"]


# 4. Для цели нужно меньше 18 на экзамене — всё равно требуется минимум 18.
def test_tz18_04_exam_need_below_18_still_requires_18():
    a = analyze_discipline(simple("exam", current=55, graded_max=60, remaining=10))
    t60, t71, t85 = (_target(a, x) for x in (60, 71, 85))
    assert t60.exam_points_needed == 18  # по сумме хватило бы 5
    assert t71.exam_points_needed == 18  # по сумме хватило бы 16
    assert t85.exam_points_needed == 30
    assert a.exam.required_for_pass == 18
    assert "обязательный минимум" in t60.explanation
    assert a.exam.total_at_exam_min == 73 and a.exam.total_at_exam_max == 85


# 5. Для цели нужно больше 30 — недостижимость при текущих семестровых баллах.
def test_tz18_05_exam_need_above_30_unreachable_with_current_points():
    a = analyze_discipline(simple("exam", current=40, graded_max=50, remaining=20))
    t85 = _target(a, 85)
    assert t85.reachable_with_current_points is False
    assert "недостижимо даже с 30" in t85.explanation
    # Семестр продолжается — показываем, сколько добрать до экзамена.
    assert t85.extra_semester_points_needed == 15
    assert t85.status == "achievable"
    assert t85.exam_points_needed == 30

    closed = analyze_discipline(simple("exam", current=50, graded_max=70, remaining=0))
    t85c = _target(closed, 85)
    assert t85c.reachable_with_current_points is False
    assert t85c.status == "unreachable"
    assert t85c.extra_semester_points_needed == 5


# 6. Низкий результат в начале семестра при большом остатке — не автоматически critical.
def test_tz18_06_low_score_early_semester_is_not_critical():
    early = discipline(
        "distributed_exam",
        [
            module("completed", item(20, 6, due=-60)),  # 30 % за первый модуль
            module("in_progress", item(20, None, due=7), item(20, None, due=20)),
            module("upcoming", item(40, None, due=60)),
        ],
        semester_progress=0.15,
    )
    a = analyze_discipline(early)
    assert a.risk.level not in ("critical", "high")
    assert a.pass_status == "achievable"
    assert a.pace_is_reliable is False
    assert a.projected_semester_points is None
    assert any("судить рано" in r for r in a.risk.reasons)


# 7. Низкий результат в конце семестра при малом остатке корректно повышает риск.
def test_tz18_07_low_score_late_semester_raises_risk():
    # Одинаковый темп 55 %, но разный этап семестра.
    early = analyze_discipline(
        simple("distributed_exam", current=11, graded_max=20, remaining=80, semester_progress=0.2)
    )
    late = analyze_discipline(
        simple("distributed_exam", current=48.4, graded_max=88, remaining=12, semester_progress=0.9)
    )
    very_late = analyze_discipline(
        simple("distributed_exam", current=49.5, graded_max=90, remaining=10, semester_progress=0.95)
    )
    order = ["stable", "low", "medium", "high", "critical"]
    assert early.risk.level == "low"
    assert late.risk.level == "high"
    assert very_late.risk.level == "critical" and very_late.pass_status == "unreachable"
    assert order.index(early.risk.level) < order.index(late.risk.level) < order.index(very_late.risk.level)


# 8. Все модули завершены — оставшийся потенциал равен нулю.
def test_tz18_08_all_modules_completed_remaining_is_zero():
    inp = discipline(
        "credit",
        [
            module("completed", item(50, 35, due=-40), item(10, 8, due=-30)),
            module("completed", item(40, 22, due=-5)),
        ],
        semester_progress=1.0,
    )
    a = analyze_discipline(inp)
    assert a.remaining_points_max == 0
    assert a.max_achievable_semester == a.current_semester_points == 65
    assert a.completed_points_max == 100
    assert a.next_actions == ()
    assert a.risk.level == "stable" and a.pass_status == "secured"
    assert "оставшегося потенциала нет" in a.explanation


# 9. Нет данных о прогрессе — система не выдаёт ложную точность.
def test_tz18_09_no_progress_data_no_false_precision():
    nothing_graded = analyze_discipline(
        discipline(
            "distributed_exam",
            [module("in_progress", item(50, None, due=10)), module("upcoming", item(50, None))],
            semester_progress=None,
        )
    )
    assert nothing_graded.risk.level == "insufficient_data"
    assert nothing_graded.pass_status == "unknown"
    assert nothing_graded.data_completeness == "insufficient"
    assert nothing_graded.projected_semester_points is None
    assert nothing_graded.required_share_of_remaining is None
    assert nothing_graded.current_pace is None
    assert all(t.status == "unknown" for t in nothing_graded.targets)
    assert nothing_graded.current_grade is None

    # Баллы есть, но этап семестра неизвестен: факты показываем, ориентир по темпу — нет.
    unknown_stage = analyze_discipline(
        simple("distributed_exam", current=45, graded_max=50, remaining=50, semester_progress=None)
    )
    assert unknown_stage.current_semester_points == 45
    assert unknown_stage.projected_semester_points is None
    assert unknown_stage.data_completeness == "partial"
    assert any("Этап семестра неизвестен" in i for i in unknown_stage.data_issues)
    assert "ориентировочно" not in " ".join(unknown_stage.risk.reasons)


# 10. Одна критическая дисциплина не теряется в хорошем сводном индексе.
def test_tz18_10_one_critical_not_hidden_by_good_index():
    good = [
        analyze_discipline(simple("credit", current=70, graded_max=80, remaining=20, title=f"Хорошая {i}"))
        for i in range(6)
    ]
    critical = analyze_discipline(
        simple("distributed_exam", current=30, graded_max=80, remaining=20, title="Проблемная")
    )
    assert critical.risk.level == "critical"

    s = summarize(good + [critical], TODAY)
    assert s.zone_counts["critical"] == 1
    assert s.zone_counts["stable"] == 6
    assert s.index.uncapped_value == pytest.approx((6 * 100 + 10) / 7)
    assert s.index.value <= 59
    assert s.index.zone != "stable"
    assert "critical" in s.index.caps_applied
    assert s.disciplines[0].title == "Проблемная"
    assert s.priorities[0].title == "Проблемная"
    assert "Проблемная" in s.explanation


TOPIC_SERIES, TOPIC_INTEGRALS, TOPIC_OTHER = 101, 102, 999


def _weak_series_discipline():
    return analyze_discipline(
        discipline(
            "exam",
            [
                module("completed", item(35, 30, due=-30), title="Интегралы", topic_ids=[TOPIC_INTEGRALS]),
                module("completed", item(15, 5, due=-5), title="Ряды", topic_ids=[TOPIC_SERIES]),
                module("in_progress", item(20, None, due=10), topic_ids=[TOPIC_OTHER]),
            ],
            title="Математический анализ",
        )
    )


# 11. Материалы соответствуют выбранной теме.
def test_tz18_11_materials_match_selected_topic():
    a = _weak_series_discipline()
    assert a.weak_topic_ids == (TOPIC_SERIES,)  # «Ряды» — 33 %, «Интегралы» — 86 %

    catalog = [
        MaterialRef(1, "Признаки сходимости рядов", "lecture", "https://example.org/1", (TOPIC_SERIES,),
                    link_status="verified"),
        MaterialRef(2, "Степенные ряды: конспект", "notes", "https://example.org/2", (TOPIC_SERIES,)),
        MaterialRef(3, "Кратные интегралы", "video", "https://example.org/3", (TOPIC_INTEGRALS,),
                    link_status="verified"),
        MaterialRef(4, "Ряды (битая ссылка)", "article", "https://example.org/4", (TOPIC_SERIES,),
                    link_status="broken"),
        MaterialRef(5, "Математический анализ: всё подряд", "textbook", "https://example.org/5", (TOPIC_OTHER,)),
    ]
    selections = materials_for_weak_topics(a, catalog, {TOPIC_SERIES: "Числовые ряды"})
    assert len(selections) == 1
    sel = selections[0]
    assert sel.topic_id == TOPIC_SERIES
    assert [m.id for m in sel.materials] == [1, 2]  # проверенные первыми; битая ссылка скрыта
    assert all(TOPIC_SERIES in m.topic_ids for m in sel.materials)
    assert not sel.is_empty
    assert "не проверены: 1" in sel.message


# 12. Пустая подборка материалов корректно обрабатывается.
def test_tz18_12_empty_materials_selection_is_handled():
    a = _weak_series_discipline()
    only_other = [MaterialRef(3, "Кратные интегралы", "video", "https://example.org/3", (TOPIC_INTEGRALS,))]
    for catalog in ([], only_other):
        sel = materials_for_weak_topics(a, catalog, {TOPIC_SERIES: "Числовые ряды"})[0]
        assert sel.is_empty is True
        assert sel.materials == ()
        assert "пока нет подходящих материалов" in sel.message
        assert sel.to_dict()["materials"] == []

    direct = select_materials_for_topic(TOPIC_SERIES, [])
    assert direct.is_empty and direct.topic_title is None

    # Слабых тем нет — подборок нет, без ошибок.
    strong = analyze_discipline(simple("credit", current=45, graded_max=50, remaining=50))
    assert materials_for_weak_topics(strong, []) == ()


def test_tz18_cases_do_not_read_system_date():
    """Результат зависит только от today во входе (дата не читается внутри модуля)."""
    a = analyze_discipline(simple("credit", current=45, graded_max=50, remaining=50, remaining_due=10))
    b = analyze_discipline(
        discipline(
            "credit",
            [module("completed", item(50, 45)), module("in_progress", item(50, None, due=date(2030, 1, 11)))],
            today=date(2030, 1, 1),
        )
    )
    assert a.as_of == TODAY and a.next_actions[0].days_left == 10
    assert b.as_of == date(2030, 1, 1) and b.next_actions[0].days_left == 10
