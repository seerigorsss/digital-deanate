# Модель данных

Схема создаётся миграцией `backend/migrations/versions/0001_initial_schema.py` (Alembic). ORM — `backend/app/models.py`.

## Сущности и связи
```
users ─┬─1:1─ student_profiles            (ФИО, факультет, направление, курс, группа, № зачётки — вымышленные)
       ├─1:1─ staff_profiles
       ├─1:N─ auth_sessions               (id = SHA-256 токена, csrf_token, срок, последняя активность)
       ├─1:N─ enrollments ──N:1── disciplines
       │        ├─1:N─ item_results ──N:1── assessment_items   (фактические баллы за работы)
       │        └─1:1─ exam_results                             (экзамен, тип C)
       ├─1:N─ record_book_entries         (итоги прошлых семестров)
       ├─1:N─ applications ─┬─1:N─ application_status_history
       │                    └─1:N─ application_messages
       └─1:N─ notifications               (уникальность user_id + source_key)

academic_periods ─1:N─ disciplines ─1:1─ assessment_configurations  (тип A/B/C, максимумы, пороги, дата экзамена)
                                    ├─1:N─ modules ─1:N─ assessment_items   (виды работ: max_points, due_date)
                                    └─1:N─ topics ─N:M─ learning_resources  (через topic_resources + relevance)
teachers ─1:N─ disciplines (лектор), lesson_templates, schedule_changes
lesson_templates (группа, день недели, пара, тип, аудитория, преподаватель, числитель/знаменатель)
schedule_changes (дата, тип: cancelled | moved | room | teacher | added, новые параметры, причина)
announcements    (объявления деканата → рассылаются в notifications)
```

## Соответствие сущностям из роли архитектора
| Сущность (роль 02) | Таблица |
|---|---|
| User / StudentProfile | `users`, `student_profiles` (+ `staff_profiles`) |
| Discipline / Enrollment / AcademicPeriod | `disciplines`, `enrollments`, `academic_periods` |
| AssessmentConfiguration | `assessment_configurations` |
| Module / ModuleResult | `modules` + `assessment_items` (работы внутри модуля), `item_results` |
| ExamResult | `exam_results` |
| GradeThreshold | конфигурация `DEFAULT_GRADE_BANDS` + переопределение `assessment_configurations.grade_bands` |
| Application / ApplicationStatusHistory | `applications`, `application_status_history` (+ `application_messages`) |
| Notification | `notifications` (+ `announcements`) |
| Topic / LearningResource | `topics`, `learning_resources`, `topic_resources` |

## Поля аналитики (ТЗ §15.6)
| Смысл | Источник |
|---|---|
| `assessment_type`, `semester_points_max`, `exam_points_min/max`, `passing_threshold` | `assessment_configurations` |
| `target_grade_thresholds` | шкала из конфигурации / переопределение дисциплины |
| `modules` (факт, максимум, статус) | `modules` + `assessment_items` + `item_results` |
| `current_semester_points`, `completed_points_max`, `remaining_points_max` | вычисляются в `domain/analytics/metrics.py` |
| `semester_progress` | доля прошедших дней `academic_periods` |

## Семантика «нет результата»
Запись в `item_results` есть → балл выставлен. Записи нет и модуль не завершён → работа впереди (оставшийся потенциал).
Записи нет, а модуль завершён → **данных нет** (не ноль). См. `docs/assumptions.md` (A3).

## Начальные данные
`backend/app/seed/`: `data/curriculum.json` (учебный план: 14 дисциплин, 38 модулей, 92 вида работ, 63 темы, 18 преподавателей),
`data/demo_results.json` (баллы), `demo_data.py` (профили, расписание и изменения, зачётки, заявки, объявления),
`data/learning_resources.json` (каталог проверенных материалов). Пустая БД заполняется при старте;
вручную: `python -m app.seed` или `python -m app.seed --reset`. Все данные вымышлены.
