-- 004: referensi nama sektor KBLI untuk tampilan antrean/scan sheet.
CREATE TABLE core.sector (
    kbli               text PRIMARY KEY,
    name               text NOT NULL,
    is_labor_intensive boolean NOT NULL
);

GRANT SELECT ON core.sector TO payray_officer, payray_supervisor, payray_scoring, payray_eval;
