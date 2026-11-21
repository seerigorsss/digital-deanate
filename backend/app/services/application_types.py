"""Каталог типов заявок, модель статусов и правила переходов.

Конфигурация отделена от кода обработчиков: новый тип справки добавляется описанием полей.
"""
from __future__ import annotations

import re
from datetime import date
from typing import Any

DELIVERY_OPTIONS = [
    {"value": "paper", "label": "Бумажный документ — в деканате"},
    {"value": "electronic", "label": "Электронный документ — в личном кабинете"},
]

APPLICATION_TYPES: list[dict[str, Any]] = [
    {
        "key": "study_certificate",
        "category": "certificate",
        "title": "Справка об обучении",
        "description": "Подтверждает, что вы обучаетесь в университете. Подходит для работы родителей, соцзащиты, банка, визы.",
        "processing_days": 3,
        "icon": "file-check",
        "fields": [
            {"name": "destination", "label": "Куда предоставляется", "type": "text", "required": True, "min_length": 3, "max_length": 200,
             "placeholder": "Например: по месту работы родителей"},
            {"name": "copies", "label": "Количество экземпляров", "type": "number", "required": True, "min": 1, "max": 5, "default": 1},
            {"name": "delivery", "label": "Способ получения", "type": "select", "required": True, "options": DELIVERY_OPTIONS, "default": "paper"},
            {"name": "comment", "label": "Комментарий для деканата", "type": "textarea", "required": False, "max_length": 1000},
        ],
    },
    {
        "key": "scholarship_certificate",
        "category": "certificate",
        "title": "Справка о размере стипендии",
        "description": "Сведения о начисленной стипендии за выбранный период — для соцзащиты, налогового вычета и т.п.",
        "processing_days": 5,
        "icon": "wallet",
        "fields": [
            {"name": "period_from", "label": "Период: с", "type": "date", "required": True},
            {"name": "period_to", "label": "Период: по", "type": "date", "required": True},
            {"name": "delivery", "label": "Способ получения", "type": "select", "required": True, "options": DELIVERY_OPTIONS, "default": "electronic"},
            {"name": "comment", "label": "Комментарий для деканата", "type": "textarea", "required": False, "max_length": 1000},
        ],
    },
    {
        "key": "military_certificate",
        "category": "certificate",
        "title": "Справка для военкомата (форма № 26)",
        "description": "Справка об обучении по форме для военного комиссариата. Выдаётся только в бумажном виде.",
        "processing_days": 5,
        "icon": "shield",
        "fields": [
            {"name": "military_office", "label": "Военный комиссариат", "type": "text", "required": True, "min_length": 3, "max_length": 200,
             "placeholder": "Например: военный комиссариат Басманного района"},
            {"name": "delivery", "label": "Способ получения", "type": "select", "required": True,
             "options": [DELIVERY_OPTIONS[0]], "default": "paper"},
            {"name": "comment", "label": "Комментарий для деканата", "type": "textarea", "required": False, "max_length": 1000},
        ],
    },
    {
        "key": "transcript",
        "category": "certificate",
        "title": "Академическая выписка оценок",
        "description": "Выписка итоговых оценок за завершённые семестры — для стажировок, обмена, перевода.",
        "processing_days": 5,
        "icon": "list",
        "fields": [
            {"name": "scope", "label": "Период", "type": "select", "required": True, "default": "all",
             "options": [{"value": "all", "label": "Все завершённые семестры"}, {"value": "last", "label": "Только последний семестр"}]},
            {"name": "language", "label": "Язык", "type": "select", "required": True, "default": "ru",
             "options": [{"value": "ru", "label": "Русский"}, {"value": "en", "label": "Английский"}]},
            {"name": "delivery", "label": "Способ получения", "type": "select", "required": True, "options": DELIVERY_OPTIONS, "default": "electronic"},
        ],
    },
    {
        "key": "individual_schedule",
        "category": "statement",
        "title": "Заявление на индивидуальный график сдачи",
        "description": "Перенос сроков сдачи работ или аттестации по уважительной причине.",
        "processing_days": 7,
        "icon": "calendar-clock",
        "fields": [
            {"name": "discipline_id", "label": "Дисциплина", "type": "discipline", "required": True},
            {"name": "reason", "label": "Причина", "type": "select", "required": True, "options": [
                {"value": "illness", "label": "Болезнь"},
                {"value": "family", "label": "Семейные обстоятельства"},
                {"value": "competition", "label": "Участие в олимпиаде или соревнованиях"},
                {"value": "other", "label": "Другая уважительная причина"}]},
            {"name": "details", "label": "Опишите ситуацию и какие работы нужно перенести", "type": "textarea", "required": True,
             "min_length": 10, "max_length": 2000},
        ],
    },
    {
        "key": "material_support",
        "category": "statement",
        "title": "Заявление на материальную помощь",
        "description": "Единовременная материальная поддержка студентов в трудной ситуации.",
        "processing_days": 10,
        "icon": "hand-heart",
        "fields": [
            {"name": "reason", "label": "Основание", "type": "select", "required": True, "options": [
                {"value": "difficult_situation", "label": "Трудная жизненная ситуация"},
                {"value": "medical", "label": "Расходы на лечение"},
                {"value": "family", "label": "Рождение ребёнка / семейные обстоятельства"},
                {"value": "other", "label": "Другое"}]},
            {"name": "details", "label": "Кратко опишите ситуацию", "type": "textarea", "required": True, "min_length": 10, "max_length": 2000},
        ],
    },
    {
        "key": "dean_question",
        "category": "question",
        "title": "Обращение в деканат",
        "description": "Вопрос по учебному процессу, расписанию, документам или стипендии. Ответ придёт в карточку обращения.",
        "processing_days": 2,
        "icon": "message-circle",
        "fields": [
            {"name": "topic", "label": "Тема", "type": "select", "required": True, "options": [
                {"value": "study", "label": "Учебный процесс"},
                {"value": "schedule", "label": "Расписание"},
                {"value": "documents", "label": "Документы"},
                {"value": "scholarship", "label": "Стипендия"},
                {"value": "other", "label": "Другое"}]},
            {"name": "subject", "label": "Кратко о вопросе", "type": "text", "required": True, "min_length": 3, "max_length": 150},
            {"name": "message", "label": "Сообщение", "type": "textarea", "required": True, "min_length": 10, "max_length": 3000},
        ],
    },
]

