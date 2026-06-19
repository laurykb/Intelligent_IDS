# Auto-critique & plan d'auto-amélioration (dataset ORNL Driver ID)

> Revue critique honnête à l'issue de P0->P5+. Objectif : nommer les failles réelles,
> ce qu'on n'a pas exploré, la littérature à mobiliser, et un plan priorisé. Même
> démarche que pour le dataset précédent, transposée au dataset **final** correspondant
> au sujet (ELD / Kenworth T270).

## Cadrage : ce que le sujet demande explicitement

Le sujet (R. Khatoun) liste des étapes précises. On les confronte à ce qu'on a fait :

| Étape du sujet | Statut | Où |
|---|---|---|
| Explorer le dataset (normal vs suspect) | **fait** | P1 EDA |
| Prétraiter (bruit, normalisation) | **fait** | P2/P3 |
| Comparer arbres / SVM / réseaux de neurones | **fait** | LogReg, SVM-lin, RF, GradBoosting, MLP, GRU |
| Diviser train / test | **fait (et durci)** | split **par conducteur** (anti-fuite) |
| Entraîner sur normal + malveillant | **fait** | chemin A |
| Évaluer : précision, rappel, **courbe ROC** | **partiel** | precision/recall/PR-AUC oui, **ROC manquante** |
| **Optimiser les hyperparamètres** | **NON FAIT** | champion = HistGB par défaut |

-> Deux demandes **littérales** du sujet restent ouvertes : la **courbe ROC** et
l'**optimisation des hyperparamètres**. Ce sont les premières choses à combler (Vague 1).

## Ce qu'on a bien fait (pour situer la critique)

- **Discipline anti-confondeurs** : exclusion GPS (lieu), split **par conducteur**,
  métrique **PR-AUC** (attaque rare 1,46 %). On a chiffré chaque piège (random 0,985 vs
  conducteur 0,632 ; GPS spurieux 0,835). Rare et sain.
- **Résultats négatifs assumés** : anomalie non supervisée **au hasard** (~0,02), deep
  **ne bat pas** les arbres (MLP 0,532 / GRU 0,566 vs 0,756), biométrie seule inutile
  (0,014). On ne survend rien.
- **Découverte P5+** : l'IDS détecte en grande partie la **réaction du conducteur**
  (gradient d'awareness G1<G2<G3) et non l'injection pure. Honnêteté de niveau recherche.

Mais il reste beaucoup de trous.

## A. Les failles réelles

### A1. Validité de la cible — « on détecte la réaction, pas l'injection » (la plus grave)
> **Statut :** diagnostiqué en [P5+](../02_experiences/p5b_group_fragility.md), **non résolu** -> *Vague 2*.

- Le label `cyberattack_active` marque la **fenêtre** d'attaque. Or P5+ montre que le
  signal détectable est largement la **réponse comportementale** (Groupe 3 prévenu+se
  garer -> le régime moteur chute, d=-0,48 ; détection 0,90/transfert 0,93), pas
  l'injection CAN. Sur le conducteur **non averti** (Groupe 1), détection **0,46 même
  entraîné sur G1** = la vraie détectabilité de l'injection pure.
- **Confirmé par la vérification dataset** : le spoof (tach/compteur -> 0) est
  **quasi absent** des features agrégées à la seconde (`mean.190.Engine.Speed` = 0 % de
  valeurs ~0 pendant l'attaque ; trace de 0,7 % sur le bus CAN0). Le logger a enregistré
  les **vraies diffusions ECU**, pas les messages malveillants injectés vers l'afficheur.
  L'injection n'est donc **structurellement pas dans nos données** -> le modèle ne *peut*
  détecter que la réaction + le contexte. Cf.
  [verification_dataset.md](verification_dataset.md).
- Conséquence honnête : on **valide une attaque à laquelle le conducteur a réagi**, pas
  un détecteur d'intrusion robuste. C'est l'équivalent ici de la « vérité terrain » du
  projet précédent. Piste (Vague 2) : récupérer la **donnée haute-résolution** (1/100 s)
  ou brute, où la signature d'injection sous-seconde pourrait survivre.

### A2. Évaluation incomplète pour un IDS (et vs le sujet)
> **Statut :** **à faire** -> *Vague 1*.

- **Courbe ROC absente** : le sujet la demande ; on n'a que PR (justifié par la rareté,
  mais ROC + AUC-ROC à ajouter, en expliquant pourquoi PR-AUC reste la métrique primaire).
- **Latence de détection** non mesurée : combien de secondes après le début de l'attaque
  déclenche-t-on ? C'est *la* métrique d'un IDS ; on n'a que du par-fenêtre.
- **Évaluation par épisode** absente : on score des fenêtres de 1 s, mais un IDS doit
  détecter l'**épisode**. A-t-on détecté les **50 épisodes** d'attaque, et en combien de
  secondes ? (Très favorable a priori, mais non mesuré.)
- **Hyperparamètres non optimisés** (cf. sujet) : le champion 0,756 est un HistGB **par
  défaut** -> ce n'est peut-être pas son plein potentiel.
- **Pas de variance multi-seed** sur le deep (MLP/GRU lancés une fois).

### A3. Robustesse / adversarial — à peine effleurée
> **Statut :** bruit gaussien fait ([P5+ §5](../02_experiences/p5b_group_fragility.md)), reste l'essentiel -> *Vague 2/3*.

- On a montré une dégradation **graduelle** sous bruit (0,632 -> 0,493 à 50 % de σ), bien,
  mais **zéro attaquant adaptatif**. Or A1 implique qu'un attaquant **furtif** (qui ne
  déclenche pas la réaction du conducteur, p. ex. attaque brève ou subtile) **évaderait**
  un détecteur qui s'appuie sur la réaction.
