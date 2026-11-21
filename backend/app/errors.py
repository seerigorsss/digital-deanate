"""Единый формат ошибок API: {"detail": str, "code": str, "errors": [{"field","message"}]?}."""
from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, errors: list[dict] | None = None):
        self.status = status
        self.code = code
        self.message = message
        self.errors = errors


def not_found(message: str = "Ресурс не найден") -> ApiError:
    # Для чужих ресурсов отвечаем так же, как для несуществующих — не раскрываем факт существования.
    return ApiError(404, "not_found", message)


def forbidden(message: str = "Недостаточно прав") -> ApiError:
    return ApiError(403, "forbidden", message)


def bad_request(message: str, code: str = "bad_request", errors: list[dict] | None = None) -> ApiError:
    return ApiError(400, code, message, errors)


def conflict(message: str, code: str = "conflict") -> ApiError:
    return ApiError(409, code, message)


_FIELD_MESSAGES = {
    "missing": "Обязательное поле",
    "string_too_short": "Слишком короткое значение",
    "string_too_long": "Слишком длинное значение",
    "greater_than_equal": "Значение слишком маленькое",
    "less_than_equal": "Значение слишком большое",
    "int_parsing": "Нужно целое число",
    "float_parsing": "Нужно число",
    "date_from_datetime_parsing": "Неверная дата",
    "date_parsing": "Неверная дата",
}


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api_error(_: Request, exc: ApiError):
        body: dict = {"detail": exc.message, "code": exc.code}
        if exc.errors:
            body["errors"] = exc.errors
        return JSONResponse(status_code=exc.status, content=body)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError):
        errors = []
        for e in exc.errors():
            loc = [str(p) for p in e.get("loc", ()) if p not in ("body", "query", "path")]
            errors.append({"field": ".".join(loc), "message": _FIELD_MESSAGES.get(e.get("type", ""), "Некорректное значение")})
        return JSONResponse(
            status_code=422,
            content={"detail": "Проверьте введённые данные", "code": "validation_error", "errors": errors},
        )

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException):
        messages = {404: "Не найдено", 405: "Метод не поддерживается", 401: "Требуется вход"}
        detail = exc.detail if isinstance(exc.detail, str) and exc.status_code not in messages else messages.get(exc.status_code, str(exc.detail))
        return JSONResponse(status_code=exc.status_code, content={"detail": detail, "code": f"http_{exc.status_code}"})

    @app.exception_handler(Exception)
    async def _unhandled(_: Request, exc: Exception):  # noqa: ARG001
        return JSONResponse(status_code=500, content={"detail": "Внутренняя ошибка сервера. Попробуйте позже.", "code": "server_error"})
