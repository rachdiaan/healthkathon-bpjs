"""Hasil inspeksi (FR-16..FR-20, BR-7..BR-13, BR-24)."""
from __future__ import annotations

import hashlib
import json
import uuid
from datetime import date, datetime, timedelta
from enum import Enum
from typing import Annotated, Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Header, Path, Query, Response
from psycopg import errors
from pydantic import BaseModel, ConfigDict, Field, model_validator

from api.deps import Ctx, Officer, Supervisor
from api.errors import ApiError
from api.queue import active_batch

router = APIRouter(prefix="/api")
WIB = ZoneInfo("Asia/Jakarta")
MAX_BACKDATE_DAYS = 30
SUPERSEDE_WINDOW = timedelta(days=7)


def now_utc() -> datetime:
    """Satu titik waktu supaya tes bisa membekukan jam (BUG-1)."""
    return datetime.now(ZoneInfo("UTC"))


def today_wib() -> date:
    return now_utc().astimezone(WIB).date()


class Outcome(str, Enum):
    violation_found = "violation_found"
    no_violation = "no_violation"
    inconclusive = "inconclusive"


class ViolationType(str, Enum):
    under_reported_wage = "under_reported_wage"
    partial_registration = "partial_registration"
    ppu_to_pbpu_shift = "ppu_to_pbpu_shift"
    other = "other"


class InspectionIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    employer_id: int = Field(ge=1)
    inspected_on: date
    outcome: Outcome
    violation_types: list[ViolationType] = Field(default_factory=list, max_length=4)
    rp_found: int | None = Field(default=None, ge=0, le=1_000_000_000_000)
    notes: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _rules(self) -> InspectionIn:
        if len(set(self.violation_types)) != len(self.violation_types):
            raise ValueError("violation_types tidak boleh berulang")
        if self.outcome is Outcome.violation_found and not self.violation_types:
            raise ValueError("violation_types wajib diisi bila outcome violation_found")
        if self.outcome is not Outcome.violation_found and self.violation_types:
            raise ValueError("violation_types harus kosong bila outcome bukan violation_found")
        if self.rp_found is not None and self.outcome is not Outcome.violation_found:
            raise ValueError("rp_found hanya boleh bila outcome violation_found")
        return self

    def canonical_hash(self) -> str:
        data = self.model_dump(mode="json")
        data["violation_types"] = sorted(data["violation_types"])
        return hashlib.sha256(json.dumps(data, sort_keys=True).encode()).hexdigest()


def _parse_key(raw: str | None) -> uuid.UUID:
    try:
        return uuid.UUID(str(raw))
    except ValueError as exc:
        raise ApiError(422, "validation_error", "Header Idempotency-Key wajib berupa UUID.",
                       {"Idempotency-Key": "UUID tidak valid"}) from exc


def _check_date(d: date, published_at: datetime | None) -> None:
    today = today_wib()
    if d > today:
        raise ApiError(422, "validation_error", "Tanggal inspeksi tidak boleh di masa depan.",
                       {"inspected_on": "tidak boleh setelah hari ini (WIB)"})
    if d < today - timedelta(days=MAX_BACKDATE_DAYS):
        raise ApiError(422, "validation_error", "Tanggal inspeksi terlalu lama.",
                       {"inspected_on": f"maksimal {MAX_BACKDATE_DAYS} hari ke belakang"})
    if published_at is not None and d < published_at.astimezone(WIB).date():
        raise ApiError(422, "validation_error", "Tanggal inspeksi sebelum batch aktif dipublikasikan.",
                       {"inspected_on": "tidak boleh sebelum tanggal publikasi batch aktif"})