- **Une seule attaque** (tachymètre->0) : risque d'overfit à cette instance ; pas de
  taxonomie (DoS/bus-off, fuzzing, replay, masquerade sans effet visible).

### A4. Modélisation — angles non explorés / sous-réglés
> **Statut :** permutation importance faite (P5) ; reste -> *Vague 1 (SHAP, tuning)* + *Vague 2 (clustering, hybride)*.

- **Optimisation d'hyperparamètres** absente (aussi A2).
- **SVM à noyau (RBF)** non testé (seulement linéaire) ; **clustering**
  (K-means/DBSCAN/GMM) **absent** ; **semi-supervisé** et **IDS hybride** (supervisé pour
  le connu + anomalie pour l'inconnu) non construits.
- **Explicabilité** : permutation importance oui, **SHAP** non (utile pour la confiance
  et le rapport).

### A5. Biométrie & awareness — l'angle UNIQUE du dataset, sous-exploité
> **Statut :** testé naïvement (CAN+BIO 0,749, BIO seule 0,014), **pas creusé** -> *Vague 2*.

- On a conclu « biométrie inutile » **trop vite**. Or P5+ établit que le vrai signal est
  la **réaction** — et la biométrie (HR/EDA) **est** la réaction physiologique. On n'a pas
  tenté une **fusion conditionnée par groupe**, ni exploité la biométrie là où le CAN
  échoue (**Groupe 1, conducteur non averti**).
- C'est l'**originalité scientifique** de ce dataset (biométrie + niveaux d'awareness),
  qu'on a traitée en note de bas de page au lieu d'en faire un axe.

### A6. Reproductibilité / rigueur
> **Statut :** **à faire** -> *Vague 1*.

- Champion = **hyperparams par défaut** -> « champion » non garanti optimal.
- Deep **mono-seed**, pas d'intervalles de confiance.
- **Règle d'exclusion GPS heuristique** (par préfixe dans `classify_columns`) **non
  auditée** exhaustivement : un confondeur de lieu pourrait fuiter dans le set « CAN ».
- Pas de **tests unitaires** (loader/classification/features), pas de **lock de versions**.

## B. Littérature à mobiliser

### Le plus important : le papier derrière NOTRE dataset
- **ORNL Driver Identification / réponse du conducteur à une cyberattaque** (équipe ORNL,
  Kenworth T270, 3 groupes d'awareness). À lire **en priorité** : il décrit **l'attaque
  exacte** et la **réponse comportementale** -> valide directement notre A1/P5+ (gradient
  d'awareness) et sépare ce que notre cible mélange.

### IDS CAN — détecter l'injection indépendamment de la réaction (réponse à A1)
- **Cho & Shin, « Fingerprinting ECUs » (CIDS, USENIX Security 2016)** — *clock-skew* par
  ECU : identifierait l'**ELD usurpateur** indépendamment du payload et **du conducteur**.
- **Song et al. (ICOIN 2016)** — détection par fréquence / inter-arrivée des messages.

### IDS CAN — deep / anomalie
- **Taylor et al., LSTM (DSAA 2016)** ; **Hanselmann et al., CANet (IEEE Access 2020)**
  (auto-encodeur par signal) ; **Seo et al., GIDS (PST 2018)** ; **Marchetti & Stabili
  (IV 2017)** (séquences d'IDs).

### Datasets de référence (généralisation — A3)
- **ROAD (Verma et al., ORNL, 2022/2024)** — attaques **masquerade/furtives** : banc
  d'essai idéal pour l'attaquant adaptatif et la généralisation hors-dataset.
- **Car-Hacking (HCRL)** — benchmark DoS/fuzzy/spoofing.

### J1939 / poids lourds / ELD (notre protocole)
- **Murvay & Groza, « Security Shortcomings of SAE J1939 »** ; travaux **heavy-vehicle de
  l'équipe Daily (CSU)** ; avis **CISA** sur la compromission ELD.

### Facteur humain (spécifique à ce dataset)
- Littérature **stress/biométrie du conducteur sous incident** (pour A5) : relie la
  réponse HR/EDA à la détection.

## C. Plan d'auto-amélioration (priorisé)

### Vague 1 — Crédibilité (impact fort / effort faible) — d'abord combler le sujet
| Action | Répond à | Effort |
|---|---|---|
| **Courbe ROC + AUC-ROC** du champion (demandé par le sujet), en gardant PR-AUC primaire | A2 | faible |
| **Optimisation d'hyperparamètres** du Gradient Boosting (demandé par le sujet) | A2/A4 | faible |
| **Latence de détection** + **métriques par épisode** (50 attaques détectées ? en combien de s ?) | A2 | faible |
| **SHAP** sur le champion (au-delà de la permutation importance) | A4 | faible |
| **Multi-seed** + intervalles de confiance sur MLP/GRU | A6 | faible |
| **Lire le papier source ORNL** et **situer nos chiffres** | B/A1 | faible |
| **Audit de l'exclusion GPS** + **tests unitaires** (loader/features) + seed/versions | A6 | faible |

### Vague 2 — Profondeur méthodologique (impact fort / effort moyen)
| Action | Répond à | Effort |
|---|---|---|
| **Isoler la signature d'injection pure** : incohérence inter-bus `190` vs `190.CAN0`, onset précis | A1 | moyen |
| **Attaquant adaptatif / évasion** (furtif, sans réaction conducteur) | A3 | moyen |
| **Fusion biométrie conditionnée par awareness**, surtout sur le Groupe 1 | A5 | moyen |
| **Clustering + semi-supervisé + IDS hybride** (connu supervisé / inconnu anomalie) | A4 | moyen |
| **Taxonomie de menaces** + 1-2 injections synthétiques (DoS, fuzzing) | A3 | moyen |

### Vague 3 — Généralisation & « intelligence » (impact fort / effort élevé)
| Action | Répond à | Effort |
|---|---|---|
| **Tester sur ROAD / Car-Hacking** (généralisation hors-dataset) | A3 | élevé |
| **Attention / Transformer** sur séquences + **RAG** (CISA/J1939) pour **expliquer** chaque alerte | — | élevé |
| **Démo en mode déploiement** (sans labels) + agent d'analyse d'intrusion | A6 | élevé |
| **Comparer au SOTA** (CIDS, CANet, papier ORNL) | B | élevé |

## D. La leçon

Le pipeline est **propre et honnête**, et sa découverte centrale — **on détecte la
réaction du conducteur, pas l'injection CAN pure** — est à la fois son **originalité** et
sa **limite fondamentale**. Le détecteur valide « une attaque à laquelle le conducteur a
réagi », pas « une injection malveillante » en soi.

La **Vague 1** rend le projet *crédible* et **conforme au sujet** (ROC, hyperparamètres,
latence) ; la **Vague 2** le rend *robuste* (isoler l'injection, attaquant adaptatif,
exploiter biométrie+awareness) ; la **Vague 3** le rend *généralisable et intelligent*.
