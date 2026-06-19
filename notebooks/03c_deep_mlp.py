"""
P4 - Chemin C (1/2) : deep tabulaire = MLP (dataset ORNL).

Question : un reseau de neurones bat-il les arbres boostes (chemin A, PR-AUC 0,756)
sur ce probleme TABULAIRE ? Memes garde-fous que les chemins A/B :
  - Features = 337 signaux CAN (GPS exclu = confondeur lieu).
  - Validation PAR CONDUCTEUR (GroupKFold 4 folds).
  - Metrique = PR-AUC (attaque rare 1,46 % ; hasard ~ 0,015).
  - Imputation mediane + standardisation AJUSTEES sur le train (anti-fuite).
  - Desequilibre gere par pos_weight dans la BCE (equivalent class_weight).

Lancer :  python notebooks/03c_deep_mlp.py
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
os.makedirs(EVAL, exist_ok=True)
SUP_CHAMPION = 0.756          # reference chemin A
EPOCHS, BATCH = 30, 1024

df = load(); y = df.cyberattack_active.values.astype(np.float32); groups = df.driver.values
CAN = feature_sets(df)["CAN"]
X = df[CAN].values.astype(np.float32)
print(f"base rate {y.mean():.4f} (hasard ~ {y.mean():.3f}) | {len(CAN)} features CAN | device {DEV}")
print(f"reference supervisee (chemin A) = {SUP_CHAMPION:.3f}\n")


class MLP(nn.Module):
    def __init__(self, d_in, dims=(256, 128, 64), p=0.3):
        super().__init__()
        layers, d = [], d_in
        for h in dims:
            layers += [nn.Linear(d, h), nn.BatchNorm1d(h), nn.ReLU(), nn.Dropout(p)]; d = h
        layers += [nn.Linear(d, 1)]
        self.net = nn.Sequential(*layers)
    def forward(self, x): return self.net(x).squeeze(1)


def fit_predict(Xtr, ytr, Xte):
    """Entraine un MLP (pos_weight pour le desequilibre), rend les scores du test."""
    net = MLP(Xtr.shape[1]).to(DEV)
    pos_w = torch.tensor([(ytr == 0).sum() / max(1, (ytr == 1).sum())], device=DEV)
    loss_fn = nn.BCEWithLogitsLoss(pos_weight=pos_w)
    opt = torch.optim.Adam(net.parameters(), lr=1e-3, weight_decay=1e-5)
    Xtr_t = torch.from_numpy(Xtr).to(DEV); ytr_t = torch.from_numpy(ytr).to(DEV)
    n = len(Xtr_t)
    for ep in range(EPOCHS):
        net.train(); perm = torch.randperm(n, device=DEV)
        for i in range(0, n, BATCH):
            idx = perm[i:i + BATCH]
            opt.zero_grad()
            loss_fn(net(Xtr_t[idx]), ytr_t[idx]).backward(); opt.step()
    net.eval()
    with torch.no_grad():
        Xte_t = torch.from_numpy(Xte).to(DEV)
        s = torch.sigmoid(net(Xte_t)).cpu().numpy()
    return s


gkf = GroupKFold(n_splits=4)
aps = []
print("=== MLP : PR-AUC par fold (GroupKFold conducteur) ===")
for f, (tr, te) in enumerate(gkf.split(X, y, groups)):
    t0 = time.time()
    imp = SimpleImputer(strategy="median").fit(X[tr])
    sc = StandardScaler().fit(imp.transform(X[tr]))
    Xtr = sc.transform(imp.transform(X[tr])).astype(np.float32)
    Xte = sc.transform(imp.transform(X[te])).astype(np.float32)
    s = fit_predict(Xtr, y[tr], Xte)
    ap = average_precision_score(y[te], s); aps.append(ap)
    print(f"  fold {f}: PR-AUC = {ap:.3f}  ({time.time()-t0:.0f}s)")

aps = np.array(aps)
print(f"\n=== MLP : PR-AUC = {aps.mean():.3f} +/- {aps.std():.3f} (val. par conducteur) ===")
print(f"  reference supervisee (arbres boostes, chemin A) = {SUP_CHAMPION:.3f}")
verdict = "bat" if aps.mean() > SUP_CHAMPION else "ne bat PAS"
print(f"  -> le MLP {verdict} les arbres boostes.")

# --- sauvegarde + figure (cumulative avec le chemin A) --------------------------
out = {"MLP": [float(aps.mean()), float(aps.std())],
       "_ref_supervise_arbres": [SUP_CHAMPION, 0.0], "_hasard": [float(y.mean()), 0.0]}
json.dump(out, open(f"{EVAL}/results_deep.json", "w"), indent=2)

fig, ax = plt.subplots(figsize=(7.5, 4.8))
bars = ["GradBoosting\n(chemin A)", "MLP\n(chemin C)"]
vals = [SUP_CHAMPION, aps.mean()]; errs = [0.088, aps.std()]
ax.bar(bars, vals, yerr=errs, color=["#2980b9", "#e67e22"], capsize=4)
ax.axhline(y.mean(), ls="--", color="k", lw=1, label=f"hasard ({y.mean():.3f})")
ax.set_ylabel("PR-AUC (val. par conducteur)"); ax.set_ylim(0, 1)
ax.set_title("Chemin C : MLP vs arbres boostes (features CAN)")
for i, v in enumerate(vals): ax.text(i, v, f"{v:.3f}", ha="center", va="bottom")
ax.legend(); plt.tight_layout(); plt.savefig(f"{ASSETS}/p4c_deep_mlp.png", dpi=120); plt.close()
print("\n[OK] figure -> docs/assets/p4c_deep_mlp.png | resultats -> docs/03_evaluation/results_deep.json")
