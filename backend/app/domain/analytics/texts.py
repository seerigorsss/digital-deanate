"""Русские тексты аналитики: причины, объяснения, рекомендации.

Все фразы строятся по шаблонам ТОЛЬКО из вычисленных данных: баллов, порогов,
работ и сроков из учебного плана. Модуль не придумывает задания и сроки и не
обещает результат. Тон — объективный и поддерживающий. Уровень риска и индекс
не называются вероятностью.
"""

from __future__ import annotations

import math
from datetime import date
from typing import TYPE_CHECKING, Iterable, Mapping, Sequence

from .types import DisciplineAnalytics, ModuleAnalytics, NextAction, TargetAnalytics

if TYPE_CHECKING:  # pragma: no cover
    from .config import AnalyticsConfig
    from .metrics import DisciplineFacts
    from .risk import RiskDecision

# --------------------------------------------------------------------------- #
# Подписи
# --------------------------------------------------------------------------- #

RISK_LABELS: Mapping[str, str] = {
    "critical": "Критический риск",
    "high": "Высокий риск",
    "medium": "Средний риск",
    "low": "Низкий риск",
    "stable": "Стабильно",
    "insufficient_data": "Недостаточно данных",
}

#: Подписи для перечисления числа дисциплин по зонам.
RISK_COUNT_LABELS: Mapping[str, str] = {
    "critical": "критический риск",
    "high": "высокий риск",
    "medium": "средний риск",
    "low": "низкий риск",
    "stable": "стабильно",
    "insufficient_data": "недостаточно данных",
}

ASSESSMENT_TYPE_LABELS: Mapping[str, str] = {
    "credit": "Зачёт",
    "distributed_exam": "Распределённый экзамен",
    "exam": "Экзамен",
}

CREDIT_TARGET_KEY = "credit"
CREDIT_TARGET_LABEL = "Зачёт"
INSUFFICIENT_INDEX_LABEL = "Недостаточно данных"

_MONTHS_GEN = (
    "января", "февраля", "марта", "апреля", "мая", "июня",
    "июля", "августа", "сентября", "октября", "ноября", "декабря",
)

# --------------------------------------------------------------------------- #
# Форматирование чисел, дат, склонений
# --------------------------------------------------------------------------- #


def fmt_num(value: float) -> str:
    """42 → «42», 42.5 → «42,5», 41.999999 → «42»."""
    rounded = round(float(value), 2)
    if rounded == 0:
        rounded = 0.0
    if rounded == int(rounded):
        return str(int(rounded))
    return f"{rounded:.2f}".rstrip("0").rstrip(".").replace(".", ",")


def fmt_pct(share: float) -> str:
    """0.667 → «67%» (округление половины вверх, без банковского округления)."""
    return f"{math.floor(share * 100 + 0.5)}%"


def fmt_approx(value: float) -> str:
    """Ориентир по темпу — целым числом, чтобы не создавать ложной точности."""
    return str(math.floor(value + 0.5))


def plural(n: int, one: str, few: str, many: str) -> str:
    n = abs(n)
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def _is_whole(value: float) -> bool:
    return round(value, 2) == int(round(value, 2))


def pts(value: float) -> str:
    """Именительный/винительный падеж: «1 балл», «3 балла», «16 баллов», «2,5 балла»."""
    if not _is_whole(value):
        return f"{fmt_num(value)} балла"
    return f"{fmt_num(value)} {plural(int(round(value)), 'балл', 'балла', 'баллов')}"


def pts_gen(value: float) -> str:
    """Родительный падеж: «до 21 балла», «не меньше 18 баллов», «до 2,5 балла»."""
    if not _is_whole(value):
        return f"{fmt_num(value)} балла"
    n = int(round(value))
    word = "балла" if n % 10 == 1 and n % 100 != 11 else "баллов"
    return f"{fmt_num(value)} {word}"


def fmt_date(value: date) -> str:
    return f"{value.day} {_MONTHS_GEN[value.month - 1]}"


def disciplines_count(n: int) -> str:
    return f"{n} {plural(n, 'дисциплина', 'дисциплины', 'дисциплин')}"


def works_count(n: int) -> str:
    return f"{n} {plural(n, 'работу', 'работы', 'работ')}"


