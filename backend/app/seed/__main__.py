from __future__ import annotations

import sys

from ..bootstrap import run_migrations
from ..db import SessionLocal
from .seed import is_seeded, reset_all, seed_all, sync_resources


def main() -> None:
    run_migrations()
    with SessionLocal() as db:
        if "--reset" in sys.argv:
            reset_all(db)
            print("Все данные удалены.")
        if is_seeded(db):
            print("БД уже содержит данные — пропускаю заполнение (используйте --reset для пересоздания).")
        else:
            seed_all(db)
            print("Демо-данные загружены: student1, student2, dekanat.")
        n = sync_resources(db)
        print(f"Каталог учебных материалов: {n} записей.")


if __name__ == "__main__":
    main()
