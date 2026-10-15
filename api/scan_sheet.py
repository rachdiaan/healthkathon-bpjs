"""Scan sheet satu BU (FR-11..FR-15). BU di luar cabang atau di luar batch aktif → 404, bukan 403."""
from __future__ import annotations

import os
from typing import Annotated, Any

from fastapi import APIRouter, Path

from api.deps import AnyUser, Ctx
from api.errors import ApiError
from api.queue import active_batch, current_period

router = APIRouter(prefix="/api")


def rp_mode() -> str:
    return "band" if os.environ.get("PAYRAY_RP_MODE", "range").strip().lower() == "band" else "range"


@router.get("/employers/{employer_id}/scan-sheet")
def scan_sheet(ctx: Annotated[Ctx, AnyUser],
               employer_id: Annotated[int, Path(ge=1, le=9_223_372_036_854_775_807)]) -> dict[str, Any]:
    batch = active_batch(ctx.conn, ctx.user.branch_id)
    if batch is None:
        raise ApiError(404, "not_found", "BU tidak ditemukan di antrean cabang Anda.")
    row = ctx.conn.execute(
        """
        SELECT e.id, e.name, coalesce(s.name, e.kbli_sector) AS sector, e.kab_kota_code, e.reported_headcount,
               rs.score, rs.rank, rs.confidence, rs.confidence_bucket, rs.reason_codes, rs.rp_low, rs.rp_high,
               rs.rp_band, rs.sme_protection, rs.flagged_workers,
               EXISTS (SELECT 1 FROM ops.inspection i WHERE i.employer_id = e.id AND i.status = 'submitted'
                       AND i.period = %(period)s) AS inspected
        FROM core.employer e
        JOIN core.risk_score rs ON rs.employer_id = e.id AND rs.batch_id = %(batch_id)s
        LEFT JOIN core.sector s ON s.kbli = e.kbli_sector
        WHERE e.id = %(id)s AND e.branch_id = %(branch_id)s
        """,
        {"id": employer_id, "branch_id": ctx.user.branch_id, "batch_id": batch["id"],
         "period": current_period()},
    ).fetchone()
    if row is None:
        raise ApiError(404, "not_found", "BU tidak ditemukan di antrean cabang Anda.")
    ctx.audit("scan_sheet.view", resource="employer", resource_id=employer_id, detail={"batch_id": batch["id"]})
    mode = rp_mode()
    return {
        "batch": {"id": batch["id"], "period": batch["period"],
                  "published_at": batch["published_at"].isoformat() if batch["published_at"] else None},
        "employer": {"id": row["id"], "name": row["name"], "sector": row["sector"], "kab_kota": row["kab_kota_code"],
                     "reported_headcount": row["reported_headcount"]},
        "score": round(row["score"], 6), "rank": row["rank"], "confidence": round(row["confidence"], 4),
        "confidence_bucket": row["confidence_bucket"],
        "reasons": [{"code": r["code"], "text": r["text"], "evidence": r.get("evidence", {}),
                     "contribution": r.get("contribution", 0), "checklist": r.get("checklist", [])}
                    for r in row["reason_codes"]],
        "rp": {"mode": mode,
               "low": row["rp_low"] if mode == "range" else None,
               "high": row["rp_high"] if mode == "range" else None,
               "band": row["rp_band"]},
        "sme_protection": row["sme_protection"],
        "verify_first": row["sme_protection"] and row["confidence_bucket"] == "rendah",
        "flagged_workers": [{"nik_token8": w["nik_token8"][:8], "reason": w["reason"]} for w in row["flagged_workers"]],
        "inspection_status": "submitted" if row["inspected"] else "none",
    }
