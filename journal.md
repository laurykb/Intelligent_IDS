# Carnet de bord

## 2026-06-19 - Redemarrage sur le dataset ORNL Driver ID (P0 + P1)

### Contexte du pivot
- Changement de dataset : on passe du log CAN brut (Wireless_Pedal_Jam) au **ORNL
  Driver Identification Dataset**. La consigne IDS s'applique a ce dataset.
- Tache retenue : **detection d'intrusion** (cible `cyberattack_active`), avec
  l'identification du conducteur comme axe secondaire ET contrainte de fuite.

### Fait
- Nouveau projet : `/Users/laury/Documents/IDS_ORNL` (structure src/docs/notebooks/...).
- Loader [`src/data.py`](src/data.py) : cache parquet (CSV de 852 Mo) + classification
  des colonnes en CAN (337) / GPS-inertie (320, confondeurs) / biometrie (HR/EDA/IBI) / meta.
- EDA [`notebooks/01_exploration.py`](notebooks/01_exploration.py) + 3 figures.
- Docs P0/P1 : contexte, problematique, plan, eda_findings.

### Decouvertes cles (EDA)
- 155 902 fenetres de 1 s, 50 conducteurs (3 groupes), **1,46 % d'attaque** (rare, realiste).
- **Confondeur LIEU** : l'attaque est 7 a 44x plus concentree geographiquement que le trajet
  -> un modele GPS detecterait le lieu, pas l'attaque. Cohen's d GPS = 2,63.
- **Confondeur TEMPS** : attaque a ~60 % du trajet ; les signaux a derive (temperatures)
  correlent avec l'heure. Meilleur signal CAN « honnete » d=1,48 = encore un confondeur.
- **Reponse biometrique** : HR monte pendant l'attaque (+1,7 a +3,1 bpm), module par le groupe
  d'awareness (max pour le groupe 2). Effet reel mais modeste (d=0,14).
- 28 % de NaN ; 141 colonnes > 50 % manquant.

### Decisions methodo qui en decoulent
- **Exclure les features GPS/inertie** (confondeur lieu).
- **Split PAR CONDUCTEUR** (anti-fuite) + validation croisee groupee.
- Metriques **PR-AUC / precision-recall** (desequilibre).
- Faire une **ablation avec/sans GPS** pour chiffrer le piege.
- Question honnete a trancher : l'attaque est-elle detectable proprement hors confondeurs ?

### Ce qui transfere de l'ancien projet
- Toute la methodo, la theorie ML, le harnais de comparaison de modeles, la rigueur
  d'evaluation, la pratique d'auto-critique, la structure des livrables.

### Prochaine etape
- **P2/P3** : pretraitement (NaN, normalisation, selection hors confondeurs) et mise en place
  du split par conducteur + validation croisee groupee.

---

## 2026-06-19 - P2/P3 (pretraitement honnete + split par conducteur)

### Fait
- [`src/features.py`](src/features.py) : jeux de features (CAN/BIO/GPS), detection des confondeurs
  temps (correlation a la progression du trajet), split par conducteur (driver_holdout) + split
  aleatoire (pour demontrer la fuite). [`notebooks/02_preprocessing.py`](notebooks/02_preprocessing.py).
- Doc [`docs/01_projet/features.md`](docs/01_projet/features.md) + figure + `data/preprocessing.json`.

