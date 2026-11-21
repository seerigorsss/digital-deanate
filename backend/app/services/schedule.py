"""Построение расписания на произвольный диапазон дат из недельной сетки и изменений."""
from __future__ import annotations

from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..models import AcademicPeriod, LessonTemplate, ScheduleChange, Teacher

LESSON_TYPE_LABELS = {"lecture": "Лекция", "seminar": "Семинар", "lab": "Лабораторная", "consultation": "Консультация"}
WEEKDAY_LABELS = ["Понедельник", "Вторник", "Среда", "Четверг", "Пятница", "Суббота", "Воскресенье"]
MONTHS_GEN = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]
WEEKDAYS_ACC = ["понедельник", "вторник", "среду", "четверг", "пятницу", "субботу", "воскресенье"]


def _hd(d: date) -> str:
    return f"{d.day} {MONTHS_GEN[d.month - 1]}"


def week_info(period: AcademicPeriod, d: date) -> tuple[int, str]:
    n = (d - period.week1_monday).days // 7 + 1
    return n, ("odd" if n % 2 == 1 else "even")


def parity_label(parity: str) -> str:
    return "Числитель" if parity == "odd" else "Знаменатель"


def _teacher(t: Teacher | None) -> dict | None:
    if t is None:
        return None
    return {"id": t.id, "full_name": t.full_name, "position": t.position}


def describe_change(ch: ScheduleChange) -> tuple[str, str]:
    lesson = ch.lesson
    disc = (lesson.discipline.title if lesson else (ch.discipline.title if ch.discipline else "Занятие"))
    ltype = LESSON_TYPE_LABELS.get(lesson.lesson_type if lesson else (ch.lesson_type or ""), "Занятие").lower()
    when = f"{_hd(ch.date)}, {lesson.start_time}" if lesson else _hd(ch.date)
    reason = f" Причина: {ch.reason}." if ch.reason else ""
    if ch.change_type == "cancelled":
        return f"Отмена: {disc}", f"{ltype.capitalize()} {when} не состоится.{reason}"
    if ch.change_type == "moved":
        target = f"{_hd(ch.new_date)} ({WEEKDAYS_ACC[ch.new_date.weekday()]}), {ch.new_start_time}" if ch.new_date else "другое время"
        room = f", ауд. {ch.new_room}" if ch.new_room else ""
        return f"Перенос: {disc}", f"{ltype.capitalize()} {when} перенесена на {target}{room}.{reason}"
    if ch.change_type == "room":
        return f"Новая аудитория: {disc}", f"{ltype.capitalize()} {when} пройдёт в аудитории {ch.new_room}.{reason}"
    if ch.change_type == "teacher":
        name = ch.new_teacher.full_name if ch.new_teacher else "другой преподаватель"
        return f"Замена преподавателя: {disc}", f"{ltype.capitalize()} {when} проведёт {name}.{reason}"
    if ch.change_type == "added":
        return f"Дополнительное занятие: {disc}", f"{ltype.capitalize()} {_hd(ch.date)}, {ch.new_start_time}–{ch.new_end_time}, ауд. {ch.new_room}.{reason}"
    return f"Изменение в расписании: {disc}", f"{when}.{reason}"


