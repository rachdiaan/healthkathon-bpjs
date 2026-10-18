"""Pool koneksi Postgres. Di production DATABASE_URL login sebagai payray_app (NOINHERIT)."""
from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

import psycopg
from psycopg.rows import DictRow, dict_row
from psycopg_pool import ConnectionPool

_pool: ConnectionPool[psycopg.Connection[DictRow]] | None = None


def pool() -> ConnectionPool[psycopg.Connection[DictRow]]:
    global _pool
    if _pool is None:
        url = os.environ["DATABASE_URL"]
        # Neon menidurkan compute setelah idle dan memutus koneksi (AdminShutdown). check_connection
        # mengetes koneksi sebelum dipinjam; max_idle menutup koneksi diam sebelum diputus server.
        _pool = ConnectionPool(url, connection_class=psycopg.Connection[DictRow], min_size=1, max_size=int(os.environ.get("PAYRAY_POOL_MAX", "8")),
                               kwargs={"row_factory": dict_row}, open=True, timeout=10,
                               check=ConnectionPool.check_connection, max_idle=240)
    return _pool


def reset_pool() -> None:
    global _pool
    if _pool is not None:
        _pool.close()
    _pool = None


@contextmanager
def transaction() -> Iterator[psycopg.Connection[DictRow]]:
    """Satu transaksi per request. Commit bila sukses, rollback bila exception."""
    with pool().connection() as conn, conn.transaction():
        yield conn