def _quoted_list(titles: Sequence[str], limit: int = 3) -> str:
    shown = [f"«{t}»" for t in titles[:limit]]
    rest = len(titles) - len(shown)
    text = ", ".join(shown)
    if rest > 0:
        text += f" и ещё {rest}"
    return text


def deadline_phrase(action: NextAction) -> str:
    if action.due_date is None:
        return "срок не указан"
    if action.overdue:
        return f"срок был {fmt_date(action.due_date)} — уточните у преподавателя, можно ли сдать"
    if action.days_left == 0:
        return f"срок — сегодня, {fmt_date(action.due_date)}"
    if action.days_left == 1:
        return f"срок — завтра, {fmt_date(action.due_date)}"
    return f"срок — {fmt_date(action.due_date)}"


def action_phrase(action: NextAction) -> str:
    return (
        f"«{action.title}» (модуль «{action.module_title}», до {pts_gen(action.max_points)}, "
        f"{deadline_phrase(action)})"
    )


def _weakest_module(modules: Iterable[ModuleAnalytics]) -> ModuleAnalytics | None:
    weak = [m for m in modules if m.is_weak and m.share is not None]
    if not weak:
        return None
    return min(weak, key=lambda m: (m.share, m.ordinal, m.id))


def _goal_phrase(assessment_type: str, passing: float, target: float, exam_min: float | None,
                 short: bool) -> str:
    """Как назвать семестровую цель S в тексте (родительный падеж: «для …», «до …»)."""
    if assessment_type == "credit":
        return f"зачётного минимума {fmt_num(passing)}"
    if assessment_type == "exam":
        if short:
            return f"семестровых {fmt_num(target)}"
        return (
            f"семестровых {fmt_num(target)} (с минимальными {fmt_num(exam_min or 0)} "
            f"на экзамене это итог {fmt_num(passing)})"
        )
    return f"порога {fmt_num(passing)}"


def _semester_goal(f: "DisciplineFacts", short: bool = False) -> str:
    return _goal_phrase(f.assessment_type, f.passing, f.semester_target, f.exam_min, short)


# --------------------------------------------------------------------------- #
# Проблемы с данными
# --------------------------------------------------------------------------- #


def data_issues(f: "DisciplineFacts") -> list[str]:
    issues: list[str] = []
    if not f.has_items:
        issues.append("В учебном плане дисциплины нет модулей или работ.")
    if f.sum_mismatch:
        issues.append(
            f"Сумма максимумов работ ({fmt_num(f.items_total_max)}) не совпадает с максимумом "
            f"семестровой части ({fmt_num(f.semester_max)}) — расчёты ведутся по фактическим работам."
        )
    if f.missing > 0:
        issues.append(
            f"Нет баллов за {works_count(len(f.missing_titles))} завершённых модулей "
            f"(до {pts_gen(f.missing)}): {_quoted_list(f.missing_titles)}."
        )
    if not f.progress_known:
        issues.append(
            "Этап семестра неизвестен — ориентир по текущему темпу не строится, "
            "показаны только фактические баллы и оставшийся максимум."
        )
    return issues


# --------------------------------------------------------------------------- #
# Причины уровня риска (1–3 фразы)
# --------------------------------------------------------------------------- #


