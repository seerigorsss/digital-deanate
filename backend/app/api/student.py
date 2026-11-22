"""Студенческие ресурсы. Ни один эндпоинт не принимает ID пользователя: данные берутся по сессии,
а ID дисциплин/тем/заявок проверяются на принадлежность текущему студенту на сервере."""
from __future__ import annotations

from datetime import date, datetime, timedelta

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings, now_local, today_local
from ..db import get_db
from ..errors import bad_request, not_found
from ..models import (
    Application,
    AssessmentItem,
    Enrollment,
    ItemResult,
    LessonTemplate,
    Module,
    Notification,
    RecordBookEntry,
    StudentProfile,
    TopicResource,
)
from ..security.deps import Principal, require_student
from ..services import academics as acad
from ..services.application_types import ACTIVE_STATUSES, STATUS_LABELS, TYPES_BY_KEY
from ..services.notifications import ensure_dynamic_notifications
from ..services.schedule import build_schedule, parity_label, week_info

router = APIRouter(prefix="/api", tags=["student"])


def _profile(db: Session, user_id: int) -> StudentProfile:
    p = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user_id))
    if p is None:
        raise not_found("Профиль не найден")
    return p


@router.get("/profile")
def profile(p: Principal = Depends(require_student), db: Session = Depends(get_db)):
    sp = _profile(db, p.id)
    return {
        "full_name": sp.full_name,
        "last_name": sp.last_name,
        "first_name": sp.first_name,
        "middle_name": sp.middle_name,
        "university": get_settings().university_name,
        "faculty": {"code": sp.faculty_code, "name": sp.faculty_name},
        "program": {"code": sp.program_code, "name": sp.program_name, "profile": sp.profile_name},
        "education_level": sp.education_level,
        "study_form": sp.study_form,
        "funding": sp.funding,
        "course": sp.course,
        "group": sp.group_name,
        "record_book_number": sp.record_book_number,
        "email": sp.email,
        "enrollment_year": sp.enrollment_year,
        "curator": sp.curator,
        "login": p.user.login,
    }


def _upcoming_deadlines(db: Session, user_id: int, today: date, days: int = 21, limit: int = 6) -> list[dict]:
    rows = db.execute(
        select(AssessmentItem, Module, Enrollment)
        .join(Module, AssessmentItem.module_id == Module.id)
        .join(Enrollment, Enrollment.discipline_id == Module.discipline_id)
        .where(Enrollment.student_id == user_id, Module.status != "completed")
        .where(AssessmentItem.due_date >= today, AssessmentItem.due_date <= today + timedelta(days=days))
        .order_by(AssessmentItem.due_date, AssessmentItem.id)
    ).all()
    graded = set(db.scalars(select(ItemResult.item_id).join(Enrollment).where(Enrollment.student_id == user_id)).all())
    out = []
    for item, module, enr in rows:
        if item.id in graded:
            continue
        out.append({
            "item_id": item.id, "title": item.title, "kind": item.kind, "max_points": item.max_points,
            "due_date": item.due_date.isoformat(), "days_left": (item.due_date - today).days,
            "discipline_id": enr.discipline_id, "discipline_title": enr.discipline.title,
            "discipline_short": enr.discipline.short_title, "module_title": module.title,
        })
        if len(out) >= limit:
            break
    return out


