"""Заполнение БД начальными вымышленными данными.

Запуск вручную:  python -m app.seed            — заполнить пустую БД
                 python -m app.seed --reset    — удалить все данные и заполнить заново
При старте приложения (SEED_ON_STARTUP=true) пустая БД заполняется автоматически,
а каталог учебных материалов синхронизируется с learning_resources.json.
"""
from __future__ import annotations

import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import Base
from ..models import (
    AcademicPeriod,
    Announcement,
    Application,
    ApplicationMessage,
    ApplicationStatusHistory,
    AssessmentConfiguration,
    AssessmentItem,
    Discipline,
    Enrollment,
    ItemResult,
    LearningResource,
    LessonTemplate,
    Module,
    Notification,
    RecordBookEntry,
    ScheduleChange,
    StaffProfile,
    StudentProfile,
    Teacher,
    Topic,
    TopicResource,
    User,
)
from ..security.passwords import hash_password
from ..services.application_types import STATUS_LABELS, TYPES_BY_KEY
from . import demo_data as D

DATA = Path(__file__).parent / "data"
MSK = ZoneInfo("Europe/Moscow")
GRADE_LABELS = {"excellent": "Отлично", "good": "Хорошо", "satisfactory": "Удовлетворительно", "passed": "Зачтено"}


def _d(s: str | None) -> date | None:
    return date.fromisoformat(s) if s else None


def _ts(s: str) -> datetime:
    return datetime.fromisoformat(s).replace(tzinfo=MSK).astimezone(timezone.utc)


def load_json(name: str) -> dict:
    return json.loads((DATA / name).read_text(encoding="utf-8"))


def is_seeded(db: Session) -> bool:
    return db.scalar(select(User.id).limit(1)) is not None


