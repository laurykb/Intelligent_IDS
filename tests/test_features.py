"""
VAGUE 1 - Item 7 : tests unitaires de features.py (split conducteur anti-fuite).
Lancer :  pytest -q
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest
import numpy as np
from data import load
from features import feature_sets, driver_holdout, random_holdout, drive_progress, time_drift


@pytest.fixture(scope="module")
def df():
    return load()


def test_feature_sets_keys_and_sizes(df):
    fs = feature_sets(df)
    assert set(fs) == {"CAN", "BIO", "GPS"}
    assert len(fs["CAN"]) > 300, "on attend ~337 features CAN"
    assert len(fs["GPS"]) > 0 and len(fs["BIO"]) > 0
    # CAN et GPS disjoints (anti-confondeur)
    assert set(fs["CAN"]).isdisjoint(fs["GPS"])


def test_driver_holdout_disjoint(df):
    """Anti-fuite : aucun conducteur a la fois en train et en test."""
    tr, te = driver_holdout(df, n_test=12, seed=0)
    assert (tr & te).sum() == 0, "des lignes sont dans train ET test"
    assert (tr | te).all(), "des lignes ne sont ni train ni test"
    drivers = df["driver"].values
    assert set(drivers[tr]).isdisjoint(set(drivers[te])), "un conducteur fuit entre train et test"
    assert len(set(drivers[te])) == 12


def test_driver_holdout_deterministic(df):
    a1, a2 = driver_holdout(df, n_test=12, seed=0)
    b1, b2 = driver_holdout(df, n_test=12, seed=0)
    assert np.array_equal(a2, b2), "driver_holdout non deterministe a seed fixe"
    # un autre seed doit changer la partition
    c1, c2 = driver_holdout(df, n_test=12, seed=1)
    assert not np.array_equal(a2, c2)


def test_random_holdout_is_a_leak_demo(df):
    """random_holdout melange les conducteurs (sert juste a DEMONTRER la fuite)."""
    tr, te = random_holdout(df, frac_test=0.25, seed=0)
    drivers = df["driver"].values
    # un meme conducteur se retrouve des deux cotes (c'est le but : fuite)
    assert not set(drivers[tr]).isdisjoint(set(drivers[te]))
    assert 0.2 < te.mean() < 0.3


def test_drive_progress_in_unit_interval(df):
    dp = drive_progress(df)
    assert dp.min() >= 0 and dp.max() <= 1
    assert dp.notna().all()


def test_time_drift_returns_valid_correlations(df):
    """time_drift renvoie des correlations valides et flague des signaux time-drift.
    NB : seuil 0,35 = celui utilise en P2/P3 (a donne 21 signaux -> CAN_STABLE=316).
    La correlation est POOLEE : un odometre cumule (245) qui croit aussi entre
    conducteurs a une correlation poolee faible et n'est pas force flagge."""
    fs = feature_sets(df)
    flagged, corr = time_drift(df, fs["CAN"], thr=0.35)
    assert len(corr) > 0
    assert all(0.0 <= v <= 1.0 for v in corr.values()), "correlations hors [0,1]"
    assert set(flagged) == {c for c, v in corr.items() if v > 0.35}
    assert len(flagged) >= 1, "aucun signal time-drift flagge a 0,35 (P2/P3 en avait 21)"
    # seuil plus haut => moins (ou autant) de signaux flagges (monotonie)
    flagged_hi, _ = time_drift(df, fs["CAN"], thr=0.5)
    assert len(flagged_hi) <= len(flagged)
