"""FastAPI-зависимости авторизации. Проверка прав выполняется на сервере для каждого защищённого ресурса."""
from __future__ import annotations

import hmac
from dataclasses import dataclass

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..errors import ApiError, forbidden
from ..models import AuthSession, User
from .sessions import get_user_for_session, resolve_session

SAFE_METHODS = {"GET", "HEAD", "OPTIONS"}


@dataclass
class Principal:
    user: User
    session: AuthSession

    @property
    def id(self) -> int:
        return self.user.id

    @property
    def role(self) -> str:
        return self.user.role


def _unauthorized() -> ApiError:
    return ApiError(401, "unauthorized", "Требуется вход в систему")


def get_principal(request: Request, db: Session = Depends(get_db)) -> Principal:
    token = request.cookies.get(get_settings().session_cookie_name)
    sess = resolve_session(db, token)
    if sess is None:
        raise _unauthorized()
    user = get_user_for_session(db, sess)
    if user is None:
        raise _unauthorized()
    # CSRF: для изменяющих запросов требуется заголовок X-CSRF-Token, совпадающий с токеном сессии,
    # и JSON-тело (cross-site HTML-формы не могут отправить ни то, ни другое).
    if request.method not in SAFE_METHODS:
        header = request.headers.get("x-csrf-token", "")
        if not header or not hmac.compare_digest(header, sess.csrf_token):
            raise ApiError(403, "csrf_failed", "Сессия устарела. Обновите страницу и повторите действие.")
        ctype = request.headers.get("content-type", "")
        if request.headers.get("content-length", "0") not in ("", "0") and not ctype.startswith("application/json"):
            raise ApiError(415, "unsupported_media_type", "Ожидается JSON")
    return Principal(user=user, session=sess)


def require_student(p: Principal = Depends(get_principal)) -> Principal:
    if p.role != "student":
        raise forbidden("Раздел доступен только студентам")
    return p


def require_staff(p: Principal = Depends(get_principal)) -> Principal:
    if p.role != "staff":
        raise forbidden("Раздел доступен только сотрудникам деканата")
    return p