def _insert(ctx: Ctx, body: InspectionIn, key: uuid.UUID, supersedes_id: int | None = None) -> dict[str, Any]:
    batch = active_batch(ctx.conn, ctx.user.branch_id)
    if batch is None:
        raise ApiError(404, "not_found", "BU tidak ada di antrean cabang Anda.")
    sel = ctx.conn.execute(
        "SELECT rs.rank FROM core.risk_score rs JOIN core.employer e ON e.id = rs.employer_id "
        "WHERE rs.batch_id = %s AND rs.employer_id = %s AND e.branch_id = %s",
        (batch["id"], body.employer_id, ctx.user.branch_id),
    ).fetchone()
    if sel is None:
        raise ApiError(404, "not_found", "BU tidak ada di antrean cabang Anda.")
    _check_date(body.inspected_on, batch["published_at"])
    period = body.inspected_on.strftime("%Y-%m")
    ctx.conn.execute("SAVEPOINT ins")
    try:
        row = ctx.conn.execute(
            "INSERT INTO ops.inspection (employer_id, branch_id, officer_id, batch_id, rank_at_selection, "
            "inspected_on, period, status, supersedes_id, idempotency_key, request_hash) "
            "VALUES (%s, %s, %s, %s, %s, %s, %s, 'submitted', %s, %s, %s) RETURNING id",
            (body.employer_id, ctx.user.branch_id, ctx.user.id, batch["id"], sel["rank"], body.inspected_on, period,
             supersedes_id, key, body.canonical_hash()),
        ).fetchone()
    except errors.UniqueViolation as exc:
        ctx.conn.execute("ROLLBACK TO SAVEPOINT ins")
        if "idempotency" in (exc.diag.constraint_name or ""):
            raise ApiError(409, "idempotency_conflict", "Permintaan yang sama sedang diproses.") from exc
        raise ApiError(409, "already_inspected_this_period", "BU ini sudah diperiksa periode ini.") from exc
    assert row is not None
    # Officer hanya punya hak INSERT di schema label: tanpa RETURNING (FR-17).
    ctx.conn.execute(
        "INSERT INTO label.inspection_outcome (inspection_id, outcome, violation_types, rp_found, notes) "
        "VALUES (%s, %s, %s, %s, %s)",
        (row["id"], body.outcome.value, [v.value for v in body.violation_types], body.rp_found, body.notes),
    )
    return {"id": row["id"], "status": "submitted", "period": period}


def _replay(ctx: Ctx, key: uuid.UUID, body: InspectionIn) -> dict[str, Any] | None:
    prev = ctx.conn.execute(
        "SELECT id, period, request_hash FROM ops.inspection WHERE officer_id = %s AND idempotency_key = %s",
        (ctx.user.id, key),
    ).fetchone()
    if prev is None:
        return None
    if prev["request_hash"] != body.canonical_hash():
        raise ApiError(422, "idempotency_mismatch", "Idempotency-Key sudah dipakai untuk isi yang berbeda.")
    return {"id": prev["id"], "status": "submitted", "period": prev["period"]}


@router.post("/inspections", status_code=201)
def submit(ctx: Annotated[Ctx, Officer], body: InspectionIn, response: Response,
           idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None) -> dict[str, Any]:
    key = _parse_key(idempotency_key)
    replay = _replay(ctx, key, body)
    if replay is not None:
        response.status_code = 200
        return replay
    out = _insert(ctx, body, key)
    ctx.audit("inspection.submit", resource="inspection", resource_id=out["id"],
              detail={"employer_id": body.employer_id, "period": out["period"]})
    return out


@router.get("/inspections/mine")
def mine(ctx: Annotated[Ctx, Officer]) -> dict[str, Any]:
    rows = ctx.conn.execute(
        "SELECT i.id, i.employer_id, e.name AS employer_name, i.rank_at_selection, i.inspected_on, i.period, "
        "i.status, i.supersedes_id, i.cancel_reason, i.created_at "
        "FROM ops.inspection i JOIN core.employer e ON e.id = i.employer_id "
        "WHERE i.officer_id = %s ORDER BY i.created_at DESC, i.id DESC LIMIT 200",
        (ctx.user.id,),
    ).fetchall()
    now = now_utc()
    return {"items": [{
        "id": r["id"], "employer_id": r["employer_id"], "employer_name": r["employer_name"],
        "rank_at_selection": r["rank_at_selection"], "inspected_on": r["inspected_on"].isoformat(),
        "period": r["period"], "status": r["status"], "supersedes_id": r["supersedes_id"],
        "cancel_reason": r["cancel_reason"], "created_at": r["created_at"].isoformat(),
        "can_correct": r["status"] == "submitted" and now - r["created_at"] <= SUPERSEDE_WINDOW,
    } for r in rows]}


