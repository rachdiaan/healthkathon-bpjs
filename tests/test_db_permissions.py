"""SEC-2 (bagian DB) dan SEC-11 (grant audit): isolasi schema label dan audit INSERT-only."""
from __future__ import annotations

import psycopg
import pytest
from psycopg import errors


def _denied(db_url: str, role: str, sql: str) -> None:
    with psycopg.connect(db_url) as conn:
        conn.execute(f"SET ROLE {role}")
        with pytest.raises(errors.InsufficientPrivilege):
            conn.execute(sql)


def test_officer_cannot_read_ground_truth(db_url: str) -> None:
    _denied(db_url, "payray_officer", "SELECT 1 FROM label.ground_truth")


def test_officer_cannot_read_inspection_outcome(db_url: str) -> None:
    _denied(db_url, "payray_officer", "SELECT 1 FROM label.inspection_outcome")


def test_scoring_cannot_read_inspection_outcome(db_url: str) -> None:
    _denied(db_url, "payray_scoring", "SELECT 1 FROM label.inspection_outcome")


def test_scoring_cannot_read_ground_truth(db_url: str) -> None:
    _denied(db_url, "payray_scoring", "SELECT 1 FROM label.ground_truth")


def test_app_cannot_update_audit(db_url: str) -> None:
    _denied(db_url, "payray_app", "UPDATE audit.event SET action = 'x'")


def test_app_cannot_delete_audit(db_url: str) -> None:
    _denied(db_url, "payray_app", "DELETE FROM audit.event WHERE id = 1")


def test_supervisor_reads_prevalence_view_not_ground_truth(db_url: str) -> None:
    with psycopg.connect(db_url) as conn:
        conn.execute("SET ROLE payray_supervisor")
        conn.execute("SELECT * FROM label.v_prevalence")
    _denied(db_url, "payray_supervisor", "SELECT 1 FROM label.ground_truth")


def test_app_inherits_nothing_without_set_role(db_url: str) -> None:
    # payray_app NOINHERIT: tanpa SET LOCAL ROLE, tidak bisa membaca antrean.
    _denied(db_url, "payray_app", "SELECT 1 FROM core.risk_score")


def test_pages_role_is_scoring_only(db_url: str) -> None:
    """007: payray_pages (secret CI di repo publik) hanya bisa jadi payray_scoring; label tertutup."""
    with psycopg.connect(db_url) as conn:
        conn.execute("SET ROLE payray_pages")
        with pytest.raises(errors.InsufficientPrivilege):
            conn.execute("SELECT 1 FROM label.ground_truth")
    with psycopg.connect(db_url) as conn:
        conn.execute("SET ROLE payray_pages")
        conn.execute("SET ROLE payray_scoring")
        with pytest.raises(errors.InsufficientPrivilege):
            conn.execute("SELECT 1 FROM label.inspection_outcome")
