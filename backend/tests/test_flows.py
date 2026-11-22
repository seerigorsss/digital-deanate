"""Функциональные сценарии: заявки (2.4), расписание (2.2), уведомления (2.5), пересчёт аналитики после изменения баллов."""
from .conftest import Api


def test_application_full_lifecycle(app, s1, staff):
    r = s1.post("/api/applications", json={"type_key": "study_certificate",
                                           "payload": {"destination": "Для банка", "copies": 1, "delivery": "electronic"}})
    assert r.status_code == 201
    a = r.json()
    assert a["status"] == "submitted" and a["number"] and a["next_step"]
    app_id = a["id"]
    assert app_id in {x["id"] for x in s1.get("/api/applications").json()["items"]}

    # «перезагрузка» и повторный вход — заявка на месте
    again = Api(app, "student1")
    assert again.get(f"/api/applications/{app_id}").json()["status"] == "submitted"

    # деканат: в работу → требуется уточнение (комментарий обязателен)
    assert staff.post(f"/api/staff/applications/{app_id}/status", json={"to_status": "in_progress"}).status_code == 200
    bad = staff.post(f"/api/staff/applications/{app_id}/status", json={"to_status": "needs_info"})
    assert bad.status_code == 422
    assert staff.post(f"/api/staff/applications/{app_id}/status",
                      json={"to_status": "needs_info", "comment": "Укажите название банка"}).status_code == 200
    # неверный переход отклоняется
    assert staff.post(f"/api/staff/applications/{app_id}/status", json={"to_status": "completed"}).status_code == 409

    notes = s1.get("/api/notifications?category=application").json()["items"]
    assert any(f"№ {a['number']}" in n["title"] for n in notes)

    # ответ студента возвращает заявку в «Отправлена»
    r = s1.post(f"/api/applications/{app_id}/messages", json={"text": "ПАО «Вымышленный банк»"})
    assert r.status_code == 201 and r.json()["status"] == "submitted"
    staff.post(f"/api/staff/applications/{app_id}/status", json={"to_status": "in_progress"})
    staff.post(f"/api/staff/applications/{app_id}/status", json={"to_status": "ready"})
    detail = s1.get(f"/api/applications/{app_id}").json()
    assert detail["status"] == "ready" and detail["document_available"]
    assert [h["to_status"] for h in detail["history"]][-1] == "ready"
    doc = s1.get(f"/api/applications/{app_id}/document").json()
    assert "ОБРАЗЕЦ" in doc["watermark"] and doc["student"]["full_name"].startswith("Воронцова")


def test_draft_edit_submit_delete_and_withdraw(s2):
    r = s2.post("/api/applications", json={"type_key": "dean_question", "payload": {"topic": "study"}, "submit": False})
    assert r.status_code == 201 and r.json()["status"] == "draft"
    did = r.json()["id"]
    assert s2.post(f"/api/applications/{did}/submit").status_code == 422  # не заполнены обязательные поля
    assert s2.patch(f"/api/applications/{did}", json={"payload": {"topic": "study", "subject": "Вопрос",
                                                                   "message": "Когда будет консультация?"}}).status_code == 200
    assert s2.post(f"/api/applications/{did}/submit").json()["status"] == "submitted"
    assert s2.delete(f"/api/applications/{did}").status_code == 409  # уже не черновик
    assert s2.post(f"/api/applications/{did}/withdraw").json()["status"] == "withdrawn"

    r = s2.post("/api/applications", json={"type_key": "transcript", "payload": {}, "submit": False})
    assert s2.delete(f"/api/applications/{r.json()['id']}").status_code == 204


def test_application_validation_errors(s1):
    r = s1.post("/api/applications", json={"type_key": "study_certificate", "payload": {"copies": 99, "delivery": "fax"}})
    assert r.status_code == 422
    fields = {e["field"] for e in r.json()["errors"]}
    assert {"destination", "copies", "delivery"} <= fields
    r = s1.post("/api/applications", json={"type_key": "scholarship_certificate",
                                           "payload": {"period_from": "2026-11-01", "period_to": "2026-10-01", "delivery": "paper"}})
    assert r.status_code == 422
    assert s1.post("/api/applications", json={"type_key": "unknown", "payload": {}}).status_code == 400


def test_schedule_week_with_changes(s1, s2):
    w = s1.get("/api/schedule?from=2026-11-23&to=2026-11-29").json()
    assert len(w["days"]) == 7 and w["days"][0]["week_parity_label"] == "Числитель"
    statuses = {l["status"] for d in w["days"] for l in d["lessons"]}
    assert {"changed", "cancelled", "moved_out", "moved_in", "added"} <= statuses
    mon = w["days"][0]["lessons"][0]
    assert {"discipline_title", "start_time", "end_time", "room", "teacher"} <= set(mon)
    assert w["days"][6]["lessons"] == []  # воскресенье
    w2 = s2.get("/api/schedule?from=2026-11-23&to=2026-11-29").json()
    assert w2["group"] == "РК9-51Б"
    assert s1.get("/api/schedule?from=2026-01-01&to=2026-12-31").status_code == 400


