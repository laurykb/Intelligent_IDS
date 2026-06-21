# Environnement de calcul & reproductibilité cross-plateforme

> Note de **provenance** : le projet a été développé sur deux machines successives. On
> documente ici *quel résultat a été calculé où*, et on **prouve** que le changement de
> machine n'a pas altéré les conclusions. Section réutilisable telle quelle dans le rapport.

## 1. Les deux machines

| | Machine A — origine | Machine B — actuelle |
|---|---|---|
| OS | macOS | Windows 11 |
| Calcul | CPU | **GPU** NVIDIA RTX 2060 SUPER 8 Go (CUDA 13.2), 16 cœurs, 34 Go RAM |
| Python | 3.11 | 3.11.9 (venv `.venv/`) |
| numpy / pandas / scikit-learn / scipy / matplotlib / pyarrow | **versions figées** | **mêmes versions figées** (`requirements.lock.txt`) |
| torch | **2.12.1 (CPU)** | **2.6.0+cu124 (CUDA)** — `requirements-gpu.lock.txt` |

Le stack scientifique sklearn est **identique** ; seul **torch** diffère (version + backend),
et uniquement pour la partie *deep*.

## 2. Provenance des résultats

| Résultats | Calculés sur | Statut |
|---|---|---|
| P0–P5+ : EDA, prétraitement, supervisé (champion 0,756), anomalie, deep mono-seed, évaluation (PR-AUC 0,735 / LODO / seuils), analyse par groupe | **Machine A (Mac)** | canoniques, inchangés |
| Vague 1 items 1/3/4/6/7 : ROC, latence/épisode, PDP, papier source, tests | **Machine A (Mac)** | canoniques |
| **Vague 1 item 2 — tuning** (0,757 → 0,798) | **Machine B (GPU)** | nouveau |
| **Vague 1 item 5 — multi-seed** (MLP 0,543 / GRU 0,571) | **Machine B (GPU)** | nouveau |
| Vérification cross-plateforme `03a` | **Machine B (GPU)** | contrôle (archivé §3, fichiers canoniques = Mac) |

## 3. Preuve de reproductibilité cross-plateforme

On a **recalculé sur la Machine B** le comparatif supervisé complet (`notebooks/03a_supervised.ipynb`,
mêmes versions figées) et confronté aux valeurs canoniques du Mac :

| Modèle (PR-AUC, GroupKFold conducteur) | Mac | Windows | \|écart\| |
|---|---|---|---|
| **Gradient Boosting — CHAMPION** | 0,7556 | 0,7556 | **0,0000** |
| Ablation CAN | 0,7556 | 0,7556 | **0,0000** |
| Ablation CAN+BIO | 0,7492 | 0,7492 | **0,0000** |
| Ablation BIO seul | 0,0139 | 0,0139 | **0,0000** |
| Ablation GPS (confondeur) | 0,8349 | 0,8349 | **0,0000** |
| RandomForest | 0,7089 | 0,7080 | 0,0009 |
| LogReg | 0,4067 | 0,4076 | 0,0009 |
| SVM-linéaire | 0,3896 | 0,4014 | 0,0118 |

**Écart absolu maximal = 0,012**, et il porte sur le **SVM linéaire** — un modèle faible,
non retenu, dont l'écart reste très inférieur à l'écart-type inter-fold (±0,12). Le **champion
et tous les chiffres porteurs de conclusion** (ablations : GPS confondeur, biométrie inutile)
sont **bit-identiques** : `HistGradientBoosting` est déterministe à `random_state` fixé, et le
stack numpy/sklearn figé donne le même résultat sur les deux OS.

Contrôle complémentaire : le **baseline du champion recalculé pour le tuning** (machine B) =
**0,757 ± 0,086**, contre **0,756 ± 0,088** sur le Mac → même valeur.

## 4. Non-déterminisme GPU (partie deep) — assumé

Les résultats *deep* sont les seuls calculés dans un environnement torch différent. Sur GPU,
les opérations CUDA (cuDNN, sommes atomiques du GRU) **ne sont pas déterministes au bit près** ;
on **ne revendique donc pas** un chiffre deep bit-exact. La parade est **méthodologique** : le
multi-seed (item 5) rapporte une **moyenne ± écart-type sur 5 graines**, ce qui absorbe ce
non-déterminisme et est plus défendable qu'un run unique. Les valeurs mono-graine du Mac (MLP
0,532 / GRU 0,566) **tombent dans les intervalles multi-graines** mesurés sur GPU (0,543 ± 0,016 /
0,571 ± 0,024) → la conclusion (deep < arbres ; pas d'avantage GRU robuste) est **stable** malgré
le changement de version torch et de backend.

## 5. Conclusion

Le changement de machine **n'a pas dégradé la rigueur** ; il l'a même **renforcée** :
- le cœur sklearn du projet est **reproduit à l'identique** (champion : écart 0,0000) ;
- la partie deep est désormais **multi-graine avec intervalles de confiance** (faisable grâce au
  GPU), au lieu d'un run unique fragile ;
- le tuning a pu être mené **sans OOM** (il avait planté sur le Mac).

Les fichiers de résultats **canoniques restent ceux du Mac** (cités dans les writeups) ; les
chiffres de la Machine B servent de **contrôle** (ci-dessus) et pour les deux nouveaux items.
