-- 002: role aplikasi dan grant sesuai PRD §10 dan §16.
-- Role adalah objek cluster, jadi dibuat idempoten (IF NOT EXISTS lewat DO block).
-- Semua role NOLOGIN di sini; password payray_app di-set di luar repo (deploy/seed lokal).

DO $$
DECLARE r text;
BEGIN
    FOREACH r IN ARRAY ARRAY['payray_officer', 'payray_supervisor', 'payray_scoring', 'payray_eval', 'payray_app'] LOOP
        IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = r) THEN
            EXECUTE format('CREATE ROLE %I NOLOGIN', r);
        END IF;
    END LOOP;
END $$;

-- payray_app: login API. NOINHERIT supaya hak officer/supervisor hanya aktif lewat SET LOCAL ROLE (FR-2).
ALTER ROLE payray_app NOINHERIT;
GRANT payray_officer, payray_supervisor TO payray_app;

-- Pastikan tidak ada hak bawaan PUBLIC ke schema aplikasi.
REVOKE ALL ON SCHEMA core, ops, label, audit FROM PUBLIC;

-- payray_app (sebelum SET ROLE): auth, session, lockout, audit, recovery batch basi (TC-5).
GRANT USAGE ON SCHEMA core, ops, audit TO payray_app;
GRANT SELECT ON ops.app_user TO payray_app;
GRANT SELECT, INSERT, DELETE ON ops.session, ops.login_attempt TO payray_app;
GRANT USAGE ON SEQUENCE ops.login_attempt_id_seq TO payray_app;
GRANT SELECT, UPDATE (status, error, finished_at) ON core.score_batch TO payray_app;
GRANT INSERT ON audit.event TO payray_app;
GRANT USAGE ON SEQUENCE audit.event_id_seq TO payray_app;

-- payray_officer: baca antrean/scan sheet, buat inspeksi, INSERT-only outcome.
GRANT USAGE ON SCHEMA core, ops, label, audit TO payray_officer;
GRANT SELECT ON core.branch, core.employer, core.wage_reference, core.score_batch, core.risk_score TO payray_officer;
GRANT SELECT, INSERT ON ops.inspection TO payray_officer;
GRANT UPDATE (status) ON ops.inspection TO payray_officer;
GRANT USAGE ON SEQUENCE ops.inspection_id_seq TO payray_officer;
GRANT INSERT ON label.inspection_outcome TO payray_officer;
GRANT INSERT ON audit.event TO payray_officer;
GRANT USAGE ON SEQUENCE audit.event_id_seq TO payray_officer;

-- payray_supervisor: tim, outcome, batch, metrik, audit log. Ground truth hanya lewat view agregat.
GRANT USAGE ON SCHEMA core, ops, label, audit TO payray_supervisor;
GRANT SELECT ON core.branch, core.employer, core.wage_reference, core.score_batch, core.risk_score TO payray_supervisor;
GRANT INSERT ON core.score_batch TO payray_supervisor;
GRANT UPDATE (status, published_at) ON core.score_batch TO payray_supervisor;
GRANT USAGE ON SEQUENCE core.score_batch_id_seq TO payray_supervisor;
GRANT SELECT ON ops.inspection, ops.metric_snapshot TO payray_supervisor;
GRANT SELECT (id, username, role, branch_id) ON ops.app_user TO payray_supervisor;
GRANT UPDATE (status, cancel_reason) ON ops.inspection TO payray_supervisor;
GRANT SELECT ON label.inspection_outcome, label.v_prevalence TO payray_supervisor;
GRANT SELECT, INSERT ON audit.event TO payray_supervisor;
GRANT USAGE ON SEQUENCE audit.event_id_seq TO payray_supervisor;

-- payray_scoring: baca core, tulis skor. Tanpa USAGE di schema label.
GRANT USAGE ON SCHEMA core TO payray_scoring;
GRANT SELECT ON ALL TABLES IN SCHEMA core TO payray_scoring;
GRANT INSERT ON core.risk_score TO payray_scoring;
GRANT UPDATE (status, n_scored, error, finished_at) ON core.score_batch TO payray_scoring;

-- payray_eval: baca label + core, tulis metric snapshot.
GRANT USAGE ON SCHEMA core, ops, label TO payray_eval;
GRANT SELECT ON ALL TABLES IN SCHEMA core TO payray_eval;
GRANT SELECT ON ALL TABLES IN SCHEMA label TO payray_eval;
GRANT SELECT, INSERT, UPDATE ON ops.metric_snapshot TO payray_eval;
