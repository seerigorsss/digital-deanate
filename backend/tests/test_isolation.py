"""Сценарий 6 ТЗ: изоляция данных между студентами (IDOR) при прямых запросах к API."""


def test_foreign_application_inaccessible(s1, s2):
    a1 = s1.get("/api/applications").json()["items"]
    assert a1, "у первого студента есть заявки"
    target = a1[0]["id"]
    assert s1.get(f"/api/applications/{target}").status_code == 200
    for method, url, body in [
        ("get", f"/api/applications/{target}", None),
        ("get", f"/api/applications/{target}/document", None),
        ("patch", f"/api/applications/{target}", {"payload": {}}),
        ("post", f"/api/applications/{target}/submit", None),
        ("post", f"/api/applications/{target}/withdraw", None),
        ("post", f"/api/applications/{target}/messages", {"text": "чужое сообщение"}),
        ("delete", f"/api/applications/{target}", None),
    ]:
        fn = getattr(s2, method)
        r = fn(url, json=body) if body is not None else fn(url)
        assert r.status_code == 404, (method, url, r.status_code)
    ids2 = {a["id"] for a in s2.get("/api/applications").json()["items"]}
    assert target not in ids2
    # заявка не изменилась
    assert s1.get(f"/api/applications/{target}").json()["status"] == a1[0]["status"]


def test_foreign_discipline_topic_and_simulation_inaccessible(s1, s2):
    d1 = {d["id"] for d in s1.get("/api/disciplines").json()["items"]}
    d2 = {d["id"] for d in s2.get("/api/disciplines").json()["items"]}
    assert d1 and d2 and not (d1 & d2)
    foreign = sorted(d1)[0]
    assert s2.get(f"/api/disciplines/{foreign}").status_code == 404
    assert s2.post(f"/api/disciplines/{foreign}/simulate", json={"overrides": []}).status_code == 404
    topic_id = s1.get(f"/api/disciplines/{foreign}").json()["topics"][0]["id"]
    assert s1.get(f"/api/topics/{topic_id}").status_code == 200
    assert s2.get(f"/api/topics/{topic_id}").status_code == 404


def test_analytics_and_grades_belong_to_current_user(s1, s2):
    t1 = {d["title"] for d in s1.get("/api/analytics").json()["disciplines"]}
    t2 = {d["title"] for d in s2.get("/api/analytics").json()["disciplines"]}
    assert "Математический анализ" in t1 and "Теория механизмов и машин" in t2
    assert not (t1 & t2)
    g1 = s1.get("/api/grades").json()
    g2 = s2.get("/api/grades").json()
    assert len(g1["record_book"]) == 2 and len(g2["record_book"]) == 4


def test_foreign_notification_cannot_be_read_or_marked(s1, s2):
    n1 = s1.get("/api/notifications").json()["items"]
    unread = [n for n in n1 if not n["is_read"]]
    assert unread
    target = unread[0]["id"]
    assert s2.post(f"/api/notifications/{target}/read").status_code == 404
    assert target not in {n["id"] for n in s2.get("/api/notifications").json()["items"]}
    after = {n["id"]: n for n in s1.get("/api/notifications").json()["items"]}
    assert after[target]["is_read"] is False


def test_user_id_query_params_are_ignored(s2):
    # попытка «подсказать» чужой ID параметром не влияет на выдачу
    p = s2.get("/api/profile?user_id=1&id=1").json()
    assert p["last_name"] == "Калинин"


def test_application_cannot_reference_foreign_discipline(s1, s2):
    foreign = sorted(d["id"] for d in s1.get("/api/disciplines").json()["items"])[0]
    r = s2.post("/api/applications", json={"type_key": "individual_schedule",
                                           "payload": {"discipline_id": foreign, "reason": "illness", "details": "Пропустил занятия по болезни"}})
    assert r.status_code == 422
    assert any(e["field"] == "discipline_id" for e in r.json()["errors"])