def test_dashboard_today(s1):
    d = s1.get("/api/dashboard").json()
    assert d["today"] == "2026-11-23" and d["today_lessons"]
    assert d["analytics"]["index"]["value"] is not None
    assert d["notifications"]["unread_count"] >= 1
    assert d["deadlines"] and d["deadlines"][0]["days_left"] >= 0


def test_notifications_read_state(s2):
    data = s2.get("/api/notifications").json()
    assert data["unread_count"] > 0
    nid = next(n["id"] for n in data["items"] if not n["is_read"])
    assert s2.post(f"/api/notifications/{nid}/read").json()["is_read"] is True
    s2.post("/api/notifications/read-all", json={"category": "all"})
    assert s2.get("/api/notifications").json()["unread_count"] == 0


def test_staff_grade_changes_recalculate_analytics(s1, staff):
    dm = next(d for d in s1.get("/api/analytics").json()["disciplines"] if d["title"] == "Дискретная математика")
    assert dm["risk"]["level"] == "medium"
    detail = s1.get(f"/api/disciplines/{dm['discipline_id']}").json()
    items = {i["title"]: i["id"] for m in detail["analytics"]["modules"] for i in m["items"]}
    me = s1.get("/api/auth/me").json()["user"]["id"]
    for title, pts in (("Домашнее задание 3", 10), ("Рубежный контроль 2", 15)):
        r = staff.put("/api/staff/results", json={"student_id": me, "item_id": items[title], "points": pts})
        assert r.status_code == 200
    dm2 = next(d for d in s1.get("/api/analytics").json()["disciplines"] if d["title"] == "Дискретная математика")
    assert dm2["current_semester_points"] == dm["current_semester_points"] + 25
    assert dm2["risk"]["level"] in ("low", "stable")
    assert any(n["category"] == "grade" for n in s1.get("/api/notifications").json()["items"])
    # откат, чтобы не влиять на другие тесты
    for title in ("Домашнее задание 3", "Рубежный контроль 2"):
        staff.put("/api/staff/results", json={"student_id": me, "item_id": items[title], "points": None})
    r = staff.put("/api/staff/results", json={"student_id": me, "item_id": items["Рубежный контроль 2"], "points": 99})
    assert r.status_code == 422


def test_simulation_does_not_persist(s2):
    tmm = next(d for d in s2.get("/api/analytics").json()["disciplines"] if d["title"] == "Теория механизмов и машин")
    detail = s2.get(f"/api/disciplines/{tmm['discipline_id']}").json()
    pending = [i for m in detail["analytics"]["modules"] for i in m["items"] if i["state"] == "pending"]
    sim = s2.post(f"/api/disciplines/{tmm['discipline_id']}/simulate",
                  json={"overrides": [{"item_id": i["id"], "points": i["max_points"]} for i in pending]}).json()
    assert sim["simulated"] is True
    assert sim["analytics"]["current_semester_points"] == tmm["current_semester_points"] + sum(i["max_points"] for i in pending)
    again = next(d for d in s2.get("/api/analytics").json()["disciplines"] if d["title"] == "Теория механизмов и машин")
    assert again["current_semester_points"] == tmm["current_semester_points"]
    graded = next(i for m in detail["analytics"]["modules"] for i in m["items"] if i["state"] == "graded")
    r = s2.post(f"/api/disciplines/{tmm['discipline_id']}/simulate", json={"overrides": [{"item_id": graded["id"], "points": 0}]})
    assert r.status_code == 400


def test_duplicate_dynamic_notification_race_is_ignored(app):
    """Регрессия: гонка двух запросов, создающих одно уведомление, не должна давать 500 (найдено e2e-проверкой)."""
    from unittest.mock import patch

    from app.db import SessionLocal
    from app.models import Notification, User
    from app.services import notifications as svc

    with SessionLocal() as db:
        uid = db.query(User).filter_by(login="student1").one().id
        svc.notify(db, uid, "deadline", "t", "b", source_key="race:test")
        db.commit()
        # имитируем гонку: проверка «уже есть?» не видит запись, созданную параллельным запросом
        with patch.object(db, "scalar", return_value=None):
            assert svc.notify(db, uid, "deadline", "t", "b", source_key="race:test") is None
        db.commit()
        assert db.query(Notification).filter_by(user_id=uid, source_key="race:test").count() == 1
