"""Format error seragam: {"error": {"code", "message", "fields"}} (PRD §17)."""
from __future__ import annotations

from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, fields: dict[str, str] | None = None,
                 headers: dict[str, str] | None = None) -> None:
        self.status, self.code, self.message, self.fields, self.headers = status, code, message, fields, headers


def body(code: str, message: str, fields: dict[str, Any] | None = None) -> dict[str, Any]:
    err: dict[str, Any] = {"code": code, "message": message}
    if fields:
        err["fields"] = fields
    return {"error": err}


def install(app: FastAPI) -> None:
    @app.exception_handler(ApiError)
    async def _api(_: Request, exc: ApiError) -> JSONResponse:
        return JSONResponse(body(exc.code, exc.message, exc.fields), status_code=exc.status, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def _validation(_: Request, exc: RequestValidationError) -> JSONResponse:
        fields: dict[str, str] = {}
        for e in exc.errors():
            loc = [str(p) for p in e.get("loc", ()) if p not in ("body", "query", "header", "path")]
            fields[".".join(loc) or "_"] = str(e.get("msg", "tidak valid"))
        return JSONResponse(body("validation_error", "Input tidak valid.", fields), status_code=422)

    @app.exception_handler(StarletteHTTPException)
    async def _http(_: Request, exc: StarletteHTTPException) -> JSONResponse:
        code = {404: "not_found", 405: "method_not_allowed", 401: "unauthorized", 403: "forbidden"}.get(
            exc.status_code, "error")
        return JSONResponse(body(code, str(exc.detail)), status_code=exc.status_code)
