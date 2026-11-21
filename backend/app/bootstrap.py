"""Инициализация БД при старте: миграции Alembic → начальные данные (если БД пуста) → справочник материалов."""
from __future__ import annotations

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config

from .config import get_settings
from .db import SessionLocal

log = logging.getLogger("deanate")
BACKEND_DIR = Path(__file__).resolve().parent.parent


def run_migrations() -> None:
    cfg = Config(str(BACKEND_DIR / "alembic.ini"))
    cfg.set_main_option("script_location", str(BACKEND_DIR / "migrations"))
    command.upgrade(cfg, "head")


def init_database() -> None:
    run_migrations()
    if not get_settings().seed_on_startup:
        return
    from .seed.seed import is_seeded, seed_all, sync_resources

    with SessionLocal() as db:
        if not is_seeded(db):
            seed_all(db)
            log.info("Demo data seeded")
        sync_resources(db)
