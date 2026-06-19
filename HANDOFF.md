# HANDOFF - Reprise du projet dans une nouvelle session

> A lire EN PREMIER pour reprendre le projet. Resume auto-suffisant de l'etat au
> 2026-06-19. Details dates dans [journal.md](journal.md).

## 1. Identite du projet

- **Sujet** : IDS Intelligent (detecteur d'intrusion par machine learning) -
  consigne de R. Khatoun, projet integrateur 2026.
  > Dataset brut + doc officielle : `/Users/laury/Documents/ORNL Driver Identification Dataset`
  > (README + dictionnaire). Verifie le 2026-06-19, cf. docs/04_conclusion/verification_dataset.md.
- **Dataset** : ORNL Driver Identification Dataset (Kenworth T270, 50 conducteurs).
  CANbus J1939 (deja decode) + GPS/inertie + biometrie (HR/EDA/IBI), agrege a la
  seconde (mean/sd/min/max). 155 902 fenetres de 1 s, 816 colonnes.
- **Tache retenue** : detection de la cyberattaque -> cible `cyberattack_active`
  (1,46 %, rare). Axe secondaire : identification du conducteur (`Subject`).
- **Emplacement du projet** : `/Users/laury/Documents/IDS_ORNL`
  (data/, src/, notebooks/, docs/, deliverables/, tests/).

> Important : il existe un ANCIEN projet sur un autre dataset (log CAN brut
> "Wireless_Pedal_Jam") dans `/Users/laury/Downloads/doi_10_5061_dryad_zw3r228jk__v20250315`.
> Le sujet a change de dataset ; cet ancien projet est en grande partie OBSOLETE
> (analyse specifique), mais sa METHODO, sa theorie, et ses generateurs de
> livrables (`build_report.py`, `build_slides.py` en python-docx/python-pptx) sont
> REUTILISABLES/adaptables.

## 2. LE point central a ne jamais oublier (les confondeurs)

L'attaque survient TOUJOURS au meme **lieu** (apres North Overland Trail) et a un
**moment** fixe (~60 % du trajet). Donc :

- **Les features GPS / inertie sont des confondeurs** -> un modele qui les utilise
  detecte l'endroit, pas l'attaque (PR-AUC GPS = 0,835, spurieux). **On les EXCLUT.**
- **Le temps de roulage** est un confondeur (signaux a derive lente). Teste :
  l'exclure ne change rien (CAN_STABLE 0,630 vs CAN 0,632), donc le signal CAN est
  genuine.
- **Fuite par le conducteur** : un split aleatoire donne 0,985 (trompeur) vs 0,632
  par conducteur. -> **TOUJOURS splitter PAR CONDUCTEUR** (GroupKFold / driver_holdout).
- Attaque rare (1,46 %) -> **metrique = PR-AUC**, jamais l'accuracy.

## 3. Etat d'avancement

| Phase | Etat | Resultat cle |
|---|---|---|
| P0 Cadrage | fait | docs/01_projet/{contexte,problematique,plan}.md |
| P1 EDA | fait | confondeurs lieu/temps, 1,46 % attaque, biometrie faible |
| P2/P3 Pretraitement + split conducteur | fait | CAN honnete PR-AUC **0,632** (holdout) ; pieges chiffres |
| **P4-A Supervise** | **fait** | **GradBoosting PR-AUC 0,756 +/- 0,088** (GroupKFold conducteur) ; biometrie inutile (0,014) ; GPS 0,835 |
| **P4-B Anomalie** | **fait** | **echec assume : 4 detecteurs AU HASARD (~0,02)** vs supervise 0,756 ; non supervise ecarte |
| **P4-C Deep** | **fait** | **MLP 0,532 / GRU 16s 0,566** -> ne battent PAS les arbres (0,756) ; arbres = champion |
| **P5 Evaluation** | **fait** | PR-AUC hors-fold 0,735 ; seuil haute-precision **P 0,88/R 0,50** ; **LODO bimodal** (med 0,92, 6 conducteurs Groupe 1 < 0,5) ; detection portee par **Engine Speed (190)** |
| **P5+ Fragilite Groupe 1** | **fait** | **gradient d'awareness** : detectabilite G1<G2<G3 ; l'IDS detecte la **REACTION du conducteur** (G3 se gare->regime chute d=-0,48), faible sur le non-averti (G1 intra 0,46). Robuste au bruit (graduel) |
| **Auto-critique** | **fait** | `docs/04_conclusion/autocritique.md` + `_v2.md` (calquees sur le projet precedent) ; 2 demandes du sujet non faites = **ROC** + **tuning hyperparams** |
| **Verification dataset** | **fait** | `docs/04_conclusion/verification_dataset.md` : classification colonnes OK (aucune fuite) ; 2 corrections : **G1S04** CAN bas debit (gradient survit) + **spoof tach->0 ABSENT des features** (on detecte la reaction, pas l'injection) |
| Vague 1 (credibilite/sujet) | A FAIRE | ROC, optimisation hyperparams, latence + metriques par episode, SHAP, multi-seed |
| Livrables | A FAIRE | demo de detection, rapport .docx, slides .pptx (reutiliser build_report.py / build_slides.py) |

## 4. Briques de code (reutilisables)

- [`src/data.py`](src/data.py) : `load()` (cache parquet, le CSV fait 852 Mo et
  met ~100 s a charger la 1re fois) ; `classify_columns()` -> dict CAN(337) /
  bio(7) / vbox-GPS(312, confondeurs) / meta ; `usable()`.
- [`src/features.py`](src/features.py) : `feature_sets()`, `time_drift()`,
  `drive_progress()`, `driver_holdout()`, `random_holdout()`.
- [`notebooks/01_exploration.py`](notebooks/01_exploration.py) : EDA + 3 figures.
- [`notebooks/02_preprocessing.py`](notebooks/02_preprocessing.py) : confondeurs,
  split conducteur, demos chiffrees ; ecrit `data/preprocessing.json`.
- [`notebooks/03a_supervised.py`](notebooks/03a_supervised.py) : comparaison
  supervisee (GroupKFold conducteur) + ablation modalites.

## 5. Conventions / gotchas techniques

- Charger via `from data import load` (cache parquet) ; ne PAS relire le CSV brut.
- Features de travail = `feature_sets(df)["CAN"]` (337). GPS = confondeur a exclure.
- `class_weight="balanced"` partout (attaque rare). HistGB gere les NaN nativement ;
  sinon `SimpleImputer(median)` + `StandardScaler` dans un `Pipeline` (anti-fuite).
- Split = `driver_holdout()` ou `GroupKFold(groups=df.driver)`. Jamais de split aleatoire.
- Metrique principale = `average_precision_score` (PR-AUC). Reporter mean +/- std sur les folds.
- Les runs lourds (RandomForest x folds) : lancer en arriere-plan (run_in_background).
- Environnement : pas de node, pas de LibreOffice ; python-docx/python-pptx OK ;
  pas de cle API LLM. sklearn, pandas, numpy, matplotlib, pyarrow dispo.

## 6. Methode (a conserver)

Boucle : theorie -> application -> experience mesuree -> verdict assume. Meme niveau
d'explication et d'exigence qu'avant : on documente chaque etape (docs/), on traque
les confondeurs/fuites, on privilegie l'honnetete (un resultat negatif assume vaut
mieux qu'un score spurieux). Pacing : etape par etape, pause apres chaque brique.

## 7. Prochaine action concrete

P4 + P5 BOUCLES. Champion = **Gradient Boosting / CAN** : PR-AUC 0,735 (hors-fold) /
0,756 (GroupKFold) / 0,813 (LODO). Seuil recommande **haute precision** (P 0,88 /
R 0,50, < 1 % d'alertes). Detection portee par le **regime moteur (SPN 190)** ;
temperature DPF (3242) = aide redondante a surveiller (confondeur temps possible).

LIMITE CLE elucidee (P5+) : la fragilite Groupe 1 = **gradient d'awareness**. L'IDS
detecte surtout la **REACTION du conducteur** (Groupe 3 se gare -> regime moteur chute,
d=-0,48 ; detection 0,90/transfert 0,93), pas l'injection CAN pure. Sur le conducteur
NON averti (Groupe 1, aucune reaction), detection 0,46 meme entraine sur G1 = la vraie
detectabilite de l'injection pure. C'est un confondeur comportemental, a assumer.

Auto-critique ecrite (`docs/04_conclusion/autocritique.md` + `_v2.md`). Elle pointe 2
trous DANS LE SCOPE DU SUJET : **courbe ROC** et **optimisation d'hyperparametres** (non
faits). Faille la plus grave (A1) : la cible melange injection + reaction conducteur.

Reprendre par la **VAGUE 1 (credibilite, peu chere, conforme au sujet)** :
- **courbe ROC + AUC-ROC** du champion (PR-AUC reste primaire) ;
- **optimisation d'hyperparametres** du Gradient Boosting ;
- **latence de detection** + **metriques par episode** (les 50 attaques sont-elles detectees ?) ;
- **SHAP**, **multi-seed** (deep), lire le papier ORNL, audit de l'exclusion GPS + tests.
Puis **LIVRABLES** (demo seuil 0,977 ; rapport .docx ; slides .pptx) en reutilisant
`build_report.py` / `build_slides.py` de l'ancien projet
(`/Users/laury/Downloads/doi_10_5061_dryad_zw3r228jk__v20250315`, python-docx/pptx).
Materiel pret : figures docs/assets/*, JSON docs/03_evaluation/results_*.json, writeups
docs/02_experiences/, conclusions docs/04_conclusion/.

Pour reprendre : lire ce fichier, puis `journal.md` et `docs/01_projet/`, puis
`python3 src/data.py` pour verifier l'environnement.