@router.get("/dashboard")
def dashboard(p: Principal = Depends(require_student), db: Session = Depends(get_db)):
    today = today_local()
    sp = _profile(db, p.id)
    period = acad.current_period(db)
    ensure_dynamic_notifications(db, p.id, today)

    week_no, parity = week_info(period, today)
    days = build_schedule(db, period, sp.group_name, today, today + timedelta(days=14))
    today_lessons = days[0]["lessons"] if days else []
    now_hm = now_local().strftime("%H:%M") if not get_settings().demo_today else "00:00"
    next_lesson = None
    for day in days:
        for les in day["lessons"]:
            if les["status"] in ("cancelled", "moved_out"):
                continue
            if day["date"] == today.isoformat() and (les["end_time"] or "") <= now_hm:
                continue
            next_lesson = {"date": day["date"], "weekday_label": day["weekday_label"], "lesson": les}
            break
        if next_lesson:
            break

    summary = acad.student_summary(db, p.id, today)
    apps = db.scalars(
        select(Application).where(Application.user_id == p.id, Application.status.in_(ACTIVE_STATUSES))
        .order_by(Application.updated_at.desc()).limit(3)
    ).all()
    unread = db.scalar(select(func.count(Notification.id)).where(Notification.user_id == p.id, Notification.read_at.is_(None)))
    latest = db.scalars(
        select(Notification).where(Notification.user_id == p.id).order_by(Notification.created_at.desc()).limit(3)
    ).all()
    return {
        "today": today.isoformat(),
        "first_name": sp.first_name,
        "period": {
            "title": period.title,
            "week_number": week_no,
            "week_parity": parity,
            "week_parity_label": parity_label(parity),
            "semester_progress": round(acad.semester_progress(period, today), 3),
            "ends_on": period.ends_on.isoformat(),
            "session_starts_on": period.session_starts_on.isoformat(),
            "is_study_day": days[0]["is_study_day"] if days else False,
        },
        "today_lessons": today_lessons,
        "next_lesson": next_lesson,
        "analytics": {
            "index": summary["index"],
            "zone_counts": summary["zone_counts"],
            "explanation": summary["explanation"],
            "top_priority": (summary["priorities"] or [None])[0],
            "priorities": _priority_rows(summary),
        },
        "deadlines": _upcoming_deadlines(db, p.id, today),
        "applications": [_app_brief(a) for a in apps],
        "notifications": {"unread_count": unread or 0, "latest": [notification_out(n) for n in latest]},
    }


def _priority_rows(summary: dict) -> list[dict]:
    """Предметы, которые стоит подтянуть, с данными для шкалы «семестр + экзамен» на главной."""
    by_id = {d["discipline_id"]: d for d in summary["disciplines"]}
    rows = []
    for p in summary["priorities"]:
        d = by_id.get(p["discipline_id"])
        if d is None or p["risk_level"] not in ("critical", "high", "medium"):
            continue
        exam = d.get("exam")
        rows.append({
            "discipline_id": p["discipline_id"], "title": p["title"], "risk_level": p["risk_level"], "risk_label": p.get("risk_label"),
            "assessment_type": d["assessment_type"], "semester_points_max": d["semester_points_max"],
            "current_semester_points": d["current_semester_points"], "remaining_points_max": d["remaining_points_max"],
            "missing_points_max": d["missing_points_max"],
            "exam": {"result": exam["result"], "points_max": exam["points_max"], "points_min": exam["points_min"]} if exam else None,
        })
    return rows[:4]


def _app_brief(a: Application) -> dict:
    t = TYPES_BY_KEY.get(a.type_key, {})
    return {"id": a.id, "number": a.number, "type_key": a.type_key, "title": t.get("title", a.type_key),
            "status": a.status, "status_label": STATUS_LABELS.get(a.status, a.status),
            "updated_at": a.updated_at.isoformat()}


def notification_out(n: Notification) -> dict:
    return {"id": n.id, "category": n.category, "title": n.title, "body": n.body, "link": n.link,
            "importance": n.importance, "created_at": n.created_at.isoformat(),
            "is_read": n.read_at is not None, "read_at": n.read_at.isoformat() if n.read_at else None}


@router.get("/schedule")
def schedule(
    date_from: date | None = Query(default=None, alias="from"),
    date_to: date | None = Query(default=None, alias="to"),
    p: Principal = Depends(require_student),
    db: Session = Depends(get_db),
):
    today = today_local()
    if date_from is None:
        date_from = today - timedelta(days=today.weekday())
    if date_to is None:
        date_to = date_from + timedelta(days=6) if date_from < date(2100, 1, 1) else date_from
    if not (date(2000, 1, 1) <= date_from <= date(2100, 1, 1)) or not (date(2000, 1, 1) <= date_to <= date(2100, 1, 1)):
        raise bad_request("Дата вне допустимого диапазона", "invalid_range")
    if date_to < date_from:
        raise bad_request("Дата окончания раньше даты начала", "invalid_range")
    if (date_to - date_from).days > 41:
        raise bad_request("Можно запросить не более 6 недель расписания", "range_too_large")
    sp = _profile(db, p.id)
    period = acad.current_period(db)
    return {
        "today": today.isoformat(),
        "group": sp.group_name,
        "period": {"title": period.title, "starts_on": period.starts_on.isoformat(), "ends_on": period.ends_on.isoformat()},
        "date_from": date_from.isoformat(),
        "date_to": date_to.isoformat(),
        "days": build_schedule(db, period, sp.group_name, date_from, date_to),
    }


