# Контракт модуля академической аналитики (v1)

Источник правил — ТЗ §14–§18. Этот документ фиксирует **интерфейс** доменного модуля,
чтобы backend и frontend работали параллельно. Пороги и коэффициенты — стартовые
значения конфигурации; их можно менять в `config.py`, не трогая код.

Пакет: `backend/app/domain/analytics/` — **чистый Python** (без БД, FastAPI, ORM, сети).
Вход — неизменяемые dataclass-структуры, выход — dataclass-структуры с методом
`to_dict()` (JSON-сериализуемые: числа, строки, bool, None, list, dict; даты — ISO-строки).

## 1. Входные данные

```python
AssessmentType = Literal["credit", "distributed_exam", "exam"]   # A, B, C из ТЗ
ModuleStatus   = Literal["completed", "in_progress", "upcoming"]

@dataclass(frozen=True)
class ItemInput:                 # вид работы внутри модуля (ДЗ, ЛР, РК, тест, проект)
    id: int
    title: str
    kind: str                    # homework | lab | control | test | project | activity
    max_points: float
    due_date: date | None
    points: float | None         # None = результата в системе нет

@dataclass(frozen=True)
class ModuleInput:
    id: int
    ordinal: int
    title: str
    status: ModuleStatus
    ends_on: date | None         # срок закрытия модуля
    items: tuple[ItemInput, ...]
    topic_ids: tuple[int, ...] = ()

@dataclass(frozen=True)
class AssessmentConfig:
    assessment_type: AssessmentType
    semester_points_max: float           # 100 (A, B) или 70 (C)
    passing_threshold: float             # 60
    exam_points_min: float | None = None # 18 (только C)
    exam_points_max: float | None = None # 30 (только C)
    grade_bands: tuple[GradeBand, ...] | None = None  # переопределение шкалы для дисциплины

@dataclass(frozen=True)
class DisciplineInput:
    discipline_id: int
    title: str
    config: AssessmentConfig
    modules: tuple[ModuleInput, ...]
    exam_points: float | None            # результат экзамена (C), None — не сдавал
    today: date
    semester_progress: float | None      # 0..1 — доля прошедшего учебного периода; None — неизвестно
```

### Семантика результатов (важно)
| Ситуация | Трактовка |
|---|---|
| `points` задан | баллы фактически набраны, работа закрыта |
| `points is None`, модуль **не** `completed` | работа впереди → входит в **оставшийся потенциал** |
| `points is None`, модуль `completed` | **данных нет** (баллы не внесены) — не ноль и не потенциал; снижает полноту данных |

## 2. Базовые величины (для каждой дисциплины)
- `current_semester_points` = Σ points по всем работам с результатом.
- `graded_points_max` = Σ max_points работ с результатом.
- `completed_points_max` = Σ max_points работ модулей в статусе `completed`.
- `remaining_points_max` = Σ max_points работ без результата в незавершённых модулях. При всех завершённых модулях = 0.
- `missing_points_max` = Σ max_points работ без результата в завершённых модулях.
- `max_achievable_semester` = current + remaining.
- `current_pace` = current / graded_points_max (если graded_points_max > 0, иначе None).
- `pace_is_reliable` = graded_points_max ≥ `min_evidence_share` · semester_points_max.
- Валидация: points ∈ [0, max_points], exam_points ∈ [0, exam_points_max]. Сумма max работ должна равняться semester_points_max; если нет — в `data_issues` и полнота `partial`.

## 3. Целевой семестровый уровень S (для риска «не сдать»)
- **A (зачёт), B (распределённый экзамен):** S = passing_threshold (60). Порог «невозможно» F = S.
- **C (экзамен):** S = passing_threshold − exam_points_min = 42 (при минимальных 18 на экзамене итог ≥ 60);
  F = passing_threshold − exam_points_max = 30 (ниже — не сдать даже с 30 на экзамене).

## 4. Уровни риска (`critical | high | medium | low | stable | insufficient_data`)
Порядок проверок (первое совпадение):
1. **insufficient_data** — нет модулей/работ; или ничего не оценено (`graded_points_max == 0`);
   или `missing_points_max > insufficient_missing_share · completed_points_max` (по умолчанию 0.5).
