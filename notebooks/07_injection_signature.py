"""
VAGUE 2 - Item 1 : isoler la SIGNATURE D'INJECTION pure (repond a A1, la faille la plus grave).

Hypothese de depart (autocritique A1/B3) : la cible melange injection + reaction du
conducteur. On cherche une signature de l'INJECTION elle-meme, independante de la reaction.

Materiau : le SPN 190 (regime moteur) est le SEUL signal present sur DEUX canaux dans le
dataset -> mean/sd/min/max .190.Engine.Speed (bus principal) ET .190.Engine.Speed.CAN0.
On compare les deux bus pendant l'attaque vs normal.

Decouverte : pendant l'attaque, le bus CAN0 se TAIT (les diffusions ECU y disparaissent)
~4 s apres l'onset, alors que le bus principal reste present a ~100 %. C'est une signature
de l'injection (l'ELD compromis sature/brouille CAN0), presente dans TOUS les groupes - donc
non portee par la reaction du conducteur. Limite honnete : pour la plupart des conducteurs
du Groupe 1, CAN0 n'etait deja quasi pas logge (baseline ~0 %) -> rien a faire taire.

Sorties : docs/03_evaluation/results_injection.json + docs/assets/v2_injection_signature.png
Lancer :  python notebooks/07_injection_signature.py
"""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.metrics import average_precision_score, precision_score, recall_score
from data import load

ROOT = os.path.join(os.path.dirname(__file__), "..")
ASSETS, EVAL = f"{ROOT}/docs/assets", f"{ROOT}/docs/03_evaluation"
P, C = "mean.190.Engine.Speed", "mean.190.Engine.Speed.CAN0"

df = load().sort_values(["driver", "interval_1s"]).reset_index(drop=True)
y = df.cyberattack_active.values.astype(int); grp = df.Group.values; drv = df.driver.values
prim = np.isfinite(df[P].values); can0 = np.isfinite(df[C].values)
print(f"base rate attaque = {y.mean()*100:.2f}% | SPN 190 sur 2 bus : {P} & {C}")

# 1. COUVERTURE du bus CAN0 (et du bus principal) attaque vs normal, par groupe
cov = {}
for g in sorted(set(grp)):
    gi = grp == g
    cov[str(g)] = {
        "can0_normal": float(can0[gi & (y == 0)].mean()),
        "can0_attaque": float(can0[gi & (y == 1)].mean()),
        "principal_normal": float(prim[gi & (y == 0)].mean()),
        "principal_attaque": float(prim[gi & (y == 1)].mean())}
cov["GLOBAL"] = {"can0_normal": float(can0[y == 0].mean()), "can0_attaque": float(can0[y == 1].mean()),
                 "principal_normal": float(prim[y == 0].mean()), "principal_attaque": float(prim[y == 1].mean())}
print("\n=== couverture CAN0 (presence) attaque vs normal ===")
for k, v in cov.items():
    print(f"  {k:7}: CAN0 normal {v['can0_normal']*100:5.1f}% -> attaque {v['can0_attaque']*100:5.1f}%"
          f"  | principal {v['principal_normal']*100:5.1f}% -> {v['principal_attaque']*100:5.1f}%")

# 2. ONSET : presence CAN0 moyenne autour du debut d'attaque (par episode)
onsets = [i for i in range(1, len(df)) if y[i] and not y[i-1] and drv[i] == drv[i-1]]
W = 10
prof = np.full((len(onsets), 2*W+1), np.nan)
for k, i in enumerate(onsets):
    for j, off in enumerate(range(-W, W+1)):
        t = i + off
        if 0 <= t < len(df) and drv[t] == drv[i]:
            prof[k, j] = can0[t]
onset_profile = np.nanmean(prof, axis=0)
print(f"\n=== onset ({len(onsets)} episodes) : CAN0 chute a t=+4s ===")
for off, m in zip(range(-W, W+1), onset_profile):
    print(f"  t={off:+3d}s  {m*100:5.1f}%")

