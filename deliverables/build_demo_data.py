"""
Construit le paquet de donnees REELLES pour la demo interactive (deliverables/demo_data.json).
Source : oof_scores.npz (scores hors-fold du champion) + cache + JSON de resultats.
Aucun reentrainement : on montre de vraies predictions held-out.
"""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np, pandas as pd
from sklearn.metrics import roc_curve, precision_recall_curve
from data import load

ROOT = os.path.join(os.path.dirname(__file__), "..")
EVAL = f"{ROOT}/docs/03_evaluation"
oof = np.load(f"{EVAL}/oof_scores.npz", allow_pickle=True)
s = oof["oof"]; y = oof["y"].astype(int); drv = oof["driver"].astype(str); itv = oof["interval"]

df = load()
df = df.assign(_s=np.nan)  # aligner les scores par (driver, interval)
key = {(d, int(t)): sc for d, t, sc in zip(drv, itv, s)}
es = df["mean.190.Engine.Speed"].values
can0 = np.isfinite(df["mean.190.Engine.Speed.CAN0"].values).astype(int)
grp = df.Group.values; D = df.driver.values; T = df["interval_1s"].values
Y = df.cyberattack_active.values.astype(int)
score = np.array([key.get((d, int(t)), np.nan) for d, t in zip(D, T)])

def episode_trace(driver, pad_before=40, pad_after=20, maxpts=160):
    m = np.where(D == driver)[0]
    order = m[np.argsort(T[m])]
    yy = Y[order]
    att = np.where(yy == 1)[0]
    if len(att) == 0: return None
    a0, a1 = att.min(), att.max()
    lo = max(0, a0 - pad_before); hi = min(len(order), a1 + pad_after)
    sel = order[lo:hi]
    # sous-echantillonnage si trop long
    if len(sel) > maxpts:
        sel = sel[np.linspace(0, len(sel)-1, maxpts).astype(int)]
    t0 = T[sel][0]
    return {"driver": driver, "group": int(grp[sel][0]),
            "t": [int(T[i]-t0) for i in sel],
            "engine_speed": [round(float(es[i]), 1) if np.isfinite(es[i]) else None for i in sel],
            "can0_present": [int(can0[i]) for i in sel],
            "score": [round(float(score[i]), 4) if np.isfinite(score[i]) else None for i in sel],
            "attack": [int(Y[i]) for i in sel]}

# traces pour TOUS les conducteurs (page "detection en direct") + 2 mis en avant
base_can0 = {d: can0[(D == d) & (Y == 0)].mean() for d in pd.unique(D)}
att_score = {d: np.nanmean(score[(D == d) & (Y == 1)]) for d in pd.unique(D)}
episodes_all = {}
for d in pd.unique(D):
    tr = episode_trace(d)
    if tr is not None:
        tr["mean_score_attack"] = round(float(att_score[d]), 3) if np.isfinite(att_score[d]) else None
        episodes_all[str(d)] = tr
cand_reactif = [d for d in pd.unique(D) if grp[D == d][0] in (2, 3) and base_can0[d] > 0.7
                and (Y[D == d] == 1).sum() > 20 and np.isfinite(att_score[d])]
reactif = max(cand_reactif, key=lambda d: att_score[d])
cand_g1 = [d for d in pd.unique(D) if grp[D == d][0] == 1 and (Y[D == d] == 1).sum() > 20]
difficile = min(cand_g1, key=lambda d: att_score[d] if np.isfinite(att_score[d]) else 1)
print(f"{len(episodes_all)} traces | reactif mis en avant = {reactif} (score {att_score[reactif]:.2f}) | difficile = {difficile}")

# courbes ROC / PR (sous-echantillonnees pour le web)
def thin(x, y_, n=120):
    idx = np.linspace(0, len(x)-1, min(n, len(x))).astype(int)
    return [round(float(x[i]), 4) for i in idx], [round(float(y_[i]), 4) for i in idx]
fpr, tpr, _ = roc_curve(y, s); prec, rec, _ = precision_recall_curve(y, s)
roc_x, roc_y = thin(fpr, tpr); pr_x, pr_y = thin(rec[::-1], prec[::-1])

# table de seuils (precision/rappel/alertes) pour le curseur
ths = np.linspace(0.01, 0.99, 99)
thr_table = []
for t in ths:
    pred = s >= np.quantile(s, t)
    tp = int(((pred == 1) & (y == 1)).sum()); fp = int(((pred == 1) & (y == 0)).sum())
    pos = int(pred.sum()); P = tp/pos if pos else 0; R = tp/int(y.sum())
    thr_table.append({"q": round(float(t), 2), "precision": round(P, 3), "recall": round(R, 3),
                      "alert_rate": round(pos/len(y), 4)})

def jload(name):
    p = f"{EVAL}/{name}"
    return json.load(open(p)) if os.path.exists(p) else {}

out = {
    "meta": {"n_windows": int(len(df)), "n_drivers": int(df.driver.nunique()),
             "attack_rate": round(float(Y.mean()), 4)},
    "models": {**{k.replace("model_", ""): v for k, v in jload("results_supervised.json").items() if k.startswith("model_")},
               "MLP": [0.543, 0.016], "GRU": [0.571, 0.024], "Anomalie (best)": [0.021, 0.002]},
    "ablation": {k.replace("abl_", ""): v for k, v in jload("results_supervised.json").items() if k.startswith("abl_")},
    "leak_demo": {"split aleatoire (FUITE)": 0.985, "split par conducteur": 0.632, "GPS (confondeur)": 0.835},
    "roc": {"fpr": roc_x, "tpr": roc_y, "auc": jload("results_roc.json").get("auc_roc")},
    "pr": {"recall": pr_x, "precision": pr_y, "auc": jload("results_roc.json").get("pr_auc_oof")},
    "thresholds": thr_table,
    "tuning": jload("results_tuning.json"),
    "multiseed": jload("results_multiseed.json"),
    "injection": jload("results_injection.json"),
    "evasion": jload("results_evasion.json"),
    "taxonomy": jload("results_taxonomy.json"),
    "characterization": jload("results_characterization.json"),
    "episodes_all": episodes_all,
    "highlights": {"reactif": str(reactif), "difficile": str(difficile)},
}
os.makedirs(f"{ROOT}/deliverables", exist_ok=True)
json.dump(out, open(f"{ROOT}/deliverables/demo_data.json", "w"), indent=1)
print(f"[OK] deliverables/demo_data.json ({os.path.getsize(f'{ROOT}/deliverables/demo_data.json')/1024:.0f} Ko)")
