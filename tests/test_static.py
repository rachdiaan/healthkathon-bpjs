"""t25: snapshot statis tanpa label/NIK (SEC-7, SEC-8), wajib generated_at + batch.period (BUG-7)."""
from __future__ import annotations

import json
import re

import psycopg
import pytest
from psycopg.rows import dict_row


@pytest.fixture(scope="module")
def built(seeded_db, tmp_path_factory):
    from scripts.build_static import snapshot, write_site

    with psycopg.connect(seeded_db, row_factory=dict_row) as conn:
        conn.execute("SET ROLE payray_scoring")
        snap = snapshot(conn, 1, "range")
    out = tmp_path_factory.mktemp("site")
    path = write_site(out, snap)
    return out, path.read_text(encoding="utf-8")


def test_no_forbidden_keys(built) -> None:
    _, text = built
    keys = set(re.findall(r'"([a-z_0-9]+)":', text))
    for key in ("is_noncompliant", "true_loss_rp", "outcome", "violation_types", "violation_type", "nik_token"):
        assert key not in keys, key
    assert not any(k.startswith("true_loss") for k in keys)


def test_tokens_are_8_chars(built) -> None:
    _, text = built
    snap = json.loads(text)
    tokens = [w["nik_token8"] for d in snap["details"].values() for w in d["flagged_workers"]]
    assert tokens and all(len(t) == 8 for t in tokens)


def test_no_nik_pattern(built) -> None:
    _, text = built
    assert not re.search(r"\b\d{16}\b", text)
    assert not re.search(r"[0-9a-f]{64}", text)


def test_required_meta(built) -> None:
    out, text = built
    snap = json.loads(text)
    assert snap["generated_at"] and snap["batch"]["period"]
    html = (out / "index.html").read_text(encoding="utf-8")
    assert 'data-mode="static"' in html and "Content-Security-Policy" in html


def test_scoring_role_cannot_reach_label(seeded_db) -> None:
    with psycopg.connect(seeded_db) as conn:
        conn.execute("SET ROLE payray_scoring")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT 1 FROM label.ground_truth")


def test_leak_guard_rejects(tmp_path) -> None:
    from scripts.build_static import check_leaks

    for bad in ('{"outcome":"x"}', '{"a":"3201234567890123"}', '{"t":"' + "a" * 64 + '"}'):
        with pytest.raises(SystemExit):
            check_leaks(bad)
