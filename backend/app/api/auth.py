from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Response
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..errors import ApiError
from ..models import User
from ..security.deps import Principal, get_principal
from ..security.passwords import hash_password, needs_rehash, verify_password
from ..security.rate_limit import login_limiter
from ..security.sessions import create_session, destroy_session, get_user_for_session, resolve_session

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginIn(BaseModel):
    login: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


def user_out(user: User) -> dict:
    if user.role == "student" and user.student_profile:
        p = user.student_profile
        name, short = p.full_name, f"{p.first_name} {p.last_name}"
        subtitle = f"{p.group_name} · {p.course} курс"
    elif user.role == "staff" and user.staff_profile:
        p = user.staff_profile
        name, short = p.full_name, f"{p.first_name} {p.last_name}"
        subtitle = p.position
    else:
        name = short = user.login
        subtitle = ""
    initials = "".join(w[0] for w in short.split()[:2]).upper()
    return {"id": user.id, "login": user.login, "role": user.role, "full_name": name, "display_name": short,
            "subtitle": subtitle, "initials": initials}


def client_ip(request: Request) -> str:
    if get_settings().trust_proxy_headers:
        fwd = request.headers.get("x-forwarded-for")
        if fwd:
            # Берём последний адрес: его дописывает доверенный прокси хостинга; первые клиент может подделать.
            return fwd.split(",")[-1].strip()
    return request.client.host if request.client else "unknown"


def _set_cookie(response: Response, token: str) -> None:
    s = get_settings()
    response.set_cookie(
        s.session_cookie_name, token,
        max_age=s.session_ttl_hours * 3600, httponly=True, secure=s.cookie_secure, samesite="lax", path="/",
    )


@router.post("/login")
def login(data: LoginIn, request: Request, response: Response, db: Session = Depends(get_db)):
    s = get_settings()
    login_norm = data.login.strip().lower()
    key = f"{client_ip(request)}|{login_norm}"
    if not login_limiter.hit(key, s.login_rate_limit, s.login_rate_window_seconds):
        raise ApiError(429, "too_many_attempts", "Слишком много попыток входа. Подождите несколько минут и попробуйте снова.")
    user = db.scalar(select(User).where(func.lower(User.login) == login_norm))
    ok = verify_password(user.password_hash if user else None, data.password)
    if not user or not ok or not user.is_active:
        raise ApiError(401, "invalid_credentials", "Неверный логин или пароль")
    login_limiter.reset(key)
    if needs_rehash(user.password_hash):
        user.password_hash = hash_password(data.password)
    user.last_login_at = datetime.now(timezone.utc)
    db.commit()
    # старую сессию из cookie (если была) закрываем — защита от фиксации сессии
    destroy_session(db, request.cookies.get(s.session_cookie_name))
    token, sess = create_session(db, user)
    _set_cookie(response, token)
    return {"user": user_out(user), "csrf_token": sess.csrf_token}


@router.post("/logout", status_code=204)
def logout(request: Request, response: Response, p: Principal = Depends(get_principal), db: Session = Depends(get_db)):
    s = get_settings()
    destroy_session(db, request.cookies.get(s.session_cookie_name))
    response.delete_cookie(s.session_cookie_name, path="/", httponly=True, secure=s.cookie_secure, samesite="lax")
    response.status_code = 204
    return response


@router.get("/me")
def me(request: Request, db: Session = Depends(get_db)):
    """Текущий пользователь. Для гостя — 200 с user=null (а не 401), чтобы старт SPA не засорял консоль ошибками."""
    sess = resolve_session(db, request.cookies.get(get_settings().session_cookie_name))
    user = get_user_for_session(db, sess) if sess else None
    if user is None:
        return {"user": None, "csrf_token": None}
    return {"user": user_out(user), "csrf_token": sess.csrf_token}