def _discipline_brief(enr: Enrollment) -> dict:
    d = enr.discipline
    a = d.assessment
    return {
        "id": d.id, "title": d.title, "short_title": d.short_title, "department": d.department,
        "description": d.description, "credits": d.credits,
        "assessment_type": a.assessment_type, "assessment_label": acad.ASSESSMENT_LABELS.get(a.assessment_type),
        "exam_date": a.exam_date.isoformat() if a.exam_date else None, "exam_room": a.exam_room,
        "lecturer": {"id": d.lecturer.id, "full_name": d.lecturer.full_name, "position": d.lecturer.position,
                     "department": d.lecturer.department, "email": d.lecturer.email} if d.lecturer else None,
    }


@router.get("/disciplines")
def disciplines(p: Principal = Depends(require_student), db: Session = Depends(get_db)):
    return {"items": [_discipline_brief(e) for e in acad.student_enrollments(db, p.id)]}


@router.get("/disciplines/{discipline_id}")
def discipline_detail(discipline_id: int, p: Principal = Depends(require_student), db: Session = Depends(get_db)):
    enr = acad.get_enrollment(db, p.id, discipline_id)
    period = acad.current_period(db)
    analytics = acad.analyze_enrollment(enr, period, today_local())
    sp = _profile(db, p.id)
    teachers = {}
    for t in db.scalars(select(LessonTemplate).where(LessonTemplate.group_name == sp.group_name,
                                                     LessonTemplate.discipline_id == discipline_id)).all():
        if t.teacher:
            entry = teachers.setdefault(t.teacher.id, {"id": t.teacher.id, "full_name": t.teacher.full_name,
                                                        "position": t.teacher.position, "email": t.teacher.email, "roles": []})
            label = {"lecture": "лекции", "seminar": "семинары", "lab": "лабораторные"}.get(t.lesson_type, "занятия")
            if label not in entry["roles"]:
                entry["roles"].append(label)
    return {
        "discipline": _discipline_brief(enr),
        "teachers": list(teachers.values()),
        "analytics": analytics,
        "topics": acad.topics_with_flags(enr, analytics),
    }


class SimOverride(BaseModel):
    item_id: int
    points: float = Field(ge=0, le=1000, allow_inf_nan=False)


class SimulateIn(BaseModel):
    overrides: list[SimOverride] = Field(default_factory=list, max_length=100)
    exam_points: float | None = Field(default=None, ge=0, le=100, allow_inf_nan=False)


@router.post("/disciplines/{discipline_id}/simulate")
def simulate(discipline_id: int, data: SimulateIn, p: Principal = Depends(require_student), db: Session = Depends(get_db)):
    """«Что если»: пересчёт аналитики с гипотетическими баллами за ещё не оценённые работы. Ничего не сохраняет."""
    enr = acad.get_enrollment(db, p.id, discipline_id)
    graded = {r.item_id for r in enr.results}
    items = {i.id: (i, m) for m in enr.discipline.modules for i in m.items}
    overrides: dict[int, float] = {}
    errors = []
    for o in data.overrides:
        pair = items.get(o.item_id)
        if pair is None:
            errors.append({"field": f"overrides.{o.item_id}", "message": "Работа не относится к дисциплине"})
            continue
        item, module = pair
        if o.item_id in graded or module.status == "completed":
            errors.append({"field": f"overrides.{o.item_id}", "message": "Для этой работы уже есть итоговый результат"})
            continue
        if o.points > item.max_points:
            errors.append({"field": f"overrides.{o.item_id}", "message": f"Максимум — {item.max_points:g} баллов"})
            continue
        overrides[o.item_id] = o.points
    cfg = enr.discipline.assessment
    exam = None
    if data.exam_points is not None:
        if cfg.assessment_type != "exam" or enr.exam_result is not None:
            errors.append({"field": "exam_points", "message": "Для дисциплины нельзя смоделировать экзамен"})
        elif data.exam_points > (cfg.exam_points_max or 0):
            errors.append({"field": "exam_points", "message": f"Максимум за экзамен — {cfg.exam_points_max:g}"})
        else:
            exam = data.exam_points
    if errors:
        raise bad_request("Проверьте значения для моделирования", "validation_error", errors)
    period = acad.current_period(db)
    today = today_local()
    from ..domain import analytics as an

    inp = acad.build_input(enr, today, acad.semester_progress(period, today), overrides)
    if exam is not None:
        from dataclasses import replace

        inp = replace(inp, exam_points=exam)
    return {"simulated": True, "analytics": an.analyze_discipline(inp).to_dict()}


