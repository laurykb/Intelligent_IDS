"""
P5+ - Pourquoi l'IDS echoue sur le Groupe 1 ? + robustesse.

Rappel (README) : l'attaque met tachymetre/compteur a ZERO et s'arrete apres 1 min
OU si le conducteur se gare. Awareness :
  - Groupe 1 (17) : AUCUNE connaissance prealable.
  - Groupe 2 (16) : prevenu qu'une attaque peut survenir.
  - Groupe 3 (17) : prevenu + consigne de SE GARER.

En P5, le LODO s'effondre surtout sur des conducteurs du Groupe 1. On teste l'hypothese :
la REACTION du conducteur (donc la signature CAN de l'attaque) depend de l'awareness.

Volets :
  A. LODO (P5) agrege PAR GROUPE.
  B. Leave-one-group-out (transfert) : train 2 groupes -> test le 3e.
  C. Detectabilite INTRA-groupe (train/test dans le meme groupe).
  D. Signature du regime moteur (SPN 190) par groupe : l'attaque le perturbe-t-elle pareil ?
  E. Robustesse du champion sous bruit gaussien.

Lancer :  python notebooks/05_group_analysis.py
"""
import os, sys, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.model_selection import GroupKFold
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import average_precision_score
from data import load
from features import feature_sets, driver_holdout

ROOT = os.path.join(os.path.dirname(__file__), "..")
ASSETS, EVAL = f"{ROOT}/docs/assets", f"{ROOT}/docs/03_evaluation"

df = load(); y = df.cyberattack_active.values.astype(int)
groups = df.driver.values; grp = df.Group.values
CAN = feature_sets(df)["CAN"]; X = df[CAN]
def champion(): return HistGradientBoostingClassifier(class_weight="balanced", random_state=0)
print(f"base rate {y.mean():.4f} | {len(CAN)} features CAN\n")

# ===================================================== A. LODO de P5 agrege par groupe
print("=== A. LODO (P5) par groupe ===")
lodo = json.load(open(f"{EVAL}/results_evaluation.json"))["lodo_par_conducteur"]
lo = pd.Series(lodo)
by_g = {g: lo[[k for k in lo.index if k.startswith(f"{g}_")]] for g in ["1", "2", "3"]}
for g, s in by_g.items():
    print(f"  Groupe {g} : mediane {s.median():.3f} | moyenne {s.mean():.3f} | "
          f"{(s < 0.5).sum()}/{len(s)} conducteurs < 0,50")

# ===================================================== B. Leave-one-group-out (transfert)
print("\n=== B. Leave-one-group-out : train sur 2 groupes -> test le 3e ===")
logo = {}
for held in [1, 2, 3]:
    te = (grp == held); tr = ~te
    m = champion().fit(X[tr], y[tr])
    s = m.predict_proba(X[te])[:, 1]
    logo[held] = float(average_precision_score(y[te], s))
    print(f"  test Groupe {held} (train sur les 2 autres) : PR-AUC = {logo[held]:.3f}")

# ===================================================== C. Detectabilite intra-groupe
print("\n=== C. Detectabilite INTRA-groupe (GroupKFold par conducteur, dans le groupe) ===")
intra = {}
for g in [1, 2, 3]:
    idx = np.where(grp == g)[0]
    Xg, yg, gg = X.iloc[idx], y[idx], groups[idx]
    aps = []
    for tr, te in GroupKFold(n_splits=4).split(Xg, yg, gg):
        m = champion().fit(Xg.iloc[tr], yg[tr])
        aps.append(average_precision_score(yg[te], m.predict_proba(Xg.iloc[te])[:, 1]))
    intra[g] = (float(np.mean(aps)), float(np.std(aps)))
    print(f"  Groupe {g} (train+test dans le groupe) : PR-AUC = {intra[g][0]:.3f} +/- {intra[g][1]:.3f}")

# ===================================================== D. Signature du regime moteur par groupe
print("\n=== D. Signature regime moteur (SPN 190) attaque vs normal, par groupe ===")
def cohend(a, b):
    a, b = a[~np.isnan(a)], b[~np.isnan(b)]
    s = np.sqrt(((len(a)-1)*a.var()+(len(b)-1)*b.var())/max(1, len(a)+len(b)-2))
    return (a.mean()-b.mean())/s if s > 0 else np.nan, a.mean(), b.mean()