def build_schedule(db: Session, period: AcademicPeriod, group_name: str, date_from: date, date_to: date) -> list[dict]:
    templates = db.scalars(
        select(LessonTemplate)
        .options(selectinload(LessonTemplate.discipline), selectinload(LessonTemplate.teacher))
        .where(LessonTemplate.group_name == group_name, LessonTemplate.period_id == period.id)
    ).all()
    # изменения, затрагивающие диапазон: по исходной дате или по новой дате переноса
    changes = db.scalars(
        select(ScheduleChange)
        .options(selectinload(ScheduleChange.lesson), selectinload(ScheduleChange.new_teacher), selectinload(ScheduleChange.discipline))
        .where(ScheduleChange.group_name == group_name)
        .where(
            ((ScheduleChange.date >= date_from) & (ScheduleChange.date <= date_to))
            | ((ScheduleChange.new_date >= date_from) & (ScheduleChange.new_date <= date_to))
        )
    ).all()
    by_lesson_date = {(c.lesson_id, c.date): c for c in changes if c.lesson_id}
    in_period = lambda d: period.starts_on <= d <= period.ends_on  # noqa: E731

    days: list[dict] = []
    d = date_from
    while d <= date_to:
        week_no, parity = week_info(period, d)
        lessons: list[dict] = []
        if in_period(d):
            for t in templates:
                if t.weekday != d.weekday() or (t.week_parity != "all" and t.week_parity != parity):
                    continue
                base = {
                    "key": f"{t.id}:{d.isoformat()}",
                    "lesson_id": t.id,
                    "discipline_id": t.discipline_id,
                    "discipline_title": t.discipline.title,
                    "discipline_short": t.discipline.short_title,
                    "lesson_type": t.lesson_type,
                    "lesson_type_label": LESSON_TYPE_LABELS.get(t.lesson_type, t.lesson_type),
                    "start_time": t.start_time,
                    "end_time": t.end_time,
                    "room": t.room,
                    "teacher": _teacher(t.teacher),
                    "status": "normal",
                    "change": None,
                }
                ch = by_lesson_date.get((t.id, d))
                if ch:
                    title, text = describe_change(ch)
                    change = {"type": ch.change_type, "title": title, "text": text, "reason": ch.reason}
                    if ch.change_type == "cancelled":
                        base.update(status="cancelled", change=change)
                    elif ch.change_type == "moved":
                        change["new_date"] = ch.new_date.isoformat() if ch.new_date else None
                        change["new_start_time"] = ch.new_start_time
                        base.update(status="moved_out", change=change)
                    elif ch.change_type == "room":
                        change["old_room"] = t.room
                        base.update(status="changed", room=ch.new_room, change=change)
                    elif ch.change_type == "teacher":
                        change["old_teacher"] = _teacher(t.teacher)
                        base.update(status="changed", teacher=_teacher(ch.new_teacher), change=change)
                lessons.append(base)
        # занятия, перенесённые НА этот день, и дополнительные
        for ch in changes:
            if ch.change_type == "moved" and ch.new_date == d and ch.lesson:
                t = ch.lesson
                title, text = describe_change(ch)
                lessons.append({
                    "key": f"{t.id}:{d.isoformat()}:moved{ch.id}", "lesson_id": t.id,
                    "discipline_id": t.discipline_id, "discipline_title": t.discipline.title, "discipline_short": t.discipline.short_title,
                    "lesson_type": t.lesson_type, "lesson_type_label": LESSON_TYPE_LABELS.get(t.lesson_type, t.lesson_type),
                    "start_time": ch.new_start_time or t.start_time, "end_time": ch.new_end_time or t.end_time,
                    "room": ch.new_room or t.room, "teacher": _teacher(t.teacher), "status": "moved_in",
                    "change": {"type": "moved", "title": title, "text": text, "reason": ch.reason, "original_date": ch.date.isoformat(),
                               "original_start_time": t.start_time},
                })
            elif ch.change_type == "added" and ch.date == d and ch.discipline:
                title, text = describe_change(ch)
                lessons.append({
                    "key": f"added{ch.id}:{d.isoformat()}", "lesson_id": None,
                    "discipline_id": ch.discipline_id, "discipline_title": ch.discipline.title, "discipline_short": ch.discipline.short_title,
                    "lesson_type": ch.lesson_type or "consultation",
                    "lesson_type_label": LESSON_TYPE_LABELS.get(ch.lesson_type or "consultation", "Занятие"),
                    "start_time": ch.new_start_time, "end_time": ch.new_end_time, "room": ch.new_room,
                    "teacher": _teacher(ch.new_teacher), "status": "added",
                    "change": {"type": "added", "title": title, "text": text, "reason": ch.reason},
                })
        lessons.sort(key=lambda x: (x["start_time"] or "", x["status"] == "cancelled"))
        days.append({
            "date": d.isoformat(),
            "weekday": d.weekday(),
            "weekday_label": WEEKDAY_LABELS[d.weekday()],
            "week_number": week_no,
            "week_parity": parity,
            "week_parity_label": parity_label(parity),
            "is_study_day": in_period(d),
            "lessons": lessons,
            "changes_count": sum(1 for x in lessons if x["status"] != "normal"),
        })
        d += timedelta(days=1)
    return days
