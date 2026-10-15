"""Dependency otorisasi per request (FR-2, GR-2, GR-3).

`require_role(...)` membaca cookie session, membuka satu transaksi sebagai payray_app,
lalu `SET LOCAL ROLE payray_officer|payray_supervisor`. Semua query endpoint dan audit
jalan di transaksi itu, sehingga grant DB ikut menegakkan §10.
"""
from __future__ import annotations

import ipaddress
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from typing import Any

import psycopg
from psycopg.rows import DictRow
from fastapi import Depends, Request

from api import audit, db
from api.errors import ApiError
from api.security import token_hash

SESSION_COOKIE = "payray_session"
DB_ROLE = {"officer": "payray_officer", "supervisor": "payray_supervisor"}


@dataclass
class User:
    id: int
    username: str
    role: str
    branch_id: int


@dataclass
class Ctx:
    conn: psycopg.Connection[DictRow]
    user: User
    ip: str | None
    token_hash: str

    def audit(self, action: str, resource: str | None = None, resource_id: Any = None,
              detail: dict[str, Any] | None = None) -> None:
        audit.write(self.conn, action, actor_id=self.user.id, role=self.user.role,
                    branch_id=self.user.branch_id, resource=resource, resource_id=resource_id,
                    ip=self.ip, detail=detail)


def client_ip(request: Request) -> str | None:
    host = request.client.host if request.client else None
    try:
        return str(ipaddress.ip_address(host)) if host else None
    except ValueError:
        return None


def _lookup(conn: psycopg.Connection[DictRow], th: str) -> User | None:
    row = conn.execute(
        "SELECT u.id, u.username, u.role, u.branch_id FROM ops.session s "
        "JOIN ops.app_user u ON u.id = s.user_id "
        "WHERE s.token_hash = %s AND s.expires_at > now() AND u.active",
        (th,),
    ).fetchone()
    return User(**row) if row else None


def require_role(*roles: str) -> Any:
    allowed = frozenset(roles)

    def dependency(request: Request) -> Iterator[Ctx]:
        token = request.cookies.get(SESSION_COOKIE)
        if not token:
            raise ApiError(401, "unauthorized", "Silakan masuk dulu.")
        th = token_hash(token)
        ip = client_ip(request)
        with db.transaction() as conn:
            user = _lookup(conn, th)
            if user is None:
                raise ApiError(401, "unauthorized", "Sesi berakhir. Silakan masuk lagi.")
            if user.role not in allowed:
                audit.write(conn, "authz.denied", actor_id=user.id, role=user.role, branch_id=user.branch_id,
                            resource=request.url.path, ip=ip)
                denied = True
            else:
                denied = False
                conn.execute(f"SET LOCAL ROLE {DB_ROLE[user.role]}")
                request.state.user = user
                yield Ctx(conn=conn, user=user, ip=ip, token_hash=th)
        if denied:
            raise ApiError(403, "forbidden", "Peran Anda tidak punya akses ke fitur ini.")

    dependency.__payray_roles__ = allowed  # type: ignore[attr-defined]
    return Depends(dependency, scope="function")


Officer = require_role("officer")
Supervisor = require_role("supervisor")
AnyUser = require_role("officer", "supervisor")
RoleDep = Callable[..., Iterator[Ctx]]
