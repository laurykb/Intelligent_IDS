"""
P4 - Chemin C (2/2) : deep temporel = GRU sur sequences (dataset ORNL).

Question : le CONTEXTE TEMPOREL aide-t-il ? Les arbres (chemin A) et le MLP
(chemin C/1) voient chaque seconde isolement. Un GRU voit une fenetre glissante de
L secondes consecutives (par conducteur) et peut capter la DYNAMIQUE de l'attaque.

Garde-fous identiques :
  - Features = 337 signaux CAN (GPS exclu). Sequences construites PAR CONDUCTEUR
    (ordre temporel interval_1s), jamais a cheval entre deux conducteurs.
  - Validation PAR CONDUCTEUR (GroupKFold 4 folds). Label = attaque a l'instant final.
  - Imputation mediane + standardisation AJUSTEES sur le train. PR-AUC.
  - Desequilibre : sous-echantillonnage des negatifs (cap) + pos_weight.

Caveat confondeur : un modele temporel pourrait apprendre la POSITION dans le trajet.
On l'a deja teste cote features (CAN_STABLE ~ CAN), mais on le garde a l'esprit.

Lancer :  python notebooks/03d_deep_gru.py
"""
import os, sys, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np, pandas as pd
import matplotlib; matplotlib.use("Agg"); import matplotlib.pyplot as plt
import torch, torch.nn as nn
from sklearn.model_selection import GroupKFold
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import average_precision_score
from data import load
from features import feature_sets

torch.manual_seed(0); np.random.seed(0)
torch.set_num_threads(max(1, os.cpu_count() // 2))
DEV = "cuda" if torch.cuda.is_available() else "cpu"

ROOT = os.path.join(os.path.dirname(__file__), "..")
ASSETS, EVAL = f"{ROOT}/docs/assets", f"{ROOT}/docs/03_evaluation"
SUP_CHAMPION, MLP_REF = 0.756, 0.532       # references chemins A et C/1
L, EPOCHS, BATCH = 16, 8, 512              # fenetre 16 s
NEG_CAP = 40000                            # plafond de negatifs a l'entrainement
rng = np.random.RandomState(0)

df = load(); y = df.cyberattack_active.values.astype(np.float32); groups = df.driver.values
CAN = feature_sets(df)["CAN"]
Xraw = df[CAN].values.astype(np.float32)
print(f"base rate {y.mean():.4f} | {len(CAN)} features CAN | device {DEV} | fenetre L={L}s")
print(f"refs : arbres={SUP_CHAMPION:.3f}  MLP={MLP_REF:.3f}\n")

# Ordre temporel par conducteur (indices globaux), calcule une fois.
order_by_driver = {}
tmp = pd.DataFrame({"g": groups, "t": df["interval_1s"].values, "i": np.arange(len(df))})
for g, sub in tmp.groupby("g"):
    order_by_driver[g] = sub.sort_values("t")["i"].values


def windows_for(drivers):
    """(W, labels) : W[n] = indices globaux des L secondes consecutives ; label = attaque finale."""
    W, lab = [], []
    for g in drivers:
        order = order_by_driver[g]
        for k in range(L - 1, len(order)):
            W.append(order[k - L + 1:k + 1]); lab.append(y[order[k]])
    return np.asarray(W, dtype=np.int64), np.asarray(lab, dtype=np.float32)


class GRUClf(nn.Module):
    def __init__(self, d_in, hid=64):
        super().__init__()
        self.gru = nn.GRU(d_in, hid, batch_first=True)
        self.head = nn.Sequential(nn.Linear(hid, 32), nn.ReLU(), nn.Dropout(0.3), nn.Linear(32, 1))
    def forward(self, x):
        _, h = self.gru(x)              # h : (1, B, hid) dernier etat
        return self.head(h[-1]).squeeze(1)


def run_fold(Xs, Wtr, ytr, Wte):
    net = GRUClf(Xs.shape[1]).to(DEV)
    pos_w = torch.tensor([(ytr == 0).sum() / max(1, (ytr == 1).sum())], device=DEV)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_w)
    opt = torch.optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-5)
    Xs_t = torch.from_numpy(Xs)                      # garde sur CPU, gather par batch
    ytr_t = torch.from_numpy(ytr).to(DEV)
    n = len(Wtr)
    for ep in range(EPOCHS):
        net.train(); perm = rng.permutation(n)
        for i in range(0, n, BATCH):
            idx = perm[i:i + BATCH]
            xb = Xs_t[torch.from_numpy(Wtr[idx])].to(DEV)   # (B, L, d)
            opt.zero_grad(); loss_fn(net(xb), ytr_t[torch.from_numpy(idx).to(DEV)]).backward(); opt.step()
    net.eval(); scores = np.empty(len(Wte), dtype=np.float32)
    with torch.no_grad():
        for i in range(0, len(Wte), 2048):
            xb = Xs_t[torch.from_numpy(Wte[i:i + 2048])].to(DEV)
            scores[i:i + 2048] = torch.sigmoid(net(xb)).cpu().numpy()
    return scores