### Resultats (PR-AUC, Gradient Boosting ; hasard ~ 0,015)
- **GPS, split conducteur = 0,834** -> spurieux (geofencing du lieu de l'attaque).
- **CAN honnete, split conducteur = 0,632** -> la vraie difficulte ; signal genuine existe.
- CAN_STABLE (21 signaux time-drift exclus) = 0,630 -> le signal NE vient PAS du confondeur temps.
- **CAN, split aleatoire = 0,985** vs 0,632 par conducteur -> fuite conducteur massive (+0,35).

### Decisions
- Features de travail : **CAN (337)** ; GPS exclu ; biometrie en axe secondaire.
- **Split par conducteur** obligatoire (GroupKFold en P5). Point de depart honnete = 0,632.
- NaN geres nativement par HistGB ; imputation mediane dans le pipeline pour les autres modeles.

### Prochaine etape
- **P4 - Modelisation multi-chemins** (supervise / anomalie / deep) sur les features CAN, avec
  validation croisee par conducteur et metriques PR-AUC / precision-recall.

---

## 2026-06-19 - P4 chemin A (apprentissage supervise)

### Fait
- [`notebooks/03a_supervised.py`](notebooks/03a_supervised.py) : 4 modeles en GroupKFold par
  conducteur (4 folds), PR-AUC, + ablation des modalites. Writeup
  [`docs/02_experiences/chemin_A_supervise.md`](docs/02_experiences/chemin_A_supervise.md) + figure.

### Resultats (PR-AUC, val. par conducteur ; hasard ~ 0,015)
- LogReg 0,407 / SVM-lin 0,390 / RandomForest 0,709 / **GradBoosting 0,756 +/- 0,088** (champion).
- Ablation : CAN 0,756 ; CAN+BIO 0,749 ; **BIO seul 0,014 (= hasard)** ; GPS 0,835 (spurieux).

### Enseignements
- Arbres boostes >> lineaires -> signature non lineaire dans le CAN.
- **La biometrie n'aide pas** (resultat honnete) : reponse HR reelle mais trop faible/bruitee.
- GPS confirme comme confondeur (0,835 > 0,756) meme par conducteur.
- Variance inter-folds elevee (+/- 0,09) -> generalisation a de nouveaux conducteurs incertaine (P5).

### Prochaine etape
- **P4 chemin B (anomalie)** : Isolation Forest / One-Class SVM / PCA, sans labels, adapte a
  l'attaque rare ; puis chemin C (deep).

---

## 2026-06-19 - P4 chemin B (detection d'anomalie)

### Fait
- [`notebooks/03b_anomaly.py`](notebooks/03b_anomaly.py) : 4 detecteurs entraines sur le NORMAL
  des conducteurs de train (novelty detection), scores en GroupKFold par conducteur, PR-AUC.
  Writeup [`docs/02_experiences/chemin_B_anomalie.md`](docs/02_experiences/chemin_B_anomalie.md)
  + figure + `docs/03_evaluation/results_anomaly.json`.

### Resultats (PR-AUC, val. par conducteur ; hasard ~ 0,015)
- One-Class SVM 0,021 / Gaussienne diag. 0,020 / PCA recon. 0,019 / Isolation Forest 0,018.
- **Les 4 detecteurs sont AU NIVEAU DU HASARD** -> echec franc de l'approche non supervisee
  (a comparer au supervise 0,756).

### Enseignements
- La **variabilite inter-conducteur** noie l'attaque : en split par conducteur, le normal de test
  est deja une nouveaute, le detecteur depense son budget d'anomalie dessus.
- L'attaque **n'est pas un outlier global** mais une combinaison conditionnelle de signaux ->
  il faut les labels (chemin A) pour l'isoler. Rare != aberrant.
- Resultat negatif assume : justifie l'approche supervisee, ecarte l'anomalie comme detecteur
  principal (eventuel garde-fou de second rang).

### Prochaine etape
- **P4 chemin C (deep)** : MLP / LSTM sur les features CAN (probable que les arbres dominent en
  tabulaire) ; puis **P5** (courbes PR, tuning, generalisation par conducteur, variance +/-0,09).

---

## 2026-06-19 - P4 chemin C (deep : MLP + GRU temporel)

### Fait
- [`notebooks/03c_deep_mlp.py`](notebooks/03c_deep_mlp.py) : MLP tabulaire (337 CAN, BatchNorm/
  Dropout, pos_weight) en GroupKFold conducteur. PyTorch 2.12 (CPU).
- [`notebooks/03d_deep_gru.py`](notebooks/03d_deep_gru.py) : GRU sur fenetres glissantes de 16 s
  construites PAR CONDUCTEUR (capte la dynamique), meme validation.
- Writeup [`docs/02_experiences/chemin_C_deep.md`](docs/02_experiences/chemin_C_deep.md) + figure
  `docs/assets/p4c_deep.png` + `docs/03_evaluation/results_deep.json`.

### Resultats (PR-AUC, val. par conducteur ; arbres = 0,756 ; hasard ~ 0,015)
- **MLP 0,532 +/- 0,100** / **GRU 0,566 +/- 0,084** -> aucun ne bat les arbres boostes (0,756).
- Le GRU > MLP : le contexte temporel (16 s) apporte un petit signal reel, mais insuffisant.

### Enseignements
- Tabulaire + peu de positifs (~1700) + forte variabilite inter-conducteur (fold 1 s'effondre :
  MLP 0,371 / GRU 0,424) -> regime defavorable aux reseaux, favorable aux arbres (etat de l'art).
- Le signal est surtout dans la signature CAN INSTANTANEE (seuillage non lineaire), pas dans sa
  dynamique temporelle.
- Confondeur temps surveille : GRU n'explose pas son score (coherent avec CAN_STABLE ~ CAN).

### Bilan P4 (3 chemins)
- A supervise (arbres) **0,756** = CHAMPION ; C deep 0,57/0,53 ; B anomalie ~0,02 (echec).

### Prochaine etape
- **P5 - Evaluation fine du champion** (Gradient Boosting CAN) : courbes precision-rappel, choix
  du seuil operationnel, generalisation par conducteur / leave-one-driver-out pour expliquer la
  variance +/-0,09, importance des signaux CAN (quels SPN portent la detection).

---

## 2026-06-19 - P5 (evaluation fine du champion Gradient Boosting / CAN)

### Fait
- [`notebooks/04_evaluation.py`](notebooks/04_evaluation.py) : (1) predictions hors-fold ->
  courbe PR + table de seuils ; (2) leave-one-driver-out (50 conducteurs) ; (3) permutation
  importance des signaux CAN. Writeup [`docs/02_experiences/p5_evaluation.md`](docs/02_experiences/p5_evaluation.md)
  + figures `p5_pr_curve.png`, `p5_lodo_importance.png` + `docs/03_evaluation/results_evaluation.json`.

### Resultats
- **Courbe PR** : PR-AUC hors-fold 0,735. Seuil F1-max -> P 0,80 / R 0,66. Point haute precision
  (rappel 0,5) -> **P 0,885, < 1 % de fenetres alertees** ; rappel 0,9 -> P 0,22 (alarme fatigue).
- **LODO** : moyenne 0,813 +/- 0,270, **mediane 0,920** ; 38/50 conducteurs >= 0,80 mais
  **7 < 0,50, dont 6 du Groupe 1** (1_S4=0,05, 1_S11=0,08, ...). Distribution BIMODALE.
- **Importance** : 2 signaux portent la detection -> **190 Engine Speed (+0,42)** et
  **3242 DPF Intake Temperature (+0,41)**, puis longue traine.

### Enseignements
- Le score moyen cache une **generalisation bimodale** : excellente sauf pour ~6 conducteurs du
  Groupe 1 -> c'est la vraie fragilite (explique la variance +/-0,09 de P4). A creuser (awareness ?).
- Detection GENUINE portee par le **regime moteur (190)** = signature plausible d'attaque CAN ;
  la temperature DPF (3242) est une aide redondante et **possible confondeur temps** (mais
  CAN_STABLE avait montre que le modele n'en depend pas : 0,630 vs 0,632).
- Seuil recommande pour un IDS deployable : **haute precision** (P 0,88 / R 0,50) ; l'attaque
  etant un bloc continu, attraper 50 % des secondes suffit a detecter l'episode.

### Prochaine etape
- **Robustesse / cote "intelligent"** de l'IDS (ex. tenue sous bruit/derive, analyse du Groupe 1),
  puis **livrables** : demo, rapport .docx et slides .pptx en reutilisant build_report.py /
  build_slides.py de l'ancien projet.

---

## 2026-06-19 - P5+ (fragilite Groupe 1 + robustesse)

### Fait
- [`notebooks/05_group_analysis.py`](notebooks/05_group_analysis.py) : LODO par groupe, leave-one-
  GROUP-out (transfert), detectabilite intra-groupe, signature SPN 190 par groupe, robustesse bruit.
  Writeup [`docs/02_experiences/p5b_group_fragility.md`](docs/02_experiences/p5b_group_fragility.md)
  + figure `p5b_group_analysis.png` + `docs/03_evaluation/results_group_analysis.json`.

### Resultats (les groupes = niveaux d'AWARENESS : G1 rien su / G2 prevenu / G3 prevenu+se garer)
- **Gradient d'awareness** : LODO mediane G1 0,74 / G2 0,92 / G3 0,96 (6/17 conducteurs G1 < 0,5).
- **Transfert (LOGO)** : test G1 (train autres) = 0,41 ; G2 = 0,75 ; G3 = 0,93.
- **Intra-groupe** : G1 = 0,46 ; G2 = 0,68 ; G3 = 0,90. -> G1 dur MEME entraine sur G1 (intrinseque).
- **Mecanisme** : regime moteur (mean.190.Engine.Speed) pendant l'attaque : G3 d=-0,48 (ils SE GARENT,
  le regime chute) vs G1 d=+0,13 (pas de reaction). Duree attaque 56s(G1)/47s(G2)/33s(G3).
- **Robustesse** : PR-AUC 0,632 -> 0,493 a 50% de sigma de bruit (degradation graduelle, pas de cliff).

### Enseignement central (a assumer)
- L'IDS detecte surtout la **REACTION du conducteur**, pas l'injection CAN pure. Il est donc le plus
  faible sur le conducteur NON averti (Groupe 1) = le cas ou un IDS serait le plus utile. Une partie
  de la "detection" est un confondeur comportemental. La detectabilite de l'injection pure est plus
  proche du 0,46 (intra-G1) que du 0,76 moyen. Limite du dataset (ne separe pas injection/reaction).

### Prochaine etape
- **Livrables** : demo de detection (scorer une trace + alerter au seuil), rapport .docx, slides .pptx
  en reutilisant build_report.py / build_slides.py de l'ancien projet (python-docx/pptx).

---

## 2026-06-19 - Auto-critique (conclusion, calquee sur le projet precedent)

### Fait
- Lu le sujet (PDF Khatoun) : checklist explicite -> 2 demandes LITTERALES non faites = **courbe ROC**
  et **optimisation d'hyperparametres**.
- Ecrit [`docs/04_conclusion/autocritique.md`](docs/04_conclusion/autocritique.md) (failles A1-A6 +
  litterature + plan en Vagues 1/2/3 + lecon) et
  [`docs/04_conclusion/autocritique_v2.md`](docs/04_conclusion/autocritique_v2.md) (seconde passe
  largeur/ingenierie B1-B13 + addendum priorise + verdict), specifiques au dataset ORNL.

### Failles cles retenues
- **A1 (la plus grave)** : la cible MELANGE injection + reaction du conducteur -> on detecte la
  reaction, pas l'injection pure (cf. P5+). Cible jamais isolee, onset/canal du spoof non confirmes.
- **A2** : ROC manquante (sujet), hyperparams non regles (sujet), latence + metriques PAR EPISODE
  absentes, deep mono-seed.
- **A5/B12** : biometrie + awareness = l'ORIGINALITE du dataset, sous-exploitee (axe d'analyse, pas
  de modelisation). Surtout pour le Groupe 1 ou le CAN echoue.
- Largeur d'ingenieur (v2) : modele de menace, deploiement embarque, gestion de projet, ethique/RGPD.

### Plan en vagues
- **Vague 1 (credibilite, peu cher)** : ROC + tuning (sujet), latence/episode, SHAP, multi-seed,
  lire le papier ORNL, audit exclusion GPS + tests.
- **Vague 2 (profondeur)** : isoler l'injection (incoherence inter-bus 190 vs 190.CAN0), attaquant
  adaptatif, fusion biometrie/awareness, clustering/hybride, taxonomie de menaces.
- **Vague 3 (generalisation/intelligent)** : ROAD/Car-Hacking, attention+RAG, demo deploiement, SOTA.

### Prochaine etape
- Soit attaquer la **Vague 1** (ROC + tuning = conformite directe au sujet), soit produire les
  **livrables** (rapport/slides/demo). Recommandation : Vague 1 d'abord (rend le projet conforme et
  credible), puis livrables qui integreront ces resultats.