sig_cols = ["mean.190.Engine.Speed.CAN0", "mean.190.Engine.Speed", "sd.190.Engine.Speed.CAN0"]
sig = {}
for col in sig_cols:
    if col not in df: continue
    print(f"  [{col}]")
    sig[col] = {}
    for g in [1, 2, 3]:
        mg = (grp == g)
        d, ma, mn = cohend(df[col].values[mg & (y == 1)], df[col].values[mg & (y == 0)])
        sig[col][g] = float(d)
        print(f"    Groupe {g} : d = {d:+.2f}  (attaque moy {ma:8.1f} | normal moy {mn:8.1f})")

# duree des episodes d'attaque par groupe (secondes d'attaque / conducteur)
dur = df[y == 1].groupby("Group").size() / df[y == 1].groupby("Group")["driver"].nunique()
print("  duree moyenne d'attaque par conducteur (s) :",
      {int(g): round(float(v), 1) for g, v in dur.items()})

# ===================================================== E. Robustesse sous bruit
print("\n=== E. Robustesse du champion sous bruit gaussien (split conducteur) ===")
tr_m, te_m = driver_holdout(df, n_test=12, seed=0)
m = champion().fit(X[tr_m], y[tr_m])
Xte = X[te_m].values; yte = y[te_m]
sd_col = np.nanstd(X[tr_m].values, axis=0)
rob = {}
rng = np.random.RandomState(0)
for lvl in [0.0, 0.05, 0.1, 0.25, 0.5]:
    Xn = Xte + rng.normal(0, 1, Xte.shape) * sd_col * lvl
    rob[lvl] = float(average_precision_score(yte, m.predict_proba(Xn)[:, 1]))
    print(f"  bruit {int(lvl*100):>3}% de sigma : PR-AUC = {rob[lvl]:.3f}")

# ===================================================== sauvegardes + figures
out = {"lodo_par_groupe": {g: [float(s.median()), float(s.mean()), int((s < 0.5).sum()), len(s)]
                           for g, s in by_g.items()},
       "leave_one_group_out": logo, "intra_groupe": intra,
       "signature_190": sig, "duree_attaque_s": {int(g): float(v) for g, v in dur.items()},
       "robustesse_bruit": rob}
json.dump(out, open(f"{EVAL}/results_group_analysis.json", "w"), indent=2)

fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5))
# gauche : transfert (LOGO) vs intra-groupe
gx = [1, 2, 3]; w = 0.38
a1.bar([g - w/2 for g in gx], [logo[g] for g in gx], w, color="#c0392b", label="transfert (train autres groupes)")
a1.bar([g + w/2 for g in gx], [intra[g][0] for g in gx], w, yerr=[intra[g][1] for g in gx],
       color="#16a085", capsize=4, label="intra-groupe (train meme groupe)")
a1.axhline(y.mean(), ls="--", color="k", lw=1, label=f"hasard ({y.mean():.3f})")
a1.set_xticks(gx); a1.set_xticklabels([f"Groupe {g}" for g in gx]); a1.set_ylim(0, 1)
a1.set_ylabel("PR-AUC"); a1.set_title("Detection : transfert vs intra-groupe"); a1.legend(fontsize=8)
for g in gx:
    a1.text(g - w/2, logo[g], f"{logo[g]:.2f}", ha="center", va="bottom", fontsize=8)
    a1.text(g + w/2, intra[g][0], f"{intra[g][0]:.2f}", ha="center", va="bottom", fontsize=8)
# droite : signature regime moteur (Cohen's d) par groupe
col0 = "mean.190.Engine.Speed.CAN0"
ds = [sig[col0][g] for g in gx]
a2.bar([f"Groupe {g}" for g in gx], ds, color=["#e67e22", "#2980b9", "#8e44ad"])
a2.axhline(0, color="k", lw=0.8)
a2.set_ylabel("Cohen's d (attaque - normal)"); a2.set_title("Effet de l'attaque sur le regime moteur (190.CAN0)")
for i, d in enumerate(ds): a2.text(i, d, f"{d:+.2f}", ha="center", va="bottom" if d >= 0 else "top")
plt.tight_layout(); plt.savefig(f"{ASSETS}/p5b_group_analysis.png", dpi=120); plt.close()
print("\n[OK] figure -> docs/assets/p5b_group_analysis.png | resultats -> docs/03_evaluation/results_group_analysis.json")
