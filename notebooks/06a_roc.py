"""
VAGUE 1 - Item 1 : Courbe ROC + AUC-ROC du champion (demande explicite du sujet).

On garde PR-AUC comme metrique PRIMAIRE (attaque rare 1,46 %) mais on ajoute la ROC,
demandee par le sujet, et on explique le contraste (base-rate).

Predictions HORS-FOLD (GroupKFold conducteur), sauvegardees pour l'item 3 (latence/episode).
Lancer :  python notebooks/06a_roc.py
"""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.model_selection import GroupKFold
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import (roc_auc_score, roc_curve, average_precision_score,
                             precision_recall_curve)
from data import load
from features import feature_sets

ROOT = os.path.join(os.path.dirname(__file__), "..")
ASSETS, EVAL = f"{ROOT}/docs/assets", f"{ROOT}/docs/03_evaluation"

df = load(); y = df.cyberattack_active.values.astype(int)
groups = df.driver.values; CAN = feature_sets(df)["CAN"]; X = df[CAN]
print(f"base rate {y.mean():.4f} | {len(CAN)} features CAN")

# Predictions hors-fold (chaque conducteur score par un modele qui ne l'a pas vu)
oof = np.full(len(y), np.nan)
for tr, te in GroupKFold(n_splits=4).split(X, y, groups):
    m = HistGradientBoostingClassifier(class_weight="balanced", random_state=0).fit(X.iloc[tr], y[tr])
    oof[te] = m.predict_proba(X.iloc[te])[:, 1]

roc_auc = roc_auc_score(y, oof); pr_auc = average_precision_score(y, oof)
fpr, tpr, _ = roc_curve(y, oof)
prec, rec, _ = precision_recall_curve(y, oof)
print(f"\n  AUC-ROC = {roc_auc:.3f}   |   PR-AUC = {pr_auc:.3f}   |   hasard PR = {y.mean():.3f}")
print("  -> AUC-ROC tres haute (la classe negative ecrase les FP) MAIS PR-AUC reste la"
      " metrique honnete pour une attaque rare.")

# Sauvegarde OOF pour l'item 3 (latence/episode)
np.savez(f"{EVAL}/oof_scores.npz", oof=oof, y=y, driver=groups,
         interval=df.interval_1s.values)
json.dump({"auc_roc": float(roc_auc), "pr_auc_oof": float(pr_auc), "base_rate": float(y.mean())},
          open(f"{EVAL}/results_roc.json", "w"), indent=2)

# Figure : ROC + PR cote a cote
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 5))
a1.plot(fpr, tpr, color="#2980b9", lw=2, label=f"GBoosting (AUC-ROC {roc_auc:.3f})")
a1.plot([0, 1], [0, 1], ls="--", color="k", lw=1, label="hasard (0,5)")
a1.set_xlabel("Taux de faux positifs"); a1.set_ylabel("Taux de vrais positifs (rappel)")
a1.set_title("Courbe ROC (hors-fold, par conducteur)"); a1.legend(loc="lower right")
a2.plot(rec, prec, color="#c0392b", lw=2, label=f"GBoosting (PR-AUC {pr_auc:.3f})")
a2.axhline(y.mean(), ls="--", color="k", lw=1, label=f"hasard ({y.mean():.3f})")
a2.set_xlabel("Rappel"); a2.set_ylabel("Precision"); a2.set_xlim(0, 1); a2.set_ylim(0, 1)
a2.set_title("Courbe PR (meme modele) - metrique primaire"); a2.legend(loc="upper right")
plt.tight_layout(); plt.savefig(f"{ASSETS}/v1_roc_vs_pr.png", dpi=120); plt.close()
print("\n[OK] figure -> docs/assets/v1_roc_vs_pr.png | OOF -> docs/03_evaluation/oof_scores.npz")
