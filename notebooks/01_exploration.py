"""
P1 - Exploration des donnees (EDA) - dataset ORNL Driver Identification.
Objectif : comprendre la structure (conducteurs, groupes, label), et surtout
mettre en evidence le piege central - les CONFONDEURS lieu/temps.

Lancer :  python notebooks/01_exploration.py
"""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
from data import load, classify_columns, usable

ASSETS = os.path.join(os.path.dirname(__file__), "..", "docs", "assets")
os.makedirs(ASSETS, exist_ok=True)
df = load(); g = classify_columns(df); y = df.cyberattack_active.values

print("=" * 70)
print(f"{len(df):,} fenetres de 1 s | {df.driver.nunique()} conducteurs | "
      f"3 groupes {dict(df.groupby('Group').driver.nunique())}")
print(f"Cible cyberattack_active : {100*y.mean():.2f}% d'attaque ({y.sum():,} fenetres)")
print(f"Features : {len(usable(df, g['can']))} CAN, {len(usable(df, g['bio']))} biometrie, "
      f"{len(usable(df, g['vbox']))} GPS/position (confondeurs)")
print("=" * 70)

# --- Confondeur LIEU : concentration geographique de l'attaque ----------------
lon, lat = "mean.longitude", "mean.latitude"
atk = df[y == 1]
print("\n--- Confondeur LIEU ---")
print(f"  ecart-type longitude : attaque={atk[lon].std():.4f} vs trajet={df[lon].std():.4f}")
print(f"  ecart-type latitude  : attaque={atk[lat].std():.4f} vs trajet={df[lat].std():.4f}")

# --- Confondeur TEMPS : position de l'attaque dans le trajet -------------------
fr = df.groupby("driver").apply(
    lambda d: d.reset_index(drop=True).index[d.reset_index(drop=True).cyberattack_active == 1].to_series().mean() / len(d)
    if (d.cyberattack_active == 1).any() else np.nan)
print(f"\n--- Confondeur TEMPS ---\n  attaque a {fr.median():.0%} du trajet (mediane), assez fixe")

# --- Pouvoir discriminant (Cohen's d) par type de feature ---------------------
def cohens_d(c):
    a, n = df.loc[y == 1, c], df.loc[y == 0, c]
    pooled = np.sqrt((a.var(skipna=True) + n.var(skipna=True)) / 2)
    return abs(a.mean() - n.mean()) / pooled if pooled else 0
rows = []
for typ, cols in [("GPS/position", usable(df, g["vbox"])), ("CAN", usable(df, g["can"])),
                  ("biometrie", usable(df, g["bio"]))]:
    for c in cols:
        rows.append((c, typ, cohens_d(c)))
rk = pd.DataFrame(rows, columns=["f", "type", "d"]).sort_values("d", ascending=False)
print("\n--- Top features par type (Cohen's d) ---")
for t in ["GPS/position", "CAN", "biometrie"]:
    best = rk[rk.type == t].iloc[0]
    print(f"  {t:14} meilleur d = {best.d:.2f}  ({best.f})")

# === FIGURE 1 : le confondeur lieu (scatter GPS colore par attaque) ===========
fig, ax = plt.subplots(figsize=(7, 5))
s = df.sample(20000, random_state=0)
ax.scatter(s[lon], s[lat], s=2, c="#bdc3c7", label="trajet (normal)", alpha=.5)
ax.scatter(atk[lon], atk[lat], s=6, c="#c0392b", label="attaque", alpha=.7)
ax.set_xlabel("longitude"); ax.set_ylabel("latitude")
ax.set_title("L'attaque a toujours lieu au MEME endroit\n(confondeur : un modele GPS detecterait le lieu, pas l'attaque)")
ax.legend()
plt.tight_layout(); plt.savefig(f"{ASSETS}/eda_confounder_gps.png", dpi=120); plt.close()

# === FIGURE 2 : Cohen's d top-15 colore par type =============================
top = rk.head(15)[::-1]
col = {"GPS/position": "#c0392b", "CAN": "#2980b9", "biometrie": "#16a085"}
fig, ax = plt.subplots(figsize=(9, 6))
ax.barh(range(len(top)), top.d, color=[col[t] for t in top.type])
ax.set_yticks(range(len(top))); ax.set_yticklabels([f[:34] for f in top.f], fontsize=8)
ax.set_xlabel("Cohen's d (separation attaque vs normal)")
ax.set_title("Les features les plus 'discriminantes' sont des CONFONDEURS (rouge = GPS/lieu)")
from matplotlib.patches import Patch
ax.legend(handles=[Patch(color=c, label=t) for t, c in col.items()], loc="lower right")
plt.tight_layout(); plt.savefig(f"{ASSETS}/eda_cohens_d.png", dpi=120); plt.close()

# === FIGURE 3 : reponse biometrique (HR) par groupe ==========================
fig, ax = plt.subplots(figsize=(7, 4.5))
groups = sorted(df.Group.unique()); w = 0.38; x = np.arange(len(groups))
hn = [df[(df.Group == gr) & (y == 0)]["mean.HR"].mean() for gr in groups]
ha = [df[(df.Group == gr) & (y == 1)]["mean.HR"].mean() for gr in groups]
ax.bar(x - w/2, hn, w, label="normal", color="#95a5a6")
ax.bar(x + w/2, ha, w, label="pendant l'attaque", color="#c0392b")
ax.set_xticks(x); ax.set_xticklabels([f"Groupe {gr}\n({'non averti' if gr==1 else 'averti' if gr==2 else 'averti + consigne'})" for gr in groups], fontsize=9)
ax.set_ylabel("rythme cardiaque moyen (bpm)"); ax.set_ylim(min(hn)-5, max(ha)+5); ax.legend()
ax.set_title("Reponse biometrique a l'attaque selon l'awareness du groupe")
plt.tight_layout(); plt.savefig(f"{ASSETS}/eda_biometric_hr.png", dpi=120); plt.close()

print("\n[OK] 3 figures -> docs/assets/ (eda_confounder_gps, eda_cohens_d, eda_biometric_hr)")
