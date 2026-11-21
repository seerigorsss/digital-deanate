"""Тексты (тон, отсутствие «вероятности»), детерминированность и пересчёт после изменения баллов."""

from __future__ import annotations

import json
from dataclasses import replace

import pytest

from app.domain.analytics import analyze_discipline, summarize
from app.domain.analytics.texts import fmt_num, fmt_pct, pts, pts_gen
from tests.domain.factories import TODAY, discipline, item, module, simple

FORBIDDEN = ("вероятн", "шанс", "отчисл", "провал", "катастроф", "безнадёж")

VARIETY = [
    simple("credit", current=59, graded_max=100, remaining=0),
    simple("credit", current=70, graded_max=80, remaining=20),
    simple("distributed_exam", current=20, graded_max=40, remaining=60),
    simple("distributed_exam", current=42, graded_max=80, remaining=20),
    simple("distributed_exam", current=44, graded_max=80, remaining=20),
    simple("distributed_exam", current=12, graded_max=20, remaining=80, semester_progress=0.15),
    simple("distributed_exam", current=45, graded_max=50, remaining=50, semester_progress=None),
    simple("exam", current=42, graded_max=60, remaining=10),
    simple("exam", current=20, graded_max=60, remaining=10),
    simple("exam", current=19, graded_max=60, remaining=10),
    simple("exam", current=70, graded_max=70, remaining=0, exam_points=17),
    simple("exam", current=41, graded_max=70, remaining=0, exam_points=18),
    simple("exam", current=60, graded_max=70, remaining=0, exam_points=25),
    discipline("credit", [module("completed", item(50, None)), module("in_progress", item(50, None, due=3))]),
    discipline("credit", []),
]


def _all_texts(a):
    yield a.explanation
    yield a.recommendation
    yield from a.risk.reasons
    yield from a.data_issues
    for t in a.targets:
        yield t.explanation


@pytest.mark.parametrize("inp", VARIETY)
def test_texts_are_supportive_and_never_call_risk_a_probability(inp):
    a = analyze_discipline(inp)
    texts = list(_all_texts(a))
    assert a.explanation and a.recommendation
    assert 1 <= len(a.risk.reasons) <= 3
    for text in texts:
        lowered = text.lower()
        for word in FORBIDDEN:
            assert word not in lowered, (word, text)
        assert "None" not in text and "nan" not in lowered


def test_summary_texts_never_call_index_a_probability():
    items = [analyze_discipline(i) for i in VARIETY]
    s = summarize(items, TODAY)
    texts = [s.explanation, s.index.formula, s.index.label]
    texts += [p.reason + p.action + p.points_target for p in s.priorities]
    texts += [p.message for p in s.positives]
    for text in texts:
        for word in FORBIDDEN:
            assert word not in text.lower(), (word, text)


def test_recommendation_mentions_only_items_from_plan():
    inp = discipline(
        "distributed_exam",
        [
            module("completed", item(40, 20, title="РК-1"), title="Графы"),
            module("in_progress", item(30, None, due=4, title="ДЗ «Деревья»"), title="Деревья"),
            module("upcoming", item(30, None, due=25, title="РК-2"), title="Булевы функции"),
        ],
    )
    a = analyze_discipline(inp)
    assert "ДЗ «Деревья»" in a.recommendation
    assert "Деревья" in a.recommendation
    assert [x.title for x in a.next_actions] == ["ДЗ «Деревья»", "РК-2"]


def test_number_formatting_and_russian_plurals():
    assert fmt_num(42.0) == "42" and fmt_num(42.5) == "42,5" and fmt_num(41.999999) == "42"
    assert fmt_pct(0.665) == "67%" and fmt_pct(0.5) == "50%"
    assert [pts(n) for n in (1, 2, 5, 11, 21, 22, 2.5)] == [
        "1 балл", "2 балла", "5 баллов", "11 баллов", "21 балл", "22 балла", "2,5 балла"
    ]
    assert [pts_gen(n) for n in (1, 18, 21, 30)] == ["1 балла", "18 баллов", "21 балла", "30 баллов"]


def test_deterministic_and_json_serializable():
    for inp in VARIETY:
        first = analyze_discipline(inp).to_dict()
        second = analyze_discipline(inp).to_dict()
        assert first == second
        json.dumps(first, ensure_ascii=False)
    assert first["as_of"] == TODAY.isoformat()


def test_recalculation_after_points_change_updates_level_and_recommendation():
    m1 = module("completed", item(20, 8, title="РК-1"), item(20, 8, title="ДЗ-1"))
    pending = item(20, None, due=3, title="ДЗ-2")
    m2 = module("in_progress", pending, item(40, None, due=20, title="РК-2"))
    before_inp = discipline("distributed_exam", [m1, m2])
    before = analyze_discipline(before_inp)

    # Преподаватель выставил баллы за ДЗ-2 — пересчёт без каких-либо заготовленных текстов.
    graded = replace(pending, points=19)
    m2_after = replace(m2, items=(graded, m2.items[1]))
    after_inp = replace(before_inp, modules=(m1, m2_after))
    after = analyze_discipline(after_inp)

    assert before.current_semester_points == 16 and after.current_semester_points == 35
    assert before.remaining_points_max == 60 and after.remaining_points_max == 40
    # До: r = 44/60 ≈ 0.73 при темпе 0.40 (оценено 40 из 100 — темп надёжен) → разрыв 0.33 → high.
    # После: r = 25/40 = 0.625 при темпе 35/60 ≈ 0.58 → разрыв < 0.1, ориентир 58 < 70 → low.
    assert (before.risk.level, before.risk.rule) == ("high", "pace_gap_high")
    assert (after.risk.level, after.risk.rule) == ("low", "realistic")
    assert before.recommendation != after.recommendation
    assert "ДЗ-2" in before.recommendation and "ДЗ-2" not in after.recommendation
    assert "РК-2" in after.recommendation

    s_before = summarize([before], TODAY)
    s_after = summarize([after], TODAY)
    assert s_after.index.value > s_before.index.value


def test_recalculation_exam_result_changes_status():
    base = simple("exam", current=45, graded_max=70, remaining=0)
    a_none = analyze_discipline(base)
    a_17 = analyze_discipline(replace(base, exam_points=17))
    a_20 = analyze_discipline(replace(base, exam_points=20))
    assert (a_none.pass_status, a_17.pass_status, a_20.pass_status) == ("secured", "failed", "passed")
    assert (a_none.risk.level, a_17.risk.level, a_20.risk.level) == ("stable", "critical", "stable")
    assert a_20.current_grade.key == "satisfactory"  # 65
