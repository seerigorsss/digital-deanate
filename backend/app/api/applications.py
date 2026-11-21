from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..db import get_db
from ..errors import ApiError, bad_request, conflict, not_found
from ..models import Application, ApplicationMessage, ApplicationStatusHistory, Enrollment, User
from ..security.deps import Principal, require_student
from ..services import academics as acad
from ..services.application_types import (
    ACTIVE_STATUSES,
    APPLICATION_TYPES,
    FINAL_STATUSES,
    STATUS_LABELS,
    TYPES_BY_KEY,
    clean_text,
    next_step,
    validate_payload,
)

router = APIRouter(prefix="/api", tags=["applications"])


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _discipline_options(db: Session, user_id: int) -> list[dict]:
    return [{"value": e.discipline.id, "label": e.discipline.title} for e in acad.student_enrollments(db, user_id)]


def _allowed_disciplines(db: Session, user_id: int) -> set[int]:
    return set(db.scalars(select(Enrollment.discipline_id).where(Enrollment.student_id == user_id)).all())


def payload_display(db: Session, a: Application) -> list[dict]:
    t = TYPES_BY_KEY.get(a.type_key)
    if not t:
        return []
    out = []
    for f in t["fields"]:
        if f["name"] not in a.payload:
            continue
        v: Any = a.payload[f["name"]]
        if f["type"] == "select":
            v = next((o["label"] for o in f["options"] if o["value"] == v), v)
        elif f["type"] == "discipline":
            from ..models import Discipline

            d = db.get(Discipline, v)
            v = d.title if d else "—"
        elif f["type"] == "date":
            try:
                y, m, dd = str(v).split("-")
                v = f"{dd}.{m}.{y}"
            except ValueError:
                pass
        out.append({"name": f["name"], "label": f["label"], "value": str(v)})
    return out


def app_out(db: Session, a: Application, viewer_role: str = "student", full: bool = True) -> dict:
    t = TYPES_BY_KEY.get(a.type_key, {})
    data = {
        "id": a.id,
        "number": a.number,
        "type_key": a.type_key,
        "title": t.get("title", a.type_key),
        "category": t.get("category"),
        "status": a.status,
        "status_label": STATUS_LABELS.get(a.status, a.status),
        "created_at": a.created_at.isoformat(),
        "updated_at": a.updated_at.isoformat(),
        "submitted_at": a.submitted_at.isoformat() if a.submitted_at else None,
        "summary": _summary_line(a),
        "is_active": a.status in ACTIVE_STATUSES,
        "unread_hint": a.status == "needs_info",
    }
    if not full:
        return data
    data.update({
        "type": {"title": t.get("title"), "description": t.get("description"), "processing_days": t.get("processing_days"),
                 "category": t.get("category")},
        "payload": a.payload,
        "payload_display": payload_display(db, a),
        "next_step": next_step(a.status, a.type_key, a.payload),
        "history": [
            {"id": h.id, "from_status": h.from_status, "to_status": h.to_status,
             "to_label": STATUS_LABELS.get(h.to_status, h.to_status), "comment": h.comment,
             "actor_role": h.actor_role, "created_at": h.created_at.isoformat()}
            for h in a.history
        ],
        "messages": [
            {"id": m.id, "author_role": m.author_role, "author_name": m.author_name, "text": m.text,
             "created_at": m.created_at.isoformat(), "is_mine": m.author_role == viewer_role}
            for m in a.messages
        ],
        "permissions": {
            "can_edit": a.status == "draft",
            "can_submit": a.status == "draft",
            "can_delete": a.status == "draft",
            "can_withdraw": a.status == "submitted",
            "can_reply": a.status not in FINAL_STATUSES and a.status != "draft",
        },
        "document_available": a.status in ("ready", "completed") and a.payload.get("delivery") == "electronic",
    })
    return data


def _summary_line(a: Application) -> str:
    p = a.payload or {}
    for key in ("subject", "destination", "military_office"):
        if p.get(key):
            return str(p[key])[:120]
    if p.get("details"):
        return str(p["details"])[:120]
    return ""


def own_application(db: Session, user_id: int, app_id: int) -> Application:
    """Заявка ищется сразу с фильтром по владельцу: чужая заявка неотличима от несуществующей."""
    a = db.scalar(select(Application).where(Application.id == app_id, Application.user_id == user_id))
    if a is None:
        raise not_found("Заявка не найдена")
    return a


def add_history(db: Session, a: Application, to_status: str, actor: User | None, role: str, comment: str | None = None) -> None:
    a.history.append(ApplicationStatusHistory(from_status=a.status if a.status != to_status else None,
                                              to_status=to_status, comment=comment, actor_user_id=actor.id if actor else None,
                                              actor_role=role, created_at=_now()))
    a.status = to_status
    a.updated_at = _now()
    if to_status in FINAL_STATUSES:
        a.closed_at = _now()


@router.get("/application-types")
def application_types(p: Principal = Depends(require_student), db: Session = Depends(get_db)):
    options = _discipline_options(db, p.id)
    items = []
    for t in APPLICATION_TYPES:
        fields = []
        for f in t["fields"]:
            f2 = dict(f)
            if f["type"] == "discipline":
                f2["options"] = options
            fields.append(f2)
        items.append({**t, "fields": fields})
    return {"items": items, "statuses": STATUS_LABELS}


