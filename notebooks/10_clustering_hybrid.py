"""
VAGUE 2 - Item 4 : clustering + SVM-RBF + semi-supervise + IDS HYBRIDE (repond a A4).

Quatre angles que l'auto-critique listait comme non explores :
  1. SVM a noyau RBF (seul le lineaire avait ete teste) - sur sous-echantillon (O(n^2)).
  2. Clustering non supervise (K-means, GMM) : l'attaque est-elle isolable sans labels ?
  3. Semi-supervise (self-training) : courbe d'efficacite-label (l'unlabeled aide-t-il ?).
  4. IDS HYBRIDE : champion supervise (reaction) UNION detecteur d'injection (silence CAN0,
     item 1). Couvre-t-il mieux que le champion seul ?

Split : driver_holdout (anti-fuite). Sorties : results_hybrid.json + v2_hybrid.png
Lancer :  python notebooks/10_clustering_hybrid.py
"""
import os, sys, json, time, warnings
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
warnings.filterwarnings("ignore")
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from sklearn.svm import SVC
from sklearn.semi_supervised import SelfTrainingClassifier
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score, adjusted_rand_score, precision_score, recall_score
from data import load
from features import feature_sets, driver_holdout

ROOT = os.path.join(os.path.dirname(__file__), "..")
ASSETS, EVAL = f"{ROOT}/docs/assets", f"{ROOT}/docs/03_evaluation"
df = load().sort_values(["driver", "interval_1s"]).reset_index(drop=True)
y = df.cyberattack_active.values.astype(int); drv = df.driver.values
CAN = feature_sets(df)["CAN"]; X = df[CAN].values.astype(np.float32)
tr, te = driver_holdout(df, n_test=12, seed=0)
rng = np.random.RandomState(0)
print(f"{len(CAN)} CAN | train {tr.sum()} / test {te.sum()} | base rate {y.mean()*100:.2f}%")
out = {}

# pipeline d'imputation/standardisation ajuste sur le train (anti-fuite)
imp = SimpleImputer(strategy="median").fit(X[tr]); sc = StandardScaler().fit(imp.transform(X[tr]))
Xtr = sc.transform(imp.transform(X[tr])).astype(np.float32)
Xte = sc.transform(imp.transform(X[te])).astype(np.float32)

# --- 1. SVM-RBF (sous-echantillon, O(n^2)) ---
try:
    t0 = time.time()
    idx = rng.choice(np.where(tr)[0], min(15000, tr.sum()), replace=False)
    Xs = sc.transform(imp.transform(X[idx])); ys = y[idx]
    svm = SVC(kernel="rbf", class_weight="balanced", C=1.0, gamma="scale").fit(Xs, ys)
    s = svm.decision_function(Xte)
    out["svm_rbf_prauc"] = float(average_precision_score(y[te], s))
    print(f"[1] SVM-RBF (n={len(idx)}) PR-AUC test = {out['svm_rbf_prauc']:.3f}  ({time.time()-t0:.0f}s)")
except Exception as e:
    out["svm_rbf_prauc"] = None; print(f"[1] SVM-RBF echoue : {e}")

# --- 2. Clustering : l'attaque est-elle isolable sans labels ? ---
km = KMeans(n_clusters=20, n_init=4, random_state=0).fit(Xtr)
lab_te = km.predict(Xte)
# purete : meilleure PR-AUC en utilisant le taux d'attaque par cluster comme score
rate = {c: y[te][lab_te == c].mean() for c in np.unique(lab_te)}
clu_score = np.array([rate[c] for c in lab_te])
out["kmeans_prauc_via_cluster_rate"] = float(average_precision_score(y[te], clu_score))
out["kmeans_ari_vs_attack"] = float(adjusted_rand_score(y[te], lab_te))
out["kmeans_ari_vs_driver"] = float(adjusted_rand_score(drv[te], lab_te))
gmm = GaussianMixture(n_components=10, covariance_type="diag", random_state=0).fit(Xtr[rng.choice(len(Xtr), 40000, replace=False)])
gl = gmm.predict(Xte); grate = {c: y[te][gl == c].mean() for c in np.unique(gl)}
out["gmm_prauc_via_cluster_rate"] = float(average_precision_score(y[te], np.array([grate[c] for c in gl])))
print(f"[2] Clustering KMeans: PR-AUC(via taux cluster)={out['kmeans_prauc_via_cluster_rate']:.3f} "
      f"| ARI vs attaque={out['kmeans_ari_vs_attack']:.3f} vs conducteur={out['kmeans_ari_vs_driver']:.3f} "
      f"| GMM PR-AUC={out['gmm_prauc_via_cluster_rate']:.3f}")