def seed_all(db: Session) -> None:
    s = get_settings()
    cur = load_json("curriculum.json")
    results = load_json("demo_results.json")

    pd = cur["period"]
    period = AcademicPeriod(key=pd["key"], title=pd["title"], starts_on=_d(pd["starts_on"]), ends_on=_d(pd["ends_on"]),
                            session_starts_on=_d(pd["session_starts_on"]), session_ends_on=_d(pd["session_ends_on"]),
                            week1_monday=_d(pd["week1_monday"]), is_current=True)
    db.add(period)
    teachers = {}
    for t in cur["teachers"]:
        teachers[t["key"]] = Teacher(key=t["key"], full_name=t["full_name"], position=t["position"],
                                     department=t["department"], email=t["email"])
        db.add(teachers[t["key"]])
    db.flush()

    disciplines: dict[str, Discipline] = {}
    items: dict[tuple[str, str], AssessmentItem] = {}
    for dd in cur["disciplines"]:
        d = Discipline(key=dd["key"], period_id=period.id, title=dd["title"], short_title=dd["short_title"],
                       department=dd["department"], description=dd["description"], credits=dd["credits"],
                       lecturer_id=teachers[dd["lecturer"]].id)
        db.add(d)
        db.flush()
        a = dd["assessment"]
        db.add(AssessmentConfiguration(discipline_id=d.id, assessment_type=a["type"], semester_points_max=a["semester_points_max"],
                                       passing_threshold=a["passing_threshold"], exam_points_min=a.get("exam_points_min"),
                                       exam_points_max=a.get("exam_points_max"), exam_date=_d(a.get("exam_date")),
                                       exam_room=a.get("exam_room")))
        mods = {}
        for m in dd["modules"]:
            mod = Module(discipline_id=d.id, ordinal=m["ordinal"], title=m["title"], starts_on=_d(m["starts_on"]),
                         ends_on=_d(m["ends_on"]), status=m["status"])
            db.add(mod)
            db.flush()
            mods[m["ordinal"]] = mod
            for it in m["items"]:
                item = AssessmentItem(module_id=mod.id, key=it["key"], title=it["title"], kind=it["kind"],
                                      max_points=it["max_points"], due_date=_d(it["due_date"]))
                db.add(item)
                items[(dd["key"], it["key"])] = item
        for i, tp in enumerate(dd["topics"]):
            db.add(Topic(key=tp["key"], discipline_id=d.id, module_id=mods[tp["module"]].id, ordinal=i, title=tp["title"]))
        disciplines[dd["key"]] = d
    db.flush()

    # Пользователи
    users: dict[str, User] = {}
    for st in D.STUDENTS:
        u = User(login=st["login"], password_hash=hash_password(getattr(s, st["password_setting"])), role="student")
        db.add(u)
        db.flush()
        db.add(StudentProfile(user_id=u.id, **st["profile"]))
        users[st["login"]] = u
    staff = User(login=D.STAFF["login"], password_hash=hash_password(getattr(s, D.STAFF["password_setting"])), role="staff")
    db.add(staff)
    db.flush()
    db.add(StaffProfile(user_id=staff.id, **D.STAFF["profile"]))
    db.flush()

    # Записи на дисциплины и баллы
    group_of = {st["login"]: st["profile"]["group_name"] for st in D.STUDENTS}
    groups = {g["name"]: g["disciplines"] for g in cur["groups"]}
    for login, u in users.items():
        for dkey in groups[group_of[login]]:
            enr = Enrollment(student_id=u.id, discipline_id=disciplines[dkey].id, period_id=period.id)
            db.add(enr)
            db.flush()
            for ikey, pts in results[login][dkey]["points"].items():
                item = items[(dkey, ikey)]
                graded = datetime.combine(item.due_date + timedelta(days=2), datetime.min.time(), tzinfo=MSK) + timedelta(hours=17)
                db.add(ItemResult(enrollment_id=enr.id, item_id=item.id, points=pts, graded_at=graded.astimezone(timezone.utc),
                                  graded_by_user_id=staff.id))
    db.flush()

    # Расписание
    lessons: dict[tuple[str, str, str], LessonTemplate] = {}
    for group, rows in D.SCHEDULE.items():
        for wd, pair, dkey, ltype, tkey, room, parity in rows:
            st_, en_ = D.P[pair]
            lt = LessonTemplate(period_id=period.id, group_name=group, discipline_id=disciplines[dkey].id, weekday=wd,
                                start_time=st_, end_time=en_, lesson_type=ltype, room=room, teacher_id=teachers[tkey].id,
                                week_parity=parity)
            db.add(lt)
            lessons.setdefault((group, dkey, ltype), lt)
    db.flush()
    for ds, group, ctype, ref, params in D.SCHEDULE_CHANGES:
        ch = ScheduleChange(group_name=group, date=_d(ds), change_type=ctype, reason=params.get("reason"),
                            created_at=_ts("2026-11-20T10:00"))
        if ref:
            ch.lesson_id = lessons[(group, ref[0], ref[1])].id
        if "new_room" in params:
            ch.new_room = params["new_room"]
        if "teacher" in params:
            ch.new_teacher_id = teachers[params["teacher"]].id
        if "new_date" in params:
            ch.new_date = _d(params["new_date"])
        if "pair" in params:
            ch.new_start_time, ch.new_end_time = D.P[params["pair"]]
        if ctype == "added":
            ch.discipline_id = disciplines[params["discipline"]].id
            ch.lesson_type = params["lesson_type"]
        db.add(ch)

    # Зачётные книжки
    for login, rows in D.RECORD_BOOK.items():
        for sem, title, atype, pts, gkey, credits, passed in rows:
            db.add(RecordBookEntry(student_id=users[login].id, semester=sem, discipline_title=title, assessment_type=atype,
                                   points=pts, grade_key=gkey, grade_label=GRADE_LABELS[gkey], credits=credits,
                                   passed_on=_d(passed)))

    # Заявки с историей, перепиской и уведомлениями о смене статуса
    staff_name = f"{D.STAFF['profile']['last_name']} {D.STAFF['profile']['first_name']} {D.STAFF['profile']['middle_name']} (деканат)"
    read_before = _ts("2026-11-17T00:00")
    for login, apps in D.APPLICATIONS.items():
        u = users[login]
        sp_name = " ".join(st["profile"][k] for st in D.STUDENTS if st["login"] == login
                           for k in ("last_name", "first_name", "middle_name"))
        for spec in apps:
            payload = dict(spec["payload"])
            if "discipline_key" in payload:
                payload["discipline_id"] = disciplines[payload.pop("discipline_key")].id
            hist = spec["history"]
            a = Application(user_id=u.id, type_key=spec["type"], status=hist[-1][0], payload=payload,
                            created_at=_ts(hist[0][1]), updated_at=_ts(hist[-1][1]))
            db.add(a)
            db.flush()
            a.number = f"26-{a.id:05d}"
            prev = None
            for status, ts, role, comment in hist:
                db.add(ApplicationStatusHistory(application_id=a.id, from_status=prev, to_status=status, comment=comment,
                                                actor_user_id=staff.id if role == "staff" else u.id, actor_role=role,
                                                created_at=_ts(ts)))
                if status == "submitted" and a.submitted_at is None:
                    a.submitted_at = _ts(ts)
                if status in ("completed", "rejected", "withdrawn"):
                    a.closed_at = _ts(ts)
                if comment and role == "staff":
                    db.add(ApplicationMessage(application_id=a.id, author_user_id=staff.id, author_role="staff",
                                              author_name=staff_name, text=comment, created_at=_ts(ts)))
                if role == "staff":
                    label = STATUS_LABELS[status]
                    n = Notification(user_id=u.id, category="application", title=f"Заявка № {a.number}: {label.lower()}",
                                     body=f"«{TYPES_BY_KEY[a.type_key]['title']}» — новый статус: {label}."
                                          + (f" Комментарий деканата: {comment}" if comment else ""),
                                     link=f"/applications/{a.id}",
                                     importance="high" if status in ("needs_info", "ready", "rejected") else "normal",
                                     source_key=f"app:{a.id}:{status}:seed", created_at=_ts(ts))
                    n.read_at = _ts(ts) + timedelta(hours=3) if _ts(ts) < read_before else None
                    db.add(n)
                prev = status
            if spec["type"] == "dean_question":
                db.add(ApplicationMessage(application_id=a.id, author_user_id=u.id, author_role="student",
                                          author_name=sp_name, text=payload["message"], created_at=_ts(hist[1][1])))

    # Объявления деканата (рассылаются всем студентам)
    for ts, title, body, importance, link in D.ANNOUNCEMENTS:
        ann = Announcement(title=title, body=body, audience="all", author_user_id=staff.id, published_at=_ts(ts))
        db.add(ann)
        db.flush()
        for u in users.values():
            db.add(Notification(user_id=u.id, category="announcement", title=title, body=body, link=link or "/notifications",
                                importance=importance, source_key=f"ann:{ann.id}", created_at=_ts(ts),
                                read_at=_ts(ts) + timedelta(hours=5) if _ts(ts) < read_before else None))

    # Уведомления о недавно выставленных баллах
    for login, dkey, ikey, ts in D.GRADE_NOTICES:
        item = items[(dkey, ikey)]
        pts = results[login][dkey]["points"][ikey]
        d = disciplines[dkey]
        mod = db.get(Module, item.module_id)
        db.add(Notification(user_id=users[login].id, category="grade", title=f"Новые баллы: {d.short_title}",
                            body=f"{item.title} («{mod.title}»): {pts:g} из {item.max_points:g}.",
                            link=f"/study/{d.id}", source_key=f"grade:seed:{dkey}:{ikey}", created_at=_ts(ts),
                            read_at=_ts(ts) + timedelta(hours=2) if _ts(ts) < read_before else None))
    db.commit()