@router.get("/applications")
def list_applications(
    status: str = Query(default="all", pattern="^(all|active|closed|draft)$"),
    p: Principal = Depends(require_student),
    db: Session = Depends(get_db),
):
    q = select(Application).where(Application.user_id == p.id)
    if status == "active":
        q = q.where(Application.status.in_(ACTIVE_STATUSES))
    elif status == "closed":
        q = q.where(Application.status.in_(FINAL_STATUSES))
    elif status == "draft":
        q = q.where(Application.status == "draft")
    apps = db.scalars(q.order_by(Application.updated_at.desc())).all()
    all_apps = db.scalars(select(Application.status).where(Application.user_id == p.id)).all()
    counts = {"all": len(all_apps), "active": sum(s in ACTIVE_STATUSES for s in all_apps),
              "closed": sum(s in FINAL_STATUSES for s in all_apps), "draft": sum(s == "draft" for s in all_apps)}
    return {"items": [app_out(db, a, full=False) for a in apps], "counts": counts}


class ApplicationIn(BaseModel):
    type_key: str = Field(max_length=64)
    payload: dict[str, Any] = Field(default_factory=dict)
    submit: bool = True


@router.post("/applications", status_code=201)
def create_application(data: ApplicationIn, p: Principal = Depends(require_student), db: Session = Depends(get_db)):
    if data.type_key not in TYPES_BY_KEY:
        raise bad_request("Неизвестный тип заявки", "unknown_type")
    clean, errors = validate_payload(data.type_key, data.payload, _allowed_disciplines(db, p.id), partial=not data.submit)
    if errors:
        raise ApiError(422, "validation_error", "Проверьте заполнение формы", errors)
    open_drafts = db.scalars(select(Application.id).where(Application.user_id == p.id, Application.status == "draft")).all()
    if not data.submit and len(open_drafts) >= 20:
        raise conflict("Слишком много черновиков. Удалите ненужные.", "too_many_drafts")
    now = _now()
    a = Application(user_id=p.id, type_key=data.type_key, status="draft", payload=clean, created_at=now, updated_at=now)
    db.add(a)
    db.flush()
    a.number = f"{now.year % 100:02d}-{a.id:05d}"
    add_history(db, a, "draft", p.user, "student")
    if data.submit:
        add_history(db, a, "submitted", p.user, "student")
        a.submitted_at = now
    db.commit()
    db.refresh(a)
    return app_out(db, a)


@router.get("/applications/{app_id}")
def get_application(app_id: int, p: Principal = Depends(require_student), db: Session = Depends(get_db)):
    return app_out(db, own_application(db, p.id, app_id))


class ApplicationPatch(BaseModel):
    payload: dict[str, Any]


@router.patch("/applications/{app_id}")
def update_draft(app_id: int, data: ApplicationPatch, p: Principal = Depends(require_student), db: Session = Depends(get_db)):
    a = own_application(db, p.id, app_id)
    if a.status != "draft":
        raise conflict("Редактировать можно только черновик", "not_draft")
    clean, errors = validate_payload(a.type_key, data.payload, _allowed_disciplines(db, p.id), partial=True)
    if errors:
        raise ApiError(422, "validation_error", "Проверьте заполнение формы", errors)
    a.payload = clean
    a.updated_at = _now()
    db.commit()
    return app_out(db, a)


@router.post("/applications/{app_id}/submit")
def submit_draft(app_id: int, p: Principal = Depends(require_student), db: Session = Depends(get_db)):
    a = own_application(db, p.id, app_id)
    if a.status != "draft":
        raise conflict("Заявка уже отправлена", "not_draft")
    clean, errors = validate_payload(a.type_key, a.payload, _allowed_disciplines(db, p.id), partial=False)
    if errors:
        raise ApiError(422, "validation_error", "Заполните обязательные поля перед отправкой", errors)
    a.payload = clean
    a.submitted_at = _now()
    add_history(db, a, "submitted", p.user, "student")
    db.commit()
    return app_out(db, a)


@router.post("/applications/{app_id}/withdraw")
def withdraw(app_id: int, p: Principal = Depends(require_student), db: Session = Depends(get_db)):
    a = own_application(db, p.id, app_id)
    if a.status != "submitted":
        raise conflict("Отозвать можно только заявку, которую деканат ещё не взял в работу", "cannot_withdraw")
    add_history(db, a, "withdrawn", p.user, "student", "Отозвана студентом")
    db.commit()
    return app_out(db, a)


@router.delete("/applications/{app_id}", status_code=204)
def delete_draft(app_id: int, p: Principal = Depends(require_student), db: Session = Depends(get_db)):
    a = own_application(db, p.id, app_id)
    if a.status != "draft":
        raise conflict("Удалить можно только черновик", "not_draft")
    db.delete(a)
    db.commit()


class MessageIn(BaseModel):
    text: str = Field(min_length=1, max_length=3000)


@router.post("/applications/{app_id}/messages", status_code=201)
def add_message(app_id: int, data: MessageIn, p: Principal = Depends(require_student), db: Session = Depends(get_db)):
    a = own_application(db, p.id, app_id)
    if a.status in FINAL_STATUSES or a.status == "draft":
        raise conflict("В эту заявку нельзя написать сообщение", "cannot_reply")
    text = clean_text(data.text)
    if not text:
        raise bad_request("Сообщение не может быть пустым", "empty_message")
    a.messages.append(ApplicationMessage(author_user_id=p.id, author_role="student",
                              author_name=p.user.student_profile.full_name if p.user.student_profile else p.user.login,
                              text=text, created_at=_now()))
    if a.status == "needs_info":  # ответ на уточнение возвращает заявку в работу деканата
        add_history(db, a, "submitted", p.user, "student", "Студент ответил на запрос уточнения")
    a.updated_at = _now()
    db.commit()
    return app_out(db, a)
