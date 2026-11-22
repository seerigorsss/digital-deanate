"""Независимая QA-проверка (агент 06): безопасность, валидация, изоляция данных, аналитика через API.

Тесты, помеченные в docstring «ДЕФЕКТ QA-xx», сейчас падают намеренно — они фиксируют найденные дефекты
(см. docs/test-report.md) и должны пройти после исправления. Остальные — регрессионные проверки заявленных мер.
Запуск: cd backend && .venv/bin/python -m pytest tests/test_qa_security.py -q
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from .conftest import PASSWORDS, Api

ROOT = Path(__file__).resolve().parents[2]
JSON = {"Content-Type": "application/json"}


def raw_post(api: Api, url: str, body: str, method: str = "POST"):
    """Сырой JSON (например, с Infinity/NaN, которые json.loads на сервере принимает)."""
    return api.c.request(method, url, content=body.encode(), headers={**JSON, "X-CSRF-Token": api.csrf})


def lenient(app, login: str) -> Api:
    """Клиент, который возвращает 500 как ответ (а не пробрасывает исключение сервера в тест)."""
    api = Api(app)
    api.c = TestClient(app, raise_server_exceptions=False)
    api.login(login)
    return api


@pytest.fixture
def ls1(app):
    return lenient(app, "student1")


@pytest.fixture
def lstaff(app):
    return lenient(app, "dekanat")


def ids_of(api: Api, url: str, key: str = "items") -> set[int]:
    return {x["id"] for x in api.get(url).json()[key]}


# --------------------------------------------------------------------------- #
# Изоляция данных (ТЗ §5.3, сценарий 6) — все ресурсы с ID
# --------------------------------------------------------------------------- #

def test_idor_every_application_of_other_student_all_methods(s1, s2):
    """Все заявки student1 (включая черновик и готовый электронный документ) недоступны student2 любым методом."""
    for a in s1.get("/api/applications?status=all").json()["items"]:
        aid = a["id"]
        for method, url, body in [
            ("get", f"/api/applications/{aid}", None),
            ("get", f"/api/applications/{aid}/document", None),
            ("patch", f"/api/applications/{aid}", {"payload": {"comment": "x"}}),
            ("post", f"/api/applications/{aid}/submit", None),
            ("post", f"/api/applications/{aid}/withdraw", None),
            ("post", f"/api/applications/{aid}/messages", {"text": "чужое"}),
            ("delete", f"/api/applications/{aid}", None),
        ]:
            fn = getattr(s2, method)
            r = fn(url, json=body) if body is not None else fn(url)
            assert r.status_code == 404, (method, url, r.status_code)
            assert "Воронцова" not in r.text
    # ничего не изменилось
    after = {a["id"]: a["status"] for a in s1.get("/api/applications?status=all").json()["items"]}
    before = {a["id"]: a["status"] for a in s1.get("/api/applications?status=all").json()["items"]}
    assert after == before


def test_idor_disciplines_topics_simulation_both_directions(s1, s2):
    for me, other in ((s1, s2), (s2, s1)):
        own = {d["id"] for d in me.get("/api/disciplines").json()["items"]}
        foreign = {d["id"] for d in other.get("/api/disciplines").json()["items"]}
        assert own and foreign and not own & foreign
        for did in foreign:
            assert me.get(f"/api/disciplines/{did}").status_code == 404
            assert me.post(f"/api/disciplines/{did}/simulate", json={"overrides": []}).status_code == 404
            for t in other.get(f"/api/disciplines/{did}").json()["topics"][:2]:
                assert me.get(f"/api/topics/{t['id']}").status_code == 404


def test_simulation_rejects_items_of_foreign_discipline(s1, s2):
    """Подстановка item_id чужой дисциплины в «Что если» своей дисциплины не раскрывает чужие данные."""
    d1 = s1.get("/api/disciplines/1").json()["analytics"]
    foreign_item = d1["modules"][-1]["items"][-1]["id"]
    own = sorted(d["id"] for d in s2.get("/api/disciplines").json()["items"])[0]
    r = s2.post(f"/api/disciplines/{own}/simulate", json={"overrides": [{"item_id": foreign_item, "points": 1}]})
    assert r.status_code == 400 and "не относится" in r.text


def test_idor_notifications_and_read_all_scope(s1, s2):
    n1 = s1.get("/api/notifications").json()
    n2 = s2.get("/api/notifications").json()
    assert not ({n["id"] for n in n1["items"]} & {n["id"] for n in n2["items"]})
    unread1 = n1["unread_count"]
    assert unread1 > 0
    for n in n1["items"][:5]:
        assert s2.post(f"/api/notifications/{n['id']}/read").status_code == 404
    # «прочитать все» у одного студента не трогает другого
    assert s2.post("/api/notifications/read-all", json={"category": "all"}).status_code == 200
    assert s1.get("/api/notifications").json()["unread_count"] == unread1


def test_two_students_see_different_data_everywhere(s1, s2):
    for url, extract in [
        ("/api/profile", lambda j: (j["full_name"], j["group"], j["course"], j["faculty"]["code"])),
        ("/api/schedule?from=2026-11-23&to=2026-11-29", lambda j: (j["group"], json.dumps(j["days"], ensure_ascii=False))),
        ("/api/grades", lambda j: json.dumps(j["record_book"], ensure_ascii=False)),
        ("/api/dashboard", lambda j: (j["first_name"], j["analytics"]["index"]["value"])),
        ("/api/application-types", lambda j: json.dumps([f.get("options") for t in j["items"] for f in t["fields"] if f["type"] == "discipline"])),
    ]:
        a, b = s1.get(url), s2.get(url)
        assert a.status_code == b.status_code == 200, url
        assert extract(a.json()) != extract(b.json()), url
    assert not ids_of(s1, "/api/applications?status=all") & ids_of(s2, "/api/applications?status=all")


def test_student_cannot_reach_any_staff_endpoint(s1):
    for method, url, body in [
        ("get", "/api/staff/applications?status=all", None), ("get", "/api/staff/applications/1", None),
        ("post", "/api/staff/applications/1/status", {"to_status": "ready"}),
        ("post", "/api/staff/applications/1/messages", {"text": "x"}),
        ("get", "/api/staff/students", None), ("get", "/api/staff/students/2/grades", None),
        ("put", "/api/staff/results", {"student_id": 1, "item_id": 1, "points": 10}),
        ("get", "/api/staff/announcements", None), ("post", "/api/staff/announcements", {"title": "abc", "body": "abc"}),
        ("get", "/api/staff/groups", None),
    ]:
        fn = getattr(s1, method)
        r = fn(url, json=body) if body is not None else fn(url)
        assert r.status_code == 403, (method, url, r.status_code)


def test_staff_cannot_use_student_endpoints_or_drafts(staff, s1):
    for url in ("/api/profile", "/api/dashboard", "/api/schedule", "/api/disciplines", "/api/disciplines/1",
                "/api/analytics", "/api/topics/1", "/api/grades", "/api/application-types", "/api/applications",
                "/api/applications/1", "/api/applications/1/document"):
        assert staff.get(url).status_code == 403, url
    assert staff.post("/api/applications", json={"type_key": "dean_question", "payload": {}, "submit": False}).status_code == 403
    draft = next(a for a in s1.get("/api/applications?status=draft").json()["items"])
    assert staff.get(f"/api/staff/applications/{draft['id']}").status_code == 404
    assert draft["id"] not in ids_of(staff, "/api/staff/applications?status=all")


def test_staff_result_requires_student_enrollment(staff):
    # item 1 — дисциплина student1; student2 (id 2) на неё не записан; id 3 — сотрудник
    for sid in (2, 3, 999):
        r = staff.put("/api/staff/results", json={"student_id": sid, "item_id": 1, "points": 1})
        assert r.status_code == 404, sid


# --------------------------------------------------------------------------- #
# Сессии, CSRF, перебор паролей, хранение паролей
# --------------------------------------------------------------------------- #

def test_old_cookie_and_csrf_useless_after_logout(app):
    api = Api(app, "student1")
    token, csrf = api.c.cookies.get("dd_session"), api.csrf
    assert api.post("/api/auth/logout").status_code == 204
    thief = TestClient(app)
    thief.cookies.set("dd_session", token)
    assert thief.get("/api/profile").status_code == 401
    assert thief.post("/api/notifications/read-all", json={}, headers={"X-CSRF-Token": csrf}).status_code == 401
    assert thief.get("/api/auth/me").json() == {"user": None, "csrf_token": None}


def test_relogin_rotates_session_token(app):
    api = Api(app, "student2")
    t1 = api.c.cookies.get("dd_session")
    api.login("student2")
    t2 = api.c.cookies.get("dd_session")
    assert t1 != t2
    old = TestClient(app)
    old.cookies.set("dd_session", t1)
    assert old.get("/api/profile").status_code == 401  # фиксация сессии невозможна


def test_csrf_foreign_token_form_and_text_plain_rejected(s1, s2):
    body = {"type_key": "dean_question", "payload": {}, "submit": False}
    assert s1.c.post("/api/applications", json=body).status_code == 403
    assert s1.c.post("/api/applications", json=body, headers={"X-CSRF-Token": s2.csrf}).status_code == 403
    r = s1.c.post("/api/applications", content="type_key=dean_question&submit=false",
                  headers={"X-CSRF-Token": s1.csrf, "Content-Type": "application/x-www-form-urlencoded"})
    assert r.status_code == 415
    r = s1.c.post("/api/applications", content=json.dumps(body), headers={"X-CSRF-Token": s1.csrf, "Content-Type": "text/plain"})
    assert r.status_code == 415
    assert s1.c.post("/api/notifications/read-all", content="category=all",
                     headers={"Content-Type": "application/x-www-form-urlencoded"}).status_code == 403
    assert s1.c.post("/api/auth/logout").status_code == 403


def test_login_accepts_only_json(app):
    c = TestClient(app)
    assert c.post("/api/auth/login", data={"login": "student1", "password": PASSWORDS["student1"]}).status_code == 422
    r = c.post("/api/auth/login", content=json.dumps({"login": "student1", "password": PASSWORDS["student1"]}),
               headers={"Content-Type": "text/plain"})
    assert r.status_code == 422 and "dd_session" not in c.cookies


def test_login_rate_limit_not_bypassed_by_spoofed_x_forwarded_for(app):
    """ДЕФЕКТ QA-03. Dockerfile включает TRUST_PROXY_HEADERS=true (и uvicorn --forwarded-allow-ips *), а client_ip()
    берёт ПЕРВЫЙ адрес X-Forwarded-For — его задаёт сам клиент. Прокси дописывает реальный IP в конец, поэтому
    подмена первого адреса не должна обнулять счётчик попыток."""
    from app.config import get_settings

    s = get_settings()
    old = s.trust_proxy_headers
    s.trust_proxy_headers = True
    try:
        c = TestClient(app)
        codes = [
            c.post("/api/auth/login", json={"login": "xff-probe", "password": "x"},
                   headers={"X-Forwarded-For": f"10.0.0.{i}, 203.0.113.7"}).status_code
            for i in range(s.login_rate_limit + 3)
        ]
    finally:
        s.trust_proxy_headers = old
    assert 429 in codes, codes


def test_wrong_login_and_wrong_password_indistinguishable(app):
    c = TestClient(app)
    a = c.post("/api/auth/login", json={"login": "student2", "password": "nope-nope"})
    b = c.post("/api/auth/login", json={"login": "nobody-here", "password": "nope-nope"})
    assert a.status_code == b.status_code == 401 and a.json() == b.json()


def test_passwords_stored_as_unique_salted_argon2id(app):
    from sqlalchemy import select

    from app.config import get_settings
    from app.db import SessionLocal
    from app.models import User

    with SessionLocal() as db:
        hashes = [u.password_hash for u in db.scalars(select(User)).all()]
    assert len(hashes) == len(set(hashes)) >= 3
    for h in hashes:
        assert h.startswith("$argon2id$v=19$m=65536,t=3,p=2$")
    # открытых паролей нет нигде в файле БД
    db_path = Path(get_settings().database_url.removeprefix("sqlite:///"))
    raw = db_path.read_bytes()
    for pw in PASSWORDS.values():
        assert pw.encode() not in raw


def test_no_secrets_in_frontend_bundle():
    dist = ROOT / "frontend" / "dist"
    if not dist.is_dir():
        pytest.skip("frontend/dist не собран")
    blob = "\n".join(p.read_text(errors="ignore") for p in dist.rglob("*") if p.suffix in (".js", ".html", ".css", ".map"))
    for needle in [*PASSWORDS.values(), "argon2", "DATABASE_URL", "PRIVATE KEY", "dd_session", "csrf_token\":\""]:
        assert needle not in blob, needle
    assert not list(dist.rglob("*.map")), "source maps в production-сборке"


def test_api_responses_do_not_expose_credentials(s1, staff):
    banned = re.compile(r'"(password|password_hash|hash|session_id|token_hash)"\s*:', re.I)
    for api, urls in ((s1, ["/api/profile", "/api/dashboard", "/api/analytics", "/api/grades", "/api/applications/1",
                            "/api/notifications", "/api/disciplines/1"]),
                      (staff, ["/api/staff/students", "/api/staff/students/1/grades", "/api/staff/applications?status=all",
                               "/api/staff/applications/1"])):
        for u in urls:
            r = api.get(u)
            assert r.status_code == 200, u
            assert not banned.search(r.text), u


def test_security_headers_on_api_and_spa(app):
    c = TestClient(app)
    for path in ("/api/health", "/", "/login", "/applications/1"):
        h = c.get(path).headers
        csp = h.get("content-security-policy", "")
        assert "default-src 'self'" in csp and "frame-ancestors 'none'" in csp and "script-src 'self'" in csp, path
        assert h.get("x-content-type-options") == "nosniff" and h.get("x-frame-options") == "DENY", path
    assert c.get("/api/health").headers.get("cache-control") == "no-store"
    r = c.post("/api/auth/login", json={"login": "student1", "password": PASSWORDS["student1"]})
    sc = r.headers["set-cookie"].lower()
    assert "httponly" in sc and "samesite=lax" in sc and "max-age=259200" in sc
    assert "access-control-allow-origin" not in c.get("/api/meta", headers={"Origin": "https://evil.example"}).headers


def test_static_serving_has_no_path_traversal(app):
    c = TestClient(app)
    for path in ("/%2e%2e/%2e%2e/backend/app/config.py", "/..%2f..%2fbackend%2fapp%2fconfig.py",
                 "/assets/..%2f..%2f..%2fbackend%2fapp%2fconfig.py", "/%2e%2e/%2e%2e/%2e%2e/etc/passwd", "//etc/passwd"):
        r = c.get(path)
        assert "BaseSettings" not in r.text and "root:" not in r.text, path


# --------------------------------------------------------------------------- #
# Валидация входа и обработка ошибок
# --------------------------------------------------------------------------- #

def test_negative_and_over_max_points_rejected(s1, staff):
    assert s1.post("/api/disciplines/1/simulate", json={"overrides": [{"item_id": 5, "points": -1}]}).status_code == 422
    assert s1.post("/api/disciplines/1/simulate", json={"overrides": [{"item_id": 5, "points": 9}]}).status_code == 400
    assert s1.post("/api/disciplines/1/simulate", json={"overrides": [], "exam_points": 31}).status_code == 400
    assert s1.post("/api/disciplines/6/simulate", json={"overrides": [], "exam_points": 20}).status_code == 400  # не экзамен
    assert raw_post(s1, "/api/disciplines/1/simulate", '{"overrides":[{"item_id":5,"points":NaN}]}').status_code == 422
    assert raw_post(s1, "/api/disciplines/1/simulate", '{"overrides":[],"exam_points":Infinity}').status_code == 422
    for pts in (-1, 11, 1e9):
        assert staff.put("/api/staff/results", json={"student_id": 1, "item_id": 1, "points": pts}).status_code == 422
    assert raw_post(staff, "/api/staff/results", '{"student_id":1,"item_id":1,"points":NaN}', "PUT").status_code == 422


def test_application_select_field_with_list_or_object_is_validation_error(ls1):
    """ДЕФЕКТ QA-04: значение-список/объект в поле select → TypeError (unhashable) → 500 вместо 422."""
    for bad in (["paper"], {"a": 1}):
        r = ls1.post("/api/applications", json={"type_key": "study_certificate",
                                               "payload": {"destination": "Для банка", "copies": 1, "delivery": bad}, "submit": False})
        assert r.status_code == 422, (bad, r.status_code)


def test_application_number_infinity_is_validation_error(ls1):
    """ДЕФЕКТ QA-04: copies/discipline_id = Infinity или 1e400 → OverflowError → 500 вместо 422."""
    for body in ('{"type_key":"study_certificate","payload":{"destination":"Для банка","copies":Infinity,"delivery":"paper"},"submit":false}',
                 '{"type_key":"study_certificate","payload":{"destination":"Для банка","copies":1e400,"delivery":"paper"},"submit":false}',
                 '{"type_key":"individual_schedule","payload":{"discipline_id":Infinity,"reason":"illness","details":"Болел две недели"},"submit":false}'):
        r = raw_post(ls1, "/api/applications", body)
        assert r.status_code == 422, (body[:60], r.status_code)


def test_application_discipline_field_rejects_float_and_bool(ls1):
    """ДЕФЕКТ QA-09: discipline_id=1.9 и true молча превращаются в 1 (int()), заявка принимается."""
    for bad in (1.9, True):
        r = ls1.post("/api/applications", json={"type_key": "individual_schedule", "submit": False,
                                               "payload": {"discipline_id": bad, "reason": "illness", "details": "Болел две недели"}})
        assert r.status_code == 422, (bad, r.status_code)


def test_required_text_cannot_be_invisible_characters(ls1):
    """ДЕФЕКТ QA-09: обязательное поле из трёх zero-width space проходит min_length=3 — заявка без содержания."""
    r = ls1.post("/api/applications", json={"type_key": "study_certificate", "submit": True,
                                           "payload": {"destination": "​​​", "copies": 1, "delivery": "paper"}})
    assert r.status_code == 422, r.status_code


@pytest.mark.parametrize("url", [
    "/api/applications/9223372036854775808",
    "/api/topics/9223372036854775808",
])
def test_huge_ids_are_not_found_not_500(ls1, url):
    """ДЕФЕКТ QA-04: ID ≥ 2^63 → OverflowError SQLite → 500 вместо 404."""
    assert ls1.get(url).status_code == 404


def test_huge_ids_on_mutations_and_staff_not_500(ls1, lstaff):
    """ДЕФЕКТ QA-04 (продолжение)."""
    assert ls1.post("/api/notifications/9223372036854775808/read").status_code == 404
    assert lstaff.get("/api/staff/applications/9223372036854775808").status_code == 404
    assert lstaff.get("/api/staff/students/9223372036854775808/grades").status_code == 404
    assert lstaff.put("/api/staff/results", json={"student_id": 1, "item_id": 9223372036854775808, "points": 1}).status_code in (404, 422)


@pytest.mark.parametrize("query", ["from=9999-12-31", "from=9999-12-31&to=9999-12-31", "from=9999-12-28&to=9999-12-31"])
def test_schedule_extreme_dates_are_rejected_not_500(ls1, query):
    """ДЕФЕКТ QA-04: дата у верхней границы календаря → OverflowError (date + timedelta) → 500."""
    r = ls1.get(f"/api/schedule?{query}")
    assert r.status_code in (400, 422), r.status_code


def test_schedule_range_validation(s1):
    assert s1.get("/api/schedule?from=2026-11-30&to=2026-11-01").status_code == 400
    assert s1.get("/api/schedule?from=2026-11-23&to=2027-01-04").status_code == 400  # > 6 недель
    assert s1.get("/api/schedule?from=2026-11-23&to=2027-01-03").status_code == 200
    assert s1.get("/api/schedule?from=abc").status_code == 422
    assert s1.get("/api/schedule?from=2026-02-30").status_code == 422


def test_application_dates_validated(s1):
    r = s1.post("/api/applications", json={"type_key": "scholarship_certificate", "submit": True,
                                           "payload": {"period_from": "2026-05-01", "period_to": "2026-03-01", "delivery": "paper"}})
    assert r.status_code == 422 and r.json()["errors"][0]["field"] == "period_to"
    r = s1.post("/api/applications", json={"type_key": "scholarship_certificate", "submit": True,
                                           "payload": {"period_from": "2026-02-30", "period_to": "2026-03-01", "delivery": "paper"}})
    assert r.status_code == 422


def test_body_size_limit_also_applies_to_chunked_requests(ls1):
    """ДЕФЕКТ QA-02: лимит 64 КБ проверяет только заголовок Content-Length; тело с Transfer-Encoding: chunked
    (без Content-Length) читается и разбирается целиком — в т.ч. на /api/auth/login без авторизации."""
    big = ('{"type_key":"dean_question","payload":{"topic":"study","subject":"abc","message":"'
           + "x" * (2 * 1024 * 1024) + '"},"submit":false}').encode()
    r = ls1.c.post("/api/applications", content=big, headers={**JSON, "X-CSRF-Token": ls1.csrf})
    assert r.status_code == 413  # с Content-Length — работает

    def chunks():
        for i in range(0, len(big), 65536):
            yield big[i:i + 65536]

    r = ls1.c.post("/api/applications", content=chunks(), headers={**JSON, "X-CSRF-Token": ls1.csrf})
    assert r.status_code == 413, r.status_code


def test_errors_do_not_leak_tracebacks_and_are_russian(ls1):
    """Частично ДЕФЕКТ QA-10: ошибка разбора тела отдаёт английский текст Starlette «There was an error parsing the body»."""
    bodies = ['{bad json', '{"type_key":"study_certificate","payload":{"copies":' + "9" * 5000 + '},"submit":false}', '[]', '"x"']
    for b in bodies:
        r = raw_post(ls1, "/api/applications", b)
        assert r.status_code < 500 or r.json()["code"] == "server_error"
        assert "Traceback" not in r.text and 'File "' not in r.text and "sqlalchemy" not in r.text.lower()
        detail = r.json()["detail"]
        assert re.search(r"[А-Яа-яЁё]", detail), f"сообщение не на русском: {detail!r}"


def test_null_byte_in_spa_path_is_not_500(app):
    """ДЕФЕКТ QA-04: GET /%00 → ValueError (embedded null byte) в обработчике SPA → 500."""
    if not (ROOT / "frontend" / "dist" / "index.html").exists():
        pytest.skip("frontend/dist не собран")
    assert TestClient(app, raise_server_exceptions=False).get("/%00").status_code in (200, 400, 404)


def test_unknown_fields_and_wrong_types_rejected(ls1):
    r = ls1.post("/api/applications", json={"type_key": "study_certificate", "submit": False,
                                           "payload": {"destination": 123, "is_admin": True}})
    assert r.status_code == 422
    fields = {e["field"] for e in r.json()["errors"]}
    assert {"destination", "is_admin"} <= fields
    assert ls1.post("/api/applications", json={"type_key": "x" * 65, "payload": {}}).status_code == 422
    assert ls1.post("/api/applications/1/messages", json={"text": "x" * 3001}).status_code == 422
    assert ls1.get("/api/notifications?category=hack").status_code == 422


# --------------------------------------------------------------------------- #
# Аналитика через API (ТЗ §14–§18): ручной пересчёт трёх типов аттестации
# --------------------------------------------------------------------------- #

def _an(api: Api, did: int) -> dict:
    return api.get(f"/api/disciplines/{did}").json()["analytics"]


def _t(a: dict, threshold: float) -> dict:
    return next(t for t in a["targets"] if t["threshold"] == threshold)


def test_manual_recalc_type_a_credit(s1):
    """«Инженерная и компьютерная графика»: 13+14+17 = 44 из 50; впереди 20+30 = 50; до 60 — 16 (32% остатка);
    темп 0.88, ориентир 44 + 0.88·50 = 88 ≥ 60+10 и r ≤ 0.5 → «Стабильно»."""
    a = _an(s1, 7)
    assert a["assessment_type"] == "credit"
    assert (a["current_semester_points"], a["remaining_points_max"], a["max_achievable_semester"]) == (44, 50, 94)
    assert a["semester_points_needed"] == 16 and a["required_share_of_remaining"] == 0.32
    assert a["current_pace"] == 0.88 and a["projected_semester_points"] == 88
    assert a["risk"]["level"] == "stable" and [t["threshold"] for t in a["targets"]] == [60]
    assert _t(a, 60)["status"] == "achievable" and _t(a, 60)["points_needed_semester"] == 16


def test_manual_recalc_type_b_distributed(s1, s2):
    """ООП: 27 + 30 = 57, впереди 35 → 60/71/85 требуют 3/14/28 (9%/40%/80%) — все достижимы.
    ТММ: 14 + 13 = 27, впереди 30 → максимум 57 < 60 → «Критический», все цели недостижимы."""
    a = _an(s1, 4)
    assert (a["current_semester_points"], a["remaining_points_max"]) == (57, 35)
    assert [(t["threshold"], t["status"], t["points_needed_semester"]) for t in a["targets"]] == [
        (60, "achievable", 3), (71, "achievable", 14), (85, "achievable", 28)]
    assert [t["required_share_of_remaining"] for t in a["targets"]] == [0.086, 0.4, 0.8]
    tmm = _an(s2, 11)
    assert (tmm["current_semester_points"], tmm["max_achievable_semester"]) == (27, 57)
    assert tmm["risk"]["level"] == "critical" and tmm["pass_status"] == "unreachable"
    assert all(t["status"] == "unreachable" for t in tmm["targets"])
    assert "57" in tmm["risk"]["reasons"][0]


def test_manual_recalc_type_c_exam(s1, s2):
    """Матанализ: 22 + 20 = 42 из 70 (S = 60 − 18 = 42 → обеспечено); экзамен: итог 60…72; 60 → 18, 71 → 29,
    85 → 85 − 30 − 42 = 13 баллов добрать в семестре. ТАУ: 26, нужно 34 > 30 → required_for_pass нет;
    цель 60 → добрать 4 и 30 на экзамене; 85 → недостижимо (максимум 46 + 30 = 76)."""
    a = _an(s1, 1)
    assert a["semester_points_max"] == 70 and a["semester_target"] == 42 and a["current_semester_points"] == 42
    assert a["risk"]["level"] == "stable" and a["pass_status"] == "secured"
    ex = a["exam"]
    assert (ex["points_min"], ex["points_max"], ex["required_for_pass"], ex["total_at_exam_min"], ex["total_at_exam_max"]) == (18, 30, 18, 60, 72)
    assert _t(a, 60)["exam_points_needed"] == 18 and _t(a, 71)["exam_points_needed"] == 29
    assert _t(a, 85)["extra_semester_points_needed"] == 13 and _t(a, 85)["status"] == "achievable"
    tau = _an(s2, 8)
    assert tau["current_semester_points"] == 26 and tau["exam"]["required_for_pass"] is None
    assert _t(tau, 60)["extra_semester_points_needed"] == 4 and _t(tau, 60)["exam_points_needed"] == 30
    assert _t(tau, 85)["status"] == "unreachable" and tau["exam"]["total_max_possible"] == 76
    assert tau["risk"]["level"] == "high"


def test_exam_minimum_18_enforced_even_if_sum_reaches_threshold(s1):
    """§14.2/§15.5: семестр 62 + экзамен 17 = 79 ≥ 60, но экзамен ниже 18 → не сдан."""
    sim = s1.post("/api/disciplines/1/simulate", json={"overrides": [{"item_id": 5, "points": 8}, {"item_id": 6, "points": 12}],
                                                      "exam_points": 17}).json()["analytics"]
    assert sim["current_semester_points"] == 62
    assert sim["exam"]["passed"] is False and sim["pass_status"] == "failed" and sim["risk"]["level"] == "critical"
    assert sim["current_grade"]["key"] == "unsatisfactory"
    assert all(t["status"] != "reached" for t in sim["targets"])
    ok = s1.post("/api/disciplines/1/simulate", json={"overrides": [], "exam_points": 18}).json()["analytics"]
    assert ok["exam"]["final_total"] == 60 and ok["pass_status"] == "passed" and ok["current_grade"]["key"] == "satisfactory"


def test_exam_target_below_18_still_requires_18(s1):
    """§18.4: семестр 50 → для 60 по сумме хватило бы 10, но требуется 18."""
    sim = s1.post("/api/disciplines/1/simulate", json={"overrides": [{"item_id": 5, "points": 8}]}).json()["analytics"]
    assert sim["current_semester_points"] == 50
    assert _t(sim, 60)["exam_points_needed"] == 18 and sim["exam"]["required_for_pass"] == 18


def test_credit_59_vs_60_via_simulation(s2):
    """§18.1 через API: «Экономика» 27 + 20 + 12 = 59 → не достигнут; + 13 = 60 → достигнут."""
    s59 = s2.post("/api/disciplines/13/simulate", json={"overrides": [{"item_id": 86, "points": 20}, {"item_id": 87, "points": 12}]}).json()["analytics"]
    s60 = s2.post("/api/disciplines/13/simulate", json={"overrides": [{"item_id": 86, "points": 20}, {"item_id": 87, "points": 13}]}).json()["analytics"]
    assert s59["current_semester_points"] == 59 and _t(s59, 60)["status"] == "achievable" and s59["pass_status"] != "secured"
    assert s60["current_semester_points"] == 60 and _t(s60, 60)["status"] == "reached" and s60["pass_status"] == "secured"


def test_insufficient_data_is_honest(s1):
    """Английский у student1: по завершённому модулю баллов нет → «Недостаточно данных», без прогноза и без учёта в индексе."""
    a = _an(s1, 6)
    assert a["risk"]["level"] == "insufficient_data" and a["data_completeness"] == "insufficient"
    assert a["projected_semester_points"] is None and a["required_share_of_remaining"] is None
    assert all(t["status"] == "unknown" for t in a["targets"])
    summary = s1.get("/api/analytics").json()
    assert summary["zone_counts"]["insufficient_data"] == 1 and summary["index"]["disciplines_counted"] == 6
    assert "Иностранный язык (английский)" in summary["explanation"]


def test_one_critical_discipline_caps_index_via_staff_grading(s1, staff):
    """§15.7/§18.10 сквозь API: сотрудник обнуляет все оставшиеся работы по «Дискретной математике» —
    дисциплина становится критической, индекс student1 (было 90) ограничивается ≤ 59, она первая в приоритетах."""
    before = s1.get("/api/analytics").json()
    assert before["index"]["value"] == 90
    a = _an(s1, 5)
    pending = [i["id"] for m in a["modules"] for i in m["items"] if i["state"] == "pending"]
    try:
        for iid in pending:
            assert staff.put("/api/staff/results", json={"student_id": 1, "item_id": iid, "points": 0}).status_code == 200
        after = s1.get("/api/analytics").json()
        dm = next(d for d in after["disciplines"] if d["discipline_id"] == 5)
        assert dm["risk"]["level"] == "critical"
        assert after["index"]["value"] <= 59 and "critical" in after["index"]["caps_applied"]
        assert after["index"]["zone"] != "stable"
        assert after["priorities"][0]["discipline_id"] == 5 and after["disciplines"][0]["discipline_id"] == 5
        assert "Дискретная математика" in after["explanation"]
    finally:
        for iid in pending:
            staff.put("/api/staff/results", json={"student_id": 1, "item_id": iid, "points": None})
    assert s1.get("/api/analytics").json()["index"]["value"] == 90


def test_index_matches_formula_for_student2(s2):
    s = s2.get("/api/analytics").json()
    scores = {"stable": 100, "low": 80, "medium": 60, "high": 35, "critical": 10}
    lv = [d["risk"]["level"] for d in s["disciplines"] if d["risk"]["level"] in scores]
    mean = sum(scores[x] for x in lv) / len(lv)
    assert s["index"]["value"] == int(mean + 0.5) == 51 and s["index"]["zone"] == "high"
    assert s["zone_counts"] == {"critical": 1, "high": 3, "medium": 1, "low": 1, "stable": 1, "insufficient_data": 0}
    assert s["disciplines"][0]["risk"]["level"] == "critical"


def test_texts_never_present_risk_as_probability(s1, s2):
    def strings(o):
        if isinstance(o, str):
            yield o
        elif isinstance(o, dict):
            for k, v in o.items():
                if k not in ("title", "module_title"):  # названия дисциплин («Теория вероятностей…») — не тексты аналитики
                    yield from strings(v)
        elif isinstance(o, list):
            for v in o:
                yield from strings(v)

    for api in (s1, s2):
        for txt in strings(api.get("/api/analytics").json()):
            low = txt.lower().replace("теория вероятностей", "")
            if "вероятн" in low:
                assert "не вероятност" in low or "а не вероятност" in low, txt
            assert not re.search(r"(шанс|вероятность)\w*\s+(сдачи|сдать)\s*[—:-]?\s*\d", low), txt


def test_topic_materials_belong_to_topic_and_hide_broken_links(s2):
    d = s2.get("/api/disciplines/11").json()
    weak = [t for t in d["topics"] if t["is_weak"]]
    assert weak, "у критической дисциплины есть темы «стоит повторить»"
    for t in d["topics"]:
        tp = s2.get(f"/api/topics/{t['id']}").json()
        assert tp["topic"]["id"] == t["id"] and tp["discipline"]["id"] == 11
        assert all(r["link_status"] != "broken" and r["url"].startswith("https://") for r in tp["resources"])


# --------------------------------------------------------------------------- #
# Сохранность и доставка статусов
# --------------------------------------------------------------------------- #

def test_application_survives_app_restart(app, s2):
    r = s2.post("/api/applications", json={"type_key": "transcript", "submit": True,
                                           "payload": {"scope": "all", "language": "en", "delivery": "electronic"}})
    aid = r.json()["id"]
    with TestClient(app):  # повторный запуск lifespan: миграции/seed не должны затирать данные
        pass
    again = Api(app, "student2")
    assert again.get(f"/api/applications/{aid}").json()["status"] == "submitted"


def test_staff_status_change_and_reply_reach_student(s2, staff):
    r = s2.post("/api/applications", json={"type_key": "dean_question", "submit": True,
                                           "payload": {"topic": "schedule", "subject": "Консультация", "message": "Когда консультация по ТАУ?"}})
    aid, number = r.json()["id"], r.json()["number"]
    assert staff.post(f"/api/staff/applications/{aid}/status", json={"to_status": "in_progress"}).status_code == 200
    assert staff.post(f"/api/staff/applications/{aid}/messages", json={"text": "В четверг в 15:40"}).status_code == 201
    d = s2.get(f"/api/applications/{aid}").json()
    assert d["status"] == "in_progress" and d["messages"][-1]["text"] == "В четверг в 15:40" and not d["messages"][-1]["is_mine"]
    titles = [n["title"] for n in s2.get("/api/notifications?category=application").json()["items"]]
    assert any(number in t and "в обработке" in t for t in titles)
    assert any(number in t and "Ответ деканата" in t for t in titles)


def test_direct_docker_run_does_not_trust_client_x_forwarded_for():
    """ДЕФЕКТ QA-03 (остаток после исправления). Dockerfile по умолчанию ставит TRUST_PROXY_HEADERS=true, а
    docker-compose.yml (локальный запуск/VPS без прокси, порт 8000 открыт напрямую) это не переопределяет. Без прокси
    «последний адрес X-Forwarded-For» тоже задаёт клиент: одиночный подменяемый заголовок обнуляет лимит попыток входа.
    Ожидается: доверять X-Forwarded-For только там, где прокси гарантированно есть (по умолчанию — false)."""
    dockerfile = (ROOT / "Dockerfile").read_text()
    compose = (ROOT / "docker-compose.yml").read_text()
    trusts_by_default = re.search(r"TRUST_PROXY_HEADERS\s*=\s*true", dockerfile, re.I) is not None
    compose_overrides = re.search(r"TRUST_PROXY_HEADERS\s*:\s*\"?false", compose, re.I) is not None
    assert not trusts_by_default or compose_overrides
