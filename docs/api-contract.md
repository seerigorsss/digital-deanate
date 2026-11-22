# API-контракт (v1)

REST/JSON, префикс `/api`, один домен с SPA (CORS не используется). Реальные ответы на демо-данных
(сегодня = 2026-11-23) лежат в [`docs/api-examples/`](api-examples/) — это эталон структуры для frontend.
Интерактивная схема в режиме разработки: `/api/docs` (OpenAPI).

## Общие правила
- **Аутентификация:** серверная сессия в cookie `dd_session` (HttpOnly, SameSite=Lax, Secure в production).
  Клиент **не видит** токен сессии.
- **CSRF:** все запросы, кроме GET, требуют заголовок `X-CSRF-Token` — значение `csrf_token` из ответа
  `POST /api/auth/login` или `GET /api/auth/me`. Тело — только `application/json`.
- **Изоляция:** ни один студенческий эндпоинт не принимает ID пользователя — данные берутся по сессии.
  ID дисциплин/тем/заявок/уведомлений проверяются на принадлежность; чужой ресурс → **404** (как несуществующий).
- **Роли:** `student` — студенческие эндпоинты; `staff` — `/api/staff/*`. Чужая роль → **403**.
- **Ошибки:** `{"detail": "человекочитаемо", "code": "машинный_код", "errors"?: [{"field", "message"}]}`.
  401 `unauthorized` → показать вход; 403 `csrf_failed` → перезапросить `/api/auth/me` и повторить;
  422 `validation_error` → подсветить поля из `errors`; 409 — недопустимое действие; 429 — лимит попыток входа; 500 — сбой.
- Даты — ISO `YYYY-MM-DD`, время — ISO 8601 с часовым поясом (UTC). Интерфейс показывает время в Europe/Moscow.

## Эндпоинты
| Метод и путь | Роль | Назначение |
|---|---|---|
| POST `/api/auth/login` `{login,password}` | — | вход → `{user, csrf_token}` + cookie |
| POST `/api/auth/logout` | любая | выход (сессия удаляется на сервере) → 204 |
| GET `/api/auth/me` | любая | `{user, csrf_token}` или 401 |
| GET `/api/meta`, `/api/faq`, `/api/health` | — | название вуза, дисклеймер, «сегодня»; FAQ |
| GET `/api/profile` | student | профиль студента |
| GET `/api/dashboard` | student | главная: сегодня, следующее занятие, индекс + приоритет №1, сроки, активные заявки, уведомления |
| GET `/api/schedule?from=&to=` | student | расписание по дням (≤ 42 дней; по умолчанию текущая неделя) |
| GET `/api/disciplines` | student | дисциплины семестра |
| GET `/api/disciplines/{id}` | student | карточка: дисциплина, преподаватели, `analytics` (DisciplineAnalytics), темы с флагом `is_weak` |
| POST `/api/disciplines/{id}/simulate` `{overrides:[{item_id,points}], exam_points?}` | student | «Что если» — пересчёт без сохранения |
| GET `/api/analytics` | student | «Академический радар» (AnalyticsSummary) |
| GET `/api/topics/{id}` | student | тема и учебные материалы |
| GET `/api/grades` | student | сессия текущего семестра + зачётная книжка |
| GET `/api/application-types` | student | каталог типов заявок с описанием полей формы |
| GET `/api/applications?status=all\|active\|closed\|draft` | student | список + счётчики |
| POST `/api/applications` `{type_key,payload,submit}` | student | создать (submit=false → черновик) → 201 |
| GET `/api/applications/{id}` | student | карточка: история, переписка, `next_step`, `permissions` |
| PATCH `/api/applications/{id}` `{payload}` | student | редактировать черновик |
| POST `/api/applications/{id}/submit` \| `/withdraw` | student | отправить черновик \| отозвать отправленную |
| DELETE `/api/applications/{id}` | student | удалить черновик → 204 |
| POST `/api/applications/{id}/messages` `{text}` | student | сообщение в деканат; при «Требуется уточнение» заявка возвращается в «Отправлена» |
| GET `/api/applications/{id}/document` | student | данные электронного документа (только `document_available`) |
| GET `/api/notifications?category=&unread=` | любая | список, `unread_count`, `unread_by_category` |
| POST `/api/notifications/{id}/read`, `/api/notifications/read-all` `{category}` | любая | отметить прочитанным |
| GET `/api/staff/applications?status=` | staff | очередь заявок (без черновиков) |
| GET `/api/staff/applications/{id}` | staff | карточка + `allowed_transitions` |
| POST `/api/staff/applications/{id}/status` `{to_status, comment}` | staff | смена статуса (комментарий обязателен для needs_info/rejected) → уведомление студенту |
| POST `/api/staff/applications/{id}/messages` `{text}` | staff | ответ студенту |
| GET `/api/staff/structure` | staff | факультеты → кафедры → группы с числом студентов (группа может быть пустой) |
| GET `/api/staff/students?group=`, `/api/staff/students/{user_id}/grades` | staff | студенты группы; баллы по работам + риск (только чтение; метода записи баллов нет — их выставляет преподаватель) |
| GET/POST `/api/staff/announcements` `{title,body,audience,importance}` | staff | объявления (audience: `all`, `group:ИУ5-34Б`, `faculty:РК`) |
| GET `/api/staff/groups` | staff | группы и факультеты для выбора аудитории |

## Ключевые перечисления
- Статусы заявки: `draft` Черновик · `submitted` Отправлена · `in_progress` В обработке · `needs_info` Требуется уточнение ·
  `approved` Одобрена · `ready` Готова к получению · `completed` Завершена · `rejected` Отклонена · `withdrawn` Отозвана.
- Поля формы заявки (`fields[].type`): `text`, `textarea`, `number`, `select`, `date`, `discipline` (options — свои дисциплины).
- Статус занятия: `normal`, `cancelled`, `moved_out` (перенесено с этого времени), `moved_in` (перенесено на это время),
  `changed` (аудитория/преподаватель), `added` (доп. занятие); у изменённых — объект `change {type,title,text,reason}`.
- Уровни риска: `critical`, `high`, `medium`, `low`, `stable`, `insufficient_data` — подписи приходят в `risk.label`.
- Категории уведомлений: `announcement`, `deadline`, `schedule`, `application`, `grade`.

Аналитика — см. [`analytics-contract.md`](analytics-contract.md) и [`analytics-model.md`](analytics-model.md).