TYPES_BY_KEY = {t["key"]: t for t in APPLICATION_TYPES}

STATUS_LABELS = {
    "draft": "Черновик",
    "submitted": "Отправлена",
    "in_progress": "В обработке",
    "needs_info": "Требуется уточнение",
    "approved": "Одобрена",
    "ready": "Готова к получению",
    "completed": "Завершена",
    "rejected": "Отклонена",
    "withdrawn": "Отозвана",
}
ACTIVE_STATUSES = {"submitted", "in_progress", "needs_info", "approved", "ready"}
FINAL_STATUSES = {"completed", "rejected", "withdrawn"}

# Переходы, доступные сотруднику деканата
STAFF_TRANSITIONS: dict[str, set[str]] = {
    "submitted": {"in_progress", "needs_info", "rejected"},
    "in_progress": {"needs_info", "approved", "ready", "completed", "rejected"},
    "needs_info": {"in_progress", "rejected"},
    "approved": {"ready", "completed"},
    "ready": {"completed"},
}
COMMENT_REQUIRED = {"needs_info", "rejected"}

DEANERY_OFFICE = "ГУК, каб. 245 (окно 3)"
DEANERY_HOURS = "пн–пт 10:00–17:00, обед 13:00–14:00"


def next_step(status: str, type_key: str, payload: dict) -> str:
    t = TYPES_BY_KEY.get(type_key, {})
    category = t.get("category")
    days = t.get("processing_days", 3)
    electronic = payload.get("delivery") == "electronic"
    if status == "draft":
        return "Черновик сохранён. Проверьте данные и нажмите «Отправить» — до этого деканат заявку не видит."
    if status == "submitted":
        return "Заявка передана в деканат. Обычно её берут в работу в течение 1 рабочего дня — статус обновится автоматически."
    if status == "in_progress":
        return f"Сотрудник деканата работает с заявкой. Ориентировочный срок — до {days} рабочих дней."
    if status == "needs_info":
        return "Деканату нужно уточнение. Ответьте в переписке ниже — заявка автоматически вернётся в работу."
    if status == "approved":
        if category == "certificate":
            return "Заявка одобрена, документ готовится. Мы сообщим, когда его можно будет получить."
        return "Заявление одобрено. Подробности решения — в комментарии деканата."
    if status == "ready":
        if electronic:
            return "Электронный документ готов — откройте его в карточке заявки."
        return f"Документ готов. Получите его в деканате: {DEANERY_OFFICE}, {DEANERY_HOURS}. Возьмите студенческий билет или паспорт."
    if status == "completed":
        if category == "question":
            return "Деканат ответил на обращение. Если остались вопросы — создайте новое обращение."
        return "Заявка выполнена и закрыта."
    if status == "rejected":
        return "Заявка отклонена — причина указана в истории. При необходимости подайте новую заявку с исправленными данными."
    if status == "withdrawn":
        return "Вы отозвали заявку. Её можно подать заново в любой момент."
    return ""


