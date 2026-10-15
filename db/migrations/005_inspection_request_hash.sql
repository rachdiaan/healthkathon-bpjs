-- 005: hash body request untuk Idempotency-Key (FR-16): key sama + body sama → respons sama,
-- key sama + body beda → 422 idempotency_mismatch. Hash dihitung API dari body yang sudah divalidasi.
ALTER TABLE ops.inspection ADD COLUMN request_hash char(64);
