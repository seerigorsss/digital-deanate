"""Индекс учебной устойчивости, зоны, приоритеты и позитивные результаты (контракт §7)."""

from __future__ import annotations

import json
from dataclasses import replace
from datetime import timedelta

import pytest

from app.domain.analytics import DEFAULT_CONFIG, analyze_discipline, compute_index, summarize
from app.domain.analytics.summary import urgency
from tests.domain.factories import TODAY, discipline, item, module, simple


def stable(title="Стабильная"):
    return analyze_discipline(simple("credit", current=70, graded_max=80, remaining=20, title=title))


def high(title="С высоким риском"):
    return analyze_discipline(simple("distributed_exam", current=42, graded_max=80, remaining=20, title=title))


def critical(title="Критическая"):
    return analyze_discipline(simple("distributed_exam", current=30, graded_max=80, remaining=20, title=title))


def insufficient(title="Без данных"):
    return analyze_discipline(
        discipline("credit", [module("in_progress", item(100, None, due=5))], title=title)
    )


def test_index_one_critical_and_six_stable_is_capped_at_59():
    s = summarize([stable(f"С{i}") for i in range(6)] + [critical()], TODAY)
    assert s.index.uncapped_value == pytest.approx(610 / 7)
    assert s.index.value == 59
    assert s.index.zone == "high"
    assert s.index.caps_applied == ("critical",)
    assert s.zone_counts == {
        "critical": 1, "high": 0, "medium": 0, "low": 0, "stable": 6, "insufficient_data": 0
    }
    assert "Индекс ограничен значением 59" in s.explanation


def test_index_one_high_and_six_stable_is_capped_at_74():
    s = summarize([stable(f"С{i}") for i in range(6)] + [high()], TODAY)
    assert s.index.value == 74
    assert s.index.zone == "medium"
    assert s.index.caps_applied == ("high",)


def test_index_cap_not_listed_when_not_binding():
    s = summarize([critical(), high(), high()], TODAY)  # (10 + 35 + 35) / 3 ≈ 26.7
    assert s.index.value == 27
    assert s.index.caps_applied == ()
    assert s.index.zone == "critical"


def test_index_ignores_insufficient_data_and_all_insufficient_gives_none():
    s = summarize([stable(), insufficient()], TODAY)
    assert s.index.value == 100
    assert s.index.disciplines_counted == 1
    assert s.zone_counts["insufficient_data"] == 1
    assert "Без данных" in s.explanation

    empty = summarize([insufficient("А"), insufficient("Б")], TODAY)
    assert empty.index.value is None
    assert empty.index.zone == "insufficient_data"
    assert empty.priorities == ()

    assert compute_index([]).value is None


@pytest.mark.parametrize(
    "value, zone",
    [(80, "stable"), (79, "medium"), (65, "medium"), (64, "high"), (50, "high"), (49, "critical")],
)
def test_index_zone_boundaries(value, zone):
    zones = DEFAULT_CONFIG.index.zones
    chosen = next(z for z in zones if value >= z.min_value)
    assert chosen.key == zone


def test_index_rounds_half_up_and_is_labelled_estimate():
    # (100 + 35) / 2 = 67.5 → 68, кап high 74 не срабатывает
    s = summarize([stable(), high()], TODAY)
    assert s.index.value == 68
    assert s.index.is_estimate is True
    assert "вероятн" not in s.index.formula.lower()
    assert "Ориентировочный индекс" in s.index.formula


def test_disciplines_sorted_by_risk_desc():
    s = summarize([stable(), insufficient(), critical(), high()], TODAY)
    assert [d.risk.level for d in s.disciplines] == ["critical", "high", "insufficient_data", "stable"]


def test_priorities_use_risk_urgency_and_achievability():
    far_medium = analyze_discipline(
        simple("distributed_exam", current=20, graded_max=40, remaining=60, remaining_due=40, title="Далёкая")
    )
    near_medium = analyze_discipline(
        simple("distributed_exam", current=20, graded_max=40, remaining=60, remaining_due=2, title="Срочная")
    )
    crit = critical()
    s = summarize([far_medium, stable(), near_medium, crit], TODAY)

    assert [p.title for p in s.priorities] == ["Критическая", "Срочная", "Далёкая"]
    by_title = {p.title: p for p in s.priorities}
    # medium 400 + срочность 100 + достижимость 50
    assert by_title["Срочная"].score == pytest.approx(550)
    # срок через 40 дней → срочность 0
    assert by_title["Далёкая"].score == pytest.approx(450)
    # critical: 1000 + срочность (срок через 10 дней), без бонуса достижимости
    assert by_title["Критическая"].score == pytest.approx(1000 + 100 * 20 / 27)

    # Сроки — только из next_actions; при недостижимом пороге — к преподавателю, без срока.
    assert by_title["Срочная"].deadline == TODAY + timedelta(days=2)
    assert by_title["Критическая"].deadline is None
    assert "преподавател" in by_title["Критическая"].action
    assert "Стабильная" not in by_title


