"""
Construit les artefacts pour la demo LIVE :
  - artifacts/ids_model.joblib       : champion HistGB (entraine sur le split train conducteur)
  - artifacts/ids_model_meta.json    : features, metriques, params
  - artifacts/demo_samples.npz       : echantillons de features (attaque/normal) du TEST + medianes
                                       normales + ranking d'importance (pour l'evasion interactive)
"""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np, joblib
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import average_precision_score, roc_auc_score, precision_score, recall_score
from data import load
from features import feature_sets, driver_holdout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ART = os.path.join(ROOT, "artifacts")
df = load(); y = df.cyberattack_active.values.astype(int); grp = df.Group.values
CAN = feature_sets(df)["CAN"]; X = df[CAN].values.astype(np.float32)
tr, te = driver_holdout(df, n_test=12, seed=0)
rng = np.random.RandomState(0)

# params tunes (Vague 1)
params = dict(learning_rate=0.1, max_leaf_nodes=15, max_iter=400, max_depth=None,
              min_samples_leaf=20, l2_regularization=10.0)
model = HistGradientBoostingClassifier(class_weight="balanced", random_state=0, **params).fit(X[tr], y[tr])
joblib.dump(model, os.path.join(ART, "ids_model.joblib"))

s_te = model.predict_proba(X[te])[:, 1]; pred = (s_te >= 0.5).astype(int)
meta = {"features_n": len(CAN), "best_params": params,
        "metrics_test": {"pr_auc": float(average_precision_score(y[te], s_te)),
                         "roc_auc": float(roc_auc_score(y[te], s_te)),
                         "precision@0.5": float(precision_score(y[te], pred, zero_division=0)),
                         "recall@0.5": float(recall_score(y[te], pred, zero_division=0))}}
json.dump(meta, open(os.path.join(ART, "ids_model_meta.json"), "w"), indent=2)
print("model meta:", meta["metrics_test"])

# ranking d'importance (permutation) sur le test -> pour l'evasion interactive
print("permutation importance (peut prendre ~1-2 min)...")
r = permutation_importance(model, X[te], y[te], scoring="average_precision",
                           n_repeats=2, random_state=0, n_jobs=4)
rank = np.argsort(r.importances_mean)[::-1]

# echantillons attaque / normal du TEST + medianes normales du TRAIN
att_idx = np.where(te & (y == 1))[0]; norm_idx = np.where(te & (y == 0))[0]
att_idx = rng.choice(att_idx, min(4000, len(att_idx)), replace=False)
norm_idx = rng.choice(norm_idx, min(4000, len(norm_idx)), replace=False)
med_norm = np.nanmedian(X[tr][y[tr] == 0], axis=0).astype(np.float32)

np.savez_compressed(os.path.join(ART, "demo_samples.npz"),
                    X_att=X[att_idx], X_norm=X[norm_idx],
                    feat_names=np.array(CAN), med_norm=med_norm,
                    rank=rank.astype(np.int32), importances=r.importances_mean.astype(np.float32))
print(f"[OK] artefacts -> ids_model.joblib ({os.path.getsize(ART+'/ids_model.joblib')/1024:.0f} Ko), "
      f"demo_samples.npz, meta. Top-3 a neutraliser :", [CAN[i] for i in rank[:3]])