_CTRL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]")


def clean_text(value: str) -> str:
    return _CTRL.sub("", value).strip()


def validate_payload(type_key: str, payload: Any, allowed_discipline_ids: set[int], *, partial: bool = False) -> tuple[dict, list[dict]]:
    """Серверная валидация полей заявки по описанию типа. partial=True — для черновика (обязательность не проверяется)."""
    t = TYPES_BY_KEY.get(type_key)
    if t is None:
        return {}, [{"field": "type_key", "message": "Неизвестный тип заявки"}]
    if not isinstance(payload, dict):
        return {}, [{"field": "payload", "message": "Некорректные данные формы"}]
    errors: list[dict] = []
    clean: dict[str, Any] = {}
    known = {f["name"] for f in t["fields"]}
    for extra in set(payload) - known:
        errors.append({"field": extra, "message": "Неизвестное поле"})
    for f in t["fields"]:
        name, ftype = f["name"], f["type"]
        raw = payload.get(name)
        empty = raw is None or (isinstance(raw, str) and raw.strip() == "")
        if empty:
            if f.get("required") and not partial:
                errors.append({"field": name, "message": "Заполните это поле"})
            continue
        if ftype in ("text", "textarea"):
            if not isinstance(raw, str):
                errors.append({"field": name, "message": "Ожидается текст"})
                continue
            v = clean_text(raw)
            if "min_length" in f and len(v) < f["min_length"] and not partial:
                errors.append({"field": name, "message": f"Минимум {f['min_length']} символов"})
                continue
            if "max_length" in f and len(v) > f["max_length"]:
                errors.append({"field": name, "message": f"Максимум {f['max_length']} символов"})
                continue
            clean[name] = v
        elif ftype == "number":
            try:
                v = int(raw)
                if isinstance(raw, bool) or float(raw) != v:
                    raise ValueError
            except (TypeError, ValueError):
                errors.append({"field": name, "message": "Нужно целое число"})
                continue
            if v < f.get("min", v) or v > f.get("max", v):
                errors.append({"field": name, "message": f"Допустимо от {f.get('min')} до {f.get('max')}"})
                continue
            clean[name] = v
        elif ftype == "select":
            values = {o["value"] for o in f["options"]}
            if raw not in values:
                errors.append({"field": name, "message": "Выберите значение из списка"})
                continue
            clean[name] = raw
        elif ftype == "date":
            try:
                v = date.fromisoformat(str(raw))
            except ValueError:
                errors.append({"field": name, "message": "Неверная дата"})
                continue
            if not (date(2000, 1, 1) <= v <= date(2100, 1, 1)):
                errors.append({"field": name, "message": "Неверная дата"})
                continue
            clean[name] = v.isoformat()
        elif ftype == "discipline":
            try:
                v = int(raw)
            except (TypeError, ValueError):
                errors.append({"field": name, "message": "Выберите дисциплину"})
                continue
            if v not in allowed_discipline_ids:  # только свои дисциплины
                errors.append({"field": name, "message": "Выберите дисциплину из списка"})
                continue
            clean[name] = v
    if type_key == "scholarship_certificate" and "period_from" in clean and "period_to" in clean:
        if clean["period_from"] > clean["period_to"]:
            errors.append({"field": "period_to", "message": "Дата окончания раньше даты начала"})
    return clean, errors
