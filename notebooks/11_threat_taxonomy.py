"""
VAGUE 2 - Item 5 : taxonomie de menaces + injections SYNTHETIQUES (repond a A3 / B2).

Le dataset ne contient QU'UNE attaque (mise a zero tachymetre/instrument cluster). Notre IDS
est donc de fait un detecteur MONO-ATTAQUE. On teste sa generalisation a d'AUTRES types
d'attaques J1939, fabriquees synthetiquement sur des fenetres NORMALES held-out :

  Taxonomie testee (sur les features CAN agregees 1 s) :
   - DoS / silence de bus : on coupe le bus CAN0 (NaN) -> mime la signature reelle (item 1).
   - Fuzzing : on randomise 20 % des signaux CAN (valeurs hors-plage).
   - Masquerade furtif : on ne touche QUE le regime moteur (190), shift plausible -> doit evader.
   - Replay : on rejoue les valeurs CAN d'une AUTRE fenetre normale (mauvais contexte).

Metrique : taux de detection (rappel) au seuil haute-precision du champion (~1 % d'alertes
calibre sur le normal reel). Compare au rappel sur l'attaque REELLE.

Sorties : results_taxonomy.json + v2_taxonomy.png    Lancer : python notebooks/11_threat_taxonomy.py
"""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.impute import SimpleImputer
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.metrics import recall_score
from data import load
from features import feature_sets, driver_holdout

ROOT = os.path.join(os.path.dirname(__file__), "..")
ASSETS, EVAL = f"{ROOT}/docs/assets", f"{ROOT}/docs/03_evaluation"
df = load().reset_index(drop=True)
y = df.cyberattack_active.values.astype(int); drv = df.driver.values
CAN = feature_sets(df)["CAN"]; X = df[CAN].values.astype(np.float32)
tr, te = driver_holdout(df, n_test=12, seed=0)
rng = np.random.RandomState(0)
print(f"{len(CAN)} CAN | train {tr.sum()} / test {te.sum()}")

# champion entraine sur la VRAIE attaque (HistGB gere les NaN nativement -> pas d'imputation)
champ = HistGradientBoostingClassifier(class_weight="balanced", random_state=0).fit(X[tr], y[tr])
s_normal_real = champ.predict_proba(X[te][y[te] == 0])[:, 1]
thr = np.quantile(s_normal_real, 0.99)         # seuil ~1 % d'alertes sur le normal reel
fp_rate = float((s_normal_real >= thr).mean())
# rappel sur l'attaque REELLE (reference)
s_att_real = champ.predict_proba(X[te][y[te] == 1])[:, 1]
recall_real = float((s_att_real >= thr).mean())
print(f"seuil @1% (taux fausses alertes reel = {fp_rate*100:.2f}%) | rappel attaque REELLE = {recall_real:.3f}")

# pool de fenetres NORMALES held-out a transformer en attaques synthetiques
norm_idx = np.where(te & (y == 0))[0]
pool = rng.choice(norm_idx, min(4000, len(norm_idx)), replace=False)
Xn = X[pool].copy()
col = {c: i for i, c in enumerate(CAN)}
can0_cols = [col[c] for c in CAN if c.endswith(".CAN0")]
spn190 = [col[c] for c in CAN if ".190.Engine.Speed" in c and not c.endswith(".CAN0")]

def detect_rate(Xmod):
    return float((champ.predict_proba(Xmod)[:, 1] >= thr).mean())

attacks = {}
# 1. DoS / silence de bus : couper CAN0
Xa = Xn.copy(); Xa[:, can0_cols] = np.nan; attacks["DoS_silence_bus"] = detect_rate(Xa)
# 2. Fuzzing : randomiser 20% des colonnes CAN avec des valeurs hors-plage
Xa = Xn.copy(); fz = rng.choice(len(CAN), int(0.2*len(CAN)), replace=False)
hi = np.nanpercentile(X[tr], 99, axis=0); lo = np.nanpercentile(X[tr], 1, axis=0)
for j in fz:
    Xa[:, j] = rng.uniform(lo[j], hi[j], size=len(Xa)) * rng.choice([1, 3], size=len(Xa))
attacks["Fuzzing_20pct"] = detect_rate(Xa)
# 3. Masquerade furtif : ne toucher QUE le regime moteur (shift plausible ~ -200 rpm)
Xa = Xn.copy(); Xa[:, spn190] = Xa[:, spn190] - 200; attacks["Masquerade_furtif_190"] = detect_rate(Xa)
# 4. Replay : rejouer les valeurs CAN d'une AUTRE fenetre normale (permutation des lignes)
Xa = Xn[rng.permutation(len(Xn))].copy(); attacks["Replay_autre_fenetre"] = detect_rate(Xa)

attacks_full = {"attaque_REELLE (ref)": recall_real, **attacks}
print("\n=== taux de detection par type d'attaque (seuil @1% d'alertes) ===")
for k, v in attacks_full.items():
    print(f"  {k:26} {v*100:5.1f}%")

# figure
fig, ax = plt.subplots(figsize=(8.2, 4.6))
ks = list(attacks_full); vals = [attacks_full[k]*100 for k in ks]
cols_ = ["#2c3e50", "#16a085", "#e67e22", "#c0392b", "#7f8c8d"]
ax.barh(ks[::-1], vals[::-1], color=cols_[::-1])
for i, v in enumerate(vals[::-1]): ax.text(v, i, f" {v:.0f}%", va="center")
ax.axvline(fp_rate*100, ls=":", color="k", lw=1, label=f"fausses alertes ({fp_rate*100:.1f}%)")
ax.set_xlabel("taux de détection (%)"); ax.set_xlim(0, 100); ax.legend()
ax.set_title("Généralisation hors mono-attaque : détection d'attaques J1939 synthétiques")
plt.tight_layout(); plt.savefig(f"{ASSETS}/v2_taxonomy.png", dpi=120); plt.close()

json.dump({"threshold_quantile": 0.99, "false_alert_rate": fp_rate,
           "detection_rates": attacks_full}, open(f"{EVAL}/results_taxonomy.json", "w"), indent=2)
print("\n[OK] -> docs/03_evaluation/results_taxonomy.json | docs/assets/v2_taxonomy.png")
