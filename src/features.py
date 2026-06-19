"""
features.py - Selection de features et split par conducteur (P2/P3).

Principes (cf. problematique.md) :
  - EXCLURE les confondeurs de LIEU (GPS / inertie) : ils detecteraient l'endroit.
  - REPERER les confondeurs de TEMPS (signaux qui derivent avec le roulage) :
    ils detecteraient le moment de l'attaque.
  - SPLIT PAR CONDUCTEUR : un conducteur du test n'est jamais vu a l'entrainement.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from data import classify_columns, usable


def drive_progress(df: pd.DataFrame) -> pd.Series:
    """Position de chaque fenetre dans son trajet (0 -> 1), par conducteur."""
    return df.groupby("driver")["interval_1s"].rank(pct=True)


def feature_sets(df: pd.DataFrame) -> dict:
    """Jeux de features utilisables : CAN (honnete), BIO, GPS (confondeur lieu)."""
    g = classify_columns(df)
    return {"CAN": usable(df, g["can"]),
            "BIO": usable(df, g["bio"]),
            "GPS": usable(df, g["vbox"])}


def time_drift(df: pd.DataFrame, cols: list[str], thr: float = 0.5):
    """Pour chaque feature, |correlation avec la progression du trajet|.
    Retourne (liste flaggee > thr, dict des correlations)."""
    dp = drive_progress(df).values
    flagged, corr = [], {}
    for c in cols:
        x = df[c].values
        m = ~np.isnan(x)
        if m.sum() < 1000:
            continue
        r = np.corrcoef(dp[m], x[m])[0, 1]
        if np.isnan(r):
            continue
        corr[c] = abs(r)
        if abs(r) > thr:
            flagged.append(c)
    return flagged, corr


def driver_holdout(df: pd.DataFrame, n_test: int = 12, seed: int = 0):
    """Masques (train, test) avec des conducteurs DISJOINTS (anti-fuite)."""
    drivers = df["driver"].unique().copy()
    np.random.RandomState(seed).shuffle(drivers)
    test_drivers = set(drivers[:n_test])
    test = df["driver"].isin(test_drivers).values
    return ~test, test


def random_holdout(df: pd.DataFrame, frac_test: float = 0.25, seed: int = 0):
    """Masques (train, test) au hasard - NON valide (fuit le conducteur).
    Sert uniquement a DEMONTRER la fuite."""
    rng = np.random.RandomState(seed)
    test = rng.rand(len(df)) < frac_test
    return ~test, test