def test_priority_deadlines_never_invented():
    no_dates = analyze_discipline(
        discipline(
            "distributed_exam",
            [module("completed", item(40, 20)), module("in_progress", item(60, None, due=None))],
            title="Без сроков",
        )
    )
    s = summarize([no_dates], TODAY)
    p = s.priorities[0]
    assert p.deadline is None
    assert urgency(no_dates, TODAY) == 0
    assert "срок не указан" in p.action


@pytest.mark.parametrize(
    "days, expected",
    [(-3, 100), (0, 100), (3, 100), (16, 100 * (30 - 16) / 27), (29, 100 / 27), (30, 0), (45, 0)],
)
def test_urgency_scale(days, expected):
    d = analyze_discipline(
        simple("distributed_exam", current=20, graded_max=40, remaining=60, remaining_due=days)
    )
    assert urgency(d, TODAY) == pytest.approx(expected)


def test_priority_weights_come_from_config():
    cfg = replace(
        DEFAULT_CONFIG,
        priority=replace(DEFAULT_CONFIG.priority, achievability_bonus=0, urgency_max=0),
    )
    s = summarize([high()], TODAY, cfg)
    assert s.priorities[0].score == 700


def test_positives_include_stable_and_low_with_projection_above_target():
    low_good = analyze_discipline(
        simple("distributed_exam", current=39, graded_max=60, remaining=40, title="Низкий риск")
    )
    assert low_good.risk.level == "low" and low_good.projected_semester_points >= 60
    s = summarize([stable("Стабильная"), low_good, high()], TODAY)
    titles = [p.title for p in s.positives]
    assert "Стабильная" in titles and "Низкий риск" in titles
    assert "С высоким риском" not in titles
    assert all(p.message for p in s.positives)


DISCIPLINE_CONTRACT_KEYS = {
    "discipline_id", "title", "assessment_type", "assessment_type_label",
    "current_semester_points", "semester_points_max", "completed_points_max", "graded_points_max",
    "remaining_points_max", "missing_points_max", "max_achievable_semester", "passing_threshold",
    "semester_target", "semester_progress", "data_completeness", "data_issues", "current_pace",
    "pace_is_reliable", "projected_semester_points", "required_share_of_remaining", "pass_status",
    "risk", "current_grade", "exam", "targets", "modules", "next_actions", "weak_topic_ids",
    "explanation", "recommendation",
}


def test_discipline_to_dict_has_contract_keys():
    exam = analyze_discipline(simple("exam", current=42, graded_max=50, remaining=20)).to_dict()
    assert DISCIPLINE_CONTRACT_KEYS <= set(exam)
    assert set(exam["risk"]) >= {"level", "label", "reasons"}
    assert set(exam["exam"]) >= {
        "points_min", "points_max", "result", "passed", "required_for_pass",
        "total_at_exam_min", "total_at_exam_max",
    }
    assert set(exam["targets"][0]) >= {
        "threshold", "grade_key", "label", "status", "points_needed_semester",
        "required_share_of_remaining", "exam_points_needed", "extra_semester_points_needed", "explanation",
    }
    assert set(exam["modules"][0]) >= {
        "id", "ordinal", "title", "status", "ends_on", "points", "max_points", "graded_max",
        "remaining", "missing", "share", "items",
    }
    assert set(exam["modules"][0]["items"][0]) >= {
        "id", "title", "kind", "max_points", "points", "due_date", "state",
    }
    assert set(exam["next_actions"][0]) >= {
        "item_id", "title", "module_title", "max_points", "due_date", "days_left", "overdue",
    }
    credit = analyze_discipline(simple("credit", current=42, graded_max=50, remaining=50)).to_dict()
    assert credit["exam"] is None and credit["current_grade"] is None


def test_summary_to_dict_is_json_serializable_and_has_contract_keys():
    s = summarize([stable(), high(), critical(), insufficient()], TODAY)
    data = s.to_dict()
    json.dumps(data, ensure_ascii=False)
    assert set(data) >= {"index", "zone_counts", "explanation", "priorities", "positives", "disciplines"}
    assert set(data["index"]) >= {"value", "max", "zone", "label", "is_estimate", "formula", "caps_applied"}
    assert set(data["priorities"][0]) >= {
        "discipline_id", "title", "risk_level", "reason", "action", "points_target", "deadline", "score"
    }
    assert data["as_of"] == TODAY.isoformat()
