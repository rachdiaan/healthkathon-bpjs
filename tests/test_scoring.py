"""t9: paritas skor Python vs browser (BUG-8), urutan stabil (BUG-5), bucket (BUG-9), Rp (BUG-2), GR-5."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from engine import ml_model
from engine.format import confidence_bucket, format_rp
from engine.score_batch import OutputInvalid, Row, finalize, validate

REF = Path(__file__).resolve().parent.parent / "ml" / "reference_scores.json"


@pytest.fixture(scope="module")
def reference() -> dict:
    return json.loads(REF.read_text(encoding="utf-8"))


def test_reference_matches_current_model(reference) -> None:
    assert reference["model_sha256"] == ml_model.model_version()
    assert len(reference["rows"]) == 5000


def test_parity_scores_within_1e6(reference) -> None:
    model = ml_model.load()
    gaps = [abs(ml_model.predict(model, r["x"], r["pr"]) - r["score_js"]) for r in reference["rows"]]
    assert max(gaps) <= 1e-6


def test_parity_rank_identical(reference) -> None:
    model = ml_model.load()
    py = sorted(reference["rows"], key=lambda r: (-ml_model.predict(model, r["x"], r["pr"]), r["employer_id"]))
    js = sorted(reference["rows"], key=lambda r: r["rank_js"])
    assert [r["employer_id"] for r in py] == [r["employer_id"] for r in js]


def _row(eid: int, score: float) -> Row:
    return Row(employer_id=eid, score=score, confidence=0.9, rp_point=1_000_000, sme_protection=False,
               reasons=[{"code": "UPAH_BEKU", "text": "x", "contribution": 1.0, "evidence": {}, "checklist": []}],
               branch_id=1)


def test_identical_scores_ordered_by_employer_id() -> None:
    for perm in ([30, 10, 20], [20, 30, 10], [10, 20, 30]):
        rows = finalize([_row(e, 0.5) for e in perm] + [_row(99, 0.9)])
        ranked = sorted(rows, key=lambda r: r.rank)
        assert [r.employer_id for r in ranked] == [99, 10, 20, 30]


@pytest.mark.parametrize("c,expected", [(0.3999, "rendah"), (0.40, "sedang"), (0.6999, "sedang"), (0.70, "tinggi")])
def test_confidence_bucket_boundaries(c: float, expected: str) -> None:
    assert confidence_bucket(c) == expected


@pytest.mark.parametrize("v,expected", [(149_999_999, "Rp 150.000.000"), (150_049_999, "Rp 150.000.000"),
                                        (150_050_000, "Rp 150.100.000")])
def test_format_rp_half_up(v: int, expected: str) -> None:
    assert format_rp(v) == expected


def test_validate_rejects_bad_rows() -> None:
    good = finalize([_row(1, 0.5)])
    validate(good)
    bad = finalize([_row(2, 0.5)])
    bad[0].reasons = [{"code": "TIDAK_ADA", "text": "", "contribution": 0, "evidence": {}, "checklist": []}]
    with pytest.raises(OutputInvalid):
        validate(bad)
    nan = finalize([_row(3, 0.5)])
    nan[0].score = float("nan")
    with pytest.raises(OutputInvalid):
        validate(nan)


def test_score_batch_writes_valid_rows(seeded_db) -> None:
    import psycopg

    from engine.score_batch import score_batch

    with psycopg.connect(seeded_db) as conn:
        bid = conn.execute(
            "INSERT INTO core.score_batch (branch_id, period, status, model_version, engine_version) "
            "VALUES (1, '2026-09', 'running', %s, 'test') RETURNING id", (ml_model.model_version(),)).fetchone()[0]
        conn.commit()
        with conn.transaction():
            conn.execute("SET LOCAL ROLE payray_scoring")
            n = score_batch(conn, bid)
        rows = conn.execute("SELECT count(*), min(rank), max(rank), bool_and(rp_low <= rp_point AND rp_point <= rp_high),"
                            " bool_and(jsonb_array_length(reason_codes) > 0) FROM core.risk_score WHERE batch_id = %s",
                            (bid,)).fetchone()
        status = conn.execute("SELECT status FROM core.score_batch WHERE id = %s", (bid,)).fetchone()[0]
        conn.execute("DELETE FROM core.risk_score WHERE batch_id = %s", (bid,))
        conn.execute("DELETE FROM core.score_batch WHERE id = %s", (bid,))
        conn.commit()
    assert n > 0 and rows == (n, 1, n, True, True) and status == "ready"
