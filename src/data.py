"""
data.py - Chargement et classification des colonnes du dataset ORNL Driver ID.

Dataset : 50 conducteurs (3 groupes d'awareness), Kenworth T270, ~155 902
fenetres de 1 s. Chaque variable est agregee par seconde (mean/sd/min/max).
Cible IDS : cyberattack_active (1,46 % - attaque rare, realiste).

POINT METHODOLOGIQUE CENTRAL (cf. eda_findings.md) : l'attaque a toujours lieu au
MEME endroit et au MEME moment du trajet. Les features GPS/position et les
signaux qui derivent dans le temps (temperatures) sont donc des CONFONDEURS : un
modele qui les utilise detecte le lieu/l'heure, pas l'attaque. On les isole.
"""
from __future__ import annotations
import os
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
# CSV brut : par defaut dans data/, mais surchargeable via la variable d'env
# IDS_CSV (utile quand le CSV de 852 Mo reste dans son dossier d'origine et
# qu'on ne veut pas le dupliquer). Le cache parquet, lui, est toujours dans data/.
CSV = os.environ.get("IDS_CSV", os.path.join(ROOT, "data", "DriverID_Full_Data_Downsampled.csv"))
CACHE = os.path.join(ROOT, "data", "cache.parquet")

META = ["ID", "Group", "Subject", "Time", "interval_1s", "cyberattack_active",
        "cumulative_distance_meters"]
STATS = ("mean.", "sd.", "min.", "max.")
_BIO_BASES = {"eda", "hr", "ibi"}   # biometrie (cardio / electrodermie)


def load(use_cache: bool = True) -> pd.DataFrame:
    """Charge le dataset (cache parquet pour la vitesse) + colonne driver."""
    if use_cache and os.path.exists(CACHE):
        df = pd.read_parquet(CACHE)
    else:
        df = pd.read_csv(CSV, low_memory=False)
        df.to_parquet(CACHE)
    if "driver" not in df:
        df["driver"] = df["Group"].astype(str) + "_S" + df["Subject"].astype(str)
    return df


def _base(col: str) -> str:
    """Renvoie le nom du signal sans le prefixe statistique (mean./sd./...)."""
    return col.split(".", 1)[1] if col.startswith(STATS) else col


def classify_columns(df: pd.DataFrame) -> dict:
    """Range les colonnes : meta, vbox (confondeur lieu), bio, can_signal.

    can_signal = signaux J1939 (prefixe SPN numerique), seuls features 'honnetes'
    pour un IDS ; vbox = a EXCLURE (fuite par le lieu) ; bio = biometrie.
    """
    groups = {"meta": [], "vbox": [], "bio": [], "can": []}
    for c in df.columns:
        if c in META or c == "driver" or not c.startswith(STATS):
            groups["meta"].append(c); continue
        base = _base(c)
        if base[0].isdigit():                       # prefixe SPN J1939 -> signal CAN
            groups["can"].append(c)
        elif base.lower() in _BIO_BASES or "skin" in base.lower():
            groups["bio"].append(c)
        else:                                       # GPS, IMU, trajectoire -> confondeur
            groups["vbox"].append(c)
    return groups


def usable(df: pd.DataFrame, cols: list[str], min_valid: float = 0.6) -> list[str]:
    """Garde les colonnes numeriques assez remplies et non constantes."""
    keep = []
    for c in cols:
        x = df[c]
        if not pd.api.types.is_numeric_dtype(x):
            continue
        if x.notna().mean() >= min_valid and (x.std(skipna=True) or 0) > 0:
            keep.append(c)
    return keep


if __name__ == "__main__":
    df = load()
    g = classify_columns(df)
    print(f"{len(df):,} lignes x {len(df.columns)} colonnes | {df.driver.nunique()} conducteurs")
    for k, v in g.items():
        print(f"  {k:5}: {len(v):>4} colonnes ; utilisables: {len(usable(df, v))}")
    print(f"  attaque: {100*df.cyberattack_active.mean():.2f}%")