2. **C, экзамен сдан:** exam < 18 → `critical` («экзамен ниже обязательного минимума»); иначе итог = sem + exam:
   ≥ 60 → `stable` (pass_status=`passed`), < 60 → `critical` (`failed`).
3. **current ≥ S** → `stable` (pass_status=`secured`; для C — с пометкой, что на экзамене всё равно нужно ≥ 18).
4. **max_achievable_semester < F** → `critical` (pass_status=`unreachable`).
5. **C и max_achievable_semester < S** → `high` (сдать можно только с экзаменом выше минимума; показать нужный балл).
6. Иначе D = S − current (дефицит), R = remaining, r = D / R (доля остатка, которую нужно набрать):
   - если R == 0 → `critical` (A/B) — уже покрыто п.4, оставить защиту;
   - `r ≥ high_share (0.9)` → `high` («нужен почти весь остаток»);
   - если `pace_is_reliable`: `r − current_pace ≥ pace_gap_high (0.25)` → `high` («темп нужно резко повысить»);
   - `r ≥ medium_share (0.7)` или (`pace_is_reliable` и `r − current_pace ≥ pace_gap_medium (0.1)`) → `medium`;
   - если `pace_is_reliable` и проекция `current + current_pace·R ≥ S + stable_margin·semester_points_max` (0.1) и `r ≤ stable_max_share (0.5)` → `stable`;
   - иначе → `low`.
   Ранний семестр с ненадёжным темпом оценивается **только по доле остатка** — поэтому низкий балл
   при большом остатке не даёт `critical` (ТЗ §18 п.6).

Каждый уровень сопровождается списком `reasons` (1–3 человекочитаемые фразы на русском, с числами).
Уровень — эвристика, **не вероятность**. Слова «вероятность сдачи» не использовать.

## 5. Цели по оценкам (`targets`)
- A: одна цель — 60 («Зачёт»).
- B: 60, 71, 85 (из шкалы). C: 60, 71, 85 по итогу = семестр + экзамен.
- Для каждой: `status` ∈ `reached | achievable | unreachable | unknown`, `points_needed_semester`,
  `required_share_of_remaining` (или None), для C — `exam_points_needed`, `extra_semester_points_needed`, текст `explanation`.
- **C, правило ТЗ §15.5:** need = T − current. `exam_points_needed = max(18, need)` если need ≤ 30.
  Если need > 30: при текущих баллах цель недостижима; `extra_semester_points_needed = T − 30 − current`;
  если extra ≤ remaining → `achievable` («нужно добрать X баллов в семестре и сдать экзамен на 30»), иначе `unreachable`.
  Всегда отдавать `total_at_exam_min = current + 18`, `total_at_exam_max = current + 30` (в блоке `exam`).
- Шкала (по умолчанию): 0–59 неуд., 60–70 удовл., 71–84 хорошо, 85–100 отлично. Граница 60 — допущение (см. `docs/assumptions.md`).