def risk_reasons(f: "DisciplineFacts", d: "RiskDecision") -> tuple[str, ...]:
    rule = d.rule
    reasons: list[str] = []
    exam_min = f.exam_min or 0.0
    exam_max = f.exam_max or 0.0

    if rule == "no_items":
        reasons.append("В учебном плане пока нет модулей или работ — оценивать риск не по чему.")
    elif rule == "no_graded":
        reasons.append("Оценённых работ пока нет — уровень риска появится после первых результатов.")
        if f.missing > 0:
            reasons.append(
                f"По завершённым модулям не внесены баллы за {works_count(len(f.missing_titles))}."
            )
    elif rule == "missing_data":
        reasons.append(
            f"По завершённым модулям не внесены баллы за {works_count(len(f.missing_titles))} "
            f"на {fmt_num(f.missing)} из {pts_gen(f.completed_max)} — данных недостаточно для оценки."
        )
        reasons.append("Если работы сданы, стоит уточнить у преподавателя, внесены ли результаты.")
    elif rule == "exam_below_minimum":
        exam = f.exam_points or 0.0
        total = f.current + exam
        reasons.append(
            f"Экзамен сдан на {pts(exam)} — это ниже обязательного минимума {fmt_num(exam_min)}."
        )
        if total >= f.passing:
            reasons.append(
                f"Сумма {fmt_num(total)} формально не ниже порога {fmt_num(f.passing)}, но без "
                "минимума на экзамене дисциплина не считается сданной."
            )
    elif rule == "exam_passed":
        exam = f.exam_points or 0.0
        reasons.append(
            f"Экзамен сдан на {pts(exam)} (минимум {fmt_num(exam_min)} выполнен), "
            f"итог — {fmt_num(f.current + exam)} из {fmt_num(f.semester_max + exam_max)}."
        )
    elif rule == "exam_total_below_threshold":
        exam = f.exam_points or 0.0
        reasons.append(
            f"Экзамен сдан на {pts(exam)}, но итог {fmt_num(f.current + exam)} "
            f"ниже порога {fmt_num(f.passing)}."
        )
    elif rule == "semester_secured":
        if f.is_exam:
            reasons.append(
                f"В семестре набрано {pts(f.current)}: при минимальных {fmt_num(exam_min)} на экзамене "
                f"итог составит {fmt_num(f.current + exam_min)} — не ниже порога {fmt_num(f.passing)}."
            )
            reasons.append(
                f"На экзамене всё равно нужно набрать не меньше {pts_gen(exam_min)} — "
                "это обязательное условие."
            )
        elif f.assessment_type == "credit":
            reasons.append(
                f"Зачётный минимум по баллам набран: {fmt_num(f.current)} при пороге {fmt_num(f.passing)}."
            )
        else:
            reasons.append(
                f"Набрано {pts(f.current)} — порог {fmt_num(f.passing)} уже достигнут."
            )
    elif rule == "unreachable":
        if f.is_exam:
            reasons.append(
                f"Даже при всех оставшихся работах семестровая часть составит не больше "
                f"{pts_gen(f.max_achievable)}, а с {fmt_num(exam_max)} на экзамене итог — не больше "
                f"{fmt_num(f.max_achievable + exam_max)}, это меньше порога {fmt_num(f.passing)}."
            )
        else:
            reasons.append(
                f"Даже при всех оставшихся работах можно набрать не больше "
                f"{pts_gen(f.max_achievable)} — это меньше порога {fmt_num(f.passing)}."
            )
        if f.remaining <= 0:
            reasons.append("Все модули завершены, оставшегося потенциала нет.")
    elif rule == "exam_above_minimum_required":
        need_exam = f.passing - f.max_achievable
        reasons.append(
            f"Даже при всех оставшихся работах семестровая часть составит {fmt_num(f.max_achievable)} — "
            f"для итоговых {fmt_num(f.passing)} на экзамене понадобится не меньше {pts_gen(need_exam)}, "
            f"больше обязательного минимума {fmt_num(exam_min)}."
        )
        reasons.append("Нужно собрать весь оставшийся максимум и хорошо подготовиться к экзамену.")
    elif rule == "no_remaining":
        reasons.append(
            f"Оставшихся работ нет, а до {_semester_goal(f)} не хватает {pts_gen(f.deficit)}."
        )
    else:  # правила шага 6: оценка по доле остатка и темпу
        r = d.share if d.share is not None else 0.0
        pace = f.pace if f.pace is not None else 0.0
        reasons.append(
            f"Для {_semester_goal(f)} нужно ещё {pts(f.deficit)} из {fmt_num(f.remaining)} "
            f"оставшихся — {fmt_pct(r)} остатка."
        )
        if rule == "almost_all_remaining":
            reasons.append("Это почти весь оставшийся максимум — важно не пропустить ни одной работы.")
        elif rule == "pace_gap_high":
            reasons.append(
                f"Сейчас набирается {fmt_pct(pace)} от максимума оценённых работ — "
                "темп нужно заметно повысить."
            )
        elif rule == "limited_margin":
            reasons.append("Порог достижим, но запас небольшой.")
        elif rule == "pace_gap_medium":
            reasons.append(
                f"Требуемая доля ({fmt_pct(r)}) выше текущего темпа ({fmt_pct(pace)}) — "
                "темп стоит немного повысить."
            )
        elif rule == "projection_margin":
            reasons.append(
                f"При текущем темпе ({fmt_pct(pace)}) ориентировочно выходит около "
                f"{fmt_approx(f.projection or 0)} — с запасом."
            )
        elif rule == "realistic" and f.pace_reliable:
            if pace >= r:
                reasons.append(
                    f"Это не больше текущего темпа ({fmt_pct(pace)}) — порог достижим в том же ритме."
                )
            else:
                reasons.append(f"Это близко к текущему темпу ({fmt_pct(pace)}).")
        if not f.pace_reliable:
            reasons.append(
                f"Оценено пока {fmt_num(f.graded_max)} из {pts_gen(f.semester_max)} — по темпу судить "
                "рано, поэтому оценка дана по доле оставшегося максимума."
            )

    if f.missing > 0 and rule not in ("missing_data", "no_graded") and len(reasons) < 3:
        reasons.append(
            f"По завершённым модулям нет баллов за {works_count(len(f.missing_titles))} — "
            "если они сданы, уточните у преподавателя."
        )
    return tuple(reasons[:3])


