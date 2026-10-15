"""Metrik supervisor (FR-26..FR-28, BR-16..BR-18) dan audit log (FR-29)."""
from __future__ import annotations

import base64
import binascii
import json
from datetime import date, datetime, time, timedelta
from typing import Annotated, Any
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Query

from api.deps import Ctx, Supervisor
from api.errors import ApiError
from api.queue import active_batch

router = APIRouter(prefix="/api")
WIB = ZoneInfo("Asia/Jakarta")
MIN_DECIDED = 10
PERIOD_RE = r"^\d{4}-(0[1-9]|1[0-2])$"
BASELINE_LABEL = "Baseline acak (prevalensi sintetis)"


def compute_metrics(ctx: Ctx, period: str) -> dict[str, Any]:
    counts = ctx.conn.execute(
        "SELECT count(*) FILTER (WHERE o.outcome = 'violation_found') AS hit, "
        "       count(*) FILTER (WHERE o.outcome IN ('violation_found', 'no_violation')) AS decided, "
        "       count(*) FILTER (WHERE o.outcome = 'inconclusive') AS inconclusive "
        "FROM ops.inspection i JOIN label.inspection_outcome o ON o.inspection_id = i.id "
        "WHERE i.branch_id = %s AND i.period = %s AND i.status = 'submitted'",
        (ctx.user.branch_id, period),
    ).fetchone()
    assert counts is not None
    hit, decided, inconclusive = int(counts["hit"]), int(counts["decided"]), int(counts["inconclusive"])
    snap = ctx.conn.execute(
        "SELECT baseline_prevalence, n_active, computed_at, source FROM ops.metric_snapshot "
        "WHERE branch_id = %s AND period = %s", (ctx.user.branch_id, period),
    ).fetchone()
    baseline = float(snap["baseline_prevalence"]) if snap else None
    insufficient = decided < MIN_DECIDED
    hit_rate = None if insufficient else round(hit / decided, 4)
    lift = None
    if hit_rate is not None and baseline:
        lift = round(hit_rate / baseline, 2)

    batch = active_batch(ctx.conn, ctx.user.branch_id)
    covered = 0
    if batch:
        row = ctx.conn.execute(
            "SELECT count(DISTINCT rs.employer_id) AS n FROM core.risk_score rs "
            "JOIN ops.inspection i ON i.employer_id = rs.employer_id AND i.status = 'submitted' AND i.period = %s "
            "WHERE rs.batch_id = %s AND rs.rank <= 10", (period, batch["id"]),
        ).fetchone()
        covered = int(row["n"]) if row else 0
    return {
        "period": period, "n_decided": decided, "n_inconclusive": inconclusive, "n_hit": hit,
        "hit_rate": hit_rate, "baseline": baseline, "baseline_label": BASELINE_LABEL,
        "baseline_source": snap["source"] if snap else None,
        "lift": lift, "lift_na": hit_rate is not None and not baseline,
        "coverage_top10": round(covered / 10, 2), "computed_at": snap["computed_at"].isoformat() if snap else None,
        "insufficient": insufficient,
    }


@router.get("/metrics")
def metrics(ctx: Annotated[Ctx, Supervisor],
            period: Annotated[str | None, Query(pattern=PERIOD_RE)] = None) -> dict[str, Any]:
    p = period or datetime.now(WIB).strftime("%Y-%m")
    return compute_metrics(ctx, p)


def _cursor(raw: str | None) -> int | None:
    if not raw:
        return None
    try:
        v = json.loads(base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4)))["before_id"]
    except (binascii.Error, ValueError, KeyError, TypeError, UnicodeDecodeError) as exc:
        raise ApiError(422, "invalid_cursor", "Cursor tidak valid.", {"cursor": "format tidak dikenal"}) from exc
    if type(v) is not int or v < 1:
        raise ApiError(422, "invalid_cursor", "Cursor tidak valid.", {"cursor": "harus bilangan bulat"})
    return v


@router.get("/audit-events")
def audit_events(ctx: Annotated[Ctx, Supervisor],
                 limit: Annotated[int, Query(ge=1, le=100)] = 50,
                 cursor: Annotated[str | None, Query(max_length=200)] = None,
                 action: Annotated[str | None, Query(max_length=64, pattern=r"^[a-z_.]+$")] = None,
                 actor_id: Annotated[int | None, Query(ge=1)] = None,
                 from_: Annotated[date | None, Query(alias="from")] = None,
                 to: Annotated[date | None, Query()] = None) -> dict[str, Any]:
    before = _cursor(cursor)
    start = datetime.combine(from_, time.min, WIB) if from_ else None
    end = datetime.combine(to + timedelta(days=1), time.min, WIB) if to else None
    rows = ctx.conn.execute(
        "SELECT a.id, a.at, a.actor_id, u.username AS actor, a.role, a.action, a.resource, a.resource_id, "
        "host(a.ip) AS ip, a.detail FROM audit.event a LEFT JOIN ops.app_user u ON u.id = a.actor_id "
        "WHERE a.branch_id = %(branch)s "
        "AND (%(before)s::bigint IS NULL OR a.id < %(before)s) "
        "AND (%(action)s::text IS NULL OR a.action = %(action)s) "
        "AND (%(actor)s::bigint IS NULL OR a.actor_id = %(actor)s) "
        "AND (%(start)s::timestamptz IS NULL OR a.at >= %(start)s) "
        "AND (%(end)s::timestamptz IS NULL OR a.at < %(end)s) "
        "ORDER BY a.id DESC LIMIT %(limit)s",
        {"branch": ctx.user.branch_id, "before": before, "action": action, "actor": actor_id,
         "start": start, "end": end, "limit": limit + 1},
    ).fetchall()
    more = len(rows) > limit
    rows = rows[:limit]
    ctx.audit("audit.read", resource="audit", detail={"action": action, "actor_id": actor_id, "n": len(rows)})
    nxt = None
    if more and rows:
        nxt = base64.urlsafe_b64encode(json.dumps({"before_id": rows[-1]["id"]}).encode()).decode().rstrip("=")
    return {"items": [{**r, "at": r["at"].isoformat()} for r in rows], "next_cursor": nxt}
