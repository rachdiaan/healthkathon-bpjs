-- 006: di Postgres hosting (Neon/Supabase) owner bukan superuser. Sejak PG16, role pembuat (payray_migrator)
-- hanya mendapat ADMIN atas role yang dibuatnya, tanpa hak SET. Script admin (bootstrap_batch, compute_baseline,
-- build_static, eval) perlu SET ROLE ke role operasional lewat payray_migrator, jadi hak SET diberikan eksplisit.
-- INHERIT FALSE: payray_migrator tidak otomatis mewarisi hak role itu (isolasi label tetap lewat SET ROLE).
GRANT payray_scoring TO payray_migrator WITH INHERIT FALSE, SET TRUE;
GRANT payray_eval TO payray_migrator WITH INHERIT FALSE, SET TRUE;
GRANT payray_officer TO payray_migrator WITH INHERIT FALSE, SET TRUE;
GRANT payray_supervisor TO payray_migrator WITH INHERIT FALSE, SET TRUE;
GRANT payray_app TO payray_migrator WITH INHERIT FALSE, SET TRUE;
