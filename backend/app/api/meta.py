from __future__ import annotations

import hashlib
from datetime import date

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from ..config import get_settings, today_local
from ..db import get_db
from ..errors import not_found
from ..models import StudentProfile
from ..security.deps import Principal, require_student
from .applications import own_application

router = APIRouter(prefix="/api", tags=["meta"])

DISCLAIMER = ("Концепт, созданный для конкурса «Цифровой деканат будущего». Не является официальным сервисом университета. "
              "Все персональные данные, оценки и документы вымышлены.")

FAQ = [
    {"id": "certificate", "category": "Документы", "question": "Как получить справку об обучении?",
     "answer": "Откройте «Заявки» → «Новая заявка» → «Справка об обучении». Укажите, куда нужна справка, и способ получения. "
               "Когда статус сменится на «Готова к получению», заберите бумажную справку в деканате или откройте электронную в карточке заявки.",
     "link": "/applications/new?type=study_certificate"},
    {"id": "status", "category": "Документы", "question": "Что означают статусы заявки?",
     "answer": "«Отправлена» — деканат получил заявку; «В обработке» — сотрудник работает с ней; «Требуется уточнение» — нужно ответить "
               "в переписке; «Готова к получению» — документ можно забрать; «Завершена» — заявка закрыта. Под статусом в карточке "
               "всегда написано, что делать дальше.", "link": "/applications"},
    {"id": "index", "category": "Успеваемость", "question": "Что такое индекс учебной устойчивости?",
     "answer": "Это ориентировочный сводный показатель от 0 до 100: он учитывает уровень риска по каждой дисциплине с равными весами. "
               "Если есть хотя бы одна дисциплина в критической зоне, индекс не может быть высоким. Это не вероятность сдачи и не официальная оценка.",
     "link": "/study"},
    {"id": "exam18", "category": "Успеваемость", "question": "Зачем на экзамене минимум 18 баллов?",
     "answer": "Для дисциплин с отдельным экзаменом итог — сумма семестровых (до 70) и экзаменационных (до 30) баллов. "
               "Экзамен считается сданным только при 18 баллах и больше, даже если сумма формально достигает 60.", "link": "/study"},
    {"id": "points", "category": "Успеваемость", "question": "Почему баллы за модуль не отображаются?",
     "answer": "Значит, преподаватель ещё не внёс их в систему. В этом случае аналитика честно пишет «Недостаточно данных» и не строит прогноз. "
               "Если срок внесения прошёл давно, напишите в деканат через «Обращение в деканат».", "link": "/applications/new?type=dean_question"},
    {"id": "schedule", "category": "Расписание", "question": "Где увидеть изменения в расписании?",
     "answer": "Отмены, переносы и замены выделены в расписании цветом и подписью, а также приходят в «Уведомления» за неделю до даты.",
     "link": "/schedule"},
    {"id": "parity", "category": "Расписание", "question": "Что такое числитель и знаменатель?",
     "answer": "Учебные недели чередуются: нечётные — числитель, чётные — знаменатель. Некоторые занятия идут только по одной из них. "
               "Тип текущей недели показан в шапке расписания.", "link": "/schedule"},
    {"id": "deanery", "category": "Деканат", "question": "Как связаться с деканатом?",
     "answer": "Создайте «Обращение в деканат» — ответ придёт в карточку обращения и в уведомления. Очный приём: ГУК, каб. 245, "
               "пн–пт 10:00–17:00 (данные вымышлены).", "link": "/applications/new?type=dean_question"},
    {"id": "materials", "category": "Учёба", "question": "Откуда берутся учебные материалы по темам?",
     "answer": "Это каталог открытых материалов, подобранных под конкретные темы дисциплин. Каждая ссылка проверена вручную, "
               "у материала указано, почему он рекомендован. Если подходящих материалов нет, сервис так и пишет.", "link": "/study"},
]


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/meta")
def meta():
    s = get_settings()
    return {"app_name": "Цифровой деканат", "university_name": s.university_name, "disclaimer": DISCLAIMER,
            "today": today_local().isoformat(), "version": "1.0.0"}


@router.get("/faq")
def faq():
    return {"items": FAQ}


@router.get("/applications/{app_id}/document")
def electronic_document(app_id: int, p: Principal = Depends(require_student), db: Session = Depends(get_db)):
    """Данные электронного документа (только для своих заявок с электронной выдачей в статусе «Готова»/«Завершена»)."""
    a = own_application(db, p.id, app_id)
    if not (a.status in ("ready", "completed") and a.payload.get("delivery") == "electronic"):
        raise not_found("Электронный документ недоступен")
    sp = db.query(StudentProfile).filter(StudentProfile.user_id == p.id).one()
    issued = next((h.created_at.date() for h in reversed(a.history) if h.to_status == "ready"), today_local())
    code = hashlib.sha256(f"{a.id}:{a.number}:{sp.record_book_number}".encode()).hexdigest()[:12].upper()
    from ..services.application_types import TYPES_BY_KEY

    return {
        "title": TYPES_BY_KEY[a.type_key]["title"],
        "number": a.number,
        "issued_on": issued.isoformat() if isinstance(issued, date) else str(issued),
        "university": get_settings().university_name,
        "student": {"full_name": sp.full_name, "course": sp.course, "group": sp.group_name,
                    "faculty": sp.faculty_name, "program": f"{sp.program_code} {sp.program_name}",
                    "study_form": sp.study_form, "funding": sp.funding, "record_book_number": sp.record_book_number},
        "payload": a.payload,
        "verification_code": f"{code[:4]}-{code[4:8]}-{code[8:]}",
        "watermark": "ОБРАЗЕЦ · КОНЦЕПТ ДЛЯ КОНКУРСА · НЕ ЯВЛЯЕТСЯ ДОКУМЕНТОМ",
    }
