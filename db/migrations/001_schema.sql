-- 001: schema v2 (core, ops, label, audit) sesuai PRD §16.
--
-- Perbedaan dengan db/schema.sql (v1, skema publik/referensi/label):
-- * v1 dipakai loader CSV lama (scripts/load_postgres.py) dan dibiarkan apa adanya.
--   v2 membuat schema baru; tidak ada tabel v1 yang diubah atau dihapus.
-- * ID BU di repo berupa teks (mis. BU04224). PRD meminta bigint, jadi core.employer.id
--   bigint dan kode asli disimpan di core.employer.code (UNIQUE).
-- * referensi.umk + referensi.benchmark_upah digabung jadi core.wage_reference
--   (median sektor per KBLI disimpan sebagai jsonb).
-- * publik.workers.worker_id (pseudonim v1) diganti core.worker.nik_token (HMAC-SHA256, FR-4).
-- * label.labels v1 dipetakan ke label.ground_truth (is_noncompliant, violation_type, true_loss_rp).
-- * username memakai text + unique index lower(username) (keputusan t3: tanpa citext).
-- * core.risk_score.rp_band ditambahkan untuk mode band KILL-5 (keputusan t14).

CREATE SCHEMA IF NOT EXISTS core;
CREATE SCHEMA IF NOT EXISTS ops;
CREATE SCHEMA IF NOT EXISTS label;
CREATE SCHEMA IF NOT EXISTS audit;

-- core ------------------------------------------------------------------------
CREATE TABLE core.branch (
    id             smallint PRIMARY KEY,
    name           text NOT NULL,
    kab_kota_code  text NOT NULL
);

CREATE TABLE core.employer (
    id                  bigint PRIMARY KEY,
    code                text NOT NULL UNIQUE,
    branch_id           smallint NOT NULL REFERENCES core.branch,
    name                text NOT NULL,
    kbli_sector         text NOT NULL,
    kab_kota_code       text NOT NULL,
    reported_headcount  int NOT NULL CHECK (reported_headcount >= 0),
    is_sme              boolean NOT NULL,
    is_labor_intensive  boolean NOT NULL,
    active              boolean NOT NULL DEFAULT true
);
CREATE INDEX employer_branch_idx ON core.employer (branch_id);

CREATE TABLE core.worker (
    id                bigint PRIMARY KEY,
    employer_id       bigint NOT NULL REFERENCES core.employer,
    nik_token         char(64) NOT NULL,
    period            char(7) NOT NULL CHECK (period ~ '^\d{4}-(0[1-9]|1[0-2])$'),
    segment           text CHECK (segment IN ('PPU', 'PBPU')),
    reported_wage_rp  bigint NOT NULL CHECK (reported_wage_rp >= 0),
    UNIQUE (employer_id, nik_token, period)
);
CREATE INDEX worker_nik_token_idx ON core.worker (nik_token);

CREATE TABLE core.wage_reference (
    kab_kota_code          text NOT NULL,
    year                   smallint NOT NULL,
    umk_rp                 bigint NOT NULL,
    sector_median_wage_rp  jsonb,
    source_url             text NOT NULL,
    accessed_on            date NOT NULL,
    PRIMARY KEY (kab_kota_code, year)
);

CREATE TABLE ops.app_user (
    id             bigserial PRIMARY KEY,
    username       text NOT NULL,
    password_hash  text NOT NULL,
    role           text NOT NULL CHECK (role IN ('officer', 'supervisor')),
    branch_id      smallint NOT NULL REFERENCES core.branch,
    active         boolean NOT NULL DEFAULT true
);
CREATE UNIQUE INDEX app_user_username_lower_idx ON ops.app_user (lower(username));

CREATE TABLE core.score_batch (
    id              bigserial PRIMARY KEY,
    branch_id       smallint NOT NULL REFERENCES core.branch,
    period          char(7) NOT NULL CHECK (period ~ '^\d{4}-(0[1-9]|1[0-2])$'),
    status          text NOT NULL CHECK (status IN ('running', 'ready', 'published', 'failed', 'archived')),
    model_version   char(64) NOT NULL,
    engine_version  text NOT NULL,
    n_scored        int,
    error           text,
    created_by      bigint REFERENCES ops.app_user,
    created_at      timestamptz NOT NULL DEFAULT now(),
    finished_at     timestamptz,
    published_at    timestamptz
);
-- FR-22: maksimal 1 batch running secara global. BR-14: tepat 1 published per cabang.
CREATE UNIQUE INDEX score_batch_one_running_idx ON core.score_batch ((true)) WHERE status = 'running';
CREATE UNIQUE INDEX score_batch_one_published_idx ON core.score_batch (branch_id) WHERE status = 'published';

