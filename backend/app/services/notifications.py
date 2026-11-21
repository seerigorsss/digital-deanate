"""Создание уведомлений. Каждое уведомление принадлежит одному пользователю; source_key делает создание идемпотентным."""
from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import (
    AssessmentItem,
    Enrollment,
    ItemResult,
    Module,
    Notification,
    ScheduleChange,
    StudentProfile,
)
from .schedule import describe_change

WEEKDAYS_GEN = ["понедельник", "вторник", "среду", "четверг", "пятницу", "субботу", "воскресенье"]
MONTHS_GEN = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"]


def human_date(d: date) -> str:
    return f"{d.day} {MONTHS_GEN[d.month - 1]}"


def notify(
    db: Session,
    user_id: int,
    category: str,
    title: str,
    body: str,
    *,
    link: str | None = None,
    importance: str = "normal",
    source_key: str | None = None,
    created_at: datetime | None = None,
) -> Notification | None:
    if source_key:
        exists = db.scalar(select(Notification.id).where(Notification.user_id == user_id, Notification.source_key == source_key))
        if exists:
            return None
    n = Notification(
        user_id=user_id,
        category=category,
        title=title[:200],
        body=body,
        link=link,
        importance=importance,
        source_key=source_key,
        created_at=created_at or datetime.now(timezone.utc),
    )
    db.add(n)
    return n


def ensure_dynamic_notifications(db: Session, user_id: int, today: date) -> None:
    """Напоминания о сроках (≤ 3 дня) и изменения расписания (≤ 7 дней) — генерируются из учебных данных, без дублей."""
    profile = db.scalar(select(StudentProfile).where(StudentProfile.user_id == user_id))
    if profile is None:
        return
    # Сроки работ без результата в незавершённых модулях
    rows = db.execute(
        select(AssessmentItem, Module, Enrollment)
        .join(Module, AssessmentItem.module_id == Module.id)
        .join(Enrollment, Enrollment.discipline_id == Module.discipline_id)
        .where(Enrollment.student_id == user_id, Module.status != "completed")
        .where(AssessmentItem.due_date >= today, AssessmentItem.due_date <= today + timedelta(days=3))
    ).all()
    for item, module, enr in rows:
        has_result = db.scalar(select(ItemResult.id).where(ItemResult.enrollment_id == enr.id, ItemResult.item_id == item.id))
        if has_result:
            continue
        days = (item.due_date - today).days
        when = "сегодня" if days == 0 else "завтра" if days == 1 else f"через {days} дня"
        notify(
            db, user_id, "deadline",
            f"Срок {when}: {item.title}",
            f"{enr.discipline.title}, модуль «{module.title}». Срок сдачи — {human_date(item.due_date)}, до {item.max_points:g} баллов.",
            link=f"/study/{enr.discipline_id}", importance="high" if days <= 1 else "normal",
            source_key=f"deadline:{item.id}",
            created_at=datetime.combine(item.due_date - timedelta(days=min(days, 3)), datetime.min.time(), tzinfo=timezone.utc) + timedelta(hours=6),
        )
    # Изменения расписания группы на ближайшую неделю
    changes = db.scalars(
        select(ScheduleChange).where(
            ScheduleChange.group_name == profile.group_name,
            ScheduleChange.date >= today,
            ScheduleChange.date <= today + timedelta(days=7),
        )
    ).all()
    for ch in changes:
        title, body = describe_change(ch)
        notify(
            db, user_id, "schedule", title, body,
            link=f"/schedule?date={ch.date.isoformat()}", importance="high" if ch.change_type in ("cancelled", "moved") else "normal",
            source_key=f"schedule:{ch.id}",
            created_at=ch.created_at,
        )
    db.commit()
