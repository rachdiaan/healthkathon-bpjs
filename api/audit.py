"""Tulis audit.event di transaksi yang sama dengan aksi (FR-3). Detail tanpa NIK/password/notes."""
from __future__ import annotations

from typing import Any

import psycopg
from psycopg.types.json import Jsonb


def write(conn: psycopg.Connection[Any], action: str, *, actor_id: int | None = None, role: str | None = None,
          branch_id: int | None = None, resource: str | None = None, resource_id: str | int | None = None,
          ip: str | None = None, detail: dict[str, Any] | None = None) -> None:
    conn.execute(
        "INSERT INTO audit.event (actor_id, role, branch_id, action, resource, resource_id, ip, detail) "
        "VALUES (%s, %s, %s, %s, %s, %s, %s, %s)",
        (actor_id, role, branch_id, action, resource, None if resource_id is None else str(resource_id),
         ip, Jsonb(detail) if detail is not None else None),
    )