# --------------------------------------------------------------------------- #
# Цели по оценкам
# --------------------------------------------------------------------------- #


def target_explanation(
    f: "DisciplineFacts",
    threshold: float,
    label: str,
    status: str,
    *,
    need: float | None = None,
    share: float | None = None,
    exam_needed: float | None = None,
    extra: float | None = None,
) -> str:
    t = fmt_num(threshold)
    exam_min = f.exam_min or 0.0
    exam_max = f.exam_max or 0.0
    if status == "unknown":
        return "Данных пока недостаточно, чтобы оценить достижимость."

    if not f.is_exam:
        if status == "reached":
            return f"Порог {t} достигнут: набрано {fmt_num(f.current)}."
        if status == "achievable":
            return (
                f"Нужно ещё {pts(need or 0)} из {fmt_num(f.remaining)} оставшихся "
                f"({fmt_pct(share or 0)} остатка)."
            )
        return (
            f"Недостижимо в этом семестре: даже при всех оставшихся работах максимум — "
            f"{fmt_num(f.max_achievable)}."
        )

    # Тип C
    if f.exam_taken:
        exam = f.exam_points or 0.0
        total = f.current + exam
        if status == "reached":
            return f"Итог {fmt_num(total)}: семестр {fmt_num(f.current)} + экзамен {fmt_num(exam)}."
        if exam < exam_min:
            return (
                f"Не засчитывается: экзамен ({fmt_num(exam)}) ниже обязательного минимума "
                f"{fmt_num(exam_min)}."
            )
        return f"Итог {fmt_num(total)} ниже {t}."

    raw_need = threshold - f.current
    if extra is None or extra <= 0:
        # Достаточно экзамена: нужно max(18, T − семестр), но не больше 30.
        if raw_need < exam_min:
            by_sum = fmt_num(max(raw_need, 0))
            return (
                f"Семестровых баллов достаточно: по сумме на экзамене хватило бы {by_sum}, "
                f"но обязательный минимум — {pts_gen(exam_min)}; итог при {fmt_num(exam_min)} — "
                f"{fmt_num(f.current + exam_min)}."
            )
        return (
            f"Семестровых баллов достаточно: на экзамене нужно не меньше "
            f"{pts_gen(exam_needed or raw_need)}."
        )
    # Нужно больше 30 на экзамене → при текущих семестровых баллах недостижимо.
    head = (
        f"При текущих {fmt_num(f.current)} семестровых баллах недостижимо даже с "
        f"{fmt_num(exam_max)} на экзамене (не хватает {pts_gen(raw_need - exam_max)})."
    )
    if status == "achievable":
        return (
            f"{head} Нужно добрать в семестре {pts(extra)} из {fmt_num(f.remaining)} оставшихся "
            f"и сдать экзамен на {fmt_num(exam_max)}."
        )
    return (
        f"{head} Оставшихся семестровых работ ({fmt_num(f.remaining)}) на это не хватает: "
        f"максимальный итог — {fmt_num(f.max_achievable + exam_max)}."
    )


# --------------------------------------------------------------------------- #
# Объяснение и рекомендация по дисциплине
# --------------------------------------------------------------------------- #


