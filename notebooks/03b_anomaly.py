"""
P4 - Chemin B : detection d'anomalie (dataset ORNL).

Idee : un IDS ne connait pas forcement l'attaque a l'avance. On apprend donc le
profil du trafic NORMAL (sans labels d'attaque) et on signale tout ce qui s'en
ecarte. C'est adapte a une attaque RARE (1,46 %) et inconnue.

Protocole HONNETE (memes garde-fous que le chemin A) :
  - Features = 337 signaux CAN (GPS exclu = confondeur lieu).
  - Validation PAR CONDUCTEUR (GroupKFold 4 folds) : conducteurs de test jamais vus.
  - On entraine UNIQUEMENT sur les fenetres NORMALES des conducteurs de train
    (novelty detection / semi-supervise) ; on score train+test du fold de test.
  - Metrique = PR-AUC (hasard ~ 0,015). Score = degre d'anomalie (haut = suspect).
  - Imputation mediane + standardisation AJUSTEES sur le normal de train (anti-fuite).

Lancer :  python notebooks/03b_anomaly.py
"""
import os, sys, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.model_selection import GroupKFold
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.ensemble import IsolationForest
from sklearn.svm import OneClassSVM
from sklearn.decomposition import PCA
from sklearn.metrics import average_precision_score
from data import load
from features import feature_sets

ROOT = os.path.join(os.path.dirname(__file__), "..")
ASSETS, EVAL = f"{ROOT}/docs/assets", f"{ROOT}/docs/03_evaluation"
os.makedirs(EVAL, exist_ok=True)

SUP_CHAMPION = 0.756          # reference : chemin A (supervise, GradBoosting CAN)
OCSVM_FIT_MAX = 4000          # One-Class SVM en O(n^2) -> on sous-echantillonne le normal

df = load(); y = df.cyberattack_active.values.astype(int); groups = df.driver.values
CAN = feature_sets(df)["CAN"]
X = df[CAN].values
print(f"base rate {y.mean():.4f} (PR-AUC hasard ~ {y.mean():.3f}) | {len(CAN)} features CAN")
print(f"reference supervisee (chemin A) = {SUP_CHAMPION:.3f}\n")

rng = np.random.RandomState(0)


def prep(tr_norm_idx, all_idx):
    """Impute (mediane) + standardise, AJUSTE sur le normal de train. -> (X_fit, X_all)."""
    imp = SimpleImputer(strategy="median").fit(X[tr_norm_idx])
    sc = StandardScaler().fit(imp.transform(X[tr_norm_idx]))
    return sc.transform(imp.transform(X[tr_norm_idx])), \
           (imp, sc)


def transform(imp_sc, idx):
    imp, sc = imp_sc
    return sc.transform(imp.transform(X[idx]))


# --- scoreurs d'anomalie : rendent un score ou HAUT = plus anormal ---------------
def score_iforest(Xfit, Xte):
    m = IsolationForest(n_estimators=200, random_state=0, n_jobs=-1).fit(Xfit)
    return -m.score_samples(Xte)                       # score_samples : haut = normal

def score_ocsvm(Xfit, Xte):
    sub = Xfit if len(Xfit) <= OCSVM_FIT_MAX else Xfit[rng.choice(len(Xfit), OCSVM_FIT_MAX, replace=False)]
    m = OneClassSVM(kernel="rbf", gamma="scale", nu=0.05).fit(sub)
    return -m.decision_function(Xte)                   # decision_function : haut = normal

def score_pca(Xfit, Xte, var=0.95):
    m = PCA(n_components=var, random_state=0).fit(Xfit)
    rec = m.inverse_transform(m.transform(Xte))
    return ((Xte - rec) ** 2).sum(axis=1)              # erreur de reconstruction

def score_gauss(Xfit, Xte):
    # Gaussienne diagonale (independante) : somme des z^2. Robuste en haute dimension.
    mu, sd = Xfit.mean(0), Xfit.std(0) + 1e-9
    return (((Xte - mu) / sd) ** 2).sum(axis=1)

SCORERS = {"IsolationForest": score_iforest, "OneClassSVM": score_ocsvm,
           "PCA (reconstruction)": score_pca, "Gaussienne diag.": score_gauss}

# --- validation croisee par conducteur ------------------------------------------
gkf = GroupKFold(n_splits=4)
res = {k: [] for k in SCORERS}
print("=== PR-AUC par fold (entraine sur NORMAL de train, score le test) ===")
for f, (tr, te) in enumerate(gkf.split(X, y, groups)):
    tr_norm = tr[y[tr] == 0]                            # normal uniquement
    Xfit, imp_sc = prep(tr_norm, None)
    Xte = transform(imp_sc, te); yte = y[te]
    line = [f"fold {f}"]
    for name, fn in SCORERS.items():
        t0 = time.time()
        ap = average_precision_score(yte, fn(Xfit, Xte))
        res[name].append(ap)
        line.append(f"{name[:10]} {ap:.3f} ({time.time()-t0:.0f}s)")
    print("  " + " | ".join(line))

res = {k: np.array(v) for k, v in res.items()}
print("\n=== Bilan (PR-AUC moyen, validation par conducteur) ===")
for name, ap in sorted(res.items(), key=lambda kv: -kv[1].mean()):
    print(f"  {name:22} {ap.mean():.3f} +/- {ap.std():.3f}")
print(f"\n  (rappel) supervise chemin A = {SUP_CHAMPION:.3f} | hasard = {y.mean():.3f}")

# --- sauvegarde + figure --------------------------------------------------------
out = {k: [float(v.mean()), float(v.std())] for k, v in res.items()}
out["_ref_supervise"] = [SUP_CHAMPION, 0.0]; out["_hasard"] = [float(y.mean()), 0.0]
json.dump(out, open(f"{EVAL}/results_anomaly.json", "w"), indent=2)

names = sorted(res, key=lambda n: -res[n].mean())
means = [res[n].mean() for n in names]; stds = [res[n].std() for n in names]
fig, ax = plt.subplots(figsize=(8.5, 4.8))
ax.bar(names, means, yerr=stds, color="#8e44ad", capsize=4)
ax.axhline(SUP_CHAMPION, ls="--", color="#2980b9", lw=1.5, label=f"supervise chemin A ({SUP_CHAMPION:.3f})")
ax.axhline(y.mean(), ls="--", color="k", lw=1, label=f"hasard ({y.mean():.3f})")
ax.set_ylabel("PR-AUC (val. par conducteur)"); ax.set_ylim(0, 1)
ax.set_title("Chemin B : detection d'anomalie (normal CAN uniquement)")
for i, m in enumerate(means): ax.text(i, m, f"{m:.2f}", ha="center", va="bottom")
plt.setp(ax.get_xticklabels(), rotation=12, ha="right"); ax.legend()
plt.tight_layout(); plt.savefig(f"{ASSETS}/p4b_anomaly.png", dpi=120); plt.close()
print("\n[OK] figure -> docs/assets/p4b_anomaly.png | resultats -> docs/03_evaluation/results_anomaly.json")
