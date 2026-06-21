# Vague 1 - Crédibilité (conformité au sujet + métrologie IDS)

> Première vague d'auto-amélioration (cf. [autocritique.md](../04_conclusion/autocritique.md)).
> Objectif : combler les **demandes littérales du sujet** (ROC, hyperparamètres) et les
> **métriques IDS manquantes**, à effort faible. État au 2026-06-19 : **7/7 faits** — les
> 2 runs de calcul lourds (items 2 et 5) ont été bouclés sur un PC à GPU (RTX 2060 SUPER).

| # | Item | Statut | Résultat |
|---|---|---|---|
| 1 | Courbe ROC + AUC-ROC | [fait] | AUC-ROC **0,977** (PR-AUC 0,735) |
| 2 | Optimisation d'hyperparamètres | [fait] | **0,757 → 0,798** (Δ **+0,040**, 40 candidats) |
| 3 | Latence + métriques par épisode | [fait] | **86 % d'épisodes détectés, ~4 s** |
| 4 | Explicabilité (PDP, substitut SHAP) | [fait] | sens des effets par signal |
| 5 | Multi-seed + IC (MLP/GRU) | [fait] | MLP **0,543±0,016** vs GRU **0,571±0,024** (écart **non significatif**) |
| 6 | Papier source ORNL + positionnement | [fait] | validation du gradient d'awareness |
| 7 | Audit exclusion GPS + tests + versions | [fait] | 14 tests OK, lock de versions |

## Item 1 — Courbe ROC vs PR (le sujet demande la ROC)

Prédictions hors-fold (GroupKFold conducteur). **AUC-ROC = 0,977** alors que **PR-AUC =
0,735**. Le contraste est pédagogique : la classe négative (98,5 %) **écrase les faux
positifs**, donc la ROC paraît excellente. Pour une attaque **rare**, la **PR-AUC reste la
métrique honnête** ; on fournit la ROC (demande du sujet) mais on ne s'appuie pas dessus.
Figure : `docs/assets/v1_roc_vs_pr.png`.

## Item 2 — Optimisation d'hyperparamètres (demande du sujet)

`RandomizedSearchCV` (40 candidats), **même GroupKFold conducteur** que partout (anti-fuite),
scoring = PR-AUC. Comparé au champion **par défaut** (PR-AUC 0,757 ± 0,086).

| | PR-AUC (GroupKFold conducteur) |
|---|---|
| HistGB défaut | 0,757 ± 0,086 |
| **HistGB optimisé** | **0,798** |
| **Gain** | **+0,040** |

Meilleurs hyperparamètres : `learning_rate=0,1`, `max_leaf_nodes=15` (arbres **peu profonds**),
`max_iter=400`, `min_samples_leaf=20`, `l2_regularization=10,0`, `max_depth=None`.

**Lecture honnête** : le gain est **réel mais modeste** (+0,040), et il reste **inférieur à
l'écart-type inter-fold** (±0,086) — donc *non significatif* au sens strict ; il améliore la
**moyenne CV** (ce que la recherche optimise), pas la garantie sur un conducteur inconnu. Il
confirme le préliminaire (+0,028 sur 2 candidats). C'est conforme à l'attente : sur un Gradient
Boosting déjà solide, le tuning aide à la marge. Le profil retenu (arbres peu profonds + forte
régularisation L2) va dans le sens d'un modèle qui **généralise** plutôt qu'il ne mémorise — utile
vu la variance inter-conducteur. Résultat → `docs/03_evaluation/results_tuning.json`.

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

## Item 5 — Multi-seed + intervalles de confiance (deep)

Le deep mono-seed de P4-C laissait croire à un avantage du GRU (0,566) sur le MLP (0,532). On
**rejoue 5 graines** (init des poids + ordre des batchs) sur les **mêmes folds** (GroupKFold
conducteur, déterministe). Calcul sur **GPU (RTX 2060 SUPER)**, ~16 min.

| Modèle | PR-AUC (moy. ± σ sur 5 seeds) |
|---|---|
| MLP | **0,543 ± 0,016** |
| GRU 16 s | **0,571 ± 0,024** |

Écart GRU − MLP = **+0,028**, écart-type combiné 0,029 → **différence NON significative** (dans
le bruit des graines). **Enseignement** : l'« avantage temporel » du GRU était un **artefact de
graine**, pas un effet robuste. Surtout, **les deux réseaux (0,54–0,57) restent loin du champion
arbres** (0,756 / 0,798 optimisé) — ce qui **confirme le verdict** : en tabulaire déséquilibré, les
arbres boostés dominent, le contexte temporel n'apporte pas de signal exploitable au-delà du bruit.
Résultat → `docs/03_evaluation/results_multiseed.json`.

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
  scikit-learn 1.2.2, scipy 1.11.4, matplotlib 3.8.0, pyarrow 14.0.2 ; torch spécifique-machine).
- **Reproductibilité cross-plateforme prouvée** (suite au changement de PC Mac→Windows+GPU) :
  le champion est **bit-identique** (0,7556 sur les deux machines), écart max 0,012 sur le seul
  SVM linéaire non retenu. Détail + provenance : [environnement_calcul.md](../04_conclusion/environnement_calcul.md).

## Bilan Vague 1 (7/7) et suite

**Vague 1 complète.** Les deux demandes littérales du sujet restantes (ROC + tuning) sont
couvertes, ainsi que les métriques IDS manquantes (latence/épisode), l'explicabilité, la
robustesse statistique du deep, le positionnement vs littérature et l'audit anti-fuite + tests.

Verdict consolidé : **champion = Gradient Boosting / CAN**, PR-AUC **0,757 → 0,798** (optimisé,
GroupKFold conducteur), bien au-dessus du deep (0,54–0,57, non discriminant entre MLP/GRU) et de
l'anomalie (~0,02). La limite clé reste **comportementale** (l'IDS détecte surtout la *réaction*
du conducteur, cf. [p5b_group_fragility.md](p5b_group_fragility.md)), à porter en Vague 2.

**Prochaine étape : LIVRABLES** — démo de détection (scorer une trace + alerter au seuil
haute-précision), rapport `.docx`, slides `.pptx` (réutiliser `build_report.py` / `build_slides.py`
de l'ancien projet). Matériel prêt : JSON `docs/03_evaluation/results_*.json`, figures
`docs/assets/*`, writeups `docs/02_experiences/`, conclusions `docs/04_conclusion/`.