def discipline_explanation(f: "DisciplineFacts", d: "RiskDecision", reasons: Sequence[str]) -> str:
    sentences: list[str] = []
    if f.graded_max > 0:
        sentences.append(
            f"Набрано {pts(f.current)} из {fmt_num(f.graded_max)} возможных по оценённым работам "
            f"({fmt_pct(f.pace or 0)})."
        )
    elif f.has_items:
        sentences.append("Оценённых работ пока нет.")
    if f.has_items and not f.exam_taken:
        if f.remaining > 0:
            sentences.append(
                f"Впереди ещё {pts(f.remaining)}, максимум семестровой части — "
                f"{fmt_num(f.semester_max)}."
            )
        else:
            sentences.append("Все модули завершены — оставшегося потенциала нет.")
    if d.level == "insufficient_data":
        sentences.append("Уровень риска не определяется, пока данных недостаточно.")
    elif reasons:
        sentences.append(reasons[0])
    if f.is_exam and not f.exam_taken and f.has_items and d.level != "insufficient_data":
        exam_min = f.exam_min or 0.0
        exam_max = f.exam_max or 0.0
        sentences.append(
            f"Итог при {fmt_num(exam_min)} на экзамене — {fmt_num(f.current + exam_min)}, "
            f"при {fmt_num(exam_max)} — {fmt_num(f.current + exam_max)}."
        )
    return " ".join(sentences[:4])


def _next_target_hint(f: "DisciplineFacts", targets: Sequence[TargetAnalytics]) -> str | None:
    """Подсказка о ближайшей недостигнутой, но достижимой оценке выше порога."""
    for t in targets:
        if t.threshold <= f.passing or t.status != "achievable":
            continue
        if f.is_exam:
            if t.reachable_with_current_points:
                return (
                    f"Для оценки «{t.label}» ({fmt_num(t.threshold)}) на экзамене понадобится "
                    f"{pts(t.exam_points_needed or 0)}."
                )
            return (
                f"Для оценки «{t.label}» ({fmt_num(t.threshold)}) нужно добрать в семестре "
                f"{pts(t.extra_semester_points_needed or 0)} и сдать экзамен на "
                f"{fmt_num(f.exam_max or 0)}."
            )
        return (
            f"До оценки «{t.label}» ({fmt_num(t.threshold)}) не хватает {pts_gen(t.points_needed_semester or 0)} — "
            f"это {fmt_pct(t.required_share_of_remaining or 0)} оставшихся."
        )
    return None


