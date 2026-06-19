# Vague 1 - Crédibilité (conformité au sujet + métrologie IDS)

> Première vague d'auto-amélioration (cf. [autocritique.md](../04_conclusion/autocritique.md)).
> Objectif : combler les **demandes littérales du sujet** (ROC, hyperparamètres) et les
> **métriques IDS manquantes**, à effort faible. État au 2026-06-19 : **5/7 faits**,
> **2 runs de calcul à finir sur une autre machine** (cf. [REPRISE_AUTRE_PC.md](../../REPRISE_AUTRE_PC.md)).

| # | Item | Statut | Résultat |
|---|---|---|---|
| 1 | Courbe ROC + AUC-ROC | ✅ | AUC-ROC **0,977** (PR-AUC 0,735) |
| 2 | Optimisation d'hyperparamètres | ⏳ autre PC | préliminaire **+0,028** (2 candidats) |
| 3 | Latence + métriques par épisode | ✅ | **86 % d'épisodes détectés, ~4 s** |
| 4 | Explicabilité (PDP, substitut SHAP) | ✅ | sens des effets par signal |
| 5 | Multi-seed + IC (MLP/GRU) | ⏳ autre PC | — |
| 6 | Papier source ORNL + positionnement | ✅ | validation du gradient d'awareness |
| 7 | Audit exclusion GPS + tests + versions | ✅ | 14 tests OK, lock de versions |

## Item 1 — Courbe ROC vs PR (le sujet demande la ROC)

Prédictions hors-fold (GroupKFold conducteur). **AUC-ROC = 0,977** alors que **PR-AUC =
0,735**. Le contraste est pédagogique : la classe négative (98,5 %) **écrase les faux
positifs**, donc la ROC paraît excellente. Pour une attaque **rare**, la **PR-AUC reste la
métrique honnête** ; on fournit la ROC (demande du sujet) mais on ne s'appuie pas dessus.
Figure : `docs/assets/v1_roc_vs_pr.png`.

## Item 3 — Latence de détection + métriques PAR ÉPISODE (la vraie métrique IDS)

On reconstruit les **51 épisodes** d'attaque (runs contigus, par conducteur ; durée
médiane 42 s) et on mesure la détection au niveau épisode, pas fenêtre :

| Seuil | Épisodes détectés | Latence médiane | Latence max | Fausses alertes (fenêtres normales) |
|---|---|---|---|---|
| F1-max (0,855) | **86 %** (44/51) | **4 s** | 16 s | 0,24 % |
| Haute-précision (0,977) | 76 % (39/51) | 4 s | 46 s | 0,10 % |

**Lecture** : bien meilleur que ne le suggère le score par-fenêtre. Le détecteur **lève
l'alerte ~4 s après le début** de l'attaque, avec très peu de fausses alertes. Les ~24 %
d'épisodes ratés correspondent aux conducteurs **non avertis** (Groupe 1) qui ne réagissent
pas — cohérent avec P5+. Figure : `docs/assets/v1_latency_episode.png`.

## Item 4 — Explicabilité directionnelle (dépendances partielles)

> SHAP **indisponible** dans l'environnement (offline) -> on utilise les **dépendances
> partielles** (sklearn), qui donnent le **sens** de chaque effet (la permutation
> importance de P5 ne donnait que l'amplitude). Échelle log-odds (classe rare).

| Signal | Sens (P(attaque)) | Amplitude (log-odds) |
|---|---|---|
| 3242 DPF Intake Temperature | **monte** | 0,27 |
| 245 Total Vehicle Distance | descend | 0,23 |
| 185 Engine Average Fuel Economy | descend | 0,10 |
| 4360 SCR Intake Temperature | descend | 0,07 |
| 1761 DEF Tank Volume | descend | 0,06 |
| 190 Engine Speed (CAN0) | descend | **0,01** |

**Enseignement honnête** : l'effet marginal le plus net est la **température DPF qui monte**
(confondeur thermique lent, l'attaque survient à ~60 % du trajet). Le **régime moteur 190**,
pourtant n°1 en importance par permutation, a un effet **marginal quasi nul (0,01)** : il agit
**par interactions**, pas par dépendance simple. Cela conforte que le modèle s'appuie sur du
**contexte/comportement**, pas sur une signature d'injection. Figure : `docs/assets/v1_partial_dependence.png`.

## Item 6 — Papier source ORNL et positionnement

Le dataset a une publication associée : **Lanigan, Biggs, Gallegos, Daily, Reid, Powers,
« Impact of Cyber Threat Awareness on Driver Response to an Unexpected Vehicle Cyberattack »,
Journal of Transportation Security, 2025** (cf. [references.md](../01_projet/references.md)).
Elle **valide directement** notre P5+ :

- Groupes = **Control / Aware / Aware+Protocol** (= nos G1/G2/G3) ; **temps de réaction
  30,3 / 16,1 / 7,5 s** -> même gradient monotone que notre détectabilité (0,74/0,92/0,96).
- **Aware+Protocol : 100 % d'arrêt** ; **Control : continue à rouler / ne remarque parfois
  pas l'attaque** -> explique notre détection 0,90 vs 0,46.
- **« instrument cluster cyberattack »** (l'afficheur) + **même lieu** pour tous ->
  confirme nos deux points : injection absente des diffusions ECU loggées, et confondeur de
  lieu. Notre cadrage **détection** semble **inédit** sur ce dataset (pas de SOTA à comparer).

## Item 7 — Audit exclusion GPS + tests unitaires + versions

- **14 tests** (`tests/test_data.py`, `tests/test_features.py`) passent : ils **codifient
  les invariants anti-fuite** (aucune colonne GPS/survey dans le set CAN ; split conducteur
  disjoint et déterministe ; cible/confondeurs exclus des features ; attaque rare ~1,5 %).
- Petite incohérence corrigée au passage : l'affichage de `02_preprocessing.py` disait
  `|corr|>0.5` alors que le seuil time-drift utilisé est **0,35**.
- **Versions figées** dans `requirements.lock.txt` (numpy 1.26.4, pandas 2.1.4,
  scikit-learn 1.2.2, scipy 1.11.4, matplotlib 3.8.0, pyarrow 14.0.2, torch 2.12.1).

## Reste à finir (sur une autre machine)

- **Item 2 (tuning)** : `python notebooks/06b_tuning.py` -> `results_tuning.json`.
  Préliminaire encourageant : **+0,028** (2 candidats) vs défaut 0,757.
- **Item 5 (multi-seed)** : `python notebooks/06e_multiseed.py` -> `results_multiseed.json`.

Instructions complètes : [REPRISE_AUTRE_PC.md](../../REPRISE_AUTRE_PC.md). Une fois les 2 JSON
ramenés, finaliser ce tableau et le journal.