## 6. Выход `DisciplineAnalytics.to_dict()`
```jsonc
{
  "discipline_id": 1, "title": "...",
  "assessment_type": "exam", "assessment_type_label": "Экзамен",
  "current_semester_points": 42.0, "semester_points_max": 70.0,
  "completed_points_max": 50.0, "graded_points_max": 50.0,
  "remaining_points_max": 20.0, "missing_points_max": 0.0,
  "max_achievable_semester": 62.0,
  "passing_threshold": 60.0, "semester_target": 42.0,
  "semester_progress": 0.72,
  "data_completeness": "full",            // full | partial | insufficient
  "data_issues": [],
  "current_pace": 0.84, "pace_is_reliable": true,
  "projected_semester_points": 58.8,      // null, если темп ненадёжен; это ориентир, не прогноз
  "required_share_of_remaining": 0.0,
  "pass_status": "secured",               // secured | achievable | unreachable | passed | failed | unknown
  "risk": {"level": "stable", "label": "Стабильно", "reasons": ["..."]},
  "current_grade": {"key": "satisfactory", "label": "Удовлетворительно"} ,   // для B — по текущей сумме; иначе null
  "exam": {                               // только C, иначе null
    "points_min": 18, "points_max": 30, "result": null, "passed": null,
    "required_for_pass": 18, "total_at_exam_min": 60, "total_at_exam_max": 72
  },
  "targets": [{"threshold": 60, "grade_key": "satisfactory", "label": "Удовлетворительно",
               "status": "reached", "points_needed_semester": 0, "required_share_of_remaining": null,
               "exam_points_needed": 18, "extra_semester_points_needed": 0, "explanation": "..."}],
  "modules": [{"id": 1, "ordinal": 1, "title": "...", "status": "completed", "ends_on": "2026-10-11",
               "points": 22, "max_points": 25, "graded_max": 25, "remaining": 0, "missing": 0,
               "share": 0.88, "items": [{"id":1,"title":"...","kind":"homework","max_points":10,
               "points":9,"due_date":"2026-09-28","state":"graded"}]}],   // state: graded | pending | missing
  "next_actions": [{"item_id": 7, "title": "Домашнее задание 3", "module_title": "Ряды",
                    "max_points": 8, "due_date": "2026-12-03", "days_left": 12, "overdue": false}],
  "weak_topic_ids": [3, 4],              // темы модулей с долей < weak_module_share (0.6)
  "explanation": "Человекочитаемое резюме 1–3 предложения",
  "recommendation": "Конкретное следующее действие на основе next_actions"
}
```

## 7. Сводка `AnalyticsSummary.to_dict()` (экран «Академический радар»)
```jsonc
{
  "index": {"value": 72, "max": 100, "zone": "medium", "label": "Требует внимания",
            "is_estimate": true, "formula": "описание формулы", "caps_applied": ["critical"]},
  "zone_counts": {"critical":0,"high":1,"medium":1,"low":2,"stable":3,"insufficient_data":1},
  "explanation": "В целом ситуация стабильная, но по двум дисциплинам запас баллов небольшой...",
  "priorities": [{"discipline_id": 5, "title": "...", "risk_level": "medium", "reason": "...",
                  "action": "...", "points_target": "...", "deadline": "2026-11-26", "score": 123.0}],
  "positives":  [{"discipline_id": 1, "title": "...", "message": "..."}],
  "disciplines": [ /* DisciplineAnalytics, отсортированы по убыванию риска */ ]
}
```
- **Индекс учебной устойчивости** (ориентировочный, не вероятность): среднее баллов зон по дисциплинам
  с известным риском, веса равные: stable 100, low 80, medium 60, high 35, critical 10.
  Ограничения сверху: есть `critical` → не выше 59; есть `high` → не выше 74 (одна критическая дисциплина
  не прячется за зелёными). Если все `insufficient_data` → value = null.
  Зоны индекса: ≥ 80 stable «Стабильно», 65–79 medium «Требует внимания», 50–64 high «Высокий риск», < 50 critical «Критично».
- **Приоритеты** — дисциплины с риском critical/high/medium/low (stable — нет). Score = вес риска
  (critical 1000, high 700, medium 400, low 100) + срочность (до 100 баллов: чем ближе ближайший срок, тем больше;
  срок ≤ 3 дней — максимум) + достижимость (если улучшение возможно в рамках остатка: +50).
  Сроки и задания брать **только** из `next_actions` (без выдумывания).
  Для `critical` с недостижимым порогом рекомендация — обратиться к преподавателю / в деканат
  (обсудить пересдачу или индивидуальный график); не обещать результат.
- **Позитивные результаты** — дисциплины `stable` (и `low` с проекцией выше порога), которых нет в приоритетах (правка по QA-07).

## 8. Конфигурация (`config.py`)
Все параметры выше (шкала, пороги типов, коэффициенты риска, веса и зоны индекса, веса приоритизации,
`weak_module_share`) — в одном месте, с комментариями. UI-компоненты и API формул не содержат.

## 9. Тесты (`backend/tests/domain/`)
Минимум — все 12 случаев ТЗ §18 плюс: пересчёт после изменения баллов; валидация диапазонов;
C со сданным экзаменом (≥18 и <18); недостижимая цель 85 для C; приоритеты с дедлайнами.
