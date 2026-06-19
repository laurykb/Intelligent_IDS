"""
P4 - Chemin A : apprentissage supervise (dataset ORNL).
Comparaison de modeles en validation croisee PAR CONDUCTEUR (GroupKFold),
metrique PR-AUC (attaque rare 1,46 %). + ablation des modalites.

Lancer :  python notebooks/03a_supervised.py
"""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.model_selection import GroupKFold
from sklearn.pipeline import make_pipeline
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.svm import LinearSVC
from sklearn.ensemble import RandomForestClassifier, HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, precision_recall_curve
from data import load
from features import feature_sets

ROOT = os.path.join(os.path.dirname(__file__), "..")
ASSETS, EVAL = f"{ROOT}/docs/assets", f"{ROOT}/docs/03_evaluation"
os.makedirs(EVAL, exist_ok=True)
df = load(); y = df.cyberattack_active.values; groups = df.driver.values
fs = feature_sets(df); CAN = fs["CAN"]; BIO = fs["BIO"]; GPS = fs["GPS"]
print(f"base rate {y.mean():.4f} (PR-AUC hasard ~ {y.mean():.3f}) | {len(CAN)} features CAN")

gkf = GroupKFold(n_splits=4)

def scores(est, cols):
    """PR-AUC par fold (GroupKFold conducteur)."""
    X = df[cols]; aps = []
    for tr, te in gkf.split(X, y, groups):
        est.fit(X.iloc[tr], y[tr])
        s = (est.predict_proba(X.iloc[te])[:, 1] if hasattr(est, "predict_proba")
             else est.decision_function(X.iloc[te]))
        aps.append(average_precision_score(y[te], s))
    return np.array(aps)

def imp_scale(model):  return make_pipeline(SimpleImputer(strategy="median"), StandardScaler(), model)
def imp(model):        return make_pipeline(SimpleImputer(strategy="median"), model)

models = {
    "LogReg":       imp_scale(LogisticRegression(max_iter=1000, class_weight="balanced")),
    "SVM-lineaire": imp_scale(LinearSVC(class_weight="balanced", dual=False)),
    "RandomForest": imp(RandomForestClassifier(n_estimators=60, n_jobs=-1, class_weight="balanced", random_state=0)),
    "GradBoosting": HistGradientBoostingClassifier(class_weight="balanced", random_state=0),
}

print("\n=== Comparaison (PR-AUC, validation par conducteur) ===")
res = {}
for name, est in models.items():
    ap = scores(est, CAN); res[name] = ap
    print(f"  {name:13} PR-AUC = {ap.mean():.3f} +/- {ap.std():.3f}")

# Champion = GradBoosting -> ablation des modalites
print("\n=== Ablation des modalites (champion Gradient Boosting) ===")
abl = {}
for tag, cols in [("CAN", CAN), ("CAN+BIO", CAN + BIO), ("BIO seul", BIO), ("GPS (confondeur)", GPS)]:
    ap = scores(HistGradientBoostingClassifier(class_weight="balanced", random_state=0), cols)
    abl[tag] = ap
    print(f"  {tag:18} PR-AUC = {ap.mean():.3f} +/- {ap.std():.3f}")

# Sauvegarde + figures
out = {k: [float(v.mean()), float(v.std())] for k, v in {**{f"model_{k}": v for k, v in res.items()},
       **{f"abl_{k}": v for k, v in abl.items()}}.items()}
json.dump(out, open(f"{EVAL}/results_supervised.json", "w"), indent=2)

fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.6))
names = list(res); means = [res[n].mean() for n in names]; stds = [res[n].std() for n in names]
a1.bar(names, means, yerr=stds, color="#2980b9", capsize=4)
a1.axhline(y.mean(), ls="--", color="k", lw=1, label=f"hasard ({y.mean():.3f})")
a1.set_ylabel("PR-AUC (val. par conducteur)"); a1.set_ylim(0, 1); a1.legend()
a1.set_title("Chemin A : comparaison de modeles (features CAN)")
for i, m in enumerate(means): a1.text(i, m, f"{m:.2f}", ha="center", va="bottom")

tags = list(abl); am = [abl[t].mean() for t in tags]
colA = ["#2980b9", "#16a085", "#95a5a6", "#c0392b"]
a2.bar(tags, am, yerr=[abl[t].std() for t in tags], color=colA, capsize=4)
a2.axhline(y.mean(), ls="--", color="k", lw=1)
a2.set_ylabel("PR-AUC"); a2.set_ylim(0, 1); a2.set_title("Ablation des modalites (Gradient Boosting)")
for i, m in enumerate(am): a2.text(i, m, f"{m:.2f}", ha="center", va="bottom")
plt.setp(a2.get_xticklabels(), rotation=12, ha="right")
plt.tight_layout(); plt.savefig(f"{ASSETS}/p4a_supervised.png", dpi=120); plt.close()
print("\n[OK] figure -> docs/assets/p4a_supervised.png | resultats -> docs/03_evaluation/results_supervised.json")
