"""
VAGUE 1 - Item 5 : Multi-seed + intervalles de confiance sur le deep (MLP, GRU).

On garde les MEMES folds (GroupKFold conducteur, deterministe) et on fait varier
seulement la graine PyTorch (init des poids + ordre des batchs) sur 5 seeds.
But : la difference MLP (0,532) vs GRU (0,566) est-elle significative ou du bruit ?

Lancer :  python notebooks/06e_multiseed.py
"""
import os, sys, json, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))
import numpy as np, pandas as pd
import torch, torch.nn as nn
from sklearn.model_selection import GroupKFold
from sklearn.impute import SimpleImputer
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import average_precision_score
from data import load
from features import feature_sets

torch.set_num_threads(max(1, os.cpu_count() // 2))
DEV = "cpu"
SEEDS = [0, 1, 2, 3, 4]
EPOCHS, BATCH = 30, 1024
L, GRU_EPOCHS, GBATCH, NEG_CAP = 16, 8, 512, 40000
EVAL = os.path.join(os.path.dirname(__file__), "..", "docs", "03_evaluation")

df = load(); y = df.cyberattack_active.values.astype(np.float32); groups = df.driver.values
CAN = feature_sets(df)["CAN"]; Xraw = df[CAN].values.astype(np.float32)
gkf = GroupKFold(n_splits=4)
FOLDS = list(gkf.split(Xraw, y, groups))
print(f"{len(CAN)} features CAN | folds fixes | seeds {SEEDS}\n")


class MLP(nn.Module):
    def __init__(self, d, dims=(256, 128, 64), p=0.3):
        super().__init__(); layers, q = [], d
        for h in dims: layers += [nn.Linear(q, h), nn.BatchNorm1d(h), nn.ReLU(), nn.Dropout(p)]; q = h
        layers += [nn.Linear(q, 1)]; self.net = nn.Sequential(*layers)
    def forward(self, x): return self.net(x).squeeze(1)


def train_mlp(Xtr, ytr, Xte):
    net = MLP(Xtr.shape[1]).to(DEV)
    pw = torch.tensor([(ytr == 0).sum() / max(1, (ytr == 1).sum())], device=DEV)
    lf = nn.BCEWithLogitsLoss(pos_weight=pw); opt = torch.optim.Adam(net.parameters(), 1e-3, weight_decay=1e-5)
    Xt = torch.from_numpy(Xtr).to(DEV); yt = torch.from_numpy(ytr).to(DEV); n = len(Xt)
    for _ in range(EPOCHS):
        net.train(); perm = torch.randperm(n, device=DEV)
        for i in range(0, n, BATCH):
            idx = perm[i:i + BATCH]; opt.zero_grad(); lf(net(Xt[idx]), yt[idx]).backward(); opt.step()
    net.eval()
    with torch.no_grad(): return torch.sigmoid(net(torch.from_numpy(Xte).to(DEV))).cpu().numpy()


order_by_driver = {}
tmp = pd.DataFrame({"g": groups, "t": df["interval_1s"].values, "i": np.arange(len(df))})
for g, sub in tmp.groupby("g"): order_by_driver[g] = sub.sort_values("t")["i"].values


def windows_for(drivers):
    W, lab = [], []
    for g in drivers:
        o = order_by_driver[g]
        for k in range(L - 1, len(o)): W.append(o[k - L + 1:k + 1]); lab.append(y[o[k]])
    return np.asarray(W, np.int64), np.asarray(lab, np.float32)


class GRUClf(nn.Module):
    def __init__(self, d, hid=64):
        super().__init__(); self.gru = nn.GRU(d, hid, batch_first=True)
        self.head = nn.Sequential(nn.Linear(hid, 32), nn.ReLU(), nn.Dropout(0.3), nn.Linear(32, 1))
    def forward(self, x): _, h = self.gru(x); return self.head(h[-1]).squeeze(1)


def train_gru(Xs, Wtr, ytr, Wte, rng):
    net = GRUClf(Xs.shape[1]).to(DEV)
    pw = torch.tensor([(ytr == 0).sum() / max(1, (ytr == 1).sum())], device=DEV)
    lf = nn.BCEWithLogitsLoss(pos_weight=pw); opt = torch.optim.Adam(net.parameters(), 1e-3, weight_decay=1e-5)
    Xs_t = torch.from_numpy(Xs); yt = torch.from_numpy(ytr).to(DEV); n = len(Wtr)
    for _ in range(GRU_EPOCHS):
        net.train(); perm = rng.permutation(n)
        for i in range(0, n, GBATCH):
            idx = perm[i:i + GBATCH]
            xb = Xs_t[torch.from_numpy(Wtr[idx])].to(DEV)
            opt.zero_grad(); lf(net(xb), yt[torch.from_numpy(idx).to(DEV)]).backward(); opt.step()
    net.eval(); s = np.empty(len(Wte), np.float32)
    with torch.no_grad():
        for i in range(0, len(Wte), 2048):
            s[i:i + 2048] = torch.sigmoid(net(Xs_t[torch.from_numpy(Wte[i:i + 2048])].to(DEV))).cpu().numpy()
    return s


def run(model):
    per_seed = []
    for seed in SEEDS:
        torch.manual_seed(seed); np.random.seed(seed); rng = np.random.RandomState(seed)
        aps = []
        for tr, te in FOLDS:
            imp = SimpleImputer(strategy="median").fit(Xraw[tr]); sc = StandardScaler().fit(imp.transform(Xraw[tr]))
            if model == "MLP":
                Xtr = sc.transform(imp.transform(Xraw[tr])).astype(np.float32)
                Xte = sc.transform(imp.transform(Xraw[te])).astype(np.float32)
                s = train_mlp(Xtr, y[tr], Xte); yte = y[te]
            else:
                Xs = sc.transform(imp.transform(Xraw)).astype(np.float32)
                trd = np.unique(groups[tr]); ted = np.unique(groups[te])
                Wtr, ytr = windows_for(trd); Wte, yte = windows_for(ted)
                pos = np.where(ytr == 1)[0]; neg = np.where(ytr == 0)[0]
                if len(neg) > NEG_CAP: neg = rng.choice(neg, NEG_CAP, replace=False)
                keep = np.concatenate([pos, neg]); rng.shuffle(keep); Wtr, ytr = Wtr[keep], ytr[keep]
                s = train_gru(Xs, Wtr, ytr, Wte, rng)
            aps.append(average_precision_score(yte, s))
        per_seed.append(float(np.mean(aps)))
        print(f"  {model} seed {seed}: PR-AUC moyen (4 folds) = {per_seed[-1]:.3f}")
    arr = np.array(per_seed)
    print(f"  -> {model} : {arr.mean():.3f} +/- {arr.std():.3f} (sur {len(SEEDS)} seeds)\n")
    return arr


print("=== MLP (multi-seed) ==="); t0 = time.time(); mlp = run("MLP")
print("=== GRU (multi-seed) ==="); gru = run("GRU")
print(f"(total {time.time()-t0:.0f}s)")

# Significativite : l'intervalle MLP recouvre-t-il GRU ?
gap = gru.mean() - mlp.mean(); pooled = np.sqrt(mlp.std()**2 + gru.std()**2)
verdict = "NON significatif (dans le bruit)" if abs(gap) < 2 * pooled else "significatif"
print(f"\nGRU - MLP = {gap:+.3f} ; ecart-type combine {pooled:.3f} -> difference {verdict}")

json.dump({"MLP_seeds": mlp.tolist(), "GRU_seeds": gru.tolist(),
           "MLP_mean_std": [float(mlp.mean()), float(mlp.std())],
           "GRU_mean_std": [float(gru.mean()), float(gru.std())],
           "gap_gru_minus_mlp": float(gap), "significatif": verdict},
          open(f"{EVAL}/results_multiseed.json", "w"), indent=2)
print("[OK] resultats -> docs/03_evaluation/results_multiseed.json")
