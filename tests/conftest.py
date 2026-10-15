"""Guard GR-13: tes hanya boleh jalan terhadap DB yang namanya berakhiran _test."""
from __future__ import annotations

import os
from urllib.parse import urlparse

import pytest


def _db_name(url: str) -> str:
    return urlparse(url).path.lstrip("/").split("?")[0]


def pytest_configure(config: pytest.Config) -> None:
    url = os.environ.get("DATABASE_URL", "")
    if url and not _db_name(url).endswith("_test"):
        pytest.exit(
            f"DATABASE_URL menunjuk DB '{_db_name(url)}', bukan *_test. Tes dihentikan (GR-13).",
            returncode=4,
        )


@pytest.fixture(scope="session")
def db_url() -> str:
    """URL admin ke DB *_test yang sudah dimigrasi. Tes DB gagal jelas bila DATABASE_URL kosong."""
    url = os.environ.get("DATABASE_URL", "")
    if not url:
        pytest.fail("Tes DB butuh DATABASE_URL ke DB *_test (lihat README).")
    from scripts.migrate import migrate

    migrate(url)
    return url


TEST_NIK_KEY = "k" * 48  # key uji, bukan secret
APP_TABLES = [
    "audit.event", "core.sector", "core.employer_feature", "label.inspection_outcome", "label.ground_truth", "ops.metric_snapshot",
    "ops.inspection", "ops.session", "ops.login_attempt", "core.risk_score", "core.score_batch",
    "ops.app_user", "core.worker", "core.wage_reference", "core.employer", "core.branch",
]


@pytest.fixture(scope="session")
def small_world(tmp_path_factory: pytest.TempPathFactory):
    """Output generator kecil (200 BU) untuk tes integrasi."""
    from generator.__main__ import main as gen_main

    out = tmp_path_factory.mktemp("world")
    assert gen_main(["--out", str(out), "--n-employers", "200", "--seed", "7", "--inject-seed", "11",
                     "--skip-validate"]) == 0
    return out


@pytest.fixture(scope="session")
def seeded_db(db_url: str, small_world) -> str:
    """payray_test dikosongkan lalu diisi dunia kecil + user demo. Hanya DB *_test (GR-13)."""
    import psycopg

    from scripts import seed as seed_mod
    from scripts.seed_users import seed_users

    with psycopg.connect(db_url) as conn:
        conn.execute(f"TRUNCATE {', '.join(APP_TABLES)} RESTART IDENTITY CASCADE")
    os.environ["PAYRAY_NIK_KEY"] = TEST_NIK_KEY
    frames = seed_mod.build_frames(small_world, "2026-09", TEST_NIK_KEY.encode())
    seed_mod.seed(db_url, frames)
    seed_users(db_url, DEMO_PASSWORD)
    from scripts.bootstrap_batch import bootstrap

    bootstrap(db_url, "2026-09")
    return db_url


APP_PASSWORD = "app-test-password"  # password lokal role payray_app di DB uji
DEMO_PASSWORD = "demo-password-123"


@pytest.fixture(scope="session")
def app_db_url(seeded_db: str) -> str:
    """URL login sebagai payray_app (NOINHERIT), sama seperti production."""
    import psycopg

    with psycopg.connect(seeded_db, autocommit=True) as conn:
        conn.execute(f"ALTER ROLE payray_app LOGIN PASSWORD '{APP_PASSWORD}'")
    u = urlparse(seeded_db)
    return u._replace(netloc=f"payray_app:{APP_PASSWORD}@{u.hostname}:{u.port}").geturl()


@pytest.fixture()
def client(app_db_url: str):
    from fastapi.testclient import TestClient

    from api import db

    os.environ["DATABASE_URL"] = app_db_url
    db.reset_pool()
    from api.main import app

    with TestClient(app, base_url="https://testserver") as c:
        yield c
    db.reset_pool()


def login(client, username: str = "officer1", password: str = DEMO_PASSWORD):
    return client.post("/api/auth/login", json={"username": username, "password": password},
                       headers={"X-PayRay-CSRF": "1"})


@pytest.fixture()
def admin(seeded_db: str):
    import psycopg

    with psycopg.connect(seeded_db, autocommit=True) as conn:
        yield conn
