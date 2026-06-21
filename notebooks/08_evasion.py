"""
VAGUE 2 - Item 2 : attaquant ADAPTATIF / evasion (repond a A3).

Menace : l'ELD compromis ecrit des messages CAN arbitraires (sujet). Un attaquant
white-box qui connait le detecteur peut **maquiller** les signaux discriminants -> faire
paraitre normales les vraies diffusions ECU. On simule cette evasion :
  - on classe les features CAN par importance (permutation) sur le champion ;
  - on neutralise les top-k (pendant les fenetres d'ATTAQUE seulement, on remplace par la
    mediane NORMALE du train) puis on re-score ;
  - on trace PR-AUC(champion) en fonction de k = nb de signaux que l'attaquant controle.

Question : combien de signaux suffisent a evader ? + le signal d'injection (silence CAN0,
item 1) resiste-t-il (il est base sur la MISSINGNESS, pas la valeur) ?

Sorties : docs/03_evaluation/results_evasion.json + docs/assets/v2_evasion.png
Lancer :  python notebooks/08_evasion.py
"""
import os, sys, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.model_selection import GroupKFold
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.inspection import permutation_importance
from sklearn.metrics import average_precision_score
from data import load
from features import feature_sets

ROOT = os.path.join(os.path.dirname(__file__), "..")
ASSETS, EVAL = f"{ROOT}/docs/assets", f"{ROOT}/docs/03_evaluation"
df = load(); y = df.cyberattack_active.values.astype(int); groups = df.driver.values; grp = df.Group.values
CAN = feature_sets(df)["CAN"]; X = df[CAN].values.astype(np.float32)
gkf = GroupKFold(n_splits=4); FOLDS = list(gkf.split(X, y, groups))
K_LIST = [0, 1, 2, 3, 5, 8, 13, 21, 34, 55]
print(f"{len(CAN)} features CAN | base rate {y.mean()*100:.2f}%")

# importance globale (permutation) : on accumule sur les 4 folds (n_repeats=2 pour la vitesse)
t0 = time.time(); imp = np.zeros(len(CAN)); fitted = []
for tr, te in FOLDS:
    m = HistGradientBoostingClassifier(class_weight="balanced", random_state=0).fit(X[tr], y[tr])
    fitted.append(m)
    r = permutation_importance(m, X[te], y[te], scoring="average_precision",
                               n_repeats=2, random_state=0, n_jobs=4)
    imp += r.importances_mean
rank = np.argsort(imp)[::-1]                       # indices des features, + important d'abord
top = [CAN[i] for i in rank[:8]]
print(f"importance calculee ({time.time()-t0:.0f}s). Top-8 features visees par l'attaquant :")
for i in rank[:8]: print(f"   {imp[i]:+.4f}  {CAN[i]}")

# medianes NORMALES (par fold, sur le train normal) pour le maquillage
def evade(k):
    """PR-AUC hors-fold quand l'attaquant neutralise les top-k features sur l'attaque."""
    oof = np.zeros(len(y));
    for (tr, te), m in zip(FOLDS, fitted):
        med = np.nanmedian(X[tr][y[tr] == 0], axis=0)
        Xte = X[te].copy(); att = y[te] == 1
        for idx in rank[:k]:
            Xte[att, idx] = med[idx]                # maquille la valeur -> mediane normale
        oof[te] = m.predict_proba(Xte)[:, 1]
    return oof

res = {}
print("\n=== evasion : PR-AUC(champion) vs nb de signaux neutralises ===")
oof_by_k = {}
for k in K_LIST:
    oof = evade(k); oof_by_k[k] = oof
    res[k] = {"global": float(average_precision_score(y, oof)),
              **{f"G{g}": float(average_precision_score(y[grp == g], oof[grp == g])) for g in sorted(set(grp))}}
    print(f"  k={k:3d} neutralises : PR-AUC global {res[k]['global']:.3f} "
          f"(G1 {res[k]['G1']:.3f} / G2 {res[k]['G2']:.3f} / G3 {res[k]['G3']:.3f})")

base = res[0]["global"]; final = res[K_LIST[-1]]["global"]
# k pour tomber sous la moitie du gain au-dessus du hasard
half = y.mean() + (base - y.mean()) / 2
k_half = next((k for k in K_LIST if res[k]["global"] <= half), None)
print(f"\nPR-AUC {base:.3f} (k=0) -> {final:.3f} (k={K_LIST[-1]}). Passe sous {half:.3f} a k={k_half}.")

# figure
fig, ax = plt.subplots(figsize=(7.5, 4.8))
ks = K_LIST
ax.plot(ks, [res[k]["global"] for k in ks], "-o", color="#c0392b", label="global")
for g, c in zip(sorted(set(grp)), ["#95a5a6", "#2980b9", "#16a085"]):
    ax.plot(ks, [res[k][f"G{g}"] for k in ks], "--", color=c, label=f"Groupe {g}")
ax.axhline(y.mean(), ls=":", color="k", lw=1, label=f"hasard ({y.mean():.3f})")
ax.set_xlabel("nb de signaux CAN neutralises par l'attaquant (top-k importance)")
ax.set_ylabel("PR-AUC du champion"); ax.set_ylim(0, 1); ax.legend()
ax.set_title("Evasion adaptative : fragilite du detecteur a un attaquant ciblant les top signaux")
plt.tight_layout(); plt.savefig(f"{ASSETS}/v2_evasion.png", dpi=120); plt.close()

json.dump({"top_features": top, "k_list": K_LIST, "prauc_vs_k": res,
           "base_prauc": base, "k_under_half_gain": k_half},
          open(f"{EVAL}/results_evasion.json", "w"), indent=2)
print("\n[OK] -> docs/03_evaluation/results_evasion.json | docs/assets/v2_evasion.png")
