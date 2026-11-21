"""Сборка входов аналитики из ``app/seed/data/curriculum.json`` + ``demo_results.json``.

Модули и работы — из учебного плана, баллы — из демо-результатов (отсутствующий
ключ = результата нет). ``semester_progress`` — доля дней между началом и концом
учебного периода. Идентификаторы работ/модулей/тем — порядковые номера.
"""

from __future__ import annotations

import json
from datetime import date
from functools import lru_cache
from pathlib import Path
from typing import Any

from app.domain.analytics import (
    AssessmentConfig,
    DisciplineInput,
    ItemInput,
    ModuleInput,
)

DATA_DIR = Path(__file__).resolve().parents[2] / "app" / "seed" / "data"
DEMO_TODAY = date(2026, 11, 23)


@lru_cache(maxsize=None)
def load_curriculum() -> dict[str, Any]:
    return json.loads((DATA_DIR / "curriculum.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def load_demo_results() -> dict[str, Any]:
    return json.loads((DATA_DIR / "demo_results.json").read_text(encoding="utf-8"))


def semester_progress(today: date, curriculum: dict[str, Any] | None = None) -> float:
    period = (curriculum or load_curriculum())["period"]
    start = date.fromisoformat(period["starts_on"])
    end = date.fromisoformat(period["ends_on"])
    share = (today - start).days / (end - start).days
    return min(1.0, max(0.0, share))


def topic_ids_by_key() -> dict[str, int]:
    ids: dict[str, int] = {}
    for disc in load_curriculum()["disciplines"]:
        for topic in disc.get("topics", []):
            ids.setdefault(topic["key"], len(ids) + 1)
    return ids


def build_inputs(student: str, today: date = DEMO_TODAY) -> list[tuple[str, DisciplineInput]]:
    """[(ключ дисциплины, DisciplineInput)] для демо-студента."""
    curriculum = load_curriculum()
    results = load_demo_results()[student]
    by_key = {d["key"]: d for d in curriculum["disciplines"]}
    topic_ids = topic_ids_by_key()
    progress = semester_progress(today, curriculum)

    out: list[tuple[str, DisciplineInput]] = []
    next_id = 1
    for disc_index, (key, res) in enumerate(results.items(), start=1):
        disc = by_key[key]
        points = res["points"]
        a = disc["assessment"]
        config = AssessmentConfig(
            assessment_type=a["type"],
            semester_points_max=a["semester_points_max"],
            passing_threshold=a["passing_threshold"],
            exam_points_min=a.get("exam_points_min"),
            exam_points_max=a.get("exam_points_max"),
        )
        modules = []
        for m in disc["modules"]:
            items = []
            for it in m["items"]:
                items.append(
                    ItemInput(
                        id=next_id,
                        title=it["title"],
                        kind=it["kind"],
                        max_points=it["max_points"],
                        due_date=date.fromisoformat(it["due_date"]) if it.get("due_date") else None,
                        points=points.get(it["key"]),
                    )
                )
                next_id += 1
            modules.append(
                ModuleInput(
                    id=next_id,
                    ordinal=m["ordinal"],
                    title=m["title"],
                    status=m["status"],
                    ends_on=date.fromisoformat(m["ends_on"]) if m.get("ends_on") else None,
                    items=tuple(items),
                    topic_ids=tuple(
                        topic_ids[t["key"]]
                        for t in disc.get("topics", [])
                        if t["module"] == m["ordinal"]
                    ),
                )
            )
            next_id += 1
        out.append(
            (
                key,
                DisciplineInput(
                    discipline_id=disc_index,
                    title=disc["title"],
                    config=config,
                    modules=tuple(modules),
                    exam_points=res.get("exam_points"),
                    today=today,
                    semester_progress=progress,
                ),
            )
        )
    return out
