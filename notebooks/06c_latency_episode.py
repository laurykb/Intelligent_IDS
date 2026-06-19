"""
VAGUE 1 - Item 3 : Latence de detection + metriques PAR EPISODE.

Un IDS ne detecte pas des fenetres isolees, il detecte des EPISODES. On reconstruit
les episodes d'attaque (runs contigus de cyberattack_active=1, par conducteur, ordre
temporel) et on mesure, a partir des scores HORS-FOLD :
  - combien d'episodes sont DETECTES (>=1 fenetre alertee) ;
  - la LATENCE = secondes entre le debut de l'episode et la 1re alerte ;
  - le cout : % de fenetres NORMALES alertees (fausses alertes).
A deux seuils : F1-max et haute-precision.

Lancer :  python notebooks/06c_latency_episode.py  (apres 06a_roc.py)
"""
import os, sys, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from sklearn.metrics import precision_recall_curve

ROOT = os.path.join(os.path.dirname(__file__), "..")
ASSETS, EVAL = f"{ROOT}/docs/assets", f"{ROOT}/docs/03_evaluation"
d = np.load(f"{EVAL}/oof_scores.npz", allow_pickle=True)
oof, y, driver, interval = d["oof"], d["y"].astype(int), d["driver"], d["interval"]

# seuils : F1-max et haute-precision (rappel ~0,5)
prec, rec, thr = precision_recall_curve(y, oof)
f1 = 2 * prec * rec / (prec + rec + 1e-12)
t_f1 = thr[np.nanargmax(f1[:-1])]
t_hp = thr[np.argmin(np.abs(rec[:-1] - 0.5))]
print(f"seuils : F1-max = {t_f1:.3f} | haute-precision (R~0,5) = {t_hp:.3f}\n")

# Reconstruction des episodes (runs contigus d'attaque, par conducteur ordonne)
df = pd.DataFrame({"y": y, "driver": driver, "interval": interval, "oof": oof})
episodes = []  # (driver, [positions dans l'ordre du conducteur])
for g, sub in df.groupby("driver"):
    sub = sub.sort_values("interval").reset_index(drop=True)
    ya = sub["y"].values; sc = sub["oof"].values
    i = 0
    while i < len(ya):
        if ya[i] == 1:
            j = i
            while j < len(ya) and ya[j] == 1:
                j += 1
            episodes.append({"driver": g, "scores": sc[i:j], "len": j - i})
            i = j
        else:
            i += 1
print(f"{len(episodes)} episodes d'attaque sur {df.driver.nunique()} conducteurs "
      f"(duree mediane {int(np.median([e['len'] for e in episodes]))} s)")


def episode_metrics(t):
    det, lat = 0, []
    for e in episodes:
        flagged = np.where(e["scores"] >= t)[0]
        if len(flagged):
            det += 1
            lat.append(int(flagged[0]))          # secondes apres le debut de l'episode
    rate = det / len(episodes)
    normal_alert = float((oof[y == 0] >= t).mean())
    return rate, np.array(lat), normal_alert


res = {}
for tag, t in [("F1-max", t_f1), ("haute-precision", t_hp)]:
    rate, lat, fa = episode_metrics(t)
    res[tag] = {"seuil": float(t), "detection_episode": rate,
                "latence_med": float(np.median(lat)) if len(lat) else None,
                "latence_moy": float(lat.mean()) if len(lat) else None,
                "latence_max": float(lat.max()) if len(lat) else None,
                "fenetres_normales_alertees": fa}
    print(f"\n[{tag}] seuil {t:.3f}")
    print(f"  episodes detectes : {rate*100:.0f}% ({int(rate*len(episodes))}/{len(episodes)})")
    if len(lat):
        print(f"  latence : mediane {np.median(lat):.0f}s | moyenne {lat.mean():.1f}s | max {lat.max():.0f}s")
    print(f"  fausses alertes : {fa*100:.2f}% des fenetres normales")

json.dump({"n_episodes": len(episodes), **res}, open(f"{EVAL}/results_episode.json", "w"), indent=2)

# Figure : detection par episode + histogramme de latence (au seuil haute-precision)
rate_hp, lat_hp, _ = episode_metrics(t_hp); rate_f1, lat_f1, _ = episode_metrics(t_f1)
fig, (a1, a2) = plt.subplots(1, 2, figsize=(12, 4.8))
a1.bar(["F1-max", "haute-precision"], [rate_f1 * 100, rate_hp * 100], color=["#2980b9", "#16a085"])
a1.set_ylabel("% d'episodes detectes"); a1.set_ylim(0, 100)
a1.set_title(f"Detection par episode (n={len(episodes)})")
for i, v in enumerate([rate_f1 * 100, rate_hp * 100]): a1.text(i, v, f"{v:.0f}%", ha="center", va="bottom")
a2.hist(lat_hp, bins=range(0, int(lat_hp.max()) + 3), color="#16a085", edgecolor="white")
a2.axvline(np.median(lat_hp), color="#c0392b", ls="--", label=f"mediane {np.median(lat_hp):.0f}s")
a2.set_xlabel("Latence de detection (s apres le debut de l'attaque)")
a2.set_ylabel("nb d'episodes"); a2.set_title("Latence (seuil haute-precision)"); a2.legend()
plt.tight_layout(); plt.savefig(f"{ASSETS}/v1_latency_episode.png", dpi=120); plt.close()
print("\n[OK] figure -> docs/assets/v1_latency_episode.png | resultats -> docs/03_evaluation/results_episode.json")
