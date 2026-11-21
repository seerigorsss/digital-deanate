import os
import tempfile

# Отдельная временная БД и фиксированная «сегодняшняя» дата — до импорта приложения
_tmp = tempfile.mkdtemp(prefix="deanate-test-")
os.environ["DATABASE_URL"] = f"sqlite:///{_tmp}/test.db"
os.environ["DEMO_TODAY"] = "2026-11-23"
os.environ["SEED_ON_STARTUP"] = "true"
os.environ["COOKIE_SECURE"] = "false"
os.environ["LOGIN_RATE_LIMIT"] = "6"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402

PASSWORDS = {"student1": "student1-demo", "student2": "student2-demo", "dekanat": "dekanat-demo"}


@pytest.fixture(scope="session")
def app():
    from app.main import app as fastapi_app

    with TestClient(fastapi_app):  # запускает lifespan: миграции + seed
        pass
    return fastapi_app


class Api:
    """Клиент, который логинится и автоматически подставляет CSRF-токен."""

    def __init__(self, app, login: str | None = None):
        self.c = TestClient(app)
        self.csrf = ""
        if login:
            self.login(login)

    def login(self, login: str, password: str | None = None):
        r = self.c.post("/api/auth/login", json={"login": login, "password": password or PASSWORDS[login]})
        if r.status_code == 200:
            self.csrf = r.json()["csrf_token"]
        return r

    def get(self, url, **kw):
        return self.c.get(url, **kw)

    def _h(self, kw):
        h = kw.pop("headers", {}) or {}
        h.setdefault("X-CSRF-Token", self.csrf)
        return h

    def post(self, url, json=None, **kw):
        return self.c.post(url, json=json, headers=self._h(kw), **kw)

    def put(self, url, json=None, **kw):
        return self.c.put(url, json=json, headers=self._h(kw), **kw)

    def patch(self, url, json=None, **kw):
        return self.c.patch(url, json=json, headers=self._h(kw), **kw)

    def delete(self, url, **kw):
        return self.c.delete(url, headers=self._h(kw), **kw)


@pytest.fixture
def s1(app):
    return Api(app, "student1")


@pytest.fixture
def s2(app):
    return Api(app, "student2")


@pytest.fixture
def staff(app):
    return Api(app, "dekanat")
