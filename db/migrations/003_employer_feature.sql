-- 003: fitur per BU hasil engine/features.py, dihitung saat seed dari data sintetis multi-tahun.
-- Batch scoring (payray_scoring) membaca tabel ini, sehingga tidak butuh file CSV di runtime.
CREATE TABLE core.employer_feature (
    employer_id  bigint PRIMARY KEY REFERENCES core.employer,
    period       char(7) NOT NULL CHECK (period ~ '^\d{4}-(0[1-9]|1[0-2])$'),
    features     jsonb NOT NULL
);

GRANT SELECT ON core.employer_feature TO payray_scoring, payray_eval;

-- Worker rescore di proses API: payray_app boleh SET LOCAL ROLE payray_scoring (NOINHERIT tetap berlaku).
GRANT payray_scoring TO payray_app;
