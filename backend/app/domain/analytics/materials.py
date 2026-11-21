"""Связка аналитики с учебными материалами по темам (ТЗ §16, §18 п.11–12).

Аналитика определяет слабые темы (``DisciplineAnalytics.weak_topic_ids`` —
темы модулей с долей набранного ниже ``weak_module_share``). Здесь — чистый
детерминированный отбор материалов из уже готового каталога по КОНКРЕТНОЙ теме:

* материал попадает в подборку, только если тема явно указана в его ``topic_ids``
  (не по названию дисциплины);
* материалы с недоступной ссылкой (``link_status == "broken"``) не показываются;
* пустая подборка — нормальный результат с честным сообщением, без «заглушек».

Сам каталог (поиск, проверка ссылок) — зона модуля учебных материалов (роль 05);
этот файл его не содержит и не придумывает материалы.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Literal, Mapping

from .types import DisciplineAnalytics

LinkStatus = Literal["verified", "unchecked", "broken"]

_LINK_ORDER = {"verified": 0, "unchecked": 1}


@dataclass(frozen=True)
class MaterialRef:
    id: int
    title: str
    material_type: str  # article | video | lecture | textbook | notes | trainer
    url: str
    topic_ids: tuple[int, ...]
    source: str | None = None
    link_status: LinkStatus = "unchecked"

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "material_type": self.material_type,
            "url": self.url,
            "topic_ids": list(self.topic_ids),
            "source": self.source,
            "link_status": self.link_status,
        }


@dataclass(frozen=True)
class TopicMaterials:
    topic_id: int
    topic_title: str | None
    materials: tuple[MaterialRef, ...]
    is_empty: bool
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "topic_id": self.topic_id,
            "topic_title": self.topic_title,
            "materials": [m.to_dict() for m in self.materials],
            "is_empty": self.is_empty,
            "message": self.message,
        }


def select_materials_for_topic(
    topic_id: int,
    catalog: Iterable[MaterialRef],
    topic_title: str | None = None,
) -> TopicMaterials:
    """Материалы каталога, привязанные именно к этой теме (проверенные ссылки — первыми)."""
    chosen = sorted(
        (m for m in catalog if topic_id in m.topic_ids and m.link_status != "broken"),
        key=lambda m: (_LINK_ORDER.get(m.link_status, 9), m.title, m.id),
    )
    name = f"«{topic_title}»" if topic_title else "этой теме"
    if not chosen:
        return TopicMaterials(
            topic_id=topic_id,
            topic_title=topic_title,
            materials=(),
            is_empty=True,
            message=(
                f"По теме {name} в каталоге пока нет подходящих материалов. "
                "Можно уточнить у преподавателя рекомендованную литературу."
            ),
        )
    unchecked = sum(1 for m in chosen if m.link_status == "unchecked")
    message = f"Подобрано материалов по теме {name}: {len(chosen)}."
    if unchecked:
        message += f" Ссылки ещё не проверены: {unchecked}."
    return TopicMaterials(
        topic_id=topic_id,
        topic_title=topic_title,
        materials=tuple(chosen),
        is_empty=False,
        message=message,
    )


def materials_for_weak_topics(
    analytics: DisciplineAnalytics,
    catalog: Iterable[MaterialRef],
    topic_titles: Mapping[int, str] | None = None,
) -> tuple[TopicMaterials, ...]:
    """Подборки по каждой слабой теме дисциплины (в порядке модулей)."""
    catalog = tuple(catalog)
    titles = topic_titles or {}
    return tuple(
        select_materials_for_topic(topic_id, catalog, titles.get(topic_id))
        for topic_id in analytics.weak_topic_ids
    )