# 3. par conducteur : chute CAN0 (attaque vs sa propre baseline normale, moteur tournant)
rows = []
for d in pd.unique(drv):
    di = drv == d; n = di & (y == 0) & prim; at = di & (y == 1) & prim
    if at.sum() < 5 or n.sum() < 50: continue
    b, a = can0[n].mean(), can0[at].mean()
    rows.append((d, int(grp[di][0]), b, a, b - a))
R = pd.DataFrame(rows, columns=["drv", "g", "base", "att", "drop"])
n_drop = int((R["drop"] > 0.2).sum())
print(f"\n=== {n_drop}/{len(R)} conducteurs avec chute CAN0 > 20 pts pendant l'attaque ===")

# 4. detecteur CHUTE-RELATIVE intra-conducteur (IDS calibre par vehicule, sans labels d'attaque)
roll = np.zeros(len(df)); Wr = 8
for d in pd.unique(drv):
    idx = np.where(drv == d)[0]; v = can0[idx].astype(float)
    cs = np.concatenate([[0], np.cumsum(v)])
    roll[idx] = [(cs[min(i+1, len(v))] - cs[max(0, i+1-Wr)]) / min(i+1, Wr) for i in range(len(v))]
base_by = {d: can0[(drv == d) & (y == 0) & prim].mean() for d in pd.unique(drv)}
basev = np.array([base_by[d] for d in drv])
score = np.clip(basev - roll, 0, 1) * prim     # chute relative a la baseline du conducteur

det = {}
print("\n=== detecteur SILENCE-CAN0 (chute relative) : PR-AUC + P/R@0.4 ===")
for g in ["GLOBAL"] + [str(x) for x in sorted(set(grp))]:
    m = np.ones(len(y), bool) if g == "GLOBAL" else (grp == int(g))
    yy, ss = y[m], score[m]; pred = (ss >= 0.4).astype(int)
    det[g] = {"pr_auc": float(average_precision_score(yy, ss)),
              "precision@0.4": float(precision_score(yy, pred, zero_division=0)),
              "recall@0.4": float(recall_score(yy, pred, zero_division=0))}
    print(f"  {g:7}: PR-AUC {det[g]['pr_auc']:.3f}  P {det[g]['precision@0.4']:.3f}  R {det[g]['recall@0.4']:.3f}")

# 5. figure : (a) onset step, (b) couverture CAN0 par groupe
fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 4.6))
tt = list(range(-W, W+1))
a1.step(tt, onset_profile*100, where="mid", color="#c0392b", lw=2)
a1.axvline(0, ls="--", color="k", lw=1); a1.axvspan(0, W, color="#c0392b", alpha=0.06)
a1.set_xlabel("temps relatif a l'onset d'attaque (s)"); a1.set_ylabel("presence du bus CAN0 (%)")
a1.set_title(f"Signature d'injection : CAN0 se tait a t=+4s ({len(onsets)} episodes)")
a1.set_ylim(-3, 100); a1.annotate("injection", (5, 8), color="#c0392b")

labels = [str(g) for g in sorted(set(grp))]; x = np.arange(len(labels)); w = 0.38
a2.bar(x - w/2, [cov[g]["can0_normal"]*100 for g in labels], w, label="normal", color="#2980b9")
a2.bar(x + w/2, [cov[g]["can0_attaque"]*100 for g in labels], w, label="attaque", color="#c0392b")
a2.set_xticks(x); a2.set_xticklabels([f"Groupe {g}" for g in labels])
a2.set_ylabel("presence CAN0 (%)"); a2.set_ylim(0, 100); a2.legend()
a2.set_title("Le bus CAN0 disparait pendant l'attaque (tous groupes)")
plt.tight_layout(); plt.savefig(f"{ASSETS}/v2_injection_signature.png", dpi=120); plt.close()

json.dump({"coverage": cov, "onset_profile": [float(v) for v in onset_profile],
           "n_onsets": len(onsets), "drivers_with_drop": [n_drop, len(R)],
           "per_driver_drop_median_pts": {str(g): float(R[R["g"] == g]["drop"].median()*100)
                                          for g in sorted(R["g"].unique())},
           "detector_silence_can0": det},
          open(f"{EVAL}/results_injection.json", "w"), indent=2)
print("\n[OK] -> docs/03_evaluation/results_injection.json | docs/assets/v2_injection_signature.png")