def discipline_recommendation(
    f: "DisciplineFacts",
    d: "RiskDecision",
    targets: Sequence[TargetAnalytics],
    next_actions: Sequence[NextAction],
) -> str:
    rule = d.rule
    na = next_actions[0] if next_actions else None
    weakest = _weakest_module(f.modules)
    exam_min = f.exam_min or 0.0
    parts: list[str] = []

    if rule in ("exam_below_minimum", "exam_total_below_threshold"):
        parts.append(
            "Обратитесь к преподавателю или в деканат, чтобы узнать порядок и сроки пересдачи."
        )
        if weakest is not None:
            parts.append(
                f"При подготовке стоит начать с тем модуля «{weakest.title}» — там набрано "
                f"{fmt_pct(weakest.share or 0)}."
            )
    elif rule in ("unreachable", "no_remaining"):
        parts.append(
            "Обратитесь к преподавателю или в деканат, чтобы обсудить дальнейшие шаги — "
            "например, пересдачу или индивидуальный график."
        )
        if weakest is not None:
            parts.append(
                f"Для подготовки стоит повторить темы модуля «{weakest.title}» — там набрано "
                f"{fmt_pct(weakest.share or 0)}."
            )
    elif rule == "exam_passed":
        exam = f.exam_points or 0.0
        parts.append(f"Дисциплина сдана: итог {fmt_num(f.current + exam)}.")
    elif rule == "no_items":
        parts.append("Уточните у преподавателя или в деканате план работ по дисциплине.")
    elif rule == "no_graded":
        if f.missing > 0:
            parts.append(
                "Проверьте, внесены ли результаты по завершённым модулям: "
                f"{_quoted_list(f.missing_titles)}."
            )
        if na is not None:
            parts.append(f"Ближайшая работа — {action_phrase(na)}.")
        if not parts:
            parts.append("Оценка появится после первых результатов.")
    elif rule == "missing_data":
        parts.append(
            f"Проверьте, внесены ли результаты за {_quoted_list(f.missing_titles)}; "
            "при расхождении обратитесь к преподавателю."
        )
        if na is not None:
            parts.append(f"Ближайшая работа — {action_phrase(na)}.")
    elif rule == "semester_secured":
        if f.is_exam:
            parts.append(
                f"Семестровых баллов достаточно — главное теперь подготовка к экзамену: "
                f"нужно не меньше {pts_gen(exam_min)}."
            )
        elif f.assessment_type == "credit":
            parts.append("Зачётный минимум по баллам набран.")
        else:
            parts.append(f"Порог {fmt_num(f.passing)} достигнут.")
        hint = _next_target_hint(f, targets)
        if hint:
            parts.append(hint)
        if na is not None:
            parts.append(f"Ближайшая работа — {action_phrase(na)}.")
    elif rule == "exam_above_minimum_required":
        need_exam = f.passing - f.max_achievable
        if na is not None:
            parts.append(f"Соберите все оставшиеся семестровые баллы — начните с {action_phrase(na)}.")
        parts.append(
            f"Готовьтесь к экзамену: при полном семестре на нём понадобится не меньше "
            f"{pts_gen(need_exam)}."
        )
    else:  # правила шага 6
        r = d.share if d.share is not None else 0.0
        if rule == "projection_margin":
            if na is not None:
                parts.append(f"Продолжайте в том же темпе: ближайшая работа — {action_phrase(na)}.")
            else:
                parts.append("Продолжайте в том же темпе.")
            hint = _next_target_hint(f, targets) if not f.is_exam else None
            if hint:
                parts.append(hint)
        else:
            if na is not None:
                lead = "Важно сдать все оставшиеся работы; начните с" if rule == "almost_all_remaining" else "Начните с работы"
                parts.append(f"{lead} {action_phrase(na)}.")
            parts.append(
                f"Всего до {_semester_goal(f)} нужно ещё {pts(f.deficit)} из "
                f"{fmt_num(f.remaining)} оставшихся ({fmt_pct(r)})."
            )
        if weakest is not None and rule != "projection_margin":
            parts.append(
                f"Стоит повторить темы модуля «{weakest.title}» — там набрано "
                f"{fmt_pct(weakest.share or 0)}."
            )
    return " ".join(parts[:3])


# --------------------------------------------------------------------------- #
# Сводка: индекс, приоритеты, позитивные результаты
# --------------------------------------------------------------------------- #


def index_formula(cfg: "AnalyticsConfig") -> str:
    scores = cfg.index.level_scores
    order = ("stable", "low", "medium", "high", "critical")
    parts = ", ".join(f"{RISK_COUNT_LABELS[k]} — {fmt_num(scores[k])}" for k in order if k in scores)
    caps = "; ".join(
        f"если есть дисциплина с уровнем «{RISK_COUNT_LABELS[k]}», индекс не выше {v}"
        for k, v in sorted(cfg.index.caps.items(), key=lambda kv: kv[1])
    )
    return (
        "Ориентировочный индекс = среднее баллов уровней риска по дисциплинам с известным риском, "
        f"веса равные ({parts}); {caps}. Дисциплины с недостаточными данными не учитываются. "
        "Это сводный ориентир, а не официальная оценка успеваемости."
    )


def points_target_text(d: DisciplineAnalytics) -> str:
    rule = d.risk.rule
    exam = d.exam
    if rule in ("exam_below_minimum", "exam_total_below_threshold") and exam is not None:
        return (
            f"Итог {fmt_num(exam.final_total or 0)} при пороге {fmt_num(d.passing_threshold)}; "
            f"на экзамене нужно не меньше {pts_gen(exam.points_min)}."
        )
    if rule in ("unreachable", "no_remaining"):
        top = d.max_achievable_semester + (exam.points_max if exam else 0)
        return (
            f"Порог {fmt_num(d.passing_threshold)} в рамках семестра недостижим: "
            f"максимум — {fmt_num(top)}."
        )
    if rule == "exam_above_minimum_required" and exam is not None:
        need_exam = d.passing_threshold - d.max_achievable_semester
        return (
            f"Все оставшиеся {pts(d.remaining_points_max)} и не меньше {pts_gen(need_exam)} "
            "на экзамене."
        )
    needed = d.semester_points_needed or 0
    share = d.required_share_of_remaining
    text = (
        f"Ещё {pts(needed)} из {fmt_num(d.remaining_points_max)} оставшихся"
        + (f" ({fmt_pct(share)})" if share is not None else "")
        + f" до {fmt_num(d.semester_target)}"
    )
    if exam is not None:
        text += f" и не меньше {pts_gen(exam.points_min)} на экзамене"
    return text + "."


