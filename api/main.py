"""PayRay API: entrypoint FastAPI."""
from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from api import auth, batches, errors, inspections, metrics, queue, scan_sheet
from api.limits import GuardMiddleware
from api.version import GIT_SHA, ROOT, VERSION

WEB_DIR = ROOT / "web"
log = logging.getLogger("payray")


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    try:
        batches.fail_stale_batches()  # TC-5
    except Exception:  # noqa: BLE001 - DB belum siap tidak boleh mematikan /api/health
        log.exception("recovery batch basi gagal saat startup")
    yield


app = FastAPI(title="PayRay", version=VERSION, docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
errors.install(app)
app.add_middleware(GuardMiddleware)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": VERSION, "git_sha": GIT_SHA}


for module in (auth, queue, scan_sheet, inspections, batches, metrics):
    app.include_router(module.router)
app.mount("/", StaticFiles(directory=WEB_DIR, html=True), name="web")