# --- 3. Semi-supervise : l'unlabeled aide-t-il ? (courbe efficacite-label) ---
semi = {}
base = HistGradientBoostingClassifier(class_weight="balanced", random_state=0)
for frac in [0.05, 0.1, 0.25, 1.0]:
    keep = rng.rand(tr.sum()) < frac          # fraction de labels conserves
    # (a) supervise sur la fraction labellisee seulement
    sup = HistGradientBoostingClassifier(class_weight="balanced", random_state=0).fit(Xtr[keep], y[tr][keep])
    pa_sup = average_precision_score(y[te], sup.predict_proba(Xte)[:, 1])
    # (b) self-training : labels masques (-1) pour le reste du train
    yl = y[tr].copy(); yl[~keep] = -1
    try:
        st = SelfTrainingClassifier(base, threshold=0.9, max_iter=3).fit(Xtr, yl)
        pa_semi = average_precision_score(y[te], st.predict_proba(Xte)[:, 1])
    except Exception:
        pa_semi = None
    semi[str(frac)] = {"supervise": float(pa_sup), "self_training": (float(pa_semi) if pa_semi else None)}
    print(f"[3] {int(frac*100):3d}% labels : supervise {pa_sup:.3f} | self-training {pa_semi if pa_semi is None else round(pa_semi,3)}")
out["semi_supervised"] = semi

# --- 4. IDS HYBRIDE : champion (reaction) UNION signature d'injection (silence CAN0) ---
champ = HistGradientBoostingClassifier(class_weight="balanced", random_state=0).fit(Xtr, y[tr])
s_champ = champ.predict_proba(Xte)[:, 1]
# detecteur silence CAN0 (par vehicule), recalcule (cf. item 1)
C = "mean.190.Engine.Speed.CAN0"; P = "mean.190.Engine.Speed"
can0 = np.isfinite(df[C].values); prim = np.isfinite(df[P].values); W = 8
roll = np.zeros(len(df))
for d in pd.unique(drv):
    ii = np.where(drv == d)[0]; v = can0[ii].astype(float); cs = np.concatenate([[0], np.cumsum(v)])
    roll[ii] = [(cs[min(i+1, len(v))] - cs[max(0, i+1-W)]) / min(i+1, W) for i in range(len(v))]
base_by = {d: can0[(drv == d) & (y == 0) & prim].mean() for d in pd.unique(drv)}
basev = np.array([base_by[d] for d in drv])
s_inj_full = np.clip(basev - roll, 0, 1) * prim
s_inj = s_inj_full[te]
def norm(a): a = np.nan_to_num(a, nan=0.0); return (a - a.min()) / (a.max() - a.min() + 1e-9)
s_hybrid = np.maximum(norm(s_champ), norm(s_inj))     # union (max) des deux axes normalises
yt = y[te]
for tag, s in [("champion", s_champ), ("injection", s_inj), ("HYBRIDE", s_hybrid)]:
    pa = average_precision_score(yt, s); thr = np.quantile(s, 0.99)  # operer a ~1% d'alertes
    pred = (s >= thr).astype(int)
    out.setdefault("hybrid", {})[tag] = {"pr_auc": float(pa),
        "precision@1pct": float(precision_score(yt, pred, zero_division=0)),
        "recall@1pct": float(recall_score(yt, pred, zero_division=0))}
    print(f"[4] {tag:9}: PR-AUC {pa:.3f} | @1% alertes  P {out['hybrid'][tag]['precision@1pct']:.3f}  R {out['hybrid'][tag]['recall@1pct']:.3f}")

# figure : courbe semi-sup + barres hybride
fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.6))
fr = [0.05, 0.1, 0.25, 1.0]
a1.plot([f*100 for f in fr], [semi[str(f)]["supervise"] for f in fr], "-o", label="supervisé", color="#2980b9")
st_vals = [semi[str(f)]["self_training"] for f in fr]
if all(v is not None for v in st_vals):
    a1.plot([f*100 for f in fr], st_vals, "-s", label="self-training", color="#8e44ad")
a1.set_xlabel("% de labels conservés"); a1.set_ylabel("PR-AUC (test, conducteurs held-out)")
a1.set_title("Semi-supervisé : l'unlabeled aide-t-il ?"); a1.legend(); a1.set_ylim(0, 1)
tags = ["champion", "injection", "HYBRIDE"]
a2.bar(tags, [out["hybrid"][t]["pr_auc"] for t in tags], color=["#2980b9", "#c0392b", "#16a085"])
for i, t in enumerate(tags): a2.text(i, out["hybrid"][t]["pr_auc"], f"{out['hybrid'][t]['pr_auc']:.2f}", ha="center", va="bottom")
a2.set_ylabel("PR-AUC (test)"); a2.set_ylim(0, 1); a2.set_title("IDS hybride : champion ∪ signature d'injection")
plt.tight_layout(); plt.savefig(f"{ASSETS}/v2_hybrid.png", dpi=120); plt.close()

json.dump(out, open(f"{EVAL}/results_hybrid.json", "w"), indent=2)
print("\n[OK] -> docs/03_evaluation/results_hybrid.json | docs/assets/v2_hybrid.png")
