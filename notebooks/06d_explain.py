"""
VAGUE 1 - Item 4 : Explicabilite directionnelle du champion.

But initial : SHAP. SHAP est INDISPONIBLE dans l'environnement (offline) -> on utilise
les DEPENDANCES PARTIELLES (sklearn, natif), qui donnent l'information directionnelle
recherchee : dans quel SENS chaque signal pousse P(attaque) ? (la permutation importance
de P5 ne donnait que l'amplitude). On regarde le top des signaux de P5.

Lancer :  python notebooks/06d_explain.py
"""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.impute import SimpleImputer
from sklearn.inspection import partial_dependence
from data import load
from features import feature_sets, driver_holdout

ROOT = os.path.join(os.path.dirname(__file__), "..")
ASSETS, EVAL = f"{ROOT}/docs/assets", f"{ROOT}/docs/03_evaluation"

df = load(); y = df.cyberattack_active.values.astype(int)
CAN = feature_sets(df)["CAN"]; X = df[CAN]
tr_m, te_m = driver_holdout(df, n_test=12, seed=0)
# Imputation mediane : la dependance partielle a besoin d'un grid SANS NaN (sinon le
# grid de percentiles est NaN et la PD reste collee au log-odds de base).
imp = SimpleImputer(strategy="median").fit(X[tr_m])
Xtr = pd.DataFrame(imp.transform(X[tr_m]), columns=CAN)
Xte = pd.DataFrame(imp.transform(X[te_m]), columns=CAN)
m = HistGradientBoostingClassifier(class_weight="balanced", random_state=0).fit(Xtr, y[tr_m])

# top signaux de P5 -> colonne mean.<signal>
top = list(json.load(open(f"{EVAL}/results_evaluation.json"))["top_signaux"].keys())
cols = [f"mean.{s}" for s in top if f"mean.{s}" in X.columns][:6]
print("Signaux expliques (dependance partielle) :")
for c in cols: print("  ", c)

# method='recursion' : echelle log-odds (decision_function), native HistGB et rapide.
# Sur une classe rare, l'echelle proba ecrase tout pres de 0 -> les log-odds montrent
# la FORME et le SENS de l'effet appris.
Xs = Xte.sample(n=min(8000, len(Xte)), random_state=0)

fig, axes = plt.subplots(2, 3, figsize=(14, 8)); axes = axes.ravel()
pd_out = {}
for ax, col in zip(axes, cols):
    pdp = partial_dependence(m, Xs, [col], kind="average", method="recursion", grid_resolution=30)
    xx = pdp.get("grid_values", pdp.get("values"))[0]; yy = pdp["average"][0]  # 'values' en sklearn<1.3
    ax.plot(xx, yy, color="#8e44ad", lw=2)
    sens = "monte" if yy[-1] > yy[0] else "descend"
    ax.set_title(f"{col.replace('mean.','')}\n(log-odds attaque {sens})", fontsize=9)
    ax.set_xlabel("valeur du signal"); ax.set_ylabel("effet partiel (log-odds)")
    pd_out[col] = {"x": [float(v) for v in xx], "pd": [float(v) for v in yy],
                   "sens": sens, "amplitude": float(yy.max() - yy.min())}
for ax in axes[len(cols):]: ax.axis("off")
plt.suptitle("Vague 1 - Dependances partielles (explicabilite directionnelle, substitut SHAP)", y=1.02)
plt.tight_layout(); plt.savefig(f"{ASSETS}/v1_partial_dependence.png", dpi=120, bbox_inches="tight"); plt.close()

json.dump({"note": "SHAP indisponible (offline) -> dependances partielles sklearn",
           "signaux": pd_out}, open(f"{EVAL}/results_explain.json", "w"), indent=2)
print("\nSens de l'effet (P(attaque) vs signal) :")
for c, v in pd_out.items():
    print(f"  {c.replace('mean.',''):55} {v['sens']:8} (amplitude {v['amplitude']:.3f})")
print("\n[OK] figure -> docs/assets/v1_partial_dependence.png | resultats -> docs/03_evaluation/results_explain.json")
