# Reprendre les 2 runs lourds de la Vague 1 sur une autre machine

> État au 2026-06-19 : la Vague 1 est faite à **5/7**. Restent **2 runs de calcul** à
> produire (ils ont été mis en pause pour être lancés sur un PC plus rapide) :
> - **Item 2 — optimisation d'hyperparamètres** : `notebooks/06b_tuning.py`
>   (le run précédent avait **planté** par manque de mémoire ; le script est maintenant
>   durci : `early_stopping`, `N_JOBS` modéré, float32).
> - **Item 5 — multi-seed deep (MLP/GRU)** : `notebooks/06e_multiseed.py`.

## 1. Ce qu'il faut copier sur l'autre PC

Tout le dossier projet **`IDS_ORNL/`**, en incluant **au moins** un des deux dans `data/` :
- `data/cache.parquet` (~360 Mo) — **recommandé** (chargement instantané) ; OU
- `data/DriverID_Full_Data_Downsampled.csv` (~852 Mo) — le loader reconstruit le cache
  tout seul au 1er lancement (~100 s).

Pas besoin des autres gros fichiers (PDF, survey) pour ces 2 runs.

## 2. Dépendances

```
pip install -r requirements.lock.txt
```
(numpy, pandas, scikit-learn, scipy, matplotlib, pyarrow ; **torch** seulement pour l'item 5.)
Versions figées dans `requirements.lock.txt` pour reproductibilité.

## 3. Lancer

```bash
# Item 2 — tuning (PR-AUC, GroupKFold conducteur). torch NON requis.
python notebooks/06b_tuning.py
#   moins de RAM :        N_JOBS=2 N_ITER=15 python notebooks/06b_tuning.py
#   machine costaude :    N_JOBS=6 N_ITER=40 python notebooks/06b_tuning.py

# Item 5 — multi-seed MLP + GRU (5 seeds). torch requis.
python notebooks/06e_multiseed.py
```

### Durée à prévoir (réaliste)

Le smoke-test ici a mesuré **~150 s par fit** (1 candidat = 4 fits ≈ 10 min) sur ce Mac.
Donc le coût total du tuning ≈ **N_ITER × 4 × (temps d'un fit)** :
- sur ce Mac : N_ITER=25 ≈ **~4 h** (trop) -> c'est pour ça qu'on l'envoie ailleurs ;
- sur une machine 3-4× plus rapide : N_ITER=20-25 ≈ **30-60 min**.

Choisis **N_ITER** selon la vitesse de ton fit : lance d'abord avec `N_ITER=3` pour
chronométrer, puis ajuste. Le multi-seed (item 5) est plus court (~10-15 min CPU).

> **Résultat préliminaire déjà obtenu ici** (2 candidats aléatoires) : PR-AUC **0,786**
> vs défaut **0,757**, soit **+0,028**. Donc le tuning aide un peu — à confirmer sur le
> run complet.

## 4. Ce qu'il faut me ramener

Juste ces deux fichiers JSON (légers), à recopier dans `docs/03_evaluation/` :
- `results_tuning.json`
- `results_multiseed.json`

Je m'en sers ici pour **finaliser la synthèse de la Vague 1** (tableau récap + writeup +
mise à jour du journal/HANDOFF).

## Note honnête sur le tuning

Sur un Gradient Boosting déjà solide (défaut PR-AUC 0,756), le gain attendu du tuning est
**faible** (souvent < 0,02, parfois nul). On le fait surtout parce que **le sujet le
demande explicitement** ; le résultat sera rapporté tel quel, gain ou pas.
