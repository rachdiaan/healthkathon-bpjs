"""Antrean risiko (FR-6..FR-10, BR-2, BR-13, BR-22)."""
from __future__ import annotations

import base64
import binascii
import csv
import io
import json
from collections.abc import Iterator
from datetime import datetime
from typing import Annotated, Any
from zoneinfo import ZoneInfo

import psycopg
from psycopg.rows import DictRow
from fastapi import APIRouter, Query
from fastapi.responses import StreamingResponse

from api.deps import AnyUser, Ctx
from api.errors import ApiError

router = APIRouter(prefix="/api")
WIB = ZoneInfo("Asia/Jakarta")
CSV_MAX_ROWS = 500
FORMULA_PREFIX = ("=", "+", "-", "@", "\t", "\r")


def current_period() -> str:
    return datetime.now(WIB).strftime("%Y-%m")


def encode_cursor(batch_id: int, after_rank: int) -> str:
    raw = json.dumps({"batch_id": batch_id, "after_rank": after_rank}, separators=(",", ":")).encode()
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def decode_cursor(cursor: str) -> tuple[int, int]:
    try:
        pad = "=" * (-len(cursor) % 4)
        data = json.loads(base64.urlsafe_b64decode(cursor + pad))
        batch_id, after_rank = data["batch_id"], data["after_rank"]
    except (binascii.Error, ValueError, KeyError, TypeError, UnicodeDecodeError) as exc:
        raise ApiError(422, "invalid_cursor", "Cursor tidak valid.", {"cursor": "format tidak dikenal"}) from exc
    if type(batch_id) is not int or type(after_rank) is not int or batch_id < 1 or after_rank < 0:
        raise ApiError(422, "invalid_cursor", "Cursor tidak valid.", {"cursor": "harus berisi bilangan bulat"})
    return batch_id, after_rank


def active_batch(conn: psycopg.Connection[DictRow], branch_id: int) -> dict[str, Any] | None:
    return conn.execute(
        "SELECT id, period, published_at FROM core.score_batch WHERE branch_id = %s AND status = 'published'",
        (branch_id,),
    ).fetchone()


ITEM_SQL = """
SELECT rs.rank, e.id AS employer_id, e.name, coalesce(s.name, e.kbli_sector) AS sector, rs.score,
       rs.confidence, rs.confidence_bucket, rs.reason_codes, rs.rp_low, rs.rp_high, rs.rp_band,
       rs.sme_protection,
       EXISTS (SELECT 1 FROM ops.inspection i WHERE i.employer_id = e.id AND i.status = 'submitted'
               AND i.period = %(period)s) AS inspected
FROM core.risk_score rs
JOIN core.employer e ON e.id = rs.employer_id
LEFT JOIN core.sector s ON s.kbli = e.kbli_sector
WHERE rs.batch_id = %(batch_id)s AND e.branch_id = %(branch_id)s AND rs.rank > %(after)s
ORDER BY rs.rank
LIMIT %(limit)s
"""


def _rp_fields(r: dict[str, Any]) -> dict[str, Any]:
    from api.scan_sheet import rp_mode

    if rp_mode() == "band":  # KILL-5: hanya band, tanpa angka Rp (FR-13)
        return {"rp_low": None, "rp_high": None, "rp_band": r["rp_band"]}
    return {"rp_low": r["rp_low"], "rp_high": r["rp_high"], "rp_band": r["rp_band"]}


def queue_items(conn: psycopg.Connection[DictRow], batch_id: int, branch_id: int, after: int, limit: int) -> list[dict[str, Any]]:
    rows = conn.execute(ITEM_SQL, {"batch_id": batch_id, "branch_id": branch_id, "after": after,
                                   "limit": limit, "period": current_period()}).fetchall()
    return [{
        "rank": r["rank"], "employer_id": r["employer_id"], "name": r["name"], "sector": r["sector"],
        "score": round(r["score"], 6), "confidence": round(r["confidence"], 4),
        "confidence_bucket": r["confidence_bucket"],
        "reasons": [{"code": x["code"], "text": x["text"]} for x in r["reason_codes"][:3]],
        **(_rp_fields(r)),
        "sme_protection": r["sme_protection"],
        "verify_first": r["sme_protection"] and r["confidence_bucket"] == "rendah",
        "inspection_status": "submitted" if r["inspected"] else "none",
    } for r in rows]


@router.get("/queue")
def get_queue(ctx: Annotated[Ctx, AnyUser], limit: Annotated[int, Query(ge=1, le=100)] = 10,
              cursor: Annotated[str | None, Query(max_length=200)] = None) -> dict[str, Any]:
    branch = ctx.user.branch_id
    if cursor:
        batch_id, after = decode_cursor(cursor)
        batch = ctx.conn.execute(
            "SELECT id, period, published_at FROM core.score_batch WHERE id = %s AND branch_id = %s "
            "AND status IN ('published', 'archived')", (batch_id, branch)).fetchone()
        if batch is None:
            raise ApiError(422, "invalid_cursor", "Cursor tidak valid.", {"cursor": "batch tidak dikenal"})
    else:
        batch = active_batch(ctx.conn, branch)
        if batch is None:
            return {"batch": None, "items": [], "next_cursor": None}
        after = 0
    items = queue_items(ctx.conn, batch["id"], branch, after, limit + 1)
    more = len(items) > limit
    items = items[:limit]
    return {
        "batch": {"id": batch["id"], "period": batch["period"],
                  "published_at": batch["published_at"].isoformat() if batch["published_at"] else None},
        "items": items,
        "next_cursor": encode_cursor(batch["id"], items[-1]["rank"]) if more and items else None,
    }


def _safe(v: Any) -> str:
    s = "" if v is None else str(v)
    return "'" + s if s.startswith(FORMULA_PREFIX) else s


CSV_COLUMNS = ["rank", "employer_id", "nama", "sektor", "skor", "confidence", "reason_codes",
               "rp_low", "rp_high", "sme_protection", "inspection_status"]


@router.get("/queue.csv")
def get_queue_csv(ctx: Annotated[Ctx, AnyUser]) -> StreamingResponse:
    batch = active_batch(ctx.conn, ctx.user.branch_id)
    items = queue_items(ctx.conn, batch["id"], ctx.user.branch_id, 0, CSV_MAX_ROWS) if batch else []
    ctx.audit("export.queue_csv", resource="queue", resource_id=batch["id"] if batch else None,
              detail={"rows": len(items)})

    def rows() -> Iterator[str]:
        buf = io.StringIO()
        w = csv.writer(buf)
        w.writerow(CSV_COLUMNS)
        for it in items:
            w.writerow([_safe(v) for v in (
                it["rank"], it["employer_id"], it["name"], it["sector"], it["score"], it["confidence_bucket"],
                " | ".join(r["code"] for r in it["reasons"]), it["rp_low"], it["rp_high"],
                it["sme_protection"], it["inspection_status"])])
            yield buf.getvalue()
            buf.seek(0)
            buf.truncate()
        if not items:
            yield buf.getvalue()

    period = batch["period"] if batch else "kosong"
    return StreamingResponse(rows(), media_type="text/csv; charset=utf-8",
                             headers={"Content-Disposition": f'attachment; filename="antrean-{period}.csv"'})