CREATE TABLE core.risk_score (
    batch_id           bigint NOT NULL REFERENCES core.score_batch,
    employer_id        bigint NOT NULL REFERENCES core.employer,
    score              double precision NOT NULL CHECK (score >= 0 AND score <= 1),
    rank               int NOT NULL,
    confidence         double precision NOT NULL,
    confidence_bucket  text NOT NULL CHECK (confidence_bucket IN ('tinggi', 'sedang', 'rendah')),
    reason_codes       jsonb NOT NULL,
    rp_low             bigint NOT NULL,
    rp_point           bigint NOT NULL,
    rp_high            bigint NOT NULL,
    rp_band            text CHECK (rp_band IN ('rendah', 'sedang', 'tinggi')),
    sme_protection     boolean NOT NULL,
    flagged_workers    jsonb NOT NULL DEFAULT '[]',
    PRIMARY KEY (batch_id, employer_id),
    UNIQUE (batch_id, rank),
    CHECK (rp_low >= 0 AND rp_low <= rp_point AND rp_point <= rp_high)
);

-- ops -------------------------------------------------------------------------
CREATE TABLE ops.session (
    token_hash  char(64) PRIMARY KEY,
    user_id     bigint NOT NULL REFERENCES ops.app_user,
    created_at  timestamptz NOT NULL DEFAULT now(),
    expires_at  timestamptz NOT NULL
);

CREATE TABLE ops.login_attempt (
    id        bigserial PRIMARY KEY,
    username  text NOT NULL,
    at        timestamptz NOT NULL DEFAULT now(),
    success   boolean NOT NULL
);
CREATE INDEX login_attempt_user_at_idx ON ops.login_attempt (lower(username), at);

CREATE TABLE ops.inspection (
    id                 bigserial PRIMARY KEY,
    employer_id        bigint NOT NULL REFERENCES core.employer,
    branch_id          smallint NOT NULL REFERENCES core.branch,
    officer_id         bigint NOT NULL REFERENCES ops.app_user,
    batch_id           bigint NOT NULL REFERENCES core.score_batch,
    rank_at_selection  int NOT NULL,
    inspected_on       date NOT NULL,
    period             char(7) NOT NULL CHECK (period ~ '^\d{4}-(0[1-9]|1[0-2])$'),
    status             text NOT NULL CHECK (status IN ('submitted', 'superseded', 'cancelled')),
    supersedes_id      bigint REFERENCES ops.inspection,
    cancel_reason      text CHECK (cancel_reason IS NULL OR length(cancel_reason) BETWEEN 10 AND 500),
    idempotency_key    uuid NOT NULL,
    created_at         timestamptz NOT NULL DEFAULT now(),
    UNIQUE (officer_id, idempotency_key)
);
-- BR-10: satu inspeksi submitted per BU per periode.
CREATE UNIQUE INDEX inspection_one_submitted_idx ON ops.inspection (employer_id, period) WHERE status = 'submitted';
CREATE INDEX inspection_branch_period_idx ON ops.inspection (branch_id, period);

CREATE TABLE ops.metric_snapshot (
    branch_id            smallint NOT NULL REFERENCES core.branch,
    period               char(7) NOT NULL,
    baseline_prevalence  numeric(6, 5) NOT NULL,
    n_active             int NOT NULL,
    computed_at          timestamptz NOT NULL DEFAULT now(),
    source               text NOT NULL,
    PRIMARY KEY (branch_id, period)
);

-- label -----------------------------------------------------------------------
CREATE TABLE label.inspection_outcome (
    inspection_id    bigint PRIMARY KEY REFERENCES ops.inspection,
    outcome          text NOT NULL CHECK (outcome IN ('violation_found', 'no_violation', 'inconclusive')),
    violation_types  text[] NOT NULL DEFAULT '{}'
        CHECK (violation_types <@ ARRAY['under_reported_wage', 'partial_registration', 'ppu_to_pbpu_shift', 'other']),
    rp_found         bigint CHECK (rp_found IS NULL OR (rp_found >= 0 AND rp_found <= 1000000000000)),
    notes            text CHECK (notes IS NULL OR length(notes) <= 1000)
);

CREATE TABLE label.ground_truth (
    employer_id      bigint NOT NULL REFERENCES core.employer,
    period           char(7) NOT NULL,
    dataset          text NOT NULL CHECK (dataset IN ('train', 'validation', 'holdout', 'blind')),
    is_noncompliant  boolean NOT NULL,
    violation_type   text,
    true_loss_rp     bigint NOT NULL DEFAULT 0,
    PRIMARY KEY (employer_id, period)
);

-- Agregat prevalensi per cabang/periode. Supervisor hanya boleh membaca view ini.
CREATE VIEW label.v_prevalence AS
SELECT e.branch_id,
       g.period,
       count(*)                                  AS n_active,
       count(*) FILTER (WHERE g.is_noncompliant) AS n_noncompliant
FROM label.ground_truth g
JOIN core.employer e ON e.id = g.employer_id
WHERE e.active
GROUP BY e.branch_id, g.period;

-- audit -----------------------------------------------------------------------
CREATE TABLE audit.event (
    id           bigserial PRIMARY KEY,
    at           timestamptz NOT NULL DEFAULT now(),
    actor_id     bigint,
    role         text,
    branch_id    smallint,
    action       text NOT NULL,
    resource     text,
    resource_id  text,
    ip           inet,
    detail       jsonb
);
CREATE INDEX audit_event_branch_id_idx ON audit.event (branch_id, id DESC);