---

## 2026-06-19 - Verification du dataset vs doc officielle (audit anti-betise)

### Fait
- Confronte le pipeline au README + dictionnaire de donnees (dossier "ORNL Driver Identification
  Dataset"). Note [`docs/04_conclusion/verification_dataset.md`](docs/04_conclusion/verification_dataset.md).

### Confirme (rien a corriger)
- VBOX = GPS/inertie (confondeur), bio = Empatica E4, CAN = J1939, groupes = awareness exacts,
  agregation 1 s par moyenne. Classification colonnes OK : AUCUNE fuite GPS/survey dans le CAN ;
  Qualtrics (MMDBQ/GRiPS/demo) + cumulative_distance bien en meta (exclus).

### Corrige (2 betises d'honnetete)
1. **G1S04** = notre pire conducteur LODO (0,05) a un **CAN basse frequence** (erreur documentee).
   Son effondrement est en partie un artefact de donnees. Mais le gradient d'awareness SURVIT sans
   lui (Groupe 1 mediane 0,75, 5/16 < 0,5, vs 0,92/0,96). Caveat ajoute a p5b_group_fragility.md.
2. **Le spoof tach->0 est ABSENT des features** : mean.190.Engine.Speed = 0 % de ~0 pendant
   l'attaque (le logger a capte les vraies diffusions ECU, pas l'injection vers l'afficheur).
   -> j'avais ecrit a tort que le SPN 190 etait une "signature de spoofing" ; corrige dans
   p5_evaluation.md. Cela RENFORCE P5+ (on detecte la reaction, pas l'injection) et A1/B3/B4.

### Impact
- Tous les chiffres restent valides (pas de fuite, pas de mauvais split). Seule l'interpretation de
  l'importance change. Piste Vague 2 : recuperer la donnee HAUTE RESOLUTION (1/100 s) pour esperer
  voir la signature d'injection sous-seconde.
- Donnees degradees a signaler : G1S04 (CAN bas debit), G1S15/16, G2S13, G3S13 (VBOX manquant, sans
  impact car GPS exclu), G1S09 (reset VBOX).

### Prochaine etape
- **VAGUE 1** (validee, on y va) : ROC + AUC-ROC, optimisation d'hyperparametres, latence + metriques
  par episode, SHAP, multi-seed deep.
