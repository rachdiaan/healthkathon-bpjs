"""Batch rescore dan publikasi (FR-21..FR-25, BR-14, BR-15, TC-5)."""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Annotated, Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, BackgroundTasks, Path, Response
from pydantic import BaseModel, ConfigDict, Field

from api import db
from api.deps import Ctx, Supervisor
from api.errors import ApiError
from api.version import GIT_SHA
from engine import ml_model
from engine import score_batch as scorer

router = APIRouter(prefix="/api")
log = logging.getLogger("payray.rescore")
WIB = ZoneInfo("Asia/Jakarta")
MIN_GAP_MINUTES = 5
STALE_MINUTES = 10
RESCORE_LOCK = 4242  # pg_advisory_xact_lock: serialisasi pembuatan batch


class RescoreIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    period: str = Field(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")


def _batch_json(r: dict[str, Any]) -> dict[str, Any]:
    out = dict(r)
    for k in ("created_at", "finished_at", "published_at"):
        if out.get(k) is not None:
            out[k] = out[k].isoformat()
    return out


def run_rescore(batch_id: int, fail_at: int | None = None) -> None:
    """BackgroundTask: scoring sebagai payray_scoring. Gagal → failed + error, tanpa retry (FR-23)."""
    try:
        with db.transaction() as conn:
            conn.execute("SET LOCAL ROLE payray_scoring")
            scorer.score_batch(conn, batch_id, fail_at=fail_at)
    except Exception as exc:  # noqa: BLE001 - semua kegagalan dicatat ke batch
        log.exception("rescore batch %s gagal", batch_id)
        with db.transaction() as conn:
            conn.execute("SET LOCAL ROLE payray_scoring")
            conn.execute("UPDATE core.score_batch SET status = 'failed', error = %s, finished_at = now() "
                         "WHERE id = %s AND status = 'running'", (f"{type(exc).__name__}: {exc}"[:500], batch_id))


# Hook uji BUG-6: tes mengisi nilai ini untuk memaksa kegagalan di BU ke-n.
TEST_FAIL_AT: int | None = None


@router.post("/rescore-batches", status_code=202)
def create(ctx: Annotated[Ctx, Supervisor], body: RescoreIn, tasks: BackgroundTasks) -> dict[str, Any]:
    current = datetime.now(WIB).strftime("%Y-%m")
    if body.period > current:
        raise ApiError(422, "validation_error", "Periode tidak boleh melewati bulan berjalan.",
                       {"period": f"maksimal {current}"})
    ctx.conn.execute("SELECT pg_advisory_xact_lock(%s)", (RESCORE_LOCK,))
    if ctx.conn.execute("SELECT 1 FROM core.score_batch WHERE status = 'running'").fetchone():
        raise ApiError(409, "batch_running", "Masih ada rescore yang berjalan.")
    recent = ctx.conn.execute(
        "SELECT 1 FROM core.score_batch WHERE created_at > now() - make_interval(mins => %s)", (MIN_GAP_MINUTES,)
    ).fetchone()
    if recent:
        raise ApiError(429, "too_soon", f"Tunggu {MIN_GAP_MINUTES} menit sejak rescore terakhir.")
    row = ctx.conn.execute(
        "INSERT INTO core.score_batch (branch_id, period, status, model_version, engine_version, created_by) "
        "VALUES (%s, %s, 'running', %s, %s, %s) RETURNING id",
        (ctx.user.branch_id, body.period, ml_model.model_version(), GIT_SHA, ctx.user.id),
    ).fetchone()
    assert row is not None
    ctx.audit("batch.create", resource="score_batch", resource_id=row["id"], detail={"period": body.period})
    tasks.add_task(run_rescore, row["id"], TEST_FAIL_AT)
    return {"id": row["id"], "status": "running"}


BATCH_COLS = ("id, branch_id, period, status, model_version, engine_version, n_scored, error, created_by, "
              "created_at, finished_at, published_at")


@router.get("/rescore-batches")
def list_batches(ctx: Annotated[Ctx, Supervisor]) -> dict[str, Any]:
    rows = ctx.conn.execute(
        f"SELECT {BATCH_COLS} FROM core.score_batch WHERE branch_id = %s ORDER BY id DESC LIMIT 50",  # nosec B608
        (ctx.user.branch_id,),
    ).fetchall()
    return {"items": [_batch_json(r) for r in rows]}


@router.get("/rescore-batches/{batch_id}")
def get_batch(ctx: Annotated[Ctx, Supervisor], batch_id: Annotated[int, Path(ge=1)]) -> dict[str, Any]:
    row = ctx.conn.execute(
        f"SELECT {BATCH_COLS} FROM core.score_batch WHERE id = %s AND branch_id = %s",  # nosec B608
        (batch_id, ctx.user.branch_id),
    ).fetchone()
    if row is None:
        raise ApiError(404, "not_found", "Batch tidak ditemukan.")
    out = _batch_json(row)
    if row["status"] in ("ready", "published", "archived"):
        active = ctx.conn.execute(
            "SELECT id FROM core.score_batch WHERE branch_id = %s AND status = 'published'", (ctx.user.branch_id,)
        ).fetchone()
        if active and active["id"] != batch_id:
            n_new = ctx.conn.execute(
                "SELECT count(*) AS n FROM core.risk_score WHERE batch_id = %s AND rank <= 10 AND employer_id NOT IN "
                "(SELECT employer_id FROM core.risk_score WHERE batch_id = %s AND rank <= 10)",
                (batch_id, active["id"]),
            ).fetchone()
            out["summary"] = {"n_scored": row["n_scored"], "new_in_top10": n_new["n"] if n_new else None,
                              "compared_to_batch": active["id"]}
        else:
            out["summary"] = {"n_scored": row["n_scored"], "new_in_top10": None, "compared_to_batch": None}
    return out


@router.post("/rescore-batches/{batch_id}/publish")
def publish(ctx: Annotated[Ctx, Supervisor], batch_id: Annotated[int, Path(ge=1)], response: Response
            ) -> dict[str, Any]:
    row = ctx.conn.execute(
        "SELECT status FROM core.score_batch WHERE id = %s AND branch_id = %s FOR UPDATE",
        (batch_id, ctx.user.branch_id),
    ).fetchone()
    if row is None:
        raise ApiError(404, "not_found", "Batch tidak ditemukan.")
    if row["status"] != "ready":
        raise ApiError(409, "not_ready", "Hanya batch berstatus siap yang bisa dipublikasikan.")
    # Atomik (FR-24): arsipkan batch published lama lalu publikasikan batch ini dalam satu transaksi.
    ctx.conn.execute("UPDATE core.score_batch SET status = 'archived' WHERE branch_id = %s AND status = 'published'",
                     (ctx.user.branch_id,))
    ctx.conn.execute("UPDATE core.score_batch SET status = 'published', published_at = now() WHERE id = %s",
                     (batch_id,))
    ctx.audit("batch.publish", resource="score_batch", resource_id=batch_id)
    return {"id": batch_id, "status": "published"}


def fail_stale_batches() -> int:
    """TC-5: saat startup, batch running > 10 menit (proses mati di tengah rescore) → failed."""
    with db.transaction() as conn:
        rows = conn.execute(
            "UPDATE core.score_batch SET status = 'failed', error = 'Dihentikan: proses API restart saat rescore', "
            "finished_at = now() WHERE status = 'running' AND created_at < now() - make_interval(mins => %s) "
            "RETURNING id", (STALE_MINUTES,),
        ).fetchall()
    for r in rows:
        log.warning("batch %s ditandai failed (basi)", r["id"])
    return len(rows)
