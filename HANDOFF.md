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
- **[Vague 2] La signature d'injection EXISTE** : le bus CAN0 (SPN 190) se tait ~4 s apres
  l'onset (couverture 67%->6,7%, tous groupes) = effet direct de l'injection, distinct de la
  reaction. C'est meme la feature n0 1 du champion. Nuance la conclusion "injection absente" de
  verification_dataset.md (absente en VALEUR, presente en MISSINGNESS). Cf. vague2_profondeur.md.

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
| **Vague 1 (credibilite/sujet)** | **7/7 FAIT** | ROC **AUC 0,977** vs PR 0,735 ; **86 % d'episodes detectes en ~4 s** ; PDP (temp DPF monte, regime 190 par interactions) ; papier source ORNL valide le gradient d'awareness ; **14 tests OK** + lock versions ; **tuning 0,757->0,798 (+0,040)** ; **multi-seed MLP 0,543 vs GRU 0,571 = non significatif** (2 runs lourds boucles sur PC GPU le 2026-06-19) |
| **Vague 2 (profondeur)** | **5/5 FAIT** | **signature d'injection isolee** (silence bus CAN0 ~4s apres onset = injection, indep. reaction -> reponse a A1) ; evasion **fragile** (1-2 signaux suffisent) ; biometrie **inutile** (meme par groupe) ; clustering/RBF/semi-sup/hybride = **rien ne bat les arbres** ; **mono-attaque** (fuzzing/masquerade/replay non detectes). Synthese : `docs/02_experiences/vague2_profondeur.md` |
| Vague 3 (generalisation) | RELEGUEE hors-scope | autres datasets/RAG/deploiement, en partie infaisable hors-ligne -> section "Limites & perspectives" du rapport, NON implementee (decision de scope) |
| **Livrables : DEMO** | **FAIT (enrichie)** | **app Streamlit** `deliverables/app.py` (11 pages) : parcours complet + **detection animee** (play/pause) + **attaquant pilote en LIVE** (evasion sur le vrai modele `artifacts/ids_model.joblib`) + **base-rate fallacy**. Inspiree de l'ancien projet, dans le scope (PAS de vue RAG). Lancer : `streamlit run deliverables/app.py`. Cf. `deliverables/README.md` |
| **Livrables : rapport + slides** | **FAIT** | `build_report.py` -> `deliverables/Rapport_IDS_Intelligent.docx` (15 chapitres) ; `build_slides.py` -> `deliverables/Presentation_IDS_Intelligent.pptx` (25 diapos). Adaptes des generateurs python-docx/pptx de l'ancien projet, sans le chapitre RAG/attention (hors-scope) |

## 4. Briques de code (reutilisables)

- [`src/data.py`](src/data.py) : `load()` (cache parquet, le CSV fait 852 Mo et
  met ~100 s a charger la 1re fois) ; `classify_columns()` -> dict CAN(337) /
  bio(7) / vbox-GPS(312, confondeurs) / meta ; `usable()`.
- [`src/features.py`](src/features.py) : `feature_sets()`, `time_drift()`,
  `drive_progress()`, `driver_holdout()`, `random_holdout()`.
- [`notebooks/01_exploration.ipynb`](notebooks/01_exploration.ipynb) : EDA + 3 figures.
- [`notebooks/02_preprocessing.ipynb`](notebooks/02_preprocessing.ipynb) : confondeurs,
  split conducteur, demos chiffrees ; ecrit `data/preprocessing.json`.
- [`notebooks/03a_supervised.ipynb`](notebooks/03a_supervised.ipynb) : comparaison
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

### >>> VAGUE 1 BOUCLEE (7/7) — les 2 runs lourds sont faits (PC GPU, 2026-06-19)

Synthese : [`docs/02_experiences/vague1_credibilite.md`]. Resultats finaux :
1. **Item 2 tuning** -> `docs/03_evaluation/results_tuning.json` : defaut **0,757** -> optimise
   **0,798** (**+0,040**). Params : max_leaf_nodes=15, learning_rate=0,1, l2=10,0, max_iter=400.
2. **Item 5 multi-seed** -> `results_multiseed.json` : MLP **0,543 ± 0,016** vs GRU **0,571 ± 0,024**,
   ecart **non significatif** (artefact de graine ; arbres restent champions).

**Environnement de CE PC (Windows + GPU)** : venv `.venv/` (Python 3.11) ; lancer via
`.venv/Scripts/python.exe`. torch **2.6.0+cu124** (CUDA, RTX 2060 SUPER). `data/cache.parquet`
reconstruit (gitignored). Le CSV brut est hors-repo -> loader surchargeable par `IDS_CSV`
(cf. `src/data.py`). `06e_multiseed.py` auto-detecte le GPU (`IDS_DEVICE` pour forcer cpu).
Provenance des chiffres + **preuve de repro cross-plateforme** (champion identique Mac/Windows) :
`docs/04_conclusion/environnement_calcul.md` ; lock GPU exact : `requirements-gpu.lock.txt`.

### >>> PROCHAINE ETAPE : LIVRABLES

Produire : **demo de detection** (scorer une trace + alerte au seuil haute-precision 0,977) ;
**rapport .docx** ; **slides .pptx** — en reutilisant `build_report.py` / `build_slides.py` de
l'ancien projet (python-docx/python-pptx). Materiel pret : figures docs/assets/* (dont v1_*),
JSON docs/03_evaluation/results_*.json, writeups docs/02_experiences/, conclusions
docs/04_conclusion/, references docs/01_projet/references.md.

Pour reprendre : lire ce fichier, puis `journal.md` et `docs/01_projet/`, puis
`.venv/Scripts/python.exe src/data.py` pour verifier l'environnement (au besoin
`IDS_CSV=<chemin du CSV> .venv/Scripts/python.exe src/data.py` si le cache est absent).
