"""
VAGUE 1 - Item 2 : Optimisation d'hyperparametres du champion (demande du sujet).

RandomizedSearchCV en **GroupKFold par conducteur** (anti-fuite), scoring = PR-AUC.
On compare au champion PAR DEFAUT (PR-AUC 0,756, chemin A).

>>> PORTABLE / ROBUSTE (peut tourner sur une autre machine) :
  - parametrable par variables d'environnement :  N_JOBS (defaut 3), N_ITER (defaut 25)
  - features en float32 numpy (moins de memoire que le DataFrame memmappe)
  - early_stopping=True + max_iter modere -> rapide et peu gourmand (evite l'OOM)
  - sauvegarde le meilleur resultat meme en cas d'interruption (try/except)

Lancer :        python notebooks/06b_tuning.py
Plus rapide :   N_JOBS=2 N_ITER=15 python notebooks/06b_tuning.py
Pre-requis :    le dossier data/ (cache.parquet OU le CSV) + requirements.lock.txt
"""
import os, sys, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np
from sklearn.model_selection import RandomizedSearchCV, GroupKFold, cross_val_score
from sklearn.ensemble import HistGradientBoostingClassifier
from data import load
from features import feature_sets

ROOT = os.path.join(os.path.dirname(__file__), "..")
EVAL = f"{ROOT}/docs/03_evaluation"
N_JOBS = int(os.environ.get("N_JOBS", "3"))      # garder modere pour la memoire
N_ITER = int(os.environ.get("N_ITER", "25"))

df = load(); y = df.cyberattack_active.values.astype(int)
groups = df.driver.values; CAN = feature_sets(df)["CAN"]
X = df[CAN].values.astype(np.float32)            # numpy float32 = leger pour le memmap
gkf = GroupKFold(n_splits=4)
print(f"{len(CAN)} features CAN | N_JOBS={N_JOBS} | N_ITER={N_ITER}")

# Reference : champion par defaut, meme CV (HistGB gere les NaN nativement)
t0 = time.time()
default = HistGradientBoostingClassifier(class_weight="balanced", random_state=0)
def_scores = cross_val_score(default, X, y, groups=groups, cv=gkf, scoring="average_precision", n_jobs=4)
print(f"defaut PR-AUC = {def_scores.mean():.3f} +/- {def_scores.std():.3f}  ({time.time()-t0:.0f}s)")

# Espace de recherche : early_stopping borne le nombre reel d'arbres -> rapide
space = {
    "learning_rate": [0.03, 0.05, 0.1, 0.2],
    "max_iter": [200, 400, 600],                 # plafond ; early_stopping coupe avant
    "max_leaf_nodes": [15, 31, 63, 127],
    "max_depth": [None, 4, 8, 12],
    "min_samples_leaf": [20, 50, 100, 200],
    "l2_regularization": [0.0, 0.1, 1.0, 10.0],
}
search = RandomizedSearchCV(
    HistGradientBoostingClassifier(class_weight="balanced", early_stopping=True,
                                   n_iter_no_change=12, validation_fraction=0.1, random_state=0),
    space, n_iter=N_ITER, scoring="average_precision", cv=gkf,
    n_jobs=N_JOBS, pre_dispatch="n_jobs", random_state=0, refit=True, verbose=2)

t0 = time.time()
try:
    search.fit(X, y, groups=groups)
    best_score, best_params = float(search.best_score_), search.best_params_
    print(f"\nsearch fini en {time.time()-t0:.0f}s ({N_ITER} candidats x 4 folds)")
except KeyboardInterrupt:
    print("\n[INTERROMPU] on sauvegarde le meilleur trouve jusqu'ici.")
    best_score = float(np.nanmax(search.cv_results_["mean_test_score"]))
    best_params = search.cv_results_["params"][int(np.nanargmax(search.cv_results_["mean_test_score"]))]

print(f"  MEILLEUR PR-AUC = {best_score:.3f}  (defaut {def_scores.mean():.3f})")
print(f"  delta = {best_score - def_scores.mean():+.3f}")
print(f"  meilleurs params : {best_params}")

out = {"default_prauc": [float(def_scores.mean()), float(def_scores.std())],
       "tuned_prauc": best_score, "delta": best_score - def_scores.mean(),
       "best_params": {k: (v if v is not None else "None") for k, v in best_params.items()},
       "n_iter": N_ITER}
json.dump(out, open(f"{EVAL}/results_tuning.json", "w"), indent=2)
print("\n[OK] resultats -> docs/03_evaluation/results_tuning.json")