@router.get("/analytics")
def analytics_summary(p: Principal = Depends(require_student), db: Session = Depends(get_db)):
    return acad.student_summary(db, p.id, today_local())


@router.get("/topics/{topic_id}")
def topic_detail(topic_id: int, p: Principal = Depends(require_student), db: Session = Depends(get_db)):
    topic, enr = acad.topic_for_student(db, p.id, topic_id)
    period = acad.current_period(db)
    analytics = acad.analyze_enrollment(enr, period, today_local())
    links = db.scalars(select(TopicResource).where(TopicResource.topic_id == topic.id)).all()
    type_labels = {"article": "Статья", "video": "Видео", "lecture": "Лекция", "textbook": "Учебник", "notes": "Конспект",
                   "course": "Онлайн-курс", "practice": "Тренажёр", "documentation": "Документация"}
    resources = []
    for link in links:
        r = link.resource
        if r.link_status == "broken":
            continue
        resources.append({
            "id": r.id, "title": r.title, "type": r.resource_type, "type_label": type_labels.get(r.resource_type, r.resource_type),
            "source": r.source, "author": r.author, "url": r.url, "language": r.language, "summary": r.summary,
            "relevance": link.relevance, "difficulty": r.difficulty, "duration_minutes": r.duration_minutes,
            "link_status": r.link_status, "checked_on": r.checked_on.isoformat() if r.checked_on else None,
            "access_note": r.access_note,
        })
    order = {"verified": 0, "unverified": 1}
    resources.sort(key=lambda x: (order.get(x["link_status"], 2), x["language"] != "ru"))
    module = topic.module
    return {
        "topic": {"id": topic.id, "title": topic.title, "is_weak": topic.id in set(analytics.get("weak_topic_ids") or [])},
        "discipline": {"id": enr.discipline.id, "title": enr.discipline.title},
        "module": {"id": module.id, "title": module.title, "ordinal": module.ordinal} if module else None,
        "resources": resources,
    }


GRADE_POINTS = {"excellent": 5, "good": 4, "satisfactory": 3}


@router.get("/grades")
def grades(p: Principal = Depends(require_student), db: Session = Depends(get_db)):
    period = acad.current_period(db)
    enrs = acad.student_enrollments(db, p.id)
    entries = db.scalars(select(RecordBookEntry).where(RecordBookEntry.student_id == p.id)
                         .order_by(RecordBookEntry.semester, RecordBookEntry.id)).all()
    semesters: dict[int, list[RecordBookEntry]] = {}
    for e in entries:
        semesters.setdefault(e.semester, []).append(e)

    def avg(es: list[RecordBookEntry]) -> float | None:
        vals = [GRADE_POINTS[e.grade_key] for e in es if e.grade_key in GRADE_POINTS]
        return round(sum(vals) / len(vals), 2) if vals else None

    return {
        "current": {
            "period_title": period.title,
            "session_starts_on": period.session_starts_on.isoformat(),
            "session_ends_on": period.session_ends_on.isoformat(),
            "credits_total": sum(e.discipline.credits for e in enrs),
            "attestations": [
                {"discipline_id": e.discipline.id, "title": e.discipline.title,
                 "assessment_type": e.discipline.assessment.assessment_type,
                 "assessment_label": acad.ASSESSMENT_LABELS.get(e.discipline.assessment.assessment_type),
                 "exam_date": e.discipline.assessment.exam_date.isoformat() if e.discipline.assessment.exam_date else None,
                 "exam_room": e.discipline.assessment.exam_room}
                for e in enrs
            ],
        },
        "record_book": [
            {"semester": sem, "average": avg(es), "entries": [
                {"id": e.id, "discipline_title": e.discipline_title, "assessment_type": e.assessment_type,
                 "assessment_label": acad.ASSESSMENT_LABELS.get(e.assessment_type), "points": e.points,
                 "grade_key": e.grade_key, "grade_label": e.grade_label, "credits": e.credits,
                 "passed_on": e.passed_on.isoformat() if e.passed_on else None} for e in es]}
            for sem, es in sorted(semesters.items(), reverse=True)
        ],
        "overall_average": avg(list(entries)),
    }