gkf = GroupKFold(n_splits=4)
drivers_all = df["driver"].values
aps = []
print("=== GRU : PR-AUC par fold (GroupKFold conducteur) ===")
for f, (tr, te) in enumerate(gkf.split(Xraw, y, groups)):
    t0 = time.time()
    imp = SimpleImputer(strategy="median").fit(Xraw[tr])
    sc = StandardScaler().fit(imp.transform(Xraw[tr]))
    Xs = sc.transform(imp.transform(Xraw)).astype(np.float32)        # scale tout (fit train)
    tr_drivers = np.unique(drivers_all[tr]); te_drivers = np.unique(drivers_all[te])
    Wtr, ytr = windows_for(tr_drivers); Wte, yte = windows_for(te_drivers)
    # sous-echantillonnage des negatifs a l'entrainement (cap), tous les positifs gardes
    pos = np.where(ytr == 1)[0]; neg = np.where(ytr == 0)[0]
    if len(neg) > NEG_CAP:
        neg = rng.choice(neg, NEG_CAP, replace=False)
    keep = np.concatenate([pos, neg]); rng.shuffle(keep)
    Wtr, ytr = Wtr[keep], ytr[keep]
    s = run_fold(Xs, Wtr, ytr, Wte)
    ap = average_precision_score(yte, s); aps.append(ap)
    print(f"  fold {f}: PR-AUC = {ap:.3f}  (train {len(Wtr)} / test {len(Wte)} fenetres, {time.time()-t0:.0f}s)")

aps = np.array(aps)
print(f"\n=== GRU : PR-AUC = {aps.mean():.3f} +/- {aps.std():.3f} (val. par conducteur) ===")
print(f"  refs : arbres boostes {SUP_CHAMPION:.3f} | MLP {MLP_REF:.3f}")
verdict = "bat" if aps.mean() > SUP_CHAMPION else "ne bat PAS"
print(f"  -> le GRU {verdict} les arbres boostes.")

# --- sauvegarde (complete results_deep.json) + figure recap chemin C -------------
path = f"{EVAL}/results_deep.json"
out = json.load(open(path)) if os.path.exists(path) else {}
out["GRU"] = [float(aps.mean()), float(aps.std())]
out["_ref_supervise_arbres"] = [SUP_CHAMPION, 0.088]; out["_hasard"] = [float(y.mean()), 0.0]
json.dump(out, open(path, "w"), indent=2)

bars = ["GradBoosting\n(chemin A)", "MLP\n(chemin C)", "GRU 16s\n(chemin C)"]
vals = [SUP_CHAMPION, MLP_REF, aps.mean()]; errs = [0.088, 0.100, aps.std()]
fig, ax = plt.subplots(figsize=(8, 4.8))
ax.bar(bars, vals, yerr=errs, color=["#2980b9", "#e67e22", "#c0392b"], capsize=4)
ax.axhline(y.mean(), ls="--", color="k", lw=1, label=f"hasard ({y.mean():.3f})")
ax.set_ylabel("PR-AUC (val. par conducteur)"); ax.set_ylim(0, 1)
ax.set_title("Chemin C : deep (MLP, GRU) vs arbres boostes (CAN)")
for i, v in enumerate(vals): ax.text(i, v, f"{v:.3f}", ha="center", va="bottom")
ax.legend(); plt.tight_layout(); plt.savefig(f"{ASSETS}/p4c_deep.png", dpi=120); plt.close()
print("\n[OK] figure -> docs/assets/p4c_deep.png | resultats -> docs/03_evaluation/results_deep.json")
