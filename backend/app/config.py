"""Настройки приложения. Все значения берутся из переменных окружения (или файла .env).

Секретов в коде нет: сессии — случайные непрозрачные токены, хранящиеся в БД в виде SHA-256,
поэтому ключ подписи не требуется. Демо-пароли — публичные тестовые учётные данные для жюри,
их можно переопределить переменными окружения при развёртывании.
"""
from __future__ import annotations

from datetime import date, datetime
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = "development"  # development | production
    database_url: str = f"sqlite:///{BACKEND_DIR / 'data' / 'deanate.db'}"

    # Сессии и cookie
    cookie_secure: bool = False  # в production за HTTPS обязательно true
    session_cookie_name: str = "dd_session"
    session_ttl_hours: int = 72  # абсолютный срок жизни сессии
    session_idle_minutes: int = 720  # сессия истекает при бездействии

    # Ограничение попыток входа (на один IP + логин)
    login_rate_limit: int = 10
    login_rate_window_seconds: int = 300
    trust_proxy_headers: bool = False  # учитывать X-Forwarded-For (только за доверенным прокси)

    # Начальные данные
    seed_on_startup: bool = True
    demo_password_student1: str = "student1-demo"
    demo_password_student2: str = "student2-demo"
    demo_password_staff: str = "dekanat-demo"

    # Отображение
    university_name: str = "Технический университет"
    timezone: str = "Europe/Moscow"
    demo_today: date | None = None  # зафиксировать «сегодня» (для тестов и демонстрации)

    frontend_dist: str = str(BACKEND_DIR.parent / "frontend" / "dist")

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def tz(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)


@lru_cache
def get_settings() -> Settings:
    return Settings()


def now_local() -> datetime:
    s = get_settings()
    return datetime.now(s.tz)


def today_local() -> date:
    s = get_settings()
    return s.demo_today or now_local().date()