@router.post("/inspections/{inspection_id}/supersede", status_code=201)
def supersede(ctx: Annotated[Ctx, Officer], inspection_id: Annotated[int, Path(ge=1)], body: InspectionIn,
              response: Response,
              idempotency_key: Annotated[str | None, Header(alias="Idempotency-Key")] = None) -> dict[str, Any]:
    key = _parse_key(idempotency_key)
    replay = _replay(ctx, key, body)
    if replay is not None:
        response.status_code = 200
        return replay
    old = ctx.conn.execute(
        "SELECT id, officer_id, branch_id, employer_id, status, created_at FROM ops.inspection "
        "WHERE id = %s FOR UPDATE",
        (inspection_id,),
    ).fetchone()
    if old is None or old["branch_id"] != ctx.user.branch_id:
        raise ApiError(404, "not_found", "Inspeksi tidak ditemukan.")
    if old["officer_id"] != ctx.user.id:
        raise ApiError(403, "forbidden", "Hanya petugas yang mencatat inspeksi ini yang boleh mengoreksinya.")
    if old["status"] != "submitted":
        raise ApiError(409, "not_submitted", "Hanya inspeksi berstatus tersimpan yang bisa dikoreksi.")
    if now_utc() - old["created_at"] > SUPERSEDE_WINDOW:
        raise ApiError(403, "correction_window_closed", "Batas koreksi 7 hari sudah lewat.")
    if body.employer_id != old["employer_id"]:
        raise ApiError(422, "validation_error", "Koreksi harus untuk BU yang sama.",
                       {"employer_id": "tidak boleh diganti"})
    ctx.conn.execute("UPDATE ops.inspection SET status = 'superseded' WHERE id = %s", (inspection_id,))
    out = _insert(ctx, body, key, supersedes_id=inspection_id)
    ctx.audit("inspection.supersede", resource="inspection", resource_id=out["id"],
              detail={"supersedes_id": inspection_id, "employer_id": body.employer_id})
    return out


class CancelIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    reason: str = Field(min_length=10, max_length=500)


@router.post("/inspections/{inspection_id}/cancel")
def cancel(ctx: Annotated[Ctx, Supervisor], inspection_id: Annotated[int, Path(ge=1)],
           body: CancelIn) -> dict[str, Any]:
    reason = body.reason.strip()
    if len(reason) < 10:
        raise ApiError(422, "validation_error", "Alasan pembatalan minimal 10 karakter.", {"reason": "minimal 10 karakter"})
    row = ctx.conn.execute(
        "UPDATE ops.inspection SET status = 'cancelled', cancel_reason = %s "
        "WHERE id = %s AND branch_id = %s AND status = 'submitted' RETURNING id",
        (reason, inspection_id, ctx.user.branch_id),
    ).fetchone()
    if row is None:
        exists = ctx.conn.execute("SELECT status FROM ops.inspection WHERE id = %s AND branch_id = %s",
                                  (inspection_id, ctx.user.branch_id)).fetchone()
        if exists is None:
            raise ApiError(404, "not_found", "Inspeksi tidak ditemukan.")
        raise ApiError(409, "not_submitted", "Hanya inspeksi berstatus tersimpan yang bisa dibatalkan.")
    ctx.audit("inspection.cancel", resource="inspection", resource_id=inspection_id)
    return {"id": inspection_id, "status": "cancelled"}


@router.get("/inspections")
def team_inspections(ctx: Annotated[Ctx, Supervisor],
                     period: Annotated[str | None, Query(pattern=r"^\d{4}-(0[1-9]|1[0-2])$")] = None
                     ) -> dict[str, Any]:
    rows = ctx.conn.execute(
        "SELECT i.id, i.employer_id, e.name AS employer_name, i.officer_id, u.username AS officer, "
        "i.rank_at_selection, i.inspected_on, i.period, i.status, i.cancel_reason, i.supersedes_id, i.created_at, "
        "o.outcome, o.violation_types, o.rp_found "
        "FROM ops.inspection i JOIN core.employer e ON e.id = i.employer_id "
        "JOIN ops.app_user u ON u.id = i.officer_id "
        "LEFT JOIN label.inspection_outcome o ON o.inspection_id = i.id "
        "WHERE i.branch_id = %s AND (%s::text IS NULL OR i.period = %s) "
        "ORDER BY i.created_at DESC, i.id DESC LIMIT 200",
        (ctx.user.branch_id, period, period),
    ).fetchall()
    ctx.audit("inspection.list", resource="inspection", detail={"period": period})
    return {"items": [{**{k: v for k, v in r.items() if k not in ("inspected_on", "created_at")},
                       "inspected_on": r["inspected_on"].isoformat(), "created_at": r["created_at"].isoformat()}
                      for r in rows]}
