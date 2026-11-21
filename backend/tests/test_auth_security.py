"""Авторизация, сессии, CSRF, хеширование паролей, заголовки безопасности."""
from sqlalchemy import select

from .conftest import Api


def test_login_profile_logout_and_second_account(app):
    api = Api(app)
    assert api.get("/api/profile").status_code == 401
    r = api.login("student1")
    assert r.status_code == 200 and r.json()["user"]["role"] == "student"
    p1 = api.get("/api/profile").json()
    assert p1["last_name"] == "Воронцова" and p1["group"] == "ИУ5-34Б" and p1["course"] == 2
    assert api.post("/api/auth/logout").status_code == 204
    assert api.get("/api/profile").status_code == 401
    api.login("student2")
    p2 = api.get("/api/profile").json()
    assert p2["last_name"] == "Калинин" and p2["group"] == "РК9-51Б" and p2["faculty"]["code"] == "РК"
    assert p1 != p2


def test_wrong_password_generic_error(app):
    api = Api(app)
    r1 = api.login("student1", "wrong-password")
    r2 = api.login("no-such-user", "wrong-password")
    assert r1.status_code == r2.status_code == 401
    assert r1.json()["detail"] == r2.json()["detail"] == "Неверный логин или пароль"


def test_login_rate_limited(app):
    api = Api(app)
    codes = [api.login("ratelimit-probe", "x").status_code for _ in range(8)]
    assert 429 in codes


def test_session_token_invalid_after_logout(app):
    api = Api(app, "student1")
    token = api.c.cookies.get("dd_session")
    assert token
    api.post("/api/auth/logout")
    other = Api(app)
    other.c.cookies.set("dd_session", token)
    assert other.get("/api/profile").status_code == 401  # украденная/старая cookie не работает


def test_cookie_flags(app):
    api = Api(app)
    r = api.login("student1")
    sc = r.headers["set-cookie"].lower()
    assert "httponly" in sc and "samesite=lax" in sc and "path=/" in sc


def test_csrf_required_for_mutations(s1):
    r = s1.c.post("/api/applications", json={"type_key": "dean_question", "payload": {}, "submit": False})
    assert r.status_code == 403 and r.json()["code"] == "csrf_failed"
    r = s1.c.post("/api/notifications/read-all", headers={"X-CSRF-Token": "forged"})
    assert r.status_code == 403


def test_passwords_hashed_with_argon2(app):
    from app.db import SessionLocal
    from app.models import User

    with SessionLocal() as db:
        for u in db.scalars(select(User)).all():
            assert u.password_hash.startswith("$argon2id$")
            assert "demo" not in u.password_hash


def test_role_separation(s1, staff):
    assert s1.get("/api/staff/applications").status_code == 403
    assert s1.get("/api/staff/students").status_code == 403
    assert staff.get("/api/profile").status_code == 403
    assert staff.get("/api/analytics").status_code == 403


def test_security_headers_and_no_secrets(app):
    api = Api(app)
    r = api.get("/api/health")
    assert r.headers["x-content-type-options"] == "nosniff"
    assert "frame-ancestors 'none'" in r.headers["content-security-policy"]
    meta = api.get("/api/meta").json()
    assert "Концепт" in meta["disclaimer"]


def test_unknown_api_route_is_json_404(app):
    r = Api(app).get("/api/does-not-exist")
    assert r.status_code == 404 and r.json()["code"] == "not_found"
