"""Адаптер «БД → доменная аналитика». Формулы живут только в app.domain.analytics."""
from __future__ import annotations

from datetime import date

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..errors import not_found
from ..models import AcademicPeriod, Discipline, Enrollment, Module, Topic
from ..domain import analytics as an

ASSESSMENT_LABELS = {"credit": "Зачёт", "distributed_exam": "Распределённый экзамен", "exam": "Экзамен"}


def current_period(db: Session) -> AcademicPeriod:
    p = db.scalar(select(AcademicPeriod).where(AcademicPeriod.is_current.is_(True)))
    if p is None:
        raise not_found("Учебный период не настроен")
    return p


def semester_progress(period: AcademicPeriod, today: date) -> float:
    total = (period.ends_on - period.starts_on).days
    if total <= 0:
        return 1.0
    return max(0.0, min(1.0, (today - period.starts_on).days / total))


def student_enrollments(db: Session, user_id: int) -> list[Enrollment]:
    return list(
        db.scalars(
            select(Enrollment)
            .options(
                selectinload(Enrollment.discipline).selectinload(Discipline.assessment),
                selectinload(Enrollment.discipline).selectinload(Discipline.lecturer),
                selectinload(Enrollment.discipline).selectinload(Discipline.modules).selectinload(Module.items),
                selectinload(Enrollment.discipline).selectinload(Discipline.topics),
                selectinload(Enrollment.results),
                selectinload(Enrollment.exam_result),
            )
            .where(Enrollment.student_id == user_id)
            .order_by(Enrollment.id)
        ).all()
    )


def get_enrollment(db: Session, user_id: int, discipline_id: int) -> Enrollment:
    """Единственная точка доступа к данным дисциплины студента: фильтр по владельцу на уровне SQL."""
    enr = next((e for e in student_enrollments(db, user_id) if e.discipline_id == discipline_id), None)
    if enr is None:
        raise not_found("Дисциплина не найдена")
    return enr


def build_input(enr: Enrollment, today: date, progress: float | None, overrides: dict[int, float] | None = None) -> an.DisciplineInput:
    d = enr.discipline
    cfg = d.assessment
    results = {r.item_id: r.points for r in enr.results}
    if overrides:
        results = {**results, **overrides}
    topics_by_module: dict[int, list[int]] = {}
    for t in d.topics:
        if t.module_id:
            topics_by_module.setdefault(t.module_id, []).append(t.id)
    modules = tuple(
        an.ModuleInput(
            id=m.id,
            ordinal=m.ordinal,
            title=m.title,
            status=m.status,
            ends_on=m.ends_on,
            items=tuple(
                an.ItemInput(
                    id=i.id, title=i.title, kind=i.kind, max_points=float(i.max_points),
                    due_date=i.due_date, points=(float(results[i.id]) if i.id in results else None),
                )
                for i in m.items
            ),
            topic_ids=tuple(topics_by_module.get(m.id, [])),
        )
        for m in d.modules
    )
    config = an.AssessmentConfig(
        assessment_type=cfg.assessment_type,
        semester_points_max=float(cfg.semester_points_max),
        passing_threshold=float(cfg.passing_threshold),
        exam_points_min=cfg.exam_points_min,
        exam_points_max=cfg.exam_points_max,
    )
    return an.DisciplineInput(
        discipline_id=d.id,
        title=d.title,
        config=config,
        modules=modules,
        exam_points=(float(enr.exam_result.points) if enr.exam_result else None),
        today=today,
        semester_progress=progress,
    )


def analyze_enrollment(enr: Enrollment, period: AcademicPeriod, today: date, overrides: dict[int, float] | None = None) -> dict:
    res = an.analyze_discipline(build_input(enr, today, semester_progress(period, today), overrides))
    return res.to_dict()


def student_summary(db: Session, user_id: int, today: date) -> dict:
    period = current_period(db)
    progress = semester_progress(period, today)
    results = [an.analyze_discipline(build_input(e, today, progress)) for e in student_enrollments(db, user_id)]
    return an.summarize(results, today).to_dict()


def topics_with_flags(enr: Enrollment, analytics: dict) -> list[dict]:
    weak = set(analytics.get("weak_topic_ids") or [])
    modules = {m.id: m for m in enr.discipline.modules}
    out = []
    for t in enr.discipline.topics:
        m = modules.get(t.module_id) if t.module_id else None
        out.append({
            "id": t.id,
            "title": t.title,
            "module_id": t.module_id,
            "module_title": m.title if m else None,
            "module_ordinal": m.ordinal if m else None,
            "is_weak": t.id in weak,
            "resources_count": len(t.links),
        })
    return out


def topic_for_student(db: Session, user_id: int, topic_id: int) -> tuple[Topic, Enrollment]:
    topic = db.get(Topic, topic_id)
    if topic is None:
        raise not_found("Тема не найдена")
    enr = db.scalar(select(Enrollment).where(Enrollment.student_id == user_id, Enrollment.discipline_id == topic.discipline_id))
    if enr is None:  # тема чужой дисциплины — недоступна
        raise not_found("Тема не найдена")
    return topic, enr
