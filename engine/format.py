"""Format angka untuk tampilan: Rp half-up ke Rp 100.000 (BR-5, BUG-2) dan bucket confidence (BR-3)."""
from __future__ import annotations

from decimal import ROUND_HALF_UP, Decimal

STEP = Decimal(100_000)


def round_rp(value: int | Decimal) -> int:
    return int((Decimal(value) / STEP).quantize(Decimal(1), rounding=ROUND_HALF_UP) * STEP)


def format_rp(value: int | Decimal) -> str:
    return "Rp " + f"{round_rp(value):,}".replace(",", ".")


def to_rp(value: float | int | Decimal) -> int:
    """Integer rupiah via Decimal (bukan float), dibulatkan half-up ke rupiah terdekat."""
    return int(Decimal(str(value)).quantize(Decimal(1), rounding=ROUND_HALF_UP))


def confidence_bucket(c: float) -> str:
    """Interval setengah terbuka: tinggi c ≥ 0,70; sedang 0,40 ≤ c < 0,70; rendah c < 0,40."""
    if c >= 0.70:
        return "tinggi"
    if c >= 0.40:
        return "sedang"
    return "rendah"
