"""Login, logout, /me (FR-1, FR-5, BR-23, SEC-5, SEC-6)."""
from __future__ import annotations

from datetime import timedelta
from typing import Annotated

from fastapi import APIRouter, Request, Response
from pydantic import BaseModel, ConfigDict, Field

from api import audit, db
from api.deps import SESSION_COOKIE, AnyUser, Ctx, client_ip
from api.errors import ApiError
from api.security import DUMMY_HASH, new_session_token, token_hash, verify_password

router = APIRouter(prefix="/api")

SESSION_TTL = timedelta(hours=8)
LOCKOUT_WINDOW = timedelta(minutes=15)
LOCKOUT_MAX_FAILS = 5
GENERIC_FAIL = "Username atau password salah."


class LoginIn(BaseModel):
    model_config = ConfigDict(extra="forbid")
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=256)


@router.post("/auth/login")
def login(body: LoginIn, request: Request, response: Response) -> dict[str, object]:
    ip = client_ip(request)
    uname = body.username.strip()
    with db.transaction() as conn:
        # Cleanup oportunistik (BR-23, ops.login_attempt > 1 hari).
        conn.execute("DELETE FROM ops.session WHERE expires_at <= now()")
        conn.execute("DELETE FROM ops.login_attempt WHERE at < now() - interval '1 day'")
        fail_row = conn.execute(
            "SELECT count(*) AS n FROM ops.login_attempt "
            "WHERE lower(username) = lower(%s) AND NOT success AND at > now() - %s",
            (uname, LOCKOUT_WINDOW),
        ).fetchone()
        fails = int(fail_row["n"]) if fail_row else 0
        if fails >= LOCKOUT_MAX_FAILS:
            audit.write(conn, "auth.login_locked", ip=ip, detail={"username": uname})
            locked = True
        else:
            locked = False
            user = conn.execute(
                "SELECT id, password_hash, role, branch_id FROM ops.app_user "
                "WHERE lower(username) = lower(%s) AND active", (uname,),
            ).fetchone()
            ok = verify_password(body.password, user["password_hash"] if user else DUMMY_HASH) and user is not None
            conn.execute("INSERT INTO ops.login_attempt (username, success) VALUES (%s, %s)", (uname, ok))
            if ok:
                assert user is not None
                token = new_session_token()
                conn.execute(
                    "INSERT INTO ops.session (token_hash, user_id, expires_at) VALUES (%s, %s, now() + %s)",
                    (token_hash(token), user["id"], SESSION_TTL),
                )
                audit.write(conn, "auth.login", actor_id=user["id"], role=user["role"],
                            branch_id=user["branch_id"], ip=ip)
            else:
                audit.write(conn, "auth.login_failed", ip=ip, detail={"username": uname})
    if locked:
        raise ApiError(429, "too_many_attempts", "Terlalu banyak percobaan. Coba lagi beberapa menit lagi.")
    if not ok or user is None:
        raise ApiError(401, "invalid_credentials", GENERIC_FAIL)
    response.set_cookie(SESSION_COOKIE, token, max_age=int(SESSION_TTL.total_seconds()), httponly=True,
                        secure=True, samesite="strict", path="/")
    return {"role": user["role"], "branch_id": user["branch_id"]}


@router.post("/auth/logout")
def logout(ctx: Annotated[Ctx, AnyUser], response: Response) -> dict[str, bool]:
    ctx.audit("auth.logout")
    ctx.conn.execute("RESET ROLE")  # session milik payray_app
    ctx.conn.execute("DELETE FROM ops.session WHERE token_hash = %s", (ctx.token_hash,))
    response.delete_cookie(SESSION_COOKIE, path="/", secure=True, httponly=True, samesite="strict")
    return {"ok": True}


@router.get("/me")
def me(ctx: Annotated[Ctx, AnyUser]) -> dict[str, object]:
    branch = ctx.conn.execute("SELECT name FROM core.branch WHERE id = %s", (ctx.user.branch_id,)).fetchone()
    return {"id": ctx.user.id, "username": ctx.user.username, "role": ctx.user.role,
            "branch_id": ctx.user.branch_id, "branch_name": branch["name"] if branch else None}
