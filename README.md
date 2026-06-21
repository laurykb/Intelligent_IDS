# IDS Intelligent — détection de cyberattaque sur bus CAN (dataset ORNL Driver ID)

> Projet intégrateur 2026 — Encadrant : Rida Khatoun.
> Détection, par *machine learning*, d'une cyberattaque sur le réseau embarqué (CAN / J1939)
> d'un camion **Kenworth T270**, à partir du dataset multimodal **ORNL Driver Identification**
> (50 conducteurs, CAN + biométrie + GPS/inertie).

## Le projet en bref

Un enregistreur électronique (**ELD**) compromis injecte une attaque sur l'afficheur du camion
(mise à zéro du tachymètre). Le dataset enregistre **50 conducteurs** subissant cette attaque, à
un endroit fixe de leur trajet, répartis en **trois niveaux d'awareness** (non averti / averti /
averti + consigne de se garer). On construit, étape par étape, un détecteur d'intrusion **honnête**
et on en mesure rigoureusement la portée — et les limites.

## Le défi central (ce qui fait la rigueur du projet)

L'attaque survient **toujours au même endroit** et à un **moment fixe**. Un modèle naïf afficherait
un score quasi parfait en détectant le **lieu** (via le GPS) ou la **personne** (chaque conducteur
ne fait qu'un trajet) — sans rien comprendre à l'attaque. Tout l'enjeu est de **déjouer ces pièges** :

- **split par conducteur** (anti-fuite) : un split aléatoire donne PR-AUC **0,985** (trompeur),
  contre **0,632** honnête ;
- **exclusion du GPS** (confondeur de lieu) : avec le GPS, **0,835** spurieux ;
- métrique **PR-AUC** (l'attaque est rare, 1,46 %), jamais l'accuracy.

## Résultats clés

| Sujet | Résultat |
|---|---|
| Champion (Gradient Boosting / CAN, validation par conducteur) | PR-AUC **0,756** → **0,798** après optimisation |
| Courbe ROC | AUC-ROC **0,977** (PR-AUC reste la métrique honnête) |
| Deep (MLP / GRU, multi-graine) | 0,54–0,57 — ne battent pas les arbres |
| Anomalie non supervisée | ≈ 0,02 (échec assumé) |
| **Découverte** : signature de l'injection | le **bus CAN0 se tait ~4 s après l'attaque**, distinct de la réaction du conducteur |
| Robustesse | détecteur **évadable** en 1–2 signaux ; **mono-attaque** (limites assumées) |

## Structure du dépôt

```
data/          dataset ORNL (cache parquet, non versionné) + dictionnaire de données
src/           modules réutilisables : data.py (chargement, classification CAN/GPS/bio), features.py
notebooks/     pipeline d'expériences reproductibles (01_exploration → 12_attack_characterization)
docs/          00_theorie  · 01_projet  · 02_experiences  · 03_evaluation  · 04_conclusion
deliverables/  démonstrateur Streamlit (app.py), rapport (.docx) et slides (.pptx) + leurs générateurs
artifacts/     modèle entraîné + échantillons (inférence de la démo)
tests/         tests unitaires (invariants anti-fuite)
```

## Démarrage rapide

```bash
# environnement (Python 3.11)
python -m venv .venv
.venv\Scripts\activate            # Windows   (Mac/Linux : source .venv/bin/activate)
pip install -r requirements.lock.txt
pip install -r deliverables/requirements.txt

# le démonstrateur interactif (ne nécessite pas les données brutes)
streamlit run deliverables/app.py     # http://localhost:8501
```

## Reproduire les expériences

Les notebooks lisent le cache `data/cache.parquet`, reconstruit au premier appel depuis le CSV
brut (852 Mo, non versionné). Pointez le loader vers le CSV via la variable d'environnement
`IDS_CSV` :

```bash
IDS_CSV="/chemin/vers/DriverID_Full_Data_Downsampled.csv" python src/data.py   # construit le cache
python notebooks/01_exploration.ipynb     # EDA + figures   (puis 02, 03a, ... dans l'ordre)
pytest tests/                          # 14 tests : invariants anti-fuite
```

## Livrables

- **Démonstrateur** (`deliverables/app.py`) : banc d'essai interactif — voir l'IDS détecter en
  direct, jouer l'attaquant, inventer une attaque, éprouver le piège méthodologique, régler le
  déploiement. Voir [deliverables/README.md](deliverables/README.md).
- **Rapport** (`deliverables/Rapport_IDS_Intelligent.docx`) — généré par `python build_report.py`.
- **Slides** (`deliverables/Presentation_IDS_Intelligent.pptx`) — générés par `python build_slides.py`.

## Documentation

Le raisonnement complet est tracé dans `docs/` : socle théorique (`00_theorie`), cadrage
(`01_projet`), expériences par chemin (`02_experiences`), résultats (`03_evaluation`), et
conclusions / auto-critiques (`04_conclusion`, dont l'auto-évaluation `evaluation_jury.md`). Le
carnet de bord daté est dans [journal.md](journal.md).

## Données & contexte

ORNL Driver Identification Dataset (downsampled) — 155 902 fenêtres de 1 s, 50 conducteurs,
Kenworth T270. Publication associée : Lanigan et al., *Journal of Transportation Security*, 2025.
Même écosystème de recherche que l'avis **CISA ICSA-24-093-01** (équipe J. Daily, Colorado State).
