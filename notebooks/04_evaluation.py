"""
P5 - Evaluation fine du CHAMPION (Gradient Boosting / CAN, chemin A).

Trois volets, tous en validation HONNETE par conducteur :
  1. Courbe precision-rappel (predictions hors-fold) + choix d'un SEUIL operationnel.
  2. Leave-one-driver-out (50 conducteurs) : d'ou vient la variance +/-0,09 ?
  3. Importance des signaux CAN (permutation) : quels SPN J1939 portent la detection ?

Garde-fous : CAN seul (GPS exclu), splits par conducteur, metrique PR-AUC.
Lancer :  python notebooks/04_evaluation.py
"""
import os, sys, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.model_selection import GroupKFold
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import average_precision_score, precision_recall_curve
from data import load, _base
from features import feature_sets, driver_holdout

ROOT = os.path.join(os.path.dirname(__file__), "..")
ASSETS, EVAL = f"{ROOT}/docs/assets", f"{ROOT}/docs/03_evaluation"
os.makedirs(EVAL, exist_ok=True)

df = load(); y = df.cyberattack_active.values.astype(int); groups = df.driver.values
CAN = feature_sets(df)["CAN"]; X = df[CAN]
def champion(): return HistGradientBoostingClassifier(class_weight="balanced", random_state=0)
print(f"base rate {y.mean():.4f} | {len(CAN)} features CAN | {df.driver.nunique()} conducteurs\n")

# ============================================================== 1. PR curve + seuil
print("=== 1. Predictions hors-fold (GroupKFold conducteur) -> courbe PR + seuil ===")
oof = np.full(len(y), np.nan)
gkf = GroupKFold(n_splits=4)
for tr, te in gkf.split(X, y, groups):
    m = champion().fit(X.iloc[tr], y[tr])
    oof[te] = m.predict_proba(X.iloc[te])[:, 1]
oof_ap = average_precision_score(y, oof)
prec, rec, thr = precision_recall_curve(y, oof)
f1 = 2 * prec * rec / (prec + rec + 1e-12)
best = np.nanargmax(f1[:-1])                       # dernier point n'a pas de seuil
t_star = thr[best]
print(f"  PR-AUC hors-fold (global) = {oof_ap:.3f}")
print(f"  seuil F1-max = {t_star:.3f} -> precision {prec[best]:.3f}, rappel {rec[best]:.3f}, F1 {f1[best]:.3f}")

# table de seuils : a quel cout en fausses alertes pour un rappel donne ?
rows = []
for target in [0.5, 0.7, 0.8, 0.9]:
    i = np.argmin(np.abs(rec[:-1] - target))
    flagged = (oof >= thr[i]).mean()
    rows.append((target, float(thr[i]), float(prec[i]), float(rec[i]), float(flagged)))
    print(f"  rappel~{target:.1f} : seuil {thr[i]:.3f}, precision {prec[i]:.3f}, "
          f"{100*flagged:.1f}% des fenetres alertees")

# ============================================================== 2. Leave-one-driver-out
print("\n=== 2. Leave-one-driver-out (50 conducteurs) ===")
drivers = df.driver.unique()
lodo = {}
t0 = time.time()
for d in drivers:
    te = (groups == d); tr = ~te
    m = champion().fit(X.iloc[np.where(tr)[0]], y[tr])
    s = m.predict_proba(X.iloc[np.where(te)[0]])[:, 1]
    lodo[d] = float(average_precision_score(y[te], s))
lo = pd.Series(lodo).sort_values()
print(f"  ({time.time()-t0:.0f}s) PR-AUC LODO : moyenne {lo.mean():.3f} +/- {lo.std():.3f} "
      f"| mediane {lo.median():.3f} | min {lo.min():.3f} | max {lo.max():.3f}")
print(f"  5 conducteurs les PIRES : " + ", ".join(f"{k}={v:.2f}" for k, v in lo.head(5).items()))
print(f"  5 conducteurs les MEILLEURS : " + ", ".join(f"{k}={v:.2f}" for k, v in lo.tail(5).items()))

# ============================================================== 3. Importance (permutation)
print("\n=== 3. Importance des signaux CAN (permutation, split conducteur) ===")
tr_m, te_m = driver_holdout(df, n_test=12, seed=0)
m = champion().fit(X[tr_m], y[tr_m])
t0 = time.time()
pi = permutation_importance(m, X[te_m], y[te_m], scoring="average_precision",
                            n_repeats=3, random_state=0, n_jobs=-1)
print(f"  ({time.time()-t0:.0f}s) permutation importance calculee sur le holdout (12 conducteurs)")
imp_col = pd.Series(pi.importances_mean, index=CAN)
# agrege par signal physique (mean./sd./min./max. -> meme SPN)
imp_sig = imp_col.groupby([_base(c) for c in CAN]).sum().sort_values(ascending=False)
top = imp_sig.head(15)
print("  Top signaux CAN (chute de PR-AUC quand on les permute) :")
for name, v in top.items():
    print(f"    {v:+.4f}  {name}")

# ============================================================== Sauvegardes + figures
out = {"oof_prauc": float(oof_ap), "seuil_f1max": float(t_star),
       "precision_f1max": float(prec[best]), "rappel_f1max": float(rec[best]), "f1max": float(f1[best]),
       "table_seuils": rows,
       "lodo_mean": float(lo.mean()), "lodo_std": float(lo.std()), "lodo_median": float(lo.median()),
       "lodo_min": float(lo.min()), "lodo_max": float(lo.max()), "lodo_par_conducteur": lodo,
       "top_signaux": {k: float(v) for k, v in top.items()}}
json.dump(out, open(f"{EVAL}/results_evaluation.json", "w"), indent=2)

# Fig 1 : courbe PR
fig, ax = plt.subplots(figsize=(6.2, 5))
ax.plot(rec, prec, color="#2980b9", lw=2, label=f"Gradient Boosting (PR-AUC {oof_ap:.3f})")
ax.axhline(y.mean(), ls="--", color="k", lw=1, label=f"hasard ({y.mean():.3f})")
ax.scatter([rec[best]], [prec[best]], color="#c0392b", zorder=5,
           label=f"seuil F1-max ({prec[best]:.2f}P / {rec[best]:.2f}R)")
ax.set_xlabel("Rappel"); ax.set_ylabel("Precision"); ax.set_xlim(0, 1); ax.set_ylim(0, 1)
ax.set_title("P5 - Courbe precision-rappel (hors-fold, par conducteur)"); ax.legend(loc="upper right")
plt.tight_layout(); plt.savefig(f"{ASSETS}/p5_pr_curve.png", dpi=120); plt.close()

# Fig 2 : LODO + Fig 3 : importance
fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5))
a1.hist(list(lodo.values()), bins=15, color="#16a085", edgecolor="white")
a1.axvline(lo.mean(), color="#c0392b", ls="--", lw=1.5, label=f"moyenne {lo.mean():.2f}")
a1.set_xlabel("PR-AUC du conducteur tenu a l'ecart"); a1.set_ylabel("nb de conducteurs")
a1.set_title("P5 - Leave-one-driver-out (50)"); a1.legend()
top.iloc[::-1].plot.barh(ax=a2, color="#8e44ad")
a2.set_xlabel("chute de PR-AUC (permutation)"); a2.set_title("P5 - Top 15 signaux CAN")
plt.tight_layout(); plt.savefig(f"{ASSETS}/p5_lodo_importance.png", dpi=120); plt.close()
print("\n[OK] figures -> docs/assets/p5_pr_curve.png, p5_lodo_importance.png "
      "| resultats -> docs/03_evaluation/results_evaluation.json")
