"""
P2/P3 - Pretraitement honnete + split par conducteur (dataset ORNL).

1. Confondeurs de TEMPS : signaux CAN qui derivent avec le roulage.
2. Jeux de features (CAN honnete / CAN stable / GPS confondeur / biometrie).
3. Split PAR CONDUCTEUR (verification anti-fuite).
4. Demonstrations chiffrees :
   (a) GPS -> PR-AUC quasi parfaite mais SPURIEUSE (geofencing)
   (b) CAN honnete -> la vraie difficulte
   (c) fuite conducteur : split aleatoire vs split par conducteur

Lancer :  python notebooks/02_preprocessing.py
"""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score
from data import load
from features import (feature_sets, time_drift, drive_progress,
                     driver_holdout, random_holdout)

ROOT = os.path.join(os.path.dirname(__file__), "..")
ASSETS = f"{ROOT}/docs/assets"
df = load(); y = df.cyberattack_active.values
fs = feature_sets(df)
base_rate = y.mean()
print(f"base rate (attaque) = {base_rate:.4f}  -> PR-AUC d'un modele aleatoire ~ {base_rate:.3f}")

# === 1) Confondeurs de TEMPS ================================================
flagged, corr = time_drift(df, fs["CAN"], thr=0.35)
top = sorted(corr.items(), key=lambda kv: -kv[1])[:8]
print("\n=== Signaux CAN les plus correles a la progression du trajet (confondeur TEMPS) ===")
for c, r in top:
    print(f"  |corr|={r:.2f}  {c[:60]}")
CAN_STABLE = [c for c in fs["CAN"] if c not in set(flagged)]
print(f"\nCAN total={len(fs['CAN'])} | flagges time-drift (|corr|>0.35)={len(flagged)} | CAN_STABLE={len(CAN_STABLE)}")

# === 2) Jeux de features ====================================================
print("\n=== Jeux de features ===")
for k in ["CAN", "BIO", "GPS"]:
    print(f"  {k:4}: {len(fs[k])} features")
print(f"  CAN_STABLE: {len(CAN_STABLE)} (CAN hors confondeur temps)")

# === 3) Split par conducteur ================================================
tr, te = driver_holdout(df, n_test=12, seed=0)
dtr, dte = set(df.driver[tr]), set(df.driver[te])
print("\n=== Split PAR CONDUCTEUR (12 conducteurs en test) ===")
print(f"  conducteurs train={len(dtr)} test={len(dte)} | chevauchement={len(dtr & dte)}")
print(f"  attaque train={y[tr].mean():.3%}  test={y[te].mean():.3%}")

def ap(cols, train, test):
    m = HistGradientBoostingClassifier(random_state=0, max_iter=200,
                                       class_weight="balanced")
    m.fit(df.loc[train, cols], y[train])
    return average_precision_score(y[test], m.predict_proba(df.loc[test, cols])[:, 1])

# === 4) Demonstrations ======================================================
print("\n=== DEMONSTRATIONS (PR-AUC) ===")
gps_drv = ap(fs["GPS"], tr, te)
can_drv = ap(fs["CAN"], tr, te)
cans_drv = ap(CAN_STABLE, tr, te)
print(f"  (a) GPS,  split conducteur  : PR-AUC = {gps_drv:.3f}  <- SPURIEUX (detecte le lieu)")
print(f"  (b) CAN,  split conducteur  : PR-AUC = {can_drv:.3f}  <- honnete (avec confondeur temps)")
print(f"      CAN_STABLE, split cond. : PR-AUC = {cans_drv:.3f}  <- plus honnete encore")

trr, ter = random_holdout(df, 0.25, seed=0)
can_rand = ap(fs["CAN"], trr, ter)
print(f"  (c) CAN, split ALEATOIRE    : PR-AUC = {can_rand:.3f}  vs split conducteur {can_drv:.3f}")
print(f"      -> ecart = fuite par le conducteur (le split aleatoire flatte)")

# === Figure : recap des demonstrations ======================================
fig, ax = plt.subplots(figsize=(9, 4.6))
labels = ["GPS\n(spurieux)", "CAN\n(honnete)", "CAN_STABLE\n(hors temps)", "CAN aleatoire\n(fuite cond.)"]
vals = [gps_drv, can_drv, cans_drv, can_rand]
cols = ["#c0392b", "#2980b9", "#16a085", "#e67e22"]
ax.bar(labels, vals, color=cols)
ax.axhline(base_rate, ls="--", color="k", lw=1, label=f"hasard ({base_rate:.3f})")
for i, v in enumerate(vals): ax.text(i, v, f"{v:.2f}", ha="center", va="bottom")
ax.set_ylabel("PR-AUC (test)"); ax.set_ylim(0, 1.05); ax.legend()
ax.set_title("Le piege des confondeurs et de la fuite conducteur (PR-AUC)")
plt.tight_layout(); plt.savefig(f"{ASSETS}/p2_confounders_demo.png", dpi=120); plt.close()

# === Artefacts reproductibles ===============================================
json.dump({"time_drift_flagged": flagged, "CAN_STABLE": CAN_STABLE,
           "test_drivers": sorted(dte)},
          open(f"{ROOT}/data/preprocessing.json", "w"), indent=2)
print("\n[OK] figure -> docs/assets/p2_confounders_demo.png | artefacts -> data/preprocessing.json")