def positive_message(d: DisciplineAnalytics) -> str | None:
    rule = d.risk.rule
    exam = d.exam
    if rule == "exam_passed" and exam is not None:
        grade = f" — «{d.current_grade.label}»" if d.current_grade else ""
        return f"Экзамен сдан: итог {fmt_num(exam.final_total or 0)}{grade}."
    if rule == "semester_secured":
        if exam is not None:
            return (
                f"Семестровых баллов ({fmt_num(d.current_semester_points)}) достаточно для итога "
                f"{fmt_num(d.passing_threshold)} при минимальных {fmt_num(exam.points_min)} на экзамене."
            )
        if d.assessment_type == "credit":
            return (
                f"Зачётный минимум по баллам набран: {fmt_num(d.current_semester_points)} "
                f"при пороге {fmt_num(d.passing_threshold)}."
            )
        return (
            f"Порог {fmt_num(d.passing_threshold)} уже достигнут: "
            f"{pts(d.current_semester_points)}."
        )
    if d.projected_semester_points is not None and d.current_pace is not None:
        return (
            f"Хороший темп ({fmt_pct(d.current_pace)}): ориентировочно "
            f"{fmt_num(d.projected_semester_points)} при семестровой цели {fmt_num(d.semester_target)}."
        )
    return None


def summary_explanation(
    *,
    index_value: int | None,
    index_label: str,
    zone_counts: Mapping[str, int],
    caps_applied: Sequence[str],
    cap_value: int | None,
    first_priority: tuple[str, NextAction | None, str] | None,
    insufficient_titles: Sequence[str],
) -> str:
    sentences: list[str] = []
    if index_value is None:
        sentences.append(
            "Данных пока недостаточно, чтобы рассчитать ориентировочный индекс: "
            "оценённых работ нет ни по одной дисциплине."
        )
    else:
        sentences.append(
            f"Ориентировочный индекс учебной устойчивости — {index_value}/100, зона «{index_label}»."
        )
        critical = zone_counts.get("critical", 0)
        high = zone_counts.get("high", 0)
        medium = zone_counts.get("medium", 0)
        if critical:
            text = (
                f"Критический риск — {disciplines_count(critical)}: порог там уже не достигается "
                "обычным порядком, поэтому важно обсудить ситуацию с преподавателем."
            )
            if caps_applied and cap_value is not None:
                text += (
                    f" Индекс ограничен значением {cap_value}, чтобы эта дисциплина не потерялась "
                    "среди благополучных."
                )
            sentences.append(text)
        elif high or medium:
            pieces = []
            if high:
                pieces.append(f"высокий риск — {disciplines_count(high)}")
            if medium:
                pieces.append(f"средний риск — {disciplines_count(medium)}")
            lead = "В целом ситуация стабильная, но" if index_label == "Стабильно" else "Есть над чем поработать:"
            sentences.append(f"{lead} {', '.join(pieces)} — там запас баллов небольшой.")
        else:
            sentences.append("Во всех дисциплинах с известным риском порог достижим без резкого роста темпа.")
    if insufficient_titles:
        sentences.append(
            f"По {len(insufficient_titles)} "
            f"{plural(len(insufficient_titles), 'дисциплине', 'дисциплинам', 'дисциплинам')} "
            f"данных пока недостаточно для оценки: {_quoted_list(insufficient_titles)}."
        )
    if first_priority is not None:
        title, action, fallback = first_priority
        if action is not None:
            sentences.append(
                f"В первую очередь стоит заняться дисциплиной «{title}»: ближайшая работа — "
                f"«{action.title}» ({deadline_phrase(action)})."
            )
        else:
            sentences.append(f"В первую очередь стоит заняться дисциплиной «{title}»: {fallback}")
    return " ".join(sentences)
