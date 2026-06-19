"""
VAGUE 1 - Item 7 : tests unitaires de data.py (invariants anti-fuite).
Lancer :  pytest -q
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import pytest
import pandas as pd
from data import load, classify_columns, usable, _base, STATS, META

# termes GPS/inertie NON ambigus (ne collisionnent pas avec les noms de SPN J1939
# comme "Pedal Position" ou "Acceleration Rate" qui sont de vrais signaux CAN).
GPS_TOKENS = ("latitude", "longitude", "gps", "prekf", "vbox", "_imu", "kalman")


@pytest.fixture(scope="module")
def df():
    return load()


@pytest.fixture(scope="module")
def groups(df):
    return classify_columns(df)


def test_buckets_partition_all_columns(df, groups):
    """Les 4 buckets partitionnent EXACTEMENT les colonnes (pas de perte, pas de doublon)."""
    union = [c for v in groups.values() for c in v]
    assert len(union) == len(set(union)), "une colonne apparait dans 2 buckets"
    assert set(union) == set(df.columns), "des colonnes ne sont classees nulle part"


def test_no_gps_leaks_into_can(df, groups):
    """LE test anti-confondeur : aucune colonne GPS/inertie (vbox) dans le set CAN."""
    assert set(groups["can"]).isdisjoint(groups["vbox"])
    for c in groups["can"]:
        low = _base(c).lower()
        assert not any(tok in low for tok in GPS_TOKENS), f"signal GPS-like dans CAN: {c}"


def test_can_are_j1939_spn(df, groups):
    """Tout signal CAN a un prefixe statistique + une base qui commence par un SPN numerique."""
    for c in groups["can"]:
        assert c.startswith(STATS), f"CAN sans prefixe stat: {c}"
        assert _base(c)[0].isdigit(), f"CAN sans SPN numerique: {c}"


def test_bio_are_biometric(df, groups):
    for c in groups["bio"]:
        base = _base(c).lower()
        assert base in {"eda", "hr", "ibi"} or "skin" in base, f"bio inattendu: {c}"


def test_target_and_confounders_excluded_from_features(df, groups):
    """La cible et les confondeurs connus ne doivent JAMAIS etre des features."""
    feature_cols = set(groups["can"]) | set(groups["bio"]) | set(groups["vbox"])
    for forbidden in ["cyberattack_active", "cumulative_distance_meters", "Group",
                      "Subject", "driver", "interval_1s", "Time"]:
        assert forbidden not in feature_cols, f"{forbidden} ne doit pas etre une feature"
        assert forbidden in groups["meta"]


def test_survey_columns_in_meta(df, groups):
    """Les colonnes Qualtrics (constantes par conducteur) sont en meta, jamais features."""
    survey = [c for c in df.columns if c.startswith(("Q11", "Q12", "cyberattack_", "avg_", "total_"))
              and c != "cyberattack_active"]
    assert survey, "sanity: on doit trouver des colonnes survey"
    for c in survey:
        assert c in groups["meta"]


def test_usable_filters_constant_and_sparse(df, groups):
    """usable() ne garde que des colonnes numeriques, assez remplies, non constantes."""
    u = usable(df, groups["can"])
    assert 0 < len(u) <= len(groups["can"])
    for c in u:
        assert pd.api.types.is_numeric_dtype(df[c])
        assert df[c].notna().mean() >= 0.6
        assert (df[c].std(skipna=True) or 0) > 0


def test_attack_is_rare(df):
    """Garde-fou : la cible reste l'attaque rare attendue (~1,46 %)."""
    rate = df["cyberattack_active"].mean()
    assert 0.005 < rate < 0.03, f"taux d'attaque inattendu: {rate}"
