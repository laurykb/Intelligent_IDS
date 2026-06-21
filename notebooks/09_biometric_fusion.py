"""
VAGUE 2 - Item 3 : fusion biometrie CONDITIONNEE par awareness (repond a A5).

P4-A avait conclu "biometrie inutile" (BIO seule 0,014, CAN+BIO 0,749 <= CAN 0,756) -
mais GLOBALEMENT. Or P5+ etablit que le vrai signal est la REACTION, et la biometrie
(HR/EDA) EST la reaction physiologique. On reteste PAR GROUPE d'awareness, en se demandant
surtout : la biometrie aide-t-elle la ou le CAN echoue (Groupe 1, conducteur non averti) ?

Methode : pour chaque groupe, GroupKFold PAR CONDUCTEUR (anti-fuite) sur les conducteurs du
groupe ; PR-AUC de CAN, BIO, CAN+BIO. + normalisation biometrie PAR CONDUCTEUR (z-score sur
le normal du conducteur) car la HR de repos varie d'une personne a l'autre.

Sorties : docs/03_evaluation/results_biofusion.json + docs/assets/v2_biofusion.png
Lancer :  python notebooks/09_biometric_fusion.py
"""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.model_selection import GroupKFold
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score
from data import load
from features import feature_sets

ROOT = os.path.join(os.path.dirname(__file__), "..")
ASSETS, EVAL = f"{ROOT}/docs/assets", f"{ROOT}/docs/03_evaluation"
df = load(); y = df.cyberattack_active.values.astype(int)
drv = df.driver.values; grp = df.Group.values
fs = feature_sets(df); CAN, BIO = fs["CAN"], fs["BIO"]
print(f"{len(CAN)} CAN | {len(BIO)} BIO | base rate {y.mean()*100:.2f}%")
print("BIO :", BIO)

# normalisation biometrie PAR CONDUCTEUR (z-score sur le normal du conducteur)
Xbio = df[BIO].values.astype(np.float64).copy()
for d in pd.unique(drv):
    di = drv == d; norm = di & (y == 0)
    mu = np.nanmean(Xbio[norm], axis=0); sd = np.nanstd(Xbio[norm], axis=0); sd[sd == 0] = 1
    Xbio[di] = (Xbio[di] - mu) / sd
Xcan = df[CAN].values.astype(np.float32)

def prauc_group(g, cols_kind):
    """PR-AUC en GroupKFold conducteur, RESTREINT au groupe g."""
    m = grp == g; gd = drv[m]
    if cols_kind == "CAN": Xg = Xcan[m]
    elif cols_kind == "BIO": Xg = Xbio[m]
    else: Xg = np.hstack([Xcan[m], Xbio[m].astype(np.float32)])
    yg = y[m]
    n_splits = min(4, len(np.unique(gd)) // 2)
    gkf = GroupKFold(n_splits=n_splits); aps = []
    for tr, te in gkf.split(Xg, yg, gd):
        if yg[tr].sum() < 2 or yg[te].sum() < 1: continue
        mdl = HistGradientBoostingClassifier(class_weight="balanced", random_state=0).fit(Xg[tr], yg[tr])
        aps.append(average_precision_score(yg[te], mdl.predict_proba(Xg[te])[:, 1]))
    return float(np.mean(aps)), float(np.std(aps))

res = {}
print("\n=== PR-AUC par groupe (val. par conducteur intra-groupe) ===")
print(f"{'groupe':8} {'CAN':>14} {'BIO seule':>14} {'CAN+BIO':>14}")
for g in sorted(set(grp)):
    r = {k: prauc_group(g, k) for k in ["CAN", "BIO", "CAN+BIO"]}
    res[f"G{g}"] = r
    print(f"  G{g:5} {r['CAN'][0]:.3f}+/-{r['CAN'][1]:.2f}  {r['BIO'][0]:.3f}+/-{r['BIO'][1]:.2f}  "
          f"{r['CAN+BIO'][0]:.3f}+/-{r['CAN+BIO'][1]:.2f}   delta(fusion-CAN)={r['CAN+BIO'][0]-r['CAN'][0]:+.3f}")

# figure
fig, ax = plt.subplots(figsize=(7.8, 4.8))
gs = sorted(set(grp)); x = np.arange(len(gs)); w = 0.26
for i, (k, c) in enumerate(zip(["CAN", "BIO", "CAN+BIO"], ["#2980b9", "#16a085", "#8e44ad"])):
    ax.bar(x + (i-1)*w, [res[f"G{g}"][k][0] for g in gs], w, label=k, color=c)
ax.axhline(y.mean(), ls=":", color="k", lw=1, label=f"hasard ({y.mean():.3f})")
ax.set_xticks(x); ax.set_xticklabels([f"Groupe {g}" for g in gs]); ax.set_ylim(0, 1)
ax.set_ylabel("PR-AUC (val. par conducteur)"); ax.legend()
ax.set_title("Fusion biometrie par groupe d'awareness : aide-t-elle la ou le CAN echoue (G1) ?")
plt.tight_layout(); plt.savefig(f"{ASSETS}/v2_biofusion.png", dpi=120); plt.close()

json.dump(res, open(f"{EVAL}/results_biofusion.json", "w"), indent=2)
print("\n[OK] -> docs/03_evaluation/results_biofusion.json | docs/assets/v2_biofusion.png")
