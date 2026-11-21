"""Серверные сессии: случайный токен в HttpOnly-cookie, в БД — только его SHA-256."""
from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..models import AuthSession, User


def _hash_token(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def _aware(dt: datetime) -> datetime:
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def create_session(db: Session, user: User) -> tuple[str, AuthSession]:
    s = get_settings()
    token = secrets.token_urlsafe(32)
    now = datetime.now(timezone.utc)
    sess = AuthSession(
        id=_hash_token(token),
        user_id=user.id,
        csrf_token=secrets.token_urlsafe(32),
        created_at=now,
        last_seen_at=now,
        expires_at=now + timedelta(hours=s.session_ttl_hours),
    )
    db.add(sess)
    # Подчищаем истёкшие сессии пользователя
    db.execute(delete(AuthSession).where(AuthSession.user_id == user.id, AuthSession.expires_at < now))
    db.commit()
    return token, sess


def resolve_session(db: Session, token: str | None) -> AuthSession | None:
    if not token or len(token) > 200:
        return None
    sess = db.get(AuthSession, _hash_token(token))
    if sess is None:
        return None
    s = get_settings()
    now = datetime.now(timezone.utc)
    if _aware(sess.expires_at) < now or _aware(sess.last_seen_at) + timedelta(minutes=s.session_idle_minutes) < now:
        db.delete(sess)
        db.commit()
        return None
    if now - _aware(sess.last_seen_at) > timedelta(minutes=1):
        sess.last_seen_at = now
        db.commit()
    return sess


def destroy_session(db: Session, token: str | None) -> None:
    if not token:
        return
    db.execute(delete(AuthSession).where(AuthSession.id == _hash_token(token)))
    db.commit()


def destroy_all_sessions(db: Session, user_id: int) -> None:
    db.execute(delete(AuthSession).where(AuthSession.user_id == user_id))
    db.commit()


def get_user_for_session(db: Session, sess: AuthSession) -> User | None:
    return db.scalar(select(User).where(User.id == sess.user_id, User.is_active.is_(True)))
