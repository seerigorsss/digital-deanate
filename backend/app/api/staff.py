"""Кабинет сотрудника деканата: обработка заявок, ответы на обращения, выставление баллов, объявления."""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..config import today_local
from ..db import get_db
from ..errors import ApiError, bad_request, conflict, not_found
from ..models import (
    Announcement,
    Application,
    ApplicationMessage,
    AssessmentItem,
    Enrollment,
    ItemResult,
    Module,
    StudentProfile,
    User,
)
from ..security.deps import Principal, require_staff
from ..services import academics as acad
from ..services.application_types import (
    ACTIVE_STATUSES,
    COMMENT_REQUIRED,
    FINAL_STATUSES,
    STAFF_TRANSITIONS,
    STATUS_LABELS,
    TYPES_BY_KEY,
    clean_text,
)
from ..services.notifications import notify
from .applications import add_history, app_out

router = APIRouter(prefix="/api/staff", tags=["staff"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _student_brief(db: Session, user_id: int) -> dict | None:
    sp = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user_id))
    if not sp:
        return None
    return {"user_id": user_id, "full_name": sp.full_name, "group": sp.group_name, "course": sp.course,
            "faculty": sp.faculty_code, "email": sp.email}


def _staff_name(p: Principal) -> str:
    sp = p.user.staff_profile
    return f"{sp.full_name} (деканат)" if sp else "Деканат"


@router.get("/applications")
def staff_applications(
    status: str = Query(default="active", pattern="^(all|active|closed|submitted|in_progress|needs_info|approved|ready)$"),
    p: Principal = Depends(require_staff),
    db: Session = Depends(get_db),
):
    q = select(Application).where(Application.status != "draft")  # черновики видит только автор
    if status == "active":
        q = q.where(Application.status.in_(ACTIVE_STATUSES))
    elif status == "closed":
        q = q.where(Application.status.in_(FINAL_STATUSES))
    elif status != "all":
        q = q.where(Application.status == status)
    apps = db.scalars(q.order_by(Application.updated_at.desc()).limit(300)).all()
    all_statuses = db.scalars(select(Application.status).where(Application.status != "draft")).all()
    counts = {s: sum(x == s for x in all_statuses) for s in STATUS_LABELS if s != "draft"}
    items = []
    for a in apps:
        d = app_out(db, a, viewer_role="staff", full=False)
        d["student"] = _student_brief(db, a.user_id)
        items.append(d)
    return {"items": items, "counts": counts}


def _staff_app(db: Session, app_id: int) -> Application:
    a = db.scalar(select(Application).where(Application.id == app_id, Application.status != "draft"))
    if a is None:
        raise not_found("Заявка не найдена")
    return a


def _staff_app_out(db: Session, a: Application) -> dict:
    d = app_out(db, a, viewer_role="staff")
    d["student"] = _student_brief(db, a.user_id)
    d["allowed_transitions"] = [{"status": s, "label": STATUS_LABELS[s], "comment_required": s in COMMENT_REQUIRED}
                                for s in sorted(STAFF_TRANSITIONS.get(a.status, set()))]
    d["permissions"] = {"can_reply": a.status not in FINAL_STATUSES}
    return d


