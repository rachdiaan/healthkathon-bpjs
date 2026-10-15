-- 007: role login khusus untuk workflow deploy-pages (secret GitHub di repo publik).
-- NOLOGIN di migrasi; password + LOGIN disetel di luar repo (scripts/provision_pages_role.py).
-- Hak = payray_scoring saja (build_static.py menjalankan SET ROLE payray_scoring): tanpa akses schema label,
-- tanpa hak tulis di luar core.risk_score/score_batch.
DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'payray_pages') THEN
        CREATE ROLE payray_pages NOLOGIN NOINHERIT;
    END IF;
END $$;
GRANT payray_scoring TO payray_pages WITH INHERIT FALSE, SET TRUE;