def sync_resources(db: Session) -> int:
    """Синхронизирует справочник учебных материалов с JSON-каталогом (идемпотентно)."""
    path = DATA / "learning_resources.json"
    if not path.exists():
        return 0
    data = json.loads(path.read_text(encoding="utf-8"))
    topics = {t.key: t for t in db.scalars(select(Topic)).all()}
    if not topics:
        return 0
    db.execute(delete(TopicResource))
    existing = {r.key: r for r in db.scalars(select(LearningResource)).all()}
    seen = set()
    count = 0
    for r in data.get("resources", []):
        key = str(r["id"])
        seen.add(key)
        res = existing.get(key) or LearningResource(key=key)
        res.title = r["title"][:300]
        res.resource_type = r.get("type", "article")
        res.source = (r.get("source") or "")[:200]
        res.author = (r.get("author") or None)
        res.url = r["url"]
        res.language = r.get("language", "ru")
        res.summary = r.get("summary", "")
        res.difficulty = r.get("difficulty")
        res.duration_minutes = r.get("duration_minutes")
        res.link_status = r.get("link_status", "unverified")
        res.checked_on = _d(r.get("checked_on"))
        res.access_note = (r.get("access_note") or None)
        if key not in existing:
            db.add(res)
        db.flush()
        rel = r.get("relevance") or {}
        for tk in r.get("topic_keys", []):
            t = topics.get(tk)
            if t is None:
                continue
            db.add(TopicResource(topic_id=t.id, resource_id=res.id, relevance=rel.get(tk, "") if isinstance(rel, dict) else str(rel)))
        count += 1
    for key, res in existing.items():
        if key not in seen:
            db.delete(res)
    db.commit()
    return count


def reset_all(db: Session) -> None:
    for table in reversed(Base.metadata.sorted_tables):
        if table.name != "alembic_version":
            db.execute(table.delete())
    db.commit()
