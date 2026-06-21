"""
AUTOCRITIQUE_V2 - B3 (caracteriser finement l'attaque) + B4 (faisabilite : latence/memoire).
Reste IN-SCOPE de la seconde auto-critique.

B3 : on caracterise la SIGNATURE de l'attaque dans le CAN au niveau de l'onset. Pour chaque
signal CAN (z-score), on aligne sur le debut d'attaque (51 episodes) et on mesure le STEP =
moyenne[t in +4..+10s] - moyenne[t in -10..-1s]. La fenetre +-10 s filtre les confondeurs a
derive lente (qui ne font pas de marche a +4 s). On classe les signaux par |step| -> empreinte.
On distingue VALEUR (le signal change) et DISPONIBILITE (le signal disparait = silence de bus).

B4 : empreinte memoire du champion (taille serialisee) + latence d'inference par fenetre (ms),
et rappel de la limite d'agregation 1 s (signature sous-seconde perdue).

Sorties : results_characterization.json + v2_attack_fingerprint.png
Lancer :  python notebooks/12_attack_characterization.py
"""
import os, sys, json, time, pickle
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.ensemble import HistGradientBoostingClassifier
from data import load
from features import feature_sets, driver_holdout

ROOT = os.path.join(os.path.dirname(__file__), "..")
ASSETS, EVAL = f"{ROOT}/docs/assets", f"{ROOT}/docs/03_evaluation"
df = load().sort_values(["driver", "interval_1s"]).reset_index(drop=True)
y = df.cyberattack_active.values.astype(int); drv = df.driver.values
CAN = feature_sets(df)["CAN"]; X = df[CAN].values.astype(np.float64)

# ---- B3 : empreinte de l'attaque a l'onset ----
W = 10
onsets = [i for i in range(1, len(df)) if y[i] and not y[i-1] and drv[i] == drv[i-1]]
# matrice d'indices (n_onsets x 2W+1) avec validite (meme conducteur)
idxm = np.full((len(onsets), 2*W+1), -1)
for k, i in enumerate(onsets):
    for j, off in enumerate(range(-W, W+1)):
        t = i + off
        if 0 <= t < len(df) and drv[t] == drv[i]: idxm[k, j] = t
valid = idxm >= 0
pre = slice(0, W); post = slice(W+4, 2*W+1)         # avant onset / apres +4s

# z-score global par signal + disponibilite
mu = np.nanmean(X, axis=0); sd = np.nanstd(X, axis=0); sd[sd == 0] = 1
Z = (X - mu) / sd
avail = np.isfinite(X).astype(float)                # 1 si present

def onset_step(col_vals):
    """step = moyenne post(+4..+10) - moyenne pre(-10..-1), sur les fenetres valides."""
    prof = np.full((len(onsets), 2*W+1), np.nan)
    flat = idxm[valid]; prof[valid] = col_vals[flat]
    return np.nanmean(np.nanmean(prof[:, post], axis=1) - np.nanmean(prof[:, pre], axis=1))

rows = []
for j, c in enumerate(CAN):
    s_val = onset_step(np.nan_to_num(Z[:, j], nan=np.nan))     # changement de VALEUR (z)
    s_avl = onset_step(avail[:, j])                            # changement de DISPONIBILITE
    rows.append((c, s_val, s_avl))
F = pd.DataFrame(rows, columns=["signal", "step_valeur", "step_dispo"]).fillna(0)
F["abs_val"] = F["step_valeur"].abs()
print("=== B3 : empreinte de l'attaque (onset, 51 episodes) ===")
print("\n-- top DISPONIBILITE (silence/apparition de signal) --")
for _, r in F.reindex(F["step_dispo"].abs().sort_values(ascending=False).index).head(6).iterrows():
    print(f"  {r['step_dispo']:+.2f}  {r['signal']}")
print("\n-- top VALEUR (le signal change brutalement a +4s) --")
for _, r in F.sort_values("abs_val", ascending=False).head(8).iterrows():
    print(f"  z {r['step_valeur']:+.2f}  {r['signal']}")

# figure : empreinte (barres top dispo + top valeur)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 5))
td = F.reindex(F["step_dispo"].abs().sort_values(ascending=False).index).head(6)[::-1]
a1.barh(range(len(td)), td["step_dispo"], color="#c0392b")
a1.set_yticks(range(len(td))); a1.set_yticklabels([s.replace("mean.", "").replace("Engine.Speed", "EngSpeed")[:34] for s in td["signal"]], fontsize=8)
a1.axvline(0, color="k", lw=.8); a1.set_xlabel("step de DISPONIBILITE a l'onset")
a1.set_title("Signature 1 : disponibilite (silence de bus)")
tv = F.sort_values("abs_val", ascending=False).head(8)[::-1]
a2.barh(range(len(tv)), tv["step_valeur"], color="#2980b9")
a2.set_yticks(range(len(tv))); a2.set_yticklabels([s.replace("mean.", "").replace("Aftertreatment.1.", "")[:34] for s in tv["signal"]], fontsize=8)
a2.axvline(0, color="k", lw=.8); a2.set_xlabel("step de VALEUR (z-score) a l'onset")
a2.set_title("Signature 2 : valeurs qui changent a +4s")
plt.tight_layout(); plt.savefig(f"{ASSETS}/v2_attack_fingerprint.png", dpi=120); plt.close()

# ---- B4 : empreinte memoire + latence d'inference ----
tr, te = driver_holdout(df, n_test=12, seed=0)
champ = HistGradientBoostingClassifier(class_weight="balanced", random_state=0).fit(X[tr].astype(np.float32), y[tr])
size_kb = len(pickle.dumps(champ)) / 1024
one = X[te][:1].astype(np.float32)
for _ in range(50): champ.predict_proba(one)        # warmup
t0 = time.time(); N = 2000
for _ in range(N): champ.predict_proba(one)
lat_ms = (time.time() - t0) / N * 1000
batch = X[te][:10000].astype(np.float32); t0 = time.time(); champ.predict_proba(batch)
thr_per_s = 10000 / (time.time() - t0)
print(f"\n=== B4 : faisabilite ===")
print(f"  taille du modele serialise = {size_kb:.0f} Ko")
print(f"  latence inference 1 fenetre = {lat_ms:.2f} ms | debit lot = {thr_per_s:,.0f} fenetres/s")
print(f"  -> compatible temps reel a l'echelle 1 s ; MAIS l'agregation 1 s perd la signature sous-seconde.")

json.dump({"fingerprint_dispo": F.reindex(F["step_dispo"].abs().sort_values(ascending=False).index).head(8)[["signal", "step_dispo"]].values.tolist(),
           "fingerprint_valeur": F.sort_values("abs_val", ascending=False).head(10)[["signal", "step_valeur"]].values.tolist(),
           "model_size_kb": size_kb, "latency_ms_per_window": lat_ms, "throughput_windows_per_s": thr_per_s,
           "n_onsets": len(onsets)},
          open(f"{EVAL}/results_characterization.json", "w"), indent=2)
print("\n[OK] -> docs/03_evaluation/results_characterization.json | docs/assets/v2_attack_fingerprint.png")