@router.get("/applications/{app_id}")
def staff_application(app_id: int, p: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    return _staff_app_out(db, _staff_app(db, app_id))


class StatusIn(BaseModel):
    to_status: str = Field(max_length=32)
    comment: str | None = Field(default=None, max_length=2000)


@router.post("/applications/{app_id}/status")
def change_status(app_id: int, data: StatusIn, p: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    a = _staff_app(db, app_id)
    allowed = STAFF_TRANSITIONS.get(a.status, set())
    if data.to_status not in allowed:
        raise conflict(f"Переход «{STATUS_LABELS.get(a.status)}» → «{STATUS_LABELS.get(data.to_status, data.to_status)}» недоступен",
                       "invalid_transition")
    comment = clean_text(data.comment or "") or None
    if data.to_status in COMMENT_REQUIRED and not comment:
        raise ApiError(422, "validation_error", "Укажите комментарий для студента",
                       [{"field": "comment", "message": "Комментарий обязателен для этого статуса"}])
    add_history(db, a, data.to_status, p.user, "staff", comment)
    if comment:
        a.messages.append(ApplicationMessage(author_user_id=p.id, author_role="staff",
                                             author_name=_staff_name(p), text=comment, created_at=_now()))
    title = TYPES_BY_KEY.get(a.type_key, {}).get("title", "Заявка")
    label = STATUS_LABELS[data.to_status]
    notify(db, a.user_id, "application", f"Заявка № {a.number}: {label.lower()}",
           f"«{title}» — новый статус: {label}." + (f" Комментарий деканата: {comment}" if comment else ""),
           link=f"/applications/{a.id}", importance="high" if data.to_status in ("needs_info", "ready", "rejected") else "normal",
           source_key=f"app:{a.id}:{data.to_status}:{_now().timestamp():.3f}")
    db.commit()
    return _staff_app_out(db, a)


class StaffMessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=3000)


@router.post("/applications/{app_id}/messages", status_code=201)
def staff_message(app_id: int, data: StaffMessageIn, p: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    a = _staff_app(db, app_id)
    if a.status in FINAL_STATUSES:
        raise conflict("Заявка закрыта", "closed")
    text = clean_text(data.text)
    if not text:
        raise bad_request("Сообщение не может быть пустым", "empty_message")
    a.messages.append(ApplicationMessage(author_user_id=p.id, author_role="staff",
                                         author_name=_staff_name(p), text=text, created_at=_now()))
    a.updated_at = _now()
    notify(db, a.user_id, "application", f"Ответ деканата по заявке № {a.number}", text[:300],
           link=f"/applications/{a.id}", importance="normal", source_key=f"appmsg:{a.id}:{_now().timestamp():.3f}")
    db.commit()
    return _staff_app_out(db, a)


@router.get("/students")
def students(p: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    sps = db.scalars(select(StudentProfile).order_by(StudentProfile.group_name, StudentProfile.last_name)).all()
    return {"items": [_student_brief(db, sp.user_id) for sp in sps]}


@router.get("/students/{user_id}/grades")
def student_grades(user_id: int, p: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    brief = _student_brief(db, user_id)
    if brief is None:
        raise not_found("Студент не найден")
    period = acad.current_period(db)
    today = today_local()
    out = []
    for enr in acad.student_enrollments(db, user_id):
        res = {r.item_id: r.points for r in enr.results}
        an = acad.analyze_enrollment(enr, period, today)
        out.append({
            "discipline_id": enr.discipline.id, "title": enr.discipline.title,
            "assessment_label": acad.ASSESSMENT_LABELS.get(enr.discipline.assessment.assessment_type),
            "current_points": an["current_semester_points"], "semester_points_max": an["semester_points_max"],
            "risk": an["risk"],
            "modules": [{"id": m.id, "ordinal": m.ordinal, "title": m.title, "status": m.status, "items": [
                {"id": i.id, "title": i.title, "max_points": i.max_points,
                 "due_date": i.due_date.isoformat() if i.due_date else None, "points": res.get(i.id)} for i in m.items]}
                for m in enr.discipline.modules],
        })
    return {"student": brief, "disciplines": out}


class ResultIn(BaseModel):
    student_id: int
    item_id: int
    points: float | None = Field(default=None, ge=0, le=1000, allow_inf_nan=False)


@router.put("/results")
def set_result(data: ResultIn, p: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    item = db.get(AssessmentItem, data.item_id)
    if item is None:
        raise not_found("Работа не найдена")
    module = db.get(Module, item.module_id)
    enr = db.scalar(select(Enrollment).where(Enrollment.student_id == data.student_id,
                                             Enrollment.discipline_id == module.discipline_id))
    if enr is None:
        raise not_found("Студент не записан на дисциплину")
    if data.points is not None and data.points > item.max_points:
        raise ApiError(422, "validation_error", f"Максимум за работу — {item.max_points:g} баллов",
                       [{"field": "points", "message": f"Не больше {item.max_points:g}"}])
    res = db.scalar(select(ItemResult).where(ItemResult.enrollment_id == enr.id, ItemResult.item_id == item.id))
    if data.points is None:
        if res:
            db.delete(res)
    else:
        if res is None:
            res = ItemResult(enrollment_id=enr.id, item_id=item.id, points=data.points)
            db.add(res)
        res.points = data.points
        res.graded_at = _now()
        res.graded_by_user_id = p.id
        db.flush()
        notify(db, data.student_id, "grade", f"Новые баллы: {enr.discipline.short_title}",
               f"{item.title} («{module.title}»): {data.points:g} из {item.max_points:g}. Аналитика успеваемости пересчитана.",
               link=f"/study/{enr.discipline_id}", source_key=f"grade:{res.id}:{res.graded_at.timestamp():.0f}")
    db.commit()
    return student_grades(data.student_id, p, db)


class AnnouncementIn(BaseModel):
    title: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=3, max_length=4000)
    audience: str = Field(default="all", pattern=r"^(all|group:[\w\-А-Яа-яЁё]{1,32}|faculty:[\wА-Яа-яЁё]{1,16})$")
    importance: str = Field(default="normal", pattern="^(normal|high)$")


@router.post("/announcements", status_code=201)
def publish_announcement(data: AnnouncementIn, p: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    q = select(StudentProfile)
    if data.audience.startswith("group:"):
        q = q.where(StudentProfile.group_name == data.audience.split(":", 1)[1])
    elif data.audience.startswith("faculty:"):
        q = q.where(StudentProfile.faculty_code == data.audience.split(":", 1)[1])
    recipients = db.scalars(q).all()
    if not recipients:
        raise bad_request("Нет студентов для выбранной аудитории", "empty_audience")
    ann = Announcement(title=clean_text(data.title), body=clean_text(data.body), audience=data.audience,
                       author_user_id=p.id, published_at=_now())
    db.add(ann)
    db.flush()
    for sp in recipients:
        notify(db, sp.user_id, "announcement", ann.title, ann.body, importance=data.importance,
               source_key=f"ann:{ann.id}", link="/notifications")
    db.commit()
    return {"id": ann.id, "recipients": len(recipients)}


@router.get("/announcements")
def list_announcements(p: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    anns = db.scalars(select(Announcement).order_by(Announcement.published_at.desc()).limit(50)).all()
    return {"items": [{"id": a.id, "title": a.title, "body": a.body, "audience": a.audience,
                       "published_at": a.published_at.isoformat()} for a in anns]}


@router.get("/groups")
def groups(p: Principal = Depends(require_staff), db: Session = Depends(get_db)):
    rows = db.execute(select(StudentProfile.group_name, StudentProfile.faculty_code, StudentProfile.faculty_name).distinct()).all()
    return {"groups": sorted({r[0] for r in rows}), "faculties": sorted({(r[1], r[2]) for r in rows})}


__all__ = ["router", "User"]
