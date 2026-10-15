import shutil

import numpy as np
import pandas as pd
import pytest

from engine import features
from generator.config import Config
from generator.export import write_all
from generator.inject import inject
from generator.world import build_world
from ml import model as M
from ml.quality import run_checks


@pytest.fixture(scope="module")
def dataset(tmp_path_factory):
    out = tmp_path_factory.mktemp("data")
    cfg = Config(n_employers=400, seed=21, inject_seed=22)
    world = build_world(cfg)
    write_all(world, inject(world, cfg), cfg, out)
    return out


@pytest.fixture(scope="module")
def fitted(dataset):
    f = features.build(features.load(dataset))
    y = pd.read_csv(dataset / "label/labels.csv").set_index("employer_id").loc[f.index].is_violator
    X = M.matrix(f)
    clf = M.fit(X, y)
    iso = M.calibrator(clf.predict_proba(X)[:, 1], y.to_numpy())
    return X, clf, M.export(clf, iso, X)


def test_exported_model_matches_sklearn(fitted):
    X, clf, js = fitted
    raw = clf._raw_predict(X.to_numpy())[:, 0]
    mine = np.array([M.contributions(js, x)[0] for x in X.to_numpy()])
    assert np.abs(raw - mine).max() < 1e-4  # nilai leaf disimpan 6 digit signifikan


def test_contributions_are_additive(fitted):
    X, _, js = fitted
    x = X.to_numpy()[0]
    raw, phi = M.contributions(js, x)
    bias = js["base"] + sum(t["v"][0] for t in js["trees"])
    assert raw == pytest.approx(bias + phi.sum(), abs=1e-9)


def test_monotonic_constraint_holds(fitted):
    X, _, js = fitted
    i = M.COLS.index("porsi_upah_beku")
    x = X.to_numpy()[0].copy()
    vals = []
    for v in np.linspace(0, 1, 11):
        x[i] = v
        vals.append(M.contributions(js, x)[0])
    assert all(b >= a - 1e-12 for a, b in zip(vals, vals[1:]))


def test_quality_checks_pass_clean_and_catch_corruption(dataset, tmp_path):
    assert all(c["status"] == "lulus" for c in run_checks(dataset))
    bad = tmp_path / "bad"
    shutil.copytree(dataset, bad)
    wh = pd.read_csv(bad / "publik/wage_history.csv")
    wh.loc[:9, "upah_dilaporkan"] = -1
    wh.loc[10:19, "worker_id"] = "P_tidak_ada"
    wh.to_csv(bad / "publik/wage_history.csv", index=False)
    status = {c["nama"]: c["status"] for c in run_checks(bad)}
    assert status["Upah dilaporkan > 0"] == "gagal"
    assert status["Riwayat upah → pekerja terdaftar"] == "gagal"
