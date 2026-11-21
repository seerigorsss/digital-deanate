from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from ..config import today_local
from ..db import get_db
from ..errors import not_found
from ..models import Notification
from ..security.deps import Principal, get_principal
from ..services.notifications import ensure_dynamic_notifications
from .student import notification_out

router = APIRouter(prefix="/api/notifications", tags=["notifications"])

CATEGORIES = {"announcement": "Объявления", "deadline": "Сроки", "schedule": "Расписание",
              "application": "Заявки", "grade": "Баллы"}
CAT_PATTERN = "^(all|announcement|deadline|schedule|application|grade)$"


@router.get("")
def list_notifications(
    category: str = Query(default="all", pattern=CAT_PATTERN),
    unread: bool = False,
    p: Principal = Depends(get_principal),
    db: Session = Depends(get_db),
):
    if p.role == "student":
        ensure_dynamic_notifications(db, p.id, today_local())
    q = select(Notification).where(Notification.user_id == p.id)
    if category != "all":
        q = q.where(Notification.category == category)
    if unread:
        q = q.where(Notification.read_at.is_(None))
    items = db.scalars(q.order_by(Notification.created_at.desc(), Notification.id.desc()).limit(200)).all()
    unread_rows = db.execute(
        select(Notification.category, func.count(Notification.id))
        .where(Notification.user_id == p.id, Notification.read_at.is_(None))
        .group_by(Notification.category)
    ).all()
    unread_by_cat = {c: n for c, n in unread_rows}
    return {
        "items": [notification_out(n) for n in items],
        "unread_count": sum(unread_by_cat.values()),
        "unread_by_category": unread_by_cat,
        "categories": CATEGORIES,
    }


@router.post("/{notification_id}/read")
def mark_read(notification_id: int, p: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    n = db.scalar(select(Notification).where(Notification.id == notification_id, Notification.user_id == p.id))
    if n is None:
        raise not_found("Уведомление не найдено")
    if n.read_at is None:
        n.read_at = datetime.now(timezone.utc)
        db.commit()
    return notification_out(n)


class ReadAllIn(BaseModel):
    category: str = Field(default="all", pattern=CAT_PATTERN)


@router.post("/read-all")
def mark_all_read(data: ReadAllIn | None = None, p: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    category = data.category if data else "all"
    q = update(Notification).where(Notification.user_id == p.id, Notification.read_at.is_(None))
    if category != "all":
        q = q.where(Notification.category == category)
    res = db.execute(q.values(read_at=datetime.now(timezone.utc)))
    db.commit()
    return {"updated": res.rowcount}
